"""
事件系统单元测试.

测试事件总线的订阅、发布、历史记录等功能。
"""

import pytest
import logging
from unittest.mock import Mock, call

from v2.core.events import EventBus, EventType, GameEvent


@pytest.mark.unit
@pytest.mark.fast
class TestEventBus:
    """事件总线测试类."""
    
    def setup_method(self):
        """测试前设置."""
        self.event_bus = EventBus()
        self.mock_listener = Mock()
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_subscribe_and_emit(self):
        """测试订阅和发射事件."""
        # 订阅事件
        self.event_bus.subscribe(EventType.HAND_STARTED, self.mock_listener)
        
        # 发射事件
        event = GameEvent(
            event_type=EventType.HAND_STARTED,
            data={'hand_number': 1}
        )
        self.event_bus.emit(event)
        
        # 验证监听器被调用
        self.mock_listener.assert_called_once_with(event)
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_emit_simple(self):
        """测试简单事件发射."""
        # 订阅事件
        self.event_bus.subscribe(EventType.PLAYER_ACTION, self.mock_listener)
        
        # 发射简单事件
        self.event_bus.emit_simple(
            EventType.PLAYER_ACTION,
            player_id=1,
            action_type="call",
            amount=50
        )
        
        # 验证监听器被调用
        self.mock_listener.assert_called_once()
        
        # 验证事件数据
        called_event = self.mock_listener.call_args[0][0]
        assert called_event.event_type == EventType.PLAYER_ACTION
        assert called_event.data['player_id'] == 1
        assert called_event.data['action_type'] == "call"
        assert called_event.data['amount'] == 50
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_multiple_listeners(self):
        """测试多个监听器."""
        listener1 = Mock()
        listener2 = Mock()
        
        # 订阅同一事件类型
        self.event_bus.subscribe(EventType.BET_PLACED, listener1)
        self.event_bus.subscribe(EventType.BET_PLACED, listener2)
        
        # 发射事件
        self.event_bus.emit_simple(EventType.BET_PLACED, amount=100)
        
        # 验证两个监听器都被调用
        listener1.assert_called_once()
        listener2.assert_called_once()
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_unsubscribe(self):
        """测试取消订阅."""
        # 订阅事件
        self.event_bus.subscribe(EventType.HAND_ENDED, self.mock_listener)
        
        # 发射事件，验证监听器被调用
        self.event_bus.emit_simple(EventType.HAND_ENDED)
        assert self.mock_listener.call_count == 1
        
        # 取消订阅
        result = self.event_bus.unsubscribe(EventType.HAND_ENDED, self.mock_listener)
        assert result is True
        
        # 再次发射事件，验证监听器不被调用
        self.event_bus.emit_simple(EventType.HAND_ENDED)
        assert self.mock_listener.call_count == 1  # 仍然是1，没有增加
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_unsubscribe_nonexistent(self):
        """测试取消订阅不存在的监听器."""
        result = self.event_bus.unsubscribe(EventType.HAND_ENDED, self.mock_listener)
        assert result is False
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_listeners_count(self):
        """测试获取监听器数量."""
        # 初始状态
        assert self.event_bus.get_listeners_count(EventType.PLAYER_FOLDED) == 0
        
        # 添加监听器
        self.event_bus.subscribe(EventType.PLAYER_FOLDED, self.mock_listener)
        assert self.event_bus.get_listeners_count(EventType.PLAYER_FOLDED) == 1
        
        # 添加更多监听器
        listener2 = Mock()
        self.event_bus.subscribe(EventType.PLAYER_FOLDED, listener2)
        assert self.event_bus.get_listeners_count(EventType.PLAYER_FOLDED) == 2
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_clear_listeners(self):
        """测试清除监听器."""
        # 添加监听器
        self.event_bus.subscribe(EventType.PHASE_CHANGED, self.mock_listener)
        self.event_bus.subscribe(EventType.POT_UPDATED, self.mock_listener)
        
        # 清除特定事件类型的监听器
        self.event_bus.clear_listeners(EventType.PHASE_CHANGED)
        assert self.event_bus.get_listeners_count(EventType.PHASE_CHANGED) == 0
        assert self.event_bus.get_listeners_count(EventType.POT_UPDATED) == 1
        
        # 清除所有监听器
        self.event_bus.clear_listeners()
        assert self.event_bus.get_listeners_count(EventType.POT_UPDATED) == 0
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_event_history(self):
        """测试事件历史记录."""
        # 发射几个事件
        self.event_bus.emit_simple(EventType.HAND_STARTED, hand_number=1)
        self.event_bus.emit_simple(EventType.PLAYER_ACTION, player_id=1)
        self.event_bus.emit_simple(EventType.HAND_ENDED, winner_ids=[1])
        
        # 获取所有历史
        history = self.event_bus.get_event_history()
        assert len(history) == 3
        assert history[0].event_type == EventType.HAND_STARTED
        assert history[1].event_type == EventType.PLAYER_ACTION
        assert history[2].event_type == EventType.HAND_ENDED
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_event_history_filtered(self):
        """测试过滤的事件历史记录."""
        # 发射不同类型的事件
        self.event_bus.emit_simple(EventType.HAND_STARTED)
        self.event_bus.emit_simple(EventType.PLAYER_ACTION)
        self.event_bus.emit_simple(EventType.PLAYER_ACTION)
        self.event_bus.emit_simple(EventType.HAND_ENDED)
        
        # 获取特定类型的历史
        player_actions = self.event_bus.get_event_history(EventType.PLAYER_ACTION)
        assert len(player_actions) == 2
        assert all(e.event_type == EventType.PLAYER_ACTION for e in player_actions)
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_event_history_limited(self):
        """测试限制数量的事件历史记录."""
        # 发射多个事件
        for i in range(5):
            self.event_bus.emit_simple(EventType.PLAYER_ACTION, action_id=i)
        
        # 获取限制数量的历史
        limited_history = self.event_bus.get_event_history(limit=3)
        assert len(limited_history) == 3
        
        # 验证是最新的3个事件
        assert limited_history[0].data['action_id'] == 2
        assert limited_history[1].data['action_id'] == 3
        assert limited_history[2].data['action_id'] == 4
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_clear_history(self):
        """测试清除事件历史."""
        # 发射事件
        self.event_bus.emit_simple(EventType.HAND_STARTED)
        assert len(self.event_bus.get_event_history()) == 1
        
        # 清除历史
        self.event_bus.clear_history()
        assert len(self.event_bus.get_event_history()) == 0
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_listener_exception_handling(self):
        """测试监听器异常处理."""
        # 创建会抛异常的监听器
        def failing_listener(event):
            raise ValueError("Test exception")
        
        # 订阅事件
        self.event_bus.subscribe(EventType.ERROR_OCCURRED, failing_listener)
        self.event_bus.subscribe(EventType.ERROR_OCCURRED, self.mock_listener)
        
        # 发射事件，不应该因为一个监听器失败而影响其他监听器
        self.event_bus.emit_simple(EventType.ERROR_OCCURRED)
        
        # 验证正常的监听器仍然被调用
        self.mock_listener.assert_called_once()
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_event_timestamp(self):
        """测试事件时间戳."""
        import time
        
        before_time = time.time()
        self.event_bus.emit_simple(EventType.GAME_STARTED)
        after_time = time.time()
        
        history = self.event_bus.get_event_history()
        assert len(history) == 1
        
        event_time = history[0].timestamp
        assert before_time <= event_time <= after_time


