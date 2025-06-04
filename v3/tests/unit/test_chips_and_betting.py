"""
筹码和下注模块的单元测试

测试筹码管理、下注引擎和边池管理的功能。
"""

import pytest
import time
from typing import Dict, List

# 导入被测试的模块
from v3.core.chips import ChipLedger, ChipTransaction, TransactionType, ChipValidator, ValidationResult
from v3.core.betting import BettingEngine, BetResult, BettingValidator, BetType, BetAction
from v3.core.pot import PotManager, SidePot, PotCalculator, PotDistributor

# 导入反作弊检查
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestChipLedger:
    """筹码账本测试"""
    
    def test_chip_ledger_initialization(self):
        """测试筹码账本初始化"""
        initial_balances = {"player1": 1000, "player2": 2000}
        ledger = ChipLedger(initial_balances)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ledger, "ChipLedger")
        
        assert ledger.get_balance("player1") == 1000
        assert ledger.get_balance("player2") == 2000
        assert ledger.get_total_chips() == 3000
    
    def test_chip_deduction_success(self):
        """测试成功扣除筹码"""
        ledger = ChipLedger({"player1": 1000})
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ledger, "ChipLedger")
        
        initial_total = ledger.get_total_chips()
        result = ledger.deduct_chips("player1", 300, "测试扣除")
        
        assert result is True
        assert ledger.get_balance("player1") == 700
        assert ledger.get_total_chips() == initial_total - 300
    
    def test_chip_deduction_insufficient_funds(self):
        """测试筹码不足时扣除失败"""
        ledger = ChipLedger({"player1": 100})
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ledger, "ChipLedger")
        
        result = ledger.deduct_chips("player1", 200, "测试扣除")
        
        assert result is False
        assert ledger.get_balance("player1") == 100  # 余额不变
    
    def test_chip_addition(self):
        """测试增加筹码"""
        ledger = ChipLedger({"player1": 1000})
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ledger, "ChipLedger")
        
        initial_total = ledger.get_total_chips()
        ledger.add_chips("player1", 500, "测试增加")
        
        assert ledger.get_balance("player1") == 1500
        assert ledger.get_total_chips() == initial_total + 500
    
    def test_chip_transfer_success(self):
        """测试成功转移筹码"""
        ledger = ChipLedger({"player1": 1000, "player2": 500})
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ledger, "ChipLedger")
        
        initial_total = ledger.get_total_chips()
        result = ledger.transfer_chips("player1", "player2", 300, "测试转移")
        
        assert result is True
        assert ledger.get_balance("player1") == 700
        assert ledger.get_balance("player2") == 800
        assert ledger.get_total_chips() == initial_total  # 总量不变
    
    def test_chip_freeze_and_unfreeze(self):
        """测试冻结和解冻筹码"""
        ledger = ChipLedger({"player1": 1000})
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ledger, "ChipLedger")
        
        # 冻结筹码
        result = ledger.freeze_chips("player1", 300, "测试冻结")
        assert result is True
        assert ledger.get_available_chips("player1") == 700
        assert ledger.get_frozen_chips("player1") == 300
        
        # 解冻筹码
        result = ledger.unfreeze_chips("player1", 100, "测试解冻")
        assert result is True
        assert ledger.get_available_chips("player1") == 800
        assert ledger.get_frozen_chips("player1") == 200


class TestChipValidator:
    """筹码验证器测试"""
    
    def test_validate_deduct_operation_success(self):
        """测试验证扣除操作成功"""
        ledger = ChipLedger({"player1": 1000})
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ledger, "ChipLedger")
        
        result = ChipValidator.validate_deduct_operation(ledger, "player1", 500)
        
        assert result.is_valid is True
        assert result.error_message == ""
    
    def test_validate_deduct_operation_insufficient_funds(self):
        """测试验证扣除操作筹码不足"""
        ledger = ChipLedger({"player1": 100})
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ledger, "ChipLedger")
        
        result = ChipValidator.validate_deduct_operation(ledger, "player1", 500)
        
        assert result.is_valid is False
        assert "筹码不足" in result.error_message
    
    def test_validate_chip_conservation(self):
        """测试筹码守恒验证"""
        result = ChipValidator.validate_chip_conservation(1000, 1000)
        assert result.is_valid is True
        
        result = ChipValidator.validate_chip_conservation(1000, 900)
        assert result.is_valid is False
        assert "筹码守恒违规" in result.error_message


