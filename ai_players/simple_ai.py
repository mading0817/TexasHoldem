"""
简化AI策略 - Phase 5 MVC职责纯化
提供基础规则驱动的可预测AI策略，专注于MVP快速验证
"""

import random
from typing import List, Optional
from dataclasses import dataclass

from app_controller.dto_models import GameStateSnapshot, PlayerActionInput, PlayerSnapshot
from core_game_logic.core.enums import ActionType


@dataclass
class SimpleAIConfig:
    """简化AI配置参数"""
    name: str = "SimpleAI"
    conservativeness: float = 0.8  # 保守程度 (0.0-1.0)
    fold_threshold: float = 0.3    # 弃牌成本阈值
    bet_frequency: float = 0.2     # 下注频率
    raise_frequency: float = 0.1   # 加注频率


class SimpleAIStrategy:
    """
    简化AI策略类
    
    特点：
    - 基础决策树逻辑，避免复杂计算
    - 可预测的行为模式，便于测试和调试
    - 基于筹码比例的简单风险评估
    - 无需手牌强度评估或复杂概率计算
    """
    
    def __init__(self, config: Optional[SimpleAIConfig] = None):
        """
        初始化简化AI策略
        
        Args:
            config: 可选的配置参数，使用默认值如果未提供
        """
        self.config = config or SimpleAIConfig()
        self.decision_count = 0  # 决策计数器，用于调试
    
    def get_decision(self, seat_id: int, snapshot: GameStateSnapshot, 
                    available_actions: List[ActionType]) -> PlayerActionInput:
        """
        获取AI决策
        
        Args:
            seat_id: AI玩家座位号
            snapshot: 当前游戏状态快照
            available_actions: 可用行动列表
        
        Returns:
            PlayerActionInput: AI的决策
        """
        self.decision_count += 1
        
        player = snapshot.get_player_snapshot(seat_id)
        if not player:
            return PlayerActionInput(seat_id=seat_id, action_type=ActionType.FOLD)
        
        # 计算决策上下文
        context = self._analyze_situation(player, snapshot)
        
        # 根据可用行动和上下文做决策
        decision = self._make_decision(player, context, available_actions)
        
        # 添加决策元数据
        decision.metadata = {
            'ai_type': 'simple',
            'decision_number': self.decision_count,
            'cost_ratio': context['cost_ratio'],
            'reasoning': context['reasoning']
        }
        
        return decision
    
    def _analyze_situation(self, player: PlayerSnapshot, snapshot: GameStateSnapshot) -> dict:
        """
        分析当前局面
        
        Returns:
            包含决策相关信息的字典
        """
        # 计算跟注成本
        call_cost = max(0, snapshot.current_bet - player.current_bet)
        
        # 计算成本比例
        if player.chips > 0:
            cost_ratio = call_cost / player.chips
        else:
            cost_ratio = 1.0
        
        # 简单的风险评估
        risk_level = "low"
        reasoning = []
        
        if cost_ratio > self.config.fold_threshold:
            risk_level = "high"
            reasoning.append(f"跟注成本过高({cost_ratio:.1%})")
        elif cost_ratio > 0.1:
            risk_level = "medium"
            reasoning.append(f"跟注成本适中({cost_ratio:.1%})")
        else:
            reasoning.append(f"跟注成本较低({cost_ratio:.1%})")
        
        # 考虑游戏阶段
        if snapshot.phase.name in ['PRE_FLOP']:
            reasoning.append("翻牌前阶段，保守决策")
        elif len(snapshot.community_cards) >= 3:
            reasoning.append("翻牌后阶段，基于成本决策")
        
        return {
            'call_cost': call_cost,
            'cost_ratio': cost_ratio,
            'risk_level': risk_level,
            'reasoning': '; '.join(reasoning)
        }
    
    def _make_decision(self, player: PlayerSnapshot, context: dict, 
                      available_actions: List[ActionType]) -> PlayerActionInput:
        """
        基于上下文做出决策
        """
        seat_id = player.seat_id
        cost_ratio = context['cost_ratio']
        call_cost = context['call_cost']
        
        # 高风险情况：弃牌
        if (ActionType.FOLD in available_actions and 
            cost_ratio > self.config.fold_threshold):
            return PlayerActionInput(seat_id=seat_id, action_type=ActionType.FOLD)
        
        # 低风险情况：过牌优先
        if ActionType.CHECK in available_actions:
            # 基于保守程度决定是否过牌
            if random.random() < self.config.conservativeness:
                return PlayerActionInput(seat_id=seat_id, action_type=ActionType.CHECK)
        
        # 中等风险：跟注
        if (ActionType.CALL in available_actions and 
            cost_ratio <= self.config.fold_threshold):
            return PlayerActionInput(seat_id=seat_id, action_type=ActionType.CALL, 
                                   amount=call_cost)
        
        # 低频率主动下注
        if (ActionType.BET in available_actions and 
            random.random() < self.config.bet_frequency):
            bet_amount = self._calculate_bet_amount(player, context)
            return PlayerActionInput(seat_id=seat_id, action_type=ActionType.BET, 
                                   amount=bet_amount)
        
        # 更低频率加注
        if (ActionType.RAISE in available_actions and 
            random.random() < self.config.raise_frequency):
            raise_amount = self._calculate_raise_amount(player, context)
            if raise_amount <= player.chips:
                return PlayerActionInput(seat_id=seat_id, action_type=ActionType.RAISE, 
                                       amount=raise_amount)
        
        # 默认优先级决策
        return self._default_action(seat_id, available_actions, call_cost)
    
    def _calculate_bet_amount(self, player: PlayerSnapshot, context: dict) -> int:
        """计算下注金额 - 保守策略"""
        # 下注金额为筹码的1/8到1/4
        min_bet = player.chips // 8
        max_bet = player.chips // 4
        return max(1, random.randint(min_bet, max_bet))
    
    def _calculate_raise_amount(self, player: PlayerSnapshot, context: dict) -> int:
        """计算加注金额 - 保守策略"""
        # 加注金额较小，通常是最小加注
        base_raise = context['call_cost'] + 2  # 最小加注
        max_raise = player.chips // 3
        return min(base_raise, max_raise)
    
    def _default_action(self, seat_id: int, available_actions: List[ActionType], 
                       call_cost: int) -> PlayerActionInput:
        """默认行动逻辑"""
        # 按优先级选择默认行动
        for action in [ActionType.CHECK, ActionType.CALL, ActionType.FOLD]:
            if action in available_actions:
                amount = call_cost if action == ActionType.CALL else None
                return PlayerActionInput(seat_id=seat_id, action_type=action, amount=amount)
        
        # 最后兜底：弃牌
        return PlayerActionInput(seat_id=seat_id, action_type=ActionType.FOLD)


def get_simple_ai_decision(seat_id: int, snapshot: GameStateSnapshot, 
                          available_actions: List[ActionType],
                          config: Optional[SimpleAIConfig] = None) -> PlayerActionInput:
    """
    获取简化AI决策的便捷函数
    
    Args:
        seat_id: AI玩家座位号
        snapshot: 游戏状态快照
        available_actions: 可用行动列表
        config: 可选的AI配置
    
    Returns:
        PlayerActionInput: AI决策
    """
    ai = SimpleAIStrategy(config)
    return ai.get_decision(seat_id, snapshot, available_actions)


# 预定义AI配置
CONSERVATIVE_AI = SimpleAIConfig(
    name="ConservativeAI",
    conservativeness=0.9,
    fold_threshold=0.2,
    bet_frequency=0.1,
    raise_frequency=0.05
)

BALANCED_AI = SimpleAIConfig(
    name="BalancedAI", 
    conservativeness=0.7,
    fold_threshold=0.3,
    bet_frequency=0.2,
    raise_frequency=0.1
)

AGGRESSIVE_AI = SimpleAIConfig(
    name="AggressiveAI",
    conservativeness=0.5,
    fold_threshold=0.4,
    bet_frequency=0.3,
    raise_frequency=0.2
) 