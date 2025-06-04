"""
德州扑克牌组相关类型定义.

定义扑克牌的花色、点数等基础枚举类型.
"""

from enum import Enum, IntEnum
from typing import List


class Suit(Enum):
    """
    扑克牌花色枚举.
    
    定义四种标准扑克牌花色，使用Unicode符号表示.
    """

    HEARTS = "♥"      # 红桃
    DIAMONDS = "♦"    # 方块
    CLUBS = "♣"       # 梅花
    SPADES = "♠"      # 黑桃


class Rank(IntEnum):
    """
    扑克牌点数枚举.
    
    定义13种扑克牌点数，数值越大表示点数越大.
    在德州扑德中，A可以作为最大或最小的牌.
    """

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


def get_all_suits() -> List[Suit]:
    """
    获取所有花色.
    
    Returns:
        List[Suit]: 包含所有四种花色的列表
    """
    return list(Suit)


def get_all_ranks() -> List[Rank]:
    """
    获取所有点数.
    
    Returns:
        List[Rank]: 包含所有13种点数的列表
    """
    return list(Rank) 