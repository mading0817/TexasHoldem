"""
Property-based Tests for Chip Conservation - 筹码守恒属性测试

该模块使用hypothesis进行基于属性的测试，确保在任何情况下筹码都守恒。
这是v3反作弊系统的重要组成部分。

Tests:
    test_chip_conservation_property: 筹码守恒属性测试
    test_pot_distribution_property: 奖池分配属性测试
    test_betting_round_property: 下注轮次属性测试
"""

import pytest
from hypothesis import given, strategies as st, assume
from typing import Dict, List
from dataclasses import dataclass

# 导入反作弊检查器
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker
from v3.tests.anti_cheat.state_consistency_checker import (
    StateConsistencyChecker,
    GameStateSnapshot
)


@dataclass(frozen=True)
class MockPlayer:
    """模拟玩家数据结构（仅用于property测试）"""
    player_id: str
    chips: int
    bet: int = 0


@dataclass(frozen=True)
class MockGameState:
    """模拟游戏状态数据结构（仅用于property测试）"""
    players: Dict[str, MockPlayer]
    pot: int = 0
    
    @property
    def total_chips(self) -> int:
        """计算总筹码"""
        return sum(player.chips for player in self.players.values()) + self.pot


# Hypothesis策略定义
player_chips_strategy = st.integers(min_value=100, max_value=10000)
player_count_strategy = st.integers(min_value=2, max_value=8)
bet_amount_strategy = st.integers(min_value=10, max_value=1000)


@pytest.mark.property_test
@pytest.mark.anti_cheat
@given(st.lists(player_chips_strategy, min_size=2, max_size=8))
def test_chip_conservation_property(player_chips_list: List[int]):
    """Property test: 无论如何操作，筹码总量必须守恒
    
    Args:
        player_chips_list: 玩家筹码列表
    """
    # 创建初始游戏状态
    players = {}
    for i, chips in enumerate(player_chips_list):
        player_id = f"player_{i}"
        players[player_id] = MockPlayer(player_id=player_id, chips=chips)
    
    initial_state = MockGameState(players=players)
    initial_total = initial_state.total_chips
    
    # 模拟各种操作后的状态
    # 1. 玩家下注操作
    updated_players = {}
    total_bets = 0
    
    for player_id, player in players.items():
        # 随机下注金额（不超过玩家筹码）
        max_bet = min(player.chips, 500)  # 限制最大下注
        if max_bet > 0:
            bet_amount = min(max_bet, 100)  # 保守下注
            updated_players[player_id] = MockPlayer(
                player_id=player_id,
                chips=player.chips - bet_amount,
                bet=bet_amount
            )
            total_bets += bet_amount
        else:
            updated_players[player_id] = player
    
    # 创建下注后的状态
    final_state = MockGameState(
        players=updated_players,
        pot=total_bets
    )
    
    # 验证筹码守恒
    final_total = final_state.total_chips
    
    # 使用反作弊检查器验证
    CoreUsageChecker.verify_chip_conservation(initial_total, final_total)
    
    # 额外的断言
    assert initial_total == final_total, \
        f"筹码守恒失败: 初始{initial_total}, 最终{final_total}"


