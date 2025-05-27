"""
德州扑克游戏的基础枚举定义
包含花色、点数、玩家状态、游戏阶段和动作类型
"""

from enum import Enum, auto


class Suit(Enum):
    """扑克牌花色枚举"""
    HEARTS = "h"      # 红桃
    DIAMONDS = "d"    # 方块  
    CLUBS = "c"       # 梅花
    SPADES = "s"      # 黑桃

    def __str__(self) -> str:
        return self.value

    @property
    def symbol(self) -> str:
        """返回花色符号"""
        symbols = {
            self.HEARTS: "♥",
            self.DIAMONDS: "♦", 
            self.CLUBS: "♣",
            self.SPADES: "♠"
        }
        return symbols[self]


class Rank(Enum):
    """扑克牌点数枚举，数值用于大小比较"""
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    def __str__(self) -> str:
        """返回点数的简短表示"""
        if self.value <= 9:
            return str(self.value)
        return {
            10: "T",
            11: "J", 
            12: "Q",
            13: "K",
            14: "A"
        }[self.value]

    @classmethod
    def from_str(cls, rank_str: str) -> 'Rank':
        """从字符串创建Rank对象"""
        if rank_str.isdigit():
            return cls(int(rank_str))
        
        rank_map = {
            "T": cls.TEN,
            "J": cls.JACK,
            "Q": cls.QUEEN, 
            "K": cls.KING,
            "A": cls.ACE
        }
        return rank_map[rank_str.upper()]


class SeatStatus(Enum):
    """玩家座位状态枚举"""
    ACTIVE = auto()   # 可行动状态
    FOLDED = auto()   # 已弃牌
    ALL_IN = auto()   # 已全押，无法继续投入
    OUT = auto()      # 筹码耗尽，退出游戏


class GamePhase(Enum):
    """游戏阶段枚举"""
    PRE_FLOP = auto()  # 翻牌前
    FLOP = auto()      # 翻牌圈
    TURN = auto()      # 转牌圈  
    RIVER = auto()     # 河牌圈
    SHOWDOWN = auto()  # 摊牌阶段


class ActionType(Enum):
    """玩家动作类型枚举"""
    FOLD = auto()      # 弃牌
    CHECK = auto()     # 过牌
    CALL = auto()      # 跟注
    BET = auto()       # 下注
    RAISE = auto()     # 加注
    ALL_IN = auto()    # 全押

    def __str__(self) -> str:
        return self.name.lower()


# 在文件末尾添加Action数据类
from dataclasses import dataclass
from typing import Optional

@dataclass
class Action:
    """
    玩家行动数据类
    包含行动类型和相关参数
    """
    action_type: ActionType
    amount: int = 0                    # 下注/加注金额
    player_seat: Optional[int] = None  # 执行行动的玩家座位号
    
    def __post_init__(self):
        """验证行动数据的有效性"""
        if self.action_type in [ActionType.BET, ActionType.RAISE] and self.amount <= 0:
            raise ValueError(f"{self.action_type.name}行动必须指定正数金额")
        
        if self.action_type in [ActionType.FOLD, ActionType.CHECK, ActionType.CALL] and self.amount != 0:
            self.amount = 0  # 这些行动不需要金额参数
    
    def __str__(self) -> str:
        if self.amount > 0:
            return f"{self.action_type.name}({self.amount})"
        return self.action_type.name


@dataclass  
class ValidatedAction:
    """
    经过验证的玩家行动
    包含原始行动和验证后的实际参数
    """
    original_action: Action
    actual_action_type: ActionType     # 可能被转换的行动类型（如加注不足转为All-in）
    actual_amount: int                 # 实际执行的金额
    player_seat: int                   # 执行行动的玩家座位号
    is_converted: bool = False         # 是否被智能转换
    conversion_reason: str = ""        # 转换原因
    
    def __str__(self) -> str:
        base = f"{self.actual_action_type.name}"
        if self.actual_amount > 0:
            base += f"({self.actual_amount})"
        if self.is_converted:
            base += f" [转换: {self.conversion_reason}]"
        return base 