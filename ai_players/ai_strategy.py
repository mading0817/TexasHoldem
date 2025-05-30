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
    
    def __init__(self, name: str = "保守AI"):
        super().__init__(name, {
            'hand_strength_threshold': 0.3,
            'bluff_frequency': 0.05,
            'pot_odds_threshold': 3.0
        })
    
    def decide_action(self, context: AIDecisionContext) -> PlayerActionInput:
        """保守决策逻辑"""
        snapshot = context.game_snapshot
        player_snapshot = snapshot.get_player_snapshot(context.player_seat_id)
        
        if not player_snapshot:
            return PlayerActionInput(
                seat_id=context.player_seat_id,
                action_type=ActionType.FOLD
            )
        
        required_amount = snapshot.current_bet - player_snapshot.current_bet
        hand_strength = context.hand_strength or 0.3
        
        # 修复决策逻辑：正确理解德州扑克规则
        if required_amount == 0:  # 不需要跟注
            # 检查是否真的没有人下注（可以主动下注）
            if snapshot.current_bet == 0:
                # 确实没有人下注，可以主动下注
                if hand_strength > 0.5:  # 好牌下注
                    bet_amount = min(snapshot.big_blind, player_snapshot.chips)
                    return PlayerActionInput(
                        seat_id=player_snapshot.seat_id,
                        action_type=ActionType.BET,
                        amount=bet_amount
                    )
                else:  # 弱牌过牌
                    return PlayerActionInput(
                        seat_id=player_snapshot.seat_id,
                        action_type=ActionType.CHECK
                    )
            else:
                # 有人下注了，但我们已经跟上了（比如已付盲注），只能过牌
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=ActionType.CHECK
                )
        else:  # 需要跟注
            pot_odds = self._calculate_pot_odds(snapshot, player_snapshot.seat_id)
            
            if hand_strength > 0.6:  # 强牌跟注
                # 修复：CALL行动返回增量金额
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


class AggressiveStrategy(AIStrategy):
    """激进型AI策略 - 偏向于激进决策"""
    
    def __init__(self, name: str = "激进AI"):
        super().__init__(name, {
            'hand_strength_threshold': 0.2,
            'bluff_frequency': 0.3,
            'aggression_factor': 2.5
        })
    
    def decide_action(self, context: AIDecisionContext) -> PlayerActionInput:
        """激进决策逻辑"""
        snapshot = context.game_snapshot
        player_snapshot = snapshot.get_player_snapshot(context.player_seat_id)
        
        if not player_snapshot:
            return PlayerActionInput(
                seat_id=context.player_seat_id,
                action_type=ActionType.FOLD
            )
        
        required_amount = snapshot.current_bet - player_snapshot.current_bet
        hand_strength = context.hand_strength or 0.3
        
        # 激进决策：偏向于加注和下注
        if hand_strength > 0.4 or random.random() < 0.3:  # 中等牌或虚张声势
            return self._aggressive_action(snapshot, player_snapshot, required_amount)
        else:
            return self._conservative_action(snapshot, player_snapshot, required_amount)
    
    def _aggressive_action(self, snapshot: GameStateSnapshot, 
                          player_snapshot, required_amount: int) -> PlayerActionInput:
        """执行激进行动"""
        if required_amount == 0:  # 不需要跟注
            # 修复：正确判断是否可以下注
            if snapshot.current_bet == 0:
                # 确实没有人下注，可以主动下注
                # 合理的下注金额：大盲注的2-4倍
                bet_amount = snapshot.big_blind * random.randint(2, 4)
                bet_amount = min(bet_amount, player_snapshot.chips)
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=ActionType.BET,
                    amount=bet_amount
                )
            else:
                # 有人下注了，但我们已经跟上了（比如已付盲注），只能过牌
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=ActionType.CHECK
                )
        else:  # 跟注或加注
            if player_snapshot.chips > required_amount + snapshot.big_blind:
                # 有足够筹码加注
                min_raise = snapshot.current_bet + snapshot.big_blind
                max_raise = min(
                    snapshot.current_bet * 2,
                    player_snapshot.chips + player_snapshot.current_bet
                )
                if min_raise <= max_raise:
                    raise_amount = random.randint(min_raise, max_raise)
                    return PlayerActionInput(
                        seat_id=player_snapshot.seat_id,
                        action_type=ActionType.RAISE,
                        amount=raise_amount
                    )
            
            # 修复：CALL行动返回增量金额
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
    
    def _conservative_action(self, snapshot: GameStateSnapshot, 
                           player_snapshot, required_amount: int) -> PlayerActionInput:
        """执行保守行动"""
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
            # 修复：只有真正没有人下注时才能下注
            available_actions.append(ActionType.CHECK)
            if snapshot.current_bet == 0:
                available_actions.append(ActionType.BET)
        else:
            available_actions.extend([ActionType.FOLD, ActionType.CALL])
            if required_amount < player_snapshot.chips:
                available_actions.append(ActionType.RAISE)
        
        action_type = random.choice(available_actions)
        
        # 计算行动金额
        amount = None
        if action_type == ActionType.BET:
            # 合理的下注金额：大盲注的1-5倍，但不超过筹码的20%
            max_bet = min(
                snapshot.big_blind * 5,
                player_snapshot.chips // 5,  # 不超过筹码的20%
                player_snapshot.chips
            )
            min_bet = snapshot.big_blind
            if max_bet >= min_bet:
                amount = random.randint(min_bet, max_bet)
            else:
                amount = min_bet
        elif action_type == ActionType.CALL:
            # 修复：CALL行动返回增量金额
            amount = min(required_amount, player_snapshot.chips)
            if amount == player_snapshot.chips:
                action_type = ActionType.ALL_IN
        elif action_type == ActionType.RAISE:
            min_raise = snapshot.current_bet + snapshot.big_blind
            # 合理的加注上限：当前下注线的2倍或大盲注的10倍，取较小值
            max_raise = min(
                snapshot.current_bet * 2,
                snapshot.current_bet + snapshot.big_blind * 5,
                player_snapshot.chips + player_snapshot.current_bet
            )
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