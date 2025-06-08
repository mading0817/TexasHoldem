#!/usr/bin/env python3
"""
ConfigService - 配置管理服务

负责集中化管理所有游戏配置，包括：
- 游戏规则配置
- 测试环境配置  
- AI决策配置
- 性能和调试配置

严格遵循CQRS模式，为Application层提供统一的配置管理接口。
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from .types import QueryResult


class ConfigType(Enum):
    """配置类型枚举"""
    GAME_RULES = "game_rules"
    AI_DECISION = "ai_decision"
    UI_TEST = "ui_test"
    PERFORMANCE = "performance"
    LOGGING = "logging"


@dataclass
class GameRulesConfig:
    """游戏规则配置"""
    small_blind: int = 5
    big_blind: int = 10
    initial_chips: int = 1000
    max_players: int = 10
    min_players: int = 2
    betting_phases: List[str] = field(default_factory=lambda: ["PRE_FLOP", "FLOP", "TURN", "RIVER"])
    non_betting_phases: List[str] = field(default_factory=lambda: ["INIT", "SHOWDOWN", "FINISHED"])
    max_raise_multiplier: int = 3  # 最大加注倍数
    min_raise_multiplier: float = 1.0  # 最小加注倍数


@dataclass  
class AIDecisionConfig:
    """AI决策配置"""
    fold_weight: float = 0.15
    check_weight: float = 0.35
    call_weight: float = 0.35
    raise_weight: float = 0.125
    all_in_weight: float = 0.025
    min_bet_ratio: float = 0.3
    max_bet_ratio: float = 0.7
    
    def __post_init__(self):
        """验证权重总和"""
        total_weight = (self.fold_weight + self.check_weight + self.call_weight + 
                       self.raise_weight + self.all_in_weight)
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"AI决策权重总和必须为1.0，当前为: {total_weight}")


@dataclass
class UITestConfig:
    """UI测试配置"""
    default_player_ids: List[str] = field(default_factory=lambda: ["player_0", "player_1", "player_2", "player_3", "player_4", "player_5"])
    initial_chips_per_player: int = 1000
    max_actions_per_hand: int = 50
    max_consecutive_same_states: int = 3
    max_force_finish_attempts: int = 10
    log_level: str = 'DEBUG'
    enable_detailed_logging: bool = True
    enable_chip_conservation_check: bool = True
    enable_invariant_violation_check: bool = True
    enable_performance_monitoring: bool = True
    timeout_per_hand_seconds: int = 30


@dataclass
class PerformanceConfig:
    """性能配置"""
    target_hands_per_second: float = 5.0
    max_memory_usage_mb: int = 500
    enable_profiling: bool = False
    profile_output_dir: str = "test-reports/profiling"
    benchmark_sample_size: int = 10


@dataclass
class LoggingConfig:
    """日志配置"""
    log_level: str = 'INFO'
    enable_file_logging: bool = True
    log_file_path: str = "v3/tests/test_logs/config_service.log"
    enable_console_logging: bool = True
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    max_log_file_size_mb: int = 10
    backup_count: int = 5


class ConfigService:
    """配置管理服务"""
    
    def __init__(self):
        """初始化配置服务"""
        self.logger = logging.getLogger(__name__)
        self._configs = {}
        self._load_default_configs()
    
    def _load_default_configs(self):
        """加载默认配置"""
        try:
            # 游戏规则配置
            self._configs[ConfigType.GAME_RULES] = {
                'default': GameRulesConfig(),
                'tournament': GameRulesConfig(
                    small_blind=10,
                    big_blind=20,
                    initial_chips=2000
                )
            }
            
            # AI决策配置
            self._configs[ConfigType.AI_DECISION] = {
                'default': AIDecisionConfig(),
                'aggressive': AIDecisionConfig(
                    fold_weight=0.1,
                    check_weight=0.2,
                    call_weight=0.3,
                    raise_weight=0.3,
                    all_in_weight=0.1
                ),
                'conservative': AIDecisionConfig(
                    fold_weight=0.3,
                    check_weight=0.4,
                    call_weight=0.25,
                    raise_weight=0.05,
                    all_in_weight=0.0
                )
            }
            
            # UI测试配置
            self._configs[ConfigType.UI_TEST] = {
                'ultimate': UITestConfig(
                    # PLAN 47要求：模拟6个玩家对战，每人筹码1000，小盲5，大盲10
                    default_player_ids=["player_0", "player_1", "player_2", "player_3", "player_4", "player_5"],
                    initial_chips_per_player=1000,
                    max_actions_per_hand=100,
                    enable_detailed_logging=True,
                    timeout_per_hand_seconds=60
                ),
                'quick': UITestConfig(
                    default_player_ids=["player_0", "player_1"],
                    max_actions_per_hand=30,
                    enable_detailed_logging=False,
                    timeout_per_hand_seconds=15
                ),
                'stress': UITestConfig(
                    max_actions_per_hand=200,
                    enable_performance_monitoring=True,
                    timeout_per_hand_seconds=120
                )
            }
            
            # 性能配置
            self._configs[ConfigType.PERFORMANCE] = {
                'default': PerformanceConfig(),
                'high_performance': PerformanceConfig(
                    target_hands_per_second=20.0,
                    enable_profiling=True
                )
            }
            
            # 日志配置
            self._configs[ConfigType.LOGGING] = {
                'default': LoggingConfig(),
                'debug': LoggingConfig(
                    log_level='DEBUG',
                    enable_file_logging=True
                ),
                'production': LoggingConfig(
                    log_level='WARNING',
                    enable_console_logging=False
                )
            }
            
            self.logger.info("默认配置加载完成")
            
        except Exception as e:
            self.logger.error(f"加载默认配置失败: {e}")
            raise
    
    def get_game_rules_config(self, profile: str = "default") -> QueryResult[GameRulesConfig]:
        """
        获取游戏规则配置
        
        Args:
            profile: 配置配置文件名
            
        Returns:
            查询结果，包含游戏规则配置
        """
        try:
            config_profiles = self._configs.get(ConfigType.GAME_RULES, {})
            if profile not in config_profiles:
                self.logger.warning(f"未找到游戏规则配置 '{profile}'，使用默认配置")
                profile = "default"
            
            config = config_profiles.get(profile, GameRulesConfig())
            return QueryResult.success_result(config)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取游戏规则配置失败: {str(e)}",
                error_code="GET_GAME_RULES_CONFIG_FAILED"
            )
    
    def get_ai_decision_config(self, profile: str = "default") -> QueryResult[AIDecisionConfig]:
        """
        获取AI决策配置
        
        Args:
            profile: 配置配置文件名 (default, aggressive, conservative)
            
        Returns:
            查询结果，包含AI决策配置
        """
        try:
            config_profiles = self._configs.get(ConfigType.AI_DECISION, {})
            if profile not in config_profiles:
                self.logger.warning(f"未找到AI决策配置 '{profile}'，使用默认配置")
                profile = "default"
            
            config = config_profiles.get(profile, AIDecisionConfig())
            return QueryResult.success_result(config)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取AI决策配置失败: {str(e)}",
                error_code="GET_AI_DECISION_CONFIG_FAILED"
            )
    
    def get_ui_test_config(self, profile: str = "ultimate") -> QueryResult[UITestConfig]:
        """
        获取UI测试配置
        
        Args:
            profile: 配置配置文件名 (ultimate, quick, stress)
            
        Returns:
            查询结果，包含UI测试配置
        """
        try:
            config_profiles = self._configs.get(ConfigType.UI_TEST, {})
            if profile not in config_profiles:
                self.logger.warning(f"未找到UI测试配置 '{profile}'，使用默认配置")
                profile = "ultimate"
            
            config = config_profiles.get(profile, UITestConfig())
            return QueryResult.success_result(config)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取UI测试配置失败: {str(e)}",
                error_code="GET_UI_TEST_CONFIG_FAILED"
            )
    
    def get_performance_config(self, profile: str = "default") -> QueryResult[PerformanceConfig]:
        """
        获取性能配置
        
        Args:
            profile: 配置配置文件名
            
        Returns:
            查询结果，包含性能配置
        """
        try:
            config_profiles = self._configs.get(ConfigType.PERFORMANCE, {})
            if profile not in config_profiles:
                self.logger.warning(f"未找到性能配置 '{profile}'，使用默认配置")
                profile = "default"
            
            config = config_profiles.get(profile, PerformanceConfig())
            return QueryResult.success_result(config)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取性能配置失败: {str(e)}",
                error_code="GET_PERFORMANCE_CONFIG_FAILED"
            )
    
    def get_logging_config(self, profile: str = "default") -> QueryResult[LoggingConfig]:
        """
        获取日志配置
        
        Args:
            profile: 配置配置文件名
            
        Returns:
            查询结果，包含日志配置
        """
        try:
            config_profiles = self._configs.get(ConfigType.LOGGING, {})
            if profile not in config_profiles:
                self.logger.warning(f"未找到日志配置 '{profile}'，使用默认配置")
                profile = "default"
            
            config = config_profiles.get(profile, LoggingConfig())
            return QueryResult.success_result(config)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取日志配置失败: {str(e)}",
                error_code="GET_LOGGING_CONFIG_FAILED"
            )
    
    def get_merged_config(self, config_type: ConfigType, profile: str = "default") -> QueryResult[Dict[str, Any]]:
        """
        获取合并后的配置字典
        
        Args:
            config_type: 配置类型
            profile: 配置配置文件名
            
        Returns:
            查询结果，包含配置字典
        """
        try:
            if config_type == ConfigType.GAME_RULES:
                result = self.get_game_rules_config(profile)
                if result.success:
                    return QueryResult.success_result(result.data.__dict__)
            elif config_type == ConfigType.AI_DECISION:
                result = self.get_ai_decision_config(profile)
                if result.success:
                    return QueryResult.success_result(result.data.__dict__)
            elif config_type == ConfigType.UI_TEST:
                result = self.get_ui_test_config(profile)
                if result.success:
                    return QueryResult.success_result(result.data.__dict__)
            elif config_type == ConfigType.PERFORMANCE:
                result = self.get_performance_config(profile)
                if result.success:
                    return QueryResult.success_result(result.data.__dict__)
            elif config_type == ConfigType.LOGGING:
                result = self.get_logging_config(profile)
                if result.success:
                    return QueryResult.success_result(result.data.__dict__)
            
            return QueryResult.failure_result(
                f"不支持的配置类型: {config_type}",
                error_code="UNSUPPORTED_CONFIG_TYPE"
            )
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取合并配置失败: {str(e)}",
                error_code="GET_MERGED_CONFIG_FAILED"
            )
    
    def update_config(self, config_type: ConfigType, profile: str, updates: Dict[str, Any]) -> QueryResult[bool]:
        """
        更新配置
        
        Args:
            config_type: 配置类型
            profile: 配置配置文件名  
            updates: 更新的配置项
            
        Returns:
            查询结果，包含更新是否成功
        """
        try:
            if config_type not in self._configs:
                return QueryResult.failure_result(
                    f"配置类型 {config_type} 不存在",
                    error_code="CONFIG_TYPE_NOT_FOUND"
                )
            
            config_profiles = self._configs[config_type]
            if profile not in config_profiles:
                return QueryResult.failure_result(
                    f"配置配置文件 {profile} 不存在",
                    error_code="CONFIG_PROFILE_NOT_FOUND"
                )
            
            # 更新配置
            current_config = config_profiles[profile]
            for key, value in updates.items():
                if hasattr(current_config, key):
                    setattr(current_config, key, value)
                else:
                    self.logger.warning(f"配置项 {key} 不存在于 {config_type}.{profile} 中")
            
            self.logger.info(f"配置 {config_type}.{profile} 更新成功")
            return QueryResult.success_result(True)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"更新配置失败: {str(e)}",
                error_code="UPDATE_CONFIG_FAILED"
            )
    
    def list_available_profiles(self, config_type: ConfigType) -> QueryResult[List[str]]:
        """
        列出可用的配置配置文件
        
        Args:
            config_type: 配置类型
            
        Returns:
            查询结果，包含可用配置文件列表
        """
        try:
            if config_type not in self._configs:
                return QueryResult.failure_result(
                    f"配置类型 {config_type} 不存在",
                    error_code="CONFIG_TYPE_NOT_FOUND"
                )
            
            profiles = list(self._configs[config_type].keys())
            return QueryResult.success_result(profiles)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"列出可用配置失败: {str(e)}",
                error_code="LIST_AVAILABLE_PROFILES_FAILED"
            )

# 全局单例
_config_service_instance: Optional[ConfigService] = None

def get_config_service() -> ConfigService:
    """
    获取配置服务的全局单例
    
    Returns:
        ConfigService: 配置服务实例
    """
    global _config_service_instance
    if _config_service_instance is None:
        _config_service_instance = ConfigService()
    return _config_service_instance 