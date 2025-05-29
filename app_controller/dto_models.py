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