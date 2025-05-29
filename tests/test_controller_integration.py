#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PokerController集成测试 - Phase 1
验证应用控制层的基本功能和原子性操作
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.core.enums import ActionType, GamePhase
from app_controller.poker_controller import PokerController
from app_controller.dto_models import PlayerActionInput, ActionResultType


def test_controller_basic_functionality():
    """测试Controller基本功能"""
    print("🧪 测试Controller基本功能...")
    
    # 创建测试玩家
    players = [
        Player(seat_id=0, name="Alice", chips=1000),
        Player(seat_id=1, name="Bob", chips=1000)
    ]
    
    # 创建初始游戏状态
    initial_state = GameState(
        players=players,
        dealer_position=0,
        small_blind=5,
        big_blind=10
    )
    
    # 创建Controller
    controller = PokerController(initial_state)
    
    # 测试快照获取
    snapshot = controller.get_state_snapshot()
    assert snapshot is not None, "快照获取失败"
    assert snapshot.version == 0, f"初始版本应为0，实际为{snapshot.version}"
    assert len(snapshot.players) == 2, f"玩家数量应为2，实际为{len(snapshot.players)}"
    
    print("✅ 基本功能测试通过")


def test_controller_atomic_operations():
    """测试Controller原子性操作"""
    print("🧪 测试Controller原子性操作...")
    
    # 创建测试玩家
    players = [
        Player(seat_id=0, name="Alice", chips=1000),
        Player(seat_id=1, name="Bob", chips=1000)
    ]
    
    # 创建初始游戏状态
    initial_state = GameState(
        players=players,
        dealer_position=0,
        small_blind=5,
        big_blind=10
    )
    
    # 创建Controller
    controller = PokerController(initial_state)
    
    # 测试开始新手牌
    result = controller.start_new_hand()
    assert result.success, f"开始新手牌失败: {result.message}"
    assert controller.version == 1, f"版本应为1，实际为{controller.version}"
    
    # 测试快照版本更新
    snapshot = controller.get_state_snapshot()
    assert snapshot.version == 1, f"快照版本应为1，实际为{snapshot.version}"
    assert snapshot.phase == GamePhase.PRE_FLOP, f"阶段应为PRE_FLOP，实际为{snapshot.phase}"
    
    print("✅ 原子性操作测试通过")


def test_controller_player_actions():
    """测试Controller玩家行动处理"""
    print("🧪 测试Controller玩家行动处理...")
    
    # 创建测试玩家
    players = [
        Player(seat_id=0, name="Alice", chips=1000),
        Player(seat_id=1, name="Bob", chips=1000)
    ]
    
    # 创建初始游戏状态
    initial_state = GameState(
        players=players,
        dealer_position=0,
        small_blind=5,
        big_blind=10
    )
    
    # 创建Controller
    controller = PokerController(initial_state)
    
    # 开始新手牌
    result = controller.start_new_hand()
    assert result.success, f"开始新手牌失败: {result.message}"
    
    # 获取当前玩家
    current_seat = controller.get_current_player_seat()
    assert current_seat is not None, "当前玩家座位不应为None"
    
    # 测试有效行动
    action_input = PlayerActionInput(
        seat_id=current_seat,
        action_type=ActionType.CALL
    )
    
    result = controller.execute_player_action(action_input)
    assert result.success, f"执行玩家行动失败: {result.message}"
    
    # 测试无效行动（错误的玩家）
    invalid_action = PlayerActionInput(
        seat_id=99,  # 不存在的座位
        action_type=ActionType.CALL
    )
    
    result = controller.execute_player_action(invalid_action)
    assert not result.success, "无效行动应该失败"
    assert result.result_type == ActionResultType.INVALID_ACTION, "错误类型应为INVALID_ACTION"
    
    print("✅ 玩家行动处理测试通过")


def test_controller_dealer_rotation():
    """测试Controller庄家轮换"""
    print("🧪 测试Controller庄家轮换...")
    
    # 创建测试玩家
    players = [
        Player(seat_id=0, name="Alice", chips=1000),
        Player(seat_id=1, name="Bob", chips=1000),
        Player(seat_id=2, name="Charlie", chips=1000)
    ]
    
    # 创建初始游戏状态
    initial_state = GameState(
        players=players,
        dealer_position=0,
        small_blind=5,
        big_blind=10
    )
    
    # 创建Controller
    controller = PokerController(initial_state)
    
    # 获取初始庄家
    initial_snapshot = controller.get_state_snapshot()
    initial_dealer = initial_snapshot.dealer_position
    
    # 执行庄家轮换
    result = controller.advance_dealer()
    assert result.success, f"庄家轮换失败: {result.message}"
    
    # 验证庄家已轮换
    new_snapshot = controller.get_state_snapshot()
    new_dealer = new_snapshot.dealer_position
    assert new_dealer != initial_dealer, f"庄家应该轮换，初始:{initial_dealer}, 新:{new_dealer}"
    
    print("✅ 庄家轮换测试通过")


def run_all_tests():
    """运行所有测试"""
    print("🚀 开始Controller集成测试...")
    print("="*60)
    
    try:
        test_controller_basic_functionality()
        test_controller_atomic_operations()
        test_controller_player_actions()
        test_controller_dealer_rotation()
        
        print("="*60)
        print("🎉 所有Controller集成测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 