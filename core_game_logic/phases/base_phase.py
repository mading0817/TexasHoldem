"""
游戏阶段抽象基类
定义每个游戏阶段的标准生命周期接口
"""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..game_state import GameState
    from ..action_validator import ValidatedAction


class BasePhase(ABC):
    """
    游戏阶段抽象基类
    每个具体阶段(PreFlop, Flop, Turn, River, Showdown)都继承此类
    """
    
    def __init__(self, state: 'GameState'):
        """
        初始化阶段
        
        Args:
            state: 游戏状态对象
        """
        self.state = state
    
    @abstractmethod
    def enter(self):
        """
        进入阶段时的一次性操作
        例如：发牌、设置盲注、重置下注轮等
        """
        pass
    
    @abstractmethod
    def act(self, action: 'ValidatedAction') -> bool:
        """
        处理玩家行动
        
        Args:
            action: 经过验证的玩家行动
            
        Returns:
            True如果下注轮继续，False如果下注轮结束
        """
        pass
    
    @abstractmethod
    def exit(self) -> Optional['BasePhase']:
        """
        退出当前阶段时的清理操作
        
        Returns:
            下一个阶段的实例，如果游戏结束则返回None
        """
        pass
    
    def is_round_complete(self) -> bool:
        """
        检查当前下注轮是否完成
        复用GameState现有逻辑
        
        Returns:
            True如果下注轮完成
        """
        return self.state.is_betting_round_complete()
    
    def advance_player(self) -> bool:
        """
        推进到下一个玩家
        复用GameState现有逻辑
        
        Returns:
            True如果成功推进
        """
        return self.state.advance_current_player() 