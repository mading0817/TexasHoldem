"""
玩家行动验证器
实现行动验证和智能转换逻辑
"""

from typing import Optional, List
from ..core.enums import ActionType, Action, ValidatedAction
from ..game.game_state import GameState
from ..core.player import Player
from ..core.exceptions import InvalidActionError, InsufficientChipsError


class ActionValidator:
    """
    玩家行动验证器
    负责验证玩家行动的合法性并进行智能转换
    """
    
    def validate(self, state: GameState, player: Player, action: Action) -> ValidatedAction:
        """
        验证并转换玩家行动
        
        Args:
            state: 当前游戏状态
            player: 执行行动的玩家
            action: 原始行动
            
        Returns:
            验证后的行动
            
        Raises:
            InvalidActionError: 当行动无效时
            InsufficientChipsError: 当筹码不足时（严格验证场景）
        """
        # 基础验证
        self._validate_basic_conditions(state, player, action)
        
        # 根据行动类型进行具体验证和转换
        if action.action_type == ActionType.FOLD:
            return self._validate_fold(player, action)
        elif action.action_type == ActionType.CHECK:
            return self._validate_check(state, player, action)
        elif action.action_type == ActionType.CALL:
            return self._validate_call(state, player, action)
        elif action.action_type == ActionType.BET:
            return self._validate_bet(state, player, action)
        elif action.action_type == ActionType.RAISE:
            return self._validate_raise(state, player, action)
        elif action.action_type == ActionType.ALL_IN:
            return self._validate_all_in(player, action)
        else:
            raise InvalidActionError(f"未知的行动类型: {action.action_type}")
    
    def _validate_basic_conditions(self, state: GameState, player: Player, action: Action):
        """验证基础条件"""
        # 检查玩家是否可以行动
        if not player.can_act():
            raise InvalidActionError(f"玩家{player.seat_id}无法行动，当前状态: {player.status.name}")
        
        # 检查是否轮到该玩家
        if state.current_player != player.seat_id:
            raise InvalidActionError(f"不是玩家{player.seat_id}的回合，当前玩家: {state.current_player}")
        
        # 验证行动金额的基础合理性
        # 注意：超出筹码的下注/加注由具体验证方法处理（可能转换为全押）
        if action.action_type in [ActionType.BET, ActionType.RAISE]:
            if action.amount <= 0:
                raise InvalidActionError(f"下注/加注金额必须为正数: {action.amount}")
            # 移除筹码上限检查，让具体验证方法处理转换
        
        # 设置行动的玩家座位号
        action.player_seat = player.seat_id
    
    def _validate_fold(self, player: Player, action: Action) -> ValidatedAction:
        """验证弃牌行动"""
        return ValidatedAction(
            original_action=action,
            actual_action_type=ActionType.FOLD,
            actual_amount=0,
            player_seat=player.seat_id
        )
    
    def _validate_check(self, state: GameState, player: Player, action: Action) -> ValidatedAction:
        """验证过牌行动"""
        # 只有在没有下注时才能过牌
        call_amount = self._calculate_call_amount(state, player)
        if call_amount > 0:
            raise InvalidActionError(f"有下注{call_amount}时不能过牌，请选择跟注或弃牌")
        
        return ValidatedAction(
            original_action=action,
            actual_action_type=ActionType.CHECK,
            actual_amount=0,
            player_seat=player.seat_id
        )
    
    def _validate_call(self, state: GameState, player: Player, action: Action) -> ValidatedAction:
        """验证跟注行动"""
        call_amount = self._calculate_call_amount(state, player)
        
        if call_amount == 0:
            # 没有需要跟注的金额，转换为过牌
            return ValidatedAction(
                original_action=action,
                actual_action_type=ActionType.CHECK,
                actual_amount=0,
                player_seat=player.seat_id,
                is_converted=True,
                conversion_reason="无需跟注，转为过牌"
            )
        
        if player.chips < call_amount:
            # 筹码不足，转换为全押
            return ValidatedAction(
                original_action=action,
                actual_action_type=ActionType.ALL_IN,
                actual_amount=player.chips,
                player_seat=player.seat_id,
                is_converted=True,
                conversion_reason=f"筹码不足跟注{call_amount}，转为全押{player.chips}"
            )
        
        return ValidatedAction(
            original_action=action,
            actual_action_type=ActionType.CALL,
            actual_amount=call_amount,
            player_seat=player.seat_id
        )
    
    def _validate_bet(self, state: GameState, player: Player, action: Action) -> ValidatedAction:
        """验证下注行动"""
        # 只有在没有人下注时才能下注
        if state.current_bet > 0:
            raise InvalidActionError(f"已有下注{state.current_bet}时不能下注，请选择跟注、加注或弃牌")
        
        # 检查下注金额
        if action.amount < state.big_blind:
            raise InvalidActionError(f"下注金额{action.amount}不能小于大盲注{state.big_blind}")
        
        if player.chips < action.amount:
            # 筹码不足，转换为全押
            return ValidatedAction(
                original_action=action,
                actual_action_type=ActionType.ALL_IN,
                actual_amount=player.chips,
                player_seat=player.seat_id,
                is_converted=True,
                conversion_reason=f"筹码不足下注{action.amount}，转为全押{player.chips}"
            )
        
        return ValidatedAction(
            original_action=action,
            actual_action_type=ActionType.BET,
            actual_amount=action.amount,
            player_seat=player.seat_id
        )
    
    def _validate_raise(self, state: GameState, player: Player, action: Action) -> ValidatedAction:
        """验证加注行动"""
        if state.current_bet == 0:
            raise InvalidActionError("没有下注时不能加注，请选择下注")
        
        # The amount the player wants their total bet to be for this street.
        intended_total_bet_by_player = action.amount

        # Determine the minimum legal raise amount.
        # This is the difference between the current bet and the bet before the last raise.
        # Or, if no raise yet, it's the big blind.
        # GameState.last_raise_amount should store this value.
        actual_last_raise_increment = state.last_raise_amount if state.last_raise_amount > 0 else state.big_blind
        
        # The minimum total bet a player must make to constitute a valid raise.
        min_legal_total_bet_for_raise = state.current_bet + actual_last_raise_increment

        # Check if the player's intended total bet meets the minimum raise requirement.
        if intended_total_bet_by_player < min_legal_total_bet_for_raise:
            # Exception: Player is going all-in.
            # An all-in can be for less than a full raise, but must be more than a call.
            # Player's total commitment if they go all-in now:
            player_total_commitment_if_all_in = player.current_bet + player.chips

            if intended_total_bet_by_player == player_total_commitment_if_all_in and player.chips > 0: # Player IS going all-in with this action.amount
                if intended_total_bet_by_player <= state.current_bet: # All-in is not even a call or is for 0 effective chips
                    # This should ideally be caught by chip check later or converted to CALL if chips < call_amount
                    # but if action.amount is the all-in amount and it's less than current_bet, it's an issue.
                    # This case is complex: if all-in is for less than call, it should be call all-in.
                    # If all-in is for more than call, but less than min raise, it is a valid all-in raise.
                    # The primary check here is for *non-all-in* raises that are too small.
                    pass # All-in for less than min raise is allowed, will be handled by chip check / conversion to ALL_IN type
                # else: This is an all-in raise that is valid but potentially short.
            else: # Not an all-in, and raise is too small
                raise InvalidActionError(
                    f"加注总额 {intended_total_bet_by_player} 小于最小加注目标 {min_legal_total_bet_for_raise}. "
                    f"(当前下注: {state.current_bet}, 要求至少增加: {actual_last_raise_increment})"
                )

        # Calculate how many additional chips the player needs to put into the pot for this action.
        chips_to_add = intended_total_bet_by_player - player.current_bet
        if chips_to_add <= 0 and intended_total_bet_by_player > state.current_bet:
            # This implies player.current_bet was already >= intended_total_bet_by_player,
            # but intended_total_bet_by_player is a raise. This state seems inconsistent.
            # For a raise, intended_total_bet_by_player must be > state.current_bet.
            # And player.current_bet should be <= state.current_bet.
            # If intended_total_bet_by_player is the target, player must add (intended_total_bet_by_player - player.current_bet).
            pass # This scenario should be okay if player.chips is sufficient.

        if player.chips < chips_to_add:
            # Not enough chips for the intended raise. Convert to All-In.
            # The actual all-in amount becomes the player's new total bet.
            all_in_new_total_bet = player.current_bet + player.chips

            # An all-in must at least be a call if a call is possible.
            # If all_in_new_total_bet < state.current_bet, it should be an AllIn Call.
            # If all_in_new_total_bet > state.current_bet, it's an AllIn Raise.
            # The previous check for intended_total_bet_by_player < min_legal_total_bet_for_raise
            # already covers non-all-in small raises. If we are here, it's an all-in conversion.
            if all_in_new_total_bet < state.current_bet and player.chips > 0:
                 # This implies the all-in is not even enough to call. 
                 # This should be handled by _validate_call conversion to ALL_IN if action was CALL.
                 # If action was RAISE but all-in is less than call, it's an invalid state for RAISE intent.
                 # However, an ALL_IN action type would be fine.
                 # For RAISE type, player must be able to at least call.
                raise InsufficientChipsError(f"筹码不足以完成跟注 {state.current_bet} (需要 {state.current_bet - player.current_bet}), 无法加注")

            return ValidatedAction(
                original_action=action,
                actual_action_type=ActionType.ALL_IN,
                actual_amount=all_in_new_total_bet, # The player's new total bet for the street
                player_seat=player.seat_id,
                is_converted=True,
                conversion_reason=f"筹码不足加注到{intended_total_bet_by_player}，转为全押至{all_in_new_total_bet}"
            )
        
        return ValidatedAction(
            original_action=action,
            actual_action_type=ActionType.RAISE,
            actual_amount=intended_total_bet_by_player,
            player_seat=player.seat_id
        )
    
    def _validate_all_in(self, player: Player, action: Action) -> ValidatedAction:
        """验证全押行动"""
        if player.chips == 0:
            raise InvalidActionError("没有筹码无法全押")
        
        return ValidatedAction(
            original_action=action,
            actual_action_type=ActionType.ALL_IN,
            actual_amount=player.chips,
            player_seat=player.seat_id
        )
    
    def _calculate_call_amount(self, state: GameState, player: Player) -> int:
        """
        计算玩家需要跟注的金额
        
        Args:
            state: 游戏状态
            player: 玩家
            
        Returns:
            需要跟注的金额
        """
        return max(0, state.current_bet - player.current_bet)
    
    def get_available_actions(self, state: GameState, player: Player) -> List[ActionType]:
        """
        获取玩家可执行的行动列表
        
        Args:
            state: 游戏状态
            player: 玩家
            
        Returns:
            可执行的行动类型列表
        """
        if not player.can_act():
            return []
        
        actions = [ActionType.FOLD]  # 总是可以弃牌
        
        call_amount = self._calculate_call_amount(state, player)
        
        if call_amount == 0:
            # 没有下注，可以过牌
            actions.append(ActionType.CHECK)
            if player.chips >= state.big_blind:
                actions.append(ActionType.BET)  # 可以下注
        else:
            # 有下注，可以跟注
            actions.append(ActionType.CALL)
            if player.chips > call_amount:
                min_raise = state.current_bet + state.big_blind
                if player.chips >= min_raise:
                    actions.append(ActionType.RAISE)  # 可以加注
        
        # 总是可以全押（如果有筹码）
        if player.chips > 0:
            actions.append(ActionType.ALL_IN)
        
        return actions 