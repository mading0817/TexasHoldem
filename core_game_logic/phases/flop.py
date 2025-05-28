"""
翻牌阶段实现
发3张公共牌并复用现有下注轮逻辑
"""

from typing import Optional, TYPE_CHECKING
from .base_phase import BasePhase
from ..core.enums import GamePhase

if TYPE_CHECKING:
    from ..action_validator import ValidatedAction


class FlopPhase(BasePhase):
    """
    翻牌阶段
    负责发3张公共牌和处理翻牌下注轮
    """
    
    def enter(self):
        """
        进入翻牌阶段的初始化操作
        1. 发3张公共牌
        2. 开始新的下注轮
        """
        # 确保游戏状态正确
        if self.state.phase != GamePhase.FLOP:
            self.state.phase = GamePhase.FLOP
        
        # 发3张公共牌
        self._deal_flop()
        
        # 开始新的下注轮
        self.state.start_new_betting_round()
        
        # 记录事件
        flop_str = " ".join(card.to_display_str() for card in self.state.community_cards[-3:])
        self.state.add_event(f"翻牌: {flop_str}，底池: {self.state.pot}")
    
    def act(self, action: 'ValidatedAction') -> bool:
        """
        处理玩家行动
        使用BasePhase的通用方法
        
        Args:
            action: 经过验证的玩家行动
            
        Returns:
            True如果下注轮继续，False如果下注轮结束
        """
        return self.process_standard_action(action)
    
    def exit(self) -> Optional['BasePhase']:
        """
        退出翻牌阶段
        收集下注到底池，推进到转牌阶段
        
        Returns:
            下一个阶段的实例（TurnPhase）
        """
        from .turn import TurnPhase
        return self.standard_exit_to_next_phase(TurnPhase, "翻牌")
    
    def _deal_flop(self):
        """发3张翻牌"""
        if not self.state.deck:
            raise ValueError("牌组未初始化")
        
        # 烧掉一张牌（德州扑克规则）
        self.state.deck.deal_card()
        
        # 发3张翻牌
        for _ in range(3):
            card = self.state.deck.deal_card()
            self.state.community_cards.append(card) 