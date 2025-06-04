"""
下注类型定义

定义下注相关的枚举类型和数据结构。
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Dict, Any

__all__ = ['BetType', 'BetAction']


class BetType(Enum):
    """下注类型"""
    FOLD = auto()       # 弃牌
    CHECK = auto()      # 过牌
    CALL = auto()       # 跟注
    RAISE = auto()      # 加注
    ALL_IN = auto()     # 全押


@dataclass(frozen=True)
class BetAction:
    """下注行动"""
    player_id: str
    bet_type: BetType
    amount: int
    timestamp: float
    description: str = ""
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """验证下注行动的有效性"""
        if not self.player_id:
            raise ValueError("player_id不能为空")
        if self.amount < 0:
            raise ValueError("下注金额不能为负数")
        if self.timestamp <= 0:
            raise ValueError("timestamp必须为正数")
        
        # 验证下注类型和金额的一致性
        if self.bet_type in [BetType.FOLD, BetType.CHECK] and self.amount != 0:
            raise ValueError(f"{self.bet_type.name}操作的金额必须为0")
        # CALL操作允许金额为0，由引擎自动计算实际跟注金额
        if self.bet_type in [BetType.RAISE, BetType.ALL_IN] and self.amount <= 0:
            raise ValueError(f"{self.bet_type.name}操作的金额必须大于0")
    
    def is_aggressive_action(self) -> bool:
        """判断是否为主动下注行动"""
        return self.bet_type in [BetType.RAISE, BetType.ALL_IN]
    
    def is_passive_action(self) -> bool:
        """判断是否为被动行动"""
        return self.bet_type in [BetType.FOLD, BetType.CHECK, BetType.CALL]
    
    def involves_chips(self) -> bool:
        """判断是否涉及筹码操作"""
        return self.bet_type in [BetType.CALL, BetType.RAISE, BetType.ALL_IN] 