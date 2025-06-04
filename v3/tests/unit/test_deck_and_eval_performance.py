"""
德州扑克牌组和评估器模块的性能测试.

测试HandEvaluator的性能，确保满足游戏需求.
包含反作弊验证，确保测试使用真实的核心模块.
"""

import pytest
import time
import random
from typing import List

from v3.core.deck import Card, Deck
from v3.core.deck.types import Suit, Rank
from v3.core.eval import HandEvaluator, HandRank, HandResult
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestHandEvaluatorPerformance:
    """HandEvaluator性能测试."""

    def test_single_evaluation_performance(self):
        """测试单次评估性能."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        # 创建测试手牌（2张手牌 + 3张公共牌）
        hole_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.ACE)
        ]
        community_cards = [
            Card(Suit.DIAMONDS, Rank.KING),
            Card(Suit.CLUBS, Rank.KING),
            Card(Suit.HEARTS, Rank.QUEEN)
        ]
        
        # 测试单次评估时间
        start_time = time.perf_counter()
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        end_time = time.perf_counter()
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        # 单次评估应该在1毫秒内完成
        evaluation_time = end_time - start_time
        assert evaluation_time < 0.001, f"单次评估时间过长: {evaluation_time:.6f}秒"
        
        # 验证结果正确性
        assert result.rank == HandRank.TWO_PAIR

    def test_batch_evaluation_performance(self):
        """测试批量评估性能."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        # 生成1000个随机手牌组合
        deck = Deck()
        test_hands = []
        
        for _ in range(1000):
            deck.reset()
            deck.shuffle()
            all_cards = deck.deal_cards(7)  # 发7张牌
            hole_cards = all_cards[:2]      # 前2张作为手牌
            community_cards = all_cards[2:] # 后5张作为公共牌
            test_hands.append((hole_cards, community_cards))
        
        # 测试批量评估时间
        start_time = time.perf_counter()
        results = []
        for hole_cards, community_cards in test_hands:
            result = evaluator.evaluate_hand(hole_cards, community_cards)
            results.append(result)
        end_time = time.perf_counter()
        
        # 验证所有结果
        assert len(results) == 1000
        for result in results:
            CoreUsageChecker.verify_real_objects(result, "HandResult")
            assert isinstance(result.rank, HandRank)
        
        # 1000次评估应该在1秒内完成（平均每次1毫秒）
        total_time = end_time - start_time
        assert total_time < 1.0, f"1000次评估时间过长: {total_time:.6f}秒"
        
        # 计算平均每次评估时间
        avg_time = total_time / 1000
        print(f"平均每次评估时间: {avg_time*1000:.3f}毫秒")

    def test_all_hand_types_performance(self):
        """测试所有牌型的评估性能."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        # 定义各种牌型的测试用例（手牌 + 公共牌）
        test_cases = [
            # 皇家同花顺
            ([Card(Suit.HEARTS, Rank.ACE), Card(Suit.HEARTS, Rank.KING)],
             [Card(Suit.HEARTS, Rank.QUEEN), Card(Suit.HEARTS, Rank.JACK), Card(Suit.HEARTS, Rank.TEN)]),
            
            # 同花顺
            ([Card(Suit.SPADES, Rank.NINE), Card(Suit.SPADES, Rank.EIGHT)],
             [Card(Suit.SPADES, Rank.SEVEN), Card(Suit.SPADES, Rank.SIX), Card(Suit.SPADES, Rank.FIVE)]),
            
            # 四条
            ([Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.ACE)],
             [Card(Suit.DIAMONDS, Rank.ACE), Card(Suit.CLUBS, Rank.ACE), Card(Suit.HEARTS, Rank.KING)]),
            
            # 葫芦
            ([Card(Suit.HEARTS, Rank.KING), Card(Suit.SPADES, Rank.KING)],
             [Card(Suit.DIAMONDS, Rank.KING), Card(Suit.CLUBS, Rank.QUEEN), Card(Suit.HEARTS, Rank.QUEEN)]),
            
            # 同花
            ([Card(Suit.HEARTS, Rank.ACE), Card(Suit.HEARTS, Rank.JACK)],
             [Card(Suit.HEARTS, Rank.NINE), Card(Suit.HEARTS, Rank.SEVEN), Card(Suit.HEARTS, Rank.FIVE)]),
            
            # 顺子
            ([Card(Suit.HEARTS, Rank.TEN), Card(Suit.SPADES, Rank.NINE)],
             [Card(Suit.DIAMONDS, Rank.EIGHT), Card(Suit.CLUBS, Rank.SEVEN), Card(Suit.HEARTS, Rank.SIX)]),
            
            # 三条
            ([Card(Suit.HEARTS, Rank.KING), Card(Suit.SPADES, Rank.KING)],
             [Card(Suit.DIAMONDS, Rank.KING), Card(Suit.CLUBS, Rank.QUEEN), Card(Suit.HEARTS, Rank.JACK)]),
            
            # 两对
            ([Card(Suit.HEARTS, Rank.KING), Card(Suit.SPADES, Rank.KING)],
             [Card(Suit.DIAMONDS, Rank.QUEEN), Card(Suit.CLUBS, Rank.QUEEN), Card(Suit.HEARTS, Rank.JACK)]),
            
            # 一对
            ([Card(Suit.HEARTS, Rank.KING), Card(Suit.SPADES, Rank.KING)],
             [Card(Suit.DIAMONDS, Rank.QUEEN), Card(Suit.CLUBS, Rank.JACK), Card(Suit.HEARTS, Rank.TEN)]),
            
            # 高牌
            ([Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.JACK)],
             [Card(Suit.DIAMONDS, Rank.NINE), Card(Suit.CLUBS, Rank.SEVEN), Card(Suit.HEARTS, Rank.FIVE)])
        ]
        
        # 测试每种牌型的评估时间
        for i, (hole_cards, community_cards) in enumerate(test_cases):
            start_time = time.perf_counter()
            result = evaluator.evaluate_hand(hole_cards, community_cards)
            end_time = time.perf_counter()
            
            # 反作弊检查
            CoreUsageChecker.verify_real_objects(result, "HandResult")
            
            evaluation_time = end_time - start_time
            assert evaluation_time < 0.001, f"牌型{i}评估时间过长: {evaluation_time:.6f}秒"

    def test_comparison_performance(self):
        """测试手牌比较性能."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        # 创建两个测试手牌
        hole_cards1 = [Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.ACE)]
        community_cards1 = [Card(Suit.DIAMONDS, Rank.KING), Card(Suit.CLUBS, Rank.KING), Card(Suit.HEARTS, Rank.QUEEN)]
        
        hole_cards2 = [Card(Suit.HEARTS, Rank.KING), Card(Suit.SPADES, Rank.KING)]
        community_cards2 = [Card(Suit.DIAMONDS, Rank.QUEEN), Card(Suit.CLUBS, Rank.QUEEN), Card(Suit.HEARTS, Rank.JACK)]
        
        # 先评估两个手牌
        result1 = evaluator.evaluate_hand(hole_cards1, community_cards1)
        result2 = evaluator.evaluate_hand(hole_cards2, community_cards2)
        
        # 测试1000次比较的时间
        start_time = time.perf_counter()
        for _ in range(1000):
            comparison = evaluator.compare_hands(result1, result2)
        end_time = time.perf_counter()
        
        # 1000次比较应该在50毫秒内完成
        total_time = end_time - start_time
        assert total_time < 0.05, f"1000次比较时间过长: {total_time:.6f}秒"
        
        # 计算平均每次比较时间
        avg_time = total_time / 1000
        print(f"平均每次比较时间: {avg_time*1000:.3f}毫秒")

    @pytest.mark.benchmark
    def test_benchmark_evaluation(self, benchmark):
        """使用pytest-benchmark进行基准测试."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        # 创建测试手牌
        hole_cards = [Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.ACE)]
        community_cards = [Card(Suit.DIAMONDS, Rank.KING), Card(Suit.CLUBS, Rank.KING), Card(Suit.HEARTS, Rank.QUEEN)]
        
        # 基准测试
        result = benchmark(evaluator.evaluate_hand, hole_cards, community_cards)
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        # 验证结果正确性
        assert result.rank == HandRank.TWO_PAIR

    def test_memory_usage(self):
        """测试内存使用情况."""
        import gc
        import sys
        
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        # 记录初始内存使用
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # 执行大量评估
        deck = Deck()
        for _ in range(1000):
            deck.reset()
            deck.shuffle()
            all_cards = deck.deal_cards(7)
            hole_cards = all_cards[:2]
            community_cards = all_cards[2:]
            result = evaluator.evaluate_hand(hole_cards, community_cards)
            # 确保结果被使用，防止优化
            assert result is not None
        
        # 检查内存使用
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # 内存增长应该在合理范围内（允许一些临时对象）
        memory_growth = final_objects - initial_objects
        assert memory_growth < 1000, f"内存增长过多: {memory_growth}个对象" 