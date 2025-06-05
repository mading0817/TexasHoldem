"""
PLAN 41: 更新相关单元测试 (服务解耦)

验证服务解耦是否正确实现：
1. GameCommandService的get_game_state_snapshot方法正确工作
2. GameQueryService正确使用快照接口，不直接访问session
3. 服务间依赖关系正确
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from v3.application import GameCommandService, GameQueryService, PlayerAction
from v3.application.types import CommandResult, QueryResult
from v3.application.query_service import GameStateSnapshot, PlayerInfo, AvailableActions
from v3.application.config_service import ConfigService
from v3.core.events import EventBus, get_event_bus, set_event_bus
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestPlan41ServiceDecoupling:
    """PLAN 41: 服务解耦测试"""
    
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
    
    def test_command_service_has_snapshot_interface(self):
        """测试CommandService有状态快照接口（PLAN 39）"""
        # 验证方法存在
        assert hasattr(self.command_service, 'get_game_state_snapshot')
        assert callable(getattr(self.command_service, 'get_game_state_snapshot'))
        
        # 创建游戏进行测试
        create_result = self.command_service.create_new_game("test_snapshot", ["p1", "p2"])
        assert create_result.success
        
        # 测试快照接口
        snapshot_result = self.command_service.get_game_state_snapshot("test_snapshot")
        
        assert isinstance(snapshot_result, QueryResult)
        assert snapshot_result.success
        assert isinstance(snapshot_result.data, GameStateSnapshot)
        assert snapshot_result.data.game_id == "test_snapshot"
    
    def test_query_service_uses_snapshot_interface(self):
        """测试QueryService使用快照接口而不是直接访问session（PLAN 40）"""
        # 创建游戏
        create_result = self.command_service.create_new_game("test_interface", ["p1", "p2"])
        assert create_result.success
        
        # 使用mock监视command_service的方法调用
        with patch.object(self.command_service, 'get_game_state_snapshot', 
                         wraps=self.command_service.get_game_state_snapshot) as mock_snapshot:
            
            # 调用查询服务的方法
            result = self.query_service.get_game_state("test_interface")
            
            # 验证使用了快照接口
            assert result.success
            mock_snapshot.assert_called_once_with("test_interface")
    
    def test_query_service_get_player_info_uses_snapshot(self):
        """测试get_player_info使用快照接口"""
        # 创建游戏
        create_result = self.command_service.create_new_game("test_player_info", ["p1", "p2"])
        assert create_result.success
        
        # 使用mock监视command_service的方法调用
        with patch.object(self.command_service, 'get_game_state_snapshot', 
                         wraps=self.command_service.get_game_state_snapshot) as mock_snapshot:
            
            # 调用查询服务的方法
            result = self.query_service.get_player_info("test_player_info", "p1")
            
            # 验证使用了快照接口
            assert result.success
            assert isinstance(result.data, PlayerInfo)
            mock_snapshot.assert_called_once_with("test_player_info")
    
    def test_query_service_get_available_actions_uses_snapshot(self):
        """测试get_available_actions使用快照接口"""
        # 创建游戏并开始手牌
        create_result = self.command_service.create_new_game("test_actions", ["p1", "p2"])
        assert create_result.success
        
        start_result = self.command_service.start_new_hand("test_actions")
        assert start_result.success
        
        # 使用mock监视command_service的方法调用
        with patch.object(self.command_service, 'get_game_state_snapshot', 
                         wraps=self.command_service.get_game_state_snapshot) as mock_snapshot:
            
            # 调用查询服务的方法
            result = self.query_service.get_available_actions("test_actions", "p1")
            
            # 验证使用了快照接口
            assert result.success
            assert isinstance(result.data, AvailableActions)
            mock_snapshot.assert_called_once_with("test_actions")
    
    def test_query_service_does_not_access_session_directly(self):
        """测试QueryService不直接访问CommandService的_get_session方法"""
        # 创建游戏
        create_result = self.command_service.create_new_game("test_no_session", ["p1", "p2"])
        assert create_result.success
        
        # Mock _get_session方法，应该不被调用
        with patch.object(self.command_service, '_get_session') as mock_get_session:
            
            # 调用查询服务的各种方法
            self.query_service.get_game_state("test_no_session")
            self.query_service.get_player_info("test_no_session", "p1")
            
            # 验证_get_session没有被调用
            mock_get_session.assert_not_called()
    
    def test_service_constructor_dependencies(self):
        """测试服务构造函数的依赖注入正确"""
        # 测试CommandService构造函数
        command_service = GameCommandService(self.event_bus)
        CoreUsageChecker.verify_real_objects(command_service, "GameCommandService")
        
        # 测试QueryService构造函数
        query_service = GameQueryService(
            command_service=command_service,
            config_service=self.config_service
        )
        CoreUsageChecker.verify_real_objects(query_service, "GameQueryService")
        
        # 验证依赖正确注入
        assert query_service._command_service is command_service
        assert query_service._config_service is self.config_service
    
    def test_service_decoupling_integration(self):
        """测试服务解耦的完整集成"""
        # 创建游戏
        game_id = "test_decoupling"
        create_result = self.command_service.create_new_game(game_id, ["p1", "p2"])
        assert create_result.success
        
        # 开始手牌
        start_result = self.command_service.start_new_hand(game_id)
        assert start_result.success
        
        # 通过查询服务获取状态（应该使用快照接口）
        state_result = self.query_service.get_game_state(game_id)
        assert state_result.success
        assert state_result.data.current_phase == "PRE_FLOP"
        
        # 执行玩家行动
        action = PlayerAction(action_type="call", amount=0, player_id="p1")
        action_result = self.command_service.execute_player_action(game_id, "p1", action)
        assert action_result.success
        
        # 再次查询状态（验证状态一致性）
        state_result2 = self.query_service.get_game_state(game_id)
        assert state_result2.success
        
        # 验证通过快照获取的状态是最新的
        assert state_result2.data.game_id == game_id
        assert state_result2.data.current_phase == "PRE_FLOP"
    
    def test_snapshot_interface_error_handling(self):
        """测试快照接口的错误处理"""
        # 测试不存在的游戏
        snapshot_result = self.command_service.get_game_state_snapshot("nonexistent")
        assert not snapshot_result.success
        assert snapshot_result.error_code == "GAME_NOT_FOUND"
        
        # 测试查询服务如何处理快照接口的错误
        query_result = self.query_service.get_game_state("nonexistent")
        assert not query_result.success
        assert query_result.error_code == "GAME_NOT_FOUND"
    
    def test_anti_cheat_verification(self):
        """测试反作弊验证"""
        # 确保所有服务对象都是真实的
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")
        
        # 创建游戏并验证核心对象被正确使用
        create_result = self.command_service.create_new_game("anti_cheat_test", ["p1", "p2"])
        assert create_result.success
        
        # 验证查询操作使用真实对象
        state_result = self.query_service.get_game_state("anti_cheat_test")
        assert state_result.success
        assert isinstance(state_result.data, GameStateSnapshot)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 