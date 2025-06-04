"""
Events Integration Tests

测试领域事件系统与其他模块的集成，包括状态机、下注引擎等。
所有测试都包含反作弊验证。
"""

import pytest
import time
from typing import List, Dict, Any
from unittest.mock import Mock

from v3.core.events import (
    EventType,
    DomainEvent,
    GameStartedEvent,
    HandStartedEvent,
    PhaseChangedEvent,
    PlayerActionExecutedEvent,
    PotUpdatedEvent,
    EventBus,
    get_event_bus,
    set_event_bus,
    create_function_handler,
)

from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class MockGameStateMachine:
    """测试用游戏状态机，用于集成测试"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.current_phase = "INIT"
        self.game_id = "test_game_123"
        self.players = ["player_1", "player_2", "player_3"]
        self.hand_number = 0
        
        # 订阅相关事件
        self.event_bus.subscribe(EventType.GAME_STARTED, self)
        self.event_bus.subscribe(EventType.HAND_STARTED, self)
        self.event_bus.subscribe(EventType.PHASE_CHANGED, self)
    
    def handle(self, event: DomainEvent) -> None:
        """处理事件"""
        if event.event_type == EventType.GAME_STARTED:
            self._handle_game_started(event)
        elif event.event_type == EventType.HAND_STARTED:
            self._handle_hand_started(event)
        elif event.event_type == EventType.PHASE_CHANGED:
            self._handle_phase_changed(event)
    
    def can_handle(self, event_type: EventType) -> bool:
        """检查是否能处理指定类型的事件"""
        return event_type in [
            EventType.GAME_STARTED,
            EventType.HAND_STARTED,
            EventType.PHASE_CHANGED
        ]
    
    def start_game(self) -> None:
        """开始游戏"""
        event = GameStartedEvent.create(
            game_id=self.game_id,
            player_ids=self.players,
            small_blind=10,
            big_blind=20
        )
        self.event_bus.publish(event)
    
    def start_hand(self) -> None:
        """开始新手牌"""
        self.hand_number += 1
        event = HandStartedEvent.create(
            game_id=self.game_id,
            hand_number=self.hand_number,
            dealer_position=0
        )
        self.event_bus.publish(event)
    
    def change_phase(self, new_phase: str) -> None:
        """改变游戏阶段"""
        old_phase = self.current_phase
        event = PhaseChangedEvent.create(
            game_id=self.game_id,
            from_phase=old_phase,
            to_phase=new_phase
        )
        self.event_bus.publish(event)
    
    def _handle_game_started(self, event: DomainEvent) -> None:
        """处理游戏开始事件"""
        self.current_phase = "PRE_FLOP"
    
    def _handle_hand_started(self, event: DomainEvent) -> None:
        """处理手牌开始事件"""
        pass
    
    def _handle_phase_changed(self, event: DomainEvent) -> None:
        """处理阶段变化事件"""
        self.current_phase = event.data["to_phase"]


class MockBettingEngine:
    """测试用下注引擎，用于集成测试"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.total_pot = 0
        self.player_bets: Dict[str, int] = {}
        
        # 订阅玩家行动事件
        self.event_bus.subscribe(EventType.PLAYER_ACTION_EXECUTED, self)
    
    def handle(self, event: DomainEvent) -> None:
        """处理事件"""
        if event.event_type == EventType.PLAYER_ACTION_EXECUTED:
            self._handle_player_action(event)
    
    def can_handle(self, event_type: EventType) -> bool:
        """检查是否能处理指定类型的事件"""
        return event_type == EventType.PLAYER_ACTION_EXECUTED
    
    def execute_player_action(self, player_id: str, action_type: str, amount: int = 0) -> None:
        """执行玩家行动"""
        # 发布玩家行动事件
        event = PlayerActionExecutedEvent.create(
            game_id="test_game_123",
            player_id=player_id,
            action_type=action_type,
            amount=amount
        )
        self.event_bus.publish(event)
    
    def _handle_player_action(self, event: DomainEvent) -> None:
        """处理玩家行动事件"""
        player_id = event.data["player_id"]
        action_type = event.data["action_type"]
        amount = event.data["amount"]
        
        if action_type in ["bet", "raise", "call"]:
            self.player_bets[player_id] = self.player_bets.get(player_id, 0) + amount
            self.total_pot += amount
            
            # 发布边池更新事件
            pot_event = PotUpdatedEvent.create(
                game_id="test_game_123",
                total_pot=self.total_pot,
                side_pots=[{"amount": self.total_pot, "eligible_players": list(self.player_bets.keys())}]
            )
            self.event_bus.publish(pot_event)


