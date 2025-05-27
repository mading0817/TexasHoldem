"""
边池计算系统
实现标准德州扑克的边池计算规则
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class SidePot:
    """
    边池数据结构
    记录边池金额和有资格竞争的玩家
    """
    amount: int                    # 边池金额
    eligible_players: List[int]    # 有资格竞争此边池的玩家座位号列表

    def __post_init__(self):
        """验证边池数据的有效性"""
        if self.amount < 0:
            raise ValueError(f"边池金额不能为负数: {self.amount}")
        
        if not self.eligible_players:
            raise ValueError("边池必须至少有一个有资格的玩家")
        
        # 确保玩家列表无重复
        if len(self.eligible_players) != len(set(self.eligible_players)):
            raise ValueError("边池的有资格玩家列表不能有重复")

    def __str__(self) -> str:
        """返回边池的可读表示"""
        players_str = ", ".join(map(str, self.eligible_players))
        return f"边池({self.amount}筹码, 玩家: {players_str})"

    def __repr__(self) -> str:
        """返回边池的调试表示"""
        return f"SidePot(amount={self.amount}, eligible_players={self.eligible_players})"


def calculate_side_pots(contrib: Dict[int, int]) -> List[SidePot]:
    """
    计算边池分配
    严格按照德州扑克标准规则实现
    
    Args:
        contrib: 玩家投入字典 {player_id: total_contribution}
        
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
    if not contrib:
        return []
    
    # 过滤掉投入为0的玩家
    contrib = {pid: amount for pid, amount in contrib.items() if amount > 0}
    
    if not contrib:
        return []
    
    pots: List[SidePot] = []
    
    # ① 按投入额升序排序
    sorted_items = sorted(contrib.items(), key=lambda kv: kv[1])
    
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


def validate_side_pot_calculation(contrib: Dict[int, int], pots: List[SidePot]) -> bool:
    """
    验证边池计算的正确性
    检查总金额是否匹配（不包括返还给单人的部分）
    
    Args:
        contrib: 原始投入字典
        pots: 计算得到的边池列表
        
    Returns:
        验证是否通过
    """
    if not contrib:
        return len(pots) == 0
    
    # 计算所有边池的总金额
    total_pot_amount = sum(pot.amount for pot in pots)
    
    # 计算应该进入边池的总金额（排除单人剩余部分）
    sorted_contribs = sorted(contrib.values())
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


def get_pot_distribution_summary(contrib: Dict[int, int]) -> Dict[str, any]:
    """
    获取边池分配的详细摘要
    包含边池信息和返还信息
    
    Args:
        contrib: 玩家投入字典
        
    Returns:
        包含边池和返还信息的摘要字典
    """
    pots = calculate_side_pots(contrib)
    
    # 计算返还金额
    total_contributed = sum(contrib.values())
    total_in_pots = sum(pot.amount for pot in pots)
    returned_amount = total_contributed - total_in_pots
    
    # 找出获得返还的玩家（投入最多且只有一人的情况）
    returned_to_player = None
    if returned_amount > 0:
        max_contrib = max(contrib.values())
        max_players = [pid for pid, amount in contrib.items() if amount == max_contrib]
        if len(max_players) == 1:
            returned_to_player = max_players[0]
    
    return {
        'side_pots': pots,
        'total_pot_amount': total_in_pots,
        'returned_amount': returned_amount,
        'returned_to_player': returned_to_player,
        'total_contributed': total_contributed,
        'validation_passed': validate_side_pot_calculation(contrib, pots)
    } 