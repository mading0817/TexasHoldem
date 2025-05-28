"""
转牌阶段实现
发1张转牌并复用下注轮逻辑
"""

from typing import Optional, TYPE_CHECKING
from .base_phase import BasePhase
from ..core.enums import GamePhase

if TYPE_CHECKING:
    from ..action_validator import ValidatedAction


class TurnPhase(BasePhase):
    """
    转牌阶段
    负责发1张转牌和处理转牌下注轮
    """
    
    def enter(self):
        """
        进入转牌阶段的初始化操作
        1. 发1张转牌
        2. 开始新的下注轮
        """
        # 确保游戏状态正确
        if self.state.phase != GamePhase.TURN:
            self.state.phase = GamePhase.TURN
        
        # 发1张转牌
        self._deal_turn()
        
        # 开始新的下注轮
        self.state.start_new_betting_round()
        
        # 记录事件
        turn_card = self.state.community_cards[-1].to_display_str()
        self.state.add_event(f"转牌: {turn_card}，底池: {self.state.pot}")
    
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
        退出转牌阶段
        收集下注到底池，推进到河牌阶段
        
        Returns:
            下一个阶段的实例（RiverPhase）
        """
        from .river import RiverPhase
        return self.standard_exit_to_next_phase(RiverPhase, "转牌")
    
    def _deal_turn(self):
        """发1张转牌"""
        if not self.state.deck:
            raise ValueError("牌组未初始化")
        
        # 烧掉一张牌（德州扑克规则）
        self.state.deck.deal_card()
        
        # 发1张转牌
        card = self.state.deck.deal_card()
        self.state.community_cards.append(card)
    
    def _execute_action(self, player, action: 'ValidatedAction'):
        """
        执行玩家行动
        复用现有的行动执行逻辑
        """
        from ..core.enums import ActionType
        
        if action.actual_action_type == ActionType.FOLD:
            player.fold()
        
        elif action.actual_action_type == ActionType.CHECK:
            # 过牌不需要额外操作
            pass
        
        elif action.actual_action_type == ActionType.CALL:
            # 跟注
            call_amount = max(0, self.state.current_bet - player.current_bet)
            player.bet(call_amount)
        
        elif action.actual_action_type == ActionType.BET:
            # 下注
            player.bet(action.actual_amount)
            self.state.current_bet = player.current_bet
            self.state.last_raiser = player.seat_id
        
        elif action.actual_action_type == ActionType.RAISE:
            # 加注
            call_amount = max(0, self.state.current_bet - player.current_bet)
            total_needed = call_amount + (action.actual_amount - self.state.current_bet)
            player.bet(total_needed)
            self.state.current_bet = action.actual_amount
            self.state.last_raiser = player.seat_id
        
        elif action.actual_action_type == ActionType.ALL_IN:
            # 全押
            player.bet(player.chips)
            if player.current_bet > self.state.current_bet:
                self.state.current_bet = player.current_bet
                self.state.last_raiser = player.seat_id
        
        # 记录玩家的最后行动类型
        player.last_action_type = action.actual_action_type
        
        # 增加行动计数
        self.state.street_index += 1 
 