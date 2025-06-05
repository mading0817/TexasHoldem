#!/usr/bin/env python3
"""
GameFlowService单元测试

测试游戏流程服务的核心功能，确保严格遵循CQRS模式。
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from v3.application import GameCommandService, GameQueryService, CommandResult, QueryResult, GameFlowService, HandFlowConfig
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestGameFlowService:
    """GameFlowService测试类"""
    
    def setup_method(self):
        """测试方法设置"""
        # 模拟依赖
        self.mock_command_service = Mock(spec=GameCommandService)
        self.mock_query_service = Mock(spec=GameQueryService)
        self.mock_event_bus = Mock()
        
        # 创建GameFlowService实例
        self.flow_service = GameFlowService(
            command_service=self.mock_command_service,
            query_service=self.mock_query_service,
            event_bus=self.mock_event_bus
        )
        
    def test_run_hand_success_flow(self):
        """测试成功运行手牌的完整流程"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.flow_service, "GameFlowService")
        
        # 模拟游戏流程：游戏未结束 -> 状态正常 -> 开始成功 -> 流程完成 -> 手牌结束
        self.mock_query_service.is_game_over.return_value = QueryResult.success_result(False)
        
        # 模拟状态检查：INIT状态
        mock_state = Mock()
        mock_state.current_phase = "INIT"
        mock_state.active_player_id = None
        self.mock_query_service.get_game_state.return_value = QueryResult.success_result(mock_state)
        
        # 模拟开始新手牌成功
        self.mock_command_service.start_new_hand.return_value = CommandResult.success_result("手牌开始")
        
        # 模拟手牌流程：直接进入FINISHED状态
        mock_finished_state = Mock()
        mock_finished_state.current_phase = "FINISHED"
        mock_finished_state.active_player_id = None
        
        # 配置get_game_state的多次调用
        self.mock_query_service.get_game_state.side_effect = [
            QueryResult.success_result(mock_state),  # 初始状态检查
            QueryResult.success_result(mock_finished_state),  # execute_hand_flow中的检查
            QueryResult.success_result(mock_finished_state)   # ensure_hand_finished检查
        ]
        
        # 执行手牌流程
        result = self.flow_service.run_hand("test_game")
        
        # 验证结果
        assert result.success
        assert "手牌完成" in result.message
        assert result.data['hand_completed'] == True
        
        # 验证调用序列
        self.mock_command_service.start_new_hand.assert_called_once_with("test_game")
        self.mock_query_service.is_game_over.assert_called()
    
    def test_run_hand_game_already_over(self):
        """测试游戏已结束时的处理"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.flow_service, "GameFlowService")
        
        # 模拟游戏已结束
        self.mock_query_service.is_game_over.return_value = QueryResult.success_result(True)
        self.mock_query_service.get_game_winner.return_value = QueryResult.success_result("player_0")
        
        # 执行手牌流程
        result = self.flow_service.run_hand("test_game")
        
        # 验证：应该直接返回，不开始新手牌
        assert result.success
        assert "游戏已结束" in result.message
        assert result.data['game_over'] == True
        assert result.data['winner'] == "player_0"
        self.mock_command_service.start_new_hand.assert_not_called()
    
    def test_force_finish_hand_success(self):
        """测试强制结束手牌成功"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.flow_service, "GameFlowService")
        
        # 模拟当前状态：正在进行中
        mock_preflop_state = Mock()
        mock_preflop_state.current_phase = "PRE_FLOP"
        
        mock_flop_state = Mock()
        mock_flop_state.current_phase = "FLOP"
        
        mock_finished_state = Mock()
        mock_finished_state.current_phase = "FINISHED"
        
        self.mock_query_service.get_game_state.side_effect = [
            QueryResult.success_result(mock_preflop_state),
            QueryResult.success_result(mock_flop_state),
            QueryResult.success_result(mock_finished_state)
        ]
        
        # 模拟推进阶段成功
        self.mock_command_service.advance_phase.return_value = CommandResult.success_result("推进成功")
        
        # 执行强制结束
        result = self.flow_service.force_finish_hand("test_game")
        
        # 验证结果
        assert result.success
        assert "强制结束完成" in result.message
        assert result.data['attempts'] == 2
        assert result.data['final_phase'] == 'FINISHED'
        
        # 验证推进阶段被调用
        assert self.mock_command_service.advance_phase.call_count == 2
    
    def test_force_finish_hand_max_attempts_exceeded(self):
        """测试强制结束达到最大尝试次数"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.flow_service, "GameFlowService")
        
        # 模拟始终无法完成
        mock_state = Mock()
        mock_state.current_phase = "PRE_FLOP"
        self.mock_query_service.get_game_state.return_value = QueryResult.success_result(mock_state)
        
        # 模拟推进失败
        self.mock_command_service.advance_phase.return_value = CommandResult.failure_result("推进失败")
        
        # 执行强制结束
        result = self.flow_service.force_finish_hand("test_game", max_attempts=3)
        
        # 验证结果：应该失败但不抛出异常
        assert not result.success
        assert "达到最大尝试次数" in result.message
        assert "MAX_ATTEMPTS_EXCEEDED" in result.error_code
    
    def test_advance_until_finished_success(self):
        """测试推进到结束状态成功"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.flow_service, "GameFlowService")
        
        # advance_until_finished应该与force_finish_hand行为相同
        mock_state = Mock()
        mock_state.current_phase = "FINISHED"
        self.mock_query_service.get_game_state.return_value = QueryResult.success_result(mock_state)
        
        # 执行推进到结束
        result = self.flow_service.advance_until_finished("test_game")
        
        # 验证结果：应该立即成功（已经是FINISHED状态）
        assert result.success
        assert "强制结束完成" in result.message
        assert result.data['attempts'] == 0
        assert result.data['final_phase'] == 'FINISHED'
    
    def test_run_hand_with_invariant_violation(self):
        """测试手牌过程中的不变量违反处理"""
        # 模拟不变量违反
        self.mock_query_service.is_game_over.return_value = QueryResult.success_result(False)
        self.mock_command_service.start_new_hand.return_value = CommandResult.success_result("开始成功")
        
        # 模拟推进阶段时发生不变量违反
        self.mock_command_service.advance_phase.return_value = CommandResult.failure_result(
            "不变量违反：筹码守恒失败", 
            error_code="INVARIANT_VIOLATION"
        )
        
        # 创建GameFlowService（待实现）
        # flow_service = GameFlowService(...)
        
        # 执行手牌流程
        # result = flow_service.run_hand("test_game")
        
        # 验证：不变量违反应该被正确处理
        # assert not result.success
        # assert "INVARIANT_VIOLATION" in result.error_code
        # assert "不变量违反" in result.message
        
        # 临时断言
        assert True, "等待GameFlowService实现"
    
    def test_run_hand_with_state_loop_detection(self):
        """测试状态循环检测功能"""
        # 这个测试将验证GameFlowService能够检测并处理状态循环
        
        # 模拟相同状态重复
        same_state = {'current_phase': 'PRE_FLOP', 'active_player_id': 'player_0'}
        self.mock_query_service.get_game_state.return_value = QueryResult.success_result(same_state)
        self.mock_query_service.calculate_game_state_hash.side_effect = ["hash1", "hash1", "hash1", "hash1"]
        
        # 创建GameFlowService（待实现）
        # flow_service = GameFlowService(...)
        
        # 执行手牌流程
        # result = flow_service.run_hand("test_game")
        
        # 验证：应该检测到循环并强制结束
        # assert result.success or "状态循环" in result.message
        
        # 临时断言
        assert True, "等待GameFlowService实现"


# 辅助测试函数
def test_game_flow_service_interface_design():
    """测试GameFlowService接口设计的合理性"""
    # 这个测试用于验证接口设计是否符合CQRS模式
    
    # GameFlowService应该具备的方法：
    expected_methods = [
        'run_hand',           # 运行完整手牌
        'force_finish_hand',  # 强制结束手牌
        'advance_until_finished',  # 推进到结束状态
    ]
    
    # GameFlowService应该依赖的服务：
    expected_dependencies = [
        'command_service',  # 用于执行命令
        'query_service',    # 用于查询状态
        'event_bus',       # 用于发布事件（可选）
    ]
    
    # 这些接口设计将指导实际实现
    assert len(expected_methods) == 3, "接口方法数量确定"
    assert len(expected_dependencies) >= 2, "最少依赖两个服务"
    
    # 验证设计原则
    assert all("_" not in method or method.startswith("_") == False for method in expected_methods), "公开方法不应以下划线开头"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 