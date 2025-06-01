"""
Base AI strategy interface for Texas Hold'em poker game v2.

This module defines the protocol that all AI strategies must implement.
"""

from typing import Protocol, runtime_checkable
from ..core import GameSnapshot, Action


@runtime_checkable
class AIStrategy(Protocol):
    """AI strategy interface protocol.
    
    Defines the standard interface for AI player decision making.
    All AI implementations should follow this protocol.
    """
    
    def decide(self, game_snapshot: GameSnapshot, player_id: int) -> Action:
        """Make a decision based on the current game state.
        
        Args:
            game_snapshot: Immutable snapshot of the current game state
            player_id: ID of the player that needs to make a decision
            
        Returns:
            The action the AI player decides to take
            
        Raises:
            ValueError: If player_id is invalid or the player cannot act
        """
        ... 