#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
牌力评估器(HandEvaluator)类单元测试
测试各种牌型识别、排名比较、胜负判断等功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_game_logic.core.card import Card
from core_game_logic.core.enums import Rank, Suit
from core_game_logic.evaluator.hand_rank import HandRank
from core_game_logic.evaluator.simple_evaluator import SimpleEvaluator, HandResult


class TestSimpleEvaluator:
    """简单牌型评估器测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.evaluator = SimpleEvaluator()
    
    def _create_cards(self, card_strs: list) -> list:
        """从字符串列表创建卡牌列表"""
        return [Card.from_str(s) for s in card_strs]
    
    def test_high_card(self):
        """测试高牌识别"""
        hole_cards = self._create_cards(["As", "Kh"])
        community_cards = self._create_cards(["Qd", "Js", "9c"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.HIGH_CARD
        assert result.primary_value == 14  # A
        assert result.kickers == (13, 12, 11, 9)  # K, Q, J, 9
    
    def test_one_pair(self):
        """测试一对识别"""
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Kd", "Qs", "Jc"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.ONE_PAIR
        assert result.primary_value == 14  # 一对A
        assert result.kickers == (13, 12, 11)  # K, Q, J
    
    def test_two_pair(self):
        """测试两对识别"""
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Kd", "Ks", "Qc"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.TWO_PAIR
        assert result.primary_value == 14  # 大对A
        assert result.secondary_value == 13  # 小对K
        assert result.kickers == (12,)  # Q
    
    def test_three_kind(self):
        """测试三条识别"""
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Ad", "Ks", "Qc"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.THREE_KIND
        assert result.primary_value == 14  # 三条A
        assert result.kickers == (13, 12)  # K, Q
    
    def test_straight(self):
        """测试顺子识别"""
        hole_cards = self._create_cards(["As", "Kh"])
        community_cards = self._create_cards(["Qd", "Js", "Tc"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.STRAIGHT
        assert result.primary_value == 14  # A高顺子
    
    def test_straight_wheel(self):
        """测试A-2-3-4-5顺子（轮子）"""
        hole_cards = self._create_cards(["As", "2h"])
        community_cards = self._create_cards(["3d", "4s", "5c"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.STRAIGHT
        assert result.primary_value == 5  # 轮子以5为高牌
    
    def test_flush(self):
        """测试同花识别"""
        hole_cards = self._create_cards(["As", "Ks"])
        community_cards = self._create_cards(["Qs", "Js", "9s"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.FLUSH
        assert result.primary_value == 14  # A高同花
        assert result.kickers == (13, 12, 11, 9)  # K, Q, J, 9
    
    def test_full_house(self):
        """测试葫芦识别"""
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Ad", "Ks", "Kc"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.FULL_HOUSE
        assert result.primary_value == 14  # 三条A
        assert result.secondary_value == 13  # 一对K
    
    def test_four_kind(self):
        """测试四条识别"""
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Ad", "Ac", "Ks"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.FOUR_KIND
        assert result.primary_value == 14  # 四条A
        assert result.kickers == (13,)  # K
    
    def test_straight_flush(self):
        """测试同花顺识别"""
        hole_cards = self._create_cards(["As", "Ks"])
        community_cards = self._create_cards(["Qs", "Js", "Ts"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert result.rank == HandRank.STRAIGHT_FLUSH
        assert result.primary_value == 14  # A高同花顺
    
    def test_seven_cards_best_hand(self):
        """测试从7张牌中选择最佳5张"""
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Ad", "Ac", "Ks", "Qd", "Jh"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 应该选择四条A + K，而不是葫芦
        assert result.rank == HandRank.FOUR_KIND
        assert result.primary_value == 14
        assert result.kickers == (13,)
    
    def test_hand_comparison(self):
        """测试牌型比较"""
        # 四条 vs 葫芦
        four_kind = HandResult(HandRank.FOUR_KIND, 10, kickers=(5,))
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
        """测试无效输入处理"""
        # 手牌不是2张
        try:
            self.evaluator.evaluate_hand([Card.from_str("As")], [Card.from_str("Kh")])
            assert False, "应该抛出ValueError"
        except ValueError:
            pass
        
        # 总牌数不足5张
        try:
            self.evaluator.evaluate_hand(
                [Card.from_str("As"), Card.from_str("Kh")],
                [Card.from_str("Qd"), Card.from_str("Js")]
            )
            assert False, "应该抛出ValueError"
        except ValueError:
            pass
        
        # 公共牌超过5张
        try:
            self.evaluator.evaluate_hand(
                [Card.from_str("As"), Card.from_str("Kh")],
                [Card.from_str(s) for s in ["Qd", "Js", "Tc", "9h", "8s", "7d"]]
            )
            assert False, "应该抛出ValueError"
        except ValueError:
            pass
    
    def test_edge_cases(self):
        """测试边界情况"""
        # 测试多个相同点数的情况
        hole_cards = self._create_cards(["As", "Ah"])
        community_cards = self._create_cards(["Ad", "Ac", "Ks"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        assert result.rank == HandRank.FOUR_KIND
        
        # 测试同花但不是同花顺
        hole_cards = self._create_cards(["As", "Ks"])
        community_cards = self._create_cards(["Qs", "Js", "9s"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        assert result.rank == HandRank.FLUSH
        
        # 测试顺子但不是同花
        hole_cards = self._create_cards(["As", "Kh"])
        community_cards = self._create_cards(["Qd", "Js", "Tc"])
        
        result = self.evaluator.evaluate_hand(hole_cards, community_cards)
        assert result.rank == HandRank.STRAIGHT


def main():
    """运行测试"""
    print("=== 牌型评估器测试 ===\n")
    
    # 创建测试实例
    test_instance = TestSimpleEvaluator()
    test_instance.setup_method()
    
    # 运行所有测试
    test_methods = [
        ("高牌识别", test_instance.test_high_card),
        ("一对识别", test_instance.test_one_pair),
        ("两对识别", test_instance.test_two_pair),
        ("三条识别", test_instance.test_three_kind),
        ("顺子识别", test_instance.test_straight),
        ("轮子顺子识别", test_instance.test_straight_wheel),
        ("同花识别", test_instance.test_flush),
        ("葫芦识别", test_instance.test_full_house),
        ("四条识别", test_instance.test_four_kind),
        ("同花顺识别", test_instance.test_straight_flush),
        ("7张牌最佳组合", test_instance.test_seven_cards_best_hand),
        ("牌型比较", test_instance.test_hand_comparison),
        ("无效输入处理", test_instance.test_invalid_inputs),
        ("边界情况", test_instance.test_edge_cases),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in test_methods:
        try:
            test_func()
            print(f"[OK] {test_name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test_name}: {e}")
            failed += 1
    
    print(f"\n测试结果: {passed}通过, {failed}失败")
    
    if failed == 0:
        print("[SUCCESS] 所有牌型评估器测试通过！")
        return True
    else:
        print("[ERROR] 部分测试失败，需要修复")
        return False


if __name__ == "__main__":
    main() 