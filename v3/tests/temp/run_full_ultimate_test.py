#!/usr/bin/env python3
"""
运行完整终极测试脚本 - 绕过PowerShell显示问题
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def run_full_ultimate_test():
    """运行完整版终极测试"""
    print("=" * 60)
    print("🚀 开始运行完整版终极测试 (100手牌)")
    print("=" * 60)
    
    # 设置工作目录为项目根目录
    os.chdir(project_root)
    
    try:
        # 运行完整终极测试
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "v3/tests/integration/test_streamlit_ultimate_user_experience_v3.py::test_streamlit_ultimate_user_experience_v3_full",
            "-v", "-s", "--tb=short"
        ], 
        capture_output=True, 
        text=True, 
        timeout=600  # 10分钟超时
        )
        
        print("📊 测试输出:")
        print("-" * 40)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        print("-" * 40)
        print(f"🎯 测试结果: {'✅ 通过' if result.returncode == 0 else '❌ 失败'}")
        print(f"📈 返回码: {result.returncode}")
        
        if result.returncode == 0:
            print("\n🎉 完整终极测试成功通过！")
            print("✅ 100手牌测试完成，满足PLAN 47要求")
        else:
            print(f"\n❌ 完整终极测试失败，返回码: {result.returncode}")
            print("需要检查并修复问题")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ 测试超时 (10分钟)")
        return False
    except Exception as e:
        print(f"❌ 运行测试时发生异常: {e}")
        return False

if __name__ == "__main__":
    start_time = time.time()
    success = run_full_ultimate_test()
    end_time = time.time()
    
    print(f"\n⏱️  总用时: {end_time - start_time:.2f}秒")
    
    if success:
        print("🎯 PLAN 47 - 完整终极测试验证: ✅ 完成")
    else:
        print("🎯 PLAN 47 - 完整终极测试验证: ❌ 需要修复")
    
    sys.exit(0 if success else 1) 