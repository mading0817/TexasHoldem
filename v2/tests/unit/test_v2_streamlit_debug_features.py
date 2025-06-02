"""
Unit tests for Streamlit debug features and performance decoupling.

Tests for PLAN #39: 调试开关与性能解耦缺失
"""

import pytest
import logging
import time
from unittest.mock import Mock, patch, MagicMock
import streamlit as st

from v2.ui.streamlit.app import run_log_level_performance_test, run_auto_play_test


class TestStreamlitDebugFeatures:
    """测试Streamlit调试功能和性能解耦."""
    
    def setup_method(self):
        """每个测试前重置状态."""
        # 清空session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # 重置日志级别
        logging.getLogger().setLevel(logging.INFO)
    
    def test_log_level_performance_test_basic(self):
        """测试日志级别性能对比测试的基本功能."""
        # Mock session state controller
        mock_controller = Mock()
        mock_controller._logger = Mock()
        st.session_state.controller = mock_controller
        
        # Mock run_auto_play_test to return quickly
        with patch('v2.ui.streamlit.app.run_auto_play_test') as mock_auto_play:
            mock_auto_play.return_value = {"hands_played": 3, "errors": []}
            
            results = run_log_level_performance_test()
            
            # 验证返回结果包含所有日志级别
            expected_levels = ["ERROR", "WARNING", "INFO", "DEBUG"]
            assert all(level in results for level in expected_levels)
            
            # 验证所有结果都是数字（时间）
            for level, duration in results.items():
                assert isinstance(duration, (int, float))
                assert duration >= 0
            
            # 验证run_auto_play_test被调用了4次（每个日志级别一次）
            assert mock_auto_play.call_count == 4
    
    def test_log_level_changes_applied(self):
        """测试日志级别变更是否正确应用."""
        # Mock session state controller
        mock_controller = Mock()
        mock_controller._logger = Mock()
        st.session_state.controller = mock_controller
        
        original_level = logging.getLogger().level
        
        with patch('v2.ui.streamlit.app.run_auto_play_test') as mock_auto_play:
            mock_auto_play.return_value = {"hands_played": 3, "errors": []}
            
            run_log_level_performance_test()
            
            # 验证日志级别被恢复到原始值
            assert logging.getLogger().level == original_level
            
            # 验证控制器的logger级别也被设置
            assert mock_controller._logger.setLevel.call_count >= 4
    
    def test_performance_test_timing(self):
        """测试性能测试的时间测量功能."""
        # Mock session state controller
        mock_controller = Mock()
        st.session_state.controller = mock_controller
        
        # Mock run_auto_play_test with controlled timing
        def slow_auto_play(*args, **kwargs):
            time.sleep(0.1)  # 模拟耗时操作
            return {"hands_played": 3, "errors": []}
        
        with patch('v2.ui.streamlit.app.run_auto_play_test', side_effect=slow_auto_play):
            start_time = time.time()
            results = run_log_level_performance_test()
            end_time = time.time()
            
            # 验证总耗时合理（4个级别 × 0.1秒 + 一些开销）
            total_duration = end_time - start_time
            assert total_duration >= 0.4  # 至少0.4秒
            assert total_duration <= 2.0   # 不超过2秒
            
            # 验证每个级别的耗时都大于0
            for level, duration in results.items():
                assert duration > 0
    
    def test_log_level_performance_comparison(self):
        """测试不同日志级别的性能差异."""
        # Mock session state controller
        mock_controller = Mock()
        mock_controller._logger = Mock()
        st.session_state.controller = mock_controller
        
        # Mock run_auto_play_test with different timing based on log level
        def variable_timing_auto_play(*args, **kwargs):
            current_level = logging.getLogger().level
            # DEBUG级别模拟更慢的执行
            if current_level == logging.DEBUG:
                time.sleep(0.05)
            else:
                time.sleep(0.01)
            return {"hands_played": 3, "errors": []}
        
        with patch('v2.ui.streamlit.app.run_auto_play_test', side_effect=variable_timing_auto_play):
            results = run_log_level_performance_test()
            
            # 验证DEBUG级别通常比其他级别慢
            debug_time = results.get("DEBUG", 0)
            other_times = [results.get(level, 0) for level in ["ERROR", "WARNING", "INFO"]]
            
            # DEBUG应该比其他级别慢（允许一些误差）
            avg_other_time = sum(other_times) / len(other_times) if other_times else 0
            assert debug_time >= avg_other_time * 0.8  # 允许20%的误差
    
    def test_auto_play_test_performance_metrics(self):
        """测试自动游戏测试的性能指标."""
        # Mock session state controller
        mock_controller = Mock()
        mock_controller.start_new_hand.return_value = True
        mock_controller.is_hand_over.side_effect = [False, False, True] * 10  # 模拟3个行动后结束
        mock_controller.get_current_player_id.side_effect = [0, 1, None] * 10
        mock_controller.process_ai_action.return_value = True
        mock_controller.end_hand.return_value = None
        
        # Mock initial and final snapshots
        mock_player = Mock()
        mock_player.chips = 1000
        mock_snapshot = Mock()
        mock_snapshot.players = [mock_player, mock_player]
        mock_controller.get_snapshot.return_value = mock_snapshot
        
        st.session_state.controller = mock_controller
        
        start_time = time.time()
        results = run_auto_play_test(5)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # 验证测试结果
        assert results["hands_played"] <= 5
        assert "total_chips_start" in results
        assert "total_chips_end" in results
        assert "chip_conservation" in results
        assert isinstance(results["errors"], list)
        
        # 验证性能合理（5手牌应该在合理时间内完成）
        assert duration <= 5.0  # 不超过5秒
    
    def test_log_level_restoration_on_exception(self):
        """测试异常情况下日志级别是否正确恢复."""
        # Mock session state controller
        mock_controller = Mock()
        mock_controller._logger = Mock()
        st.session_state.controller = mock_controller
        
        original_level = logging.getLogger().level
        
        # Mock run_auto_play_test to raise exception
        with patch('v2.ui.streamlit.app.run_auto_play_test') as mock_auto_play:
            mock_auto_play.side_effect = Exception("Test exception")
            
            try:
                run_log_level_performance_test()
            except Exception:
                pass  # 忽略异常
            
            # 验证即使发生异常，日志级别也被恢复
            assert logging.getLogger().level == original_level
    
    def test_performance_test_with_different_hand_counts(self):
        """测试不同手牌数量的性能测试."""
        # Mock session state controller
        mock_controller = Mock()
        mock_controller.start_new_hand.return_value = True
        mock_controller.is_hand_over.return_value = True
        mock_controller.get_current_player_id.return_value = None
        mock_controller.end_hand.return_value = None
        
        # Mock snapshots
        mock_player = Mock()
        mock_player.chips = 1000
        mock_snapshot = Mock()
        mock_snapshot.players = [mock_player]
        mock_controller.get_snapshot.return_value = mock_snapshot
        
        st.session_state.controller = mock_controller
        
        # 测试不同手牌数量
        hand_counts = [1, 3, 5, 10]
        
        for count in hand_counts:
            start_time = time.time()
            results = run_auto_play_test(count)
            end_time = time.time()
            
            duration = end_time - start_time
            
            # 验证手牌数量与耗时的关系
            assert results["hands_played"] <= count
            # 更多手牌通常需要更多时间（允许一些变化）
            expected_max_time = count * 0.5  # 每手牌最多0.5秒
            assert duration <= expected_max_time + 1.0  # 加1秒缓冲 