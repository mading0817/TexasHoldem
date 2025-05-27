#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
卡牌(Card)和卡牌池(CardPool)类单元测试
测试卡牌创建、对象池、字符串转换等功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core_game_logic.core.card import Card, CardPool
from core_game_logic.core.enums import Suit, Rank


class TestCard:
    """卡牌类测试"""
    
    def test_card_creation(self):
        """测试卡牌创建"""
        print("测试卡牌创建...")
        
        # 测试正常创建
        card = Card(Rank.ACE, Suit.SPADES)
        assert card.rank == Rank.ACE, "点数应该正确"
        assert card.suit == Suit.SPADES, "花色应该正确"
        
        # 测试不可变性
        try:
            card.rank = Rank.KING  # 尝试修改应该失败
            assert False, "卡牌应该是不可变的"
        except AttributeError:
            pass  # 预期的异常
        
        print("✓ 卡牌创建测试通过")
    
    def test_card_string_conversion(self):
        """测试卡牌字符串转换"""
        print("测试卡牌字符串转换...")
        
        # 测试to_str方法
        card = Card(Rank.ACE, Suit.SPADES)
        assert card.to_str() == "As", "黑桃A应该是As"
        
        card = Card(Rank.KING, Suit.HEARTS)
        assert card.to_str() == "Kh", "红桃K应该是Kh"
        
        card = Card(Rank.TEN, Suit.DIAMONDS)
        assert card.to_str() == "Td", "方块10应该是Td"
        
        card = Card(Rank.TWO, Suit.CLUBS)
        assert card.to_str() == "2c", "梅花2应该是2c"
        
        # 测试from_str方法
        card = Card.from_str("As")
        assert card.rank == Rank.ACE and card.suit == Suit.SPADES, "应该能解析As"
        
        card = Card.from_str("Kh")
        assert card.rank == Rank.KING and card.suit == Suit.HEARTS, "应该能解析Kh"
        
        card = Card.from_str("Td")
        assert card.rank == Rank.TEN and card.suit == Suit.DIAMONDS, "应该能解析Td"
        
        card = Card.from_str("2c")
        assert card.rank == Rank.TWO and card.suit == Suit.CLUBS, "应该能解析2c"
        
        print("✓ 卡牌字符串转换测试通过")
    
    def test_card_string_representations(self):
        """测试卡牌字符串表示"""
        print("测试卡牌字符串表示...")
        
        card = Card(Rank.ACE, Suit.SPADES)
        
        # 测试__str__方法
        assert str(card) == "As", "__str__应该返回简短格式"
        
        # 测试__repr__方法
        repr_str = repr(card)
        assert "Card" in repr_str, "__repr__应该包含类名"
        assert "ACE" in repr_str, "__repr__应该包含点数"
        assert "SPADES" in repr_str, "__repr__应该包含花色"
        
        print("✓ 卡牌字符串表示测试通过")
    
    def test_card_validation(self):
        """测试卡牌验证"""
        print("测试卡牌验证...")
        
        # 测试无效点数
        try:
            Card(None, Suit.SPADES)
            assert False, "无效点数应该抛出异常"
        except (ValueError, TypeError):
            pass
        
        # 测试无效花色
        try:
            Card(Rank.ACE, None)
            assert False, "无效花色应该抛出异常"
        except (ValueError, TypeError):
            pass
        
        # 测试无效字符串格式
        try:
            Card.from_str("XX")
            assert False, "无效字符串应该抛出异常"
        except ValueError:
            pass
        
        try:
            Card.from_str("A")  # 缺少花色
            assert False, "不完整字符串应该抛出异常"
        except ValueError:
            pass
        
        print("✓ 卡牌验证测试通过")


