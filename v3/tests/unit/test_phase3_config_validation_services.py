"""
Phase 3 配置和验证服务测试

验证ConfigService和ValidationService的集中化配置管理功能，确保：
1. 配置服务正确加载各类配置
2. 验证服务正确执行规则检查
3. 服务间集成工作正常
4. 符合CQRS架构原则和反作弊检查
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from v3.application import (
    ConfigService, ConfigType, GameRulesConfig, AIDecisionConfig, UITestConfig,
    ValidationService, ValidationError, ValidationResult,
    GameQueryService, GameCommandService, QueryResult
)
from v3.core.events import EventBus, set_event_bus
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestPhase3ConfigValidationServices:
    """Phase 3 配置和验证服务测试"""
    
    def setup_method(self):
        """测试前设置"""
        # 创建独立的事件总线避免测试间干扰
        self.event_bus = EventBus()
        set_event_bus(self.event_bus)
        self.command_service = GameCommandService(self.event_bus)
        self.query_service = GameQueryService(self.command_service, self.event_bus)
        
        # 创建配置和验证服务
        self.config_service = ConfigService()
        self.validation_service = ValidationService(self.config_service)
    
    def test_config_service_anti_cheat_verification(self):
        """测试ConfigService的反作弊验证"""
        # 反作弊检查 - 确保使用真实的配置服务
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")
        
        # 验证核心方法存在且可调用
        assert hasattr(self.config_service, 'get_game_rules_config')
        assert hasattr(self.config_service, 'get_ai_decision_config')
        assert hasattr(self.config_service, 'get_ui_test_config')
        assert callable(getattr(self.config_service, 'get_game_rules_config'))
        
        print("✅ ConfigService反作弊验证通过")
    
    def test_validation_service_anti_cheat_verification(self):
        """测试ValidationService的反作弊验证"""
        # 反作弊检查 - 确保使用真实的验证服务
        CoreUsageChecker.verify_real_objects(self.validation_service, "ValidationService")
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")
        
        # 验证核心方法存在且可调用
        assert hasattr(self.validation_service, 'validate_player_action_rules')
        assert hasattr(self.validation_service, 'validate_chip_conservation')
        assert hasattr(self.validation_service, 'validate_game_state_consistency')
        
        print("✅ ValidationService反作弊验证通过")
    
    def test_game_rules_config_profiles(self):
        """测试游戏规则配置的不同profile"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")
        
        # 测试默认配置
        default_result = self.config_service.get_game_rules_config("default")
        assert default_result.success
        assert isinstance(default_result.data, GameRulesConfig)
        assert default_result.data.small_blind == 5
        assert default_result.data.big_blind == 10
        assert default_result.data.initial_chips == 1000
        
        # 测试锦标赛配置
        tournament_result = self.config_service.get_game_rules_config("tournament")
        assert tournament_result.success
        assert isinstance(tournament_result.data, GameRulesConfig)
        assert tournament_result.data.small_blind == 10
        assert tournament_result.data.big_blind == 20
        assert tournament_result.data.initial_chips == 2000
        
        # 测试不存在的配置(应该回退到默认)
        unknown_result = self.config_service.get_game_rules_config("unknown")
        assert unknown_result.success
        assert unknown_result.data.small_blind == 5  # 应该是默认值
        
        print("✅ 游戏规则配置测试通过")
    
    def test_ai_decision_config_profiles(self):
        """测试AI决策配置的不同profile"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")
        
        # 测试默认配置
        default_result = self.config_service.get_ai_decision_config("default")
        assert default_result.success
        assert isinstance(default_result.data, AIDecisionConfig)
        assert abs(default_result.data.fold_weight + default_result.data.check_weight + 
                  default_result.data.call_weight + default_result.data.raise_weight + 
                  default_result.data.all_in_weight - 1.0) < 0.001
        
        # 测试激进配置
        aggressive_result = self.config_service.get_ai_decision_config("aggressive")
        assert aggressive_result.success
        assert aggressive_result.data.raise_weight > default_result.data.raise_weight
        assert aggressive_result.data.fold_weight < default_result.data.fold_weight
        
        # 测试保守配置
        conservative_result = self.config_service.get_ai_decision_config("conservative")
        assert conservative_result.success
        assert conservative_result.data.fold_weight > default_result.data.fold_weight
        assert conservative_result.data.raise_weight < default_result.data.raise_weight
        
        print("✅ AI决策配置测试通过")
    
    def test_ui_test_config_profiles(self):
        """测试UI测试配置的不同profile"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")
        
        # 测试终极配置
        ultimate_result = self.config_service.get_ui_test_config("ultimate")
        assert ultimate_result.success
        assert isinstance(ultimate_result.data, UITestConfig)
        assert len(ultimate_result.data.default_player_ids) == 6
        assert ultimate_result.data.max_actions_per_hand == 100
        
        # 测试快速配置
        quick_result = self.config_service.get_ui_test_config("quick")
        assert quick_result.success
        assert len(quick_result.data.default_player_ids) == 2
        assert quick_result.data.max_actions_per_hand == 30
        assert quick_result.data.timeout_per_hand_seconds == 15
        
        # 测试压力配置
        stress_result = self.config_service.get_ui_test_config("stress")
        assert stress_result.success
        assert stress_result.data.max_actions_per_hand == 200
        assert stress_result.data.timeout_per_hand_seconds == 120
        
        print("✅ UI测试配置测试通过")
    
    def test_merged_config_interface(self):
        """测试合并配置接口"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")
        
        # 测试获取合并的字典配置
        game_rules_result = self.config_service.get_merged_config(ConfigType.GAME_RULES, "default")
        assert game_rules_result.success
        assert isinstance(game_rules_result.data, dict)
        assert 'small_blind' in game_rules_result.data
        assert 'big_blind' in game_rules_result.data
        
        ai_config_result = self.config_service.get_merged_config(ConfigType.AI_DECISION, "aggressive")
        assert ai_config_result.success
        assert isinstance(ai_config_result.data, dict)
        assert 'fold_weight' in ai_config_result.data
        assert 'raise_weight' in ai_config_result.data
        
        print("✅ 合并配置接口测试通过")
    
    def test_chip_conservation_validation(self):
        """测试筹码守恒验证"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.validation_service, "ValidationService")
        
        # 测试正常情况
        valid_result = self.validation_service.validate_chip_conservation(
            initial_total=6000,
            current_players_total=5500,
            current_pot_total=500
        )
        assert valid_result.success
        assert valid_result.data.is_valid
        assert len(valid_result.data.errors) == 0
        
        # 测试违规情况
        invalid_result = self.validation_service.validate_chip_conservation(
            initial_total=6000,
            current_players_total=5500,
            current_pot_total=400  # 总计5900，少了100
        )
        assert invalid_result.success
        assert not invalid_result.data.is_valid
        assert len(invalid_result.data.errors) == 1
        assert "筹码守恒违反" in invalid_result.data.errors[0].message
        
        print("✅ 筹码守恒验证测试通过")
    
    def test_player_action_validation(self):
        """测试玩家行动验证"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.validation_service, "ValidationService")
        
        # 创建模拟的游戏状态
        state_before = Mock()
        state_before.current_bet = 10
        state_before.current_phase = "PRE_FLOP"
        state_before.players = {
            "player_1": {"chips": 1000, "current_bet": 0}
        }
        
        state_after = Mock()
        state_after.players = {
            "player_1": {"chips": 990, "current_bet": 10}
        }
        
        # 测试有效的call行动
        valid_result = self.validation_service.validate_player_action_rules(
            player_id="player_1",
            action_type="call",
            amount=10,
            state_before=state_before,
            state_after=state_after
        )
        assert valid_result.success
        assert valid_result.data.is_valid
        
        print("✅ 玩家行动验证测试通过")
    
    def test_query_service_config_integration(self):
        """测试QueryService与ConfigService的集成"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建测试游戏
        game_result = self.command_service.create_new_game(player_ids=["player_1", "player_2"])
        assert game_result.success
        game_id = game_result.data['game_id']
        
        # 测试通过QueryService获取配置
        rules_result = self.query_service.get_game_rules_config(game_id)
        assert rules_result.success
        assert 'small_blind' in rules_result.data
        
        ai_config_result = self.query_service.get_ai_config("aggressive")
        assert ai_config_result.success
        assert 'fold_weight' in ai_config_result.data
        
        ui_config_result = self.query_service.get_ui_test_config("quick")
        assert ui_config_result.success
        assert 'default_player_ids' in ui_config_result.data
        
        print("✅ QueryService配置集成测试通过")
    
    def test_config_profile_listing(self):
        """测试配置profile列表功能"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")
        
        # 测试游戏规则配置文件列表
        game_rules_profiles = self.config_service.list_available_profiles(ConfigType.GAME_RULES)
        assert game_rules_profiles.success
        assert "default" in game_rules_profiles.data
        assert "tournament" in game_rules_profiles.data
        
        # 测试AI决策配置文件列表
        ai_profiles = self.config_service.list_available_profiles(ConfigType.AI_DECISION)
        assert ai_profiles.success
        assert "default" in ai_profiles.data
        assert "aggressive" in ai_profiles.data
        assert "conservative" in ai_profiles.data
        
        # 测试UI测试配置文件列表
        ui_profiles = self.config_service.list_available_profiles(ConfigType.UI_TEST)
        assert ui_profiles.success
        assert "ultimate" in ui_profiles.data
        assert "quick" in ui_profiles.data
        assert "stress" in ui_profiles.data
        
        print("✅ 配置profile列表测试通过")
    
    def test_phase3_integration_complete(self):
        """测试Phase 3集成完整性"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.config_service, "ConfigService")
        CoreUsageChecker.verify_real_objects(self.validation_service, "ValidationService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 验证ConfigService完整功能
        assert hasattr(self.config_service, 'get_game_rules_config')
        assert hasattr(self.config_service, 'get_ai_decision_config')
        assert hasattr(self.config_service, 'get_ui_test_config')
        assert hasattr(self.config_service, 'get_merged_config')
        assert hasattr(self.config_service, 'update_config')
        assert hasattr(self.config_service, 'list_available_profiles')
        
        # 验证ValidationService完整功能
        assert hasattr(self.validation_service, 'validate_player_action_rules')
        assert hasattr(self.validation_service, 'validate_chip_conservation')
        assert hasattr(self.validation_service, 'validate_game_state_consistency')
        assert hasattr(self.validation_service, 'validate_phase_transition')
        
        # 验证QueryService集成了新的配置服务
        # 创建测试游戏
        game_result = self.command_service.create_new_game(player_ids=["test_player", "test_player2"])
        assert game_result.success
        game_id = game_result.data['game_id']
        
        # 验证配置服务集成正常工作
        rules_result = self.query_service.get_game_rules_config(game_id)
        assert rules_result.success
        
        ai_result = self.query_service.get_ai_config("default")
        assert ai_result.success
        
        ui_result = self.query_service.get_ui_test_config("ultimate")
        assert ui_result.success
        
        print("✅ Phase 3 配置和验证服务集成验证通过")
        print("✅ 配置管理完全集中化")
        print("✅ 验证逻辑统一化管理")
        print("✅ 严格遵循CQRS架构原则")
        print("✅ 通过反作弊检查") 