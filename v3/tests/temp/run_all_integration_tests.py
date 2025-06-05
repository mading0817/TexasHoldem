#!/usr/bin/env python3
"""
运行所有集成测试
"""

import subprocess
import sys
import os

def main():
    """运行所有集成测试"""
    try:
        # 确保在正确的目录中
        os.chdir(r"C:\Users\Martin\PycharmProjects\TexasHoldem")
        
        # 运行所有集成测试
        cmd = [
            r".venv\Scripts\python.exe",
            "-m", "pytest",
            r"v3\tests\integration",
            "-v", "--tb=short", "-x"
        ]
        
        print("运行所有集成测试...")
        print("命令:", " ".join(cmd))
        print("-" * 50)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\n退出代码: {result.returncode}")
        
        return result.returncode
        
    except Exception as e:
        print(f"运行测试失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 