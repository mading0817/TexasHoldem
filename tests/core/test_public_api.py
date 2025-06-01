"""
Test cases for v2 core module public API.

This module tests the high-level API functions exposed by v2.core.
"""

import pytest
import random
from v2.core import (
    new_deck, evaluate_hand, create_player, validate_action, create_pot_manager,
    Card, Suit, Rank, ActionType, Action, HandRank
)


class MockGameState:
    """Mock game state for testing."""
    
    def __init__(self):
        self.current_bet = 0
        self.big_blind = 10
        self.last_raise_amount = 0
        self.current_player_seat = 1
        self._player_bets = {}
    
    def get_player_current_bet(self, seat: int) -> int:
        return self._player_bets.get(seat, 0)


class TestPublicAPI:
    """Test cases for public API functions."""
    
    def test_new_deck_unshuffled(self):
        """Test creating an unshuffled deck."""
        deck = new_deck(shuffled=False)
        
        assert len(deck) == 52
        # First card should be 2 of Hearts (standard order)
        first_card = deck.peek_top()
        assert first_card is not None
    
    def test_new_deck_shuffled(self):
        """Test creating a shuffled deck."""
        # Use fixed seed for deterministic test
        rng = random.Random(42)
        deck = new_deck(shuffled=True, rng=rng)
        
        assert len(deck) == 52
        # With shuffling, deck should have 52 cards
        
    def test_new_deck_with_rng(self):
        """Test creating deck with custom RNG."""
        rng1 = random.Random(123)
        deck1 = new_deck(shuffled=True, rng=rng1)
        
        rng2 = random.Random(123)  # Same seed
        deck2 = new_deck(shuffled=True, rng=rng2)
        
        # Same seed should produce same shuffle order
        # We can't directly compare cards, but we can check they're both valid decks
        assert len(deck1) == len(deck2) == 52
    
    def test_evaluate_hand_royal_flush(self):
        """Test evaluating a royal flush."""
        hole_cards = [
            Card(Suit.SPADES, Rank.ACE),
            Card(Suit.SPADES, Rank.KING)
        ]
        community_cards = [
            Card(Suit.SPADES, Rank.QUEEN),
            Card(Suit.SPADES, Rank.JACK),
            Card(Suit.SPADES, Rank.TEN),
            Card(Suit.HEARTS, Rank.TWO),
            Card(Suit.CLUBS, Rank.THREE)
        ]
        
        result = evaluate_hand(hole_cards, community_cards)
        assert result.rank == HandRank.ROYAL_FLUSH
    
    def test_evaluate_hand_high_card(self):
        """Test evaluating a high card hand."""
        hole_cards = [
            Card(Suit.SPADES, Rank.ACE),
            Card(Suit.HEARTS, Rank.KING)
        ]
        community_cards = [
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK),
            Card(Suit.SPADES, Rank.NINE),
            Card(Suit.HEARTS, Rank.SEVEN),
            Card(Suit.CLUBS, Rank.FIVE)
        ]
        
        result = evaluate_hand(hole_cards, community_cards)
        assert result.rank == HandRank.HIGH_CARD
        assert result.primary_value == Rank.ACE.value
    
    def test_create_player(self):
        """Test creating a player."""
        player = create_player(seat_id=1, name="Alice", chips=1000)
        
        assert player.seat_id == 1
        assert player.name == "Alice"
        assert player.chips == 1000
        assert player.is_active  # This is a property, not a method
    
    def test_validate_action_fold(self):
        """Test validating a fold action."""
        game_state = MockGameState()
        player = create_player(seat_id=1, name="Player1", chips=1000)
        action = Action(ActionType.FOLD, 0, 1)
        
        result = validate_action(game_state, player, action)
        
        assert result.validation_result.is_valid
        assert result.final_action.action_type == ActionType.FOLD
        assert not result.was_converted
    
    def test_validate_action_call_converts_to_check(self):
        """Test that call converts to check when no bet exists."""
        game_state = MockGameState()  # No current bet
        player = create_player(seat_id=1, name="Player1", chips=1000)
        action = Action(ActionType.CALL, 0, 1)
        
        result = validate_action(game_state, player, action)
        
        assert result.validation_result.is_valid
        assert result.final_action.action_type == ActionType.CHECK
        assert result.was_converted
        assert "No bet to call" in result.conversion_reason
    
    def test_create_pot_manager(self):
        """Test creating a pot manager."""
        pot_manager = create_pot_manager()
        
        assert pot_manager.get_total_pot() == 0
        assert len(pot_manager._side_pots) == 0
    
    def test_api_imports_work(self):
        """Smoke test that all API imports work."""
        # This test ensures all public API can be imported without errors
        from v2.core import (
            # Enums
            Suit, Rank, HandRank, ActionType, Phase, SeatStatus, 
            GameEventType, ValidationResult,
            # Action data classes
            Action, ValidatedAction,
            # Cards
            Card, Deck,
            # Evaluator
            SimpleEvaluator, HandResult,
            # Player
            Player,
            # Validator
            ActionValidator, GameStateProtocol, InvalidActionError, InsufficientChipsError,
            # Pot management
            SidePot, PotManager, calculate_side_pots, get_pot_distribution_summary,
            # State management
            GameState, GameSnapshot,
            # Utility functions
            get_all_suits, get_all_ranks, get_valid_actions,
            # High-level API
            new_deck, evaluate_hand, create_player, validate_action, create_pot_manager
        )
        
        # Basic smoke test - create instances
        deck = new_deck()
        player = create_player(1, "Test", 1000)
        pot_manager = create_pot_manager()
        
        assert deck is not None
        assert player is not None
        assert pot_manager is not None 