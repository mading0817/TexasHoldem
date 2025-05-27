"""
底池管理器
整合主池和边池的计算与分配逻辑
"""

from typing import List, Dict, Optional
from .side_pot import SidePot, calculate_side_pots
from ..core.player import Player


class PotManager:
    """
    底池管理器
    负责收集玩家下注、计算边池分配和奖励发放
    """
    
    def __init__(self):
        """初始化底池管理器"""
        self.main_pot = 0
        self.side_pots: List[SidePot] = []
        self._total_collected = 0  # 历史收集的总金额，用于验证
    
    def collect_from_players(self, players: List[Player]) -> Dict[int, int]:
        """
        从玩家收集当前下注到底池
        自动计算主池和边池分配，并处理返还逻辑
        
        Args:
            players: 玩家列表
            
        Returns:
            返还给玩家的筹码 {seat_id: amount}
        """
        # 收集每个玩家的当前下注
        contributions = {}
        total_collected = 0
        
        for player in players:
            if player.current_bet > 0:
                contributions[player.seat_id] = player.current_bet
                total_collected += player.current_bet
                # 重置玩家的当前下注
                player.reset_current_bet()
        
        if not contributions:
            return {}  # 没有下注需要收集
        
        # 使用边池计算算法获取详细信息
        from .side_pot import get_pot_distribution_summary
        summary = get_pot_distribution_summary(contributions)
        
        calculated_pots = summary['side_pots']
        returned_amount = summary['returned_amount']
        returned_to_player = summary['returned_to_player']
        
        # 更新底池状态
        if calculated_pots:
            # 第一个边池作为主池
            if not self.side_pots:
                self.main_pot += calculated_pots[0].amount
                self.side_pots.extend(calculated_pots[1:])  # 其余作为边池
            else:
                # 如果已有边池，全部作为边池处理
                self.side_pots.extend(calculated_pots)
        
        # 处理返还逻辑
        returns = {}
        if returned_amount > 0 and returned_to_player is not None:
            # 将返还的筹码直接给回玩家
            for player in players:
                if player.seat_id == returned_to_player:
                    player.add_chips(returned_amount)
                    returns[returned_to_player] = returned_amount
                    break
        
        self._total_collected += total_collected
        return returns
    
    def award_pots(self, winners_by_pot: Dict[int, List[Player]]) -> Dict[int, int]:
        """
        按照胜负结果分配底池
        
        Args:
            winners_by_pot: 每个底池的获胜者 {pot_index: [winners]}
                          pot_index=0表示主池，>0表示边池
        
        Returns:
            每个玩家获得的筹码 {seat_id: amount}
        """
        awards = {}
        
        # 分配主池
        if 0 in winners_by_pot and self.main_pot > 0:
            winners = winners_by_pot[0]
            if winners:
                award_per_winner = self.main_pot // len(winners)
                remainder = self.main_pot % len(winners)
                
                for i, winner in enumerate(winners):
                    amount = award_per_winner + (1 if i < remainder else 0)
                    awards[winner.seat_id] = awards.get(winner.seat_id, 0) + amount
                    winner.add_chips(amount)
                
                self.main_pot = 0
        
        # 分配边池
        for pot_index, side_pot in enumerate(self.side_pots, 1):
            if pot_index in winners_by_pot:
                winners = winners_by_pot[pot_index]
                if winners:
                    award_per_winner = side_pot.amount // len(winners)
                    remainder = side_pot.amount % len(winners)
                    
                    for i, winner in enumerate(winners):
                        amount = award_per_winner + (1 if i < remainder else 0)
                        awards[winner.seat_id] = awards.get(winner.seat_id, 0) + amount
                        winner.add_chips(amount)
        
        # 清空已分配的边池
        self.side_pots.clear()
        
        return awards
    
    def get_total_pot(self) -> int:
        """
        获取总底池金额（主池+所有边池）
        
        Returns:
            总底池金额
        """
        return self.main_pot + sum(pot.amount for pot in self.side_pots)
    
    def get_pot_summary(self) -> Dict:
        """
        获取底池状态摘要
        
        Returns:
            底池状态摘要字典
        """
        return {
            'main_pot': self.main_pot,
            'side_pots_count': len(self.side_pots),
            'side_pots': [
                {
                    'amount': pot.amount,
                    'eligible_players': pot.eligible_players
                }
                for pot in self.side_pots
            ],
            'total_pot': self.get_total_pot(),
            'total_collected': self._total_collected
        }
    
    def reset(self):
        """
        重置底池管理器
        用于开始新手牌
        """
        self.main_pot = 0
        self.side_pots.clear()
        self._total_collected = 0
    
    def validate_pot_integrity(self, expected_total: Optional[int] = None) -> bool:
        """
        验证底池完整性
        
        Args:
            expected_total: 期望的总金额
            
        Returns:
            验证是否通过
        """
        current_total = self.get_total_pot()
        
        if expected_total is not None:
            return current_total == expected_total
        
        # 基本完整性检查
        return (
            self.main_pot >= 0 and
            all(pot.amount >= 0 for pot in self.side_pots) and
            current_total <= self._total_collected
        )
    
    def __str__(self) -> str:
        """返回底池的可读表示"""
        side_pots_str = f", {len(self.side_pots)}个边池" if self.side_pots else ""
        return f"主池: {self.main_pot}{side_pots_str}, 总计: {self.get_total_pot()}"
    
    def __repr__(self) -> str:
        """返回底池的调试表示"""
        return f"PotManager(main={self.main_pot}, sides={len(self.side_pots)}, total={self.get_total_pot()})" 