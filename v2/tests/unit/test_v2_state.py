"""
Unit tests for v2 game state management.

Tests the GameState and GameSnapshot classes for data management,
snapshot functionality, and controlled randomness.
"""

import pytest
import random
from v2.core.state import GameState, GameSnapshot
from v2.core.player import Player
from v2.core.cards import Card, Deck
from v2.core.enums import Phase, SeatStatus, Suit, Rank


@pytest.mark.unit
@pytest.mark.fast
class TestGameSnapshot:
    """Test the GameSnapshot class."""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_snapshot_creation(self):
        """Test basic snapshot creation."""
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        
        snapshot = GameSnapshot(
            phase=Phase.FLOP,
            community_cards=[Card(Suit.HEARTS, Rank.ACE)],
            pot=100,
            current_bet=50,
            last_raiser=1,
            last_raise_amount=25,
            players=[player1, player2],
            dealer_position=1,
            current_player=2,
            small_blind=5,
            big_blind=10,
            street_index=1,
            events=["Game started"]
        )
        
        assert snapshot.phase == Phase.FLOP
        assert len(snapshot.community_cards) == 1
        assert snapshot.pot == 100
        assert snapshot.current_bet == 50
        assert len(snapshot.players) == 2
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_active_players(self):
        """Test getting active players from snapshot."""
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        player3 = Player(seat_id=3, name="Charlie", chips=500)
        
        player2.status = SeatStatus.FOLDED
        player3.status = SeatStatus.ALL_IN
        
        snapshot = GameSnapshot(
            phase=Phase.FLOP,
            community_cards=[],
            pot=0,
            current_bet=0,
            last_raiser=None,
            last_raise_amount=0,
            players=[player1, player2, player3],
            dealer_position=1,
            current_player=1,
            small_blind=5,
            big_blind=10,
            street_index=0,
            events=[]
        )
        
        active_players = snapshot.get_active_players()
        assert len(active_players) == 1
        assert active_players[0].name == "Alice"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_players_in_hand(self):
        """Test getting players still in hand from snapshot."""
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        player3 = Player(seat_id=3, name="Charlie", chips=500)
        
        player2.status = SeatStatus.FOLDED
        player3.status = SeatStatus.ALL_IN
        
        snapshot = GameSnapshot(
            phase=Phase.FLOP,
            community_cards=[],
            pot=0,
            current_bet=0,
            last_raiser=None,
            last_raise_amount=0,
            players=[player1, player2, player3],
            dealer_position=1,
            current_player=1,
            small_blind=5,
            big_blind=10,
            street_index=0,
            events=[]
        )
        
        players_in_hand = snapshot.get_players_in_hand()
        assert len(players_in_hand) == 2
        assert {p.name for p in players_in_hand} == {"Alice", "Charlie"}
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_player_by_seat(self):
        """Test getting player by seat number from snapshot."""
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        
        snapshot = GameSnapshot(
            phase=Phase.PRE_FLOP,
            community_cards=[],
            pot=0,
            current_bet=0,
            last_raiser=None,
            last_raise_amount=0,
            players=[player1, player2],
            dealer_position=1,
            current_player=1,
            small_blind=5,
            big_blind=10,
            street_index=0,
            events=[]
        )
        
        found_player = snapshot.get_player_by_seat(2)
        assert found_player is not None
        assert found_player.name == "Bob"
        
        not_found = snapshot.get_player_by_seat(3)
        assert not_found is None
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_current_player(self):
        """Test getting current player from snapshot."""
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        
        snapshot = GameSnapshot(
            phase=Phase.PRE_FLOP,
            community_cards=[],
            pot=0,
            current_bet=0,
            last_raiser=None,
            last_raise_amount=0,
            players=[player1, player2],
            dealer_position=1,
            current_player=2,
            small_blind=5,
            big_blind=10,
            street_index=0,
            events=[]
        )
        
        current_player = snapshot.get_current_player()
        assert current_player is not None
        assert current_player.name == "Bob"
        
        # Test with no current player
        snapshot.current_player = None
        assert snapshot.get_current_player() is None
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_dict_with_viewer(self):
        """Test converting snapshot to dict with viewer perspective."""
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        
        # Add hole cards
        player1.set_hole_cards([Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.KING)])
        player2.set_hole_cards([Card(Suit.DIAMONDS, Rank.QUEEN), Card(Suit.CLUBS, Rank.JACK)])
        
        snapshot = GameSnapshot(
            phase=Phase.FLOP,
            community_cards=[Card(Suit.HEARTS, Rank.TEN)],
            pot=100,
            current_bet=50,
            last_raiser=1,
            last_raise_amount=25,
            players=[player1, player2],
            dealer_position=1,
            current_player=2,
            small_blind=5,
            big_blind=10,
            street_index=1,
            events=["Game started"]
        )
        
        # Test from Alice's perspective
        data = snapshot.to_dict(viewer_seat=1)
        assert data['phase'] == 'FLOP'
        assert data['pot'] == 100
        assert len(data['players']) == 2
        
        # Alice should see her own cards
        alice_data = next(p for p in data['players'] if p['seat_id'] == 1)
        assert 'AH' in alice_data['hole_cards']
        
        # Bob's cards should be hidden
        bob_data = next(p for p in data['players'] if p['seat_id'] == 2)
        assert bob_data['hole_cards'] == "XX XX"


