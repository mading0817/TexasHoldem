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
    
    def __init__(self, command_service=None, event_bus: Optional[EventBus] = None):
        """
        初始化查询服务
        
        Args:
            command_service: 命令服务实例，用于访问游戏会话
            event_bus: 事件总线，如果为None则使用全局事件总线
        """
        self._command_service = command_service
        self._event_bus = event_bus or get_event_bus()
    
    def get_game_state(self, game_id: str) -> QueryResult[GameStateSnapshot]:
        """
        获取游戏状态快照
        
        Args:
            game_id: 游戏ID
            
        Returns:
            查询结果，包含游戏状态快照
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
            
            # 创建状态快照
            snapshot = GameStateSnapshot(
                game_id=session.context.game_id,
                current_phase=session.state_machine.current_phase.name,
                players=session.context.players.copy(),
                community_cards=session.context.community_cards.copy(),
                pot_total=session.context.pot_total,
                current_bet=session.context.current_bet,
                active_player_id=session.context.active_player_id,
                timestamp=session.last_updated
            )
            
            return QueryResult.success_result(snapshot)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取游戏状态失败: {str(e)}",
                error_code="GET_GAME_STATE_FAILED"
            )
    
    def get_player_info(self, game_id: str, player_id: str) -> QueryResult[PlayerInfo]:
        """
        获取玩家信息
        
        Args:
            game_id: 游戏ID
            player_id: 玩家ID
            
        Returns:
            查询结果，包含玩家信息
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
            
            # 检查玩家是否存在
            if player_id not in session.context.players:
                return QueryResult.failure_result(
                    f"玩家 {player_id} 不在游戏中",
                    error_code="PLAYER_NOT_IN_GAME"
                )
            
            player_data = session.context.players[player_id]
            player_info = PlayerInfo(
                player_id=player_id,
                chips=player_data.get('chips', 0),
                active=player_data.get('active', False),
                current_bet=player_data.get('current_bet', 0),
                hole_cards=player_data.get('hole_cards', [])
            )
            
            return QueryResult.success_result(player_info)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取玩家信息失败: {str(e)}",
                error_code="GET_PLAYER_INFO_FAILED"
            )
    
    def get_available_actions(self, game_id: str, player_id: str) -> QueryResult[AvailableActions]:
        """
        获取玩家可用行动
        
        Args:
            game_id: 游戏ID
            player_id: 玩家ID
            
        Returns:
            查询结果，包含可用行动
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
            
            # 检查玩家是否存在
            if player_id not in session.context.players:
                return QueryResult.failure_result(
                    f"玩家 {player_id} 不在游戏中",
                    error_code="PLAYER_NOT_IN_GAME"
                )
            
            # 根据当前阶段和玩家状态确定可用行动
            available_actions = self._determine_available_actions(
                session.context, player_id
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
        获取当前阶段信息
        
        Args:
            game_id: 游戏ID
            
        Returns:
            查询结果，包含阶段信息
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
            
            phase_info = {
                'current_phase': session.state_machine.current_phase.name,
                'transition_history': session.state_machine.transition_history,
                'can_advance': self._can_advance_phase(session.context),
                'next_phase': self._get_next_phase(session.state_machine.current_phase)
            }
            
            return QueryResult.success_result(phase_info)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取阶段信息失败: {str(e)}",
                error_code="GET_PHASE_INFO_FAILED"
            )
    
    def _determine_available_actions(self, context: GameContext, player_id: str) -> AvailableActions:
        """
        确定玩家可用行动
        
        Args:
            context: 游戏上下文
            player_id: 玩家ID
            
        Returns:
            可用行动
        """
        player_data = context.players[player_id]
        
        # 基础行动
        actions = []
        
        # 如果玩家还活跃
        if player_data.get('active', False):
            # 根据当前阶段确定可用行动
            if context.current_phase in [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]:
                # 总是可以弃牌
                actions.append('fold')
                
                current_bet = context.current_bet
                player_chips = player_data.get('chips', 0)
                player_current_bet = player_data.get('current_bet', 0)
                
                # 计算需要跟注的金额
                call_amount = max(0, current_bet - player_current_bet)
                
                # 如果当前没有下注，可以过牌或下注
                if current_bet == 0:
                    actions.append('check')
                    if player_chips > 0:
                        actions.append('raise')  # 第一次下注也算加注
                else:
                    # 如果有下注，可以跟注或加注
                    if player_chips >= call_amount:
                        actions.append('call')
                        
                        # 如果还有足够筹码，可以加注
                        # 获取大盲注金额作为最小加注增量
                        big_blind = getattr(context, 'big_blind_amount', 20)  # 默认20
                        min_raise = big_blind
                        if player_chips > call_amount + min_raise:
                            actions.append('raise')
                
                # 如果有筹码，总是可以全押
                if player_chips > 0:
                    actions.append('all_in')
        
        return AvailableActions(
            player_id=player_id,
            actions=actions,
            min_bet=context.current_bet,
            max_bet=player_data.get('chips', 0)
        )
    
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
        检查游戏是否已结束
        
        在德州扑克中，游戏在以下情况结束：
        1. 只剩下1个或0个有筹码的玩家
        2. 游戏被手动终止
        
        Args:
            game_id: 游戏ID
            
        Returns:
            查询结果，包含游戏是否已结束的布尔值
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
            
            # 计算有筹码的玩家数量
            players_with_chips = [
                player_id for player_id, player_data in session.context.players.items()
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
            
        except Exception as e:
            return QueryResult.failure_result(
                f"检查游戏结束状态失败: {str(e)}",
                error_code="CHECK_GAME_OVER_FAILED"
            )
    
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