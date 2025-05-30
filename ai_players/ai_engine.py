"""
AI决策引擎
整合AI策略、手牌评估、事件系统的统一决策接口
"""

import time
import random
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime

from app_controller.dto_models import GameStateSnapshot, PlayerActionInput, GameEvent, GameEventType
from core_game_logic.core.enums import ActionType, GamePhase
from core_game_logic.core.card import Card, Rank

from .ai_strategy import AIStrategy, AIDecisionContext, StrategyFactory
from .event_bus import EventBus, get_global_event_bus


@dataclass
class HandStrengthEvaluator:
    """手牌强度评估器 - 简化版实现"""
    
    @staticmethod
    def evaluate_hand_strength(hole_cards: List[Card], community_cards: List[Card] = None) -> float:
        """
        评估手牌强度
        
        Args:
            hole_cards: 底牌
            community_cards: 公共牌（可选）
            
        Returns:
            手牌强度 (0.0-1.0)
        """
        if not hole_cards or len(hole_cards) != 2:
            return 0.0
        
        card1, card2 = hole_cards
        strength = 0.0
        
        # 基础强度评估
        # 1. 对子评估
        if card1.rank == card2.rank:
            pair_strength = card1.rank.value / 14.0  # 归一化到0-1
            strength += 0.3 + pair_strength * 0.4  # 对子基础分0.3，最高分0.7
        
        # 2. 高牌评估
        high_card_value = max(card1.rank.value, card2.rank.value)
        strength += (high_card_value / 14.0) * 0.25  # 高牌最多贡献0.25分
        
        # 3. 同花潜力
        if card1.suit == card2.suit:
            strength += 0.15
        
        # 4. 连牌潜力
        rank_diff = abs(card1.rank.value - card2.rank.value)
        if rank_diff <= 4:  # 4张牌内的连牌
            strength += (5 - rank_diff) * 0.02  # 越接近加分越多
        
        # 5. 公共牌组合评估（简化版）
        if community_cards:
            strength += HandStrengthEvaluator._evaluate_with_community(
                hole_cards, community_cards
            )
        
        # 6. 添加小幅随机因素模拟不确定性
        strength += random.uniform(-0.05, 0.05)
        
        return max(0.0, min(1.0, strength))
    
    @staticmethod
    def _evaluate_with_community(hole_cards: List[Card], community_cards: List[Card]) -> float:
        """结合公共牌评估额外强度"""
        if not community_cards:
            return 0.0
        
        all_cards = hole_cards + community_cards
        bonus = 0.0
        
        # 简化的组合检测
        ranks = [card.rank for card in all_cards]
        suits = [card.suit for card in all_cards]
        
        # 检测可能的组合
        rank_counts = {}
        for rank in ranks:
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
        
        # 对子/三条/四条检测
        max_count = max(rank_counts.values()) if rank_counts else 0
        if max_count >= 3:
            bonus += 0.2  # 三条或更好
        elif max_count == 2:
            bonus += 0.1  # 一对
        
        # 同花检测
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        max_suit_count = max(suit_counts.values()) if suit_counts else 0
        if max_suit_count >= 4:
            bonus += 0.15  # 同花draw或成同花
        
        return min(bonus, 0.3)  # 限制bonus最大值
    
    @staticmethod
    def calculate_pot_odds(snapshot: GameStateSnapshot, player_seat_id: int) -> float:
        """
        计算底池赔率
        
        Args:
            snapshot: 游戏状态快照
            player_seat_id: 玩家座位ID
            
        Returns:
            底池赔率
        """
        player_snapshot = snapshot.get_player_snapshot(player_seat_id)
        if not player_snapshot:
            return 0.0
        
        required_amount = snapshot.current_bet - player_snapshot.current_bet
        if required_amount <= 0:
            return float('inf')  # 免费看牌
        
        # 计算总底池（当前底池 + 所有玩家当前下注）
        total_pot = snapshot.pot
        for p in snapshot.players:
            total_pot += p.current_bet
        
        return total_pot / required_amount if required_amount > 0 else float('inf')


@dataclass
class AIPlayerProfile:
    """AI玩家配置文件"""
    seat_id: int
    name: str
    strategy_type: str  # 策略类型
    custom_config: Dict[str, Any] = field(default_factory=dict)  # 自定义配置
    thinking_time_range: tuple = (0.5, 2.0)  # 思考时间范围(秒)
    decision_history_limit: int = 50  # 决策历史保留数量


