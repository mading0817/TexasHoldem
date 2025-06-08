"""
初始化阶段处理器
"""
from typing import Dict, Any
from .types import GamePhase, GameEvent, GameContext
from .base_phase_handler import BasePhaseHandler

__all__ = ['InitHandler']

class InitHandler(BasePhaseHandler):
    """初始化阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.INIT)
    
    def on_enter(self, ctx: GameContext) -> None:
        """初始化游戏状态"""
        super().on_enter(ctx)
        # 重置游戏状态
        ctx.community_cards.clear()
        ctx.pot_total = 0
        ctx.current_bet = 0
        ctx.active_player_id = None
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """初始化阶段不处理玩家行动"""
        return GameEvent(
            event_type="INVALID_ACTION",
            data={"reason": "初始化阶段不能执行玩家行动"},
            source_phase=self.phase
        ) 