"""
牌组类的实现
包含洗牌、发牌和可重现随机性支持
"""

import random
from typing import List, Optional
from .card import Card, CardPool


class Deck:
    """
    德州扑克牌组类
    管理52张牌的洗牌、发牌等操作
    """

    def __init__(self, seed: Optional[int] = None):
        """
        初始化牌组
        
        Args:
            seed: 随机种子，用于可重现的洗牌结果
        """
        self._cards: List[Card] = []
        self._random = random.Random(seed) if seed is not None else random.Random()
        self.reset()

    def reset(self):
        """
        重置牌组，重新加载所有52张牌
        牌组将恢复到未洗牌状态
        """
        self._cards = CardPool.get_all_cards().copy()

    def shuffle(self, seed: Optional[int] = None):
        """
        洗牌操作
        
        Args:
            seed: 可选的随机种子，如果提供则使用新种子
        """
        if seed is not None:
            self._random = random.Random(seed)
        
        self._random.shuffle(self._cards)

    def deal_card(self) -> Card:
        """
        发一张牌
        
        Returns:
            发出的卡牌
            
        Raises:
            ValueError: 当牌组为空时
        """
        if not self._cards:
            raise ValueError("牌组已空，无法发牌")
        
        return self._cards.pop()

    def deal_cards(self, count: int) -> List[Card]:
        """
        发多张牌
        
        Args:
            count: 要发的牌数
            
        Returns:
            发出的卡牌列表
            
        Raises:
            ValueError: 当牌组中的牌不足时
        """
        if count > len(self._cards):
            raise ValueError(f"牌组中只有{len(self._cards)}张牌，无法发{count}张")
        
        cards = []
        for _ in range(count):
            cards.append(self.deal_card())
        
        return cards

    @property
    def remaining_count(self) -> int:
        """返回牌组中剩余的牌数"""
        return len(self._cards)

    @property
    def is_empty(self) -> bool:
        """检查牌组是否为空"""
        return len(self._cards) == 0

    def peek_top_card(self) -> Optional[Card]:
        """
        查看顶部卡牌但不发出
        
        Returns:
            顶部卡牌，如果牌组为空则返回None
        """
        return self._cards[-1] if self._cards else None

    def peek_cards(self, count: int) -> List[Card]:
        """
        查看顶部多张卡牌但不发出
        
        Args:
            count: 要查看的牌数
            
        Returns:
            顶部的卡牌列表
            
        Raises:
            ValueError: 当牌组中的牌不足时
        """
        if count > len(self._cards):
            raise ValueError(f"牌组中只有{len(self._cards)}张牌，无法查看{count}张")
        
        return self._cards[-count:].copy()

    def __len__(self) -> int:
        """返回牌组中的牌数"""
        return len(self._cards)

    def __repr__(self) -> str:
        """返回牌组的调试表示"""
        return f"Deck(remaining={len(self._cards)})"

    def __str__(self) -> str:
        """返回牌组的可读表示"""
        return f"牌组剩余: {len(self._cards)} 张" 