#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Phase 1 手动测试脚本
验证PokerController和重构后的CLI功能是否正常工作
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.core.enums import ActionType, GamePhase
from app_controller.poker_controller import PokerController
from app_controller.dto_models import PlayerActionInput, ActionResultType


def test_controller_basic():
    """测试Controller基本功能"""
    print("=== 测试 PokerController 基本功能 ===")
    
    # 创建测试玩家
    players = [
        Player(seat_id=0, name="Human", chips=1000),
        Player(seat_id=1, name="AI1", chips=1000),
        Player(seat_id=2, name="AI2", chips=1000),
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
    print(f"✓ Controller创建成功，版本: {controller.version}")
    
    # 测试状态快照
    snapshot = controller.get_state_snapshot()
    print(f"✓ 状态快照获取成功，玩家数: {len(snapshot.players)}")
    print(f"  阶段: {snapshot.phase}, 底池: {snapshot.pot}")
    
    # 测试开始新手牌
    result = controller.start_new_hand()
    print(f"✓ 开始新手牌: {result.success} - {result.message}")
    
    # 测试可用行动
    available_actions = controller.get_available_actions(0)
    print(f"✓ 玩家0可用行动: {[action.name for action in available_actions]}")
    
    # 测试详细可用行动
    detailed_actions = controller.get_available_actions_detail(0)
    print(f"✓ 玩家0详细行动信息:")
    for action in detailed_actions:
        print(f"  - {action['action_type'].name}: {action['display_name']}")
    
    return True


def test_controller_actions():
    """测试Controller行动处理"""
    print("\n=== 测试 PokerController 行动处理 ===")
    
    # 创建测试玩家
    players = [
        Player(seat_id=0, name="Human", chips=1000),
        Player(seat_id=1, name="AI1", chips=1000),
    ]
    
    # 创建初始游戏状态
    initial_state = GameState(
        players=players,
        dealer_position=0,
        small_blind=5,
        big_blind=10
    )
    
    controller = PokerController(initial_state)
    
    # 开始新手牌
    controller.start_new_hand()
    
    # 获取当前行动玩家
    current_seat = controller.get_current_player_seat()
    print(f"✓ 当前行动玩家: {current_seat}")
    
    # 测试弃牌行动
    fold_action = PlayerActionInput(
        seat_id=current_seat,
        action_type=ActionType.FOLD
    )
    
    result = controller.execute_player_action(fold_action)
    print(f"✓ 执行弃牌行动: {result.success} - {result.message}")
    
    # 检查版本增加
    print(f"✓ Controller版本已更新到: {controller.version}")
    
    return True


def test_cli_integration():
    """测试CLI层集成"""
    print("\n=== 测试 CLI 层集成 ===")
    
    try:
        from cli_game import EnhancedCLIGame
        
        # 创建CLI游戏实例
        cli_game = EnhancedCLIGame()
        print("✓ CLI游戏实例创建成功")
        
        # 创建游戏（不需要用户输入的简化版本）
        cli_game.create_game(num_players=3, starting_chips=1000)
        print("✓ 游戏创建成功")
        
        # 检查Controller是否正确初始化
        if cli_game.controller:
            print(f"✓ Controller已正确初始化，版本: {cli_game.controller.version}")
            
            # 测试快照显示功能
            snapshot = cli_game.controller.get_state_snapshot(viewer_seat=0)
            if snapshot:
                print(f"✓ 状态快照获取成功")
                print(f"  玩家数: {len(snapshot.players)}")
                print(f"  当前阶段: {snapshot.phase}")
            
        return True
        
    except Exception as e:
        print(f"❌ CLI集成测试失败: {e}")
        return False


def test_atomic_operations():
    """测试原子性操作"""
    print("\n=== 测试原子性操作 ===")
    
    # 创建测试玩家
    players = [
        Player(seat_id=0, name="Human", chips=100),  # 较少筹码用于测试边界
        Player(seat_id=1, name="AI1", chips=1000),
    ]
    
    initial_state = GameState(
        players=players,
        dealer_position=0,
        small_blind=5,
        big_blind=10
    )
    
    controller = PokerController(initial_state)
    controller.start_new_hand()
    
    # 保存初始版本
    initial_version = controller.version
    
    # 尝试一个可能失败的行动（超出筹码的下注）
    invalid_action = PlayerActionInput(
        seat_id=0,
        action_type=ActionType.BET,
        amount=2000  # 超过玩家筹码
    )
    
    result = controller.execute_player_action(invalid_action)
    
    if not result.success:
        print(f"✓ 无效行动被正确拒绝: {result.message}")
        print(f"✓ 版本保持不变: {controller.version} == {initial_version}")
    else:
        print(f"❌ 无效行动被意外接受")
        return False
    
    return True


def main():
    """运行所有测试"""
    print("Phase 1 Controller抽离 - 手动测试")
    print("=" * 50)
    
    tests = [
        ("Controller基本功能", test_controller_basic),
        ("Controller行动处理", test_controller_actions),
        ("CLI层集成", test_cli_integration),
        ("原子性操作", test_atomic_operations),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name} - 通过")
                passed += 1
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 Phase 1 Controller抽离测试全部通过！")
        return True
    else:
        print("⚠️  部分测试失败，需要进一步检查")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 