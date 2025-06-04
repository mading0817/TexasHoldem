"""
RandomAI - 纯随机决策AI

提供完全随机的决策逻辑，对所有可执行行动等概率选择。
用作基准测试和对照组。
"""

import random
from typing import Optional

from ..types import AIDecision, AIDecisionType, AIStrategy, RandomAIConfig
from ...core.snapshot.types import GameStateSnapshot


class RandomAI:
    """纯随机AI玩家
    
    对所有可执行的行动进行等概率随机选择，不考虑牌力、位置等因素。
    主要用于：
    1. 作为其他AI策略的基准对照组
    2. 测试游戏逻辑的鲁棒性
    3. 提供完全不可预测的对手行为
    """
    
    def __init__(self, config: Optional[RandomAIConfig] = None, query_service=None):
        """初始化RandomAI
        
        Args:
            config: AI配置，如果为None则使用默认配置
            query_service: 查询服务实例，用于获取可用行动
        """
        self.config = config or RandomAIConfig()
        self.query_service = query_service
        
        # 初始化随机数生成器
        if self.config.seed is not None:
            self._random = random.Random(self.config.seed)
        else:
            self._random = random.Random()
    
    def get_strategy_name(self) -> str:
        """获取策略名称
        
        Returns:
            策略名称字符串
        """
        return "RandomAI"
    
    def decide_action(self, game_state: GameStateSnapshot, player_id: str) -> AIDecision:
        """基于游戏状态随机决定行动
        
        Args:
            game_state: 当前游戏状态快照
            player_id: 玩家ID
            
        Returns:
            AI决策结果
        """
        # 如果没有查询服务，使用简化逻辑
        if self.query_service is None:
            return self._decide_action_fallback(game_state, player_id)
        
        # 使用查询服务获取可用行动（遵循CQRS架构）
        available_actions_result = self.query_service.get_available_actions(game_state.game_id, player_id)
        
        if not available_actions_result.success:
            return AIDecision(
                decision_type=AIDecisionType.FOLD,
                amount=0,
                confidence=1.0,
                reasoning=f"获取可用行动失败: {available_actions_result.message}"
            )
        
        available_actions = available_actions_result.data.actions
        
        if not available_actions:
            return AIDecision(
                decision_type=AIDecisionType.FOLD,
                amount=0,
                confidence=1.0,
                reasoning="无可用行动，默认弃牌"
            )
        
        # 转换为AI决策类型并随机选择
        available_ai_types = [self._action_str_to_ai_type(action) for action in available_actions]
        chosen_ai_type = self._random.choice(available_ai_types)
        
        # 计算行动金额
        amount = self._calculate_action_amount(game_state, player_id, chosen_ai_type)
        
        return AIDecision(
            decision_type=chosen_ai_type,
            amount=amount,
            confidence=1.0,
            reasoning=f"随机选择: {chosen_ai_type.name}"
        )
    
    def _action_str_to_ai_type(self, action_str: str) -> AIDecisionType:
        """将字符串行动转换为AI决策类型"""
        type_map = {
            'fold': AIDecisionType.FOLD,
            'check': AIDecisionType.CHECK,
            'call': AIDecisionType.CALL,
            'raise': AIDecisionType.RAISE,
            'all_in': AIDecisionType.ALL_IN
        }
        return type_map.get(action_str, AIDecisionType.FOLD)
    
    def _calculate_action_amount(self, game_state: GameStateSnapshot, player_id: str, ai_type: AIDecisionType) -> int:
        """计算行动金额
        
        Args:
            game_state: 游戏状态
            player_id: 玩家ID
            ai_type: AI决策类型
            
        Returns:
            行动金额
        """
        if ai_type in [AIDecisionType.FOLD, AIDecisionType.CHECK]:
            return 0
        elif ai_type == AIDecisionType.CALL:
            # 使用查询服务获取跟注金额
            if self.query_service:
                # 通过可用行动结果获取跟注金额
                available_actions_result = self.query_service.get_available_actions(game_state.game_id, player_id)
                if available_actions_result.success:
                    return available_actions_result.data.min_bet
            # 回退逻辑
            return self._calculate_call_amount_fallback(game_state, player_id)
        elif ai_type == AIDecisionType.RAISE:
            # 使用查询服务计算随机加注金额
            if self.query_service:
                raise_result = self.query_service.calculate_random_raise_amount(
                    game_state.game_id, player_id,
                    self.config.min_bet_ratio, self.config.max_bet_ratio
                )
                if raise_result.success:
                    return raise_result.data
            # 回退逻辑
            return self._calculate_raise_amount_fallback(game_state, player_id)
        elif ai_type == AIDecisionType.ALL_IN:
            # 获取玩家筹码数
            player = game_state.get_player_by_id(player_id)
            return player.chips if player else 0
        else:
            return 0
    
    def _decide_action_fallback(self, game_state: GameStateSnapshot, player_id: str) -> AIDecision:
        """当没有查询服务时的回退决策逻辑"""
        # 简化的决策逻辑
        actions = ['fold']
        
        player = game_state.get_player_by_id(player_id)
        if not player or not player.is_active:
            return AIDecision(
                decision_type=AIDecisionType.FOLD,
                amount=0,
                confidence=1.0,
                reasoning="玩家不活跃，默认弃牌"
            )
        
        # 基本行动判断
        if game_state.current_bet == 0:
            actions.extend(['check', 'raise'])
        else:
            if player.chips >= game_state.current_bet - player.current_bet:
                actions.append('call')
            if player.chips > game_state.current_bet - player.current_bet + game_state.big_blind_amount:
                actions.append('raise')
        
        if player.chips > 0:
            actions.append('all_in')
        
        chosen_action = self._random.choice(actions)
        ai_type = self._action_str_to_ai_type(chosen_action)
        amount = self._calculate_action_amount_fallback(game_state, player_id, ai_type)
        
        return AIDecision(
            decision_type=ai_type,
            amount=amount,
            confidence=1.0,
            reasoning=f"回退逻辑随机选择: {ai_type.name}"
        )
    
    def _calculate_call_amount_fallback(self, game_state: GameStateSnapshot, player_id: str) -> int:
        """回退的跟注金额计算"""
        player = game_state.get_player_by_id(player_id)
        if not player:
            return 0
        return max(0, game_state.current_bet - player.current_bet)
    
    def _calculate_raise_amount_fallback(self, game_state: GameStateSnapshot, player_id: str) -> int:
        """回退的加注金额计算"""
        player = game_state.get_player_by_id(player_id)
        if not player:
            return 0
        
        pot_size = game_state.pot.total_pot
        min_bet = max(
            int(pot_size * self.config.min_bet_ratio),
            game_state.big_blind_amount,
            game_state.current_bet + game_state.big_blind_amount
        )
        max_bet = min(
            int(pot_size * self.config.max_bet_ratio),
            player.current_bet + player.chips
        )
        
        if min_bet > max_bet:
            min_bet = max_bet
        
        return self._random.randint(min_bet, max_bet) if min_bet < max_bet else min_bet
    
    def _calculate_action_amount_fallback(self, game_state: GameStateSnapshot, player_id: str, ai_type: AIDecisionType) -> int:
        """回退的行动金额计算"""
        if ai_type in [AIDecisionType.FOLD, AIDecisionType.CHECK]:
            return 0
        elif ai_type == AIDecisionType.CALL:
            return self._calculate_call_amount_fallback(game_state, player_id)
        elif ai_type == AIDecisionType.RAISE:
            return self._calculate_raise_amount_fallback(game_state, player_id)
        elif ai_type == AIDecisionType.ALL_IN:
            player = game_state.get_player_by_id(player_id)
            return player.chips if player else 0
        else:
            return 0 