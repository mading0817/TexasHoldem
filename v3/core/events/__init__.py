"""
Events Module - 领域事件

该模块实现德州扑克的领域事件系统，包括：
- 事件定义和发布
- 事件总线管理
- 事件持久化和重放

Classes:
    DomainEvent: 领域事件基类
    EventBus: 事件总线
    EventHandler: 事件处理器协议
    AsyncEventHandler: 异步事件处理器协议
    
Event Types:
    EventType: 事件类型枚举
    GameStartedEvent: 游戏开始事件
    HandStartedEvent: 手牌开始事件
    PhaseChangedEvent: 阶段转换事件
    PlayerActionExecutedEvent: 玩家行动执行事件
    PotUpdatedEvent: 边池更新事件
    CardsDealtEvent: 发牌事件
    CommunityCardsRevealedEvent: 公共牌揭示事件
    
Functions:
    get_event_bus: 获取全局事件总线实例
    set_event_bus: 设置全局事件总线实例
    create_function_handler: 创建基于函数的事件处理器
    create_async_function_handler: 创建基于异步函数的事件处理器
"""

from .domain_events import (
    EventType,
    DomainEvent,
    GameStartedEvent,
    HandStartedEvent,
    PhaseChangedEvent,
    PlayerActionExecutedEvent,
    PotUpdatedEvent,
    CardsDealtEvent,
    CommunityCardsRevealedEvent,
)

from .event_bus import (
    EventHandler,
    AsyncEventHandler,
    EventBus,
    get_event_bus,
    set_event_bus,
    create_function_handler,
    create_async_function_handler,
)

__all__ = [
    # 事件类型
    "EventType",
    
    # 事件类
    "DomainEvent",
    "GameStartedEvent",
    "HandStartedEvent",
    "PhaseChangedEvent",
    "PlayerActionExecutedEvent",
    "PotUpdatedEvent",
    "CardsDealtEvent",
    "CommunityCardsRevealedEvent",
    
    # 事件总线
    "EventHandler",
    "AsyncEventHandler",
    "EventBus",
    "get_event_bus",
    "set_event_bus",
    
    # 便利函数
    "create_function_handler",
    "create_async_function_handler",
] 