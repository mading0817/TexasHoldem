"""
RandomAI单元测试

测试纯随机AI的决策逻辑，确保行为符合游戏规则且真正随机。
"""

import pytest
import random
from collections import Counter
from typing import List

from v3.ai.Dummy.random_ai import RandomAI
from v3.ai.types import AIDecision, AIDecisionType, RandomAIConfig
from v3.core.snapshot.types import GameStateSnapshot, PlayerSnapshot, PotSnapshot, SnapshotMetadata, SnapshotVersion
from v3.core.betting.betting_types import BetType
from v3.core.state_machine.types import GamePhase
from v3.core.deck.card import Card
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker
import time


class TestRandomAI:
    """RandomAI测试类"""
    
    def setup_method(self):
        """测试前置设置"""
        self.config = RandomAIConfig(seed=42)  # 固定种子用于测试
        self.ai = RandomAI(self.config)
        
        # 反作弊检查 - 确保使用真实对象
        CoreUsageChecker.verify_real_objects(self.ai, "RandomAI")
        CoreUsageChecker.verify_real_objects(self.config, "RandomAIConfig")
    
    def test_random_ai_initialization(self):
        """测试RandomAI初始化"""
        # 测试默认配置
        default_ai = RandomAI()
        CoreUsageChecker.verify_real_objects(default_ai, "RandomAI")
        assert default_ai.config.name == "RandomAI"
        assert default_ai.config.description == "纯随机决策AI，对可执行行动等概率选择"
        
        # 测试自定义配置
        custom_config = RandomAIConfig(
            seed=123,
            min_bet_ratio=0.2,
            max_bet_ratio=0.8
        )
        custom_ai = RandomAI(custom_config)
        CoreUsageChecker.verify_real_objects(custom_ai, "RandomAI")
        CoreUsageChecker.verify_real_objects(custom_config, "RandomAIConfig")
        assert custom_ai.config.seed == 123
        assert custom_ai.config.min_bet_ratio == 0.2
        assert custom_ai.config.max_bet_ratio == 0.8
    
    def test_get_strategy_name(self):
        """测试策略名称获取"""
        assert self.ai.get_strategy_name() == "RandomAI"
    
    def test_decide_action_with_valid_actions(self):
        """测试在有效行动范围内的决策"""
        # 创建测试用的游戏状态
        game_state = self._create_test_game_state()
        player_id = "player1"
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(game_state, "GameStateSnapshot")
        
        # 执行决策
        decision = self.ai.decide_action(game_state, player_id)
        
        # 验证决策结果
        CoreUsageChecker.verify_real_objects(decision, "AIDecision")
        assert isinstance(decision, AIDecision)
        assert decision.decision_type in AIDecisionType
        assert decision.confidence == 1.0  # 随机AI总是100%确信
        assert "随机选择" in decision.reasoning
    
    def test_decision_randomness_distribution(self):
        """测试决策的随机性分布"""
        game_state = self._create_test_game_state()
        player_id = "player1"
        
        # 收集多次决策结果
        decisions = []
        for _ in range(1000):
            decision = self.ai.decide_action(game_state, player_id)
            decisions.append(decision.decision_type)
        
        # 统计分布
        distribution = Counter(decisions)
        
        # 验证所有可能的决策类型都出现了
        expected_types = {AIDecisionType.FOLD, AIDecisionType.CALL, AIDecisionType.RAISE, AIDecisionType.ALL_IN}
        assert set(distribution.keys()) == expected_types
        
        # 验证分布相对均匀（允许一定的随机波动）
        total_decisions = len(decisions)
        for decision_type, count in distribution.items():
            ratio = count / total_decisions
            # 期望每种决策约占1/4，允许±10%的波动
            assert 0.15 <= ratio <= 0.35, f"{decision_type}的比例{ratio}超出预期范围"
    
    def test_bet_amount_randomness(self):
        """测试下注金额的随机性"""
        game_state = self._create_test_game_state()
        player_id = "player1"
        
        # 收集多次RAISE决策的下注金额
        bet_amounts = []
        attempts = 0
        while len(bet_amounts) < 100 and attempts < 2000:
            decision = self.ai.decide_action(game_state, player_id)
            if decision.decision_type == AIDecisionType.RAISE:
                bet_amounts.append(decision.amount)
            attempts += 1
        
        # 验证收集到足够的样本
        assert len(bet_amounts) >= 50, "未收集到足够的RAISE决策样本"
        
        # 验证金额在合理范围内
        pot_size = game_state.pot.total_pot
        min_expected = int(pot_size * self.config.min_bet_ratio)
        max_expected = int(pot_size * self.config.max_bet_ratio)
        
        for amount in bet_amounts:
            assert min_expected <= amount <= max_expected, f"下注金额{amount}超出预期范围[{min_expected}, {max_expected}]"
        
        # 验证金额分布的随机性（不应该都是同一个值）
        unique_amounts = set(bet_amounts)
        assert len(unique_amounts) > 1, "下注金额缺乏随机性"
    
    def test_seed_reproducibility(self):
        """测试随机种子的可重现性"""
        # 使用相同种子创建两个AI
        config1 = RandomAIConfig(seed=999)
        config2 = RandomAIConfig(seed=999)
        ai1 = RandomAI(config1)
        ai2 = RandomAI(config2)
        
        game_state = self._create_test_game_state()
        player_id = "player1"
        
        # 生成决策序列
        decisions1 = []
        decisions2 = []
        
        for _ in range(50):
            decision1 = ai1.decide_action(game_state, player_id)
            decision2 = ai2.decide_action(game_state, player_id)
            decisions1.append((decision1.decision_type, decision1.amount))
            decisions2.append((decision2.decision_type, decision2.amount))
        
        # 验证序列完全相同
        assert decisions1 == decisions2, "相同种子应该产生相同的决策序列"
    
    def test_different_seeds_produce_different_results(self):
        """测试不同种子产生不同结果"""
        config1 = RandomAIConfig(seed=111)
        config2 = RandomAIConfig(seed=222)
        ai1 = RandomAI(config1)
        ai2 = RandomAI(config2)
        
        game_state = self._create_test_game_state()
        player_id = "player1"
        
        # 生成决策序列
        decisions1 = []
        decisions2 = []
        
        for _ in range(100):
            decision1 = ai1.decide_action(game_state, player_id)
            decision2 = ai2.decide_action(game_state, player_id)
            decisions1.append((decision1.decision_type, decision1.amount))
            decisions2.append((decision2.decision_type, decision2.amount))
        
        # 验证序列不完全相同
        assert decisions1 != decisions2, "不同种子应该产生不同的决策序列"
    
    def test_config_validation(self):
        """测试配置参数验证"""
        # 测试无效的min_bet_ratio
        with pytest.raises(ValueError, match="min_bet_ratio必须在0.0-1.0之间"):
            RandomAIConfig(min_bet_ratio=0.0)
        
        with pytest.raises(ValueError, match="min_bet_ratio必须在0.0-1.0之间"):
            RandomAIConfig(min_bet_ratio=1.5)
        
        # 测试无效的max_bet_ratio
        with pytest.raises(ValueError, match="max_bet_ratio必须在0.0-1.0之间"):
            RandomAIConfig(max_bet_ratio=0.0)
        
        with pytest.raises(ValueError, match="max_bet_ratio必须在0.0-1.0之间"):
            RandomAIConfig(max_bet_ratio=1.5)
        
        # 测试min > max的情况
        with pytest.raises(ValueError, match="min_bet_ratio不能大于max_bet_ratio"):
            RandomAIConfig(min_bet_ratio=0.8, max_bet_ratio=0.5)
    
    def test_decision_to_bet_action_conversion(self):
        """测试AI决策转换为下注行动"""
        game_state = self._create_test_game_state()
        player_id = "player1"
        
        decision = self.ai.decide_action(game_state, player_id)
        bet_action = decision.to_bet_action(player_id)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(bet_action, "BetAction")
        
        # 验证转换正确性
        assert bet_action.player_id == player_id
        assert bet_action.amount == decision.amount
        
        # 验证决策类型映射
        type_mapping = {
            AIDecisionType.FOLD: BetType.FOLD,
            AIDecisionType.CHECK: BetType.CHECK,
            AIDecisionType.CALL: BetType.CALL,
            AIDecisionType.BET: BetType.RAISE,  # BET映射到RAISE
            AIDecisionType.RAISE: BetType.RAISE,
            AIDecisionType.ALL_IN: BetType.ALL_IN
        }
        expected_bet_type = type_mapping[decision.decision_type]
        assert bet_action.bet_type == expected_bet_type
    
    def _create_test_game_state(self) -> GameStateSnapshot:
        """创建测试用的游戏状态快照"""
        # 创建玩家快照
        players = (
            PlayerSnapshot(
                player_id="player1",
                name="Player 1",
                chips=1000,
                hole_cards=(Card.from_str("Ah"), Card.from_str("Kh")),
                position=0,
                is_active=True,
                is_all_in=False,
                current_bet=50,
                total_bet_this_hand=50
            ),
            PlayerSnapshot(
                player_id="player2", 
                name="Player 2",
                chips=800,
                hole_cards=(Card.from_str("Qc"), Card.from_str("Jc")),
                position=1,
                is_active=True,
                is_all_in=False,
                current_bet=50,
                total_bet_this_hand=50
            )
        )
        
        # 创建奖池快照
        pot = PotSnapshot(
            main_pot=100,
            side_pots=(),
            total_pot=100,
            eligible_players=("player1", "player2")
        )
        
        # 创建元数据
        timestamp = time.time()
        metadata = SnapshotMetadata(
            snapshot_id="test_snapshot",
            version=SnapshotVersion.CURRENT,
            created_at=timestamp,
            game_duration=0.0,
            hand_number=1,
            description="测试快照"
        )
        
        # 创建游戏状态快照
        game_state = GameStateSnapshot(
            metadata=metadata,
            game_id="test_game",
            phase=GamePhase.PRE_FLOP,
            players=players,
            pot=pot,
            community_cards=(),
            current_bet=50,
            dealer_position=0,
            small_blind_position=0,
            big_blind_position=1,
            active_player_position=0,
            small_blind_amount=25,
            big_blind_amount=50
        )
        
        return game_state 