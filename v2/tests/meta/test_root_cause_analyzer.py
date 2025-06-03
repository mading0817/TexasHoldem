"""
根因分析器测试模块

测试自动化失败根因分析系统的各项功能。
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from v2.tests.meta.root_cause_analyzer import (
    RootCauseAnalyzer,
    FailureInfo,
    RootCauseAnalysis,
    TestLayer,
    FailureCategory,
    ComponentType
)


@pytest.mark.root_cause
@pytest.mark.fast
class TestRootCauseAnalyzer:
    """根因分析器测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.analyzer = RootCauseAnalyzer()
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        assert self.analyzer.project_root is not None
        assert isinstance(self.analyzer.analysis_results, list)
        assert len(self.analyzer.analysis_results) == 0
        
        # 检查组件模式配置
        assert ComponentType.CORE in self.analyzer.component_patterns
        assert ComponentType.CONTROLLER in self.analyzer.component_patterns
        assert ComponentType.UI_CLI in self.analyzer.component_patterns
        assert ComponentType.UI_STREAMLIT in self.analyzer.component_patterns
        
        # 检查失败模式配置
        assert FailureCategory.ASSERTION_ERROR in self.analyzer.failure_patterns
        assert FailureCategory.IMPORT_ERROR in self.analyzer.failure_patterns
        
        # 检查修复建议配置
        assert ComponentType.CORE in self.analyzer.fix_suggestions
        assert len(self.analyzer.fix_suggestions[ComponentType.CORE]) > 0
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_determine_test_layer(self):
        """测试测试层级判断"""
        # 单元测试
        assert self.analyzer._determine_test_layer("v2/tests/unit/test_cards.py") == TestLayer.UNIT
        
        # 集成测试
        assert self.analyzer._determine_test_layer("v2/tests/integration/test_flow.py") == TestLayer.INTEGRATION
        
        # 端到端测试
        assert self.analyzer._determine_test_layer("v2/tests/e2e/test_game.py") == TestLayer.E2E
        
        # Meta测试
        assert self.analyzer._determine_test_layer("v2/tests/meta/test_analyzer.py") == TestLayer.META
        
        # 未知类型
        assert self.analyzer._determine_test_layer("v2/tests/unknown.py") == TestLayer.UNKNOWN
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_categorize_failure(self):
        """测试失败类型分类"""
        # 断言错误
        assert self.analyzer._categorize_failure("AssertionError: Expected 5 but got 3") == FailureCategory.ASSERTION_ERROR
        
        # 导入错误
        assert self.analyzer._categorize_failure("ModuleNotFoundError: No module named 'xyz'") == FailureCategory.IMPORT_ERROR
        
        # 属性错误
        assert self.analyzer._categorize_failure("AttributeError: 'NoneType' object has no attribute 'value'") == FailureCategory.ATTRIBUTE_ERROR
        
        # 类型错误
        assert self.analyzer._categorize_failure("TypeError: takes 2 positional arguments but 3 were given") == FailureCategory.TYPE_ERROR
        
        # 值错误
        assert self.analyzer._categorize_failure("ValueError: invalid literal for int()") == FailureCategory.VALUE_ERROR
        
        # 超时错误
        assert self.analyzer._categorize_failure("TimeoutError: operation timed out") == FailureCategory.TIMEOUT_ERROR
        
        # 未知错误
        assert self.analyzer._categorize_failure("SomeUnknownError: weird error") == FailureCategory.UNKNOWN_ERROR
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_identify_component(self):
        """测试组件识别"""
        # Core组件
        assert self.analyzer._identify_component(
            "v2/tests/unit/test_cards.py",
            "from v2.core.cards import Card"
        ) == ComponentType.CORE
        
        # Controller组件
        assert self.analyzer._identify_component(
            "v2/tests/unit/test_controller.py",
            "from v2.controller.poker_controller import PokerController"
        ) == ComponentType.CONTROLLER
        
        # CLI UI组件
        assert self.analyzer._identify_component(
            "v2/tests/unit/test_cli.py",
            "from v2.ui.cli.cli_game import main"
        ) == ComponentType.UI_CLI
        
        # Streamlit UI组件
        assert self.analyzer._identify_component(
            "v2/tests/unit/test_streamlit.py",
            "import streamlit as st"
        ) == ComponentType.UI_STREAMLIT
        
        # AI组件
        assert self.analyzer._identify_component(
            "v2/tests/unit/test_ai.py",
            "from v2.ai.simple_ai import SimpleAI"
        ) == ComponentType.AI
        
        # 测试框架
        assert self.analyzer._identify_component(
            "v2/tests/conftest.py",
            "import pytest"
        ) == ComponentType.TEST_FRAMEWORK
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_extract_line_number(self):
        """测试行号提取"""
        traceback_info = """
        File "test.py", line 42, in test_function
            assert result == expected
        AssertionError: Expected 5 but got 3
        """
        
        line_number = self.analyzer._extract_line_number(traceback_info)
        assert line_number == 42
        
        # 无行号信息
        line_number = self.analyzer._extract_line_number("No line info")
        assert line_number == 0
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_analyze_single_failure(self):
        """测试单个失败分析"""
        analysis = self.analyzer.analyze_single_failure(
            test_name="test_card_creation",
            test_file="v2/tests/unit/test_cards.py",
            error_message="AssertionError: Expected Ace but got King",
            traceback_info="File 'test_cards.py', line 25, in test_card_creation"
        )
        
        assert isinstance(analysis, RootCauseAnalysis)
        assert analysis.failure_info.test_name == "test_card_creation"
        assert analysis.failure_info.test_layer == TestLayer.UNIT
        assert analysis.failure_info.failure_category == FailureCategory.ASSERTION_ERROR
        assert analysis.failure_info.component_type == ComponentType.CORE
        assert analysis.failure_info.line_number == 25
        
        assert analysis.root_cause_layer == ComponentType.CORE
        assert 0.0 <= analysis.confidence_score <= 1.0
        assert len(analysis.fix_suggestions) > 0
        assert analysis.responsibility_assignment == "核心逻辑开发团队"
        assert analysis.severity_level in ["HIGH", "MEDIUM", "LOW"]
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_analyze_root_cause_layer(self):
        """测试根因层级分析"""
        # 断言错误 + Core组件 = Core层级
        failure_info = FailureInfo(
            test_name="test",
            test_file="test.py",
            test_layer=TestLayer.UNIT,
            failure_category=FailureCategory.ASSERTION_ERROR,
            error_message="",
            traceback_info="",
            line_number=0,
            component_type=ComponentType.CORE,
            timestamp=""
        )
        
        root_cause = self.analyzer._analyze_root_cause_layer(failure_info)
        assert root_cause == ComponentType.CORE
        
        # 导入错误 = 测试框架
        failure_info.failure_category = FailureCategory.IMPORT_ERROR
        root_cause = self.analyzer._analyze_root_cause_layer(failure_info)
        assert root_cause == ComponentType.TEST_FRAMEWORK
        
        # 属性错误 = 原组件
        failure_info.failure_category = FailureCategory.ATTRIBUTE_ERROR
        failure_info.component_type = ComponentType.CONTROLLER
        root_cause = self.analyzer._analyze_root_cause_layer(failure_info)
        assert root_cause == ComponentType.CONTROLLER
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_calculate_confidence_score(self):
        """测试置信度计算"""
        failure_info = FailureInfo(
            test_name="test",
            test_file="test.py",
            test_layer=TestLayer.UNIT,
            failure_category=FailureCategory.ASSERTION_ERROR,
            error_message="",
            traceback_info="",
            line_number=0,
            component_type=ComponentType.CORE,
            timestamp=""
        )
        
        # 组件匹配 + 断言错误 + 单元测试 = 高置信度
        confidence = self.analyzer._calculate_confidence_score(failure_info, ComponentType.CORE)
        assert confidence >= 0.8
        
        # 组件不匹配 = 较低置信度
        confidence = self.analyzer._calculate_confidence_score(failure_info, ComponentType.UI_CLI)
        assert confidence <= 0.8
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_generate_fix_suggestions(self):
        """测试修复建议生成"""
        failure_info = FailureInfo(
            test_name="test",
            test_file="test.py",
            test_layer=TestLayer.UNIT,
            failure_category=FailureCategory.ASSERTION_ERROR,
            error_message="",
            traceback_info="",
            line_number=0,
            component_type=ComponentType.CORE,
            timestamp=""
        )
        
        suggestions = self.analyzer._generate_fix_suggestions(failure_info, ComponentType.CORE)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert len(suggestions) <= 5  # 限制建议数量
        
        # 检查是否包含断言错误的特定建议
        suggestion_text = " ".join(suggestions)
        assert "断言" in suggestion_text or "测试" in suggestion_text
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_assign_responsibility(self):
        """测试责任归属"""
        failure_info = FailureInfo(
            test_name="test",
            test_file="test.py",
            test_layer=TestLayer.UNIT,
            failure_category=FailureCategory.ASSERTION_ERROR,
            error_message="",
            traceback_info="",
            line_number=0,
            component_type=ComponentType.CORE,
            timestamp=""
        )
        
        responsibility = self.analyzer._assign_responsibility(failure_info, ComponentType.CORE)
        assert responsibility == "核心逻辑开发团队"
        
        responsibility = self.analyzer._assign_responsibility(failure_info, ComponentType.CONTROLLER)
        assert responsibility == "控制器层开发团队"
        
        responsibility = self.analyzer._assign_responsibility(failure_info, ComponentType.UI_CLI)
        assert responsibility == "CLI界面开发团队"
        
        responsibility = self.analyzer._assign_responsibility(failure_info, ComponentType.UI_STREAMLIT)
        assert responsibility == "Web界面开发团队"
        
        responsibility = self.analyzer._assign_responsibility(failure_info, ComponentType.AI)
        assert responsibility == "AI策略开发团队"
        
        responsibility = self.analyzer._assign_responsibility(failure_info, ComponentType.TEST_FRAMEWORK)
        assert responsibility == "测试框架维护团队"
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_identify_related_components(self):
        """测试相关组件识别"""
        # 单元测试 - 只有自身组件
        failure_info = FailureInfo(
            test_name="test",
            test_file="test.py",
            test_layer=TestLayer.UNIT,
            failure_category=FailureCategory.ASSERTION_ERROR,
            error_message="",
            traceback_info="",
            line_number=0,
            component_type=ComponentType.CORE,
            timestamp=""
        )
        
        related = self.analyzer._identify_related_components(failure_info)
        assert ComponentType.CORE in related
        
        # 集成测试 - 多个相关组件
        failure_info.test_layer = TestLayer.INTEGRATION
        failure_info.component_type = ComponentType.CONTROLLER
        related = self.analyzer._identify_related_components(failure_info)
        assert ComponentType.CONTROLLER in related
        assert ComponentType.CORE in related
        assert ComponentType.UI_CLI in related
        
        # 端到端测试 - 所有组件
        failure_info.test_layer = TestLayer.E2E
        related = self.analyzer._identify_related_components(failure_info)
        assert ComponentType.CORE in related
        assert ComponentType.CONTROLLER in related
        assert ComponentType.UI_CLI in related
        assert ComponentType.UI_STREAMLIT in related
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_determine_severity_level(self):
        """测试严重程度判断"""
        failure_info = FailureInfo(
            test_name="test",
            test_file="test.py",
            test_layer=TestLayer.UNIT,
            failure_category=FailureCategory.ASSERTION_ERROR,
            error_message="",
            traceback_info="",
            line_number=0,
            component_type=ComponentType.CORE,
            timestamp=""
        )
        
        # 高严重程度
        assert self.analyzer._determine_severity_level(failure_info) == "HIGH"
        
        # 中等严重程度
        failure_info.failure_category = FailureCategory.ATTRIBUTE_ERROR
        assert self.analyzer._determine_severity_level(failure_info) == "MEDIUM"
        
        # 低严重程度
        failure_info.failure_category = FailureCategory.IMPORT_ERROR
        assert self.analyzer._determine_severity_level(failure_info) == "LOW"
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_analyze_pytest_json_report(self):
        """测试pytest JSON报告分析"""
        # 创建模拟的pytest报告
        mock_report = {
            "tests": [
                {
                    "nodeid": "v2/tests/unit/test_cards.py::test_card_creation",
                    "outcome": "failed",
                    "call": {
                        "longrepr": "AssertionError: Expected Ace but got King",
                        "traceback": "File 'test_cards.py', line 25, in test_card_creation",
                        "duration": 0.1
                    }
                },
                {
                    "nodeid": "v2/tests/unit/test_other.py::test_success",
                    "outcome": "passed",
                    "call": {
                        "duration": 0.05
                    }
                }
            ]
        }
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mock_report, f)
            temp_file = f.name
        
        try:
            # 分析报告
            results = self.analyzer.analyze_pytest_json_report(temp_file)
            
            assert len(results) == 1  # 只有一个失败的测试
            analysis = results[0]
            
            assert analysis.failure_info.test_name == "v2/tests/unit/test_cards.py::test_card_creation"
            assert analysis.failure_info.test_file == "v2/tests/unit/test_cards.py"
            assert analysis.failure_info.test_layer == TestLayer.UNIT
            assert analysis.failure_info.failure_category == FailureCategory.ASSERTION_ERROR
            assert analysis.failure_info.duration == 0.1
            
        finally:
            # 清理临时文件
            Path(temp_file).unlink()
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_generate_analysis_report_no_failures(self):
        """测试无失败时的报告生成"""
        report = self.analyzer.generate_analysis_report()
        
        assert "未发现测试失败" in report
        assert "所有测试通过" in report
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_generate_analysis_report_with_failures(self):
        """测试有失败时的报告生成"""
        # 添加一个模拟的分析结果
        failure_info = FailureInfo(
            test_name="test_example",
            test_file="test.py",
            test_layer=TestLayer.UNIT,
            failure_category=FailureCategory.ASSERTION_ERROR,
            error_message="Test failed",
            traceback_info="",
            line_number=10,
            component_type=ComponentType.CORE,
            timestamp="2025-06-02T10:00:00"
        )
        
        analysis = RootCauseAnalysis(
            failure_info=failure_info,
            root_cause_layer=ComponentType.CORE,
            confidence_score=0.9,
            analysis_reasoning="Test analysis",
            fix_suggestions=["Fix suggestion 1", "Fix suggestion 2"],
            responsibility_assignment="核心逻辑开发团队",
            related_components=[ComponentType.CORE],
            severity_level="HIGH"
        )
        
        self.analyzer.analysis_results.append(analysis)
        
        report = self.analyzer.generate_analysis_report()
        
        assert "自动化失败根因分析报告" in report
        assert "失败测试数: 1" in report
        assert "高严重程度失败" in report
        assert "test_example" in report
        assert "核心逻辑开发团队" in report
        assert "Fix suggestion 1" in report
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_export_json_report(self):
        """测试JSON报告导出"""
        # 添加一个模拟的分析结果
        failure_info = FailureInfo(
            test_name="test_example",
            test_file="test.py",
            test_layer=TestLayer.UNIT,
            failure_category=FailureCategory.ASSERTION_ERROR,
            error_message="Test failed",
            traceback_info="",
            line_number=10,
            component_type=ComponentType.CORE,
            timestamp="2025-06-02T10:00:00"
        )
        
        analysis = RootCauseAnalysis(
            failure_info=failure_info,
            root_cause_layer=ComponentType.CORE,
            confidence_score=0.9,
            analysis_reasoning="Test analysis",
            fix_suggestions=["Fix suggestion 1"],
            responsibility_assignment="核心逻辑开发团队",
            related_components=[ComponentType.CORE],
            severity_level="HIGH"
        )
        
        self.analyzer.analysis_results.append(analysis)
        
        # 导出到临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            self.analyzer.export_json_report(temp_file)
            
            # 验证导出的JSON
            with open(temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert "timestamp" in data
            assert data["total_failures"] == 1
            assert len(data["analyses"]) == 1
            
            analysis_data = data["analyses"][0]
            assert analysis_data["failure_info"]["test_name"] == "test_example"
            assert analysis_data["root_cause_layer"] == "core"
            assert analysis_data["confidence_score"] == 0.9
            assert analysis_data["severity_level"] == "HIGH"
            
        finally:
            # 清理临时文件
            Path(temp_file).unlink()
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_error_handling_invalid_json(self):
        """测试无效JSON文件的错误处理"""
        # 创建无效的JSON文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name
        
        try:
            results = self.analyzer.analyze_pytest_json_report(temp_file)
            assert results == []  # 应该返回空列表
            
        finally:
            # 清理临时文件
            Path(temp_file).unlink()
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_error_handling_missing_file(self):
        """测试文件不存在的错误处理"""
        results = self.analyzer.analyze_pytest_json_report("nonexistent_file.json")
        assert results == []  # 应该返回空列表


@pytest.mark.root_cause
@pytest.mark.fast
class TestFailureInfoDataClass:
    """FailureInfo数据类测试"""
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_failure_info_creation(self):
        """测试FailureInfo创建"""
        failure_info = FailureInfo(
            test_name="test_example",
            test_file="test.py",
            test_layer=TestLayer.UNIT,
            failure_category=FailureCategory.ASSERTION_ERROR,
            error_message="Test failed",
            traceback_info="traceback",
            line_number=10,
            component_type=ComponentType.CORE,
            timestamp="2025-06-02T10:00:00",
            duration=0.5
        )
        
        assert failure_info.test_name == "test_example"
        assert failure_info.test_file == "test.py"
        assert failure_info.test_layer == TestLayer.UNIT
        assert failure_info.failure_category == FailureCategory.ASSERTION_ERROR
        assert failure_info.error_message == "Test failed"
        assert failure_info.traceback_info == "traceback"
        assert failure_info.line_number == 10
        assert failure_info.component_type == ComponentType.CORE
        assert failure_info.timestamp == "2025-06-02T10:00:00"
        assert failure_info.duration == 0.5
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_failure_info_to_dict(self):
        """测试FailureInfo转换为字典"""
        failure_info = FailureInfo(
            test_name="test_example",
            test_file="test.py",
            test_layer=TestLayer.UNIT,
            failure_category=FailureCategory.ASSERTION_ERROR,
            error_message="Test failed",
            traceback_info="traceback",
            line_number=10,
            component_type=ComponentType.CORE,
            timestamp="2025-06-02T10:00:00"
        )
        
        data = failure_info.to_dict()
        
        assert isinstance(data, dict)
        assert data["test_name"] == "test_example"
        assert data["test_file"] == "test.py"
        assert data["test_layer"] == "unit"
        assert data["failure_category"] == "assertion_error"


@pytest.mark.root_cause
@pytest.mark.fast
class TestRootCauseAnalysisDataClass:
    """RootCauseAnalysis数据类测试"""
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_root_cause_analysis_creation(self):
        """测试RootCauseAnalysis创建"""
        failure_info = FailureInfo(
            test_name="test_example",
            test_file="test.py",
            test_layer=TestLayer.UNIT,
            failure_category=FailureCategory.ASSERTION_ERROR,
            error_message="Test failed",
            traceback_info="traceback",
            line_number=10,
            component_type=ComponentType.CORE,
            timestamp="2025-06-02T10:00:00"
        )
        
        analysis = RootCauseAnalysis(
            failure_info=failure_info,
            root_cause_layer=ComponentType.CORE,
            confidence_score=0.9,
            analysis_reasoning="Test analysis",
            fix_suggestions=["Fix 1", "Fix 2"],
            responsibility_assignment="核心逻辑开发团队",
            related_components=[ComponentType.CORE, ComponentType.CONTROLLER],
            severity_level="HIGH"
        )
        
        assert analysis.failure_info == failure_info
        assert analysis.root_cause_layer == ComponentType.CORE
        assert analysis.confidence_score == 0.9
        assert analysis.analysis_reasoning == "Test analysis"
        assert analysis.fix_suggestions == ["Fix 1", "Fix 2"]
        assert analysis.responsibility_assignment == "核心逻辑开发团队"
        assert analysis.related_components == [ComponentType.CORE, ComponentType.CONTROLLER]
        assert analysis.severity_level == "HIGH"
    
    @pytest.mark.root_cause
    @pytest.mark.fast
    def test_root_cause_analysis_to_dict(self):
        """测试RootCauseAnalysis转换为字典"""
        failure_info = FailureInfo(
            test_name="test_example",
            test_file="test.py",
            test_layer=TestLayer.UNIT,
            failure_category=FailureCategory.ASSERTION_ERROR,
            error_message="Test failed",
            traceback_info="traceback",
            line_number=10,
            component_type=ComponentType.CORE,
            timestamp="2025-06-02T10:00:00"
        )
        
        analysis = RootCauseAnalysis(
            failure_info=failure_info,
            root_cause_layer=ComponentType.CORE,
            confidence_score=0.9,
            analysis_reasoning="Test analysis",
            fix_suggestions=["Fix 1"],
            responsibility_assignment="核心逻辑开发团队",
            related_components=[ComponentType.CORE],
            severity_level="HIGH"
        )
        
        data = analysis.to_dict()
        
        assert isinstance(data, dict)
        assert "failure_info" in data
        assert isinstance(data["failure_info"], dict)
        assert data["root_cause_layer"] == "core"
        assert data["confidence_score"] == 0.9
        assert data["severity_level"] == "HIGH" 