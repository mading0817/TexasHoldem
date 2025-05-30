"""
同步事件总线系统
提供发布-订阅模式的事件处理机制
"""

from typing import List, Dict, Callable, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import logging
from threading import Lock
import uuid

from app_controller.dto_models import GameEvent, GameEventType


# 事件处理器类型定义
EventHandler = Callable[[GameEvent], None]


@dataclass
class EventSubscription:
    """事件订阅信息"""
    subscription_id: str
    handler: EventHandler
    priority: int = 0  # 优先级，数字越大优先级越高
    filter_func: Optional[Callable[[GameEvent], bool]] = None  # 事件过滤函数
    
    def __post_init__(self):
        if not self.subscription_id:
            self.subscription_id = str(uuid.uuid4())


class EventBus:
    """同步事件总线 - 线程安全的事件发布订阅系统"""
    
    def __init__(self, enable_logging: bool = True):
        """
        初始化事件总线
        
        Args:
            enable_logging: 是否启用事件日志
        """
        self._subscribers: Dict[GameEventType, List[EventSubscription]] = defaultdict(list)
        self._global_subscribers: List[EventSubscription] = []  # 全局订阅者（接收所有事件）
        self._event_history: List[GameEvent] = []  # 事件历史记录
        self._lock = Lock()  # 线程安全锁
        self._enable_logging = enable_logging
        self._logger = logging.getLogger(__name__) if enable_logging else None
        
        # 统计信息
        self._stats = {
            'events_published': 0,
            'events_handled': 0,
            'failed_handlers': 0
        }
    
    def subscribe(self, event_type: Union[GameEventType, str], handler: EventHandler, 
                 priority: int = 0, filter_func: Optional[Callable[[GameEvent], bool]] = None) -> str:
        """
        订阅特定类型的事件或所有事件
        
        Args:
            event_type: 事件类型或 '*' 表示订阅所有事件
            handler: 事件处理器函数
            priority: 优先级（数字越大优先级越高）
            filter_func: 事件过滤函数，返回True的事件才会被处理
            
        Returns:
            订阅ID，用于取消订阅
        """
        subscription = EventSubscription(
            subscription_id=str(uuid.uuid4()),
            handler=handler,
            priority=priority,
            filter_func=filter_func
        )
        
        # 处理全局订阅（'*'）
        if event_type == '*':
            with self._lock:
                self._global_subscribers.append(subscription)
                # 按优先级排序（高优先级在前）
                self._global_subscribers.sort(key=lambda s: s.priority, reverse=True)
            
            if self._logger:
                self._logger.debug(f"订阅所有事件: 处理器: {handler.__name__}, 优先级: {priority}")
        else:
            # 确保是有效的枚举类型
            if isinstance(event_type, str):
                # 尝试转换字符串为枚举
                try:
                    event_type = GameEventType[event_type.upper()]
                except KeyError:
                    raise ValueError(f"无效的事件类型: {event_type}")
            
            with self._lock:
                self._subscribers[event_type].append(subscription)
                # 按优先级排序（高优先级在前）
                self._subscribers[event_type].sort(key=lambda s: s.priority, reverse=True)
            
            if self._logger:
                event_type_str = event_type.value if hasattr(event_type, 'value') else str(event_type)
                self._logger.debug(f"订阅事件: {event_type_str}, 处理器: {handler.__name__}, 优先级: {priority}")
        
        return subscription.subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        取消订阅
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            是否成功取消
        """
        with self._lock:
            # 在特定事件类型订阅者中查找
            for event_type, subscriptions in self._subscribers.items():
                for i, sub in enumerate(subscriptions):
                    if sub.subscription_id == subscription_id:
                        del subscriptions[i]
                        if self._logger:
                            event_type_str = event_type.value if hasattr(event_type, 'value') else str(event_type)
                            self._logger.debug(f"取消订阅: {subscription_id} for {event_type_str}")
                        return True
            
            # 在全局订阅者中查找
            for i, sub in enumerate(self._global_subscribers):
                if sub.subscription_id == subscription_id:
                    del self._global_subscribers[i]
                    if self._logger:
                        self._logger.debug(f"取消全局订阅: {subscription_id}")
                    return True
        
        return False
    
    def publish(self, event: GameEvent) -> None:
        """
        发布事件
        
        Args:
            event: 要发布的事件
        """
        with self._lock:
            # 记录事件历史
            self._event_history.append(event)
            # 保持历史记录在合理范围内
            if len(self._event_history) > 1000:
                self._event_history = self._event_history[-500:]
            
            self._stats['events_published'] += 1
        
        if self._logger:
            self._logger.info(f"发布事件: {event.event_type.value} - {event.message}")
        
        # 处理特定类型的订阅者
        handlers_to_call = []
        
        with self._lock:
            # 获取特定事件类型的处理器
            if event.event_type in self._subscribers:
                for subscription in self._subscribers[event.event_type]:
                    if self._should_handle_event(subscription, event):
                        handlers_to_call.append(subscription.handler)
            
            # 获取全局处理器
            for subscription in self._global_subscribers:
                if self._should_handle_event(subscription, event):
                    handlers_to_call.append(subscription.handler)
        
        # 执行处理器（在锁外执行，避免阻塞）
        for handler in handlers_to_call:
            try:
                handler(event)
                self._stats['events_handled'] += 1
            except Exception as e:
                self._stats['failed_handlers'] += 1
                if self._logger:
                    self._logger.error(f"事件处理器执行失败: {handler.__name__}, 错误: {e}")
    
    def _should_handle_event(self, subscription: EventSubscription, event: GameEvent) -> bool:
        """检查是否应该处理事件"""
        if subscription.filter_func:
            try:
                return subscription.filter_func(event)
            except Exception as e:
                if self._logger:
                    self._logger.error(f"事件过滤函数执行失败: {e}")
                return False
        return True
    
    def get_event_history(self, event_type: Optional[GameEventType] = None, 
                         limit: Optional[int] = None) -> List[GameEvent]:
        """
        获取事件历史记录
        
        Args:
            event_type: 过滤事件类型，None表示所有类型
            limit: 限制返回数量，None表示无限制
            
        Returns:
            事件历史列表
        """
        with self._lock:
            history = self._event_history.copy()
        
        # 按类型过滤
        if event_type:
            history = [e for e in history if e.event_type == event_type]
        
        # 限制数量（返回最新的N个）
        if limit:
            history = history[-limit:]
        
        return history
    
    def clear_history(self) -> None:
        """清空事件历史"""
        with self._lock:
            self._event_history.clear()
        
        if self._logger:
            self._logger.info("事件历史已清空")
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        with self._lock:
            return self._stats.copy()
    
    def get_subscription_count(self) -> Dict[str, int]:
        """获取订阅统计"""
        with self._lock:
            stats = {
                'global_subscribers': len(self._global_subscribers)
            }
            for event_type, subscriptions in self._subscribers.items():
                event_type_str = event_type.value if hasattr(event_type, 'value') else str(event_type)
                stats[f'{event_type_str}_subscribers'] = len(subscriptions)
        
        return stats


# 全局事件总线实例
_global_event_bus: Optional[EventBus] = None


def get_global_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def set_global_event_bus(event_bus: EventBus) -> None:
    """设置全局事件总线实例"""
    global _global_event_bus
    _global_event_bus = event_bus


# 事件总线装饰器
def event_handler(event_type: GameEventType, priority: int = 0):
    """
    事件处理器装饰器
    
    Args:
        event_type: 要处理的事件类型
        priority: 处理优先级
    """
    def decorator(func: Callable[[GameEvent], None]):
        # 自动注册到全局事件总线
        bus = get_global_event_bus()
        subscription_id = bus.subscribe(event_type, func, priority)
        
        # 将订阅ID作为函数属性保存，便于调试
        func.subscription_id = subscription_id
        return func
    
    return decorator


# 内置事件处理器示例
class EventLogger:
    """事件日志记录器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.event_bus = get_global_event_bus()
        
        # 注册日志处理器 - 使用 '*' 订阅所有事件
        self.subscription_id = self.event_bus.subscribe(
            event_type='*',
            handler=self._log_event,
            priority=-100  # 低优先级，确保在其他处理器之后执行
        )
    
    def _log_event(self, event: GameEvent) -> None:
        """记录事件日志"""
        self.logger.info(
            f"[{event.timestamp.strftime('%H:%M:%S')}] "
            f"{event.event_type.value}: {event.message}"
        )
        
        if event.affected_seat_ids:
            self.logger.debug(f"  受影响座位: {event.affected_seat_ids}")
        
        if event.data:
            self.logger.debug(f"  事件数据: {event.data}")
    
    def unregister(self) -> None:
        """取消注册日志处理器"""
        self.event_bus.unsubscribe(self.subscription_id)


