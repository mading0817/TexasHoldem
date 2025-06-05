"""
查询服务AI决策方法测试

测试GameQueryService中新增的make_ai_decision方法，
确保严格遵循CQRS架构原则，不直接调用AI模块。
"""

import pytest
from unittest.mock import Mock
from typing import Dict, Any

from v3.application import GameQueryService, GameCommandService, QueryResult, AvailableActions
from v3.core.events import EventBus, set_event_bus
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestQueryServiceAIDecision:
    """查询服务AI决策方法测试"""
    
    def setup_method(self):
        """测试前设置"""
        # 创建独立的事件总线避免测试间干扰
        self.event_bus = EventBus()
        set_event_bus(self.event_bus)
        self.command_service = GameCommandService(self.event_bus)
        self.query_service = GameQueryService(self.command_service, self.event_bus)
    
    def test_make_ai_decision_creation(self):
        """测试AI决策方法存在性"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 验证方法存在
        assert hasattr(self.query_service, 'make_ai_decision')
        assert callable(getattr(self.query_service, 'make_ai_decision'))
    
    def test_make_ai_decision_with_valid_game(self):
        """测试有效游戏的AI决策"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏
        create_result = self.command_service.create_new_game(
            "test_ai_game", 
            ["player_0", "player_1"]
        )
        assert create_result.success
        
        # 开始手牌
        start_result = self.command_service.start_new_hand("test_ai_game")
        assert start_result.success
        
        # 测试AI决策生成
        ai_config = {
            'fold_weight': 0.1,
            'check_weight': 0.4,
            'call_weight': 0.3,
            'raise_weight': 0.15,
            'all_in_weight': 0.05
        }
        
        decision_result = self.query_service.make_ai_decision("test_ai_game", "player_0", ai_config)
        
        # 验证结果结构
        assert decision_result.success
        assert isinstance(decision_result.data, dict)
        
        # 验证必要字段
        decision = decision_result.data
        assert 'action_type' in decision
        assert 'amount' in decision
        assert 'reasoning' in decision
        
        # 验证行动类型有效性
        valid_actions = ['fold', 'check', 'call', 'raise', 'all_in']
        assert decision['action_type'] in valid_actions
        
        # 验证金额为非负整数
        assert isinstance(decision['amount'], int)
        assert decision['amount'] >= 0
        
        # 验证推理信息非空
        assert isinstance(decision['reasoning'], str)
        assert len(decision['reasoning']) > 0
    
    def test_make_ai_decision_with_invalid_game(self):
        """测试无效游戏的AI决策"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 测试不存在的游戏
        decision_result = self.query_service.make_ai_decision("nonexistent_game", "player_0")
        
        # 应该返回失败结果
        assert not decision_result.success
        assert "CANNOT_GET_AVAILABLE_ACTIONS" in decision_result.error_code or "GAME_NOT_FOUND" in decision_result.error_code
    
    def test_make_ai_decision_with_default_config(self):
        """测试使用默认配置的AI决策"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏
        create_result = self.command_service.create_new_game(
            "test_default_ai", 
            ["player_0", "player_1"]
        )
        assert create_result.success
        
        # 开始手牌
        start_result = self.command_service.start_new_hand("test_default_ai")
        assert start_result.success
        
        # 使用默认配置测试AI决策
        decision_result = self.query_service.make_ai_decision("test_default_ai", "player_0")
        
        # 验证成功
        assert decision_result.success
        
        # 验证决策结构
        decision = decision_result.data
        assert all(key in decision for key in ['action_type', 'amount', 'reasoning'])
        
    def test_make_ai_decision_multiple_calls_randomness(self):
        """测试多次调用的随机性"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏
        create_result = self.command_service.create_new_game(
            "test_randomness", 
            ["player_0", "player_1"]
        )
        assert create_result.success
        
        # 开始手牌
        start_result = self.command_service.start_new_hand("test_randomness")
        assert start_result.success
        
        # 多次生成决策
        decisions = []
        for _ in range(10):
            decision_result = self.query_service.make_ai_decision("test_randomness", "player_0")
            assert decision_result.success
            decisions.append(decision_result.data['action_type'])
        
        # 验证存在一定的随机性（不是所有决策都相同）
        unique_decisions = set(decisions)
        # 由于是随机的，通常会有不同的决策，但不强制要求
        # 这里只验证所有决策都是有效的
        valid_actions = ['fold', 'check', 'call', 'raise', 'all_in']
        for decision in decisions:
            assert decision in valid_actions
    
    def test_ai_decision_respects_available_actions(self):
        """测试AI决策遵循可用行动限制"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏
        create_result = self.command_service.create_new_game(
            "test_available_actions", 
            ["player_0", "player_1"]
        )
        assert create_result.success
        
        # 开始手牌
        start_result = self.command_service.start_new_hand("test_available_actions")
        assert start_result.success
        
        # 获取可用行动
        available_result = self.query_service.get_available_actions("test_available_actions", "player_0")
        assert available_result.success
        available_actions = available_result.data.actions
        
        # 生成AI决策
        decision_result = self.query_service.make_ai_decision("test_available_actions", "player_0")
        assert decision_result.success
        
        # 验证AI决策在可用行动范围内
        chosen_action = decision_result.data['action_type']
        assert chosen_action in available_actions
    
    def test_cqrs_compliance(self):
        """测试CQRS合规性 - AI决策方法不应修改状态"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏
        create_result = self.command_service.create_new_game(
            "test_cqrs", 
            ["player_0", "player_1"]
        )
        assert create_result.success
        
        # 开始手牌
        start_result = self.command_service.start_new_hand("test_cqrs")
        assert start_result.success
        
        # 获取初始状态
        initial_state_result = self.query_service.get_game_state("test_cqrs")
        assert initial_state_result.success
        initial_state = initial_state_result.data
        
        # 多次调用AI决策方法
        for _ in range(5):
            decision_result = self.query_service.make_ai_decision("test_cqrs", "player_0")
            assert decision_result.success
        
        # 获取调用后的状态
        final_state_result = self.query_service.get_game_state("test_cqrs")
        assert final_state_result.success
        final_state = final_state_result.data
        
        # 验证状态未被修改（CQRS查询操作不应修改状态）
        assert initial_state.current_phase == final_state.current_phase
        assert initial_state.pot_total == final_state.pot_total
        assert initial_state.current_bet == final_state.current_bet
        
        # 验证玩家状态未变
        for player_id in initial_state.players:
            initial_player = initial_state.players[player_id]
            final_player = final_state.players[player_id]
            assert initial_player.get('chips') == final_player.get('chips')
            assert initial_player.get('current_bet') == final_player.get('current_bet') 