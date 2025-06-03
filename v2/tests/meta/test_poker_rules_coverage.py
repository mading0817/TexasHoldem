"""
德州扑克规则覆盖率监控器测试

测试 PokerRulesCoverageMonitor 类的所有功能，确保规则覆盖率监控正确工作。
"""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from v2.tests.meta.poker_rules_coverage import (
    PokerRulesCoverageMonitor,
    RuleCategory,
    CoverageStatus,
    RuleScenario,
    CoverageReport
)


@pytest.mark.rule_coverage
@pytest.mark.fast
class TestRuleScenario:
    """测试 RuleScenario 数据类"""
    
    @pytest.mark.rule_coverage
    def test_rule_scenario_creation(self):
        """测试规则场景创建"""
        scenario = RuleScenario(
            rule_id="TEST001",
            category=RuleCategory.BASIC_FLOW,
            description="测试规则",
            requirements=["要求1", "要求2"],
            test_patterns=["pattern1", "pattern2"],
            priority="HIGH"
        )
        
        assert scenario.rule_id == "TEST001"
        assert scenario.category == RuleCategory.BASIC_FLOW
        assert scenario.description == "测试规则"
        assert scenario.requirements == ["要求1", "要求2"]
        assert scenario.test_patterns == ["pattern1", "pattern2"]
        assert scenario.priority == "HIGH"
        assert scenario.covered_by == []
        assert scenario.coverage_status == CoverageStatus.UNKNOWN
    
    @pytest.mark.rule_coverage
    def test_rule_scenario_to_dict(self):
        """测试规则场景转换为字典"""
        scenario = RuleScenario(
            rule_id="TEST001",
            category=RuleCategory.BETTING_RULES,
            description="测试规则",
            requirements=["要求1"],
            test_patterns=["pattern1"],
            priority="MEDIUM"
        )
        scenario.coverage_status = CoverageStatus.COVERED
        scenario.covered_by = ["test_file.py::pattern1"]
        
        result = scenario.to_dict()
        
        assert result["rule_id"] == "TEST001"
        assert result["category"] == "betting_rules"
        assert result["coverage_status"] == "covered"
        assert result["covered_by"] == ["test_file.py::pattern1"]


@pytest.mark.rule_coverage
@pytest.mark.fast
class TestCoverageReport:
    """测试 CoverageReport 数据类"""
    
    @pytest.mark.rule_coverage
    def test_coverage_report_creation(self):
        """测试覆盖率报告创建"""
        report = CoverageReport(
            timestamp="2025-06-02T12:00:00",
            total_rules=10,
            covered_rules=8,
            partial_rules=1,
            uncovered_rules=1,
            coverage_percentage=80.0,
            category_coverage={"basic_flow": {"total": 5, "covered": 4}},
            priority_coverage={"HIGH": {"total": 3, "covered": 3}},
            detailed_scenarios=[]
        )
        
        assert report.total_rules == 10
        assert report.covered_rules == 8
        assert report.coverage_percentage == 80.0
    
    @pytest.mark.rule_coverage
    def test_coverage_report_to_dict(self):
        """测试覆盖率报告转换为字典"""
        report = CoverageReport(
            timestamp="2025-06-02T12:00:00",
            total_rules=5,
            covered_rules=3,
            partial_rules=1,
            uncovered_rules=1,
            coverage_percentage=60.0,
            category_coverage={},
            priority_coverage={},
            detailed_scenarios=[]
        )
        
        result = report.to_dict()
        
        assert isinstance(result, dict)
        assert result["total_rules"] == 5
        assert result["coverage_percentage"] == 60.0


