"""
边池管理模块.

实现标准德州扑克的边池计算和分配规则。
包含SidePot数据结构和PotManager类，用于处理主池和边池的计算与奖励发放。
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .player import Player


@dataclass
class SidePot:
    """
    边池数据结构.
    
    记录边池金额和有资格竞争的玩家座位号列表。
    
    Attributes:
        amount: 边池金额
        eligible_players: 有资格竞争此边池的玩家座位号列表
    """

    amount: int
    eligible_players: List[int]

    def __post_init__(self) -> None:
        """验证边池数据的有效性.
        
        Raises:
            ValueError: 当边池数据无效时
        """
        if self.amount < 0:
            raise ValueError(f"边池金额不能为负数: {self.amount}")
        
        if not self.eligible_players:
            raise ValueError("边池必须至少有一个有资格的玩家")
        
        # 确保玩家列表无重复
        if len(self.eligible_players) != len(set(self.eligible_players)):
            raise ValueError("边池的有资格玩家列表不能有重复")

    def __str__(self) -> str:
        """返回边池的可读表示.
        
        Returns:
            包含边池金额和参与玩家的字符串
        """
        players_str = ", ".join(map(str, self.eligible_players))
        return f"边池({self.amount}筹码, 玩家: {players_str})"

    def __repr__(self) -> str:
        """返回边池的调试表示.
        
        Returns:
            SidePot对象的详细字符串表示
        """
        return f"SidePot(amount={self.amount}, eligible_players={self.eligible_players})"


def calculate_side_pots(contributions: Dict[int, int]) -> List[SidePot]:
    """
    计算边池分配.
    
    严格按照德州扑克标准规则实现边池计算算法。
    
    Args:
        contributions: 玩家投入字典 {player_id: total_contribution}
        
    Returns:
        边池列表，按生成顺序排列 [主池, 边池1, 边池2, ...]
        
    算法说明:
        1. 按投入金额升序排序玩家
        2. 从最小投入开始，逐层构建边池
        3. 每层边池金额 = (当前层投入 - 上层投入) × 当前层活跃玩家数
        4. 单人剩余筹码直接返还，不形成可争夺池
        
    示例:
        玩家投入 {0: 25, 1: 50, 2: 100}
        - 主池: 25 × 3 = 75 (玩家0,1,2)
        - 边池1: (50-25) × 2 = 50 (玩家1,2)  
        - 玩家2剩余: 100-50 = 50 (直接返还)
    """
    if not contributions:
        return []
    
    # 过滤掉投入为0的玩家
    contributions = {pid: amount for pid, amount in contributions.items() if amount > 0}
    
    if not contributions:
        return []
    
    pots: List[SidePot] = []
    
    # 按投入额升序排序
    sorted_items = sorted(contributions.items(), key=lambda kv: kv[1])
    
    prev = 0                     # 前一层已扣除的筹码
    active = len(sorted_items)   # 当前仍在争夺的玩家数
    
    for idx, (pid, amount) in enumerate(sorted_items):
        layer = amount - prev    # 该层每人需再扣除多少
        
        if layer == 0:
            # 多名玩家全押额相同，继续处理下一个玩家
            active -= 1
            continue
        
        if active <= 1:
            # 只剩一个玩家，剩余筹码直接返还，不形成边池
            break
        
        pool_amount = layer * active
        eligibles = [p for p, _ in sorted_items[idx:]]  # 从当前玩家到末尾
        pots.append(SidePot(pool_amount, eligibles))
        
        prev = amount
        active -= 1              # 当前玩家已用完筹码，脱离后续争夺
    
    return pots


def validate_side_pot_calculation(contributions: Dict[int, int], pots: List[SidePot]) -> bool:
    """
    验证边池计算的正确性.
    
    检查总金额是否匹配（不包括返还给单人的部分）。
    
    Args:
        contributions: 原始投入字典
        pots: 计算得到的边池列表
        
    Returns:
        验证是否通过
    """
    if not contributions:
        return len(pots) == 0
    
    # 计算所有边池的总金额
    total_pot_amount = sum(pot.amount for pot in pots)
    
    # 计算应该进入边池的总金额（排除单人剩余部分）
    sorted_contribs = sorted(contributions.values())
    expected_total = 0
    
    for i, amount in enumerate(sorted_contribs):
        if i == 0:
            # 主池：最小投入 × 总人数
            expected_total += amount * len(sorted_contribs)
        else:
            # 边池：(当前投入 - 前一投入) × 剩余人数
            remaining_players = len(sorted_contribs) - i
            if remaining_players > 1:  # 只有多人时才形成边池
                expected_total += (amount - sorted_contribs[i-1]) * remaining_players
    
    return total_pot_amount == expected_total


def get_pot_distribution_summary(contributions: Dict[int, int]) -> Dict[str, any]:
    """
    获取边池分配的详细摘要.
    
    包含边池信息和返还信息的完整摘要。
    
    Args:
        contributions: 玩家投入字典
        
    Returns:
        包含边池和返还信息的摘要字典，包含以下键：
        - side_pots: 边池列表
        - total_pot_amount: 总底池金额
        - returned_amount: 返还金额
        - returned_to_player: 获得返还的玩家ID
        - total_contributed: 总投入金额
        - validation_passed: 验证是否通过
    """
    pots = calculate_side_pots(contributions)
    
    # 计算返还金额
    total_contributed = sum(contributions.values())
    total_in_pots = sum(pot.amount for pot in pots)
    returned_amount = total_contributed - total_in_pots
    
    # 找出获得返还的玩家（投入最多且只有一人的情况）
    returned_to_player = None
    if returned_amount > 0:
        max_contrib = max(contributions.values())
        max_players = [pid for pid, amount in contributions.items() if amount == max_contrib]
        if len(max_players) == 1:
            returned_to_player = max_players[0]
    
    return {
        'side_pots': pots,
        'total_pot_amount': total_in_pots,
        'returned_amount': returned_amount,
        'returned_to_player': returned_to_player,
        'total_contributed': total_contributed,
        'validation_passed': validate_side_pot_calculation(contributions, pots)
    }


class PotManager:
    """
    边池管理器.
    
    负责收集玩家投入、计算边池分配、奖励发放等功能。
    支持复杂的多边池场景和筹码完整性验证。
    """

    def __init__(self) -> None:
        """初始化边池管理器.
        
        创建空的边池列表和投入记录。
        """
        self._main_pot: int = 0
        self._side_pots: List[SidePot] = []
        self._contributions: Dict[int, int] = {}
        self._total_collected: int = 0

    @property
    def side_pots(self) -> List[SidePot]:
        """获取边池列表（兼容性属性）.
        
        Returns:
            List[SidePot]: 当前的边池列表副本（不包括主池）
        """
        return self._side_pots.copy()

    def collect_from_players(self, players: List["Player"]) -> Dict[int, int]:
        """从玩家收集投入筹码.
        
        收集所有玩家的当前下注金额，自动创建边池，并处理返还。
        
        Args:
            players: 玩家列表
            
        Returns:
            Dict[int, int]: 返还给玩家的筹码字典 {player_id: returned_amount}
            
        Note:
            此方法会修改玩家的下注状态，将current_bet重置为0。
            收集的筹码会自动分配到主池和边池中。
            超额投入会返还给玩家。
        """
        # 收集当前轮次的投入
        round_contributions = {}
        
        for player in players:
            if player.current_bet > 0:
                contribution = player.current_bet
                round_contributions[player.seat_id] = contribution
                
                # 累加到总投入记录
                if player.seat_id not in self._contributions:
                    self._contributions[player.seat_id] = 0
                self._contributions[player.seat_id] += contribution
                
                # 重置玩家当前下注
                player.current_bet = 0
                
                # 更新总收集金额
                self._total_collected += contribution
        
        # 如果没有投入，直接返回
        if not round_contributions:
            return {}
        
        # 计算边池分配
        if len(set(round_contributions.values())) == 1:
            # 所有投入相等，只有主池
            self._main_pot += sum(round_contributions.values())
            return {}
        else:
            # 投入不等，需要计算边池和返还
            distribution = get_pot_distribution_summary(round_contributions)
            
            # 分配主池和边池
            all_pots = distribution['side_pots']
            if all_pots:
                self._main_pot += all_pots[0].amount  # 第一个是主池
                self._side_pots.extend(all_pots[1:])  # 其余是边池
            
            # 处理返还
            returns = {}
            if distribution['returned_amount'] > 0:
                # 找到投入最多的玩家
                max_contribution = max(round_contributions.values())
                max_contributors = [pid for pid, amount in round_contributions.items() 
                                 if amount == max_contribution]
                
                # 返还给第一个最大投入者（确定性）
                return_player = min(max_contributors)
                returns[return_player] = distribution['returned_amount']
                
                # 将返还的筹码加回给玩家
                for player in players:
                    if player.seat_id == return_player:
                        player.chips += distribution['returned_amount']
                        break
            
            return returns

    @property
    def main_pot(self) -> int:
        """获取主池金额（兼容性属性）.
        
        Returns:
            int: 主池金额
        """
        return self._main_pot

    def allocate_side_pots(self, contributions: Dict[int, int]) -> List[SidePot]:
        """分配边池.
        
        根据玩家投入计算边池分配，但不修改内部状态。
        
        Args:
            contributions: 玩家投入字典
            
        Returns:
            List[SidePot]: 计算得到的边池列表
        """
        return calculate_side_pots(contributions)

    def award_pots(self, winners_by_pot: Dict[int, List["Player"]]) -> Dict[int, int]:
        """奖励边池给获胜者.
        
        将各个边池的奖金分配给对应的获胜者。
        
        Args:
            winners_by_pot: 各边池的获胜者字典 {pot_index: [winner_players]}
                           pot_index=0表示主池，pot_index>0表示边池
            
        Returns:
            Dict[int, int]: 各玩家获得的奖金 {player_id: award_amount}
            
        Raises:
            ValueError: 当边池索引无效或获胜者列表为空时
            
        Note:
            - 如果一个边池有多个获胜者，奖金会平均分配
            - 如果有余数，会按玩家ID顺序分配给前几个获胜者
            - 奖励后边池会被清空
        """
        awards = {}
        
        for pot_index, winners in winners_by_pot.items():
            if not winners:
                raise ValueError(f"边池 {pot_index} 的获胜者列表不能为空")
            
            if pot_index == 0:
                # 主池
                pot_amount = self._main_pot
                if pot_amount == 0:
                    continue
            else:
                # 边池
                side_pot_index = pot_index - 1
                if side_pot_index >= len(self._side_pots):
                    raise ValueError(f"无效的边池索引: {pot_index}")
                pot_amount = self._side_pots[side_pot_index].amount
            
            winner_count = len(winners)
            base_award = pot_amount // winner_count
            remainder = pot_amount % winner_count
            
            # 按玩家ID排序以确保确定性的余数分配
            sorted_winners = sorted(winners, key=lambda p: p.seat_id)
            
            for i, winner in enumerate(sorted_winners):
                award = base_award
                if i < remainder:  # 前remainder个获胜者多得1筹码
                    award += 1
                
                if winner.seat_id not in awards:
                    awards[winner.seat_id] = 0
                awards[winner.seat_id] += award
                
                # 将奖金加到获胜者的筹码中
                winner.chips += award
        
        # 清空已分配的边池
        self._main_pot = 0
        self._side_pots.clear()
        
        return awards

    def get_total_pot(self) -> int:
        """获取总底池金额.
        
        Returns:
            int: 主池和所有边池的总金额
        """
        return self._main_pot + sum(pot.amount for pot in self._side_pots)

    def get_pot_summary(self) -> Dict:
        """获取底池摘要信息.
        
        Returns:
            Dict: 包含边池详情的摘要信息，包含以下键：
            - main_pot: 主池金额
            - side_pots_count: 边池数量（不包括主池）
            - total_pot: 总底池金额
            - total_collected: 总收集金额
            - contributions: 玩家投入记录
        """
        return {
            'main_pot': self._main_pot,
            'side_pots_count': len(self._side_pots),
            'total_pot': self.get_total_pot(),
            'total_collected': self._total_collected,
            'contributions': self._contributions.copy()
        }

    def reset(self) -> None:
        """重置边池管理器.
        
        清空所有边池、投入记录和收集金额，准备新的一手牌。
        """
        self._main_pot = 0
        self._side_pots.clear()
        self._contributions.clear()
        self._total_collected = 0

    def validate_pot_integrity(self, expected_total: Optional[int] = None) -> bool:
        """验证边池完整性.
        
        检查边池总金额是否与预期一致，确保筹码守恒。
        
        Args:
            expected_total: 预期的总金额，如果为None则使用总收集金额
            
        Returns:
            bool: 验证是否通过
            
        Note:
            此方法用于调试和测试，确保边池计算的正确性。
        """
        if expected_total is None:
            expected_total = self._total_collected
        
        actual_total = self.get_total_pot()
        return actual_total == expected_total

    def __str__(self) -> str:
        """返回边池管理器的字符串表示.
        
        Returns:
            str: 包含边池数量和总金额的字符串
        """
        total_pot = self.get_total_pot()
        return f"主池: {self._main_pot}, 总计: {total_pot}"

    def __repr__(self) -> str:
        """返回边池管理器的详细字符串表示.
        
        Returns:
            str: 包含所有边池详情的字符串
        """
        side_count = len(self._side_pots)
        total_pot = self.get_total_pot()
        return f"PotManager(main={self._main_pot}, sides={side_count}, total={total_pot})" 