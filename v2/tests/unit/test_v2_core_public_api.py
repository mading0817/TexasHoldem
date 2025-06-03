"""
Tests for v2.core public API.

This module tests that all public APIs exported from v2.core can be imported
and used correctly, ensuring the module provides a clean interface.
"""

import pytest
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
    get_all_suits, get_all_ranks, get_valid_actions
)


@pytest.mark.unit
@pytest.mark.fast
class TestPublicAPIImports:
    """Test that all public API components can be imported."""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_enums_import(self):
        """Test that all enums are properly imported."""
        assert Suit.HEARTS.value == "♥"
        assert Rank.ACE.value == 14
        assert HandRank.ROYAL_FLUSH.value == 10
        assert ActionType.FOLD.value == "fold"
        assert Phase.PRE_FLOP.value == "pre_flop"
        assert SeatStatus.ACTIVE.value == "active"
        assert GameEventType.HAND_STARTED.value == "hand_started"
        assert ValidationResult.VALID.value == "valid"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_action_dataclasses_import(self):
        """Test that action data classes are properly imported."""
        action = Action(ActionType.BET, 100)
        assert action.action_type == ActionType.BET
        assert action.amount == 100
        
        # 创建一个简单的验证结果
        from v2.core.enums import ValidationResultData
        validation_result = ValidationResultData(is_valid=True)
        
        validated = ValidatedAction(action, action, validation_result)
        assert validated.original_action == action
        assert validated.final_action.action_type == ActionType.BET
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_cards_import(self):
        """Test that card classes are properly imported."""
        card = Card(Suit.SPADES, Rank.ACE)
        assert card.rank == Rank.ACE
        assert card.suit == Suit.SPADES
        
        deck = Deck()
        assert len(deck) == 52
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_evaluator_import(self):
        """Test that evaluator classes are properly imported."""
        evaluator = SimpleEvaluator()
        assert evaluator is not None
        
        hole_cards = [
            Card(Suit.SPADES, Rank.ACE),
            Card(Suit.SPADES, Rank.KING)
        ]
        community_cards = [
            Card(Suit.SPADES, Rank.QUEEN),
            Card(Suit.SPADES, Rank.JACK),
            Card(Suit.SPADES, Rank.TEN)
        ]
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        assert isinstance(result, HandResult)
        assert result.rank == HandRank.ROYAL_FLUSH
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_player_import(self):
        """Test that player class is properly imported."""
        player = Player(1, "Test Player", 1000)
        assert player.name == "Test Player"
        assert player.chips == 1000
        assert player.status == SeatStatus.ACTIVE
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validator_import(self):
        """Test that validator classes are properly imported."""
        validator = ActionValidator()
        assert validator is not None
        
        assert issubclass(InvalidActionError, Exception)
        assert issubclass(InsufficientChipsError, Exception)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_pot_management_import(self):
        """Test that pot management classes are properly imported."""
        side_pot = SidePot(100, ["player1", "player2"])
        assert side_pot.amount == 100
        assert side_pot.eligible_players == ["player1", "player2"]
        
        pot_manager = PotManager()
        assert pot_manager is not None
        
        contributions = {1: 100, 2: 50}
        side_pots = calculate_side_pots(contributions)
        assert isinstance(side_pots, list)
        
        summary = get_pot_distribution_summary(contributions)
        assert isinstance(summary, dict)
        assert 'side_pots' in summary
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_state_management_import(self):
        """Test that state management classes are properly imported."""
        game_state = GameState()
        assert game_state is not None
        
        snapshot = game_state.create_snapshot()
        assert isinstance(snapshot, GameSnapshot)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_utility_functions_import(self):
        """Test that utility functions are properly imported."""
        suits = get_all_suits()
        assert len(suits) == 4
        assert Suit.HEARTS in suits
        
        ranks = get_all_ranks()
        assert len(ranks) == 13
        assert Rank.ACE in ranks
        
        actions = get_valid_actions()
        assert len(actions) >= 5
        assert ActionType.FOLD in actions


@pytest.mark.unit
@pytest.mark.fast
class TestPublicAPIUsage:
    """Test that public APIs work together correctly."""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_and_evaluate_hand(self):
        """Test creating cards and evaluating a hand."""
        deck = Deck()
        deck.shuffle()
        
        cards = deck.deal_cards(7)
        
        hole_cards = cards[:2]
        community_cards = cards[2:]
        
        evaluator = SimpleEvaluator()
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        
        assert isinstance(result, HandResult)
        assert result.rank in get_all_hand_ranks()
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_player_and_action_workflow(self):
        """Test player creation and action validation workflow."""
        player = Player(1, "Test Player", 1000)
        
        action = Action(ActionType.BET, 100)
        
        validator = ActionValidator()
        
        assert player.chips >= action.amount
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_pot_calculation_workflow(self):
        """Test pot calculation with multiple players."""
        contributions = {
            1: 100,
            2: 200,
            3: 50
        }
        
        side_pots = calculate_side_pots(contributions)
        
        assert len(side_pots) > 0
        total_amount = sum(pot.amount for pot in side_pots)
        assert total_amount <= sum(contributions.values())
        
        summary = get_pot_distribution_summary(contributions)
        assert isinstance(summary, dict)
        assert 'side_pots' in summary
        assert len(summary['side_pots']) > 0


def get_all_hand_ranks():
    """Helper function to get all hand ranks."""
    return [
        HandRank.HIGH_CARD,
        HandRank.ONE_PAIR,
        HandRank.TWO_PAIR,
        HandRank.THREE_OF_A_KIND,
        HandRank.STRAIGHT,
        HandRank.FLUSH,
        HandRank.FULL_HOUSE,
        HandRank.FOUR_OF_A_KIND,
        HandRank.STRAIGHT_FLUSH,
        HandRank.ROYAL_FLUSH
    ] 