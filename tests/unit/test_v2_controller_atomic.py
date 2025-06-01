"""
Unit tests for atomic transaction decorator in v2 controller.

Tests the atomic decorator's rollback functionality when exceptions occur.
"""

import pytest
from unittest.mock import Mock, patch

from v2.controller import PokerController
from v2.controller.decorators import atomic
from v2.core import GameState, Player, Action, ActionType, SeatStatus
from v2.ai import SimpleAI


class TestAtomicDecorator:
    """Test cases for the atomic decorator."""
    
    def test_atomic_decorator_success(self):
        """Test that atomic decorator doesn't interfere with successful operations."""
        # Create a controller with test data
        game_state = GameState()
        player1 = Player(seat_id=1, name="Player1", chips=100)
        player2 = Player(seat_id=2, name="Player2", chips=100)
        game_state.add_player(player1)
        game_state.add_player(player2)
        
        controller = PokerController(game_state=game_state)
        
        # Start a hand
        controller.start_new_hand()
        
        # Get initial state
        initial_snapshot = controller.get_snapshot()
        initial_pot = initial_snapshot.pot
        
        # Execute a valid action
        action = Action(player_id=1, action_type=ActionType.FOLD)
        result = controller.execute_action(action)
        
        # Verify success
        assert result is True
        
        # Verify state changed (player folded)
        final_snapshot = controller.get_snapshot()
        player1_final = final_snapshot.get_player_by_seat(1)
        assert player1_final.status == SeatStatus.FOLDED
        
    def test_atomic_decorator_rollback_on_exception(self):
        """Test that atomic decorator rolls back state when exception occurs."""
        # Create a controller with test data
        game_state = GameState()
        player1 = Player(seat_id=1, name="Player1", chips=100)
        player2 = Player(seat_id=2, name="Player2", chips=100)
        game_state.add_player(player1)
        game_state.add_player(player2)
        
        controller = PokerController(game_state=game_state)
        
        # Start a hand
        controller.start_new_hand()
        
        # Get initial state
        initial_snapshot = controller.get_snapshot()
        initial_events_count = len(initial_snapshot.events)
        
        # Mock _apply_action to raise an exception
        with patch.object(controller, '_apply_action', side_effect=RuntimeError("Test error")):
            # Try to execute an action that will fail
            action = Action(player_id=1, action_type=ActionType.FOLD)
            
            with pytest.raises(RuntimeError, match="Test error"):
                controller.execute_action(action)
        
        # Verify state was rolled back
        final_snapshot = controller.get_snapshot()
        
        # Player should still be active (not folded)
        player1_final = final_snapshot.get_player_by_seat(1)
        assert player1_final.status == SeatStatus.ACTIVE
        
        # Should have a rollback event
        assert len(final_snapshot.events) > initial_events_count
        rollback_events = [e for e in final_snapshot.events if "rolled back" in e]
        assert len(rollback_events) > 0
        
    def test_atomic_decorator_validation_error_rollback(self):
        """Test rollback when validation fails."""
        # Create a controller with test data
        game_state = GameState()
        player1 = Player(seat_id=1, name="Player1", chips=100)
        player2 = Player(seat_id=2, name="Player2", chips=100)
        game_state.add_player(player1)
        game_state.add_player(player2)
        
        controller = PokerController(game_state=game_state)
        
        # Start a hand
        controller.start_new_hand()
        
        # Get initial state
        initial_snapshot = controller.get_snapshot()
        
        # Try to execute an invalid action (wrong player)
        action = Action(player_id=999, action_type=ActionType.FOLD)
        
        with pytest.raises(ValueError):
            controller.execute_action(action)
        
        # Verify state was rolled back
        final_snapshot = controller.get_snapshot()
        
        # Game state should be unchanged except for rollback event
        assert final_snapshot.phase == initial_snapshot.phase
        assert final_snapshot.current_bet == initial_snapshot.current_bet
        
        # Should have a rollback event
        rollback_events = [e for e in final_snapshot.events if "rolled back" in e]
        assert len(rollback_events) > 0


class TestAtomicDecoratorRequirements:
    """Test atomic decorator requirements and error handling."""
    
    def test_atomic_decorator_requires_game_state_attribute(self):
        """Test that atomic decorator requires _game_state attribute."""
        
        class TestClass:
            @atomic
            def test_method(self):
                return True
        
        test_obj = TestClass()
        
        with pytest.raises(AttributeError, match="_game_state"):
            test_obj.test_method()
            
    def test_atomic_decorator_requires_correct_type(self):
        """Test that atomic decorator requires GameState type."""
        
        class TestClass:
            def __init__(self):
                self._game_state = "not a GameState"
            
            @atomic
            def test_method(self):
                return True
        
        test_obj = TestClass()
        
        with pytest.raises(TypeError, match="GameState"):
            test_obj.test_method()


class TestControllerWithAI:
    """Test controller with AI strategy and atomic operations."""
    
    def test_ai_action_with_atomic_rollback(self):
        """Test that AI actions are also protected by atomic decorator."""
        # Create a controller with AI
        game_state = GameState()
        player1 = Player(seat_id=1, name="Human", chips=100)
        player2 = Player(seat_id=2, name="AI", chips=100)
        game_state.add_player(player1)
        game_state.add_player(player2)
        
        ai_strategy = SimpleAI()
        controller = PokerController(game_state=game_state, ai_strategy=ai_strategy)
        
        # Start a hand
        controller.start_new_hand()
        
        # Get initial state
        initial_snapshot = controller.get_snapshot()
        
        # Mock AI to make a decision, but make execution fail
        with patch.object(controller, '_apply_action', side_effect=RuntimeError("AI action failed")):
            # Process AI action should fail and rollback
            result = controller.process_ai_action()
            assert result is False
        
        # Verify state was rolled back
        final_snapshot = controller.get_snapshot()
        
        # Should have rollback events
        rollback_events = [e for e in final_snapshot.events if "rolled back" in e]
        assert len(rollback_events) > 0 