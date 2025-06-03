"""
Core game logic for Texas Hold'em poker.

This package contains the fundamental game components including cards, players,
game state management, and rule validation.
"""

from .enums import Suit, Rank, ActionType, Phase, SeatStatus, HandRank, Action, ValidatedAction, ValidationResultData, GameEventType, ValidationResult, get_all_suits, get_all_ranks, get_valid_actions
from .cards import Card, Deck
from .evaluator import SimpleEvaluator, HandResult
from .player import Player
from .validator import ActionValidator, GameStateProtocol, InvalidActionError, InsufficientChipsError
from .pot import SidePot, PotManager, calculate_side_pots, get_pot_distribution_summary
from .state import GameState, GameSnapshot
from .events import EventBus, EventType, GameEvent, get_event_bus
from .health_checker import (
    GameStateHealthChecker, 
    HealthIssue, 
    HealthCheckResult, 
    HealthIssueType, 
    HealthIssueSeverity
)

# Convenience functions for common operations
def new_deck(shuffle: bool = True) -> Deck:
    """Create a new deck of cards.
    
    Args:
        shuffle: Whether to shuffle the deck after creation.
        
    Returns:
        A new deck of cards.
    """
    deck = Deck()
    if shuffle:
        deck.shuffle()
    return deck


def evaluate(cards: list) -> HandResult:
    """Evaluate a poker hand.
    
    Args:
        cards: List of Card objects to evaluate.
        
    Returns:
        HandResult containing the evaluation.
    """
    evaluator = SimpleEvaluator()
    return evaluator.evaluate(cards)


def create_player(seat_id: int, name: str, chips: int) -> Player:
    """Create a new player.
    
    Args:
        seat_id: The seat ID for the player.
        name: The player's name.
        chips: The player's starting chips.
        
    Returns:
        A new Player instance.
    """
    return Player(seat_id=seat_id, name=name, chips=chips)


__all__ = [
    # Enums
    'Suit', 'Rank', 'ActionType', 'Phase', 'SeatStatus', 'HandRank', 'Action', 'ValidatedAction', 'ValidationResultData', 'GameEventType', 'ValidationResult',
    
    # Core classes
    'Card', 'Deck', 'Player', 'GameState', 'GameSnapshot',
    
    # Evaluation
    'SimpleEvaluator', 'HandResult',
    
    # Validation
    'ActionValidator', 'GameStateProtocol', 'InvalidActionError', 'InsufficientChipsError',
    
    # Pot management
    'SidePot', 'PotManager', 'calculate_side_pots', 'get_pot_distribution_summary',
    
    # Events
    'EventBus', 'EventType', 'GameEvent', 'get_event_bus',
    
    # Health checking
    'GameStateHealthChecker', 'HealthIssue', 'HealthCheckResult', 'HealthIssueType', 'HealthIssueSeverity',
    
    # Convenience functions
    'new_deck', 'evaluate', 'create_player',
    
    # Utility functions
    'get_all_suits', 'get_all_ranks', 'get_valid_actions'
] 