class TestBettingEngine:
    """下注引擎测试"""
    
    def test_betting_engine_initialization(self):
        """测试下注引擎初始化"""
        ledger = ChipLedger({"player1": 1000, "player2": 1000})
        engine = BettingEngine(ledger, big_blind=20)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(engine, "BettingEngine")
        CoreUsageChecker.verify_real_objects(ledger, "ChipLedger")
        
        assert engine.get_current_bet() == 0
        assert engine.get_min_raise() == 20
    
    def test_start_new_round_with_blinds(self):
        """测试开始新轮次并处理盲注"""
        ledger = ChipLedger({"player1": 1000, "player2": 1000, "player3": 1000})
        engine = BettingEngine(ledger, big_blind=20)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(engine, "BettingEngine")
        
        result = engine.start_new_round(["player1", "player2", "player3"], "player1", "player2")
        
        assert result is True
        assert engine.get_current_bet() == 20
        assert ledger.get_balance("player1") == 990  # 小盲注10
        assert ledger.get_balance("player2") == 980  # 大盲注20
    
    def test_execute_fold_action(self):
        """测试执行弃牌行动"""
        ledger = ChipLedger({"player1": 1000, "player2": 1000, "player3": 1000})
        engine = BettingEngine(ledger)
        engine.start_new_round(["player1", "player2", "player3"], "player1", "player2")
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(engine, "BettingEngine")
        
        # player3弃牌（player1和player2已经在盲注阶段行动过了）
        result = engine.execute_player_action("player3", BetType.FOLD)
        
        assert result.success is True
        assert "player3" not in engine.get_active_players()
    
    def test_execute_call_action(self):
        """测试执行跟注行动"""
        ledger = ChipLedger({"player1": 1000, "player2": 1000, "player3": 1000})
        engine = BettingEngine(ledger, big_blind=20)
        engine.start_new_round(["player1", "player2", "player3"], "player1", "player2")
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(engine, "BettingEngine")
        
        # player3跟注大盲注 - CALL操作不需要传递金额
        result = engine.execute_player_action("player3", BetType.CALL)
        
        assert result.success is True
        assert result.chips_moved == 20
        assert ledger.get_balance("player3") == 980
    
    def test_execute_raise_action(self):
        """测试执行加注行动"""
        ledger = ChipLedger({"player1": 1000, "player2": 1000, "player3": 1000})
        engine = BettingEngine(ledger, big_blind=20)
        engine.start_new_round(["player1", "player2", "player3"], "player1", "player2")
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(engine, "BettingEngine")
        
        # player3加注到40
        result = engine.execute_player_action("player3", BetType.RAISE, 40)
        
        assert result.success is True
        assert engine.get_current_bet() == 40
        assert engine.get_min_raise() == 20  # 加注幅度
        assert ledger.get_balance("player3") == 960


class TestPotManager:
    """边池管理器测试"""
    
    def test_pot_manager_initialization(self):
        """测试边池管理器初始化"""
        ledger = ChipLedger({"player1": 1000})
        pot_manager = PotManager(ledger)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(pot_manager, "PotManager")
        CoreUsageChecker.verify_real_objects(ledger, "ChipLedger")
        
        assert pot_manager.get_total_pot_amount() == 0
        assert len(pot_manager.get_side_pots()) == 0
    
    def test_calculate_side_pots_simple(self):
        """测试简单边池计算"""
        ledger = ChipLedger({"player1": 1000, "player2": 1000})
        pot_manager = PotManager(ledger)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(pot_manager, "PotManager")
        
        player_bets = {"player1": 100, "player2": 100}
        side_pots = pot_manager.calculate_side_pots(player_bets)
        
        assert len(side_pots) == 1
        assert side_pots[0].amount == 200
        assert side_pots[0].is_main_pot is True
        assert "player1" in side_pots[0].eligible_players
        assert "player2" in side_pots[0].eligible_players
    
    def test_calculate_side_pots_with_all_in(self):
        """测试包含全押的边池计算"""
        ledger = ChipLedger({"player1": 1000, "player2": 1000, "player3": 1000})
        pot_manager = PotManager(ledger)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(pot_manager, "PotManager")
        
        # player1全押50，player2和player3各下注100
        player_bets = {"player1": 50, "player2": 100, "player3": 100}
        side_pots = pot_manager.calculate_side_pots(player_bets)
        
        assert len(side_pots) == 2
        
        # 主池：50 * 3 = 150，所有玩家有资格
        main_pot = side_pots[0]
        assert main_pot.amount == 150
        assert main_pot.is_main_pot is True
        assert len(main_pot.eligible_players) == 3
        
        # 边池：50 * 2 = 100，只有player2和player3有资格
        side_pot = side_pots[1]
        assert side_pot.amount == 100
        assert side_pot.is_main_pot is False
        assert len(side_pot.eligible_players) == 2
        assert "player1" not in side_pot.eligible_players
    
    def test_distribute_winnings_simple(self):
        """测试简单奖金分配"""
        ledger = ChipLedger({"player1": 1000, "player2": 1000})
        pot_manager = PotManager(ledger)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(pot_manager, "PotManager")
        
        # 创建边池
        player_bets = {"player1": 100, "player2": 100}
        pot_manager.calculate_side_pots(player_bets)
        
        # player1获胜
        winners = {"player1": 100}
        hand_strengths = {"player1": 100, "player2": 50}
        
        initial_balance = ledger.get_balance("player1")
        result = pot_manager.distribute_winnings(winners, hand_strengths)
        
        assert result.total_distributed == 200
        assert result.distributions["player1"] == 200
        assert ledger.get_balance("player1") == initial_balance + 200


