"""
基础阶段处理器模块
"""
from .types import GamePhase, GameContext

__all__ = ['BasePhaseHandler']

class BasePhaseHandler:
    """基础阶段处理器，提供通用功能"""
    
    def __init__(self, phase: GamePhase):
        self.phase = phase
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入阶段的默认处理"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[游戏阶段] 进入阶段: {self.phase.name}")
    
    def on_exit(self, ctx: GameContext) -> None:
        """退出阶段的默认处理"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[游戏阶段] 退出阶段: {self.phase.name}")
    
    def can_transition_to(self, target_phase: GamePhase, ctx: GameContext) -> bool:
        """检查是否可以转换到目标阶段"""
        # 基本的转换规则
        valid_transitions = {
            GamePhase.INIT: [GamePhase.PRE_FLOP],
            GamePhase.PRE_FLOP: [GamePhase.FLOP, GamePhase.SHOWDOWN, GamePhase.FINISHED],
            GamePhase.FLOP: [GamePhase.TURN, GamePhase.SHOWDOWN, GamePhase.FINISHED],
            GamePhase.TURN: [GamePhase.RIVER, GamePhase.SHOWDOWN, GamePhase.FINISHED],
            GamePhase.RIVER: [GamePhase.SHOWDOWN, GamePhase.FINISHED],
            GamePhase.SHOWDOWN: [GamePhase.FINISHED],
            GamePhase.FINISHED: [GamePhase.PRE_FLOP, GamePhase.INIT]
        }
        
        return target_phase in valid_transitions.get(self.phase, []) 