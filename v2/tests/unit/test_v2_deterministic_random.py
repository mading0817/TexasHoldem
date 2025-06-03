"""
Tests for deterministic randomness in v2 core components.

This module tests that random number generation can be controlled
for deterministic testing, particularly for deck shuffling.
"""

import pytest
import random
from v2.core import GameState, Deck, Player


@pytest.mark.unit
@pytest.mark.fast
class TestDeterministicRandomness:
    """Test deterministic behavior with controlled randomness."""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_game_state_with_fixed_seed(self):
        """Test that GameState produces deterministic results with fixed seed."""
        # Create two game states with the same seed
        state1 = GameState(rng=random.Random(42))
        state2 = GameState(rng=random.Random(42))
        
        # Initialize decks with the same seed
        state1.initialize_deck(seed=42)
        state2.initialize_deck(seed=42)
        
        # Deal some cards and verify they're identical
        cards1 = state1.deck.deal_cards(5)
        cards2 = state2.deck.deal_cards(5)
        
        assert cards1 == cards2, "Cards should be identical with same seed"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_deck_with_fixed_rng(self):
        """Test that Deck produces deterministic results with fixed RNG."""
        # Create two decks with the same RNG seed
        rng1 = random.Random(123)
        rng2 = random.Random(123)
        
        deck1 = Deck(rng1)
        deck2 = Deck(rng2)
        
        # Shuffle both decks
        deck1.shuffle()
        deck2.shuffle()
        
        # Deal cards and verify they're identical
        cards1 = deck1.deal_cards(10)
        cards2 = deck2.deal_cards(10)
        
        assert cards1 == cards2, "Shuffled decks should be identical with same RNG seed"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_different_seeds_produce_different_results(self):
        """Test that different seeds produce different results."""
        # Create two game states with different seeds
        state1 = GameState(rng=random.Random(42))
        state2 = GameState(rng=random.Random(43))
        
        # Initialize decks with different seeds
        state1.initialize_deck(seed=42)
        state2.initialize_deck(seed=43)
        
        # Deal cards and verify they're different
        cards1 = state1.deck.deal_cards(5)
        cards2 = state2.deck.deal_cards(5)
        
        assert cards1 != cards2, "Cards should be different with different seeds"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_reproducible_hole_card_dealing(self):
        """Test that hole card dealing is reproducible with fixed seed."""
        # Create two identical game setups
        state1 = GameState(rng=random.Random(999))
        state2 = GameState(rng=random.Random(999))
        
        # Add identical players
        for i in range(3):
            state1.add_player(Player(i, f"Player{i}", 1000))
            state2.add_player(Player(i, f"Player{i}", 1000))
        
        # Initialize decks with same seed
        state1.initialize_deck(seed=999)
        state2.initialize_deck(seed=999)
        
        # Deal hole cards
        state1.deal_hole_cards()
        state2.deal_hole_cards()
        
        # Verify all players have identical hole cards
        for i in range(3):
            player1 = state1.get_player_by_seat(i)
            player2 = state2.get_player_by_seat(i)
            
            assert player1.hole_cards == player2.hole_cards, \
                f"Player {i} should have identical hole cards"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_reproducible_community_cards(self):
        """Test that community card dealing is reproducible with fixed seed."""
        # Create two identical game setups
        state1 = GameState(rng=random.Random(777))
        state2 = GameState(rng=random.Random(777))
        
        # Initialize decks with same seed
        state1.initialize_deck(seed=777)
        state2.initialize_deck(seed=777)
        
        # Deal flop (3 cards)
        state1.deal_community_cards(3)
        state2.deal_community_cards(3)
        
        assert state1.community_cards == state2.community_cards, \
            "Community cards should be identical with same seed"
        
        # Deal turn (1 card)
        state1.deal_community_cards(1)
        state2.deal_community_cards(1)
        
        assert state1.community_cards == state2.community_cards, \
            "Community cards should remain identical after turn"
        
        # Deal river (1 card)
        state1.deal_community_cards(1)
        state2.deal_community_cards(1)
        
        assert state1.community_cards == state2.community_cards, \
            "Community cards should remain identical after river"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_snapshot_preserves_determinism(self):
        """Test that snapshots preserve deterministic state."""
        # Create game state with fixed seed
        state = GameState(rng=random.Random(555))
        state.initialize_deck(seed=555)
        
        # Add a player and deal cards
        state.add_player(Player(0, "TestPlayer", 1000))
        state.deal_hole_cards()
        state.deal_community_cards(3)
        
        # Create snapshot
        snapshot = state.create_snapshot()
        
        # Create new state and restore from snapshot
        new_state = GameState(rng=random.Random(555))
        new_state.restore_from_snapshot(snapshot)
        
        # Verify community cards are preserved
        assert new_state.community_cards == state.community_cards
        
        # Verify player hole cards are preserved
        original_player = state.get_player_by_seat(0)
        restored_player = new_state.get_player_by_seat(0)
        assert restored_player.hole_cards == original_player.hole_cards
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_multiple_shuffles_with_same_seed(self):
        """Test that multiple shuffles with same seed produce same sequence."""
        # Test multiple shuffle operations
        results1 = []
        results2 = []
        
        for _ in range(3):
            # First sequence
            rng1 = random.Random(100)
            deck1 = Deck(rng1)
            deck1.shuffle()
            results1.append(deck1.deal_cards(3))
            
            # Second sequence
            rng2 = random.Random(100)
            deck2 = Deck(rng2)
            deck2.shuffle()
            results2.append(deck2.deal_cards(3))
        
        assert results1 == results2, "Multiple shuffle sequences should be identical"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_rng_state_independence(self):
        """Test that different GameState instances have independent RNG."""
        # Create two states with different RNG instances but same seed
        state1 = GameState(rng=random.Random(200))
        state2 = GameState(rng=random.Random(200))
        
        # Initialize decks
        state1.initialize_deck(seed=200)
        state2.initialize_deck(seed=200)
        
        # Deal different numbers of cards from each
        cards1_first = state1.deck.deal_cards(2)
        cards2_first = state2.deck.deal_cards(5)  # Different amount
        
        # Now deal same amount from both
        cards1_second = state1.deck.deal_cards(3)
        cards2_second = state2.deck.deal_cards(3)
        
        # They should be different because RNG states diverged
        assert cards1_second != cards2_second, \
            "RNG states should be independent after different operations" 