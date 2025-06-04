"""
测试重构后的RandomAI

验证RandomAI正确使用QueryService获取可用行动。
"""

import pytest
from unittest.mock import Mock, MagicMock
from v3.ai.Dummy.random_ai import RandomAI
from v3.ai.types import AIDecisionType, RandomAIConfig
from v3.core.snapshot.types import GameStateSnapshot, PlayerSnapshot, PotSnapshot, SnapshotMetadata, SnapshotVersion
from v3.core.state_machine.types import GamePhase
from v3.core.deck.card import Card
from v3.application.query_service import AvailableActions
from v3.application.types import QueryResult
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker
import time


class TestRandomAIRefactored:
    """测试重构后的RandomAI功能"""
    
    def setup_method(self):
        """设置测试环境"""
        self.config = RandomAIConfig(seed=42)  # 固定种子确保可重现
        self.mock_query_service = Mock()
        self.ai = RandomAI(self.config, self.mock_query_service)
    
    def _create_test_game_state(self, player_id="player1", chips=1000, current_bet=0):
        """创建测试用的游戏状态快照"""
        players = (
            PlayerSnapshot(
                player_id=player_id,
                name="TestPlayer",
                chips=chips,
                hole_cards=(Card.from_str("Ah"), Card.from_str("Kh")),
                position=0,
                is_active=True,
                is_all_in=False,
                current_bet=0,
                total_bet_this_hand=0
            ),
        )
        
        metadata = SnapshotMetadata("test_snapshot", SnapshotVersion.CURRENT, time.time(), 0.0, 1)
        
        return GameStateSnapshot(
            metadata=metadata,
            game_id="test_game",
            phase=GamePhase.PRE_FLOP,
            players=players,
            pot=PotSnapshot(0, (), 0, (player_id,)),
            community_cards=(),
            current_bet=current_bet,
            dealer_position=0,
            small_blind_position=0,
            big_blind_position=0,
            small_blind_amount=10,
            big_blind_amount=20
        )
    
    def test_decide_action_with_query_service_success(self):
        """测试使用QueryService成功获取行动"""
        game_state = self._create_test_game_state()
        
        # 反作弊检测
        CoreUsageChecker.verify_real_objects(self.ai, "RandomAI")
        
        # 模拟QueryService返回可用行动
        available_actions = AvailableActions(
            player_id="player1",
            actions=['fold', 'check', 'raise', 'all_in'],
            min_bet=0,
            max_bet=1000
        )
        self.mock_query_service.get_available_actions.return_value = QueryResult.success_result(available_actions)
        
        # 模拟加注金额计算
        self.mock_query_service.calculate_random_raise_amount.return_value = QueryResult.success_result(100)
        
        # 执行决策
        decision = self.ai.decide_action(game_state, "player1")
        
        # 验证结果
        assert decision.decision_type in [AIDecisionType.FOLD, AIDecisionType.CHECK, AIDecisionType.RAISE, AIDecisionType.ALL_IN]
        assert decision.confidence == 1.0
        assert "随机选择" in decision.reasoning
        
        # 验证调用了QueryService
        self.mock_query_service.get_available_actions.assert_called_once_with("test_game", "player1")
    
    def test_decide_action_with_query_service_failure(self):
        """测试QueryService失败时的处理"""
        game_state = self._create_test_game_state()
        
        # 反作弊检测
        CoreUsageChecker.verify_real_objects(self.ai, "RandomAI")
        
        # 模拟QueryService失败
        self.mock_query_service.get_available_actions.return_value = QueryResult.failure_result(
            "服务不可用", "SERVICE_UNAVAILABLE"
        )
        
        # 执行决策
        decision = self.ai.decide_action(game_state, "player1")
        
        # 验证结果：应该弃牌
        assert decision.decision_type == AIDecisionType.FOLD
        assert decision.amount == 0
        assert "获取可用行动失败" in decision.reasoning
    
    def test_decide_action_without_query_service(self):
        """测试没有QueryService时的回退逻辑"""
        ai_without_service = RandomAI(self.config, None)
        game_state = self._create_test_game_state()
        
        # 反作弊检测
        CoreUsageChecker.verify_real_objects(ai_without_service, "RandomAI")
        
        # 执行决策
        decision = ai_without_service.decide_action(game_state, "player1")
        
        # 验证结果
        assert decision.decision_type in [AIDecisionType.FOLD, AIDecisionType.CHECK, AIDecisionType.RAISE, AIDecisionType.ALL_IN]
        assert decision.confidence == 1.0
        assert "回退逻辑随机选择" in decision.reasoning
    
    def test_action_str_to_ai_type_conversion(self):
        """测试字符串行动到AI类型的转换"""
        # 反作弊检测
        CoreUsageChecker.verify_real_objects(self.ai, "RandomAI")
        
        # 测试各种转换
        assert self.ai._action_str_to_ai_type('fold') == AIDecisionType.FOLD
        assert self.ai._action_str_to_ai_type('check') == AIDecisionType.CHECK
        assert self.ai._action_str_to_ai_type('call') == AIDecisionType.CALL
        assert self.ai._action_str_to_ai_type('raise') == AIDecisionType.RAISE
        assert self.ai._action_str_to_ai_type('all_in') == AIDecisionType.ALL_IN
        
        # 测试未知行动
        assert self.ai._action_str_to_ai_type('unknown') == AIDecisionType.FOLD
    
    def test_calculate_action_amount_with_query_service(self):
        """测试使用QueryService计算行动金额"""
        game_state = self._create_test_game_state()
        
        # 反作弊检测
        CoreUsageChecker.verify_real_objects(self.ai, "RandomAI")
        
        # 测试CALL金额计算
        available_actions = AvailableActions("player1", ['call'], min_bet=50, max_bet=1000)
        self.mock_query_service.get_available_actions.return_value = QueryResult.success_result(available_actions)
        
        call_amount = self.ai._calculate_action_amount(game_state, "player1", AIDecisionType.CALL)
        assert call_amount == 50
        
        # 测试RAISE金额计算
        self.mock_query_service.calculate_random_raise_amount.return_value = QueryResult.success_result(200)
        
        raise_amount = self.ai._calculate_action_amount(game_state, "player1", AIDecisionType.RAISE)
        assert raise_amount == 200
        
        # 测试ALL_IN金额
        all_in_amount = self.ai._calculate_action_amount(game_state, "player1", AIDecisionType.ALL_IN)
        assert all_in_amount == 1000  # 玩家的筹码数
    
    def test_fallback_logic_comprehensive(self):
        """测试回退逻辑的全面性"""
        ai_without_service = RandomAI(self.config, None)
        
        # 反作弊检测
        CoreUsageChecker.verify_real_objects(ai_without_service, "RandomAI")
        
        # 测试无下注情况
        game_state = self._create_test_game_state(current_bet=0)
        decision = ai_without_service.decide_action(game_state, "player1")
        assert decision.decision_type in [AIDecisionType.FOLD, AIDecisionType.CHECK, AIDecisionType.RAISE, AIDecisionType.ALL_IN]
        
        # 测试有下注情况
        game_state = self._create_test_game_state(current_bet=50)
        decision = ai_without_service.decide_action(game_state, "player1")
        assert decision.decision_type in [AIDecisionType.FOLD, AIDecisionType.CALL, AIDecisionType.RAISE, AIDecisionType.ALL_IN]
        
        # 测试筹码不足情况
        game_state = self._create_test_game_state(chips=10, current_bet=50)
        decision = ai_without_service.decide_action(game_state, "player1")
        assert decision.decision_type in [AIDecisionType.FOLD, AIDecisionType.ALL_IN]
    
    def test_config_parameters_usage(self):
        """测试配置参数的使用"""
        config = RandomAIConfig(min_bet_ratio=0.5, max_bet_ratio=1.5, seed=123)
        ai = RandomAI(config, self.mock_query_service)
        
        # 反作弊检测
        CoreUsageChecker.verify_real_objects(ai, "RandomAI")
        
        game_state = self._create_test_game_state()
        
        # 模拟QueryService调用
        available_actions = AvailableActions("player1", ['raise'], min_bet=0, max_bet=1000)
        self.mock_query_service.get_available_actions.return_value = QueryResult.success_result(available_actions)
        
        # 执行决策
        ai.decide_action(game_state, "player1")
        
        # 验证配置参数被传递给QueryService
        self.mock_query_service.calculate_random_raise_amount.assert_called_with(
            "test_game", "player1", 0.5, 1.5
        ) 