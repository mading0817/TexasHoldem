"""
状态机单元测试

测试游戏状态机的核心功能，包括状态转换、事件处理和阶段管理。
"""

import pytest
from typing import Dict, Any
from v3.core.state_machine import (
    GamePhase, GameEvent, GameContext, GameStateMachine, StateMachineFactory
)
from v3.core.state_machine.phase_handlers import PreFlopHandler, FlopHandler
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestGamePhase:
    """测试游戏阶段枚举"""
    
    def test_game_phase_enum_values(self):
        """测试游戏阶段枚举值"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(GamePhase.INIT, "GamePhase")
        
        # 验证所有必需的阶段都存在
        expected_phases = {
            'INIT', 'PRE_FLOP', 'FLOP', 'TURN', 'RIVER', 'SHOWDOWN', 'FINISHED'
        }
        actual_phases = {phase.name for phase in GamePhase}
        
        assert expected_phases.issubset(actual_phases), f"缺少必需的游戏阶段: {expected_phases - actual_phases}"


class TestGameEvent:
    """测试游戏事件"""
    
    def test_game_event_creation(self):
        """测试游戏事件创建"""
        event = GameEvent(
            event_type="PLAYER_FOLDED",
            data={"player_id": "player1"},
            source_phase=GamePhase.PRE_FLOP
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(event, "GameEvent")
        
        assert event.event_type == "PLAYER_FOLDED"
        assert event.data["player_id"] == "player1"
        assert event.source_phase == GamePhase.PRE_FLOP
    
    def test_game_event_immutable(self):
        """测试游戏事件不可变性"""
        event = GameEvent(
            event_type="TEST",
            data={"key": "value"},
            source_phase=GamePhase.INIT
        )
        
        # 尝试修改frozen dataclass应该失败
        with pytest.raises(AttributeError):
            event.event_type = "MODIFIED"


class TestGameContext:
    """测试游戏上下文"""
    
    def test_game_context_creation(self):
        """测试游戏上下文创建"""
        players = {"player1": {"chips": 1000}, "player2": {"chips": 1500}}
        ctx = GameContext(
            game_id="game123",
            current_phase=GamePhase.INIT,
            players=players,
            community_cards=[],
            pot_total=0,
            current_bet=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ctx, "GameContext")
        
        assert ctx.game_id == "game123"
        assert ctx.current_phase == GamePhase.INIT
        assert len(ctx.players) == 2
        assert ctx.pot_total == 0
        assert ctx.current_bet == 0
    
    def test_game_context_validation(self):
        """测试游戏上下文验证"""
        # 测试空game_id
        with pytest.raises(ValueError, match="game_id不能为空"):
            GameContext(
                game_id="",
                current_phase=GamePhase.INIT,
                players={},
                community_cards=[],
                pot_total=0,
                current_bet=0
            )
        
        # 测试负数pot_total
        with pytest.raises(ValueError, match="pot_total不能为负数"):
            GameContext(
                game_id="game123",
                current_phase=GamePhase.INIT,
                players={},
                community_cards=[],
                pot_total=-100,
                current_bet=0
            )
        
        # 测试负数current_bet
        with pytest.raises(ValueError, match="current_bet不能为负数"):
            GameContext(
                game_id="game123",
                current_phase=GamePhase.INIT,
                players={},
                community_cards=[],
                pot_total=0,
                current_bet=-50
            )


class TestGameStateMachine:
    """测试游戏状态机"""
    
    def test_state_machine_creation(self):
        """测试状态机创建"""
        state_machine = StateMachineFactory.create_default_state_machine()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(state_machine, "GameStateMachine")
        
        assert state_machine.current_phase == GamePhase.INIT
        assert len(state_machine.transition_history) == 0
    
    def test_state_machine_empty_phases_validation(self):
        """测试状态机空阶段验证"""
        with pytest.raises(ValueError, match="phases不能为空"):
            GameStateMachine({})
    
    def test_state_machine_missing_required_phases(self):
        """测试状态机缺少必需阶段"""
        incomplete_phases = {
            GamePhase.INIT: PreFlopHandler(),
            GamePhase.PRE_FLOP: PreFlopHandler()
            # 缺少其他必需阶段
        }
        
        with pytest.raises(ValueError, match="缺少必需的阶段处理器"):
            GameStateMachine(incomplete_phases)
    
    def test_basic_state_transition(self):
        """测试基本状态转换"""
        state_machine = StateMachineFactory.create_default_state_machine()
        ctx = GameContext(
            game_id="test_game",
            current_phase=GamePhase.INIT,
            players={"player1": {"chips": 1000}},
            community_cards=[],
            pot_total=0,
            current_bet=0
        )
        
        # 测试从INIT到PRE_FLOP的转换
        event = GameEvent(
            event_type="HAND_START",
            data={"new_hand": True},
            source_phase=GamePhase.INIT
        )
        
        state_machine.transition(event, ctx)
        
        assert state_machine.current_phase == GamePhase.PRE_FLOP
        assert ctx.current_phase == GamePhase.PRE_FLOP
        assert len(state_machine.transition_history) == 1
        
        # 验证转换历史
        history = state_machine.transition_history[0]
        assert history['from'] == GamePhase.INIT
        assert history['to'] == GamePhase.PRE_FLOP
        assert history['event'] == event
    
    def test_invalid_state_transition(self):
        """测试无效状态转换"""
        state_machine = StateMachineFactory.create_default_state_machine()
        ctx = GameContext(
            game_id="test_game",
            current_phase=GamePhase.INIT,
            players={"player1": {"chips": 1000}},
            community_cards=[],
            pot_total=0,
            current_bet=0
        )
        
        # 尝试从INIT直接跳转到SHOWDOWN（无效转换）
        event = GameEvent(
            event_type="INVALID_TRANSITION",
            data={},
            source_phase=GamePhase.INIT
        )
        
        # 修改_determine_target_phase的返回值来测试无效转换
        original_method = state_machine._determine_target_phase
        state_machine._determine_target_phase = lambda e, c: GamePhase.SHOWDOWN
        
        with pytest.raises(ValueError, match="不能从.*转换到.*"):
            state_machine.transition(event, ctx)
        
        # 恢复原方法
        state_machine._determine_target_phase = original_method
    
    def test_player_action_handling(self):
        """测试玩家行动处理"""
        state_machine = StateMachineFactory.create_default_state_machine()
        ctx = GameContext(
            game_id="test_game",
            current_phase=GamePhase.PRE_FLOP,
            players={"player1": {"chips": 1000}},
            community_cards=[],
            pot_total=30,
            current_bet=20
        )
        
        # 手动设置状态机到PRE_FLOP阶段
        state_machine._current_phase = GamePhase.PRE_FLOP
        
        # 测试玩家弃牌行动
        action = {"type": "fold"}
        event = state_machine.handle_player_action(ctx, "player1", action)
        
        assert event.event_type == "PLAYER_FOLDED"
        assert event.data["player_id"] == "player1"
        assert event.source_phase == GamePhase.PRE_FLOP
    
    def test_state_machine_reset(self):
        """测试状态机重置"""
        state_machine = StateMachineFactory.create_default_state_machine()
        
        # 添加一些转换历史
        state_machine._current_phase = GamePhase.FLOP
        state_machine._transition_history.append({"test": "data"})
        
        # 重置状态机
        state_machine.reset()
        
        assert state_machine.current_phase == GamePhase.INIT
        assert len(state_machine.transition_history) == 0


class TestStateMachineFactory:
    """测试状态机工厂"""
    
    def test_create_default_state_machine(self):
        """测试创建默认状态机"""
        state_machine = StateMachineFactory.create_default_state_machine()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(state_machine, "GameStateMachine")
        
        assert isinstance(state_machine, GameStateMachine)
        assert state_machine.current_phase == GamePhase.INIT
        
        # 验证所有必需的阶段处理器都存在
        required_phases = {
            GamePhase.INIT, GamePhase.PRE_FLOP, GamePhase.FLOP,
            GamePhase.TURN, GamePhase.RIVER, GamePhase.SHOWDOWN, GamePhase.FINISHED
        }
        
        for phase in required_phases:
            assert phase in state_machine._phases
    
    def test_create_custom_state_machine(self):
        """测试创建自定义状态机"""
        custom_handlers = {
            GamePhase.FLOP: FlopHandler()
        }
        
        state_machine = StateMachineFactory.create_custom_state_machine(custom_handlers)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(state_machine, "GameStateMachine")
        
        assert isinstance(state_machine, GameStateMachine)
        assert isinstance(state_machine._phases[GamePhase.FLOP], FlopHandler)


class TestPhaseTransitionLogic:
    """测试阶段转换逻辑"""
    
    def test_complete_game_flow(self):
        """测试完整的游戏流程转换"""
        state_machine = StateMachineFactory.create_default_state_machine()
        ctx = GameContext(
            game_id="test_game",
            current_phase=GamePhase.INIT,
            players={"player1": {"chips": 1000}, "player2": {"chips": 1000}},
            community_cards=[],
            pot_total=0,
            current_bet=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(state_machine, "GameStateMachine")
        
        # 测试完整的游戏流程
        transitions = [
            ("HAND_START", GamePhase.PRE_FLOP),
            ("BETTING_ROUND_COMPLETE", GamePhase.FLOP),
            ("BETTING_ROUND_COMPLETE", GamePhase.TURN),
            ("BETTING_ROUND_COMPLETE", GamePhase.RIVER),
            ("BETTING_ROUND_COMPLETE", GamePhase.SHOWDOWN),
            ("SHOWDOWN_COMPLETE", GamePhase.FINISHED)
        ]
        
        for event_type, expected_phase in transitions:
            event = GameEvent(
                event_type=event_type,
                data={},
                source_phase=state_machine.current_phase
            )
            
            state_machine.transition(event, ctx)
            assert state_machine.current_phase == expected_phase
            assert ctx.current_phase == expected_phase
        
        # 验证转换历史记录了所有转换
        assert len(state_machine.transition_history) == len(transitions) 