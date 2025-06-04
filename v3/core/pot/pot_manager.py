"""
边池管理器

处理边池的创建、计算和分配。
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from ..chips.chip_ledger import ChipLedger

__all__ = ['PotManager', 'SidePot', 'PotDistributionResult']


@dataclass(frozen=True)
class SidePot:
    """边池数据结构"""
    pot_id: str
    amount: int
    eligible_players: Set[str]
    is_main_pot: bool = False
    
    def __post_init__(self):
        """验证边池数据的有效性"""
        if self.amount < 0:
            raise ValueError("边池金额不能为负数")
        if not self.eligible_players:
            raise ValueError("边池必须有至少一个有资格的玩家")


@dataclass(frozen=True)
class PotDistributionResult:
    """边池分配结果"""
    distributions: Dict[str, int]  # 玩家ID -> 获得金额
    total_distributed: int
    remaining_chips: int = 0  # 由于无法整除产生的余额
    
    def __post_init__(self):
        """验证分配结果的一致性"""
        calculated_total = sum(self.distributions.values()) + self.remaining_chips
        if calculated_total != self.total_distributed:
            raise ValueError(f"分配结果不一致: 计算总额{calculated_total}, 声明总额{self.total_distributed}")


class PotManager:
    """
    边池管理器
    
    处理边池的创建、计算和分配逻辑。
    """
    
    def __init__(self, chip_ledger: ChipLedger):
        """
        初始化边池管理器
        
        Args:
            chip_ledger: 筹码账本
        """
        self._chip_ledger = chip_ledger
        self._side_pots: List[SidePot] = []
        self._pot_counter = 0
    
    def calculate_side_pots(self, player_bets: Dict[str, int]) -> List[SidePot]:
        """
        计算边池分配
        
        Args:
            player_bets: 玩家下注记录 {player_id: bet_amount}
            
        Returns:
            边池列表
        """
        if not player_bets:
            return []
        
        # 按下注金额排序
        sorted_bets = sorted(player_bets.items(), key=lambda x: x[1])
        side_pots = []
        
        previous_level = 0
        remaining_players = set(player_bets.keys())
        
        for i, (player_id, bet_amount) in enumerate(sorted_bets):
            if bet_amount <= previous_level:
                continue
            
            # 计算当前层级的边池
            level_contribution = bet_amount - previous_level
            pot_amount = level_contribution * len(remaining_players)
            
            if pot_amount > 0:
                pot_id = f"pot_{self._pot_counter}"
                self._pot_counter += 1
                
                side_pot = SidePot(
                    pot_id=pot_id,
                    amount=pot_amount,
                    eligible_players=remaining_players.copy(),
                    is_main_pot=(i == 0)
                )
                side_pots.append(side_pot)
            
            # 移除当前玩家（如果他们全押了）
            if i < len(sorted_bets) - 1:
                next_bet = sorted_bets[i + 1][1]
                if bet_amount < next_bet:
                    remaining_players.discard(player_id)
            
            previous_level = bet_amount
        
        self._side_pots = side_pots
        return side_pots.copy()
    
    def distribute_winnings(self, winners: Dict[str, int], hand_strengths: Dict[str, int]) -> PotDistributionResult:
        """
        分配奖金到获胜者
        
        Args:
            winners: 获胜者及其手牌强度 {player_id: hand_strength}
            hand_strengths: 所有玩家的手牌强度 {player_id: hand_strength}
            
        Returns:
            分配结果
        """
        if not self._side_pots:
            return PotDistributionResult({}, 0)
        
        total_distributions = {}
        total_distributed = 0
        total_remaining = 0
        
        # 按边池顺序分配（从主池到边池）
        for side_pot in self._side_pots:
            pot_result = self._distribute_single_pot(side_pot, winners, hand_strengths)
            
            # 合并分配结果
            for player_id, amount in pot_result.distributions.items():
                total_distributions[player_id] = total_distributions.get(player_id, 0) + amount
            
            total_distributed += pot_result.total_distributed
            total_remaining += pot_result.remaining_chips
        
        # 执行实际的筹码分配
        for player_id, amount in total_distributions.items():
            if amount > 0:
                self._chip_ledger.add_chips(player_id, amount, f"获得奖金 {amount}")
        
        return PotDistributionResult(
            distributions=total_distributions,
            total_distributed=total_distributed,
            remaining_chips=total_remaining
        )
    
    def _distribute_single_pot(self, side_pot: SidePot, winners: Dict[str, int], 
                             hand_strengths: Dict[str, int]) -> PotDistributionResult:
        """
        分配单个边池
        
        Args:
            side_pot: 边池
            winners: 获胜者及其手牌强度
            hand_strengths: 所有玩家的手牌强度
            
        Returns:
            分配结果
        """
        # 找出有资格获得此边池的获胜者
        eligible_winners = {}
        for player_id, strength in winners.items():
            if player_id in side_pot.eligible_players:
                eligible_winners[player_id] = strength
        
        if not eligible_winners:
            # 没有有资格的获胜者，边池保留
            return PotDistributionResult({}, side_pot.amount, side_pot.amount)
        
        # 按手牌强度分组
        strength_groups = {}
        for player_id, strength in eligible_winners.items():
            if strength not in strength_groups:
                strength_groups[strength] = []
            strength_groups[strength].append(player_id)
        
        # 找出最强的手牌
        max_strength = max(strength_groups.keys())
        top_winners = strength_groups[max_strength]
        
        # 平分边池
        per_winner_amount = side_pot.amount // len(top_winners)
        remaining_chips = side_pot.amount % len(top_winners)
        
        distributions = {}
        for player_id in top_winners:
            distributions[player_id] = per_winner_amount
        
        return PotDistributionResult(
            distributions=distributions,
            total_distributed=side_pot.amount,
            remaining_chips=remaining_chips
        )
    
    def get_total_pot_amount(self) -> int:
        """获取所有边池的总金额"""
        return sum(pot.amount for pot in self._side_pots)
    
    def get_side_pots(self) -> List[SidePot]:
        """获取当前边池列表"""
        return self._side_pots.copy()
    
    def get_main_pot(self) -> Optional[SidePot]:
        """获取主池"""
        for pot in self._side_pots:
            if pot.is_main_pot:
                return pot
        return None
    
    def clear_pots(self) -> None:
        """清空所有边池"""
        self._side_pots.clear()
    
    def validate_pot_integrity(self, expected_total: int) -> bool:
        """
        验证边池完整性
        
        Args:
            expected_total: 期望的总金额
            
        Returns:
            是否完整
        """
        actual_total = self.get_total_pot_amount()
        return actual_total == expected_total
    
    def get_player_eligible_pots(self, player_id: str) -> List[SidePot]:
        """
        获取玩家有资格参与的边池
        
        Args:
            player_id: 玩家ID
            
        Returns:
            有资格的边池列表
        """
        eligible_pots = []
        for pot in self._side_pots:
            if player_id in pot.eligible_players:
                eligible_pots.append(pot)
        return eligible_pots 