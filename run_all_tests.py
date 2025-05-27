#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克项目测试运行器
运行所有单元测试、集成测试和端到端测试
"""

import sys
import os
import subprocess
from pathlib import Path

def run_unit_tests():
    """运行单元测试"""
    print("=== 运行单元测试 ===")
    
    unit_test_files = [
        "tests/test_enums.py",
        "tests/test_card.py", 
        "tests/test_config.py",
        "tests/test_deck.py",
        "tests/test_player.py",
        "tests/test_evaluator.py",
        "tests/test_action_validator.py",
        "tests/test_pot_manager.py",
        "tests/test_side_pot.py",
        "tests/test_game_state.py",
        "tests/test_game_controller.py",
        "tests/test_phase_transition.py",
        "tests/test_simple_betting.py",
    ]
    
    passed = 0
    failed = 0
    
    for test_file in unit_test_files:
        if os.path.exists(test_file):
            print(f"\n运行 {test_file}...")
            try:
                result = subprocess.run([sys.executable, test_file], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    print(f"✓ {test_file} 通过")
                    passed += 1
                else:
                    print(f"✗ {test_file} 失败")
                    print(f"错误输出: {result.stderr}")
                    failed += 1
            except subprocess.TimeoutExpired:
                print(f"✗ {test_file} 超时")
                failed += 1
            except Exception as e:
                print(f"✗ {test_file} 异常: {e}")
                failed += 1
        else:
            print(f"⚠ {test_file} 不存在")
    
    print(f"\n单元测试结果: {passed}通过, {failed}失败")
    return failed == 0

def run_integration_tests():
    """运行集成测试"""
    print("\n=== 运行集成测试 ===")
    
    integration_test_files = [
        "tests/integration/test_core_integration.py",
        "tests/integration/test_full_game.py",
    ]
    
    passed = 0
    failed = 0
    
    for test_file in integration_test_files:
        if os.path.exists(test_file):
            print(f"\n运行 {test_file}...")
            try:
                result = subprocess.run([sys.executable, test_file], 
                                      capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    print(f"✓ {test_file} 通过")
                    passed += 1
                else:
                    print(f"✗ {test_file} 失败")
                    print(f"错误输出: {result.stderr}")
                    failed += 1
            except subprocess.TimeoutExpired:
                print(f"✗ {test_file} 超时")
                failed += 1
            except Exception as e:
                print(f"✗ {test_file} 异常: {e}")
                failed += 1
        else:
            print(f"⚠ {test_file} 不存在")
    
    print(f"\n集成测试结果: {passed}通过, {failed}失败")
    return failed == 0

def run_e2e_tests():
    """运行端到端测试"""
    print("\n=== 运行端到端测试 ===")
    
    e2e_test_files = [
        "tests/e2e/ai_simulation_test.py",
    ]
    
    passed = 0
    failed = 0
    
    for test_file in e2e_test_files:
        if os.path.exists(test_file):
            print(f"\n运行 {test_file}...")
            try:
                result = subprocess.run([sys.executable, test_file], 
                                      capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    print(f"✓ {test_file} 通过")
                    passed += 1
                else:
                    print(f"✗ {test_file} 失败")
                    print(f"错误输出: {result.stderr}")
                    failed += 1
            except subprocess.TimeoutExpired:
                print(f"✗ {test_file} 超时")
                failed += 1
            except Exception as e:
                print(f"✗ {test_file} 异常: {e}")
                failed += 1
        else:
            print(f"⚠ {test_file} 不存在")
    
    print(f"\n端到端测试结果: {passed}通过, {failed}失败")
    return failed == 0

def main():
    """主函数"""
    print("德州扑克项目 - 完整测试套件")
    print("=" * 50)
    
    # 检查项目结构
    print("\n检查项目结构...")
    required_dirs = [
        "core_game_logic/core",
        "core_game_logic/game", 
        "core_game_logic/betting",
        "core_game_logic/phases",
        "core_game_logic/evaluator",
        "tests",
        "tests/integration",
        "tests/e2e"
    ]
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✓ {dir_path}")
        else:
            print(f"✗ {dir_path} 缺失")
    
    # 运行所有测试
    unit_success = run_unit_tests()
    integration_success = run_integration_tests()
    e2e_success = run_e2e_tests()
    
    # 总结
    print("\n" + "=" * 50)
    print("测试总结:")
    print(f"单元测试: {'✓ 通过' if unit_success else '✗ 失败'}")
    print(f"集成测试: {'✓ 通过' if integration_success else '✗ 失败'}")
    print(f"端到端测试: {'✓ 通过' if e2e_success else '✗ 失败'}")
    
    if unit_success and integration_success and e2e_success:
        print("\n🎉 所有测试通过！项目结构重组成功。")
        return 0
    else:
        print("\n❌ 部分测试失败，需要修复导入路径或其他问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 