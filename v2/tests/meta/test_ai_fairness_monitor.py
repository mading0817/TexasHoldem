"""
AI公平性约束验证系统测试

测试AI公平性监控器的各项功能，确保能正确检测AI作弊行为。
"""

import pytest
import tempfile
import json
import os
from unittest.mock import Mock, patch

from .ai_fairness_monitor import (
    AIFairnessMonitor, AccessType, ViolationType, AccessRecord, 
    FairnessReport, MonitoredGameSnapshot
)
from v2.core import GameSnapshot, Player, Card, Suit, Rank, Phase, SeatStatus, GameState
from v2.ai.simple_ai import SimpleAI


@pytest.mark.ai_fairness
@pytest.mark.fast
class TestAIFairnessMonitor:
    """AI公平性监控器测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.monitor = AIFairnessMonitor()
        self.ai_player_id = 1
        
        # 创建测试用的游戏快照
        self.test_snapshot = self._create_test_snapshot()
        
    def _create_test_snapshot(self) -> GameSnapshot:
        """创建测试用的游戏快照"""
        players = [
            Player(seat_id=1, name="AI_Player", chips=1000),
            Player(seat_id=2, name="Human_Player", chips=1000)
        ]
        
        # 给玩家发底牌
        players[0].set_hole_cards([Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.KING)])
        players[1].set_hole_cards([Card(Suit.DIAMONDS, Rank.QUEEN), Card(Suit.CLUBS, Rank.JACK)])
        
        community_cards = [
            Card(Suit.HEARTS, Rank.TEN),
            Card(Suit.SPADES, Rank.NINE),
            Card(Suit.DIAMONDS, Rank.EIGHT)
        ]
        
        return GameSnapshot(
            phase=Phase.FLOP,
            community_cards=community_cards,
            pot=100,
            current_bet=20,
            last_raiser=None,
            last_raise_amount=0,
            players=players,
            dealer_position=0,
            current_player=1,
            small_blind=5,
            big_blind=10,
            street_index=1,
            events=["Game started", "Cards dealt"]
        )
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_monitor_initialization(self):
        """测试监控器初始化"""
        assert len(self.monitor.access_records) == 0
        assert len(self.monitor.monitored_ais) == 0
        assert 'phase' in self.monitor.legal_attributes
        assert 'community_cards' in self.monitor.legal_attributes
        assert 'seat_id' in self.monitor.player_legal_attributes
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_register_ai(self):
        """测试AI注册"""
        ai_strategy = SimpleAI()
        self.monitor.register_ai(self.ai_player_id, ai_strategy)
        
        assert self.ai_player_id in self.monitor.monitored_ais
        assert self.monitor.monitored_ais[self.ai_player_id] == ai_strategy
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_create_monitored_snapshot(self):
        """测试创建监控快照"""
        monitored_snapshot = self.monitor.create_monitored_snapshot(
            self.test_snapshot, self.ai_player_id
        )
        
        assert isinstance(monitored_snapshot, MonitoredGameSnapshot)
        assert monitored_snapshot._original == self.test_snapshot
        assert monitored_snapshot._ai_player_id == self.ai_player_id
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_legal_access_recording(self):
        """测试合法访问记录"""
        monitored_snapshot = self.monitor.create_monitored_snapshot(
            self.test_snapshot, self.ai_player_id
        )
        
        # 访问合法属性
        _ = monitored_snapshot.phase
        _ = monitored_snapshot.pot
        _ = monitored_snapshot.community_cards
        _ = monitored_snapshot.players
        
        # 检查记录
        assert len(self.monitor.access_records) == 4
        for record in self.monitor.access_records:
            assert record.access_type == AccessType.LEGAL
            assert record.violation_type is None
            assert record.ai_player_id == self.ai_player_id
            
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_illegal_access_detection(self):
        """测试非法访问检测"""
        monitored_snapshot = self.monitor.create_monitored_snapshot(
            self.test_snapshot, self.ai_player_id
        )
        
        # 直接测试监控器的_analyze_access方法来检测非法访问
        # 而不是尝试patch不存在的属性
        access_type, violation_type = self.monitor._analyze_access(
            self.ai_player_id, '_private_data', 'secret'
        )
        
        # 验证检测结果
        assert access_type == AccessType.ILLEGAL
        assert violation_type == ViolationType.PRIVATE_GAME_STATE
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_suspicious_access_detection(self):
        """测试可疑访问检测"""
        monitored_snapshot = self.monitor.create_monitored_snapshot(
            self.test_snapshot, self.ai_player_id
        )
        
        # 直接测试监控器的_analyze_access方法来检测可疑访问
        # 而不是尝试patch不存在的属性
        access_type, violation_type = self.monitor._analyze_access(
            self.ai_player_id, 'unknown_attribute', 'unknown_value'
        )
        
        # 验证检测结果
        assert access_type == AccessType.SUSPICIOUS
        assert violation_type is None
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_analyze_access_legal(self):
        """测试合法访问分析"""
        # 测试基本合法属性
        access_type, violation_type = self.monitor._analyze_access(
            self.ai_player_id, 'phase', Phase.FLOP
        )
        assert access_type == AccessType.LEGAL
        assert violation_type is None
        
        # 测试玩家列表访问
        access_type, violation_type = self.monitor._analyze_access(
            self.ai_player_id, 'players', []
        )
        assert access_type == AccessType.LEGAL
        assert violation_type is None
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_analyze_access_illegal(self):
        """测试非法访问分析"""
        # 测试私有属性访问
        access_type, violation_type = self.monitor._analyze_access(
            self.ai_player_id, '_private_state', 'secret'
        )
        assert access_type == AccessType.ILLEGAL
        assert violation_type == ViolationType.PRIVATE_GAME_STATE
        
        # 测试牌堆访问
        access_type, violation_type = self.monitor._analyze_access(
            self.ai_player_id, 'deck_cards', []
        )
        assert access_type == AccessType.ILLEGAL
        assert violation_type == ViolationType.OPPONENT_HOLE_CARDS
        
        # 测试真正的牌堆操作访问
        access_type, violation_type = self.monitor._analyze_access(
            self.ai_player_id, 'deck_manipulation', []
        )
        assert access_type == AccessType.ILLEGAL
        assert violation_type == ViolationType.DECK_MANIPULATION
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_analyze_access_suspicious(self):
        """测试可疑访问分析"""
        access_type, violation_type = self.monitor._analyze_access(
            self.ai_player_id, 'unknown_attribute', 'unknown_value'
        )
        assert access_type == AccessType.SUSPICIOUS
        assert violation_type is None
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_sanitize_value(self):
        """测试值清理功能"""
        # 测试长列表
        long_list = list(range(20))
        sanitized = self.monitor._sanitize_value(long_list)
        assert "list of 20 items" in sanitized
        
        # 测试长字典
        long_dict = {f"key_{i}": i for i in range(15)}
        sanitized = self.monitor._sanitize_value(long_dict)
        assert "dict with 15 keys" in sanitized
        
        # 测试长字符串
        long_string = "a" * 150
        sanitized = self.monitor._sanitize_value(long_string)
        assert len(sanitized) <= 200
        assert "..." in sanitized
        
        # 测试正常值
        normal_value = "normal"
        sanitized = self.monitor._sanitize_value(normal_value)
        assert sanitized == "normal"
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_monitor_ai_decision(self):
        """测试AI决策监控"""
        ai_strategy = SimpleAI()
        self.monitor.register_ai(self.ai_player_id, ai_strategy)
        
        # 监控AI决策
        decision = self.monitor.monitor_ai_decision(
            ai_strategy, self.test_snapshot, self.ai_player_id
        )
        
        # 检查决策结果
        assert decision is not None
        assert hasattr(decision, 'player_id')
        assert hasattr(decision, 'action_type')
        
        # 检查访问记录
        assert len(self.monitor.access_records) > 0
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_generate_fairness_report(self):
        """测试公平性报告生成"""
        # 先进行一些访问
        monitored_snapshot = self.monitor.create_monitored_snapshot(
            self.test_snapshot, self.ai_player_id
        )
        
        _ = monitored_snapshot.phase  # 合法访问
        _ = monitored_snapshot.pot    # 合法访问
        
        # 生成报告
        report = self.monitor.generate_fairness_report(self.ai_player_id)
        
        assert isinstance(report, FairnessReport)
        assert report.ai_player_id == self.ai_player_id
        assert report.total_accesses == 2
        assert report.legal_accesses == 2
        assert report.illegal_accesses == 0
        assert report.suspicious_accesses == 0
        assert report.is_fair is True
        assert report.fairness_score == 1.0
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_fairness_score_calculation(self):
        """测试公平性分数计算"""
        # 创建包含违规的报告
        report = FairnessReport(
            ai_player_id=self.ai_player_id,
            total_decisions=10,
            total_accesses=100,
            legal_accesses=80,
            illegal_accesses=5,
            suspicious_accesses=15
        )
        
        # 检查分数计算
        assert report.fairness_score < 1.0
        assert report.is_fair is False  # 因为有非法访问
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_detect_cheating_patterns(self):
        """测试作弊模式检测"""
        # 添加一些违规记录
        self.monitor.access_records = [
            AccessRecord(
                timestamp=1.0,
                ai_player_id=self.ai_player_id,
                access_type=AccessType.ILLEGAL,
                violation_type=ViolationType.OPPONENT_HOLE_CARDS,
                accessed_attribute="opponent_cards",
                accessed_value="hidden",
                stack_trace=[]
            ),
            AccessRecord(
                timestamp=2.0,
                ai_player_id=self.ai_player_id,
                access_type=AccessType.ILLEGAL,
                violation_type=ViolationType.UNDEALT_CARDS,
                accessed_attribute="deck_peek",
                accessed_value="hidden",
                stack_trace=[]
            )
        ]
        
        patterns = self.monitor.detect_cheating_patterns(self.ai_player_id)
        
        assert len(patterns) >= 2
        pattern_types = [p['type'] for p in patterns]
        assert 'frequent_opponent_card_access' in pattern_types
        assert 'undealt_card_access' in pattern_types
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_export_fairness_report(self):
        """测试公平性报告导出"""
        # 创建测试报告
        report = FairnessReport(
            ai_player_id=self.ai_player_id,
            total_decisions=5,
            total_accesses=20,
            legal_accesses=18,
            illegal_accesses=1,
            suspicious_accesses=1,
            violations_by_type={ViolationType.PRIVATE_GAME_STATE: 1}
        )
        
        # 导出到临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
            
        try:
            self.monitor.export_fairness_report(report, temp_path)
            
            # 验证文件内容
            with open(temp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            assert data['ai_player_id'] == self.ai_player_id
            assert data['total_accesses'] == 20
            assert data['legal_accesses'] == 18
            assert data['illegal_accesses'] == 1
            assert data['is_fair'] is False
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_clear_records(self):
        """测试清空记录"""
        # 添加一些记录
        self.monitor.access_records = [
            AccessRecord(
                timestamp=1.0,
                ai_player_id=self.ai_player_id,
                access_type=AccessType.LEGAL,
                violation_type=None,
                accessed_attribute="phase",
                accessed_value="FLOP",
                stack_trace=[]
            )
        ]
        
        assert len(self.monitor.access_records) == 1
        
        self.monitor.clear_records()
        assert len(self.monitor.access_records) == 0
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_get_summary_stats(self):
        """测试统计摘要"""
        # 空记录情况
        stats = self.monitor.get_summary_stats()
        assert stats['total_records'] == 0
        
        # 添加一些记录
        self.monitor.access_records = [
            AccessRecord(
                timestamp=1.0,
                ai_player_id=1,
                access_type=AccessType.LEGAL,
                violation_type=None,
                accessed_attribute="phase",
                accessed_value="FLOP",
                stack_trace=[]
            ),
            AccessRecord(
                timestamp=2.0,
                ai_player_id=1,
                access_type=AccessType.ILLEGAL,
                violation_type=ViolationType.PRIVATE_GAME_STATE,
                accessed_attribute="_private",
                accessed_value="secret",
                stack_trace=[]
            ),
            AccessRecord(
                timestamp=3.0,
                ai_player_id=2,
                access_type=AccessType.SUSPICIOUS,
                violation_type=None,
                accessed_attribute="unknown",
                accessed_value="value",
                stack_trace=[]
            )
        ]
        
        stats = self.monitor.get_summary_stats()
        
        assert stats['total_records'] == 3
        assert stats['legal_accesses'] == 1
        assert stats['illegal_accesses'] == 1
        assert stats['suspicious_accesses'] == 1
        assert stats['legal_ratio'] == 1/3
        assert stats['illegal_ratio'] == 1/3
        assert stats['suspicious_ratio'] == 1/3
        assert 1 in stats['monitored_ais']
        assert 2 in stats['monitored_ais']
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_access_record_severity(self):
        """测试访问记录严重程度设置"""
        # 测试关键违规
        record = AccessRecord(
            timestamp=1.0,
            ai_player_id=1,
            access_type=AccessType.ILLEGAL,
            violation_type=ViolationType.OPPONENT_HOLE_CARDS,
            accessed_attribute="opponent_cards",
            accessed_value="hidden",
            stack_trace=[]
        )
        assert record.severity == "critical"
        
        # 测试高级违规
        record = AccessRecord(
            timestamp=1.0,
            ai_player_id=1,
            access_type=AccessType.ILLEGAL,
            violation_type=ViolationType.DECK_MANIPULATION,
            accessed_attribute="deck",
            accessed_value="cards",
            stack_trace=[]
        )
        assert record.severity == "high"
        
        # 测试中级违规
        record = AccessRecord(
            timestamp=1.0,
            ai_player_id=1,
            access_type=AccessType.ILLEGAL,
            violation_type=ViolationType.PRIVATE_GAME_STATE,
            accessed_attribute="_private",
            accessed_value="data",
            stack_trace=[]
        )
        assert record.severity == "medium"
        
        # 测试无违规
        record = AccessRecord(
            timestamp=1.0,
            ai_player_id=1,
            access_type=AccessType.LEGAL,
            violation_type=None,
            accessed_attribute="phase",
            accessed_value="FLOP",
            stack_trace=[]
        )
        assert record.severity == "low"


@pytest.mark.ai_fairness
@pytest.mark.fast
class TestLargeScaleFairnessTest:
    """大规模公平性测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.monitor = AIFairnessMonitor()
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_run_small_scale_fairness_test(self):
        """测试小规模公平性测试（避免测试时间过长）"""
        ai_strategy = SimpleAI()
        
        # 运行小规模测试
        report = self.monitor.run_large_scale_fairness_test(ai_strategy, num_hands=10)
        
        assert isinstance(report, FairnessReport)
        assert report.ai_player_id == 1
        assert report.total_accesses > 0
        assert report.total_decisions > 0
        
        # SimpleAI应该是公平的
        assert report.illegal_accesses == 0
        assert report.is_fair is True
        
    @pytest.mark.slow
    def test_run_large_scale_fairness_test(self):
        """测试大规模公平性测试（标记为慢速测试）"""
        ai_strategy = SimpleAI()
        
        # 运行大规模测试
        report = self.monitor.run_large_scale_fairness_test(ai_strategy, num_hands=100)
        
        assert isinstance(report, FairnessReport)
        assert report.ai_player_id == 1
        assert report.total_accesses > 0
        assert report.total_decisions > 0
        
        # SimpleAI应该是公平的
        assert report.illegal_accesses == 0
        assert report.is_fair is True
        assert report.fairness_score >= 0.8