@pytest.mark.unit
@pytest.mark.fast
class TestGameState:
    """Test the GameState class."""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_initialization(self):
        """Test basic game state initialization."""
        state = GameState()
        
        assert state.phase == Phase.PRE_FLOP
        assert state.pot == 0
        assert state.current_bet == 0
        assert len(state.players) == 0
        assert len(state.community_cards) == 0
        assert state.small_blind == 1
        assert state.big_blind == 2
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_initialization_validation(self):
        """Test validation during initialization."""
        # Test negative pot
        with pytest.raises(ValueError, match="Pot amount cannot be negative"):
            GameState(pot=-10)
        
        # Test negative current bet
        with pytest.raises(ValueError, match="Current bet cannot be negative"):
            GameState(current_bet=-5)
        
        # Test invalid small blind
        with pytest.raises(ValueError, match="Small blind must be positive"):
            GameState(small_blind=0)
        
        # Test invalid big blind
        with pytest.raises(ValueError, match="Big blind .* must be greater than small blind"):
            GameState(small_blind=10, big_blind=5)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_add_player(self):
        """Test adding players to the game."""
        state = GameState()
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        
        state.add_player(player1)
        assert len(state.players) == 1
        assert state.get_player_by_seat(1) == player1
        assert "Player Alice joined at seat 1" in state.events
        
        state.add_player(player2)
        assert len(state.players) == 2
        
        # Test adding player to occupied seat
        player3 = Player(seat_id=1, name="Charlie", chips=500)
        with pytest.raises(ValueError, match="Seat 1 is already occupied"):
            state.add_player(player3)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_remove_player(self):
        """Test removing players from the game."""
        state = GameState()
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        
        state.add_player(player1)
        state.add_player(player2)
        
        removed = state.remove_player(1)
        assert removed == player1
        assert len(state.players) == 1
        assert state.get_player_by_seat(1) is None
        assert "Player Alice left seat 1" in state.events
        
        # Test removing non-existent player
        not_removed = state.remove_player(3)
        assert not_removed is None
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_initialize_deck(self):
        """Test deck initialization and shuffling."""
        state = GameState()
        
        # Test without seed
        state.initialize_deck()
        assert state.deck is not None
        assert state.deck.cards_remaining == 52
        assert "Deck initialized and shuffled" in state.events
        
        # Test with seed for deterministic behavior
        state2 = GameState()
        state2.initialize_deck(seed=42)
        
        state3 = GameState()
        state3.initialize_deck(seed=42)
        
        # Both should have the same first card when using same seed
        card1 = state2.deck.deal_card()
        card2 = state3.deck.deal_card()
        assert card1 == card2
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_deal_hole_cards(self):
        """Test dealing hole cards to players."""
        state = GameState()
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        
        state.add_player(player1)
        state.add_player(player2)
        
        # Test without deck
        with pytest.raises(ValueError, match="Deck not initialized"):
            state.deal_hole_cards()
        
        # Test with deck
        state.initialize_deck(seed=42)
        state.deal_hole_cards()
        
        assert len(player1.hole_cards) == 2
        assert len(player2.hole_cards) == 2
        assert state.deck.cards_remaining == 48  # 52 - 4 cards dealt
        assert "[pre_flop] 发底牌给 2 位玩家" in state.events
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_deal_community_cards(self):
        """Test dealing community cards."""
        state = GameState()
        state.initialize_deck(seed=42)
        
        # Test dealing flop (3 cards)
        state.phase = Phase.FLOP
        state.deal_community_cards(3)
        
        assert len(state.community_cards) == 3
        assert state.deck.cards_remaining == 48  # 52 - 1 burn - 3 community
        assert "[flop] 翻牌:" in state.events[-1]
        
        # Test dealing turn (1 card)
        state.phase = Phase.TURN
        state.deal_community_cards(1)
        
        assert len(state.community_cards) == 4
        assert state.deck.cards_remaining == 46  # 48 - 1 burn - 1 community
        assert "[turn] 转牌:" in state.events[-1]
        
        # Test dealing river (1 card)
        state.phase = Phase.RIVER
        state.deal_community_cards(1)
        
        assert len(state.community_cards) == 5
        assert state.deck.cards_remaining == 44  # 46 - 1 burn - 1 community
        assert "[river] 河牌:" in state.events[-1]
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_collect_bets_to_pot(self):
        """Test collecting bets to pot."""
        state = GameState()
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        
        state.add_player(player1)
        state.add_player(player2)
        
        # Players make bets
        player1.bet(50)
        player2.bet(100)
        
        collected = state.collect_bets_to_pot()
        
        assert collected == 150
        assert state.pot == 150
        assert player1.current_bet == 0
        assert player2.current_bet == 0
        assert "Collected 150 chips to pot" in state.events[-1]
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_reset_betting_round(self):
        """Test resetting betting round state."""
        state = GameState()
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        
        state.add_player(player1)
        state.add_player(player2)
        
        # Set up betting round state
        state.current_bet = 100
        state.last_raiser = 1
        state.last_raise_amount = 50
        state.street_index = 2
        player1.bet(50)
        player2.bet(100)
        
        state.reset_betting_round()
        
        assert state.current_bet == 0
        assert state.last_raiser is None
        assert state.last_raise_amount == 0
        assert state.street_index == 0
        assert player1.current_bet == 0
        assert player2.current_bet == 0
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_advance_phase(self):
        """Test advancing game phases."""
        state = GameState()
        
        assert state.phase == Phase.PRE_FLOP
        
        state.advance_phase()
        assert state.phase == Phase.FLOP
        assert "阶段转换: 翻牌前 → 翻牌" in state.events[-1]
        
        state.advance_phase()
        assert state.phase == Phase.TURN
        
        state.advance_phase()
        assert state.phase == Phase.RIVER
        
        state.advance_phase()
        assert state.phase == Phase.SHOWDOWN
        
        # Should stay at showdown
        state.advance_phase()
        assert state.phase == Phase.SHOWDOWN
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_snapshot(self):
        """Test creating game state snapshots."""
        state = GameState()
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        
        state.add_player(player1)
        state.add_player(player2)
        state.pot = 100
        state.current_bet = 50
        state.phase = Phase.FLOP
        
        snapshot = state.create_snapshot()
        
        assert isinstance(snapshot, GameSnapshot)
        assert snapshot.phase == Phase.FLOP
        assert snapshot.pot == 100
        assert snapshot.current_bet == 50
        assert len(snapshot.players) == 2
        
        # Verify it's a deep copy
        state.pot = 200
        assert snapshot.pot == 100  # Should not change
        
        # Verify player changes don't affect snapshot
        player1.chips = 500
        snapshot_player = snapshot.get_player_by_seat(1)
        assert snapshot_player.chips == 1000  # Should not change
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_restore_from_snapshot(self):
        """Test restoring game state from snapshot."""
        state = GameState()
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        
        state.add_player(player1)
        state.add_player(player2)
        state.pot = 100
        state.current_bet = 50
        state.phase = Phase.FLOP
        
        # Create snapshot
        snapshot = state.create_snapshot()
        
        # Modify state
        state.pot = 200
        state.current_bet = 100
        state.phase = Phase.TURN
        player1.chips = 500
        
        # Restore from snapshot
        state.restore_from_snapshot(snapshot)
        
        assert state.phase == Phase.FLOP
        assert state.pot == 100
        assert state.current_bet == 50
        restored_player = state.get_player_by_seat(1)
        assert restored_player.chips == 1000
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_clone(self):
        """Test cloning game state."""
        state = GameState()
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        state.add_player(player1)
        state.pot = 100
        
        cloned = state.clone()
        
        assert cloned is not state
        assert cloned.pot == 100
        assert len(cloned.players) == 1
        
        # Verify deep copy
        state.pot = 200
        assert cloned.pot == 100
        
        state.players[0].chips = 500
        assert cloned.players[0].chips == 1000
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_event_management(self):
        """Test event logging and management."""
        state = GameState()
        
        state.add_event("Test event 1")
        state.add_event("Test event 2")
        
        assert len(state.events) == 2
        assert "Test event 1" in state.events
        assert "Test event 2" in state.events
        
        state.clear_events()
        assert len(state.events) == 0
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_dict(self):
        """Test converting state to dictionary."""
        state = GameState()
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        state.add_player(player1)
        state.pot = 100
        state.phase = Phase.FLOP
        
        data = state.to_dict()
        
        assert data['phase'] == 'FLOP'
        assert data['pot'] == 100
        assert len(data['players']) == 1
        assert data['players'][0]['name'] == 'Alice'
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_string_representations(self):
        """Test string representations of game state."""
        state = GameState()
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        state.add_player(player1)
        state.pot = 100
        state.current_bet = 50
        state.phase = Phase.FLOP
        
        str_repr = str(state)
        assert "Phase: FLOP" in str_repr
        assert "Pot: 100" in str_repr
        assert "Current bet: 50" in str_repr
        assert "Active players: 1" in str_repr
        
        repr_str = repr(state)
        assert "GameState(phase=FLOP, pot=100, players=1)" == repr_str


