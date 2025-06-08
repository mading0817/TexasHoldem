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
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING
from dataclasses import dataclass

from .types import QueryResult
from .config_service import ConfigService, GameRulesConfig, get_config_service

if TYPE_CHECKING:
    from .types import PlayerAction


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
    
    def validate_player_action(self, 
                             game_context: Any,
                             player_id: str, 
                             player_action: 'PlayerAction') -> QueryResult[ValidationResult]:
        """
        验证玩家行动是否符合德州扑克规则（PLAN 31：重命名为更清晰的名称）
        
        Args:
            game_context: 游戏上下文（由命令服务提供）
            player_id: 玩家ID
            player_action: 玩家行动详细信息
            
        Returns:
            查询结果，包含验证结果
        """
        try:
            errors = []
            warnings = []
            checks_performed = 0
            
            # From PlayerAction获取行动信息
            action_type = player_action.action_type.lower() # 统一转为小写
            amount = player_action.amount or 0
            
            # (Phase 2) 从ChipLedger和context获取真实的筹码信息
            player_data = game_context.players.get(player_id, {})
            player_balance = game_context.chip_ledger.get_balance(player_id)
            player_current_bet = game_context.current_hand_bets.get(player_id, 0)
            
            # 1. 验证玩家是否有资格行动
            checks_performed += 1
            eligibility_validation = self._validate_player_action_eligibility(
                player_id, player_data, game_context
            )
            if not eligibility_validation.is_valid:
                errors.extend(eligibility_validation.errors)
            
            # 2. 验证基本行动规则
            checks_performed += 1
            action_validation = self._validate_action_type(action_type, amount, player_balance, game_context)
            if not action_validation.is_valid:
                errors.extend(action_validation.errors)
            
            # 3. 验证下注规则（使用从ConfigService获取的规则）
            checks_performed += 1
            betting_validation = self._validate_betting_rules_enhanced(
                action_type, amount, player_current_bet, game_context.current_bet, player_balance
            )
            if not betting_validation.is_valid:
                errors.extend(betting_validation.errors)
            
            # 4. 验证阶段规则
            checks_performed += 1
            phase_validation = self._validate_phase_rules(action_type, game_context.current_phase)
            if not phase_validation.is_valid:
                errors.extend(phase_validation.errors)
            
            # 5. 验证轮次规则
            checks_performed += 1
            turn_validation = self._validate_turn_rules(player_id, game_context)
            if not turn_validation.is_valid:
                errors.extend(turn_validation.errors)
            
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
        player_bet = game_state.current_hand_bets.get(player_id, 0)
        if action_type == "check" and game_state.current_bet > player_bet:
            errors.append(ValidationError(
                rule_name="check_action_prerequisite",
                error_type="invalid_check",
                message="当需要跟注时不能check",
                expected_value=player_bet,
                actual_value=game_state.current_bet
            ))
        
        if action_type == "call" and game_state.current_bet == player_bet:
            errors.append(ValidationError(
                rule_name="call_action_prerequisite",
                error_type="invalid_call",
                message="没有需要跟注时不能call",
                expected_value=f"<{game_state.current_bet}",
                actual_value=player_bet
            ))
        
        if action_type in ["raise", "all_in"] and amount is not None and amount <= 0:
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
    
    def _validate_phase_rules(self, action_type: str, current_phase) -> ValidationResult:
        """验证阶段规则"""
        errors = []
        
        # 将GamePhase枚举转换为字符串进行比较
        if hasattr(current_phase, 'name'):
            phase_name = current_phase.name
        else:
            phase_name = str(current_phase)
        
        # 检查当前阶段是否允许玩家行动
        if phase_name not in self.game_rules.betting_phases:
            errors.append(ValidationError(
                rule_name="phase_allows_betting",
                error_type="invalid_phase_action",
                message=f"当前阶段({phase_name})不允许玩家行动",
                expected_value=self.game_rules.betting_phases,
                actual_value=phase_name
            ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=[], rule_checks_performed=1)
    
    def _validate_player_action_eligibility(self, player_id: str, player_data: Dict[str, Any], 
                                           game_context: Any) -> ValidationResult:
        """验证玩家是否有资格行动"""
        errors = []
        
        # 验证玩家是否在游戏中
        if not player_data:
            errors.append(ValidationError(
                rule_name="player_exists",
                error_type="player_not_found",
                message=f"玩家 {player_id} 不在游戏中",
                expected_value="exists",
                actual_value="not_found"
            ))
            return ValidationResult(is_valid=False, errors=errors, warnings=[], rule_checks_performed=1)
        
        # 验证玩家是否处于活跃状态
        if not player_data.get('active', False):
            errors.append(ValidationError(
                rule_name="player_active",
                error_type="inactive_player",
                message=f"玩家 {player_id} 不处于活跃状态",
                expected_value=True,
                actual_value=player_data.get('active', False)
            ))
        
        # 验证玩家是否有筹码（除了fold行动）
        player_chips = player_data.get('chips', 0)
        if player_chips <= 0:
            errors.append(ValidationError(
                rule_name="player_has_chips",
                error_type="no_chips",
                message=f"玩家 {player_id} 没有筹码",
                expected_value=">0",
                actual_value=player_chips
            ))
        
        # 验证玩家状态（不是all_in状态，除了特殊情况）
        player_status = player_data.get('status', 'active')
        if player_status == 'all_in':
            errors.append(ValidationError(
                rule_name="player_not_all_in",
                error_type="already_all_in",
                message=f"玩家 {player_id} 已经All-In，不能再行动",
                expected_value="active",
                actual_value=player_status
            ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=[], rule_checks_performed=1)
    
    def _validate_turn_rules(self, player_id: str, game_context: Any) -> ValidationResult:
        """验证轮次规则"""
        errors = []
        
        # 验证是否轮到该玩家
        if hasattr(game_context, 'active_player_id') and game_context.active_player_id:
            if game_context.active_player_id != player_id:
                errors.append(ValidationError(
                    rule_name="player_turn",
                    error_type="not_player_turn",
                    message=f"当前轮到玩家 {game_context.active_player_id}，不是 {player_id}",
                    expected_value=game_context.active_player_id,
                    actual_value=player_id
                ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=[], rule_checks_performed=1)
    
    def _validate_betting_rules_enhanced(self, action_type: str, amount: int,
                                       current_player_bet: int, game_current_bet: int,
                                       player_chips: int) -> ValidationResult:
        """
        增强的下注规则验证（PLAN 33）
        (Phase 2) 使用 player_chips (即 player_balance)
        """
        errors = []
        checks_performed = 0
        
        min_raise = self.game_rules.min_raise_multiplier * game_current_bet
        
        # 1. 跟注(Call)验证
        if action_type == "call":
            checks_performed += 1
            amount_to_call = game_current_bet - current_player_bet
            
            # 允许All-In式的不足额跟注
            is_all_in_call = amount < amount_to_call and amount == player_chips
            
            if amount != amount_to_call and not is_all_in_call:
                errors.append(ValidationError(
                    rule_name="call_amount_validation",
                    error_type="invalid_call_amount",
                    message=f"跟注金额不正确。需要: {amount_to_call}, 提供: {amount}",
                    expected_value=amount_to_call,
                    actual_value=amount
                ))
            
            checks_performed += 1
            if amount > player_chips:
                errors.append(ValidationError(
                    rule_name="call_funds_validation",
                    error_type="insufficient_funds",
                    message=f"跟注筹码不足。需要: {amount}, 拥有: {player_chips}",
                    expected_value=f"<= {player_chips}",
                    actual_value=amount
                ))
        
        # 2. 加注(Raise)验证
        elif action_type == "raise":
            total_bet = amount
            
            checks_performed += 1
            if total_bet <= game_current_bet:
                errors.append(ValidationError(
                    rule_name="raise_min_amount_validation",
                    error_type="raise_too_small",
                    message=f"加注总额必须大于当前下注额。当前: {game_current_bet}, 提供: {total_bet}",
                    expected_value=f"> {game_current_bet}",
                    actual_value=total_bet
                ))
            
            # 验证加注增量 (raise amount = total_bet - game_current_bet)
            # 这里的逻辑需要细化，暂时简化
            
            checks_performed += 1
            if total_bet > player_chips + current_player_bet:
                errors.append(ValidationError(
                    rule_name="raise_funds_validation",
                    error_type="insufficient_funds",
                    message=f"加注筹码不足。需要总下注: {total_bet}, 拥有: {player_chips} (已下注 {current_player_bet})",
                    expected_value=f"<= {player_chips + current_player_bet}",
                    actual_value=total_bet
                ))

        # 3. 下注(Bet)验证
        elif action_type == "bet":
            checks_performed += 1
            if game_current_bet > 0:
                 errors.append(ValidationError(
                    rule_name="bet_in_unopened_pot",
                    error_type="invalid_bet",
                    message="已有下注，不能执行'bet'，应为'raise'",
                    expected_value=0,
                    actual_value=game_current_bet
                ))
            
            checks_performed += 1
            if amount < self.game_rules.big_blind:
                # 允许all-in
                if amount != player_chips:
                    errors.append(ValidationError(
                        rule_name="bet_min_amount_validation",
                        error_type="bet_too_small",
                        message=f"首次下注额不能小于大盲注。需要: >={self.game_rules.big_blind}, 提供: {amount}",
                        expected_value=f">= {self.game_rules.big_blind}",
                        actual_value=amount
                    ))
            
            checks_performed += 1
            if amount > player_chips:
                 errors.append(ValidationError(
                    rule_name="bet_funds_validation",
                    error_type="insufficient_funds",
                    message=f"下注筹码不足。需要: {amount}, 拥有: {player_chips}",
                    expected_value=f"<= {player_chips}",
                    actual_value=amount
                ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=[], rule_checks_performed=checks_performed)
    
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


# 全局单例
_validation_service_instance: Optional[ValidationService] = None

def get_validation_service() -> "ValidationService":
    """
    获取验证服务的单例实例
    
    Returns:
        ValidationService: 验证服务实例
    """
    global _validation_service_instance
    if _validation_service_instance is None:
        # 验证服务依赖配置服务，所以我们也从单例获取配置服务
        config_service = get_config_service()
        _validation_service_instance = ValidationService(config_service=config_service)
    return _validation_service_instance 