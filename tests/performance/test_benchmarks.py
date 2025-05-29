#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能基准测试

从comprehensive_test.py中提取性能相关测试，
专注于游戏各组件的性能表现和基准测试。
"""

import time
import gc
import unittest
import psutil
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_game_logic.game.game_controller import GameController
from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.core.enums import Action, ActionType, GamePhase, SeatStatus
from core_game_logic.core.exceptions import InvalidActionError
from core_game_logic.evaluator.simple_evaluator import SimpleEvaluator as HandEvaluator
from tests.common.base_tester import BaseTester
from tests.common.test_helpers import format_test_header, performance_timer, ActionHelper, TestValidator, GameStateHelper
from tests.common.data_structures import TestResult, TestScenario
from core_game_logic.core.deck import Deck


class PerformanceTester(unittest.TestCase):
    """性能基准测试器"""
    
    # 性能基准值（毫秒）
    BENCHMARKS = {
        'deck_shuffle': 1.0,        # 牌组洗牌：1ms
        'hand_evaluation': 5.0,     # 手牌评估：5ms
        'single_hand': 100.0,       # 单手牌游戏：100ms
        'hundred_hands': 5000.0,    # 100手牌：5秒
        'game_startup': 50.0        # 游戏启动：50ms
    }
    
    def setUp(self):
        """设置测试环境"""
        print("\n" + format_test_header("性能基准测试"))
        
        # 创建基础测试器以复用其方法
        self.base_tester = BaseTester("Performance")
        
        # 初始化性能测试所需的组件
        scenario = TestScenario(
            name="性能测试场景",
            players_count=4,
            starting_chips=[1000, 1000, 1000, 1000],
            dealer_position=0,
            expected_behavior={},
            description="4人德州扑克性能测试"
        )
        
        self.game_state = self.base_tester.create_scenario_game(scenario)
        self.controller = GameController(self.game_state)
        self.evaluator = HandEvaluator()
        self.deck = Deck()
        
        # 性能统计
        self.performance_stats = {}
    
    def test_deck_shuffle_performance(self):
        """测试洗牌性能"""
        print("开始测试洗牌性能...")
        
        deck = self.controller.game_state.deck
        times = []
        
        # 执行多次洗牌并测量时间
        for i in range(100):
            start_time = time.perf_counter()
            deck.shuffle()
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # 转换为毫秒
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"  洗牌性能统计:")
        print(f"    平均时间: {avg_time:.3f}ms")
        print(f"    最大时间: {max_time:.3f}ms")
        print(f"    最小时间: {min_time:.3f}ms")
        
        # 性能基准检查
        self.assertLess(avg_time, self.BENCHMARKS['deck_shuffle'], 
                       f"洗牌平均时间 {avg_time:.3f}ms 超过基准 {self.BENCHMARKS['deck_shuffle']}ms")
        
        print("✓ 洗牌性能测试通过")
    
    def test_hand_evaluation_performance(self):
        """测试手牌评估性能"""
        print("开始测试手牌评估性能...")
        
        times = []
        
        # 生成测试手牌
        for i in range(1000):
            # 每次创建新的牌组
            deck = Deck()
            deck.shuffle()
            
            hand_cards = [deck.deal_card(), deck.deal_card()]
            community_cards = [deck.deal_card() for _ in range(5)]
            
            start_time = time.perf_counter()
            result = self.evaluator.evaluate_hand(hand_cards, community_cards)
            end_time = time.perf_counter()
            
            times.append((end_time - start_time) * 1000)  # 转换为毫秒
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        percentile_95 = sorted(times)[int(len(times) * 0.95)]
        
        print(f"  手牌评估性能统计 (1000次测试):")
        print(f"    平均时间: {avg_time:.3f}ms")
        print(f"    最大时间: {max_time:.3f}ms")
        print(f"    95%时间: {percentile_95:.3f}ms")
        
        # 性能基准检查
        self.assertLess(avg_time, self.BENCHMARKS['hand_evaluation'],
                       f"手牌评估平均时间 {avg_time:.3f}ms 超过基准 {self.BENCHMARKS['hand_evaluation']}ms")
        
        print("✓ 手牌评估性能测试通过")
    
    def test_single_hand_performance(self):
        """测试单手牌完整流程性能"""
        print("开始测试单手牌完整流程性能...")
        
        times = []
        
        # 执行多次完整手牌流程
        for i in range(50):
            start_time = time.perf_counter()
            
            # 开始新手牌
            self.controller.start_new_hand()
            
            # 模拟完整流程
            self._simulate_fast_hand()
            
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # 转换为毫秒
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"  单手牌性能统计 (50次测试):")
        print(f"    平均时间: {avg_time:.3f}ms")
        print(f"    最大时间: {max_time:.3f}ms")
        print(f"    最小时间: {min_time:.3f}ms")
        
        # 性能基准检查
        self.assertLess(avg_time, self.BENCHMARKS['single_hand'],
                       f"单手牌平均时间 {avg_time:.3f}ms 超过基准 {self.BENCHMARKS['single_hand']}ms")
        
        print("✓ 单手牌性能测试通过")
    
    def test_hundred_hands_performance(self):
        """测试100手牌连续性能"""
        print("开始测试100手牌连续性能...")
        
        start_time = time.perf_counter()
        
        # 连续执行100手牌
        for hand_num in range(100):
            if hand_num % 20 == 0:
                print(f"  进度: {hand_num}/100 手牌...")
            
            self.controller.start_new_hand()
            self._simulate_fast_hand()
        
        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000  # 转换为毫秒
        avg_per_hand = total_time / 100
        
        print(f"  100手牌性能统计:")
        print(f"    总时间: {total_time:.1f}ms")
        print(f"    平均每手牌: {avg_per_hand:.3f}ms")
        
        # 性能基准检查
        self.assertLess(total_time, self.BENCHMARKS['hundred_hands'],
                       f"100手牌总时间 {total_time:.1f}ms 超过基准 {self.BENCHMARKS['hundred_hands']}ms")
        
        print("✓ 100手牌性能测试通过")
    
    def test_memory_usage(self):
        """测试内存使用情况"""
        print("开始测试内存使用情况...")
        
        # 获取初始内存使用
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"  初始内存使用: {initial_memory:.1f}MB")
        
        # 执行大量游戏操作
        for round_num in range(10):
            for hand_num in range(50):
                self.controller.start_new_hand()
                self._simulate_fast_hand()
            
            # 强制垃圾回收
            gc.collect()
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            print(f"  轮次 {round_num + 1}: 内存使用 {current_memory:.1f}MB (增长 {memory_increase:.1f}MB)")
            
            # 检查内存泄漏（增长不应超过50MB）
            self.assertLess(memory_increase, 50.0, 
                           f"内存增长 {memory_increase:.1f}MB 可能存在内存泄漏")
        
        print("✓ 内存使用测试通过")
    
    def test_game_startup_performance(self):
        """测试游戏启动性能"""
        print("开始测试游戏启动性能...")
        
        times = []
        
        # 多次测试游戏启动时间
        for i in range(20):
            start_time = time.perf_counter()
            
            # 创建新游戏实例
            test_scenario = TestScenario(
                name="性能测试场景",
                players_count=4,
                starting_chips=[1000, 1000, 1000, 1000],
                dealer_position=0,
                expected_behavior={},
                description="游戏启动性能测试"
            )
            test_state = self.base_tester.create_scenario_game(test_scenario)
            new_controller = GameController(test_state)
            
            # 玩家已在test_state中创建，无需重复添加
            
            # 初始化第一手牌
            new_controller.start_new_hand()
            
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # 转换为毫秒
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        print(f"  游戏启动性能统计 (20次测试):")
        print(f"    平均时间: {avg_time:.3f}ms")
        print(f"    最大时间: {max_time:.3f}ms")
        
        # 性能基准检查
        self.assertLess(avg_time, self.BENCHMARKS['game_startup'],
                       f"游戏启动平均时间 {avg_time:.3f}ms 超过基准 {self.BENCHMARKS['game_startup']}ms")
        
        print("✓ 游戏启动性能测试通过")
    
    def test_stress_scenario(self):
        """压力测试场景"""
        print("开始压力测试场景...")
        
        start_time = time.perf_counter()
        operations = 0
        
        # 持续压力测试（5秒）
        while time.perf_counter() - start_time < 5.0:
            self.controller.start_new_hand()
            self._simulate_fast_hand()
            operations += 1
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        ops_per_second = operations / total_time
        
        print(f"  压力测试统计:")
        print(f"    测试时间: {total_time:.1f}秒")
        print(f"    完成操作: {operations}次")
        print(f"    操作速率: {ops_per_second:.1f}次/秒")
        
        # 性能基准检查（至少每秒10次操作）
        self.assertGreater(ops_per_second, 10.0,
                          f"操作速率 {ops_per_second:.1f}次/秒 低于最低要求 10.0次/秒")
        
        print("✓ 压力测试通过")
    
    def _simulate_fast_hand(self):
        """快速模拟一手牌（最少操作）"""
        # 所有玩家直接check到底，快速结束
        from core_game_logic.core.enums import GamePhase
        
        phases = [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]
        
        for phase in phases:
            current_phase = self.controller.game_state.phase
            if current_phase == phase:
                # 快速完成下注轮
                max_checks = 10
                check_count = 0
                
                while not self.controller.game_state.is_betting_round_complete() and check_count < max_checks:
                    current_player = self.controller.game_state.get_current_player()
                    if current_player is None:
                        break
                    
                    try:
                        # 尝试check - 使用ActionHelper创建正确的Action
                        action = ActionHelper.create_current_player_action(
                            self.controller.game_state, ActionType.CHECK, 0
                        )
                        self.controller.process_action(action)
                    except Exception:  # 捕获所有异常，不只是InvalidActionError
                        # 如果check失败，fold - 使用ActionHelper创建正确的Action
                        action = ActionHelper.create_current_player_action(
                            self.controller.game_state, ActionType.FOLD, 0
                        )
                        self.controller.process_action(action)
                    
                    check_count += 1
                
                # 进入下一阶段
                if phase != GamePhase.RIVER:
                    self.controller.advance_phase()
        
        # 进入showdown并结算
        if self.controller.game_state.phase == GamePhase.RIVER:
            self.controller.advance_phase()
        
        if self.controller.game_state.phase == GamePhase.SHOWDOWN:
            self.controller.determine_winners()


def run_performance_tests():
    """运行性能测试"""
    print("=" * 60)
    print("性能基准测试套件")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(PerformanceTester)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果 - 修复构造函数参数
    return TestResult(
        scenario_name="性能基准测试套件",
        test_name="性能基准测试",
        passed=result.wasSuccessful(),
        expected="所有性能测试通过",
        actual=f"成功: {result.testsRun - len(result.failures) - len(result.errors)}, "
               f"失败: {len(result.failures)}, 错误: {len(result.errors)}",
        details=f"总测试数: {result.testsRun}, 成功: {result.testsRun - len(result.failures) - len(result.errors)}, "
                f"失败: {len(result.failures)}, 错误: {len(result.errors)}"
    )


if __name__ == "__main__":
    print(f"性能测试开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    result = run_performance_tests()
    print(f"\n测试结果: {result}")
    exit(0 if result.passed else 1) 