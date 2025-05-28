"""
玩家相关类的实现
包含玩家状态管理和操作方法
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from .card import Card
from .enums import SeatStatus, ActionType


@dataclass
class Player:
    """
    德州扑克玩家类
    管理玩家的筹码、手牌、状态等信息
    """
    seat_id: int                                    # 座位号
    name: str                                       # 玩家名称
    chips: int                                      # 当前筹码数量
    hole_cards: List[Card] = field(default_factory=list)  # 手牌（最多2张）
    current_bet: int = 0                           # 本轮已投入的筹码
    status: SeatStatus = SeatStatus.ACTIVE         # 座位状态
    is_dealer: bool = False                        # 是否为庄家
    is_small_blind: bool = False                   # 是否为小盲注
    is_big_blind: bool = False                     # 是否为大盲注
    last_action_type: Optional[ActionType] = None  # 最后一次行动类型

    def __post_init__(self):
        """验证玩家数据的有效性"""
        if self.seat_id < 0:
            raise ValueError(f"座位号不能为负数: {self.seat_id}")
        
        if self.chips < 0:
            raise ValueError(f"筹码数量不能为负数: {self.chips}")
        
        if self.current_bet < 0:
            raise ValueError(f"当前下注不能为负数: {self.current_bet}")
        
        if len(self.hole_cards) > 2:
            raise ValueError(f"手牌不能超过2张: {len(self.hole_cards)}")

    def can_act(self) -> bool:
        """
        检查玩家是否可以行动
        
        Returns:
            True如果玩家可以行动，False否则
        """
        return self.status == SeatStatus.ACTIVE and self.chips > 0

    def is_all_in(self) -> bool:
        """
        检查玩家是否已全押
        
        Returns:
            True如果玩家已全押，False否则
        """
        return self.status == SeatStatus.ALL_IN or (self.chips == 0 and self.current_bet > 0)

    def is_folded(self) -> bool:
        """
        检查玩家是否已弃牌
        
        Returns:
            True如果玩家已弃牌，False否则
        """
        return self.status == SeatStatus.FOLDED

    def is_out(self) -> bool:
        """
        检查玩家是否已出局
        
        Returns:
            True如果玩家已出局，False否则
        """
        return self.status == SeatStatus.OUT

    def get_effective_stack(self) -> int:
        """
        获取有效筹码数（当前筹码 + 本轮已投入）
        
        Returns:
            有效筹码总数
        """
        return self.chips + self.current_bet

    def can_bet(self, amount: int) -> bool:
        """
        检查玩家是否可以下注指定金额
        
        Args:
            amount: 要下注的金额
            
        Returns:
            True如果可以下注，False否则
        """
        return self.can_act() and self.chips >= amount

    def can_call(self, call_amount: int) -> bool:
        """
        检查玩家是否可以跟注
        
        Args:
            call_amount: 需要跟注的金额
            
        Returns:
            True如果可以跟注，False否则
        """
        return self.can_act() and (self.chips >= call_amount or self.chips > 0)

    def bet(self, amount: int) -> int:
        """
        玩家下注
        
        Args:
            amount: 下注金额
            
        Returns:
            实际下注金额
            
        Raises:
            ValueError: 当下注金额无效时
        """
        if not self.can_act():
            raise ValueError(f"玩家{self.seat_id}无法行动")
        
        if amount < 0:
            raise ValueError(f"下注金额不能为负数: {amount}")
        
        # 如果下注金额超过筹码，则全押
        actual_amount = min(amount, self.chips)
        
        self.chips -= actual_amount
        self.current_bet += actual_amount
        
        # 如果筹码用完，设置为全押状态
        if self.chips == 0:
            self.status = SeatStatus.ALL_IN
        
        return actual_amount

    def fold(self):
        """玩家弃牌"""
        if not self.can_act():
            raise ValueError(f"玩家{self.seat_id}无法弃牌")
        
        self.status = SeatStatus.FOLDED

    def set_hole_cards(self, cards: List[Card]):
        """
        设置玩家手牌
        
        Args:
            cards: 手牌列表（最多2张）
            
        Raises:
            ValueError: 当手牌数量无效时
        """
        if len(cards) > 2:
            raise ValueError(f"手牌不能超过2张: {len(cards)}")
        
        self.hole_cards = cards.copy()

    def get_hole_cards_str(self, hidden: bool = False) -> str:
        """
        获取手牌的字符串表示
        
        Args:
            hidden: 是否隐藏手牌（显示为XX）
            
        Returns:
            手牌的字符串表示
        """
        if hidden:
            return "XX XX" if len(self.hole_cards) == 2 else "XX" * len(self.hole_cards)
        
        return " ".join(card.to_display_str() for card in self.hole_cards)

    def reset_for_new_hand(self):
        """
        为新手牌重置玩家状态
        保留筹码，清空手牌和当前下注
        注意：位置标记(is_dealer, is_small_blind, is_big_blind)由游戏状态管理，不在此重置
        """
        self.hole_cards.clear()
        self.current_bet = 0
        # 不重置位置标记，这些由GameState.set_blinds()管理
        # self.is_dealer = False
        # self.is_small_blind = False  
        # self.is_big_blind = False
        self.last_action_type = None  # 重置最后行动类型
        
        # 重置状态（除非玩家已出局）
        if self.status != SeatStatus.OUT:
            if self.chips > 0:
                self.status = SeatStatus.ACTIVE
            else:
                self.status = SeatStatus.OUT

    def reset_current_bet(self):
        """
        重置当前下注（通常在下注轮结束时调用）
        """
        self.current_bet = 0

    def add_chips(self, amount: int):
        """
        增加筹码（用于赢得底池时）
        
        Args:
            amount: 要增加的筹码数量
        """
        if amount < 0:
            raise ValueError(f"增加的筹码数量不能为负数: {amount}")
        
        self.chips += amount
        
        # 如果玩家重新有筹码，可能需要重新激活
        if self.chips > 0 and self.status == SeatStatus.OUT:
            self.status = SeatStatus.ACTIVE

    def __str__(self) -> str:
        """返回玩家的可读表示"""
        status_str = self.status.name
        cards_str = self.get_hole_cards_str()
        
        position_info = []
        if self.is_dealer:
            position_info.append("庄家")
        if self.is_small_blind:
            position_info.append("小盲")
        if self.is_big_blind:
            position_info.append("大盲")
        
        position_str = f"({', '.join(position_info)})" if position_info else ""
        
        return f"{self.name}{position_str}: {self.chips}筹码, 当前下注{self.current_bet}, 手牌[{cards_str}], 状态{status_str}"

    def __repr__(self) -> str:
        """返回玩家的调试表示"""
        return f"Player(seat={self.seat_id}, name='{self.name}', chips={self.chips}, status={self.status.name})" 