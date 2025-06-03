#!/usr/bin/env python3
"""
调试CI测试失败问题的脚本
"""

import subprocess
import sys
import os
from pathlib import Path

def run_test_command(command, description):
    """运行测试命令并显示详细输出"""
    print(f"\n{'='*80}")
    print(f"🔍 {description}")
    print(f"命令: {command}")
    print('='*80)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        
        print(f"返回码: {result.returncode}")
        print(f"成功: {'✅' if result.returncode == 0 else '❌'}")
        
        if result.stdout:
            print("\n📤 标准输出:")
            print(result.stdout)
        
        if result.stderr:
            print("\n📥 错误输出:")
            print(result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ 执行异常: {e}")
        return False

def main():
    """主函数"""
    print("🔍 开始诊断CI测试失败问题")
    print(f"工作目录: {Path.cwd()}")
    
    # 检查虚拟环境
    if not Path('.venv/Scripts/python.exe').exists():
        print("❌ 虚拟环境不存在")
        return
    
    # 测试1: 简单的单元测试
    run_test_command(
        ".venv\\Scripts\\python -m pytest v2/tests/unit/test_v2_cards.py -v",
        "测试1: 简单单元测试"
    )
    
    # 测试2: 带标记的测试
    run_test_command(
        ".venv\\Scripts\\python -m pytest v2/tests/meta/ -m supervisor -v",
        "测试2: 监督者标记测试"
    )
    
    # 测试3: 集成测试
    run_test_command(
        ".venv\\Scripts\\python -m pytest v2/tests/integration/test_end_to_end_integration.py -v",
        "测试3: 集成测试"
    )
    
    # 测试4: 检查pytest标记
    run_test_command(
        ".venv\\Scripts\\python -m pytest --markers",
        "测试4: 检查pytest标记"
    )
    
    # 测试5: 检查测试收集
    run_test_command(
        ".venv\\Scripts\\python -m pytest v2/tests/unit/ --collect-only",
        "测试5: 检查单元测试收集"
    )

if __name__ == '__main__':
    main() 