#!/usr/bin/env python3
"""
ValidationService 单元测试 - PLAN 31-33

测试ValidationService的增强功能以及与GameCommandService的集成。
确保验证逻辑正确集中化，以及CQRS模式的正确实施。
"""

import pytest
from unittest.mock import Mock, patch
from dataclasses import dataclass

# 添加项目路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v3.application.validation_service import ValidationService, ValidationResult, ValidationError
from v3.application.config_service import ConfigService
from v3.application.types import PlayerAction, QueryResult
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


@dataclass
class MockGameContext:
    """模拟游戏上下文"""
    game_id: str = "test_game"
    current_phase: str = "PRE_FLOP"
    current_bet: int = 100
    active_player_id: str = "player_1"
    players: dict = None
    
    def __post_init__(self):
        if self.players is None:
            self.players = {
                "player_1": {
                    "chips": 1000,
                    "current_bet": 0,
                    "active": True,
                    "status": "active"
                },
                "player_2": {
                    "chips": 800,
                    "current_bet": 100,
                    "active": True,
                    "status": "active"
                }
            }


class TestValidationServicePlan31:
    """测试PLAN 31: ValidationService功能增强"""
    
    def setup_method(self):
        """测试前设置"""
        self.config_service = ConfigService()
        self.validation_service = ValidationService(self.config_service)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.validation_service, "ValidationService")
    
    def test_validate_player_action_method_exists(self):
        """测试validate_player_action方法存在且接口正确"""
        # 准备测试数据
        game_context = MockGameContext()
        player_action = PlayerAction(action_type="call", amount=100)
        
        # 调用方法
        result = self.validation_service.validate_player_action(
            game_context, "player_1", player_action
        )
        
        # 验证返回类型
        assert isinstance(result, QueryResult)
        assert hasattr(result, 'success')
        assert hasattr(result, 'data')
        
        if result.success:
            validation_result = result.data
            assert isinstance(validation_result, ValidationResult)
            assert hasattr(validation_result, 'is_valid')
            assert hasattr(validation_result, 'errors')
            assert hasattr(validation_result, 'warnings')
            assert hasattr(validation_result, 'rule_checks_performed')
    
    def test_validate_valid_call_action(self):
        """测试有效的跟注行动验证"""
        game_context = MockGameContext()
        player_action = PlayerAction(action_type="call", amount=100)
        
        result = self.validation_service.validate_player_action(
            game_context, "player_1", player_action
        )
        
        assert result.success
        validation_result = result.data
        assert validation_result.is_valid
        assert len(validation_result.errors) == 0
        assert validation_result.rule_checks_performed > 0
    
    def test_validate_invalid_player_not_exists(self):
        """测试不存在玩家的验证"""
        game_context = MockGameContext()
        player_action = PlayerAction(action_type="call", amount=100)
        
        result = self.validation_service.validate_player_action(
            game_context, "non_existent_player", player_action
        )
        
        assert result.success  # 服务调用成功
        validation_result = result.data
        assert not validation_result.is_valid  # 但验证失败
        assert len(validation_result.errors) > 0
        
        # 检查错误详情
        error = validation_result.errors[0]
        assert error.rule_name == "player_exists"
        assert error.error_type == "player_not_found"
    
    def test_validate_inactive_player(self):
        """测试非活跃玩家验证"""
        game_context = MockGameContext()
        game_context.players["player_1"]["active"] = False
        player_action = PlayerAction(action_type="call", amount=100)
        
        result = self.validation_service.validate_player_action(
            game_context, "player_1", player_action
        )
        
        assert result.success
        validation_result = result.data
        assert not validation_result.is_valid
        
        # 查找特定错误
        inactive_error = next(
            (e for e in validation_result.errors if e.rule_name == "player_active"), 
            None
        )
        assert inactive_error is not None
        assert inactive_error.error_type == "inactive_player"
    
    def test_validate_insufficient_chips(self):
        """测试筹码不足验证"""
        game_context = MockGameContext()
        player_action = PlayerAction(action_type="raise", amount=2000)  # 超过玩家筹码
        
        result = self.validation_service.validate_player_action(
            game_context, "player_1", player_action
        )
        
        assert result.success
        validation_result = result.data
        assert not validation_result.is_valid
        
        # 查找筹码不足错误
        chips_error = next(
            (e for e in validation_result.errors if "insufficient_chips" in e.error_type),
            None
        )
        assert chips_error is not None
    
    def test_validate_wrong_turn(self):
        """测试轮次错误验证"""
        game_context = MockGameContext()
        game_context.active_player_id = "player_2"  # 不是player_1的回合
        player_action = PlayerAction(action_type="call", amount=100)
        
        result = self.validation_service.validate_player_action(
            game_context, "player_1", player_action
        )
        
        assert result.success
        validation_result = result.data
        assert not validation_result.is_valid
        
        # 查找轮次错误
        turn_error = next(
            (e for e in validation_result.errors if e.rule_name == "player_turn"),
            None
        )
        assert turn_error is not None
        assert turn_error.error_type == "not_player_turn"
    
    def test_validate_minimum_raise_rule(self):
        """测试最小加注规则验证"""
        game_context = MockGameContext()
        game_context.current_bet = 100
        # 加注金额太小（应该至少是current_bet + big_blind = 100 + 100 = 200）
        player_action = PlayerAction(action_type="raise", amount=50)
        
        result = self.validation_service.validate_player_action(
            game_context, "player_1", player_action
        )
        
        assert result.success
        validation_result = result.data
        assert not validation_result.is_valid
        
        # 查找最小加注错误
        raise_error = next(
            (e for e in validation_result.errors if "minimum_raise_rule" in e.rule_name),
            None
        )
        assert raise_error is not None


