"""
Anti-Cheat Integration Tests - 反作弊系统集成测试

测试反作弊系统各组件的协作，确保整个反作弊框架正常工作。
"""

import pytest
from unittest.mock import Mock, MagicMock

from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker
from v3.tests.anti_cheat.module_usage_tracker import ModuleUsageTracker
from v3.tests.anti_cheat.coverage_verifier import CoverageVerifier
from v3.tests.anti_cheat.state_consistency_checker import StateConsistencyChecker
from v3.core.state_machine.types import GamePhase, GameContext
from v3.core.snapshot.types import GameStateSnapshot


class TestAntiCheatIntegration:
    """反作弊系统集成测试类"""
    
    def test_complete_anti_cheat_workflow(self):
        """测试完整的反作弊工作流"""
        # 1. 创建反作弊组件
        tracker = ModuleUsageTracker()
        verifier = CoverageVerifier()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        # 2. 使用跟踪器和覆盖率验证器
        @tracker.track_core_module_calls
        def test_function():
            with verifier.coverage_context("test_workflow"):
                # 创建真实的核心对象
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
                return context
        
        # 3. 执行测试函数
        result = test_function()
        
        # 4. 验证结果
        CoreUsageChecker.verify_real_objects(result, "GameContext")
        
        # 5. 检查跟踪统计
        stats = tracker.get_module_usage_stats()
        assert stats["total_calls"] > 0
        assert stats["core_modules_percentage"] > 0
        
        # 6. 检查覆盖率统计
        coverage_stats = verifier.get_coverage_stats()
        assert "test_workflow" in coverage_stats
        assert coverage_stats["test_workflow"]["coverage_percentage"] >= 0
    
    def test_anti_cheat_mock_detection(self):
        """测试反作弊系统的mock检测能力"""
        tracker = ModuleUsageTracker()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        
        # 创建真实对象和mock对象
        real_context = GameContext(
            game_id="test_game",
            current_phase=GamePhase.PRE_FLOP,
            players={"player1": {}, "player2": {}},
            community_cards=[],
            pot_total=0,
            current_bet=0,
            small_blind=50,
            big_blind=100
        )
        
        mock_object = Mock()
        
        # 验证真实对象通过检查
        tracker.verify_real_objects_used([real_context])
        
        # 验证mock对象被检测到
        with pytest.raises(AssertionError, match="检测到mock对象"):
            tracker.verify_real_objects_used([mock_object])
    
    def test_state_consistency_integration(self):
        """测试状态一致性检查集成"""
        # 导入GameStateSnapshot类
        from v3.tests.anti_cheat.state_consistency_checker import GameStateSnapshot
        
        # 创建状态快照
        before_snapshot = GameStateSnapshot(
            total_chips=1000,
            pot_size=0,
            player_chips={"player1": 500, "player2": 500},
            current_phase="PRE_FLOP",
            current_bet=0,
            active_players=["player1", "player2"]
        )
        
        after_snapshot = GameStateSnapshot(
            total_chips=1000,  # 筹码守恒
            pot_size=100,
            player_chips={"player1": 450, "player2": 450},
            current_phase="PRE_FLOP",
            current_bet=50,
            active_players=["player1", "player2"]
        )
        
        # 验证筹码守恒
        StateConsistencyChecker.verify_chip_conservation(before_snapshot, after_snapshot)
        
        # 验证下注规则
        StateConsistencyChecker.verify_betting_rules(
            before_snapshot, after_snapshot, "player1", "raise", 50
        )
    
    def test_anti_cheat_performance(self):
        """测试反作弊系统性能"""
        tracker = ModuleUsageTracker()
        verifier = CoverageVerifier()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        import time
        
        @tracker.track_core_module_calls
        def performance_test():
            start_time = time.time()
            
            with verifier.coverage_context("performance_test"):
                # 执行多个核心模块操作
                for i in range(10):
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
            
            end_time = time.time()
            return end_time - start_time
        
        # 执行性能测试
        duration = performance_test()
        
        # 验证性能（反作弊开销应该很小）
        assert duration < 1.0  # 应该在1秒内完成
        
        # 验证跟踪数据
        stats = tracker.get_module_usage_stats()
        assert stats["total_calls"] >= 10
    
    def test_anti_cheat_error_handling(self):
        """测试反作弊系统错误处理"""
        tracker = ModuleUsageTracker()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        
        # 测试空列表
        tracker.verify_real_objects_used([])
        
        # 测试包含None的列表
        with pytest.raises(AssertionError):
            tracker.verify_real_objects_used([None])
        
        # 测试无效的百分比要求
        with pytest.raises(AssertionError):
            tracker.verify_core_module_usage_percentage(min_percentage=2.0)  # 超过100%
    
    def test_anti_cheat_report_generation(self):
        """测试反作弊报告生成"""
        # 生成反作弊报告
        report = CoreUsageChecker.generate_anti_cheat_report()
        
        # 验证报告结构
        assert hasattr(report, 'passed')
        assert hasattr(report, 'violations')
        assert hasattr(report, 'warnings')
        assert hasattr(report, 'object_count')
        assert hasattr(report, 'mock_objects_detected')
        assert hasattr(report, 'module_violations')
        
        # 验证报告内容
        assert isinstance(report.passed, bool)
        assert isinstance(report.violations, list)
        assert isinstance(report.warnings, list)
        assert isinstance(report.object_count, int)
        assert isinstance(report.mock_objects_detected, int)
        assert isinstance(report.module_violations, int)
    
    def test_anti_cheat_cache_performance(self):
        """测试反作弊缓存性能"""
        # 创建相同的对象多次
        contexts = []
        for i in range(5):
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
            contexts.append(context)
        
        import time
        
        # 第一次验证（填充缓存）
        start_time = time.time()
        for context in contexts:
            CoreUsageChecker.verify_real_objects(context, "GameContext")
        first_duration = time.time() - start_time
        
        # 第二次验证（使用缓存）
        start_time = time.time()
        for context in contexts:
            CoreUsageChecker.verify_real_objects(context, "GameContext")
        second_duration = time.time() - start_time
        
        # 缓存应该提高性能（第二次应该更快或相近）
        assert second_duration <= first_duration * 1.5  # 允许一些误差
    
    def test_module_boundary_verification(self):
        """测试模块边界验证"""
        # 创建核心模块对象
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
        
        # 验证模块边界
        allowed_modules = ["v3.core.", "v3.tests."]
        CoreUsageChecker.verify_module_boundaries(context, allowed_modules)
        
        # 验证不允许的模块会被拒绝
        with pytest.raises(AssertionError, match="对象来自不允许的模块"):
            CoreUsageChecker.verify_module_boundaries(context, ["v3.ui."])
    
    def test_comprehensive_anti_cheat_validation(self):
        """测试综合反作弊验证"""
        # 创建所有反作弊组件
        tracker = ModuleUsageTracker()
        verifier = CoverageVerifier()
        
        # 验证所有组件都是真实对象
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        CoreUsageChecker.verify_real_objects(verifier, "CoverageVerifier")
        
        # 执行综合测试
        @tracker.track_core_module_calls
        def comprehensive_test():
            with verifier.coverage_context("comprehensive_test"):
                # 创建多种核心对象
                context = GameContext(
                    game_id="comprehensive_test",
                    current_phase=GamePhase.PRE_FLOP,
                    players={"player1": {}, "player2": {}},
                    community_cards=[],
                    pot_total=0,
                    current_bet=0,
                    small_blind=50,
                    big_blind=100
                )
                
                phase = GamePhase.FLOP
                
                return context, phase
        
        # 执行测试
        result_context, result_phase = comprehensive_test()
        
        # 验证所有结果
        CoreUsageChecker.verify_real_objects(result_context, "GameContext")
        assert result_phase == GamePhase.FLOP
        
        # 验证跟踪统计
        usage_stats = tracker.get_module_usage_stats()
        assert usage_stats["core_modules_percentage"] > 0
        
        # 验证覆盖率统计
        coverage_stats = verifier.get_coverage_stats()
        assert "comprehensive_test" in coverage_stats
        
        # 生成最终报告
        report = CoreUsageChecker.generate_anti_cheat_report()
        assert report.passed or len(report.violations) == 0 