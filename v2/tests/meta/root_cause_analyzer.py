"""
自动化失败根因分析系统

该模块负责分析测试失败的根本原因，实现UI→Controller→Core→Controller→UI的自动化闭环回溯分析。
主要功能包括：
1. 失败分类器 - 按测试层级（unit/integration/e2e）自动分组
2. 根因分析引擎 - 自动判断问题所在层级
3. 修复指导生成器 - 生成结构化的修复建议
4. 责任归属分析 - 确定问题责任归属
"""

import json
import re
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import ast
import sys


class TestLayer(Enum):
    """测试层级枚举"""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    META = "meta"
    UNKNOWN = "unknown"


class FailureCategory(Enum):
    """失败类别枚举"""
    ASSERTION_ERROR = "assertion_error"
    IMPORT_ERROR = "import_error"
    ATTRIBUTE_ERROR = "attribute_error"
    TYPE_ERROR = "type_error"
    VALUE_ERROR = "value_error"
    TIMEOUT_ERROR = "timeout_error"
    SETUP_ERROR = "setup_error"
    TEARDOWN_ERROR = "teardown_error"
    UNKNOWN_ERROR = "unknown_error"


class ComponentType(Enum):
    """组件类型枚举"""
    CORE = "core"
    CONTROLLER = "controller"
    UI_CLI = "ui_cli"
    UI_STREAMLIT = "ui_streamlit"
    AI = "ai"
    TEST_FRAMEWORK = "test_framework"
    UNKNOWN = "unknown"


@dataclass
class FailureInfo:
    """失败信息数据类"""
    test_name: str
    test_file: str
    test_layer: TestLayer
    failure_category: FailureCategory
    error_message: str
    traceback_info: str
    line_number: int
    component_type: ComponentType
    timestamp: str
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        # 将枚举转换为字符串值以支持JSON序列化
        result['test_layer'] = self.test_layer.value
        result['failure_category'] = self.failure_category.value
        result['component_type'] = self.component_type.value
        return result


@dataclass
class RootCauseAnalysis:
    """根因分析结果"""
    failure_info: FailureInfo
    root_cause_layer: ComponentType
    confidence_score: float  # 0.0-1.0
    analysis_reasoning: str
    fix_suggestions: List[str]
    responsibility_assignment: str
    related_components: List[ComponentType]
    severity_level: str  # HIGH, MEDIUM, LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        result['failure_info'] = self.failure_info.to_dict()
        # 将枚举转换为字符串值以支持JSON序列化
        result['root_cause_layer'] = self.root_cause_layer.value
        result['related_components'] = [comp.value for comp in self.related_components]
        return result


