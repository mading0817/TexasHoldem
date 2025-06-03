"""
根因分析器演示脚本

演示自动化失败根因分析系统的功能。
"""

import json
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v2.tests.meta.root_cause_analyzer import RootCauseAnalyzer


def create_mock_pytest_report():
    """创建模拟的pytest报告"""
    return {
        "tests": [
            {
                "nodeid": "v2/tests/unit/test_cards.py::test_card_creation",
                "outcome": "failed",
                "call": {
                    "longrepr": "AssertionError: Expected Ace of Spades but got King of Hearts",
                    "traceback": "File 'v2/core/cards.py', line 25, in __init__\n    assert rank in valid_ranks\nAssertionError",
                    "duration": 0.1
                }
            },
            {
                "nodeid": "v2/tests/unit/test_controller.py::test_invalid_action",
                "outcome": "failed",
                "call": {
                    "longrepr": "TypeError: PokerController.process_action() takes 2 positional arguments but 3 were given",
                    "traceback": "File 'v2/controller/poker_controller.py', line 45, in process_action",
                    "duration": 0.05
                }
            },
            {
                "nodeid": "v2/tests/integration/test_ui_flow.py::test_streamlit_integration",
                "outcome": "failed",
                "call": {
                    "longrepr": "AttributeError: 'NoneType' object has no attribute 'session_state'",
                    "traceback": "File 'v2/ui/streamlit/app.py', line 120, in render_game_state\n    st.session_state.game_data",
                    "duration": 0.3
                }
            },
            {
                "nodeid": "v2/tests/unit/test_ai.py::test_ai_decision",
                "outcome": "failed",
                "call": {
                    "longrepr": "ImportError: No module named 'v2.ai.advanced_strategy'",
                    "traceback": "File 'v2/tests/unit/test_ai.py', line 10, in <module>",
                    "duration": 0.01
                }
            },
            {
                "nodeid": "v2/tests/e2e/test_full_game.py::test_complete_game_flow",
                "outcome": "failed",
                "call": {
                    "longrepr": "TimeoutError: Game flow timed out after 30 seconds",
                    "traceback": "File 'v2/tests/e2e/test_full_game.py', line 50, in test_complete_game_flow",
                    "duration": 30.1
                }
            },
            {
                "nodeid": "v2/tests/unit/test_success.py::test_working_feature",
                "outcome": "passed",
                "call": {
                    "duration": 0.02
                }
            }
        ]
    }


def main():
    """主演示函数"""
    print("🔍 根因分析器演示")
    print("=" * 50)
    
    # 创建分析器
    analyzer = RootCauseAnalyzer()
    
    # 创建模拟报告
    mock_report = create_mock_pytest_report()
    
    # 保存到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(mock_report, f)
        temp_file = f.name
    
    try:
        print(f"📄 分析模拟pytest报告: {temp_file}")
        
        # 分析报告
        results = analyzer.analyze_pytest_json_report(temp_file)
        
        print(f"🔍 发现 {len(results)} 个失败测试")
        print()
        
        # 生成详细报告
        report = analyzer.generate_analysis_report()
        print(report)
        
        # 导出JSON报告
        json_file = "test-reports/demo-root-cause-analysis.json"
        analyzer.export_json_report(json_file)
        print(f"📊 JSON报告已导出到: {json_file}")
        
        # 显示一些统计信息
        print("\n📈 分析统计:")
        print("-" * 30)
        
        # 按组件统计
        component_stats = {}
        severity_stats = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        for analysis in results:
            component = analysis.root_cause_layer.value
            component_stats[component] = component_stats.get(component, 0) + 1
            severity_stats[analysis.severity_level] += 1
        
        print(f"按根因组件: {component_stats}")
        print(f"按严重程度: {severity_stats}")
        
        # 显示置信度分布
        confidences = [analysis.confidence_score for analysis in results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        print(f"平均置信度: {avg_confidence:.2f}")
        
        print("\n🎯 演示完成！")
        
    finally:
        # 清理临时文件
        Path(temp_file).unlink()


if __name__ == "__main__":
    main() 