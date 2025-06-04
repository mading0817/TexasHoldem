"""
Coverage Verifier Tests - 覆盖率验证器测试

测试覆盖率验证器的功能，确保测试真正覆盖了核心代码路径。
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List

from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker
from v3.tests.anti_cheat.coverage_verifier import CoverageVerifier
from v3.core.state_machine.types import GamePhase, GameContext


class TestCoverageVerifier:
    """覆盖率验证器测试类"""
    
    def test_verifier_creation(self):
        """测试验证器创建"""
        verifier = CoverageVerifier()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        # 验证初始状态
        assert verifier.get_tracked_modules() == []
        assert verifier.get_coverage_stats() == {}
    
    def test_start_coverage_tracking(self):
        """测试开始覆盖率跟踪"""
        verifier = CoverageVerifier()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        # 开始跟踪
        verifier.start_coverage_tracking("test_function")
        
        # 验证跟踪状态
        assert verifier.is_tracking()
        assert verifier.get_current_test_name() == "test_function"
    
    def test_stop_coverage_tracking(self):
        """测试停止覆盖率跟踪"""
        verifier = CoverageVerifier()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        # 开始并停止跟踪
        verifier.start_coverage_tracking("test_function")
        assert verifier.is_tracking()
        
        coverage_data = verifier.stop_coverage_tracking()
        
        # 验证停止后状态
        assert not verifier.is_tracking()
        assert isinstance(coverage_data, dict)
        assert "test_name" in coverage_data
        assert coverage_data["test_name"] == "test_function"
    
    def test_verify_core_module_coverage_sufficient(self):
        """测试验证核心模块覆盖率 - 充足"""
        verifier = CoverageVerifier()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        # 模拟高覆盖率的测试
        verifier.start_coverage_tracking("test_high_coverage")
        
        # 执行一些核心模块操作
        context = GameContext(
            game_id="test_game",
            current_phase=GamePhase.PRE_FLOP,
            players={"player1": {}, "player2": {}},
            community_cards=[],
            pot_total=0,
            current_bet=0,
            small_blind=50,
            big_blind=100
        )
        phase = GamePhase.PRE_FLOP
        
        # 停止跟踪并验证
        verifier.stop_coverage_tracking()
        
        # 验证覆盖率应该通过（使用较低的阈值）
        verifier.verify_core_module_coverage("test_high_coverage", min_coverage=0.1)
    
    def test_verify_core_module_coverage_insufficient(self):
        """测试验证核心模块覆盖率 - 不足"""
        verifier = CoverageVerifier()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        # 模拟低覆盖率的测试
        verifier.start_coverage_tracking("test_low_coverage")
        
        # 执行很少的核心模块操作
        dummy_result = "minimal_operation"
        
        # 停止跟踪
        verifier.stop_coverage_tracking()
        
        # 验证应该失败（要求过高的覆盖率）
        with pytest.raises(AssertionError, match="核心模块覆盖率不足"):
            verifier.verify_core_module_coverage("test_low_coverage", min_coverage=0.9)
    
    def test_get_coverage_report(self):
        """测试获取覆盖率报告"""
        verifier = CoverageVerifier()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        # 执行多个测试
        for i in range(3):
            test_name = f"test_function_{i}"
            verifier.start_coverage_tracking(test_name)
            
            # 执行一些操作
            context = GameContext(
                game_id=f"test_game_{i}",
                current_phase=GamePhase.PRE_FLOP,
                players={"player1": {}, "player2": {}},
                community_cards=[],
                pot_total=0,
                current_bet=0,
                small_blind=50,
                big_blind=100
            )
            
            verifier.stop_coverage_tracking()
        
        # 获取覆盖率报告
        report = verifier.get_coverage_report()
        
        # 验证报告内容
        assert isinstance(report, dict)
        assert "total_tests" in report
        assert "average_coverage" in report
        assert "tests_details" in report
        assert report["total_tests"] == 3
        assert len(report["tests_details"]) == 3
    
    def test_verify_line_coverage(self):
        """测试验证行覆盖率"""
        verifier = CoverageVerifier()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        # 模拟行覆盖率数据
        line_coverage = {
            "v3/core/state_machine/types.py": {
                "covered_lines": [1, 2, 3, 5, 7, 8, 10],
                "total_lines": 10,
                "coverage_percentage": 0.7
            }
        }
        
        # 验证行覆盖率
        verifier.verify_line_coverage(line_coverage, min_coverage=0.6)
        
        # 验证应该失败（要求过高的覆盖率）
        with pytest.raises(AssertionError, match="行覆盖率不足"):
            verifier.verify_line_coverage(line_coverage, min_coverage=0.8)
    
    def test_verify_branch_coverage(self):
        """测试验证分支覆盖率"""
        verifier = CoverageVerifier()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        # 模拟分支覆盖率数据
        branch_coverage = {
            "v3/core/state_machine/types.py": {
                "covered_branches": 6,
                "total_branches": 8,
                "coverage_percentage": 0.75
            }
        }
        
        # 验证分支覆盖率
        verifier.verify_branch_coverage(branch_coverage, min_coverage=0.7)
        
        # 验证应该失败（要求过高的覆盖率）
        with pytest.raises(AssertionError, match="分支覆盖率不足"):
            verifier.verify_branch_coverage(branch_coverage, min_coverage=0.8)
    
    def test_get_uncovered_lines(self):
        """测试获取未覆盖的行"""
        verifier = CoverageVerifier()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        # 模拟覆盖率数据
        coverage_data = {
            "v3/core/state_machine/types.py": {
                "covered_lines": [1, 2, 3, 5, 7, 8, 10],
                "total_lines": 10
            }
        }
        
        # 获取未覆盖的行
        uncovered = verifier.get_uncovered_lines(coverage_data)
        
        # 验证结果
        assert isinstance(uncovered, dict)
        assert "v3/core/state_machine/types.py" in uncovered
        expected_uncovered = [4, 6, 9]  # 未覆盖的行号
        assert uncovered["v3/core/state_machine/types.py"] == expected_uncovered
    
    def test_reset_coverage_data(self):
        """测试重置覆盖率数据"""
        verifier = CoverageVerifier()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        # 执行一些跟踪
        verifier.start_coverage_tracking("test_function")
        context = GameContext(
            game_id="test_game",
            current_phase=GamePhase.PRE_FLOP,
            players={"player1": {}, "player2": {}},
            community_cards=[],
            pot_total=0,
            current_bet=0,
            small_blind=50,
            big_blind=100
        )
        verifier.stop_coverage_tracking()
        
        # 验证有数据
        assert len(verifier.get_coverage_stats()) > 0
        
        # 重置数据
        verifier.reset_coverage_data()
        
        # 验证重置后状态
        assert verifier.get_coverage_stats() == {}
        assert verifier.get_tracked_modules() == []
    
    def test_coverage_context_manager(self):
        """测试覆盖率上下文管理器"""
        verifier = CoverageVerifier()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        # 使用上下文管理器
        with verifier.coverage_context("test_context"):
            # 执行一些核心模块操作
            context = GameContext(
                game_id="test_game",
                current_phase=GamePhase.PRE_FLOP,
                players={"player1": {}, "player2": {}},
                community_cards=[],
                pot_total=0,
                current_bet=0,
                small_blind=50,
                big_blind=100
            )
            phase = GamePhase.PRE_FLOP
        
        # 验证上下文管理器正确工作
        coverage_stats = verifier.get_coverage_stats()
        assert "test_context" in coverage_stats
        
        # 验证覆盖率数据
        test_data = coverage_stats["test_context"]
        assert "coverage_percentage" in test_data
        assert test_data["coverage_percentage"] >= 0 