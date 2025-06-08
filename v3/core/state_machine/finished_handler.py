"""
手牌结束阶段处理器
"""
import logging
from typing import Dict, Any, List
from .types import GamePhase, GameEvent, GameContext
from .base_phase_handler import BasePhaseHandler
from ..pot.pot_manager import PotManager
from ..chips.chip_ledger import ChipLedger

__all__ = ['FinishedHandler']

class FinishedHandler(BasePhaseHandler):
    """手牌结束阶段处理器，负责清理和准备下一手牌"""
    
    def __init__(self):
        super().__init__(GamePhase.FINISHED)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入手牌结束阶段"""
        super().on_enter(ctx)
        logger = logging.getLogger(__name__)

        # 如果是因为只剩一人而自动结束，需要在此分配底池
        if self._is_auto_finish_scenario(ctx):
             self._handle_auto_finish(ctx)

        logger.info("-" * 20 + " 手牌结束 " + "-" * 20)
        # 清理工作
        self._cleanup_hand(ctx)
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """
        此阶段可能处理 'continue' 或 'exit' 类型的"行动"，
        以决定是开始新手牌还是结束游戏。
        目前简化为自动开始新手牌。
        """
        # 检查是否所有玩家都已出局
        active_players = [p for p in ctx.players.values() if p.get('status') != 'out']
        if len(active_players) < 2:
            return GameEvent("GAME_OVER", {"reason": "玩家不足，游戏结束"}, self.phase)
            
        # 自动转换到 PRE_FLOP 开始新手牌
        return GameEvent("START_NEW_HAND", {}, self.phase)

    def _cleanup_hand(self, ctx: GameContext) -> None:
        """清理手牌状态，为下一手做准备"""
        logger = logging.getLogger(__name__)

        # 移动大小盲注和庄家位置
        player_ids = list(ctx.players.keys())
        if ctx.dealer_player and ctx.dealer_player in player_ids:
            dealer_idx = player_ids.index(ctx.dealer_player)
            ctx.dealer_player = player_ids[(dealer_idx + 1) % len(player_ids)]
            # ... 完整的大小盲注逻辑需要更复杂的位置计算 ...
        else:
            # 随机或默认设置一个
            ctx.dealer_player = player_ids[0]
        
        # 重置玩家状态
        for player_id, player_data in ctx.players.items():
            if player_data['chips'] <= 0 and player_data['status'] != 'out':
                player_data['status'] = 'out'
                logger.info(f"玩家 {player_id} 因筹码耗尽而出局。")
            elif player_data['status'] != 'out':
                 player_data['status'] = 'active'
                 player_data['hole_cards'] = []
                 player_data['current_bet'] = 0
                 player_data['total_bet_this_hand'] = 0
                 player_data['has_acted_this_round'] = False
        
        # 重置牌局状态
        ctx.community_cards.clear()
        ctx.current_bet = 0
        ctx.active_player_id = None
        ctx.winners_this_hand = []
        ctx.current_hand_bets.clear() # 清理本手牌的下注记录
        
        logger.info("已完成手牌清理，准备下一手。")

    def _handle_auto_finish(self, ctx: GameContext) -> None:
        """处理因所有其他玩家弃牌导致的自动结束情况"""
        logger = logging.getLogger(__name__)
        
        active_players = [p_id for p_id, p_data in ctx.players.items() if p_data.get('status') not in ['folded', 'out']]
        
        if len(active_players) == 1:
            winner_id = active_players[0]
            logger.info(f"所有其他玩家弃牌，玩家 {winner_id} 赢得底池。")

            total_pot = sum(ctx.current_hand_bets.values())

            # 构建结算交易
            transactions = {p: -b for p, b in ctx.current_hand_bets.items()}
            transactions[winner_id] = transactions.get(winner_id, 0) + total_pot

            logger.info(f"准备执行的筹码结算交易: {transactions}")
            ctx.chip_ledger.settle_hand(transactions)

            ctx.pot_total = 0
            
            ctx.winners_this_hand = [{
                'player_id': winner_id,
                'amount': total_pot,
                'hand_rank': 'N/A (uncontested)'
            }]
            logger.info(f"玩家 {winner_id} 赢得 {total_pot}。结算完成。")
        elif len(active_players) == 0:
            logger.warning("手牌结束时没有活跃玩家，这是一个异常情况。将清算所有赌注。")
            ctx.chip_ledger.settle_hand({}) # 传入空交易以清算所有冻结筹码
            ctx.pot_total = 0
        # 如果有多个活跃玩家，则不应由此处理器处理，而是由ShowdownHandler处理

    def _is_auto_finish_scenario(self, ctx: GameContext) -> bool:
        """检查是否是只有一个玩家在手的自动结束场景"""
        players_in_hand = [p for p_id, p in ctx.players.items() if p.get('status') not in ['folded', 'out']]
        return len(players_in_hand) <= 1 