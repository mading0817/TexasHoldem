"""
Action validator for Texas Hold'em poker game.

This module provides validation logic for player actions, including
intelligent conversion of invalid actions to valid alternatives.
"""

from typing import Protocol, List, Optional
from .enums import ActionType, Action, ValidatedAction, ValidationResultData, SeatStatus
from .player import Player


class GameStateProtocol(Protocol):
    """Protocol defining the game state interface required by the validator.
    
    This protocol defines the minimum interface that a game state object
    must implement to be used with the ActionValidator.
    """
    
    @property
    def current_bet(self) -> int:
        """The current highest bet amount in the current betting round."""
        ...
    
    @property
    def big_blind(self) -> int:
        """The big blind amount for this game."""
        ...
    
    @property
    def last_raise_amount(self) -> int:
        """The amount of the last raise in the current betting round."""
        ...
    
    @property
    def current_player_seat(self) -> Optional[int]:
        """The seat number of the player whose turn it is to act."""
        ...
    
    def get_player_current_bet(self, seat: int) -> int:
        """Get the current bet amount for a specific player.
        
        Args:
            seat: The seat number of the player.
            
        Returns:
            The amount the player has bet in the current betting round.
        """
        ...


class InvalidActionError(Exception):
    """Exception raised when a player action is invalid."""

    pass


class InsufficientChipsError(Exception):
    """Exception raised when a player doesn't have enough chips for an action."""

    pass


