"""
测试GameQueryService重构为使用状态快照接口 (PLAN 40)

验证查询服务正确使用CommandService的get_game_state_snapshot方法，
而不是直接访问内部session。
"""

import pytest
from unittest.mock import Mock, MagicMock

from v3.application.query_service import GameQueryService, GameStateSnapshot, PlayerInfo, AvailableActions
from v3.application.types import QueryResult
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestGameQueryServiceSnapshotIntegration:
    """测试GameQueryService与状态快照接口的集成"""
    
    def setup_method(self):
        """设置测试环境"""
        # 创建mock command service
        self.mock_command_service = Mock()
        self.mock_config_service = Mock()
        
        # 创建真实的GameQueryService实例
        self.query_service = GameQueryService(
            command_service=self.mock_command_service,
            config_service=self.mock_config_service
        )
        
        # 反作弊检查 - 确保使用真实对象
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
    
    def test_get_game_state_uses_snapshot_interface(self):
        """测试get_game_state使用快照接口而不是直接访问session"""
        # Arrange
        game_id = "test_game_123"
        expected_snapshot = GameStateSnapshot(
            game_id=game_id,
            current_phase="PRE_FLOP",
            players={"player_1": {"chips": 1000}},
            community_cards=[],
            pot_total=30,
            current_bet=20,
            active_player_id="player_1",
            timestamp=123.456
        )
        
        # 模拟command_service.get_game_state_snapshot返回成功
        self.mock_command_service.get_game_state_snapshot.return_value = QueryResult.success_result(expected_snapshot)
        
        # Act
        result = self.query_service.get_game_state(game_id)
        
        # Assert
        assert result.success
        assert result.data == expected_snapshot
        
        # 验证调用了正确的方法
        self.mock_command_service.get_game_state_snapshot.assert_called_once_with(game_id)
        
        # 验证没有直接访问_get_session
        assert not hasattr(self.mock_command_service, '_get_session') or \
               not self.mock_command_service._get_session.called
    
    def test_get_game_state_handles_snapshot_failure(self):
        """测试get_game_state正确处理快照接口失败"""
        # Arrange
        game_id = "nonexistent_game"
        
        # 模拟command_service.get_game_state_snapshot返回失败
        self.mock_command_service.get_game_state_snapshot.return_value = QueryResult.business_rule_violation(
            "游戏不存在", 
            error_code="GAME_NOT_FOUND"
        )
        
        # Act
        result = self.query_service.get_game_state(game_id)
        
        # Assert
        assert not result.success
        assert result.error_code == "GAME_NOT_FOUND"
        assert "游戏不存在" in result.message
        
        # 验证调用了正确的方法
        self.mock_command_service.get_game_state_snapshot.assert_called_once_with(game_id)
    
    def test_get_player_info_uses_snapshot_interface(self):
        """测试get_player_info使用快照接口获取玩家信息"""
        # Arrange
        game_id = "test_game_123"
        player_id = "player_1"
        
        snapshot = GameStateSnapshot(
            game_id=game_id,
            current_phase="PRE_FLOP",
            players={
                "player_1": {
                    "chips": 1000, 
                    "active": True, 
                    "current_bet": 20,
                    "hole_cards": ["Ah", "Kd"]
                }
            },
            community_cards=[],
            pot_total=30,
            current_bet=20,
            active_player_id="player_1",
            timestamp=123.456
        )
        
        self.mock_command_service.get_game_state_snapshot.return_value = QueryResult.success_result(snapshot)
        
        # Act
        result = self.query_service.get_player_info(game_id, player_id)
        
        # Assert
        assert result.success
        assert isinstance(result.data, PlayerInfo)
        assert result.data.player_id == player_id
        assert result.data.chips == 1000
        assert result.data.active == True
        assert result.data.current_bet == 20
        assert result.data.hole_cards == ["Ah", "Kd"]
        
        # 验证调用了正确的方法
        self.mock_command_service.get_game_state_snapshot.assert_called_once_with(game_id)
    
    def test_get_player_info_handles_player_not_found(self):
        """测试get_player_info正确处理玩家不存在的情况"""
        # Arrange
        game_id = "test_game_123"
        player_id = "nonexistent_player"
        
        snapshot = GameStateSnapshot(
            game_id=game_id,
            current_phase="PRE_FLOP",
            players={"player_1": {"chips": 1000}},
            community_cards=[],
            pot_total=30,
            current_bet=20,
            active_player_id="player_1",
            timestamp=123.456
        )
        
        self.mock_command_service.get_game_state_snapshot.return_value = QueryResult.success_result(snapshot)
        
        # Act
        result = self.query_service.get_player_info(game_id, player_id)
        
        # Assert
        assert not result.success
        assert result.error_code == "PLAYER_NOT_IN_GAME"
        assert "不在游戏中" in result.message
    
    def test_get_available_actions_uses_snapshot_interface(self):
        """测试get_available_actions使用快照接口获取可用行动"""
        # Arrange
        game_id = "test_game_123"
        player_id = "player_1"
        
        snapshot = GameStateSnapshot(
            game_id=game_id,
            current_phase="PRE_FLOP",
            players={
                "player_1": {"chips": 1000, "active": True, "current_bet": 0},
                "player_2": {"chips": 1000, "active": True, "current_bet": 20}
            },
            community_cards=[],
            pot_total=30,
            current_bet=20,
            active_player_id="player_1",
            timestamp=123.456
        )
        
        self.mock_command_service.get_game_state_snapshot.return_value = QueryResult.success_result(snapshot)
        
        # Act
        result = self.query_service.get_available_actions(game_id, player_id)
        
        # Assert
        assert result.success
        assert isinstance(result.data, AvailableActions)
        assert result.data.player_id == player_id
        assert "call" in result.data.actions  # 应该可以跟注
        assert "raise" in result.data.actions  # 应该可以加注
        assert "fold" in result.data.actions  # 应该可以弃牌
        
        # 验证调用了正确的方法
        self.mock_command_service.get_game_state_snapshot.assert_called_once_with(game_id)
    
    def test_is_game_over_uses_snapshot_interface(self):
        """测试is_game_over使用快照接口判断游戏是否结束"""
        # Arrange
        game_id = "test_game_123"
        
        snapshot = GameStateSnapshot(
            game_id=game_id,
            current_phase="FINISHED",
            players={"player_1": {"chips": 2000, "active": False}},
            community_cards=["Ah", "Kd", "Qc", "Js", "Tc"],
            pot_total=0,
            current_bet=0,
            active_player_id=None,
            timestamp=123.456
        )
        
        self.mock_command_service.get_game_state_snapshot.return_value = QueryResult.success_result(snapshot)
        
        # Act
        result = self.query_service.is_game_over(game_id)
        
        # Assert
        assert result.success
        assert result.data == True  # 游戏已结束
        
        # 验证调用了正确的方法
        self.mock_command_service.get_game_state_snapshot.assert_called_once_with(game_id)
    
    def test_get_phase_info_uses_snapshot_interface(self):
        """测试get_phase_info使用快照接口获取阶段信息"""
        # Arrange
        game_id = "test_game_123"
        
        snapshot = GameStateSnapshot(
            game_id=game_id,
            current_phase="FLOP",
            players={"player_1": {"chips": 1000}},
            community_cards=["Ah", "Kd", "Qc"],
            pot_total=100,
            current_bet=0,
            active_player_id="player_1",
            timestamp=123.456
        )
        
        self.mock_command_service.get_game_state_snapshot.return_value = QueryResult.success_result(snapshot)
        
        # Act
        result = self.query_service.get_phase_info(game_id)
        
        # Assert
        assert result.success
        assert result.data["current_phase"] == "FLOP"
        assert len(result.data["community_cards"]) == 3
        
        # 验证调用了正确的方法
        self.mock_command_service.get_game_state_snapshot.assert_called_once_with(game_id)
    
    def test_anti_cheat_verification(self):
        """反作弊测试：验证查询服务使用真实对象"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 验证不是mock对象
        assert not isinstance(self.query_service, Mock)
        assert not isinstance(self.query_service, MagicMock)
        
        # 验证核心方法存在
        assert hasattr(self.query_service, 'get_game_state')
        assert hasattr(self.query_service, 'get_player_info')
        assert hasattr(self.query_service, 'get_available_actions')
        assert callable(getattr(self.query_service, 'get_game_state')) 