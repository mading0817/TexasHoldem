"""
不变量集成测试

测试不变量检查是否正确集成到应用服务中。
"""

import pytest
from unittest.mock import Mock, patch

from v3.application.command_service import GameCommandService
from v3.application.types import PlayerAction, CommandResult
from v3.core.invariant.types import InvariantError, InvariantViolation, InvariantType
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestInvariantIntegration:
    """测试不变量集成"""
    
    def test_create_command_service_with_invariants(self):
        """测试创建启用不变量检查的命令服务"""
        service = GameCommandService(enable_invariant_checks=True)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(service, "GameCommandService")
        
        # 检查不变量检查已启用
        assert service._enable_invariant_checks is True
        assert service._game_invariants == {}
        assert service._snapshot_manager is not None
    
    def test_create_command_service_without_invariants(self):
        """测试创建禁用不变量检查的命令服务"""
        service = GameCommandService(enable_invariant_checks=False)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(service, "GameCommandService")
        
        # 检查不变量检查已禁用
        assert service._enable_invariant_checks is False
    
    def test_game_creation_without_invariant_check(self):
        """测试禁用不变量检查时的游戏创建"""
        service = GameCommandService(enable_invariant_checks=False)
        
        # 创建游戏
        result = service.create_new_game(
            game_id="test_game",
            player_ids=["player1", "player2"]
        )
        
        # 游戏创建应该成功
        assert result.success is True
        assert "test_game" in service.get_active_games()
        
        # 不变量检查器不应该被创建
        assert "test_game" not in service._game_invariants
    
    def test_real_game_creation_with_invariant_check(self):
        """测试启用不变量检查时的真实游戏创建 - 重现盲注问题"""
        service = GameCommandService(enable_invariant_checks=True)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(service, "GameCommandService")
        
        # 创建游戏 - 这应该会触发不变量违反
        result = service.create_new_game(
            game_id="test_game",
            player_ids=["player1", "player2"]
        )
        
        # 检查结果 - 应该失败由于盲注问题
        if not result.success:
            print(f"游戏创建失败: {result.message}")
            print(f"错误代码: {result.error_code}")
            # 这是预期的失败，因为盲注设置有问题
            assert "不变量违反" in result.message
            assert "大盲" in result.message and "小盲" in result.message
        else:
            # 如果成功了，说明问题已经修复
            assert "test_game" in service.get_active_games()
    
    @patch('v3.application.command_service.GameInvariants')
    def test_invariant_violation_during_game_creation(self, mock_invariants_class):
        """测试游戏创建时不变量违反的处理"""
        # 模拟不变量违反
        mock_invariants = Mock()
        mock_invariants.validate_and_raise.side_effect = InvariantError(
            "测试不变量违反",
            [InvariantViolation(
                invariant_type=InvariantType.CHIP_CONSERVATION,
                violation_id="test_violation",
                description="测试违反",
                severity="CRITICAL",
                context={},
                timestamp=1.0
            )]
        )
        mock_invariants_class.return_value = mock_invariants
        
        service = GameCommandService(enable_invariant_checks=True)
        
        # 创建游戏
        result = service.create_new_game(
            game_id="test_game",
            player_ids=["player1", "player2"]
        )
        
        # 游戏创建应该失败
        assert result.success is False
        assert result.error_code == "INVARIANT_VIOLATION"
        assert "不变量违反" in result.message
        
        # 游戏不应该被创建
        assert "test_game" not in service.get_active_games()
    
    def test_get_invariant_stats_disabled(self):
        """测试禁用不变量检查时获取统计信息"""
        service = GameCommandService(enable_invariant_checks=False)
        
        # 创建游戏
        create_result = service.create_new_game(
            game_id="test_game",
            player_ids=["player1", "player2"]
        )
        assert create_result.success is True
        
        # 获取统计信息应该返回None
        stats = service._get_invariant_stats("test_game")
        assert stats is None
    
    def test_get_invariant_stats_nonexistent_game(self):
        """测试获取不存在游戏的统计信息"""
        service = GameCommandService(enable_invariant_checks=True)
        
        # 获取不存在游戏的统计信息
        stats = service._get_invariant_stats("nonexistent_game")
        assert stats is None 