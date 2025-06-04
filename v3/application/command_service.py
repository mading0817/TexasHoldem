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
                 enable_invariant_checks: bool = True):
        """
        初始化命令服务
        
        Args:
            event_bus: 事件总线，如果为None则使用全局事件总线
            enable_invariant_checks: 是否启用不变量检查
        """
        self._event_bus = event_bus or get_event_bus()
        self._sessions: Dict[str, GameSession] = {}
        self._state_machine_factory = StateMachineFactory()
        self._snapshot_manager = SnapshotManager()
        self._enable_invariant_checks = enable_invariant_checks
        self._game_invariants: Dict[str, GameInvariants] = {}
    
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
            
            # 验证玩家数量
            if player_ids is None:
                player_ids = [f"player_{i}" for i in range(2)]  # 默认2个玩家
            
            if len(player_ids) < 2 or len(player_ids) > 10:
                return CommandResult.validation_error(
                    f"玩家数量必须在2-10之间，当前: {len(player_ids)}",
                    error_code="INVALID_PLAYER_COUNT"
                )
            
            # 创建状态机和上下文
            state_machine = self._state_machine_factory.create_default_state_machine()
            context = GameContext(
                game_id=game_id,
                current_phase=GamePhase.INIT,
                players={pid: {'chips': 1000, 'active': True} for pid in player_ids},
                community_cards=[],
                pot_total=0,
                current_bet=0,
                small_blind=50,  # 设置小盲注
                big_blind=100    # 设置大盲注
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
            
            # 发布游戏开始事件
            event = GameStartedEvent.create(
                game_id=game_id,
                player_ids=player_ids,
                small_blind=50,  # 默认小盲注
                big_blind=100    # 默认大盲注
            )
            self._event_bus.publish(event)
            
            # 验证游戏不变量
            try:
                self._verify_game_invariants(game_id, "游戏创建")
            except InvariantError as e:
                # 如果不变量违反，清理已创建的游戏
                del self._sessions[game_id]
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
            
            # 检查当前状态是否允许开始新手牌
            current_phase = session.state_machine.current_phase
            if current_phase not in [GamePhase.INIT, GamePhase.FINISHED]:
                return CommandResult.business_rule_violation(
                    f"当前阶段 {current_phase.name} 不允许开始新手牌",
                    error_code="INVALID_PHASE_FOR_NEW_HAND"
                )
            
            # 创建手牌开始事件
            hand_event = GameEvent(
                event_type='HAND_START',
                data={'game_id': game_id, 'timestamp': time.time()},
                source_phase=session.state_machine.current_phase
            )
            
            # 执行状态转换
            session.state_machine.transition(hand_event, session.context)
            session.update_timestamp()
            
            # 发布手牌开始事件
            domain_event = HandStartedEvent.create(
                game_id=game_id,
                hand_number=getattr(session.context, 'hand_number', 1),
                dealer_position=0  # 默认庄家位置
            )
            self._event_bus.publish(domain_event)
            
            # 验证游戏不变量
            try:
                self._verify_game_invariants(game_id, "开始新手牌")
            except InvariantError as e:
                return CommandResult.failure_result(
                    message=f"开始新手牌失败，不变量违反: {str(e)}",
                    error_code="INVARIANT_VIOLATION"
                )
            
            return CommandResult.success_result(
                message=f"游戏 {game_id} 新手牌开始",
                data={'current_phase': session.state_machine.current_phase.name}
            )
            
        except ValidationError as e:
            return CommandResult.validation_error(str(e), e.error_code)
        except BusinessRuleViolationError as e:
            return CommandResult.business_rule_violation(str(e), e.error_code)
        except Exception as e:
            return CommandResult.failure_result(
                message=f"开始新手牌失败: {str(e)}",
                error_code="START_HAND_FAILED"
            )
    
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
            
            # 验证玩家ID
            if player_id not in session.context.players:
                return CommandResult.validation_error(
                    f"玩家 {player_id} 不在游戏中",
                    error_code="PLAYER_NOT_IN_GAME"
                )
            
            # 验证行动类型
            valid_actions = ['fold', 'call', 'raise', 'check', 'all_in']
            if action.action_type not in valid_actions:
                return CommandResult.validation_error(
                    f"无效的行动类型: {action.action_type}",
                    error_code="INVALID_ACTION_TYPE"
                )
            
            # 验证下注金额
            if action.action_type in ['raise', 'all_in'] and action.amount <= 0:
                return CommandResult.validation_error(
                    f"下注金额必须大于0: {action.amount}",
                    error_code="INVALID_BET_AMOUNT"
                )
            
            # 处理玩家行动
            action_dict = action.to_dict()
            game_event = session.state_machine.handle_player_action(
                session.context, player_id, action_dict
            )
            
            session.update_timestamp()
            
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
            
            # 获取或创建游戏的不变量检查器
            if game_id not in self._game_invariants:
                self._game_invariants[game_id] = GameInvariants.create_for_game(snapshot)
            
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