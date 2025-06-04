"""
Event Bus - 事件总线系统

该模块实现了德州扑克游戏的事件总线，负责事件的发布、订阅和分发。
"""

from __future__ import annotations
from typing import Protocol, Dict, List, Callable, Any, Optional
from collections import defaultdict
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

from .domain_events import DomainEvent, EventType


class EventHandler(Protocol):
    """事件处理器协议"""
    
    def handle(self, event: DomainEvent) -> None:
        """
        处理事件
        
        Args:
            event: 要处理的领域事件
        """
        ...
    
    def can_handle(self, event_type: EventType) -> bool:
        """
        检查是否能处理指定类型的事件
        
        Args:
            event_type: 事件类型
            
        Returns:
            bool: 是否能处理该事件
        """
        ...


class AsyncEventHandler(Protocol):
    """异步事件处理器协议"""
    
    async def handle_async(self, event: DomainEvent) -> None:
        """
        异步处理事件
        
        Args:
            event: 要处理的领域事件
        """
        ...
    
    def can_handle(self, event_type: EventType) -> bool:
        """
        检查是否能处理指定类型的事件
        
        Args:
            event_type: 事件类型
            
        Returns:
            bool: 是否能处理该事件
        """
        ...


class EventBus:
    """
    事件总线
    
    负责事件的发布、订阅和分发。支持同步和异步事件处理。
    """
    
    def __init__(self, max_workers: int = 4):
        """
        初始化事件总线
        
        Args:
            max_workers: 线程池最大工作线程数
        """
        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._async_handlers: Dict[EventType, List[AsyncEventHandler]] = defaultdict(list)
        self._global_handlers: List[EventHandler] = []
        self._global_async_handlers: List[AsyncEventHandler] = []
        self._event_history: List[DomainEvent] = []
        self._max_history_size = 1000
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """
        订阅特定类型的事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理器
        """
        with self._lock:
            self._handlers[event_type].append(handler)
            self._logger.debug(f"Handler {handler.__class__.__name__} subscribed to {event_type.name}")
    
    def subscribe_async(self, event_type: EventType, handler: AsyncEventHandler) -> None:
        """
        订阅特定类型的事件（异步处理器）
        
        Args:
            event_type: 事件类型
            handler: 异步事件处理器
        """
        with self._lock:
            self._async_handlers[event_type].append(handler)
            self._logger.debug(f"Async handler {handler.__class__.__name__} subscribed to {event_type.name}")
    
    def subscribe_all(self, handler: EventHandler) -> None:
        """
        订阅所有事件
        
        Args:
            handler: 事件处理器
        """
        with self._lock:
            self._global_handlers.append(handler)
            self._logger.debug(f"Handler {handler.__class__.__name__} subscribed to all events")
    
    def subscribe_all_async(self, handler: AsyncEventHandler) -> None:
        """
        订阅所有事件（异步处理器）
        
        Args:
            handler: 异步事件处理器
        """
        with self._lock:
            self._global_async_handlers.append(handler)
            self._logger.debug(f"Async handler {handler.__class__.__name__} subscribed to all events")
    
    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """
        取消订阅特定类型的事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理器
            
        Returns:
            bool: 是否成功取消订阅
        """
        with self._lock:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
                self._logger.debug(f"Handler {handler.__class__.__name__} unsubscribed from {event_type.name}")
                return True
            return False
    
    def publish(self, event: DomainEvent) -> None:
        """
        发布事件（同步）
        
        Args:
            event: 要发布的事件
        """
        with self._lock:
            # 记录事件历史
            self._add_to_history(event)
            
            # 获取处理器
            specific_handlers = self._handlers[event.event_type][:]
            global_handlers = self._global_handlers[:]
            specific_async_handlers = self._async_handlers[event.event_type][:]
            global_async_handlers = self._global_async_handlers[:]
        
        self._logger.debug(f"Publishing event {event.event_type.name} with ID {event.event_id}")
        
        # 同步处理器
        all_sync_handlers = specific_handlers + global_handlers
        for handler in all_sync_handlers:
            try:
                if hasattr(handler, 'can_handle') and not handler.can_handle(event.event_type):
                    continue
                handler.handle(event)
            except Exception as e:
                self._logger.error(f"Error in handler {handler.__class__.__name__}: {e}")
        
        # 异步处理器
        all_async_handlers = specific_async_handlers + global_async_handlers
        if all_async_handlers:
            # 在线程池中运行异步处理器
            self._executor.submit(self._run_async_handlers, all_async_handlers, event)
    
    def publish_async(self, event: DomainEvent) -> None:
        """
        异步发布事件
        
        Args:
            event: 要发布的事件
        """
        self._executor.submit(self.publish, event)
    
    def _run_async_handlers(self, handlers: List[AsyncEventHandler], event: DomainEvent) -> None:
        """
        在新的事件循环中运行异步处理器
        
        Args:
            handlers: 异步处理器列表
            event: 事件
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def run_handlers():
                tasks = []
                for handler in handlers:
                    try:
                        if hasattr(handler, 'can_handle') and not handler.can_handle(event.event_type):
                            continue
                        tasks.append(handler.handle_async(event))
                    except Exception as e:
                        self._logger.error(f"Error creating task for handler {handler.__class__.__name__}: {e}")
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            
            loop.run_until_complete(run_handlers())
        except Exception as e:
            self._logger.error(f"Error running async handlers: {e}")
        finally:
            loop.close()
    
    def _add_to_history(self, event: DomainEvent) -> None:
        """
        添加事件到历史记录
        
        Args:
            event: 事件
        """
        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)
    
    def get_event_history(self, 
                         event_type: Optional[EventType] = None,
                         aggregate_id: Optional[str] = None,
                         limit: Optional[int] = None) -> List[DomainEvent]:
        """
        获取事件历史
        
        Args:
            event_type: 过滤的事件类型
            aggregate_id: 过滤的聚合ID
            limit: 返回的最大事件数量
            
        Returns:
            List[DomainEvent]: 事件列表
        """
        with self._lock:
            events = self._event_history[:]
        
        # 过滤
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if aggregate_id:
            events = [e for e in events if e.aggregate_id == aggregate_id]
        
        # 限制数量
        if limit:
            events = events[-limit:]
        
        return events
    
    def clear_history(self) -> None:
        """清空事件历史"""
        with self._lock:
            self._event_history.clear()
    
    def get_handler_count(self, event_type: Optional[EventType] = None) -> int:
        """
        获取处理器数量
        
        Args:
            event_type: 事件类型，None表示获取全局处理器数量
            
        Returns:
            int: 处理器数量
        """
        with self._lock:
            if event_type is None:
                return len(self._global_handlers) + len(self._global_async_handlers)
            else:
                return len(self._handlers[event_type]) + len(self._async_handlers[event_type])
    
    def shutdown(self) -> None:
        """关闭事件总线"""
        self._executor.shutdown(wait=True)
        self._logger.info("Event bus shutdown completed")


# 便利的函数式处理器
def create_function_handler(func: Callable[[DomainEvent], None], 
                          event_types: Optional[List[EventType]] = None) -> EventHandler:
    """
    创建基于函数的事件处理器
    
    Args:
        func: 处理函数
        event_types: 支持的事件类型列表，None表示支持所有类型
        
    Returns:
        EventHandler: 事件处理器
    """
    class FunctionHandler:
        def handle(self, event: DomainEvent) -> None:
            func(event)
        
        def can_handle(self, event_type: EventType) -> bool:
            return event_types is None or event_type in event_types
    
    return FunctionHandler()


def create_async_function_handler(func: Callable[[DomainEvent], Any], 
                                event_types: Optional[List[EventType]] = None) -> AsyncEventHandler:
    """
    创建基于异步函数的事件处理器
    
    Args:
        func: 异步处理函数
        event_types: 支持的事件类型列表，None表示支持所有类型
        
    Returns:
        AsyncEventHandler: 异步事件处理器
    """
    class AsyncFunctionHandler:
        async def handle_async(self, event: DomainEvent) -> None:
            await func(event)
        
        def can_handle(self, event_type: EventType) -> bool:
            return event_types is None or event_type in event_types
    
    return AsyncFunctionHandler()


# 全局事件总线实例
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    获取全局事件总线实例
    
    Returns:
        EventBus: 事件总线实例
    """
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def set_event_bus(event_bus: EventBus) -> None:
    """
    设置全局事件总线实例
    
    Args:
        event_bus: 事件总线实例
    """
    global _global_event_bus
    _global_event_bus = event_bus 