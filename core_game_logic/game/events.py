"""
游戏事件记录系统
包含动作事件和事件总线，支持观察者模式
"""

import time
from dataclasses import dataclass
from typing import List, Callable, Any, Optional
from ..core.enums import GamePhase, ActionType


@dataclass(frozen=True)
class ActionEvent:
    """
    游戏动作事件记录
    用于记录玩家的每一个动作，支持重放和AI分析
    """
    phase: GamePhase                    # 游戏阶段
    street_index: int                   # 该阶段内的第几次行动
    player_id: int                      # 行动玩家的座位号
    action: ActionType                  # 动作类型
    amount: int                         # 动作金额（下注/加注时使用）
    timestamp: float                    # 时间戳
    pot_before: int                     # 动作前的底池金额
    pot_after: int                      # 动作后的底池金额
    player_chips_before: int            # 动作前玩家筹码
    player_chips_after: int             # 动作后玩家筹码
    
    @classmethod
    def create(cls, 
               phase: GamePhase,
               street_index: int,
               player_id: int,
               action: ActionType,
               amount: int = 0,
               pot_before: int = 0,
               pot_after: int = 0,
               player_chips_before: int = 0,
               player_chips_after: int = 0) -> 'ActionEvent':
        """
        创建动作事件的便捷方法
        自动添加时间戳
        """
        return cls(
            phase=phase,
            street_index=street_index,
            player_id=player_id,
            action=action,
            amount=amount,
            timestamp=time.time(),
            pot_before=pot_before,
            pot_after=pot_after,
            player_chips_before=player_chips_before,
            player_chips_after=player_chips_after
        )

    def to_dict(self) -> dict:
        """转换为字典格式，便于序列化"""
        return {
            'phase': self.phase.name,
            'street_index': self.street_index,
            'player_id': self.player_id,
            'action': self.action.name,
            'amount': self.amount,
            'timestamp': self.timestamp,
            'pot_before': self.pot_before,
            'pot_after': self.pot_after,
            'player_chips_before': self.player_chips_before,
            'player_chips_after': self.player_chips_after
        }

    def __str__(self) -> str:
        """返回事件的可读描述"""
        if self.action in [ActionType.BET, ActionType.RAISE, ActionType.ALL_IN]:
            return f"玩家{self.player_id} {self.action.name.lower()} {self.amount}"
        else:
            return f"玩家{self.player_id} {self.action.name.lower()}"


# 事件处理器类型定义
EventHandler = Callable[[ActionEvent], None]


class EventBus:
    """
    游戏事件总线
    实现观察者模式，支持事件的发布和订阅
    """

    def __init__(self):
        """初始化事件总线"""
        self._handlers: List[EventHandler] = []
        self._event_history: List[ActionEvent] = []

    def subscribe(self, handler: EventHandler):
        """
        订阅事件
        
        Args:
            handler: 事件处理函数
        """
        if handler not in self._handlers:
            self._handlers.append(handler)

    def unsubscribe(self, handler: EventHandler):
        """
        取消订阅事件
        
        Args:
            handler: 要取消的事件处理函数
        """
        if handler in self._handlers:
            self._handlers.remove(handler)

    def publish(self, event: ActionEvent):
        """
        发布事件
        
        Args:
            event: 要发布的事件
        """
        # 记录到历史中
        self._event_history.append(event)
        
        # 通知所有订阅者
        for handler in self._handlers:
            try:
                handler(event)
            except Exception as e:
                # 事件处理器异常不应该影响游戏流程
                print(f"事件处理器异常: {e}")

    def get_history(self, 
                   player_id: Optional[int] = None,
                   phase: Optional[GamePhase] = None,
                   action_type: Optional[ActionType] = None) -> List[ActionEvent]:
        """
        获取事件历史
        
        Args:
            player_id: 筛选特定玩家的事件
            phase: 筛选特定阶段的事件
            action_type: 筛选特定动作类型的事件
            
        Returns:
            符合条件的事件列表
        """
        events = self._event_history
        
        if player_id is not None:
            events = [e for e in events if e.player_id == player_id]
        
        if phase is not None:
            events = [e for e in events if e.phase == phase]
        
        if action_type is not None:
            events = [e for e in events if e.action == action_type]
        
        return events

    def get_recent_events(self, count: int) -> List[ActionEvent]:
        """
        获取最近的事件
        
        Args:
            count: 要获取的事件数量
            
        Returns:
            最近的事件列表
        """
        return self._event_history[-count:] if count > 0 else []

    def clear_history(self):
        """清空事件历史"""
        self._event_history.clear()

    def get_event_count(self) -> int:
        """获取事件总数"""
        return len(self._event_history)

    def export_history(self) -> List[dict]:
        """
        导出事件历史为字典列表
        便于序列化和存储
        """
        return [event.to_dict() for event in self._event_history]

    def __len__(self) -> int:
        """返回事件历史的长度"""
        return len(self._event_history)

    def __repr__(self) -> str:
        """返回事件总线的调试表示"""
        return f"EventBus(handlers={len(self._handlers)}, events={len(self._event_history)})"


# 预定义的事件处理器

def console_event_handler(event: ActionEvent):
    """
    控制台事件处理器
    将事件输出到控制台
    """
    print(f"[{event.phase.name}] {event}")


def debug_event_handler(event: ActionEvent):
    """
    调试事件处理器
    输出详细的事件信息
    """
    print(f"DEBUG: {event.to_dict()}") 