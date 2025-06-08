"""
筹码账本

提供筹码管理的核心功能，确保所有筹码操作的原子性和一致性。
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from .chip_transaction import ChipTransaction, TransactionType
import threading
import time

__all__ = ['ChipLedger', 'ChipLedgerSnapshot']


@dataclass(frozen=True)
class ChipLedgerSnapshot:
    """筹码账本快照"""
    player_balances: Dict[str, int]
    frozen_chips: Dict[str, int]
    total_chips: int
    transaction_count: int
    timestamp: float
    
    def get_available_chips(self, player_id: str) -> int:
        """获取玩家可用筹码（总筹码 - 冻结筹码）"""
        total = self.player_balances.get(player_id, 0)
        frozen = self.frozen_chips.get(player_id, 0)
        return max(0, total - frozen)


class ChipLedger:
    """
    筹码账本
    
    确保所有筹码操作的原子性和一致性，支持筹码守恒检查。
    """
    
    def __init__(self, initial_balances: Optional[Dict[str, int]] = None):
        """
        初始化筹码账本
        
        Args:
            initial_balances: 初始筹码分配
        """
        self._player_balances: Dict[str, int] = initial_balances.copy() if initial_balances else {}
        self._frozen_chips: Dict[str, int] = {}  # 冻结的筹码
        self._transaction_history: List[ChipTransaction] = []
        self._lock = threading.RLock()  # 线程安全锁
        
        # 验证初始余额
        for player_id, balance in self._player_balances.items():
            if balance < 0:
                raise ValueError(f"玩家{player_id}的初始余额不能为负数: {balance}")
    
    def get_balance(self, player_id: str) -> int:
        """获取玩家总筹码余额"""
        with self._lock:
            return self._player_balances.get(player_id, 0)
    
    def get_available_chips(self, player_id: str) -> int:
        """获取玩家可用筹码（总筹码 - 冻结筹码）"""
        with self._lock:
            total = self._player_balances.get(player_id, 0)
            frozen = self._frozen_chips.get(player_id, 0)
            return max(0, total - frozen)
    
    def get_frozen_chips(self, player_id: str) -> int:
        """获取玩家冻结的筹码数量"""
        with self._lock:
            return self._frozen_chips.get(player_id, 0)
    
    def get_total_chips(self) -> int:
        """获取系统总筹码，用于守恒检查"""
        with self._lock:
            return sum(self._player_balances.values())
    
    def get_all_players(self) -> Set[str]:
        """获取所有玩家ID"""
        with self._lock:
            return set(self._player_balances.keys())
    
    def deduct_chips(self, player_id: str, amount: int, description: str = "") -> bool:
        """
        扣除玩家筹码
        
        Args:
            player_id: 玩家ID
            amount: 扣除数量
            description: 交易描述
            
        Returns:
            是否成功扣除
        """
        if amount <= 0:
            raise ValueError("扣除数量必须为正数")
        
        with self._lock:
            available = self.get_available_chips(player_id)
            if available < amount:
                return False
            
            # 执行扣除
            self._player_balances[player_id] = self._player_balances.get(player_id, 0) - amount
            
            # 记录交易
            transaction = ChipTransaction.create_deduct_transaction(player_id, amount, description)
            self._transaction_history.append(transaction)
            
            return True
    
    def add_chips(self, player_id: str, amount: int, description: str = "") -> None:
        """
        增加玩家筹码
        
        Args:
            player_id: 玩家ID
            amount: 增加数量
            description: 交易描述
        """
        if amount <= 0:
            raise ValueError("增加数量必须为正数")
        
        with self._lock:
            self._player_balances[player_id] = self._player_balances.get(player_id, 0) + amount
            
            # 记录交易
            transaction = ChipTransaction.create_add_transaction(player_id, amount, description)
            self._transaction_history.append(transaction)
    
    def transfer_chips(self, from_player: str, to_player: str, amount: int, description: str = "") -> bool:
        """
        在玩家之间转移筹码
        
        Args:
            from_player: 转出玩家ID
            to_player: 转入玩家ID
            amount: 转移数量
            description: 交易描述
            
        Returns:
            是否成功转移
        """
        if amount <= 0:
            raise ValueError("转移数量必须为正数")
        if from_player == to_player:
            raise ValueError("不能向自己转移筹码")
        
        with self._lock:
            # 检查转出玩家是否有足够筹码
            if not self.deduct_chips(from_player, amount, f"转移给{to_player}: {description}"):
                return False
            
            # 增加转入玩家筹码
            self.add_chips(to_player, amount, f"从{from_player}接收: {description}")
            
            return True
    
    def freeze_chips(self, player_id: str, amount: int, description: str = "") -> bool:
        """
        冻结玩家筹码（用于下注等操作）
        
        Args:
            player_id: 玩家ID
            amount: 冻结数量
            description: 交易描述
            
        Returns:
            是否成功冻结
        """
        if amount <= 0:
            raise ValueError("冻结数量必须为正数")
        
        with self._lock:
            available = self.get_available_chips(player_id)
            if available < amount:
                return False
            
            self._frozen_chips[player_id] = self._frozen_chips.get(player_id, 0) + amount
            
            # 记录交易
            transaction = ChipTransaction(
                transaction_id=f"freeze_{player_id}_{len(self._transaction_history)}",
                transaction_type=TransactionType.FREEZE,
                player_id=player_id,
                amount=amount,
                timestamp=time.time(),
                description=description
            )
            self._transaction_history.append(transaction)
            
            return True
    
    def unfreeze_chips(self, player_id: str, amount: int, description: str = "") -> bool:
        """
        解冻玩家筹码
        
        Args:
            player_id: 玩家ID
            amount: 解冻数量
            description: 交易描述
            
        Returns:
            是否成功解冻
        """
        if amount <= 0:
            raise ValueError("解冻数量必须为正数")
        
        with self._lock:
            frozen = self._frozen_chips.get(player_id, 0)
            if frozen < amount:
                return False
            
            self._frozen_chips[player_id] = frozen - amount
            if self._frozen_chips[player_id] == 0:
                del self._frozen_chips[player_id]
            
            # 记录交易
            transaction = ChipTransaction(
                transaction_id=f"unfreeze_{player_id}_{len(self._transaction_history)}",
                transaction_type=TransactionType.UNFREEZE,
                player_id=player_id,
                amount=amount,
                timestamp=time.time(),
                description=description
            )
            self._transaction_history.append(transaction)
            
            return True
    
    def create_snapshot(self) -> ChipLedgerSnapshot:
        """创建当前状态的快照"""
        with self._lock:
            return ChipLedgerSnapshot(
                player_balances=self._player_balances.copy(),
                frozen_chips=self._frozen_chips.copy(),
                total_chips=self.get_total_chips(),
                transaction_count=len(self._transaction_history),
                timestamp=time.time()
            )
    
    def settle_hand(self, transactions: Dict[str, int]) -> None:
        """
        结算一手牌，原子性地处理所有玩家的筹码输赢。
        这会清空所有冻结的筹码，然后根据传入的交易字典调整玩家余额。

        Args:
            transactions: 一个字典，{player_id: net_chip_change}。
                          赢家用正数表示，输家用负数表示。
        """
        with self._lock:
            # 1. 记录结算前的总筹码，用于验证
            total_before_settle = self.get_total_chips()

            # 2. 清空所有冻结的筹码
            self._frozen_chips.clear()
            
            # 3. 应用净变化
            for player_id, net_change in transactions.items():
                self._player_balances[player_id] = self._player_balances.get(player_id, 0) + net_change
                
                # 记录详细的Settle交易
                transaction = ChipTransaction(
                    transaction_id=f"settle_{player_id}_{len(self._transaction_history)}",
                    transaction_type=TransactionType.SETTLE,
                    player_id=player_id,
                    amount=abs(net_change),
                    timestamp=time.time(),
                    description=f"手牌结算: 净变化 {net_change}",
                    metadata={'net_change': net_change}
                )
                self._transaction_history.append(transaction)

            # 4. 验证筹码守恒
            total_after_settle = self.get_total_chips()
            if total_before_settle != total_after_settle:
                # 这是一个严重的内部错误，应立即抛出异常
                raise RuntimeError(
                    f"手牌结算后筹码不守恒! "
                    f"结算前: {total_before_settle}, 结算后: {total_after_settle}"
                )

    def get_transaction_history(self, player_id: Optional[str] = None) -> List[ChipTransaction]:
        """
        获取交易历史
        
        Args:
            player_id: 可选，只获取特定玩家的交易历史
            
        Returns:
            交易历史列表
        """
        with self._lock:
            if player_id is None:
                return self._transaction_history.copy()
            else:
                return [t for t in self._transaction_history if t.player_id == player_id]
    
    def validate_chip_conservation(self, expected_total: Optional[int] = None) -> bool:
        """
        验证筹码守恒
        
        Args:
            expected_total: 期望的总筹码数量
            
        Returns:
            是否满足筹码守恒
        """
        with self._lock:
            current_total = self.get_total_chips()
            
            if expected_total is not None:
                return current_total == expected_total
            
            # 如果没有指定期望总数，检查是否有负余额
            for player_id, balance in self._player_balances.items():
                if balance < 0:
                    return False
            
            return True 