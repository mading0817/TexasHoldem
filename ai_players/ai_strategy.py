"""
AI策略接口和基础实现
为不同AI玩家提供可插拔的策略模式
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import random
import time

from app_controller.dto_models import GameStateSnapshot, PlayerActionInput, GameEvent
from core_game_logic.core.enums import ActionType, GamePhase, SeatStatus


@dataclass
class AIDecisionContext:
    """AI决策上下文 - 包含决策所需的所有信息"""
    game_snapshot: GameStateSnapshot
    player_seat_id: int
    hand_strength: Optional[float] = None  # 手牌强度评估 (0-1)
    pot_odds: Optional[float] = None       # 底池赔率
    history_events: List[GameEvent] = None # 历史事件记录
    decision_time_limit: float = 5.0       # 决策时间限制(秒)
    metadata: Dict[str, Any] = None        # 扩展元数据


class AIStrategy(ABC):
    """AI策略抽象基类"""
    
    def __init__(self, name: str, personality_config: Dict[str, Any] = None):
        """
        初始化AI策略
        
        Args:
            name: 策略名称
            personality_config: 性格配置参数
        """
        self.name = name
        self.personality_config = personality_config or {}
        self.decision_history: List[Dict[str, Any]] = []  # 决策历史记录
    
    @abstractmethod
    def decide_action(self, context: AIDecisionContext) -> PlayerActionInput:
        """
        根据上下文决定行动
        
        Args:
            context: 决策上下文
            
        Returns:
            玩家行动输入
        """
        pass
    
    def record_decision(self, context: AIDecisionContext, action: PlayerActionInput, 
                       reasoning: str = "") -> None:
        """记录决策历史"""
        decision_record = {
            'timestamp': time.time(),
            'game_phase': context.game_snapshot.phase.name,
            'hand_strength': context.hand_strength,
            'pot_odds': context.pot_odds,
            'action_type': action.action_type.name,
            'amount': action.amount,
            'reasoning': reasoning
        }
        self.decision_history.append(decision_record)
        
        # 保持历史记录在合理范围内
        if len(self.decision_history) > 100:
            self.decision_history = self.decision_history[-50:]
    
    def get_personality_trait(self, trait_name: str, default_value: Any = None) -> Any:
        """获取性格特征参数"""
        return self.personality_config.get(trait_name, default_value)


class ConservativeStrategy(AIStrategy):
    """保守型AI策略 - 偏向于保守决策"""
    
    def __init__(self, name: str = "保守型AI"):
        super().__init__(name, {
            'aggression': 0.3,      # 攻击性低
            'bluff_frequency': 0.1, # 很少虚张声势
            'risk_tolerance': 0.4   # 风险承受能力低
        })
    
    def decide_action(self, context: AIDecisionContext) -> PlayerActionInput:
        """保守策略决策逻辑"""
        snapshot = context.game_snapshot
        player_snapshot = snapshot.get_player_snapshot(context.player_seat_id)
        
        if not player_snapshot:
            # 异常情况处理 - 找不到玩家信息
            return PlayerActionInput(
                seat_id=context.player_seat_id,
                action_type=ActionType.FOLD
            )
        
        # 计算基础信息
        required_amount = snapshot.current_bet - player_snapshot.current_bet
        hand_strength = context.hand_strength or 0.3  # 默认为中等偏低
        pot_odds = context.pot_odds or 1.0
        
        reasoning = f"保守策略分析: 手牌强度={hand_strength:.2f}, 底池赔率={pot_odds:.2f}"
        
        # 保守策略决策逻辑
        if hand_strength >= 0.8:  # 非常强的牌
            action = self._handle_strong_hand(snapshot, player_snapshot, required_amount)
            reasoning += ", 强牌积极行动"
        elif hand_strength >= 0.6:  # 中等强度
            action = self._handle_medium_hand(snapshot, player_snapshot, required_amount, pot_odds)
            reasoning += ", 中等牌谨慎行动"
        else:  # 弱牌
            action = self._handle_weak_hand(snapshot, player_snapshot, required_amount, pot_odds)
            reasoning += ", 弱牌保守行动"
        
        # 记录决策
        self.record_decision(context, action, reasoning)
        return action
    
    def _handle_strong_hand(self, snapshot: GameStateSnapshot, 
                           player_snapshot, required_amount: int) -> PlayerActionInput:
        """处理强牌的情况"""
        if required_amount == 0:  # 没有人下注
            # 小幅下注引诱对手
            bet_amount = max(snapshot.big_blind, snapshot.pot // 4)
            bet_amount = min(bet_amount, player_snapshot.chips)
            return PlayerActionInput(
                seat_id=player_snapshot.seat_id,
                action_type=ActionType.BET,
                amount=bet_amount
            )
        else:  # 有人下注
            if required_amount >= player_snapshot.chips:
                # All-in情况
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=ActionType.ALL_IN,
                    amount=player_snapshot.chips
                )
            else:
                # 小幅加注
                raise_amount = snapshot.current_bet + snapshot.big_blind
                raise_amount = min(raise_amount, player_snapshot.chips)
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=ActionType.RAISE,
                    amount=raise_amount
                )
    
    def _handle_medium_hand(self, snapshot: GameStateSnapshot, 
                           player_snapshot, required_amount: int, pot_odds: float) -> PlayerActionInput:
        """处理中等牌的情况"""
        if required_amount == 0:  # 过牌
            return PlayerActionInput(
                seat_id=player_snapshot.seat_id,
                action_type=ActionType.CHECK
            )
        else:  # 根据底池赔率决定
            if pot_odds > 3.0:  # 好的赔率
                call_amount = min(required_amount, player_snapshot.chips)
                if call_amount == player_snapshot.chips:
                    action_type = ActionType.ALL_IN
                else:
                    action_type = ActionType.CALL
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=action_type,
                    amount=call_amount
                )
            else:  # 弃牌
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=ActionType.FOLD
                )
    
    def _handle_weak_hand(self, snapshot: GameStateSnapshot, 
                         player_snapshot, required_amount: int, pot_odds: float) -> PlayerActionInput:
        """处理弱牌的情况"""
        if required_amount == 0:  # 免费看牌
            return PlayerActionInput(
                seat_id=player_snapshot.seat_id,
                action_type=ActionType.CHECK
            )
        else:  # 通常弃牌，除非赔率极好
            if pot_odds > 5.0 and required_amount <= player_snapshot.chips * 0.05:
                # 赔率极好且代价很小时跟注
                call_amount = min(required_amount, player_snapshot.chips)
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=ActionType.CALL,
                    amount=call_amount
                )
            else:
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=ActionType.FOLD
                )


class AggressiveStrategy(AIStrategy):
    """激进型AI策略 - 偏向于激进决策"""
    
    def __init__(self, name: str = "激进型AI"):
        super().__init__(name, {
            'aggression': 0.8,      # 攻击性高
            'bluff_frequency': 0.3, # 经常虚张声势
            'risk_tolerance': 0.7   # 风险承受能力高
        })
    
    def decide_action(self, context: AIDecisionContext) -> PlayerActionInput:
        """激进策略决策逻辑"""
        snapshot = context.game_snapshot
        player_snapshot = snapshot.get_player_snapshot(context.player_seat_id)
        
        if not player_snapshot:
            return PlayerActionInput(
                seat_id=context.player_seat_id,
                action_type=ActionType.FOLD
            )
        
        required_amount = snapshot.current_bet - player_snapshot.current_bet
        hand_strength = context.hand_strength or 0.5
        aggression = self.get_personality_trait('aggression', 0.8)
        
        reasoning = f"激进策略分析: 手牌强度={hand_strength:.2f}, 攻击性={aggression}"
        
        # 激进策略倾向于更多的下注和加注
        if hand_strength >= 0.5 or random.random() < aggression * 0.3:  # 虚张声势
            action = self._aggressive_action(snapshot, player_snapshot, required_amount)
            reasoning += ", 激进行动"
        else:
            action = self._conservative_fallback(snapshot, player_snapshot, required_amount)
            reasoning += ", 保守回退"
        
        self.record_decision(context, action, reasoning)
        return action
    
    def _aggressive_action(self, snapshot: GameStateSnapshot, 
                          player_snapshot, required_amount: int) -> PlayerActionInput:
        """执行激进行动"""
        if required_amount == 0:  # 主动下注
            bet_amount = max(snapshot.big_blind * 2, snapshot.pot // 2)
            bet_amount = min(bet_amount, player_snapshot.chips)
            return PlayerActionInput(
                seat_id=player_snapshot.seat_id,
                action_type=ActionType.BET,
                amount=bet_amount
            )
        else:  # 加注或跟注
            if random.random() < 0.6:  # 60%概率加注
                raise_amount = snapshot.current_bet + snapshot.big_blind * 2
                if raise_amount <= player_snapshot.chips:
                    return PlayerActionInput(
                        seat_id=player_snapshot.seat_id,
                        action_type=ActionType.RAISE,
                        amount=raise_amount
                    )
            
            # 跟注
            call_amount = min(required_amount, player_snapshot.chips)
            action_type = ActionType.ALL_IN if call_amount == player_snapshot.chips else ActionType.CALL
            return PlayerActionInput(
                seat_id=player_snapshot.seat_id,
                action_type=action_type,
                amount=call_amount
            )
    
    def _conservative_fallback(self, snapshot: GameStateSnapshot, 
                              player_snapshot, required_amount: int) -> PlayerActionInput:
        """保守回退行动"""
        if required_amount == 0:
            return PlayerActionInput(
                seat_id=player_snapshot.seat_id,
                action_type=ActionType.CHECK
            )
        else:
            return PlayerActionInput(
                seat_id=player_snapshot.seat_id,
                action_type=ActionType.FOLD
            )


class RandomStrategy(AIStrategy):
    """随机策略 - 用于测试和基准对比"""
    
    def __init__(self, name: str = "随机AI"):
        super().__init__(name, {
            'randomness': 1.0
        })
    
    def decide_action(self, context: AIDecisionContext) -> PlayerActionInput:
        """随机决策逻辑"""
        snapshot = context.game_snapshot
        player_snapshot = snapshot.get_player_snapshot(context.player_seat_id)
        
        if not player_snapshot:
            return PlayerActionInput(
                seat_id=context.player_seat_id,
                action_type=ActionType.FOLD
            )
        
        required_amount = snapshot.current_bet - player_snapshot.current_bet
        
        # 随机选择可用行动
        available_actions = []
        
        if required_amount == 0:
            available_actions.extend([ActionType.CHECK, ActionType.BET])
        else:
            available_actions.extend([ActionType.FOLD, ActionType.CALL])
            if required_amount < player_snapshot.chips:
                available_actions.append(ActionType.RAISE)
        
        action_type = random.choice(available_actions)
        
        # 计算行动金额
        amount = None
        if action_type == ActionType.BET:
            amount = random.randint(snapshot.big_blind, min(player_snapshot.chips, snapshot.pot))
        elif action_type == ActionType.CALL:
            amount = min(required_amount, player_snapshot.chips)
            if amount == player_snapshot.chips:
                action_type = ActionType.ALL_IN
        elif action_type == ActionType.RAISE:
            min_raise = snapshot.current_bet + snapshot.big_blind
            max_raise = player_snapshot.chips
            if min_raise <= max_raise:
                amount = random.randint(min_raise, max_raise)
            else:
                # 无法加注，改为跟注
                action_type = ActionType.CALL
                amount = min(required_amount, player_snapshot.chips)
        
        action = PlayerActionInput(
            seat_id=player_snapshot.seat_id,
            action_type=action_type,
            amount=amount
        )
        
        self.record_decision(context, action, "随机决策")
        return action


# 策略工厂
class StrategyFactory:
    """AI策略工厂"""
    
    _strategies = {
        'conservative': ConservativeStrategy,
        'aggressive': AggressiveStrategy,
        'random': RandomStrategy
    }
    
    @classmethod
    def create_strategy(cls, strategy_type: str, name: str = None) -> AIStrategy:
        """
        创建AI策略实例
        
        Args:
            strategy_type: 策略类型 ('conservative', 'aggressive', 'random')
            name: 自定义名称
            
        Returns:
            AI策略实例
        """
        if strategy_type not in cls._strategies:
            raise ValueError(f"未知的策略类型: {strategy_type}. 可用类型: {list(cls._strategies.keys())}")
        
        strategy_class = cls._strategies[strategy_type]
        if name:
            return strategy_class(name)
        else:
            return strategy_class()
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """获取所有可用的策略类型"""
        return list(cls._strategies.keys()) 