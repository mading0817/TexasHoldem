"""
Event system for Texas Hold'em poker game v2.

This module provides an event bus system for decoupling game logic
from UI and other observers.
"""

from typing import Any, Callable, Dict, List, Optional, Protocol
from dataclasses import dataclass
from enum import Enum
import logging


class EventType(Enum):
    """Types of events that can be emitted by the game."""
    
    # Game lifecycle events
    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    HAND_STARTED = "hand_started"
    HAND_ENDED = "hand_ended"
    
    # Phase events
    PHASE_CHANGED = "phase_changed"
    CARDS_DEALT = "cards_dealt"
    
    # Player action events
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    PLAYER_ACTION = "player_action"
    PLAYER_FOLDED = "player_folded"
    PLAYER_ALL_IN = "player_all_in"
    
    # Betting events
    BET_PLACED = "bet_placed"
    POT_UPDATED = "pot_updated"
    BLINDS_POSTED = "blinds_posted"
    
    # System events
    ERROR_OCCURRED = "error_occurred"
    STATE_CHANGED = "state_changed"


@dataclass
class GameEvent:
    """Represents a game event with associated data.
    
    Attributes:
        event_type: The type of event
        data: Event-specific data
        timestamp: When the event occurred (optional)
        source: Source of the event (optional)
    """
    
    event_type: EventType
    data: Dict[str, Any]
    timestamp: Optional[float] = None
    source: Optional[str] = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            import time
            self.timestamp = time.time()


# Type alias for event listeners
EventListener = Callable[[GameEvent], None]


class EventBus:
    """Event bus for managing game events and listeners.
    
    This class implements the observer pattern, allowing components
    to subscribe to specific event types and receive notifications
    when those events occur.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the event bus.
        
        Args:
            logger: Optional logger for debugging events
        """
        self._listeners: Dict[EventType, List[EventListener]] = {}
        self._logger = logger or logging.getLogger(__name__)
        self._event_history: List[GameEvent] = []
        self._max_history = 1000  # Limit history to prevent memory leaks
        
    def subscribe(self, event_type: EventType, listener: EventListener) -> None:
        """Subscribe a listener to an event type.
        
        Args:
            event_type: The type of event to listen for
            listener: The callback function to call when the event occurs
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        
        self._listeners[event_type].append(listener)
        self._logger.debug(f"Subscribed listener to {event_type.value}")
        
    def unsubscribe(self, event_type: EventType, listener: EventListener) -> bool:
        """Unsubscribe a listener from an event type.
        
        Args:
            event_type: The type of event to stop listening for
            listener: The callback function to remove
            
        Returns:
            True if the listener was found and removed, False otherwise
        """
        if event_type not in self._listeners:
            return False
            
        try:
            self._listeners[event_type].remove(listener)
            self._logger.debug(f"Unsubscribed listener from {event_type.value}")
            return True
        except ValueError:
            return False
            
    def emit(self, event: GameEvent) -> None:
        """Emit an event to all subscribed listeners.
        
        Args:
            event: The event to emit
        """
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
            
        # Notify listeners
        listeners = self._listeners.get(event.event_type, [])
        self._logger.debug(f"Emitting {event.event_type.value} to {len(listeners)} listeners")
        
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                self._logger.error(f"Error in event listener: {e}")
                
    def emit_simple(self, event_type: EventType, **data) -> None:
        """Emit a simple event with data as keyword arguments.
        
        Args:
            event_type: The type of event to emit
            **data: Event data as keyword arguments
        """
        event = GameEvent(event_type=event_type, data=data)
        self.emit(event)
        
    def get_listeners_count(self, event_type: EventType) -> int:
        """Get the number of listeners for an event type.
        
        Args:
            event_type: The event type to check
            
        Returns:
            Number of listeners subscribed to the event type
        """
        return len(self._listeners.get(event_type, []))
        
    def clear_listeners(self, event_type: Optional[EventType] = None) -> None:
        """Clear listeners for a specific event type or all event types.
        
        Args:
            event_type: The event type to clear, or None to clear all
        """
        if event_type is None:
            self._listeners.clear()
            self._logger.debug("Cleared all event listeners")
        else:
            self._listeners[event_type] = []
            self._logger.debug(f"Cleared listeners for {event_type.value}")
            
    def get_event_history(self, event_type: Optional[EventType] = None, 
                         limit: Optional[int] = None) -> List[GameEvent]:
        """Get event history, optionally filtered by type and limited.
        
        Args:
            event_type: Optional event type to filter by
            limit: Optional limit on number of events to return
            
        Returns:
            List of events from history
        """
        events = self._event_history
        
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
            
        if limit is not None:
            events = events[-limit:]
            
        return events
        
    def clear_history(self) -> None:
        """Clear the event history."""
        self._event_history.clear()
        self._logger.debug("Cleared event history")


# Global event bus instance (can be overridden for testing)
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance.
    
    Returns:
        The global EventBus instance
    """
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def set_event_bus(event_bus: EventBus) -> None:
    """Set the global event bus instance.
    
    Args:
        event_bus: The EventBus instance to use globally
    """
    global _global_event_bus
    _global_event_bus = event_bus 