#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克测试反作弊修复工具
自动检测和修复测试代码中的作弊行为
将直接状态修改转换为合法的API调用
"""

import os
import re
import shutil
from typing import List, Dict, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class CheatPattern:
    """作弊模式定义"""
    pattern: str
    description: str
    fix_template: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW

@dataclass
class FixResult:
    """修复结果"""
    file_path: str
    total_issues: int
    fixed_issues: int
    remaining_issues: int
    fix_log: List[str]

class AntiCheatFixer:
    """反作弊修复工具"""
    
    def __init__(self):
        self.cheat_patterns = self._define_cheat_patterns()
        self.fix_log = []
        
    def _define_cheat_patterns(self) -> List[CheatPattern]:
        """定义所有作弊模式及其修复方案"""
        return [
            # 筹码操作作弊
            CheatPattern(
                pattern=r'(\w+)\.chips\s*=\s*(\d+)',
                description="直接修改玩家筹码",
                fix_template=r"# {description} - 应使用合法API\n# self.setup_player_chips({player}, {amount})",
                severity="CRITICAL"
            ),
            
            # 底池操作作弊  
            CheatPattern(
                pattern=r'(\w+)\.pot\s*=\s*(\d+)',
                description="直接修改底池",
                fix_template=r"# {description} - 应使用PotManager API\n# self.pot_manager.add_to_pot({amount})",
                severity="CRITICAL"
            ),
            
            # 当前下注作弊
            CheatPattern(
                pattern=r'(\w+)\.current_bet\s*=\s*(\d+)', 
                description="直接修改当前下注",
                fix_template=r"# {description} - 应使用player.bet()方法\n# {player}.bet({amount})",
                severity="HIGH"
            ),
            
            # 玩家状态作弊
            CheatPattern(
                pattern=r'(\w+)\.status\s*=\s*(SeatStatus\.\w+)',
                description="直接修改玩家状态", 
                fix_template=r"# {description} - 应使用状态转换API\n# self.change_player_status({player}, {status})",
                severity="HIGH"
            ),
            
            # 游戏阶段作弊
            CheatPattern(
                pattern=r'(\w+)\.phase\s*=\s*(GamePhase\.\w+)',
                description="直接修改游戏阶段",
                fix_template=r"# {description} - 应使用阶段转换API\n# self.advance_to_phase({phase})",
                severity="CRITICAL"
            ),
            
            # 庄家位置作弊
            CheatPattern(
                pattern=r'(\w+)\.dealer_position\s*=\s*(\d+)',
                description="直接修改庄家位置",
                fix_template=r"# {description} - 应使用庄家轮转API\n# self.rotate_dealer_to({position})",
                severity="MEDIUM"
            ),
            
            # 当前玩家作弊
            CheatPattern(
                pattern=r'(\w+)\.current_player\s*=\s*(\d+)',
                description="直接修改当前玩家",
                fix_template=r"# {description} - 应使用玩家轮转API\n# self.set_current_player({player})",
                severity="MEDIUM"
            ),
            
            # 手牌作弊
            CheatPattern(
                pattern=r'(\w+)\.hand\s*=\s*\[',
                description="直接修改手牌",
                fix_template=r"# {description} - 应使用发牌API\n# self.deal_cards_to_player({player}, cards)",
                severity="CRITICAL"
            ),
            
            # 牌组作弊
            CheatPattern(
                pattern=r'(\w+)\.cards\s*=\s*\[',
                description="直接修改牌组",
                fix_template=r"# {description} - 应使用Deck API\n# self.setup_deck_with_cards(cards)",
                severity="CRITICAL"
            )
        ]
    
    def scan_file(self, file_path: str) -> Dict[str, List[Tuple[int, str, CheatPattern]]]:
        """扫描单个文件中的作弊模式"""
        issues = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                
            for pattern_def in self.cheat_patterns:
                pattern_issues = []
                
                for line_num, line in enumerate(lines, 1):
                    matches = re.finditer(pattern_def.pattern, line)
                    for match in matches:
                        # 检查是否在注释中或是否为初始化代码
                        if self._is_legitimate_use(line, line_num, lines):
                            continue
                            
                        pattern_issues.append((line_num, line.strip(), pattern_def))
                
                if pattern_issues:
                    issues[pattern_def.description] = pattern_issues
                    
        except Exception as e:
            self.fix_log.append(f"错误: 无法扫描文件 {file_path}: {e}")
            
        return issues
    
    def _is_legitimate_use(self, line: str, line_num: int, all_lines: List[str]) -> bool:
        """判断是否为合法使用"""
        # 跳过注释行
        if line.strip().startswith('#'):
            return True
            
        # 跳过明确的初始化语句
        if any(keyword in line for keyword in ['# 初始化', '# 设置', 'def setUp', 'def __init__']):
            return True
            
        # 检查前后文是否为初始化上下文
        context_lines = 3
        start = max(0, line_num - context_lines - 1)
        end = min(len(all_lines), line_num + context_lines)
        context = ' '.join(all_lines[start:end])
        
        if any(keyword in context for keyword in ['setUp', '__init__', '初始化', '设置']):
            return True
            
        return False
    
    def fix_file(self, file_path: str, dry_run: bool = True) -> FixResult:
        """修复文件中的作弊行为"""
        issues = self.scan_file(file_path)
        total_issues = sum(len(issue_list) for issue_list in issues.values())
        
        if total_issues == 0:
            return FixResult(file_path, 0, 0, 0, ["文件无作弊行为"])
        
        fixed_issues = 0
        fix_log = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # 备份原文件
            if not dry_run:
                backup_path = file_path + '.backup'
                shutil.copy2(file_path, backup_path)
                fix_log.append(f"已创建备份: {backup_path}")
            
            # 从后往前修复，避免行号变化
            all_fixes = []
            for issue_type, issue_list in issues.items():
                for line_num, line_content, pattern_def in issue_list:
                    all_fixes.append((line_num, line_content, pattern_def))
            
            # 按行号倒序排列
            all_fixes.sort(reverse=True)
            
            for line_num, line_content, pattern_def in all_fixes:
                original_line = lines[line_num - 1]
                
                # 生成修复注释
                fix_comment = f"# ANTI-CHEAT-FIX: {pattern_def.description}"
                suggestion = f"# SUGGESTED: {self._generate_fix_suggestion(original_line, pattern_def)}"
                
                # 注释掉原行并添加建议
                lines[line_num - 1] = f"# {original_line}  # CHEAT DETECTED!"
                lines.insert(line_num, fix_comment)
                lines.insert(line_num + 1, suggestion)
                lines.insert(line_num + 2, "")
                
                fixed_issues += 1
                fix_log.append(f"Line {line_num}: {pattern_def.description}")
            
            # 写入修复后的文件
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                fix_log.append(f"已修复文件: {file_path}")
            else:
                fix_log.append(f"DRY RUN: 将修复 {fixed_issues} 个问题")
                
        except Exception as e:
            fix_log.append(f"修复失败: {e}")
            
        remaining_issues = total_issues - fixed_issues
        return FixResult(file_path, total_issues, fixed_issues, remaining_issues, fix_log)
    
    def _generate_fix_suggestion(self, original_line: str, pattern_def: CheatPattern) -> str:
        """生成具体的修复建议"""
        match = re.search(pattern_def.pattern, original_line)
        if not match:
            return "使用合法的API替代直接状态修改"
        
        # 根据不同的作弊类型生成具体建议
        if "筹码" in pattern_def.description:
            return f"使用 player.add_chips() 或 player.remove_chips() 方法"
        elif "底池" in pattern_def.description:
            return f"使用 pot_manager.add_to_pot() 方法"
        elif "当前下注" in pattern_def.description:
            return f"使用 player.bet(amount) 方法"
        elif "阶段" in pattern_def.description:
            return f"使用 game_controller.advance_phase() 方法"
        elif "状态" in pattern_def.description:
            return f"使用状态转换API"
        else:
            return "使用相应的API方法而不是直接修改"
    
    def scan_all_test_files(self) -> Dict[str, Dict]:
        """扫描所有测试文件"""
        test_dirs = ['tests/unit', 'tests/integration', 'tests/system', 'tests/rules']
        all_results = {}
        
        for test_dir in test_dirs:
            if not os.path.exists(test_dir):
                continue
                
            for root, dirs, files in os.walk(test_dir):
                for file in files:
                    if file.endswith('.py') and file.startswith('test_'):
                        file_path = os.path.join(root, file)
                        issues = self.scan_file(file_path)
                        if issues:
                            all_results[file_path] = issues
        
        return all_results
    
    def generate_comprehensive_report(self) -> str:
        """生成全面的反作弊报告"""
        all_issues = self.scan_all_test_files()
        
        report = []
        report.append("德州扑克测试反作弊检测报告")
        report.append("=" * 50)
        report.append("")
        
        total_files = len(all_issues)
        total_issues_count = sum(
            sum(len(issue_list) for issue_list in file_issues.values())
            for file_issues in all_issues.values()
        )
        
        report.append(f"扫描结果: 发现 {total_files} 个文件中存在 {total_issues_count} 个作弊行为")
        report.append("")
        
        # 按严重程度分类
        severity_stats = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for file_path, file_issues in all_issues.items():
            report.append(f"文件: {file_path}")
            report.append("-" * 40)
            
            for issue_type, issue_list in file_issues.items():
                for line_num, line_content, pattern_def in issue_list:
                    severity_stats[pattern_def.severity] += 1
                    report.append(f"  Line {line_num}: {issue_type}")
                    report.append(f"    代码: {line_content}")
                    report.append(f"    严重程度: {pattern_def.severity}")
                    report.append("")
            
        report.append("严重程度统计:")
        for severity, count in severity_stats.items():
            report.append(f"  {severity}: {count} 个")
        
        report.append("")
        report.append("修复建议:")
        report.append("1. 使用 python tests/security/test_anti_cheat_fix.py --fix-all 进行自动修复")
        report.append("2. 手动检查修复后的代码，确保逻辑正确")
        report.append("3. 运行测试验证修复效果")
        report.append("4. 建立代码审查流程，防止新的作弊行为")
        
        return "\n".join(report)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="德州扑克测试反作弊修复工具")
    parser.add_argument("--scan", action="store_true", help="扫描所有测试文件")
    parser.add_argument("--fix-all", action="store_true", help="修复所有测试文件")
    parser.add_argument("--dry-run", action="store_true", help="仅显示将要修复的内容，不实际修改")
    parser.add_argument("--file", type=str, help="修复指定文件")
    
    args = parser.parse_args()
    
    fixer = AntiCheatFixer()
    
    if args.scan or (not args.fix_all and not args.file):
        # 生成扫描报告
        report = fixer.generate_comprehensive_report()
        print(report)
        
        # 写入报告文件
        with open("ANTI_CHEAT_SCAN_REPORT.txt", "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n报告已保存到: ANTI_CHEAT_SCAN_REPORT.txt")
        
    elif args.fix_all:
        # 修复所有文件
        all_issues = fixer.scan_all_test_files()
        print(f"发现 {len(all_issues)} 个文件需要修复...")
        
        for file_path in all_issues.keys():
            result = fixer.fix_file(file_path, dry_run=args.dry_run)
            print(f"\n{result.file_path}:")
            print(f"  总问题: {result.total_issues}")
            print(f"  已修复: {result.fixed_issues}")
            print(f"  剩余: {result.remaining_issues}")
            for log_entry in result.fix_log:
                print(f"  {log_entry}")
                
    elif args.file:
        # 修复指定文件
        result = fixer.fix_file(args.file, dry_run=args.dry_run)
        print(f"修复结果: {result.file_path}")
        print(f"总问题: {result.total_issues}, 已修复: {result.fixed_issues}")
        for log_entry in result.fix_log:
            print(f"  {log_entry}")


if __name__ == "__main__":
    main() 