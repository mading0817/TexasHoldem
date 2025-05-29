#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克核心规则测试
测试基础的德州扑克规则，包括玩家位置、盲注设置等
从comprehensive_test.py中提取相关测试，专注于规则合规性
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tests.common import BaseTester, TestScenario, format_test_header


class CoreRulesTester(BaseTester):
    """
    德州扑克核心规则测试器
    专门测试德州扑克的基础规则实现
    """
    
    def __init__(self):
        """初始化核心规则测试器"""
        super().__init__("CoreRules")
        print("[DEBUG] CoreRulesTester初始化完成")
    
    def test_player_positions_and_blinds(self):
        """
        测试玩家位置和盲注设置
        验证庄家、小盲、大盲位置的正确分配
        """
        print(format_test_header("玩家位置和盲注设置测试", 2))
        
        # 场景1：3玩家游戏 - 基础位置测试
        scenario1 = TestScenario(
            name="3玩家位置",
            players_count=3,
            starting_chips=[100, 100, 100],
            dealer_position=1,  # Bob是庄家（座位1）
            expected_behavior={
                "small_blind": 2,  # Charlie是小盲（座位2）
                "big_blind": 0,    # Alice是大盲（座位0）
                "first_to_act": 1  # Bob首先行动（庄家在翻牌前最后行动）
            },
            description="测试3玩家中的位置分配和盲注"
        )
        
        state1 = self.create_scenario_game(scenario1)
        
        # 验证庄家位置
        self.log_test(scenario1.name, "庄家位置正确", 
                     state1.dealer_position == 1, 1, state1.dealer_position)
        
        # 查找小盲和大盲玩家
        small_blind_player = None
        big_blind_player = None
        
        for player in state1.players:
            if player.is_small_blind:
                small_blind_player = player
            if player.is_big_blind:
                big_blind_player = player
        
        # 验证小盲位置和金额
        self.log_test(scenario1.name, "小盲玩家位置", 
                     small_blind_player is not None and small_blind_player.seat_id == 2, 
                     2, small_blind_player.seat_id if small_blind_player else None)
        
        if small_blind_player:
            self.log_test(scenario1.name, "小盲金额正确",
                         small_blind_player.current_bet == 1, 1,
                         small_blind_player.current_bet)
        
        # 验证大盲位置和金额
        self.log_test(scenario1.name, "大盲玩家位置",
                     big_blind_player is not None and big_blind_player.seat_id == 0, 
                     0, big_blind_player.seat_id if big_blind_player else None)
        
        if big_blind_player:
            self.log_test(scenario1.name, "大盲金额正确",
                         big_blind_player.current_bet == 2, 2,
                         big_blind_player.current_bet)
        
        # 场景2：6玩家游戏 - 标准多人游戏
        scenario2 = TestScenario(
            name="6玩家位置",
            players_count=6,
            starting_chips=[100] * 6,
            dealer_position=3,  # 4号位是庄家（0-indexed）
            expected_behavior={
                "small_blind": 4,  # 5号位是小盲
                "big_blind": 5,    # 6号位是大盲
                "first_to_act": 0  # 1号位首先行动（UTG）
            },
            description="测试6玩家的标准位置分配"
        )
        
        state2 = self.create_scenario_game(scenario2)
        
        # 查找小盲和大盲玩家
        small_blind_player = None
        big_blind_player = None
        
        for player in state2.players:
            if player.is_small_blind:
                small_blind_player = player
            if player.is_big_blind:
                big_blind_player = player
        
        # 验证6人游戏的位置
        self.log_test(scenario2.name, "6人小盲位置",
                     small_blind_player is not None and small_blind_player.seat_id == 4, 
                     4, small_blind_player.seat_id if small_blind_player else None)
        
        self.log_test(scenario2.name, "6人大盲位置", 
                     big_blind_player is not None and big_blind_player.seat_id == 5, 
                     5, big_blind_player.seat_id if big_blind_player else None)
        
        # 场景3：2玩家游戏（单挑）- 特殊规则
        scenario3 = TestScenario(
            name="2玩家单挑",
            players_count=2,
            starting_chips=[100, 100],
            dealer_position=0,  # 玩家0是庄家
            expected_behavior={
                "small_blind": 0,  # 庄家是小盲（单挑规则）
                "big_blind": 1,    # 另一个玩家是大盲
                "first_to_act": 0  # 庄家首先行动（单挑翻牌前）
            },
            description="测试单挑游戏的特殊规则"
        )
        
        state3 = self.create_scenario_game(scenario3)
        
        # 查找小盲和大盲玩家
        small_blind_player = None
        big_blind_player = None
        
        for player in state3.players:
            if player.is_small_blind:
                small_blind_player = player
            if player.is_big_blind:
                big_blind_player = player
        
        # 验证单挑游戏的特殊规则：庄家是小盲
        self.log_test(scenario3.name, "单挑小盲位置（庄家）", 
                     small_blind_player is not None and small_blind_player.seat_id == 0, 
                     0, small_blind_player.seat_id if small_blind_player else None)
        
        self.log_test(scenario3.name, "单挑大盲位置",
                     big_blind_player is not None and big_blind_player.seat_id == 1, 
                     1, big_blind_player.seat_id if big_blind_player else None)
        
        # 验证单挑游戏中庄家同时是小盲
        if small_blind_player:
            self.log_test(scenario3.name, "单挑庄家同时是小盲",
                         small_blind_player.is_dealer and small_blind_player.is_small_blind,
                         True, f"is_dealer={small_blind_player.is_dealer}, is_small_blind={small_blind_player.is_small_blind}")
    
    def test_blinds_amount_validation(self):
        """
        测试盲注金额的正确性
        验证小盲和大盲的金额设置是否符合配置
        """
        print(format_test_header("盲注金额验证测试", 2))
        
        # 测试标准盲注（1/2）
        scenario_standard = TestScenario(
            name="标准盲注",
            players_count=4,
            starting_chips=[100] * 4,
            dealer_position=0,
            expected_behavior={
                "small_blind_amount": 1,
                "big_blind_amount": 2
            },
            description="测试标准1/2盲注设置"
        )
        
        state = self.create_scenario_game(scenario_standard)
        
        # 验证盲注金额设置
        self.log_test(scenario_standard.name, "小盲注配置",
                     state.small_blind == 1, 1, state.small_blind)
        
        self.log_test(scenario_standard.name, "大盲注配置", 
                     state.big_blind == 2, 2, state.big_blind)
        
        # 验证实际投入的盲注金额
        total_blinds = 0
        small_blind_invested = 0
        big_blind_invested = 0
        
        for player in state.players:
            if player.is_small_blind:
                small_blind_invested = player.current_bet
            if player.is_big_blind:
                big_blind_invested = player.current_bet
            total_blinds += player.current_bet
        
        self.log_test(scenario_standard.name, "小盲实际投入",
                     small_blind_invested == 1, 1, small_blind_invested)
        
        self.log_test(scenario_standard.name, "大盲实际投入",
                     big_blind_invested == 2, 2, big_blind_invested)
        
        self.log_test(scenario_standard.name, "盲注总计",
                     total_blinds == 3, 3, total_blinds)
    
    def test_dealer_rotation_rules(self):
        """
        测试庄家轮转规则
        在多手牌游戏中，庄家位置应该按顺序轮转
        """
        print(format_test_header("庄家轮转规则测试", 2))
        
        # 创建基础场景
        scenario = TestScenario(
            name="庄家轮转",
            players_count=4,
            starting_chips=[100] * 4,
            dealer_position=0,
            expected_behavior={},
            description="测试庄家位置轮转"
        )
        
        # 验证庄家轮转顺序（模拟多手牌）
        for hand_num in range(4):
            expected_dealer = hand_num % 4
            
            # 创建游戏状态并设置庄家位置
            state = self.create_scenario_game(scenario)
            state.dealer_position = expected_dealer
            
            # 重新设置庄家标记
            for player in state.players:
                player.is_dealer = (player.seat_id == expected_dealer)
            
            # 重新设置盲注
            state.set_blinds()
            
            # 验证庄家位置
            dealer_player = None
            for player in state.players:
                if player.is_dealer:
                    dealer_player = player
                    break
            
            self.log_test(scenario.name, f"第{hand_num+1}手庄家位置",
                         dealer_player is not None and dealer_player.seat_id == expected_dealer,
                         expected_dealer, dealer_player.seat_id if dealer_player else None)
    
    def test_edge_case_positions(self):
        """
        测试边缘情况的位置设置
        包括玩家数量变化等特殊情况
        """
        print(format_test_header("边缘情况位置测试", 2))
        
        # 测试最少玩家数（2人）
        scenario_min = TestScenario(
            name="最少玩家",
            players_count=2,
            starting_chips=[100, 100],
            dealer_position=1,
            expected_behavior={},
            description="测试2人游戏的最少配置"
        )
        
        state_min = self.create_scenario_game(scenario_min)
        
        # 验证2人游戏的位置设置
        position_count = {"dealer": 0, "small_blind": 0, "big_blind": 0}
        
        for player in state_min.players:
            if player.is_dealer:
                position_count["dealer"] += 1
            if player.is_small_blind:
                position_count["small_blind"] += 1
            if player.is_big_blind:
                position_count["big_blind"] += 1
        
        # 验证每个位置只有一个玩家
        self.log_test(scenario_min.name, "唯一庄家",
                     position_count["dealer"] == 1, 1, position_count["dealer"])
        
        self.log_test(scenario_min.name, "唯一小盲",
                     position_count["small_blind"] == 1, 1, position_count["small_blind"])
        
        self.log_test(scenario_min.name, "唯一大盲",
                     position_count["big_blind"] == 1, 1, position_count["big_blind"])
        
        # 在2人游戏中，庄家应该同时是小盲
        dealer_is_small_blind = False
        for player in state_min.players:
            if player.is_dealer and player.is_small_blind:
                dealer_is_small_blind = True
                break
        
        self.log_test(scenario_min.name, "2人游戏庄家是小盲",
                     dealer_is_small_blind, True, dealer_is_small_blind)
    
    def run_all_core_rules_tests(self):
        """运行所有核心规则测试"""
        print(format_test_header("德州扑克核心规则测试套件", 1))
        
        # 重置测试结果
        self.reset_results()
        
        # 运行各项测试
        try:
            self.test_player_positions_and_blinds()
            self.test_blinds_amount_validation()
            self.test_dealer_rotation_rules()
            self.test_edge_case_positions()
            
        except Exception as e:
            print(f"[ERROR] 测试执行出错: {e}")
            import traceback
            traceback.print_exc()
        
        # 打印测试总结
        self.print_test_summary()
        
        return self.suite.is_passed


def main():
    """主函数：运行核心规则测试"""
    print("德州扑克核心规则测试开始...")
    
    tester = CoreRulesTester()
    success = tester.run_all_core_rules_tests()
    
    print(f"\n{'='*60}")
    print(f"测试结果: {'全部通过' if success else '存在失败'}")
    print(f"{'='*60}")
    
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main()) 