#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快速CLI测试 - 验证重构后的CLI游戏是否可以正常运行
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cli_game import EnhancedCLIGame
from app_controller.dto_models import PlayerActionInput
from core_game_logic.core.enums import ActionType


def test_cli_basic_flow():
    """测试CLI基本流程"""
    print("=== 快速CLI测试 ===")
    
    # 模拟无用户输入的情况
    import builtins
    original_input = builtins.input
    
    # 模拟用户输入
    inputs = iter([
        "TestPlayer",  # 玩家名称
        "2",           # 选择弃牌（如果需要行动）
        "n",           # 不继续游戏
    ])
    
    def mock_input(prompt=""):
        print(f"[模拟输入] {prompt}", end="")
        response = next(inputs, "n")  # 默认返回 "n"
        print(response)
        return response
    
    builtins.input = mock_input
    
    try:
        # 创建CLI游戏
        game = EnhancedCLIGame()
        
        # 设置调试模式
        game.debug_mode = True
        
        # 创建游戏
        game.create_game(num_players=3, starting_chips=500)
        
        print("✓ CLI游戏创建成功")
        
        # 检查Controller状态
        if game.controller:
            snapshot = game.controller.get_state_snapshot()
            print(f"✓ 当前状态: 阶段={snapshot.phase}, 玩家数={len(snapshot.players)}")
            
            # 开始一手牌
            result = game.controller.start_new_hand()
            print(f"✓ 开始新手牌: {result.success}")
            
            if result.success:
                # 获取当前玩家
                current_seat = game.controller.get_current_player_seat()
                print(f"✓ 当前行动玩家: {current_seat}")
                
                # 如果是人类玩家，我们可以模拟一个弃牌行动
                if current_seat == game.human_seat:
                    fold_action = PlayerActionInput(
                        seat_id=current_seat,
                        action_type=ActionType.FOLD
                    )
                    action_result = game.controller.execute_player_action(fold_action)
                    print(f"✓ 执行弃牌行动: {action_result.success}")
        
        print("✅ 快速CLI测试完成")
        return True
        
    except Exception as e:
        print(f"❌ CLI测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 恢复原始input函数
        builtins.input = original_input


if __name__ == "__main__":
    success = test_cli_basic_flow()
    print("🎉 CLI重构测试成功！" if success else "❌ CLI重构测试失败")
    sys.exit(0 if success else 1) 