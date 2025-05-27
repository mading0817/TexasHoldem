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
        3. 设置盲注
        4. 开始下注轮
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
        
        # 设置盲注
        self.state.set_blinds()
        
        # 开始下注轮，从大盲注左边的玩家开始
        self._start_preflop_betting()
        
        # 记录事件
        self.state.add_event(f"翻牌前阶段开始，底池: {self.state.pot}")
    
    def act(self, action: 'ValidatedAction') -> bool:
        """
        处理玩家行动
        
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
        退出翻牌前阶段
        收集下注到底池，推进到翻牌阶段
        
        Returns:
            下一个阶段的实例（FlopPhase）
        """
        # 收集所有下注到底池
        self.state.collect_bets_to_pot()
        
        # 推进游戏阶段
        self.state.advance_phase()
        
        # 记录事件
        self.state.add_event(f"翻牌前结束，底池: {self.state.pot}")
        
        # 检查是否只剩一个玩家（其他都弃牌了）
        players_in_hand = self.state.get_players_in_hand()
        if len(players_in_hand) <= 1:
            # 直接进入摊牌阶段
            from .showdown import ShowdownPhase
            return ShowdownPhase(self.state)
        
        # 进入翻牌阶段
        from .flop import FlopPhase
        return FlopPhase(self.state)
    
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
        dealer_index = all_seats.index(self.state.dealer_position)
        
        # 找到大盲注位置
        if len(all_seats) == 2:
            # 单挑：庄家是小盲，另一个是大盲
            big_blind_index = 1 - dealer_index
        else:
            # 多人：庄家左边是小盲，小盲左边是大盲
            big_blind_index = (dealer_index + 2) % len(all_seats)
        
        # 从大盲注左边开始
        first_to_act_index = (big_blind_index + 1) % len(all_seats)
        first_to_act_seat = all_seats[first_to_act_index]
        
        # 设置当前行动玩家
        self.state.current_player = first_to_act_seat
        
        # 重置下注轮计数器
        self.state.street_index = 0
        self.state.last_raiser = None
    
    def _execute_action(self, player, action: 'ValidatedAction'):
        """执行玩家行动"""
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