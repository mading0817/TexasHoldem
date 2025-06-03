"""
Unit tests for v2 action validator module.

Tests the ActionValidator class and its validation logic for all action types.
"""

import pytest
from v2.core import (
    ActionValidator, Action, ValidatedAction, ActionType, SeatStatus,
    Player, InvalidActionError, InsufficientChipsError, GameStateProtocol
)
from v2.core.enums import ValidationResultData


class MockGameState:
    """Mock game state for testing validator."""
    
    def __init__(self, current_bet=0, big_blind=10, last_raise_amount=0, 
                 current_player_seat=1, player_bets=None):
        self._current_bet = current_bet
        self._big_blind = big_blind
        self._last_raise_amount = last_raise_amount
        self._current_player_seat = current_player_seat
        self._player_bets = player_bets or {}
    
    @property
    def current_bet(self) -> int:
        return self._current_bet
    
    @property
    def big_blind(self) -> int:
        return self._big_blind
    
    @property
    def last_raise_amount(self) -> int:
        return self._last_raise_amount
    
    @property
    def current_player_seat(self) -> int:
        return self._current_player_seat
    
    def get_player_current_bet(self, seat: int) -> int:
        return self._player_bets.get(seat, 0)


@pytest.mark.unit
@pytest.mark.fast
class TestActionValidator:
    """Test cases for ActionValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ActionValidator()
        self.player = Player(seat_id=1, name="Player1", chips=1000)
        self.game_state = MockGameState()
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_fold_action(self):
        """Test validation of fold actions."""
        action = Action(ActionType.FOLD)
        result = self.validator.validate(self.game_state, self.player, action)
        
        assert isinstance(result, ValidatedAction)
        assert result.final_action.action_type == ActionType.FOLD
        assert result.final_action.amount == 0
        assert result.final_action.player_id == 1
        assert not result.was_converted
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_check_action_valid(self):
        """Test validation of check action when no bet exists."""
        action = Action(ActionType.CHECK)
        result = self.validator.validate(self.game_state, self.player, action)
        
        assert result.final_action.action_type == ActionType.CHECK
        assert result.final_action.amount == 0
        assert not result.was_converted
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_check_action_invalid_with_bet(self):
        """Test that check is invalid when there's a bet."""
        self.game_state._current_bet = 50
        action = Action(ActionType.CHECK)
        
        with pytest.raises(InvalidActionError, match="Cannot check when there is a bet"):
            self.validator.validate(self.game_state, self.player, action)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_call_action_no_bet_converts_to_check(self):
        """Test that call converts to check when there's no bet."""
        action = Action(ActionType.CALL)
        result = self.validator.validate(self.game_state, self.player, action)
        
        assert result.final_action.action_type == ActionType.CHECK
        assert result.final_action.amount == 0
        assert result.was_converted
        assert "No bet to call" in result.conversion_reason
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_call_action_valid(self):
        """Test validation of call action with sufficient chips."""
        self.game_state._current_bet = 50
        action = Action(ActionType.CALL)
        result = self.validator.validate(self.game_state, self.player, action)
        
        assert result.final_action.action_type == ActionType.CALL
        assert result.final_action.amount == 50
        assert not result.was_converted
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_call_action_insufficient_chips_converts_to_all_in(self):
        """Test that call converts to all-in when chips are insufficient."""
        self.game_state._current_bet = 1500  # More than player's chips
        self.player = Player(seat_id=1, name="Player1", chips=800)
        action = Action(ActionType.CALL)
        result = self.validator.validate(self.game_state, self.player, action)
        
        assert result.final_action.action_type == ActionType.ALL_IN
        assert result.final_action.amount == 800
        assert result.was_converted
        assert "Insufficient chips to call" in result.conversion_reason
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_bet_action_valid(self):
        """Test validation of bet action when no current bet exists."""
        action = Action(ActionType.BET, amount=100)
        result = self.validator.validate(self.game_state, self.player, action)
        
        assert result.final_action.action_type == ActionType.BET
        assert result.final_action.amount == 100
        assert not result.was_converted
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_bet_action_invalid_with_existing_bet(self):
        """Test that bet is invalid when there's already a bet."""
        self.game_state._current_bet = 50
        action = Action(ActionType.BET, amount=100)
        
        with pytest.raises(InvalidActionError, match="Cannot bet when there is already a bet"):
            self.validator.validate(self.game_state, self.player, action)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_bet_action_invalid_below_big_blind(self):
        """Test that bet below big blind is invalid."""
        action = Action(ActionType.BET, amount=5)  # Less than big blind (10)
        
        with pytest.raises(InvalidActionError, match="Bet amount .* is less than big blind"):
            self.validator.validate(self.game_state, self.player, action)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_bet_action_insufficient_chips_converts_to_all_in(self):
        """Test that bet converts to all-in when chips are insufficient."""
        self.player = Player(seat_id=1, name="Player1", chips=50)
        action = Action(ActionType.BET, amount=100)
        result = self.validator.validate(self.game_state, self.player, action)
        
        assert result.final_action.action_type == ActionType.ALL_IN
        assert result.final_action.amount == 50
        assert result.was_converted
        assert "Insufficient chips to bet" in result.conversion_reason
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_raise_action_valid(self):
        """Test validation of raise action with sufficient amount."""
        self.game_state._current_bet = 50
        self.game_state._last_raise_amount = 10
        action = Action(ActionType.RAISE, amount=70)  # 50 + 10 minimum
        result = self.validator.validate(self.game_state, self.player, action)
        
        assert result.final_action.action_type == ActionType.RAISE
        assert result.final_action.amount == 70
        assert not result.was_converted
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_raise_action_invalid_no_bet(self):
        """Test that raise is invalid when there's no bet."""
        action = Action(ActionType.RAISE, amount=100)
        
        with pytest.raises(InvalidActionError, match="Cannot raise when there is no bet"):
            self.validator.validate(self.game_state, self.player, action)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_raise_action_invalid_below_minimum(self):
        """Test that raise below minimum is invalid."""
        self.game_state._current_bet = 50
        self.game_state._last_raise_amount = 20
        action = Action(ActionType.RAISE, amount=60)  # Less than 50 + 20
        
        with pytest.raises(InvalidActionError, match="Raise total .* is less than minimum raise"):
            self.validator.validate(self.game_state, self.player, action)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_raise_action_all_in_below_minimum_valid(self):
        """Test that all-in raise below minimum is valid."""
        self.game_state._current_bet = 50
        self.game_state._last_raise_amount = 20
        self.game_state._player_bets = {1: 0}  # Player hasn't bet yet
        self.player = Player(seat_id=1, name="Player1", chips=60)  # Can only go to 60 total
        action = Action(ActionType.RAISE, amount=60)  # Less than minimum 70, but all-in
        result = self.validator.validate(self.game_state, self.player, action)
        
        assert result.final_action.action_type == ActionType.ALL_IN
        assert result.final_action.amount == 60
        assert result.was_converted
        assert "equals all-in total" in result.conversion_reason
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_raise_action_insufficient_chips_to_call(self):
        """Test that raise fails when player can't even call."""
        self.game_state._current_bet = 100
        self.game_state._player_bets = {1: 0}
        self.player = Player(seat_id=1, name="Player1", chips=50)  # Can't even call
        action = Action(ActionType.RAISE, amount=120)
        
        with pytest.raises(InsufficientChipsError, match="Insufficient chips to call"):
            self.validator.validate(self.game_state, self.player, action)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_all_in_action_valid(self):
        """Test validation of all-in action."""
        action = Action(ActionType.ALL_IN)
        result = self.validator.validate(self.game_state, self.player, action)
        
        assert result.final_action.action_type == ActionType.ALL_IN
        assert result.final_action.amount == 1000  # Player's chip count
        assert not result.was_converted
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_all_in_action_invalid_no_chips(self):
        """Test that all-in is invalid when player has no chips."""
        self.player = Player(seat_id=1, name="Player1", chips=0)
        action = Action(ActionType.ALL_IN)
        
        with pytest.raises(InvalidActionError, match="Cannot go all-in with no chips"):
            self.validator.validate(self.game_state, self.player, action)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_basic_conditions_wrong_turn(self):
        """Test that validation fails when it's not the player's turn."""
        self.game_state._current_player_seat = 2  # Different player's turn
        action = Action(ActionType.FOLD)
        
        with pytest.raises(InvalidActionError, match="Not player .* turn"):
            self.validator.validate(self.game_state, self.player, action)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_basic_conditions_player_cannot_act(self):
        """Test that validation fails when player cannot act."""
        self.player.fold()  # Player is now folded
        action = Action(ActionType.CHECK)
        
        with pytest.raises(InvalidActionError, match="Player .* cannot act"):
            self.validator.validate(self.game_state, self.player, action)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_basic_conditions_no_current_player(self):
        """Test that validation fails when no player can act."""
        self.game_state._current_player_seat = None
        action = Action(ActionType.FOLD)
        
        with pytest.raises(InvalidActionError, match="No player can act"):
            self.validator.validate(self.game_state, self.player, action)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_calculate_call_amount_no_bet(self):
        """Test call amount calculation when there's no bet."""
        call_amount = self.validator._calculate_call_amount(self.game_state, self.player)
        assert call_amount == 0
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_calculate_call_amount_with_bet(self):
        """Test call amount calculation with existing bet."""
        self.game_state._current_bet = 100
        self.game_state._player_bets = {1: 30}  # Player has already bet 30
        call_amount = self.validator._calculate_call_amount(self.game_state, self.player)
        assert call_amount == 70  # 100 - 30
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_available_actions_no_bet(self):
        """Test available actions when there's no bet."""
        actions = self.validator.get_available_actions(self.game_state, self.player)
        
        assert ActionType.FOLD in actions
        assert ActionType.CHECK in actions
        assert ActionType.BET in actions
        assert ActionType.ALL_IN in actions
        assert ActionType.CALL not in actions
        assert ActionType.RAISE not in actions
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_available_actions_with_bet(self):
        """Test available actions when there's a bet."""
        self.game_state._current_bet = 50
        actions = self.validator.get_available_actions(self.game_state, self.player)
        
        assert ActionType.FOLD in actions
        assert ActionType.CALL in actions
        assert ActionType.RAISE in actions
        assert ActionType.ALL_IN in actions
        assert ActionType.CHECK not in actions
        assert ActionType.BET not in actions
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_available_actions_insufficient_chips_for_raise(self):
        """Test available actions when player can't afford minimum raise."""
        self.game_state._current_bet = 50
        self.game_state._last_raise_amount = 10
        self.game_state._player_bets = {1: 0}
        self.player = Player(seat_id=1, name="Player1", chips=55)  # Can call but not raise to 70
        actions = self.validator.get_available_actions(self.game_state, self.player)
        
        assert ActionType.FOLD in actions
        assert ActionType.CALL in actions
        assert ActionType.ALL_IN in actions
        assert ActionType.RAISE not in actions
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_available_actions_folded_player(self):
        """Test that folded player has no available actions."""
        self.player.fold()
        actions = self.validator.get_available_actions(self.game_state, self.player)
        
        assert actions == []
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_available_actions_no_chips(self):
        """Test available actions when player has no chips."""
        self.player = Player(seat_id=1, name="Player1", chips=0)
        actions = self.validator.get_available_actions(self.game_state, self.player)
        
        assert ActionType.FOLD in actions
        assert ActionType.CHECK in actions  # Can still check if no bet
        assert ActionType.ALL_IN not in actions  # Can't go all-in with no chips
        assert ActionType.BET not in actions