class TestCardPool:
    """卡牌池测试"""
    
    def test_card_pool_singleton(self):
        """测试卡牌池单例模式"""
        print("测试卡牌池单例模式...")
        
        # 测试相同卡牌返回同一对象
        card1 = CardPool.get_card(Rank.ACE, Suit.SPADES)
        card2 = CardPool.get_card(Rank.ACE, Suit.SPADES)
        assert card1 is card2, "相同卡牌应该返回同一对象"
        
        # 测试不同卡牌返回不同对象
        card3 = CardPool.get_card(Rank.KING, Suit.HEARTS)
        assert card1 is not card3, "不同卡牌应该返回不同对象"
        
        print("✓ 卡牌池单例模式测试通过")
    
    def test_card_pool_from_string(self):
        """测试卡牌池字符串创建"""
        print("测试卡牌池字符串创建...")
        
        # 测试from_str方法
        card1 = CardPool.from_str("As")
        card2 = CardPool.from_str("As")
        assert card1 is card2, "相同字符串应该返回同一对象"
        
        # 验证卡牌内容正确
        assert card1.rank == Rank.ACE, "点数应该正确"
        assert card1.suit == Suit.SPADES, "花色应该正确"
        
        print("✓ 卡牌池字符串创建测试通过")
    
    def test_card_pool_all_cards(self):
        """测试卡牌池所有卡牌"""
        print("测试卡牌池所有卡牌...")
        
        # 获取所有卡牌
        all_cards = CardPool.get_all_cards()
        assert len(all_cards) == 52, "应该有52张卡牌"
        
        # 验证没有重复
        card_strs = [card.to_str() for card in all_cards]
        assert len(set(card_strs)) == 52, "所有卡牌应该不重复"
        
        # 验证包含所有花色和点数的组合
        suits = set()
        ranks = set()
        for card in all_cards:
            suits.add(card.suit)
            ranks.add(card.rank)
        
        assert len(suits) == 4, "应该包含4种花色"
        assert len(ranks) == 13, "应该包含13种点数"
        
        print("✓ 卡牌池所有卡牌测试通过")
    
    def test_card_pool_reset(self):
        """测试卡牌池重置"""
        print("测试卡牌池重置...")
        
        # 获取一张卡牌
        card_before = CardPool.get_card(Rank.ACE, Suit.SPADES)
        
        # 重置卡牌池
        CardPool.reset()
        
        # 重新获取相同卡牌
        card_after = CardPool.get_card(Rank.ACE, Suit.SPADES)
        
        # 重置后应该是不同的对象
        assert card_before is not card_after, "重置后应该创建新对象"
        
        # 但内容应该相同
        assert card_before.rank == card_after.rank, "点数应该相同"
        assert card_before.suit == card_after.suit, "花色应该相同"
        
        print("✓ 卡牌池重置测试通过")


def run_tests():
    """运行所有测试"""
    print("=== 卡牌和卡牌池单元测试 ===\n")
    
    card_test = TestCard()
    pool_test = TestCardPool()
    
    test_methods = [
        ("卡牌创建", card_test.test_card_creation),
        ("卡牌字符串转换", card_test.test_card_string_conversion),
        ("卡牌字符串表示", card_test.test_card_string_representations),
        ("卡牌验证", card_test.test_card_validation),
        ("卡牌池单例模式", pool_test.test_card_pool_singleton),
        ("卡牌池字符串创建", pool_test.test_card_pool_from_string),
        ("卡牌池所有卡牌", pool_test.test_card_pool_all_cards),
        ("卡牌池重置", pool_test.test_card_pool_reset),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in test_methods:
        try:
            test_func()
            print(f"✓ {test_name}测试通过\n")
            passed += 1
        except Exception as e:
            print(f"✗ {test_name}测试失败: {e}\n")
            failed += 1
    
    print(f"测试结果: {passed}通过, {failed}失败")
    
    if failed == 0:
        print("🎉 所有卡牌和卡牌池测试通过！")
        return True
    else:
        print("❌ 部分测试失败，需要修复")
        return False


if __name__ == "__main__":
    run_tests() 