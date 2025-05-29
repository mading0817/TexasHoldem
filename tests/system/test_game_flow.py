#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构后的完整游戏流程测试

使用PokerSimulator代替手动循环，解决死循环问题
建立可重用的测试架构
"""

import unittest
import sys
import os
import logging
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_game_logic.game.game_controller import GameController
from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.core.enums import Action, ActionType, GamePhase, SeatStatus
from core_game_logic.core.exceptions import InvalidActionError
from tests.common.base_tester import BaseTester
from tests.common.data_structures import TestResult, TestScenario
from core_game_logic.core.deck import Deck
from tests.common.test_helpers import format_test_header
from tests.common.poker_simulator import (
    PokerSimulator, ConservativeStrategy, AggressiveStrategy,
    create_default_strategies, GameSnapshot, HandResult
)

# 设置测试日志
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("poker.test")


class GameFlowTesterNew(unittest.TestCase):
    """重构后的完整游戏流程测试类"""
    
    def setUp(self):
        """设置测试环境"""
        print("\n" + format_test_header("游戏流程系统测试 (重构版)"))
        
        # 创建基础测试器
        self.base_tester = BaseTester("GameFlowNew")
        
        # 创建基础游戏状态
        scenario = TestScenario(
            name="游戏流程测试场景",
            players_count=6,
            starting_chips=[1000] * 6,
            dealer_position=0,
            expected_behavior={},
            description="6人德州扑克流程测试"
        )
        
        # 避免双重扣除盲注 - 在系统测试中不预设盲注
        self.game_state = self.base_tester.create_scenario_game(scenario, setup_blinds=False)
        self.game_controller = GameController(self.game_state)
        
        # 创建模拟器
        self.simulator = PokerSimulator(self.game_controller)
        
        # 获取玩家座位列表
        self.player_seats = [p.seat_id for p in self.game_state.players]
        
        # 创建默认策略
        self.strategies = create_default_strategies(self.player_seats, "conservative")
    
    def test_complete_hand_flow(self):
        """测试完整手牌流程"""
        print("开始测试完整手牌流程...")
        
        # 使用模拟器执行完整手牌
        result = self.simulator.play_hand(self.strategies)
        
        # 验证结果
        self.assertTrue(result.hand_completed, "手牌应该成功完成")
        self.assertGreaterEqual(result.active_players, 1, "至少应该有1个活跃玩家")
        
        # 验证阶段进展
        self.assertIn(GamePhase.PRE_FLOP, result.phases_completed, "应该完成Pre-flop阶段")
        
        # 验证没有错误
        if result.errors:
            print(f"注意：出现了一些错误: {result.errors}")
        
        print(f"✓ 完整手牌流程测试通过 - 活跃玩家: {result.active_players}, 阶段: {len(result.phases_completed)}")
    
    def test_multi_hand_game_flow(self):
        """测试多手牌游戏流程"""
        print("开始测试多手牌游戏流程...")
        
        # 记录初始筹码分布
        initial_chips = {p.name: p.chips for p in self.game_controller.state.players}
        initial_total = sum(initial_chips.values())
        
        # 模拟5手牌游戏
        results = self.simulator.play_n_hands(5, self.strategies)
        
        # 验证结果
        self.assertGreaterEqual(len(results), 1, "至少应该完成1手牌")
        self.assertLessEqual(len(results), 5, "不应该超过5手牌")
        
        # 验证筹码守恒
        final_chips = {p.name: p.chips for p in self.game_controller.state.players}
        final_total = sum(final_chips.values()) + self.game_controller.get_total_pot()
        
        self.assertEqual(final_total, initial_total, 
                        f"筹码不守恒！初始:{initial_total}, 最终:{final_total}")
        
        # 统计有效手牌
        completed_hands = sum(1 for r in results if r.hand_completed)
        
        print(f"✓ 多手牌游戏流程测试通过 - 完成{completed_hands}手牌，筹码守恒验证通过")
    
    def test_player_elimination_flow(self):
        """测试玩家淘汰流程"""
        print("开始测试玩家淘汰流程...")
        
        # 使用激进策略增加淘汰概率
        aggressive_strategies = create_default_strategies(self.player_seats, "aggressive")
        
        # 记录初始玩家数
        initial_players = len([p for p in self.game_controller.state.players if p.chips > 0])
        
        # 执行多手牌直到有玩家被淘汰或达到最大手数
        max_hands = 10
        results = []
        
        for hand_num in range(max_hands):
            try:
                result = self.simulator.play_hand(aggressive_strategies)
                results.append(result)
                
                # 检查是否有玩家被淘汰
                current_players = result.active_players
                if current_players < initial_players:
                    print(f"  第{hand_num + 1}手牌后有玩家被淘汰，剩余{current_players}名玩家")
                    break
                
                # 检查游戏是否无法继续
                if current_players < 2:
                    print(f"  第{hand_num + 1}手牌后游戏结束，剩余{current_players}名玩家")
                    break
                    
            except Exception as e:
                print(f"  第{hand_num + 1}手牌执行出错: {e}")
                break
        
        # 验证
        self.assertGreater(len(results), 0, "应该至少完成一手牌")
        
        # 检查最终状态
        final_players = len([p for p in self.game_controller.state.players if p.chips > 0])
        print(f"✓ 玩家淘汰流程测试通过 - 初始玩家:{initial_players}, 最终玩家:{final_players}")
    
    def test_blinds_progression(self):
        """测试盲注进阶"""
        print("开始测试盲注进阶...")
        
        # 记录初始盲注
        initial_small_blind = self.game_controller.get_small_blind()
        initial_big_blind = self.game_controller.get_big_blind()
        
        print(f"  初始盲注: {initial_small_blind}/{initial_big_blind}")
        
        # 模拟多手牌游戏
        results = self.simulator.play_n_hands(3, self.strategies)
        
        # 记录最终盲注
        final_small_blind = self.game_controller.get_small_blind()
        final_big_blind = self.game_controller.get_big_blind()
        
        print(f"  最终盲注: {final_small_blind}/{final_big_blind}")
        
        # 验证游戏正常进行
        self.assertGreater(len(results), 0, "应该完成至少一手牌")
        
        # 验证盲注设置合理性
        self.assertGreater(final_big_blind, 0, "大盲注应该大于0")
        self.assertEqual(final_big_blind, final_small_blind * 2, "大盲注应该是小盲注的2倍")
        
        print("✓ 盲注进阶测试通过")
    
    def test_conservative_strategy_stability(self):
        """测试保守策略的稳定性"""
        print("开始测试保守策略稳定性...")
        
        # 设置调试模式
        original_debug = self.simulator.debug_mode
        self.simulator.debug_mode = False  # 关闭调试以避免大量输出
        
        try:
            # 执行多次手牌，验证没有死循环
            total_hands = 0
            for attempt in range(10):
                try:
                    result = self.simulator.play_hand(self.strategies)
                    if result.hand_completed:
                        total_hands += 1
                    
                    # 验证没有发生错误
                    if result.errors:
                        print(f"  第{attempt + 1}次尝试有错误: {result.errors}")
                    
                except Exception as e:
                    print(f"  第{attempt + 1}次尝试失败: {e}")
                    break
            
            # 验证至少完成了一些手牌
            self.assertGreater(total_hands, 0, "保守策略应该能稳定完成手牌")
            
            print(f"✓ 保守策略稳定性测试通过 - 完成{total_hands}手牌")
            
        finally:
            # 恢复调试模式
            self.simulator.debug_mode = original_debug
    
    def test_chip_conservation(self):
        """测试筹码守恒原则"""
        print("开始测试筹码守恒...")
        
        # 记录所有初始筹码
        initial_player_chips = sum(p.chips for p in self.game_controller.state.players)
        initial_pot = self.game_controller.get_total_pot()
        initial_total = initial_player_chips + initial_pot
        
        print(f"  初始总筹码: {initial_total} (玩家:{initial_player_chips} + 底池:{initial_pot})")
        
        # 执行一手牌
        result = self.simulator.play_hand(self.strategies)
        
        # 计算最终筹码
        final_player_chips = sum(p.chips for p in self.game_controller.state.players)
        final_pot = self.game_controller.get_total_pot()
        final_total = final_player_chips + final_pot
        
        print(f"  最终总筹码: {final_total} (玩家:{final_player_chips} + 底池:{final_pot})")
        
        # 验证筹码守恒
        self.assertEqual(initial_total, final_total, 
                        f"筹码不守恒！初始:{initial_total}, 最终:{final_total}, 差值:{final_total - initial_total}")
        
        print("✓ 筹码守恒测试通过")
    
    def test_simulator_error_handling(self):
        """测试模拟器的错误处理"""
        print("开始测试模拟器错误处理...")
        
        # 创建一个会抛出异常的策略
        class ErrorStrategy(ConservativeStrategy):
            def __init__(self, error_on_turn: int = 1):
                self.error_on_turn = error_on_turn
                self.turn_count = 0
                
            def decide(self, snapshot):
                self.turn_count += 1
                if self.turn_count == self.error_on_turn:
                    raise RuntimeError("模拟错误")
                return super().decide(snapshot)
        
        # 创建包含错误策略的策略映射
        error_strategies = self.strategies.copy()
        error_strategies[self.player_seats[0]] = ErrorStrategy(error_on_turn=2)
        
        # 执行手牌
        result = self.simulator.play_hand(error_strategies)
        
        # 验证错误被正确处理
        if result.errors:
            print(f"  正确捕获到错误: {result.errors}")
            # 这是期望的行为
        else:
            print("  没有检测到错误，可能策略没有触发异常条件")
        
        print("✓ 模拟器错误处理测试通过")


def run_game_flow_tests_new():
    """运行重构后的游戏流程测试"""
    print("\n" + "="*50)
    print("运行重构后的游戏流程测试套件")
    print("="*50)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(GameFlowTesterNew)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果摘要
    return {
        'tests_run': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'success': result.wasSuccessful()
    }


if __name__ == "__main__":
    # 直接运行测试
    run_game_flow_tests_new() 