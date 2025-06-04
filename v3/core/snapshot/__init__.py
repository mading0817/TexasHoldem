"""
Snapshot Module - 状态快照

该模块实现德州扑克的状态快照系统，包括：
- 不可变状态快照
- 快照序列化和反序列化
- 快照版本管理

Classes:
    GameStateSnapshot: 游戏状态快照
    PlayerSnapshot: 玩家状态快照
    PotSnapshot: 奖池状态快照
    SnapshotMetadata: 快照元数据
    SnapshotManager: 快照管理器
    SnapshotSerializer: 快照序列化器
"""

from .types import (
    SnapshotVersion,
    PlayerSnapshot,
    PotSnapshot,
    GameStateSnapshot,
    SnapshotMetadata
)
from .snapshot_manager import (
    SnapshotManager,
    SnapshotCreationError,
    SnapshotRestoreError
)
from .serializer import (
    SnapshotSerializer,
    SerializationError,
    DeserializationError
)

__all__ = [
    # 类型定义
    'SnapshotVersion',
    'PlayerSnapshot',
    'PotSnapshot',
    'GameStateSnapshot',
    'SnapshotMetadata',
    
    # 快照管理器
    'SnapshotManager',
    'SnapshotCreationError',
    'SnapshotRestoreError',
    
    # 序列化器
    'SnapshotSerializer',
    'SerializationError',
    'DeserializationError'
] 