"""
单元测试: PotManager
"""
import unittest

from v3.core.pot.pot_manager import PotManager
from v3.core.chips.chip_ledger import ChipLedger
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker

class TestPotManager(unittest.TestCase):
    """测试 PotManager 的功能"""

    def setUp(self):
        """测试设置"""
        # PotManager 需要一个 ledger，但对于计算边池的测试，我们可以传入一个空的
        self.pot_manager = PotManager(ChipLedger())
        CoreUsageChecker.verify_real_objects(self.pot_manager, "PotManager")

    def test_calculate_side_pots_complex_case_from_ultimate_test(self):
        """
        测试：一个在终极测试中导致失败的复杂边池计算场景
        """
        # 1. 设置
        player_bets = {
            'player_0': 800, 
            'player_1': 900, 
            'player_2': 800, 
            'player_4': 900, 
            'player_5': 900
        }
        
        # 2. 执行
        side_pots = self.pot_manager.calculate_side_pots(player_bets)
        total_pot_calculated = sum(p.amount for p in side_pots)

        # 3. 断言
        self.assertEqual(total_pot_calculated, 4300)
        self.assertEqual(len(side_pots), 2)

        # 验证主池
        main_pot = next(p for p in side_pots if len(p.eligible_players) == 5)
        self.assertEqual(main_pot.amount, 4000)
        self.assertEqual(main_pot.eligible_players, {'player_0', 'player_1', 'player_2', 'player_4', 'player_5'})

        # 验证边池
        side_pot_1 = next(p for p in side_pots if len(p.eligible_players) == 3)
        self.assertEqual(side_pot_1.amount, 300)
        self.assertEqual(side_pot_1.eligible_players, {'player_1', 'player_4', 'player_5'})

if __name__ == '__main__':
    unittest.main() 