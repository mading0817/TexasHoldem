"""
行动逻辑模块

实现德州扑克可用行动的判断逻辑。
"""

from typing import List
from v3.core.state_machine.types import GameContext, GamePhase
from v3.core.betting.betting_types import BetType
from v3.core.rules.types import CorePermissibleActionsData, ActionConstraints

__all__ = ['determine_permissible_actions']


def determine_permissible_actions(game_context: GameContext, player_id: str) -> CorePermissibleActionsData:
    """
    确定玩家的可用行动
    
    Args:
        game_context: 游戏上下文
        player_id: 玩家ID
        
    Returns:
        核心层可用行动数据
        
    Raises:
        ValueError: 当玩家不存在或参数无效时
    """
    if not player_id:
        raise ValueError("player_id不能为空")
    
    if player_id not in game_context.players:
        raise ValueError(f"玩家 {player_id} 不在游戏中")
    
    player_data = game_context.players[player_id]
    is_player_active = player_data.get('active', False)
    player_chips = player_data.get('chips', 0)
    player_current_bet = player_data.get('current_bet', 0)
    
    # 非活跃玩家没有可用行动
    if not is_player_active:
        return CorePermissibleActionsData(
            player_id=player_id,
            available_bet_types=[],
            constraints=ActionConstraints(
                big_blind_amount=game_context.big_blind
            ),
            player_chips=player_chips,
            is_player_active=False,
            reasoning="玩家非活跃状态"
        )
    
    # 只有在下注阶段才有行动
    if game_context.current_phase not in [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]:
        return CorePermissibleActionsData(
            player_id=player_id,
            available_bet_types=[BetType.FOLD],  # 活跃玩家至少能弃牌
            constraints=ActionConstraints(
                big_blind_amount=game_context.big_blind
            ),
            player_chips=player_chips,
            is_player_active=True,
            reasoning=f"当前阶段 {game_context.current_phase.name} 不允许玩家行动"
        )
    
    # 计算行动约束
    current_bet = game_context.current_bet
    call_amount = max(0, current_bet - player_current_bet)
    big_blind = game_context.big_blind
    
    # 计算加注范围
    min_raise_amount = current_bet + big_blind  # 最小加注到当前下注 + 大盲注
    max_raise_amount = player_current_bet + player_chips  # 玩家的所有筹码
    
    constraints = ActionConstraints(
        min_call_amount=call_amount,
        min_raise_amount=min_raise_amount,
        max_raise_amount=max_raise_amount,
        big_blind_amount=big_blind,
        is_all_in_available=(player_chips > 0)
    )
    
    # 确定可用行动
    available_actions: List[BetType] = []
    
    # 总是可以弃牌
    available_actions.append(BetType.FOLD)
    
    # 如果当前没有下注，可以过牌
    if current_bet == 0:
        available_actions.append(BetType.CHECK)
        
        # 如果有筹码，可以下注（作为加注处理）
        if player_chips > 0:
            available_actions.append(BetType.RAISE)
    else:
        # 如果有下注，需要决定是否可以跟注
        if player_chips >= call_amount:
            available_actions.append(BetType.CALL)
            
            # 如果还有足够筹码进行最小加注，可以加注
            needed_for_min_raise = call_amount + big_blind
            if player_chips > needed_for_min_raise:
                available_actions.append(BetType.RAISE)
    
    # 如果有筹码，总是可以全押
    if player_chips > 0:
        available_actions.append(BetType.ALL_IN)
    
    return CorePermissibleActionsData(
        player_id=player_id,
        available_bet_types=available_actions,
        constraints=constraints,
        player_chips=player_chips,
        is_player_active=True,
        reasoning="基于当前游戏状态和玩家筹码确定可用行动"
    ) 