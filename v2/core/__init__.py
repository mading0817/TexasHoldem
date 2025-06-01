"""
Core game logic module for Texas Hold'em poker.

This module provides the fundamental building blocks for poker game logic.
"""

from .enums import *
from .cards import Card, Deck
from .evaluator import SimpleEvaluator, HandResult
from .player import Player
from .validator import ActionValidator, GameStateProtocol, InvalidActionError, InsufficientChipsError
from .pot import SidePot, PotManager, calculate_side_pots, get_pot_distribution_summary
from .state import GameState, GameSnapshot

# High-level API functions
def new_deck(shuffled: bool = True, rng=None) -> Deck:
    """
    Create a new deck of cards.
    
    Args:
        shuffled: Whether to shuffle the deck after creation
        rng: Random number generator for shuffling
        
    Returns:
        Deck: A new deck of 52 cards
    """
    deck = Deck(rng=rng)
    if shuffled:
        deck.shuffle()
    return deck


def evaluate_hand(hole_cards, community_cards) -> HandResult:
    """
    Evaluate the best poker hand from hole cards and community cards.
    
    Args:
        hole_cards: List of 2 hole cards
        community_cards: List of community cards (up to 5)
        
    Returns:
        HandResult: The best hand evaluation result
    """
    evaluator = SimpleEvaluator()
    return evaluator.evaluate_hand(hole_cards, community_cards)


def create_player(seat_id: int, name: str, chips: int) -> Player:
    """
    Create a new player.
    
    Args:
        seat_id: Unique seat identifier
        name: Player name
        chips: Initial chip count
        
    Returns:
        Player: A new player instance
    """
    return Player(seat_id=seat_id, name=name, chips=chips)


def validate_action(game_state, player: Player, action) -> 'ValidatedAction':
    """
    Validate a player action.
    
    Args:
        game_state: Current game state
        player: Player attempting the action
        action: Action to validate
        
    Returns:
        ValidatedAction: Validation result with possible conversions
    """
    validator = ActionValidator()
    return validator.validate(game_state, player, action)


def create_pot_manager() -> PotManager:
    """
    Create a new pot manager.
    
    Returns:
        PotManager: A new pot manager instance
    """
    return PotManager()


__all__ = [
    # Enums
    'Suit', 'Rank', 'HandRank', 'ActionType', 'Phase', 'SeatStatus', 
    'GameEventType', 'ValidationResult', 'ValidationResultData',
    # Action data classes
    'Action', 'ValidatedAction',
    # Cards
    'Card', 'Deck',
    # Evaluator
    'SimpleEvaluator', 'HandResult',
    # Player
    'Player',
    # Validator
    'ActionValidator', 'GameStateProtocol', 'InvalidActionError', 'InsufficientChipsError',
    # Pot management
    'SidePot', 'PotManager', 'calculate_side_pots', 'get_pot_distribution_summary',
    # State management
    'GameState', 'GameSnapshot',
    # Utility functions
    'get_all_suits', 'get_all_ranks', 'get_valid_actions',
    # High-level API
    'new_deck', 'evaluate_hand', 'create_player', 'validate_action', 'create_pot_manager'
] 