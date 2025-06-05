#!/usr/bin/env python3
"""
修复终极测试文件中的Unicode字符
"""

import os

def fix_unicode_in_file():
    """修复文件中的Unicode字符"""
    file_path = r"v3\tests\integration\test_streamlit_ultimate_user_experience_v3.py"
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换Unicode字符
    replacements = {
        '🧪': '',
        '✅': '',
        '❌': '',
        'ℹ️': '',
        '✅通过': '通过',
        '❌违反': '违反',
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Unicode字符修复完成")

if __name__ == "__main__":
    fix_unicode_in_file() 