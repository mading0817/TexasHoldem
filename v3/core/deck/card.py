"""
扑克牌数据结构.

定义不可变的Card类，支持严格的类型检查和完整的操作接口.
"""

from dataclasses import dataclass
from typing import Dict

from .types import Suit, Rank


@dataclass(frozen=True)
class Card:
    """
    表示一张扑克牌.
    
    不可变数据类，包含花色和点数，支持比较、排序和字符串表示等操作.
    
    Attributes:
        suit: 花色
        rank: 点数
        
    Examples:
        >>> card = Card(Suit.HEARTS, Rank.ACE)
        >>> str(card)
        'AH'
        >>> card.rank.value
        14
    """

    suit: Suit
    rank: Rank
    
    def __post_init__(self) -> None:
        """
        验证扑克牌数据的有效性.
        
        Raises:
            TypeError: 当花色或点数类型无效时
            ValueError: 当花色或点数值无效时
        """
        if not isinstance(self.suit, Suit):
            raise TypeError(f"花色必须是Suit类型，实际: {type(self.suit)}")
        if not isinstance(self.rank, Rank):
            raise TypeError(f"点数必须是Rank类型，实际: {type(self.rank)}")
    
    def __str__(self) -> str:
        """
        返回扑克牌的字符串表示.
        
        Returns:
            str: 格式为"点数花色"的字符串，如"AH"表示红桃A
        """
        rank_display: Dict[Rank, str] = {
            Rank.TWO: "2", Rank.THREE: "3", Rank.FOUR: "4", Rank.FIVE: "5",
            Rank.SIX: "6", Rank.SEVEN: "7", Rank.EIGHT: "8", Rank.NINE: "9",
            Rank.TEN: "10", Rank.JACK: "J", Rank.QUEEN: "Q", 
            Rank.KING: "K", Rank.ACE: "A"
        }
        suit_display: Dict[Suit, str] = {
            Suit.HEARTS: "H", Suit.DIAMONDS: "D", 
            Suit.CLUBS: "C", Suit.SPADES: "S"
        }
        return f"{rank_display[self.rank]}{suit_display[self.suit]}"
    
    def __repr__(self) -> str:
        """
        返回扑克牌的详细字符串表示.
        
        Returns:
            str: 包含类名的详细表示，如"Card(suit=Suit.HEARTS, rank=Rank.ACE)"
        """
        return f"Card({self.rank.name}, {self.suit.name})"
    
    @classmethod
    def from_str(cls, card_str: str) -> 'Card':
        """
        从字符串创建扑克牌对象.
        
        Args:
            card_str: 扑克牌字符串，格式为"点数花色"，如"AH"
            
        Returns:
            Card: 对应的扑克牌对象
            
        Raises:
            ValueError: 当字符串格式无效时
        """
        if not isinstance(card_str, str):
            raise TypeError(f"输入必须是字符串，实际: {type(card_str)}")
            
        if len(card_str) < 2:
            raise ValueError(f"卡牌字符串格式错误: {card_str}")
        
        # 处理10的特殊情况
        if card_str.startswith("10"):
            rank_str, suit_str = "10", card_str[2:]
        else:
            rank_str, suit_str = card_str[0], card_str[1:]
        
        # 解析点数
        rank_map: Dict[str, Rank] = {
            "2": Rank.TWO, "3": Rank.THREE, "4": Rank.FOUR, "5": Rank.FIVE,
            "6": Rank.SIX, "7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE,
            "10": Rank.TEN, "T": Rank.TEN, "J": Rank.JACK, "Q": Rank.QUEEN,
            "K": Rank.KING, "A": Rank.ACE
        }
        
        # 解析花色
        suit_map: Dict[str, Suit] = {
            "h": Suit.HEARTS, "H": Suit.HEARTS,
            "d": Suit.DIAMONDS, "D": Suit.DIAMONDS,
            "c": Suit.CLUBS, "C": Suit.CLUBS,
            "s": Suit.SPADES, "S": Suit.SPADES
        }
        
        if rank_str not in rank_map:
            raise ValueError(f"无效的点数: {rank_str}")
        if suit_str not in suit_map:
            raise ValueError(f"无效的花色: {suit_str}")
        
        return cls(suit_map[suit_str], rank_map[rank_str])
    
    def __lt__(self, other: 'Card') -> bool:
        """
        比较两张牌的大小.
        
        Args:
            other: 另一张牌
            
        Returns:
            bool: 如果当前牌小于另一张牌则返回True
        """
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank.value < other.rank.value
    
    def __eq__(self, other: object) -> bool:
        """
        判断两张牌是否相等.
        
        Args:
            other: 另一个对象
            
        Returns:
            bool: 如果两张牌的花色和点数都相同则返回True
        """
        if not isinstance(other, Card):
            return NotImplemented
        return self.suit == other.suit and self.rank == other.rank
    
    def __hash__(self) -> int:
        """
        返回扑克牌的哈希值.
        
        Returns:
            int: 基于花色和点数计算的哈希值
        """
        return hash((self.suit, self.rank)) 