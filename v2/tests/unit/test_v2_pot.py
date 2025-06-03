"""
v2边池管理器单元测试。

测试SidePot数据结构、PotManager类和边池计算算法的正确性。
包含三人不同额全押用例和各种边界情况。
"""

import pytest
from v2.core import (
    SidePot, PotManager, Player, SeatStatus,
    calculate_side_pots, get_pot_distribution_summary
)


@pytest.mark.unit
@pytest.mark.fast
class TestSidePot:
    """测试SidePot数据结构。"""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_valid_side_pot(self):
        """测试有效的边池创建。"""
        pot = SidePot(amount=100, eligible_players=[0, 1, 2])
        
        assert pot.amount == 100
        assert pot.eligible_players == [0, 1, 2]
        assert "边池(100筹码, 玩家: 0, 1, 2)" in str(pot)
        assert "SidePot(amount=100, eligible_players=[0, 1, 2])" == repr(pot)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_negative_amount_raises_error(self):
        """测试负数金额抛出异常。"""
        with pytest.raises(ValueError, match="边池金额不能为负数"):
            SidePot(amount=-10, eligible_players=[0, 1])
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_empty_players_raises_error(self):
        """测试空玩家列表抛出异常。"""
        with pytest.raises(ValueError, match="边池必须至少有一个有资格的玩家"):
            SidePot(amount=100, eligible_players=[])
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_duplicate_players_raises_error(self):
        """测试重复玩家抛出异常。"""
        with pytest.raises(ValueError, match="边池的有资格玩家列表不能有重复"):
            SidePot(amount=100, eligible_players=[0, 1, 1])


@pytest.mark.unit
@pytest.mark.fast
class TestCalculateSidePots:
    """测试边池计算算法。"""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_empty_contributions(self):
        """测试空投入。"""
        result = calculate_side_pots({})
        assert result == []
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_zero_contributions(self):
        """测试零投入。"""
        result = calculate_side_pots({0: 0, 1: 0})
        assert result == []
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_single_player(self):
        """测试单人投入。"""
        result = calculate_side_pots({0: 100})
        assert result == []  # 单人不形成边池
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_equal_contributions(self):
        """测试相等投入。"""
        result = calculate_side_pots({0: 50, 1: 50, 2: 50})
        
        assert len(result) == 1
        assert result[0].amount == 150  # 50 * 3
        assert set(result[0].eligible_players) == {0, 1, 2}
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_two_different_amounts(self):
        """测试两种不同投入。"""
        result = calculate_side_pots({0: 25, 1: 50})
        
        assert len(result) == 1
        assert result[0].amount == 50  # 25 * 2
        assert set(result[0].eligible_players) == {0, 1}
        # 玩家1的剩余25应该返还，不形成边池
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_three_way_all_in_different_amounts(self):
        """测试三人不同额全押（PLAN #10核心用例）。"""
        # 玩家投入：A=25, B=50, C=100
        contributions = {0: 25, 1: 50, 2: 100}
        result = calculate_side_pots(contributions)
        
        # 应该有2个边池
        assert len(result) == 2
        
        # 主池：25 × 3 = 75 (玩家0,1,2)
        main_pot = result[0]
        assert main_pot.amount == 75
        assert set(main_pot.eligible_players) == {0, 1, 2}
        
        # 边池1：(50-25) × 2 = 50 (玩家1,2)
        side_pot1 = result[1]
        assert side_pot1.amount == 50
        assert set(side_pot1.eligible_players) == {1, 2}
        
        # 玩家2剩余：100-50 = 50 (应该返还，不形成边池)
        total_in_pots = sum(pot.amount for pot in result)
        total_contributed = sum(contributions.values())
        returned_amount = total_contributed - total_in_pots
        assert returned_amount == 50
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_four_way_complex(self):
        """测试四人复杂场景。"""
        # A=10, B=20, C=30, D=40
        contributions = {0: 10, 1: 20, 2: 30, 3: 40}
        result = calculate_side_pots(contributions)
        
        assert len(result) == 3
        
        # 主池：10 × 4 = 40
        assert result[0].amount == 40
        assert set(result[0].eligible_players) == {0, 1, 2, 3}
        
        # 边池1：(20-10) × 3 = 30
        assert result[1].amount == 30
        assert set(result[1].eligible_players) == {1, 2, 3}
        
        # 边池2：(30-20) × 2 = 20
        assert result[2].amount == 20
        assert set(result[2].eligible_players) == {2, 3}
        
        # 玩家3剩余：40-30 = 10 (返还)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_multiple_equal_amounts(self):
        """测试多人相同投入。"""
        # A=B=25, C=D=50
        contributions = {0: 25, 1: 25, 2: 50, 3: 50}
        result = calculate_side_pots(contributions)
        
        assert len(result) == 2
        
        # 主池：25 × 4 = 100
        assert result[0].amount == 100
        assert set(result[0].eligible_players) == {0, 1, 2, 3}
        
        # 边池1：(50-25) × 2 = 50
        assert result[1].amount == 50
        assert set(result[1].eligible_players) == {2, 3}