@pytest.mark.unit
@pytest.mark.fast
class TestGameEvent:
    """游戏事件测试类."""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_game_event_creation(self):
        """测试游戏事件创建."""
        event = GameEvent(
            event_type=EventType.HAND_STARTED,
            data={'hand_number': 1, 'players': 4}
        )
        
        assert event.event_type == EventType.HAND_STARTED
        assert event.data['hand_number'] == 1
        assert event.data['players'] == 4
        assert event.timestamp is not None
        assert event.source is None
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_game_event_with_source(self):
        """测试带来源的游戏事件."""
        event = GameEvent(
            event_type=EventType.STATE_CHANGED,
            data={'new_state': 'active'},
            source='controller'
        )
        
        assert event.source == 'controller'
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_game_event_custom_timestamp(self):
        """测试自定义时间戳的游戏事件."""
        custom_time = 1234567890.0
        event = GameEvent(
            event_type=EventType.GAME_ENDED,
            data={},
            timestamp=custom_time
        )
        
        assert event.timestamp == custom_time


@pytest.mark.unit
@pytest.mark.fast
class TestEventType:
    """事件类型测试类."""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_event_type_values(self):
        """测试事件类型值."""
        assert EventType.GAME_STARTED.value == "game_started"
        assert EventType.HAND_ENDED.value == "hand_ended"
        assert EventType.PLAYER_ACTION.value == "player_action"
        assert EventType.BET_PLACED.value == "bet_placed"
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_event_type_enumeration(self):
        """测试事件类型枚举."""
        # 验证所有事件类型都有值
        for event_type in EventType:
            assert isinstance(event_type.value, str)
            assert len(event_type.value) > 0 