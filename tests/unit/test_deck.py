#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
牌堆(Deck)类单元测试
测试牌堆初始化、洗牌、发牌、重置等功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_game_logic.core.deck import Deck
from core_game_logic.core.card import Card, CardPool
from core_game_logic.core.enums import Suit, Rank


class TestDeck:
    """牌组类测试"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.deck = Deck()
    
    def test_deck_initialization(self):
        """测试牌组初始化"""
        print("测试牌组初始化...")
        
        # 测试默认初始化
        deck = Deck()
        assert deck.remaining_count == 52, "新牌组应该有52张牌"
        assert not deck.is_empty, "新牌组不应该为空"
        assert len(deck) == 52, "__len__方法应该返回52"
        
        # 测试带种子的初始化
        deck_with_seed = Deck(seed=42)
        assert deck_with_seed.remaining_count == 52, "带种子的牌组也应该有52张牌"
        
        print("[OK] 牌组初始化测试通过")
    
    def test_deck_reset(self):
        """测试牌组重置功能"""
        print("测试牌组重置功能...")
        
        # 发几张牌
        self.deck.deal_cards(10)
        assert self.deck.remaining_count == 42, "发牌后应该剩余42张"
        
        # 重置牌组
        self.deck.reset()
        assert self.deck.remaining_count == 52, "重置后应该恢复到52张"
        assert not self.deck.is_empty, "重置后不应该为空"
        
        print("[OK] 牌组重置功能测试通过")
    
    def test_shuffle_reproducibility(self):
        """测试洗牌的可重现性"""
        print("测试洗牌的可重现性...")
        
        # 使用相同种子的两个牌组
        deck1 = Deck(seed=123)
        deck2 = Deck(seed=123)
        
        deck1.shuffle()
        deck2.shuffle()
        
        # 发牌顺序应该相同
        for i in range(10):
            card1 = deck1.deal_card()
            card2 = deck2.deal_card()
            assert card1.rank == card2.rank and card1.suit == card2.suit, f"第{i+1}张牌应该相同"
        
        print("[OK] 洗牌可重现性测试通过")
    
    def test_shuffle_randomness(self):
        """测试洗牌的随机性"""
        print("测试洗牌的随机性...")
        
        # 创建两个不同种子的牌组
        deck1 = Deck(seed=123)
        deck2 = Deck(seed=456)
        
        deck1.shuffle()
        deck2.shuffle()
        
        # 发前10张牌，应该有不同
        cards1 = deck1.deal_cards(10)
        cards2 = deck2.deal_cards(10)
        
        # 至少应该有一些不同的牌
        different_count = 0
        for i in range(10):
            if cards1[i].rank != cards2[i].rank or cards1[i].suit != cards2[i].suit:
                different_count += 1
        
        assert different_count > 0, "不同种子的洗牌结果应该有差异"
        
        print("[OK] 洗牌随机性测试通过")
    
    def test_deal_single_card(self):
        """测试发单张牌"""
        print("测试发单张牌...")
        
        initial_count = self.deck.remaining_count
        card = self.deck.deal_card()
        
        # 验证返回的是Card对象
        assert isinstance(card, Card), "应该返回Card对象"
        assert card.rank in Rank, "牌的点数应该有效"
        assert card.suit in Suit, "牌的花色应该有效"
        
        # 验证牌组数量减少
        assert self.deck.remaining_count == initial_count - 1, "发牌后数量应该减1"
        
        print("[OK] 发单张牌测试通过")
    
    def test_deal_multiple_cards(self):
        """测试发多张牌"""
        print("测试发多张牌...")
        
        initial_count = self.deck.remaining_count
        cards = self.deck.deal_cards(5)
        
        # 验证返回的牌数
        assert len(cards) == 5, "应该返回5张牌"
        assert self.deck.remaining_count == initial_count - 5, "发牌后数量应该减5"
        
        # 验证每张牌都是有效的
        for card in cards:
            assert isinstance(card, Card), "每张牌都应该是Card对象"
        
        # 验证没有重复的牌
        card_strs = [card.to_str() for card in cards]
        assert len(set(card_strs)) == 5, "发出的牌不应该重复"
        
        print("[OK] 发多张牌测试通过")
    
    def test_peek_functionality(self):
        """测试查看功能"""
        print("测试查看功能...")
        
        # 查看顶部牌
        top_card = self.deck.peek_top_card()
        assert isinstance(top_card, Card), "应该返回Card对象"
        
        # 查看后牌组数量不变
        initial_count = self.deck.remaining_count
        assert self.deck.remaining_count == initial_count, "查看后数量不应该变化"
        
        # 查看的牌应该和实际发出的牌相同
        dealt_card = self.deck.deal_card()
        assert top_card.rank == dealt_card.rank and top_card.suit == dealt_card.suit, "查看的牌应该和发出的牌相同"
        
        # 测试查看多张牌
        self.deck.reset()
        peek_cards = self.deck.peek_cards(3)
        assert len(peek_cards) == 3, "应该查看到3张牌"
        
        dealt_cards = self.deck.deal_cards(3)
        # peek_cards返回的是[-3:]，即倒数3张，顺序是从倒数第3张到最后一张
        # deal_cards是从最后一张开始pop，所以顺序是相反的
        for i in range(3):
            peek_idx = len(peek_cards) - 1 - i  # 从peek_cards的最后一张开始比较
            assert peek_cards[peek_idx].rank == dealt_cards[i].rank and peek_cards[peek_idx].suit == dealt_cards[i].suit, f"第{i+1}张查看的牌应该匹配"
        
        print("[OK] 查看功能测试通过")
    
    def test_empty_deck_exceptions(self):
        """测试空牌组异常处理"""
        print("测试空牌组异常处理...")
        
        # 发完所有牌
        self.deck.deal_cards(52)
        assert self.deck.is_empty, "发完所有牌后应该为空"
        assert self.deck.remaining_count == 0, "剩余数量应该为0"
        
        # 尝试从空牌组发牌应该抛出异常
        try:
            self.deck.deal_card()
            assert False, "从空牌组发牌应该抛出异常"
        except ValueError as e:
            assert "牌组已空" in str(e), "异常信息应该包含'牌组已空'"
        
        # 尝试发多张牌也应该抛出异常
        try:
            self.deck.deal_cards(1)
            assert False, "从空牌组发多张牌应该抛出异常"
        except ValueError as e:
            assert "牌组中只有0张牌" in str(e), "异常信息应该正确"
        
        # 查看空牌组应该返回None
        assert self.deck.peek_top_card() is None, "查看空牌组应该返回None"
        
        print("[OK] 空牌组异常处理测试通过")
    
    def test_invalid_operations(self):
        """测试无效操作"""
        print("测试无效操作...")
        
        # 尝试发超过剩余数量的牌
        try:
            self.deck.deal_cards(53)  # 超过52张
            assert False, "发超过剩余数量的牌应该抛出异常"
        except ValueError as e:
            assert "无法发53张" in str(e), "异常信息应该正确"
        
        # 尝试查看超过剩余数量的牌
        try:
            self.deck.peek_cards(53)
            assert False, "查看超过剩余数量的牌应该抛出异常"
        except ValueError as e:
            assert "无法查看53张" in str(e), "异常信息应该正确"
        
        print("[OK] 无效操作测试通过")
    
    def test_string_representations(self):
        """测试字符串表示"""
        print("测试字符串表示...")
        
        # 测试__str__方法
        str_repr = str(self.deck)
        assert "牌组剩余: 52 张" in str_repr, "__str__应该包含剩余牌数"
        
        # 测试__repr__方法
        repr_str = repr(self.deck)
        assert "Deck(remaining=52)" in repr_str, "__repr__应该包含调试信息"
        
        # 发几张牌后再测试
        self.deck.deal_cards(10)
        str_repr = str(self.deck)
        assert "牌组剩余: 42 张" in str_repr, "发牌后字符串表示应该更新"
        
        print("[OK] 字符串表示测试通过")


def run_tests():
    """运行所有测试"""
    print("=== 牌组(Deck)类单元测试 ===\n")
    
    test_instance = TestDeck()
    
    test_methods = [
        ("牌组初始化", test_instance.test_deck_initialization),
        ("牌组重置功能", test_instance.test_deck_reset),
        ("洗牌可重现性", test_instance.test_shuffle_reproducibility),
        ("洗牌随机性", test_instance.test_shuffle_randomness),
        ("发单张牌", test_instance.test_deal_single_card),
        ("发多张牌", test_instance.test_deal_multiple_cards),
        ("查看功能", test_instance.test_peek_functionality),
        ("空牌组异常处理", test_instance.test_empty_deck_exceptions),
        ("无效操作", test_instance.test_invalid_operations),
        ("字符串表示", test_instance.test_string_representations),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in test_methods:
        try:
            test_instance.setup_method()
            test_func()
            print(f"[OK] {test_name}测试通过\n")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test_name}测试失败: {e}\n")
            failed += 1
    
    print(f"测试结果: {passed}通过, {failed}失败")
    
    if failed == 0:
        print("[SUCCESS] 所有Deck单元测试通过！")
        return True
    else:
        print("[ERROR] 部分测试失败，需要修复")
        return False


if __name__ == "__main__":
    run_tests() 