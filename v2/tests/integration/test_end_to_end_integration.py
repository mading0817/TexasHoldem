"""
端到端集成测试

使用pytest框架测试完整闭环集成测试框架的功能。
"""

import pytest
import sys
from pathlib import Path

# 添加v2目录到Python路径
v2_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(v2_path))

from v2.tests.integration.end_to_end_loop import EndToEndLoopTester
from v2.tests.integration.performance_benchmarks import PerformanceBenchmarkSuite
from v2.tests.integration.test_integration_demo import IntegrationTestDemo


@pytest.mark.integration
@pytest.mark.fast
class TestEndToEndIntegration:
    """端到端集成测试类"""
    
    def setup_method(self):
        """设置测试方法"""
        self.demo = IntegrationTestDemo()
        self.tester = EndToEndLoopTester()
        self.benchmark_suite = PerformanceBenchmarkSuite()
    
    @pytest.mark.integration
    @pytest.mark.fast
    def test_complete_hand_simulation(self):
        """测试完整手牌模拟"""
        result = self.demo.test_complete_hand_simulation()
        assert result["success"], "完整手牌模拟测试失败"
        assert len(result["actions_executed"]) > 0, "没有执行任何行动"
        assert result["hand_completed"], "手牌没有完成"
    
    @pytest.mark.integration
    @pytest.mark.fast
    def test_user_operation_simulator(self):
        """测试用户操作模拟器"""
        self.demo.setup_game()
        result = self.demo.test_user_operation_simulator()
        assert result["success"], "用户操作模拟器测试失败"
        assert result["successful_operations"] > 0, "没有成功执行任何操作"
        assert result["success_rate"] > 0, "成功率为0"
    
    @pytest.mark.integration
    @pytest.mark.fast
    def test_performance_benchmarks(self):
        """测试性能基准"""
        self.demo.setup_game()
        result = self.demo.test_performance_benchmarks()
        assert result["success"], f"性能基准测试失败: {result.get('error', '未知错误')}"
        assert result["passed_benchmarks"] > 0, "没有通过任何基准测试"
    
    @pytest.mark.integration
    @pytest.mark.fast
    @pytest.mark.end_to_end
    def test_end_to_end_loop(self):
        """测试端到端循环"""
        self.demo.setup_game()
        result = self.demo.test_end_to_end_loop()
        assert result["success"], f"端到端循环测试失败: {result.get('error', '未知错误')}"
        assert result["steps_executed"] > 0, "没有执行任何步骤"
    
    @pytest.mark.integration
    @pytest.mark.fast
    @pytest.mark.end_to_end
    def test_standalone_end_to_end_tester(self):
        """测试独立的端到端测试器"""
        result = self.tester.run_complete_test()
        assert result.success, f"端到端测试失败: {result.error_message}"
        assert result.steps_executed > 0, "没有执行任何步骤"
        assert result.state_changes >= 0, "状态变更数量异常"
    
    @pytest.mark.integration
    @pytest.mark.fast
    def test_standalone_performance_benchmarks(self):
        """测试独立的性能基准测试"""
        results = self.benchmark_suite.run_benchmarks()
        assert len(results) > 0, "没有运行任何基准测试"
        
        # 检查至少有一个测试通过
        passed_count = sum(1 for r in results if r.passed)
        assert passed_count > 0, "没有通过任何基准测试"
    
    @pytest.mark.integration
    @pytest.mark.fast
    @pytest.mark.end_to_end
    def test_integration_framework_completeness(self):
        """测试集成框架的完整性"""
        # 运行所有演示测试
        results = self.demo.run_all_demos()
        
        # 检查所有测试类型都被执行
        test_names = {r["test_name"] for r in results}
        expected_tests = {
            "complete_hand_simulation",
            "user_operation_simulator", 
            "performance_benchmarks",
            "end_to_end_loop"
        }
        
        assert test_names == expected_tests, f"缺少测试类型: {expected_tests - test_names}"
        
        # 检查成功率
        passed_count = sum(1 for r in results if r["success"])
        success_rate = passed_count / len(results)
        assert success_rate >= 0.75, f"成功率过低: {success_rate:.1%}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 