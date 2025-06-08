"""
翻牌前阶段处理器
"""
from .types import GamePhase, GameContext
from .base_betting_handler import BaseBettingHandler
from ..deck.card import Card, Suit, Rank

__all__ = ['PreFlopHandler']

class PreFlopHandler(BaseBettingHandler):
    """翻牌前阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.PRE_FLOP)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入翻牌前阶段"""
        # 注意：不调用 super().on_enter()，因为PRE_FLOP不需要在进入时重置下注轮
        # 盲注已经作为一种下注形式存在
        
        # 仅在需要时发牌和清理（例如从INIT转换而来）
        # 如果是从其他下注轮转换而来，则不执行
        if not ctx.community_cards:
            self._deal_hole_cards(ctx)

        # 修复：从context中获取正确的bb_pos，并使用它来找到UTG玩家
        # 职责：PreFlopHandler负责确定第一个行动者
        if not ctx.active_player_id:
            bb_pos = ctx.big_blind_position
            if bb_pos is not None:
                # 修复：必须找到该位置对应的玩家ID，并将其传递给辅助方法
                
                # 创建一个从位置到ID的映射
                players_by_pos = {p_data['position']: p_id for p_id, p_data in ctx.players.items()}
                bb_player_id = players_by_pos.get(bb_pos)

                if bb_player_id:
                    ctx.active_player_id = self._find_next_actionable_player(ctx, current_player_id=bb_player_id)

    
    def _cleanup_previous_hand(self, ctx: GameContext) -> None:
        """清理之前手牌的状态"""
        ctx.community_cards.clear()
        
    def _deal_hole_cards(self, ctx: GameContext) -> None:
        """为玩家发底牌"""
        # 这里的实现应该调用Deck服务
        # 仅为示例
        for player_id in ctx.players:
            player = ctx.players[player_id]
            if player['status'] == 'active':
                # 假设的Deck服务
                # card1 = ctx.deck.deal()
                # card2 = ctx.deck.deal()
                # player['hole_cards'] = [card1, card2]
                pass
        import logging
        logger = logging.getLogger(__name__)
        logger.info("[游戏流程] 已为所有玩家发底牌") 