@pytest.mark.ai_fairness
@pytest.mark.fast
class TestMonitoredGameSnapshot:
    """监控游戏快照测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.monitor = AIFairnessMonitor()
        self.ai_player_id = 1
        
        # 创建测试快照
        players = [Player(seat_id=1, name="AI", chips=1000)]
        self.original_snapshot = GameSnapshot(
            phase=Phase.FLOP,
            community_cards=[],
            pot=100,
            current_bet=20,
            last_raiser=None,
            last_raise_amount=0,
            players=players,
            dealer_position=0,
            current_player=1,
            small_blind=5,
            big_blind=10,
            street_index=1,
            events=[]
        )
        
        self.monitored_snapshot = MonitoredGameSnapshot(
            self.original_snapshot, self.monitor, self.ai_player_id
        )
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_getattr_interception(self):
        """测试属性访问拦截"""
        # 访问属性
        phase = self.monitored_snapshot.phase
        pot = self.monitored_snapshot.pot
        
        # 检查返回值正确
        assert phase == Phase.FLOP
        assert pot == 100
        
        # 检查访问被记录
        assert len(self.monitor.access_records) == 2
        
        # 检查记录内容
        phase_record = next(r for r in self.monitor.access_records if r.accessed_attribute == 'phase')
        assert phase_record.ai_player_id == self.ai_player_id
        assert phase_record.access_type == AccessType.LEGAL
        
    @pytest.mark.ai_fairness
    @pytest.mark.fast
    def test_method_call_interception(self):
        """测试方法调用拦截"""
        # 调用方法
        active_players = self.monitored_snapshot.get_active_players()
        
        # 检查返回值正确
        assert isinstance(active_players, list)
        
        # 检查访问被记录
        method_records = [r for r in self.monitor.access_records if 'get_active_players' in r.accessed_attribute]
        assert len(method_records) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 