"""
翻牌圈阶段处理器
"""
import logging
from .types import GamePhase, GameContext
from .base_betting_handler import BaseBettingHandler
from ..deck.card import Card
from ..deck.types import Suit, Rank

__all__ = ['FlopHandler']

class FlopHandler(BaseBettingHandler):
    """翻牌圈阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.FLOP)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入翻牌圈阶段"""
        super().on_enter(ctx)
        self._deal_flop_cards(ctx)
        # 找到第一个行动的玩家，通常是小盲注位或之后第一个还在游戏中的玩家
        # 这里的逻辑可能需要根据游戏规则细化
        if ctx.dealer_player:
             player_ids = list(ctx.players.keys())
             start_pos = (player_ids.index(ctx.dealer_player) + 1) % len(player_ids)
             ctx.active_player_id = self._find_next_actionable_player(ctx, player_ids[start_pos-1])

    def _deal_flop_cards(self, ctx: GameContext) -> None:
        """发出三张公共牌"""
        # 应从Deck服务获取
        # 伪代码
        # ctx.community_cards.extend([ctx.deck.deal() for _ in range(3)])
        ctx.community_cards.extend([
            Card(Suit.CLUBS, Rank.TEN),
            Card(Suit.DIAMONDS, Rank.JACK),
            Card(Suit.HEARTS, Rank.QUEEN)
        ])
        logger = logging.getLogger(__name__)
        logger.info(f"[游戏流程] 发出翻牌: {ctx.community_cards}") 