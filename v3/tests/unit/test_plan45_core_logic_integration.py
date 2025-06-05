"""
PLAN 45: 更新相关单元测试 (核心逻辑下沉)

测试应用层正确使用核心逻辑函数，验证数据转换和错误处理。
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from v3.application import GameCommandService, GameQueryService, QueryResult
from v3.application.query_service import GameStateSnapshot, AvailableActions
from v3.application.config_service import ConfigService
from v3.core.events import EventBus, set_event_bus
from v3.core.state_machine.types import GamePhase, GameContext
from v3.core.rules.types import CorePermissibleActionsData, ActionConstraints
from v3.core.betting.betting_types import BetType
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestPlan45CoreLogicIntegration:
    """PLAN 45: 测试应用层使用核心逻辑的集成"""
    
    def setup_method(self):
        """设置测试环境"""
        # 创建独立的事件总线
        self.event_bus = EventBus()
        set_event_bus(self.event_bus)
        
        # 创建真实的服务实例
        self.command_service = GameCommandService(self.event_bus)
        self.config_service = ConfigService()
        self.query_service = GameQueryService(
            command_service=self.command_service,
            config_service=self.config_service
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")
    
    def test_get_available_actions_uses_core_logic(self):
        """测试get_available_actions正确使用核心逻辑"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 使用patch监视核心函数调用
        with patch('v3.core.rules.determine_permissible_actions') as mock_core_func:
            # 设置mock返回值
            mock_constraints = ActionConstraints(
                min_call_amount=100,
                min_raise_amount=200,
                max_raise_amount=1000,
                big_blind_amount=100,
                is_all_in_available=True
            )
            mock_core_data = CorePermissibleActionsData(
                player_id="p1",
                available_bet_types=[BetType.FOLD, BetType.CALL, BetType.RAISE, BetType.ALL_IN],
                constraints=mock_constraints,
                player_chips=1000,
                is_player_active=True
            )
            mock_core_func.return_value = mock_core_data
            
            # 创建游戏并开始手牌
            self.command_service.create_new_game("core_logic_test", ["p1", "p2"])
            self.command_service.start_new_hand("core_logic_test")
            
            # 获取可用行动
            result = self.query_service.get_available_actions("core_logic_test", "p1")
            
            # 验证核心函数被调用
            assert mock_core_func.called
            call_args = mock_core_func.call_args
            assert len(call_args[0]) == 2  # GameContext和player_id
            game_context, player_id = call_args[0]
            assert isinstance(game_context, GameContext)
            assert game_context.game_id == "core_logic_test"
            assert player_id == "p1"
            
            # 验证结果正确转换
            assert result.success is True
            actions = result.data
            assert actions.player_id == "p1"
            assert set(actions.actions) == {"fold", "call", "raise", "all_in"}
            assert actions.min_bet == 100
            assert actions.max_bet == 1000
    
    def test_get_available_actions_core_data_conversion(self):
        """测试核心层数据向应用层的正确转换"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        with patch('v3.core.rules.determine_permissible_actions') as mock_core_func:
            # 测试只有fold和check的场景
            mock_constraints = ActionConstraints(
                min_call_amount=0,
                min_raise_amount=0,
                max_raise_amount=0,
                big_blind_amount=100,
                is_all_in_available=False
            )
            mock_core_data = CorePermissibleActionsData(
                player_id="p1",
                available_bet_types=[BetType.FOLD, BetType.CHECK],
                constraints=mock_constraints,
                player_chips=1000,
                is_player_active=True
            )
            mock_core_func.return_value = mock_core_data
            
            # 创建游戏
            self.command_service.create_new_game("conversion_test", ["p1", "p2"])
            self.command_service.start_new_hand("conversion_test")
            
            # 获取可用行动
            result = self.query_service.get_available_actions("conversion_test", "p1")
            
            # 验证转换结果
            assert result.success is True
            actions = result.data
            assert set(actions.actions) == {"fold", "check"}
            assert actions.min_bet == 0
            assert actions.max_bet == 0
    
    def test_get_available_actions_core_exception_handling(self):
        """测试核心层函数异常时的处理"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        with patch('v3.core.rules.determine_permissible_actions') as mock_core_func:
            # 设置核心函数抛出异常
            mock_core_func.side_effect = Exception("核心层计算错误")
            
            # 创建游戏
            self.command_service.create_new_game("exception_test", ["p1", "p2"])
            self.command_service.start_new_hand("exception_test")
            
            # 获取可用行动
            result = self.query_service.get_available_actions("exception_test", "p1")
            
            # 验证异常被正确处理
            assert result.success is False
            assert result.error_code == "GET_AVAILABLE_ACTIONS_FAILED"
            assert "核心层计算错误" in result.message
    
    def test_get_available_actions_invalid_phase_handling(self):
        """测试无效游戏阶段的处理"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏
        self.command_service.create_new_game("invalid_phase_test", ["p1", "p2"])
        self.command_service.start_new_hand("invalid_phase_test")
        
        # 使用patch修改快照中的阶段为无效值
        with patch.object(self.command_service, 'get_game_state_snapshot') as mock_snapshot:
            invalid_snapshot = GameStateSnapshot(
                game_id="invalid_phase_test",
                current_phase="INVALID_PHASE",  # 无效阶段
                players={"p1": {"chips": 1000, "active": True}},
                community_cards=[],
                pot_total=0,
                current_bet=0,
                active_player_id="p1",
                timestamp=time.time()
            )
            mock_snapshot.return_value = QueryResult.success_result(invalid_snapshot)
            
            # 获取可用行动
            result = self.query_service.get_available_actions("invalid_phase_test", "p1")
            
            # 验证错误处理
            assert result.success is False
            assert result.error_code == "INVALID_GAME_PHASE"
    
    def test_get_available_actions_snapshot_failure_propagation(self):
        """测试快照获取失败时的错误传播"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 使用patch让快照获取失败
        with patch.object(self.command_service, 'get_game_state_snapshot') as mock_snapshot:
            mock_snapshot.return_value = QueryResult.failure_result(
                "游戏不存在", 
                error_code="GAME_NOT_FOUND"
            )
            
            # 获取可用行动
            result = self.query_service.get_available_actions("nonexistent_game", "p1")
            
            # 验证错误被正确传播
            assert result.success is False
            assert result.error_code == "GAME_NOT_FOUND"
            assert "游戏不存在" in result.message
    
    def test_core_logic_integration_with_real_game_context(self):
        """测试与真实游戏上下文的核心逻辑集成"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建真实游戏
        self.command_service.create_new_game("real_context_test", ["p1", "p2"])
        self.command_service.start_new_hand("real_context_test")
        
        # 不使用mock，测试真实的核心逻辑调用
        result = self.query_service.get_available_actions("real_context_test", "p1")
        
        # 验证结果
        assert result.success is True
        actions = result.data
        assert isinstance(actions, AvailableActions)
        assert actions.player_id == "p1"
        assert len(actions.actions) > 0
        
        # 验证包含基本行动
        assert "fold" in actions.actions
        # 在PRE_FLOP阶段应该有call或check
        assert any(action in actions.actions for action in ["call", "check"])
    
    def test_verify_old_methods_removed(self):
        """验证旧的内部方法已被移除"""
        # 确保旧方法不再存在
        assert not hasattr(self.query_service, '_determine_available_actions')
        
        # 验证没有任何代码直接调用已删除的方法
        import inspect
        source = inspect.getsource(self.query_service.get_available_actions)
        assert '_determine_available_actions' not in source
        assert 'determine_permissible_actions' in source
    
    def test_anti_cheat_verification(self):
        """测试反作弊验证"""
        # 确保所有服务对象都是真实的
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")
        
        # 创建游戏并验证核心对象被正确使用
        create_result = self.command_service.create_new_game("anti_cheat_test", ["p1", "p2"])
        assert create_result.success
        
        start_result = self.command_service.start_new_hand("anti_cheat_test")
        assert start_result.success
        
        # 验证查询操作使用真实对象
        actions_result = self.query_service.get_available_actions("anti_cheat_test", "p1")
        assert actions_result.success
        assert isinstance(actions_result.data, AvailableActions) 