"""
Unit tests for game state health checker.

Tests for PLAN #41: 游戏状态健康度检查缺失
"""

import pytest
from unittest.mock import Mock

from v2.core.health_checker import (
    GameStateHealthChecker,
    HealthIssue,
    HealthCheckResult,
    HealthIssueType,
    HealthIssueSeverity
)
from v2.core.enums import Phase, SeatStatus, Suit, Rank
from v2.core.cards import Card
from v2.core.player import Player
from v2.core.state import GameSnapshot


@pytest.mark.unit
@pytest.mark.fast
class TestGameStateHealthChecker:
    """测试游戏状态健康检查器."""
    
    def setup_method(self):
        """每个测试前重置状态."""
        self.checker = GameStateHealthChecker()
    
    def create_test_snapshot(self, **kwargs):
        """创建测试用的游戏状态快照."""
        defaults = {
            'phase': Phase.PRE_FLOP,
            'pot': 0,
            'current_bet': 0,
            'current_player': 0,
            'players': [
                Player(seat_id=0, name="Alice", chips=1000),
                Player(seat_id=1, name="Bob", chips=1000)
            ],
            'community_cards': [],
            'events': [],
            'dealer_position': 0,
            'small_blind': 5,
            'big_blind': 10
        }
        defaults.update(kwargs)
        
        # 创建mock snapshot
        snapshot = Mock(spec=GameSnapshot)
        for key, value in defaults.items():
            setattr(snapshot, key, value)
        
        return snapshot
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_healthy_game_state(self):
        """测试健康的游戏状态."""
        snapshot = self.create_test_snapshot()
        self.checker.set_expected_total_chips(2000)
        
        result = self.checker.check_health(snapshot)
        
        assert result.is_healthy
        assert len(result.issues) == 0
        assert result.summary['total_issues'] == 0
        assert result.summary['critical_issues'] == 0
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_chip_conservation_violation(self):
        """测试筹码守恒违规检测."""
        # 创建筹码不守恒的快照
        players = [
            Player(seat_id=0, name="Alice", chips=900),  # 少了100筹码
            Player(seat_id=1, name="Bob", chips=1000)
        ]
        snapshot = self.create_test_snapshot(players=players, pot=50)  # 总计1950，少了50
        self.checker.set_expected_total_chips(2000)
        
        result = self.checker.check_health(snapshot)
        
        assert not result.is_healthy
        assert len(result.issues) == 1
        assert result.issues[0].issue_type == HealthIssueType.CHIP_CONSERVATION_VIOLATION
        assert result.issues[0].severity == HealthIssueSeverity.CRITICAL
        assert "Chip conservation violated" in result.issues[0].message
        assert result.issues[0].details['expected_total'] == 2000
        assert result.issues[0].details['actual_total'] == 1950
        assert result.issues[0].details['difference'] == -50
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_invalid_player_count_too_few(self):
        """测试玩家数量过少."""
        players = [Player(seat_id=0, name="Alice", chips=1000)]  # 只有1个玩家
        snapshot = self.create_test_snapshot(players=players)
        
        result = self.checker.check_health(snapshot)
        
        assert not result.is_healthy
        issues = [i for i in result.issues if i.issue_type == HealthIssueType.INVALID_PLAYER_COUNT]
        assert len(issues) == 1
        assert issues[0].severity == HealthIssueSeverity.CRITICAL
        assert "Too few players" in issues[0].message
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_invalid_player_count_too_many(self):
        """测试玩家数量过多."""
        players = [Player(seat_id=i, name=f"Player{i}", chips=1000) for i in range(12)]  # 12个玩家
        snapshot = self.create_test_snapshot(players=players)
        
        result = self.checker.check_health(snapshot)
        
        issues = [i for i in result.issues if i.issue_type == HealthIssueType.INVALID_PLAYER_COUNT]
        assert len(issues) == 1
        assert issues[0].severity == HealthIssueSeverity.WARNING
        assert "Too many players" in issues[0].message
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_no_active_players_during_game(self):
        """测试游戏中无活跃玩家."""
        players = [
            Player(seat_id=0, name="Alice", chips=1000),
            Player(seat_id=1, name="Bob", chips=1000)
        ]
        players[0].status = SeatStatus.FOLDED
        players[1].status = SeatStatus.OUT
        snapshot = self.create_test_snapshot(players=players, phase=Phase.FLOP)
        
        result = self.checker.check_health(snapshot)
        
        assert not result.is_healthy
        issues = [i for i in result.issues if i.issue_type == HealthIssueType.INVALID_PLAYER_COUNT]
        assert len(issues) == 1
        assert issues[0].severity == HealthIssueSeverity.CRITICAL
        assert "No active players" in issues[0].message
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_invalid_current_player_index(self):
        """测试无效的当前玩家索引."""
        snapshot = self.create_test_snapshot(current_player=5)  # 索引超出范围
        
        result = self.checker.check_health(snapshot)
        
        assert not result.is_healthy
        issues = [i for i in result.issues if i.issue_type == HealthIssueType.INVALID_CURRENT_PLAYER]
        assert len(issues) == 1
        assert issues[0].severity == HealthIssueSeverity.CRITICAL
        assert "Invalid current player index" in issues[0].message
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_current_player_not_active(self):
        """测试当前玩家非活跃状态."""
        players = [
            Player(seat_id=0, name="Alice", chips=1000),
            Player(seat_id=1, name="Bob", chips=1000)
        ]
        players[0].status = SeatStatus.FOLDED
        snapshot = self.create_test_snapshot(players=players, current_player=0)
        
        result = self.checker.check_health(snapshot)
        
        issues = [i for i in result.issues if i.issue_type == HealthIssueType.INVALID_CURRENT_PLAYER]
        assert len(issues) == 1
        assert issues[0].severity == HealthIssueSeverity.WARNING
        assert "is not active" in issues[0].message
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_negative_bet_amounts(self):
        """测试负数下注金额."""
        players = [
            Player(seat_id=0, name="Alice", chips=1000),
            Player(seat_id=1, name="Bob", chips=1000)
        ]
        players[0].current_bet = -50  # 负数下注
        snapshot = self.create_test_snapshot(players=players)
        
        result = self.checker.check_health(snapshot)
        
        assert not result.is_healthy
        issues = [i for i in result.issues if i.issue_type == HealthIssueType.INVALID_BET_AMOUNTS]
        assert len(issues) == 1
        assert issues[0].severity == HealthIssueSeverity.CRITICAL
        assert "negative bet" in issues[0].message
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_bet_exceeds_available_chips(self):
        """测试下注超过可用筹码."""
        players = [
            Player(seat_id=0, name="Alice", chips=100),
            Player(seat_id=1, name="Bob", chips=1000)
        ]
        players[0].current_bet = 200  # 下注超过筹码
        snapshot = self.create_test_snapshot(players=players)
        
        result = self.checker.check_health(snapshot)
        
        assert not result.is_healthy
        issues = [i for i in result.issues if i.issue_type == HealthIssueType.INVALID_BET_AMOUNTS]
        assert len(issues) == 1
        assert issues[0].severity == HealthIssueSeverity.CRITICAL
        assert "bet exceeds available chips" in issues[0].message
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_negative_current_bet(self):
        """测试负数当前下注."""
        snapshot = self.create_test_snapshot(current_bet=-10)
        
        result = self.checker.check_health(snapshot)
        
        assert not result.is_healthy
        issues = [i for i in result.issues if i.issue_type == HealthIssueType.INVALID_BET_AMOUNTS]
        assert len(issues) == 1
        assert issues[0].severity == HealthIssueSeverity.CRITICAL
        assert "Negative current bet" in issues[0].message
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_invalid_community_cards_count(self):
        """测试无效的公共牌数量."""
        # FLOP阶段应该有3张公共牌，但只有2张
        cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING)
        ]
        snapshot = self.create_test_snapshot(phase=Phase.FLOP, community_cards=cards)
        
        result = self.checker.check_health(snapshot)
        
        issues = [i for i in result.issues if i.issue_type == HealthIssueType.INVALID_COMMUNITY_CARDS]
        assert len(issues) == 1
        assert issues[0].severity == HealthIssueSeverity.WARNING
        assert "Unexpected community card count" in issues[0].message
        assert issues[0].details['expected_count'] == 3
        assert issues[0].details['actual_count'] == 2
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_duplicate_cards_detection(self):
        """测试重复牌检测."""
        # 创建重复的牌
        duplicate_card = Card(Suit.HEARTS, Rank.ACE)
        cards = [duplicate_card, duplicate_card]  # 两张相同的牌
        
        players = [
            Player(seat_id=0, name="Alice", chips=1000),
            Player(seat_id=1, name="Bob", chips=1000)
        ]
        # 给玩家设置手牌（包含重复牌）
        players[0].hole_cards = [duplicate_card]
        
        snapshot = self.create_test_snapshot(
            players=players,
            community_cards=[duplicate_card]
        )
        
        result = self.checker.check_health(snapshot)
        
        assert not result.is_healthy
        issues = [i for i in result.issues if i.issue_type == HealthIssueType.DUPLICATE_CARDS]
        assert len(issues) == 1
        assert issues[0].severity == HealthIssueSeverity.CRITICAL
        assert "Duplicate cards detected" in issues[0].message
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_negative_pot_amount(self):
        """测试负数底池金额."""
        snapshot = self.create_test_snapshot(pot=-100)
        
        result = self.checker.check_health(snapshot)
        
        assert not result.is_healthy
        issues = [i for i in result.issues if i.issue_type == HealthIssueType.INVALID_POT_AMOUNT]
        assert len(issues) == 1
        assert issues[0].severity == HealthIssueSeverity.CRITICAL
        assert "Negative pot amount" in issues[0].message
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_expected_total_chips(self):
        """测试设置期望总筹码."""
        self.checker.set_expected_total_chips(5000)
        assert self.checker.expected_total_chips == 5000
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_health_summary_healthy(self):
        """测试健康状态的摘要."""
        snapshot = self.create_test_snapshot()
        self.checker.set_expected_total_chips(2000)
        
        summary = self.checker.get_health_summary(snapshot)
        
        assert "✅ Game state is healthy" in summary
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_health_summary_with_issues(self):
        """测试有问题状态的摘要."""
        snapshot = self.create_test_snapshot(pot=-50)  # 负数底池
        
        summary = self.checker.get_health_summary(snapshot)
        
        assert "❌ Game state has issues:" in summary
        assert "🔴" in summary  # 严重问题的emoji
        assert "Negative pot amount" in summary
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_multiple_issues_detection(self):
        """测试多个问题的检测."""
        # 创建有多个问题的快照
        players = [Player(seat_id=0, name="Alice", chips=1000)]  # 玩家太少
        snapshot = self.create_test_snapshot(
            players=players,
            pot=-50,  # 负数底池
            current_bet=-10  # 负数当前下注
        )
        
        result = self.checker.check_health(snapshot)
        
        assert not result.is_healthy
        assert len(result.issues) >= 3  # 至少3个问题
        
        # 验证摘要统计
        assert result.summary['total_issues'] >= 3
        assert result.summary['critical_issues'] >= 3
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_chip_conservation_without_expected_total(self):
        """测试未设置期望总筹码时的筹码守恒检查."""
        # 不设置expected_total_chips
        snapshot = self.create_test_snapshot()
        
        result = self.checker.check_health(snapshot)
        
        # 应该没有筹码守恒相关的问题
        chip_issues = [i for i in result.issues if i.issue_type == HealthIssueType.CHIP_CONSERVATION_VIOLATION]
        assert len(chip_issues) == 0
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_health_check_result_structure(self):
        """测试健康检查结果的结构."""
        snapshot = self.create_test_snapshot()
        
        result = self.checker.check_health(snapshot)
        
        # 验证结果结构
        assert isinstance(result, HealthCheckResult)
        assert isinstance(result.is_healthy, bool)
        assert isinstance(result.issues, list)
        assert isinstance(result.summary, dict)
        
        # 验证摘要包含必要字段
        required_fields = [
            'total_issues', 'critical_issues', 'warning_issues', 'info_issues',
            'checked_at_phase', 'total_players', 'active_players'
        ]
        for field in required_fields:
            assert field in result.summary 