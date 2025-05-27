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
        复用现有的行动处理逻辑
        
        Args:
            action: 经过验证的玩家行动
            
        Returns:
            True如果下注轮继续，False如果下注轮结束
        """
        player = self.state.get_player_by_seat(action.player_seat)
        if not player:
            raise ValueError(f"找不到座位{action.player_seat}的玩家")
        
        # 执行行动
        self._execute_action(player, action)
        
        # 记录事件
        self.state.add_event(f"{player.name} {action}")
        
        # 推进到下一个玩家
        if not self.state.advance_current_player():
            # 没有更多玩家可行动，下注轮结束
            return False
        
        # 检查下注轮是否完成
        if self.state.is_betting_round_complete():
            return False
        
        return True
    
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