"""
状态快照类型定义

定义德州扑克游戏状态快照的不可变数据结构。
"""

from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional
from enum import Enum, auto
import time

from ..state_machine.types import GamePhase
from ..deck.card import Card
from ..chips.chip_transaction import ChipTransaction

__all__ = [
    'SnapshotVersion',
    'PlayerSnapshot', 
    'PotSnapshot',
    'GameStateSnapshot',
    'SnapshotMetadata'
]


class SnapshotVersion(Enum):
    """快照版本枚举"""
    V1_0 = "1.0"
    V1_1 = "1.1"
    CURRENT = V1_1


@dataclass(frozen=True)
class PlayerSnapshot:
    """玩家状态快照"""
    player_id: str
    name: str
    chips: int
    hole_cards: Tuple[Card, ...]  # 手牌，最多2张
    position: int  # 座位位置
    is_active: bool  # 是否在游戏中且未弃牌（包括all-in玩家）
    is_all_in: bool  # 是否全押
    current_bet: int  # 当前轮下注金额
    total_bet_this_hand: int  # 本手牌总下注金额
    last_action: Optional[str] = None  # 最后一次行动
    
    def __post_init__(self):
        """验证玩家快照的有效性"""
        if not self.player_id:
            raise ValueError("player_id不能为空")
        if self.chips < 0:
            raise ValueError("chips不能为负数")
        if len(self.hole_cards) > 2:
            raise ValueError("手牌不能超过2张")
        if self.position < 0:
            raise ValueError("position不能为负数")
        if self.current_bet < 0:
            raise ValueError("current_bet不能为负数")
        if self.total_bet_this_hand < 0:
            raise ValueError("total_bet_this_hand不能为负数")


@dataclass(frozen=True)
class PotSnapshot:
    """奖池状态快照"""
    main_pot: int  # 主池
    side_pots: Tuple[Dict[str, Any], ...]  # 边池列表
    total_pot: int  # 总奖池
    eligible_players: Tuple[str, ...]  # 有资格争夺奖池的玩家
    
    def __post_init__(self):
        """验证奖池快照的有效性"""
        if self.main_pot < 0:
            raise ValueError("main_pot不能为负数")
        if self.total_pot < 0:
            raise ValueError("total_pot不能为负数")
        if self.total_pot < self.main_pot:
            raise ValueError("total_pot不能小于main_pot")


@dataclass(frozen=True)
class SnapshotMetadata:
    """快照元数据"""
    snapshot_id: str
    version: SnapshotVersion
    created_at: float
    game_duration: float  # 游戏持续时间（秒）
    hand_number: int  # 手牌编号
    description: Optional[str] = None
    
    def __post_init__(self):
        """验证快照元数据的有效性"""
        if not self.snapshot_id:
            raise ValueError("snapshot_id不能为空")
        if self.created_at <= 0:
            raise ValueError("created_at必须为正数")
        if self.game_duration < 0:
            raise ValueError("game_duration不能为负数")
        if self.hand_number < 0:
            raise ValueError("hand_number不能为负数")


@dataclass(frozen=True)
class GameStateSnapshot:
    """游戏状态快照"""
    metadata: SnapshotMetadata
    game_id: str
    phase: GamePhase
    players: Tuple[PlayerSnapshot, ...]
    pot: PotSnapshot
    community_cards: Tuple[Card, ...]  # 公共牌，最多5张
    current_bet: int  # 当前轮最高下注
    dealer_position: int  # 庄家位置
    small_blind_position: int  # 小盲位置
    big_blind_position: int  # 大盲位置
    active_player_position: Optional[int] = None  # 当前行动玩家位置
    small_blind_amount: int = 0  # 小盲金额
    big_blind_amount: int = 0  # 大盲金额
    recent_transactions: Tuple[ChipTransaction, ...] = ()  # 最近的筹码交易
    
    def __post_init__(self):
        """验证游戏状态快照的有效性"""
        if not self.game_id:
            raise ValueError("game_id不能为空")
        if len(self.community_cards) > 5:
            raise ValueError("公共牌不能超过5张")
        if self.current_bet < 0:
            raise ValueError("current_bet不能为负数")
        if self.dealer_position < 0:
            raise ValueError("dealer_position不能为负数")
        if self.small_blind_position < 0:
            raise ValueError("small_blind_position不能为负数")
        if self.big_blind_position < 0:
            raise ValueError("big_blind_position不能为负数")
        if self.small_blind_amount < 0:
            raise ValueError("small_blind_amount不能为负数")
        if self.big_blind_amount < 0:
            raise ValueError("big_blind_amount不能为负数")
        if len(self.players) == 0:
            raise ValueError("players不能为空")
        
        # 验证位置的有效性
        max_position = len(self.players) - 1
        if self.dealer_position > max_position:
            raise ValueError(f"dealer_position({self.dealer_position})超出玩家数量范围")
        if self.small_blind_position > max_position:
            raise ValueError(f"small_blind_position({self.small_blind_position})超出玩家数量范围")
        if self.big_blind_position > max_position:
            raise ValueError(f"big_blind_position({self.big_blind_position})超出玩家数量范围")
        if self.active_player_position is not None and self.active_player_position > max_position:
            raise ValueError(f"active_player_position({self.active_player_position})超出玩家数量范围")
    
    @classmethod
    def create_initial_snapshot(cls, game_id: str, players: Tuple[PlayerSnapshot, ...], 
                              small_blind: int, big_blind: int) -> 'GameStateSnapshot':
        """创建初始游戏状态快照"""
        if len(players) < 2:
            raise ValueError("至少需要2个玩家")
        
        # 创建元数据
        timestamp = time.time()
        metadata = SnapshotMetadata(
            snapshot_id=f"snapshot_{game_id}_{int(timestamp * 1000000)}",
            version=SnapshotVersion.CURRENT,
            created_at=timestamp,
            game_duration=0.0,
            hand_number=1,
            description="初始游戏状态"
        )
        
        # 创建初始奖池
        pot = PotSnapshot(
            main_pot=0,
            side_pots=(),
            total_pot=0,
            eligible_players=tuple(p.player_id for p in players)
        )
        
        return cls(
            metadata=metadata,
            game_id=game_id,
            phase=GamePhase.INIT,
            players=players,
            pot=pot,
            community_cards=(),
            current_bet=0,
            dealer_position=0,
            small_blind_position=1 % len(players),
            big_blind_position=2 % len(players),
            small_blind_amount=small_blind,
            big_blind_amount=big_blind
        )
    
    def get_player_by_id(self, player_id: str) -> Optional[PlayerSnapshot]:
        """根据ID获取玩家快照"""
        for player in self.players:
            if player.player_id == player_id:
                return player
        return None
    
    def get_active_players(self) -> Tuple[PlayerSnapshot, ...]:
        """获取活跃玩家列表"""
        return tuple(p for p in self.players if p.is_active)
    
    def get_total_chips(self) -> int:
        """获取所有玩家的筹码总数"""
        return sum(p.chips for p in self.players) + self.pot.total_pot 