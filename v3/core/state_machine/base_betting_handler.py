"""
通用下注阶段处理器模块
"""
from typing import Dict, Any, Optional
from .types import GamePhase, GameEvent, GameContext
from .base_phase_handler import BasePhaseHandler

__all__ = ['BaseBettingHandler']

class BaseBettingHandler(BasePhaseHandler):
    """所有下注阶段处理器的基类，包含通用的下注逻辑"""

    def on_enter(self, ctx: GameContext) -> None:
        super().on_enter(ctx)
        self._reset_betting_round(ctx)

    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """
        (Phase 2) 使用ChipLedger重构，统一处理所有下注阶段的玩家行动
        """
        action_type = action.get('action_type', '').lower()
        player_data = ctx.players.get(player_id)
        
        if not player_data:
            return GameEvent("INVALID_ACTION", {"reason": f"玩家 {player_id} 不存在"}, self.phase)

        if not self._is_player_actionable(ctx, player_id):
             return GameEvent("INVALID_ACTION", {"reason": f"玩家 {player_id} 当前不可行动"}, self.phase)

        player_balance = ctx.chip_ledger.get_balance(player_id)
        player_current_bet = ctx.current_hand_bets.get(player_id, 0)

        # 行动处理
        if action_type == 'fold':
            player_data['status'] = 'folded'
        
        elif action_type == 'check':
            # 验证已在ValidationService中完成，这里只处理状态
            pass
        
        elif action_type == 'call':
            amount_to_call = ctx.current_bet - player_current_bet
            amount_to_freeze = min(amount_to_call, player_balance)
            
            if amount_to_freeze > 0:
                ctx.chip_ledger.freeze_chips(player_id, amount_to_freeze, "Action: CALL")
                ctx.current_hand_bets[player_id] += amount_to_freeze
                if amount_to_freeze >= player_balance:
                    player_data['status'] = 'all_in'

        elif action_type == 'raise':
            # action['amount'] 是指加注后的总下注额
            total_bet_amount = action.get('amount', 0)
            amount_to_freeze = total_bet_amount - player_current_bet
            
            ctx.chip_ledger.freeze_chips(player_id, amount_to_freeze, "Action: RAISE")
            ctx.current_hand_bets[player_id] = total_bet_amount
            ctx.current_bet = total_bet_amount
            
            if amount_to_freeze >= player_balance:
                player_data['status'] = 'all_in'
            
            # 加注后，其他玩家需要重新行动
            self._reset_players_action_status(ctx, raiser_id=player_id)

        elif action_type == 'all_in':
            amount_to_freeze = player_balance
            if amount_to_freeze > 0:
                ctx.chip_ledger.freeze_chips(player_id, amount_to_freeze, "Action: ALL_IN")
                new_total_bet = player_current_bet + amount_to_freeze
                ctx.current_hand_bets[player_id] = new_total_bet
                player_data['status'] = 'all_in'
                
                if new_total_bet > ctx.current_bet:
                    ctx.current_bet = new_total_bet
                    self._reset_players_action_status(ctx, raiser_id=player_id)
        else:
            return GameEvent("INVALID_ACTION", {"reason": f"未知行动 {action_type}"}, self.phase)

        player_data['has_acted_this_round'] = True
        return self._determine_next_step(ctx)

    def _determine_next_step(self, ctx: GameContext) -> GameEvent:
        """在玩家行动后，决定游戏的下一步"""
        if self._should_auto_finish_hand(ctx):
            return GameEvent("HAND_AUTO_FINISH", {"reason": "只剩一个或零个玩家在手"}, self.phase)
            
        next_player_id = self._find_next_actionable_player(ctx, ctx.active_player_id)
        
        if not next_player_id or self._check_betting_round_complete(ctx):
            event_map = {
                GamePhase.PRE_FLOP: "PRE_FLOP_COMPLETE",
                GamePhase.FLOP: "FLOP_COMPLETE",
                GamePhase.TURN: "TURN_COMPLETE",
                GamePhase.RIVER: "RIVER_COMPLETE",
            }
            reason = "无更多可行动玩家" if not next_player_id else "下注回合完成"
            return GameEvent(event_map.get(self.phase, "UNKNOWN_ROUND_COMPLETE"), {"reason": reason}, self.phase)

        ctx.active_player_id = next_player_id
        return GameEvent("ACTION_PROCESSED", {"next_player": next_player_id}, self.phase)

    def _is_player_actionable(self, ctx: GameContext, player_id: str) -> bool:
        player_data = ctx.players.get(player_id, {})
        # (Phase 2) 使用ChipLedger检查筹码
        return (
            player_data.get('active', False) and
            ctx.chip_ledger.get_balance(player_id) > 0 and
            player_data.get('status') not in ['folded', 'out', 'all_in']
        )

    def _find_next_actionable_player(self, ctx: GameContext, current_player_id: str) -> Optional[str]:
        # 修复：必须根据玩家位置对玩家进行排序，以确保正确的行动顺序
        if not ctx.players:
            return None

        # 创建一个 (position, player_id) 的元组列表并排序
        sorted_players = sorted(
            [(p_data['position'], p_id) for p_id, p_data in ctx.players.items()]
        )
        
        # 提取排序后的 player_ids
        player_ids = [p_id for _, p_id in sorted_players]

        if not player_ids: return None

        try:
            start_index = player_ids.index(current_player_id)
        except ValueError:
            # 如果起始玩家ID无效或不存在，这可能是一个问题，但我们暂时从头开始
            start_index = -1

        # 从起始玩家的下一个位置开始循环，寻找可行动的玩家
        for i in range(1, len(player_ids) + 1):
            next_index = (start_index + i) % len(player_ids)
            next_player_id = player_ids[next_index]
            
            # 检查该玩家是否可以行动
            player_data = ctx.players[next_player_id]
            if (player_data.get('status') not in ['folded', 'out', 'all_in'] and
                    ctx.chip_ledger.get_balance(next_player_id) > 0):
                return next_player_id
        
        return None
        
    def _check_betting_round_complete(self, ctx: GameContext) -> bool:
        # A simpler check:
        # Get all players still in the hand (not folded or out).
        active_players_data = [p for p in ctx.players.values() if p.get('status') not in ['folded', 'out']]
        if not active_players_data:
            return True

        # Among them, get those who are not all-in. They are the ones who must have equal bets.
        players_who_can_bet_data = [p for p in active_players_data if p.get('status') != 'all_in']

        # If there are no players who can still bet (e.g., everyone is all-in), the betting round is over.
        if not players_who_can_bet_data:
            return True

        # Check if all players who can bet have acted in this round.
        if not all(p.get('has_acted_this_round', False) for p in players_who_can_bet_data):
            return False
        
        # We need player_ids to check their bets in the context
        active_player_ids = [p_id for p_id, p in ctx.players.items() if p.get('status') not in ['folded', 'out']]
        players_who_can_bet_ids = [p_id for p_id in active_player_ids if ctx.players[p_id].get('status') != 'all_in']

        if not players_who_can_bet_ids:
            return True # Everyone is all-in or folded

        # Check if all players who can bet have acted in this round and have equal bets.
        first_player_bet = ctx.current_hand_bets.get(players_who_can_bet_ids[0], 0)
        
        all_bets_equal = all(
            ctx.current_hand_bets.get(p_id, 0) == first_player_bet 
            for p_id in players_who_can_bet_ids
        )
        
        all_acted = all(
            ctx.players[p_id].get('has_acted_this_round', False)
            for p_id in players_who_can_bet_ids
        )

        return all_acted and all_bets_equal

    def _should_auto_finish_hand(self, ctx: GameContext) -> bool:
        players_in_hand = [p for p_id, p in ctx.players.items() if p.get('status') not in ['folded', 'out']]
        return len(players_in_hand) <= 1

    def _reset_players_action_status(self, ctx: GameContext, raiser_id: str) -> None:
        for p_id, p_data in ctx.players.items():
            if p_id != raiser_id and p_data.get('status') not in ['folded', 'out', 'all_in']:
                p_data['has_acted_this_round'] = False

    def _reset_betting_round(self, ctx: GameContext) -> None:
        ctx.current_bet = 0
        for p_id, player_data in ctx.players.items():
            # Only reset if they are not out
            if player_data.get('status') != 'out':
                player_data['has_acted_this_round'] = False
                # The per-round bet 'current_bet' is cleared by clearing current_hand_bets for the new hand
                # but for subsequent rounds (flop, turn, river) we need to reset action status
                # but not their total hand bets. Let's adjust GameCommandService._reset_players_for_new_hand
                # to clear current_hand_bets instead. Here we only reset current_bet.
                
                # NO, _reset_players_for_new_hand is for a NEW HAND.
                # Here, for a NEW ROUND, we need to reset the 'has_acted' flag and the round's current bet.
                # ctx.current_hand_bets should NOT be cleared here. It tracks bets for the whole hand.
                # The logic in `handle_player_action` relies on player_current_bet from ctx.current_hand_bets
                # to calculate the needed amount for a call.
                # What needs to be reset is the concept of a "round bet".
                # The field player_data['current_bet'] was serving this purpose. Let's keep it for that.
                player_data['current_bet'] = 0

        # We also need to reset the round's `current_bet` to 0 so players can check.
        ctx.current_bet = 0 