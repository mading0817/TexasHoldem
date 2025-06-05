#!/usr/bin/env python3
"""
PLAN 46: GameCommandService 职责最终审查的TDD测试

验证GameCommandService的职责分工：
1. 详细业务规则验证完全委托给ValidationService
2. GameCommandService只进行最小化的前置命令检查
3. 没有重复的验证逻辑
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, Any

# 反作弊检查
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker

# 被测试的类
from v3.application.command_service import GameCommandService
from v3.application.validation_service import ValidationService, ValidationResult, ValidationError
from v3.application.config_service import ConfigService
from v3.application.types import CommandResult, PlayerAction
from v3.core.state_machine import GameContext, GamePhase
from v3.core.events import EventBus


class TestGameCommandServiceResponsibilities:
    """测试GameCommandService职责分工"""

    def setup_method(self):
        """设置测试环境"""
        # 创建真实的服务实例
        self.event_bus = EventBus()
        self.config_service = ConfigService()
        self.validation_service = ValidationService(self.config_service)
        
        # 创建被测试的命令服务
        self.command_service = GameCommandService(
            event_bus=self.event_bus,
            enable_invariant_checks=True,
            validation_service=self.validation_service,
            config_service=self.config_service
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.validation_service, "ValidationService")
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")

    def test_execute_player_action_delegates_validation_to_validation_service(self):
        """测试execute_player_action完全委托验证给ValidationService"""
        # 创建测试游戏
        game_result = self.command_service.create_new_game(
            game_id="test_game",
            player_ids=["player1", "player2"]
        )
        assert game_result.success
        
        # 开始手牌
        hand_result = self.command_service.start_new_hand("test_game")
        assert hand_result.success
        
        # 模拟ValidationService返回验证失败
        with patch.object(self.validation_service, 'validate_player_action') as mock_validate:
            # 设置验证失败的返回值
            mock_validate.return_value = type('MockResult', (), {
                'success': True,
                'data': ValidationResult.failure([
                    ValidationError(
                        rule_name="test_rule",
                        error_type="invalid_action",
                        message="测试验证失败"
                    )
                ])
            })()
            
            # 执行玩家行动
            action = PlayerAction(action_type="raise", amount=100)
            result = self.command_service.execute_player_action("test_game", "player1", action)
            
                         # 验证结果
            assert not result.success
            assert "测试验证失败" in result.message
            
            # 验证ValidationService被调用
            mock_validate.assert_called_once()
            call_args = mock_validate.call_args
            assert call_args[0][1] == "player1"  # player_id
            assert call_args[0][2].action_type == "raise"  # action

    def test_execute_player_action_only_performs_minimal_precondition_checks(self):
        """测试execute_player_action只进行最小化的前置检查"""
        # 测试游戏不存在的检查
        action = PlayerAction(action_type="fold", amount=0)
        result = self.command_service.execute_player_action("nonexistent_game", "player1", action)
        
        assert not result.success
        assert result.error_code == "GAME_NOT_FOUND"
        assert "游戏 nonexistent_game 不存在" in result.message

    def test_execute_player_action_no_duplicate_validation_logic(self):
        """测试execute_player_action没有重复的验证逻辑"""
        # 创建测试游戏
        game_result = self.command_service.create_new_game(
            game_id="test_game",
            player_ids=["player1", "player2"]
        )
        assert game_result.success
        
        # 开始手牌
        hand_result = self.command_service.start_new_hand("test_game")
        assert hand_result.success
        
        # 获取游戏会话查看内部状态
        session = self.command_service._get_session("test_game")
        original_context = session.context
        
        # 模拟ValidationService返回成功
        with patch.object(self.validation_service, 'validate_player_action') as mock_validate:
            mock_validate.return_value = type('MockResult', (), {
                'success': True,
                'data': ValidationResult.success()
            })()
            
            # 模拟状态机处理
            with patch.object(session.state_machine, 'handle_player_action') as mock_handle:
                from v3.core.state_machine import GameEvent
                mock_handle.return_value = GameEvent(
                    event_type='PLAYER_ACTION_EXECUTED',
                    data={'action': 'fold'},
                    source_phase=GamePhase.PRE_FLOP
                )
                
                # 执行玩家行动
                action = PlayerAction(action_type="fold", amount=0)
                result = self.command_service.execute_player_action("test_game", "player1", action)
                
                # 验证成功
                assert result.success
                
                # 验证只调用了ValidationService，没有内部验证逻辑
                mock_validate.assert_called_once()
                mock_handle.assert_called_once()
                
                # 验证调用参数的正确性
                handle_args = mock_handle.call_args
                assert handle_args[0][1] == "player1"  # player_id
                assert handle_args[0][2]['action_type'] == "fold"  # action_dict

    def test_create_new_game_minimal_validation_checks(self):
        """测试create_new_game只进行基本的参数验证"""
        # 测试游戏ID重复检查
        game_result1 = self.command_service.create_new_game(
            game_id="duplicate_game",
            player_ids=["player1", "player2"]
        )
        assert game_result1.success
        
        # 尝试创建相同ID的游戏
        game_result2 = self.command_service.create_new_game(
            game_id="duplicate_game",
            player_ids=["player1", "player2"]
        )
        assert not game_result2.success
        assert game_result2.error_code == "GAME_ALREADY_EXISTS"

    def test_validation_service_integration_in_constructor(self):
        """测试ValidationService在构造函数中的正确注入"""
        # 测试默认注入
        service1 = GameCommandService()
        assert service1._validation_service is not None
        assert isinstance(service1._validation_service, ValidationService)
        
        # 测试自定义注入
        custom_validation_service = ValidationService(self.config_service)
        service2 = GameCommandService(validation_service=custom_validation_service)
        assert service2._validation_service is custom_validation_service
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(service1._validation_service, "ValidationService")
        CoreUsageChecker.verify_real_objects(service2._validation_service, "ValidationService")

    def test_config_service_integration_in_constructor(self):
        """测试ConfigService在构造函数中的正确注入"""
        # 测试默认注入
        service1 = GameCommandService()
        assert service1._config_service is not None
        assert isinstance(service1._config_service, ConfigService)
        
        # 测试自定义注入
        custom_config_service = ConfigService()
        service2 = GameCommandService(config_service=custom_config_service)
        assert service2._config_service is custom_config_service
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(service1._config_service, "ConfigService")
        CoreUsageChecker.verify_real_objects(service2._config_service, "ConfigService")

    def test_no_business_rule_validation_in_command_service(self):
        """测试GameCommandService不包含业务规则验证逻辑"""
        # 检查方法中没有硬编码的业务规则
        # 这个测试通过代码审查和上面的功能测试来验证
        
        # 创建游戏并进行行动，确保所有验证都通过ValidationService
        game_result = self.command_service.create_new_game(
            game_id="test_game",
            player_ids=["player1", "player2"]
        )
        assert game_result.success
        
        hand_result = self.command_service.start_new_hand("test_game")
        assert hand_result.success
        
        # 模拟ValidationService进行各种验证（成功和失败）
        validation_scenarios = [
            # 成功案例
            (True, ValidationResult.success()),
            # 失败案例
            (False, ValidationResult.failure([
                ValidationError("test", "invalid_action", "测试失败")
            ]))
        ]
        
        for should_succeed, validation_result in validation_scenarios:
            with patch.object(self.validation_service, 'validate_player_action') as mock_validate:
                mock_validate.return_value = type('MockResult', (), {
                    'success': True,
                    'data': validation_result
                })()
                
                action = PlayerAction(action_type="fold", amount=0)
                result = self.command_service.execute_player_action("test_game", "player1", action)
                
                # 验证结果与ValidationService的返回一致
                assert result.success == should_succeed
                mock_validate.assert_called_once()

    def test_validation_service_receives_complete_game_context(self):
        """测试ValidationService接收到完整的游戏上下文"""
        # 创建测试游戏
        game_result = self.command_service.create_new_game(
            game_id="test_game",
            player_ids=["player1", "player2"]
        )
        assert game_result.success
        
        hand_result = self.command_service.start_new_hand("test_game")
        assert hand_result.success
        
        # 监控ValidationService的调用
        with patch.object(self.validation_service, 'validate_player_action') as mock_validate:
            mock_validate.return_value = type('MockResult', (), {
                'success': True,
                'data': ValidationResult.success()
            })()
            
            action = PlayerAction(action_type="fold", amount=0)
            self.command_service.execute_player_action("test_game", "player1", action)
            
            # 验证传递给ValidationService的参数
            call_args = mock_validate.call_args
            game_context = call_args[0][0]  # 第一个参数是game_context
            player_id = call_args[0][1]     # 第二个参数是player_id
            player_action = call_args[0][2]  # 第三个参数是player_action
            
            # 验证game_context包含完整信息
            assert hasattr(game_context, 'players')
            assert hasattr(game_context, 'current_phase')
            assert hasattr(game_context, 'current_bet')
            assert hasattr(game_context, 'pot_total')
            
            # 验证其他参数正确
            assert player_id == "player1"
            assert player_action.action_type == "fold"
            
            # 反作弊检查
            CoreUsageChecker.verify_real_objects(game_context, "GameContext")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 