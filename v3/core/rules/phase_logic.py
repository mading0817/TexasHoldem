"""
德州扑克游戏阶段逻辑模块

提供德州扑克游戏阶段转换和下一阶段判断的核心逻辑。
"""

from typing import Optional, List, Dict, Any
from ..state_machine.types import GamePhase, GameEvent, GameContext
from .types import PhaseTransition, CorePhaseLogicData
from .result import OperationResult

__all__ = [
    'get_possible_next_phases',
    'get_defined_next_phase_for_event',
    'get_next_phase_in_sequence',
    'get_core_phase_logic_data'
]


def get_possible_next_phases(current_phase: GamePhase, context: Optional[GameContext] = None) -> OperationResult[List[GamePhase]]:
    """
    获取从当前阶段可能转换到的所有下一阶段
    
    Args:
        current_phase: 当前游戏阶段
        context: 游戏上下文（可选，用于条件判断）
        
    Returns:
        包含可能的下一阶段列表的操作结果
    """
    # 德州扑克标准阶段转换规则
    phase_transitions = {
        GamePhase.INIT: [GamePhase.PRE_FLOP, GamePhase.FINISHED],
        GamePhase.PRE_FLOP: [GamePhase.FLOP, GamePhase.FINISHED],
        GamePhase.FLOP: [GamePhase.TURN, GamePhase.FINISHED],
        GamePhase.TURN: [GamePhase.RIVER, GamePhase.FINISHED],
        GamePhase.RIVER: [GamePhase.SHOWDOWN, GamePhase.FINISHED],
        GamePhase.SHOWDOWN: [GamePhase.FINISHED],
        GamePhase.FINISHED: []  # 终态，无下一阶段
    }
    
    possible_phases = phase_transitions.get(current_phase, [])
    
    # 如果提供了上下文，可以根据游戏状态进行条件判断
    if context is not None:
        # 例如：如果只剩一个玩家，可能直接跳到FINISHED
        if _only_one_active_player(context):
            possible_phases = [GamePhase.FINISHED]
    
    return OperationResult.success_result(data=possible_phases)


def get_defined_next_phase_for_event(current_phase: GamePhase, event_type: str, 
                                    context: Optional[GameContext] = None) -> OperationResult[Optional[GamePhase]]:
    """
    根据事件类型获取明确定义的下一阶段
    
    Args:
        current_phase: 当前游戏阶段
        event_type: 事件类型
        context: 游戏上下文（可选）
        
    Returns:
        包含下一阶段的操作结果，如果事件不会触发阶段转换则data为None
    """
    # 德州扑克事件驱动的阶段转换规则
    event_transitions = {
        'BETTING_ROUND_COMPLETE': {
            GamePhase.PRE_FLOP: GamePhase.FLOP,
            GamePhase.FLOP: GamePhase.TURN,
            GamePhase.TURN: GamePhase.RIVER,
            GamePhase.RIVER: GamePhase.SHOWDOWN,
            GamePhase.SHOWDOWN: GamePhase.FINISHED,
        },
        'HAND_START': {
            GamePhase.INIT: GamePhase.PRE_FLOP,
            GamePhase.FINISHED: GamePhase.PRE_FLOP,
        },
        'SHOWDOWN_COMPLETE': {
            GamePhase.SHOWDOWN: GamePhase.FINISHED,
        },
        'HAND_AUTO_FINISH': {
            GamePhase.PRE_FLOP: GamePhase.FINISHED,
            GamePhase.FLOP: GamePhase.FINISHED,
            GamePhase.TURN: GamePhase.FINISHED,
            GamePhase.RIVER: GamePhase.FINISHED,
        },
        'ALL_PLAYERS_FOLD': {
            GamePhase.PRE_FLOP: GamePhase.FINISHED,
            GamePhase.FLOP: GamePhase.FINISHED,
            GamePhase.TURN: GamePhase.FINISHED,
            GamePhase.RIVER: GamePhase.FINISHED,
        }
    }
    
    if event_type in event_transitions:
        transitions = event_transitions[event_type]
        next_phase = transitions.get(current_phase)
        
        # 如果提供了上下文，可以进行额外验证
        if next_phase is not None and context is not None:
            # 验证转换的合法性
            if not _is_valid_transition(current_phase, next_phase, context):
                return OperationResult.failure_result(
                    message=f"从 {current_phase} 到 {next_phase} 的转换在当前上下文无效",
                    error_code="INVALID_TRANSITION"
                )
        
        return OperationResult.success_result(data=next_phase)
    
    return OperationResult.success_result(data=None)


