"""
德州扑克牌型评估相关类型定义.

定义牌型等级、评估结果等核心数据结构.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Tuple

from ..deck.types import Rank


class HandRank(IntEnum):
    """
    德州扑克牌型枚举.
    
    定义所有可能的牌型，数值越大表示牌型越强.
    包含皇家同花顺在内的10种标准牌型.
    """

    HIGH_CARD = 1          # 高牌
    ONE_PAIR = 2           # 一对
    TWO_PAIR = 3           # 两对
    THREE_OF_A_KIND = 4    # 三条
    STRAIGHT = 5           # 顺子
    FLUSH = 6              # 同花
    FULL_HOUSE = 7         # 葫芦
    FOUR_OF_A_KIND = 8     # 四条
    STRAIGHT_FLUSH = 9     # 同花顺
    ROYAL_FLUSH = 10       # 皇家同花顺


@dataclass(frozen=True)
class HandResult:
    """
    牌型评估结果.
    
    包含牌型等级、关键牌和踢脚牌信息，支持牌型比较.
    
    Attributes:
        rank: 牌型等级
        primary_value: 主要牌值（如对子的点数）
        secondary_value: 次要牌值（如两对中较小的对子）
        kickers: 踢脚牌点数，按降序排列
        
    Examples:
        >>> result = HandResult(HandRank.ONE_PAIR, 14, 0, (13, 12, 11))
        >>> result.rank
        <HandRank.ONE_PAIR: 2>
        >>> result.primary_value
        14
    """

    rank: HandRank
    primary_value: int
    secondary_value: int = 0
    kickers: Tuple[int, ...] = ()

    def __post_init__(self) -> None:
        """
        验证评估结果的有效性.
        
        Raises:
            TypeError: 当牌型等级类型无效时
            ValueError: 当评估结果数据无效时
        """
        if not isinstance(self.rank, HandRank):
            raise TypeError(f"牌型等级必须是HandRank类型，实际: {type(self.rank)}")
        
        if self.primary_value < 2 or self.primary_value > 14:
            raise ValueError(f"无效的主要牌值: {self.primary_value}")
            
        if self.secondary_value < 0 or self.secondary_value > 14:
            raise ValueError(f"无效的次要牌值: {self.secondary_value}")
            
        # 验证踢脚牌
        for kicker in self.kickers:
            if kicker < 2 or kicker > 14:
                raise ValueError(f"无效的踢脚牌值: {kicker}")

    def compare_to(self, other: 'HandResult') -> int:
        """
        比较两个牌型的强弱.
        
        Args:
            other: 另一个牌型评估结果
            
        Returns:
            int: 1表示当前牌型更强，-1表示更弱，0表示相等
            
        Raises:
            TypeError: 当other不是HandResult类型时
        """
        if not isinstance(other, HandResult):
            raise TypeError(f"比较对象必须是HandResult类型，实际: {type(other)}")
        
        # 首先比较牌型等级
        if self.rank != other.rank:
            return 1 if self.rank > other.rank else -1
        
        # 牌型相同，比较主要牌值
        if self.primary_value != other.primary_value:
            return 1 if self.primary_value > other.primary_value else -1
        
        # 主要牌值相同，比较次要牌值
        if self.secondary_value != other.secondary_value:
            return 1 if self.secondary_value > other.secondary_value else -1
        
        # 比较踢脚牌
        for my_kicker, other_kicker in zip(self.kickers, other.kickers):
            if my_kicker != other_kicker:
                return 1 if my_kicker > other_kicker else -1
        
        # 完全相同
        return 0

    def __str__(self) -> str:
        """
        返回牌型的字符串描述.
        
        Returns:
            str: 包含牌型名称和关键牌的描述
        """
        rank_names = {
            HandRank.HIGH_CARD: "高牌",
            HandRank.ONE_PAIR: "一对",
            HandRank.TWO_PAIR: "两对",
            HandRank.THREE_OF_A_KIND: "三条",
            HandRank.STRAIGHT: "顺子",
            HandRank.FLUSH: "同花",
            HandRank.FULL_HOUSE: "葫芦",
            HandRank.FOUR_OF_A_KIND: "四条",
            HandRank.STRAIGHT_FLUSH: "同花顺",
            HandRank.ROYAL_FLUSH: "皇家同花顺"
        }
        
        rank_name = rank_names.get(self.rank, str(self.rank))
        
        if self.rank == HandRank.ONE_PAIR:
            return f"{rank_name}({Rank(self.primary_value).name})"
        elif self.rank == HandRank.TWO_PAIR:
            return f"{rank_name}({Rank(self.primary_value).name}和{Rank(self.secondary_value).name})"
        elif self.rank in [HandRank.THREE_OF_A_KIND, HandRank.FOUR_OF_A_KIND]:
            return f"{rank_name}({Rank(self.primary_value).name})"
        elif self.rank == HandRank.FULL_HOUSE:
            return f"{rank_name}({Rank(self.primary_value).name}带{Rank(self.secondary_value).name})"
        elif self.rank in [HandRank.STRAIGHT, HandRank.STRAIGHT_FLUSH, HandRank.ROYAL_FLUSH]:
            return f"{rank_name}({Rank(self.primary_value).name}高)"
        else:
            return rank_name 