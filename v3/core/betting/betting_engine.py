"""
下注引擎

处理所有下注逻辑的核心引擎。
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from ..chips.chip_ledger import ChipLedger
from .betting_types import BetType, BetAction
from .betting_validator import BettingValidator, BetValidationResult
import time

__all__ = ['BettingEngine', 'BetResult', 'BettingRound']


@dataclass(frozen=True)
class BetResult:
    """下注结果"""
    success: bool
    action: Optional[BetAction]
    error_message: str = ""
    chips_moved: int = 0
    
    def __bool__(self) -> bool:
        return self.success


@dataclass
class BettingRound:
    """下注轮次状态"""
    current_bet: int = 0
    min_raise: int = 0
    player_bets: Dict[str, int] = None
    player_actions: Dict[str, BetAction] = None
    active_players: List[str] = None
    
    def __post_init__(self):
        if self.player_bets is None:
            self.player_bets = {}
        if self.player_actions is None:
            self.player_actions = {}
        if self.active_players is None:
            self.active_players = []


class BettingEngine:
    """
    下注引擎
    
    处理所有下注逻辑，包括验证、执行和状态管理。
    """
    
    def __init__(self, chip_ledger: ChipLedger, big_blind: int = 20):
        """
        初始化下注引擎
        
        Args:
            chip_ledger: 筹码账本
            big_blind: 大盲注金额
        """
        self._chip_ledger = chip_ledger
        self._big_blind = big_blind
        self._current_round = BettingRound(min_raise=big_blind)
        self._betting_history: List[BetAction] = []
    
    def start_new_round(self, active_players: List[str], small_blind_player: str, big_blind_player: str) -> bool:
        """
        开始新的下注轮次
        
        Args:
            active_players: 活跃玩家列表
            small_blind_player: 小盲注玩家
            big_blind_player: 大盲注玩家
            
        Returns:
            是否成功开始
        """
        if len(active_players) < 2:
            return False
        
        # 重置轮次状态 - 初始状态为0，盲注后再更新
        self._current_round = BettingRound(
            current_bet=0,
            min_raise=self._big_blind,
            active_players=active_players.copy()
        )
        
        # 处理盲注 - 盲注是强制性的，不需要验证
        small_blind_amount = self._big_blind // 2
        
        # 小盲注 - 直接执行，不通过验证
        if not self._chip_ledger.deduct_chips(small_blind_player, small_blind_amount, "小盲注"):
            return False
        
        self._current_round.player_bets[small_blind_player] = small_blind_amount
        self._current_round.current_bet = small_blind_amount
        
        small_blind_action = BetAction(
            player_id=small_blind_player,
            bet_type=BetType.RAISE,
            amount=small_blind_amount,
            timestamp=time.time(),
            description="小盲注"
        )
        self._current_round.player_actions[small_blind_player] = small_blind_action
        self._betting_history.append(small_blind_action)
        
        # 大盲注 - 直接执行，不通过验证
        if not self._chip_ledger.deduct_chips(big_blind_player, self._big_blind, "大盲注"):
            return False
        
        self._current_round.player_bets[big_blind_player] = self._big_blind
        self._current_round.current_bet = self._big_blind
        
        big_blind_action = BetAction(
            player_id=big_blind_player,
            bet_type=BetType.RAISE,
            amount=self._big_blind,
            timestamp=time.time(),
            description="大盲注"
        )
        self._current_round.player_actions[big_blind_player] = big_blind_action
        self._betting_history.append(big_blind_action)
        
        return True
    
    def execute_player_action(self, player_id: str, bet_type: BetType, amount: int = 0) -> BetResult:
        """
        执行玩家下注行动
        
        Args:
            player_id: 玩家ID
            bet_type: 下注类型
            amount: 下注金额
            
        Returns:
            下注结果
        """
        if player_id not in self._current_round.active_players:
            return BetResult(False, None, f"玩家{player_id}不在活跃玩家列表中")
        
        if player_id in self._current_round.player_actions:
            return BetResult(False, None, f"玩家{player_id}已经行动过了")
        
        # 创建下注行动
        action = BetAction(
            player_id=player_id,
            bet_type=bet_type,
            amount=amount,
            timestamp=time.time()
        )
        
        return self._execute_bet_action(action)
    
    def _execute_bet_action(self, action: BetAction) -> BetResult:
        """
        执行下注行动的内部方法
        
        Args:
            action: 下注行动
            
        Returns:
            下注结果
        """
        # 获取玩家当前下注
        player_current_bet = self._current_round.player_bets.get(action.player_id, 0)
        
        # 验证行动合法性
        validation_result = BettingValidator.validate_bet_action(
            self._chip_ledger, action, self._current_round.current_bet, 
            self._current_round.min_raise, player_current_bet
        )
        
        if not validation_result:
            return BetResult(False, action, validation_result.error_message)
        
        # 执行具体的下注逻辑
        if action.bet_type == BetType.FOLD:
            return self._execute_fold(action)
        elif action.bet_type == BetType.CHECK:
            return self._execute_check(action)
        elif action.bet_type == BetType.CALL:
            return self._execute_call(action)
        elif action.bet_type == BetType.RAISE:
            return self._execute_raise(action)
        elif action.bet_type == BetType.ALL_IN:
            return self._execute_all_in(action)
        else:
            return BetResult(False, action, f"未知的下注类型: {action.bet_type}")
    
    def _execute_fold(self, action: BetAction) -> BetResult:
        """执行弃牌"""
        # 从活跃玩家中移除
        if action.player_id in self._current_round.active_players:
            self._current_round.active_players.remove(action.player_id)
        
        # 记录行动
        self._current_round.player_actions[action.player_id] = action
        self._betting_history.append(action)
        
        return BetResult(True, action, chips_moved=0)
    
    def _execute_check(self, action: BetAction) -> BetResult:
        """执行过牌"""
        # 记录行动
        self._current_round.player_actions[action.player_id] = action
        self._betting_history.append(action)
        
        return BetResult(True, action, chips_moved=0)
    
    def _execute_call(self, action: BetAction) -> BetResult:
        """执行跟注"""
        player_current_bet = self._current_round.player_bets.get(action.player_id, 0)
        call_amount = self._current_round.current_bet - player_current_bet
        
        # 扣除筹码
        if not self._chip_ledger.deduct_chips(action.player_id, call_amount, f"跟注 {call_amount}"):
            return BetResult(False, action, "筹码扣除失败")
        
        # 更新下注记录
        self._current_round.player_bets[action.player_id] = self._current_round.current_bet
        self._current_round.player_actions[action.player_id] = action
        self._betting_history.append(action)
        
        return BetResult(True, action, chips_moved=call_amount)
    
    def _execute_raise(self, action: BetAction) -> BetResult:
        """执行加注"""
        player_current_bet = self._current_round.player_bets.get(action.player_id, 0)
        raise_amount = action.amount - player_current_bet
        
        # 扣除筹码
        if not self._chip_ledger.deduct_chips(action.player_id, raise_amount, f"加注到 {action.amount}"):
            return BetResult(False, action, "筹码扣除失败")
        
        # 更新下注状态
        self._current_round.current_bet = action.amount
        self._current_round.player_bets[action.player_id] = action.amount
        self._current_round.player_actions[action.player_id] = action
        self._betting_history.append(action)
        
        return BetResult(True, action, chips_moved=raise_amount)
    
    def _execute_all_in(self, action: BetAction) -> BetResult:
        """执行全押"""
        available_chips = self._chip_ledger.get_available_chips(action.player_id)
        player_current_bet = self._current_round.player_bets.get(action.player_id, 0)
        all_in_total = player_current_bet + available_chips
        
        # 扣除所有可用筹码
        if not self._chip_ledger.deduct_chips(action.player_id, available_chips, "全押"):
            return BetResult(False, action, "筹码扣除失败")
        
        # 更新下注状态
        if all_in_total > self._current_round.current_bet:
            old_current_bet = self._current_round.current_bet
            self._current_round.current_bet = all_in_total
            self._current_round.min_raise = all_in_total - old_current_bet
        
        self._current_round.player_bets[action.player_id] = all_in_total
        
        # 创建实际的全押行动（金额为实际全押总额）
        actual_action = BetAction(
            player_id=action.player_id,
            bet_type=BetType.ALL_IN,
            amount=all_in_total,
            timestamp=action.timestamp,
            description=f"全押 {all_in_total}",
            metadata={"original_amount": action.amount}
        )
        
        self._current_round.player_actions[action.player_id] = actual_action
        self._betting_history.append(actual_action)
        
        return BetResult(True, actual_action, chips_moved=available_chips)
    
    def is_round_complete(self) -> bool:
        """检查当前轮次是否完成"""
        if len(self._current_round.active_players) <= 1:
            return True
        
        validation_result = BettingValidator.validate_betting_round_completion(
            self._current_round.player_actions, self._current_round.active_players
        )
        
        return validation_result.is_valid
    
    def get_current_bet(self) -> int:
        """获取当前下注额"""
        return self._current_round.current_bet
    
    def get_min_raise(self) -> int:
        """获取最小加注额"""
        return self._current_round.min_raise
    
    def get_player_bet(self, player_id: str) -> int:
        """获取玩家当前轮次下注额"""
        return self._current_round.player_bets.get(player_id, 0)
    
    def get_active_players(self) -> List[str]:
        """获取活跃玩家列表"""
        return self._current_round.active_players.copy()
    
    def get_total_pot(self) -> int:
        """获取当前底池总额"""
        return sum(self._current_round.player_bets.values())
    
    def get_betting_history(self) -> List[BetAction]:
        """获取下注历史"""
        return self._betting_history.copy()
    
    def reset_for_next_round(self) -> None:
        """为下一轮次重置状态"""
        # 保留活跃玩家，重置其他状态
        active_players = self._current_round.active_players.copy()
        self._current_round = BettingRound(
            current_bet=0,
            min_raise=self._big_blind,
            active_players=active_players
        ) 