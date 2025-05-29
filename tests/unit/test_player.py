#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
玩家(Player)类单元测试
测试玩家初始化、筹码管理、动作执行、状态变化等功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_game_logic.core.player import Player
from core_game_logic.core.card import Card, CardPool
from core_game_logic.core.enums import SeatStatus, Action, Rank, Suit
from core_game_logic.core.exceptions import InvalidActionError


class TestPlayer:
    """玩家类测试"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.player = Player(seat_id=0, name="测试玩家", chips=100)
    
    def test_player_initialization(self):
        """测试玩家初始化"""
        print("测试玩家初始化...")
        
        # 测试正常初始化
        player = Player(seat_id=1, name="Alice", chips=200)
        assert player.seat_id == 1, "座位号应该正确"
        assert player.name == "Alice", "名称应该正确"
        assert player.chips == 200, "筹码应该正确"
        assert player.current_bet == 0, "初始下注应该为0"
        assert player.status == SeatStatus.ACTIVE, "初始状态应该为ACTIVE"
        assert len(player.hole_cards) == 0, "初始手牌应该为空"
        assert not player.is_dealer, "初始不应该是庄家"
        assert not player.is_small_blind, "初始不应该是小盲"
        assert not player.is_big_blind, "初始不应该是大盲"
        
        print("[OK] 玩家初始化测试通过")
    
    def test_player_validation(self):
        """测试玩家数据验证"""
        print("测试玩家数据验证...")
        
        # 测试无效座位号
        try:
            Player(seat_id=-1, name="Invalid", chips=100)
            assert False, "负数座位号应该抛出异常"
        except ValueError as e:
            assert "座位号不能为负数" in str(e)
        
        # 测试无效筹码数
        try:
            Player(seat_id=0, name="Invalid", chips=-10)
            assert False, "负数筹码应该抛出异常"
        except ValueError as e:
            assert "筹码数量不能为负数" in str(e)
        
        # 测试无效当前下注
        try:
            Player(seat_id=0, name="Invalid", chips=100, current_bet=-5)
            assert False, "负数当前下注应该抛出异常"
        except ValueError as e:
            assert "当前下注不能为负数" in str(e)
        
        print("[OK] 玩家数据验证测试通过")
    
    def test_player_status_checks(self):
        """测试玩家状态检查方法"""
        print("测试玩家状态检查方法...")
        
        # 测试初始状态
        assert self.player.can_act(), "初始状态应该可以行动"
        assert not self.player.is_all_in(), "初始状态不应该是全押"
        assert not self.player.is_folded(), "初始状态不应该是弃牌"
        assert not self.player.is_out(), "初始状态不应该是出局"
        
        # 测试弃牌状态
        self.player.fold()
        assert not self.player.can_act(), "弃牌后不应该可以行动"
        assert self.player.is_folded(), "弃牌后应该是弃牌状态"
        
        # 重置状态测试全押
        # 创建新玩家进行全押测试（避免直接修改状态）
        all_in_player = Player(seat_id=2, name="全押测试玩家", chips=50)
        all_in_player.bet(50)  # 下注所有筹码
        assert all_in_player.is_all_in(), "筹码为0且有下注应该是全押"
        assert not all_in_player.can_act(), "全押后不应该可以行动"
        
        # 测试出局状态 - 创建筹码为0的玩家
        out_player = Player(seat_id=3, name="出局测试玩家", chips=0)
        assert not out_player.can_act(), "出局后不应该可以行动"
        assert out_player.chips == 0, "筹码应该为0"
        
        print("[OK] 玩家状态检查方法测试通过")
    
    def test_betting_functionality(self):
        """测试下注功能"""
        print("测试下注功能...")
        
        # 测试正常下注
        initial_chips = self.player.chips
        actual_amount = self.player.bet(20)
        
        assert actual_amount == 20, "实际下注金额应该正确"
        assert self.player.current_bet == 20, "当前下注应该更新"
        assert self.player.chips == initial_chips - 20, "筹码应该减少"
        assert self.player.status == SeatStatus.ACTIVE, "状态应该保持ACTIVE"
        
        # 测试累积下注
        actual_amount = self.player.bet(15)
        assert actual_amount == 15, "第二次下注金额应该正确"
        assert self.player.current_bet == 35, "当前下注应该累积"
        assert self.player.chips == initial_chips - 35, "筹码应该继续减少"
        
        print("[OK] 下注功能测试通过")
    
    def test_all_in_scenarios(self):
        """测试全押场景"""
        print("测试全押场景...")
        
        # 测试筹码不足时的全押 - 创建只有30筹码的玩家
        limited_player = Player(seat_id=2, name="限制筹码玩家", chips=30)
        actual_amount = limited_player.bet(50)  # 尝试下注超过筹码的金额
        
        assert actual_amount == 30, "实际下注应该是剩余筹码"
        assert limited_player.current_bet == 30, "当前下注应该是剩余筹码"
        assert limited_player.chips == 0, "筹码应该为0"
        assert limited_player.status == SeatStatus.ALL_IN, "状态应该变为ALL_IN"
        
        # 测试全押后无法继续下注
        try:
            limited_player.bet(10)
            assert False, "全押后不应该能继续下注"
        except ValueError as e:
            assert "无法行动" in str(e)
        
        print("[OK] 全押场景测试通过")
    
    def test_betting_validation(self):
        """测试下注验证"""
        print("测试下注验证...")
        
        # 测试负数下注
        try:
            self.player.bet(-10)
            assert False, "负数下注应该抛出异常"
        except ValueError as e:
            assert "下注金额不能为负数" in str(e)
        
        # 测试弃牌后下注
        self.player.fold()
        try:
            self.player.bet(10)
            assert False, "弃牌后不应该能下注"
        except ValueError as e:
            assert "无法行动" in str(e)
        
        print("[OK] 下注验证测试通过")
    
    def test_betting_ability_checks(self):
        """测试下注能力检查"""
        print("测试下注能力检查...")
        
        # 测试正常情况
        assert self.player.can_bet(50), "应该可以下注50"
        assert self.player.can_bet(100), "应该可以下注100"
        assert not self.player.can_bet(150), "不应该可以下注150（超过筹码）"
        
        # 测试跟注能力
        assert self.player.can_call(50), "应该可以跟注50"
        assert self.player.can_call(100), "应该可以跟注100"
        assert self.player.can_call(150), "应该可以跟注150（可以全押）"
        
        # 测试弃牌后
        self.player.fold()
        assert not self.player.can_bet(10), "弃牌后不应该可以下注"
        assert not self.player.can_call(10), "弃牌后不应该可以跟注"
        
        print("[OK] 下注能力检查测试通过")
    
    def test_fold_functionality(self):
        """测试弃牌功能"""
        print("测试弃牌功能...")
        
        # 测试正常弃牌
        self.player.fold()
        assert self.player.status == SeatStatus.FOLDED, "弃牌后状态应该是FOLDED"
        assert not self.player.can_act(), "弃牌后不应该可以行动"
        
        # 测试全押状态下弃牌 - 创建全押状态的玩家
        all_in_player = Player(seat_id=1, name="Player2", chips=50)
        all_in_player.bet(50)  # 全押
        assert all_in_player.status == SeatStatus.ALL_IN, "应该是全押状态"
        
        all_in_player.fold()  # 全押状态下应该可以弃牌
        assert all_in_player.status == SeatStatus.FOLDED, "全押状态下弃牌应该成功"
        
        print("[OK] 弃牌功能测试通过")
    
    def test_hole_cards_management(self):
        """测试手牌管理"""
        print("测试手牌管理...")
        
        # 创建测试牌
        card1 = CardPool.get_card(Rank.ACE, Suit.SPADES)
        card2 = CardPool.get_card(Rank.KING, Suit.HEARTS)
        card3 = CardPool.get_card(Rank.QUEEN, Suit.DIAMONDS)
        
        # 测试设置手牌
        self.player.set_hole_cards([card1, card2])
        assert len(self.player.hole_cards) == 2, "应该有2张手牌"
        assert self.player.hole_cards[0] == card1, "第一张牌应该正确"
        assert self.player.hole_cards[1] == card2, "第二张牌应该正确"
        
        # 测试手牌字符串表示 - 修复Unicode显示问题
        cards_str = self.player.get_hole_cards_str()
        # Card类的to_str()方法返回简短格式（如"As Kh"），不是Unicode符号格式
        assert "As" in cards_str and "Kh" in cards_str, "手牌字符串应该包含正确的牌"
        
        # 测试隐藏手牌
        hidden_str = self.player.get_hole_cards_str(hidden=True)
        assert hidden_str == "XX XX", "隐藏手牌应该显示XX XX"
        
        # 测试超过2张牌的异常
        try:
            self.player.set_hole_cards([card1, card2, card3])
            assert False, "超过2张手牌应该抛出异常"
        except ValueError as e:
            assert "手牌不能超过2张" in str(e)
        
        print("[OK] 手牌管理测试通过")
    
    def test_effective_stack(self):
        """测试有效筹码计算"""
        print("测试有效筹码计算...")
        
        # 测试初始状态
        assert self.player.get_effective_stack() == 100, "初始有效筹码应该等于筹码数"
        
        # 测试下注后
        self.player.bet(30)
        assert self.player.get_effective_stack() == 100, "下注后有效筹码应该保持不变"
        assert self.player.chips == 70, "筹码应该减少"
        assert self.player.current_bet == 30, "当前下注应该增加"
        
        print("[OK] 有效筹码计算测试通过")
    
    def test_chip_management(self):
        """测试筹码管理"""
        print("测试筹码管理...")
        
        # 测试增加筹码
        initial_chips = self.player.chips
        self.player.add_chips(50)
        assert self.player.chips == initial_chips + 50, "筹码应该增加"
        
        # 测试负数筹码异常
        try:
            self.player.add_chips(-10)
            assert False, "增加负数筹码应该抛出异常"
        except ValueError as e:
            assert "增加的筹码数量不能为负数" in str(e)
        
        # 测试出局玩家重新激活 - 创建出局状态的玩家
        out_player = Player(seat_id=4, name="出局玩家", chips=0)
        # 将状态设置为OUT（通过重置功能实现）
        out_player.reset_for_new_hand()  # 筹码为0时会设置为OUT
        assert out_player.status == SeatStatus.OUT, "应该是出局状态"
        
        out_player.add_chips(100)
        assert out_player.status == SeatStatus.ACTIVE, "增加筹码后应该重新激活"
        
        print("[OK] 筹码管理测试通过")
    
    def test_reset_functionality(self):
        """测试重置功能"""
        print("测试重置功能...")
        
        # 设置一些状态
        card1 = CardPool.get_card(Rank.ACE, Suit.SPADES)
        card2 = CardPool.get_card(Rank.KING, Suit.HEARTS)
        self.player.set_hole_cards([card1, card2])
        self.player.bet(30)
        self.player.is_dealer = True
        self.player.is_small_blind = True
        
        # 测试重置当前下注
        self.player.reset_current_bet()
        assert self.player.current_bet == 0, "当前下注应该重置为0"
        assert len(self.player.hole_cards) == 2, "手牌不应该被清空"
        
        # 测试新手牌重置
        self.player.reset_for_new_hand()
        assert len(self.player.hole_cards) == 0, "手牌应该被清空"
        assert self.player.current_bet == 0, "当前下注应该为0"
        # 位置标记由GameState管理，不在此重置
        # assert not self.player.is_dealer, "庄家标记应该被清除"
        # assert not self.player.is_small_blind, "小盲标记应该被清除"
        # assert not self.player.is_big_blind, "大盲标记应该被清除"
        assert self.player.status == SeatStatus.ACTIVE, "状态应该重置为ACTIVE"
        
        # 测试筹码为0的重置
        zero_chip_player = Player(seat_id=5, name="零筹码玩家", chips=0)
        zero_chip_player.reset_for_new_hand()
        assert zero_chip_player.status == SeatStatus.OUT, "筹码为0应该设置为OUT"
        
        print("[OK] 重置功能测试通过")
    
    def test_string_representations(self):
        """测试字符串表示"""
        print("测试字符串表示...")
        
        # 设置一些状态进行测试
        card1 = CardPool.get_card(Rank.ACE, Suit.SPADES)
        card2 = CardPool.get_card(Rank.KING, Suit.HEARTS)
        self.player.set_hole_cards([card1, card2])
        self.player.bet(20)
        self.player.is_dealer = True
        self.player.is_small_blind = True
        
        # 测试__str__方法
        str_repr = str(self.player)
        assert "测试玩家" in str_repr, "应该包含玩家名称"
        assert "80筹码" in str_repr, "应该包含筹码数"
        assert "当前下注20" in str_repr, "应该包含当前下注"
        assert "庄家" in str_repr, "应该包含庄家标记"
        assert "小盲" in str_repr, "应该包含小盲标记"
        # 修复Unicode显示问题 - Card使用简短格式，不是Unicode符号
        assert "As Kh" in str_repr, "应该包含手牌"
        
        # 测试__repr__方法
        repr_str = repr(self.player)
        assert "Player(seat=0" in repr_str, "应该包含座位号"
        assert "name='测试玩家'" in repr_str, "应该包含名称"
        assert "chips=80" in repr_str, "应该包含筹码"
        assert "status=ACTIVE" in repr_str, "应该包含状态"
        
        print("[OK] 字符串表示测试通过")


def run_tests():
    """运行所有测试"""
    print("=== 玩家(Player)类单元测试 ===\n")
    
    test_instance = TestPlayer()
    
    test_methods = [
        ("玩家初始化", test_instance.test_player_initialization),
        ("玩家数据验证", test_instance.test_player_validation),
        ("玩家状态检查方法", test_instance.test_player_status_checks),
        ("下注功能", test_instance.test_betting_functionality),
        ("全押场景", test_instance.test_all_in_scenarios),
        ("下注验证", test_instance.test_betting_validation),
        ("下注能力检查", test_instance.test_betting_ability_checks),
        ("弃牌功能", test_instance.test_fold_functionality),
        ("手牌管理", test_instance.test_hole_cards_management),
        ("有效筹码计算", test_instance.test_effective_stack),
        ("筹码管理", test_instance.test_chip_management),
        ("重置功能", test_instance.test_reset_functionality),
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
        print("[SUCCESS] 所有Player单元测试通过！")
        return True
    else:
        print("[ERROR] 部分测试失败，需要修复")
        return False


if __name__ == "__main__":
    run_tests() 