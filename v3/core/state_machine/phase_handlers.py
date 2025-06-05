"""
阶段处理器实现

提供各个游戏阶段的具体处理逻辑。
"""

from typing import Dict, Any, List, Optional
from .types import GamePhase, GameEvent, GameContext, PhaseHandler

__all__ = [
    'InitHandler',
    'PreFlopHandler', 
    'FlopHandler',
    'TurnHandler',
    'RiverHandler',
    'ShowdownHandler',
    'FinishedHandler'
]


class BasePhaseHandler:
    """基础阶段处理器，提供通用功能"""
    
    def __init__(self, phase: GamePhase):
        self.phase = phase
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入阶段的默认处理"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[游戏阶段] 进入阶段: {self.phase.name}")
    
    def on_exit(self, ctx: GameContext) -> None:
        """退出阶段的默认处理"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[游戏阶段] 退出阶段: {self.phase.name}")
    
    def can_transition_to(self, target_phase: GamePhase, ctx: GameContext) -> bool:
        """检查是否可以转换到目标阶段"""
        # 基本的转换规则
        valid_transitions = {
            GamePhase.INIT: [GamePhase.PRE_FLOP],
            GamePhase.PRE_FLOP: [GamePhase.FLOP, GamePhase.SHOWDOWN, GamePhase.FINISHED],
            GamePhase.FLOP: [GamePhase.TURN, GamePhase.SHOWDOWN, GamePhase.FINISHED],
            GamePhase.TURN: [GamePhase.RIVER, GamePhase.SHOWDOWN, GamePhase.FINISHED],
            GamePhase.RIVER: [GamePhase.SHOWDOWN, GamePhase.FINISHED],
            GamePhase.SHOWDOWN: [GamePhase.FINISHED],
            GamePhase.FINISHED: [GamePhase.PRE_FLOP, GamePhase.INIT]
        }
        
        return target_phase in valid_transitions.get(self.phase, [])


class InitHandler(BasePhaseHandler):
    """初始化阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.INIT)
    
    def on_enter(self, ctx: GameContext) -> None:
        """初始化游戏状态"""
        super().on_enter(ctx)
        # 重置游戏状态
        ctx.community_cards.clear()
        ctx.pot_total = 0
        ctx.current_bet = 0
        ctx.active_player_id = None
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """初始化阶段不处理玩家行动"""
        return GameEvent(
            event_type="INVALID_ACTION",
            data={"reason": "初始化阶段不能执行玩家行动"},
            source_phase=self.phase
        )


