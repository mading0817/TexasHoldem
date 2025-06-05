#!/usr/bin/env python3
"""
快速终极测试验证
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def run_quick_ultimate_test():
    """运行快速终极测试"""
    try:
        from v3.tests.integration.test_streamlit_ultimate_user_experience_v3 import test_streamlit_ultimate_user_experience_v3_quick
        
        print("开始运行快速终极测试...")
        test_streamlit_ultimate_user_experience_v3_quick()
        print("✅ 快速终极测试通过!")
        return True
    except Exception as e:
        print(f"❌ 快速终极测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_quick_ultimate_test()
    if success:
        print("\n🎉 PLAN B修复验证成功! 游戏流程已恢复正常!")
    else:
        print("\n⚠️ 测试失败，需要进一步检查") 