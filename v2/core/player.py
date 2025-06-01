"""
德州扑克玩家状态管理.

包含玩家的基本信息、筹码管理、手牌管理和状态控制功能.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .cards import Card
from .enums import SeatStatus, ActionType


@dataclass
class Player:
    """
    德州扑克玩家类.
    
    管理玩家的基本信息、筹码、手牌和游戏状态.
    """

    seat_id: int
    name: str
    chips: int
    hole_cards: List[Card] = field(default_factory=list)
    current_bet: int = 0
    status: SeatStatus = SeatStatus.ACTIVE
    is_dealer: bool = False
    is_small_blind: bool = False
    is_big_blind: bool = False
    last_action_type: Optional[ActionType] = None
    is_human: bool = False
    total_bet_this_hand: int = 0

    def __post_init__(self) -> None:
        """
        验证玩家数据的有效性.
        
        Raises:
            ValueError: 当玩家数据无效时
        """
        if self.seat_id < 0:
            raise ValueError(f"座位号不能为负数: {self.seat_id}")
        
        if self.chips < 0:
            raise ValueError(f"筹码数量不能为负数: {self.chips}")
        
        if self.current_bet < 0:
            raise ValueError(f"当前下注不能为负数: {self.current_bet}")
        
        if len(self.hole_cards) > 2:
            raise ValueError(f"手牌不能超过2张: {len(self.hole_cards)}")

    def __hash__(self) -> int:
        """
        返回玩家的哈希值.
        
        Returns:
            int: 基于座位号的哈希值
        """
        return hash(self.seat_id)

    def __eq__(self, other: object) -> bool:
        """
        判断两个玩家是否相等.
        
        Args:
            other: 另一个对象
            
        Returns:
            bool: 如果座位号相同则返回True
        """
        if not isinstance(other, Player):
            return False
        return self.seat_id == other.seat_id

    def can_act(self) -> bool:
        """
        检查玩家是否可以行动.
        
        Returns:
            bool: 如果玩家状态为ACTIVE则返回True
        """
        return self.status == SeatStatus.ACTIVE and self.chips > 0

    def is_all_in(self) -> bool:
        """
        检查玩家是否全押.
        
        Returns:
            bool: 如果玩家状态为ALL_IN则返回True
        """
        return self.status == SeatStatus.ALL_IN or (self.chips == 0 and self.current_bet > 0)

    def is_folded(self) -> bool:
        """
        检查玩家是否已弃牌.
        
        Returns:
            bool: 如果玩家状态为FOLDED则返回True
        """
        return self.status == SeatStatus.FOLDED

    def is_out(self) -> bool:
        """
        检查玩家是否已出局.
        
        Returns:
            bool: 如果玩家状态为OUT则返回True
        """
        return self.status == SeatStatus.OUT

    def get_effective_stack(self) -> int:
        """
        获取玩家的有效筹码数.
        
        Returns:
            int: 玩家当前可用的筹码数
        """
        return self.chips + self.current_bet

    def can_bet(self, amount: int) -> bool:
        """
        检查玩家是否可以下注指定金额.
        
        Args:
            amount: 要下注的金额
            
        Returns:
            bool: 如果玩家有足够筹码则返回True
        """
        return self.can_act() and self.chips >= amount

    def can_call(self, call_amount: int) -> bool:
        """
        检查玩家是否可以跟注指定金额.
        
        Args:
            call_amount: 要跟注的金额
            
        Returns:
            bool: 如果玩家有足够筹码则返回True
        """
        return self.can_act() and (self.chips >= call_amount or self.chips > 0)

    def bet(self, amount: int) -> int:
        """
        执行下注操作.
        
        Args:
            amount: 下注金额
            
        Returns:
            int: 实际下注的金额
            
        Raises:
            ValueError: 当下注金额无效或筹码不足时
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

    def fold(self) -> None:
        """
        执行弃牌操作.
        
        将玩家状态设置为FOLDED.
        """
        if not self.can_act() and self.status != SeatStatus.ALL_IN:
            raise ValueError(f"玩家{self.seat_id}无法弃牌")
        
        self.status = SeatStatus.FOLDED

    def set_hole_cards(self, cards: List[Card]) -> None:
        """
        设置玩家的手牌.
        
        Args:
            cards: 手牌列表，通常为2张牌
            
        Raises:
            ValueError: 当手牌数量不正确时
        """
        if len(cards) > 2:
            raise ValueError(f"手牌不能超过2张: {len(cards)}")
        
        self.hole_cards = cards.copy()

    def get_hole_cards_str(self, hidden: bool = False) -> str:
        """
        获取手牌的字符串表示.
        
        Returns:
            str: 手牌的字符串表示，如"AH KS"
        """
        if hidden:
            return "XX XX" if len(self.hole_cards) == 2 else "XX" * len(self.hole_cards)
        
        return " ".join(str(card) for card in self.hole_cards)

    def reset_for_new_hand(self) -> None:
        """
        为新一手牌重置玩家状态.
        
        清空手牌，重置下注金额和状态.
        """
        self.hole_cards.clear()
        self.current_bet = 0
        self.last_action_type = None
        
        # 重置状态（除非玩家已出局）
        if self.status != SeatStatus.OUT:
            if self.chips > 0:
                self.status = SeatStatus.ACTIVE
            else:
                self.status = SeatStatus.OUT

    def reset_current_bet(self) -> None:
        """
        重置当前轮次的下注金额.
        
        通常在新的下注轮开始时调用.
        """
        self.current_bet = 0
        self.last_action_type = None

    def add_chips(self, amount: int) -> None:
        """
        增加玩家的筹码.
        
        Args:
            amount: 要增加的筹码数量
            
        Raises:
            ValueError: 当金额为负数时
        """
        if amount < 0:
            raise ValueError(f"增加的筹码数量不能为负数: {amount}")
        
        self.chips += amount
        
        # 如果玩家重新有筹码，可能需要重新激活
        if self.chips > 0 and self.status == SeatStatus.OUT:
            self.status = SeatStatus.ACTIVE

    def __str__(self) -> str:
        """
        返回玩家的字符串表示.
        
        Returns:
            str: 包含玩家基本信息的字符串
        """
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
        """
        返回玩家的详细字符串表示.
        
        Returns:
            str: 包含所有玩家信息的详细字符串
        """
        return f"Player(seat={self.seat_id}, name='{self.name}', chips={self.chips}, status={self.status.name})"
    
    # === 测试兼容性方法 ===
    
    def get_hand_cards(self) -> List[Card]:
        """
        获取玩家手牌（测试兼容性方法）.
        
        Returns:
            玩家的手牌列表副本
        """
        return self.hole_cards.copy()
    
    @property
    def is_active(self) -> bool:
        """
        检查玩家是否处于活跃状态（测试兼容性属性）.
        
        Returns:
            如果玩家处于活跃状态则返回True
        """
        return self.status == SeatStatus.ACTIVE