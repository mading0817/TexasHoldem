"""
德州扑克牌型评估器。

提供牌型识别、比较和评估功能，使用直观的算法实现。
"""

from dataclasses import dataclass
from typing import List, Tuple, Counter
from collections import Counter as CollectionsCounter
from itertools import combinations

from .cards import Card
from .enums import Rank, Suit, HandRank


@dataclass(frozen=True)
class HandResult:
    """
    牌型评估结果。
    
    包含牌型等级和用于比较的关键牌值。
    
    Attributes:
        rank: 牌型等级
        primary_value: 主要牌值（如对子的点数）
        secondary_value: 次要牌值（如两对中较小的对子）
        kickers: 踢脚牌（按大小降序排列）
    """
    rank: HandRank
    primary_value: int
    secondary_value: int = 0
    kickers: Tuple[int, ...] = ()

    def __post_init__(self):
        """验证结果数据的有效性。
        
        Raises:
            ValueError: 如果牌型等级或牌值无效
        """
        if not isinstance(self.rank, HandRank):
            raise ValueError(f"无效的牌型等级: {self.rank}")
        
        if self.primary_value < 2 or self.primary_value > 14:
            raise ValueError(f"无效的主要牌值: {self.primary_value}")

    def compare_to(self, other: 'HandResult') -> int:
        """
        比较两个牌型结果。
        
        Args:
            other: 另一个牌型结果
            
        Returns:
            1 if self > other, -1 if self < other, 0 if equal
        """
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
        """返回牌型的可读描述。
        
        Returns:
            牌型的中文描述字符串
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


class SimpleEvaluator:
    """
    简单牌型评估器。
    
    使用直观的算法实现所有牌型识别，易于理解和调试。
    """

    def evaluate_hand(self, hole_cards: List[Card], community_cards: List[Card]) -> HandResult:
        """
        评估7张牌中的最佳5张牌组合。
        
        Args:
            hole_cards: 玩家手牌（2张）
            community_cards: 公共牌（最多5张）
            
        Returns:
            最佳牌型结果
            
        Raises:
            ValueError: 如果输入牌数不符合要求
        """
        if len(hole_cards) != 2:
            raise ValueError(f"手牌必须是2张，实际: {len(hole_cards)}")
        
        if len(community_cards) > 5:
            raise ValueError(f"公共牌不能超过5张，实际: {len(community_cards)}")
        
        all_cards = hole_cards + community_cards
        if len(all_cards) < 5:
            raise ValueError(f"总牌数不足5张，无法评估: {len(all_cards)}")
        
        # 从所有牌中找出最佳5张牌组合
        return self._find_best_hand(all_cards)

    def _find_best_hand(self, cards: List[Card]) -> HandResult:
        """
        从给定牌中找出最佳5张牌组合。
        
        Args:
            cards: 所有可用的牌
            
        Returns:
            最佳牌型结果
        """
        if len(cards) == 5:
            return self._evaluate_five_cards(cards)
        
        # 如果超过5张牌，尝试所有5张牌的组合
        best_result = None
        for five_cards in combinations(cards, 5):
            result = self._evaluate_five_cards(list(five_cards))
            if best_result is None or result.compare_to(best_result) > 0:
                best_result = result
        
        return best_result

    def _evaluate_five_cards(self, cards: List[Card]) -> HandResult:
        """
        评估恰好5张牌的牌型。
        
        Args:
            cards: 恰好5张牌
            
        Returns:
            牌型结果
            
        Raises:
            ValueError: 如果不是恰好5张牌
        """
        if len(cards) != 5:
            raise ValueError(f"必须是5张牌，实际: {len(cards)}")
        
        # 按点数降序排序
        sorted_cards = sorted(cards, key=lambda c: c.rank.value, reverse=True)
        ranks = [card.rank.value for card in sorted_cards]
        suits = [card.suit for card in sorted_cards]
        
        # 统计点数出现次数
        rank_counts = CollectionsCounter(ranks)
        count_groups = CollectionsCounter(rank_counts.values())
        
        # 检查是否为同花
        is_flush = len(set(suits)) == 1
        
        # 检查是否为顺子
        is_straight, straight_high = self._check_straight(ranks)
        
        # 按优先级检查各种牌型
        if is_straight and is_flush:
            # 检查是否为皇家同花顺
            if straight_high == 14 and set(ranks) == {14, 13, 12, 11, 10}:
                return HandResult(HandRank.ROYAL_FLUSH, straight_high)
            return HandResult(HandRank.STRAIGHT_FLUSH, straight_high)
        
        if count_groups[4] == 1:  # 四条
            four_rank = self._get_rank_with_count(rank_counts, 4)
            kicker = self._get_rank_with_count(rank_counts, 1)
            return HandResult(HandRank.FOUR_OF_A_KIND, four_rank, kickers=(kicker,))
        
        if count_groups[3] == 1 and count_groups[2] == 1:  # 葫芦
            three_rank = self._get_rank_with_count(rank_counts, 3)
            pair_rank = self._get_rank_with_count(rank_counts, 2)
            return HandResult(HandRank.FULL_HOUSE, three_rank, pair_rank)
        
        if is_flush:
            return HandResult(HandRank.FLUSH, ranks[0], kickers=tuple(ranks[1:]))
        
        if is_straight:
            return HandResult(HandRank.STRAIGHT, straight_high)
        
        if count_groups[3] == 1:  # 三条
            three_rank = self._get_rank_with_count(rank_counts, 3)
            kickers = tuple(sorted([r for r in ranks if r != three_rank], reverse=True))
            return HandResult(HandRank.THREE_OF_A_KIND, three_rank, kickers=kickers)
        
        if count_groups[2] == 2:  # 两对
            pairs = sorted([r for r, c in rank_counts.items() if c == 2], reverse=True)
            kicker = self._get_rank_with_count(rank_counts, 1)
            return HandResult(HandRank.TWO_PAIR, pairs[0], pairs[1], kickers=(kicker,))
        
        if count_groups[2] == 1:  # 一对
            pair_rank = self._get_rank_with_count(rank_counts, 2)
            kickers = tuple(sorted([r for r in ranks if r != pair_rank], reverse=True))
            return HandResult(HandRank.ONE_PAIR, pair_rank, kickers=kickers)
        
        # 高牌
        return HandResult(HandRank.HIGH_CARD, ranks[0], kickers=tuple(ranks[1:]))

    def _check_straight(self, ranks: List[int]) -> Tuple[bool, int]:
        """
        检查是否为顺子。
        
        Args:
            ranks: 按降序排列的点数列表
            
        Returns:
            (是否为顺子, 顺子的最高牌)
        """
        # 去重并排序
        unique_ranks = sorted(set(ranks), reverse=True)
        
        if len(unique_ranks) < 5:
            return False, 0
        
        # 检查普通顺子
        for i in range(len(unique_ranks) - 4):
            if unique_ranks[i] - unique_ranks[i + 4] == 4:
                return True, unique_ranks[i]
        
        # 检查A-2-3-4-5的特殊顺子
        if set(unique_ranks[:5]) == {14, 5, 4, 3, 2}:
            return True, 5  # A-2-3-4-5顺子以5为高牌
        
        return False, 0

    def _get_rank_with_count(self, rank_counts: Counter, count: int) -> int:
        """
        获取出现指定次数的点数。
        
        Args:
            rank_counts: 点数计数器
            count: 目标出现次数
            
        Returns:
            符合条件的点数
            
        Raises:
            ValueError: 如果未找到符合条件的点数
        """
        for rank, cnt in rank_counts.items():
            if cnt == count:
                return rank
        raise ValueError(f"未找到出现{count}次的点数")

    def compare_hands(self, hand1: HandResult, hand2: HandResult) -> int:
        """
        比较两个牌型。
        
        Args:
            hand1: 第一个牌型
            hand2: 第二个牌型
            
        Returns:
            1 if hand1 > hand2, -1 if hand1 < hand2, 0 if equal
        """
        return hand1.compare_to(hand2) 