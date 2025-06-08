"""
Domain Events - 领域事件定义

该模块定义了德州扑克游戏的领域事件系统基础类型。
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum, auto
import time
import uuid


class EventType(Enum):
    """事件类型枚举"""
    # 游戏生命周期事件
    GAME_STARTED = auto()
    GAME_ENDED = auto()
    HAND_STARTED = auto()
    HAND_ENDED = auto()
    
    # 阶段转换事件
    PHASE_CHANGED = auto()
    
    # 玩家行动事件
    PLAYER_JOINED = auto()
    PLAYER_LEFT = auto()
    PLAYER_ACTION_EXECUTED = auto()
    PLAYER_FOLDED = auto()
    PLAYER_ALL_IN = auto()
    
    # 下注事件
    BET_PLACED = auto()
    RAISE_MADE = auto()
    CALL_MADE = auto()
    CHECK_MADE = auto()
    
    # 发牌事件
    CARDS_DEALT = auto()
    COMMUNITY_CARDS_REVEALED = auto()
    
    # 边池事件
    POT_UPDATED = auto()
    SIDE_POT_CREATED = auto()
    WINNINGS_DISTRIBUTED = auto()
    
    # 错误事件
    INVALID_ACTION_ATTEMPTED = auto()
    RULE_VIOLATION = auto()


@dataclass(frozen=True)
class DomainEvent:
    """
    领域事件基类
    
    所有游戏事件都应该继承此类，确保事件的一致性和可追溯性。
    
    Attributes:
        event_id: 事件唯一标识符
        event_type: 事件类型
        aggregate_id: 聚合根ID（通常是game_id）
        timestamp: 事件发生时间戳
        data: 事件数据
        version: 事件版本号
        correlation_id: 关联ID，用于追踪相关事件
    """
    event_id: str
    event_type: EventType
    aggregate_id: str
    timestamp: float
    data: Dict[str, Any]
    version: int = 1
    correlation_id: Optional[str] = None
    
    @classmethod
    def create(
        cls,
        event_type: EventType,
        aggregate_id: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> DomainEvent:
        """
        创建领域事件的工厂方法
        
        Args:
            event_type: 事件类型
            aggregate_id: 聚合根ID
            data: 事件数据
            correlation_id: 关联ID
            
        Returns:
            DomainEvent: 创建的事件实例
        """
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            aggregate_id=aggregate_id,
            timestamp=time.time(),
            data=data,
            correlation_id=correlation_id
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将事件转换为字典格式，用于序列化
        
        Returns:
            Dict[str, Any]: 事件的字典表示
        """
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.name,
            'aggregate_id': self.aggregate_id,
            'timestamp': self.timestamp,
            'data': self.data,
            'version': self.version,
            'correlation_id': self.correlation_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DomainEvent:
        """
        从字典创建事件实例，用于反序列化
        
        Args:
            data: 事件字典数据
            
        Returns:
            DomainEvent: 事件实例
        """
        return cls(
            event_id=data['event_id'],
            event_type=EventType[data['event_type']],
            aggregate_id=data['aggregate_id'],
            timestamp=data['timestamp'],
            data=data['data'],
            version=data.get('version', 1),
            correlation_id=data.get('correlation_id')
        )


# 具体事件类型定义

@dataclass(frozen=True)
class GameStartedEvent(DomainEvent):
    """游戏开始事件"""
    
    @classmethod
    def create(
        cls,
        game_id: str,
        player_ids: list[str],
        small_blind: int,
        big_blind: int,
        correlation_id: Optional[str] = None
    ) -> GameStartedEvent:
        data = {
            'player_ids': player_ids,
            'small_blind': small_blind,
            'big_blind': big_blind
        }
        base_event = DomainEvent.create(
            EventType.GAME_STARTED,
            game_id,
            data,
            correlation_id
        )
        return cls(**base_event.__dict__)


@dataclass(frozen=True)
class HandStartedEvent(DomainEvent):
    """手牌开始事件"""
    
    @classmethod
    def create(
        cls,
        game_id: str,
        hand_number: int,
        dealer_position: int,
        correlation_id: Optional[str] = None
    ) -> HandStartedEvent:
        data = {
            'hand_number': hand_number,
            'dealer_position': dealer_position
        }
        base_event = DomainEvent.create(
            EventType.HAND_STARTED,
            game_id,
            data,
            correlation_id
        )
        return cls(**base_event.__dict__)


