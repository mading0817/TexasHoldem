"""
德州扑克牌型等级定义
包含9种标准牌型的常量和名称映射
"""

from enum import IntEnum


class HandRank(IntEnum):
    """
    德州扑克牌型等级枚举
    数值越大牌型越强，用于直接比较
    """
    HIGH_CARD = 1       # 高牌
    ONE_PAIR = 2        # 一对
    TWO_PAIR = 3        # 两对
    THREE_KIND = 4      # 三条
    STRAIGHT = 5        # 顺子
    FLUSH = 6           # 同花
    FULL_HOUSE = 7      # 葫芦（满堂红）
    FOUR_KIND = 8       # 四条
    STRAIGHT_FLUSH = 9  # 同花顺

    def __str__(self) -> str:
        return HAND_RANK_NAMES[self]


# 牌型名称映射
HAND_RANK_NAMES = {
    HandRank.HIGH_CARD: "高牌",
    HandRank.ONE_PAIR: "一对", 
    HandRank.TWO_PAIR: "两对",
    HandRank.THREE_KIND: "三条",
    HandRank.STRAIGHT: "顺子",
    HandRank.FLUSH: "同花",
    HandRank.FULL_HOUSE: "葫芦",
    HandRank.FOUR_KIND: "四条",
    HandRank.STRAIGHT_FLUSH: "同花顺"
}


def get_hand_rank_name(rank: HandRank) -> str:
    """
    获取牌型的中文名称
    
    Args:
        rank: 牌型等级
        
    Returns:
        牌型的中文名称
    """
    return HAND_RANK_NAMES.get(rank, "未知牌型") 