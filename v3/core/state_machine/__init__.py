"""
游戏状态机模块

提供德州扑克游戏的状态管理和阶段转换功能。
"""

from typing import Dict, Any
from .types import GamePhase, GameEvent, GameContext, PhaseHandler

__all__ = [
    'GamePhase',
    'GameEvent', 
    'GameContext',
    'PhaseHandler',
    'GameStateMachine',
    'StateMachineFactory'
]


class GameStateMachine:
    """游戏状态机"""
    
    def __init__(self, phases: Dict[GamePhase, PhaseHandler]):
        """
        初始化状态机
        
        Args:
            phases: 阶段处理器映射
        """
        if not phases:
            raise ValueError("phases不能为空")
        
        required_phases = {GamePhase.INIT, GamePhase.PRE_FLOP, GamePhase.FLOP, 
                          GamePhase.TURN, GamePhase.RIVER, GamePhase.SHOWDOWN}
        missing_phases = required_phases - set(phases.keys())
        if missing_phases:
            raise ValueError(f"缺少必需的阶段处理器: {missing_phases}")
        
        self._phases = phases
        self._current_phase = GamePhase.INIT
        self._transition_history: list = []
    
    @property
    def current_phase(self) -> GamePhase:
        """获取当前阶段"""
        return self._current_phase
    
    @property
    def transition_history(self) -> list:
        """获取状态转换历史"""
        return self._transition_history.copy()
    
    def transition(self, event: GameEvent, ctx: GameContext) -> None:
        """
        执行状态转换
        
        Args:
            event: 触发转换的事件
            ctx: 游戏上下文
            
        Raises:
            ValueError: 当转换不合法时
        """
        current_handler = self._phases[self._current_phase]
        
        # 确定目标阶段
        target_phase = self._determine_target_phase(event, ctx)
        
        if target_phase == self._current_phase:
            # 同阶段内的事件处理
            if hasattr(current_handler, 'handle_event'):
                current_handler.handle_event(event, ctx)
            return
        
        # 检查转换合法性
        if not current_handler.can_transition_to(target_phase, ctx):
            raise ValueError(f"不能从{self._current_phase}转换到{target_phase}")
        
        # 执行转换
        current_handler.on_exit(ctx)
        
        old_phase = self._current_phase
        self._current_phase = target_phase
        ctx.current_phase = target_phase
        
        target_handler = self._phases[target_phase]
        target_handler.on_enter(ctx)
        
        # 记录转换历史
        self._transition_history.append({
            'from': old_phase,
            'to': target_phase,
            'event': event,
            'timestamp': getattr(ctx, 'timestamp', 0)
        })
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """
        处理玩家行动
        
        Args:
            ctx: 游戏上下文
            player_id: 玩家ID
            action: 玩家行动
            
        Returns:
            生成的游戏事件
        """
        current_handler = self._phases[self._current_phase]
        return current_handler.handle_player_action(ctx, player_id, action)
    
    def _determine_target_phase(self, event: GameEvent, ctx: GameContext) -> GamePhase:
        """
        根据事件和上下文确定目标阶段
        
        Args:
            event: 游戏事件
            ctx: 游戏上下文
            
        Returns:
            目标阶段
        """
        # 基本的阶段转换逻辑
        phase_transitions = {
            'BETTING_ROUND_COMPLETE': {
                GamePhase.PRE_FLOP: GamePhase.FLOP,
                GamePhase.FLOP: GamePhase.TURN,
                GamePhase.TURN: GamePhase.RIVER,
                GamePhase.RIVER: GamePhase.SHOWDOWN,
            },
            'HAND_START': {
                GamePhase.INIT: GamePhase.PRE_FLOP,
                GamePhase.FINISHED: GamePhase.PRE_FLOP,
            },
            'SHOWDOWN_COMPLETE': {
                GamePhase.SHOWDOWN: GamePhase.FINISHED,
            }
        }
        
        if event.event_type in phase_transitions:
            transitions = phase_transitions[event.event_type]
            return transitions.get(self._current_phase, self._current_phase)
        
        return self._current_phase
    
    def reset(self) -> None:
        """重置状态机到初始状态"""
        self._current_phase = GamePhase.INIT
        self._transition_history.clear()


# 导入工厂类
from .state_machine_factory import StateMachineFactory 