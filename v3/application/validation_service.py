#!/usr/bin/env python3
"""
ValidationService - 验证服务

负责集中化管理所有游戏规则验证，包括：
- 玩家行动规则验证
- 游戏状态一致性验证
- 筹码守恒验证
- 不变量检查

严格遵循CQRS模式，为Application层提供统一的验证接口。
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from .types import QueryResult
from .config_service import ConfigService, GameRulesConfig


@dataclass
class ValidationError:
    """验证错误信息"""
    rule_name: str
    error_type: str
    message: str
    severity: str = "error"  # error, warning, info
    expected_value: Any = None
    actual_value: Any = None


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    rule_checks_performed: int
    
    @classmethod
    def success(cls) -> 'ValidationResult':
        """创建成功的验证结果"""
        return cls(is_valid=True, errors=[], warnings=[], rule_checks_performed=0)
    
    @classmethod
    def failure(cls, errors: List[ValidationError]) -> 'ValidationResult':
        """创建失败的验证结果"""
        return cls(is_valid=False, errors=errors, warnings=[], rule_checks_performed=len(errors))


class ValidationService:
    """验证服务"""
    
    def __init__(self, config_service: ConfigService):
        """
        初始化验证服务
        
        Args:
            config_service: 配置服务实例
        """
        self.logger = logging.getLogger(__name__)
        self.config_service = config_service
        self._load_validation_rules()
    
    def _load_validation_rules(self):
        """加载验证规则"""
        try:
            # 获取游戏规则配置
            rules_result = self.config_service.get_game_rules_config()
            if rules_result.success:
                self.game_rules = rules_result.data
            else:
                self.logger.warning("无法加载游戏规则，使用默认规则")
                self.game_rules = GameRulesConfig()
            
            self.logger.info("验证规则加载完成")
            
        except Exception as e:
            self.logger.error(f"加载验证规则失败: {e}")
            self.game_rules = GameRulesConfig()
    
    def validate_player_action_rules(self, 
                                   player_id: str, 
                                   action_type: str, 
                                   amount: int,
                                   state_before: Any,
                                   state_after: Any) -> QueryResult[ValidationResult]:
        """
        验证玩家行动是否符合德州扑克规则
        
        Args:
            player_id: 玩家ID
            action_type: 行动类型 (fold, check, call, raise, all_in)
            amount: 行动金额
            state_before: 行动前游戏状态
            state_after: 行动后游戏状态
            
        Returns:
            查询结果，包含验证结果
        """
        try:
            errors = []
            warnings = []
            checks_performed = 0
            
            # 获取玩家状态
            player_before = state_before.players.get(player_id, {})
            player_after = state_after.players.get(player_id, {})
            
            chips_before = player_before.get('chips', 0)
            chips_after = player_after.get('chips', 0)
            bet_before = player_before.get('current_bet', 0)
            bet_after = player_after.get('current_bet', 0)
            
            # 1. 验证基本行动规则
            checks_performed += 1
            action_validation = self._validate_action_type(action_type, amount, chips_before, state_before)
            if not action_validation.is_valid:
                errors.extend(action_validation.errors)
            
            # 2. 验证筹码变化
            checks_performed += 1
            chips_validation = self._validate_chips_change(
                action_type, amount, chips_before, chips_after, bet_before, bet_after
            )
            if not chips_validation.is_valid:
                errors.extend(chips_validation.errors)
            
            # 3. 验证下注规则
            checks_performed += 1
            betting_validation = self._validate_betting_rules(
                action_type, amount, bet_before, bet_after, state_before.current_bet
            )
            if not betting_validation.is_valid:
                errors.extend(betting_validation.errors)
            
            # 4. 验证阶段规则
            checks_performed += 1
            phase_validation = self._validate_phase_rules(action_type, state_before.current_phase)
            if not phase_validation.is_valid:
                errors.extend(phase_validation.errors)
            
            result = ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                rule_checks_performed=checks_performed
            )
            
            return QueryResult.success_result(result)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"验证玩家行动规则失败: {str(e)}",
                error_code="VALIDATE_PLAYER_ACTION_FAILED"
            )
    
    def _validate_action_type(self, action_type: str, amount: int, player_chips: int, game_state: Any) -> ValidationResult:
        """验证行动类型的合法性"""
        errors = []
        
        valid_actions = ["fold", "check", "call", "raise", "all_in"]
        if action_type not in valid_actions:
            errors.append(ValidationError(
                rule_name="valid_action_type",
                error_type="invalid_action",
                message=f"无效的行动类型: {action_type}",
                expected_value=valid_actions,
                actual_value=action_type
            ))
        
        # 检查特定行动的前提条件
        if action_type == "check" and game_state.current_bet > 0:
            errors.append(ValidationError(
                rule_name="check_action_prerequisite",
                error_type="invalid_check",
                message="当前有下注时不能check",
                expected_value=0,
                actual_value=game_state.current_bet
            ))
        
        if action_type == "call" and game_state.current_bet == 0:
            errors.append(ValidationError(
                rule_name="call_action_prerequisite",
                error_type="invalid_call",
                message="没有下注时不能call",
                expected_value=">0",
                actual_value=game_state.current_bet
            ))
        
        if action_type in ["raise", "all_in"] and amount <= 0:
            errors.append(ValidationError(
                rule_name="raise_amount_positive",
                error_type="invalid_amount",
                message=f"{action_type}行动的金额必须大于0",
                expected_value=">0",
                actual_value=amount
            ))
        
        if action_type == "all_in" and amount != player_chips:
            errors.append(ValidationError(
                rule_name="all_in_amount_equals_chips",
                error_type="invalid_all_in",
                message="All-in金额必须等于玩家剩余筹码",
                expected_value=player_chips,
                actual_value=amount
            ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=[], rule_checks_performed=1)
    
    def _validate_chips_change(self, action_type: str, amount: int, 
                             chips_before: int, chips_after: int,
                             bet_before: int, bet_after: int) -> ValidationResult:
        """验证筹码变化的合理性"""
        errors = []
        
        # 计算期望的筹码变化
        expected_chips_change = 0
        expected_bet_change = 0
        
        if action_type == "fold":
            expected_chips_change = 0
            expected_bet_change = 0
        elif action_type == "check":
            expected_chips_change = 0
            expected_bet_change = 0
        elif action_type == "call":
            expected_chips_change = -amount
            expected_bet_change = amount
        elif action_type == "raise":
            expected_chips_change = -amount
            expected_bet_change = amount
        elif action_type == "all_in":
            expected_chips_change = -amount
            expected_bet_change = amount
        
        # 验证筹码变化
        actual_chips_change = chips_after - chips_before
        if actual_chips_change != expected_chips_change:
            errors.append(ValidationError(
                rule_name="chips_change_consistency",
                error_type="chips_inconsistency",
                message=f"{action_type}行动的筹码变化不正确",
                expected_value=expected_chips_change,
                actual_value=actual_chips_change
            ))
        
        # 验证下注变化
        actual_bet_change = bet_after - bet_before
        if action_type != "fold" and actual_bet_change != expected_bet_change:
            errors.append(ValidationError(
                rule_name="bet_change_consistency",
                error_type="bet_inconsistency",
                message=f"{action_type}行动的下注变化不正确",
                expected_value=expected_bet_change,
                actual_value=actual_bet_change
            ))
        
        # 验证筹码不能为负数
        if chips_after < 0:
            errors.append(ValidationError(
                rule_name="chips_non_negative",
                error_type="negative_chips",
                message="玩家筹码不能为负数",
                expected_value=">=0",
                actual_value=chips_after
            ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=[], rule_checks_performed=1)
    
    def _validate_betting_rules(self, action_type: str, amount: int,
                              bet_before: int, bet_after: int, current_bet: int) -> ValidationResult:
        """验证下注规则"""
        errors = []
        
        if action_type == "raise":
            # 加注必须至少是big blind的倍数
            if amount % self.game_rules.big_blind != 0:
                errors.append(ValidationError(
                    rule_name="raise_big_blind_multiple",
                    error_type="invalid_raise_amount",
                    message=f"加注金额必须是大盲注({self.game_rules.big_blind})的倍数",
                    expected_value=f"n * {self.game_rules.big_blind}",
                    actual_value=amount
                ))
            
            # 加注后的总下注必须至少是当前下注的两倍（最小加注规则）
            min_raise_amount = current_bet * self.game_rules.min_raise_multiplier
            if bet_after < min_raise_amount:
                errors.append(ValidationError(
                    rule_name="minimum_raise_rule",
                    error_type="insufficient_raise",
                    message=f"加注后的总下注必须至少为当前下注的{self.game_rules.min_raise_multiplier}倍",
                    expected_value=min_raise_amount,
                    actual_value=bet_after
                ))
        
        elif action_type == "call":
            # Call的金额应该等于当前下注减去已下注的金额
            expected_call_amount = max(0, current_bet - bet_before)
            if amount != expected_call_amount:
                errors.append(ValidationError(
                    rule_name="call_amount_correct",
                    error_type="incorrect_call_amount",
                    message="Call金额不正确",
                    expected_value=expected_call_amount,
                    actual_value=amount
                ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=[], rule_checks_performed=1)
    
    def _validate_phase_rules(self, action_type: str, current_phase: str) -> ValidationResult:
        """验证阶段规则"""
        errors = []
        
        # 检查当前阶段是否允许玩家行动
        if current_phase not in self.game_rules.betting_phases:
            errors.append(ValidationError(
                rule_name="phase_allows_betting",
                error_type="invalid_phase_action",
                message=f"当前阶段({current_phase})不允许玩家行动",
                expected_value=self.game_rules.betting_phases,
                actual_value=current_phase
            ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=[], rule_checks_performed=1)
    
    def validate_chip_conservation(self, 
                                 initial_total: int,
                                 current_players_total: int,
                                 current_pot_total: int) -> QueryResult[ValidationResult]:
        """
        验证筹码守恒
        
        Args:
            initial_total: 初始总筹码
            current_players_total: 当前玩家筹码总和
            current_pot_total: 当前底池筹码总和
            
        Returns:
            查询结果，包含验证结果
        """
        try:
            errors = []
            current_total = current_players_total + current_pot_total
            
            if current_total != initial_total:
                errors.append(ValidationError(
                    rule_name="chip_conservation",
                    error_type="chip_conservation_violation",
                    message="筹码守恒违反",
                    expected_value=initial_total,
                    actual_value=current_total
                ))
            
            result = ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=[],
                rule_checks_performed=1
            )
            
            return QueryResult.success_result(result)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"验证筹码守恒失败: {str(e)}",
                error_code="VALIDATE_CHIP_CONSERVATION_FAILED"
            )
    
    def validate_game_state_consistency(self, game_state: Any) -> QueryResult[ValidationResult]:
        """
        验证游戏状态一致性
        
        Args:
            game_state: 游戏状态快照
            
        Returns:
            查询结果，包含验证结果
        """
        try:
            errors = []
            warnings = []
            checks_performed = 0
            
            # 1. 验证玩家数量
            checks_performed += 1
            player_count = len(game_state.players)
            if player_count < self.game_rules.min_players:
                errors.append(ValidationError(
                    rule_name="minimum_players",
                    error_type="insufficient_players",
                    message=f"玩家数量少于最小要求",
                    expected_value=f">={self.game_rules.min_players}",
                    actual_value=player_count
                ))
            elif player_count > self.game_rules.max_players:
                errors.append(ValidationError(
                    rule_name="maximum_players",
                    error_type="too_many_players",
                    message=f"玩家数量超过最大限制",
                    expected_value=f"<={self.game_rules.max_players}",
                    actual_value=player_count
                ))
            
            # 2. 验证活跃玩家逻辑
            checks_performed += 1
            active_players = [pid for pid, pdata in game_state.players.items() 
                            if pdata.get('active', False)]
            
            if len(active_players) > 1 and not game_state.active_player_id:
                warnings.append(ValidationError(
                    rule_name="active_player_designation",
                    error_type="missing_active_player",
                    message="有多个活跃玩家但未指定当前行动玩家",
                    severity="warning",
                    expected_value="not None",
                    actual_value=None
                ))
            
            # 3. 验证底池金额合理性
            checks_performed += 1
            if game_state.pot_total < 0:
                errors.append(ValidationError(
                    rule_name="pot_non_negative",
                    error_type="negative_pot",
                    message="底池金额不能为负数",
                    expected_value=">=0",
                    actual_value=game_state.pot_total
                ))
            
            result = ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                rule_checks_performed=checks_performed
            )
            
            return QueryResult.success_result(result)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"验证游戏状态一致性失败: {str(e)}",
                error_code="VALIDATE_GAME_STATE_FAILED"
            )
    
    def validate_phase_transition(self, 
                                from_phase: str, 
                                to_phase: str,
                                game_state: Any) -> QueryResult[ValidationResult]:
        """
        验证阶段转换的合法性
        
        Args:
            from_phase: 源阶段
            to_phase: 目标阶段
            game_state: 当前游戏状态
            
        Returns:
            查询结果，包含验证结果
        """
        try:
            errors = []
            
            # 定义合法的阶段转换
            valid_transitions = {
                "INIT": ["PRE_FLOP"],
                "PRE_FLOP": ["FLOP", "FINISHED"],
                "FLOP": ["TURN", "FINISHED"],
                "TURN": ["RIVER", "FINISHED"],
                "RIVER": ["SHOWDOWN", "FINISHED"],
                "SHOWDOWN": ["FINISHED"],
                "FINISHED": ["INIT"]  # 新手牌开始
            }
            
            if from_phase not in valid_transitions:
                errors.append(ValidationError(
                    rule_name="valid_source_phase",
                    error_type="invalid_phase",
                    message=f"无效的源阶段: {from_phase}",
                    expected_value=list(valid_transitions.keys()),
                    actual_value=from_phase
                ))
            elif to_phase not in valid_transitions[from_phase]:
                errors.append(ValidationError(
                    rule_name="valid_phase_transition",
                    error_type="invalid_transition",
                    message=f"不能从{from_phase}转换到{to_phase}",
                    expected_value=valid_transitions[from_phase],
                    actual_value=to_phase
                ))
            
            result = ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=[],
                rule_checks_performed=1
            )
            
            return QueryResult.success_result(result)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"验证阶段转换失败: {str(e)}",
                error_code="VALIDATE_PHASE_TRANSITION_FAILED"
            ) 