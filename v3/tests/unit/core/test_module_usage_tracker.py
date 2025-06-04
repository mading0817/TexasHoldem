"""
Module Usage Tracker Tests - 模块使用跟踪器测试

测试模块使用跟踪器的功能，确保能够正确跟踪和验证核心模块的使用情况。
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Any

from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker
from v3.tests.anti_cheat.module_usage_tracker import ModuleUsageTracker
from v3.core.state_machine.types import GamePhase, GameContext
from v3.core.snapshot.types import GameStateSnapshot


class TestModuleUsageTracker:
    """模块使用跟踪器测试类"""
    
    def test_tracker_creation(self):
        """测试跟踪器创建"""
        tracker = ModuleUsageTracker()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        
        # 验证初始状态
        assert tracker.get_tracked_modules() == []
        assert tracker.get_call_count() == 0
    
    def test_track_core_module_calls_decorator(self):
        """测试核心模块调用跟踪装饰器"""
        tracker = ModuleUsageTracker()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        
        @tracker.track_core_module_calls
        def test_function():
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
        
        # 执行被装饰的函数
        result = test_function()
        
        # 验证跟踪结果
        assert tracker.get_call_count() > 0
        tracked_modules = tracker.get_tracked_modules()
        assert any("v3.core" in module for module in tracked_modules)
        
        # 验证返回的对象是真实的
        CoreUsageChecker.verify_real_objects(result, "GameContext")
    
    def test_verify_real_objects_used_with_real_objects(self):
        """测试验证真实对象使用 - 真实对象"""
        tracker = ModuleUsageTracker()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        
        # 创建真实对象列表
        real_objects = [
            GameContext(
                game_id="test_game",
                current_phase=GamePhase.PRE_FLOP,
                players={"player1": {}, "player2": {}},
                community_cards=[],
                pot_total=0,
                current_bet=0,
                small_blind=50,
                big_blind=100
            ),
            GamePhase.PRE_FLOP
        ]
        
        # 验证应该通过
        tracker.verify_real_objects_used(real_objects)
    
    def test_verify_real_objects_used_with_mock_objects(self):
        """测试验证真实对象使用 - mock对象"""
        tracker = ModuleUsageTracker()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        
        # 创建包含mock对象的列表
        mock_objects = [
            Mock(),
            MagicMock(),
            "fake_object"
        ]
        
        # 验证应该失败
        with pytest.raises(AssertionError, match="检测到mock对象"):
            tracker.verify_real_objects_used(mock_objects)
    
    def test_verify_real_objects_used_mixed_objects(self):
        """测试验证真实对象使用 - 混合对象"""
        tracker = ModuleUsageTracker()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        
        # 创建混合对象列表（真实对象 + mock对象）
        mixed_objects = [
            GameContext(
                game_id="test_game",
                current_phase=GamePhase.PRE_FLOP,
                players={"player1": {}, "player2": {}},
                community_cards=[],
                pot_total=0,
                current_bet=0,
                small_blind=50,
                big_blind=100
            ),
            Mock()  # 这个mock对象应该被检测到
        ]
        
        # 验证应该失败
        with pytest.raises(AssertionError, match="检测到mock对象"):
            tracker.verify_real_objects_used(mixed_objects)
    
    def test_get_module_usage_stats(self):
        """测试获取模块使用统计"""
        tracker = ModuleUsageTracker()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        
        @tracker.track_core_module_calls
        def test_function():
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
        
        # 执行多次
        for _ in range(3):
            test_function()
        
        # 获取统计信息
        stats = tracker.get_module_usage_stats()
        
        # 验证统计信息
        assert isinstance(stats, dict)
        assert "total_calls" in stats
        assert "modules_used" in stats
        assert "core_modules_percentage" in stats
        assert stats["total_calls"] >= 3
        assert stats["core_modules_percentage"] > 0
    
    def test_reset_tracking(self):
        """测试重置跟踪"""
        tracker = ModuleUsageTracker()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        
        @tracker.track_core_module_calls
        def test_function():
            return GameContext(
                game_id="test_game",
                current_phase=GamePhase.PRE_FLOP,
                players={"player1": {}, "player2": {}},
                community_cards=[],
                pot_total=0,
                current_bet=0,
                small_blind=50,
                big_blind=100
            )
        
        # 执行一些操作
        test_function()
        assert tracker.get_call_count() > 0
        
        # 重置跟踪
        tracker.reset_tracking()
        
        # 验证重置后状态
        assert tracker.get_call_count() == 0
        assert tracker.get_tracked_modules() == []
    
    def test_verify_core_module_usage_percentage(self):
        """测试验证核心模块使用百分比"""
        tracker = ModuleUsageTracker()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        
        @tracker.track_core_module_calls
        def test_function_with_core_usage():
            # 大量使用核心模块
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
            return context, phase
        
        # 执行函数
        test_function_with_core_usage()
        
        # 验证核心模块使用百分比应该很高
        tracker.verify_core_module_usage_percentage(min_percentage=0.05)  # 至少5%
    
    def test_verify_core_module_usage_percentage_insufficient(self):
        """测试验证核心模块使用百分比 - 不足"""
        tracker = ModuleUsageTracker()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(tracker, "ModuleUsageTracker")
        
        @tracker.track_core_module_calls
        def test_function_minimal_core_usage():
            # 最少的核心模块使用
            return "non_core_result"
        
        # 执行函数
        test_function_minimal_core_usage()
        
        # 验证应该失败（要求过高的百分比）
        with pytest.raises(AssertionError, match="核心模块使用百分比不足"):
            tracker.verify_core_module_usage_percentage(min_percentage=0.9)  # 要求90% 