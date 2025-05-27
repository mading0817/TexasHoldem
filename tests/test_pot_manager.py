"""
PotManager边池系统的单元测试
测试边池计算、收集和分配逻辑
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core_game_logic.betting.pot_manager import PotManager
from core_game_logic.core.player import Player
from core_game_logic.core.enums import SeatStatus


class TestPotManager:
    """测试PotManager边池系统"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.pot_manager = PotManager()
        
        # 创建测试玩家
        self.players = [
            Player(seat_id=0, name="玩家A", chips=100),
            Player(seat_id=1, name="玩家B", chips=100), 
            Player(seat_id=2, name="玩家C", chips=100)
        ]
    
    def test_simple_pot_collection(self):
        """测试简单的底池收集"""
        print("测试简单的底池收集...")
        self.setup_method()
        
        # 设置玩家下注
        self.players[0].current_bet = 10
        self.players[1].current_bet = 10
        self.players[2].current_bet = 10
        
        # 收集下注
        self.pot_manager.collect_from_players(self.players)
        
        # 验证结果
        assert self.pot_manager.main_pot == 30
        assert len(self.pot_manager.side_pots) == 0
        assert self.pot_manager.get_total_pot() == 30
        
        # 验证玩家下注已重置
        for player in self.players:
            assert player.current_bet == 0
        
        print("✓ 简单底池收集测试通过")
    
    def test_three_way_all_in_side_pots(self):
        """测试三人不同All-in金额的边池计算"""
        print("测试三人不同All-in金额的边池计算...")
        self.setup_method()
        
        # 设置不同的All-in金额：A=25, B=50, C=100
        self.players[0].current_bet = 25  # 玩家A全押25
        self.players[1].current_bet = 50  # 玩家B全押50
        self.players[2].current_bet = 100 # 玩家C下注100
        
        # 收集下注
        self.pot_manager.collect_from_players(self.players)
        
        # 验证主池：25 × 3 = 75
        assert self.pot_manager.main_pot == 75
        
        # 验证边池：(50-25) × 2 = 50
        assert len(self.pot_manager.side_pots) == 1
        assert self.pot_manager.side_pots[0].amount == 50
        assert set(self.pot_manager.side_pots[0].eligible_players) == {1, 2}
        
        # 验证总底池：75 + 50 = 125 (剩余25应该退还给玩家C)
        assert self.pot_manager.get_total_pot() == 125
        
        print("✓ 三人不同All-in边池计算测试通过")
    
    def test_pot_award_single_winner(self):
        """测试单一获胜者的底池分配"""
        print("测试单一获胜者的底池分配...")
        self.setup_method()
        
        # 设置底池
        self.players[0].current_bet = 20
        self.players[1].current_bet = 20
        self.players[2].current_bet = 20
        self.pot_manager.collect_from_players(self.players)
        
        # 玩家A获胜
        winners_by_pot = {0: [self.players[0]]}
        awards = self.pot_manager.award_pots(winners_by_pot)
        
        # 验证分配结果
        assert awards[0] == 60  # 玩家A获得全部60筹码
        assert self.players[0].chips == 160  # 原100 + 60
        assert self.pot_manager.main_pot == 0  # 主池已清空
        
        print("✓ 单一获胜者底池分配测试通过")
    
    def test_pot_award_split_pot(self):
        """测试平分底池的情况"""
        print("测试平分底池的情况...")
        self.setup_method()
        
        # 设置底池
        self.players[0].current_bet = 15
        self.players[1].current_bet = 15
        self.players[2].current_bet = 15
        self.pot_manager.collect_from_players(self.players)
        
        # 玩家A和B平分
        winners_by_pot = {0: [self.players[0], self.players[1]]}
        awards = self.pot_manager.award_pots(winners_by_pot)
        
        # 验证分配结果：45 / 2 = 22 + 23 (余数给第一个)
        assert awards[0] == 23  # 玩家A获得23
        assert awards[1] == 22  # 玩家B获得22
        assert self.players[0].chips == 123
        assert self.players[1].chips == 122
        
        print("✓ 平分底池测试通过")
    
    def test_complex_side_pot_award(self):
        """测试复杂边池分配"""
        print("测试复杂边池分配...")
        self.setup_method()
        
        # 设置复杂的All-in场景 - 正确模拟下注流程
        # A全押30：筹码从100变为70，current_bet=30
        self.players[0].chips = 70
        self.players[0].current_bet = 30
        
        # B全押60：筹码从100变为40，current_bet=60
        self.players[1].chips = 40
        self.players[1].current_bet = 60
        
        # C下注90：筹码从100变为10，current_bet=90
        self.players[2].chips = 10
        self.players[2].current_bet = 90
        
        self.pot_manager.collect_from_players(self.players)
        
        # 验证边池结构
        # 主池：30 × 3 = 90 (A,B,C竞争)
        # 边池1：(60-30) × 2 = 60 (B,C竞争)
        # 返还：90-60 = 30 (给C)
        assert self.pot_manager.main_pot == 90
        assert len(self.pot_manager.side_pots) == 1
        assert self.pot_manager.side_pots[0].amount == 60
        
        # 验证返还后的筹码状态
        # C应该有：10(剩余) + 30(返还) = 40筹码
        assert self.players[2].chips == 40
        
        # 设置获胜者：主池C胜，边池1B胜
        winners_by_pot = {
            0: [self.players[2]],  # C赢主池
            1: [self.players[1]]   # B赢边池1
        }
        
        awards = self.pot_manager.award_pots(winners_by_pot)
        
        # 验证分配
        assert awards[2] == 90  # C获得主池90
        assert awards[1] == 60  # B获得边池60
        
        # 验证最终筹码
        # C: 40(返还后) + 90(主池奖励) = 130
        # B: 40(剩余) + 60(边池奖励) = 100
        assert self.players[2].chips == 130
        assert self.players[1].chips == 100
        
        print("✓ 复杂边池分配测试通过")
    
    def test_pot_integrity_validation(self):
        """测试底池完整性验证"""
        print("测试底池完整性验证...")
        self.setup_method()
        
        # 正常状态应该通过验证
        assert self.pot_manager.validate_pot_integrity()
        
        # 添加一些底池
        self.players[0].current_bet = 20
        self.players[1].current_bet = 20
        self.pot_manager.collect_from_players(self.players)
        
        # 验证期望总额
        assert self.pot_manager.validate_pot_integrity(40)
        assert not self.pot_manager.validate_pot_integrity(50)  # 错误的期望值
        
        print("✓ 底池完整性验证测试通过")
    
    def test_pot_summary(self):
        """测试底池状态摘要"""
        print("测试底池状态摘要...")
        self.setup_method()
        
        # 设置复杂场景
        self.players[0].current_bet = 25
        self.players[1].current_bet = 50
        self.players[2].current_bet = 75
        self.pot_manager.collect_from_players(self.players)
        
        summary = self.pot_manager.get_pot_summary()
        
        # 验证摘要内容
        assert summary['main_pot'] == 75  # 25 × 3
        assert summary['side_pots_count'] == 1
        assert summary['total_pot'] == 125  # 75 + 50
        assert summary['total_collected'] == 150
        
        print("✓ 底池状态摘要测试通过")
    
    def test_pot_reset(self):
        """测试底池重置功能"""
        print("测试底池重置功能...")
        self.setup_method()
        
        # 设置一些底池
        self.players[0].current_bet = 30
        self.players[1].current_bet = 30
        self.pot_manager.collect_from_players(self.players)
        
        # 验证有底池
        assert self.pot_manager.get_total_pot() > 0
        
        # 重置
        self.pot_manager.reset()
        
        # 验证已清空
        assert self.pot_manager.main_pot == 0
        assert len(self.pot_manager.side_pots) == 0
        assert self.pot_manager.get_total_pot() == 0
        assert self.pot_manager._total_collected == 0
        
        print("✓ 底池重置功能测试通过")


def run_tests():
    """运行所有测试"""
    print("开始运行PotManager边池系统测试...")
    print("=" * 50)
    
    test_instance = TestPotManager()
    
    try:
        test_instance.test_simple_pot_collection()
        test_instance.test_three_way_all_in_side_pots()
        test_instance.test_pot_award_single_winner()
        test_instance.test_pot_award_split_pot()
        test_instance.test_complex_side_pot_award()
        test_instance.test_pot_integrity_validation()
        test_instance.test_pot_summary()
        test_instance.test_pot_reset()
        
        print("=" * 50)
        print("✅ 所有测试通过！PotManager边池系统工作正常。")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_tests() 