class AIDecisionEngine:
    """AI决策引擎 - 统一的AI决策接口"""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        初始化AI决策引擎
        
        Args:
            event_bus: 事件总线实例，None使用全局实例
        """
        self.event_bus = event_bus or get_global_event_bus()
        self.ai_profiles: Dict[int, AIPlayerProfile] = {}  # 座位ID -> AI配置
        self.ai_strategies: Dict[int, AIStrategy] = {}     # 座位ID -> AI策略实例
        self.hand_evaluator = HandStrengthEvaluator()
        
        # 注册事件处理器
        self._setup_event_handlers()
    
    def register_ai_player(self, profile: AIPlayerProfile) -> None:
        """
        注册AI玩家
        
        Args:
            profile: AI玩家配置文件
        """
        try:
            # 创建策略实例
            strategy = StrategyFactory.create_strategy(
                strategy_type=profile.strategy_type,
                name=profile.name
            )
            
            # 应用自定义配置
            if profile.custom_config:
                strategy.personality_config.update(profile.custom_config)
            
            # 保存配置和策略
            self.ai_profiles[profile.seat_id] = profile
            self.ai_strategies[profile.seat_id] = strategy
            
            # 发布AI注册事件
            event = GameEvent(
                event_type=GameEventType.PLAYER_ACTION,  # 复用现有事件类型
                message=f"AI玩家 {profile.name} (座位{profile.seat_id}) 已注册策略: {profile.strategy_type}",
                affected_seat_ids=[profile.seat_id],
                data={
                    'action': 'ai_registered',
                    'strategy_type': profile.strategy_type,
                    'seat_id': profile.seat_id
                }
            )
            self.event_bus.publish(event)
            
        except Exception as e:
            raise RuntimeError(f"注册AI玩家失败 (座位{profile.seat_id}): {e}")
    
    def unregister_ai_player(self, seat_id: int) -> bool:
        """
        注销AI玩家
        
        Args:
            seat_id: 座位ID
            
        Returns:
            是否成功注销
        """
        if seat_id in self.ai_profiles:
            profile = self.ai_profiles[seat_id]
            del self.ai_profiles[seat_id]
            del self.ai_strategies[seat_id]
            
            # 发布AI注销事件
            event = GameEvent(
                event_type=GameEventType.PLAYER_ACTION,
                message=f"AI玩家 {profile.name} (座位{seat_id}) 已注销",
                affected_seat_ids=[seat_id],
                data={'action': 'ai_unregistered', 'seat_id': seat_id}
            )
            self.event_bus.publish(event)
            return True
        
        return False
    
    def get_ai_decision(self, snapshot: GameStateSnapshot, seat_id: int, 
                       hole_cards: List[Card] = None) -> PlayerActionInput:
        """
        获取AI决策
        
        Args:
            snapshot: 游戏状态快照
            seat_id: AI玩家座位ID
            hole_cards: AI玩家底牌（用于手牌评估）
            
        Returns:
            AI决策的行动输入
        """
        if seat_id not in self.ai_strategies:
            raise ValueError(f"座位{seat_id}没有注册AI策略")
        
        profile = self.ai_profiles[seat_id]
        strategy = self.ai_strategies[seat_id]
        
        # 模拟思考时间
        thinking_time = random.uniform(*profile.thinking_time_range)
        time.sleep(thinking_time)
        
        # 构建决策上下文
        context = self._build_decision_context(snapshot, seat_id, hole_cards)
        
        # 执行策略决策
        try:
            decision_start = time.time()
            action_input = strategy.decide_action(context)
            decision_duration = time.time() - decision_start
            
            # 添加决策元数据
            action_input.metadata.update({
                'strategy_type': profile.strategy_type,
                'thinking_time': thinking_time,
                'decision_duration': decision_duration,
                'hand_strength': context.hand_strength,
                'pot_odds': context.pot_odds,
                'engine_version': '1.0'
            })
            
            # 发布AI决策事件
            self._publish_ai_decision_event(profile, action_input, context)
            
            return action_input
            
        except Exception as e:
            # 决策失败时的回退策略
            fallback_action = self._get_fallback_action(snapshot, seat_id)
            
            # 发布决策失败事件
            error_event = GameEvent(
                event_type=GameEventType.PLAYER_ACTION,
                message=f"AI玩家 {profile.name} 决策失败，使用回退策略: {e}",
                affected_seat_ids=[seat_id],
                data={'action': 'ai_decision_failed', 'error': str(e)}
            )
            self.event_bus.publish(error_event)
            
            return fallback_action
    
    def _build_decision_context(self, snapshot: GameStateSnapshot, seat_id: int, 
                               hole_cards: List[Card] = None) -> AIDecisionContext:
        """构建AI决策上下文"""
        # 评估手牌强度
        hand_strength = None
        if hole_cards:
            # 获取公共牌（需要从字符串转换为Card对象）
            community_cards = []
            # 这里简化处理，在实际实现中需要从snapshot.community_cards解析
            hand_strength = self.hand_evaluator.evaluate_hand_strength(
                hole_cards, community_cards
            )
        
        # 计算底池赔率
        pot_odds = self.hand_evaluator.calculate_pot_odds(snapshot, seat_id)
        
        # 获取历史事件（最近的N个事件）
        history_events = self.event_bus.get_event_history(limit=20)
        
        return AIDecisionContext(
            game_snapshot=snapshot,
            player_seat_id=seat_id,
            hand_strength=hand_strength,
            pot_odds=pot_odds,
            history_events=history_events,
            decision_time_limit=5.0,
            metadata={'engine_timestamp': datetime.now()}
        )
    
    def _get_fallback_action(self, snapshot: GameStateSnapshot, seat_id: int) -> PlayerActionInput:
        """获取回退行动（保守策略）"""
        player_snapshot = snapshot.get_player_snapshot(seat_id)
        if not player_snapshot:
            return PlayerActionInput(seat_id=seat_id, action_type=ActionType.FOLD)
        
        required_amount = snapshot.current_bet - player_snapshot.current_bet
        
        # 保守的回退策略
        if required_amount == 0:
            # 免费看牌
            return PlayerActionInput(seat_id=seat_id, action_type=ActionType.CHECK)
        elif required_amount <= player_snapshot.chips * 0.1:
            # 代价很小时跟注
            # 修复：CALL行动返回增量金额
            call_amount = min(required_amount, player_snapshot.chips)
            action_type = ActionType.ALL_IN if call_amount == player_snapshot.chips else ActionType.CALL
            return PlayerActionInput(seat_id=seat_id, action_type=action_type, amount=call_amount)
        else:
            # 代价太大时弃牌
            return PlayerActionInput(seat_id=seat_id, action_type=ActionType.FOLD)
    
    def _publish_ai_decision_event(self, profile: AIPlayerProfile, 
                                  action_input: PlayerActionInput, context: AIDecisionContext) -> None:
        """发布AI决策事件"""
        event = GameEvent(
            event_type=GameEventType.PLAYER_ACTION,
            message=f"AI玩家 {profile.name} 决策: {action_input.action_type.name}"
                   + (f" {action_input.amount}" if action_input.amount else ""),
            affected_seat_ids=[profile.seat_id],
            data={
                'action': 'ai_decision',
                'seat_id': profile.seat_id,
                'action_type': action_input.action_type.name,
                'amount': action_input.amount,
                'strategy_type': profile.strategy_type,
                'hand_strength': context.hand_strength,
                'pot_odds': context.pot_odds,
                'metadata': action_input.metadata
            }
        )
        self.event_bus.publish(event)
    
    def _setup_event_handlers(self) -> None:
        """设置事件处理器"""
        # 监听阶段转换事件，用于调整AI策略
        self.event_bus.subscribe(
            GameEventType.PHASE_TRANSITION,
            self._handle_phase_transition,
            priority=10
        )
        
        # 监听手牌完成事件，用于清理和统计
        self.event_bus.subscribe(
            GameEventType.HAND_COMPLETE,
            self._handle_hand_complete,
            priority=10
        )
    
    def _handle_phase_transition(self, event: GameEvent) -> None:
        """处理阶段转换事件"""
        # 可以在这里实现阶段特定的策略调整
        # 例如：在翻牌后调整手牌评估权重
        pass
    
    def _handle_hand_complete(self, event: GameEvent) -> None:
        """处理手牌完成事件"""
        # 可以在这里实现手牌结束后的学习或统计
        # 例如：更新AI的决策历史分析
        pass
    
    def get_ai_statistics(self, seat_id: Optional[int] = None) -> Dict[str, Any]:
        """
        获取AI统计信息
        
        Args:
            seat_id: 特定座位ID，None返回所有AI统计
            
        Returns:
            AI统计数据
        """
        if seat_id is not None:
            if seat_id in self.ai_strategies:
                strategy = self.ai_strategies[seat_id]
                profile = self.ai_profiles[seat_id]
                return {
                    'seat_id': seat_id,
                    'name': profile.name,
                    'strategy_type': profile.strategy_type,
                    'decision_count': len(strategy.decision_history),
                    'recent_decisions': strategy.decision_history[-10:] if strategy.decision_history else []
                }
            else:
                return {}
        
        # 返回所有AI统计
        stats = {}
        for seat_id in self.ai_strategies:
            stats[seat_id] = self.get_ai_statistics(seat_id)
        
        return stats
    
    def clear_ai_histories(self) -> None:
        """清空所有AI的决策历史"""
        for strategy in self.ai_strategies.values():
            strategy.decision_history.clear()
    
    def get_registered_ais(self) -> List[Dict[str, Any]]:
        """获取所有注册的AI信息"""
        return [
            {
                'seat_id': profile.seat_id,
                'name': profile.name,
                'strategy_type': profile.strategy_type,
                'thinking_time_range': profile.thinking_time_range
            }
            for profile in self.ai_profiles.values()
        ]


# 便利函数
def create_standard_ai_engine() -> AIDecisionEngine:
    """创建标准配置的AI决策引擎"""
    engine = AIDecisionEngine()
    
    # 可以在这里预配置一些标准的AI玩家
    # 例如：注册不同策略类型的AI
    
    return engine


def setup_demo_ais(engine: AIDecisionEngine, ai_seats: List[int]) -> None:
    """
    为演示设置多个不同类型的AI
    
    Args:
        engine: AI决策引擎
        ai_seats: AI座位列表
    """
    strategies = ['conservative', 'aggressive', 'random']
    
    for i, seat_id in enumerate(ai_seats):
        strategy_type = strategies[i % len(strategies)]
        profile = AIPlayerProfile(
            seat_id=seat_id,
            name=f"AI-{strategy_type}-{seat_id}",
            strategy_type=strategy_type,
            thinking_time_range=(0.3, 1.5)
        )
        engine.register_ai_player(profile) 