class TestBetAction:
    """下注行动测试"""
    
    def test_bet_action_creation_valid(self):
        """测试创建有效的下注行动"""
        action = BetAction(
            player_id="player1",
            bet_type=BetType.RAISE,
            amount=100,
            timestamp=time.time()
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(action, "BetAction")
        
        assert action.player_id == "player1"
        assert action.bet_type == BetType.RAISE
        assert action.amount == 100
        assert action.is_aggressive_action() is True
        assert action.involves_chips() is True
    
    def test_bet_action_validation_errors(self):
        """测试下注行动验证错误"""
        # 测试FOLD操作不能有金额
        with pytest.raises(ValueError, match="FOLD操作的金额必须为0"):
            BetAction(
                player_id="player1",
                bet_type=BetType.FOLD,
                amount=100,
                timestamp=time.time()
            )
        
        # 测试RAISE操作必须有金额
        with pytest.raises(ValueError, match="RAISE操作的金额必须大于0"):
            BetAction(
                player_id="player1",
                bet_type=BetType.RAISE,
                amount=0,
                timestamp=time.time()
            )


class TestChipConservation:
    """筹码守恒测试"""
    
    def test_chip_conservation_in_betting_round(self):
        """测试下注轮次中的筹码守恒"""
        initial_balances = {"player1": 1000, "player2": 1000, "player3": 1000}
        ledger = ChipLedger(initial_balances)
        engine = BettingEngine(ledger, big_blind=20)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ledger, "ChipLedger")
        CoreUsageChecker.verify_real_objects(engine, "BettingEngine")
        
        initial_total = ledger.get_total_chips()
        
        # 开始新轮次
        engine.start_new_round(["player1", "player2", "player3"], "player1", "player2")
        
        # 执行一系列下注行动
        engine.execute_player_action("player3", BetType.RAISE, 40)
        engine.execute_player_action("player1", BetType.CALL)
        engine.execute_player_action("player2", BetType.FOLD)
        
        # 验证筹码守恒 - 筹码总数应该保持不变
        # 注意：筹码被扣除但仍在系统中（在底池中）
        final_total = ledger.get_total_chips()
        pot_total = engine.get_total_pot()
        
        # 系统中的总筹码 = 玩家账户中的筹码 + 底池中的筹码
        assert initial_total == final_total + pot_total
    
    def test_chip_conservation_in_pot_distribution(self):
        """测试边池分配中的筹码守恒"""
        initial_balances = {"player1": 1000, "player2": 1000, "player3": 1000}
        ledger = ChipLedger(initial_balances)
        pot_manager = PotManager(ledger)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ledger, "ChipLedger")
        CoreUsageChecker.verify_real_objects(pot_manager, "PotManager")
        
        # 模拟下注
        player_bets = {"player1": 100, "player2": 200, "player3": 150}
        total_bet = sum(player_bets.values())
        
        # 从玩家账户扣除下注金额
        for player_id, bet_amount in player_bets.items():
            ledger.deduct_chips(player_id, bet_amount, f"下注 {bet_amount}")
        
        initial_total_after_bets = ledger.get_total_chips()
        
        # 计算边池
        side_pots = pot_manager.calculate_side_pots(player_bets)
        
        # 分配奖金（player2获胜）
        winners = {"player2": 100}
        hand_strengths = {"player1": 50, "player2": 100, "player3": 75}
        result = pot_manager.distribute_winnings(winners, hand_strengths)
        
        # 验证筹码守恒 - 分配后的总筹码应该等于分配前的总筹码
        final_total = ledger.get_total_chips()
        assert final_total == initial_total_after_bets + result.total_distributed
        assert result.total_distributed == total_bet


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 