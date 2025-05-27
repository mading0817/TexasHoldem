"""
扑克牌相关类的实现
包含Card类和CardPool对象池，用于内存优化
"""

from dataclasses import dataclass
from typing import Dict, Tuple, List
from .enums import Suit, Rank


@dataclass(frozen=True)
class Card:
    """
    不可变的扑克牌类
    使用frozen dataclass确保不可变性
    """
    rank: Rank
    suit: Suit

    def __post_init__(self):
        """验证卡牌的有效性"""
        if not isinstance(self.rank, Rank):
            raise ValueError(f"无效的点数: {self.rank}")
        if not isinstance(self.suit, Suit):
            raise ValueError(f"无效的花色: {self.suit}")

    def to_str(self) -> str:
        """
        返回卡牌的简短字符串表示
        例如: "As" (黑桃A), "Kh" (红桃K)
        """
        return f"{self.rank}{self.suit}"
    
    def to_display_str(self) -> str:
        """
        返回卡牌的显示字符串表示（使用花色符号）
        例如: "A♠" (黑桃A), "K♥" (红桃K)
        """
        return f"{self.rank}{self.suit.symbol}"

    @classmethod
    def from_str(cls, card_str: str) -> 'Card':
        """
        从字符串创建Card对象
        例如: "As" -> Card(ACE, SPADES)
        """
        if len(card_str) != 2:
            raise ValueError(f"卡牌字符串格式错误: {card_str}")
        
        rank_str, suit_str = card_str[0], card_str[1]
        
        try:
            rank = Rank.from_str(rank_str)
            suit = Suit(suit_str.lower())
            return cls(rank, suit)
        except (ValueError, KeyError) as e:
            raise ValueError(f"无法解析卡牌字符串 '{card_str}': {e}")

    def __str__(self) -> str:
        """返回卡牌的简短字符串表示"""
        return self.to_str()

    def __repr__(self) -> str:
        """返回卡牌的调试表示"""
        return f"Card({self.rank.name}, {self.suit.name})"


class CardPool:
    """
    卡牌对象池，用于内存优化
    预创建所有52张卡牌的单例，避免重复创建对象
    """
    _instances: Dict[Tuple[Rank, Suit], Card] = {}
    _initialized = False

    @classmethod
    def _initialize(cls):
        """初始化对象池，创建所有52张卡牌"""
        if cls._initialized:
            return
        
        for rank in Rank:
            for suit in Suit:
                cls._instances[(rank, suit)] = Card(rank, suit)
        
        cls._initialized = True

    @classmethod
    def get_card(cls, rank: Rank, suit: Suit) -> Card:
        """
        获取指定的卡牌对象
        使用对象池避免重复创建
        """
        cls._initialize()
        return cls._instances[(rank, suit)]

    @classmethod
    def get_all_cards(cls) -> List[Card]:
        """获取所有52张卡牌的列表"""
        cls._initialize()
        return list(cls._instances.values())

    @classmethod
    def from_str(cls, card_str: str) -> Card:
        """
        从字符串获取卡牌对象（使用对象池）
        这是Card.from_str的优化版本
        """
        if len(card_str) != 2:
            raise ValueError(f"卡牌字符串格式错误: {card_str}")
        
        rank_str, suit_str = card_str[0], card_str[1]
        
        try:
            rank = Rank.from_str(rank_str)
            suit = Suit(suit_str.lower())
            return cls.get_card(rank, suit)
        except (ValueError, KeyError) as e:
            raise ValueError(f"无法解析卡牌字符串 '{card_str}': {e}")

    @classmethod
    def reset(cls):
        """重置对象池（主要用于测试）"""
        cls._instances.clear()
        cls._initialized = False 