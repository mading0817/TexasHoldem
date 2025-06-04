"""
Events Module Unit Tests

测试领域事件系统的各个组件，包括事件创建、发布、订阅等功能。
所有测试都包含反作弊验证。
"""

import pytest
import time
import asyncio
from typing import List
from unittest.mock import Mock

from v3.core.events import (
    EventType,
    DomainEvent,
    GameStartedEvent,
    HandStartedEvent,
    PhaseChangedEvent,
    PlayerActionExecutedEvent,
    PotUpdatedEvent,
    CardsDealtEvent,
    CommunityCardsRevealedEvent,
    EventBus,
    EventHandler,
    AsyncEventHandler,
    get_event_bus,
    set_event_bus,
    create_function_handler,
    create_async_function_handler,
)

from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestDomainEvent:
    """测试DomainEvent基类"""
    
    def test_create_domain_event(self):
        """测试创建基础领域事件"""
        # 创建事件
        event = DomainEvent.create(
            event_type=EventType.GAME_STARTED,
            aggregate_id="game_123",
            data={"player_count": 4}
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(event, "DomainEvent")
        
        # 验证事件属性
        assert event.event_type == EventType.GAME_STARTED
        assert event.aggregate_id == "game_123"
        assert event.data == {"player_count": 4}
        assert event.version == 1
        assert event.correlation_id is None
        assert isinstance(event.event_id, str)
        assert len(event.event_id) > 0
        assert isinstance(event.timestamp, float)
        assert event.timestamp > 0
    
    def test_create_domain_event_with_correlation_id(self):
        """测试创建带关联ID的领域事件"""
        correlation_id = "corr_456"
        event = DomainEvent.create(
            event_type=EventType.HAND_STARTED,
            aggregate_id="game_123",
            data={"hand_number": 1},
            correlation_id=correlation_id
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(event, "DomainEvent")
        
        assert event.correlation_id == correlation_id
    
    def test_event_serialization(self):
        """测试事件序列化和反序列化"""
        original_event = DomainEvent.create(
            event_type=EventType.PLAYER_ACTION_EXECUTED,
            aggregate_id="game_123",
            data={"player_id": "player_1", "action": "fold"}
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(original_event, "DomainEvent")
        
        # 序列化
        event_dict = original_event.to_dict()
        assert isinstance(event_dict, dict)
        assert event_dict["event_type"] == "PLAYER_ACTION_EXECUTED"
        assert event_dict["aggregate_id"] == "game_123"
        
        # 反序列化
        restored_event = DomainEvent.from_dict(event_dict)
        CoreUsageChecker.verify_real_objects(restored_event, "DomainEvent")
        
        # 验证一致性
        assert restored_event.event_id == original_event.event_id
        assert restored_event.event_type == original_event.event_type
        assert restored_event.aggregate_id == original_event.aggregate_id
        assert restored_event.data == original_event.data
        assert restored_event.timestamp == original_event.timestamp


class TestSpecificEvents:
    """测试具体事件类型"""
    
    def test_game_started_event(self):
        """测试游戏开始事件"""
        event = GameStartedEvent.create(
            game_id="game_123",
            player_ids=["player_1", "player_2"],
            small_blind=10,
            big_blind=20
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(event, "GameStartedEvent")
        
        assert event.event_type == EventType.GAME_STARTED
        assert event.aggregate_id == "game_123"
        assert event.data["player_ids"] == ["player_1", "player_2"]
        assert event.data["small_blind"] == 10
        assert event.data["big_blind"] == 20
    
    def test_hand_started_event(self):
        """测试手牌开始事件"""
        event = HandStartedEvent.create(
            game_id="game_123",
            hand_number=5,
            dealer_position=2
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(event, "HandStartedEvent")
        
        assert event.event_type == EventType.HAND_STARTED
        assert event.data["hand_number"] == 5
        assert event.data["dealer_position"] == 2
    
    def test_phase_changed_event(self):
        """测试阶段转换事件"""
        event = PhaseChangedEvent.create(
            game_id="game_123",
            from_phase="PRE_FLOP",
            to_phase="FLOP"
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(event, "PhaseChangedEvent")
        
        assert event.event_type == EventType.PHASE_CHANGED
        assert event.data["from_phase"] == "PRE_FLOP"
        assert event.data["to_phase"] == "FLOP"
    
    def test_player_action_executed_event(self):
        """测试玩家行动执行事件"""
        event = PlayerActionExecutedEvent.create(
            game_id="game_123",
            player_id="player_1",
            action_type="raise",
            amount=50
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(event, "PlayerActionExecutedEvent")
        
        assert event.event_type == EventType.PLAYER_ACTION_EXECUTED
        assert event.data["player_id"] == "player_1"
        assert event.data["action_type"] == "raise"
        assert event.data["amount"] == 50
    
    def test_pot_updated_event(self):
        """测试边池更新事件"""
        side_pots = [{"amount": 100, "eligible_players": ["player_1", "player_2"]}]
        event = PotUpdatedEvent.create(
            game_id="game_123",
            total_pot=150,
            side_pots=side_pots
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(event, "PotUpdatedEvent")
        
        assert event.event_type == EventType.POT_UPDATED
        assert event.data["total_pot"] == 150
        assert event.data["side_pots"] == side_pots
    
    def test_cards_dealt_event(self):
        """测试发牌事件"""
        cards_dealt = {
            "player_1": ["As", "Kh"],
            "player_2": ["Qd", "Jc"]
        }
        event = CardsDealtEvent.create(
            game_id="game_123",
            cards_dealt=cards_dealt
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(event, "CardsDealtEvent")
        
        assert event.event_type == EventType.CARDS_DEALT
        assert event.data["cards_dealt"] == cards_dealt
    
    def test_community_cards_revealed_event(self):
        """测试公共牌揭示事件"""
        event = CommunityCardsRevealedEvent.create(
            game_id="game_123",
            revealed_cards=["Ah", "Kd", "Qc"],
            total_community_cards=["Ah", "Kd", "Qc"]
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(event, "CommunityCardsRevealedEvent")
        
        assert event.event_type == EventType.COMMUNITY_CARDS_REVEALED
        assert event.data["revealed_cards"] == ["Ah", "Kd", "Qc"]
        assert event.data["total_community_cards"] == ["Ah", "Kd", "Qc"]


class TestEventBus:
    """测试事件总线"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.event_bus = EventBus()
        self.handled_events: List[DomainEvent] = []
    
    def test_create_event_bus(self):
        """测试创建事件总线"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.event_bus, "EventBus")
        
        assert self.event_bus.get_handler_count() == 0
        assert len(self.event_bus.get_event_history()) == 0
    
    def test_subscribe_and_publish_event(self):
        """测试订阅和发布事件"""
        # 创建处理器
        class TestHandler:
            def __init__(self, handled_events: List[DomainEvent]):
                self.handled_events = handled_events
            
            def handle(self, event: DomainEvent) -> None:
                self.handled_events.append(event)
            
            def can_handle(self, event_type: EventType) -> bool:
                return event_type == EventType.GAME_STARTED
        
        handler = TestHandler(self.handled_events)
        
        # 订阅事件
        self.event_bus.subscribe(EventType.GAME_STARTED, handler)
        assert self.event_bus.get_handler_count(EventType.GAME_STARTED) == 1
        
        # 发布事件
        event = GameStartedEvent.create(
            game_id="game_123",
            player_ids=["player_1", "player_2"],
            small_blind=10,
            big_blind=20
        )
        
        self.event_bus.publish(event)
        
        # 验证处理器被调用
        assert len(self.handled_events) == 1
        assert self.handled_events[0].event_id == event.event_id
        
        # 验证事件历史
        history = self.event_bus.get_event_history()
        assert len(history) == 1
        assert history[0].event_id == event.event_id
    
    def test_subscribe_all_events(self):
        """测试订阅所有事件"""
        class GlobalHandler:
            def __init__(self, handled_events: List[DomainEvent]):
                self.handled_events = handled_events
            
            def handle(self, event: DomainEvent) -> None:
                self.handled_events.append(event)
            
            def can_handle(self, event_type: EventType) -> bool:
                return True
        
        handler = GlobalHandler(self.handled_events)
        self.event_bus.subscribe_all(handler)
        
        # 发布不同类型的事件
        game_event = GameStartedEvent.create("game_123", ["p1"], 10, 20)
        hand_event = HandStartedEvent.create("game_123", 1, 0)
        
        self.event_bus.publish(game_event)
        self.event_bus.publish(hand_event)
        
        # 验证全局处理器处理了所有事件
        assert len(self.handled_events) == 2
        assert self.handled_events[0].event_type == EventType.GAME_STARTED
        assert self.handled_events[1].event_type == EventType.HAND_STARTED
    
    def test_unsubscribe_event(self):
        """测试取消订阅事件"""
        class TestHandler:
            def handle(self, event: DomainEvent) -> None:
                self.handled_events.append(event)
            
            def can_handle(self, event_type: EventType) -> bool:
                return True
        
        handler = TestHandler()
        handler.handled_events = self.handled_events
        
        # 订阅然后取消订阅
        self.event_bus.subscribe(EventType.GAME_STARTED, handler)
        assert self.event_bus.get_handler_count(EventType.GAME_STARTED) == 1
        
        success = self.event_bus.unsubscribe(EventType.GAME_STARTED, handler)
        assert success
        assert self.event_bus.get_handler_count(EventType.GAME_STARTED) == 0
        
        # 发布事件，应该不会被处理
        event = GameStartedEvent.create("game_123", ["p1"], 10, 20)
        self.event_bus.publish(event)
        
        assert len(self.handled_events) == 0
    
    def test_event_history_filtering(self):
        """测试事件历史过滤"""
        # 发布不同类型和聚合ID的事件
        event1 = GameStartedEvent.create("game_123", ["p1"], 10, 20)
        event2 = HandStartedEvent.create("game_123", 1, 0)
        event3 = GameStartedEvent.create("game_456", ["p2"], 5, 10)
        
        self.event_bus.publish(event1)
        self.event_bus.publish(event2)
        self.event_bus.publish(event3)
        
        # 按事件类型过滤
        game_events = self.event_bus.get_event_history(event_type=EventType.GAME_STARTED)
        assert len(game_events) == 2
        assert all(e.event_type == EventType.GAME_STARTED for e in game_events)
        
        # 按聚合ID过滤
        game_123_events = self.event_bus.get_event_history(aggregate_id="game_123")
        assert len(game_123_events) == 2
        assert all(e.aggregate_id == "game_123" for e in game_123_events)
        
        # 限制数量
        limited_events = self.event_bus.get_event_history(limit=2)
        assert len(limited_events) == 2
    
    def test_clear_event_history(self):
        """测试清空事件历史"""
        event = GameStartedEvent.create("game_123", ["p1"], 10, 20)
        self.event_bus.publish(event)
        
        assert len(self.event_bus.get_event_history()) == 1
        
        self.event_bus.clear_history()
        assert len(self.event_bus.get_event_history()) == 0
    
    def test_async_event_handler(self):
        """测试异步事件处理器"""
        handled_events = []
        
        class AsyncTestHandler:
            async def handle_async(self, event: DomainEvent) -> None:
                await asyncio.sleep(0.01)  # 模拟异步操作
                handled_events.append(event)
            
            def can_handle(self, event_type: EventType) -> bool:
                return event_type == EventType.GAME_STARTED
        
        handler = AsyncTestHandler()
        self.event_bus.subscribe_async(EventType.GAME_STARTED, handler)
        
        # 发布事件
        event = GameStartedEvent.create("game_123", ["p1"], 10, 20)
        self.event_bus.publish(event)
        
        # 等待异步处理完成
        time.sleep(0.1)
        
        assert len(handled_events) == 1
        assert handled_events[0].event_id == event.event_id


class TestEventHandlerHelpers:
    """测试事件处理器辅助函数"""
    
    def test_create_function_handler(self):
        """测试创建基于函数的处理器"""
        handled_events = []
        
        def handle_event(event: DomainEvent) -> None:
            handled_events.append(event)
        
        handler = create_function_handler(handle_event, [EventType.GAME_STARTED])
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(handler, "FunctionHandler")
        
        # 测试can_handle
        assert handler.can_handle(EventType.GAME_STARTED)
        assert not handler.can_handle(EventType.HAND_STARTED)
        
        # 测试handle
        event = GameStartedEvent.create("game_123", ["p1"], 10, 20)
        handler.handle(event)
        
        assert len(handled_events) == 1
        assert handled_events[0].event_id == event.event_id
    
    def test_create_async_function_handler(self):
        """测试创建基于异步函数的处理器"""
        handled_events = []
        
        async def handle_event_async(event: DomainEvent) -> None:
            await asyncio.sleep(0.01)
            handled_events.append(event)
        
        handler = create_async_function_handler(handle_event_async)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(handler, "AsyncFunctionHandler")
        
        # 测试can_handle（None表示支持所有类型）
        assert handler.can_handle(EventType.GAME_STARTED)
        assert handler.can_handle(EventType.HAND_STARTED)


class TestGlobalEventBus:
    """测试全局事件总线"""
    
    def test_get_global_event_bus(self):
        """测试获取全局事件总线"""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(bus1, "EventBus")
        CoreUsageChecker.verify_real_objects(bus2, "EventBus")
        
        # 应该是同一个实例
        assert bus1 is bus2
    
    def test_set_global_event_bus(self):
        """测试设置全局事件总线"""
        custom_bus = EventBus()
        set_event_bus(custom_bus)
        
        retrieved_bus = get_event_bus()
        assert retrieved_bus is custom_bus
        
        # 恢复默认状态
        set_event_bus(EventBus())


class TestEventBusPerformance:
    """测试事件总线性能"""
    
    def test_high_volume_event_publishing(self):
        """测试大量事件发布的性能"""
        event_bus = EventBus()
        handled_count = 0
        
        class CountingHandler:
            def handle(self, event: DomainEvent) -> None:
                nonlocal handled_count
                handled_count += 1
            
            def can_handle(self, event_type: EventType) -> bool:
                return True
        
        handler = CountingHandler()
        event_bus.subscribe_all(handler)
        
        # 发布大量事件
        start_time = time.time()
        event_count = 1000
        
        for i in range(event_count):
            event = GameStartedEvent.create(f"game_{i}", ["p1"], 10, 20)
            event_bus.publish(event)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 验证性能（应该能在1秒内处理1000个事件）
        assert duration < 1.0
        assert handled_count == event_count
        
        # 验证事件历史
        history = event_bus.get_event_history()
        assert len(history) == event_count 