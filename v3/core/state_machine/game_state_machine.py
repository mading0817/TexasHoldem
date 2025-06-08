"""
游戏状态机
"""
from typing import Dict, Any
from .types import GamePhase, GameEvent, GameContext, PhaseHandler

__all__ = ['GameStateMachine']


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
                           GamePhase.TURN, GamePhase.RIVER, GamePhase.SHOWDOWN, GamePhase.FINISHED}
        missing_phases = required_phases - set(phases.keys())
        if missing_phases:
            raise ValueError(f"缺少必需的阶段处理器: {missing_phases}")

        self._phases = phases
        # The initial phase should be INIT, not PRE_FLOP.
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

    def get_handler(self, phase: GamePhase = None) -> PhaseHandler:
        """获取指定阶段的处理器，如果未指定，则返回当前阶段的处理器"""
        if phase is None:
            phase = self._current_phase
        return self._phases[phase]

    def transition_to(self, target_phase: GamePhase, ctx: GameContext, event: GameEvent) -> None:
        """
        执行到目标阶段的转换

        Args:
            target_phase: 目标阶段
            ctx: 游戏上下文
            event: 触发转换的事件

        Raises:
            ValueError: 当转换不合法时
        """
        current_handler = self.get_handler()

        # 检查转换合法性
        if not current_handler.can_transition_to(target_phase, ctx):
            raise ValueError(f"不能从 {self._current_phase} 转换到 {target_phase}")

        # 执行转换
        if hasattr(current_handler, 'on_exit'):
            current_handler.on_exit(ctx)

        old_phase = self._current_phase
        self._current_phase = target_phase
        ctx.current_phase = target_phase

        target_handler = self.get_handler()
        if hasattr(target_handler, 'on_enter'):
            target_handler.on_enter(ctx)

        # 记录转换历史
        self._transition_history.append({
            'from': old_phase,
            'to': target_phase,
            'event': event,
            'timestamp': getattr(ctx, 'timestamp', 'N/A')
        })

    def handle_event(self, event: GameEvent, ctx: GameContext):
        """
        处理一个事件，可能会触发状态转换。
        """
        # 这个方法需要一个更复杂的逻辑来决定基于事件的目标状态
        # For now, we assume simple event-to-phase mapping
        target_phase = self._determine_target_phase(event, ctx)

        if target_phase != self.current_phase:
            self.transition_to(target_phase, ctx, event)
        else:
            # Handle event within the same phase if needed
            pass


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
        current_handler = self.get_handler()
        if hasattr(current_handler, 'handle_player_action'):
            return current_handler.handle_player_action(ctx, player_id, action)
        
        # Fallback for handlers that don't implement player action
        return GameEvent("INVALID_ACTION", {"reason": f"{self.current_phase} 阶段不接受玩家行动"}, self.current_phase)


    def _determine_target_phase(self, event: GameEvent, ctx: GameContext) -> GamePhase:
        """
        根据事件和上下文确定目标阶段
        
        Args:
            event: 游戏事件
            ctx: 游戏上下文
            
        Returns:
            目标阶段
        """
        # This logic is critical and likely needs to be more sophisticated.
        # It might depend on game rules, context, etc.
        # This is a simplified placeholder.
        
        event_to_phase_map = {
            "START_NEW_HAND": GamePhase.PRE_FLOP,
            "PRE_FLOP_COMPLETE": GamePhase.FLOP,
            "FLOP_COMPLETE": GamePhase.TURN,
            "TURN_COMPLETE": GamePhase.RIVER,
            "RIVER_COMPLETE": GamePhase.SHOWDOWN,
            "SHOWDOWN_COMPLETE": GamePhase.FINISHED,
            "HAND_AUTO_FINISH": GamePhase.FINISHED,
            "GAME_OVER": GamePhase.INIT, # Or some other terminal state
        }
        
        return event_to_phase_map.get(event.event_type, self.current_phase)

    def reset(self) -> None:
        """重置状态机到初始状态"""
        self._current_phase = GamePhase.INIT
        self._transition_history.clear() 