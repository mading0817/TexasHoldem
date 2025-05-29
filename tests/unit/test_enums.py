#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
枚举类型(Enums)单元测试
测试扑克游戏中使用的各种枚举类型的正确性和一致性
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_game_logic.core.enums import (
    Suit, Rank, ActionType, GamePhase, SeatStatus
)
from core_game_logic.evaluator.hand_rank import HandRank


class TestEnums:
    """枚举类型测试"""
    
    def test_suit_enum(self):
        """测试花色枚举"""
        print("测试花色枚举...")
        
        # 测试花色值
        assert Suit.HEARTS.value == "h", "红桃值应该是h"
        assert Suit.DIAMONDS.value == "d", "方块值应该是d"
        assert Suit.CLUBS.value == "c", "梅花值应该是c"
        assert Suit.SPADES.value == "s", "黑桃值应该是s"
        
        # 测试字符串表示
        assert str(Suit.HEARTS) == "h", "红桃字符串应该是h"
        assert str(Suit.SPADES) == "s", "黑桃字符串应该是s"
        
        # 测试符号属性
        assert Suit.HEARTS.symbol == "♥", "红桃符号应该正确"
        assert Suit.DIAMONDS.symbol == "♦", "方块符号应该正确"
        assert Suit.CLUBS.symbol == "♣", "梅花符号应该正确"
        assert Suit.SPADES.symbol == "♠", "黑桃符号应该正确"
        
        print("[OK] 花色枚举测试通过")
    
    def test_rank_enum(self):
        """测试点数枚举"""
        print("测试点数枚举...")
        
        # 测试点数值
        assert Rank.TWO.value == 2, "2的值应该是2"
        assert Rank.ACE.value == 14, "A的值应该是14"
        assert Rank.KING.value == 13, "K的值应该是13"
        assert Rank.QUEEN.value == 12, "Q的值应该是12"
        assert Rank.JACK.value == 11, "J的值应该是11"
        
        # 测试字符串表示
        assert str(Rank.ACE) == "A", "A的字符串应该是A"
        assert str(Rank.KING) == "K", "K的字符串应该是K"
        assert str(Rank.QUEEN) == "Q", "Q的字符串应该是Q"
        assert str(Rank.JACK) == "J", "J的字符串应该是J"
        assert str(Rank.TEN) == "T", "10的字符串应该是T"
        assert str(Rank.TWO) == "2", "2的字符串应该是2"
        
        # 测试从字符串解析
        assert Rank.from_str("A") == Rank.ACE, "应该能解析A为ACE"
        assert Rank.from_str("K") == Rank.KING, "应该能解析K为KING"
        assert Rank.from_str("Q") == Rank.QUEEN, "应该能解析Q为QUEEN"
        assert Rank.from_str("J") == Rank.JACK, "应该能解析J为JACK"
        assert Rank.from_str("T") == Rank.TEN, "应该能解析T为TEN"
        assert Rank.from_str("2") == Rank.TWO, "应该能解析2为TWO"
        
        # 测试无效解析
        try:
            Rank.from_str("X")
            assert False, "无效字符应该抛出异常"
        except ValueError:
            pass
        
        print("[OK] 点数枚举测试通过")
    
    def test_seat_status_enum(self):
        """测试座位状态枚举"""
        print("测试座位状态枚举...")
        
        # 测试所有状态存在
        assert SeatStatus.ACTIVE is not None, "ACTIVE状态应该存在"
        assert SeatStatus.FOLDED is not None, "FOLDED状态应该存在"
        assert SeatStatus.ALL_IN is not None, "ALL_IN状态应该存在"
        assert SeatStatus.OUT is not None, "OUT状态应该存在"
        
        # 测试状态不同
        assert SeatStatus.ACTIVE != SeatStatus.FOLDED, "不同状态应该不相等"
        assert SeatStatus.ALL_IN != SeatStatus.OUT, "不同状态应该不相等"
        
        print("[OK] 座位状态枚举测试通过")
    
    def test_game_phase_enum(self):
        """测试游戏阶段枚举"""
        print("测试游戏阶段枚举...")
        
        # 测试所有阶段存在
        assert GamePhase.PRE_FLOP is not None, "PRE_FLOP阶段应该存在"
        assert GamePhase.FLOP is not None, "FLOP阶段应该存在"
        assert GamePhase.TURN is not None, "TURN阶段应该存在"
        assert GamePhase.RIVER is not None, "RIVER阶段应该存在"
        assert GamePhase.SHOWDOWN is not None, "SHOWDOWN阶段应该存在"
        
        # 测试阶段顺序（通过值比较）
        phases = [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER, GamePhase.SHOWDOWN]
        for i in range(len(phases) - 1):
            assert phases[i].value < phases[i + 1].value, f"{phases[i].name}应该在{phases[i + 1].name}之前"
        
        print("[OK] 游戏阶段枚举测试通过")
    
    def test_action_type_enum(self):
        """测试行动类型枚举"""
        print("测试行动类型枚举...")
        
        # 测试所有行动类型存在
        assert ActionType.FOLD is not None, "FOLD行动应该存在"
        assert ActionType.CHECK is not None, "CHECK行动应该存在"
        assert ActionType.CALL is not None, "CALL行动应该存在"
        assert ActionType.BET is not None, "BET行动应该存在"
        assert ActionType.RAISE is not None, "RAISE行动应该存在"
        assert ActionType.ALL_IN is not None, "ALL_IN行动应该存在"
        
        # 测试字符串表示
        assert str(ActionType.FOLD) == "弃牌", "FOLD的字符串应该正确"
        assert str(ActionType.CHECK) == "过牌", "CHECK的字符串应该正确"
        assert str(ActionType.CALL) == "跟注", "CALL的字符串应该正确"
        assert str(ActionType.BET) == "下注", "BET的字符串应该正确"
        assert str(ActionType.RAISE) == "加注", "RAISE的字符串应该正确"
        assert str(ActionType.ALL_IN) == "全押", "ALL_IN的字符串应该正确"
        
        print("[OK] 行动类型枚举测试通过")


def run_tests():
    """运行所有测试"""
    print("=== 枚举类型单元测试 ===\n")
    
    test_instance = TestEnums()
    
    test_methods = [
        ("花色枚举", test_instance.test_suit_enum),
        ("点数枚举", test_instance.test_rank_enum),
        ("座位状态枚举", test_instance.test_seat_status_enum),
        ("游戏阶段枚举", test_instance.test_game_phase_enum),
        ("行动类型枚举", test_instance.test_action_type_enum),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in test_methods:
        try:
            test_func()
            print(f"[OK] {test_name}测试通过\n")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test_name}测试失败: {e}\n")
            failed += 1
    
    print(f"测试结果: {passed}通过, {failed}失败")
    
    if failed == 0:
        print("[SUCCESS] 所有枚举类型测试通过！")
        return True
    else:
        print("[ERROR] 部分测试失败，需要修复")
        return False


if __name__ == "__main__":
    run_tests() 