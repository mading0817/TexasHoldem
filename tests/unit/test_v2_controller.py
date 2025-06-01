"""
德州扑克控制器单元测试.

测试控制器的核心功能，包括游戏流程控制、行动处理、状态管理等。
"""

import pytest
import logging
from unittest.mock import Mock, patch

from v2.controller import PokerController, HandResult
from v2.ai import AIStrategy, SimpleAI
from v2.core import GameState, Player, Action, ActionType, SeatStatus, Phase
from v2.core.events import EventBus, EventType


class TestPokerController:
    """Test the PokerController class."""
    
    def test_controller_initialization(self):
        """Test controller initialization with default parameters."""
        controller = PokerController()
        
        assert controller._game_state is not None
        assert controller._ai_strategy is None
        assert controller._logger is not None
        assert controller._validator is not None
        assert controller._hand_in_progress is False
    
    def test_controller_initialization_with_custom_params(self):
        """Test controller initialization with custom parameters."""
        game_state = GameState()
        ai_strategy = Mock(spec=AIStrategy)
        logger = logging.getLogger("test")
        
        controller = PokerController(game_state, ai_strategy, logger)
        
        assert controller._game_state is game_state
        assert controller._ai_strategy is ai_strategy
        assert controller._logger is logger
    
    def test_start_new_hand_insufficient_players(self):
        """Test starting new hand with insufficient players."""
        controller = PokerController()
        
        # 只添加一个玩家
        player = Player(0, "Test Player", 1000)
        controller._game_state.add_player(player)
        
        result = controller.start_new_hand()
        assert result is False
        assert controller._hand_in_progress is False
    
    def test_start_new_hand_success(self):
        """Test successfully starting a new hand."""
        controller = PokerController()
        
        # 添加两个玩家
        player1 = Player(0, "Player 1", 1000)
        player2 = Player(1, "Player 2", 1000)
        controller._game_state.add_player(player1)
        controller._game_state.add_player(player2)
        
        result = controller.start_new_hand()
        assert result is True
        assert controller._hand_in_progress is True
        assert controller._game_state.phase == Phase.PRE_FLOP
    
    def test_start_new_hand_already_in_progress(self):
        """Test starting new hand when one is already in progress."""
        controller = PokerController()
        controller._hand_in_progress = True
        
        with pytest.raises(RuntimeError, match="当前已有手牌在进行中"):
            controller.start_new_hand()
    
    def test_get_snapshot(self):
        """Test getting game state snapshot."""
        controller = PokerController()
        
        snapshot = controller.get_snapshot()
        
        assert snapshot is not None
        assert snapshot.phase == Phase.PRE_FLOP
        assert snapshot.pot == 0
        assert len(snapshot.players) == 0
    
    def test_is_hand_over_no_hand_in_progress(self):
        """Test is_hand_over when no hand is in progress."""
        controller = PokerController()
        
        assert controller.is_hand_over() is True
    
    def test_is_hand_over_hand_in_progress(self):
        """Test is_hand_over when hand is in progress."""
        controller = PokerController()
        controller._hand_in_progress = True
        
        # 添加两个活跃玩家
        player1 = Player(0, "Player 1", 1000)
        player2 = Player(1, "Player 2", 1000)
        controller._game_state.add_player(player1)
        controller._game_state.add_player(player2)
        
        assert controller.is_hand_over() is False
    
    def test_get_current_player_id_no_hand(self):
        """Test getting current player ID when no hand is in progress."""
        controller = PokerController()
        
        assert controller.get_current_player_id() is None
    
    def test_get_current_player_id_with_hand(self):
        """Test getting current player ID when hand is in progress."""
        controller = PokerController()
        controller._hand_in_progress = True
        
        # 添加玩家以确保is_hand_over返回False
        player1 = Player(0, "Player 1", 1000)
        player2 = Player(1, "Player 2", 1000)
        controller._game_state.add_player(player1)
        controller._game_state.add_player(player2)
        
        controller._game_state.current_player = 0
        
        assert controller.get_current_player_id() == 0
    
    def test_execute_action_no_hand_in_progress(self):
        """Test executing action when no hand is in progress."""
        controller = PokerController()
        action = Action(ActionType.FOLD, 0, 0)
        
        with pytest.raises(RuntimeError, match="当前没有手牌在进行中"):
            controller.execute_action(action)
    
    def test_process_ai_action_no_strategy(self):
        """Test processing AI action without strategy."""
        controller = PokerController()
        controller._hand_in_progress = True
        controller._game_state.current_player = 0
        
        result = controller.process_ai_action()
        assert result is False
    
    def test_process_ai_action_no_current_player(self):
        """Test processing AI action without current player."""
        controller = PokerController()
        ai_strategy = Mock(spec=AIStrategy)
        controller._ai_strategy = ai_strategy
        
        result = controller.process_ai_action()
        assert result is False
    
    def test_end_hand_no_hand_in_progress(self):
        """Test ending hand when no hand is in progress."""
        controller = PokerController()
        
        result = controller.end_hand()
        assert result is None
    
    def test_end_hand_success(self):
        """Test successfully ending a hand."""
        controller = PokerController()
        controller._hand_in_progress = True
        controller._game_state.pot = 100
        
        result = controller.end_hand()
        
        assert result is not None
        assert isinstance(result, HandResult)
        assert result.pot_amount == 100
        assert controller._hand_in_progress is False


class TestAIStrategy:
    """Test the AIStrategy protocol."""
    
    def test_ai_strategy_protocol(self):
        """Test that AIStrategy is a proper protocol."""
        # 创建一个实现AIStrategy的类
        class TestAI:
            def decide(self, game_snapshot, player_id):
                return Action(ActionType.FOLD, 0, player_id)
        
        ai = TestAI()
        assert isinstance(ai, AIStrategy)
    
    def test_ai_strategy_mock(self):
        """Test using mock for AIStrategy."""
        ai_mock = Mock(spec=AIStrategy)
        ai_mock.decide.return_value = Action(ActionType.FOLD, 0, 0)
        
        # 验证mock可以正常调用
        action = ai_mock.decide(None, 0)
        assert action.action_type == ActionType.FOLD


class TestHandResult:
    """Test the HandResult dataclass."""
    
    def test_hand_result_creation(self):
        """Test creating HandResult instance."""
        result = HandResult(
            winner_ids=[0, 1],
            pot_amount=200,
            winning_hand_description="Two Pair",
            side_pots=[{"amount": 100, "players": [0, 1]}]
        )
        
        assert result.winner_ids == [0, 1]
        assert result.pot_amount == 200
        assert result.winning_hand_description == "Two Pair"
        assert len(result.side_pots) == 1
    
    def test_hand_result_immutable(self):
        """Test that HandResult is immutable."""
        result = HandResult(
            winner_ids=[0],
            pot_amount=100,
            winning_hand_description="High Card",
            side_pots=[]
        )
        
        # 尝试修改应该失败
        with pytest.raises(AttributeError):
            result.pot_amount = 200 