@dataclass(frozen=True)
class PhaseChangedEvent(DomainEvent):
    """阶段转换事件"""
    
    @classmethod
    def create(
        cls,
        game_id: str,
        from_phase: str,
        to_phase: str,
        correlation_id: Optional[str] = None
    ) -> PhaseChangedEvent:
        data = {
            'from_phase': from_phase,
            'to_phase': to_phase
        }
        base_event = DomainEvent.create(
            EventType.PHASE_CHANGED,
            game_id,
            data,
            correlation_id
        )
        return cls(**base_event.__dict__)


@dataclass(frozen=True)
class PlayerActionExecutedEvent(DomainEvent):
    """玩家行动执行事件"""
    
    @classmethod
    def create(
        cls,
        game_id: str,
        player_id: str,
        action_type: str,
        amount: int = 0,
        correlation_id: Optional[str] = None
    ) -> PlayerActionExecutedEvent:
        data = {
            'player_id': player_id,
            'action_type': action_type,
            'amount': amount
        }
        base_event = DomainEvent.create(
            EventType.PLAYER_ACTION_EXECUTED,
            game_id,
            data,
            correlation_id
        )
        return cls(**base_event.__dict__)


@dataclass(frozen=True)
class PotUpdatedEvent(DomainEvent):
    """边池更新事件"""
    
    @classmethod
    def create(
        cls,
        game_id: str,
        total_pot: int,
        side_pots: list[Dict[str, Any]],
        correlation_id: Optional[str] = None
    ) -> PotUpdatedEvent:
        data = {
            'total_pot': total_pot,
            'side_pots': side_pots
        }
        base_event = DomainEvent.create(
            EventType.POT_UPDATED,
            game_id,
            data,
            correlation_id
        )
        return cls(**base_event.__dict__)


@dataclass(frozen=True)
class CardsDealtEvent(DomainEvent):
    """发牌事件"""
    
    @classmethod
    def create(
        cls,
        game_id: str,
        cards_dealt: Dict[str, list[str]],  # player_id -> cards
        correlation_id: Optional[str] = None
    ) -> CardsDealtEvent:
        data = {
            'cards_dealt': cards_dealt
        }
        base_event = DomainEvent.create(
            EventType.CARDS_DEALT,
            game_id,
            data,
            correlation_id
        )
        return cls(**base_event.__dict__)


@dataclass(frozen=True)
class CommunityCardsRevealedEvent(DomainEvent):
    """公共牌揭示事件"""
    
    @classmethod
    def create(
        cls,
        game_id: str,
        revealed_cards: list[str],
        total_community_cards: list[str],
        correlation_id: Optional[str] = None
    ) -> CommunityCardsRevealedEvent:
        data = {
            'revealed_cards': revealed_cards,
            'total_community_cards': total_community_cards
        }
        base_event = DomainEvent.create(
            EventType.COMMUNITY_CARDS_REVEALED,
            game_id,
            data,
            correlation_id
        )
        return cls(**base_event.__dict__)


@dataclass(frozen=True)
class PlayerJoinedEvent(DomainEvent):
    """玩家加入事件"""

    @classmethod
    def create(
        cls,
        game_id: str,
        player_id: str,
        initial_chips: int,
        correlation_id: Optional[str] = None
    ) -> PlayerJoinedEvent:
        data = {
            'player_id': player_id,
            'initial_chips': initial_chips
        }
        base_event = DomainEvent.create(
            EventType.PLAYER_JOINED,
            game_id,
            data,
            correlation_id
        )
        return cls(**base_event.__dict__)


@dataclass(frozen=True)
class HandEndedEvent(DomainEvent):
    """手牌结束事件"""

    @classmethod
    def create(
        cls,
        game_id: str,
        winners: Dict[str, int],  # player_id -> amount won
        pot_distribution: list[Dict[str, Any]],
        correlation_id: Optional[str] = None
    ) -> HandEndedEvent:
        data = {
            'winners': winners,
            'pot_distribution': pot_distribution
        }
        base_event = DomainEvent.create(
            EventType.HAND_ENDED,
            game_id,
            data,
            correlation_id
        )
        return cls(**base_event.__dict__) 