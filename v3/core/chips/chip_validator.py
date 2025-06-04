"""
筹码验证器

提供筹码操作的合法性验证功能。
"""

from typing import Dict, List, Optional
from .chip_ledger import ChipLedger
from .chip_transaction import ChipTransaction, TransactionType

__all__ = ['ChipValidator', 'ValidationResult']


class ValidationResult:
    """验证结果"""
    
    def __init__(self, is_valid: bool, error_message: str = ""):
        self.is_valid = is_valid
        self.error_message = error_message
    
    def __bool__(self) -> bool:
        return self.is_valid
    
    def __str__(self) -> str:
        return f"ValidationResult(valid={self.is_valid}, error='{self.error_message}')"


class ChipValidator:
    """
    筹码验证器
    
    提供筹码操作的合法性验证功能。
    """
    
    @staticmethod
    def validate_deduct_operation(ledger: ChipLedger, player_id: str, amount: int) -> ValidationResult:
        """
        验证扣除筹码操作的合法性
        
        Args:
            ledger: 筹码账本
            player_id: 玩家ID
            amount: 扣除数量
            
        Returns:
            验证结果
        """
        if amount <= 0:
            return ValidationResult(False, "扣除数量必须为正数")
        
        if not player_id:
            return ValidationResult(False, "玩家ID不能为空")
        
        available_chips = ledger.get_available_chips(player_id)
        if available_chips < amount:
            return ValidationResult(
                False, 
                f"玩家{player_id}可用筹码不足: 需要{amount}, 可用{available_chips}"
            )
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_add_operation(player_id: str, amount: int) -> ValidationResult:
        """
        验证增加筹码操作的合法性
        
        Args:
            player_id: 玩家ID
            amount: 增加数量
            
        Returns:
            验证结果
        """
        if amount <= 0:
            return ValidationResult(False, "增加数量必须为正数")
        
        if not player_id:
            return ValidationResult(False, "玩家ID不能为空")
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_transfer_operation(ledger: ChipLedger, from_player: str, to_player: str, amount: int) -> ValidationResult:
        """
        验证转移筹码操作的合法性
        
        Args:
            ledger: 筹码账本
            from_player: 转出玩家ID
            to_player: 转入玩家ID
            amount: 转移数量
            
        Returns:
            验证结果
        """
        if amount <= 0:
            return ValidationResult(False, "转移数量必须为正数")
        
        if not from_player or not to_player:
            return ValidationResult(False, "玩家ID不能为空")
        
        if from_player == to_player:
            return ValidationResult(False, "不能向自己转移筹码")
        
        available_chips = ledger.get_available_chips(from_player)
        if available_chips < amount:
            return ValidationResult(
                False, 
                f"玩家{from_player}可用筹码不足: 需要{amount}, 可用{available_chips}"
            )
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_freeze_operation(ledger: ChipLedger, player_id: str, amount: int) -> ValidationResult:
        """
        验证冻结筹码操作的合法性
        
        Args:
            ledger: 筹码账本
            player_id: 玩家ID
            amount: 冻结数量
            
        Returns:
            验证结果
        """
        if amount <= 0:
            return ValidationResult(False, "冻结数量必须为正数")
        
        if not player_id:
            return ValidationResult(False, "玩家ID不能为空")
        
        available_chips = ledger.get_available_chips(player_id)
        if available_chips < amount:
            return ValidationResult(
                False, 
                f"玩家{player_id}可用筹码不足: 需要{amount}, 可用{available_chips}"
            )
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_unfreeze_operation(ledger: ChipLedger, player_id: str, amount: int) -> ValidationResult:
        """
        验证解冻筹码操作的合法性
        
        Args:
            ledger: 筹码账本
            player_id: 玩家ID
            amount: 解冻数量
            
        Returns:
            验证结果
        """
        if amount <= 0:
            return ValidationResult(False, "解冻数量必须为正数")
        
        if not player_id:
            return ValidationResult(False, "玩家ID不能为空")
        
        frozen_chips = ledger.get_frozen_chips(player_id)
        if frozen_chips < amount:
            return ValidationResult(
                False, 
                f"玩家{player_id}冻结筹码不足: 需要{amount}, 冻结{frozen_chips}"
            )
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_chip_conservation(initial_total: int, final_total: int) -> ValidationResult:
        """
        验证筹码守恒
        
        Args:
            initial_total: 初始总筹码
            final_total: 最终总筹码
            
        Returns:
            验证结果
        """
        if initial_total != final_total:
            return ValidationResult(
                False, 
                f"筹码守恒违规: 初始{initial_total}, 最终{final_total}, 差异{final_total - initial_total}"
            )
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_transaction_consistency(transactions: List[ChipTransaction]) -> ValidationResult:
        """
        验证交易记录的一致性
        
        Args:
            transactions: 交易记录列表
            
        Returns:
            验证结果
        """
        if not transactions:
            return ValidationResult(True)
        
        # 检查交易ID唯一性
        transaction_ids = [t.transaction_id for t in transactions]
        if len(transaction_ids) != len(set(transaction_ids)):
            return ValidationResult(False, "存在重复的交易ID")
        
        # 检查时间戳顺序
        for i in range(1, len(transactions)):
            if transactions[i].timestamp < transactions[i-1].timestamp:
                return ValidationResult(False, f"交易时间戳顺序错误: {transactions[i-1].transaction_id} -> {transactions[i].transaction_id}")
        
        # 检查交易数据完整性
        for transaction in transactions:
            if not transaction.transaction_id:
                return ValidationResult(False, "交易ID不能为空")
            if not transaction.player_id:
                return ValidationResult(False, "玩家ID不能为空")
            if transaction.amount < 0:
                return ValidationResult(False, f"交易金额不能为负数: {transaction.amount}")
        
        return ValidationResult(True) 