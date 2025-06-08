"""
状态机工厂

提供创建配置好的状态机实例的工厂方法。
"""

from typing import Dict
from .types import GamePhase
from .init_handler import InitHandler
from .pre_flop_handler import PreFlopHandler
from .flop_handler import FlopHandler
from .turn_handler import TurnHandler
from .river_handler import RiverHandler
from .showdown_handler import ShowdownHandler
from .finished_handler import FinishedHandler

__all__ = ['StateMachineFactory']


class StateMachineFactory:
    """状态机工厂类"""
    
    @staticmethod
    def create_default_state_machine():
        """
        创建默认配置的状态机
        
        Returns:
            配置好的GameStateMachine实例
        """
        # 延迟导入避免循环依赖
        from . import GameStateMachine
        
        phases = {
            GamePhase.INIT: InitHandler(),
            GamePhase.PRE_FLOP: PreFlopHandler(),
            GamePhase.FLOP: FlopHandler(),
            GamePhase.TURN: TurnHandler(),
            GamePhase.RIVER: RiverHandler(),
            GamePhase.SHOWDOWN: ShowdownHandler(),
            GamePhase.FINISHED: FinishedHandler()
        }
        
        return GameStateMachine(phases)
    
    @staticmethod
    def create_custom_state_machine(custom_handlers):
        """
        创建自定义配置的状态机
        
        Args:
            custom_handlers: 自定义的阶段处理器映射
            
        Returns:
            配置好的GameStateMachine实例
        """
        # 延迟导入避免循环依赖
        from . import GameStateMachine
        
        # 使用默认处理器作为基础
        default_phases = {
            GamePhase.INIT: InitHandler(),
            GamePhase.PRE_FLOP: PreFlopHandler(),
            GamePhase.FLOP: FlopHandler(),
            GamePhase.TURN: TurnHandler(),
            GamePhase.RIVER: RiverHandler(),
            GamePhase.SHOWDOWN: ShowdownHandler(),
            GamePhase.FINISHED: FinishedHandler()
        }
        
        # 用自定义处理器覆盖默认处理器
        default_phases.update(custom_handlers)
        
        return GameStateMachine(default_phases) 