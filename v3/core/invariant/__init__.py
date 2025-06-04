"""
Invariant Module - 数学不变量

该模块实现德州扑克的数学不变量检查，包括：
- 筹码守恒验证
- 游戏状态一致性检查
- 数学约束验证

Classes:
    GameInvariants: 游戏不变量检查器
    ChipConservationChecker: 筹码守恒检查器
    BettingRulesChecker: 下注规则检查器
    PhaseConsistencyChecker: 阶段一致性检查器
    BaseInvariantChecker: 不变量检查器基类
    
Types:
    InvariantType: 不变量类型枚举
    InvariantViolation: 不变量违反记录
    InvariantCheckResult: 不变量检查结果
    InvariantError: 不变量错误异常
"""

from .types import (
    InvariantType,
    InvariantViolation,
    InvariantCheckResult,
    InvariantError
)
from .base_checker import BaseInvariantChecker
from .chip_conservation_checker import ChipConservationChecker
from .betting_rules_checker import BettingRulesChecker
from .phase_consistency_checker import PhaseConsistencyChecker
from .game_invariants import GameInvariants

__all__ = [
    # 主要接口
    'GameInvariants',
    
    # 具体检查器
    'ChipConservationChecker',
    'BettingRulesChecker', 
    'PhaseConsistencyChecker',
    'BaseInvariantChecker',
    
    # 类型定义
    'InvariantType',
    'InvariantViolation',
    'InvariantCheckResult',
    'InvariantError'
] 