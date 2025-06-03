"""数据传输对象定义.

这个模块定义了控制器与UI层之间传输数据的标准格式。
使用Pydantic dataclass确保数据验证和序列化的一致性。
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic.dataclasses import dataclass as pydantic_dataclass
from pydantic import Field, validator

from v2.core import ActionType, Phase, SeatStatus, Card, Suit, Rank


@pydantic_dataclass
class PlayerSnapshot:
    """玩家状态快照.
    
    包含玩家在某个时刻的完整状态信息。
    """
    seat_id: int = Field(..., ge=0, description="座位ID")
    name: str = Field(..., min_length=1, description="玩家名称")
    chips: int = Field(..., ge=0, description="剩余筹码")
    current_bet: int = Field(..., ge=0, description="当前轮下注金额")
    status: SeatStatus = Field(..., description="玩家状态")
    hole_cards: Optional[List[Card]] = Field(None, description="底牌（仅对有权限的玩家可见）")
    is_dealer: bool = Field(False, description="是否为庄家")
    is_small_blind: bool = Field(False, description="是否为小盲")
    is_big_blind: bool = Field(False, description="是否为大盲")


@pydantic_dataclass
class GameStateSnapshot:
    """游戏状态快照.
    
    包含游戏在某个时刻的完整状态信息，用于UI显示。
    """
    phase: Phase = Field(..., description="当前游戏阶段")
    pot: int = Field(..., ge=0, description="底池金额")
    current_bet: int = Field(..., ge=0, description="当前最高下注")
    players: List[PlayerSnapshot] = Field(..., description="玩家列表")
    community_cards: List[Card] = Field(default_factory=list, description="公共牌")
    current_player: Optional[int] = Field(None, description="当前行动玩家座位ID")
    dealer_position: int = Field(..., ge=0, description="庄家位置")
    small_blind: int = Field(..., gt=0, description="小盲金额")
    big_blind: int = Field(..., gt=0, description="大盲金额")
    hand_number: int = Field(..., ge=1, description="手牌编号")
    timestamp: datetime = Field(default_factory=datetime.now, description="快照时间戳")
    
    @validator('current_player')
    def validate_current_player(cls, v, values):
        """验证当前玩家ID是否有效."""
        if v is not None and 'players' in values:
            player_ids = [p.seat_id for p in values['players']]
            if v not in player_ids:
                raise ValueError(f"当前玩家ID {v} 不在玩家列表中")
        return v
    
    @validator('big_blind')
    def validate_blind_relationship(cls, v, values):
        """验证大盲必须大于小盲."""
        if 'small_blind' in values and v <= values['small_blind']:
            raise ValueError("大盲必须大于小盲")
        return v


@pydantic_dataclass
class ActionInput:
    """玩家行动输入.
    
    表示玩家要执行的行动，用于从UI传递到控制器。
    """
    player_id: int = Field(..., ge=0, description="玩家座位ID")
    action_type: ActionType = Field(..., description="行动类型")
    amount: int = Field(0, ge=0, description="行动金额（下注、加注、全押时使用）")
    timestamp: datetime = Field(default_factory=datetime.now, description="行动时间戳")
    
    @validator('amount')
    def validate_amount_for_action(cls, v, values):
        """验证金额与行动类型的匹配性."""
        if 'action_type' in values:
            action_type = values['action_type']
            if action_type in [ActionType.FOLD, ActionType.CHECK]:
                if v != 0:
                    raise ValueError(f"{action_type.value}行动不应包含金额")
            elif action_type in [ActionType.BET, ActionType.RAISE, ActionType.CALL, ActionType.ALL_IN]:
                if v < 0:
                    raise ValueError(f"{action_type.value}行动金额不能为负数")
        return v


@pydantic_dataclass
class ValidationResult:
    """行动验证结果.
    
    包含行动验证的详细信息。
    """
    is_valid: bool = Field(..., description="是否有效")
    error_message: Optional[str] = Field(None, description="错误信息")
    suggested_action: Optional[ActionInput] = Field(None, description="建议的替代行动")
    warnings: List[str] = Field(default_factory=list, description="警告信息")


@pydantic_dataclass
class ActionResult:
    """行动执行结果.
    
    包含行动执行后的状态和结果信息。
    """
    success: bool = Field(..., description="是否执行成功")
    executed_action: Optional[ActionInput] = Field(None, description="实际执行的行动")
    validation_result: ValidationResult = Field(..., description="验证结果")
    new_state: Optional[GameStateSnapshot] = Field(None, description="执行后的新状态")
    events: List[Dict[str, Any]] = Field(default_factory=list, description="触发的事件列表")
    message: Optional[str] = Field(None, description="执行结果消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="执行时间戳")


@pydantic_dataclass
class HandResult:
    """手牌结束结果.
    
    包含一手牌结束后的完整结果信息。
    """
    winner_ids: List[int] = Field(..., description="获胜玩家ID列表")
    pot_amount: int = Field(..., ge=0, description="底池总金额")
    winning_hand_description: str = Field(..., description="获胜牌型描述")
    side_pots: List[Dict[str, Any]] = Field(default_factory=list, description="边池分配信息")
    showdown_hands: Dict[int, Dict[str, Any]] = Field(default_factory=dict, description="摊牌时各玩家的牌型")
    hand_number: int = Field(..., ge=1, description="手牌编号")
    duration_seconds: Optional[float] = Field(None, description="手牌持续时间（秒）")
    total_actions: int = Field(0, ge=0, description="总行动次数")
    timestamp: datetime = Field(default_factory=datetime.now, description="结束时间戳")


@pydantic_dataclass
class GameConfiguration:
    """游戏配置.
    
    包含游戏的基本配置参数。
    """
    num_players: int = Field(..., ge=2, le=10, description="玩家数量")
    initial_chips: int = Field(..., gt=0, description="初始筹码")
    small_blind: int = Field(..., gt=0, description="小盲金额")
    big_blind: int = Field(..., gt=0, description="大盲金额")
    human_seat: int = Field(0, ge=0, description="人类玩家座位")
    ai_difficulty: str = Field("normal", description="AI难度")
    enable_events: bool = Field(True, description="是否启用事件系统")
    
    @validator('big_blind')
    def validate_blind_relationship(cls, v, values):
        """验证大盲必须大于小盲."""
        if 'small_blind' in values and v <= values['small_blind']:
            raise ValueError("大盲必须大于小盲")
        return v
    
    @validator('human_seat')
    def validate_human_seat(cls, v, values):
        """验证人类玩家座位在有效范围内."""
        if 'num_players' in values and v >= values['num_players']:
            raise ValueError("人类玩家座位超出玩家数量范围")
        return v


@pydantic_dataclass
class EventData:
    """事件数据.
    
    包含游戏事件的标准化数据格式。
    """
    event_type: str = Field(..., description="事件类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间戳")
    player_id: Optional[int] = Field(None, description="相关玩家ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="事件数据")
    message: Optional[str] = Field(None, description="事件描述消息")


# 类型别名，用于向后兼容
PlayerData = PlayerSnapshot
GameSnapshot = GameStateSnapshot 