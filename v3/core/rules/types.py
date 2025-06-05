"""
核心规则类型定义

定义游戏规则相关的数据结构和类型。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from v3.core.betting.betting_types import BetType
from v3.core.state_machine.types import GamePhase

__all__ = [
    'CorePermissibleActionsData',
    'ActionConstraints',
    'PhaseTransition',
    'CorePhaseLogicData'
]


@dataclass(frozen=True)
class PhaseTransition:
    """阶段转换信息"""
    from_phase: GamePhase
    to_phase: GamePhase
    event_type: Optional[str] = None
    condition: Optional[str] = None


@dataclass(frozen=True)
class CorePhaseLogicData:
    """核心阶段逻辑数据"""
    current_phase: GamePhase
    possible_next_phases: List[GamePhase]
    default_next_phase: Optional[GamePhase]
    valid_transitions: List[PhaseTransition]


@dataclass(frozen=True)
class ActionConstraints:
    """行动约束信息"""
    min_call_amount: int = 0
    min_raise_amount: int = 0
    max_raise_amount: int = 0
    big_blind_amount: int = 0
    is_all_in_available: bool = True
    
    def __post_init__(self):
        """验证约束信息的有效性"""
        if self.min_call_amount < 0:
            raise ValueError("min_call_amount不能为负数")
        if self.min_raise_amount < 0:
            raise ValueError("min_raise_amount不能为负数")
        if self.max_raise_amount < 0:
            raise ValueError("max_raise_amount不能为负数")
        if self.big_blind_amount <= 0:
            raise ValueError("big_blind_amount必须大于0")


@dataclass(frozen=True)
class CorePermissibleActionsData:
    """核心层可用行动数据"""
    player_id: str
    available_bet_types: List[BetType]
    constraints: ActionConstraints
    player_chips: int
    is_player_active: bool
    reasoning: Optional[str] = None
    
    def __post_init__(self):
        """验证可用行动数据的有效性"""
        if not self.player_id:
            raise ValueError("player_id不能为空")
        if not isinstance(self.available_bet_types, list):
            raise ValueError("available_bet_types必须是列表")
        if self.player_chips < 0:
            raise ValueError("player_chips不能为负数")
        
        # 验证BetType的逻辑一致性
        has_fold = BetType.FOLD in self.available_bet_types
        has_check = BetType.CHECK in self.available_bet_types
        has_call = BetType.CALL in self.available_bet_types
        has_raise = BetType.RAISE in self.available_bet_types
        has_all_in = BetType.ALL_IN in self.available_bet_types
        
        # 如果玩家不活跃，应该没有可用行动
        if not self.is_player_active and self.available_bet_types:
            raise ValueError("非活跃玩家不应有可用行动")
        
        # 如果玩家活跃，至少应该能弃牌
        if self.is_player_active and not has_fold:
            raise ValueError("活跃玩家至少应该能够弃牌")
        
        # CHECK和CALL不应同时存在
        if has_check and has_call:
            raise ValueError("CHECK和CALL不应同时存在")
    
    def get_action_types_as_strings(self) -> List[str]:
        """获取行动类型的字符串表示"""
        return [bet_type.name.lower() for bet_type in self.available_bet_types]
    
    def can_check(self) -> bool:
        """判断是否可以过牌"""
        return BetType.CHECK in self.available_bet_types
    
    def can_call(self) -> bool:
        """判断是否可以跟注"""
        return BetType.CALL in self.available_bet_types
    
    def can_raise(self) -> bool:
        """判断是否可以加注"""
        return BetType.RAISE in self.available_bet_types
    
    def can_all_in(self) -> bool:
        """判断是否可以全押"""
        return BetType.ALL_IN in self.available_bet_types 