class RootCauseAnalyzer:
    """
    自动化失败根因分析器
    
    负责分析测试失败的根本原因，提供修复指导和责任归属。
    """
    
    def __init__(self, project_root: str = None):
        """
        初始化根因分析器
        
        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.analysis_results: List[RootCauseAnalysis] = []
        
        # 组件识别模式
        self.component_patterns = {
            ComponentType.CORE: [
                r'v2[/\\]core[/\\]',
                r'from v2\.core',
                r'import.*v2\.core',
                r'GameState',
                r'Card',
                r'Player',
                r'Evaluator',
                r'Validator'
            ],
            ComponentType.CONTROLLER: [
                r'v2[/\\]controller[/\\]',
                r'from v2\.controller',
                r'import.*v2\.controller',
                r'PokerController',
                r'atomic_operation'
            ],
            ComponentType.UI_CLI: [
                r'v2[/\\]ui[/\\]cli[/\\]',
                r'from v2\.ui\.cli',
                r'import.*v2\.ui\.cli',
                r'cli_game',
                r'input_handler',
                r'render'
            ],
            ComponentType.UI_STREAMLIT: [
                r'v2[/\\]ui[/\\]streamlit[/\\]',
                r'from v2\.ui\.streamlit',
                r'import.*v2\.ui\.streamlit',
                r'streamlit',
                r'st\.',
                r'session_state'
            ],
            ComponentType.AI: [
                r'v2[/\\]ai[/\\]',
                r'from v2\.ai',
                r'import.*v2\.ai',
                r'SimpleAI',
                r'AIStrategy'
            ],
            ComponentType.TEST_FRAMEWORK: [
                r'pytest',
                r'unittest',
                r'mock',
                r'fixture',
                r'conftest'
            ]
        }
        
        # 失败模式识别
        self.failure_patterns = {
            FailureCategory.ASSERTION_ERROR: [
                r'AssertionError',
                r'assert.*failed',
                r'Expected.*but got'
            ],
            FailureCategory.IMPORT_ERROR: [
                r'ImportError',
                r'ModuleNotFoundError',
                r'No module named'
            ],
            FailureCategory.ATTRIBUTE_ERROR: [
                r'AttributeError',
                r'has no attribute',
                r'object has no attribute'
            ],
            FailureCategory.TYPE_ERROR: [
                r'TypeError',
                r'takes.*positional arguments',
                r'unexpected keyword argument'
            ],
            FailureCategory.VALUE_ERROR: [
                r'ValueError',
                r'invalid literal',
                r'could not convert'
            ],
            FailureCategory.TIMEOUT_ERROR: [
                r'TimeoutError',
                r'timeout',
                r'timed out'
            ]
        }
        
        # 修复建议模板
        self.fix_suggestions = {
            ComponentType.CORE: [
                "检查核心逻辑的数据结构和算法实现",
                "验证游戏状态的完整性和一致性",
                "确认业务规则的正确实现",
                "检查数据验证和边界条件处理"
            ],
            ComponentType.CONTROLLER: [
                "检查控制器的API接口和参数传递",
                "验证原子操作的事务完整性",
                "确认错误处理和异常传播机制",
                "检查控制器与核心层的交互逻辑"
            ],
            ComponentType.UI_CLI: [
                "检查命令行输入解析和验证",
                "验证用户交互流程的正确性",
                "确认输出格式和显示逻辑",
                "检查CLI与控制器的集成"
            ],
            ComponentType.UI_STREAMLIT: [
                "检查Streamlit组件的状态管理",
                "验证会话状态的持久化和同步",
                "确认用户界面的响应性和交互",
                "检查Web UI与控制器的集成"
            ],
            ComponentType.AI: [
                "检查AI策略的决策逻辑",
                "验证AI访问信息的合法性",
                "确认AI行为的随机性和公平性",
                "检查AI与游戏引擎的集成"
            ],
            ComponentType.TEST_FRAMEWORK: [
                "检查测试用例的设计和实现",
                "验证测试数据和Mock对象的正确性",
                "确认测试环境的配置和隔离",
                "检查测试框架的配置和依赖"
            ]
        }
    
    def analyze_pytest_json_report(self, report_file: str) -> List[RootCauseAnalysis]:
        """
        分析pytest JSON报告
        
        Args:
            report_file: pytest JSON报告文件路径
            
        Returns:
            根因分析结果列表
        """
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            self.analysis_results.clear()
            
            # 分析每个测试结果
            for test in report_data.get('tests', []):
                if test.get('outcome') in ['failed', 'error']:
                    failure_info = self._extract_failure_info(test)
                    if failure_info:
                        analysis = self._perform_root_cause_analysis(failure_info)
                        self.analysis_results.append(analysis)
            
            return self.analysis_results
            
        except Exception as e:
            print(f"分析pytest报告时出错: {e}")
            return []
    
    def analyze_single_failure(self, test_name: str, test_file: str, 
                             error_message: str, traceback_info: str) -> RootCauseAnalysis:
        """
        分析单个测试失败
        
        Args:
            test_name: 测试名称
            test_file: 测试文件路径
            error_message: 错误消息
            traceback_info: 堆栈跟踪信息
            
        Returns:
            根因分析结果
        """
        failure_info = FailureInfo(
            test_name=test_name,
            test_file=test_file,
            test_layer=self._determine_test_layer(test_file),
            failure_category=self._categorize_failure(error_message),
            error_message=error_message,
            traceback_info=traceback_info,
            line_number=self._extract_line_number(traceback_info),
            component_type=self._identify_component(test_file, traceback_info),
            timestamp=datetime.now().isoformat()
        )
        
        return self._perform_root_cause_analysis(failure_info)
    
    def _extract_failure_info(self, test_data: Dict[str, Any]) -> Optional[FailureInfo]:
        """从测试数据中提取失败信息"""
        try:
            call_info = test_data.get('call', {})
            error_message = call_info.get('longrepr', '')
            traceback_info = str(call_info.get('traceback', ''))
            
            return FailureInfo(
                test_name=test_data.get('nodeid', ''),
                test_file=test_data.get('nodeid', '').split('::')[0],
                test_layer=self._determine_test_layer(test_data.get('nodeid', '')),
                failure_category=self._categorize_failure(error_message),
                error_message=error_message,
                traceback_info=traceback_info,
                line_number=self._extract_line_number(traceback_info),
                component_type=self._identify_component(
                    test_data.get('nodeid', ''), traceback_info
                ),
                timestamp=datetime.now().isoformat(),
                duration=test_data.get('call', {}).get('duration', 0.0)
            )
        except Exception as e:
            print(f"提取失败信息时出错: {e}")
            return None
    
    def _determine_test_layer(self, test_path: str) -> TestLayer:
        """确定测试层级"""
        test_path = test_path.lower()
        
        if 'unit' in test_path:
            return TestLayer.UNIT
        elif 'integration' in test_path:
            return TestLayer.INTEGRATION
        elif 'e2e' in test_path or 'end_to_end' in test_path:
            return TestLayer.E2E
        elif 'meta' in test_path:
            return TestLayer.META
        else:
            return TestLayer.UNKNOWN
    
    def _categorize_failure(self, error_message: str) -> FailureCategory:
        """分类失败类型"""
        error_message = error_message.lower()
        
        for category, patterns in self.failure_patterns.items():
            for pattern in patterns:
                if re.search(pattern.lower(), error_message):
                    return category
        
        return FailureCategory.UNKNOWN_ERROR
    
    def _identify_component(self, test_file: str, traceback_info: str) -> ComponentType:
        """识别相关组件"""
        combined_text = f"{test_file} {traceback_info}".lower()
        
        # 计算每个组件的匹配分数
        component_scores = {}
        for component, patterns in self.component_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern.lower(), combined_text))
                score += matches
            component_scores[component] = score
        
        # 返回得分最高的组件
        if component_scores:
            best_component = max(component_scores, key=component_scores.get)
            if component_scores[best_component] > 0:
                return best_component
        
        return ComponentType.UNKNOWN
    
    def _extract_line_number(self, traceback_info: str) -> int:
        """从堆栈跟踪中提取行号"""
        try:
            # 查找行号模式
            line_pattern = r'line (\d+)'
            matches = re.findall(line_pattern, traceback_info)
            if matches:
                return int(matches[-1])  # 返回最后一个行号
        except Exception:
            pass
        return 0
    
    def _perform_root_cause_analysis(self, failure_info: FailureInfo) -> RootCauseAnalysis:
        """执行根因分析"""
        # 分析根本原因层级
        root_cause_layer = self._analyze_root_cause_layer(failure_info)
        
        # 计算置信度
        confidence_score = self._calculate_confidence_score(failure_info, root_cause_layer)
        
        # 生成分析推理
        analysis_reasoning = self._generate_analysis_reasoning(failure_info, root_cause_layer)
        
        # 生成修复建议
        fix_suggestions = self._generate_fix_suggestions(failure_info, root_cause_layer)
        
        # 确定责任归属
        responsibility_assignment = self._assign_responsibility(failure_info, root_cause_layer)
        
        # 识别相关组件
        related_components = self._identify_related_components(failure_info)
        
        # 确定严重程度
        severity_level = self._determine_severity_level(failure_info)
        
        return RootCauseAnalysis(
            failure_info=failure_info,
            root_cause_layer=root_cause_layer,
            confidence_score=confidence_score,
            analysis_reasoning=analysis_reasoning,
            fix_suggestions=fix_suggestions,
            responsibility_assignment=responsibility_assignment,
            related_components=related_components,
            severity_level=severity_level
        )
    
    def _analyze_root_cause_layer(self, failure_info: FailureInfo) -> ComponentType:
        """分析根本原因所在层级"""
        # 基于组件类型和失败类别进行分析
        component = failure_info.component_type
        category = failure_info.failure_category
        
        # 特殊情况处理
        if category == FailureCategory.IMPORT_ERROR:
            return ComponentType.TEST_FRAMEWORK
        elif category == FailureCategory.ASSERTION_ERROR:
            # 断言错误通常反映业务逻辑问题
            if component in [ComponentType.CORE, ComponentType.CONTROLLER]:
                return component
            else:
                return ComponentType.CORE
        elif category == FailureCategory.ATTRIBUTE_ERROR:
            # 属性错误通常是接口问题
            return component
        else:
            return component
    
    def _calculate_confidence_score(self, failure_info: FailureInfo, 
                                  root_cause_layer: ComponentType) -> float:
        """计算分析置信度"""
        score = 0.5  # 基础分数
        
        # 基于组件匹配度调整
        if failure_info.component_type == root_cause_layer:
            score += 0.3
        
        # 基于失败类别调整
        if failure_info.failure_category in [
            FailureCategory.ASSERTION_ERROR,
            FailureCategory.TYPE_ERROR,
            FailureCategory.VALUE_ERROR
        ]:
            score += 0.2
        
        # 基于测试层级调整
        if failure_info.test_layer == TestLayer.UNIT:
            score += 0.1
        elif failure_info.test_layer == TestLayer.INTEGRATION:
            score += 0.05
        
        return min(1.0, score)
    
    def _generate_analysis_reasoning(self, failure_info: FailureInfo, 
                                   root_cause_layer: ComponentType) -> str:
        """生成分析推理"""
        reasoning_parts = []
        
        # 基础分析
        reasoning_parts.append(
            f"测试 '{failure_info.test_name}' 在 {failure_info.test_layer.value} 层级失败"
        )
        
        # 失败类型分析
        reasoning_parts.append(
            f"失败类型为 {failure_info.failure_category.value}，"
            f"主要涉及 {failure_info.component_type.value} 组件"
        )
        
        # 根因分析
        reasoning_parts.append(
            f"根据错误模式和组件分析，根本原因可能在 {root_cause_layer.value} 层级"
        )
        
        # 具体错误信息
        if failure_info.error_message:
            error_summary = failure_info.error_message[:100] + "..." \
                if len(failure_info.error_message) > 100 else failure_info.error_message
            reasoning_parts.append(f"错误信息: {error_summary}")
        
        return "。".join(reasoning_parts) + "。"
    
    def _generate_fix_suggestions(self, failure_info: FailureInfo, 
                                root_cause_layer: ComponentType) -> List[str]:
        """生成修复建议"""
        suggestions = []
        
        # 获取通用建议
        general_suggestions = self.fix_suggestions.get(root_cause_layer, [])
        suggestions.extend(general_suggestions[:2])  # 取前两个通用建议
        
        # 基于失败类别的特定建议
        if failure_info.failure_category == FailureCategory.ASSERTION_ERROR:
            suggestions.append("检查测试断言的预期值和实际值是否正确")
            suggestions.append("验证测试数据的准备和清理逻辑")
        elif failure_info.failure_category == FailureCategory.IMPORT_ERROR:
            suggestions.append("检查模块导入路径和依赖关系")
            suggestions.append("确认Python路径和虚拟环境配置")
        elif failure_info.failure_category == FailureCategory.ATTRIBUTE_ERROR:
            suggestions.append("检查对象属性的定义和初始化")
            suggestions.append("验证API接口的一致性")
        elif failure_info.failure_category == FailureCategory.TYPE_ERROR:
            suggestions.append("检查函数参数的类型和数量")
            suggestions.append("验证数据类型转换的正确性")
        
        # 基于测试层级的建议
        if failure_info.test_layer == TestLayer.INTEGRATION:
            suggestions.append("检查组件间的集成和接口匹配")
        elif failure_info.test_layer == TestLayer.E2E:
            suggestions.append("验证端到端流程的完整性")
        
        return suggestions[:5]  # 限制建议数量
    
    def _assign_responsibility(self, failure_info: FailureInfo, 
                             root_cause_layer: ComponentType) -> str:
        """分配责任归属"""
        layer_responsibilities = {
            ComponentType.CORE: "核心逻辑开发团队",
            ComponentType.CONTROLLER: "控制器层开发团队",
            ComponentType.UI_CLI: "CLI界面开发团队",
            ComponentType.UI_STREAMLIT: "Web界面开发团队",
            ComponentType.AI: "AI策略开发团队",
            ComponentType.TEST_FRAMEWORK: "测试框架维护团队",
            ComponentType.UNKNOWN: "需要进一步调查确定责任方"
        }
        
        return layer_responsibilities.get(root_cause_layer, "未知责任方")
    
    def _identify_related_components(self, failure_info: FailureInfo) -> List[ComponentType]:
        """识别相关组件"""
        related = [failure_info.component_type]
        
        # 基于测试层级添加相关组件
        if failure_info.test_layer == TestLayer.INTEGRATION:
            # 集成测试通常涉及多个组件
            if failure_info.component_type == ComponentType.CONTROLLER:
                related.extend([ComponentType.CORE, ComponentType.UI_CLI])
            elif failure_info.component_type in [ComponentType.UI_CLI, ComponentType.UI_STREAMLIT]:
                related.append(ComponentType.CONTROLLER)
        elif failure_info.test_layer == TestLayer.E2E:
            # 端到端测试涉及所有组件
            related.extend([
                ComponentType.CORE, ComponentType.CONTROLLER,
                ComponentType.UI_CLI, ComponentType.UI_STREAMLIT
            ])
        
        # 去重并返回
        return list(set(related))
    
    def _determine_severity_level(self, failure_info: FailureInfo) -> str:
        """确定严重程度"""
        # 基于失败类别确定严重程度
        high_severity_categories = [
            FailureCategory.ASSERTION_ERROR,
            FailureCategory.TYPE_ERROR,
            FailureCategory.VALUE_ERROR
        ]
        
        medium_severity_categories = [
            FailureCategory.ATTRIBUTE_ERROR,
            FailureCategory.TIMEOUT_ERROR
        ]
        
        if failure_info.failure_category in high_severity_categories:
            return "HIGH"
        elif failure_info.failure_category in medium_severity_categories:
            return "MEDIUM"
        else:
            return "LOW"
    
    def generate_analysis_report(self, output_file: str = None) -> str:
        """
        生成分析报告
        
        Args:
            output_file: 输出文件路径，如果为None则返回字符串
            
        Returns:
            报告内容
        """
        if not self.analysis_results:
            report = "📊 根因分析报告\n\n✅ 未发现测试失败，所有测试通过！\n"
        else:
            report = self._generate_detailed_analysis_report()
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report
    
    def _generate_detailed_analysis_report(self) -> str:
        """生成详细的分析报告"""
        report_lines = [
            "📊 自动化失败根因分析报告",
            "=" * 60,
            f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"失败测试数: {len(self.analysis_results)}",
            ""
        ]
        
        # 统计信息
        layer_stats = {}
        component_stats = {}
        severity_stats = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for analysis in self.analysis_results:
            # 层级统计
            layer = analysis.failure_info.test_layer.value
            layer_stats[layer] = layer_stats.get(layer, 0) + 1
            
            # 组件统计
            component = analysis.root_cause_layer.value
            component_stats[component] = component_stats.get(component, 0) + 1
            
            # 严重程度统计
            severity_stats[analysis.severity_level] += 1
        
        # 添加统计信息
        report_lines.extend([
            "📈 失败统计:",
            "-" * 30,
            f"按测试层级: {dict(layer_stats)}",
            f"按根因组件: {dict(component_stats)}",
            f"按严重程度: {dict(severity_stats)}",
            ""
        ])
        
        # 按严重程度分组显示
        high_failures = [a for a in self.analysis_results if a.severity_level == "HIGH"]
        medium_failures = [a for a in self.analysis_results if a.severity_level == "MEDIUM"]
        low_failures = [a for a in self.analysis_results if a.severity_level == "LOW"]
        
        if high_failures:
            report_lines.extend([
                "🔴 高严重程度失败:",
                "-" * 30
            ])
            for analysis in high_failures:
                report_lines.extend(self._format_analysis_result(analysis))
            report_lines.append("")
        
        if medium_failures:
            report_lines.extend([
                "🟡 中等严重程度失败:",
                "-" * 30
            ])
            for analysis in medium_failures:
                report_lines.extend(self._format_analysis_result(analysis))
            report_lines.append("")
        
        if low_failures:
            report_lines.extend([
                "🟢 低严重程度失败:",
                "-" * 30
            ])
            for analysis in low_failures:
                report_lines.extend(self._format_analysis_result(analysis))
            report_lines.append("")
        
        # 添加总结和建议
        report_lines.extend([
            "💡 总结和建议:",
            "-" * 30,
            "1. 优先修复高严重程度的失败",
            "2. 关注根因组件的系统性问题",
            "3. 加强相关组件的集成测试",
            "4. 建立预防性质量检查机制",
            ""
        ])
        
        return "\n".join(report_lines)
    
    def _format_analysis_result(self, analysis: RootCauseAnalysis) -> List[str]:
        """格式化单个分析结果"""
        lines = [
            f"📍 {analysis.failure_info.test_name}",
            f"   文件: {analysis.failure_info.test_file}",
            f"   层级: {analysis.failure_info.test_layer.value}",
            f"   根因: {analysis.root_cause_layer.value}",
            f"   置信度: {analysis.confidence_score:.2f}",
            f"   责任方: {analysis.responsibility_assignment}",
            f"   分析: {analysis.analysis_reasoning}",
            "   修复建议:"
        ]
        
        for i, suggestion in enumerate(analysis.fix_suggestions, 1):
            lines.append(f"     {i}. {suggestion}")
        
        lines.append("")
        return lines
    
    def export_json_report(self, output_file: str):
        """导出JSON格式报告"""
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_failures": len(self.analysis_results),
            "analyses": [analysis.to_dict() for analysis in self.analysis_results]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)


def main():
    """主函数，用于命令行执行"""
    import argparse
    
    parser = argparse.ArgumentParser(description="自动化失败根因分析器")
    parser.add_argument("--pytest-report", help="pytest JSON报告文件路径")
    parser.add_argument("--output", help="输出报告文件路径")
    parser.add_argument("--json-output", help="JSON格式输出文件路径")
    parser.add_argument("--project-root", help="项目根目录路径")
    
    args = parser.parse_args()
    
    analyzer = RootCauseAnalyzer(project_root=args.project_root)
    
    if args.pytest_report:
        analyzer.analyze_pytest_json_report(args.pytest_report)
    
    # 生成报告
    report = analyzer.generate_analysis_report(output_file=args.output)
    
    if args.json_output:
        analyzer.export_json_report(args.json_output)
    
    if not args.output:
        print(report)


if __name__ == "__main__":
    main() 