@pytest.mark.unit
@pytest.mark.fast
class TestSnapshotComparison:
    """Test snapshot comparison for testing purposes."""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_snapshot_bet_comparison(self):
        """Test comparing snapshots after betting action."""
        state = GameState()
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        
        state.add_player(player1)
        state.add_player(player2)
        
        # Take snapshot before betting
        before_snapshot = state.create_snapshot()
        
        # Player makes a bet
        player1.bet(50)
        state.current_bet = 50
        
        # Take snapshot after betting
        after_snapshot = state.create_snapshot()
        
        # Verify changes
        before_player = before_snapshot.get_player_by_seat(1)
        after_player = after_snapshot.get_player_by_seat(1)
        
        assert before_player.current_bet == 0
        assert after_player.current_bet == 50
        assert before_player.chips == 1000
        assert after_player.chips == 950
        
        assert before_snapshot.current_bet == 0
        assert after_snapshot.current_bet == 50
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_snapshot_no_opponent_cards(self):
        """Test that snapshots don't reveal opponent cards."""
        state = GameState()
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Bob", chips=1500)
        
        # Add hole cards
        player1.set_hole_cards([Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.KING)])
        player2.set_hole_cards([Card(Suit.DIAMONDS, Rank.QUEEN), Card(Suit.CLUBS, Rank.JACK)])
        
        state.add_player(player1)
        state.add_player(player2)
        
        snapshot = state.create_snapshot()
        
        # Convert to dict from Alice's perspective
        alice_view = snapshot.to_dict(viewer_seat=1)
        
        # Alice should see her own cards
        alice_data = next(p for p in alice_view['players'] if p['seat_id'] == 1)
        assert 'AH' in alice_data['hole_cards']
        assert 'KS' in alice_data['hole_cards']
        
        # Bob's cards should be hidden
        bob_data = next(p for p in alice_view['players'] if p['seat_id'] == 2)
        assert bob_data['hole_cards'] == "XX XX" 