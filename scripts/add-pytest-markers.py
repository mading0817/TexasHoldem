#!/usr/bin/env python3
"""
批量为测试文件添加pytest标记的脚本
"""

import os
import re
from pathlib import Path

def add_markers_to_file(file_path, markers):
    """为测试文件添加pytest标记"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找测试类和测试函数
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        # 检查是否是测试类或测试函数
        if (line.strip().startswith('class Test') or 
            line.strip().startswith('def test_')):
            
            # 检查前面是否已经有标记
            has_markers = False
            for j in range(max(0, i-10), i):
                if '@pytest.mark.' in lines[j]:
                    has_markers = True
                    break
            
            # 如果没有标记，添加标记
            if not has_markers:
                indent = len(line) - len(line.lstrip())
                for marker in markers:
                    new_lines.append(' ' * indent + f'@pytest.mark.{marker}')
        
        new_lines.append(line)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print(f"✅ 已为 {file_path} 添加标记: {', '.join(markers)}")

def main():
    """主函数"""
    base_path = Path('v2/tests')
    
    # 单元测试标记
    unit_markers = ['unit', 'fast']
    unit_test_dir = base_path / 'unit'
    
    if unit_test_dir.exists():
        for test_file in unit_test_dir.glob('test_*.py'):
            add_markers_to_file(test_file, unit_markers)
    
    # 集成测试标记
    integration_markers = ['integration', 'fast']
    integration_test_dir = base_path / 'integration'
    
    if integration_test_dir.exists():
        for test_file in integration_test_dir.glob('test_*.py'):
            add_markers_to_file(test_file, integration_markers)
    
    # 特殊处理端到端测试
    end_to_end_file = integration_test_dir / 'test_end_to_end_integration.py'
    if end_to_end_file.exists():
        # 为端到端测试添加额外标记
        add_markers_to_file(end_to_end_file, ['end_to_end'])
    
    # meta测试标记
    meta_test_dir = base_path / 'meta'
    meta_files_markers = {
        'test_ai_fairness_monitor.py': ['ai_fairness', 'fast'],
        'test_root_cause_analyzer.py': ['root_cause', 'fast'],
    }
    
    if meta_test_dir.exists():
        for filename, markers in meta_files_markers.items():
            file_path = meta_test_dir / filename
            if file_path.exists():
                add_markers_to_file(file_path, markers)
    
    print("\n🎉 所有测试文件标记添加完成！")

if __name__ == '__main__':
    main() 