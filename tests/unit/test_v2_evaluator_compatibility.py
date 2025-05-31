#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
v2评估器与v1评估器兼容性测试。

使用原有测试数据集验证v2评估器与v1评估器的结果一致性。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
import random
from typing import List

# v1 imports
from core_game_logic.core.card import Card as V1Card
from core_game_logic.evaluator.simple_evaluator import SimpleEvaluator as V1Evaluator
from core_game_logic.evaluator.hand_rank import HandRank as V1HandRank

# v2 imports
from v2.core.cards import Card as V2Card
from v2.core.evaluator import SimpleEvaluator as V2Evaluator
from v2.core.enums import HandRank as V2HandRank


class TestEvaluatorCompatibility:
    """评估器兼容性测试类。"""
    
    def setup_method(self):
        """每个测试方法前的设置。"""
        self.v1_evaluator = V1Evaluator()
        self.v2_evaluator = V2Evaluator()
        
        # 枚举映射表
        self.v1_to_v2_rank_map = {
            V1HandRank.HIGH_CARD: V2HandRank.HIGH_CARD,
            V1HandRank.ONE_PAIR: V2HandRank.ONE_PAIR,
            V1HandRank.TWO_PAIR: V2HandRank.TWO_PAIR,
            V1HandRank.THREE_KIND: V2HandRank.THREE_OF_A_KIND,
            V1HandRank.STRAIGHT: V2HandRank.STRAIGHT,
            V1HandRank.FLUSH: V2HandRank.FLUSH,
            V1HandRank.FULL_HOUSE: V2HandRank.FULL_HOUSE,
            V1HandRank.FOUR_KIND: V2HandRank.FOUR_OF_A_KIND,
            V1HandRank.STRAIGHT_FLUSH: V2HandRank.STRAIGHT_FLUSH,
        }
    
    def _convert_v1_to_v2_cards(self, v1_cards: List[V1Card]) -> List[V2Card]:
        """将v1的Card对象转换为v2的Card对象。
        
        Args:
            v1_cards: v1的Card对象列表
            
        Returns:
            v2的Card对象列表
        """
        v2_cards = []
        for v1_card in v1_cards:
            card_str = v1_card.to_str()
            v2_card = V2Card.from_str(card_str)
            v2_cards.append(v2_card)
        return v2_cards
    
    def _compare_hand_results(self, v1_result, v2_result) -> bool:
        """比较v1和v2的评估结果是否一致。
        
        Args:
            v1_result: v1的HandResult
            v2_result: v2的HandResult
            
        Returns:
            是否一致
        """
        # 映射v1的牌型到v2
        expected_v2_rank = self.v1_to_v2_rank_map.get(v1_result.rank)
        
        # 特殊处理：v1没有ROYAL_FLUSH，但v2有
        if (v1_result.rank == V1HandRank.STRAIGHT_FLUSH and 
            v1_result.primary_value == 14 and 
            v2_result.rank == V2HandRank.ROYAL_FLUSH):
            expected_v2_rank = V2HandRank.ROYAL_FLUSH
        
        if v2_result.rank != expected_v2_rank:
            return False
        
        # 比较主要牌值
        if v1_result.primary_value != v2_result.primary_value:
            return False
        
        # 比较次要牌值
        if v1_result.secondary_value != v2_result.secondary_value:
            return False
        
        # 比较踢脚牌
        if v1_result.kickers != v2_result.kickers:
            return False
        
        return True
    
    def test_known_hands(self):
        """测试已知的牌型组合。"""
        test_cases = [
            # (hole_cards, community_cards, expected_rank_name)
            (["As", "Ah"], ["Kd", "Qs", "Jc"], "ONE_PAIR"),
            (["As", "Ah"], ["Kd", "Ks", "Qc"], "TWO_PAIR"),
            (["As", "Ah"], ["Ad", "Ks", "Qc"], "THREE_KIND"),
            (["As", "Kh"], ["Qd", "Js", "Tc"], "STRAIGHT"),
            (["As", "Ks"], ["Qs", "Js", "9s"], "FLUSH"),
            (["As", "Ah"], ["Ad", "Ks", "Kc"], "FULL_HOUSE"),
            (["As", "Ah"], ["Ad", "Ac", "Ks"], "FOUR_KIND"),
            (["9s", "8s"], ["7s", "6s", "5s"], "STRAIGHT_FLUSH"),
            (["As", "2h"], ["3d", "4s", "5c"], "STRAIGHT"),  # 轮子
        ]
        
        for hole_strs, community_strs, expected_rank in test_cases:
            # 创建v1卡牌
            v1_hole = [V1Card.from_str(s) for s in hole_strs]
            v1_community = [V1Card.from_str(s) for s in community_strs]
            
            # 创建v2卡牌
            v2_hole = [V2Card.from_str(s) for s in hole_strs]
            v2_community = [V2Card.from_str(s) for s in community_strs]
            
            # 评估
            v1_result = self.v1_evaluator.evaluate_hand(v1_hole, v1_community)
            v2_result = self.v2_evaluator.evaluate_hand(v2_hole, v2_community)
            
            # 验证一致性
            assert self._compare_hand_results(v1_result, v2_result), \
                f"不一致的结果: {hole_strs} + {community_strs}\n" \
                f"v1: {v1_result.rank.name}({v1_result.primary_value}, {v1_result.secondary_value}, {v1_result.kickers})\n" \
                f"v2: {v2_result.rank.name}({v2_result.primary_value}, {v2_result.secondary_value}, {v2_result.kickers})"
    
    def test_random_hands(self):
        """测试随机生成的牌型组合。"""
        # 创建一副完整的牌
        all_cards_v1 = []
        all_cards_v2 = []
        
        suits = ["h", "d", "c", "s"]
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
        
        for suit in suits:
            for rank in ranks:
                card_str = f"{rank}{suit}"
                all_cards_v1.append(V1Card.from_str(card_str))
                all_cards_v2.append(V2Card.from_str(card_str))
        
        # 测试100组随机7张牌
        random.seed(42)  # 固定种子确保可重现
        
        for i in range(100):
            # 随机选择7张牌
            indices = random.sample(range(52), 7)
            
            v1_cards = [all_cards_v1[idx] for idx in indices]
            v2_cards = [all_cards_v2[idx] for idx in indices]
            
            v1_hole = v1_cards[:2]
            v1_community = v1_cards[2:]
            
            v2_hole = v2_cards[:2]
            v2_community = v2_cards[2:]
            
            # 评估
            v1_result = self.v1_evaluator.evaluate_hand(v1_hole, v1_community)
            v2_result = self.v2_evaluator.evaluate_hand(v2_hole, v2_community)
            
            # 验证一致性
            assert self._compare_hand_results(v1_result, v2_result), \
                f"随机测试 #{i} 不一致:\n" \
                f"牌: {[c.to_str() for c in v1_cards]}\n" \
                f"v1: {v1_result.rank.name}({v1_result.primary_value}, {v1_result.secondary_value}, {v1_result.kickers})\n" \
                f"v2: {v2_result.rank.name}({v2_result.primary_value}, {v2_result.secondary_value}, {v2_result.kickers})"
    
    def test_hand_comparison_consistency(self):
        """测试牌型比较的一致性。"""
        test_hands = [
            (["As", "Ah"], ["Kd", "Qs", "Jc"]),  # 一对A
            (["Ks", "Kh"], ["Ad", "Qs", "Jc"]),  # 一对K
            (["As", "Ah"], ["Kd", "Ks", "Qc"]),  # 两对A和K
            (["Qs", "Qh"], ["Kd", "Ks", "Ac"]),  # 两对K和Q
            (["As", "Ah"], ["Ad", "Ks", "Qc"]),  # 三条A
        ]
        
        # 评估所有手牌
        v1_results = []
        v2_results = []
        
        for hole_strs, community_strs in test_hands:
            v1_hole = [V1Card.from_str(s) for s in hole_strs]
            v1_community = [V1Card.from_str(s) for s in community_strs]
            v1_result = self.v1_evaluator.evaluate_hand(v1_hole, v1_community)
            v1_results.append(v1_result)
            
            v2_hole = [V2Card.from_str(s) for s in hole_strs]
            v2_community = [V2Card.from_str(s) for s in community_strs]
            v2_result = self.v2_evaluator.evaluate_hand(v2_hole, v2_community)
            v2_results.append(v2_result)
        
        # 比较所有手牌对
        for i in range(len(v1_results)):
            for j in range(len(v1_results)):
                if i != j:
                    v1_cmp = v1_results[i].compare_to(v1_results[j])
                    v2_cmp = v2_results[i].compare_to(v2_results[j])
                    
                    # 比较结果应该一致（符号相同）
                    assert (v1_cmp > 0) == (v2_cmp > 0), \
                        f"比较不一致: hand{i} vs hand{j}\n" \
                        f"v1: {v1_cmp}, v2: {v2_cmp}"
                    assert (v1_cmp < 0) == (v2_cmp < 0), \
                        f"比较不一致: hand{i} vs hand{j}\n" \
                        f"v1: {v1_cmp}, v2: {v2_cmp}"
                    assert (v1_cmp == 0) == (v2_cmp == 0), \
                        f"比较不一致: hand{i} vs hand{j}\n" \
                        f"v1: {v1_cmp}, v2: {v2_cmp}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 