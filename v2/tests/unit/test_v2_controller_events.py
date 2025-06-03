"""
Tests for v2 controller event emission.

This module tests that the poker controller correctly emits events
during game operations.
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import List

from v2.core import (
    GameState, Player, Action, ActionType, EventType, GameEvent, 
    EventBus, Phase, SeatStatus
)
from v2.controller import PokerController
from v2.ai import SimpleAI


@pytest.mark.unit
@pytest.mark.fast
class TestControllerEventEmission:
    """Test that controller emits events correctly."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.event_bus = EventBus()
        self.game_state = GameState()
        self.controller = PokerController(
            game_state=self.game_state,
            event_bus=self.event_bus
        )
        
        # Add test players
        self.game_state.add_player(Player(seat_id=0, name="Player1", chips=1000))
        self.game_state.add_player(Player(seat_id=1, name="Player2", chips=1000))
        
        # Event collector
        self.received_events = []
        
        def event_collector(event: GameEvent):
            self.received_events.append(event)
            
        # Subscribe to all event types
        for event_type in EventType:
            self.event_bus.subscribe(event_type, event_collector)
            
    @pytest.mark.unit
    @pytest.mark.fast
    def test_hand_started_event(self):
        """Test that HAND_STARTED event is emitted when starting a new hand."""
        # Start new hand
        result = self.controller.start_new_hand()
        assert result is True
        
        # Check that HAND_STARTED event was emitted
        hand_started_events = [e for e in self.received_events if e.event_type == EventType.HAND_STARTED]
        assert len(hand_started_events) == 1
        
        event = hand_started_events[0]
        assert event.data["active_players"] == 2
        assert "dealer_position" in event.data
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_blinds_posted_event(self):
        """Test that BLINDS_POSTED event is emitted when posting blinds."""
        # Start new hand (which posts blinds)
        self.controller.start_new_hand()
        
        # Check that BLINDS_POSTED event was emitted
        blinds_events = [e for e in self.received_events if e.event_type == EventType.BLINDS_POSTED]
        assert len(blinds_events) == 1
        
        event = blinds_events[0]
        assert "small_blind_player_id" in event.data
        assert "small_blind_amount" in event.data
        assert "big_blind_player_id" in event.data
        assert "big_blind_amount" in event.data
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_player_action_events(self):
        """Test that player action events are emitted correctly."""
        # Start new hand
        self.controller.start_new_hand()
        self.received_events.clear()  # Clear setup events
        
        # Get current player
        current_player_id = self.controller.get_current_player_id()
        assert current_player_id is not None
        
        # Execute a call action (since there's a big blind bet)
        call_action = Action(player_id=current_player_id, action_type=ActionType.CALL)
        self.controller.execute_action(call_action)
        
        # Check that PLAYER_ACTION event was emitted
        action_events = [e for e in self.received_events if e.event_type == EventType.PLAYER_ACTION]
        assert len(action_events) == 1
        
        event = action_events[0]
        assert event.data["player_id"] == current_player_id
        assert event.data["action_type"] == "call"
        assert event.data["amount"] > 0  # Should be calling the big blind
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_player_fold_event(self):
        """Test that PLAYER_FOLDED event is emitted when player folds."""
        # Start new hand
        self.controller.start_new_hand()
        self.received_events.clear()
        
        # Get current player and fold
        current_player_id = self.controller.get_current_player_id()
        fold_action = Action(player_id=current_player_id, action_type=ActionType.FOLD)
        self.controller.execute_action(fold_action)
        
        # Check that PLAYER_FOLDED event was emitted
        fold_events = [e for e in self.received_events if e.event_type == EventType.PLAYER_FOLDED]
        assert len(fold_events) == 1
        
        event = fold_events[0]
        assert event.data["player_id"] == current_player_id
        assert "player_name" in event.data
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_bet_placed_event(self):
        """Test that BET_PLACED event is emitted when player bets."""
        # Start new hand
        self.controller.start_new_hand()
        self.received_events.clear()
        
        # Get current player and make a raise (since there's already a big blind bet)
        current_player_id = self.controller.get_current_player_id()
        raise_action = Action(player_id=current_player_id, action_type=ActionType.RAISE, amount=100)
        self.controller.execute_action(raise_action)
        
        # Check that BET_PLACED event was emitted
        bet_events = [e for e in self.received_events if e.event_type == EventType.BET_PLACED]
        assert len(bet_events) == 1
        
        event = bet_events[0]
        assert event.data["player_id"] == current_player_id
        assert event.data["action_type"] == "raise"
        assert "amount" in event.data
        assert "new_current_bet" in event.data
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_pot_updated_event(self):
        """Test that POT_UPDATED event is emitted after player actions."""
        # Start new hand
        self.controller.start_new_hand()
        self.received_events.clear()
        
        # Execute a call action
        current_player_id = self.controller.get_current_player_id()
        call_action = Action(player_id=current_player_id, action_type=ActionType.CALL)
        self.controller.execute_action(call_action)
        
        # Check that POT_UPDATED event was emitted
        pot_events = [e for e in self.received_events if e.event_type == EventType.POT_UPDATED]
        assert len(pot_events) == 1
        
        event = pot_events[0]
        assert "pot_amount" in event.data
        assert "current_bet" in event.data
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_in_event(self):
        """Test that PLAYER_ALL_IN event is emitted when player goes all-in."""
        # Start new hand
        self.controller.start_new_hand()
        self.received_events.clear()
        
        # Get current player and go all-in
        current_player_id = self.controller.get_current_player_id()
        player = self.game_state.get_player_by_seat(current_player_id)
        all_in_action = Action(player_id=current_player_id, action_type=ActionType.ALL_IN)
        self.controller.execute_action(all_in_action)
        
        # Check that PLAYER_ALL_IN event was emitted
        all_in_events = [e for e in self.received_events if e.event_type == EventType.PLAYER_ALL_IN]
        assert len(all_in_events) == 1
        
        event = all_in_events[0]
        assert event.data["player_id"] == current_player_id
        assert "amount" in event.data
        assert "new_current_bet" in event.data
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_hand_ended_event(self):
        """Test that HAND_ENDED event is emitted when hand ends."""
        # Start new hand
        self.controller.start_new_hand()
        
        # End the hand
        result = self.controller.end_hand()
        assert result is not None
        
        # Check that HAND_ENDED event was emitted
        hand_ended_events = [e for e in self.received_events if e.event_type == EventType.HAND_ENDED]
        assert len(hand_ended_events) == 1
        
        event = hand_ended_events[0]
        assert "winner_ids" in event.data
        assert "pot_amount" in event.data
        assert "winning_hand_description" in event.data
        assert "side_pots" in event.data
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_phase_transition_events(self):
        """Test that phase transition events are emitted correctly."""
        # Add more players to ensure we can progress through phases
        self.game_state.add_player(Player(seat_id=2, name="Player3", chips=1000))
        self.game_state.add_player(Player(seat_id=3, name="Player4", chips=1000))
        
        # Start new hand
        self.controller.start_new_hand()
        self.received_events.clear()
        
        # Make all players call to advance to next phase
        while self.controller.get_current_player_id() is not None:
            current_player_id = self.controller.get_current_player_id()
            if current_player_id is None:
                break
                
            # Call or check to keep the hand going
            action = Action(player_id=current_player_id, action_type=ActionType.CALL)
            try:
                self.controller.execute_action(action)
            except ValueError:
                # If call is not valid, try check
                action = Action(player_id=current_player_id, action_type=ActionType.CHECK)
                self.controller.execute_action(action)
                
            # Break if we've gone through all players once
            if len([e for e in self.received_events if e.event_type == EventType.PLAYER_ACTION]) >= 4:
                break
        
        # Check for phase change events
        phase_events = [e for e in self.received_events if e.event_type == EventType.PHASE_CHANGED]
        if phase_events:  # Phase change might occur
            event = phase_events[0]
            assert "from_phase" in event.data
            assert "to_phase" in event.data
            
        # Check for cards dealt events
        cards_events = [e for e in self.received_events if e.event_type == EventType.CARDS_DEALT]
        if cards_events:  # Cards might be dealt
            event = cards_events[0]
            assert "phase" in event.data
            assert "cards_count" in event.data
            assert "community_cards_count" in event.data
            
    @pytest.mark.unit
    @pytest.mark.fast
    def test_event_order(self):
        """Test that events are emitted in the correct order."""
        # Start new hand
        self.controller.start_new_hand()
        
        # Check that HAND_STARTED comes before BLINDS_POSTED
        hand_started_index = None
        blinds_posted_index = None
        
        for i, event in enumerate(self.received_events):
            if event.event_type == EventType.HAND_STARTED and hand_started_index is None:
                hand_started_index = i
            elif event.event_type == EventType.BLINDS_POSTED and blinds_posted_index is None:
                blinds_posted_index = i
                
        assert hand_started_index is not None, "HAND_STARTED event not found"
        assert blinds_posted_index is not None, "BLINDS_POSTED event not found"
        assert hand_started_index < blinds_posted_index, f"HAND_STARTED at {hand_started_index}, BLINDS_POSTED at {blinds_posted_index}"
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_event_data_consistency(self):
        """Test that event data is consistent and complete."""
        # Start new hand
        self.controller.start_new_hand()
        
        # Check all events have required fields
        for event in self.received_events:
            assert event.event_type is not None
            assert event.data is not None
            assert event.timestamp is not None
            assert isinstance(event.data, dict)
            
    @pytest.mark.unit
    @pytest.mark.fast
    def test_multiple_listeners(self):
        """Test that multiple listeners receive the same events."""
        # Add another event collector
        received_events_2 = []
        
        def event_collector_2(event: GameEvent):
            received_events_2.append(event)
            
        # Subscribe second collector to hand events
        self.event_bus.subscribe(EventType.HAND_STARTED, event_collector_2)
        
        # Start new hand
        self.controller.start_new_hand()
        
        # Both collectors should receive HAND_STARTED event
        hand_events_1 = [e for e in self.received_events if e.event_type == EventType.HAND_STARTED]
        hand_events_2 = received_events_2
        
        assert len(hand_events_1) == 1
        assert len(hand_events_2) == 1
        assert hand_events_1[0].event_type == hand_events_2[0].event_type
        assert hand_events_1[0].data == hand_events_2[0].data 