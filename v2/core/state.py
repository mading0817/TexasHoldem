"""
Game state management for Texas Hold'em poker game v2.

This module provides the core game state management functionality,
focusing on data storage and snapshot capabilities without game rules.
"""

import copy
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from .enums import Phase, SeatStatus
from .cards import Card, Deck
from .player import Player


@dataclass
class GameSnapshot:
    """
    Immutable snapshot of game state for external consumption.
    
    This class provides a read-only view of the game state that can be
    safely shared with UI components, AI players, and other external systems.
    """
    
    # Game phase and cards
    phase: Phase
    community_cards: List[Card]
    
    # Pot and betting information
    pot: int
    current_bet: int
    last_raiser: Optional[int]
    last_raise_amount: int
    
    # Player and position information
    players: List[Player]  # These are copies, not references
    dealer_position: int
    current_player: Optional[int]
    
    # Game configuration
    small_blind: int
    big_blind: int
    
    # Round tracking
    street_index: int
    
    # Event log
    events: List[str]
    
    def get_active_players(self) -> List[Player]:
        """Get all players who can currently act.
        
        Returns:
            List of players with ACTIVE status.
        """
        return [p for p in self.players if p.status == SeatStatus.ACTIVE]
    
    def get_players_in_hand(self) -> List[Player]:
        """Get all players still in the current hand.
        
        Returns:
            List of players with ACTIVE or ALL_IN status.
        """
        return [p for p in self.players if p.status in [SeatStatus.ACTIVE, SeatStatus.ALL_IN]]
    
    def get_player_by_seat(self, seat_id: int) -> Optional[Player]:
        """Get player by seat number.
        
        Args:
            seat_id: The seat number to look up.
            
        Returns:
            The player at the specified seat, or None if not found.
        """
        for player in self.players:
            if player.seat_id == seat_id:
                return player
        return None
    
    def get_current_player(self) -> Optional[Player]:
        """Get the player whose turn it is to act.
        
        Returns:
            The current player, or None if no current player.
        """
        if self.current_player is None:
            return None
        return self.get_player_by_seat(self.current_player)
    
    def to_dict(self, viewer_seat: Optional[int] = None) -> Dict[str, Any]:
        """Convert snapshot to dictionary format.
        
        Args:
            viewer_seat: Seat number of the viewer, used to hide other players' cards.
            
        Returns:
            Dictionary representation of the game state.
        """
        players_data = []
        for player in self.players:
            # Hide cards from other players
            hide_cards = viewer_seat is not None and player.seat_id != viewer_seat
            
            player_data = {
                'seat_id': player.seat_id,
                'name': player.name,
                'chips': player.chips,
                'current_bet': player.current_bet,
                'status': player.status.name,
                'hole_cards': player.get_hole_cards_str(hidden=hide_cards),
                'is_dealer': player.is_dealer,
                'is_small_blind': player.is_small_blind,
                'is_big_blind': player.is_big_blind
            }
            players_data.append(player_data)
        
        return {
            'phase': self.phase.name,
            'community_cards': [str(card) for card in self.community_cards],
            'pot': self.pot,
            'current_bet': self.current_bet,
            'current_player': self.current_player,
            'dealer_position': self.dealer_position,
            'players': players_data,
            'small_blind': self.small_blind,
            'big_blind': self.big_blind,
            'street_index': self.street_index,
            'last_raiser': self.last_raiser,
            'last_raise_amount': self.last_raise_amount
        }


