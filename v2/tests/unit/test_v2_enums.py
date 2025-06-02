"""
Unit tests for v2 core enumerations.

Tests the enumeration classes and utility functions in v2.core.enums.
"""

import pytest
from v2.core.enums import (
    Suit, Rank, HandRank, ActionType, Phase, SeatStatus,
    GameEventType, ValidationResult,
    get_all_suits, get_all_ranks, get_valid_actions
)


class TestSuit:
    """Test cases for Suit enumeration."""
    
    def test_suit_values(self):
        """Test that suit values are correct Unicode symbols."""
        assert Suit.HEARTS.value == "♥"
        assert Suit.DIAMONDS.value == "♦"
        assert Suit.CLUBS.value == "♣"
        assert Suit.SPADES.value == "♠"
    
    def test_suit_count(self):
        """Test that there are exactly 4 suits."""
        assert len(list(Suit)) == 4


class TestRank:
    """Test cases for Rank enumeration."""
    
    def test_rank_values(self):
        """Test that rank values are correct integers."""
        assert Rank.TWO == 2
        assert Rank.THREE == 3
        assert Rank.ACE == 14
    
    def test_rank_comparison(self):
        """Test that ranks can be compared correctly."""
        assert Rank.TWO < Rank.THREE
        assert Rank.KING < Rank.ACE
        assert Rank.ACE > Rank.KING
    
    def test_rank_count(self):
        """Test that there are exactly 13 ranks."""
        assert len(list(Rank)) == 13


class TestHandRank:
    """Test cases for HandRank enumeration."""
    
    def test_hand_rank_order(self):
        """Test that hand ranks are in correct order."""
        assert HandRank.HIGH_CARD < HandRank.ONE_PAIR
        assert HandRank.ONE_PAIR < HandRank.TWO_PAIR
        assert HandRank.STRAIGHT_FLUSH < HandRank.ROYAL_FLUSH
        assert HandRank.ROYAL_FLUSH == 10
    
    def test_hand_rank_count(self):
        """Test that there are exactly 10 hand ranks."""
        assert len(list(HandRank)) == 10


class TestActionType:
    """Test cases for ActionType enumeration."""
    
    def test_action_values(self):
        """Test that action values are correct strings."""
        assert ActionType.FOLD.value == "fold"
        assert ActionType.CHECK.value == "check"
        assert ActionType.CALL.value == "call"
        assert ActionType.BET.value == "bet"
        assert ActionType.RAISE.value == "raise"
        assert ActionType.ALL_IN.value == "all_in"
    
    def test_action_count(self):
        """Test that there are exactly 6 action types."""
        assert len(list(ActionType)) == 6


class TestPhase:
    """Test cases for Phase enumeration."""
    
    def test_phase_values(self):
        """Test that phase values are correct strings."""
        assert Phase.PRE_FLOP.value == "pre_flop"
        assert Phase.FLOP.value == "flop"
        assert Phase.TURN.value == "turn"
        assert Phase.RIVER.value == "river"
        assert Phase.SHOWDOWN.value == "showdown"
    
    def test_phase_count(self):
        """Test that there are exactly 5 phases."""
        assert len(list(Phase)) == 5


class TestSeatStatus:
    """Test cases for SeatStatus enumeration."""
    
    def test_seat_status_values(self):
        """Test that seat status values are correct strings."""
        assert SeatStatus.ACTIVE.value == "active"
        assert SeatStatus.FOLDED.value == "folded"
        assert SeatStatus.ALL_IN.value == "all_in"
        assert SeatStatus.OUT.value == "out"
        assert SeatStatus.SITTING_OUT.value == "sitting_out"
    
    def test_seat_status_count(self):
        """Test that there are exactly 5 seat statuses."""
        assert len(list(SeatStatus)) == 5


class TestGameEventType:
    """Test cases for GameEventType enumeration."""
    
    def test_event_type_values(self):
        """Test that event type values are correct strings."""
        assert GameEventType.HAND_STARTED.value == "hand_started"
        assert GameEventType.CARDS_DEALT.value == "cards_dealt"
        assert GameEventType.PHASE_CHANGED.value == "phase_changed"
        assert GameEventType.PLAYER_ACTION.value == "player_action"
        assert GameEventType.POT_AWARDED.value == "pot_awarded"
        assert GameEventType.HAND_ENDED.value == "hand_ended"
        assert GameEventType.GAME_ENDED.value == "game_ended"
    
    def test_event_type_count(self):
        """Test that there are exactly 7 event types."""
        assert len(list(GameEventType)) == 7


class TestValidationResult:
    """Test cases for ValidationResult enumeration."""
    
    def test_validation_result_values(self):
        """Test that validation result values are correct strings."""
        assert ValidationResult.VALID.value == "valid"
        assert ValidationResult.INVALID_AMOUNT.value == "invalid_amount"
        assert ValidationResult.INSUFFICIENT_CHIPS.value == "insufficient_chips"
        assert ValidationResult.OUT_OF_TURN.value == "out_of_turn"
        assert ValidationResult.INVALID_ACTION.value == "invalid_action"
        assert ValidationResult.GAME_NOT_ACTIVE.value == "game_not_active"
    
    def test_validation_result_count(self):
        """Test that there are exactly 6 validation results."""
        assert len(list(ValidationResult)) == 6


class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_get_all_suits(self):
        """Test get_all_suits function."""
        suits = get_all_suits()
        assert len(suits) == 4
        assert all(isinstance(suit, Suit) for suit in suits)
        assert Suit.HEARTS in suits
        assert Suit.DIAMONDS in suits
        assert Suit.CLUBS in suits
        assert Suit.SPADES in suits
    
    def test_get_all_ranks(self):
        """Test get_all_ranks function."""
        ranks = get_all_ranks()
        assert len(ranks) == 13
        assert all(isinstance(rank, Rank) for rank in ranks)
        assert Rank.TWO in ranks
        assert Rank.ACE in ranks
    
    def test_get_valid_actions(self):
        """Test get_valid_actions function."""
        actions = get_valid_actions()
        assert len(actions) == 6
        assert all(isinstance(action, ActionType) for action in actions)
        assert ActionType.FOLD in actions
        assert ActionType.ALL_IN in actions 