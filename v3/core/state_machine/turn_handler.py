"""
转牌圈阶段处理器
"""
import logging
from .types import GamePhase, GameContext
from .base_betting_handler import BaseBettingHandler
from ..deck.card import Card
from ..deck.types import Suit, Rank

__all__ = ['TurnHandler']

class TurnHandler(BaseBettingHandler):
    """转牌圈阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.TURN)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入转牌圈阶段"""
        super().on_enter(ctx)
        self._deal_turn_card(ctx)
        if ctx.dealer_player:
             player_ids = list(ctx.players.keys())
             start_pos = (player_ids.index(ctx.dealer_player) + 1) % len(player_ids)
             ctx.active_player_id = self._find_next_actionable_player(ctx, player_ids[start_pos-1])

    def _deal_turn_card(self, ctx: GameContext) -> None:
        """发出一张转牌"""
        # 伪代码
        # ctx.community_cards.append(ctx.deck.deal())
        ctx.community_cards.append(Card(Suit.SPADES, Rank.KING))
        logger = logging.getLogger(__name__)
        logger.info(f"[游戏流程] 发出转牌: {ctx.community_cards[-1]}") 