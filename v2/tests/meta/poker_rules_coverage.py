"""
德州扑克规则覆盖率监控系统

该模块负责监控测试用例对德州扑克规则的覆盖情况，确保所有规则分支都有对应的测试覆盖。
基于 TexasHoldemGameRule.md 建立完整的规则场景清单。
"""

import json
import re
import ast
import inspect
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
import importlib.util


class RuleCategory(Enum):
    """规则类别枚举"""
    BASIC_FLOW = "basic_flow"           # 基本流程
    BETTING_RULES = "betting_rules"     # 下注规则
    HAND_RANKINGS = "hand_rankings"     # 牌型排名
    SIDE_POT = "side_pot"              # 边池规则
    SHOWDOWN = "showdown"              # 摊牌规则
    SPECIAL_CASES = "special_cases"     # 特殊情况
    TOURNAMENT = "tournament"           # 锦标赛规则


class CoverageStatus(Enum):
    """覆盖状态枚举"""
    COVERED = "covered"                 # 已覆盖
    PARTIAL = "partial"                 # 部分覆盖
    NOT_COVERED = "not_covered"         # 未覆盖
    UNKNOWN = "unknown"                 # 未知状态


@dataclass
class RuleScenario:
    """规则场景数据类"""
    rule_id: str
    category: RuleCategory
    description: str
    requirements: List[str]
    test_patterns: List[str]  # 用于识别相关测试的模式
    priority: str  # HIGH, MEDIUM, LOW
    covered_by: List[str] = None  # 覆盖该规则的测试用例
    coverage_status: CoverageStatus = CoverageStatus.UNKNOWN
    
    def __post_init__(self):
        if self.covered_by is None:
            self.covered_by = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        result['category'] = self.category.value
        result['coverage_status'] = self.coverage_status.value
        return result


@dataclass
class CoverageReport:
    """覆盖率报告"""
    timestamp: str
    total_rules: int
    covered_rules: int
    partial_rules: int
    uncovered_rules: int
    coverage_percentage: float
    category_coverage: Dict[str, Dict[str, int]]
    priority_coverage: Dict[str, Dict[str, int]]
    detailed_scenarios: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


