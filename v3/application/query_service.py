"""
Game Query Service - 游戏查询服务

处理所有游戏只读操作，遵循CQRS模式。
查询服务负责：
- 获取游戏状态
- 查询玩家信息
- 获取可用行动
- 查询游戏历史
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from .types import QueryResult
from ..core.state_machine import GamePhase, GameContext
from ..core.events import EventBus, get_event_bus, DomainEvent


@dataclass(frozen=True)
class GameStateSnapshot:
    """游戏状态快照"""
    game_id: str
    current_phase: str
    players: Dict[str, Any]
    community_cards: List[Any]
    pot_total: int
    current_bet: int
    active_player_id: Optional[str]
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


@dataclass(frozen=True)
class PlayerInfo:
    """玩家信息"""
    player_id: str
    chips: int
    active: bool
    current_bet: int = 0
    hole_cards: List[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


@dataclass(frozen=True)
class AvailableActions:
    """可用行动"""
    player_id: str
    actions: List[str]
    min_bet: int = 0
    max_bet: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


class GameQueryService:
    """游戏查询服务"""
    
    def __init__(self, command_service=None, event_bus: Optional[EventBus] = None, 
                 config_service=None):
        """
        初始化查询服务（PLAN 37：注入ConfigService）
        
        Args:
            command_service: 命令服务实例，用于访问游戏会话
            event_bus: 事件总线，如果为None则使用全局事件总线
            config_service: 配置服务，如果为None则创建新实例
        """
        self._command_service = command_service
        self._event_bus = event_bus or get_event_bus()
        
        # PLAN 37: 依赖注入ConfigService
        if config_service is None:
            from .config_service import ConfigService
            config_service = ConfigService()
        self._config_service = config_service
    
    def get_game_state(self, game_id: str) -> QueryResult[GameStateSnapshot]:
        """
        获取游戏状态快照 (PLAN 40: 使用快照接口)
        
        Args:
            game_id: 游戏ID
            
        Returns:
            查询结果，包含游戏状态快照
        """
        if self._command_service is None:
            return QueryResult.failure_result(
                "命令服务未初始化",
                error_code="COMMAND_SERVICE_NOT_INITIALIZED"
            )
        
        # PLAN 40: 使用命令服务的快照接口而不是直接访问session
        return self._command_service.get_game_state_snapshot(game_id)
    
    def get_player_info(self, game_id: str, player_id: str) -> QueryResult[PlayerInfo]:
        """
        获取玩家信息 (PLAN 40: 使用快照接口)
        
        Args:
            game_id: 游戏ID
            player_id: 玩家ID
            
        Returns:
            查询结果，包含玩家信息
        """
        if self._command_service is None:
            return QueryResult.failure_result(
                "命令服务未初始化",
                error_code="COMMAND_SERVICE_NOT_INITIALIZED"
            )
        
        # PLAN 40: 使用快照接口获取游戏状态
        snapshot_result = self._command_service.get_game_state_snapshot(game_id)
        if not snapshot_result.success:
            return QueryResult.failure_result(
                snapshot_result.message,
                error_code=snapshot_result.error_code
            )
        
        snapshot = snapshot_result.data
        
        # 检查玩家是否存在
        if player_id not in snapshot.players:
            return QueryResult.failure_result(
                f"玩家 {player_id} 不在游戏中",
                error_code="PLAYER_NOT_IN_GAME"
            )
        
        player_data = snapshot.players[player_id]
        player_info = PlayerInfo(
            player_id=player_id,
            chips=player_data.get('chips', 0),
            active=player_data.get('active', False),
            current_bet=player_data.get('current_bet', 0),
            hole_cards=player_data.get('hole_cards', [])
        )
        
        return QueryResult.success_result(player_info)
    
    def get_available_actions(self, game_id: str, player_id: str) -> QueryResult[AvailableActions]:
        """
        获取玩家可用行动 (PLAN 44: 使用核心层逻辑)
        
        Args:
            game_id: 游戏ID
            player_id: 玩家ID
            
        Returns:
            查询结果，包含可用行动
        """
        if self._command_service is None:
            return QueryResult.failure_result(
                "命令服务未初始化",
                error_code="COMMAND_SERVICE_NOT_INITIALIZED"
            )
        
        try:
            # PLAN 40: 使用快照接口获取游戏状态
            snapshot_result = self._command_service.get_game_state_snapshot(game_id)
            if not snapshot_result.success:
                return QueryResult.failure_result(
                    snapshot_result.message,
                    error_code=snapshot_result.error_code
                )
            
            snapshot = snapshot_result.data
            
            # 检查玩家是否存在
            if player_id not in snapshot.players:
                return QueryResult.failure_result(
                    f"玩家 {player_id} 不在游戏中",
                    error_code="PLAYER_NOT_IN_GAME"
                )
            # PLAN 44: 使用核心层逻辑确定可用行动
            from ..core.state_machine import GameContext, GamePhase
            from ..core.rules import determine_permissible_actions
            
            # 构建GameContext用于核心层逻辑
            # 需要将快照中的阶段字符串转换为枚举
            current_phase_enum = None
            for phase in GamePhase:
                if phase.name == snapshot.current_phase:
                    current_phase_enum = phase
                    break
            
            if current_phase_enum is None:
                return QueryResult.failure_result(
                    f"无效的游戏阶段: {snapshot.current_phase}",
                    error_code="INVALID_GAME_PHASE"
                )
            
            game_context = GameContext(
                game_id=snapshot.game_id,
                current_phase=current_phase_enum,
                players=snapshot.players,
                community_cards=snapshot.community_cards,
                pot_total=snapshot.pot_total,
                current_bet=snapshot.current_bet,
                active_player_id=snapshot.active_player_id
            )
            
            # 调用核心层逻辑获取可用行动
            core_actions_data = determine_permissible_actions(game_context, player_id)
            
            # 转换为应用层DTO
            available_actions = AvailableActions(
                player_id=player_id,
                actions=core_actions_data.get_action_types_as_strings(),
                min_bet=core_actions_data.constraints.min_call_amount,
                max_bet=core_actions_data.constraints.max_raise_amount
            )
            
            return QueryResult.success_result(available_actions)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取可用行动失败: {str(e)}",
                error_code="GET_AVAILABLE_ACTIONS_FAILED"
            )
    
    def get_game_list(self) -> QueryResult[List[str]]:
        """
        获取活跃游戏列表
        
        Returns:
            查询结果，包含游戏ID列表
        """
        try:
            if self._command_service is None:
                return QueryResult.failure_result(
                    "命令服务未初始化",
                    error_code="COMMAND_SERVICE_NOT_INITIALIZED"
                )
            
            game_list = self._command_service.get_active_games()
            return QueryResult.success_result(game_list)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取游戏列表失败: {str(e)}",
                error_code="GET_GAME_LIST_FAILED"
            )
    
    def get_game_history(self, game_id: str, limit: int = 50) -> QueryResult[List[Dict[str, Any]]]:
        """
        获取游戏历史事件
        
        Args:
            game_id: 游戏ID
            limit: 返回事件数量限制
            
        Returns:
            查询结果，包含历史事件列表
        """
        try:
            # 从事件总线获取历史事件
            history = self._event_bus.get_event_history()
            
            # 过滤指定游戏的事件
            game_events = [
                {
                    'event_id': event.event_id,
                    'event_type': event.event_type.name,
                    'timestamp': event.timestamp,
                    'data': event.data
                }
                for event in history
                if event.aggregate_id == game_id
            ]
            
            # 按时间戳倒序排列，取最新的limit条
            game_events.sort(key=lambda x: x['timestamp'], reverse=True)
            game_events = game_events[:limit]
            
            return QueryResult.success_result(game_events)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取游戏历史失败: {str(e)}",
                error_code="GET_GAME_HISTORY_FAILED"
            )
    
    def get_phase_info(self, game_id: str) -> QueryResult[Dict[str, Any]]:
        """
        获取当前阶段信息 (PLAN 40: 使用快照接口)
        
        Args:
            game_id: 游戏ID
            
        Returns:
            查询结果，包含阶段信息
        """
        if self._command_service is None:
            return QueryResult.failure_result(
                "命令服务未初始化",
                error_code="COMMAND_SERVICE_NOT_INITIALIZED"
            )
        
        # PLAN 40: 使用快照接口获取游戏状态
        snapshot_result = self._command_service.get_game_state_snapshot(game_id)
        if not snapshot_result.success:
            return QueryResult.failure_result(
                snapshot_result.message,
                error_code=snapshot_result.error_code
            )
        
        snapshot = snapshot_result.data
        
        # 临时：基于快照信息构建阶段信息
        # TODO: 在PLAN 43中将部分逻辑移到core层
        from ..core.state_machine import GamePhase
        current_phase_enum = None
        for phase in GamePhase:
            if phase.name == snapshot.current_phase:
                current_phase_enum = phase
                break
        
        phase_info = {
            'current_phase': snapshot.current_phase,
            'transition_history': [],  # 快照中暂无此信息
            'can_advance': False,  # 临时简化，TODO: 在PLAN 43中实现
            'next_phase': self._get_next_phase(current_phase_enum) if current_phase_enum else None,
            'community_cards': snapshot.community_cards,
            'pot_total': snapshot.pot_total
        }
        
        return QueryResult.success_result(phase_info)
    

    def calculate_random_raise_amount(self, game_id: str, player_id: str, 
                                    min_ratio: float = 0.25, max_ratio: float = 2.0) -> QueryResult[int]:
        """
        为随机AI计算符合规则的加注金额
        
        Args:
            game_id: 游戏ID
            player_id: 玩家ID
            min_ratio: 相对于底池的最小下注比例
            max_ratio: 相对于底池的最大下注比例
            
        Returns:
            查询结果，包含符合规则的加注金额
        """
        try:
            import random
            
            if self._command_service is None:
                return QueryResult.failure_result(
                    "命令服务未初始化",
                    error_code="COMMAND_SERVICE_NOT_INITIALIZED"
                )
            
            # 获取游戏会话
            session = self._command_service._get_session(game_id)
            if session is None:
                return QueryResult.failure_result(
                    f"游戏 {game_id} 不存在",
                    error_code="GAME_NOT_FOUND"
                )
            
            # 检查玩家是否存在
            if player_id not in session.context.players:
                return QueryResult.failure_result(
                    f"玩家 {player_id} 不在游戏中",
                    error_code="PLAYER_NOT_IN_GAME"
                )
            
            player_data = session.context.players[player_id]
            current_bet = session.context.current_bet
            player_chips = player_data.get('chips', 0)
            player_current_bet = player_data.get('current_bet', 0)
            pot_total = session.context.pot_total
            big_blind = getattr(session.context, 'big_blind_amount', 20)
            
            # 计算加注范围
            min_raise_amount = current_bet + big_blind
            max_raise_amount = player_current_bet + player_chips
            
            if min_raise_amount > max_raise_amount:
                return QueryResult.failure_result(
                    "玩家筹码不足以进行加注",
                    error_code="INSUFFICIENT_CHIPS_FOR_RAISE"
                )
            
            # 基于底池大小计算期望范围
            desired_min = max(min_raise_amount, int(pot_total * min_ratio))
            desired_max = min(max_raise_amount, int(pot_total * max_ratio))
            
            # 确保范围有效
            if desired_min > desired_max:
                desired_min = min_raise_amount
                desired_max = max_raise_amount
            
            # 调整到5BB增量的倍数
            increment = 5 * big_blind
            desired_min = ((desired_min + increment - 1) // increment) * increment
            desired_max = ((desired_max + increment - 1) // increment) * increment
            
            # 确保在有效范围内
            desired_min = max(desired_min, min_raise_amount)
            desired_max = min(desired_max, max_raise_amount)
            
            if desired_min > desired_max:
                amount = min_raise_amount
            else:
                # 生成5BB增量的候选金额
                candidates = []
                current = desired_min
                while current <= desired_max:
                    if current >= min_raise_amount and current <= max_raise_amount:
                        candidates.append(current)
                    current += increment
                
                if not candidates:
                    amount = min_raise_amount
                else:
                    amount = random.choice(candidates)
            
            return QueryResult.success_result(amount)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"计算随机加注金额失败: {str(e)}",
                error_code="CALCULATE_RANDOM_RAISE_FAILED"
            )
    
    def make_ai_decision(self, game_id: str, player_id: str, 
                        ai_config: Optional[Dict[str, Any]] = None) -> QueryResult[Dict[str, Any]]:
        """
        为指定玩家生成AI决策（遵循CQRS模式的统一入口）
        
        Args:
            game_id: 游戏ID
            player_id: 玩家ID
            ai_config: AI配置参数（如概率权重等）
            
        Returns:
            查询结果，包含AI决策信息 {action_type: str, amount: int, reasoning: str}
        """
        try:
            import random
            
            # 获取可用行动
            available_actions_result = self.get_available_actions(game_id, player_id)
            if not available_actions_result.success:
                return QueryResult.failure_result(
                    f"无法获取玩家 {player_id} 的可用行动: {available_actions_result.message}",
                    error_code="CANNOT_GET_AVAILABLE_ACTIONS"
                )
            
            available_actions = available_actions_result.data.actions
            if not available_actions:
                return QueryResult.success_result({
                    'action_type': 'fold',
                    'amount': 0,
                    'reasoning': '无可用行动，默认弃牌'
                })
            
            # 应用AI决策概率（可配置）
            if ai_config is None:
                ai_config = {}
            
            # 设置默认概率权重
            action_weights = {
                'fold': ai_config.get('fold_weight', 0.15),
                'check': ai_config.get('check_weight', 0.35),
                'call': ai_config.get('call_weight', 0.35),
                'raise': ai_config.get('raise_weight', 0.125),
                'all_in': ai_config.get('all_in_weight', 0.025)
            }
            
            # 筛选可用行动及其权重
            available_weights = {action: action_weights.get(action, 0.1) 
                               for action in available_actions}
            
            # 归一化权重
            total_weight = sum(available_weights.values())
            if total_weight > 0:
                normalized_weights = {action: weight / total_weight 
                                    for action, weight in available_weights.items()}
            else:
                # 如果权重全为0，使用均匀分布
                normalized_weights = {action: 1.0 / len(available_actions) 
                                    for action in available_actions}
            
            # 使用加权随机选择
            actions = list(normalized_weights.keys())
            weights = list(normalized_weights.values())
            chosen_action = random.choices(actions, weights=weights)[0]
            
            # 计算行动金额
            amount = 0
            reasoning = f"概率选择行动: {chosen_action}"
            
            if chosen_action in ['fold', 'check']:
                amount = 0
            elif chosen_action == 'call':
                amount = available_actions_result.data.min_bet
                reasoning += f", 跟注金额: {amount}"
            elif chosen_action == 'raise':
                # 使用现有的随机加注金额计算
                min_ratio = ai_config.get('min_bet_ratio', 0.3)
                max_ratio = ai_config.get('max_bet_ratio', 0.7)
                raise_result = self.calculate_random_raise_amount(game_id, player_id, min_ratio, max_ratio)
                if raise_result.success:
                    amount = raise_result.data
                    reasoning += f", 加注金额: {amount}"
                else:
                    # 回退到跟注
                    chosen_action = 'call'
                    amount = available_actions_result.data.min_bet
                    reasoning = f"加注失败，回退到跟注: {amount}"
            elif chosen_action == 'all_in':
                # 获取玩家筹码作为all-in金额
                game_state_result = self.get_game_state(game_id)
                if game_state_result.success:
                    player_data = game_state_result.data.players.get(player_id, {})
                    amount = player_data.get('chips', 0)
                    reasoning += f", 全押金额: {amount}"
                else:
                    # 回退到弃牌
                    chosen_action = 'fold'
                    amount = 0
                    reasoning = "无法获取玩家筹码，回退到弃牌"
            
            return QueryResult.success_result({
                'action_type': chosen_action,
                'amount': amount,
                'reasoning': reasoning
            })
            
        except Exception as e:
            return QueryResult.failure_result(
                f"生成AI决策失败: {str(e)}",
                error_code="AI_DECISION_FAILED"
            )
    
    def _can_advance_phase(self, context: GameContext) -> bool:
        """
        检查是否可以推进阶段
        
        Args:
            context: 游戏上下文
            
        Returns:
            是否可以推进
        """
        # 简化的逻辑：如果所有活跃玩家都已行动，则可以推进
        active_players = [
            pid for pid, data in context.players.items()
            if data.get('active', False)
        ]
        
        # 至少需要2个活跃玩家
        return len(active_players) >= 2
    
    def _get_next_phase(self, current_phase: GamePhase) -> Optional[str]:
        """
        获取下一个阶段
        
        Args:
            current_phase: 当前阶段
            
        Returns:
            下一个阶段名称
        """
        phase_order = [
            GamePhase.INIT,
            GamePhase.PRE_FLOP,
            GamePhase.FLOP,
            GamePhase.TURN,
            GamePhase.RIVER,
            GamePhase.SHOWDOWN,
            GamePhase.FINISHED
        ]
        
        try:
            current_index = phase_order.index(current_phase)
            if current_index < len(phase_order) - 1:
                return phase_order[current_index + 1].name
        except (ValueError, IndexError):
            pass
        
        return None
    
    def is_game_over(self, game_id: str) -> QueryResult[bool]:
        """
        检查游戏是否已结束 (PLAN 40: 使用快照接口)
        
        在德州扑克中，游戏在以下情况结束：
        1. 只剩下1个或0个有筹码的玩家
        2. 游戏被手动终止
        
        Args:
            game_id: 游戏ID
            
        Returns:
            查询结果，包含游戏是否已结束的布尔值
        """
        if self._command_service is None:
            return QueryResult.failure_result(
                "命令服务未初始化",
                error_code="COMMAND_SERVICE_NOT_INITIALIZED"
            )
        
        # PLAN 40: 使用快照接口获取游戏状态
        snapshot_result = self._command_service.get_game_state_snapshot(game_id)
        if not snapshot_result.success:
            return QueryResult.failure_result(
                snapshot_result.message,
                error_code=snapshot_result.error_code
            )
        
        snapshot = snapshot_result.data
        
        # 检查是否已经是FINISHED阶段
        if snapshot.current_phase == "FINISHED":
            return QueryResult.success_result(True)
        
        # 计算有筹码的玩家数量
        players_with_chips = [
            player_id for player_id, player_data in snapshot.players.items()
            if player_data.get('chips', 0) > 0
        ]
        
        # 如果少于2个玩家有筹码，游戏结束
        game_over = len(players_with_chips) < 2
        
        result = QueryResult.success_result(game_over)
        # 手动设置额外数据
        result.__dict__['data_details'] = {
            'players_with_chips_count': len(players_with_chips),
            'players_with_chips': players_with_chips,
            'reason': 'insufficient_players' if game_over else 'ongoing'
        }
        return result
    
    def get_game_winner(self, game_id: str) -> QueryResult[Optional[str]]:
        """
        获取游戏获胜者
        
        Args:
            game_id: 游戏ID
            
        Returns:
            查询结果，包含获胜者ID（如果游戏未结束则返回None）
        """
        try:
            # 首先检查游戏是否结束
            game_over_result = self.is_game_over(game_id)
            if not game_over_result.success:
                return QueryResult.failure_result(
                    game_over_result.message,
                    error_code=game_over_result.error_code
                )
            
            if not game_over_result.data:
                # 游戏未结束，没有获胜者
                result = QueryResult.success_result(None)
                result.__dict__['data_details'] = {'reason': 'game_not_over'}
                return result
            
            # 获取游戏会话
            session = self._command_service._get_session(game_id)
            if session is None:
                return QueryResult.failure_result(
                    f"游戏 {game_id} 不存在",
                    error_code="GAME_NOT_FOUND"
                )
            
            # 找到最后一个有筹码的玩家
            players_with_chips = [
                (player_id, player_data.get('chips', 0))
                for player_id, player_data in session.context.players.items()
                if player_data.get('chips', 0) > 0
            ]
            
            if len(players_with_chips) == 1:
                winner_id = players_with_chips[0][0]
                winner_chips = players_with_chips[0][1]
                result = QueryResult.success_result(winner_id)
                result.__dict__['data_details'] = {
                    'winner_chips': winner_chips,
                    'reason': 'last_player_standing'
                }
                return result
            elif len(players_with_chips) == 0:
                # 所有玩家都没有筹码，这种情况不应该发生
                result = QueryResult.success_result(None)
                result.__dict__['data_details'] = {'reason': 'no_players_with_chips'}
                return result
            else:
                # 多个玩家有筹码，游戏未结束
                result = QueryResult.success_result(None)
                result.__dict__['data_details'] = {'reason': 'multiple_players_remaining'}
                return result
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取游戏获胜者失败: {str(e)}",
                error_code="GET_GAME_WINNER_FAILED"
            )
    
    def should_advance_phase(self, game_id: str) -> QueryResult[bool]:
        """
        判断是否应该推进游戏阶段
        
        Args:
            game_id: 游戏ID
            
        Returns:
            查询结果，包含是否应该推进阶段的布尔值
        """
        try:
            if self._command_service is None:
                return QueryResult.failure_result(
                    "命令服务未初始化",
                    error_code="COMMAND_SERVICE_NOT_INITIALIZED"
                )
            
            # 获取游戏会话
            session = self._command_service._get_session(game_id)
            if session is None:
                return QueryResult.failure_result(
                    f"游戏 {game_id} 不存在",
                    error_code="GAME_NOT_FOUND"
                )
            
            # 如果已经是FINISHED阶段，不需要推进
            if session.state_machine.current_phase.name == "FINISHED":
                return QueryResult.success_result(False)
            
            # 检查是否有活跃玩家
            active_player_id = session.context.active_player_id
            
            # 如果有活跃玩家，不推进阶段
            if active_player_id is not None:
                return QueryResult.success_result(False)
            
            # 检查是否所有玩家都已行动完毕
            all_action_complete_result = self.all_players_action_complete(game_id)
            if not all_action_complete_result.success:
                return QueryResult.failure_result(
                    all_action_complete_result.message,
                    error_code=all_action_complete_result.error_code
                )
            
            should_advance = all_action_complete_result.data
            return QueryResult.success_result(should_advance)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"判断是否推进阶段失败: {str(e)}",
                error_code="SHOULD_ADVANCE_PHASE_FAILED"
            )
    
    def all_players_action_complete(self, game_id: str) -> QueryResult[bool]:
        """
        检查是否所有玩家都已完成行动
        
        Args:
            game_id: 游戏ID
            
        Returns:
            查询结果，包含所有玩家是否都已完成行动的布尔值
        """
        try:
            if self._command_service is None:
                return QueryResult.failure_result(
                    "命令服务未初始化",
                    error_code="COMMAND_SERVICE_NOT_INITIALIZED"
                )
            
            # 获取游戏会话
            session = self._command_service._get_session(game_id)
            if session is None:
                return QueryResult.failure_result(
                    f"游戏 {game_id} 不存在",
                    error_code="GAME_NOT_FOUND"
                )
            
            current_phase = session.state_machine.current_phase.name
            
            # 如果是FINISHED阶段，行动已完成
            if current_phase == "FINISHED":
                return QueryResult.success_result(True)
            
            # 检查是否有活跃玩家
            active_player_id = session.context.active_player_id
            if active_player_id is not None:
                return QueryResult.success_result(False)  # 还有活跃玩家，行动未完成
            
            # 检查是否是需要玩家行动的阶段
            betting_phases = ["PRE_FLOP", "FLOP", "TURN", "RIVER"]
            if current_phase in betting_phases:
                # 在下注阶段，需要更严格地检查是否所有玩家都已行动
                # 使用CommandService的内部方法检查是否还有玩家需要行动
                needs_action = self._command_service._find_players_needing_action(session.context)
                
                # 如果还有玩家需要行动，则行动未完成
                if needs_action:
                    return QueryResult.success_result(False)
                
                # 所有玩家都已行动完毕
                return QueryResult.success_result(True)
            
            # 其他阶段（如SHOWDOWN），如果没有活跃玩家，认为可以推进
            return QueryResult.success_result(True)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"检查玩家行动完成状态失败: {str(e)}",
                error_code="ALL_PLAYERS_ACTION_COMPLETE_FAILED"
            )
    
    def get_game_rules_config(self, game_id: str, profile: str = "default") -> QueryResult[Dict[str, Any]]:
        """
        获取游戏规则配置 (通过ConfigService)
        
        Args:
            game_id: 游戏ID  
            profile: 配置配置文件名
            
        Returns:
            查询结果，包含游戏规则配置
        """
        try:
            # 使用注入的ConfigService获取配置
            from .config_service import ConfigType
            
            config_result = self._config_service.get_merged_config(
                ConfigType.GAME_RULES, profile
            )
            
            if config_result.success:
                # 如果有游戏会话，用会话中的实际值覆盖配置
                if self._command_service is not None:
                    session = self._command_service._get_session(game_id)
                    if session is not None:
                        config_result.data.update({
                            'small_blind': session.context.small_blind,
                            'big_blind': session.context.big_blind
                        })
                
                return config_result
            else:
                return QueryResult.failure_result(
                    f"获取游戏规则配置失败: {config_result.message}",
                    error_code="GET_GAME_RULES_CONFIG_FAILED"
                )
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取游戏规则配置失败: {str(e)}",
                error_code="GET_GAME_RULES_CONFIG_FAILED"
            )

    def get_ai_config(self, player_id: str = "default") -> QueryResult[Dict[str, Any]]:
        """
        获取AI配置 (通过ConfigService)
        
        Args:
            player_id: 玩家ID，用于个性化配置 (default, aggressive, conservative)
            
        Returns:
            查询结果，包含AI配置
        """
        try:
            # 使用注入的ConfigService获取配置
            from .config_service import ConfigType
            
            # 根据player_id选择配置配置文件
            profile = "default"
            if player_id in ["aggressive", "conservative"]:
                profile = player_id
            
            config_result = self._config_service.get_merged_config(
                ConfigType.AI_DECISION, profile
            )
            
            return config_result
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取AI配置失败: {str(e)}",
                error_code="GET_AI_CONFIG_FAILED"
            )

    def get_ui_test_config(self, test_type: str = "ultimate") -> QueryResult[Dict[str, Any]]:
        """
        获取UI测试配置
        
        Args:
            test_type: 测试类型 (ultimate, quick, stress等)
            
        Returns:
            查询结果，包含UI测试配置
        """
        try:
            # 使用注入的ConfigService获取配置
            from .config_service import ConfigType
            
            config_result = self._config_service.get_merged_config(
                ConfigType.UI_TEST, test_type
            )
            
            return config_result
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取UI测试配置失败: {str(e)}",
                error_code="GET_UI_TEST_CONFIG_FAILED"
            )

    def calculate_game_state_hash(self, game_id: str) -> QueryResult[str]:
        """
        计算游戏状态哈希值
        
        Args:
            game_id: 游戏ID
            
        Returns:
            查询结果，包含状态哈希值
        """
        try:
            import hashlib
            import json
            
            # 获取游戏状态
            state_result = self.get_game_state(game_id)
            if not state_result.success:
                return QueryResult.failure_result(
                    f"无法获取游戏状态: {state_result.message}",
                    error_code=state_result.error_code
                )
            
            game_state = state_result.data
            
            # 提取关键状态信息
            state_info = {
                'phase': game_state.current_phase,
                'pot_total': game_state.pot_total,
                'current_bet': game_state.current_bet,
                'active_player': game_state.active_player_id,
                'community_cards_count': len(game_state.community_cards),
            }
            
            # 添加玩家状态信息
            player_states = {}
            for player_id, player_data in game_state.players.items():
                player_states[player_id] = {
                    'chips': player_data.get('chips', 0),
                    'current_bet': player_data.get('current_bet', 0),
                    'active': player_data.get('active', False),
                    'status': player_data.get('status', 'unknown')
                }
            
            state_info['players'] = player_states
            
            # 计算哈希
            state_json = json.dumps(state_info, sort_keys=True)
            state_hash = hashlib.md5(state_json.encode('utf-8')).hexdigest()[:12]
            
            return QueryResult.success_result(state_hash)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"计算状态哈希失败: {str(e)}",
                error_code="CALCULATE_STATE_HASH_FAILED"
            )

    # PLAN 33: 移除验证逻辑 - validate_player_action_rules方法已删除
    # 验证不是查询服务的职责，已移至ValidationService 