@pytest.mark.unit
@pytest.mark.fast
class TestActionDataClass:
    """Test cases for Action data class."""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_action_creation_valid(self):
        """Test creating valid actions."""
        fold_action = Action(ActionType.FOLD)
        assert fold_action.action_type == ActionType.FOLD
        assert fold_action.amount == 0
        
        bet_action = Action(ActionType.BET, amount=100)
        assert bet_action.action_type == ActionType.BET
        assert bet_action.amount == 100
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_action_creation_invalid_negative_amount(self):
        """Test that negative amounts are rejected."""
        with pytest.raises(ValueError, match="行动金额不能为负数"):
            Action(ActionType.BET, amount=-50)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_action_creation_invalid_fold_with_amount(self):
        """Test that fold with amount is rejected."""
        with pytest.raises(ValueError, match="fold行动不应该有金额"):
            Action(ActionType.FOLD, amount=100)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_action_creation_invalid_check_with_amount(self):
        """Test that check with amount is rejected."""
        with pytest.raises(ValueError, match="check行动不应该有金额"):
            Action(ActionType.CHECK, amount=50)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_action_string_representation(self):
        """Test string representation of actions."""
        fold_action = Action(ActionType.FOLD)
        # Action uses default dataclass string representation
        assert "ActionType.FOLD" in str(fold_action)
        assert "amount=0" in str(fold_action)


@pytest.mark.unit
@pytest.mark.fast
class TestValidatedActionDataClass:
    """Test cases for ValidatedAction data class."""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validated_action_creation(self):
        """Test creating ValidatedAction instances."""
        original = Action(ActionType.CALL)
        final = Action(ActionType.CHECK, 0, 1)
        validation_result = ValidationResultData(is_valid=True)
        
        validated = ValidatedAction(
            original_action=original,
            final_action=final,
            validation_result=validation_result,
            was_converted=True,
            conversion_reason="No bet to call"
        )
        
        assert validated.original_action == original
        assert validated.final_action == final
        assert validated.validation_result == validation_result
        assert validated.was_converted
        assert validated.conversion_reason == "No bet to call"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validated_action_string_representation(self):
        """Test string representation of ValidatedAction."""
        original = Action(ActionType.CALL)
        final = Action(ActionType.CALL, 50, 1)
        validation_result = ValidationResultData(is_valid=True)
        
        # Non-converted action
        validated = ValidatedAction(
            original_action=original,
            final_action=final,
            validation_result=validation_result
        )
        # ValidatedAction uses default dataclass string representation
        assert "ValidatedAction" in str(validated)
        assert "was_converted=False" in str(validated) 