"""
State Consistency Checker - 状态一致性检查器

该模块验证游戏状态变化的一致性和合理性，防止测试绕过业务规则。
确保所有状态变化都符合德州扑克的标准规则。
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class GameStateSnapshot:
    """游戏状态快照"""
    total_chips: int
    pot_size: int
    player_chips: Dict[str, int]
    current_phase: str
    current_bet: int
    active_players: List[str]


class StateConsistencyChecker:
    """状态一致性检查器"""
    
    @staticmethod
    def verify_chip_conservation(
        before: GameStateSnapshot, 
        after: GameStateSnapshot
    ) -> None:
        """验证筹码守恒"""
        before_total = before.total_chips
        after_total = after.total_chips
        
        assert before_total == after_total, \
            f"筹码必须守恒: 操作前{before_total}, 操作后{after_total}"
    
    @staticmethod
    def verify_betting_rules(
        before: GameStateSnapshot,
        after: GameStateSnapshot,
        player_id: str,
        action: str,
        amount: int = 0
    ) -> None:
        """验证下注规则"""
        assert player_id in before.player_chips, f"玩家 {player_id} 不存在"
        assert player_id in before.active_players, f"玩家 {player_id} 不活跃"
        
        before_chips = before.player_chips[player_id]
        after_chips = after.player_chips[player_id]
        
        if action == "fold":
            assert before_chips == after_chips, "弃牌不应该改变筹码"
        elif action == "call":
            call_amount = before.current_bet
            expected_chips = before_chips - call_amount
            assert after_chips == expected_chips, "跟注后筹码不正确"
        elif action == "raise":
            expected_chips = before_chips - amount
            assert after_chips == expected_chips, "加注后筹码不正确"
            assert amount > before.current_bet, "加注金额必须大于当前下注"
        elif action == "check":
            assert before_chips == after_chips, "过牌不应该改变筹码"
            assert before.current_bet == 0, "有下注时不能过牌"
    
    @staticmethod
    def verify_phase_transitions(
        before: GameStateSnapshot,
        after: GameStateSnapshot
    ) -> None:
        """验证阶段转换的合法性"""
        # 定义合法的阶段转换
        valid_transitions = {
            "INIT": ["PRE_FLOP"],
            "PRE_FLOP": ["FLOP", "FINISHED"],  # 可以直接结束（所有人弃牌）
            "FLOP": ["TURN", "FINISHED"],
            "TURN": ["RIVER", "FINISHED"],
            "RIVER": ["SHOWDOWN", "FINISHED"],
            "SHOWDOWN": ["FINISHED"],
            "FINISHED": []  # 结束状态不能转换到其他状态
        }
        
        before_phase = before.current_phase
        after_phase = after.current_phase
        
        # 允许相同阶段（同一阶段内的状态变化）
        if before_phase == after_phase:
            return
        
        # 检查转换是否合法
        allowed_phases = valid_transitions.get(before_phase, [])
        assert after_phase in allowed_phases, \
            f"非法的阶段转换: {before_phase} -> {after_phase}, 允许的转换: {allowed_phases}" 