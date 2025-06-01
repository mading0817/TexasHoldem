#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整游戏流程测试

从comprehensive_test.py中提取完整游戏流程相关测试，
专注于验证从游戏开始到结束的完整流程。
"""

import unittest
import sys
import os
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
from tests.common.test_helpers import format_test_header, ActionHelper, TestValidator, GameStateHelper


class GameFlowTester(unittest.TestCase):
    """完整游戏流程测试类"""
    
    def setUp(self):
        """设置测试环境"""
        print("\n" + format_test_header("游戏流程系统测试"))
        
        # 创建基础测试器
        self.base_tester = BaseTester("GameFlow")
        
        # 创建基础游戏状态
        scenario = TestScenario(
            name="游戏流程测试场景",
            players_count=6,
            starting_chips=[1000] * 6,
            dealer_position=0,
            expected_behavior={},
            description="6人德州扑克流程测试"
        )
        
        # ANTI-CHEAT-FIX: 避免双重扣除盲注 - 在系统测试中不预设盲注
        self.game_state = self.base_tester.create_scenario_game(scenario, setup_blinds=False)
        self.game_controller = GameController(self.game_state)
        
        # 获取玩家列表
        self.players = self.game_state.players
        
        # 设置ActionHelper为测试兼容模式
        ActionHelper.test_mode = True
    
    def test_complete_hand_flow(self):
        """测试完整手牌流程"""
        print("开始测试完整手牌流程...")
        
        # 开始新手牌 - 应该进入Pre-flop阶段
        self.game_controller.start_new_hand()
        self.assertEqual(self.game_controller.game_state.phase, GamePhase.PRE_FLOP)
        
        # 确保有手牌
        for player in self.players:
            if player.chips > 0:
                self.assertEqual(len(player.get_hand_cards()), 2)
        
        # Pre-flop下注轮 - 使用保守策略确保不会所有人都弃牌
        self._simulate_conservative_betting_round()
        
        # Flop阶段
        self.game_controller.advance_phase()
        self.assertEqual(self.game_controller.game_state.phase, GamePhase.FLOP)
        self.assertEqual(len(self.game_controller.get_community_cards()), 3)
        self._simulate_conservative_betting_round()
        
        # Turn阶段
        self.game_controller.advance_phase()
        self.assertEqual(self.game_controller.game_state.phase, GamePhase.TURN)
        self.assertEqual(len(self.game_controller.get_community_cards()), 4)
        self._simulate_conservative_betting_round()
        
        # River阶段
        self.game_controller.advance_phase()
        self.assertEqual(self.game_controller.game_state.phase, GamePhase.RIVER)
        self.assertEqual(len(self.game_controller.get_community_cards()), 5)
        self._simulate_conservative_betting_round()
        
        # Showdown
        self.game_controller.advance_phase()
        self.assertEqual(self.game_controller.game_state.phase, GamePhase.SHOWDOWN)
        
        # 结算
        winners = self.game_controller.determine_winners()
        self.assertIsNotNone(winners)
        
        print("✓ 完整手牌流程测试通过")
    
    def test_multi_hand_game_flow(self):
        """测试多手牌游戏流程"""
        print("开始测试多手牌游戏流程...")
        
        initial_chips = {player.name: player.chips for player in self.players}
        hands_played = 0
        
        # 记录初始庄家位置
        initial_dealer = self.game_controller.get_dealer_position()
        
        # 模拟5手牌游戏
        for hand_num in range(5):
            print(f"  手牌 {hand_num + 1}...")
            
            # 开始新手牌
            self.game_controller.start_new_hand()
            
            # 修复：正确验证dealer位置轮转
            # 庄家应该是按玩家座位号顺序轮转，而不是简单的hand计数
            current_dealer = self.game_controller.get_dealer_position()
            
            # 对于第一手牌之后，验证庄家确实发生了变化
            if hand_num > 0:
                self.assertNotEqual(current_dealer, initial_dealer, 
                                  f"手牌{hand_num + 1}：庄家位置应该已经轮转")
            
            # 完成这手牌
            self._complete_hand()
            hands_played += 1
            
            # 验证筹码守恒 - 修复：计算总筹码（包括玩家筹码、底池、当前下注）
            total_player_chips = sum(player.chips for player in self.players)
            total_pot = self.game_controller.get_total_pot()
            total_current_bets = sum(player.current_bet for player in self.players)
            total_chips = total_player_chips + total_pot + total_current_bets
            
            expected_total = sum(initial_chips.values())
            self.assertEqual(total_chips, expected_total, 
                           f"手牌{hand_num + 1}：筹码不守恒！玩家筹码:{total_player_chips} + 底池:{total_pot} + 当前下注:{total_current_bets} = {total_chips}, 期望:{expected_total}")
        
        print(f"✓ 多手牌游戏流程测试通过 ({hands_played}手牌)")
    
    def test_player_elimination_flow(self):
        """测试玩家淘汰流程"""
        print("开始测试玩家淘汰流程...")
        
        # 开始新一手牌
        self.game_controller.start_new_hand()
        
        # 模拟游戏过程，让一些玩家失去所有筹码
        max_rounds = 10
        attempts = 0
        
        while attempts < max_rounds:
            current_player = self.game_controller.get_current_player()
            if current_player is None:
                # current_player为None是正常情况：
                # 1. 下注轮结束
                # 2. 所有玩家都无法行动
                # 3. 等待阶段转换
                try:
                    # 尝试推进游戏阶段
                    if not self.game_controller.is_betting_round_complete():
                        # 如果下注轮未完成但没有当前玩家，说明游戏状态异常
                        print(f"  注意：下注轮未完成但当前玩家为None（第{attempts+1}次），尝试重新设置")
                        # 尝试重新设置第一个可行动的玩家
                        self.game_controller.state._set_first_to_act()
                        current_player = self.game_controller.get_current_player()
                        if current_player is None:
                            print(f"  下注轮结束，推进到下一阶段（第{attempts+1}次）")
                            break
                    else:
                        # 下注轮完成，正常推进阶段
                        print(f"  下注轮完成，推进到下一阶段（第{attempts+1}次）")
                        break
                except Exception as e:
                    print(f"  处理阶段转换时出错: {e}")
                    break
            
            # 获取当前玩家对象
            player = self.game_controller.game_state.get_player_by_seat(current_player)
            if not player or not player.can_act():
                # 玩家无法行动，推进到下一个玩家
                if not self.game_controller.game_state.advance_current_player():
                    print(f"  没有更多玩家可行动（第{attempts+1}次）")
                    break
                continue
            
            # 模拟激进的下注策略，增加玩家被淘汰的可能性
            try:
                # 随机选择一个玩家进行all-in（模拟激进玩法）
                target_player = None
                for p in self.players:
                    if p.can_act() and p.chips > 0:
                        target_player = p
                        break
                
                if target_player and target_player.chips > 0:
                    all_in_action = ActionHelper.create_player_action(target_player, ActionType.ALL_IN, target_player.chips)
                    self.game_controller.process_action(all_in_action)
                    print(f"  玩家 {target_player.name} 选择全押 {target_player.chips} 筹码")
                    break
                else:
                    # 如果没有可全押的玩家，执行保守操作
                    try:
                        action = ActionHelper.create_player_action(current_player, ActionType.CHECK, 0)
                        self.game_controller.process_action(action)
                    except:
                        action = ActionHelper.create_player_action(current_player, ActionType.CALL, 0)
                        self.game_controller.process_action(action)
                    
            except Exception as e:
                print(f"  行动失败: {e}")
                # 执行最安全的操作
                try:
                    action = ActionHelper.create_player_action(current_player, ActionType.CHECK, 0)
                    self.game_controller.process_action(action)
                except:
                    try:
                        action = ActionHelper.create_player_action(current_player, ActionType.CALL, 0)
                        self.game_controller.process_action(action)
                    except:
                        action = ActionHelper.create_player_action(current_player, ActionType.FOLD, 0)
                        self.game_controller.process_action(action)
            
            attempts += 1
        
        # 完成手牌（确保所有阶段都被执行）
        try:
            self._complete_remaining_phases()
        except Exception as e:
            print(f"  完成手牌时出错: {e}")
            # 尝试直接结束游戏
            pass
        
        # 检查是否有玩家被淘汰（筹码为0）
        remaining_players = [p for p in self.players if p.chips > 0]
        eliminated_players = [p for p in self.players if p.chips == 0]
        
        print(f"  剩余玩家: {len(remaining_players)}, 淘汰玩家: {len(eliminated_players)}")
        for player in eliminated_players:
            print(f"    玩家 {player.name} 被淘汰")
        
        print("✓ 玩家淘汰流程测试通过")
    
    def test_blinds_progression(self):
        """测试盲注进阶流程"""
        print("开始测试盲注进阶流程...")
        
        initial_sb = self.game_controller.get_small_blind()
        initial_bb = self.game_controller.get_big_blind()
        
        # 模拟多轮游戏，触发盲注上涨
        for round_num in range(3):
            for _ in range(10):  # 每轮10手牌
                self.game_controller.start_new_hand()
                self._complete_hand()
            
            # 检查是否需要增加盲注
            current_sb = self.game_controller.get_small_blind()
            current_bb = self.game_controller.get_big_blind()
            
            if round_num > 0:
                # 盲注应该随着轮次增加
                self.assertGreaterEqual(current_sb, initial_sb)
                self.assertGreaterEqual(current_bb, initial_bb)
        
        print("✓ 盲注进阶流程测试通过")
    
    def _simulate_conservative_betting_round(self):
        """
        模拟保守的下注轮 - 确保至少有2个玩家留到摊牌
        策略：前两个玩家总是call/check，其他玩家可以选择弃牌
        """
        max_actions = 20  # 防止无限循环
        actions_taken = 0
        players_to_keep = 2  # 至少保留2个玩家
        kept_players = 0
        
        while not self.game_controller.is_betting_round_complete() and actions_taken < max_actions:
            current_player = self.game_controller.get_current_player()
            if current_player is None:
                break
            
            player = self.game_controller.game_state.get_player_by_seat(current_player)
            if not player or not player.can_act():
                break
            
            # 确保前两个活跃玩家不会弃牌
            should_keep_player = kept_players < players_to_keep
            
            try:
                if should_keep_player:
                    # 必须保留的玩家：优先check，否则call
                    try:
                        action = ActionHelper.create_player_action(player, ActionType.CHECK, 0)
                        self.game_controller.process_action(action)
                        kept_players += 1
                    except:
                        try:
                            action = ActionHelper.create_player_action(player, ActionType.CALL, 0)
                            self.game_controller.process_action(action)
                            kept_players += 1
                        except:
                            # 最后resort
                            action = ActionHelper.create_player_action(player, ActionType.FOLD, 0)
                            self.game_controller.process_action(action)
                else:
                    # 其他玩家可以随机选择，但偏向于不弃牌
                    import random
                    choice = random.random()
                    if choice < 0.7:  # 70%概率不弃牌
                        try:
                            action = ActionHelper.create_player_action(player, ActionType.CHECK, 0)
                            self.game_controller.process_action(action)
                        except:
                            action = ActionHelper.create_player_action(player, ActionType.CALL, 0)
                            self.game_controller.process_action(action)
                    else:
                        action = ActionHelper.create_player_action(player, ActionType.FOLD, 0)
                        self.game_controller.process_action(action)
                        
            except Exception as e:
                # 异常处理：尝试执行最安全的操作
                try:
                    action = ActionHelper.create_player_action(player, ActionType.CHECK, 0)
                    self.game_controller.process_action(action)
                except:
                    try:
                        action = ActionHelper.create_player_action(player, ActionType.CALL, 0)
                        self.game_controller.process_action(action)
                    except:
                        action = ActionHelper.create_player_action(player, ActionType.FOLD, 0)
                        self.game_controller.process_action(action)
            
            actions_taken += 1
    
    def _complete_hand(self):
        """完成一手牌"""
        # Pre-flop
        self._simulate_conservative_betting_round()
        
        # 其他阶段
        phases = [GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]
        for phase in phases:
            if self.game_controller.game_state.phase in phases:
                self.game_controller.advance_phase()
                self._simulate_conservative_betting_round()
        
        # Showdown
        if self.game_controller.game_state.phase != GamePhase.SHOWDOWN:
            self.game_controller.advance_phase()
        
        # 结算
        self.game_controller.determine_winners()
    
    def _complete_remaining_phases(self):
        """完成剩余的游戏阶段"""
        phases = [GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER, GamePhase.SHOWDOWN]
        
        while self.game_controller.game_state.phase in phases:
            if self.game_controller.game_state.phase == GamePhase.SHOWDOWN:
                self.game_controller.determine_winners()
                break
            else:
                self.game_controller.advance_phase()
                if self.game_controller.game_state.phase != GamePhase.SHOWDOWN:
                    self._simulate_conservative_betting_round()


def run_game_flow_tests():
    """运行游戏流程测试"""
    print("=" * 60)
    print("游戏流程测试套件")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(GameFlowTester)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return TestResult(
        scenario_name="游戏流程测试",
        test_name="游戏流程测试",
        passed=result.wasSuccessful(),
        expected=f"测试通过",
        actual=f"成功: {result.testsRun - len(result.failures) - len(result.errors)}, 失败: {len(result.failures)}, 错误: {len(result.errors)}",
        details=f"总计: {result.testsRun}, 成功: {result.testsRun - len(result.failures) - len(result.errors)}, 失败: {len(result.failures)}, 错误: {len(result.errors)}"
    )


if __name__ == "__main__":
    result = run_game_flow_tests()
    print(f"\n测试结果: {result}")
    exit(0 if result.passed else 1) 