@pytest.mark.unit
@pytest.mark.fast
class TestGetPotDistributionSummary:
    """测试边池分配摘要。"""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_summary_with_return(self):
        """测试包含返还的摘要。"""
        contributions = {0: 25, 1: 50, 2: 100}
        summary = get_pot_distribution_summary(contributions)
        
        assert len(summary['side_pots']) == 2
        assert summary['total_pot_amount'] == 125  # 75 + 50
        assert summary['returned_amount'] == 50
        assert summary['returned_to_player'] == 2  # 投入最多的玩家
        assert summary['total_contributed'] == 175
        assert summary['validation_passed'] is True
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_summary_no_return(self):
        """测试无返还的摘要。"""
        contributions = {0: 50, 1: 50, 2: 50}
        summary = get_pot_distribution_summary(contributions)
        
        assert len(summary['side_pots']) == 1
        assert summary['total_pot_amount'] == 150
        assert summary['returned_amount'] == 0
        assert summary['returned_to_player'] is None
        assert summary['total_contributed'] == 150
        assert summary['validation_passed'] is True


@pytest.mark.unit
@pytest.mark.fast
class TestPotManager:
    """测试PotManager类。"""
    
    def setup_method(self):
        """设置测试环境。"""
        self.pot_manager = PotManager()
        self.players = [
            Player(seat_id=0, name="Alice", chips=100),
            Player(seat_id=1, name="Bob", chips=100),
            Player(seat_id=2, name="Charlie", chips=100)
        ]
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_initial_state(self):
        """测试初始状态。"""
        assert self.pot_manager.main_pot == 0
        assert len(self.pot_manager.side_pots) == 0
        assert self.pot_manager.get_total_pot() == 0
        assert self.pot_manager.validate_pot_integrity()
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_collect_equal_bets(self):
        """测试收集相等下注。"""
        # 每人下注20
        for player in self.players:
            player.bet(20)
        
        returns = self.pot_manager.collect_from_players(self.players)
        
        assert self.pot_manager.main_pot == 60
        assert len(self.pot_manager.side_pots) == 0
        assert returns == {}  # 无返还
        
        # 验证玩家状态
        for player in self.players:
            assert player.current_bet == 0  # 已重置
            assert player.chips == 80  # 100 - 20
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_collect_three_way_all_in(self):
        """测试三人不同额全押收集（PLAN #10核心测试）。"""
        # 设置不同的下注：A=25, B=50, C=100
        self.players[0].bet(25)
        self.players[1].bet(50)
        self.players[2].bet(100)
        
        returns = self.pot_manager.collect_from_players(self.players)
        
        # 验证主池：25 × 3 = 75
        assert self.pot_manager.main_pot == 75
        
        # 验证边池：(50-25) × 2 = 50
        assert len(self.pot_manager.side_pots) == 1
        assert self.pot_manager.side_pots[0].amount == 50
        assert set(self.pot_manager.side_pots[0].eligible_players) == {1, 2}
        
        # 验证总底池：75 + 50 = 125
        assert self.pot_manager.get_total_pot() == 125
        
        # 验证返还：玩家2应该得到50返还
        assert returns == {2: 50}
        assert self.players[2].chips == 50  # 100 - 100 + 50
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_allocate_side_pots_method(self):
        """测试allocate_side_pots方法（PLAN #10要求的核心方法）。"""
        contributions = {0: 25, 1: 50, 2: 100}
        pots = self.pot_manager.allocate_side_pots(contributions)
        
        # 不应该修改当前底池状态
        assert self.pot_manager.main_pot == 0
        assert len(self.pot_manager.side_pots) == 0
        
        # 但应该返回正确的边池计算结果
        assert len(pots) == 2
        assert pots[0].amount == 75
        assert pots[1].amount == 50
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_award_single_winner(self):
        """测试单一获胜者分配。"""
        # 设置底池
        self.players[0].bet(20)
        self.players[1].bet(20)
        self.players[2].bet(20)
        self.pot_manager.collect_from_players(self.players)
        
        # 玩家0获胜
        winners_by_pot = {0: [self.players[0]]}
        awards = self.pot_manager.award_pots(winners_by_pot)
        
        assert awards[0] == 60
        assert self.players[0].chips == 140  # 100 - 20 + 60
        assert self.pot_manager.main_pot == 0  # 已清空
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_award_multiple_winners(self):
        """测试多个获胜者分配。"""
        # 设置底池
        for player in self.players:
            player.bet(30)
        self.pot_manager.collect_from_players(self.players)
        
        # 玩家0和1平分
        winners_by_pot = {0: [self.players[0], self.players[1]]}
        awards = self.pot_manager.award_pots(winners_by_pot)
        
        assert awards[0] == 45  # 90 / 2
        assert awards[1] == 45
        assert self.players[0].chips == 115  # 100 - 30 + 45
        assert self.players[1].chips == 115
        assert self.players[2].chips == 70   # 100 - 30
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_award_complex_side_pots(self):
        """测试复杂边池分配。"""
        # 设置复杂场景：A=30, B=60, C=90
        self.players[0].bet(30)
        self.players[1].bet(60)
        self.players[2].bet(90)
        
        self.pot_manager.collect_from_players(self.players)
        
        # 验证边池结构
        assert self.pot_manager.main_pot == 90  # 30 × 3
        assert len(self.pot_manager.side_pots) == 1
        assert self.pot_manager.side_pots[0].amount == 60  # (60-30) × 2
        
        # 设置获胜者：主池C胜，边池1B胜
        winners_by_pot = {
            0: [self.players[2]],  # C赢主池
            1: [self.players[1]]   # B赢边池1
        }
        
        awards = self.pot_manager.award_pots(winners_by_pot)
        
        assert awards[2] == 90  # C获得主池
        assert awards[1] == 60  # B获得边池
        
        # 验证最终筹码（考虑之前的返还）
        # C: 100-90+30(返还)+90(主池) = 130
        # B: 100-60+60(边池) = 100
        assert self.players[2].chips == 130
        assert self.players[1].chips == 100
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_pot_summary(self):
        """测试底池摘要。"""
        # 设置边池
        self.players[0].bet(25)
        self.players[1].bet(50)
        self.pot_manager.collect_from_players(self.players)
        
        summary = self.pot_manager.get_pot_summary()
        
        assert summary['main_pot'] == 50  # 25 × 2
        assert summary['side_pots_count'] == 0
        assert summary['total_pot'] == 50
        assert summary['total_collected'] == 75
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_reset(self):
        """测试重置功能。"""
        # 设置一些底池
        for player in self.players:
            player.bet(10)
        self.pot_manager.collect_from_players(self.players)
        
        assert self.pot_manager.get_total_pot() > 0
        
        # 重置
        self.pot_manager.reset()
        
        assert self.pot_manager.main_pot == 0
        assert len(self.pot_manager.side_pots) == 0
        assert self.pot_manager.get_total_pot() == 0
        assert self.pot_manager._total_collected == 0
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_validate_pot_integrity(self):
        """测试底池完整性验证。"""
        # 正常情况
        assert self.pot_manager.validate_pot_integrity()
        
        # 设置底池
        for player in self.players:
            player.bet(20)
        self.pot_manager.collect_from_players(self.players)
        
        # 验证期望总额
        assert self.pot_manager.validate_pot_integrity(60)
        assert not self.pot_manager.validate_pot_integrity(100)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_string_representations(self):
        """测试字符串表示。"""
        # 空底池
        assert "主池: 0, 总计: 0" in str(self.pot_manager)
        assert "PotManager(main=0, sides=0, total=0)" == repr(self.pot_manager)
        
        # 有底池
        for player in self.players:
            player.bet(10)
        self.pot_manager.collect_from_players(self.players)
        
        assert "主池: 30" in str(self.pot_manager)
        assert "总计: 30" in str(self.pot_manager)


@pytest.mark.unit
@pytest.mark.fast
class TestEdgeCases:
    """测试边界情况。"""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_mixed_zero_and_positive_contributions(self):
        """测试混合零和正投入。"""
        contributions = {0: 0, 1: 50, 2: 100, 3: 0}
        result = calculate_side_pots(contributions)
        
        # 应该只考虑非零投入
        assert len(result) == 1
        assert result[0].amount == 100  # 50 × 2
        assert set(result[0].eligible_players) == {1, 2}
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_single_non_zero_contribution(self):
        """测试单个非零投入。"""
        contributions = {0: 0, 1: 100, 2: 0}
        result = calculate_side_pots(contributions)
        
        assert result == []  # 单人不形成边池
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_same_non_zero_amounts(self):
        """测试所有相同非零金额。"""
        contributions = {0: 75, 1: 75, 2: 75, 3: 75}
        result = calculate_side_pots(contributions)
        
        assert len(result) == 1
        assert result[0].amount == 300  # 75 × 4
        assert set(result[0].eligible_players) == {0, 1, 2, 3} 