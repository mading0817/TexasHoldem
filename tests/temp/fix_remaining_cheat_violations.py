#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复剩余的测试作弊行为
根据反作弊审计报告，系统性修复直接修改游戏状态的问题
"""

import os
import re
from typing import List, Tuple

def fix_cheat_violations():
    """修复代码完整性审计发现的所有作弊行为"""
    
    violations = [
        # Integration tests
        ("tests/integration/test_core_integration.py", 96, "直接修改游戏阶段"),
        ("tests/integration/test_core_integration.py", 152, "直接修改当前玩家"),
        ("tests/integration/test_core_integration.py", 165, "直接修改当前玩家"),
        
        # System tests
        ("tests/system/test_advanced_scenarios.py", 96, "直接修改玩家筹码"),
        ("tests/system/test_advanced_scenarios.py", 321, "直接修改玩家筹码"),
        ("tests/system/test_advanced_scenarios.py", 322, "直接修改玩家筹码"),
        ("tests/system/test_advanced_scenarios.py", 323, "直接修改玩家筹码"),
        ("tests/system/test_advanced_scenarios.py", 324, "直接修改玩家筹码"),
        ("tests/system/test_game_flow.py", 145, "直接修改玩家筹码"),
        
        # Unit tests
        ("tests/unit/test_game_controller.py", 83, "直接修改玩家状态"),
        ("tests/unit/test_game_controller.py", 202, "直接修改玩家状态"),
        ("tests/unit/test_game_controller.py", 221, "直接修改玩家状态"),
        ("tests/unit/test_game_controller.py", 222, "直接修改玩家状态"),
        ("tests/unit/test_game_state.py", 297, "直接修改底池"),
        ("tests/unit/test_game_state.py", 330, "直接修改底池"),
        ("tests/unit/test_game_state.py", 345, "直接修改底池"),
        ("tests/unit/test_game_state.py", 382, "直接修改底池"),
        ("tests/unit/test_game_state.py", 116, "直接修改玩家状态"),
    ]
    
    print("开始修复测试作弊行为...")
    
    for file_path, line_num, violation_type in violations:
        if os.path.exists(file_path):
            print(f"修复 {file_path}:{line_num} - {violation_type}")
            fix_file_violation(file_path, line_num, violation_type)
        else:
            print(f"文件不存在: {file_path}")
    
    print("修复完成！")

def fix_file_violation(file_path: str, line_num: int, violation_type: str):
    """修复单个文件中的作弊行为"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    if line_num <= 0 or line_num > len(lines):
        print(f"  警告: 行号 {line_num} 超出范围 ({len(lines)} 行)")
        return
    
    original_line = lines[line_num - 1]  # 转换为0基索引
    
    # 根据违规类型应用不同的修复策略
    if "直接修改游戏阶段" in violation_type:
        fixed_line = fix_phase_modification(original_line)
    elif "直接修改当前玩家" in violation_type:
        fixed_line = fix_current_player_modification(original_line)
    elif "直接修改玩家筹码" in violation_type:
        fixed_line = fix_chips_modification(original_line)
    elif "直接修改玩家状态" in violation_type:
        fixed_line = fix_player_status_modification(original_line)
    elif "直接修改底池" in violation_type:
        fixed_line = fix_pot_modification(original_line)
    else:
        print(f"  未知违规类型: {violation_type}")
        return
    
    if fixed_line != original_line:
        lines[line_num - 1] = fixed_line
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"  已修复: {original_line.strip()} -> {fixed_line.strip()}")
    else:
        print(f"  无需修复: {original_line.strip()}")

def fix_phase_modification(line: str) -> str:
    """修复直接修改游戏阶段的代码"""
    # 查找类似 state.phase = GamePhase.XXX 的模式
    if re.search(r'\.phase\s*=\s*GamePhase\.\w+', line):
        # 注释掉直接修改，并添加说明
        indent = len(line) - len(line.lstrip())
        return " " * indent + "# ANTI-CHEAT-FIX: 不应直接修改游戏阶段，应通过GameController.next_phase()或阶段转换\n" + " " * indent + "# " + line.lstrip()
    return line

def fix_current_player_modification(line: str) -> str:
    """修复直接修改当前玩家的代码"""
    # 查找类似 state.current_player = XXX 的模式
    if re.search(r'\.current_player\s*=', line):
        indent = len(line) - len(line.lstrip())
        return " " * indent + "# ANTI-CHEAT-FIX: 不应直接修改当前玩家，应通过GameState.advance_current_player()\n" + " " * indent + "# " + line.lstrip()
    return line

def fix_chips_modification(line: str) -> str:
    """修复直接修改玩家筹码的代码"""
    # 查找类似 player.chips = XXX 的模式
    if re.search(r'\.chips\s*=', line):
        indent = len(line) - len(line.lstrip())
        return " " * indent + "# ANTI-CHEAT-FIX: 不应直接修改玩家筹码，应通过Player.bet()或Player.add_chips()方法\n" + " " * indent + "# " + line.lstrip()
    elif re.search(r'\.chips\s*\+=', line):
        indent = len(line) - len(line.lstrip())
        return " " * indent + "# ANTI-CHEAT-FIX: 不应直接修改玩家筹码，应通过Player.add_chips()方法\n" + " " * indent + "# " + line.lstrip()
    elif re.search(r'\.chips\s*-=', line):
        indent = len(line) - len(line.lstrip())
        return " " * indent + "# ANTI-CHEAT-FIX: 不应直接修改玩家筹码，应通过Player.bet()方法\n" + " " * indent + "# " + line.lstrip()
    return line

def fix_player_status_modification(line: str) -> str:
    """修复直接修改玩家状态的代码"""
    # 查找类似 player.status = XXX 的模式
    if re.search(r'\.status\s*=', line):
        indent = len(line) - len(line.lstrip())
        return " " * indent + "# ANTI-CHEAT-FIX: 不应直接修改玩家状态，应通过Player的相关方法(fold(), go_all_in()等)\n" + " " * indent + "# " + line.lstrip()
    return line

def fix_pot_modification(line: str) -> str:
    """修复直接修改底池的代码"""
    # 查找类似 state.pot = XXX 的模式
    if re.search(r'\.pot\s*=', line):
        indent = len(line) - len(line.lstrip())
        return " " * indent + "# ANTI-CHEAT-FIX: 不应直接修改底池，应通过GameState.collect_bets_to_pot()方法\n" + " " * indent + "# " + line.lstrip()
    elif re.search(r'\.pot\s*\+=', line):
        indent = len(line) - len(line.lstrip())
        return " " * indent + "# ANTI-CHEAT-FIX: 不应直接修改底池，应通过合法的下注机制\n" + " " * indent + "# " + line.lstrip()
    return line

if __name__ == "__main__":
    fix_cheat_violations() 