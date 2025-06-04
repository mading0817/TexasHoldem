"""
下注验证器

提供下注操作的合法性验证功能。
"""

from typing import Dict, List, Optional
from ..chips.chip_ledger import ChipLedger
from .betting_types import BetType, BetAction

__all__ = ['BettingValidator', 'BetValidationResult']


class BetValidationResult:
    """下注验证结果"""
    
    def __init__(self, is_valid: bool, error_message: str = ""):
        self.is_valid = is_valid
        self.error_message = error_message
    
    def __bool__(self) -> bool:
        return self.is_valid
    
    def __str__(self) -> str:
        return f"BetValidationResult(valid={self.is_valid}, error='{self.error_message}')"


class BettingValidator:
    """
    下注验证器
    
    提供下注操作的合法性验证功能。
    """
    
    @staticmethod
    def validate_fold_action(player_id: str) -> BetValidationResult:
        """
        验证弃牌操作的合法性
        
        Args:
            player_id: 玩家ID
            
        Returns:
            验证结果
        """
        if not player_id:
            return BetValidationResult(False, "玩家ID不能为空")
        
        return BetValidationResult(True)
    
    @staticmethod
    def validate_check_action(player_id: str, current_bet: int) -> BetValidationResult:
        """
        验证过牌操作的合法性
        
        Args:
            player_id: 玩家ID
            current_bet: 当前轮次的下注额
            
        Returns:
            验证结果
        """
        if not player_id:
            return BetValidationResult(False, "玩家ID不能为空")
        
        if current_bet > 0:
            return BetValidationResult(False, "当前有下注时不能过牌，只能跟注、加注或弃牌")
        
        return BetValidationResult(True)
    
    @staticmethod
    def validate_call_action(ledger: ChipLedger, player_id: str, call_amount: int, player_current_bet: int) -> BetValidationResult:
        """
        验证跟注操作的合法性
        
        Args:
            ledger: 筹码账本
            player_id: 玩家ID
            call_amount: 需要跟注的金额
            player_current_bet: 玩家当前轮次已下注金额
            
        Returns:
            验证结果
        """
        if not player_id:
            return BetValidationResult(False, "玩家ID不能为空")
        
        if call_amount <= 0:
            return BetValidationResult(False, "跟注金额必须大于0")
        
        # 计算实际需要投入的筹码
        actual_call_amount = call_amount - player_current_bet
        if actual_call_amount <= 0:
            return BetValidationResult(False, "玩家已经跟注或超过当前下注额")
        
        available_chips = ledger.get_available_chips(player_id)
        if available_chips < actual_call_amount:
            return BetValidationResult(
                False, 
                f"玩家{player_id}筹码不足: 需要{actual_call_amount}, 可用{available_chips}"
            )
        
        return BetValidationResult(True)
    
    @staticmethod
    def validate_raise_action(ledger: ChipLedger, player_id: str, raise_amount: int, current_bet: int, 
                            min_raise: int, player_current_bet: int) -> BetValidationResult:
        """
        验证加注操作的合法性
        
        Args:
            ledger: 筹码账本
            player_id: 玩家ID
            raise_amount: 加注总额
            current_bet: 当前轮次最高下注额
            min_raise: 最小加注额
            player_current_bet: 玩家当前轮次已下注金额
            
        Returns:
            验证结果
        """
        if not player_id:
            return BetValidationResult(False, "玩家ID不能为空")
        
        if raise_amount <= current_bet:
            return BetValidationResult(False, f"加注金额{raise_amount}必须大于当前下注额{current_bet}")
        
        raise_increment = raise_amount - current_bet
        if raise_increment < min_raise:
            return BetValidationResult(False, f"加注幅度{raise_increment}不能小于最小加注额{min_raise}")
        
        # 计算实际需要投入的筹码
        actual_raise_amount = raise_amount - player_current_bet
        if actual_raise_amount <= 0:
            return BetValidationResult(False, "加注金额计算错误")
        
        available_chips = ledger.get_available_chips(player_id)
        if available_chips < actual_raise_amount:
            return BetValidationResult(
                False, 
                f"玩家{player_id}筹码不足: 需要{actual_raise_amount}, 可用{available_chips}"
            )
        
        return BetValidationResult(True)
    
    @staticmethod
    def validate_all_in_action(ledger: ChipLedger, player_id: str) -> BetValidationResult:
        """
        验证全押操作的合法性
        
        Args:
            ledger: 筹码账本
            player_id: 玩家ID
            
        Returns:
            验证结果
        """
        if not player_id:
            return BetValidationResult(False, "玩家ID不能为空")
        
        available_chips = ledger.get_available_chips(player_id)
        if available_chips <= 0:
            return BetValidationResult(False, f"玩家{player_id}没有可用筹码进行全押")
        
        return BetValidationResult(True)
    
    @staticmethod
    def validate_bet_action(ledger: ChipLedger, action: BetAction, current_bet: int, 
                          min_raise: int, player_current_bet: int) -> BetValidationResult:
        """
        验证下注行动的合法性
        
        Args:
            ledger: 筹码账本
            action: 下注行动
            current_bet: 当前轮次最高下注额
            min_raise: 最小加注额
            player_current_bet: 玩家当前轮次已下注金额
            
        Returns:
            验证结果
        """
        if action.bet_type == BetType.FOLD:
            return BettingValidator.validate_fold_action(action.player_id)
        
        elif action.bet_type == BetType.CHECK:
            return BettingValidator.validate_check_action(action.player_id, current_bet)
        
        elif action.bet_type == BetType.CALL:
            return BettingValidator.validate_call_action(
                ledger, action.player_id, current_bet, player_current_bet
            )
        
        elif action.bet_type == BetType.RAISE:
            return BettingValidator.validate_raise_action(
                ledger, action.player_id, action.amount, current_bet, min_raise, player_current_bet
            )
        
        elif action.bet_type == BetType.ALL_IN:
            return BettingValidator.validate_all_in_action(ledger, action.player_id)
        
        else:
            return BetValidationResult(False, f"未知的下注类型: {action.bet_type}")
    
    @staticmethod
    def validate_betting_round_completion(player_actions: Dict[str, BetAction], active_players: List[str]) -> BetValidationResult:
        """
        验证下注轮次是否完成
        
        Args:
            player_actions: 玩家行动记录
            active_players: 活跃玩家列表
            
        Returns:
            验证结果
        """
        if not active_players:
            return BetValidationResult(False, "没有活跃玩家")
        
        # 检查是否所有活跃玩家都已行动
        for player_id in active_players:
            if player_id not in player_actions:
                return BetValidationResult(False, f"玩家{player_id}尚未行动")
        
        # 检查下注是否平衡（除了全押玩家）
        bet_amounts = {}
        all_in_players = set()
        
        for player_id, action in player_actions.items():
            if action.bet_type == BetType.FOLD:
                continue
            elif action.bet_type == BetType.ALL_IN:
                all_in_players.add(player_id)
                bet_amounts[player_id] = action.amount
            else:
                bet_amounts[player_id] = action.amount
        
        if len(bet_amounts) <= 1:
            return BetValidationResult(True)  # 只有一个或没有玩家下注
        
        # 检查非全押玩家的下注是否相等
        non_all_in_bets = [amount for player_id, amount in bet_amounts.items() if player_id not in all_in_players]
        if len(set(non_all_in_bets)) > 1:
            return BetValidationResult(False, "下注轮次未完成，玩家下注金额不一致")
        
        return BetValidationResult(True) 