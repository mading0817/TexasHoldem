"""
德州扑克牌型评估器.

提供牌型识别、比较和评估功能，支持标准的德州扑克规则.
从v2迁移并增强了类型安全和错误处理.
"""

from collections import Counter
from itertools import combinations
from typing import List, Tuple

from ..deck.card import Card
from ..deck.types import Rank, Suit
from .types import HandRank, HandResult


class HandEvaluator:
    """
    德州扑克牌型评估器.
    
    实现标准的德州扑克牌型识别和比较算法.
    支持从7张牌中找出最佳5张牌组合.
    
    Examples:
        >>> evaluator = HandEvaluator()
        >>> hole_cards = [Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.ACE)]
        >>> community_cards = [Card(Suit.HEARTS, Rank.KING), ...]
        >>> result = evaluator.evaluate_hand(hole_cards, community_cards)
        >>> result.rank
        <HandRank.ONE_PAIR: 2>
    """

    def evaluate_hand(self, hole_cards: List[Card], community_cards: List[Card]) -> HandResult:
        """
        评估给定牌的最佳牌型.
        
        Args:
            hole_cards: 玩家手牌（必须是2张）
            community_cards: 公共牌（最多5张）
            
        Returns:
            HandResult: 最佳牌型的评估结果
            
        Raises:
            TypeError: 当输入参数类型无效时
            ValueError: 当牌数不符合要求时
        """
        # 类型检查
        if not isinstance(hole_cards, list):
            raise TypeError(f"手牌必须是列表类型，实际: {type(hole_cards)}")
        if not isinstance(community_cards, list):
            raise TypeError(f"公共牌必须是列表类型，实际: {type(community_cards)}")
        
        # 验证手牌数量
        if len(hole_cards) != 2:
            raise ValueError(f"手牌必须是2张，实际: {len(hole_cards)}")
        
        # 验证公共牌数量
        if len(community_cards) > 5:
            raise ValueError(f"公共牌不能超过5张，实际: {len(community_cards)}")
        
        # 验证所有牌都是Card类型
        all_cards = hole_cards + community_cards
        for i, card in enumerate(all_cards):
            if not isinstance(card, Card):
                raise TypeError(f"第{i}张牌必须是Card类型，实际: {type(card)}")
        
        # 验证总牌数
        if len(all_cards) < 5:
            raise ValueError(f"总牌数不足5张，无法评估: {len(all_cards)}")
        
        # 从所有牌中找出最佳5张牌组合
        return self._find_best_hand(all_cards)

    def compare_hands(self, hand1: HandResult, hand2: HandResult) -> int:
        """
        比较两个牌型的强弱.
        
        Args:
            hand1: 第一个牌型
            hand2: 第二个牌型
            
        Returns:
            int: 1表示hand1更强，-1表示hand2更强，0表示相等
            
        Raises:
            TypeError: 当输入参数类型无效时
        """
        if not isinstance(hand1, HandResult):
            raise TypeError(f"hand1必须是HandResult类型，实际: {type(hand1)}")
        if not isinstance(hand2, HandResult):
            raise TypeError(f"hand2必须是HandResult类型，实际: {type(hand2)}")
        
        return hand1.compare_to(hand2)

    def _find_best_hand(self, cards: List[Card]) -> HandResult:
        """
        从给定牌中找出最佳的5张牌组合.
        
        Args:
            cards: 候选牌列表（5-7张）
            
        Returns:
            HandResult: 最佳牌型的评估结果
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
        评估恰好5张牌的牌型.
        
        Args:
            cards: 恰好5张牌的列表
            
        Returns:
            HandResult: 牌型评估结果
        """
        if len(cards) != 5:
            raise ValueError(f"必须是5张牌，实际: {len(cards)}")
        
        # 按点数降序排序
        sorted_cards = sorted(cards, key=lambda c: c.rank.value, reverse=True)
        ranks = [card.rank.value for card in sorted_cards]
        suits = [card.suit for card in sorted_cards]
        
        # 统计点数出现次数
        rank_counts = Counter(ranks)
        count_groups = Counter(rank_counts.values())
        
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
            return HandResult(HandRank.FOUR_OF_A_KIND, four_rank, 0, (kicker,))
        
        if count_groups[3] == 1 and count_groups[2] == 1:  # 葫芦
            three_rank = self._get_rank_with_count(rank_counts, 3)
            pair_rank = self._get_rank_with_count(rank_counts, 2)
            return HandResult(HandRank.FULL_HOUSE, three_rank, pair_rank)
        
        if is_flush:  # 同花
            return HandResult(HandRank.FLUSH, ranks[0], 0, tuple(ranks[1:]))
        
        if is_straight:  # 顺子
            return HandResult(HandRank.STRAIGHT, straight_high)
        
        if count_groups[3] == 1:  # 三条
            three_rank = self._get_rank_with_count(rank_counts, 3)
            kickers = tuple(sorted([r for r in ranks if rank_counts[r] == 1], reverse=True))
            return HandResult(HandRank.THREE_OF_A_KIND, three_rank, 0, kickers)
        
        if count_groups[2] == 2:  # 两对
            pairs = sorted([rank for rank, count in rank_counts.items() if count == 2], reverse=True)
            kicker = self._get_rank_with_count(rank_counts, 1)
            return HandResult(HandRank.TWO_PAIR, pairs[0], pairs[1], (kicker,))
        
        if count_groups[2] == 1:  # 一对
            pair_rank = self._get_rank_with_count(rank_counts, 2)
            kickers = tuple(sorted([r for r in ranks if rank_counts[r] == 1], reverse=True))
            return HandResult(HandRank.ONE_PAIR, pair_rank, 0, kickers)
        
        # 高牌
        return HandResult(HandRank.HIGH_CARD, ranks[0], 0, tuple(ranks[1:]))

    def _check_straight(self, ranks: List[int]) -> Tuple[bool, int]:
        """
        检查是否为顺子.
        
        Args:
            ranks: 按降序排列的点数列表
            
        Returns:
            Tuple[bool, int]: (是否为顺子, 顺子的最高牌)
        """
        # 去重并排序
        unique_ranks = sorted(set(ranks), reverse=True)
        
        # 检查标准顺子
        for i in range(len(unique_ranks) - 4):
            if unique_ranks[i] - unique_ranks[i + 4] == 4:
                return True, unique_ranks[i]
        
        # 检查A-2-3-4-5的特殊顺子
        if set(unique_ranks) >= {14, 5, 4, 3, 2}:
            return True, 5  # A-2-3-4-5顺子的最高牌是5
        
        return False, 0

    def _get_rank_with_count(self, rank_counts: Counter, count: int) -> int:
        """
        获取出现指定次数的点数.
        
        Args:
            rank_counts: 点数计数器
            count: 指定的出现次数
            
        Returns:
            int: 出现指定次数的点数
            
        Raises:
            ValueError: 当找不到指定次数的点数时
        """
        for rank, rank_count in rank_counts.items():
            if rank_count == count:
                return rank
        raise ValueError(f"找不到出现{count}次的点数") 