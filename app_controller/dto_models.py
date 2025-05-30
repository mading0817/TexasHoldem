"""
数据传输对象(DTO)模型
定义应用服务层与其他层之间的数据传输格式
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from datetime import datetime

from core_game_logic.core.enums import ActionType, GamePhase, SeatStatus
from core_game_logic.core.card import Card
from core_game_logic.game.game_state import GameState


@dataclass(frozen=True)
class PlayerSnapshot:
    """玩家状态快照 - 不可变数据对象"""
    seat_id: int
    name: str
    chips: int
    current_bet: int
    status: SeatStatus
    hole_cards_display: str  # 手牌的显示字符串，对其他玩家隐藏
    is_dealer: bool
    is_small_blind: bool
    is_big_blind: bool
    last_action: Optional[str] = None  # 最后执行的动作描述


@dataclass(frozen=True)
class GameStateSnapshot:
    """游戏状态快照 - 完整的只读视图"""
    version: int  # 状态版本号，用于增量更新优化
    phase: GamePhase
    community_cards: Tuple[str, ...]  # 公共牌的字符串表示
    pot: int
    current_bet: int
    current_player_seat: Optional[int]
    dealer_position: int
    small_blind: int
    big_blind: int
    players: Tuple[PlayerSnapshot, ...]  # 所有玩家的快照
    is_betting_round_complete: bool
    timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_game_state(cls, game_state: GameState, version: int, viewer_seat: Optional[int] = None) -> 'GameStateSnapshot':
        """
        从GameState创建快照
        
        Args:
            game_state: 源游戏状态
            version: 状态版本号
            viewer_seat: 观察者座位号，用于隐藏其他玩家手牌
        
        Returns:
            不可变的游戏状态快照
        """
        # 创建玩家快照列表
        player_snapshots = []
        for player in game_state.players:
            # 决定是否隐藏手牌信息
            hide_cards = viewer_seat is not None and player.seat_id != viewer_seat
            hole_cards_display = player.get_hole_cards_str(hidden=hide_cards)
            
            player_snapshot = PlayerSnapshot(
                seat_id=player.seat_id,
                name=player.name,
                chips=player.chips,
                current_bet=player.current_bet,
                status=player.status,
                hole_cards_display=hole_cards_display,
                is_dealer=player.is_dealer,
                is_small_blind=player.is_small_blind,
                is_big_blind=player.is_big_blind,
                last_action=getattr(player, 'last_action_description', None)
            )
            player_snapshots.append(player_snapshot)
        
        return cls(
            version=version,
            phase=game_state.phase,
            community_cards=tuple(card.to_display_str() for card in game_state.community_cards),
            pot=game_state.pot,
            current_bet=game_state.current_bet,
            current_player_seat=game_state.current_player,
            dealer_position=game_state.dealer_position,
            small_blind=game_state.small_blind,
            big_blind=game_state.big_blind,
            players=tuple(player_snapshots),
            is_betting_round_complete=game_state.is_betting_round_complete()
        )
    
    def get_player_snapshot(self, seat_id: int) -> Optional[PlayerSnapshot]:
        """根据座位号获取玩家快照"""
        for player in self.players:
            if player.seat_id == seat_id:
                return player
        return None
    
    def get_active_players(self) -> List[PlayerSnapshot]:
        """获取所有活跃玩家的快照"""
        return [p for p in self.players if p.status == SeatStatus.ACTIVE]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，方便序列化"""
        return {
            'version': self.version,
            'phase': self.phase.name,
            'community_cards': list(self.community_cards),
            'pot': self.pot,
            'current_bet': self.current_bet,
            'current_player_seat': self.current_player_seat,
            'dealer_position': self.dealer_position,
            'small_blind': self.small_blind,
            'big_blind': self.big_blind,
            'players': [
                {
                    'seat_id': p.seat_id,
                    'name': p.name,
                    'chips': p.chips,
                    'current_bet': p.current_bet,
                    'status': p.status.name,
                    'hole_cards_display': p.hole_cards_display,
                    'is_dealer': p.is_dealer,
                    'is_small_blind': p.is_small_blind,
                    'is_big_blind': p.is_big_blind,
                    'last_action': p.last_action
                } for p in self.players
            ],
            'is_betting_round_complete': self.is_betting_round_complete,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class PlayerActionInput:
    """玩家行动输入对象"""
    seat_id: int
    action_type: ActionType
    amount: Optional[int] = None  # 用于下注/加注
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据，如决策时间等
    
    def validate(self) -> bool:
        """验证输入的有效性"""
        if self.seat_id < 0:
            return False
        
        # 下注/加注动作必须有金额
        if self.action_type in [ActionType.BET, ActionType.RAISE]:
            if self.amount is None or self.amount <= 0:
                return False
        
        return True


class ActionResultType(Enum):
    """行动结果类型"""
    SUCCESS = "success"
    INVALID_ACTION = "invalid_action"  
    INSUFFICIENT_CHIPS = "insufficient_chips"
    OUT_OF_TURN = "out_of_turn"
    GAME_ERROR = "game_error"


@dataclass
class ActionResult:
    """行动执行结果"""
    result_type: ActionResultType
    success: bool
    message: str
    events: List['GameEvent'] = field(default_factory=list)
    game_state_changed: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success_result(cls, message: str, events: List['GameEvent'] = None) -> 'ActionResult':
        """创建成功结果"""
        return cls(
            result_type=ActionResultType.SUCCESS,
            success=True,
            message=message,
            events=events or [],
            game_state_changed=True
        )
    
    @classmethod
    def error_result(cls, result_type: ActionResultType, message: str, 
                    game_state_changed: bool = False) -> 'ActionResult':
        """创建错误结果"""
        return cls(
            result_type=result_type,
            success=False,
            message=message,
            events=[],
            game_state_changed=game_state_changed
        )


class GameEventType(Enum):
    """游戏事件类型"""
    PLAYER_ACTION = "player_action"
    PHASE_TRANSITION = "phase_transition"  
    BETTING_ROUND_COMPLETE = "betting_round_complete"
    HAND_COMPLETE = "hand_complete"
    DEALER_ROTATION = "dealer_rotation"
    CARDS_DEALT = "cards_dealt"
    POT_AWARDED = "pot_awarded"
    PLAYER_ELIMINATED = "player_eliminated"
    WARNING = "warning"  # 添加 WARNING 事件类型


@dataclass
class GameEvent:
    """游戏事件对象 - 用于同步事件系统"""
    event_type: GameEventType
    message: str
    affected_seat_ids: List[int] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def player_action_event(cls, seat_id: int, action_type: ActionType, 
                           amount: Optional[int] = None) -> 'GameEvent':
        """创建玩家行动事件"""
        action_desc = action_type.name.lower()
        if amount is not None:
            action_desc += f" {amount}"
        
        return cls(
            event_type=GameEventType.PLAYER_ACTION,
            message=f"玩家 {seat_id} 执行了 {action_desc}",
            affected_seat_ids=[seat_id],
            data={
                'seat_id': seat_id,
                'action_type': action_type.name,
                'amount': amount
            }
        )
    
    @classmethod
    def phase_transition_event(cls, from_phase: GamePhase, to_phase: GamePhase) -> 'GameEvent':
        """创建阶段转换事件"""
        return cls(
            event_type=GameEventType.PHASE_TRANSITION,
            message=f"游戏阶段从 {from_phase.name} 转换到 {to_phase.name}",
            data={
                'from_phase': from_phase.name,
                'to_phase': to_phase.name
            }
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'event_type': self.event_type.value,
            'message': self.message,
            'affected_seat_ids': self.affected_seat_ids,
            'data': self.data,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class PlayerActionRequest:
    """玩家行动请求对象 - 用于高级API回调机制"""
    seat_id: int
    player_name: str
    available_actions: List[ActionType]  # 当前可用的行动类型
    snapshot: GameStateSnapshot  # 当前游戏状态快照
    current_bet_to_call: int  # 需要跟注的金额
    minimum_raise_amount: int  # 最小加注金额
    player_chips: int  # 玩家当前筹码
    
    def format_action_choices(self) -> str:
        """格式化行动选择为用户友好的字符串"""
        choices = []
        for i, action in enumerate(self.available_actions, 1):
            if action == ActionType.FOLD:
                choices.append(f"{i}. 弃牌 (Fold)")
            elif action == ActionType.CHECK:
                choices.append(f"{i}. 过牌 (Check)")
            elif action == ActionType.CALL:
                choices.append(f"{i}. 跟注 (Call {self.current_bet_to_call})")
            elif action == ActionType.BET:
                choices.append(f"{i}. 下注 (Bet, min: {self.minimum_raise_amount})")
            elif action == ActionType.RAISE:
                choices.append(f"{i}. 加注 (Raise, min: {self.minimum_raise_amount})")
            elif action == ActionType.ALL_IN:
                choices.append(f"{i}. 全下 (All-in {self.player_chips})")
        return "\n".join(choices)
    
    def validate_action_choice(self, choice_index: int, amount: Optional[int] = None) -> bool:
        """验证用户选择的行动是否有效"""
        if choice_index < 1 or choice_index > len(self.available_actions):
            return False
        
        action_type = self.available_actions[choice_index - 1]
        
        # 下注/加注需要验证金额
        if action_type in [ActionType.BET, ActionType.RAISE]:
            if amount is None or amount < self.minimum_raise_amount:
                return False
            if amount > self.player_chips:
                return False
        
        return True
    
    def to_action_input(self, choice_index: int, amount: Optional[int] = None) -> PlayerActionInput:
        """将用户选择转换为PlayerActionInput对象"""
        if not self.validate_action_choice(choice_index, amount):
            raise ValueError(f"无效的行动选择: {choice_index}, amount: {amount}")
        
        action_type = self.available_actions[choice_index - 1]
        
        # 特殊处理金额
        final_amount = None
        if action_type in [ActionType.BET, ActionType.RAISE]:
            final_amount = amount
        elif action_type == ActionType.CALL:
            final_amount = self.current_bet_to_call
        elif action_type == ActionType.ALL_IN:
            final_amount = self.player_chips
        
        return PlayerActionInput(
            seat_id=self.seat_id,
            action_type=action_type,
            amount=final_amount
        )


@dataclass
class HandResult:
    """手牌结果对象 - 用于完整手牌流程的结果返回"""
    completed: bool  # 手牌是否正常完成
    winners: List[int]  # 获胜者座位号列表
    pot_distribution: Dict[int, int]  # 底池分配：座位号 -> 获得筹码
    total_pot: int  # 总底池金额
    final_phase: GamePhase  # 最终完成的阶段
    phases_completed: List[GamePhase]  # 已完成的阶段列表
    hand_duration_seconds: float  # 手牌持续时间（秒）
    total_actions: int  # 总行动次数
    events: List[GameEvent] = field(default_factory=list)  # 手牌过程中的事件
    error_message: Optional[str] = None  # 如果未正常完成，记录错误信息
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据
    
    @classmethod
    def successful_completion(cls, winners: List[int], pot_distribution: Dict[int, int], 
                             total_pot: int, phases_completed: List[GamePhase],
                             duration_seconds: float, total_actions: int,
                             events: List[GameEvent] = None) -> 'HandResult':
        """创建成功完成的手牌结果"""
        return cls(
            completed=True,
            winners=winners,
            pot_distribution=pot_distribution,
            total_pot=total_pot,
            final_phase=phases_completed[-1] if phases_completed else GamePhase.PRE_FLOP,
            phases_completed=phases_completed,
            hand_duration_seconds=duration_seconds,
            total_actions=total_actions,
            events=events or []
        )
    
    @classmethod
    def interrupted_completion(cls, error_message: str, final_phase: GamePhase,
                              phases_completed: List[GamePhase], duration_seconds: float,
                              total_actions: int, events: List[GameEvent] = None) -> 'HandResult':
        """创建中断的手牌结果"""
        return cls(
            completed=False,
            winners=[],
            pot_distribution={},
            total_pot=0,
            final_phase=final_phase,
            phases_completed=phases_completed,
            hand_duration_seconds=duration_seconds,
            total_actions=total_actions,
            events=events or [],
            error_message=error_message
        )
    
    def format_summary(self) -> str:
        """格式化手牌结果摘要"""
        if not self.completed:
            return f"手牌中断: {self.error_message}\n" \
                   f"完成阶段: {[p.name for p in self.phases_completed]}\n" \
                   f"持续时间: {self.hand_duration_seconds:.2f}秒"
        
        winner_info = f"获胜者: {self.winners}" if len(self.winners) == 1 else f"平分获胜者: {self.winners}"
        pot_info = "\n".join([f"座位{seat}: +{amount}筹码" for seat, amount in self.pot_distribution.items()])
        
        return f"{winner_info}\n" \
               f"总底池: {self.total_pot}\n" \
               f"筹码分配:\n{pot_info}\n" \
               f"完成阶段: {self.final_phase.name}\n" \
               f"总行动数: {self.total_actions}\n" \
               f"持续时间: {self.hand_duration_seconds:.2f}秒"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，方便序列化"""
        return {
            'completed': self.completed,
            'winners': self.winners,
            'pot_distribution': self.pot_distribution,
            'total_pot': self.total_pot,
            'final_phase': self.final_phase.name,
            'phases_completed': [p.name for p in self.phases_completed],
            'hand_duration_seconds': self.hand_duration_seconds,
            'total_actions': self.total_actions,
            'events': [event.to_dict() for event in self.events],
            'error_message': self.error_message,
            'metadata': self.metadata
        } 