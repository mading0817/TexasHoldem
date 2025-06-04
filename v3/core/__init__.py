"""
V3 Core Module - 纯领域逻辑层

该模块包含德州扑克游戏的核心业务逻辑，遵循DDD原则。
核心模块只能依赖其他核心模块，不能依赖应用层或UI层。

Modules:
    state_machine: 游戏状态机和阶段处理器
    betting: 下注引擎和下注逻辑
    pot: 边池管理和奖金分配
    chips: 筹码账本和筹码操作
    deck: 牌组管理和发牌逻辑
    eval: 牌型评估和手牌比较
    rules: 游戏规则和验证逻辑
    invariant: 数学不变量检查
    events: 领域事件系统
    snapshot: 状态快照管理
"""

__version__ = "3.0.0"
__author__ = "Texas Holdem V3 Team"

# 核心模块访问权限控制
__all__ = [
    # 将在各子模块实现后逐步添加公共接口
] 