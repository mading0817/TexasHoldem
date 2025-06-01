"""
Decorators for controller layer functionality.

This module provides decorators for transaction management and other
controller-level concerns.
"""

import functools
import copy
from typing import Any, Callable, TypeVar

from ..core import GameState

F = TypeVar('F', bound=Callable[..., Any])


def atomic(func: F) -> F:
    """
    Decorator to ensure atomic operations on game state.
    
    This decorator implements Copy-on-Write semantics for game state operations.
    If an exception occurs during the decorated method execution, the game state
    is automatically rolled back to its previous state.
    
    Args:
        func: The method to decorate. Must be a method of a class that has
              a _game_state attribute of type GameState.
              
    Returns:
        The decorated function with atomic behavior.
        
    Example:
        @atomic
        def execute_action(self, action: Action) -> bool:
            # This operation will be rolled back if an exception occurs
            self._game_state.apply_action(action)
            return True
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Check if the instance has a _game_state attribute
        if not hasattr(self, '_game_state'):
            raise AttributeError(
                f"@atomic decorator requires the class to have a '_game_state' attribute. "
                f"Class {self.__class__.__name__} does not have this attribute."
            )
            
        game_state = getattr(self, '_game_state')
        if not isinstance(game_state, GameState):
            raise TypeError(
                f"@atomic decorator requires '_game_state' to be of type GameState. "
                f"Got {type(game_state).__name__} instead."
            )
        
        # Create a snapshot of the current state
        original_snapshot = game_state.create_snapshot()
        
        try:
            # Execute the decorated function
            result = func(self, *args, **kwargs)
            return result
        except Exception as e:
            # Rollback to the original state on any exception
            game_state.restore_from_snapshot(original_snapshot)
            game_state.add_event(f"Transaction rolled back due to error: {str(e)}")
            
            # Re-raise the original exception
            raise
    
    return wrapper


def logged_action(action_name: str = None):
    """
    Decorator to automatically log controller actions.
    
    Args:
        action_name: Optional custom name for the action. If not provided,
                    the function name will be used.
                    
    Returns:
        Decorator function.
        
    Example:
        @logged_action("Player Action")
        def execute_action(self, action: Action) -> bool:
            # This will automatically log the action execution
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get the logger from the instance
            logger = getattr(self, '_logger', None)
            name = action_name or func.__name__
            
            if logger:
                logger.debug(f"Starting {name}")
            
            try:
                result = func(self, *args, **kwargs)
                if logger:
                    logger.debug(f"Completed {name} successfully")
                return result
            except Exception as e:
                if logger:
                    logger.error(f"Failed {name}: {str(e)}")
                raise
                
        return wrapper
    return decorator 