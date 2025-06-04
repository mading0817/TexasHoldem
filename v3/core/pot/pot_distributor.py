"""
边池分配器

提供边池分配的辅助功能。
"""

from typing import Dict, List, Optional, Tuple
from .pot_manager import SidePot, PotDistributionResult

__all__ = ['PotDistributor']


class PotDistributor:
    """
    边池分配器
    
    提供边池分配的静态方法和辅助功能。
    """
    
    @staticmethod
    def calculate_split_pot_distribution(pot_amount: int, winners: List[str]) -> Dict[str, int]:
        """
        计算平分底池的分配
        
        Args:
            pot_amount: 底池金额
            winners: 获胜者列表
            
        Returns:
            分配结果 {player_id: amount}
        """
        if not winners or pot_amount <= 0:
            return {}
        
        per_winner = pot_amount // len(winners)
        remainder = pot_amount % len(winners)
        
        distribution = {}
        for i, player_id in enumerate(winners):
            amount = per_winner
            # 余数分配给前几个获胜者
            if i < remainder:
                amount += 1
            distribution[player_id] = amount
        
        return distribution
    
    @staticmethod
    def calculate_proportional_distribution(pot_amount: int, player_contributions: Dict[str, int]) -> Dict[str, int]:
        """
        按贡献比例分配底池
        
        Args:
            pot_amount: 底池金额
            player_contributions: 玩家贡献 {player_id: contribution}
            
        Returns:
            分配结果 {player_id: amount}
        """
        if not player_contributions or pot_amount <= 0:
            return {}
        
        total_contribution = sum(player_contributions.values())
        if total_contribution == 0:
            return {}
        
        distribution = {}
        remaining_amount = pot_amount
        
        # 按比例计算分配
        for player_id, contribution in player_contributions.items():
            if contribution > 0:
                proportion = contribution / total_contribution
                amount = int(pot_amount * proportion)
                distribution[player_id] = amount
                remaining_amount -= amount
        
        # 分配余额给第一个玩家
        if remaining_amount > 0 and distribution:
            first_player = next(iter(distribution.keys()))
            distribution[first_player] += remaining_amount
        
        return distribution
    
    @staticmethod
    def validate_distribution_total(distribution: Dict[str, int], expected_total: int) -> bool:
        """
        验证分配总额是否正确
        
        Args:
            distribution: 分配结果
            expected_total: 期望总额
            
        Returns:
            是否正确
        """
        actual_total = sum(distribution.values())
        return actual_total == expected_total
    
    @staticmethod
    def merge_distributions(distributions: List[Dict[str, int]]) -> Dict[str, int]:
        """
        合并多个分配结果
        
        Args:
            distributions: 分配结果列表
            
        Returns:
            合并后的分配结果
        """
        merged = {}
        
        for distribution in distributions:
            for player_id, amount in distribution.items():
                merged[player_id] = merged.get(player_id, 0) + amount
        
        return merged
    
    @staticmethod
    def calculate_high_card_tiebreaker(tied_players: List[str], pot_amount: int, 
                                     high_cards: Dict[str, List[int]]) -> Dict[str, int]:
        """
        使用高牌决定平局的分配
        
        Args:
            tied_players: 平局的玩家
            pot_amount: 底池金额
            high_cards: 玩家的高牌 {player_id: [card_values]}
            
        Returns:
            分配结果
        """
        if not tied_players or pot_amount <= 0:
            return {}
        
        # 按高牌排序
        def compare_high_cards(player_id: str) -> List[int]:
            return high_cards.get(player_id, [])
        
        # 按高牌降序排序
        sorted_players = sorted(tied_players, key=compare_high_cards, reverse=True)
        
        # 找出真正的最高牌玩家
        if not high_cards:
            # 没有高牌信息，平分
            return PotDistributor.calculate_split_pot_distribution(pot_amount, tied_players)
        
        best_high_cards = high_cards.get(sorted_players[0], [])
        winners = []
        
        for player_id in sorted_players:
            player_high_cards = high_cards.get(player_id, [])
            if player_high_cards == best_high_cards:
                winners.append(player_id)
            else:
                break
        
        return PotDistributor.calculate_split_pot_distribution(pot_amount, winners)
    
    @staticmethod
    def calculate_all_in_protection(side_pots: List[SidePot], all_in_player: str, 
                                  max_win_amount: int) -> List[SidePot]:
        """
        计算全押保护后的边池分配
        
        Args:
            side_pots: 原始边池列表
            all_in_player: 全押玩家
            max_win_amount: 全押玩家最大可赢金额
            
        Returns:
            调整后的边池列表
        """
        if not side_pots or max_win_amount <= 0:
            return side_pots
        
        adjusted_pots = []
        remaining_win_amount = max_win_amount
        
        for pot in side_pots:
            if all_in_player not in pot.eligible_players:
                # 全押玩家不参与此边池
                adjusted_pots.append(pot)
                continue
            
            if remaining_win_amount <= 0:
                # 全押玩家已达到最大可赢金额，从后续边池中移除
                new_eligible = pot.eligible_players.copy()
                new_eligible.discard(all_in_player)
                
                if new_eligible:
                    adjusted_pot = SidePot(
                        pot_id=pot.pot_id,
                        amount=pot.amount,
                        eligible_players=new_eligible,
                        is_main_pot=pot.is_main_pot
                    )
                    adjusted_pots.append(adjusted_pot)
                continue
            
            if pot.amount <= remaining_win_amount:
                # 全押玩家可以赢得整个边池
                adjusted_pots.append(pot)
                remaining_win_amount -= pot.amount
            else:
                # 需要分割边池
                win_pot = SidePot(
                    pot_id=f"{pot.pot_id}_win",
                    amount=remaining_win_amount,
                    eligible_players=pot.eligible_players.copy(),
                    is_main_pot=pot.is_main_pot
                )
                
                remaining_eligible = pot.eligible_players.copy()
                remaining_eligible.discard(all_in_player)
                
                if remaining_eligible:
                    remaining_pot = SidePot(
                        pot_id=f"{pot.pot_id}_remaining",
                        amount=pot.amount - remaining_win_amount,
                        eligible_players=remaining_eligible,
                        is_main_pot=False
                    )
                    adjusted_pots.extend([win_pot, remaining_pot])
                else:
                    adjusted_pots.append(win_pot)
                
                remaining_win_amount = 0
        
        return adjusted_pots 