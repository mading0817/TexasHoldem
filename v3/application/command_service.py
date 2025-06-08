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
from dataclasses import dataclass, asdict
import logging
import bisect

from .types import CommandResult, PlayerAction, ValidationError, BusinessRuleViolationError, SystemError
from ..core.state_machine import GameStateMachine, StateMachineFactory, GamePhase, GameContext, GameEvent
from ..core.events import (
    EventBus, get_event_bus, DomainEvent, EventType,
    GameStartedEvent, HandStartedEvent, PhaseChangedEvent, PlayerActionExecutedEvent,
    PlayerJoinedEvent, HandEndedEvent
)
from ..core.invariant import GameInvariants, InvariantError
from ..core.snapshot import SnapshotManager, get_snapshot_manager
from ..core.chips.chip_ledger import ChipLedger
from ..core.rules.phase_logic import get_possible_next_phases
from v3.application.types import QueryResult


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
                 config_service: Optional['ConfigService'] = None,
                 snapshot_manager: Optional[SnapshotManager] = None):
        """
        初始化命令服务（PLAN 32：注入ValidationService和ConfigService）
        
        Args:
            event_bus: 事件总线，如果为None则使用全局事件总线
            enable_invariant_checks: 是否启用不变量检查
            validation_service: 验证服务
            config_service: 配置服务
            snapshot_manager: 快照管理器
        """
        self._event_bus = event_bus or get_event_bus()
        self._sessions: Dict[str, GameSession] = {}
        self._state_machine_factory = StateMachineFactory()
        self._snapshot_manager = snapshot_manager or get_snapshot_manager()
        self._enable_invariant_checks = enable_invariant_checks
        self._game_invariants: Dict[str, GameInvariants] = {}
        
        # PLAN 32: 依赖注入ValidationService和ConfigService
        from .validation_service import ValidationService, get_validation_service
        from .config_service import ConfigService, get_config_service
        self.validation_service = validation_service or get_validation_service()
        self._config_service = config_service or get_config_service()
        self._subscribe_to_events()
    
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

            # (Phase 1.B) 创建ChipLedger作为筹码的唯一真实来源
            initial_balances = {
                pid: game_rules.initial_chips
                for pid in player_ids
            }
            chip_ledger = ChipLedger(initial_balances=initial_balances)

            # (Phase 1.B) players_dict现在只存储状态，不存储筹码
            players_dict = {
                pid: {'active': True, 'position': i}
                for i, pid in enumerate(player_ids)
            }
            
            context = GameContext(
                game_id=game_id,
                current_phase=GamePhase.INIT,
                players=players_dict,
                chip_ledger=chip_ledger, # (Phase 1.B) 注入ChipLedger
                community_cards=[],
                current_bet=0,
                small_blind=game_rules.small_blind,
                big_blind=game_rules.big_blind
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
            
            # (Phase 1.B) 更新不变量检查以使用ChipLedger
            if self._enable_invariant_checks:
                # 从ChipLedger获取初始总筹码
                initial_total_chips = chip_ledger.get_total_chips()
                
                self._game_invariants[game_id] = GameInvariants(
                    initial_total_chips=initial_total_chips,
                    min_raise_multiplier=game_rules.min_raise_multiplier
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
        logger = logging.getLogger(__name__)

        try:
            # Step 1: 获取游戏会话
            try:
                session = self._get_session(game_id)
                if session is None:
                    return CommandResult.validation_error(f"游戏 {game_id} 不存在", error_code="GAME_NOT_FOUND")
            except TypeError as e:
                logger.error(f"START_NEW_HAND FAILED at Step 1 (_get_session): {e}", exc_info=True)
                raise SystemError(f"获取会话时发生内部错误: {e}") from e

            # Step 2: 验证活跃玩家
            try:
                # (Phase 1.B) 验证是否有足够的活跃玩家，使用ChipLedger
                active_players = [
                    player_id for player_id in session.context.players
                    if session.context.chip_ledger.get_balance(player_id) > 0
                ]
                
                if len(active_players) < 2:
                    return CommandResult.business_rule_violation(
                        f"至少需要2个有筹码的玩家才能开始新手牌，当前只有 {len(active_players)} 个",
                        error_code="INSUFFICIENT_ACTIVE_PLAYERS"
                    )
            except TypeError as e:
                logger.error(f"START_NEW_HAND FAILED at Step 2 (active player validation): {e}", exc_info=True)
                logger.error(f"Problematic players object type: {type(session.context.players)}")
                raise SystemError(f"验证活跃玩家时发生内部错误: {e}") from e

            # Step 3: 重置玩家状态为新手牌
            try:
                self._reset_players_for_new_hand(session.context)
            except TypeError as e:
                logger.error(f"START_NEW_HAND FAILED at Step 3 (_reset_players_for_new_hand): {e}", exc_info=True)
                raise SystemError(f"重置玩家状态时发生内部错误: {e}") from e
            
            # Step 4: 创建并处理状态机事件
            try:
                # 创建开始新手牌事件 - 修复：使用正确的事件类型
                start_event = GameEvent(
                    event_type='START_NEW_HAND',
                    data={'game_id': game_id, 'timestamp': time.time()},
                    source_phase=session.state_machine.current_phase
                )
                
                # 执行状态转换
                session.state_machine.handle_event(start_event, session.context)
                session.update_timestamp()
            except TypeError as e:
                logger.error(f"START_NEW_HAND FAILED at Step 4 (state machine event): {e}", exc_info=True)
                raise SystemError(f"状态机处理事件时发生内部错误: {e}") from e

            # Step 5: 设置盲注
            try:
                # 设置盲注（在状态转换后）
                blind_result = self._setup_blinds_for_new_hand(session.context)
                if not blind_result:
                    return CommandResult.business_rule_violation(
                        "设置盲注失败，可能是玩家筹码不足",
                        error_code="BLIND_SETUP_FAILED"
                    )
                
                # 修复：在盲注设置后，触发状态机进入下一个阶段（PRE_FLOP）
                blinds_posted_event = GameEvent(
                    event_type='BLINDS_POSTED',
                    data={'game_id': game_id},
                    source_phase=session.context.current_phase
                )
                session.state_machine.handle_event(blinds_posted_event, session.context)
                session.update_timestamp()

            except TypeError as e:
                logger.error(f"START_NEW_HAND FAILED at Step 5 (_setup_blinds_for_new_hand or state transition): {e}", exc_info=True)
                raise SystemError(f"设置盲注或状态转换时发生内部错误: {e}") from e

            # Step 6: 发布新手牌开始事件
            try:
                domain_event = HandStartedEvent.create(
                    game_id=game_id,
                    hand_number=1,  # 简化处理，使用默认值
                    dealer_position=0  # 默认庄家位置
                )
                self._event_bus.publish(domain_event)
            except TypeError as e:
                logger.error(f"START_NEW_HAND FAILED at Step 6 (publish event): {e}", exc_info=True)
                raise SystemError(f"发布领域事件时发生内部错误: {e}") from e

            # Step 7: 验证不变量
            try:
                self._verify_game_invariants(game_id, "开始新手牌")
            except InvariantError as e:
                return CommandResult.failure_result(
                    message=f"开始新手牌失败，不变量违反: {str(e)}",
                    error_code="INVARIANT_VIOLATION"
                )
            except TypeError as e:
                logger.error(f"START_NEW_HAND FAILED at Step 7 (_verify_game_invariants): {e}", exc_info=True)
                raise SystemError(f"验证不变量时发生内部错误: {e}") from e
            
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
            
        except BusinessRuleViolationError as e:
            return CommandResult.business_rule_violation(str(e), error_code=e.error_code)
        
        except ValidationError as e:
            return CommandResult.validation_error(str(e), error_code=e.error_code)

        except SystemError as e:
            # 捕获由内部try-except块重新引发的SystemError
            logger.critical(f"系统错误导致 start_new_hand 失败: {e}", exc_info=True)
            return CommandResult.failure_result(f"内部系统错误: {e}", error_code="INTERNAL_SYSTEM_ERROR")

        except Exception as e:
            logger.critical(f"未知错误导致 start_new_hand 失败: {e}", exc_info=True)
            return CommandResult.failure_result(
                message=f"开始新手牌失败: {str(e)}",
                error_code="UNEXPECTED_ERROR_ON_HAND_START"
            )
    
    def _reset_players_for_new_hand(self, context: GameContext) -> None:
        """
        为新手牌重置玩家状态。
        
        增加了防御性编程，以确保即使 context.players 意外地成为元组，也能正确处理。
        """
        logger = logging.getLogger(__name__)

        # 防御性检查：确保 players 是一个字典
        if not isinstance(context.players, dict):
            logger.warning(f"context.players 的类型不是 dict，而是 {type(context.players)}。正在尝试恢复。")
            
            # 尝试从元组或其他可迭代对象恢复为字典
            try:
                # 假设元组中的每个元素都是一个有 'player_id' 键的字典
                recovered_players = {p['player_id']: p for p in context.players}
                context.players = recovered_players
                logger.info(f"已成功将 players 恢复为字典结构。")
            except (TypeError, KeyError) as e:
                logger.error(f"无法从意外的 players 结构中恢复: {e}", exc_info=True)
                # 如果无法恢复，则抛出异常以防止进一步的状态损坏
                raise SystemError("玩家数据结构已损坏且无法恢复")

        player_ids = list(context.players.keys())
        if not player_ids:
            return  # 没有玩家，无需重置

        # 重置所有玩家的状态
        for player_id, player_data in context.players.items():
            # 确保 player_data 是字典
            if not isinstance(player_data, dict):
                logger.warning(f"玩家 {player_id} 的数据不是字典，而是 {type(player_data)}。跳过重置。")
                continue

            # 修复：使用 ChipLedger 获取真实的筹码余额
            player_chips = context.chip_ledger.get_balance(player_id)
            if player_chips <= 0:
                player_data['status'] = 'out'
            else:
                player_data['status'] = 'active'
            
            player_data['active'] = (player_data['status'] == 'active')
            player_data['hole_cards'] = []
            player_data['current_bet'] = 0
            player_data['total_bet_this_hand'] = 0
            player_data['has_acted_this_round'] = False
            player_data['last_action'] = None
        
        # 重置牌局级别的状态
        context.community_cards = []
        context.current_bet = 0
        context.active_player_id = None
        context.winners_this_hand = []
        context.current_hand_bets.clear()
    
    def _setup_blinds_for_new_hand(self, context: GameContext) -> bool:
        """为新手牌设置盲注"""
        # (Phase 1.B) 使用ChipLedger和current_hand_bets重构
        
        players_dict = context.players
        
        # 确定大小盲注玩家
        num_players = len(players_dict)
        
        # 修复：在第一手牌时初始化dealer_position
        if context.dealer_position is None:
            context.dealer_position = -1 # 初始化为-1，这样+1后从0开始
        
        dealer_pos = context.dealer_position
        
        # 获取有筹码的活跃玩家ID和位置
        active_players = sorted([
            (p_id, p_data['position'])
            for p_id, p_data in players_dict.items()
            if context.chip_ledger.get_balance(p_id) > 0 and p_data.get('active')
        ], key=lambda x: x[1])

        if len(active_players) < 2:
            return False # 活跃玩家少于2人，无法开始

        # 确定按钮位置（庄家位置），每手牌顺时针移动
        # 注意：这里的逻辑假设了 context.players 的迭代顺序是稳定的（按位置排序）
        # 如果不是，需要先排序
        all_player_positions = sorted(p_data['position'] for p_data in context.players.values())
        current_dealer_index = all_player_positions.index(context.dealer_position) if context.dealer_position in all_player_positions else -1
        next_dealer_index = (current_dealer_index + 1) % len(all_player_positions)
        context.dealer_position = all_player_positions[next_dealer_index]

        # 确定小盲注和大盲注位置
        # 修复：处理两人游戏(Heads-up)的特殊情况
        if len(active_players) == 2:
            # 两人游戏：庄家兼任小盲注，对手是大盲注
            small_blind_pos = context.dealer_position
            
            # 找到非庄家玩家作为大盲注
            big_blind_pos = None  # 初始化变量
            for _, pos in active_players:
                if pos != context.dealer_position:
                    big_blind_pos = pos
                    break
            
            # 如果没有找到非庄家玩家，使用默认逻辑（不应该发生）
            if big_blind_pos is None:
                big_blind_pos = (context.dealer_position + 1) % 2
        else:
            # 3人及以上游戏：标准德州扑克规则
            # 修复：从庄家位置(dealer_position)之后开始寻找，而不是button_pos
            active_positions = {pos for _, pos in active_players}
            
            # 为了能循环，需要一个有序的位置列表
            sorted_active_positions = [pos for _, pos in active_players]

            # 找到 dealer 在 sorted_active_positions 中的索引，或他本该在的位置
            # 这确保了即使dealer本人不活跃，也能从他之后开始计算
            # bisect_left 可以在 dealer_pos 不存在时，找到其应该插入的位置
            dealer_idx = bisect.bisect_left(sorted_active_positions, context.dealer_position)
            
            # 从庄家之后开始找小盲注
            sb_idx = (dealer_idx + 1) % len(sorted_active_positions)
            small_blind_pos = sorted_active_positions[sb_idx]
            
            # 从小盲注之后开始找大盲注
            bb_idx = (sb_idx + 1) % len(sorted_active_positions)
            big_blind_pos = sorted_active_positions[bb_idx]

        # 修复: 将计算出的盲注位置更新到上下文中
        context.small_blind_position = small_blind_pos
        context.big_blind_position = big_blind_pos
        
        # 获取player_id
        active_players_by_pos = {pos: p_id for p_id, pos in active_players}
        small_blind_player = active_players_by_pos[small_blind_pos]
        big_blind_player = active_players_by_pos[big_blind_pos]

        # 内部函数来处理下盲注逻辑
        def post_blind(player_id: str, blind_amount: int, blind_type: str) -> int:
            player_balance = context.chip_ledger.get_balance(player_id)
            amount_to_post = min(player_balance, blind_amount)
            
            if amount_to_post > 0:
                context.chip_ledger.freeze_chips(player_id, amount_to_post, f"下{blind_type}")
                context.current_hand_bets[player_id] = context.current_hand_bets.get(player_id, 0) + amount_to_post
                context.players[player_id]['current_bet'] = amount_to_post
                context.players[player_id]['total_bet_this_hand'] = amount_to_post
                
                if amount_to_post >= player_balance:
                    context.players[player_id]['status'] = 'all_in'
            
            return amount_to_post

        # 下大小盲注
        sb_posted = post_blind(small_blind_player, context.small_blind, "小盲注")
        bb_posted = post_blind(big_blind_player, context.big_blind, "大盲注")

        # 设置当前下注额
        context.current_bet = bb_posted
        
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
            
            # (Phase 2) 使用ValidationService进行详细业务规则验证
            validation_result = self.validation_service.validate_player_action(
                session.context, player_id, action
            )
            
            if not validation_result.success:
                return CommandResult.failure_result(
                    f"玩家行动验证失败: {validation_result.message}",
                    error_code="VALIDATION_SERVICE_FAILED"
                )
            
            validation_data = validation_result.data
            if not validation_data.is_valid:
                # 根据ValidationResult中的详细信息返回适当的错误
                errors = validation_data.errors
                if errors:
                    first_error = errors[0]
                    return CommandResult.validation_error(
                        first_error.message,
                        error_code=first_error.error_type.upper()
                    )
                else:
                    return CommandResult.business_rule_violation(
                        "玩家行动不符合游戏规则",
                        error_code="VALIDATION_FAILED"
                    )
            
            # (Phase 2) 创建事件并交由状态机处理，状态变更在Handler中进行
            action_type = action.action_type.upper()
            game_event = GameEvent(
                event_type=f'PLAYER_ACTION_{action_type}',
                data={'player_id': player_id, 'action': action.to_dict()},
                source_phase=session.context.current_phase
            )
            
            session.state_machine.handle_event(game_event, session.context)
            session.update_timestamp()

            # 发布领域事件
            domain_event = PlayerActionExecutedEvent.create(
                game_id=game_id,
                player_id=player_id,
                action_type=action.action_type,
                amount=action.amount,
                phase=session.context.current_phase.name
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
                pass # 可以在这里记录日志
            
            return CommandResult.success_result(
                message=f"玩家 {player_id} 执行 {action.action_type} 成功",
                data={
                    'action_type': action.action_type,
                    'amount': action.amount,
                    'current_phase': session.context.current_phase.name
                }
            )
            
        except ValidationError as e:
            return CommandResult.validation_error(str(e), e.error_code)
        except BusinessRuleViolationError as e:
            return CommandResult.business_rule_violation(str(e), e.error_code)
        except Exception as e:
            logger.error(f"执行玩家操作时发生未知错误: {e}", exc_info=True)
            return CommandResult.failure_result(f"执行玩家操作失败: {e}", "PLAYER_ACTION_FAILED")
    
    def advance_phase(self, game_id: str) -> CommandResult:
        """
        自动推进游戏到下一阶段
        
        只有在没有玩家需要行动且存在唯一的、无条件的下一阶段时，此方法才会成功推进。
        例如，从 INIT 到 PRE_FLOP，或者从 PRE_FLOP 轮下注结束后到 FLOP。
        
        Args:
            game_id: 游戏ID
            
        Returns:
            命令执行结果
        """
        logger = logging.getLogger(__name__)

        try:
            session = self._get_session(game_id)
            if not session:
                return CommandResult.validation_error(f"游戏 {game_id} 不存在", "GAME_NOT_FOUND")

            current_phase = session.context.current_phase
            logger.debug(f"尝试从阶段 {current_phase.name} 自动推进")

            # 调用核心逻辑获取可能的下一阶段
            result = get_possible_next_phases(current_phase, session.context)

            if not result.success:
                return CommandResult.failure_result(
                    f"无法确定下一阶段: {result.message}", "PHASE_LOGIC_ERROR"
                )

            possible_phases = result.data
            next_phase = None

            # 决策逻辑：
            # 1. 如果当前是INIT，并且有足够玩家，则明确进入PRE_FLOP
            if current_phase == GamePhase.INIT:
                active_players = [
                    p for p in session.context.players
                    if session.context.chip_ledger.get_balance(p) > 0
                ]
                if len(active_players) >= 2:
                    next_phase = GamePhase.PRE_FLOP
                else: # 玩家不够，游戏结束
                    next_phase = GamePhase.FINISHED
            
            # 2. 如果只有一个可能的非FINISHED阶段，则选择它
            elif len(possible_phases) > 0:
                non_finished_phases = [p for p in possible_phases if p != GamePhase.FINISHED]
                if len(non_finished_phases) == 1:
                    next_phase = non_finished_phases[0]
                # 如果有多个可能阶段，或只有FINISHED，则依赖更明确的事件触发，不自动推进

            if next_phase:
                logger.info(f"游戏 {game_id} 自动从 {current_phase.name} 推进到 {next_phase.name}")
                
                # 更新上下文中的当前阶段
                # 注意：这是对状态机的"提示"，实际阶段转换由状态机处理器完成
                session.context.current_phase = next_phase
                
                # 创建并让状态机处理 on_enter/on_exit 逻辑
                event = GameEvent(
                    event_type=EventType.PHASE_CHANGED,
                    data={'next_phase': next_phase},
                    source_phase=current_phase
                )
                session.state_machine.handle_event(event, session.context)
                
                # 发布领域事件
                self._event_bus.publish(PhaseChangedEvent.create(
                    game_id=game_id,
                    from_phase=current_phase.name,
                    to_phase=next_phase.name,
                ))

                session.update_timestamp()

                # 阶段转换后验证不变量
                self._verify_game_invariants(game_id, f"阶段转换后: {next_phase.name}")

                return CommandResult.success_result(
                    message=f"阶段已成功从 {current_phase.name} 推进到 {next_phase.name}",
                    data={'new_phase': next_phase.name}
                )
            else:
                message = f"无法从阶段 {current_phase.name} 自动推进（无明确单一目标）"
                logger.warning(message)
                return CommandResult.success_result(
                    message=message,
                    data={'requires_player_action': True}
                )

        except InvariantError as e:
            logger.error(f"推进阶段时发生不变量错误: {e}", exc_info=True)
            return CommandResult.failure_result(f"不变量违反: {e}", "INVARIANT_VIOLATION")
        except Exception as e:
            logger.error(f"推进阶段时发生未知错误: {e}", exc_info=True)
            return CommandResult.failure_result(f"推进阶段失败: {e}", "ADVANCE_PHASE_FAILED")
    
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
    
    def _get_session(self, game_id: str) -> GameSession:
        """安全地获取游戏会话，如果不存在则抛出异常"""
        session = self._sessions.get(game_id)
        if session is None:
            raise ValueError(f"游戏 {game_id} 不存在或未初始化")
        return session

    def get_live_context(self, game_id: str) -> QueryResult:
        """
        获取实时的游戏上下文 (非快照)
        
        Args:
            game_id: 游戏ID
        
        Returns:
            查询结果，包含实时的GameContext
        """
        try:
            session = self._get_session(game_id)
            return QueryResult.success_result(session.context)
        except ValueError as e:
            return QueryResult.failure_result(str(e), error_code="GAME_NOT_FOUND")
    
    def get_active_games(self) -> List[str]:
        """获取活跃游戏列表"""
        return list(self._sessions.keys())
    
    def get_game_state_snapshot(self, game_id: str) -> QueryResult:
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
            from ..core.snapshot.types import GameStateSnapshot
            
            # 获取游戏会话
            session = self._get_session(game_id)
            if session is None:
                return QueryResult.business_rule_violation(
                    f"游戏 {game_id} 不存在",
                    error_code="GAME_NOT_FOUND"
                )
            
            # (Phase 4 Fix) 统一使用SnapshotManager创建快照，避免逻辑分散
            snapshot = self._snapshot_manager.create_snapshot(session.context)
            
            return QueryResult.success_result(snapshot)
            
        except Exception as e:
            # 导入QueryService以返回错误
            from .types import QueryResult
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
        
        # 在PRE_FLOP阶段，如果还没有确定活跃玩家，返回空列表让PreFlopHandler处理
        if context.current_phase == GamePhase.PRE_FLOP and context.active_player_id is None:
            return []
        
        for player_id, player_data in context.players.items():
            # 检查玩家是否可以行动：必须活跃且有筹码，且不是fold/out/all_in状态
            can_act = (
                player_data.get('active', False) and 
                context.chip_ledger.get_balance(player_id) > 0 and 
                player_data.get('status', 'active') not in ['folded', 'out', 'all_in']
            )
            
            if can_act:
                # 在PRE_FLOP阶段，如果有活跃玩家，那么首先应该是该玩家行动
                if context.current_phase == GamePhase.PRE_FLOP and context.active_player_id == player_id:
                    players_needing_action.append(player_id)
                # 在其他情况下，检查是否需要行动（下注不足）
                elif context.current_phase != GamePhase.PRE_FLOP or context.active_player_id != player_id:
                    current_bet_amount = player_data.get('current_bet', 0)
                    if current_bet_amount < context.current_bet:
                        players_needing_action.append(player_id)
        
        return players_needing_action

    def _subscribe_to_events(self):
        """订阅事件"""
        self._event_bus.subscribe(EventType.PLAYER_JOINED, self.handle_player_joined)
        self._event_bus.subscribe(EventType.HAND_ENDED, self.handle_hand_completed)

    def handle_player_joined(self, event: PlayerJoinedEvent):
        """处理玩家加入事件"""
        self.logger.info(f"处理玩家加入事件: 玩家 {event.player_id} 加入游戏 {event.game_id}")

    def handle_game_started(self, event: GameStartedEvent):
        """处理游戏开始事件"""
        self.logger.info(f"处理游戏开始事件: 游戏 {event.game_id} 开始")

    def handle_phase_changed(self, event: PhaseChangedEvent):
        """处理阶段变更事件"""
        self.logger.info(f"处理阶段变更事件: 游戏 {event.game_id} 阶段变为 {event.to_phase}")

    def handle_hand_completed(self, event: HandEndedEvent):
        """
        处理手牌结束事件
        
        Args:
            event (HandEndedEvent): 手牌结束事件
        """
        logger = logging.getLogger(__name__)
        logger.info(f"手牌在游戏 {event.aggregate_id} 中结束. 赢家: {event.data.get('winners')}")
        
        # 可以在这里触发开始新手牌的逻辑，或者由外部调用者决定
        # self.start_new_hand(event.aggregate_id)

    def should_advance_phase_query(self, game_id: str) -> QueryResult:
        """
        [查询型方法] 判断是否应该推进游戏阶段。
        此方法用于替代QueryService中的同名方法，供内部服务(如GameFlowService)使用。
        
        Args:
            game_id: 游戏ID
            
        Returns:
            查询结果，包含布尔值
        """
        try:
            session = self._get_session(game_id)
            context = session.context

            if context.current_phase == GamePhase.FINISHED:
                return QueryResult.success_result(False)

            if context.active_player_id is not None:
                return QueryResult.success_result(False)

            betting_phases = [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]
            if context.current_phase in betting_phases:
                needs_action_players = self._find_players_needing_action(context)
                if needs_action_players:
                    return QueryResult.success_result(False)
                return QueryResult.success_result(True)

            return QueryResult.success_result(True)

        except ValueError as e:
            return QueryResult.failure_result(str(e), error_code="GAME_NOT_FOUND")
        except Exception as e:
            logger.error(f"Error checking if phase should advance for game {game_id}: {e}", exc_info=True)
            return QueryResult.failure_result(f"判断推进阶段失败: {e}", error_code="CHECK_ADVANCE_FAILED")

    def calculate_live_hash(self, game_id: str) -> QueryResult:
        """
        [查询型方法] 计算实时游戏状态的哈希值。
        此方法用于替代QueryService中的同名方法，供内部服务(如GameFlowService)使用。

        Args:
            game_id: 游戏ID

        Returns:
            查询结果，包含状态哈希字符串
        """
        try:
            import hashlib
            import json

            context_result = self.get_live_context(game_id)
            if not context_result.success:
                return context_result

            context = context_result.data
            
            # 为了确保哈希的一致性，我们需要一个稳定的玩家顺序
            player_ids = sorted(context.players.keys())
            
            # 提取关键状态信息
            state_info = {
                'phase': context.current_phase.name,
                'pot_total': context.pot.total_pot,
                'current_bet': context.highest_bet,
                'active_player': context.active_player_id,
                'community_cards': [str(c) for c in context.community_cards],
                'players': {
                    pid: {
                        'chips': context.players[pid].chips,
                        'current_bet': context.players[pid].current_bet,
                        'is_active': context.players[pid].is_active,
                        'is_all_in': context.players[pid].is_all_in,
                        'has_folded': context.players[pid].has_folded,
                    } for pid in player_ids
                }
            }
            
            state_string = json.dumps(state_info, sort_keys=True, default=str)
            return QueryResult.success_result(
                hashlib.md5(state_string.encode()).hexdigest()
            )

        except ValueError as e:
            return QueryResult.failure_result(str(e), error_code="GAME_NOT_FOUND")
        except Exception as e:
            logger.error(f"Error calculating hash for game {game_id}: {e}", exc_info=True)
            return QueryResult.failure_result(f"计算哈希失败: {e}", error_code="CALCULATE_HASH_FAILED") 