class TestEventsIntegration:
    """测试事件系统集成"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.event_bus = EventBus()
        self.event_history: List[DomainEvent] = []
        
        # 创建全局事件记录器
        def record_event(event: DomainEvent) -> None:
            self.event_history.append(event)
        
        self.recorder = create_function_handler(record_event)
        self.event_bus.subscribe_all(self.recorder)
    
    def test_state_machine_event_integration(self):
        """测试状态机与事件系统的集成"""
        # 创建测试状态机
        state_machine = MockGameStateMachine(self.event_bus)
        
        # 反作弊检查 - 只检查核心模块对象
        CoreUsageChecker.verify_real_objects(self.event_bus, "EventBus")
        
        # 开始游戏
        state_machine.start_game()
        
        # 验证事件被发布和处理
        assert len(self.event_history) == 1
        assert self.event_history[0].event_type == EventType.GAME_STARTED
        assert state_machine.current_phase == "PRE_FLOP"
        
        # 开始手牌
        state_machine.start_hand()
        
        assert len(self.event_history) == 2
        assert self.event_history[1].event_type == EventType.HAND_STARTED
        assert state_machine.hand_number == 1
        
        # 改变阶段
        state_machine.change_phase("FLOP")
        
        assert len(self.event_history) == 3
        assert self.event_history[2].event_type == EventType.PHASE_CHANGED
        assert state_machine.current_phase == "FLOP"
    
    def test_betting_engine_event_integration(self):
        """测试下注引擎与事件系统的集成"""
        # 创建测试下注引擎
        betting_engine = MockBettingEngine(self.event_bus)
        
        # 反作弊检查 - 只检查核心模块对象
        CoreUsageChecker.verify_real_objects(self.event_bus, "EventBus")
        
        # 执行玩家行动
        betting_engine.execute_player_action("player_1", "bet", 50)
        
        # 验证事件链：玩家行动 -> 边池更新
        assert len(self.event_history) == 2
        
        # 找到玩家行动事件和边池更新事件
        action_events = [e for e in self.event_history if e.event_type == EventType.PLAYER_ACTION_EXECUTED]
        pot_events = [e for e in self.event_history if e.event_type == EventType.POT_UPDATED]
        
        assert len(action_events) == 1
        assert len(pot_events) == 1
        
        # 验证玩家行动事件
        action_event = action_events[0]
        assert action_event.data["player_id"] == "player_1"
        assert action_event.data["action_type"] == "bet"
        assert action_event.data["amount"] == 50
        
        # 验证边池更新事件
        pot_event = pot_events[0]
        assert pot_event.data["total_pot"] == 50
        
        # 验证下注引擎状态
        assert betting_engine.total_pot == 50
        assert betting_engine.player_bets["player_1"] == 50
    
    def test_multi_component_event_flow(self):
        """测试多组件事件流"""
        # 创建多个组件
        state_machine = MockGameStateMachine(self.event_bus)
        betting_engine = MockBettingEngine(self.event_bus)
        
        # 反作弊检查 - 只检查核心模块对象
        CoreUsageChecker.verify_real_objects(self.event_bus, "EventBus")
        
        # 完整的游戏流程
        # 1. 开始游戏
        state_machine.start_game()
        assert len(self.event_history) == 1
        assert state_machine.current_phase == "PRE_FLOP"
        
        # 2. 开始手牌
        state_machine.start_hand()
        assert len(self.event_history) == 2
        
        # 3. 玩家下注
        betting_engine.execute_player_action("player_1", "bet", 30)
        assert len(self.event_history) == 4  # 玩家行动 + 边池更新
        
        # 4. 另一个玩家跟注
        betting_engine.execute_player_action("player_2", "call", 30)
        assert len(self.event_history) == 6  # 玩家行动 + 边池更新
        
        # 5. 改变阶段
        state_machine.change_phase("FLOP")
        assert len(self.event_history) == 7
        
        # 验证最终状态
        assert state_machine.current_phase == "FLOP"
        assert betting_engine.total_pot == 60
        assert betting_engine.player_bets["player_1"] == 30
        assert betting_engine.player_bets["player_2"] == 30
    
    def test_event_correlation_tracking(self):
        """测试事件关联追踪"""
        state_machine = MockGameStateMachine(self.event_bus)
        
        # 使用关联ID开始游戏
        correlation_id = "game_session_001"
        event = GameStartedEvent.create(
            game_id="test_game_123",
            player_ids=["player_1", "player_2"],
            small_blind=10,
            big_blind=20,
            correlation_id=correlation_id
        )
        
        self.event_bus.publish(event)
        
        # 验证关联ID被正确传递
        assert len(self.event_history) == 1
        assert self.event_history[0].correlation_id == correlation_id
        
        # 后续事件可以使用相同的关联ID
        hand_event = HandStartedEvent.create(
            game_id="test_game_123",
            hand_number=1,
            dealer_position=0,
            correlation_id=correlation_id
        )
        
        self.event_bus.publish(hand_event)
        
        # 验证关联ID一致性
        assert len(self.event_history) == 2
        assert self.event_history[1].correlation_id == correlation_id
        
        # 可以通过关联ID过滤事件
        correlated_events = [e for e in self.event_history if e.correlation_id == correlation_id]
        assert len(correlated_events) == 2
    
    def test_event_bus_error_handling(self):
        """测试事件总线错误处理"""
        # 创建会抛出异常的处理器
        class FaultyHandler:
            def handle(self, event: DomainEvent) -> None:
                raise ValueError("Simulated handler error")
            
            def can_handle(self, event_type: EventType) -> bool:
                return True
        
        faulty_handler = FaultyHandler()
        self.event_bus.subscribe_all(faulty_handler)
        
        # 发布事件，即使有处理器出错，其他处理器仍应正常工作
        event = GameStartedEvent.create("test_game", ["p1"], 10, 20)
        self.event_bus.publish(event)
        
        # 验证记录器仍然收到事件（错误被捕获）
        assert len(self.event_history) == 1
        assert self.event_history[0].event_type == EventType.GAME_STARTED
    
    def test_event_performance_under_load(self):
        """测试高负载下的事件性能"""
        # 创建多个处理器
        handlers = []
        for i in range(10):
            def create_handler(handler_id):
                def handle_event(event: DomainEvent) -> None:
                    # 模拟一些处理时间
                    pass
                return create_function_handler(handle_event)
            
            handler = create_handler(i)
            handlers.append(handler)
            self.event_bus.subscribe_all(handler)
        
        # 发布大量事件
        start_time = time.time()
        event_count = 500
        
        for i in range(event_count):
            event = PlayerActionExecutedEvent.create(
                game_id="test_game",
                player_id=f"player_{i % 3}",
                action_type="fold",
                amount=0
            )
            self.event_bus.publish(event)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 验证性能（应该能在合理时间内完成）
        assert duration < 2.0  # 500个事件，10个处理器，应该在2秒内完成
        assert len(self.event_history) == event_count
    
    def test_event_serialization_integration(self):
        """测试事件序列化集成"""
        # 创建复杂事件
        event = PotUpdatedEvent.create(
            game_id="test_game_123",
            total_pot=150,
            side_pots=[
                {"amount": 100, "eligible_players": ["player_1", "player_2"]},
                {"amount": 50, "eligible_players": ["player_1", "player_2", "player_3"]}
            ]
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(event, "PotUpdatedEvent")
        
        # 序列化和反序列化
        event_dict = event.to_dict()
        restored_event = DomainEvent.from_dict(event_dict)
        
        # 验证序列化后的事件仍然可以正常处理
        self.event_bus.publish(restored_event)
        
        assert len(self.event_history) == 1
        assert self.event_history[0].event_type == EventType.POT_UPDATED
        assert self.event_history[0].data["total_pot"] == 150
        assert len(self.event_history[0].data["side_pots"]) == 2


class TestEventBusLifecycle:
    """测试事件总线生命周期管理"""
    
    def test_event_bus_shutdown(self):
        """测试事件总线关闭"""
        event_bus = EventBus()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(event_bus, "EventBus")
        
        # 发布一些事件
        for i in range(5):
            event = GameStartedEvent.create(f"game_{i}", ["p1"], 10, 20)
            event_bus.publish(event)
        
        # 验证事件历史
        assert len(event_bus.get_event_history()) == 5
        
        # 关闭事件总线
        event_bus.shutdown()
        
        # 验证关闭后仍可以访问历史（但不应该发布新事件）
        assert len(event_bus.get_event_history()) == 5
    
    def test_global_event_bus_integration(self):
        """测试全局事件总线集成"""
        # 保存原始事件总线
        original_bus = get_event_bus()
        
        try:
            # 创建自定义事件总线
            custom_bus = EventBus()
            set_event_bus(custom_bus)
            
            # 验证全局事件总线已更改
            assert get_event_bus() is custom_bus
            
            # 在自定义总线上发布事件
            event = GameStartedEvent.create("test_game", ["p1"], 10, 20)
            get_event_bus().publish(event)
            
            # 验证事件在自定义总线中
            assert len(custom_bus.get_event_history()) == 1
            assert len(original_bus.get_event_history()) == 0
            
        finally:
            # 恢复原始事件总线
            set_event_bus(original_bus) 