"""
翻牌阶段实现
处理发翻牌和下注轮
"""

from typing import Optional, TYPE_CHECKING, Callable, List, Any
from .base_phase import BasePhase
from ..core.enums import GamePhase, SeatStatus

if TYPE_CHECKING:
    from ..action_validator import ValidatedAction


class FlopPhase(BasePhase):
    """
    翻牌阶段
    负责发出翻牌（3张公共牌）和处理翻牌后下注轮
    """
    
    def enter(self):
        """
        进入翻牌阶段的初始化操作
        1. 设置游戏阶段为FLOP
        2. 发出3张翻牌
        3. 重置下注轮
        """
        # 设置游戏阶段
        self.state.phase = GamePhase.FLOP
        
        # 发翻牌（3张公共牌）
        self._deal_flop()
        
        # 重置下注轮，从庄家左边第一个活跃玩家开始
        self._start_post_flop_betting()
        
        # 记录事件
        flop_cards = ", ".join(str(card) for card in self.state.community_cards[-3:])
        self.state.add_event(f"翻牌: {flop_cards}")
        self.state.add_event(f"翻牌阶段开始，底池: {self.state.pot}")
    
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

    def process_betting_round(self, get_player_action_callback: Callable[[int], Any]) -> List[str]:
        """
        处理翻牌下注轮
        使用标准下注轮处理逻辑
        
        Args:
            get_player_action_callback: 获取玩家行动的回调函数
        
        Returns:
            产生的事件列表
        """
        return self._standard_process_betting_round(get_player_action_callback)
    
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

    def _start_post_flop_betting(self):
        """开始翻牌后下注轮"""
        # 翻牌后从庄家左边第一个活跃玩家开始
        self.state.start_new_betting_round()
        
        # 设置第一个行动的玩家（从庄家左边开始找活跃玩家）
        active_players = self.state.get_active_players()
        if not active_players:
            return
        
        all_seats = sorted([p.seat_id for p in self.state.players 
                           if p.status != SeatStatus.OUT])
        if not all_seats:
            return
            
        dealer_index = all_seats.index(self.state.dealer_position)
        
        # 从庄家左边开始找第一个可以行动的玩家
        for i in range(1, len(all_seats) + 1):
            check_index = (dealer_index + i) % len(all_seats)
            check_seat = all_seats[check_index]
            check_player = self.state.get_player_by_seat(check_seat)
            
            if check_player and check_player.can_act():
                self.state.current_player = check_seat
                break
        else:
            # 如果没有找到可行动的玩家，设置为第一个活跃玩家
            if active_players:
                self.state.current_player = active_players[0].seat_id 