class TestGameCommandServicePlan32:
    """测试PLAN 32: GameCommandService集成ValidationService"""
    
    def setup_method(self):
        """测试前设置"""
        from v3.core.events import EventBus, set_event_bus
        from v3.application.command_service import GameCommandService
        from v3.application.validation_service import ValidationService
        from v3.application.config_service import ConfigService
        
        # 设置事件总线
        self.event_bus = EventBus()
        set_event_bus(self.event_bus)
        
        # 创建服务实例（带依赖注入）
        self.config_service = ConfigService()
        self.validation_service = ValidationService(self.config_service)
        self.command_service = GameCommandService(
            event_bus=self.event_bus,
            validation_service=self.validation_service,
            config_service=self.config_service
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.validation_service, "ValidationService")
    
    def test_command_service_has_validation_service(self):
        """测试GameCommandService正确注入了ValidationService"""
        assert hasattr(self.command_service, '_validation_service')
        assert isinstance(self.command_service._validation_service, ValidationService)
        assert hasattr(self.command_service, '_config_service')
        assert isinstance(self.command_service._config_service, ConfigService)
    
    def test_execute_player_action_uses_validation_service(self):
        """测试execute_player_action使用ValidationService进行验证"""
        # 创建游戏
        create_result = self.command_service.create_new_game("test_game", ["player_1", "player_2"])
        assert create_result.success
        
        # 开始新手牌
        start_result = self.command_service.start_new_hand("test_game")
        assert start_result.success
        
        # 准备一个有效的行动
        player_action = PlayerAction(action_type="call", amount=0)  # 跟注0，相当于check
        
        # 使用mock来验证ValidationService被调用
        with patch.object(self.command_service._validation_service, 'validate_player_action') as mock_validate:
            # 设置mock返回成功的验证结果
            mock_validate.return_value = QueryResult.success_result(
                ValidationResult(is_valid=True, errors=[], warnings=[], rule_checks_performed=1)
            )
            
            # 执行玩家行动
            result = self.command_service.execute_player_action("test_game", "player_1", player_action)
            
            # 验证ValidationService被调用
            mock_validate.assert_called_once()
            call_args = mock_validate.call_args[0]
            assert len(call_args) == 3  # game_context, player_id, player_action
            assert call_args[1] == "player_1"  # player_id
            assert call_args[2] == player_action  # player_action
    
    def test_execute_player_action_rejects_invalid_action(self):
        """测试execute_player_action正确拒绝无效行动"""
        # 创建游戏
        create_result = self.command_service.create_new_game("test_game", ["player_1", "player_2"])
        assert create_result.success
        
        # 开始新手牌
        start_result = self.command_service.start_new_hand("test_game")
        assert start_result.success
        
        # 准备一个无效的行动（不存在的玩家）
        player_action = PlayerAction(action_type="call", amount=100)
        
        # 执行行动（应该失败）
        result = self.command_service.execute_player_action("test_game", "non_existent_player", player_action)
        
        # 验证失败
        assert not result.success
        assert "validation" in result.error_code.lower() or "player_not_found" in result.error_code.lower()


class TestQueryServicePlan33:
    """测试PLAN 33: 从GameQueryService移除验证逻辑"""
    
    def setup_method(self):
        """测试前设置"""
        from v3.core.events import EventBus, set_event_bus
        from v3.application.command_service import GameCommandService
        from v3.application.query_service import GameQueryService
        
        # 设置事件总线
        self.event_bus = EventBus()
        set_event_bus(self.event_bus)
        
        # 创建服务实例
        self.command_service = GameCommandService(event_bus=self.event_bus)
        self.query_service = GameQueryService(self.command_service, self.event_bus)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
    
    def test_validate_player_action_rules_method_removed(self):
        """测试validate_player_action_rules方法已被移除"""
        # 验证方法不存在
        assert not hasattr(self.query_service, 'validate_player_action_rules')
    
    def test_query_service_focuses_on_queries_only(self):
        """测试GameQueryService只包含查询相关方法"""
        # 获取所有公共方法
        public_methods = [method for method in dir(self.query_service) 
                         if not method.startswith('_') and callable(getattr(self.query_service, method))]
        
        # 验证没有验证相关的方法
        validation_methods = [method for method in public_methods if 'validate' in method.lower()]
        assert len(validation_methods) == 0, f"发现验证相关方法: {validation_methods}"
        
        # 确认包含预期的查询方法
        expected_query_methods = ['get_game_state', 'get_available_actions', 'make_ai_decision']
        for method in expected_query_methods:
            assert method in public_methods, f"缺少查询方法: {method}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 