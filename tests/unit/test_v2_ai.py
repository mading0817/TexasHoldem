"""
Unit tests for v2 AI strategies.

Tests the AI strategy implementations and their integration with the game controller.
"""

import pytest
from unittest.mock import Mock
import random

from v2.ai import SimpleAI, SimpleAIConfig
from v2.core import (
    GameSnapshot, Player, Action, ActionType, Phase, SeatStatus, Card, Suit, Rank
)


class TestSimpleAI:
    """Test cases for SimpleAI strategy."""
    
    def test_ai_creation(self):
        """Test AI strategy creation with default config."""
        ai = SimpleAI()
        assert ai.config.name == "SimpleAI"
        assert ai.config.conservativeness == 0.8
        assert ai.decision_count == 0
        
    def test_ai_creation_with_custom_config(self):
        """Test AI strategy creation with custom config."""
        config = SimpleAIConfig(
            name="TestAI",
            conservativeness=0.5,
            fold_threshold=0.4
        )
        ai = SimpleAI(config)
        assert ai.config.name == "TestAI"
        assert ai.config.conservativeness == 0.5
        assert ai.config.fold_threshold == 0.4
        
    def test_decide_invalid_player(self):
        """Test decision making with invalid player ID."""
        ai = SimpleAI()
        snapshot = self._create_test_snapshot()
        
        with pytest.raises(ValueError, match="Player 999 not found"):
            ai.decide(snapshot, 999)
            
    def test_decide_high_cost_fold(self):
        """Test that AI folds when call cost is too high."""
        config = SimpleAIConfig(fold_threshold=0.2)  # Low threshold
        ai = SimpleAI(config)
        
        # Create snapshot where call cost is high relative to chips
        snapshot = self._create_test_snapshot(
            current_bet=80,  # High bet
            player_chips=100,  # Low chips
            player_current_bet=0
        )
        
        action = ai.decide(snapshot, 1)
        assert action.action_type == ActionType.FOLD
        assert ai.decision_count == 1
        
    def test_decide_check_when_no_bet(self):
        """Test that AI checks when there's no bet to call."""
        ai = SimpleAI()
        
        # Create snapshot with no current bet
        snapshot = self._create_test_snapshot(
            current_bet=0,
            player_current_bet=0
        )
        
        # Set random seed for predictable behavior
        random.seed(42)
        action = ai.decide(snapshot, 1)
        
        # Should check most of the time due to conservativeness
        assert action.action_type in [ActionType.CHECK, ActionType.BET]
        
    def test_decide_call_acceptable_cost(self):
        """Test that AI calls when cost is acceptable."""
        config = SimpleAIConfig(fold_threshold=0.5)  # High threshold
        ai = SimpleAI(config)
        
        # Create snapshot with acceptable call cost
        snapshot = self._create_test_snapshot(
            current_bet=20,  # Reasonable bet
            player_chips=100,  # Good chips
            player_current_bet=0
        )
        
        action = ai.decide(snapshot, 1)
        assert action.action_type in [ActionType.CALL, ActionType.RAISE]
        
        if action.action_type == ActionType.CALL:
            assert action.amount == 20  # Call amount
            
    def test_analyze_situation(self):
        """Test situation analysis functionality."""
        ai = SimpleAI()
        
        player = Player(seat_id=1, name="TestPlayer", chips=100)
        player.current_bet = 10
        
        snapshot = self._create_test_snapshot(
            current_bet=30,
            player_chips=100,
            player_current_bet=10
        )
        
        context = ai._analyze_situation(player, snapshot)
        
        assert context['call_cost'] == 20  # 30 - 10
        assert context['cost_ratio'] == 0.2  # 20 / 100
        assert 'reasoning' in context
        
    def test_bet_amount_calculation(self):
        """Test bet amount calculation."""
        ai = SimpleAI()
        
        player = Player(seat_id=1, name="TestPlayer", chips=100)
        snapshot = self._create_test_snapshot()
        
        bet_amount = ai._calculate_bet_amount(player, snapshot)
        
        # Should be between 1-3 times big blind (10-30)
        assert 10 <= bet_amount <= 30
        assert bet_amount <= player.chips
        
    def test_raise_amount_calculation(self):
        """Test raise amount calculation."""
        ai = SimpleAI()
        
        player = Player(seat_id=1, name="TestPlayer", chips=100)
        snapshot = self._create_test_snapshot(current_bet=20)
        
        raise_amount = ai._calculate_raise_amount(player, snapshot)
        
        # Should be current bet + 1-2 times big blind (30-40)
        assert 30 <= raise_amount <= 40
        assert raise_amount <= player.chips
        
    def _create_test_snapshot(
        self, 
        current_bet: int = 0,
        player_chips: int = 100,
        player_current_bet: int = 0
    ) -> GameSnapshot:
        """Create a test game snapshot."""
        # Create test players
        player1 = Player(seat_id=1, name="Player1", chips=player_chips)
        player1.current_bet = player_current_bet
        player1.status = SeatStatus.ACTIVE
        
        player2 = Player(seat_id=2, name="Player2", chips=100)
        player2.status = SeatStatus.ACTIVE
        
        # Create test snapshot
        snapshot = GameSnapshot(
            players=[player1, player2],
            community_cards=[],
            phase=Phase.PRE_FLOP,
            current_bet=current_bet,
            pot=0,
            current_player=1,
            dealer_position=0,
            small_blind=5,
            big_blind=10,
            street_index=0,
            last_raiser=None,
            last_raise_amount=0,
            events=[]
        )
        
        return snapshot


class TestAlwaysFoldAI:
    """Test case for an AI that always folds - used for testing game flow."""
    
    def test_always_fold_ai(self):
        """Test an AI strategy that always folds."""
        
        class AlwaysFoldAI:
            """AI that always folds for testing purposes."""
            
            def decide(self, game_snapshot: GameSnapshot, player_id: int) -> Action:
                return Action(player_id=player_id, action_type=ActionType.FOLD)
        
        ai = AlwaysFoldAI()
        snapshot = self._create_test_snapshot()
        
        action = ai.decide(snapshot, 1)
        assert action.action_type == ActionType.FOLD
        assert action.player_id == 1
        
    def _create_test_snapshot(self) -> GameSnapshot:
        """Create a minimal test snapshot."""
        player1 = Player(seat_id=1, name="Player1", chips=100)
        player1.status = SeatStatus.ACTIVE
        
        player2 = Player(seat_id=2, name="Player2", chips=100)
        player2.status = SeatStatus.ACTIVE
        
        return GameSnapshot(
            players=[player1, player2],
            community_cards=[],
            phase=Phase.PRE_FLOP,
            current_bet=0,
            pot=0,
            current_player=1,
            dealer_position=0,
            small_blind=5,
            big_blind=10,
            street_index=0,
            last_raiser=None,
            last_raise_amount=0,
            events=[]
        ) 