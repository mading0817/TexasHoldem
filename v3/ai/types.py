"""
AI模块类型定义

定义AI玩家相关的数据结构和接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Any, Optional, Protocol

from ..core.betting.betting_types import BetAction, BetType
from ..core.snapshot.types import GameStateSnapshot


class AIDecisionType(Enum):
    """AI决策类型"""
    FOLD = auto()
    CHECK = auto()
    CALL = auto()  
    BET = auto()
    RAISE = auto()
    ALL_IN = auto()


@dataclass(frozen=True)
class AIDecision:
    """AI决策结果"""
    decision_type: AIDecisionType
    amount: int = 0
    confidence: float = 1.0
    reasoning: str = ""
    
    def to_bet_action(self, player_id: str) -> BetAction:
        """转换为下注行动"""
        bet_type_map = {
            AIDecisionType.FOLD: BetType.FOLD,
            AIDecisionType.CHECK: BetType.CHECK,
            AIDecisionType.CALL: BetType.CALL,
            AIDecisionType.BET: BetType.RAISE,  # BET映射到RAISE
            AIDecisionType.RAISE: BetType.RAISE,
            AIDecisionType.ALL_IN: BetType.ALL_IN
        }
        
        bet_type = bet_type_map[self.decision_type]
        import time
        return BetAction(player_id, bet_type, self.amount, time.time())


class AIStrategy(Protocol):
    """AI策略接口"""
    
    def decide_action(self, game_state: GameStateSnapshot, player_id: str) -> AIDecision:
        """基于游戏状态决定行动
        
        Args:
            game_state: 当前游戏状态快照
            player_id: 玩家ID
            
        Returns:
            AI决策结果
        """
        ...
    
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        ...


@dataclass
class AIConfig:
    """AI配置基类"""
    name: str = "BaseAI"
    description: str = ""
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class RandomAIConfig(AIConfig):
    """随机AI配置"""
    seed: Optional[int] = None     # 随机种子，用于测试重现
    min_bet_ratio: float = 0.2     # 最小下注比例（相对于底池）
    max_bet_ratio: float = 0.5     # 最大下注比例（相对于底池）
    
    def __post_init__(self):
        super().__post_init__()
        self.name = "RandomAI"
        self.description = "纯随机决策AI，对可执行行动等概率选择"
        
        # 验证参数范围
        if not 0.0 < self.min_bet_ratio <= 5.0:
            raise ValueError("min_bet_ratio必须在0.0-5.0之间")
        if not 0.0 < self.max_bet_ratio <= 5.0:
            raise ValueError("max_bet_ratio必须在0.0-5.0之间")
        if self.min_bet_ratio > self.max_bet_ratio:
            raise ValueError("min_bet_ratio不能大于max_bet_ratio")


@dataclass(frozen=True)
class GameSituation:
    """游戏情况分析"""
    call_cost: int                # 跟注成本
    cost_ratio: float            # 成本比例
    risk_level: str              # 风险等级: "low", "medium", "high"
    reasoning: str               # 推理过程
    pot_odds: float              # 底池赔率
    player_count: int            # 活跃玩家数量
    is_pre_flop: bool           # 是否翻牌前 