class PreFlopHandler(BasePhaseHandler):
    """翻牌前阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.PRE_FLOP)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入翻牌前阶段"""
        super().on_enter(ctx)
        # 清理之前手牌的状态（如果是新手牌开始）
        self._cleanup_previous_hand(ctx)
        # 发手牌 - 盲注已在application层设置，这里不再重复设置
        self._deal_hole_cards(ctx)
        # 设置第一个行动的玩家（如果还没有设置的话）
        if not ctx.active_player_id:
            self._set_first_active_player(ctx)
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理翻牌前的玩家行动"""
        action_type = action.get('action_type')
        
        if action_type == 'fold':
            return self._handle_fold(ctx, player_id, action)
        elif action_type == 'call':
            return self._handle_call(ctx, player_id, action)
        elif action_type == 'raise':
            return self._handle_raise(ctx, player_id, action)
        elif action_type == 'check':
            return self._handle_check(ctx, player_id, action)
        elif action_type == 'all_in':
            return self._handle_all_in(ctx, player_id, action)
        else:
            return GameEvent(
                event_type="INVALID_ACTION",
                data={"reason": f"未知的行动类型: {action_type}"},
                source_phase=self.phase
            )
    
    def _cleanup_previous_hand(self, ctx: GameContext) -> None:
        """清理之前手牌的状态"""
        # 清理公共牌
        ctx.community_cards.clear()
        
        # 清理玩家手牌
        for player_data in ctx.players.values():
            player_data.pop('hole_cards', None)
    
    def _set_first_active_player(self, ctx: GameContext) -> None:
        """设置第一个行动的玩家"""
        player_ids = list(ctx.players.keys())
        if len(player_ids) < 2:
            return
        
        # 在翻牌前，第一个行动的玩家是大盲注后的第一个玩家
        # 简化：如果有3个或更多玩家，第三个玩家先行动；否则第一个玩家（小盲）先行动
        if len(player_ids) >= 3:
            first_player = player_ids[2]  # 大盲注后的第一个玩家
        else:
            first_player = player_ids[0]  # 小盲注玩家
        
        ctx.active_player_id = first_player
    
    def _deal_hole_cards(self, ctx: GameContext) -> None:
        """发手牌"""
        # 简化的发牌逻辑：给每个活跃玩家发2张牌
        from v3.core.deck import Card
        from v3.core.deck.types import Suit, Rank
        
        # 创建一些测试用的牌
        test_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK)
        ]
        
        card_index = 0
        for player_id in ctx.players:
            # 只给真正活跃且有筹码的玩家发牌
            player_data = ctx.players[player_id]
            is_active = (
                player_data.get('active', False) and 
                player_data.get('chips', 0) > 0 and
                player_data.get('status', 'out') not in ['out', 'folded']
            )
            
            if is_active:
                # 给每个玩家发2张牌
                ctx.players[player_id]['hole_cards'] = [
                    test_cards[card_index % len(test_cards)],
                    test_cards[(card_index + 1) % len(test_cards)]
                ]
                
                # 添加发牌日志
                import logging
                logger = logging.getLogger(__name__)
                hole_cards = ctx.players[player_id]['hole_cards']
                logger.debug(f"[发牌] {player_id} 收到底牌: {hole_cards[0]} {hole_cards[1]}")
                
                card_index += 2
    
    def _handle_fold(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理弃牌行动"""
        if player_id in ctx.players:
            player = ctx.players[player_id]
            
            # 弃牌玩家的当前下注需要计入奖池（如果还没有计入的话）
            current_bet = player.get('current_bet', 0)
            if current_bet > 0:
                # 确保下注已经计入奖池（通常应该已经计入了）
                # 这里不需要重复计入，只需要清空当前下注
                player['current_bet'] = 0
            
            # 设置玩家状态（先设置，再检查是否需要自动结束）
            player['status'] = 'folded'
            player['active'] = False
            
            # 检查是否应该自动结束手牌（德州扑克规则）
            if self._should_auto_finish_hand(ctx):
                # 只有一个或零个活跃玩家，手牌应该结束
                ctx.active_player_id = None  # 清除活跃玩家
                return GameEvent(
                    event_type="HAND_AUTO_FINISH",
                    data={"reason": "只剩一个或零个活跃玩家", "last_folder": player_id},
                    source_phase=self.phase
                )
            else:
                # 还有多个活跃玩家，找到下一个可行动玩家
                next_player_id = self._find_next_actionable_player(ctx, player_id)
                ctx.active_player_id = next_player_id
        
        return GameEvent(
            event_type="PLAYER_FOLDED",
            data={"player_id": player_id},
            source_phase=self.phase
        )
    
    def _handle_call(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理跟注行动"""
        if player_id in ctx.players:
            player = ctx.players[player_id]
            current_bet = player.get('current_bet', 0)
            need_to_call = ctx.current_bet - current_bet
            
            if need_to_call > 0:
                if player['chips'] >= need_to_call:
                    player['chips'] -= need_to_call
                    player['current_bet'] = ctx.current_bet
                    player['total_bet_this_hand'] = player.get('total_bet_this_hand', 0) + need_to_call
                    ctx.pot_total += need_to_call
                else:
                    # 筹码不足，自动转为全下
                    all_in_amount = player['chips']
                    player['chips'] = 0
                    player['current_bet'] = current_bet + all_in_amount
                    player['total_bet_this_hand'] = player.get('total_bet_this_hand', 0) + all_in_amount
                    player['status'] = 'all_in'
                    player['is_all_in'] = True  # 修复：设置is_all_in属性
                    player['active'] = True  # 修复：all_in玩家保持活跃
                    ctx.pot_total += all_in_amount
        
        # 轮换到下一个玩家
        self._advance_to_next_player(ctx)
        
        return GameEvent(
            event_type="PLAYER_CALLED",
            data={"player_id": player_id, "amount": ctx.current_bet},
            source_phase=self.phase
        )
    
    def _handle_raise(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理加注行动"""
        raise_amount = action.get('amount', 0)
        if raise_amount <= ctx.current_bet:
            return GameEvent(
                event_type="INVALID_ACTION",
                data={"reason": "加注金额必须大于当前下注"},
                source_phase=self.phase
            )
        
        # 处理筹码和下注
        if player_id in ctx.players:
            player = ctx.players[player_id]
            current_bet = player.get('current_bet', 0)
            need_to_bet = raise_amount - current_bet
            
            if player['chips'] >= need_to_bet:
                player['chips'] -= need_to_bet
                player['current_bet'] = raise_amount
                player['total_bet_this_hand'] = player.get('total_bet_this_hand', 0) + need_to_bet
                ctx.pot_total += need_to_bet
                ctx.current_bet = raise_amount
            else:
                # 筹码不足，自动转为全下
                all_in_amount = player['chips']
                player['chips'] = 0
                player['current_bet'] = current_bet + all_in_amount
                player['total_bet_this_hand'] = player.get('total_bet_this_hand', 0) + all_in_amount
                player['status'] = 'all_in'
                player['is_all_in'] = True  # 修复：设置is_all_in属性
                player['active'] = True  # 修复：all_in玩家保持活跃
                ctx.pot_total += all_in_amount
                
                # 如果全下金额大于当前下注，更新当前下注
                if player['current_bet'] > ctx.current_bet:
                    ctx.current_bet = player['current_bet']
        
        # 轮换到下一个玩家
        self._advance_to_next_player(ctx)
        
        return GameEvent(
            event_type="PLAYER_RAISED",
            data={"player_id": player_id, "amount": raise_amount},
            source_phase=self.phase
        )
    
    def _handle_check(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理过牌行动"""
        if ctx.current_bet > 0:
            # 有下注时不能过牌，但可以检查是否已经跟注
            if player_id in ctx.players:
                player = ctx.players[player_id]
                current_bet = player.get('current_bet', 0)
                if current_bet < ctx.current_bet:
                    return GameEvent(
                        event_type="INVALID_ACTION",
                        data={"reason": "有下注时不能过牌，请选择跟注、加注或弃牌"},
                        source_phase=self.phase
                    )
        
        # 轮换到下一个玩家
        self._advance_to_next_player(ctx)
        
        return GameEvent(
            event_type="PLAYER_CHECKED",
            data={"player_id": player_id},
            source_phase=self.phase
        )
    
    def _handle_all_in(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理全下行动"""
        if player_id in ctx.players:
            player = ctx.players[player_id]
            all_in_amount = player['chips']
            current_bet = player.get('current_bet', 0)
            
            if all_in_amount > 0:
                # 全下所有筹码
                player['chips'] = 0
                player['current_bet'] = current_bet + all_in_amount
                player['total_bet_this_hand'] = player.get('total_bet_this_hand', 0) + all_in_amount
                player['status'] = 'all_in'
                player['is_all_in'] = True  # 修复：正确设置is_all_in属性
                player['active'] = True  # 修复：all_in玩家应该保持活跃状态，直到手牌结束
                ctx.pot_total += all_in_amount
                
                # 如果全下金额大于当前下注，更新当前下注
                if player['current_bet'] > ctx.current_bet:
                    ctx.current_bet = player['current_bet']
        
        # 轮换到下一个玩家
        self._advance_to_next_player(ctx)
        
        return GameEvent(
            event_type="PLAYER_ALL_IN",
            data={"player_id": player_id, "amount": all_in_amount},
            source_phase=self.phase
        )
    
    def _advance_to_next_player(self, ctx: GameContext) -> None:
        """轮换到下一个可以行动的玩家
        
        核心修复：
        1. 使用原子性操作，避免中间状态
        2. 在设置前完整验证，避免设置后再清空
        3. 增强状态一致性保证
        """
        # 获取所有玩家ID（保持稳定顺序）
        player_ids = list(ctx.players.keys())
        if len(player_ids) < 2:
            # 玩家数不足，直接清空
            ctx.active_player_id = None
            return

        # 确定搜索起点
        start_index = 0
        if ctx.active_player_id and ctx.active_player_id in player_ids:
            start_index = player_ids.index(ctx.active_player_id)

        # 原子性搜索：先找到下一个可行动玩家，再设置
        next_active_player = None
        
        # 从当前玩家的下一个位置开始搜索
        for i in range(1, len(player_ids) + 1):
            candidate_index = (start_index + i) % len(player_ids)
            candidate_id = player_ids[candidate_index]
            
            # 完整验证候选玩家的可行动性
            if self._is_player_actionable(ctx, candidate_id):
                next_active_player = candidate_id
                break

        # 原子性设置：一次性更新，无中间状态
        ctx.active_player_id = next_active_player
        
        # 最终一致性验证（用于调试和监控）
        if ctx.active_player_id is not None:
            if not self._is_player_actionable(ctx, ctx.active_player_id):
                # 这应该永远不会发生，如果发生，说明逻辑有bug
                ctx.active_player_id = None
    
    def _is_player_actionable(self, ctx: GameContext, player_id: str) -> bool:
        """检查玩家是否可以行动（原子性检查方法）
        
        可行动条件：
        1. 玩家存在于游戏中
        2. active=True（仍在手牌中）
        3. chips > 0（有筹码可下注）
        4. status不是folded/out（未弃牌或出局）
        
        注意：all_in玩家虽然active=True，但chips=0，所以不可行动
        """
        if player_id not in ctx.players:
            return False
            
        player_data = ctx.players[player_id]
        
        return (
            player_data.get('active', False) and 
            player_data.get('chips', 0) > 0 and 
            player_data.get('status', 'active') not in ['folded', 'out']
        )
    
    def _find_first_actionable_player(self, ctx: GameContext) -> Optional[str]:
        """找到第一个可以行动的玩家"""
        for player_id in ctx.players.keys():
            if self._is_player_actionable(ctx, player_id):
                return player_id
        return None
    
    def _find_next_actionable_player(self, ctx: GameContext, current_player_id: str) -> Optional[str]:
        """找到指定玩家之后的下一个可以行动的玩家（用于原子性操作）"""
        player_ids = list(ctx.players.keys())
        if len(player_ids) < 2:
            return None

        try:
            current_index = player_ids.index(current_player_id)
        except ValueError:
            # 当前玩家不在列表中，返回第一个可行动玩家
            return self._find_first_actionable_player(ctx)

        # 寻找下一个可以行动的玩家（排除当前玩家）
        for i in range(1, len(player_ids) + 1):
            next_index = (current_index + i) % len(player_ids)
            next_player_id = player_ids[next_index]
            
            # 跳过当前玩家（即将fold的玩家）
            if next_player_id == current_player_id:
                continue
                
            # 使用统一的可行动性检查方法
            if self._is_player_actionable(ctx, next_player_id):
                return next_player_id

        # 如果没有找到可行动玩家，返回None
        return None
    
    def _check_betting_round_complete(self, ctx: GameContext) -> bool:
        """检查下注轮是否完成"""
        # 获取真正可以行动的玩家
        actionable_players = [
            pid for pid in ctx.players.keys()
            if self._is_player_actionable(ctx, pid)
        ]
        
        # 如果只有一个或没有可行动玩家，下注轮结束
        if len(actionable_players) <= 1:
            return True
        
        # 检查所有可行动玩家是否都已下注相同金额
        current_bets = [
            ctx.players[pid].get('current_bet', 0)
            for pid in actionable_players
        ]
        
        # 所有活跃玩家的下注金额应该相等
        return len(set(current_bets)) <= 1
    
    def _should_auto_finish_hand(self, ctx: GameContext) -> bool:
        """检查是否应该自动结束手牌（德州扑克规则：只有一个活跃玩家时自动获胜）"""
        # 获取真正可以行动的玩家
        actionable_players = [
            pid for pid in ctx.players.keys()
            if self._is_player_actionable(ctx, pid)
        ]
        
        # 德州扑克规则：如果只有一个或零个可行动玩家，手牌应该结束
        return len(actionable_players) <= 1


class FlopHandler(BasePhaseHandler):
    """翻牌阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.FLOP)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入翻牌阶段"""
        super().on_enter(ctx)
        # 发翻牌
        self._deal_flop_cards(ctx)
        # 验证奖池一致性
        self._validate_pot_consistency(ctx, "FLOP")
        # 重置下注轮
        self._reset_betting_round(ctx)
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理翻牌阶段的玩家行动"""
        # 复用PreFlopHandler的行动处理逻辑
        pre_flop_handler = PreFlopHandler()
        event = pre_flop_handler.handle_player_action(ctx, player_id, action)
        # 更新事件的源阶段
        return GameEvent(
            event_type=event.event_type,
            data=event.data,
            source_phase=self.phase
        )
    
    def _deal_flop_cards(self, ctx: GameContext) -> None:
        """发翻牌（三张公共牌）"""
        from v3.core.deck import Card
        from v3.core.deck.types import Suit, Rank
        
        # 简化的发牌逻辑
        if len(ctx.community_cards) == 0:
            flop_cards = [
                Card(Suit.HEARTS, Rank.TEN),
                Card(Suit.DIAMONDS, Rank.NINE),
                Card(Suit.CLUBS, Rank.EIGHT)
            ]
            ctx.community_cards.extend(flop_cards)
    
    def _validate_pot_consistency(self, ctx: GameContext, phase_name: str) -> None:
        """验证奖池与玩家下注的一致性"""
        from ..invariant.chip_conservation_validator import ChipConservationValidator
        ChipConservationValidator.validate_pot_consistency(ctx, f"{phase_name}阶段进入")
    
    def _reset_betting_round(self, ctx: GameContext) -> None:
        """重置下注轮"""
        # 在重置前，确保所有current_bet都已经被计入奖池
        # 这是筹码守恒的关键步骤
        for player_id, player_data in ctx.players.items():
            current_bet = player_data.get('current_bet', 0)
            if current_bet > 0:
                # 确保current_bet已经被计入total_bet_this_hand
                total_bet = player_data.get('total_bet_this_hand', 0)
                if total_bet < current_bet:
                    # 如果total_bet_this_hand小于current_bet，说明有筹码没有被正确记录
                    # 这种情况不应该发生，但为了安全起见，我们修正它
                    player_data['total_bet_this_hand'] = max(total_bet, current_bet)
        
        # 重置全局下注
        ctx.current_bet = 0
        
        # 重置所有玩家的当前下注（但保留total_bet_this_hand）
        for player_id in ctx.players:
            ctx.players[player_id]['current_bet'] = 0


class TurnHandler(BasePhaseHandler):
    """转牌阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.TURN)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入转牌阶段"""
        super().on_enter(ctx)
        # 发第四张公共牌
        self._deal_turn_card(ctx)
        # 验证奖池一致性
        self._validate_pot_consistency(ctx, "TURN")
        # 重置下注轮（包括玩家current_bet清零）
        self._reset_betting_round(ctx)
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理转牌阶段的玩家行动"""
        pre_flop_handler = PreFlopHandler()
        event = pre_flop_handler.handle_player_action(ctx, player_id, action)
        return GameEvent(
            event_type=event.event_type,
            data=event.data,
            source_phase=self.phase
        )
    
    def _deal_turn_card(self, ctx: GameContext) -> None:
        """发转牌（第四张公共牌）"""
        from v3.core.deck import Card
        from v3.core.deck.types import Suit, Rank
        
        if len(ctx.community_cards) == 3:
            turn_card = Card(Suit.SPADES, Rank.SEVEN)
            ctx.community_cards.append(turn_card)
    
    def _validate_pot_consistency(self, ctx: GameContext, phase_name: str) -> None:
        """验证奖池与玩家下注的一致性"""
        from ..invariant.chip_conservation_validator import ChipConservationValidator
        ChipConservationValidator.validate_pot_consistency(ctx, f"{phase_name}阶段进入")
    
    def _reset_betting_round(self, ctx: GameContext) -> None:
        """重置下注轮"""
        # 在重置前，确保所有current_bet都已经被计入奖池
        # 这是筹码守恒的关键步骤
        for player_id, player_data in ctx.players.items():
            current_bet = player_data.get('current_bet', 0)
            if current_bet > 0:
                # 确保current_bet已经被计入total_bet_this_hand
                total_bet = player_data.get('total_bet_this_hand', 0)
                if total_bet < current_bet:
                    # 如果total_bet_this_hand小于current_bet，说明有筹码没有被正确记录
                    # 这种情况不应该发生，但为了安全起见，我们修正它
                    player_data['total_bet_this_hand'] = max(total_bet, current_bet)
        
        # 重置全局下注
        ctx.current_bet = 0
        
        # 重置所有玩家的当前下注（但保留total_bet_this_hand）
        for player_id in ctx.players:
            ctx.players[player_id]['current_bet'] = 0


class RiverHandler(BasePhaseHandler):
    """河牌阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.RIVER)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入河牌阶段"""
        super().on_enter(ctx)
        # 发第五张公共牌
        self._deal_river_card(ctx)
        # 验证奖池一致性
        self._validate_pot_consistency(ctx, "RIVER")
        # 重置下注轮（包括玩家current_bet清零）
        self._reset_betting_round(ctx)
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理河牌阶段的玩家行动"""
        pre_flop_handler = PreFlopHandler()
        event = pre_flop_handler.handle_player_action(ctx, player_id, action)
        return GameEvent(
            event_type=event.event_type,
            data=event.data,
            source_phase=self.phase
        )
    
    def _deal_river_card(self, ctx: GameContext) -> None:
        """发河牌（第五张公共牌）"""
        from v3.core.deck import Card
        from v3.core.deck.types import Suit, Rank
        
        if len(ctx.community_cards) == 4:
            river_card = Card(Suit.HEARTS, Rank.SIX)
            ctx.community_cards.append(river_card)
    
    def _validate_pot_consistency(self, ctx: GameContext, phase_name: str) -> None:
        """验证奖池与玩家下注的一致性"""
        from ..invariant.chip_conservation_validator import ChipConservationValidator
        ChipConservationValidator.validate_pot_consistency(ctx, f"{phase_name}阶段进入")
    
    def _reset_betting_round(self, ctx: GameContext) -> None:
        """重置下注轮"""
        # 在重置前，确保所有current_bet都已经被计入奖池
        # 这是筹码守恒的关键步骤
        for player_id, player_data in ctx.players.items():
            current_bet = player_data.get('current_bet', 0)
            if current_bet > 0:
                # 确保current_bet已经被计入total_bet_this_hand
                total_bet = player_data.get('total_bet_this_hand', 0)
                if total_bet < current_bet:
                    # 如果total_bet_this_hand小于current_bet，说明有筹码没有被正确记录
                    # 这种情况不应该发生，但为了安全起见，我们修正它
                    player_data['total_bet_this_hand'] = max(total_bet, current_bet)
        
        # 重置全局下注
        ctx.current_bet = 0
        
        # 重置所有玩家的当前下注（但保留total_bet_this_hand）
        for player_id in ctx.players:
            ctx.players[player_id]['current_bet'] = 0


class ShowdownHandler(BasePhaseHandler):
    """摊牌阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.SHOWDOWN)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入摊牌阶段"""
        super().on_enter(ctx)
        # 清除活跃玩家，SHOWDOWN阶段不需要玩家行动
        ctx.active_player_id = None
        # 比较手牌，确定胜者
        self._determine_winners(ctx)
        # 摊牌完成，标记需要转换到结束阶段
        ctx.showdown_complete = True
    
    def can_transition_to(self, target_phase: GamePhase, ctx: GameContext) -> bool:
        """检查是否可以转换到目标阶段"""
        if target_phase == GamePhase.FINISHED:
            return getattr(ctx, 'showdown_complete', False)
        return super().can_transition_to(target_phase, ctx)
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """摊牌阶段不处理玩家行动"""
        return GameEvent(
            event_type="INVALID_ACTION",
            data={"reason": "摊牌阶段不能执行玩家行动"},
            source_phase=self.phase
        )
    
    def _determine_winners(self, ctx: GameContext) -> None:
        """确定胜者并分配奖池"""
        # 在分配前验证筹码守恒
        total_player_chips = sum(player.get('chips', 0) for player in ctx.players.values())
        total_bets = sum(player.get('total_bet_this_hand', 0) for player in ctx.players.values())
        expected_pot = total_bets
        
        # 严格验证奖池与总下注的一致性
        if ctx.pot_total != expected_pot:
            # 收集详细的调试信息
            player_details = {
                player_id: {
                    'chips': player.get('chips', 0),
                    'total_bet_this_hand': player.get('total_bet_this_hand', 0),
                    'status': player.get('status', 'unknown')
                }
                for player_id, player in ctx.players.items()
            }
            
            error_msg = (
                f"摊牌阶段筹码守恒违规：奖池({ctx.pot_total}) != 玩家总下注({expected_pot})\n"
                f"差额: {ctx.pot_total - expected_pot}\n"
                f"玩家详情: {player_details}\n"
                f"当前阶段: {ctx.current_phase}"
            )
            
            # 抛出异常，强制修复根本问题
            raise ValueError(error_msg)
        
        # 简化的胜者确定逻辑
        active_players = [pid for pid, pdata in ctx.players.items() 
                         if pdata.get('status') != 'folded']
        
        if active_players and ctx.pot_total > 0:
            # 简单地选择第一个活跃玩家作为胜者
            winner = active_players[0]
            # 将奖池直接加到胜者的筹码中
            ctx.players[winner]['chips'] += ctx.pot_total
            # 记录奖金用于日志
            ctx.players[winner]['winnings'] = ctx.pot_total
            # 清空奖池
            ctx.pot_total = 0
        elif not active_players and ctx.pot_total > 0:
            # 如果没有活跃玩家但有奖池，这是异常情况
            # 将奖池平分给所有非弃牌玩家
            non_folded_players = [pid for pid, pdata in ctx.players.items() 
                                if pdata.get('status') != 'folded']
            if non_folded_players:
                per_player = ctx.pot_total // len(non_folded_players)
                remainder = ctx.pot_total % len(non_folded_players)
                
                for i, player_id in enumerate(non_folded_players):
                    amount = per_player + (1 if i < remainder else 0)
                    ctx.players[player_id]['chips'] += amount
                    ctx.players[player_id]['winnings'] = amount
                
                ctx.pot_total = 0
        
        # *** 关键修复：立即清理下注记录，确保状态一致性 ***
        # 奖池已经分配完毕，现在清理所有玩家的下注记录
        # 这样不变量检查就不会看到不一致的中间状态
        for player_data in ctx.players.values():
            player_data['current_bet'] = 0
            player_data['total_bet_this_hand'] = 0
        
        # 重置当前下注
        ctx.current_bet = 0


class FinishedHandler(BasePhaseHandler):
    """结束阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.FINISHED)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入结束阶段"""
        super().on_enter(ctx)
        # 处理自动结束的手牌（如果适用）
        self._handle_auto_finish(ctx)
        # 清理本手牌的状态
        self._cleanup_hand(ctx)
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """结束阶段处理新手牌开始"""
        action_type = action.get('type')
        
        if action_type == 'start_new_hand':
            return GameEvent(
                event_type="HAND_START",
                data={"new_hand": True},
                source_phase=self.phase
            )
        
        return GameEvent(
            event_type="INVALID_ACTION",
            data={"reason": f"结束阶段不支持行动: {action_type}"},
            source_phase=self.phase
        )
    
    def _cleanup_hand(self, ctx: GameContext) -> None:
        """清理本手牌的状态"""
        # 重置玩家状态（但保留手牌和筹码）
        for player_data in ctx.players.values():
            # 清除状态标记
            player_data.pop('status', None)
            player_data.pop('winnings', None)
            # 重置本手牌的下注
            player_data['current_bet'] = 0
            player_data['total_bet_this_hand'] = 0
        
        # 重置下注状态
        ctx.current_bet = 0
        # 奖池应该已经在SHOWDOWN阶段被分配，这里确保为0
        ctx.pot_total = 0
        
        # 清除摊牌完成标记
        if hasattr(ctx, 'showdown_complete'):
            delattr(ctx, 'showdown_complete')
    
    def _handle_auto_finish(self, ctx: GameContext) -> None:
        """处理自动结束的手牌（德州扑克规则：只有一个活跃玩家时自动获胜）"""
        # 获取非折牌玩家（包括全下玩家）
        non_folded_players = [
            pid for pid, data in ctx.players.items()
            if data.get('status') != 'folded'
        ]
        
        # 获取还有筹码的玩家（可以继续下一手牌的玩家）
        players_with_chips = [
            pid for pid, data in ctx.players.items()
            if data.get('chips', 0) > 0
        ]
        
        if ctx.pot_total > 0:
            if len(non_folded_players) == 1:
                # 只有一个非折牌玩家，自动获胜
                winner_id = non_folded_players[0]
                winner_data = ctx.players[winner_id]
                
                # 将奖池加到获胜者的筹码中
                winner_data['chips'] += ctx.pot_total
                winner_data['winnings'] = ctx.pot_total
                
                # 清空奖池
                ctx.pot_total = 0
                
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[游戏结果] 自动获胜: {winner_id} 获得 {winner_data['winnings']} 筹码（其他玩家弃牌）")
            elif len(non_folded_players) > 1:
                # 多个非折牌玩家，需要进行摊牌比较
                # 这里简化处理：选择第一个非折牌玩家作为获胜者
                winner_id = non_folded_players[0]
                winner_data = ctx.players[winner_id]
                
                # 将奖池加到获胜者的筹码中
                winner_data['chips'] += ctx.pot_total
                winner_data['winnings'] = ctx.pot_total
                
                # 清空奖池
                ctx.pot_total = 0
                
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[游戏结果] 摊牌获胜: {winner_id} 获得 {winner_data['winnings']} 筹码（{len(non_folded_players)}人摊牌）")
            elif len(non_folded_players) == 0 and players_with_chips:
                # 所有玩家都弃牌，异常情况
                # 将奖池分给第一个有筹码的玩家
                winner_id = players_with_chips[0]
                ctx.players[winner_id]['chips'] += ctx.pot_total
                ctx.players[winner_id]['winnings'] = ctx.pot_total
                ctx.pot_total = 0
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"[游戏异常] 异常获胜: {winner_id} 获得 {ctx.players[winner_id]['winnings']} 筹码（所有玩家弃牌）")
            else:
                # 没有玩家有筹码，奖池消失（极端异常情况）
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"[游戏错误] 奖池 {ctx.pot_total} 筹码无法分配（没有合格的获胜者）")
                ctx.pot_total = 0 