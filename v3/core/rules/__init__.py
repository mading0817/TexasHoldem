"""
Rules Module - 游戏规则

该模块实现德州扑克的游戏规则逻辑，包括：
- 游戏规则定义和验证
- 行动合法性检查
- 规则配置管理

Classes:
    GameRules: 游戏规则管理器
    ActionValidator: 行动验证器
    RuleConfiguration: 规则配置
"""

from .types import CorePermissibleActionsData, ActionConstraints
from .action_logic import determine_permissible_actions

__all__ = [
    'CorePermissibleActionsData',
    'ActionConstraints', 
    'determine_permissible_actions'
] 