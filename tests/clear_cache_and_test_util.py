#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
清除Python模块缓存并重新测试

解决模块重新加载导致的方法找不到问题
"""

import sys
import os
import importlib
import subprocess

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
project_root = os.path.abspath(project_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def clear_module_cache():
    """清除Python模块缓存"""
    print("清除Python模块缓存...")
    
    # 清除所有项目相关的模块
    modules_to_clear = []
    for module_name in list(sys.modules.keys()):
        if any(pattern in module_name for pattern in ['core_game_logic', 'tests']):
            modules_to_clear.append(module_name)
    
    print(f"发现 {len(modules_to_clear)} 个项目模块需要清除:")
    for module_name in modules_to_clear:
        print(f"  - {module_name}")
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    print("模块缓存清除完成")

def test_import():
    """测试关键模块的导入"""
    print("\n测试关键模块导入...")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"项目根目录: {project_root}")
    print(f"Python路径: {sys.path[:3]}...")  # 只显示前3个路径
    
    try:
        # 重新导入核心模块
        from core_game_logic.game.game_controller import GameController
        from core_game_logic.game.game_state import GameState
        
        print("✓ 核心模块导入成功")
        
        # 检查GameController的advance_phase方法
        if hasattr(GameController, 'advance_phase'):
            print("✓ GameController.advance_phase 方法存在")
            
            # 创建一个实例来测试方法
            from core_game_logic.core.player import Player
            from core_game_logic.core.enums import GamePhase
            
            # 创建测试游戏状态
            from tests.common.base_tester import BaseTester
            from tests.common.data_structures import TestScenario
            
            print("✓ 测试辅助类导入成功")
            
            base_tester = BaseTester("ImportTest")
            scenario = TestScenario(
                name="导入测试场景",
                players_count=2,
                starting_chips=[1000, 1000],
                dealer_position=0,
                expected_behavior={},
                description="测试GameController方法可用性"
            )
            
            game_state = base_tester.create_scenario_game(scenario)
            controller = GameController(game_state)
            
            print("✓ GameController实例创建成功")
            print(f"✓ 实例确实有advance_phase方法: {hasattr(controller, 'advance_phase')}")
            
        else:
            print("✗ GameController.advance_phase 方法不存在")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_performance_test():
    """运行性能测试"""
    print("\n运行性能测试...")
    
    # 设置环境变量
    env = os.environ.copy()
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = project_root + os.pathsep + env['PYTHONPATH']
    else:
        env['PYTHONPATH'] = project_root
    
    print(f"设置PYTHONPATH: {env['PYTHONPATH']}")
    
    try:
        result = subprocess.run(
            [sys.executable, "tests/performance/test_benchmarks.py"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=project_root,
            env=env,
            timeout=300
        )
        
        print(f"返回码: {result.returncode}")
        
        if result.stdout:
            print("标准输出:")
            print(result.stdout[-1000:])  # 只显示最后1000个字符
        
        if result.stderr:
            print("错误输出:")
            print(result.stderr[-1000:])  # 只显示最后1000个字符
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"运行测试时发生异常: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("Python模块缓存清除和测试工具")
    print("=" * 60)
    
    # 步骤1：清除模块缓存
    clear_module_cache()
    
    # 步骤2：测试导入
    if not test_import():
        print("\n❌ 模块导入测试失败")
        return 1
    
    # 步骤3：运行性能测试
    if run_performance_test():
        print("\n🎉 性能测试成功!")
        return 0
    else:
        print("\n❌ 性能测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 