class EventAggregator:
    """事件聚合器 - 收集和分析事件模式"""
    
    def __init__(self):
        self.event_bus = get_global_event_bus()
        self.aggregated_data: Dict[str, Any] = {}
        
        # 注册聚合处理器
        self.subscription_id = self.event_bus.subscribe_all(
            handler=self._aggregate_event,
            priority=50
        )
    
    def _aggregate_event(self, event: GameEvent) -> None:
        """聚合事件数据"""
        event_type = event.event_type.value
        
        # 初始化计数器
        if event_type not in self.aggregated_data:
            self.aggregated_data[event_type] = {
                'count': 0,
                'first_seen': event.timestamp,
                'last_seen': event.timestamp,
                'affected_seats': set()
            }
        
        # 更新统计
        stats = self.aggregated_data[event_type]
        stats['count'] += 1
        stats['last_seen'] = event.timestamp
        stats['affected_seats'].update(event.affected_seat_ids)
    
    def get_aggregated_stats(self) -> Dict[str, Any]:
        """获取聚合统计数据"""
        # 转换set为list以便序列化
        result = {}
        for event_type, stats in self.aggregated_data.items():
            result[event_type] = {
                'count': stats['count'],
                'first_seen': stats['first_seen'].isoformat(),
                'last_seen': stats['last_seen'].isoformat(),
                'affected_seats': list(stats['affected_seats'])
            }
        return result
    
    def reset_stats(self) -> None:
        """重置聚合统计"""
        self.aggregated_data.clear()
    
    def unregister(self) -> None:
        """取消注册聚合处理器"""
        self.event_bus.unsubscribe(self.subscription_id) 