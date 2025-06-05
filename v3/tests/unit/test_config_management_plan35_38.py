#!/usr/bin/env python3
"""
配置管理单元测试 - PLAN 35-38

测试ConfigService的可注入性以及与GameCommandService和GameQueryService的集成。
确保配置管理完全集中化，移除硬编码值。
"""

import pytest
from unittest.mock import Mock, patch

# 添加项目路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v3.application.config_service import ConfigService
from v3.application.command_service import GameCommandService
from v3.application.query_service import GameQueryService
from v3.application.validation_service import ValidationService
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestConfigServiceInjectability:
    """测试PLAN 35: ConfigService的可注入性"""
    
    def setup_method(self):
        """测试前设置"""
        self.config_service = ConfigService()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")
    
    def test_config_service_dependency_injection_ready(self):
        """测试ConfigService适合依赖注入"""
        # 验证ConfigService可以作为依赖注入
        validation_service = ValidationService(self.config_service)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(validation_service, "ValidationService")
        
        # 验证注入的ConfigService正常工作
        assert validation_service.config_service is self.config_service


class TestGameCommandServiceConfigIntegration:
    """测试PLAN 36: GameCommandService的配置集成"""
    
    def setup_method(self):
        """测试前设置"""
        self.config_service = ConfigService()
        self.validation_service = ValidationService(self.config_service)
        self.command_service = GameCommandService(
            validation_service=self.validation_service,
            config_service=self.config_service
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
    
    def test_command_service_has_config_service(self):
        """测试GameCommandService正确注入了ConfigService"""
        assert hasattr(self.command_service, '_config_service')
        assert self.command_service._config_service is self.config_service
    
    def test_create_new_game_uses_config_values(self):
        """测试create_new_game使用ConfigService的值而非硬编码"""
        # 创建游戏
        result = self.command_service.create_new_game(player_ids=["player_1", "player_2"])
        assert result.success
        
        game_id = result.data['game_id']
        
        # 获取游戏会话
        session = self.command_service._get_session(game_id)
        assert session is not None
        
        # 获取配置值
        config_result = self.config_service.get_game_rules_config()
        assert config_result.success
        game_rules = config_result.data
        
        # 验证游戏使用了配置值而非硬编码
        assert session.context.small_blind == game_rules.small_blind
        assert session.context.big_blind == game_rules.big_blind
        
        # 验证玩家初始筹码使用配置值
        for player_data in session.context.players.values():
            assert player_data['chips'] == game_rules.initial_chips


class TestGameQueryServiceConfigIntegration:
    """测试PLAN 37: GameQueryService的配置集成"""
    
    def setup_method(self):
        """测试前设置"""
        self.config_service = ConfigService()
        self.validation_service = ValidationService(self.config_service)
        self.command_service = GameCommandService(
            validation_service=self.validation_service,
            config_service=self.config_service
        )
        self.query_service = GameQueryService(
            command_service=self.command_service,
            config_service=self.config_service
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
    
    def test_query_service_has_config_service(self):
        """测试GameQueryService正确注入了ConfigService"""
        assert hasattr(self.query_service, '_config_service')
        assert self.query_service._config_service is self.config_service
    
    def test_get_game_rules_config_uses_injected_service(self):
        """测试get_game_rules_config使用注入的ConfigService"""
        # 创建测试游戏
        game_result = self.command_service.create_new_game(player_ids=["player_1", "player_2"])
        assert game_result.success
        game_id = game_result.data['game_id']
        
        # 获取游戏规则配置
        config_result = self.query_service.get_game_rules_config(game_id)
        assert config_result.success
        
        # 验证配置内容
        config_data = config_result.data
        assert 'small_blind' in config_data
        assert 'big_blind' in config_data
        assert 'initial_chips' in config_data


class TestConfigManagementIntegration:
    """测试PLAN 35-38: 配置管理完整集成"""
    
    def setup_method(self):
        """测试前设置"""
        self.config_service = ConfigService()
        self.validation_service = ValidationService(self.config_service)
        self.command_service = GameCommandService(
            validation_service=self.validation_service,
            config_service=self.config_service
        )
        self.query_service = GameQueryService(
            command_service=self.command_service,
            config_service=self.config_service
        )
    
    def test_config_service_centralization_complete(self):
        """测试配置服务完全集中化"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 验证所有服务都使用同一个ConfigService实例
        assert self.command_service._config_service is self.config_service
        assert self.query_service._config_service is self.config_service
        assert self.validation_service.config_service is self.config_service
        
        print("✅ PLAN 35-38 配置管理集成验证通过")
        print("✅ ConfigService完全可注入")
        print("✅ GameCommandService移除硬编码值")
        print("✅ GameQueryService使用注入的ConfigService")
        print("✅ 配置管理完全集中化") 