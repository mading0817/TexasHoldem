"""
Core enumerations for Texas Hold'em poker game.

This module defines all the enumeration types used throughout the game,
providing type safety and clear value definitions.
"""

from enum import Enum, IntEnum
from typing import List


class Suit(Enum):
    """Card suits enumeration.
    
    Represents the four suits in a standard deck of cards.
    """
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"


class Rank(IntEnum):
    """Card ranks enumeration.
    
    Represents card ranks with integer values for easy comparison.
    Ace is high (14) in most contexts.
    """
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


class HandRank(IntEnum):
    """Poker hand rankings enumeration.
    
    Higher values represent stronger hands.
    """
    HIGH_CARD = 1
    ONE_PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10


class ActionType(Enum):
    """Player action types enumeration.
    
    Represents all possible actions a player can take during a hand.
    """
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


class Phase(Enum):
    """Game phase enumeration.
    
    Represents the different phases of a poker hand.
    """
    PRE_FLOP = "pre_flop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"


class SeatStatus(Enum):
    """Player seat status enumeration.
    
    Represents the current status of a player in their seat.
    """
    ACTIVE = "active"
    FOLDED = "folded"
    ALL_IN = "all_in"
    OUT = "out"
    SITTING_OUT = "sitting_out"


class GameEventType(Enum):
    """Game event types enumeration.
    
    Represents different types of events that can occur during the game.
    """
    HAND_STARTED = "hand_started"
    CARDS_DEALT = "cards_dealt"
    PHASE_CHANGED = "phase_changed"
    PLAYER_ACTION = "player_action"
    POT_AWARDED = "pot_awarded"
    HAND_ENDED = "hand_ended"
    GAME_ENDED = "game_ended"


class ValidationResult(Enum):
    """Action validation result enumeration.
    
    Represents the result of validating a player action.
    """
    VALID = "valid"
    INVALID_AMOUNT = "invalid_amount"
    INSUFFICIENT_CHIPS = "insufficient_chips"
    OUT_OF_TURN = "out_of_turn"
    INVALID_ACTION = "invalid_action"
    GAME_NOT_ACTIVE = "game_not_active"


# Utility functions for enums
def get_all_suits() -> List[Suit]:
    """Get all card suits.
    
    Returns:
        List of all Suit enum values.
    """
    return list(Suit)


def get_all_ranks() -> List[Rank]:
    """Get all card ranks.
    
    Returns:
        List of all Rank enum values.
    """
    return list(Rank)


def get_valid_actions() -> List[ActionType]:
    """Get all valid player actions.
    
    Returns:
        List of all ActionType enum values.
    """
    return list(ActionType) 