def get_next_phase_in_sequence(current_phase: GamePhase) -> OperationResult[Optional[GamePhase]]:
    """
    获取德州扑克标准序列中的下一阶段
    
    Args:
        current_phase: 当前游戏阶段
        
    Returns:
        包含序列中的下一阶段的操作结果，如果已是最后阶段则data为None
    """
    # 德州扑克标准阶段序列
    phase_sequence = [
        GamePhase.INIT,
        GamePhase.PRE_FLOP,
        GamePhase.FLOP,
        GamePhase.TURN,
        GamePhase.RIVER,
        GamePhase.SHOWDOWN,
        GamePhase.FINISHED
    ]
    
    try:
        current_index = phase_sequence.index(current_phase)
        if current_index < len(phase_sequence) - 1:
            return OperationResult.success_result(data=phase_sequence[current_index + 1])
    except ValueError:
        # 当前阶段不在标准序列中
        return OperationResult.failure_result(
            f"当前阶段 {current_phase} 不在标准序列中",
            error_code="INVALID_PHASE"
        )
    
    return OperationResult.success_result(data=None)


def get_core_phase_logic_data(current_phase: GamePhase, context: Optional[GameContext] = None) -> CorePhaseLogicData:
    """
    获取完整的核心阶段逻辑数据
    
    Args:
        current_phase: 当前游戏阶段
        context: 游戏上下文（可选）
        
    Returns:
        核心阶段逻辑数据
    """
    possible_next_result = get_possible_next_phases(current_phase, context)
    default_next_result = get_next_phase_in_sequence(current_phase)
    
    possible_next = possible_next_result.data if possible_next_result.success else []
    default_next = default_next_result.data if default_next_result.success else None
    
    # 构建有效的转换列表
    valid_transitions = []
    for next_phase in possible_next:
        transition = PhaseTransition(
            from_phase=current_phase,
            to_phase=next_phase,
            condition=_get_transition_condition(current_phase, next_phase)
        )
        valid_transitions.append(transition)
    
    return CorePhaseLogicData(
        current_phase=current_phase,
        possible_next_phases=possible_next,
        default_next_phase=default_next,
        valid_transitions=valid_transitions
    )


def _only_one_active_player(context: GameContext) -> bool:
    """
    检查是否只剩一个活跃玩家
    
    Args:
        context: 游戏上下文
        
    Returns:
        是否只剩一个活跃玩家
    """
    if not hasattr(context, 'players') or not context.players:
        return True  # 没有玩家时认为是单玩家状态
    
    # 计算有筹码的玩家数量（不管是否active，只要有筹码就算）
    players_with_chips = [
        player_id for player_id, player_data in context.players.items()
        if player_data.get('chips', 0) > 0
    ]
    
    return len(players_with_chips) <= 1


def _is_valid_transition(from_phase: GamePhase, to_phase: GamePhase, context: GameContext) -> bool:
    """
    验证阶段转换的合法性
    
    Args:
        from_phase: 源阶段
        to_phase: 目标阶段
        context: 游戏上下文
        
    Returns:
        转换是否合法
    """
    # 基本的转换合法性验证
    possible_phases_result = get_possible_next_phases(from_phase, context)
    if not possible_phases_result.success:
        return False
    return to_phase in possible_phases_result.data


def _get_transition_condition(from_phase: GamePhase, to_phase: GamePhase) -> Optional[str]:
    """
    获取阶段转换的条件描述
    
    Args:
        from_phase: 源阶段
        to_phase: 目标阶段
        
    Returns:
        转换条件的描述
    """
    conditions = {
        (GamePhase.INIT, GamePhase.PRE_FLOP): "开始新手牌",
        (GamePhase.PRE_FLOP, GamePhase.FLOP): "翻前下注轮结束",
        (GamePhase.FLOP, GamePhase.TURN): "翻牌下注轮结束",
        (GamePhase.TURN, GamePhase.RIVER): "转牌下注轮结束",
        (GamePhase.RIVER, GamePhase.SHOWDOWN): "河牌下注轮结束",
        (GamePhase.SHOWDOWN, GamePhase.FINISHED): "摊牌完成",
        # 特殊情况：直接结束
        (GamePhase.PRE_FLOP, GamePhase.FINISHED): "所有玩家弃牌或只剩一人",
        (GamePhase.FLOP, GamePhase.FINISHED): "所有玩家弃牌或只剩一人",
        (GamePhase.TURN, GamePhase.FINISHED): "所有玩家弃牌或只剩一人",
        (GamePhase.RIVER, GamePhase.FINISHED): "所有玩家弃牌或只剩一人",
    }
    
    return conditions.get((from_phase, to_phase)) 