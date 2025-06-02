#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
v2牌型评估器单元测试。

测试各种牌型识别、排名比较、胜负判断等功能。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from v2.core.cards import Card
from v2.core.enums import Rank, Suit, HandRank
from v2.core.evaluator import SimpleEvaluator, HandResult


class TestSimpleEvaluator:
    """简单牌型评估器测试类。"""
    
    def setup_method(self):
        """每个测试方法前的设置。"""
        self.evaluator = SimpleEvaluator()
    
    def _create_cards(self, card_strs: list) -> list:
        """从字符串列表创建卡牌列表。
        
        Args:
            card_strs: 卡牌字符串列表，如["As", "Kh"]
            
        Returns:
            Card对象列表
        """
        return [Card.from_str(s) for s in card_strs]
    
    def test_high_card(self):
        """测试高牌识别。"""
        hole_cards = self._create_cards(["As", "Kh"])
        community_cards = self._create_cards(["Qd", "Js", "9c"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.HIGH_CARD
        assert result.primary_value == 14  # A
        assert result.kickers == (13, 12, 11, 9)  # K, Q, J, 9
    
    def test_one_pair(self):
        """测试一对识别。"""
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Kd", "Qs", "Jc"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.ONE_PAIR
        assert result.primary_value == 14  # 一对A
        assert result.kickers == (13, 12, 11)  # K, Q, J
    
    def test_two_pair(self):
        """测试两对识别。"""
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Kd", "Ks", "Qc"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.TWO_PAIR
        assert result.primary_value == 14  # 大对A
        assert result.secondary_value == 13  # 小对K
        assert result.kickers == (12,)  # Q
    
    def test_three_of_a_kind(self):
        """测试三条识别。"""
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Ad", "Ks", "Qc"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.THREE_OF_A_KIND
        assert result.primary_value == 14  # 三条A
        assert result.kickers == (13, 12)  # K, Q
    
    def test_straight(self):
        """测试顺子识别。"""
        hole_cards = self._create_cards(["As", "Kh"])
        community_cards = self._create_cards(["Qd", "Js", "10c"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.STRAIGHT
        assert result.primary_value == 14  # A高顺子
    
    def test_straight_wheel(self):
        """测试A-2-3-4-5顺子（轮子）。"""
        hole_cards = self._create_cards(["As", "2h"])
        community_cards = self._create_cards(["3d", "4s", "5c"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.STRAIGHT
        assert result.primary_value == 5  # 轮子以5为高牌
    
    def test_flush(self):
        """测试同花识别。"""
        hole_cards = self._create_cards(["As", "Ks"])
        community_cards = self._create_cards(["Qs", "Js", "9s"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.FLUSH
        assert result.primary_value == 14  # A高同花
        assert result.kickers == (13, 12, 11, 9)  # K, Q, J, 9
    
    def test_full_house(self):
        """测试葫芦识别。"""
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Ad", "Ks", "Kc"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.FULL_HOUSE
        assert result.primary_value == 14  # 三条A
        assert result.secondary_value == 13  # 一对K
    
    def test_four_of_a_kind(self):
        """测试四条识别。"""
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Ad", "Ac", "Ks"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.FOUR_OF_A_KIND
        assert result.primary_value == 14  # 四条A
        assert result.kickers == (13,)  # K
    
    def test_straight_flush(self):
        """测试同花顺识别。"""
        hole_cards = self._create_cards(["9s", "8s"])
        community_cards = self._create_cards(["7s", "6s", "5s"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.STRAIGHT_FLUSH
        assert result.primary_value == 9  # 9高同花顺
    
    def test_royal_flush(self):
        """测试皇家同花顺识别。"""
        hole_cards = self._create_cards(["As", "Ks"])
        community_cards = self._create_cards(["Qs", "Js", "10s"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 注意：A-K-Q-J-10同花顺应该被识别为皇家同花顺
        assert result.rank == HandRank.ROYAL_FLUSH
        assert result.primary_value == 14  # A高皇家同花顺
    
    def test_seven_cards_best_hand(self):
        """测试从7张牌中选择最佳5张。"""
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Ad", "Ac", "Ks", "Qd", "Jh"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 应该选择四条A + K，而不是葫芦
        assert result.rank == HandRank.FOUR_OF_A_KIND
        assert result.primary_value == 14
        assert result.kickers == (13,)
    
    def test_hand_comparison(self):
        """测试牌型比较。"""
        # 四条 vs 葫芦
        four_kind = HandResult(HandRank.FOUR_OF_A_KIND, 10, kickers=(5,))
        full_house = HandResult(HandRank.FULL_HOUSE, 14, 13)
        
        assert four_kind.compare_to(full_house) > 0
        assert full_house.compare_to(four_kind) < 0
        
        # 相同牌型比较主要牌值
        pair_aces = HandResult(HandRank.ONE_PAIR, 14, kickers=(13, 12, 11))
        pair_kings = HandResult(HandRank.ONE_PAIR, 13, kickers=(14, 12, 11))
        
        assert pair_aces.compare_to(pair_kings) > 0
        
        # 相同牌型和主要牌值，比较踢脚牌
        pair_aces_k = HandResult(HandRank.ONE_PAIR, 14, kickers=(13, 12, 11))
        pair_aces_q = HandResult(HandRank.ONE_PAIR, 14, kickers=(12, 11, 10))
        
        assert pair_aces_k.compare_to(pair_aces_q) > 0
        
        # 完全相同
        pair1 = HandResult(HandRank.ONE_PAIR, 14, kickers=(13, 12, 11))
        pair2 = HandResult(HandRank.ONE_PAIR, 14, kickers=(13, 12, 11))
        
        assert pair1.compare_to(pair2) == 0
    
    def test_invalid_inputs(self):
        """测试无效输入处理。"""
        # 手牌不是2张
        with pytest.raises(ValueError, match="手牌必须是2张"):
            self.evaluator.evaluate_hand([Card.from_str("As")], [Card.from_str("Kh")])
        
        # 总牌数不足5张
        with pytest.raises(ValueError, match="总牌数不足5张"):
            self.evaluator.evaluate_hand(
                [Card.from_str("As"), Card.from_str("Kh")],
                [Card.from_str("Qd"), Card.from_str("Js")]
            )
        
        # 公共牌超过5张
        with pytest.raises(ValueError, match="公共牌不能超过5张"):
            self.evaluator.evaluate_hand(
                [Card.from_str("As"), Card.from_str("Kh")],
                [Card.from_str(s) for s in ["Qd", "Js", "10c", "9h", "8s", "7d"]]
            )
    
    def test_edge_cases(self):
        """测试边界情况。"""
        # 测试多个相同点数的情况
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Ad", "Ac", "Ks"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        assert result.rank == HandRank.FOUR_OF_A_KIND
        
        # 测试同花但不是同花顺
        hole_cards = self._create_cards(["As", "Ks"])
        community_cards = self._create_cards(["Qs", "Js", "9s"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        assert result.rank == HandRank.FLUSH
        
        # 测试顺子但不是同花
        hole_cards = self._create_cards(["As", "Kh"])
        community_cards = self._create_cards(["Qd", "Js", "10c"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        assert result.rank == HandRank.STRAIGHT
    
    def test_hand_result_str(self):
        """测试HandResult的字符串表示。"""
        # 测试一对
        pair = HandResult(HandRank.ONE_PAIR, 14, kickers=(13, 12, 11))
        assert "一对" in str(pair)
        assert "ACE" in str(pair)
        
        # 测试两对
        two_pair = HandResult(HandRank.TWO_PAIR, 14, 13, kickers=(12,))
        assert "两对" in str(two_pair)
        assert "ACE" in str(two_pair)
        assert "KING" in str(two_pair)
        
        # 测试同花顺
        straight_flush = HandResult(HandRank.STRAIGHT_FLUSH, 14)
        assert "同花顺" in str(straight_flush)
        assert "ACE" in str(straight_flush)


def test_card_from_str():
    """测试Card.from_str方法。"""
    # 测试基本功能
    card = Card.from_str("As")
    assert card.rank == Rank.ACE
    assert card.suit == Suit.SPADES
    
    # 测试10的处理
    card = Card.from_str("10h")
    assert card.rank == Rank.TEN
    assert card.suit == Suit.HEARTS
    
    # 测试T的处理
    card = Card.from_str("Th")
    assert card.rank == Rank.TEN
    assert card.suit == Suit.HEARTS
    
    # 测试无效输入
    with pytest.raises(ValueError):
        Card.from_str("X")
    
    with pytest.raises(ValueError):
        Card.from_str("Az")  # 无效花色


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 