@pytest.mark.rule_coverage
@pytest.mark.critical
class TestPokerRulesCoverageMonitor:
    """测试 PokerRulesCoverageMonitor 类"""
    
    def setup_method(self):
        """测试前设置"""
        self.monitor = PokerRulesCoverageMonitor()
    
    @pytest.mark.rule_coverage
    @pytest.mark.fast
    def test_monitor_initialization(self):
        """测试监控器初始化"""
        assert self.monitor.project_root == Path.cwd()
        assert len(self.monitor.rule_scenarios) > 0
        assert self.monitor.test_files == []
        assert self.monitor.coverage_report is None
    
    @pytest.mark.rule_coverage
    @pytest.mark.fast
    def test_rule_scenarios_initialization(self):
        """测试规则场景初始化"""
        scenarios = self.monitor.rule_scenarios
        
        # 检查是否包含所有类别
        categories = {s.category for s in scenarios}
        expected_categories = {
            RuleCategory.BASIC_FLOW,
            RuleCategory.BETTING_RULES,
            RuleCategory.HAND_RANKINGS,
            RuleCategory.SIDE_POT,
            RuleCategory.SHOWDOWN,
            RuleCategory.SPECIAL_CASES
        }
        assert expected_categories.issubset(categories)
        
        # 检查是否有高优先级规则
        high_priority_rules = [s for s in scenarios if s.priority == "HIGH"]
        assert len(high_priority_rules) > 0
        
        # 检查基本流程规则
        basic_flow_rules = [s for s in scenarios if s.category == RuleCategory.BASIC_FLOW]
        assert len(basic_flow_rules) >= 4
        
        # 检查下注规则
        betting_rules = [s for s in scenarios if s.category == RuleCategory.BETTING_RULES]
        assert len(betting_rules) >= 6
        
        # 检查牌型规则
        hand_ranking_rules = [s for s in scenarios if s.category == RuleCategory.HAND_RANKINGS]
        assert len(hand_ranking_rules) >= 10
    
    @pytest.mark.rule_coverage
    @pytest.mark.fast
    def test_scan_test_files(self):
        """测试扫描测试文件"""
        # 使用实际的测试目录
        test_files = self.monitor.scan_test_files("v2/tests")
        
        assert len(test_files) > 0
        assert all(file.endswith('.py') for file in test_files)
        # 只检查实际的测试文件，而不是所有Python文件
        test_files_only = [f for f in test_files if 'test_' in Path(f).name]
        assert len(test_files_only) > 0, "应该找到至少一个测试文件"
    
    @patch('builtins.open', new_callable=mock_open, read_data="""
def test_fold_action():
    '''测试弃牌操作'''
    player.fold()
    assert player.is_folded

def test_check_action():
    '''测试看牌操作'''
    player.check()
    assert not player.has_bet

class TestHandRankings:
    def test_royal_flush(self):
        '''测试皇家同花顺'''
        hand = create_royal_flush()
        assert hand.rank == HandRank.ROYAL_FLUSH
    
    def test_straight_flush(self):
        '''测试同花顺'''
        hand = create_straight_flush()
        assert hand.rank == HandRank.STRAIGHT_FLUSH
""")
    @pytest.mark.rule_coverage
    @pytest.mark.fast
    def test_analyze_single_test_file(self, mock_file):
        """测试分析单个测试文件"""
        # 重置覆盖状态
        for scenario in self.monitor.rule_scenarios:
            scenario.covered_by = []
        
        # 分析模拟的测试文件
        self.monitor._analyze_single_test_file("test_mock.py")
        
        # 检查弃牌规则是否被覆盖
        fold_scenarios = [s for s in self.monitor.rule_scenarios if "fold" in s.test_patterns]
        if fold_scenarios:
            assert any(len(s.covered_by) > 0 for s in fold_scenarios)
        
        # 检查看牌规则是否被覆盖
        check_scenarios = [s for s in self.monitor.rule_scenarios if "check" in s.test_patterns]
        if check_scenarios:
            assert any(len(s.covered_by) > 0 for s in check_scenarios)
    
    def test_check_pattern_in_content(self):
        """测试模式检查"""
        content = """
        def test_fold_operation():
            player.fold()
            assert player.is_folded
        """
        test_functions = ["test_fold_operation"]
        
        # 测试内容匹配
        assert self.monitor._check_pattern_in_content("fold", content, test_functions)
        assert not self.monitor._check_pattern_in_content("raise", content, test_functions)
        
        # 测试函数名匹配
        assert self.monitor._check_pattern_in_content("fold", "", test_functions)
    
    def test_update_coverage_status(self):
        """测试更新覆盖状态"""
        # 创建测试场景
        scenario1 = RuleScenario(
            rule_id="TEST001",
            category=RuleCategory.BASIC_FLOW,
            description="完全覆盖",
            requirements=["要求1", "要求2"],
            test_patterns=["pattern1"],
            priority="HIGH"
        )
        scenario1.covered_by = ["test1.py::pattern1", "test2.py::pattern1"]
        
        scenario2 = RuleScenario(
            rule_id="TEST002",
            category=RuleCategory.BASIC_FLOW,
            description="部分覆盖",
            requirements=["要求1", "要求2"],
            test_patterns=["pattern2"],
            priority="MEDIUM"
        )
        scenario2.covered_by = ["test1.py::pattern2"]
        
        scenario3 = RuleScenario(
            rule_id="TEST003",
            category=RuleCategory.BASIC_FLOW,
            description="未覆盖",
            requirements=["要求1"],
            test_patterns=["pattern3"],
            priority="LOW"
        )
        scenario3.covered_by = []
        
        # 临时替换规则场景
        original_scenarios = self.monitor.rule_scenarios
        self.monitor.rule_scenarios = [scenario1, scenario2, scenario3]
        
        # 更新覆盖状态
        self.monitor._update_coverage_status()
        
        # 检查结果
        assert scenario1.coverage_status == CoverageStatus.COVERED
        assert scenario2.coverage_status == CoverageStatus.PARTIAL
        assert scenario3.coverage_status == CoverageStatus.NOT_COVERED
        
        # 恢复原始场景
        self.monitor.rule_scenarios = original_scenarios
    
    def test_generate_coverage_report(self):
        """测试生成覆盖率报告"""
        # 设置一些测试数据
        for i, scenario in enumerate(self.monitor.rule_scenarios[:5]):
            if i < 3:
                scenario.coverage_status = CoverageStatus.COVERED
                scenario.covered_by = [f"test{i}.py::pattern"]
            elif i == 3:
                scenario.coverage_status = CoverageStatus.PARTIAL
                scenario.covered_by = [f"test{i}.py::pattern"]
            else:
                scenario.coverage_status = CoverageStatus.NOT_COVERED
                scenario.covered_by = []
        
        # 生成报告
        report = self.monitor._generate_coverage_report()
        
        assert isinstance(report, CoverageReport)
        assert report.total_rules == len(self.monitor.rule_scenarios)
        assert report.coverage_percentage >= 0
        assert report.coverage_percentage <= 100
        assert isinstance(report.category_coverage, dict)
        assert isinstance(report.priority_coverage, dict)
    
    def test_generate_coverage_report_text(self):
        """测试生成文本格式报告"""
        # 先生成覆盖率报告
        self.monitor.analyze_test_coverage()
        
        # 生成文本报告
        text_report = self.monitor.generate_coverage_report_text()
        
        assert isinstance(text_report, str)
        assert "德州扑克规则覆盖率报告" in text_report
        assert "总规则数" in text_report
        assert "覆盖率" in text_report
        assert "按类别覆盖率" in text_report
        assert "按优先级覆盖率" in text_report
    
    def test_export_coverage_report(self):
        """测试导出覆盖率报告"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_coverage.json"
            
            # 先生成覆盖率报告
            self.monitor.analyze_test_coverage()
            
            # 导出报告
            self.monitor.export_coverage_report(str(output_file))
            
            # 检查文件是否存在
            assert output_file.exists()
            
            # 检查文件内容
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert "timestamp" in data
            assert "total_rules" in data
            assert "coverage_percentage" in data
            assert "detailed_scenarios" in data
    
    def test_get_missing_test_scenarios(self):
        """测试获取缺失测试场景"""
        # 先分析覆盖率
        self.monitor.analyze_test_coverage()
        
        # 获取缺失场景
        missing_scenarios = self.monitor.get_missing_test_scenarios()
        
        assert isinstance(missing_scenarios, list)
        assert all(isinstance(s, RuleScenario) for s in missing_scenarios)
        assert all(s.coverage_status == CoverageStatus.NOT_COVERED for s in missing_scenarios)
    
    def test_suggest_test_cases(self):
        """测试建议测试用例"""
        # 先分析覆盖率
        self.monitor.analyze_test_coverage()
        
        # 获取建议
        suggestions = self.monitor.suggest_test_cases()
        
        assert isinstance(suggestions, list)
        if suggestions:  # 如果有建议
            assert all(isinstance(s, str) for s in suggestions)
    
    def test_analyze_test_coverage_integration(self):
        """测试完整的覆盖率分析流程"""
        # 执行完整分析
        report = self.monitor.analyze_test_coverage()
        
        # 检查报告
        assert isinstance(report, CoverageReport)
        assert report.total_rules > 0
        assert report.coverage_percentage >= 0
        assert report.coverage_percentage <= 100
        assert len(report.detailed_scenarios) == report.total_rules
        
        # 检查类别覆盖率
        assert "basic_flow" in report.category_coverage
        assert "betting_rules" in report.category_coverage
        assert "hand_rankings" in report.category_coverage
        
        # 检查优先级覆盖率
        assert "HIGH" in report.priority_coverage
        assert "MEDIUM" in report.priority_coverage
        assert "LOW" in report.priority_coverage
    
    def test_rule_scenario_completeness(self):
        """测试规则场景的完整性"""
        scenarios = self.monitor.rule_scenarios
        
        # 检查每个场景的必要字段
        for scenario in scenarios:
            assert scenario.rule_id
            assert scenario.category
            assert scenario.description
            assert scenario.requirements
            assert scenario.test_patterns
            assert scenario.priority in ["HIGH", "MEDIUM", "LOW"]
            assert isinstance(scenario.covered_by, list)
            assert isinstance(scenario.coverage_status, CoverageStatus)
    
    def test_category_distribution(self):
        """测试规则类别分布"""
        scenarios = self.monitor.rule_scenarios
        category_counts = {}
        
        for scenario in scenarios:
            category = scenario.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # 确保每个类别都有规则
        expected_categories = [
            "basic_flow", "betting_rules", "hand_rankings",
            "side_pot", "showdown", "special_cases"
        ]
        
        for category in expected_categories:
            assert category in category_counts
            assert category_counts[category] > 0
    
    def test_priority_distribution(self):
        """测试优先级分布"""
        scenarios = self.monitor.rule_scenarios
        priority_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for scenario in scenarios:
            priority_counts[scenario.priority] += 1
        
        # 确保有高优先级规则
        assert priority_counts["HIGH"] > 0
        # 确保有中等优先级规则
        assert priority_counts["MEDIUM"] > 0
        # 可能有低优先级规则
        assert priority_counts["LOW"] >= 0


class TestRuleScenarioPatterns:
    """测试规则场景的模式匹配"""
    
    def setup_method(self):
        """测试前设置"""
        self.monitor = PokerRulesCoverageMonitor()
    
    def test_basic_flow_patterns(self):
        """测试基本流程规则的模式"""
        basic_flow_scenarios = [
            s for s in self.monitor.rule_scenarios 
            if s.category == RuleCategory.BASIC_FLOW
        ]
        
        # 检查庄家按钮规则
        dealer_scenarios = [s for s in basic_flow_scenarios if "dealer" in s.test_patterns]
        assert len(dealer_scenarios) > 0
        
        # 检查盲注规则
        blind_scenarios = [s for s in basic_flow_scenarios if "blind" in s.test_patterns]
        assert len(blind_scenarios) > 0
    
    def test_betting_rules_patterns(self):
        """测试下注规则的模式"""
        betting_scenarios = [
            s for s in self.monitor.rule_scenarios 
            if s.category == RuleCategory.BETTING_RULES
        ]
        
        # 检查基本动作
        actions = ["fold", "check", "call", "raise", "all_in"]
        for action in actions:
            action_scenarios = [
                s for s in betting_scenarios 
                if any(action in pattern for pattern in s.test_patterns)
            ]
            assert len(action_scenarios) > 0, f"缺少 {action} 动作的规则"
    
    def test_hand_rankings_patterns(self):
        """测试牌型规则的模式"""
        hand_scenarios = [
            s for s in self.monitor.rule_scenarios 
            if s.category == RuleCategory.HAND_RANKINGS
        ]
        
        # 检查主要牌型
        hand_types = [
            "royal_flush", "straight_flush", "four_of_a_kind",
            "full_house", "flush", "straight", "three_of_a_kind",
            "two_pair", "one_pair", "high_card"
        ]
        
        for hand_type in hand_types:
            hand_type_scenarios = [
                s for s in hand_scenarios 
                if any(hand_type in pattern for pattern in s.test_patterns)
            ]
            assert len(hand_type_scenarios) > 0, f"缺少 {hand_type} 牌型的规则"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 