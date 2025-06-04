"""
扑克牌组管理.

定义Deck类，提供标准52张牌的管理功能，包括洗牌、发牌等操作.
"""

import random
from typing import List, Optional

from .card import Card
from .types import Suit, Rank, get_all_suits, get_all_ranks


class Deck:
    """
    表示一副扑克牌.
    
    包含52张标准扑克牌，支持洗牌、发牌等操作.
    使用可选的随机数生成器以支持确定性测试.
    
    Attributes:
        _cards: 当前牌组中的牌列表
        _rng: 随机数生成器
        
    Examples:
        >>> deck = Deck()
        >>> deck.shuffle()
        >>> card = deck.deal_card()
        >>> len(deck)
        51
    """

    def __init__(self, rng: Optional[random.Random] = None) -> None:
        """
        初始化牌组.
        
        Args:
            rng: 随机数生成器，用于洗牌操作。如果为None，使用默认随机数生成器
        """
        self._rng = rng or random.Random()
        self._cards: List[Card] = []
        self._reset_deck()
    
    def _reset_deck(self) -> None:
        """重置牌组为完整的52张牌."""
        self._cards = [
            Card(suit, rank) 
            for suit in get_all_suits()
            for rank in get_all_ranks()
        ]
    
    def shuffle(self) -> None:
        """
        洗牌.
        
        使用Fisher-Yates洗牌算法随机打乱牌的顺序.
        """
        self._rng.shuffle(self._cards)
    
    def deal_card(self) -> Card:
        """
        发一张牌.
        
        Returns:
            Card: 发出的牌
            
        Raises:
            IndexError: 当牌组为空时
        """
        if not self._cards:
            raise IndexError("Cannot deal from empty deck")
        return self._cards.pop()
    
    def deal_cards(self, count: int) -> List[Card]:
        """
        发多张牌.
        
        Args:
            count: 要发的牌数
            
        Returns:
            List[Card]: 发出的牌列表
            
        Raises:
            ValueError: 当count为负数时
            IndexError: 当牌组中的牌不足时
        """
        if count < 0:
            raise ValueError("Count must be non-negative")
        if count > len(self._cards):
            raise IndexError(f"Cannot deal {count} cards, only {len(self._cards)} remaining")
        
        dealt_cards = []
        for _ in range(count):
            dealt_cards.append(self.deal_card())
        return dealt_cards
    
    @property
    def cards_remaining(self) -> int:
        """
        获取剩余牌数.
        
        Returns:
            int: 牌组中剩余的牌数
        """
        return len(self._cards)
    
    @property
    def is_empty(self) -> bool:
        """
        检查牌组是否为空.
        
        Returns:
            bool: 如果牌组为空则返回True
        """
        return len(self._cards) == 0
    
    def reset(self) -> None:
        """重置牌组为完整的52张牌."""
        self._reset_deck()
    
    def peek_top(self) -> Optional[Card]:
        """
        查看顶部的牌但不发出.
        
        Returns:
            Optional[Card]: 顶部的牌，如果牌组为空则返回None
        """
        if not self._cards:
            return None
        return self._cards[-1]
    
    def __len__(self) -> int:
        """
        返回牌组中剩余的牌数.
        
        Returns:
            int: 剩余牌数
        """
        return len(self._cards)
    
    def __str__(self) -> str:
        """
        返回牌组的字符串表示.
        
        Returns:
            str: 包含剩余牌数的描述
        """
        return f"Deck({len(self._cards)} cards remaining)"
    
    def __repr__(self) -> str:
        """
        返回牌组的详细字符串表示.
        
        Returns:
            str: 包含类名和剩余牌数的详细描述
        """
        return f"Deck(cards_remaining={len(self._cards)})" 