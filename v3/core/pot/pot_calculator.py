"""
边池计算器

提供边池计算的辅助功能。
"""

from typing import Dict, List, Tuple
from .pot_manager import SidePot

__all__ = ['PotCalculator']


class PotCalculator:
    """
    边池计算器
    
    提供边池计算的静态方法和辅助功能。
    """
    
    @staticmethod
    def calculate_contribution_levels(player_bets: Dict[str, int]) -> List[Tuple[int, List[str]]]:
        """
        计算贡献层级
        
        Args:
            player_bets: 玩家下注记录
            
        Returns:
            层级列表 [(level_amount, players_at_level)]
        """
        if not player_bets:
            return []
        
        # 按下注金额分组
        bet_groups = {}
        for player_id, bet_amount in player_bets.items():
            if bet_amount not in bet_groups:
                bet_groups[bet_amount] = []
            bet_groups[bet_amount].append(player_id)
        
        # 按金额排序
        sorted_levels = sorted(bet_groups.items())
        
        contribution_levels = []
        for bet_amount, players in sorted_levels:
            contribution_levels.append((bet_amount, players))
        
        return contribution_levels
    
    @staticmethod
    def calculate_pot_distribution_preview(player_bets: Dict[str, int]) -> Dict[str, List[str]]:
        """
        预览边池分配（不实际创建边池）
        
        Args:
            player_bets: 玩家下注记录
            
        Returns:
            边池预览 {pot_description: eligible_players}
        """
        if not player_bets:
            return {}
        
        sorted_bets = sorted(player_bets.items(), key=lambda x: x[1])
        pot_preview = {}
        
        previous_level = 0
        remaining_players = set(player_bets.keys())
        pot_index = 0
        
        for i, (player_id, bet_amount) in enumerate(sorted_bets):
            if bet_amount <= previous_level:
                continue
            
            level_contribution = bet_amount - previous_level
            pot_amount = level_contribution * len(remaining_players)
            
            if pot_amount > 0:
                pot_name = f"主池" if pot_index == 0 else f"边池{pot_index}"
                pot_description = f"{pot_name} ({pot_amount}筹码)"
                pot_preview[pot_description] = list(remaining_players)
                pot_index += 1
            
            # 移除当前玩家（如果他们全押了）
            if i < len(sorted_bets) - 1:
                next_bet = sorted_bets[i + 1][1]
                if bet_amount < next_bet:
                    remaining_players.discard(player_id)
            
            previous_level = bet_amount
        
        return pot_preview
    
    @staticmethod
    def validate_bet_consistency(player_bets: Dict[str, int]) -> bool:
        """
        验证下注记录的一致性
        
        Args:
            player_bets: 玩家下注记录
            
        Returns:
            是否一致
        """
        if not player_bets:
            return True
        
        # 检查是否有负数下注
        for player_id, bet_amount in player_bets.items():
            if bet_amount < 0:
                return False
        
        return True
    
    @staticmethod
    def calculate_minimum_call_amount(player_bets: Dict[str, int], calling_player: str) -> int:
        """
        计算玩家需要跟注的最小金额
        
        Args:
            player_bets: 玩家下注记录
            calling_player: 要跟注的玩家
            
        Returns:
            最小跟注金额
        """
        if not player_bets:
            return 0
        
        max_bet = max(player_bets.values())
        current_bet = player_bets.get(calling_player, 0)
        
        return max(0, max_bet - current_bet)
    
    @staticmethod
    def get_pot_equity_distribution(side_pots: List[SidePot], player_id: str) -> Dict[str, int]:
        """
        获取玩家在各边池中的权益
        
        Args:
            side_pots: 边池列表
            player_id: 玩家ID
            
        Returns:
            权益分配 {pot_id: potential_amount}
        """
        equity_distribution = {}
        
        for pot in side_pots:
            if player_id in pot.eligible_players:
                # 假设平分的情况下的潜在收益
                potential_amount = pot.amount // len(pot.eligible_players)
                equity_distribution[pot.pot_id] = potential_amount
        
        return equity_distribution