class ActionValidator:
    """Action validator for poker player actions.
    
    Validates player actions and provides intelligent conversion of invalid
    actions to valid alternatives when possible.
    """
    
    def validate(self, game_state: GameStateProtocol, player: Player, action: Action) -> ValidatedAction:
        """Validate and potentially convert a player action.
        
        Args:
            game_state: The current game state.
            player: The player attempting the action.
            action: The action to validate.
            
        Returns:
            A ValidatedAction containing the original action and validated parameters.
            
        Raises:
            InvalidActionError: When the action is invalid and cannot be converted.
            InsufficientChipsError: When the player lacks chips for the action.
        """
        # Basic validation
        self._validate_basic_conditions(game_state, player, action)
        
        # Validate specific action types
        if action.action_type == ActionType.FOLD:
            return self._validate_fold(player, action)
        elif action.action_type == ActionType.CHECK:
            return self._validate_check(game_state, player, action)
        elif action.action_type == ActionType.CALL:
            return self._validate_call(game_state, player, action)
        elif action.action_type == ActionType.BET:
            return self._validate_bet(game_state, player, action)
        elif action.action_type == ActionType.RAISE:
            return self._validate_raise(game_state, player, action)
        elif action.action_type == ActionType.ALL_IN:
            return self._validate_all_in(player, action)
        else:
            raise InvalidActionError(f"Unknown action type: {action.action_type}")
    
    def _validate_basic_conditions(self, game_state: GameStateProtocol, player: Player, action: Action) -> None:
        """Validate basic conditions for any action.
        
        Args:
            game_state: The current game state.
            player: The player attempting the action.
            action: The action to validate.
            
        Raises:
            InvalidActionError: When basic conditions are not met.
        """
        # Check if player can act
        if player.status != SeatStatus.ACTIVE:
            raise InvalidActionError(f"Player {player.seat_id} cannot act, status: {player.status.value}")
        
        # Check if it's the player's turn
        if game_state.current_player_seat is None:
            raise InvalidActionError("No player can act, game phase should transition")
        
        if game_state.current_player_seat != player.seat_id:
            raise InvalidActionError(
                f"Not player {player.seat_id}'s turn, current player: {game_state.current_player_seat}"
            )
        
        # Validate action amount for betting actions
        if action.action_type in [ActionType.BET, ActionType.RAISE]:
            if action.amount <= 0:
                raise InvalidActionError(f"Bet/raise amount must be positive: {action.amount}")
    
    def _validate_fold(self, player: Player, action: Action) -> ValidatedAction:
        """Validate a fold action.
        
        Args:
            player: The player attempting to fold.
            action: The fold action.
            
        Returns:
            A validated fold action.
        """
        final_action = Action(ActionType.FOLD, 0, player.seat_id)
        validation_result = ValidationResultData(is_valid=True)
        
        return ValidatedAction(
            original_action=action,
            final_action=final_action,
            validation_result=validation_result
        )
    
    def _validate_check(self, game_state: GameStateProtocol, player: Player, action: Action) -> ValidatedAction:
        """Validate a check action.
        
        Args:
            game_state: The current game state.
            player: The player attempting to check.
            action: The check action.
            
        Returns:
            A validated check action.
            
        Raises:
            InvalidActionError: When checking is not allowed.
        """
        call_amount = self._calculate_call_amount(game_state, player)
        if call_amount > 0:
            raise InvalidActionError(f"Cannot check when there is a bet of {call_amount}, must call or fold")
        
        final_action = Action(ActionType.CHECK, 0, player.seat_id)
        validation_result = ValidationResultData(is_valid=True)
        
        return ValidatedAction(
            original_action=action,
            final_action=final_action,
            validation_result=validation_result
        )
    
    def _validate_call(self, game_state: GameStateProtocol, player: Player, action: Action) -> ValidatedAction:
        """Validate a call action.
        
        Args:
            game_state: The current game state.
            player: The player attempting to call.
            action: The call action.
            
        Returns:
            A validated call action, possibly converted to check or all-in.
        """
        call_amount = self._calculate_call_amount(game_state, player)
        
        if call_amount == 0:
            # No bet to call, convert to check
            final_action = Action(ActionType.CHECK, 0, player.seat_id)
            validation_result = ValidationResultData(is_valid=True)
            
            return ValidatedAction(
                original_action=action,
                final_action=final_action,
                validation_result=validation_result,
                was_converted=True,
                conversion_reason="No bet to call, converted to check"
            )
        
        if player.chips < call_amount:
            # Insufficient chips, convert to all-in
            final_action = Action(ActionType.ALL_IN, player.chips, player.seat_id)
            validation_result = ValidationResultData(is_valid=True)
            
            return ValidatedAction(
                original_action=action,
                final_action=final_action,
                validation_result=validation_result,
                was_converted=True,
                conversion_reason=f"Insufficient chips to call {call_amount}, converted to all-in {player.chips}"
            )
        
        final_action = Action(ActionType.CALL, call_amount, player.seat_id)
        validation_result = ValidationResultData(is_valid=True)
        
        return ValidatedAction(
            original_action=action,
            final_action=final_action,
            validation_result=validation_result
        )
    
    def _validate_bet(self, game_state: GameStateProtocol, player: Player, action: Action) -> ValidatedAction:
        """Validate a bet action.
        
        Args:
            game_state: The current game state.
            player: The player attempting to bet.
            action: The bet action.
            
        Returns:
            A validated bet action, possibly converted to all-in.
            
        Raises:
            InvalidActionError: When betting is not allowed.
        """
        # Can only bet when there's no current bet
        if game_state.current_bet > 0:
            raise InvalidActionError(
                f"Cannot bet when there is already a bet of {game_state.current_bet}, "
                "must call, raise, or fold"
            )
        
        # Check minimum bet amount
        if action.amount < game_state.big_blind:
            raise InvalidActionError(
                f"Bet amount {action.amount} is less than big blind {game_state.big_blind}"
            )
        
        if player.chips < action.amount:
            # Insufficient chips, convert to all-in
            final_action = Action(ActionType.ALL_IN, player.chips, player.seat_id)
            validation_result = ValidationResultData(is_valid=True)
            
            return ValidatedAction(
                original_action=action,
                final_action=final_action,
                validation_result=validation_result,
                was_converted=True,
                conversion_reason=f"Insufficient chips to bet {action.amount}, converted to all-in {player.chips}"
            )
        
        final_action = Action(ActionType.BET, action.amount, player.seat_id)
        validation_result = ValidationResultData(is_valid=True)
        
        return ValidatedAction(
            original_action=action,
            final_action=final_action,
            validation_result=validation_result
        )
    
    def _validate_raise(self, game_state: GameStateProtocol, player: Player, action: Action) -> ValidatedAction:
        """Validate a raise action.
        
        Args:
            game_state: The current game state.
            player: The player attempting to raise.
            action: The raise action.
            
        Returns:
            A validated raise action, possibly converted to all-in.
            
        Raises:
            InvalidActionError: When raising is not allowed.
            InsufficientChipsError: When the player cannot even call.
        """
        if game_state.current_bet == 0:
            raise InvalidActionError("Cannot raise when there is no bet, must bet instead")
        
        # Calculate minimum raise amount
        last_raise_increment = game_state.last_raise_amount if game_state.last_raise_amount > 0 else game_state.big_blind
        min_raise_total = game_state.current_bet + last_raise_increment
        
        # Calculate player's current bet and potential all-in total
        player_current_bet = game_state.get_player_current_bet(player.seat_id)
        all_in_total = player_current_bet + player.chips
        
        # Check if this is an all-in situation (player wants to raise to exactly their all-in amount)
        if action.amount == all_in_total and player.chips > 0:
            # This is an all-in raise
            if all_in_total <= game_state.current_bet:
                # All-in is not even enough to call
                raise InsufficientChipsError(
                    f"Insufficient chips to call {game_state.current_bet}, cannot raise"
                )
            # All-in raise is valid even if less than minimum raise
            final_action = Action(ActionType.ALL_IN, all_in_total, player.seat_id)
            validation_result = ValidationResultData(is_valid=True)
            
            return ValidatedAction(
                original_action=action,
                final_action=final_action,
                validation_result=validation_result,
                was_converted=True,
                conversion_reason=f"Raise amount {action.amount} equals all-in total, converted to all-in"
            )
        
        # Check if raise amount meets minimum requirement for non-all-in raises
        if action.amount < min_raise_total:
            raise InvalidActionError(
                f"Raise total {action.amount} is less than minimum raise {min_raise_total}. "
                f"(Current bet: {game_state.current_bet}, minimum increase: {last_raise_increment})"
            )
        
        # Calculate chips needed for this raise
        chips_needed = action.amount - player_current_bet
        
        if player.chips < chips_needed:
            # Not enough chips for intended raise, convert to all-in
            if all_in_total < game_state.current_bet and player.chips > 0:
                raise InsufficientChipsError(
                    f"Insufficient chips to call {game_state.current_bet}, cannot raise"
                )
            
            final_action = Action(ActionType.ALL_IN, all_in_total, player.seat_id)
            validation_result = ValidationResultData(is_valid=True)
            
            return ValidatedAction(
                original_action=action,
                final_action=final_action,
                validation_result=validation_result,
                was_converted=True,
                conversion_reason=f"Insufficient chips to raise to {action.amount}, converted to all-in {all_in_total}"
            )
        
        final_action = Action(ActionType.RAISE, action.amount, player.seat_id)
        validation_result = ValidationResultData(is_valid=True)
        
        return ValidatedAction(
            original_action=action,
            final_action=final_action,
            validation_result=validation_result
        )
    
    def _validate_all_in(self, player: Player, action: Action) -> ValidatedAction:
        """Validate an all-in action.
        
        Args:
            player: The player attempting to go all-in.
            action: The all-in action.
            
        Returns:
            A validated all-in action.
            
        Raises:
            InvalidActionError: When the player has no chips.
        """
        if player.chips == 0:
            raise InvalidActionError("Cannot go all-in with no chips")
        
        final_action = Action(ActionType.ALL_IN, player.chips, player.seat_id)
        validation_result = ValidationResultData(is_valid=True)
        
        return ValidatedAction(
            original_action=action,
            final_action=final_action,
            validation_result=validation_result
        )
    
    def _calculate_call_amount(self, game_state: GameStateProtocol, player: Player) -> int:
        """Calculate the amount needed for a player to call.
        
        Args:
            game_state: The current game state.
            player: The player for whom to calculate the call amount.
            
        Returns:
            The amount needed to call (0 if no call is needed).
        """
        player_current_bet = game_state.get_player_current_bet(player.seat_id)
        return max(0, game_state.current_bet - player_current_bet)
    
    def get_available_actions(self, game_state: GameStateProtocol, player: Player) -> List[ActionType]:
        """Get the list of available actions for a player.
        
        Args:
            game_state: The current game state.
            player: The player for whom to get available actions.
            
        Returns:
            A list of available action types.
        """
        if player.status != SeatStatus.ACTIVE:
            return []
        
        actions = [ActionType.FOLD]  # Can always fold
        
        call_amount = self._calculate_call_amount(game_state, player)
        
        if call_amount == 0:
            # No bet to call, can check
            actions.append(ActionType.CHECK)
            if player.chips >= game_state.big_blind:
                actions.append(ActionType.BET)  # Can bet
        else:
            # There is a bet, can call
            actions.append(ActionType.CALL)
            if player.chips > call_amount:
                # Can afford more than a call
                last_raise_increment = game_state.last_raise_amount if game_state.last_raise_amount > 0 else game_state.big_blind
                min_raise_total = game_state.current_bet + last_raise_increment
                player_current_bet = game_state.get_player_current_bet(player.seat_id)
                chips_needed_for_min_raise = min_raise_total - player_current_bet
                
                if player.chips >= chips_needed_for_min_raise:
                    actions.append(ActionType.RAISE)  # Can raise
        
        # Can always go all-in if have chips
        if player.chips > 0:
            actions.append(ActionType.ALL_IN)
        
        return actions 