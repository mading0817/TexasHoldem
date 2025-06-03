#!/usr/bin/env python3
"""
简化的CI测试脚本 - 用于诊断问题
"""

import subprocess
import sys
from pathlib import Path

def run_simple_test(command, name):
    """运行简单测试"""
    print(f"\n🔄 运行: {name}")
    print(f"命令: {command}")
    print("-" * 60)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            text=True,
            cwd=Path.cwd()
        )
        
        success = result.returncode == 0
        print(f"结果: {'✅ 成功' if success else '❌ 失败'} (返回码: {result.returncode})")
        return success
        
    except Exception as e:
        print(f"❌ 异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 简化CI测试开始")
    print(f"工作目录: {Path.cwd()}")
    
    tests = [
        (".venv/Scripts/python -m pytest v2/tests/unit/test_v2_cards.py -q", "单个单元测试文件"),
        (".venv/Scripts/python -m pytest v2/tests/unit/ -q", "所有单元测试"),
        (".venv/Scripts/python -m pytest v2/tests/integration/ -q", "所有集成测试"),
        (".venv/Scripts/python -m pytest v2/tests/meta/ -m supervisor -q", "监督者测试"),
        (".venv/Scripts/python -m pytest v2/tests/meta/ -m state_tamper -q", "状态篡改测试"),
        (".venv/Scripts/python -m pytest v2/tests/meta/ -m rule_coverage -q", "规则覆盖率测试"),
        (".venv/Scripts/python -m pytest v2/tests/meta/ -m ai_fairness -q", "AI公平性测试"),
        (".venv/Scripts/python -m pytest v2/tests/meta/ -m root_cause -q", "根因分析测试"),
        (".venv/Scripts/python -m pytest v2/tests/integration/ -m end_to_end -q", "端到端测试"),
    ]
    
    results = []
    for command, name in tests:
        success = run_simple_test(command, name)
        results.append((name, success))
    
    print("\n" + "="*80)
    print("📊 测试结果汇总")
    print("="*80)
    
    passed = 0
    total = len(results)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
        if success:
            passed += 1
    
    print(f"\n🏆 总结: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有测试通过！CI问题可能在其他地方。")
    else:
        print("💥 发现失败的测试，需要进一步调查。")

if __name__ == '__main__':
    main() 