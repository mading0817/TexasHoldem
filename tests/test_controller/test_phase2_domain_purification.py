"""
Phase 2 Domain纯化测试
验证核心逻辑已成功下沉到Domain层
"""

import pytest
from unittest.mock import Mock, MagicMock

from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.core.enums import GamePhase, ActionType
from core_game_logic.phases import PreFlopPhase, FlopPhase, TurnPhase, RiverPhase, ShowdownPhase
from app_controller.poker_controller import PokerController
from app_controller.dto_models import PlayerActionInput


class TestPhase2DomainPurification:
    """测试Domain纯化的实现"""
    
    def setup_method(self):
        """每个测试前的设置"""
        # 创建基础游戏状态
        players = [
            Player(seat_id=0, name="Human", chips=1000),
            Player(seat_id=1, name="AI1", chips=1000),
            Player(seat_id=2, name="AI2", chips=1000)
        ]
        
        self.state = GameState(
            players=players,
            small_blind=10,
            big_blind=20,
            dealer_position=0
        )
        
        self.controller = PokerController(self.state)
    
    def test_phase_has_process_betting_round_method(self):
        """测试所有Phase类都实现了process_betting_round方法"""
        # 测试PreFlopPhase
        preflop = PreFlopPhase(self.state)
        assert hasattr(preflop, 'process_betting_round')
        assert callable(preflop.process_betting_round)
        
        # 测试FlopPhase
        flop = FlopPhase(self.state)
        assert hasattr(flop, 'process_betting_round')
        assert callable(flop.process_betting_round)
        
        # 测试TurnPhase
        turn = TurnPhase(self.state)
        assert hasattr(turn, 'process_betting_round')
        assert callable(turn.process_betting_round)
        
        # 测试RiverPhase
        river = RiverPhase(self.state)
        assert hasattr(river, 'process_betting_round')
        assert callable(river.process_betting_round)
        
        # 测试ShowdownPhase
        showdown = ShowdownPhase(self.state)
        assert hasattr(showdown, 'process_betting_round')
        assert callable(showdown.process_betting_round)
    
    def test_controller_delegates_to_phase(self):
        """测试Controller正确委托给Phase层处理下注轮"""
        # 设置游戏状态为翻牌前
        self.state.phase = GamePhase.PRE_FLOP
        
        # 创建模拟回调
        mock_callback = Mock()
        mock_callback.return_value = PlayerActionInput(
            seat_id=0,
            action_type=ActionType.FOLD
        )
        
        # 调用Controller的process_betting_round
        result = self.controller.process_betting_round(mock_callback)
        
        # 验证结果
        assert result.success
        assert "下注轮完成" in result.message
    
    def test_phase_callback_adaptation(self):
        """测试Controller正确适配回调函数格式"""
        # 设置游戏状态
        self.state.phase = GamePhase.PRE_FLOP
        
        # 创建模拟回调，验证参数格式
        def mock_callback(seat_id, snapshot):
            # 验证参数类型
            assert isinstance(seat_id, int)
            assert hasattr(snapshot, 'phase')  # 验证是GameStateSnapshot
            
            return PlayerActionInput(
                seat_id=seat_id,
                action_type=ActionType.FOLD
            )
        
        # 调用Controller的process_betting_round
        result = self.controller.process_betting_round(mock_callback)
        
        # 验证结果
        assert result.success
    
    def test_get_current_phase_method(self):
        """测试Controller的_get_current_phase方法"""
        # 测试各个阶段
        test_phases = [
            (GamePhase.PRE_FLOP, PreFlopPhase),
            (GamePhase.FLOP, FlopPhase),
            (GamePhase.TURN, TurnPhase),
            (GamePhase.RIVER, RiverPhase),
            (GamePhase.SHOWDOWN, ShowdownPhase)
        ]
        
        for phase_enum, expected_class in test_phases:
            self.state.phase = phase_enum
            current_phase = self.controller._get_current_phase()
            
            assert current_phase is not None
            assert isinstance(current_phase, expected_class)
            assert current_phase.state is self.state
    
    def test_showdown_phase_special_handling(self):
        """测试ShowdownPhase的特殊处理（不需要下注轮）"""
        # 设置为摊牌阶段
        self.state.phase = GamePhase.SHOWDOWN
        showdown = ShowdownPhase(self.state)
        
        # 创建模拟回调（不应该被调用）
        mock_callback = Mock()
        
        # 调用process_betting_round
        events = showdown.process_betting_round(mock_callback)
        
        # 验证结果
        assert events == []  # 摊牌阶段返回空事件列表
        assert not mock_callback.called  # 回调不应该被调用
    
    def test_domain_logic_separation(self):
        """测试Domain逻辑与Controller的分离"""
        # 验证Controller不再包含具体的下注轮逻辑
        controller_source = self.controller.__class__.__module__
        
        # Controller应该只是协调器，不包含具体业务逻辑
        # 这个测试验证Controller的process_betting_round方法确实委托给了Phase
        
        # 设置游戏状态
        self.state.phase = GamePhase.PRE_FLOP
        
        # 创建简单的回调
        def simple_callback(seat_id, snapshot):
            return PlayerActionInput(
                seat_id=seat_id,
                action_type=ActionType.FOLD
            )
        
        # 调用并验证委托成功
        result = self.controller.process_betting_round(simple_callback)
        assert result.success
        
        # 验证事件格式正确（从字符串转换为GameEvent对象）
        assert result.events is not None
        if result.events:
            from app_controller.dto_models import GameEvent
            assert all(isinstance(event, GameEvent) for event in result.events)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 