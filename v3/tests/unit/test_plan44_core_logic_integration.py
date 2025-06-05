"""
PLAN 44: 应用层使用核心逻辑测试

测试 GameQueryService 正确使用核心层的 determine_permissible_actions 函数。
"""

import pytest
from unittest.mock import Mock, MagicMock
from v3.application.query_service import GameQueryService, AvailableActions
from v3.application.command_service import GameCommandService
from v3.application.config_service import ConfigService
from v3.application.types import QueryResult
from v3.core.state_machine.types import GameContext, GamePhase
from v3.core.betting.betting_types import BetType
from v3.core.rules.types import CorePermissibleActionsData, ActionConstraints
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestPlan44CoreLogicIntegration:
    """测试PLAN 44: 应用层使用核心逻辑"""
    
    def setup_method(self):
        """设置测试环境"""
        # 创建模拟的依赖
        self.config_service = ConfigService()
        self.command_service = Mock(spec=GameCommandService)
        self.query_service = GameQueryService(
            command_service=self.command_service,
            config_service=self.config_service
        )
        
        # 创建测试用的游戏状态快照
        self.test_snapshot = Mock()
        self.test_snapshot.game_id = "test_game"
        self.test_snapshot.current_phase = "PRE_FLOP"
        self.test_snapshot.players = {
            "player1": {
                "chips": 1000,
                "active": True,
                "current_bet": 0
            }
        }
        self.test_snapshot.community_cards = []
        self.test_snapshot.pot_total = 150
        self.test_snapshot.current_bet = 100
        self.test_snapshot.active_player_id = "player1"
    
    def test_get_available_actions_uses_core_logic_anti_cheat(self):
        """反作弊检查：确保使用真实核心逻辑"""
        # 设置mock返回成功的快照
        self.command_service.get_game_state_snapshot.return_value = QueryResult.success_result(self.test_snapshot)
        
        # 调用方法
        result = self.query_service.get_available_actions("test_game", "player1")
        
        # 反作弊验证：确保结果是真实对象
        assert result.success is True
        CoreUsageChecker.verify_real_objects(result, "QueryResult")
        CoreUsageChecker.verify_real_objects(result.data, "AvailableActions")
        
        # 验证调用了快照接口
        self.command_service.get_game_state_snapshot.assert_called_once_with("test_game")
    
    def test_get_available_actions_core_logic_integration(self):
        """测试与核心逻辑的正确集成"""
        # 设置mock返回成功的快照
        self.command_service.get_game_state_snapshot.return_value = QueryResult.success_result(self.test_snapshot)
        
        # 调用方法
        result = self.query_service.get_available_actions("test_game", "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "QueryResult")
        
        # 验证成功
        assert result.success is True
        
        # 验证返回的数据结构
        available_actions = result.data
        assert isinstance(available_actions, AvailableActions)
        assert available_actions.player_id == "player1"
        assert isinstance(available_actions.actions, list)
        assert all(isinstance(action, str) for action in available_actions.actions)
        
        # 验证包含预期的行动类型（基于当前下注100，玩家有1000筹码的场景）
        expected_actions = {'fold', 'call', 'raise', 'all_in'}
        actual_actions = set(available_actions.actions)
        assert actual_actions == expected_actions
        
        # 验证约束信息
        assert available_actions.min_bet == 100  # call amount
        assert available_actions.max_bet == 1000  # max raise amount
    
    def test_get_available_actions_no_current_bet_scenario(self):
        """测试没有当前下注的场景"""
        # 修改快照：没有当前下注
        self.test_snapshot.current_bet = 0
        self.test_snapshot.players["player1"]["current_bet"] = 0
        
        self.command_service.get_game_state_snapshot.return_value = QueryResult.success_result(self.test_snapshot)
        
        result = self.query_service.get_available_actions("test_game", "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "QueryResult")
        
        assert result.success is True
        available_actions = result.data
        
        # 验证行动类型（没有当前下注时应该能check而不是call）
        expected_actions = {'fold', 'check', 'raise', 'all_in'}
        actual_actions = set(available_actions.actions)
        assert actual_actions == expected_actions
        
        # 验证约束
        assert available_actions.min_bet == 0  # no call needed
    
    def test_get_available_actions_inactive_player(self):
        """测试非活跃玩家的场景"""
        # 修改快照：玩家非活跃
        self.test_snapshot.players["player1"]["active"] = False
        
        self.command_service.get_game_state_snapshot.return_value = QueryResult.success_result(self.test_snapshot)
        
        result = self.query_service.get_available_actions("test_game", "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "QueryResult")
        
        assert result.success is True
        available_actions = result.data
        
        # 非活跃玩家应该没有可用行动
        assert available_actions.actions == []
    
    def test_get_available_actions_invalid_phase(self):
        """测试无效阶段的场景"""
        # 修改快照：设置为SHOWDOWN阶段
        self.test_snapshot.current_phase = "SHOWDOWN"
        
        self.command_service.get_game_state_snapshot.return_value = QueryResult.success_result(self.test_snapshot)
        
        result = self.query_service.get_available_actions("test_game", "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "QueryResult")
        
        assert result.success is True
        available_actions = result.data
        
        # SHOWDOWN阶段只能弃牌
        assert available_actions.actions == ['fold']
    
    def test_get_available_actions_player_not_found(self):
        """测试玩家不存在的场景"""
        self.command_service.get_game_state_snapshot.return_value = QueryResult.success_result(self.test_snapshot)
        
        result = self.query_service.get_available_actions("test_game", "nonexistent_player")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "QueryResult")
        
        # 应该返回失败
        assert result.success is False
        assert result.error_code == "PLAYER_NOT_IN_GAME"
    
    def test_get_available_actions_command_service_failure(self):
        """测试命令服务失败的场景"""
        # 设置命令服务返回失败
        self.command_service.get_game_state_snapshot.return_value = QueryResult.failure_result(
            "游戏不存在", 
            error_code="GAME_NOT_FOUND"
        )
        
        result = self.query_service.get_available_actions("test_game", "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "QueryResult")
        
        # 应该传播失败
        assert result.success is False
        assert result.error_code == "GAME_NOT_FOUND"
    
    def test_get_available_actions_no_command_service(self):
        """测试命令服务未初始化的场景"""
        # 创建没有命令服务的查询服务
        query_service = GameQueryService(command_service=None, config_service=self.config_service)
        
        result = query_service.get_available_actions("test_game", "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "QueryResult")
        
        # 应该返回失败
        assert result.success is False
        assert result.error_code == "COMMAND_SERVICE_NOT_INITIALIZED"
    
    def test_get_available_actions_unknown_phase_enum(self):
        """测试未知阶段枚举的场景"""
        # 设置一个不存在的阶段名称
        self.test_snapshot.current_phase = "UNKNOWN_PHASE"
        
        self.command_service.get_game_state_snapshot.return_value = QueryResult.success_result(self.test_snapshot)
        
        result = self.query_service.get_available_actions("test_game", "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "QueryResult")
        
        # 应该返回失败
        assert result.success is False
        assert result.error_code == "INVALID_GAME_PHASE"
    
    def test_get_available_actions_exception_handling(self):
        """测试异常处理"""
        # 设置命令服务抛出异常
        self.command_service.get_game_state_snapshot.side_effect = Exception("Test exception")
        
        result = self.query_service.get_available_actions("test_game", "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "QueryResult")
        
        # 应该捕获异常并返回失败
        assert result.success is False
        assert result.error_code == "GET_AVAILABLE_ACTIONS_FAILED"
        assert "Test exception" in result.message
    
    def test_core_logic_data_conversion(self):
        """测试核心层数据向应用层的正确转换"""
        self.command_service.get_game_state_snapshot.return_value = QueryResult.success_result(self.test_snapshot)
        
        result = self.query_service.get_available_actions("test_game", "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "QueryResult")
        
        assert result.success is True
        available_actions = result.data
        
        # 验证数据类型转换：从BetType枚举转为小写字符串
        for action in available_actions.actions:
            assert isinstance(action, str)
            assert action.islower()
            # 验证是有效的BetType名称
            assert any(action == bet_type.name.lower() for bet_type in BetType)
        
        # 验证约束信息的正确映射
        assert isinstance(available_actions.min_bet, int)
        assert isinstance(available_actions.max_bet, int)
        assert available_actions.min_bet >= 0
        assert available_actions.max_bet >= 0
    
    def test_verify_old_method_removed(self):
        """验证旧的_determine_available_actions方法已被移除"""
        # 确保旧方法不再存在
        assert not hasattr(self.query_service, '_determine_available_actions')
        
        # 验证没有任何代码直接调用已删除的方法
        import inspect
        source = inspect.getsource(GameQueryService.get_available_actions)
        assert '_determine_available_actions' not in source
        assert 'determine_permissible_actions' in source 