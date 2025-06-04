"""
德州扑克牌组和评估器模块的集成测试.

测试Deck和HandEvaluator的集成使用场景，模拟真实游戏流程.
包含反作弊验证，确保测试使用真实的核心模块.
"""

import pytest
import random
from typing import List, Tuple

from v3.core.deck import Card, Deck
from v3.core.deck.types import Suit, Rank
from v3.core.eval import HandEvaluator, HandRank, HandResult
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestDeckEvalIntegration:
    """Deck和HandEvaluator集成测试."""

    def test_complete_hand_evaluation_workflow(self):
        """测试完整的手牌评估工作流程."""
        deck = Deck()
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        # 模拟发牌和评估流程
        deck.shuffle()
        
        # 发手牌
        hole_cards = deck.deal_cards(2)
        assert len(hole_cards) == 2
        
        # 发公共牌
        community_cards = deck.deal_cards(5)
        assert len(community_cards) == 5
        
        # 评估手牌
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        # 验证结果
        assert isinstance(result.rank, HandRank)
        assert result.primary_value > 0
        assert len(deck) == 45  # 52 - 7 = 45

    def test_multiple_players_evaluation(self):
        """测试多玩家手牌评估."""
        deck = Deck()
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        deck.shuffle()
        
        # 模拟4个玩家
        players_hands = []
        for i in range(4):
            hole_cards = deck.deal_cards(2)
            players_hands.append(hole_cards)
        
        # 发公共牌
        community_cards = deck.deal_cards(5)
        
        # 评估所有玩家的手牌
        results = []
        for i, hole_cards in enumerate(players_hands):
            result = evaluator.evaluate_hand(hole_cards, community_cards)
            CoreUsageChecker.verify_real_objects(result, "HandResult")
            results.append(result)
        
        # 验证所有结果
        assert len(results) == 4
        for result in results:
            assert isinstance(result.rank, HandRank)
        
        # 验证剩余牌数
        assert len(deck) == 39  # 52 - 8 - 5 = 39

    def test_hand_comparison_workflow(self):
        """测试手牌比较工作流程."""
        deck = Deck()
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        deck.shuffle()
        
        # 两个玩家的手牌
        player1_hole = deck.deal_cards(2)
        player2_hole = deck.deal_cards(2)
        community_cards = deck.deal_cards(5)
        
        # 评估两个玩家的手牌
        result1 = evaluator.evaluate_hand(player1_hole, community_cards)
        result2 = evaluator.evaluate_hand(player2_hole, community_cards)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(result1, "HandResult")
        CoreUsageChecker.verify_real_objects(result2, "HandResult")
        
        # 比较手牌
        comparison = evaluator.compare_hands(result1, result2)
        
        # 验证比较结果
        assert comparison in [-1, 0, 1]
        
        # 验证比较的一致性
        reverse_comparison = evaluator.compare_hands(result2, result1)
        assert comparison == -reverse_comparison

    def test_edge_case_evaluations(self):
        """测试边缘情况的评估."""
        deck = Deck()
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        # 测试最少公共牌的情况（0张公共牌，应该失败）
        deck.shuffle()
        hole_cards = deck.deal_cards(2)
        
        with pytest.raises(ValueError):
            evaluator.evaluate_hand(hole_cards, [])
        
        # 测试部分公共牌的情况
        deck.reset()
        deck.shuffle()
        hole_cards = deck.deal_cards(2)
        community_cards = deck.deal_cards(3)  # 只有3张公共牌
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        assert isinstance(result.rank, HandRank)

    def test_specific_hand_scenarios(self):
        """测试特定的手牌场景."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        # 测试皇家同花顺
        hole_cards = [Card(Suit.HEARTS, Rank.ACE), Card(Suit.HEARTS, Rank.KING)]
        community_cards = [
            Card(Suit.HEARTS, Rank.QUEEN),
            Card(Suit.HEARTS, Rank.JACK),
            Card(Suit.HEARTS, Rank.TEN),
            Card(Suit.SPADES, Rank.TWO),
            Card(Suit.CLUBS, Rank.THREE)
        ]
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        assert result.rank == HandRank.ROYAL_FLUSH
        
        # 测试高牌
        hole_cards = [Card(Suit.HEARTS, Rank.TWO), Card(Suit.SPADES, Rank.FOUR)]
        community_cards = [
            Card(Suit.DIAMONDS, Rank.SIX),
            Card(Suit.CLUBS, Rank.EIGHT),
            Card(Suit.HEARTS, Rank.TEN),
            Card(Suit.SPADES, Rank.QUEEN),
            Card(Suit.DIAMONDS, Rank.ACE)
        ]
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        assert result.rank == HandRank.HIGH_CARD
        assert result.primary_value == 14  # ACE

    def test_deck_state_consistency(self):
        """测试牌组状态的一致性."""
        deck = Deck()
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        initial_count = len(deck)
        assert initial_count == 52
        
        # 记录发出的牌
        dealt_cards = []
        
        # 发多轮牌
        for round_num in range(3):
            hole_cards = deck.deal_cards(2)
            community_cards = deck.deal_cards(5)
            
            dealt_cards.extend(hole_cards)
            dealt_cards.extend(community_cards)
            
            # 评估手牌
            result = evaluator.evaluate_hand(hole_cards, community_cards)
            CoreUsageChecker.verify_real_objects(result, "HandResult")
            
            # 验证牌组状态
            expected_remaining = initial_count - len(dealt_cards)
            assert len(deck) == expected_remaining
        
        # 验证没有重复的牌
        card_strings = [str(card) for card in dealt_cards]
        assert len(card_strings) == len(set(card_strings))

    def test_random_game_simulation(self):
        """测试随机游戏模拟."""
        deck = Deck()
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        # 模拟100局游戏
        for game_num in range(100):
            deck.reset()
            deck.shuffle()
            
            # 随机2-6个玩家
            num_players = random.randint(2, 6)
            players_results = []
            
            # 发手牌
            for player in range(num_players):
                hole_cards = deck.deal_cards(2)
                community_cards = deck.deal_cards(5)
                
                result = evaluator.evaluate_hand(hole_cards, community_cards)
                CoreUsageChecker.verify_real_objects(result, "HandResult")
                players_results.append(result)
                
                # 重置牌组为下一个玩家
                deck.reset()
                deck.shuffle()
            
            # 验证所有结果都有效
            for result in players_results:
                assert isinstance(result.rank, HandRank)
                assert result.primary_value >= 2  # 最小值是2

    def test_performance_integration(self):
        """测试集成性能."""
        import time
        
        deck = Deck()
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        # 测试100次完整的发牌和评估流程
        start_time = time.perf_counter()
        
        for _ in range(100):
            deck.reset()
            deck.shuffle()
            
            hole_cards = deck.deal_cards(2)
            community_cards = deck.deal_cards(5)
            result = evaluator.evaluate_hand(hole_cards, community_cards)
            
            # 确保结果被使用
            assert result is not None
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # 100次完整流程应该在1秒内完成
        assert total_time < 1.0, f"100次完整流程时间过长: {total_time:.6f}秒"
        
        avg_time = total_time / 100
        print(f"平均每次完整流程时间: {avg_time*1000:.3f}毫秒") 