"""
Simple AI strategy implementation for Texas Hold'em poker game v2.

This module provides a basic AI strategy that makes conservative decisions
based on simple rules and cost analysis.
"""

import random
from typing import Optional
from dataclasses import dataclass

from ..core import GameSnapshot, Action, ActionType, Player


@dataclass
class SimpleAIConfig:
    """Configuration for Simple AI strategy.
    
    Attributes:
        name: Name of the AI strategy
        conservativeness: How conservative the AI is (0.0-1.0)
        fold_threshold: Cost ratio threshold for folding
        bet_frequency: Frequency of making bets
        raise_frequency: Frequency of making raises
    """
    name: str = "SimpleAI"
    conservativeness: float = 0.8
    fold_threshold: float = 0.3
    bet_frequency: float = 0.2
    raise_frequency: float = 0.1


class SimpleAI:
    """Simple AI strategy implementation.
    
    This AI uses basic decision tree logic with conservative play style.
    It makes decisions based on cost analysis and simple risk assessment
    without complex hand strength evaluation.
    """
    
    def __init__(self, config: Optional[SimpleAIConfig] = None):
        """Initialize the Simple AI strategy.
        
        Args:
            config: Optional configuration parameters
        """
        self.config = config or SimpleAIConfig()
        self.decision_count = 0
        
    def decide(self, game_snapshot: GameSnapshot, player_id: int) -> Action:
        """Make a decision based on the current game state.
        
        Args:
            game_snapshot: Current game state snapshot
            player_id: ID of the player making the decision
            
        Returns:
            The action to take
            
        Raises:
            ValueError: If player_id is invalid
        """
        self.decision_count += 1
        
        # Find the player
        player = None
        for p in game_snapshot.players:
            if p.seat_id == player_id:
                player = p
                break
                
        if player is None:
            raise ValueError(f"Player {player_id} not found in game state")
            
        # Analyze the situation
        context = self._analyze_situation(player, game_snapshot)
        
        # Make decision based on context
        action = self._make_decision(player, context, game_snapshot)
        
        return action
        
    def _analyze_situation(self, player: Player, snapshot: GameSnapshot) -> dict:
        """Analyze the current situation for decision making.
        
        Args:
            player: The player making the decision
            snapshot: Current game state
            
        Returns:
            Dictionary containing analysis results
        """
        # Calculate call cost
        call_cost = max(0, snapshot.current_bet - player.current_bet)
        
        # Calculate cost ratio
        if player.chips > 0:
            cost_ratio = call_cost / player.chips
        else:
            cost_ratio = 1.0
            
        # Simple risk assessment
        risk_level = "low"
        reasoning = []
        
        if cost_ratio > self.config.fold_threshold:
            risk_level = "high"
            reasoning.append(f"Call cost too high ({cost_ratio:.1%})")
        elif cost_ratio > 0.1:
            risk_level = "medium"
            reasoning.append(f"Moderate call cost ({cost_ratio:.1%})")
        else:
            reasoning.append(f"Low call cost ({cost_ratio:.1%})")
            
        # Consider game phase
        if snapshot.phase.value == "PRE_FLOP":
            reasoning.append("Pre-flop phase, conservative play")
        elif len(snapshot.community_cards) >= 3:
            reasoning.append("Post-flop phase, cost-based decision")
            
        return {
            'call_cost': call_cost,
            'cost_ratio': cost_ratio,
            'risk_level': risk_level,
            'reasoning': '; '.join(reasoning)
        }
        
    def _make_decision(self, player: Player, context: dict, snapshot: GameSnapshot) -> Action:
        """Make the actual decision based on analysis.
        
        Args:
            player: The player making the decision
            context: Analysis context
            snapshot: Current game state
            
        Returns:
            The action to take
        """
        cost_ratio = context['cost_ratio']
        call_cost = context['call_cost']
        
        # High risk: fold if possible
        if cost_ratio > self.config.fold_threshold:
            return Action(player_id=player.seat_id, action_type=ActionType.FOLD)
            
        # Check if we can check (no bet to call)
        if snapshot.current_bet == player.current_bet:
            # Conservative check most of the time
            if random.random() < self.config.conservativeness:
                return Action(player_id=player.seat_id, action_type=ActionType.CHECK)
            # Occasionally bet
            elif random.random() < self.config.bet_frequency:
                bet_amount = self._calculate_bet_amount(player, snapshot)
                return Action(
                    player_id=player.seat_id, 
                    action_type=ActionType.BET, 
                    amount=bet_amount
                )
                
        # If there's a bet to call
        if call_cost > 0:
            # Call if cost is acceptable
            if cost_ratio <= self.config.fold_threshold:
                # Occasionally raise instead of call
                if random.random() < self.config.raise_frequency:
                    raise_amount = self._calculate_raise_amount(player, snapshot)
                    if raise_amount <= player.chips:
                        return Action(
                            player_id=player.seat_id,
                            action_type=ActionType.RAISE,
                            amount=raise_amount
                        )
                        
                # Default to call
                return Action(
                    player_id=player.seat_id,
                    action_type=ActionType.CALL,
                    amount=call_cost
                )
                
        # Default to check if possible, otherwise fold
        if snapshot.current_bet == player.current_bet:
            return Action(player_id=player.seat_id, action_type=ActionType.CHECK)
        else:
            return Action(player_id=player.seat_id, action_type=ActionType.FOLD)
            
    def _calculate_bet_amount(self, player: Player, snapshot: GameSnapshot) -> int:
        """Calculate bet amount using conservative strategy.
        
        Args:
            player: The player making the bet
            snapshot: Current game state
            
        Returns:
            Bet amount
        """
        # Use big blind as base unit (assume 10 for now)
        big_blind = snapshot.big_blind if hasattr(snapshot, 'big_blind') else 10
        
        # Bet 1-3 times the big blind
        min_bet = big_blind
        max_bet = big_blind * 3
        bet_amount = random.randint(min_bet, max_bet)
        
        # Don't bet more than we have
        return min(bet_amount, player.chips)
        
    def _calculate_raise_amount(self, player: Player, snapshot: GameSnapshot) -> int:
        """Calculate raise amount using conservative strategy.
        
        Args:
            player: The player making the raise
            snapshot: Current game state
            
        Returns:
            Raise amount
        """
        # Use big blind as base unit
        big_blind = snapshot.big_blind if hasattr(snapshot, 'big_blind') else 10
        current_bet = snapshot.current_bet
        
        # Raise by 1-2 times the big blind
        min_raise = current_bet + big_blind
        max_raise = current_bet + big_blind * 2
        raise_amount = random.randint(min_raise, max_raise)
        
        # Don't raise more than we have
        return min(raise_amount, player.chips) 