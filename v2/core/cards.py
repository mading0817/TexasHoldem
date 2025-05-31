"""
扑克牌相关的核心数据对象。

包含Card（单张牌）和Deck（牌堆）的实现，保持纯数据对象特性。
"""

import random
from dataclasses import dataclass
from typing import List, Optional

from .enums import Suit, Rank


@dataclass(frozen=True)
class Card:
    """
    表示一张扑克牌。
    
    Attributes:
        suit: 花色
        rank: 点数
    """
    suit: Suit
    rank: Rank
    
    def __str__(self) -> str:
        """返回牌的字符串表示。
        
        Returns:
            格式为"点数花色"的字符串，如"AH"表示红桃A
        """
        rank_display = {
            Rank.TWO: "2", Rank.THREE: "3", Rank.FOUR: "4", Rank.FIVE: "5",
            Rank.SIX: "6", Rank.SEVEN: "7", Rank.EIGHT: "8", Rank.NINE: "9",
            Rank.TEN: "10", Rank.JACK: "J", Rank.QUEEN: "Q", 
            Rank.KING: "K", Rank.ACE: "A"
        }
        suit_display = {
            Suit.HEARTS: "H", Suit.DIAMONDS: "D", 
            Suit.CLUBS: "C", Suit.SPADES: "S"
        }
        return f"{rank_display[self.rank]}{suit_display[self.suit]}"
    
    def __repr__(self) -> str:
        """返回牌的详细表示。
        
        Returns:
            Card对象的详细字符串表示
        """
        return f"Card({self.rank.name}, {self.suit.name})"
    
    @classmethod
    def from_str(cls, card_str: str) -> 'Card':
        """从字符串创建Card对象。
        
        Args:
            card_str: 牌的字符串表示，如"As"表示黑桃A，"Kh"表示红桃K
            
        Returns:
            对应的Card对象
            
        Raises:
            ValueError: 如果字符串格式无效
        """
        if len(card_str) < 2:
            raise ValueError(f"卡牌字符串格式错误: {card_str}")
        
        # 处理10的特殊情况
        if card_str.startswith("10"):
            rank_str, suit_str = "10", card_str[2:]
        else:
            rank_str, suit_str = card_str[0], card_str[1:]
        
        # 解析点数
        rank_map = {
            "2": Rank.TWO, "3": Rank.THREE, "4": Rank.FOUR, "5": Rank.FIVE,
            "6": Rank.SIX, "7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE,
            "10": Rank.TEN, "T": Rank.TEN, "J": Rank.JACK, "Q": Rank.QUEEN,
            "K": Rank.KING, "A": Rank.ACE
        }
        
        # 解析花色
        suit_map = {
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
        """比较两张牌的大小（仅比较点数）。
        
        Args:
            other: 另一张牌
            
        Returns:
            如果当前牌点数小于另一张牌则返回True
        """
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank.value < other.rank.value
    
    def __eq__(self, other: object) -> bool:
        """判断两张牌是否相等。
        
        Args:
            other: 另一个对象
            
        Returns:
            如果花色和点数都相同则返回True
        """
        if not isinstance(other, Card):
            return NotImplemented
        return self.suit == other.suit and self.rank == other.rank
    
    def __hash__(self) -> int:
        """返回牌的哈希值。
        
        Returns:
            基于花色和点数的哈希值
        """
        return hash((self.suit, self.rank))


class Deck:
    """
    表示一副扑克牌。
    
    提供洗牌、发牌等基本功能。
    """
    
    def __init__(self, rng: Optional[random.Random] = None):
        """
        初始化一副完整的52张牌。
        
        Args:
            rng: 随机数生成器，用于洗牌。如果为None则使用默认随机数生成器
        """
        self._rng = rng or random.Random()
        self._cards: List[Card] = []
        self._reset_deck()
    
    def _reset_deck(self) -> None:
        """重置牌堆为完整的52张牌。"""
        self._cards = [
            Card(suit, rank) 
            for suit in Suit 
            for rank in Rank
        ]
    
    def shuffle(self) -> None:
        """洗牌。"""
        self._rng.shuffle(self._cards)
    
    def deal_card(self) -> Card:
        """
        发一张牌。
        
        Returns:
            发出的牌
            
        Raises:
            IndexError: 如果牌堆为空
        """
        if not self._cards:
            raise IndexError("Cannot deal from empty deck")
        return self._cards.pop()
    
    def deal_cards(self, count: int) -> List[Card]:
        """
        发多张牌。
        
        Args:
            count: 要发的牌数
            
        Returns:
            发出的牌列表
            
        Raises:
            ValueError: 如果要发的牌数超过剩余牌数
        """
        if count < 0:
            raise ValueError("Count must be non-negative")
        if count > len(self._cards):
            raise ValueError(f"Cannot deal {count} cards, only {len(self._cards)} remaining")
        
        dealt_cards = []
        for _ in range(count):
            dealt_cards.append(self.deal_card())
        return dealt_cards
    
    def cards_remaining(self) -> int:
        """
        返回剩余牌数。
        
        Returns:
            剩余的牌数
        """
        return len(self._cards)
    
    def is_empty(self) -> bool:
        """
        检查牌堆是否为空。
        
        Returns:
            如果牌堆为空则返回True
        """
        return len(self._cards) == 0
    
    def reset(self) -> None:
        """重置牌堆为完整的52张牌（未洗牌）。"""
        self._reset_deck()
    
    def peek_top(self) -> Optional[Card]:
        """
        查看顶部的牌但不发出。
        
        Returns:
            顶部的牌，如果牌堆为空则返回None
        """
        return self._cards[-1] if self._cards else None
    
    def __len__(self) -> int:
        """返回牌堆中的牌数。"""
        return len(self._cards)
    
    def __str__(self) -> str:
        """返回牌堆的字符串表示。"""
        return f"Deck({len(self._cards)} cards)"
    
    def __repr__(self) -> str:
        """返回牌堆的详细表示。"""
        return f"Deck(cards_remaining={len(self._cards)})" 