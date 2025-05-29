#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克测试基础类
包含所有测试类使用的通用方法和属性
从原comprehensive_test.py的TexasHoldemAdvancedTester中提取通用部分
"""

import sys
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# 添加项目根目录到路径，确保可以导入核心模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 导入核心游戏逻辑
from core_game_logic.core.enums import ActionType, GamePhase, Suit, Rank, Action, SeatStatus
from core_game_logic.core.card import Card
from core_game_logic.core.deck import Deck
from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.betting.action_validator import ActionValidator
from core_game_logic.betting.pot_manager import PotManager

# 导入测试数据结构
from .data_structures import TestResult, TestScenario, TestSuite


class BaseTester:
    """
    基础测试器类
    为所有具体测试类提供通用的测试基础设施
    """
    
    def __init__(self, suite_name: str = "Base"):
        """
        初始化基础测试器
        
        Args:
            suite_name: 测试套件名称
        """
        print(f"[DEBUG] BaseTester.__init__ starting for {suite_name}")
        self.validator = ActionValidator()
        self.suite = TestSuite(
            name=suite_name,
            category="General",
            results=[]
        )
        
        # 兼容原代码的属性
        self.test_results: List[TestResult] = self.suite.results
        self.scenarios_passed = 0
        self.scenarios_total = 0
        self.total_tests = 0
        self.passed_tests = 0
        
    def log_test(self, scenario_name: str, test_name: str, passed: bool, 
                 expected: Any = None, actual: Any = None, details: str = ""):
        """
        记录测试结果的通用方法
        
        Args:
            scenario_name: 场景名称
            test_name: 测试名称
            passed: 是否通过
            expected: 预期结果
            actual: 实际结果
            details: 详细信息
        """
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            
        status = "[PASSED]" if passed else "[FAILED]"
        
        print(f"  {status} {test_name}")
        if expected is not None or actual is not None:
            print(f"    期望: {expected}")
            print(f"    实际: {actual}")
        if details:
            print(f"    详情: {details}")
        
        # 记录结果到测试套件
        result = TestResult(
            scenario_name=scenario_name,
            test_name=test_name, 
            passed=passed,
            expected=expected,
            actual=actual,
            details=details
        )
        self.test_results.append(result)
        
        # 更新套件统计
        self.suite.total_tests = self.total_tests
        self.suite.passed_tests = self.passed_tests
        
    def create_scenario_game(self, scenario: TestScenario, setup_blinds: bool = True) -> GameState:
        """
        根据测试场景创建游戏状态
        
        Args:
            scenario: 测试场景配置
            setup_blinds: 是否设置盲注（默认True，规则测试需要）
            
        Returns:
            配置好的游戏状态对象
            
        注意：不会手动发牌，发牌由相应的Phase处理，避免作弊行为
        """
        players = []
        names = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack"]
        
        for i in range(scenario.players_count):
            chips = scenario.starting_chips[i] if i < len(scenario.starting_chips) else scenario.starting_chips[0]
            player = Player(
                seat_id=i,
                name=names[i] if i < len(names) else f"Player{i}",
                chips=chips
            )
            # 确保玩家状态正确
            if chips > 0:
                player.status = SeatStatus.ACTIVE
            else:
                player.status = SeatStatus.OUT
            players.append(player)
        
        state = GameState(
            players=players,
            dealer_position=scenario.dealer_position,
            small_blind=1,
            big_blind=2
        )
        
        # 重置玩家状态为新手牌
        for player in state.players:
            player.reset_for_new_hand()
            # 确保玩家状态正确
            if player.chips > 0:
                player.status = SeatStatus.ACTIVE
            else:
                player.status = SeatStatus.OUT
        
        # 设置庄家标记
        for player in state.players:
            player.is_dealer = (player.seat_id == state.dealer_position)
        
        # 根据setup_blinds参数决定是否设置盲注
        if setup_blinds:
            # 为规则测试设置盲注，以便验证盲注系统的正确性
            state.set_blinds()
        # 否则，让GameController的start_new_hand方法来处理，避免重复扣除盲注的问题
        
        # 初始化其他游戏状态
        state.community_cards = []
        state.phase = GamePhase.PRE_FLOP
        state.street_index = 0
        state.last_raiser = None
        
        # 初始化牌组（用于测试）
        state.deck = Deck()
        state.deck.shuffle()
        
        # 注意：不在这里初始化牌组和发牌，让PreFlopPhase来处理，避免作弊
        
        return state
    
    def print_test_summary(self):
        """打印测试总结"""
        print(f"\n{'='*60}")
        print(f"测试套件: {self.suite.name}")
        print(f"总测试数: {self.total_tests}")
        print(f"通过数: {self.passed_tests}")
        print(f"失败数: {self.total_tests - self.passed_tests}")
        print(f"成功率: {self.suite.success_rate:.1f}%")
        print(f"套件状态: {'通过' if self.suite.is_passed else '失败'}")
        print(f"{'='*60}")
        
    def get_failed_tests(self) -> List[TestResult]:
        """获取失败的测试列表"""
        return [result for result in self.test_results if not result.passed]
    
    def get_passed_tests(self) -> List[TestResult]:
        """获取通过的测试列表"""
        return [result for result in self.test_results if result.passed]
    
    def reset_results(self):
        """重置测试结果"""
        self.test_results.clear()
        self.suite.results.clear()
        self.total_tests = 0
        self.passed_tests = 0
        self.scenarios_passed = 0
        self.scenarios_total = 0
        self.suite.total_tests = 0
        self.suite.passed_tests = 0 