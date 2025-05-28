"""
翻牌前阶段实现
处理发底牌、设置盲注和下注轮处理，最大化复用GameState现有逻辑
"""

from typing import Optional, TYPE_CHECKING
from .base_phase import BasePhase
from ..core.enums import GamePhase, SeatStatus
from ..core.deck import Deck

if TYPE_CHECKING:
    from ..action_validator import ValidatedAction


class PreFlopPhase(BasePhase):
    """
    翻牌前阶段
    负责发底牌、设置盲注和处理翻牌前下注轮
    """
    
    def enter(self):
        """
        进入翻牌前阶段的初始化操作
        1. 创建并洗牌
        2. 发底牌给每个玩家
        3. 开始下注轮
        注意：盲注设置应该在游戏初始化时完成，而不是在此处
        """
        # 确保游戏状态正确
        if self.state.phase != GamePhase.PRE_FLOP:
            self.state.phase = GamePhase.PRE_FLOP
        
        # 创建新牌组并洗牌
        if self.state.deck is None:
            self.state.deck = Deck()
        self.state.deck.reset()
        self.state.deck.shuffle()
        
        # 发底牌给每个玩家（每人2张）
        self._deal_hole_cards()
        
        # 不再重复设置盲注 - 这应该在游戏初始化时完成
        # self.state.set_blinds()  # 删除这一行
        
        # 开始下注轮，从大盲注左边的玩家开始
        self._start_preflop_betting()
        
        # 记录事件
        self.state.add_event(f"翻牌前阶段开始，底池: {self.state.pot}")
    
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
        退出翻牌前阶段
        收集下注到底池，推进到翻牌阶段
        
        Returns:
            下一个阶段的实例（FlopPhase）
        """
        from .flop import FlopPhase
        return self.standard_exit_to_next_phase(FlopPhase, "翻牌前")
    
    def _deal_hole_cards(self):
        """发底牌给每个玩家"""
        active_players = [p for p in self.state.players if p.status != SeatStatus.OUT]
        
        # 按座位顺序发牌，从庄家左边开始
        all_seats = sorted([p.seat_id for p in active_players])
        dealer_index = all_seats.index(self.state.dealer_position)
        
        # 发两轮牌，每轮每人一张
        for round_num in range(2):
            for i in range(len(all_seats)):
                seat_index = (dealer_index + 1 + i) % len(all_seats)
                seat_id = all_seats[seat_index]
                player = self.state.get_player_by_seat(seat_id)
                
                if player and player.status != SeatStatus.OUT:
                    card = self.state.deck.deal_card()
                    player.hole_cards.append(card)
    
    def _start_preflop_betting(self):
        """开始翻牌前下注轮"""
        # 翻牌前特殊规则：从大盲注左边的玩家开始行动
        active_players = self.state.get_active_players()
        if not active_players:
            return
        
        all_seats = sorted([p.seat_id for p in self.state.players if p.status != SeatStatus.OUT])
        if not all_seats:
            return
            
        dealer_index = all_seats.index(self.state.dealer_position)
        
        # 找到大盲注位置
        if len(all_seats) == 2:
            # 单挑：庄家是小盲，另一个是大盲
            big_blind_index = 1 - dealer_index
        else:
            # 多人：庄家左边是小盲，小盲左边是大盲
            big_blind_index = (dealer_index + 2) % len(all_seats)
        
        # 从大盲注左边开始找第一个可以行动的玩家
        first_to_act_index = (big_blind_index + 1) % len(all_seats)
        
        # 确保找到一个可以行动的玩家
        for i in range(len(all_seats)):
            check_index = (first_to_act_index + i) % len(all_seats)
            check_seat = all_seats[check_index]
            check_player = self.state.get_player_by_seat(check_seat)
            
            if check_player and check_player.can_act():
                self.state.current_player = check_seat
                break
        else:
            # 如果没有找到可行动的玩家，设置为第一个活跃玩家
            if active_players:
                self.state.current_player = active_players[0].seat_id
        
        # 重置下注轮计数器
        self.state.street_index = 0
        self.state.last_raiser = None 