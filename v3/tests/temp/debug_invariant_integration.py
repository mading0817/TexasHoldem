"""
调试不变量集成问题

查看游戏创建时不变量检查的具体问题。
"""

from v3.application.command_service import GameCommandService
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


def debug_game_creation():
    """调试游戏创建过程"""
    print("=== 调试游戏创建过程 ===")
    
    # 创建启用不变量检查的命令服务
    service = GameCommandService(enable_invariant_checks=True)
    print(f"命令服务创建成功，不变量检查: {service._enable_invariant_checks}")
    
    # 尝试创建游戏
    try:
        print("开始创建游戏...")
        result = service.create_new_game(
            game_id="debug_game",
            player_ids=["player1", "player2"]
        )
        
        print(f"游戏创建结果:")
        print(f"  成功: {result.success}")
        print(f"  消息: {result.message}")
        print(f"  错误代码: {result.error_code}")
        print(f"  数据: {result.data}")
        
        if result.success:
            print(f"活跃游戏: {service.get_active_games()}")
            print(f"不变量检查器: {list(service._game_invariants.keys())}")
            
            # 尝试获取统计信息
            stats = service._get_invariant_stats("debug_game")
            if stats:
                print(f"不变量统计: {stats}")
            else:
                print("无法获取不变量统计信息")
        
    except Exception as e:
        print(f"异常: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()


def debug_disabled_invariant():
    """调试禁用不变量检查的情况"""
    print("\n=== 调试禁用不变量检查 ===")
    
    # 创建禁用不变量检查的命令服务
    service = GameCommandService(enable_invariant_checks=False)
    print(f"命令服务创建成功，不变量检查: {service._enable_invariant_checks}")
    
    # 尝试创建游戏
    try:
        result = service.create_new_game(
            game_id="debug_game_disabled",
            player_ids=["player1", "player2"]
        )
        
        print(f"游戏创建结果:")
        print(f"  成功: {result.success}")
        print(f"  消息: {result.message}")
        print(f"  错误代码: {result.error_code}")
        print(f"  数据: {result.data}")
        
        if result.success:
            print(f"活跃游戏: {service.get_active_games()}")
            print(f"不变量检查器: {list(service._game_invariants.keys())}")
        
    except Exception as e:
        print(f"异常: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()


def test_debug_disabled_invariant():
    """测试禁用不变量检查的情况"""
    debug_disabled_invariant()


def test_debug_game_creation():
    """测试游戏创建过程"""
    debug_game_creation() 