class PokerRulesCoverageMonitor:
    """
    德州扑克规则覆盖率监控器
    
    负责监控测试用例对德州扑克规则的覆盖情况。
    """
    
    def __init__(self, project_root: str = None):
        """
        初始化规则覆盖率监控器
        
        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.rule_scenarios = self._initialize_rule_scenarios()
        self.test_files = []
        self.coverage_report = None
        
    def _initialize_rule_scenarios(self) -> List[RuleScenario]:
        """初始化德州扑克规则场景清单"""
        scenarios = []
        
        # 基本流程规则
        scenarios.extend([
            RuleScenario(
                rule_id="BF001",
                category=RuleCategory.BASIC_FLOW,
                description="庄家按钮顺时针移动",
                requirements=["每手牌开始前庄家按钮顺时针移动一位"],
                test_patterns=["dealer", "button", "rotate", "clockwise"],
                priority="HIGH"
            ),
            RuleScenario(
                rule_id="BF002",
                category=RuleCategory.BASIC_FLOW,
                description="盲注设置和位置",
                requirements=["小盲注为大盲注的一半", "盲注位置正确"],
                test_patterns=["blind", "small_blind", "big_blind"],
                priority="HIGH"
            ),
            RuleScenario(
                rule_id="BF003",
                category=RuleCategory.BASIC_FLOW,
                description="发牌阶段顺序",
                requirements=["底牌→翻牌→转牌→河牌的正确顺序"],
                test_patterns=["hole_cards", "flop", "turn", "river", "stage"],
                priority="HIGH"
            ),
            RuleScenario(
                rule_id="BF004",
                category=RuleCategory.BASIC_FLOW,
                description="下注轮次顺序",
                requirements=["翻牌前从大盲注左侧开始", "翻牌后从庄家左侧开始"],
                test_patterns=["betting_order", "action_order", "position"],
                priority="HIGH"
            ),
        ])
        
        # 下注规则
        scenarios.extend([
            RuleScenario(
                rule_id="BR001",
                category=RuleCategory.BETTING_RULES,
                description="弃牌操作",
                requirements=["玩家可以弃牌退出当前手牌"],
                test_patterns=["fold", "弃牌"],
                priority="HIGH"
            ),
            RuleScenario(
                rule_id="BR002",
                category=RuleCategory.BETTING_RULES,
                description="看牌操作",
                requirements=["无人下注时可以看牌"],
                test_patterns=["check", "看牌"],
                priority="HIGH"
            ),
            RuleScenario(
                rule_id="BR003",
                category=RuleCategory.BETTING_RULES,
                description="跟注操作",
                requirements=["匹配当前最高下注金额"],
                test_patterns=["call", "跟注"],
                priority="HIGH"
            ),
            RuleScenario(
                rule_id="BR004",
                category=RuleCategory.BETTING_RULES,
                description="加注操作",
                requirements=["在当前下注基础上增加下注金额"],
                test_patterns=["raise", "加注", "bet"],
                priority="HIGH"
            ),
            RuleScenario(
                rule_id="BR005",
                category=RuleCategory.BETTING_RULES,
                description="全押操作",
                requirements=["将所有筹码投入底池"],
                test_patterns=["all_in", "全押", "allin"],
                priority="HIGH"
            ),
            RuleScenario(
                rule_id="BR006",
                category=RuleCategory.BETTING_RULES,
                description="最低加注额限制",
                requirements=["加注金额不得低于前一次加注的金额"],
                test_patterns=["minimum_raise", "raise_amount", "min_bet"],
                priority="MEDIUM"
            ),
        ])
        
        # 牌型排名规则
        scenarios.extend([
            RuleScenario(
                rule_id="HR001",
                category=RuleCategory.HAND_RANKINGS,
                description="皇家同花顺",
                requirements=["同一花色的A、K、Q、J、10"],
                test_patterns=["royal_flush", "皇家同花顺"],
                priority="MEDIUM"
            ),
            RuleScenario(
                rule_id="HR002",
                category=RuleCategory.HAND_RANKINGS,
                description="同花顺",
                requirements=["同一花色的连续五张牌"],
                test_patterns=["straight_flush", "同花顺"],
                priority="MEDIUM"
            ),
            RuleScenario(
                rule_id="HR003",
                category=RuleCategory.HAND_RANKINGS,
                description="四条",
                requirements=["四张相同点数的牌"],
                test_patterns=["four_of_a_kind", "四条", "quads"],
                priority="MEDIUM"
            ),
            RuleScenario(
                rule_id="HR004",
                category=RuleCategory.HAND_RANKINGS,
                description="葫芦",
                requirements=["三张相同点数的牌加一对"],
                test_patterns=["full_house", "葫芦", "boat"],
                priority="MEDIUM"
            ),
            RuleScenario(
                rule_id="HR005",
                category=RuleCategory.HAND_RANKINGS,
                description="同花",
                requirements=["五张同一花色的非连续牌"],
                test_patterns=["flush", "同花"],
                priority="MEDIUM"
            ),
            RuleScenario(
                rule_id="HR006",
                category=RuleCategory.HAND_RANKINGS,
                description="顺子",
                requirements=["五张连续点数的非同花色牌"],
                test_patterns=["straight", "顺子"],
                priority="MEDIUM"
            ),
            RuleScenario(
                rule_id="HR007",
                category=RuleCategory.HAND_RANKINGS,
                description="三条",
                requirements=["三张相同点数的牌"],
                test_patterns=["three_of_a_kind", "三条", "trips", "set"],
                priority="MEDIUM"
            ),
            RuleScenario(
                rule_id="HR008",
                category=RuleCategory.HAND_RANKINGS,
                description="两对",
                requirements=["两组不同点数的对子"],
                test_patterns=["two_pair", "两对"],
                priority="MEDIUM"
            ),
            RuleScenario(
                rule_id="HR009",
                category=RuleCategory.HAND_RANKINGS,
                description="一对",
                requirements=["两张相同点数的牌"],
                test_patterns=["one_pair", "一对", "pair"],
                priority="MEDIUM"
            ),
            RuleScenario(
                rule_id="HR010",
                category=RuleCategory.HAND_RANKINGS,
                description="高牌",
                requirements=["无法组成上述任何牌型的最高单张牌"],
                test_patterns=["high_card", "高牌", "kicker"],
                priority="MEDIUM"
            ),
        ])
        
        # 边池规则
        scenarios.extend([
            RuleScenario(
                rule_id="SP001",
                category=RuleCategory.SIDE_POT,
                description="边池创建",
                requirements=["全押玩家触发边池创建"],
                test_patterns=["side_pot", "边池", "all_in"],
                priority="HIGH"
            ),
            RuleScenario(
                rule_id="SP002",
                category=RuleCategory.SIDE_POT,
                description="主池分配",
                requirements=["所有玩家按最小全押金额匹配"],
                test_patterns=["main_pot", "主池"],
                priority="HIGH"
            ),
            RuleScenario(
                rule_id="SP003",
                category=RuleCategory.SIDE_POT,
                description="多边池处理",
                requirements=["多个全押玩家的复杂边池分配"],
                test_patterns=["multiple_side_pot", "多边池"],
                priority="MEDIUM"
            ),
        ])
        
        # 摊牌规则
        scenarios.extend([
            RuleScenario(
                rule_id="SD001",
                category=RuleCategory.SHOWDOWN,
                description="摊牌顺序",
                requirements=["最后下注者首先亮牌，或从庄家左侧开始"],
                test_patterns=["showdown", "摊牌", "reveal"],
                priority="MEDIUM"
            ),
            RuleScenario(
                rule_id="SD002",
                category=RuleCategory.SHOWDOWN,
                description="牌型比较",
                requirements=["正确比较牌型大小和踢脚牌"],
                test_patterns=["hand_comparison", "牌型比较", "kicker"],
                priority="HIGH"
            ),
            RuleScenario(
                rule_id="SD003",
                category=RuleCategory.SHOWDOWN,
                description="平分底池",
                requirements=["相同牌型时平分底池"],
                test_patterns=["split_pot", "平分", "tie"],
                priority="MEDIUM"
            ),
        ])
        
        # 特殊情况
        scenarios.extend([
            RuleScenario(
                rule_id="SC001",
                category=RuleCategory.SPECIAL_CASES,
                description="使用公共牌",
                requirements=["玩家可选择使用0-2张底牌与公共牌组合"],
                test_patterns=["community_cards", "公共牌", "board"],
                priority="MEDIUM"
            ),
            RuleScenario(
                rule_id="SC002",
                category=RuleCategory.SPECIAL_CASES,
                description="打公牌",
                requirements=["最佳手牌仅由公共牌组成时平分底池"],
                test_patterns=["play_board", "打公牌"],
                priority="LOW"
            ),
            RuleScenario(
                rule_id="SC003",
                category=RuleCategory.SPECIAL_CASES,
                description="筹码守恒",
                requirements=["游戏过程中筹码总数保持不变"],
                test_patterns=["chip_conservation", "筹码守恒"],
                priority="HIGH"
            ),
        ])
        
        return scenarios
    
    def scan_test_files(self, test_directory: str = "v2/tests") -> List[str]:
        """
        扫描测试文件
        
        Args:
            test_directory: 测试目录路径
            
        Returns:
            测试文件路径列表
        """
        test_dir = self.project_root / test_directory
        test_files = []
        
        for file_path in test_dir.rglob("*.py"):
            if file_path.name.startswith("test_") or file_path.name.endswith("_test.py"):
                test_files.append(str(file_path))
        
        self.test_files = test_files
        return test_files
    
    def analyze_test_coverage(self) -> CoverageReport:
        """
        分析测试覆盖率
        
        Returns:
            覆盖率报告
        """
        if not self.test_files:
            self.scan_test_files()
        
        # 重置覆盖状态
        for scenario in self.rule_scenarios:
            scenario.covered_by = []
            scenario.coverage_status = CoverageStatus.NOT_COVERED
        
        # 分析每个测试文件
        for test_file in self.test_files:
            self._analyze_single_test_file(test_file)
        
        # 更新覆盖状态
        self._update_coverage_status()
        
        # 生成报告
        return self._generate_coverage_report()
    
    def _analyze_single_test_file(self, test_file: str):
        """分析单个测试文件"""
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析AST
            tree = ast.parse(content)
            
            # 提取测试函数和类
            test_functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    test_functions.append(node.name)
                elif isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                            test_functions.append(f"{node.name}.{item.name}")
            
            # 检查每个规则场景
            for scenario in self.rule_scenarios:
                for pattern in scenario.test_patterns:
                    if self._check_pattern_in_content(pattern, content, test_functions):
                        scenario.covered_by.append(f"{Path(test_file).name}::{pattern}")
                        break
        
        except Exception as e:
            print(f"分析测试文件时出错 {test_file}: {e}")
    
    def _check_pattern_in_content(self, pattern: str, content: str, test_functions: List[str]) -> bool:
        """检查模式是否在内容中出现"""
        # 检查文件内容
        if re.search(pattern, content, re.IGNORECASE):
            return True
        
        # 检查测试函数名
        for func_name in test_functions:
            if re.search(pattern, func_name, re.IGNORECASE):
                return True
        
        return False
    
    def _update_coverage_status(self):
        """更新覆盖状态"""
        for scenario in self.rule_scenarios:
            if len(scenario.covered_by) >= len(scenario.requirements):
                scenario.coverage_status = CoverageStatus.COVERED
            elif len(scenario.covered_by) > 0:
                scenario.coverage_status = CoverageStatus.PARTIAL
            else:
                scenario.coverage_status = CoverageStatus.NOT_COVERED
    
    def _generate_coverage_report(self) -> CoverageReport:
        """生成覆盖率报告"""
        total_rules = len(self.rule_scenarios)
        covered_rules = sum(1 for s in self.rule_scenarios if s.coverage_status == CoverageStatus.COVERED)
        partial_rules = sum(1 for s in self.rule_scenarios if s.coverage_status == CoverageStatus.PARTIAL)
        uncovered_rules = sum(1 for s in self.rule_scenarios if s.coverage_status == CoverageStatus.NOT_COVERED)
        
        coverage_percentage = (covered_rules / total_rules * 100) if total_rules > 0 else 0
        
        # 按类别统计
        category_coverage = {}
        for category in RuleCategory:
            category_scenarios = [s for s in self.rule_scenarios if s.category == category]
            if category_scenarios:
                category_covered = sum(1 for s in category_scenarios if s.coverage_status == CoverageStatus.COVERED)
                category_partial = sum(1 for s in category_scenarios if s.coverage_status == CoverageStatus.PARTIAL)
                category_uncovered = sum(1 for s in category_scenarios if s.coverage_status == CoverageStatus.NOT_COVERED)
                
                category_coverage[category.value] = {
                    "total": len(category_scenarios),
                    "covered": category_covered,
                    "partial": category_partial,
                    "uncovered": category_uncovered,
                    "percentage": (category_covered / len(category_scenarios) * 100) if category_scenarios else 0
                }
        
        # 按优先级统计
        priority_coverage = {}
        for priority in ["HIGH", "MEDIUM", "LOW"]:
            priority_scenarios = [s for s in self.rule_scenarios if s.priority == priority]
            if priority_scenarios:
                priority_covered = sum(1 for s in priority_scenarios if s.coverage_status == CoverageStatus.COVERED)
                priority_partial = sum(1 for s in priority_scenarios if s.coverage_status == CoverageStatus.PARTIAL)
                priority_uncovered = sum(1 for s in priority_scenarios if s.coverage_status == CoverageStatus.NOT_COVERED)
                
                priority_coverage[priority] = {
                    "total": len(priority_scenarios),
                    "covered": priority_covered,
                    "partial": priority_partial,
                    "uncovered": priority_uncovered,
                    "percentage": (priority_covered / len(priority_scenarios) * 100) if priority_scenarios else 0
                }
        
        self.coverage_report = CoverageReport(
            timestamp=datetime.now().isoformat(),
            total_rules=total_rules,
            covered_rules=covered_rules,
            partial_rules=partial_rules,
            uncovered_rules=uncovered_rules,
            coverage_percentage=coverage_percentage,
            category_coverage=category_coverage,
            priority_coverage=priority_coverage,
            detailed_scenarios=[s.to_dict() for s in self.rule_scenarios]
        )
        
        return self.coverage_report
    
    def generate_coverage_report_text(self) -> str:
        """生成文本格式的覆盖率报告"""
        if not self.coverage_report:
            self.analyze_test_coverage()
        
        report = self.coverage_report
        lines = []
        
        lines.append("📊 德州扑克规则覆盖率报告")
        lines.append("=" * 60)
        lines.append(f"生成时间: {report.timestamp}")
        lines.append(f"总规则数: {report.total_rules}")
        lines.append(f"已覆盖: {report.covered_rules}")
        lines.append(f"部分覆盖: {report.partial_rules}")
        lines.append(f"未覆盖: {report.uncovered_rules}")
        lines.append(f"覆盖率: {report.coverage_percentage:.1f}%")
        lines.append("")
        
        # 按类别统计
        lines.append("📈 按类别覆盖率:")
        lines.append("-" * 40)
        for category, stats in report.category_coverage.items():
            lines.append(f"{category}: {stats['covered']}/{stats['total']} ({stats['percentage']:.1f}%)")
        lines.append("")
        
        # 按优先级统计
        lines.append("🎯 按优先级覆盖率:")
        lines.append("-" * 40)
        for priority, stats in report.priority_coverage.items():
            lines.append(f"{priority}: {stats['covered']}/{stats['total']} ({stats['percentage']:.1f}%)")
        lines.append("")
        
        # 未覆盖的高优先级规则
        high_priority_uncovered = [
            s for s in self.rule_scenarios 
            if s.priority == "HIGH" and s.coverage_status == CoverageStatus.NOT_COVERED
        ]
        
        if high_priority_uncovered:
            lines.append("🚨 未覆盖的高优先级规则:")
            lines.append("-" * 40)
            for scenario in high_priority_uncovered:
                lines.append(f"• {scenario.rule_id}: {scenario.description}")
            lines.append("")
        
        # 部分覆盖的规则
        partial_covered = [
            s for s in self.rule_scenarios 
            if s.coverage_status == CoverageStatus.PARTIAL
        ]
        
        if partial_covered:
            lines.append("⚠️ 部分覆盖的规则:")
            lines.append("-" * 40)
            for scenario in partial_covered:
                lines.append(f"• {scenario.rule_id}: {scenario.description}")
                lines.append(f"  覆盖测试: {', '.join(scenario.covered_by)}")
            lines.append("")
        
        # 建议
        lines.append("💡 改进建议:")
        lines.append("-" * 40)
        if report.coverage_percentage < 80:
            lines.append("• 覆盖率偏低，建议优先补充高优先级规则的测试用例")
        if high_priority_uncovered:
            lines.append("• 存在未覆盖的高优先级规则，建议立即补充相关测试")
        if partial_covered:
            lines.append("• 存在部分覆盖的规则，建议完善测试用例以达到完全覆盖")
        if report.coverage_percentage >= 95:
            lines.append("• 覆盖率优秀！建议维持当前测试质量")
        
        return "\n".join(lines)
    
    def export_coverage_report(self, output_file: str):
        """
        导出覆盖率报告到JSON文件
        
        Args:
            output_file: 输出文件路径
        """
        if not self.coverage_report:
            self.analyze_test_coverage()
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.coverage_report.to_dict(), f, indent=2, ensure_ascii=False)
    
    def get_missing_test_scenarios(self) -> List[RuleScenario]:
        """
        获取缺失测试的场景
        
        Returns:
            缺失测试的规则场景列表
        """
        if not self.coverage_report:
            self.analyze_test_coverage()
        
        return [
            s for s in self.rule_scenarios 
            if s.coverage_status == CoverageStatus.NOT_COVERED
        ]
    
    def suggest_test_cases(self) -> List[str]:
        """
        建议需要添加的测试用例
        
        Returns:
            测试用例建议列表
        """
        missing_scenarios = self.get_missing_test_scenarios()
        suggestions = []
        
        for scenario in missing_scenarios:
            suggestions.append(f"测试用例建议: test_{scenario.rule_id.lower()}")
            suggestions.append(f"  规则: {scenario.description}")
            suggestions.append(f"  要求: {', '.join(scenario.requirements)}")
            suggestions.append(f"  优先级: {scenario.priority}")
            suggestions.append("")
        
        return suggestions


def main():
    """主函数，演示规则覆盖率监控功能"""
    print("🎯 德州扑克规则覆盖率监控")
    print("=" * 50)
    
    # 创建监控器
    monitor = PokerRulesCoverageMonitor()
    
    # 扫描测试文件
    test_files = monitor.scan_test_files()
    print(f"📁 扫描到 {len(test_files)} 个测试文件")
    
    # 分析覆盖率
    report = monitor.analyze_test_coverage()
    
    # 生成报告
    text_report = monitor.generate_coverage_report_text()
    print(text_report)
    
    # 导出JSON报告
    json_file = "test-reports/poker-rules-coverage.json"
    monitor.export_coverage_report(json_file)
    print(f"📊 JSON报告已导出到: {json_file}")
    
    # 生成测试用例建议
    suggestions = monitor.suggest_test_cases()
    if suggestions:
        print("\n💡 测试用例建议:")
        print("-" * 30)
        for suggestion in suggestions[:10]:  # 只显示前10个建议
            print(suggestion)


if __name__ == "__main__":
    main()