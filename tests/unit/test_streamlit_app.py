#!/usr/bin/env python3
"""
Unit tests for Streamlit application.

Tests the core functionality of the Streamlit web interface without
actually running the Streamlit server.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from v2.ui.streamlit.app import (
    initialize_session_state,
    render_header,
    render_game_state,
    process_ai_actions_continuously,
    run_auto_play_test
)
from v2.controller.poker_controller import PokerController
from v2.core.state import GameState
from v2.core.enums import Phase, ActionType, SeatStatus
from v2.core.cards import Card, Suit, Rank
from v2.controller.dto import GameStateSnapshot, PlayerSnapshot


class TestStreamlitApp:
    """Test cases for Streamlit application functions."""
    
    @patch('v2.ui.streamlit.app.st')
    def test_initialize_session_state(self, mock_st):
        """测试 session state 初始化."""
        # Mock session_state as a proper object with attribute access
        mock_session_state = Mock()
        mock_st.session_state = mock_session_state
        
        # Call function
        initialize_session_state()
        
        # Verify session state was initialized
        assert hasattr(mock_session_state, 'controller')
        assert hasattr(mock_session_state, 'game_started')
        assert hasattr(mock_session_state, 'events')
        assert hasattr(mock_session_state, 'debug_mode')
        
        assert isinstance(mock_session_state.controller, PokerController)
        assert mock_session_state.game_started is False
        assert mock_session_state.events == []
        assert mock_session_state.debug_mode is False
    
    @patch('v2.ui.streamlit.app.st')
    def test_render_header(self, mock_st):
        """测试页面头部渲染."""
        render_header()
        
        # Verify title and markdown were called
        mock_st.title.assert_called_once_with("🃏 德州扑克 Texas Hold'em")
        mock_st.markdown.assert_called_once_with("---")
    
    @patch('v2.ui.streamlit.app.st')
    def test_render_game_state_no_snapshot(self, mock_st):
        """测试无游戏状态时的渲染."""
        render_game_state(None)
        
        # Should show info message
        mock_st.info.assert_called_once_with("点击 '开始新手牌' 开始游戏")
    
    @patch('v2.ui.streamlit.app.st')
    def test_render_game_state_with_snapshot(self, mock_st):
        """测试有游戏状态时的渲染."""
        # Create mock snapshot
        player1 = PlayerSnapshot(
            seat_id=0,  # 使用正确的字段名
            name="Player 1",
            chips=1000,
            current_bet=50,
            status=SeatStatus.ACTIVE,
            hole_cards=[
                Card(Suit.HEARTS, Rank.ACE),
                Card(Suit.SPADES, Rank.KING)
            ]
        )
        
        player2 = PlayerSnapshot(
            seat_id=1,  # 使用正确的字段名
            name="AI Player",
            chips=950,
            current_bet=50,
            status=SeatStatus.ACTIVE,
            hole_cards=[]
        )
        
        snapshot = GameStateSnapshot(
            phase=Phase.FLOP,
            pot=100,
            current_bet=50,
            current_player=0,
            players=[player1, player2],
            community_cards=[
                Card(Suit.HEARTS, Rank.TWO),
                Card(Suit.DIAMONDS, Rank.THREE),
                Card(Suit.CLUBS, Rank.FOUR)
            ],
            dealer_position=0,
            small_blind=5,
            big_blind=10,
            hand_number=1
        )
        
        # Mock columns
        mock_columns = [Mock(), Mock(), Mock()]
        mock_st.columns.return_value = mock_columns
        
        # Mock expander
        mock_expander = Mock()
        mock_st.expander.return_value.__enter__ = Mock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = Mock(return_value=None)
        
        render_game_state(snapshot)
        
        # Verify columns were created
        mock_st.columns.assert_called()
        
        # Verify subheader was called for phase
        assert any("当前阶段" in str(call) for call in mock_st.subheader.call_args_list)
        
        # Verify metric was called for pot
        assert any("底池" in str(call) for call in mock_st.metric.call_args_list)
    
    def test_process_ai_actions_continuously(self):
        """测试连续AI行动处理."""
        # Create mock controller
        mock_controller = Mock()
        
        # Test case 1: No current player
        mock_controller.get_current_player_id.return_value = None
        result = process_ai_actions_continuously(mock_controller)
        assert result is False
        
        # Test case 2: Human player turn
        mock_controller.get_current_player_id.return_value = 0
        result = process_ai_actions_continuously(mock_controller)
        assert result is False
        
        # Test case 3: AI player processes action
        mock_controller.get_current_player_id.side_effect = [1, 0]  # AI then human
        mock_controller.is_hand_over.return_value = False
        mock_controller.process_ai_action.return_value = True
        
        result = process_ai_actions_continuously(mock_controller)
        assert result is True
        mock_controller.process_ai_action.assert_called_once()
    
    @patch('v2.ui.streamlit.app.st')
    def test_run_auto_play_test(self, mock_st):
        """测试自动游戏测试功能."""
        # Create mock controller
        mock_controller = Mock()
        
        # Mock initial snapshot with proper player objects
        player1 = Mock()
        player1.chips = 1000
        player2 = Mock()
        player2.chips = 1000
        
        initial_snapshot = Mock()
        initial_snapshot.players = [player1, player2]
        
        # Mock final snapshot
        final_snapshot = Mock()
        final_snapshot.players = [player1, player2]  # Same players, same chips
        
        mock_controller.get_snapshot.side_effect = [initial_snapshot, final_snapshot]
        
        # Mock game flow
        mock_controller.start_new_hand.return_value = True
        mock_controller.is_hand_over.side_effect = [False, False, True]  # Two actions then end
        mock_controller.get_current_player_id.side_effect = [0, 1, None]  # Human, AI, end
        mock_controller.process_ai_action.return_value = True
        mock_controller.execute_action.return_value = True
        mock_controller.end_hand.return_value = Mock()
        
        # Mock session state
        mock_st.session_state.controller = mock_controller
        
        results = run_auto_play_test(1)
        
        # Verify results
        assert results["hands_played"] == 1
        assert results["total_chips_start"] == 2000
        assert results["total_chips_end"] == 2000
        assert results["chip_conservation"] is True
        assert len(results["errors"]) == 0
    
    @patch('v2.ui.streamlit.app.st')
    def test_run_auto_play_test_with_errors(self, mock_st):
        """测试自动游戏测试错误处理."""
        # Create mock controller that fails
        mock_controller = Mock()
        mock_controller.start_new_hand.return_value = False
        
        # Mock session state
        mock_st.session_state.controller = mock_controller
        
        results = run_auto_play_test(1)
        
        # Verify error was recorded
        assert results["hands_played"] == 0
        assert len(results["errors"]) > 0
        assert "Failed to start" in results["errors"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 