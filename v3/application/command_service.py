"""
Game Command Service - 游戏命令服务

处理所有游戏状态变更操作，遵循CQRS模式。
命令服务负责：
- 执行玩家行动
- 开始新手牌
- 管理游戏状态转换
- 发布领域事件
- 验证数学不变量
"""

import uuid
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .types import CommandResult, PlayerAction, ValidationError, BusinessRuleViolationError, SystemError
from ..core.state_machine import GameStateMachine, StateMachineFactory, GamePhase, GameContext, GameEvent
from ..core.events import (
    EventBus, get_event_bus, DomainEvent, EventType,
    GameStartedEvent, HandStartedEvent, PhaseChangedEvent, PlayerActionExecutedEvent
)
from ..core.invariant import GameInvariants, InvariantError
from ..core.snapshot import SnapshotManager


@dataclass
class GameSession:
    """游戏会话"""
    game_id: str
    state_machine: GameStateMachine
    context: GameContext
    created_at: float
    last_updated: float
    
    def update_timestamp(self) -> None:
        """更新最后修改时间"""
        self.last_updated = time.time()


class GameCommandService:
    """游戏命令服务"""
    
    def __init__(self, event_bus: Optional[EventBus] = None, 
                 enable_invariant_checks: bool = True,
                 validation_service: Optional['ValidationService'] = None,
                 config_service: Optional['ConfigService'] = None):
        """
        初始化命令服务（PLAN 32：注入ValidationService和ConfigService）
        
        Args:
            event_bus: 事件总线，如果为None则使用全局事件总线
            enable_invariant_checks: 是否启用不变量检查
            validation_service: 验证服务
            config_service: 配置服务
        """
        self._event_bus = event_bus or get_event_bus()
        self._sessions: Dict[str, GameSession] = {}
        self._state_machine_factory = StateMachineFactory()
        self._snapshot_manager = SnapshotManager()
        self._enable_invariant_checks = enable_invariant_checks
        self._game_invariants: Dict[str, GameInvariants] = {}
        
        # PLAN 32: 依赖注入ValidationService和ConfigService
        from .validation_service import ValidationService
        from .config_service import ConfigService
        self._validation_service = validation_service or ValidationService(config_service or ConfigService())
        self._config_service = config_service or ConfigService()
    
    def create_new_game(self, game_id: Optional[str] = None, 
                       player_ids: Optional[List[str]] = None) -> CommandResult:
        """
        创建新游戏
        
        Args:
            game_id: 游戏ID，如果为None则自动生成
            player_ids: 玩家ID列表
            
        Returns:
            命令执行结果
        """
        try:
            # 生成游戏ID
            if game_id is None:
                game_id = f"game_{uuid.uuid4().hex[:8]}"
            
            # 检查游戏是否已存在
            if game_id in self._sessions:
                return CommandResult.validation_error(
                    f"游戏 {game_id} 已存在",
                    error_code="GAME_ALREADY_EXISTS"
                )
            
            # 从ConfigService获取游戏规则配置
            game_rules_result = self._config_service.get_game_rules_config()
            if not game_rules_result.success:
                return CommandResult.failure_result(
                    f"获取游戏规则配置失败: {game_rules_result.message}",
                    error_code="CONFIG_LOAD_FAILED"
                )
            game_rules = game_rules_result.data
            
            # 验证玩家数量
            if player_ids is None:
                player_ids = [f"player_{i}" for i in range(game_rules.min_players)]  # 使用配置的最小玩家数
            
            if len(player_ids) < game_rules.min_players or len(player_ids) > game_rules.max_players:
                return CommandResult.validation_error(
                    f"玩家数量必须在{game_rules.min_players}-{game_rules.max_players}之间，当前: {len(player_ids)}",
                    error_code="INVALID_PLAYER_COUNT"
                )
            
            # 创建状态机和上下文
            state_machine = self._state_machine_factory.create_default_state_machine()
            # 为每个玩家分配正确的序列位置
            players_dict = {}
            for i, pid in enumerate(player_ids):
                players_dict[pid] = {
                    'chips': game_rules.initial_chips,  # 使用配置的初始筹码
                    'active': True, 
                    'position': i  # 分配序列位置：0, 1, 2, 3, 4, 5
                }
            
            context = GameContext(
                game_id=game_id,
                current_phase=GamePhase.INIT,
                players=players_dict,
                community_cards=[],
                pot_total=0,
                current_bet=0,
                small_blind=game_rules.small_blind,  # 使用配置的小盲注
                big_blind=game_rules.big_blind       # 使用配置的大盲注
            )
            
            # 创建游戏会话
            session = GameSession(
                game_id=game_id,
                state_machine=state_machine,
                context=context,
                created_at=time.time(),
                last_updated=time.time()
            )
            
            self._sessions[game_id] = session
            
            # 在游戏创建时立即初始化不变量检查器，使用正确的初始筹码
            if self._enable_invariant_checks:
                # 计算真实的初始总筹码：所有玩家的筹码总和（此时底池为0）
                initial_total_chips = sum(player_data['chips'] for player_data in context.players.values())
                
                self._game_invariants[game_id] = GameInvariants(
                    initial_total_chips=initial_total_chips,
                    min_raise_multiplier=game_rules.min_raise_multiplier  # 使用配置的最小加注倍数
                )
            
            # 发布游戏开始事件
            event = GameStartedEvent.create(
                game_id=game_id,
                player_ids=player_ids,
                small_blind=game_rules.small_blind,  # 使用配置的小盲注
                big_blind=game_rules.big_blind       # 使用配置的大盲注
            )
            self._event_bus.publish(event)
            
            # 验证游戏不变量
            try:
                self._verify_game_invariants(game_id, "游戏创建")
            except InvariantError as e:
                # 如果不变量违反，清理已创建的游戏
                del self._sessions[game_id]
                if game_id in self._game_invariants:
                    del self._game_invariants[game_id]
                # 获取详细的违反信息
                violation_details = []
                for violation in e.violations:
                    violation_details.append(f"{violation.invariant_type.name}: {violation.description}")
                
                return CommandResult.failure_result(
                    message=f"游戏创建失败，不变量违反: {str(e)}。详细信息: {'; '.join(violation_details)}",
                    error_code="INVARIANT_VIOLATION"
                )
            
            return CommandResult.success_result(
                message=f"游戏 {game_id} 创建成功",
                data={'game_id': game_id, 'player_count': len(player_ids)}
            )
            
        except Exception as e:
            return CommandResult.failure_result(
                message=f"创建游戏失败: {str(e)}",
                error_code="GAME_CREATION_FAILED"
            )
    
    def start_new_hand(self, game_id: str) -> CommandResult:
        """
        开始新手牌
        
        Args:
            game_id: 游戏ID
            
        Returns:
            命令执行结果
        """
        try:
            # 获取游戏会话
            session = self._get_session(game_id)
            if session is None:
                return CommandResult.validation_error(
                    f"游戏 {game_id} 不存在",
                    error_code="GAME_NOT_FOUND"
                )
            
            # 验证是否有足够的活跃玩家
            active_players = [
                player_id for player_id, player_data in session.context.players.items()
                if player_data.get('chips', 0) > 0
            ]
            
            if len(active_players) < 2:
                return CommandResult.business_rule_violation(
                    f"至少需要2个有筹码的玩家才能开始新手牌，当前只有 {len(active_players)} 个",
                    error_code="INSUFFICIENT_ACTIVE_PLAYERS"
                )
            
            # 重置玩家状态为新手牌
            self._reset_players_for_new_hand(session.context)
            
            # 创建开始新手牌事件
            start_event = GameEvent(
                event_type='HAND_START',
                data={'game_id': game_id, 'timestamp': time.time()},
                source_phase=session.state_machine.current_phase
            )
            
            # 执行状态转换
            session.state_machine.transition(start_event, session.context)
            session.update_timestamp()
            
            # 设置盲注（在状态转换后）
            blind_result = self._setup_blinds_for_new_hand(session.context)
            if not blind_result:
                return CommandResult.business_rule_violation(
                    "设置盲注失败，可能是玩家筹码不足",
                    error_code="BLIND_SETUP_FAILED"
                )
            
            # 发布新手牌开始事件
            domain_event = HandStartedEvent.create(
                game_id=game_id,
                hand_number=1,  # 简化处理，使用默认值
                dealer_position=0  # 默认庄家位置
            )
            self._event_bus.publish(domain_event)
            
            # 注意：不应该在新手牌开始时重置筹码守恒检查器的基准值
            # 筹码守恒的基准应该始终是游戏开始时的总筹码，不应该随着手牌变化
            
            # 验证游戏不变量
            try:
                self._verify_game_invariants(game_id, "开始新手牌")
            except InvariantError as e:
                return CommandResult.failure_result(
                    message=f"开始新手牌失败，不变量违反: {str(e)}",
                    error_code="INVARIANT_VIOLATION"
                )
            
            return CommandResult.success_result(
                message="新手牌开始",
                data={
                    'hand_number': 1,  # 简化处理
                    'current_phase': session.state_machine.current_phase.name,
                    'active_players': len(active_players),
                    'small_blind': session.context.small_blind,
                    'big_blind': session.context.big_blind
                }
            )
            
        except ValidationError as e:
            return CommandResult.validation_error(str(e), e.error_code)
        except BusinessRuleViolationError as e:
            return CommandResult.business_rule_violation(str(e), e.error_code)
        except Exception as e:
            return CommandResult.failure_result(
                message=f"开始新手牌失败: {str(e)}",
                error_code="START_NEW_HAND_FAILED"
            )
    
    def _reset_players_for_new_hand(self, context: GameContext) -> None:
        """重置玩家状态为新手牌"""
        for player_id, player_data in context.players.items():
            # 重置下注相关字段
            player_data['current_bet'] = 0
            player_data['total_bet_this_hand'] = 0
            
            # 重置状态：只有有筹码的玩家才是活跃的
            if player_data.get('chips', 0) > 0:
                player_data['active'] = True
                player_data['status'] = 'active'
            else:
                player_data['active'] = False
                player_data['status'] = 'out'
            
            # 清除上一手牌的状态标记
            player_data.pop('winnings', None)
        
        # 重置游戏状态
        context.pot_total = 0
        context.current_bet = 0
        context.active_player_id = None
    
    def _setup_blinds_for_new_hand(self, context: GameContext) -> bool:
        """为新手牌设置盲注"""
        # 获取有筹码的活跃玩家
        active_players = [
            player_id for player_id, player_data in context.players.items()
            if player_data.get('chips', 0) > 0 and player_data.get('active', False)
        ]
        
        if len(active_players) < 2:
            return False
        
        # 简化处理：第一个玩家小盲，第二个玩家大盲
        small_blind_player = active_players[0]
        big_blind_player = active_players[1]
        
        # 设置小盲注
        small_blind_amount = context.small_blind
        if context.players[small_blind_player]['chips'] >= small_blind_amount:
            context.players[small_blind_player]['chips'] -= small_blind_amount
            context.players[small_blind_player]['current_bet'] = small_blind_amount
            context.players[small_blind_player]['total_bet_this_hand'] = small_blind_amount
            context.pot_total += small_blind_amount
        else:
            # 如果筹码不足，全押
            all_in_amount = context.players[small_blind_player]['chips']
            context.players[small_blind_player]['chips'] = 0
            context.players[small_blind_player]['current_bet'] = all_in_amount
            context.players[small_blind_player]['total_bet_this_hand'] = all_in_amount
            context.players[small_blind_player]['status'] = 'all_in'
            context.pot_total += all_in_amount
        
        # 设置大盲注
        big_blind_amount = context.big_blind
        if context.players[big_blind_player]['chips'] >= big_blind_amount:
            context.players[big_blind_player]['chips'] -= big_blind_amount
            context.players[big_blind_player]['current_bet'] = big_blind_amount
            context.players[big_blind_player]['total_bet_this_hand'] = big_blind_amount
            context.pot_total += big_blind_amount
        else:
            # 如果筹码不足，全押
            all_in_amount = context.players[big_blind_player]['chips']
            context.players[big_blind_player]['chips'] = 0
            context.players[big_blind_player]['current_bet'] = all_in_amount
            context.players[big_blind_player]['total_bet_this_hand'] = all_in_amount
            context.players[big_blind_player]['status'] = 'all_in'
            context.pot_total += all_in_amount
        
        # 设置当前下注为实际的最高下注金额
        max_bet = max(
            context.players[small_blind_player]['current_bet'],
            context.players[big_blind_player]['current_bet']
        )
        context.current_bet = max_bet
        
        # 设置下一个行动玩家（大盲注后的玩家）
        if len(active_players) > 2:
            context.active_player_id = active_players[2]
        else:
            # 只有两个玩家时，小盲注先行动
            context.active_player_id = small_blind_player
        
        return True
    
    def execute_player_action(self, game_id: str, player_id: str, action: PlayerAction) -> CommandResult:
        """
        执行玩家行动
        
        Args:
            game_id: 游戏ID
            player_id: 玩家ID
            action: 玩家行动
            
        Returns:
            命令执行结果
        """
        try:
            # 获取游戏会话
            session = self._get_session(game_id)
            if session is None:
                return CommandResult.validation_error(
                    f"游戏 {game_id} 不存在",
                    error_code="GAME_NOT_FOUND"
                )
            
            # PLAN 32: 使用ValidationService进行详细业务规则验证
            validation_result = self._validation_service.validate_player_action(
                session.context, player_id, action
            )
            
            if not validation_result.success:
                return CommandResult.validation_error(
                    f"玩家行动验证失败: {validation_result.message}",
                    error_code="VALIDATION_SERVICE_FAILED"
                )
            
            validation_data = validation_result.data
            if not validation_data.is_valid:
                # 根据ValidationResult中的详细信息返回适当的错误
                errors = validation_data.errors
                if errors:
                    first_error = errors[0]
                    if first_error.error_type in ["invalid_action", "invalid_amount"]:
                        return CommandResult.validation_error(
                            first_error.message,
                            error_code=first_error.error_type.upper()
                        )
                    else:
                        return CommandResult.business_rule_violation(
                            first_error.message,
                            error_code=first_error.error_type.upper()
                        )
                else:
                    return CommandResult.business_rule_violation(
                        "玩家行动不符合游戏规则",
                        error_code="VALIDATION_FAILED"
                    )
            
            # 处理玩家行动
            action_dict = action.to_dict()
            game_event = session.state_machine.handle_player_action(
                session.context, player_id, action_dict
            )
            
            session.update_timestamp()
            
            # 检查是否触发了自动结束事件
            if game_event.event_type == "HAND_AUTO_FINISH":
                # 手牌自动结束，直接跳转到FINISHED阶段
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[游戏事件] 检测到自动结束事件: {game_event.data}")
                
                # 执行状态转换到FINISHED阶段
                session.state_machine.transition(game_event, session.context)
                session.update_timestamp()
                
                # 发布阶段变更事件
                domain_event = PhaseChangedEvent.create(
                    game_id=game_id,
                    from_phase=game_event.source_phase.name,
                    to_phase=session.state_machine.current_phase.name
                )
                self._event_bus.publish(domain_event)
                
                return CommandResult.success_result(
                    message=f"玩家 {player_id} 执行 {action.action_type} 后手牌自动结束",
                    data={
                        'action_type': action.action_type,
                        'amount': action.amount,
                        'current_phase': session.state_machine.current_phase.name,
                        'auto_finished': True,
                        'reason': game_event.data.get('reason', '未知原因')
                    }
                )
            
            # 发布玩家行动执行事件
            domain_event = PlayerActionExecutedEvent.create(
                game_id=game_id,
                player_id=player_id,
                action_type=action.action_type,
                amount=action.amount
            )
            self._event_bus.publish(domain_event)
            
            # 验证游戏不变量
            try:
                self._verify_game_invariants(game_id, f"玩家行动: {action.action_type}")
            except InvariantError as e:
                return CommandResult.failure_result(
                    message=f"玩家行动失败，不变量违反: {str(e)}",
                    error_code="INVARIANT_VIOLATION"
                )
            
            # 检查是否需要自动推进阶段
            auto_advance_result = self._check_and_auto_advance_phase(session)
            if auto_advance_result and not auto_advance_result.success:
                # 自动推进失败，记录警告但不影响玩家行动成功
                pass  # 可以在这里记录日志
            
            return CommandResult.success_result(
                message=f"玩家 {player_id} 执行 {action.action_type} 成功",
                data={
                    'action_type': action.action_type,
                    'amount': action.amount,
                    'current_phase': session.state_machine.current_phase.name
                }
            )
            
        except ValidationError as e:
            return CommandResult.validation_error(str(e), e.error_code)
        except BusinessRuleViolationError as e:
            return CommandResult.business_rule_violation(str(e), e.error_code)
        except Exception as e:
            return CommandResult.failure_result(
                message=f"执行玩家行动失败: {str(e)}",
                error_code="PLAYER_ACTION_FAILED"
            )
    
    def advance_phase(self, game_id: str) -> CommandResult:
        """
        推进游戏阶段
        
        Args:
            game_id: 游戏ID
            
        Returns:
            命令执行结果
        """
        try:
            # 获取游戏会话
            session = self._get_session(game_id)
            if session is None:
                return CommandResult.validation_error(
                    f"游戏 {game_id} 不存在",
                    error_code="GAME_NOT_FOUND"
                )
            
            old_phase = session.state_machine.current_phase
            
            # 创建阶段推进事件
            phase_event = GameEvent(
                event_type='BETTING_ROUND_COMPLETE',
                data={'game_id': game_id, 'timestamp': time.time()},
                source_phase=session.state_machine.current_phase
            )
            
            # 执行状态转换
            session.state_machine.transition(phase_event, session.context)
            session.update_timestamp()
            
            new_phase = session.state_machine.current_phase
            
            # 发布阶段变更事件
            domain_event = PhaseChangedEvent.create(
                game_id=game_id,
                from_phase=old_phase.name,
                to_phase=new_phase.name
            )
            self._event_bus.publish(domain_event)
            
            # 验证游戏不变量
            try:
                self._verify_game_invariants(game_id, f"阶段推进: {old_phase.name} -> {new_phase.name}")
            except InvariantError as e:
                return CommandResult.failure_result(
                    message=f"阶段推进失败，不变量违反: {str(e)}",
                    error_code="INVARIANT_VIOLATION"
                )
            
            return CommandResult.success_result(
                message=f"游戏阶段从 {old_phase.name} 推进到 {new_phase.name}",
                data={
                    'old_phase': old_phase.name,
                    'new_phase': new_phase.name
                }
            )
            
        except Exception as e:
            return CommandResult.failure_result(
                message=f"推进游戏阶段失败: {str(e)}",
                error_code="ADVANCE_PHASE_FAILED"
            )
    
    def remove_game(self, game_id: str) -> CommandResult:
        """
        移除游戏
        
        Args:
            game_id: 游戏ID
            
        Returns:
            命令执行结果
        """
        try:
            if game_id not in self._sessions:
                return CommandResult.validation_error(
                    f"游戏 {game_id} 不存在",
                    error_code="GAME_NOT_FOUND"
                )
            
            del self._sessions[game_id]
            
            return CommandResult.success_result(
                message=f"游戏 {game_id} 已移除"
            )
            
        except Exception as e:
            return CommandResult.failure_result(
                message=f"移除游戏失败: {str(e)}",
                error_code="REMOVE_GAME_FAILED"
            )
    
    def _get_session(self, game_id: str) -> Optional[GameSession]:
        """获取游戏会话"""
        return self._sessions.get(game_id)
    
    def get_active_games(self) -> List[str]:
        """获取活跃游戏列表"""
        return list(self._sessions.keys())
    
    def get_game_state_snapshot(self, game_id: str) -> 'QueryResult[GameStateSnapshot]':
        """
        获取游戏状态快照 (PLAN 39: 只读状态快照接口)
        
        该方法为查询服务提供解耦的状态访问接口，返回不可变的状态快照。
        
        Args:
            game_id: 游戏ID
            
        Returns:
            QueryResult[GameStateSnapshot]: 查询结果，包含游戏状态快照
        """
        try:
            # 导入必要的类型
            from .types import QueryResult
            from .query_service import GameStateSnapshot
            
            # 获取游戏会话
            session = self._get_session(game_id)
            if session is None:
                return QueryResult.business_rule_violation(
                    f"游戏 {game_id} 不存在",
                    error_code="GAME_NOT_FOUND"
                )
            
            # 创建不可变的状态快照（只复制必要数据，避免暴露内部对象）
            snapshot = GameStateSnapshot(
                game_id=session.context.game_id,
                current_phase=session.state_machine.current_phase.name,
                players=session.context.players.copy(),  # 浅拷贝玩家数据
                community_cards=session.context.community_cards.copy(),  # 浅拷贝公共牌
                pot_total=session.context.pot_total,
                current_bet=session.context.current_bet,
                active_player_id=session.context.active_player_id,
                timestamp=session.last_updated
            )
            
            return QueryResult.success_result(snapshot)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取游戏状态快照失败: {str(e)}",
                error_code="GET_GAME_STATE_SNAPSHOT_FAILED"
            )
    
    def _verify_game_invariants(self, game_id: str, operation_context: str = "游戏操作") -> None:
        """
        验证游戏不变量
        
        Args:
            game_id: 游戏ID
            operation_context: 操作上下文描述
            
        Raises:
            InvariantError: 当不变量被违反时
        """
        if not self._enable_invariant_checks:
            return
        
        session = self._get_session(game_id)
        if session is None:
            return
        
        try:
            # 创建当前状态快照
            snapshot = self._snapshot_manager.create_snapshot(session.context)
            
            # 获取游戏的不变量检查器（应该在游戏创建时已经创建）
            if game_id not in self._game_invariants:
                # 这种情况不应该发生，但为了安全起见，使用固定的初始筹码
                # 注意：这里不应该重新计算，而应该使用固定的6000筹码
                self._game_invariants[game_id] = GameInvariants(
                    initial_total_chips=6000,  # 固定使用6000筹码，不依赖当前玩家数量
                    min_raise_multiplier=2.0
                )
            
            invariants = self._game_invariants[game_id]
            
            # 验证不变量并在违反时抛出异常
            invariants.validate_and_raise(snapshot, operation_context)
            
        except InvariantError:
            # 重新抛出不变量错误
            raise
        except Exception as e:
            # 其他错误转换为系统错误
            raise SystemError(f"不变量检查失败: {str(e)}")
    
    def _get_invariant_stats(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        获取游戏的不变量统计信息
        
        Args:
            game_id: 游戏ID
            
        Returns:
            Optional[Dict[str, Any]]: 统计信息，如果游戏不存在则返回None
        """
        if not self._enable_invariant_checks or game_id not in self._game_invariants:
            return None
        
        session = self._get_session(game_id)
        if session is None:
            return None
        
        try:
            snapshot = self._snapshot_manager.create_snapshot(session.context)
            invariants = self._game_invariants[game_id]
            return invariants.get_performance_stats(snapshot)
        except Exception:
            return None
    
    def _check_and_auto_advance_phase(self, session: GameSession) -> Optional[CommandResult]:
        """
        检查是否需要自动推进阶段
        
        Args:
            session: 游戏会话
            
        Returns:
            如果需要推进阶段，返回推进结果；否则返回None
        """
        try:
            # 只在特定阶段检查自动推进
            betting_phases = ['PRE_FLOP', 'FLOP', 'TURN', 'RIVER']
            current_phase_name = session.state_machine.current_phase.name
            
            if current_phase_name not in betting_phases:
                return None
            
            # 检查是否还有需要行动的玩家
            needs_action = self._find_players_needing_action(session.context)
            
            if not needs_action:
                # 没有玩家需要行动，自动推进阶段
                from ..core.state_machine.types import GameEvent
                import time
                
                phase_event = GameEvent(
                    event_type='BETTING_ROUND_COMPLETE',
                    data={
                        'game_id': session.game_id, 
                        'timestamp': time.time(),
                        'auto_advanced': True
                    },
                    source_phase=session.state_machine.current_phase
                )
                
                # 执行状态转换
                old_phase = session.state_machine.current_phase
                session.state_machine.transition(phase_event, session.context)
                session.update_timestamp()
                
                new_phase = session.state_machine.current_phase
                
                # 发布阶段变更事件
                from ..core.events.domain_events import PhaseChangedEvent
                domain_event = PhaseChangedEvent.create(
                    game_id=session.game_id,
                    from_phase=old_phase.name,
                    to_phase=new_phase.name
                )
                self._event_bus.publish(domain_event)
                
                return CommandResult.success_result(
                    message=f"自动推进阶段: {old_phase.name} → {new_phase.name}",
                    data={
                        'from_phase': old_phase.name,
                        'to_phase': new_phase.name,
                        'auto_advanced': True
                    }
                )
            
            return None
            
        except Exception as e:
            return CommandResult.failure_result(
                message=f"自动推进阶段失败: {str(e)}",
                error_code="AUTO_ADVANCE_FAILED"
            )
    
    def _find_players_needing_action(self, context: GameContext) -> List[str]:
        """
        找到需要行动的玩家
        
        Args:
            context: 游戏上下文
            
        Returns:
            需要行动的玩家ID列表
        """
        players_needing_action = []
        
        for player_id, player_data in context.players.items():
            # 检查玩家是否可以行动：必须活跃且有筹码，且不是fold/out/all_in状态
            can_act = (
                player_data.get('active', False) and 
                player_data.get('chips', 0) > 0 and 
                player_data.get('status', 'active') not in ['folded', 'out', 'all_in']
            )
            
            if can_act:
                # 检查是否需要行动（下注不足）
                current_bet_amount = player_data.get('current_bet', 0)
                if current_bet_amount < context.current_bet:
                    players_needing_action.append(player_id)
        
        return players_needing_action 