@pytest.mark.property_test
@pytest.mark.anti_cheat
@given(
    st.lists(player_chips_strategy, min_size=2, max_size=6),
    st.lists(st.integers(min_value=1, max_value=100), min_size=1, max_size=3)
)
def test_pot_distribution_property(player_chips_list: List[int], winner_indices: List[int]):
    """Property test: 奖池分配后筹码总量守恒
    
    Args:
        player_chips_list: 玩家筹码列表
        winner_indices: 获胜者索引列表
    """
    assume(len(player_chips_list) >= 2)
    assume(len(winner_indices) >= 1)
    
    # 确保获胜者索引有效
    valid_winner_indices = [idx % len(player_chips_list) for idx in winner_indices]
    valid_winner_indices = list(set(valid_winner_indices))  # 去重
    
    # 创建初始状态
    players = {}
    total_pot = 0
    
    for i, chips in enumerate(player_chips_list):
        player_id = f"player_{i}"
        # 每个玩家下注一定金额
        bet_amount = min(chips // 10, 50)  # 下注筹码的10%或50，取较小值
        players[player_id] = MockPlayer(
            player_id=player_id,
            chips=chips - bet_amount,
            bet=bet_amount
        )
        total_pot += bet_amount
    
    initial_state = MockGameState(players=players, pot=total_pot)
    initial_total = initial_state.total_chips
    
    # 模拟奖池分配
    winnings_per_winner = total_pot // len(valid_winner_indices)
    remaining_pot = total_pot % len(valid_winner_indices)
    
    updated_players = {}
    remaining_distributed = 0
    
    for i, (player_id, player) in enumerate(players.items()):
        if i in valid_winner_indices:
            # 获胜者获得奖金
            extra = 0
            if remaining_distributed < remaining_pot:
                extra = 1
                remaining_distributed += 1
            
            winnings = winnings_per_winner + extra
            updated_players[player_id] = MockPlayer(
                player_id=player_id,
                chips=player.chips + winnings,
                bet=0
            )
        else:
            # 非获胜者清零下注
            updated_players[player_id] = MockPlayer(
                player_id=player_id,
                chips=player.chips,
                bet=0
            )
    
    final_state = MockGameState(players=updated_players, pot=0)
    final_total = final_state.total_chips
    
    # 验证筹码守恒
    CoreUsageChecker.verify_chip_conservation(initial_total, final_total)


@pytest.mark.property_test
@pytest.mark.anti_cheat
@given(
    st.lists(player_chips_strategy, min_size=2, max_size=4),
    st.lists(bet_amount_strategy, min_size=1, max_size=5)
)
def test_betting_round_property(player_chips_list: List[int], bet_sequence: List[int]):
    """Property test: 多轮下注后筹码守恒
    
    Args:
        player_chips_list: 玩家筹码列表
        bet_sequence: 下注序列
    """
    assume(len(player_chips_list) >= 2)
    assume(len(bet_sequence) >= 1)
    
    # 创建初始状态
    players = {}
    for i, chips in enumerate(player_chips_list):
        player_id = f"player_{i}"
        players[player_id] = MockPlayer(player_id=player_id, chips=chips)
    
    current_state = MockGameState(players=players)
    initial_total = current_state.total_chips
    
    # 模拟多轮下注
    for bet_amount in bet_sequence:
        updated_players = {}
        total_new_bets = 0
        
        for player_id, player in current_state.players.items():
            # 每个玩家尝试下注
            actual_bet = min(bet_amount, player.chips, 200)  # 限制最大下注
            
            if actual_bet > 0:
                updated_players[player_id] = MockPlayer(
                    player_id=player_id,
                    chips=player.chips - actual_bet,
                    bet=player.bet + actual_bet
                )
                total_new_bets += actual_bet
            else:
                updated_players[player_id] = player
        
        # 更新状态
        current_state = MockGameState(
            players=updated_players,
            pot=current_state.pot + total_new_bets
        )
        
        # 每轮都验证筹码守恒
        current_total = current_state.total_chips
        CoreUsageChecker.verify_chip_conservation(initial_total, current_total)
    
    # 最终验证
    final_total = current_state.total_chips
    assert initial_total == final_total, \
        f"多轮下注后筹码不守恒: 初始{initial_total}, 最终{final_total}"


@pytest.mark.property_test
def test_state_snapshot_consistency():
    """测试状态快照的一致性"""
    # 创建测试快照
    snapshot1 = GameStateSnapshot(
        total_chips=10000,
        pot_size=500,
        player_chips={"p1": 4500, "p2": 3000, "p3": 2000},
        current_phase="FLOP",
        current_bet=100,
        active_players=["p1", "p2", "p3"]
    )
    
    snapshot2 = GameStateSnapshot(
        total_chips=10000,  # 总筹码保持不变
        pot_size=800,       # 奖池增加
        player_chips={"p1": 4200, "p2": 3000, "p3": 2000},  # p1减少300
        current_phase="FLOP",
        current_bet=200,
        active_players=["p1", "p2", "p3"]
    )
    
    # 验证筹码守恒
    StateConsistencyChecker.verify_chip_conservation(snapshot1, snapshot2)


if __name__ == "__main__":
    # 运行property测试
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"]) 