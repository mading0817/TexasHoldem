"""
河牌阶段实现
发1张河牌并复用下注轮逻辑
"""

from typing import Optional, TYPE_CHECKING
from .base_phase import BasePhase
from ..core.enums import GamePhase

if TYPE_CHECKING:
    from ..action_validator import ValidatedAction


class RiverPhase(BasePhase):
    """
    河牌阶段
    负责发1张河牌和处理河牌下注轮
    """
    
    def enter(self):
        """
        进入河牌阶段的初始化操作
        1. 发1张河牌
        2. 开始新的下注轮
        """
        # 确保游戏状态正确
        if self.state.phase != GamePhase.RIVER:
            self.state.phase = GamePhase.RIVER
        
        # 发1张河牌
        self._deal_river()
        
        # 开始新的下注轮
        self.state.start_new_betting_round()
        
        # 记录事件
        river_card = self.state.community_cards[-1].to_display_str()
        self.state.add_event(f"河牌: {river_card}，底池: {self.state.pot}")
    
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
        退出河牌阶段
        收集下注到底池，推进到摊牌阶段
        
        Returns:
            下一个阶段的实例（ShowdownPhase）
        """
        # 收集所有下注到底池
        self.state.collect_bets_to_pot()
        
        # 推进游戏阶段
        self.state.advance_phase()
        
        # 记录事件
        self.state.add_event(f"河牌结束，底池: {self.state.pot}")
        
        # 进入摊牌阶段
        from .showdown import ShowdownPhase
        return ShowdownPhase(self.state)
    
    def _deal_river(self):
        """发1张河牌"""
        if not self.state.deck:
            raise ValueError("牌组未初始化")
        
        # 烧掉一张牌（德州扑克规则）
        self.state.deck.deal_card()
        
        # 发1张河牌
        card = self.state.deck.deal_card()
        self.state.community_cards.append(card) 