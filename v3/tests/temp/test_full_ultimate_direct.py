#!/usr/bin/env python3
"""
直接运行完整终极测试 - 避免PowerShell显示问题
"""

import sys
import os
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def run_full_ultimate_test_direct():
    """直接运行完整版终极测试"""
    print("=" * 60)
    print("🚀 直接运行完整版终极测试 (100手牌)")
    print("=" * 60)
    
    try:
        # 导入测试函数
        from v3.tests.integration.test_streamlit_ultimate_user_experience_v3 import test_streamlit_ultimate_user_experience_v3_full
        
        # 运行测试
        start_time = time.time()
        test_streamlit_ultimate_user_experience_v3_full()
        end_time = time.time()
        
        print(f"\n🎉 完整终极测试成功通过！")
        print(f"⏱️  测试用时: {end_time - start_time:.2f}秒")
        print("✅ 100手牌测试完成，满足PLAN 47要求")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ 完整终极测试断言失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 运行测试时发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    start_time = time.time()
    success = run_full_ultimate_test_direct()
    end_time = time.time()
    
    print(f"\n⏱️  总用时: {end_time - start_time:.2f}秒")
    
    if success:
        print("🎯 PLAN 47 - 完整终极测试验证: ✅ 完成")
        print("🎊 v3 应用层重构验证成功！")
    else:
        print("🎯 PLAN 47 - 完整终极测试验证: ❌ 需要修复")
    
    sys.exit(0 if success else 1) 