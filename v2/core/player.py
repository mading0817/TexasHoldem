"""
玩家状态管理模块。

包含Player类的实现，管理玩家的筹码、手牌、状态等信息。
该模块保持纯数据对象特性，不包含任何UI相关的打印功能。
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .cards import Card
from .enums import SeatStatus, ActionType


@dataclass
class Player:
    """
    德州扑克玩家类。
    
    管理玩家的筹码、手牌、状态等信息。该类为纯数据对象，
    不包含任何UI相关的打印或显示功能。
    
    Attributes:
        seat_id: 座位号，用于标识玩家位置
        name: 玩家名称
        chips: 当前筹码数量
        hole_cards: 手牌列表，最多2张
        current_bet: 本轮已投入的筹码
        status: 座位状态
        is_dealer: 是否为庄家
        is_small_blind: 是否为小盲注
        is_big_blind: 是否为大盲注
        last_action_type: 最后一次行动类型
        is_human: 是否为人类玩家
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

    def __post_init__(self) -> None:
        """验证玩家数据的有效性。
        
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
        """使Player对象可hash，基于seat_id。
        
        Returns:
            基于座位号的哈希值
        """
        return hash(self.seat_id)

    def __eq__(self, other: object) -> bool:
        """基于seat_id比较Player对象。
        
        Args:
            other: 另一个对象
            
        Returns:
            如果是相同座位的玩家则返回True
        """
        if not isinstance(other, Player):
            return False
        return self.seat_id == other.seat_id

    def can_act(self) -> bool:
        """
        检查玩家是否可以行动。
        
        Returns:
            如果玩家可以行动则返回True，否则返回False
        """
        return self.status == SeatStatus.ACTIVE and self.chips > 0

    def is_all_in(self) -> bool:
        """
        检查玩家是否已全押。
        
        Returns:
            如果玩家已全押则返回True，否则返回False
        """
        return self.status == SeatStatus.ALL_IN or (self.chips == 0 and self.current_bet > 0)

    def is_folded(self) -> bool:
        """
        检查玩家是否已弃牌。
        
        Returns:
            如果玩家已弃牌则返回True，否则返回False
        """
        return self.status == SeatStatus.FOLDED

    def is_out(self) -> bool:
        """
        检查玩家是否已出局。
        
        Returns:
            如果玩家已出局则返回True，否则返回False
        """
        return self.status == SeatStatus.OUT

    def get_effective_stack(self) -> int:
        """
        获取有效筹码数（当前筹码 + 本轮已投入）。
        
        Returns:
            有效筹码总数
        """
        return self.chips + self.current_bet

    def can_bet(self, amount: int) -> bool:
        """
        检查玩家是否可以下注指定金额。
        
        Args:
            amount: 要下注的金额
            
        Returns:
            如果可以下注则返回True，否则返回False
        """
        return self.can_act() and self.chips >= amount

    def can_call(self, call_amount: int) -> bool:
        """
        检查玩家是否可以跟注。
        
        Args:
            call_amount: 需要跟注的金额
            
        Returns:
            如果可以跟注则返回True，否则返回False
        """
        return self.can_act() and (self.chips >= call_amount or self.chips > 0)

    def bet(self, amount: int) -> int:
        """
        玩家下注。
        
        Args:
            amount: 下注金额
            
        Returns:
            实际下注金额
            
        Raises:
            ValueError: 当下注金额无效或玩家无法行动时
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
        玩家弃牌。
        
        Raises:
            ValueError: 当玩家无法弃牌时
        """
        if not self.can_act() and self.status != SeatStatus.ALL_IN:
            raise ValueError(f"玩家{self.seat_id}无法弃牌")
        
        self.status = SeatStatus.FOLDED

    def set_hole_cards(self, cards: List[Card]) -> None:
        """
        设置玩家手牌。
        
        Args:
            cards: 手牌列表，最多2张
            
        Raises:
            ValueError: 当手牌数量无效时
        """
        if len(cards) > 2:
            raise ValueError(f"手牌不能超过2张: {len(cards)}")
        
        self.hole_cards = cards.copy()

    def get_hole_cards_str(self, hidden: bool = False) -> str:
        """
        获取手牌的字符串表示。
        
        Args:
            hidden: 是否隐藏手牌（显示为XX）
            
        Returns:
            手牌的字符串表示
        """
        if hidden:
            return "XX XX" if len(self.hole_cards) == 2 else "XX" * len(self.hole_cards)
        
        return " ".join(str(card) for card in self.hole_cards)

    def reset_for_new_hand(self) -> None:
        """
        为新手牌重置玩家状态。
        
        保留筹码，清空手牌和当前下注。
        注意：位置标记(is_dealer, is_small_blind, is_big_blind)由游戏状态管理，不在此重置。
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
        重置当前下注。
        
        通常在下注轮结束时调用，同时重置最后行动类型，为新的下注轮做准备。
        """
        self.current_bet = 0
        self.last_action_type = None

    def add_chips(self, amount: int) -> None:
        """
        增加筹码。
        
        用于赢得底池时增加玩家筹码。
        
        Args:
            amount: 要增加的筹码数量
            
        Raises:
            ValueError: 当增加的筹码数量为负数时
        """
        if amount < 0:
            raise ValueError(f"增加的筹码数量不能为负数: {amount}")
        
        self.chips += amount
        
        # 如果玩家重新有筹码，可能需要重新激活
        if self.chips > 0 and self.status == SeatStatus.OUT:
            self.status = SeatStatus.ACTIVE

    def __str__(self) -> str:
        """
        返回玩家的可读表示。
        
        Returns:
            包含玩家基本信息的字符串
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
        返回玩家的调试表示。
        
        Returns:
            Player对象的详细字符串表示
        """
        return f"Player(seat={self.seat_id}, name='{self.name}', chips={self.chips}, status={self.status.name})"
    
    # === 测试兼容性方法 ===
    
    def get_hand_cards(self) -> List[Card]:
        """
        获取玩家手牌（测试兼容性方法）。
        
        Returns:
            玩家的手牌列表副本
        """
        return self.hole_cards.copy()
    
    @property
    def is_active(self) -> bool:
        """
        检查玩家是否处于活跃状态（测试兼容性属性）。
        
        Returns:
            如果玩家处于活跃状态则返回True
        """
        return self.status == SeatStatus.ACTIVE 