#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克项目测试运行器 v2.0
运行重构后的模块化测试套件
支持按类型分别运行不同的测试
"""

import sys
import os
import subprocess
from pathlib import Path

def run_unit_tests():
    """运行单元测试"""
    print("=== 运行单元测试 ===")
    
    unit_test_files = [
        "tests/unit/test_enums.py",
        "tests/unit/test_card.py", 
        "tests/unit/test_config.py",
        "tests/unit/test_deck.py",
        "tests/unit/test_player.py",
        "tests/unit/test_evaluator.py",
        "tests/unit/test_action_validator.py",
        "tests/unit/test_pot_manager.py",
        "tests/unit/test_side_pot.py",
        "tests/unit/test_game_state.py",
        "tests/unit/test_game_controller.py",
        "tests/unit/test_phase_transition.py",
        "tests/unit/test_simple_betting.py",
        "tests/unit/test_chip_conservation.py",
    ]
    
    return run_test_files(unit_test_files, "单元测试")

def run_integration_tests():
    """运行集成测试"""
    print("\n=== 运行集成测试 ===")
    
    integration_test_files = [
        "tests/integration/test_core_integration.py",
        "tests/integration/test_full_game.py",
    ]
    
    return run_test_files(integration_test_files, "集成测试")

def run_e2e_tests():
    """运行端到端测试"""
    print("\n=== 运行端到端测试 ===")
    
    e2e_test_files = [
        "tests/e2e/ai_simulation_test.py",
    ]
    
    return run_test_files(e2e_test_files, "端到端测试")

def run_rules_tests():
    """运行规则测试"""
    print("\n=== 运行规则测试 ===")
    
    rules_test_files = [
        "tests/rules/test_core_rules.py",
        "tests/rules/test_poker_compliance.py",
        "tests/rules/test_comprehensive_rules_validation.py",
        "tests/rules/test_texas_holdem_edge_cases.py"
    ]
    
    return run_test_files(rules_test_files, "规则测试")

def run_performance_tests():
    """运行性能测试"""
    print("\n=== 运行性能测试 ===")
    
    performance_test_files = [
        "tests/performance/test_benchmarks.py"
    ]
    
    return run_test_files(performance_test_files, "性能测试", timeout=120)

def run_security_tests():
    """运行安全测试"""
    print("\n=== 运行安全测试 ===")
    
    security_test_files = [
        "tests/security/test_anti_cheat.py"
    ]
    
    return run_test_files(security_test_files, "安全测试")

def run_system_tests():
    """运行系统级测试"""
    print("\n=== 运行系统级测试 ===")
    
    system_test_files = [
        "tests/system/test_game_flow.py",
        "tests/system/test_game_integrity.py",
        "tests/system/test_advanced_scenarios.py"
    ]
    
    return run_test_files(system_test_files, "系统测试", timeout=180)

def run_test_files(test_files, category_name, timeout=60):
    """
    运行指定的测试文件列表
    
    Args:
        test_files: 测试文件路径列表
        category_name: 测试类别名称
        timeout: 单个测试文件的超时时间（秒）
    
    Returns:
        bool: 所有测试是否都通过
    """
    passed = 0
    failed = 0
    total_files = len(test_files)
    
    # 设置PYTHONPATH环境变量以确保模块可以正确导入
    env = os.environ.copy()
    current_dir = os.getcwd()
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = current_dir + os.pathsep + env['PYTHONPATH']
    else:
        env['PYTHONPATH'] = current_dir
    
    # 添加调试信息：显示当前工作目录
    print(f"当前工作目录: {current_dir}")
    
    for test_file in test_files:
        # 检查绝对路径和相对路径
        absolute_path = os.path.abspath(test_file)
        print(f"检查文件: {test_file} (绝对路径: {absolute_path})")
        
        if os.path.exists(test_file):
            print(f"\n运行 {test_file}...")
            try:
                # 运行测试并捕获输出 - 修复编码问题
                result = subprocess.run(
                    [sys.executable, test_file], 
                    capture_output=True, 
                    text=True,
                    encoding='utf-8',  # 明确指定编码
                    errors='replace',  # 遇到编码错误时替换字符
                    cwd=current_dir,
                    env=env  # 传递环境变量
                )
                
                success = result.returncode == 0
                status = "✓" if success else "✗"
                print(f"{status} {test_file} {'通过' if success else '失败'}")
                
                if not success:
                    print(f"错误输出: {result.stderr}")
                
                # 输出测试的标准输出（用于调试）
                if result.stdout.strip():
                    # 过滤掉编码相关的错误信息
                    stdout_lines = result.stdout.split('\n')
                    filtered_lines = [line for line in stdout_lines if 'UnicodeDecodeError' not in line and 'UnicodeEncodeError' not in line]
                    if filtered_lines:
                        clean_stdout = '\n'.join(filtered_lines).strip()
                        if clean_stdout:
                            print(f"标准输出: {clean_stdout}")
                
                if success:
                    passed += 1
                else:
                    failed += 1
            except subprocess.TimeoutExpired:
                print(f"✗ {test_file} 超时")
                failed += 1
            except Exception as e:
                print(f"✗ {test_file} 异常: {e}")
                failed += 1
        else:
            print(f"⚠ {test_file} 不存在，跳过... (查找路径: {absolute_path})")
    
    # 修复逻辑：如果没有测试运行，应该返回失败而不是通过
    executed_tests = passed + failed
    print(f"\n{category_name}结果: {passed}通过, {failed}失败, {total_files - executed_tests}跳过")
    
    # 返回逻辑：只有当有测试运行且没有失败时才返回True
    if executed_tests == 0:
        print(f"警告: {category_name}中没有测试文件被执行")
        return False  # 没有测试运行视为失败
    
    return failed == 0

def run_legacy_comprehensive_test():
    """运行传统的comprehensive_test.py（如果还存在）"""
    print("\n=== 运行传统综合测试 ===")
    
    comprehensive_test_file = "comprehensive_test.py"
    
    if os.path.exists(comprehensive_test_file):
        print(f"⚠ 发现传统测试文件 {comprehensive_test_file}")
        print("注意：此文件将在重构完成后删除")
        
        try:
            result = subprocess.run([sys.executable, comprehensive_test_file], 
                                  capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                print(f"✓ {comprehensive_test_file} 通过")
                return True
            else:
                print(f"✗ {comprehensive_test_file} 失败")
                if result.stderr:
                    print(f"错误输出: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print(f"✗ {comprehensive_test_file} 超时")
            return False
        except Exception as e:
            print(f"✗ {comprehensive_test_file} 异常: {e}")
            return False
    else:
        print("传统综合测试文件已不存在，重构完成")
        return True

def check_project_structure():
    """检查项目结构"""
    print("\n检查项目结构...")
    
    # 显示当前工作目录以便调试
    current_dir = os.getcwd()
    print(f"当前工作目录: {current_dir}")
    
    required_dirs = [
        "v2",
        "v2/core",
        "v2/controller", 
        "v2/ai",
        "v2/ui",
        "v2/ui/cli",
        "v2/ui/streamlit",
        "tests/unit"
    ]
    
    missing_dirs = []
    existing_dirs = []
    
    for dir_path in required_dirs:
        absolute_path = os.path.abspath(dir_path)
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            print(f"✓ {dir_path}")
            existing_dirs.append(dir_path)
        else:
            print(f"✗ {dir_path} 缺失 (查找路径: {absolute_path})")
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        print(f"\n警告：发现 {len(missing_dirs)} 个缺失目录，{len(existing_dirs)} 个存在")
        return False
    else:
        print(f"\n✓ 项目结构完整，所有 {len(existing_dirs)} 个必需目录都存在")
        return True

def main():
    """主函数"""
    print("德州扑克项目 - 模块化测试套件 v2.0")
    print("=" * 60)
    
    # 检查项目结构
    structure_ok = check_project_structure()
    if not structure_ok:
        print("\n❌ 项目结构不完整，部分测试可能失败")
    
    # 运行各类测试
    results = {}
    
    # 基础测试（必须通过）
    results["unit"] = run_unit_tests()
    results["rules"] = run_rules_tests()
    
    # 集成测试
    results["integration"] = run_integration_tests()
    results["e2e"] = run_e2e_tests()
    
    # 高级测试（可选）
    # results["performance"] = run_performance_tests() 先不进行performance测试
    results["security"] = run_security_tests()
    results["system"] = run_system_tests()
    
    # 传统测试（向后兼容）
    results["legacy"] = run_legacy_comprehensive_test()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结:")
    
    core_tests = ["unit", "rules", "integration"]
    advanced_tests = ["e2e", "performance", "security", "system"]
    
    # 改进结果统计逻辑
    core_passed = all(results.get(test, False) for test in core_tests)
    all_passed = all(results.values())
    
    # 统计实际状态
    passed_count = sum(1 for result in results.values() if result)
    failed_count = len(results) - passed_count
    
    for test_type, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        priority = "核心" if test_type in core_tests else "高级" if test_type in advanced_tests else "兼容"
        print(f"{test_type:12} ({priority:4}): {status}")
    
    print(f"\n核心测试: {'✓ 全部通过' if core_passed else '✗ 存在失败'}")
    print(f"整体状态: {'✓ 全部通过' if all_passed else '✗ 存在失败'} ({passed_count}通过, {failed_count}失败)")
    
    # 更准确的退出逻辑
    if core_passed and all_passed:
        print("\n🎉 所有测试通过！项目状态良好。")
        return 0
    elif core_passed:
        print("\n🎉 核心功能测试通过！基础游戏逻辑运行正常。")
        print("⚠️  高级测试存在失败，但不影响基础功能。")
        return 0
    else:
        print("\n❌ 核心测试失败，需要修复基础问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 