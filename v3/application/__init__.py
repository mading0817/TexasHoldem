"""
Application Layer - 应用服务层

该层实现CQRS模式，包含命令服务和查询服务。
应用层可以访问核心层，但不能被核心层访问。

Services:
    GameCommandService: 游戏命令服务（状态变更操作）
    GameQueryService: 游戏查询服务（只读操作）

Types:
    CommandResult: 命令执行结果
    QueryResult: 查询结果
    PlayerAction: 玩家行动
    GameStateSnapshot: 游戏状态快照
    PlayerInfo: 玩家信息
    AvailableActions: 可用行动
"""

from .types import (
    ResultStatus,
    CommandResult,
    QueryResult,
    PlayerAction,
    ApplicationError,
    ValidationError,
    BusinessRuleViolationError,
    SystemError,
)

from .command_service import GameCommandService, GameSession
from .query_service import GameQueryService, GameStateSnapshot, PlayerInfo, AvailableActions
from .test_stats_service import TestStatsService, TestStatsSnapshot

__version__ = "3.0.0"

__all__ = [
    # 类型
    "ResultStatus",
    "CommandResult",
    "QueryResult",
    "PlayerAction",
    "ApplicationError",
    "ValidationError",
    "BusinessRuleViolationError",
    "SystemError",
    
    # 服务
    "GameCommandService",
    "GameQueryService",
    "TestStatsService",
    
    # 数据类
    "GameSession",
    "GameStateSnapshot",
    "PlayerInfo",
    "AvailableActions",
    "TestStatsSnapshot",
] 