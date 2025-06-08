"""
筹码交易记录

定义筹码交易的类型和记录结构。
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Dict, Any
import time

__all__ = ['TransactionType', 'ChipTransaction']


class TransactionType(Enum):
    """筹码交易类型"""
    DEDUCT = auto()      # 扣除筹码
    ADD = auto()         # 增加筹码
    TRANSFER = auto()    # 转移筹码
    FREEZE = auto()      # 冻结筹码
    UNFREEZE = auto()    # 解冻筹码
    SETTLE = auto()      # 结算手牌


@dataclass(frozen=True)
class ChipTransaction:
    """筹码交易记录"""
    transaction_id: str
    transaction_type: TransactionType
    player_id: str
    amount: int
    timestamp: float
    description: str
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """验证交易记录的有效性"""
        if not self.transaction_id:
            raise ValueError("transaction_id不能为空")
        if not self.player_id:
            raise ValueError("player_id不能为空")
        if self.amount < 0:
            raise ValueError("amount不能为负数")
        if self.timestamp <= 0:
            raise ValueError("timestamp必须为正数")
    
    @classmethod
    def create_deduct_transaction(cls, player_id: str, amount: int, description: str) -> 'ChipTransaction':
        """创建扣除筹码交易"""
        return cls(
            transaction_id=f"deduct_{player_id}_{int(time.time() * 1000000)}",
            transaction_type=TransactionType.DEDUCT,
            player_id=player_id,
            amount=amount,
            timestamp=time.time(),
            description=description
        )
    
    @classmethod
    def create_add_transaction(cls, player_id: str, amount: int, description: str) -> 'ChipTransaction':
        """创建增加筹码交易"""
        return cls(
            transaction_id=f"add_{player_id}_{int(time.time() * 1000000)}",
            transaction_type=TransactionType.ADD,
            player_id=player_id,
            amount=amount,
            timestamp=time.time(),
            description=description
        )
    
    @classmethod
    def create_transfer_transaction(cls, from_player: str, to_player: str, amount: int, description: str) -> tuple:
        """创建转移筹码交易（返回两个交易记录）"""
        timestamp = time.time()
        transaction_base_id = int(timestamp * 1000000)
        
        deduct_transaction = cls(
            transaction_id=f"transfer_out_{transaction_base_id}",
            transaction_type=TransactionType.DEDUCT,
            player_id=from_player,
            amount=amount,
            timestamp=timestamp,
            description=f"转移给{to_player}: {description}",
            metadata={"transfer_to": to_player, "transfer_id": transaction_base_id}
        )
        
        add_transaction = cls(
            transaction_id=f"transfer_in_{transaction_base_id}",
            transaction_type=TransactionType.ADD,
            player_id=to_player,
            amount=amount,
            timestamp=timestamp,
            description=f"从{from_player}接收: {description}",
            metadata={"transfer_from": from_player, "transfer_id": transaction_base_id}
        )
        
        return deduct_transaction, add_transaction 