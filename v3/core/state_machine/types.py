"""
状态机类型定义

定义状态机相关的基础类型和枚举。
"""

from enum import Enum, auto
from typing import Protocol, Dict, Optional, Any
from dataclasses import dataclass, field
from v3.core.chips.chip_ledger import ChipLedger

__all__ = [
    'GamePhase',
    'GameEvent', 
    'GameContext',
    'PhaseHandler'
]


class GamePhase(Enum):
    """游戏阶段枚举"""
    INIT = auto()
    PRE_FLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()
    SHOWDOWN = auto()
    FINISHED = auto()


@dataclass(frozen=True)
class GameEvent:
    """游戏事件"""
    event_type: str
    data: Dict[str, Any]
    source_phase: GamePhase


@dataclass
class GameContext:
    """游戏上下文，包含游戏状态信息"""
    game_id: str
    current_phase: GamePhase
    players: Dict[str, Any]  # 玩家状态信息 (e.g., is_folded, position), 筹码由chip_ledger管理
    chip_ledger: ChipLedger  # 唯一的筹码真实来源
    community_cards: list
    current_bet: int
    current_hand_bets: Dict[str, int] = field(default_factory=dict)  # 当前手牌的总下注
    small_blind: int = 50  # 小盲注金额
    big_blind: int = 100   # 大盲注金额
    dealer_position: Optional[int] = None  # 庄家位置 (button)
    small_blind_position: Optional[int] = None  # 小盲注位置
    big_blind_position: Optional[int] = None  # 大盲注位置
    active_player_id: Optional[str] = None
    last_event: Optional['GameEvent'] = None
    game_events: list = field(default_factory=list)
    
    def __post_init__(self):
        """验证游戏上下文的有效性"""
        if not self.game_id:
            raise ValueError("game_id不能为空")
        if self.current_bet < 0:
            raise ValueError("current_bet不能为负数")
        if self.small_blind <= 0:
            raise ValueError("small_blind必须大于0")
        if self.big_blind <= 0:
            raise ValueError("big_blind必须大于0")
        if self.big_blind <= self.small_blind:
            raise ValueError("big_blind必须大于small_blind")


class PhaseHandler(Protocol):
    """阶段处理器协议"""
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入阶段时的处理逻辑"""
        ...
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理玩家行动"""
        ...
    
    def on_exit(self, ctx: GameContext) -> None:
        """退出阶段时的处理逻辑"""
        ...
    
    def can_transition_to(self, target_phase: GamePhase, ctx: GameContext) -> bool:
        """检查是否可以转换到目标阶段"""
        ... 