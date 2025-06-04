"""
阶段一致性检查器单元测试

测试阶段一致性不变量检查器的功能。
"""

import pytest
import time
from unittest.mock import Mock

from v3.core.invariant.phase_consistency_checker import PhaseConsistencyChecker
from v3.core.invariant.types import InvariantType, InvariantCheckResult
from v3.core.snapshot.types import (
    GameStateSnapshot, PlayerSnapshot, PotSnapshot, SnapshotMetadata, SnapshotVersion
)
from v3.core.state_machine.types import GamePhase
from v3.core.deck.card import Card, Suit, Rank
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestPhaseConsistencyChecker:
    """测试阶段一致性检查器"""
    
    def create_test_snapshot(self, phase=GamePhase.PRE_FLOP, community_cards=None,
                           player_chips=None, player_bets=None, pot_total=0):
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
    
    def test_create_checker(self):
        """测试创建阶段一致性检查器"""
        checker = PhaseConsistencyChecker()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(checker, "PhaseConsistencyChecker")
        
        assert checker.invariant_type == InvariantType.PHASE_CONSISTENCY
    
    def test_check_valid_preflop_phase(self):
        """测试有效的翻牌前阶段"""
        checker = PhaseConsistencyChecker()
        snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            community_cards=(),  # 翻牌前没有公共牌
            player_chips=[980, 980],
            player_bets=[10, 20],  # 盲注
            pot_total=30
        )
        
        result = checker.check(snapshot)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(result, "InvariantCheckResult")
        
        assert result.is_valid is True
        assert len(result.violations) == 0
        assert result.invariant_type == InvariantType.PHASE_CONSISTENCY
    
    def test_check_valid_flop_phase(self):
        """测试有效的翻牌阶段"""
        checker = PhaseConsistencyChecker()
        
        # 创建3张公共牌
        community_cards = (
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN)
        )
        
        snapshot = self.create_test_snapshot(
            phase=GamePhase.FLOP,
            community_cards=community_cards,
            player_chips=[950, 950],
            player_bets=[50, 50],
            pot_total=100
        )
        
        result = checker.check(snapshot)
        
        assert result.is_valid is True
        assert len(result.violations) == 0
    
    def test_check_valid_turn_phase(self):
        """测试有效的转牌阶段"""
        checker = PhaseConsistencyChecker()
        
        # 创建4张公共牌
        community_cards = (
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK)
        )
        
        snapshot = self.create_test_snapshot(
            phase=GamePhase.TURN,
            community_cards=community_cards,
            player_chips=[900, 900],
            player_bets=[100, 100],
            pot_total=200
        )
        
        result = checker.check(snapshot)
        
        assert result.is_valid is True
        assert len(result.violations) == 0
    
    def test_check_valid_river_phase(self):
        """测试有效的河牌阶段"""
        checker = PhaseConsistencyChecker()
        
        # 创建5张公共牌
        community_cards = (
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK),
            Card(Suit.HEARTS, Rank.TEN)
        )
        
        snapshot = self.create_test_snapshot(
            phase=GamePhase.RIVER,
            community_cards=community_cards,
            player_chips=[850, 850],
            player_bets=[150, 150],
            pot_total=300
        )
        
        result = checker.check(snapshot)
        
        assert result.is_valid is True
        assert len(result.violations) == 0
    
    def test_check_invalid_preflop_with_community_cards(self):
        """测试翻牌前阶段有公共牌的无效情况"""
        checker = PhaseConsistencyChecker()
        
        # 翻牌前不应该有公共牌
        community_cards = (
            Card(Suit.HEARTS, Rank.ACE),
        )
        
        snapshot = self.create_test_snapshot(
            phase=GamePhase.PRE_FLOP,
            community_cards=community_cards,
            player_chips=[980, 980],
            player_bets=[10, 20],
            pot_total=30
        )
        
        result = checker.check(snapshot)
        
        assert result.is_valid is False
        assert len(result.violations) > 0
        
        # 检查违反记录
        violation = result.violations[0]
        assert "PRE_FLOP" in violation.description
        assert "公共牌" in violation.description
        assert violation.severity == "CRITICAL"
    
    def test_check_invalid_flop_card_count(self):
        """测试翻牌阶段公共牌数量错误"""
        checker = PhaseConsistencyChecker()
        
        # 翻牌阶段应该有3张公共牌，这里只有2张
        community_cards = (
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING)
        )
        
        snapshot = self.create_test_snapshot(
            phase=GamePhase.FLOP,
            community_cards=community_cards,
            player_chips=[950, 950],
            player_bets=[50, 50],
            pot_total=100
        )
        
        result = checker.check(snapshot)
        
        assert result.is_valid is False
        assert len(result.violations) > 0
        
        # 检查违反记录
        violation = result.violations[0]
        assert "FLOP" in violation.description
        assert "3张" in violation.description
        assert violation.severity == "CRITICAL"
    
    def test_check_invalid_turn_card_count(self):
        """测试转牌阶段公共牌数量错误"""
        checker = PhaseConsistencyChecker()
        
        # 转牌阶段应该有4张公共牌，这里有5张
        community_cards = (
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK),
            Card(Suit.HEARTS, Rank.TEN)
        )
        
        snapshot = self.create_test_snapshot(
            phase=GamePhase.TURN,
            community_cards=community_cards,
            player_chips=[900, 900],
            player_bets=[100, 100],
            pot_total=200
        )
        
        result = checker.check(snapshot)
        
        assert result.is_valid is False
        assert len(result.violations) > 0
        
        # 检查违反记录
        violation = result.violations[0]
        assert "TURN" in violation.description
        assert "4张" in violation.description
        assert violation.severity == "CRITICAL"
    
    def test_check_invalid_river_card_count(self):
        """测试河牌阶段公共牌数量错误"""
        checker = PhaseConsistencyChecker()
        
        # 河牌阶段应该有5张公共牌，这里只有4张
        community_cards = (
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK)
        )
        
        snapshot = self.create_test_snapshot(
            phase=GamePhase.RIVER,
            community_cards=community_cards,
            player_chips=[850, 850],
            player_bets=[150, 150],
            pot_total=300
        )
        
        result = checker.check(snapshot)
        
        assert result.is_valid is False
        assert len(result.violations) > 0
        
        # 检查违反记录
        violation = result.violations[0]
        assert "RIVER" in violation.description
        assert "5张" in violation.description
        assert violation.severity == "CRITICAL"
    
    def test_check_duplicate_community_cards(self):
        """测试重复的公共牌检查"""
        checker = PhaseConsistencyChecker()
        
        # 创建包含重复公共牌的翻牌阶段快照
        duplicate_cards = (
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.HEARTS, Rank.ACE)  # 重复的红桃A
        )
        
        snapshot = self.create_test_snapshot(
            phase=GamePhase.FLOP,
            community_cards=duplicate_cards,
            player_chips=[950, 950],
            player_bets=[50, 50],
            pot_total=100
        )
        
        result = checker.check(snapshot)
        
        # 应该检测到重复公共牌的违反
        assert result.is_valid is False
        assert len(result.violations) > 0
        
        # 检查违反记录
        violation_descriptions = [v.description for v in result.violations]
        assert any("重复" in desc or "相同" in desc or "牌重复" in desc for desc in violation_descriptions)
        
        # 测试河牌阶段的重复牌
        river_duplicate_cards = (
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK),
            Card(Suit.SPADES, Rank.KING)  # 重复的黑桃K
        )
        
        river_snapshot = self.create_test_snapshot(
            phase=GamePhase.RIVER,
            community_cards=river_duplicate_cards,
            player_chips=[850, 850],
            player_bets=[150, 150],
            pot_total=300
        )
        
        river_result = checker.check(river_snapshot)
        
        # 河牌阶段也应该检测到重复牌
        assert river_result.is_valid is False
        assert len(river_result.violations) > 0
        
        # 验证没有重复牌的正常情况
        normal_cards = (
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK),
            Card(Suit.HEARTS, Rank.TEN)  # 不同的牌
        )
        
        normal_snapshot = self.create_test_snapshot(
            phase=GamePhase.RIVER,
            community_cards=normal_cards,
            player_chips=[850, 850],
            player_bets=[150, 150],
            pot_total=300
        )
        
        normal_result = checker.check(normal_snapshot)
        
        # 正常情况应该通过检查
        assert normal_result.is_valid is True
    
    def test_check_empty_snapshot(self):
        """测试空快照检查"""
        checker = PhaseConsistencyChecker()
        
        result = checker.check(None)
        
        assert result.is_valid is False
        assert len(result.violations) > 0
        
        violation = result.violations[0]
        assert "快照为空" in violation.description
        assert violation.severity == "CRITICAL"
    
    def test_check_init_phase(self):
        """测试初始阶段"""
        checker = PhaseConsistencyChecker()
        snapshot = self.create_test_snapshot(
            phase=GamePhase.INIT,
            community_cards=(),
            player_chips=[1000, 1000],
            player_bets=[0, 0],
            pot_total=0
        )
        
        result = checker.check(snapshot)
        
        # 初始阶段应该是有效的
        assert result.is_valid is True
    
    def test_check_finished_phase(self):
        """测试结束阶段"""
        checker = PhaseConsistencyChecker()
        
        # 结束阶段可以有任意数量的公共牌
        community_cards = (
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK),
            Card(Suit.HEARTS, Rank.TEN)
        )
        
        snapshot = self.create_test_snapshot(
            phase=GamePhase.FINISHED,
            community_cards=community_cards,
            player_chips=[800, 1200],
            player_bets=[0, 0],
            pot_total=0
        )
        
        result = checker.check(snapshot)
        
        # 结束阶段应该是有效的
        assert result.is_valid is True 