@dataclass
class GameState:
    """
    Mutable game state for Texas Hold'em poker.
    
    This class manages the core game state data without implementing
    game rules. It provides data storage, snapshot creation, and
    controlled randomness for testing.
    """
    
    # Game phase and cards
    phase: Phase = Phase.PRE_FLOP
    community_cards: List[Card] = field(default_factory=list)
    
    # Pot and betting information
    pot: int = 0
    current_bet: int = 0
    last_raiser: Optional[int] = None
    last_raise_amount: int = 0
    
    # Player and position information
    players: List[Player] = field(default_factory=list)
    dealer_position: int = 0
    current_player: Optional[int] = None
    
    # Game configuration
    small_blind: int = 1
    big_blind: int = 2
    
    # Round tracking
    street_index: int = 0
    
    # Deck and randomness
    deck: Optional[Deck] = None
    rng: random.Random = field(default_factory=random.Random)
    
    # Event log
    events: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate state after initialization."""
        if self.pot < 0:
            raise ValueError(f"Pot amount cannot be negative: {self.pot}")
        
        if self.current_bet < 0:
            raise ValueError(f"Current bet cannot be negative: {self.current_bet}")
        
        if self.small_blind <= 0:
            raise ValueError(f"Small blind must be positive: {self.small_blind}")
        
        if self.big_blind <= self.small_blind:
            raise ValueError(f"Big blind ({self.big_blind}) must be greater than small blind ({self.small_blind})")
    
    def create_snapshot(self) -> GameSnapshot:
        """Create an immutable snapshot of the current game state.
        
        Returns:
            A GameSnapshot containing a deep copy of the current state.
        """
        # Create deep copies of mutable objects
        players_copy = [copy.deepcopy(player) for player in self.players]
        community_cards_copy = copy.deepcopy(self.community_cards)
        events_copy = copy.deepcopy(self.events)
        
        return GameSnapshot(
            phase=self.phase,
            community_cards=community_cards_copy,
            pot=self.pot,
            current_bet=self.current_bet,
            last_raiser=self.last_raiser,
            last_raise_amount=self.last_raise_amount,
            players=players_copy,
            dealer_position=self.dealer_position,
            current_player=self.current_player,
            small_blind=self.small_blind,
            big_blind=self.big_blind,
            street_index=self.street_index,
            events=events_copy
        )
    
    def restore_from_snapshot(self, snapshot: GameSnapshot) -> None:
        """Restore game state from a snapshot.
        
        Args:
            snapshot: The snapshot to restore from.
        """
        self.phase = snapshot.phase
        self.community_cards = copy.deepcopy(snapshot.community_cards)
        self.pot = snapshot.pot
        self.current_bet = snapshot.current_bet
        self.last_raiser = snapshot.last_raiser
        self.last_raise_amount = snapshot.last_raise_amount
        self.players = copy.deepcopy(snapshot.players)
        self.dealer_position = snapshot.dealer_position
        self.current_player = snapshot.current_player
        self.small_blind = snapshot.small_blind
        self.big_blind = snapshot.big_blind
        self.street_index = snapshot.street_index
        self.events = copy.deepcopy(snapshot.events)
    
    def get_active_players(self) -> List[Player]:
        """Get all players who can currently act.
        
        Returns:
            List of players with ACTIVE status.
        """
        return [p for p in self.players if p.status == SeatStatus.ACTIVE]
    
    def get_players_in_hand(self) -> List[Player]:
        """Get all players still in the current hand.
        
        Returns:
            List of players with ACTIVE or ALL_IN status.
        """
        return [p for p in self.players if p.status in [SeatStatus.ACTIVE, SeatStatus.ALL_IN]]
    
    def get_player_by_seat(self, seat_id: int) -> Optional[Player]:
        """Get player by seat number.
        
        Args:
            seat_id: The seat number to look up.
            
        Returns:
            The player at the specified seat, or None if not found.
        """
        for player in self.players:
            if player.seat_id == seat_id:
                return player
        return None
    
    def get_current_player(self) -> Optional[Player]:
        """Get the player whose turn it is to act.
        
        Returns:
            The current player, or None if no current player.
        """
        if self.current_player is None:
            return None
        return self.get_player_by_seat(self.current_player)
    
    def add_player(self, player: Player) -> None:
        """Add a player to the game.
        
        Args:
            player: The player to add.
            
        Raises:
            ValueError: If seat is already occupied.
        """
        if self.get_player_by_seat(player.seat_id) is not None:
            raise ValueError(f"Seat {player.seat_id} is already occupied")
        
        self.players.append(player)
        self.add_event(f"Player {player.name} joined at seat {player.seat_id}")
    
    def remove_player(self, seat_id: int) -> Optional[Player]:
        """Remove a player from the game.
        
        Args:
            seat_id: The seat number of the player to remove.
            
        Returns:
            The removed player, or None if not found.
        """
        for i, player in enumerate(self.players):
            if player.seat_id == seat_id:
                removed_player = self.players.pop(i)
                self.add_event(f"Player {removed_player.name} left seat {seat_id}")
                return removed_player
        return None
    
    def initialize_deck(self, seed: Optional[int] = None) -> None:
        """Initialize and shuffle the deck.
        
        Args:
            seed: Optional seed for deterministic shuffling.
        """
        if seed is not None:
            self.rng.seed(seed)
        self.deck = Deck(self.rng)
        self.deck.shuffle()
        self.add_event("Deck initialized and shuffled")
    
    def deal_hole_cards(self) -> None:
        """Deal two hole cards to each active player.
        
        Raises:
            ValueError: If deck is not initialized or insufficient cards.
        """
        if self.deck is None:
            raise ValueError("Deck not initialized")
        
        active_players = [p for p in self.players if p.status != SeatStatus.OUT]
        
        if len(active_players) * 2 > self.deck.cards_remaining:
            raise ValueError("Insufficient cards in deck for hole cards")
        
        # Deal two cards to each player
        for player in active_players:
            if player.status != SeatStatus.OUT:
                cards = self.deck.deal_cards(2)
                player.set_hole_cards(cards)
        
        self.add_event(f"Dealt hole cards to {len(active_players)} players")
    
    def deal_community_cards(self, count: int) -> None:
        """Deal community cards.
        
        Args:
            count: Number of cards to deal.
            
        Raises:
            ValueError: If deck is not initialized or insufficient cards.
        """
        if self.deck is None:
            raise ValueError("Deck not initialized")
        
        if count <= 0:
            return
        
        # Burn a card (Texas Hold'em rule)
        if self.deck.cards_remaining > 0:
            self.deck.deal_card()
        
        # Deal the specified number of community cards
        for _ in range(count):
            if self.deck.cards_remaining > 0:
                card = self.deck.deal_card()
                self.community_cards.append(card)
            else:
                raise ValueError(f"Insufficient cards in deck to deal {count} community cards")
        
        # Log the event based on phase
        if self.phase == Phase.FLOP:
            cards_str = " ".join(str(card) for card in self.community_cards[-3:])
            self.add_event(f"Flop dealt: {cards_str}")
        elif self.phase == Phase.TURN:
            card_str = str(self.community_cards[-1])
            self.add_event(f"Turn dealt: {card_str}")
        elif self.phase == Phase.RIVER:
            card_str = str(self.community_cards[-1])
            self.add_event(f"River dealt: {card_str}")
    
    def collect_bets_to_pot(self) -> int:
        """Collect all current bets into the pot.
        
        Returns:
            The total amount collected.
        """
        collected = 0
        for player in self.players:
            collected += player.current_bet
            self.pot += player.current_bet
            player.reset_current_bet()
        
        if collected > 0:
            self.add_event(f"Collected {collected} chips to pot (total: {self.pot})")
        
        return collected
    
    def reset_betting_round(self) -> None:
        """Reset betting round state for a new round."""
        self.current_bet = 0
        self.last_raiser = None
        self.last_raise_amount = 0
        self.street_index = 0
        
        # Reset all players' current bets
        for player in self.players:
            player.reset_current_bet()
    
    def advance_phase(self) -> None:
        """Advance to the next game phase."""
        phase_order = [Phase.PRE_FLOP, Phase.FLOP, Phase.TURN, Phase.RIVER, Phase.SHOWDOWN]
        
        try:
            current_index = phase_order.index(self.phase)
            if current_index < len(phase_order) - 1:
                self.phase = phase_order[current_index + 1]
                self.add_event(f"Advanced to {self.phase.name}")
        except ValueError:
            # If current phase is not in the list, set to showdown
            self.phase = Phase.SHOWDOWN
            self.add_event(f"Advanced to {self.phase.name}")
    
    def add_event(self, event: str) -> None:
        """Add an event to the game log.
        
        Args:
            event: The event description to add.
        """
        self.events.append(event)
    
    def clear_events(self) -> None:
        """Clear the event log."""
        self.events.clear()
    
    def clone(self) -> 'GameState':
        """Create a deep copy of the game state.
        
        Returns:
            A deep copy of this GameState.
        """
        return copy.deepcopy(self)
    
    def to_dict(self, viewer_seat: Optional[int] = None) -> Dict[str, Any]:
        """Convert game state to dictionary format.
        
        Args:
            viewer_seat: Seat number of the viewer, used to hide other players' cards.
            
        Returns:
            Dictionary representation of the game state.
        """
        return self.create_snapshot().to_dict(viewer_seat)
    
    def __str__(self) -> str:
        """Return a readable representation of the game state."""
        community_str = " ".join(str(card) for card in self.community_cards)
        active_count = len(self.get_active_players())
        
        return (f"Phase: {self.phase.name}, "
                f"Community: [{community_str}], "
                f"Pot: {self.pot}, "
                f"Current bet: {self.current_bet}, "
                f"Active players: {active_count}")
    
    def __repr__(self) -> str:
        """Return a debug representation of the game state."""
        return f"GameState(phase={self.phase.name}, pot={self.pot}, players={len(self.players)})" 