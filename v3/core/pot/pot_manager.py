"""
边池管理器

处理边池的创建、计算和分配。
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from ..chips.chip_ledger import ChipLedger
from ..eval.types import HandResult

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

        # 过滤掉没有下注的玩家
        active_bets = {p: b for p, b in player_bets.items() if b > 0}
        if not active_bets:
            return []

        self._side_pots.clear()
        self._pot_counter = 0

        # 获取所有不重复的下注额，并排序
        sorted_bet_levels = sorted(list(set(active_bets.values())))
        
        last_level = 0
        
        for i, level in enumerate(sorted_bet_levels):
            # 找出所有下注额大于等于当前层级的玩家
            # 这些玩家对当前层级的底池有贡献
            contributors = {p for p, b in active_bets.items() if b >= level}
            
            # 计算当前层级的贡献额
            contribution_per_player = level - last_level
            pot_amount = contribution_per_player * len(contributors)
            
            if pot_amount > 0:
                pot_id = f"pot_{self._pot_counter}"
                self._pot_counter += 1
                
                side_pot = SidePot(
                    pot_id=pot_id,
                    amount=pot_amount,
                    eligible_players=contributors,
                    is_main_pot=(i == 0)
                )
                self._side_pots.append(side_pot)
            
            last_level = level
            
        return self._side_pots.copy()
    
    def distribute_pots(self, side_pots: List[SidePot], player_hand_results: Dict[str, HandResult]) -> Dict[str, int]:
        """
        根据玩家手牌强度，分配所有边池

        Args:
            side_pots: 待分配的边池列表
            player_hand_results: 参与摊牌玩家的手牌评估结果 {player_id: HandResult}

        Returns:
            一个字典，包含每个获胜玩家及其赢得的总金额 {player_id: total_winnings}
        """
        winnings = {player_id: 0 for player_id in player_hand_results.keys()}

        # 通常边池是从主池开始，按顺序分配
        for pot in side_pots:
            # 找出有资格争夺此底池且参与摊牌的玩家
            eligible_players_in_showdown = [
                p_id for p_id in pot.eligible_players if p_id in player_hand_results
            ]

            if not eligible_players_in_showdown:
                # 这种情况理论上不应该发生，但作为保护，跳过这个池
                continue

            # 在有资格的玩家中找到最好的手牌
            best_hand_in_pot: Optional[HandResult] = None
            for player_id in eligible_players_in_showdown:
                hand_result = player_hand_results[player_id]
                if best_hand_in_pot is None or hand_result.compare_to(best_hand_in_pot) > 0:
                    best_hand_in_pot = hand_result

            # 找到所有拥有这手最好牌的玩家（处理平分底池的情况）
            if best_hand_in_pot is None:
                continue
                
            pot_winners = [
                player_id for player_id in eligible_players_in_showdown
                if player_hand_results[player_id].compare_to(best_hand_in_pot) == 0
            ]

            # 在赢家之间分配底池金额
            if pot_winners:
                pot_amount = pot.amount
                per_winner_amount = pot_amount // len(pot_winners)
                remainder = pot_amount % len(pot_winners)

                # 为了确定性地分配余数，按玩家ID排序
                sorted_pot_winners = sorted(pot_winners)
                for i, winner_id in enumerate(sorted_pot_winners):
                    win_amount = per_winner_amount
                    if i < remainder:
                        win_amount += 1
                    
                    if win_amount > 0:
                        winnings[winner_id] = winnings.get(winner_id, 0) + win_amount

        # 返回只包含有奖金的玩家
        return {p_id: amount for p_id, amount in winnings.items() if amount > 0}

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
        # 为了确定性地分配余数，按玩家ID排序
        sorted_winners = sorted(top_winners)
        
        for i, player_id in enumerate(sorted_winners):
            amount = per_winner_amount
            if i < remaining_chips:
                amount += 1
            distributions[player_id] = amount
        
        # 移除分配为0的玩家
        distributions = {p: a for p, a in distributions.items() if a > 0}

        return PotDistributionResult(
            distributions=distributions,
            total_distributed=side_pot.amount,
            remaining_chips=0  # 余数已经分配
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