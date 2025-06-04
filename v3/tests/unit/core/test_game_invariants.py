"""
游戏不变量检查器单元测试

测试GameInvariants类的功能。
"""

import pytest
import time
from unittest.mock import Mock, patch

from v3.core.invariant.game_invariants import GameInvariants
from v3.core.invariant.types import InvariantType, InvariantCheckResult, InvariantError, InvariantViolation
from v3.core.snapshot.types import (
    GameStateSnapshot, PlayerSnapshot, PotSnapshot, SnapshotMetadata, SnapshotVersion
)
from v3.core.state_machine.types import GamePhase
from v3.core.deck.card import Card, Suit, Rank
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestGameInvariants:
    """测试游戏不变量检查器"""
    
    def create_test_snapshot(self, phase=GamePhase.PRE_FLOP, player_chips=None,
                           player_bets=None, pot_total=0, community_cards=None):
        """创建测试用的游戏状态快照"""
        if player_chips is None:
            player_chips = [1000, 1000]
        if player_bets is None:
            player_bets = [0, 0]
        if community_cards is None:
            community_cards = ()
        
        # 创建玩家快照
        players = []
        for i, (chips, bet) in enumerate(zip(player_chips, player_bets)):
            # 为活跃玩家创建手牌（除了INIT阶段）
            hole_cards = ()
            if phase != GamePhase.INIT:
                hole_cards = (
                    Card(Suit.HEARTS, Rank.ACE),
                    Card(Suit.SPADES, Rank.KING)
                )
            
            player = PlayerSnapshot(
                player_id=f"player_{i+1}",
                name=f"Player {i+1}",
                chips=chips,
                hole_cards=hole_cards,
                position=i,
                is_active=True,
                is_all_in=False,
                current_bet=bet,
                total_bet_this_hand=bet
            )
            players.append(player)
        
        # 创建奖池快照
        pot = PotSnapshot(
            main_pot=pot_total,
            side_pots=(),
            total_pot=pot_total,
            eligible_players=tuple(p.player_id for p in players)
        )
        
        # 创建元数据
        metadata = SnapshotMetadata(
            snapshot_id="test_snapshot",
            version=SnapshotVersion.CURRENT,
            created_at=time.time(),
            game_duration=0.0,
            hand_number=1
        )
        
        return GameStateSnapshot(
            metadata=metadata,
            game_id="test_game",
            phase=phase,
            players=tuple(players),
            pot=pot,
            community_cards=community_cards,
            current_bet=max(player_bets) if player_bets else 0,
            dealer_position=0,
            small_blind_position=0,
            big_blind_position=1,
            small_blind_amount=10,
            big_blind_amount=20,
            recent_transactions=()
        )
    
    def test_create_game_invariants(self):
        """测试创建游戏不变量检查器"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(invariants, "GameInvariants")
        
        # 检查内部检查器
        assert invariants.chip_checker is not None
        assert invariants.betting_checker is not None
        assert invariants.phase_checker is not None
        
        # 检查检查器字典
        assert len(invariants._checkers) == 3
        assert InvariantType.CHIP_CONSERVATION in invariants._checkers
        assert InvariantType.BETTING_RULES in invariants._checkers
        assert InvariantType.PHASE_CONSISTENCY in invariants._checkers
    
    def test_check_all_valid_state(self):
        """测试检查所有不变量 - 有效状态"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            player_chips=[990, 980],
            player_bets=[10, 20],
            pot_total=30
        )
        
        results = invariants.check_all(snapshot)
        
        # 反作弊检查
        for result in results.values():
            CoreUsageChecker.verify_real_objects(result, "InvariantCheckResult")
        
        # 检查结果
        assert len(results) == 3
        assert all(result.is_valid for result in results.values())
        
        # 检查每个不变量类型都有结果
        assert InvariantType.CHIP_CONSERVATION in results
        assert InvariantType.BETTING_RULES in results
        assert InvariantType.PHASE_CONSISTENCY in results
    
    def test_check_all_with_violations(self):
        """测试检查所有不变量 - 有违反的状态"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        
        # 创建有违反的快照（筹码不守恒）
        snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            player_chips=[500, 500],  # 总筹码1000，但初始设置为2000
            player_bets=[10, 20],
            pot_total=30
        )
        
        results = invariants.check_all(snapshot)
        
        # 应该有至少一个检查失败
        assert not all(result.is_valid for result in results.values())
        
        # 筹码守恒检查应该失败
        chip_result = results[InvariantType.CHIP_CONSERVATION]
        assert not chip_result.is_valid
        assert len(chip_result.violations) > 0
    
    def test_check_all_raise_on_violation(self):
        """测试检查所有不变量 - 违反时抛出异常"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        
        # 创建有严重违反的快照
        snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            player_chips=[500, 500],
            player_bets=[10, 20],
            pot_total=30
        )
        
        # 应该抛出异常
        with pytest.raises(InvariantError) as exc_info:
            invariants.check_all(snapshot, raise_on_violation=True)
        
        # 检查异常信息
        assert "严重不变量违反" in str(exc_info.value)
        assert len(exc_info.value.violations) > 0
    
    def test_individual_checkers(self):
        """测试单独的检查器方法"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            player_chips=[990, 980],
            player_bets=[10, 20],
            pot_total=30
        )
        
        # 测试筹码守恒检查
        chip_result = invariants.check_chip_conservation(snapshot)
        CoreUsageChecker.verify_real_objects(chip_result, "InvariantCheckResult")
        assert chip_result.invariant_type == InvariantType.CHIP_CONSERVATION
        assert chip_result.is_valid
        
        # 测试下注规则检查
        betting_result = invariants.check_betting_rules(snapshot)
        CoreUsageChecker.verify_real_objects(betting_result, "InvariantCheckResult")
        assert betting_result.invariant_type == InvariantType.BETTING_RULES
        assert betting_result.is_valid
        
        # 测试阶段一致性检查
        phase_result = invariants.check_phase_consistency(snapshot)
        CoreUsageChecker.verify_real_objects(phase_result, "InvariantCheckResult")
        assert phase_result.invariant_type == InvariantType.PHASE_CONSISTENCY
        assert phase_result.is_valid
    
    def test_is_valid_state(self):
        """测试状态有效性检查"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        
        # 有效状态
        valid_snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            player_chips=[990, 980],
            player_bets=[10, 20],
            pot_total=30
        )
        
        assert invariants.is_valid_state(valid_snapshot) is True
        
        # 无效状态
        invalid_snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            player_chips=[500, 500],
            player_bets=[10, 20],
            pot_total=30
        )
        
        assert invariants.is_valid_state(invalid_snapshot) is False
    
    def test_get_violations(self):
        """测试获取违反记录"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        
        # 创建有违反的快照
        snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            player_chips=[500, 500],
            player_bets=[10, 20],
            pot_total=30
        )
        
        violations = invariants.get_violations(snapshot)
        
        # 应该有违反记录
        assert len(violations) > 0
        
        # 检查违反记录的结构
        for violation in violations:
            CoreUsageChecker.verify_real_objects(violation, "InvariantViolation")
            assert hasattr(violation, 'description')
            assert hasattr(violation, 'severity')
            assert hasattr(violation, 'context')
    
    def test_get_critical_violations(self):
        """测试获取严重违反记录"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        
        # 创建有严重违反的快照
        snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            player_chips=[500, 500],
            player_bets=[10, 20],
            pot_total=30
        )
        
        critical_violations = invariants.get_critical_violations(snapshot)
        
        # 应该有严重违反记录
        assert len(critical_violations) > 0
        
        # 所有违反都应该是严重的
        for violation in critical_violations:
            assert violation.severity == 'CRITICAL'
    
    def test_reset_chip_conservation(self):
        """测试重置筹码守恒检查器"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        
        # 重置为新的初始筹码
        invariants.reset_chip_conservation(3000)
        
        # 创建符合新初始筹码的快照
        snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            player_chips=[1490, 1480],
            player_bets=[10, 20],
            pot_total=30
        )
        
        result = invariants.check_chip_conservation(snapshot)
        assert result.is_valid
    
    def test_get_performance_stats(self):
        """测试获取性能统计信息"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            player_chips=[990, 980],
            player_bets=[10, 20],
            pot_total=30
        )
        
        stats = invariants.get_performance_stats(snapshot)
        
        # 检查统计信息结构
        assert 'total_check_time' in stats
        assert 'individual_times' in stats
        assert 'total_violations' in stats
        assert 'critical_violations' in stats
        assert 'warning_violations' in stats
        assert 'info_violations' in stats
        
        # 检查时间统计
        assert isinstance(stats['total_check_time'], float)
        assert stats['total_check_time'] >= 0
        
        # 检查个别时间统计
        assert len(stats['individual_times']) == 3
        for invariant_name in ['CHIP_CONSERVATION', 'BETTING_RULES', 'PHASE_CONSISTENCY']:
            assert invariant_name in stats['individual_times']
        
        # 检查违反统计
        assert isinstance(stats['total_violations'], int)
        assert isinstance(stats['critical_violations'], int)
        assert isinstance(stats['warning_violations'], int)
        assert isinstance(stats['info_violations'], int)
    
    def test_create_for_game(self):
        """测试为特定游戏创建不变量检查器"""
        snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            player_chips=[1000, 1000],
            player_bets=[0, 0],
            pot_total=0
        )
        
        invariants = GameInvariants.create_for_game(snapshot, min_raise_multiplier=3.0)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(invariants, "GameInvariants")
        
        # 检查初始筹码计算正确
        # 总筹码 = 玩家筹码 + 奖池 = 1000 + 1000 + 0 = 2000
        chip_result = invariants.check_chip_conservation(snapshot)
        assert chip_result.is_valid
        
        # 检查最小加注倍数设置正确
        # 这里我们无法直接验证，但可以通过下注规则检查间接验证
        assert invariants.betting_checker is not None
    
    def test_validate_and_raise_valid_state(self):
        """测试验证并抛出异常 - 有效状态"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            player_chips=[990, 980],
            player_bets=[10, 20],
            pot_total=30
        )
        
        # 有效状态不应该抛出异常
        try:
            invariants.validate_and_raise(snapshot, "测试操作")
        except InvariantError:
            pytest.fail("有效状态不应该抛出异常")
    
    def test_validate_and_raise_invalid_state(self):
        """测试验证并抛出异常 - 无效状态"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        
        # 创建有严重违反的快照
        snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            player_chips=[500, 500],
            player_bets=[10, 20],
            pot_total=30
        )
        
        # 应该抛出异常
        with pytest.raises(InvariantError) as exc_info:
            invariants.validate_and_raise(snapshot, "测试操作")
        
        # 检查异常信息包含上下文
        assert "测试操作" in str(exc_info.value)
        assert "严重不变量违反" in str(exc_info.value)
    
    def test_empty_snapshot_handling(self):
        """测试空快照处理"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        
        # 测试None快照
        results = invariants.check_all(None)
        
        # 所有检查都应该失败
        assert not all(result.is_valid for result in results.values())
        
        # 每个检查器都应该有违反记录
        for result in results.values():
            assert len(result.violations) > 0
    
    def test_edge_case_zero_chips(self):
        """测试边缘情况 - 零筹码"""
        invariants = GameInvariants(initial_total_chips=0, min_raise_multiplier=2.0)
        
        # 创建零筹码快照
        snapshot = self.create_test_snapshot(
            phase=GamePhase.FINISHED,
            player_chips=[0, 0],
            player_bets=[0, 0],
            pot_total=0
        )
        
        # 筹码守恒应该通过
        chip_result = invariants.check_chip_conservation(snapshot)
        assert chip_result.is_valid
    
    def test_multiple_violations_aggregation(self):
        """测试多个违反的聚合"""
        invariants = GameInvariants(initial_total_chips=2000, min_raise_multiplier=2.0)
        
        # 创建有多种违反的快照
        snapshot = self.create_test_snapshot(
            phase=GamePhase.FLOP,  # 翻牌阶段
            player_chips=[500, 500],  # 筹码不守恒
            player_bets=[10, 20],
            pot_total=30,
            community_cards=()  # 翻牌阶段没有公共牌（阶段不一致）
        )
        
        violations = invariants.get_violations(snapshot)
        
        # 应该有多个违反
        assert len(violations) >= 2
        
        # 应该包含不同类型的违反
        violation_types = set()
        for violation in violations:
            if "筹码" in violation.description:
                violation_types.add("chip")
            if "公共牌" in violation.description or "FLOP" in violation.description:
                violation_types.add("phase")
        
        assert len(violation_types) >= 2 