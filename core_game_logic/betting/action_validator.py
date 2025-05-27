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
        # 必须有下注才能加注
        if state.current_bet == 0:
            raise InvalidActionError("没有下注时不能加注，请选择下注")
        
        call_amount = self._calculate_call_amount(state, player)
        # 最小加注为当前跟注金额+一个大盲注
        min_raise = state.current_bet + state.big_blind
        
        # 检查加注金额
        if action.amount < min_raise:
            raise InvalidActionError(f"加注金额{action.amount}不能小于最小加注{min_raise}")
        
        total_needed = call_amount + (action.amount - state.current_bet)
        
        if player.chips < total_needed:
            # 筹码不足，转换为全押
            return ValidatedAction(
                original_action=action,
                actual_action_type=ActionType.ALL_IN,
                actual_amount=player.chips,
                player_seat=player.seat_id,
                is_converted=True,
                conversion_reason=f"筹码不足加注到{action.amount}，转为全押{player.chips}"
            )
        
        return ValidatedAction(
            original_action=action,
            actual_action_type=ActionType.RAISE,
            actual_amount=action.amount,
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