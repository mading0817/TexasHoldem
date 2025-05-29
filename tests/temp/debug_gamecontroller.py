#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试GameController类，检查advance_phase方法
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

def debug_gamecontroller():
    """调试GameController类"""
    print("=" * 60)
    print("GameController类调试")
    print("=" * 60)
    
    try:
        # 导入GameController
        from core_game_logic.game.game_controller import GameController
        print(f"✓ GameController导入成功")
        print(f"  模块路径: {GameController.__module__}")
        print(f"  类定义文件: {GameController.__module__.replace('.', '/') + '.py'}")
        
        # 检查类的方法
        methods = [attr for attr in dir(GameController) if not attr.startswith('_')]
        print(f"\n✓ GameController有 {len(methods)} 个公共方法:")
        for method in sorted(methods):
            print(f"  - {method}")
        
        # 特别检查advance_phase方法
        if hasattr(GameController, 'advance_phase'):
            print(f"\n✓ advance_phase方法存在")
            advance_phase_method = getattr(GameController, 'advance_phase')
            print(f"  方法类型: {type(advance_phase_method)}")
            print(f"  是否可调用: {callable(advance_phase_method)}")
        else:
            print(f"\n✗ advance_phase方法不存在")
        
        # 检查缓存测试方法
        if hasattr(GameController, 'debug_method_for_cache_test'):
            print(f"\n✓ debug_method_for_cache_test方法存在 - 文件确实被重新加载")
        else:
            print(f"\n✗ debug_method_for_cache_test方法不存在 - 可能仍在使用缓存版本")
            
        # 创建实例测试
        print(f"\n开始创建GameController实例测试...")
        
        from core_game_logic.game.game_state import GameState
        from core_game_logic.core.player import Player
        from core_game_logic.core.enums import SeatStatus
        
        # 创建简单的游戏状态
        players = [
            Player(seat_id=0, name="Player1", starting_chips=1000),
            Player(seat_id=1, name="Player2", starting_chips=1000)
        ]
        
        # 设置玩家状态
        for player in players:
            # FIXED: 直接修改状态 player.status = SeatStatus.ACTIVE
        # 应使用游戏控制器的合法API进行状态变更
        
        game_state = GameState(players=players, small_blind=10, big_blind=20)
        controller = GameController(game_state)
        
        print(f"✓ GameController实例创建成功")
        
        # 检查实例方法
        if hasattr(controller, 'advance_phase'):
            print(f"✓ 实例有advance_phase方法")
            print(f"  方法类型: {type(controller.advance_phase)}")
            print(f"  是否可调用: {callable(controller.advance_phase)}")
        else:
            print(f"✗ 实例没有advance_phase方法")
            
        # 列出实例的所有方法
        instance_methods = [attr for attr in dir(controller) if not attr.startswith('_') and callable(getattr(controller, attr))]
        print(f"\n✓ 实例有 {len(instance_methods)} 个公共方法:")
        for method in sorted(instance_methods):
            print(f"  - {method}")
            
        return True
        
    except Exception as e:
        print(f"✗ 调试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_gamecontroller() 