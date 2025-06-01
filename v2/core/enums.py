"""
游戏相关枚举定义模块.

包含德州扑克游戏中使用的所有枚举类型，如花色、点数、牌型、行动类型等.
"""

from enum import Enum, IntEnum
from typing import List
from dataclasses import dataclass
from typing import Optional


class Suit(Enum):
    """
    扑克牌花色枚举.
    
    定义四种标准扑克牌花色，使用Unicode符号表示.
    """

    HEARTS = "♥"      # 红桃
    DIAMONDS = "♦"    # 方块
    CLUBS = "♣"       # 梅花
    SPADES = "♠"      # 黑桃


class Rank(IntEnum):
    """
    扑克牌点数枚举.
    
    定义13种扑克牌点数，数值越大表示点数越大.
    在德州扑克中，A可以作为最大或最小的牌.
    """

    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


class HandRank(IntEnum):
    """
    德州扑克牌型枚举.
    
    定义所有可能的牌型，数值越大表示牌型越强.
    包含皇家同花顺在内的10种标准牌型.
    """

    HIGH_CARD = 1          # 高牌
    ONE_PAIR = 2           # 一对
    TWO_PAIR = 3           # 两对
    THREE_OF_A_KIND = 4    # 三条
    STRAIGHT = 5           # 顺子
    FLUSH = 6              # 同花
    FULL_HOUSE = 7         # 葫芦
    FOUR_OF_A_KIND = 8     # 四条
    STRAIGHT_FLUSH = 9     # 同花顺
    ROYAL_FLUSH = 10       # 皇家同花顺


class ActionType(Enum):
    """
    玩家行动类型枚举.
    
    定义德州扑克中玩家可以执行的所有行动类型.
    """

    FOLD = "fold"          # 弃牌
    CHECK = "check"        # 过牌
    CALL = "call"          # 跟注
    BET = "bet"            # 下注
    RAISE = "raise"        # 加注
    ALL_IN = "all_in"      # 全押


class Phase(Enum):
    """
    游戏阶段枚举.
    
    定义德州扑克一手牌的各个阶段.
    """

    PRE_FLOP = "pre_flop"  # 翻牌前
    FLOP = "flop"          # 翻牌
    TURN = "turn"          # 转牌
    RIVER = "river"        # 河牌
    SHOWDOWN = "showdown"  # 摊牌


class SeatStatus(Enum):
    """
    座位状态枚举.
    
    定义玩家在游戏中的状态.
    """

    ACTIVE = "active"          # 活跃状态，可以行动
    FOLDED = "folded"          # 已弃牌
    ALL_IN = "all_in"          # 全押状态
    OUT = "out"                # 已出局（筹码为0）
    SITTING_OUT = "sitting_out"  # 暂离状态


class GameEventType(Enum):
    """
    游戏事件类型枚举.
    
    定义游戏过程中可能发生的各种事件类型，用于日志记录和事件处理.
    """

    HAND_STARTED = "hand_started"      # 新手牌开始
    CARDS_DEALT = "cards_dealt"        # 发牌
    PLAYER_ACTION = "player_action"    # 玩家行动
    PHASE_CHANGED = "phase_changed"    # 阶段变更
    POT_AWARDED = "pot_awarded"        # 底池奖励
    HAND_ENDED = "hand_ended"          # 手牌结束
    GAME_ENDED = "game_ended"          # 游戏结束


class ValidationResult(Enum):
    """
    行动验证结果枚举.
    
    定义行动验证的各种可能结果.
    """

    VALID = "valid"                        # 有效行动
    INVALID_AMOUNT = "invalid_amount"      # 无效金额
    INSUFFICIENT_CHIPS = "insufficient_chips"  # 筹码不足
    OUT_OF_TURN = "out_of_turn"            # 不轮到该玩家
    INVALID_ACTION = "invalid_action"      # 无效行动
    GAME_NOT_ACTIVE = "game_not_active"    # 游戏未激活


@dataclass(frozen=True)
class ValidationResultData:
    """
    行动验证结果数据.
    
    包含验证是否通过、错误信息和建议行动等信息.
    """

    is_valid: bool
    error_message: Optional[str] = None
    suggested_action: Optional['Action'] = None


@dataclass(frozen=True)
class Action:
    """
    玩家行动数据类.
    
    表示玩家的一个具体行动，包含行动类型和相关参数.
    
    Attributes:
        action_type: 行动类型
        amount: 行动涉及的筹码数量（下注、加注时使用）
        player_id: 执行行动的玩家ID
        
    Examples:
        >>> Action(ActionType.BET, 100, 0)  # 玩家0下注100
        >>> Action(ActionType.FOLD, 0, 1)   # 玩家1弃牌
        >>> Action(ActionType.CALL, 50, 2)  # 玩家2跟注50
    """

    action_type: ActionType
    amount: int = 0
    player_id: int = 0
    
    def __post_init__(self):
        """验证行动数据的有效性."""
        if self.amount < 0:
            raise ValueError(f"行动金额不能为负数: {self.amount}")
        
        # 某些行动类型不应该有金额
        if self.action_type in [ActionType.FOLD, ActionType.CHECK] and self.amount != 0:
            raise ValueError(f"{self.action_type.value}行动不应该有金额")


@dataclass(frozen=True)
class ValidatedAction:
    """
    验证后的行动数据类.
    
    包含原始行动、验证结果和可能的转换后行动.
    用于行动验证器的输出结果.
    
    Attributes:
        original_action: 原始行动
        final_action: 最终执行的行动（可能经过转换）
        validation_result: 验证结果
        was_converted: 是否进行了行动转换
        conversion_reason: 转换原因说明
    """

    original_action: Action
    final_action: Action
    validation_result: ValidationResultData
    was_converted: bool = False
    conversion_reason: Optional[str] = None


# Utility functions for enums
def get_all_suits() -> List[Suit]:
    """Get all card suits.
    
    Returns:
        List of all Suit enum values.
    """
    return list(Suit)


def get_all_ranks() -> List[Rank]:
    """Get all card ranks.
    
    Returns:
        List of all Rank enum values.
    """
    return list(Rank)


def get_valid_actions() -> List[ActionType]:
    """Get all valid player actions.
    
    Returns:
        List of all ActionType enum values.
    """
    return list(ActionType) 