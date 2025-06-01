"""
边池计算系统的单元测试
验证标准德州扑克边池算法的正确性
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_game_logic.betting.side_pot import calculate_side_pots, SidePot, validate_side_pot_calculation, get_pot_distribution_summary


class TestSidePotCalculation:
    """边池计算测试类"""

    def test_three_player_all_in_example(self):
        """测试用户提供的三人全押示例"""
        # 玩家投入: A=25, B=50, C=100
        contrib = {0: 25, 1: 50, 2: 100}
        pots = calculate_side_pots(contrib)
        
        # 验证边池数量
        assert len(pots) == 2
        
        # 验证主池: 25 × 3 = 75 (玩家0,1,2)
        assert pots[0].amount == 75
        assert set(pots[0].eligible_players) == {0, 1, 2}
        
        # 验证边池1: (50-25) × 2 = 50 (玩家1,2)
        assert pots[1].amount == 50
        assert set(pots[1].eligible_players) == {1, 2}
        
        # 验证总金额正确性
        assert validate_side_pot_calculation(contrib, pots)

    def test_empty_contribution(self):
        """测试空投入"""
        contrib = {}
        pots = calculate_side_pots(contrib)
        assert len(pots) == 0

    def test_zero_contribution(self):
        """测试零投入"""
        contrib = {0: 0, 1: 0}
        pots = calculate_side_pots(contrib)
        assert len(pots) == 0

    def test_single_player(self):
        """测试单人投入"""
        contrib = {0: 100}
        pots = calculate_side_pots(contrib)
        assert len(pots) == 0  # 单人不形成边池

    def test_two_players_equal_contribution(self):
        """测试两人相等投入"""
        contrib = {0: 50, 1: 50}
        pots = calculate_side_pots(contrib)
        
        assert len(pots) == 1
        assert pots[0].amount == 100  # 50 × 2
        assert set(pots[0].eligible_players) == {0, 1}

    def test_two_players_different_contribution(self):
        """测试两人不同投入"""
        contrib = {0: 30, 1: 80}
        pots = calculate_side_pots(contrib)
        
        assert len(pots) == 1
        assert pots[0].amount == 60  # 30 × 2
        assert set(pots[0].eligible_players) == {0, 1}
        
        # 玩家1剩余50应该返还，不形成边池

    def test_four_players_incremental_all_in(self):
        """测试四人递增全押"""
        contrib = {0: 10, 1: 20, 2: 30, 3: 40}
        pots = calculate_side_pots(contrib)
        
        assert len(pots) == 3
        
        # 主池: 10 × 4 = 40
        assert pots[0].amount == 40
        assert set(pots[0].eligible_players) == {0, 1, 2, 3}
        
        # 边池1: (20-10) × 3 = 30
        assert pots[1].amount == 30
        assert set(pots[1].eligible_players) == {1, 2, 3}
        
        # 边池2: (30-20) × 2 = 20
        assert pots[2].amount == 20
        assert set(pots[2].eligible_players) == {2, 3}
        
        # 玩家3剩余10返还，不形成边池

    def test_same_amount_multiple_players(self):
        """测试多人相同投入额"""
        contrib = {0: 25, 1: 25, 2: 50}
        pots = calculate_side_pots(contrib)
        
        assert len(pots) == 1
        assert pots[0].amount == 75  # 25 × 3
        assert set(pots[0].eligible_players) == {0, 1, 2}
        
        # 玩家2剩余25返还

    def test_complex_scenario(self):
        """测试复杂场景"""
        contrib = {0: 15, 1: 15, 2: 30, 3: 30, 4: 60}
        pots = calculate_side_pots(contrib)
        
        assert len(pots) == 2
        
        # 主池: 15 × 5 = 75
        assert pots[0].amount == 75
        assert set(pots[0].eligible_players) == {0, 1, 2, 3, 4}
        
        # 边池1: (30-15) × 3 = 45
        assert pots[1].amount == 45
        assert set(pots[1].eligible_players) == {2, 3, 4}
        
        # 玩家4剩余30返还

    def test_validation_function(self):
        """测试验证函数"""
        contrib = {0: 25, 1: 50, 2: 100}
        pots = calculate_side_pots(contrib)
        
        # 正确的边池应该通过验证
        assert validate_side_pot_calculation(contrib, pots)
        
        # 错误的边池应该不通过验证
        wrong_pots = [SidePot(100, [0, 1, 2])]
        assert not validate_side_pot_calculation(contrib, wrong_pots)

    def test_pot_distribution_summary(self):
        """测试边池分配摘要"""
        contrib = {0: 25, 1: 50, 2: 100}
        summary = get_pot_distribution_summary(contrib)
        
        assert summary['total_contributed'] == 175
        assert summary['total_pot_amount'] == 125  # 75 + 50
        assert summary['returned_amount'] == 50
        assert summary['returned_to_player'] == 2
        assert summary['validation_passed']
        assert len(summary['side_pots']) == 2


class TestSidePotDataStructure:
    """边池数据结构测试类"""

    def test_side_pot_creation(self):
        """测试边池创建"""
        pot = SidePot(100, [0, 1, 2])
        assert pot.amount == 100
        assert pot.eligible_players == [0, 1, 2]

    def test_side_pot_validation(self):
        """测试边池验证"""
        # 正常边池
        pot = SidePot(100, [0, 1])
        assert pot.amount == 100
        
        # 负金额应该抛出异常
        try:
            SidePot(-10, [0, 1])
            assert False, "应该抛出ValueError"
        except ValueError as e:
            assert "边池金额不能为负数" in str(e)
        
        # 空玩家列表应该抛出异常
        try:
            SidePot(100, [])
            assert False, "应该抛出ValueError"
        except ValueError as e:
            assert "边池必须至少有一个有资格的玩家" in str(e)
        
        # 重复玩家应该抛出异常
        try:
            SidePot(100, [0, 1, 1])
            assert False, "应该抛出ValueError"
        except ValueError as e:
            assert "边池的有资格玩家列表不能有重复" in str(e)

    def test_side_pot_string_representation(self):
        """测试边池字符串表示"""
        pot = SidePot(100, [0, 1, 2])
        
        str_repr = str(pot)
        assert "100" in str_repr
        assert "0, 1, 2" in str_repr
        
        repr_str = repr(pot)
        assert "SidePot" in repr_str
        assert "amount=100" in repr_str


def run_tests():
    """运行所有测试"""
    print("=== 边池计算系统单元测试 ===\n")
    
    calc_test = TestSidePotCalculation()
    structure_test = TestSidePotDataStructure()
    
    test_methods = [
        ("三人全押示例", calc_test.test_three_player_all_in_example),
        ("空投入", calc_test.test_empty_contribution),
        ("零投入", calc_test.test_zero_contribution),
        ("单人投入", calc_test.test_single_player),
        ("两人相等投入", calc_test.test_two_players_equal_contribution),
        ("两人不同投入", calc_test.test_two_players_different_contribution),
        ("四人递增全押", calc_test.test_four_players_incremental_all_in),
        ("多人相同投入", calc_test.test_same_amount_multiple_players),
        ("复杂场景", calc_test.test_complex_scenario),
        ("验证函数", calc_test.test_validation_function),
        ("边池分配摘要", calc_test.test_pot_distribution_summary),
        ("边池创建", structure_test.test_side_pot_creation),
        ("边池验证", structure_test.test_side_pot_validation),
        ("边池字符串表示", structure_test.test_side_pot_string_representation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in test_methods:
        try:
            test_func()
            print(f"[OK] {test_name}测试通过")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test_name}测试失败: {e}")
            failed += 1
    
    print(f"\n测试结果: {passed}通过, {failed}失败")
    
    if failed == 0:
        print("[SUCCESS] 所有边池计算测试通过！")
        return True
    else:
        print("[ERROR] 部分测试失败，需要修复")
        return False


if __name__ == "__main__":
    run_tests() 