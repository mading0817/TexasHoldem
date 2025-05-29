#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
游戏控制器的单元测试
测试GameController的各种功能和边缘情况
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_game_logic.game.game_controller import GameController
from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.core.deck import Deck
from core_game_logic.core.enums import GamePhase, SeatStatus, Action, ActionType
from core_game_logic.core.exceptions import InvalidActionError
from tests.common.test_helpers import ActionHelper


class TestGameController:
    """游戏控制器类测试"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 创建3个玩家
        self.players = [
            Player(seat_id=0, name="Alice", chips=100),
            Player(seat_id=1, name="Bob", chips=100),
            Player(seat_id=2, name="Charlie", chips=100)
        ]
        
        # 创建并洗牌的牌组
        deck = Deck()
        deck.shuffle()
        
        self.state = GameState(
            players=self.players,
            dealer_position=0,
            small_blind=1,
            big_blind=2,
            phase=GamePhase.PRE_FLOP,
            current_bet=0,
            current_player=0,  # 设置当前玩家
            deck=deck  # 添加已初始化的牌组
        )
        
        self.controller = GameController(self.state)
    
    def test_controller_initialization(self):
        """测试控制器初始化"""
        print("测试控制器初始化...")
        
        # 测试正常初始化
        controller = GameController(self.state)
        assert controller.state is self.state, "控制器应该持有游戏状态引用"
        
        # 测试状态访问
        assert len(controller.state.players) == 3, "应该能访问游戏状态"
        assert controller.state.phase == GamePhase.PRE_FLOP, "初始阶段应该正确"
        
        print("[OK] 控制器初始化测试通过")
    
    def test_game_status_reporting(self):
        """测试游戏状态报告"""
        print("测试游戏状态报告...")
        
        # 通过GameController合法地设置状态，不直接修改
        # 模拟一些游戏状态变化
        alice_action = ActionHelper.create_player_action(self.players[0], ActionType.BET, amount=20)
        self.controller.process_action(alice_action)
        
        # 推进到翻牌阶段 - 使用合法方式
        self.controller.advance_phase()
        
        # 一个玩家弃牌
        bob_action = ActionHelper.create_player_action(self.players[1], ActionType.FOLD)
        self.controller.process_action(bob_action)
        
        # 获取游戏状态
        status = self.controller.get_game_status()
        
        # 验证状态报告
        assert isinstance(status, dict), "状态应该是字典格式"
        assert 'game_phase' in status, "应该包含游戏阶段"
        assert 'active_players' in status, "应该包含活跃玩家数"
        assert 'total_players' in status, "应该包含总玩家数"
        assert 'dealer_position' in status, "应该包含庄家位置"
        assert 'small_blind' in status, "应该包含小盲注"
        assert 'big_blind' in status, "应该包含大盲注"
        
        print("[OK] 游戏状态报告测试通过")
    
    def test_player_status_reporting(self):
        """测试玩家状态报告"""
        print("测试玩家状态报告...")
        
        # 设置一些玩家状态 - 使用合法方式
        alice_action = ActionHelper.create_player_action(self.players[0], ActionType.BET, amount=30)
        self.controller.process_action(alice_action)
        
        self.players[0].is_dealer = True
        
        bob_action = ActionHelper.create_player_action(self.players[1], ActionType.FOLD)
        self.controller.process_action(bob_action)
        
        # 设置玩家2为全押状态 - 使用合法方式
        charlie_action = ActionHelper.create_player_action(self.players[2], ActionType.ALL_IN)
        self.controller.process_action(charlie_action)
        
        # 获取玩家状态
        players_status = self.controller.get_players_status()
        
        # 验证玩家状态报告
        assert isinstance(players_status, list), "玩家状态应该是列表"
        assert len(players_status) == 3, "应该有3个玩家的状态"
        
        # 基本验证，不依赖具体的状态值
        for player_status in players_status:
            assert 'seat_id' in player_status, "应该包含座位ID"
            assert 'name' in player_status, "应该包含玩家名称"
            assert 'chips' in player_status, "应该包含筹码数"
            assert 'current_bet' in player_status, "应该包含当前下注"
            assert 'status' in player_status, "应该包含状态"
        
        print("[OK] 玩家状态报告测试通过")
    
    def test_game_state_serialization(self):
        """测试游戏状态序列化"""
        print("测试游戏状态序列化...")
        
        # 通过合法方式设置一些状态
        alice_action = ActionHelper.create_player_action(self.players[0], ActionType.BET, amount=25)
        self.controller.process_action(alice_action)
        
        # 测试完整状态序列化
        full_state = self.controller.get_full_game_state()
        
        # 验证完整状态
        assert isinstance(full_state, dict), "完整状态应该是字典"
        assert 'phase' in full_state, "应该包含阶段信息"
        assert 'players' in full_state, "应该包含玩家信息"
        assert 'pot' in full_state, "应该包含底池信息"
        
        # 测试带观察者的序列化
        viewer_state = self.controller.get_game_state_for_player(seat_id=0)
        assert isinstance(viewer_state, dict), "观察者状态应该是字典"
        assert 'pot' in viewer_state, "应该包含底池信息"
        
        # 验证观察者看到的玩家信息
        if 'players' in viewer_state:
            players_info = viewer_state['players']
            assert isinstance(players_info, list), "玩家信息应该是列表"
        
        print("[OK] 游戏状态序列化测试通过")
    
    def test_game_events_management(self):
        """测试游戏事件管理"""
        print("测试游戏事件管理...")
        
        # 添加一些事件
        initial_events_count = len(self.controller.get_game_events())
        
        self.state.add_event("玩家Alice下注20")
        self.state.add_event("玩家Bob跟注")
        self.state.add_event("翻牌: As Kh Qd")
        
        # 获取事件列表
        events = self.controller.get_game_events()
        
        # 验证事件管理
        assert isinstance(events, list), "事件应该是列表"
        assert len(events) == initial_events_count + 3, "应该有3个新事件"
        assert "玩家Alice下注20" in events, "应该包含第一个事件"
        assert "翻牌: As Kh Qd" in events, "应该包含最后一个事件"
        
        # 测试获取最近事件
        recent_events = self.controller.get_recent_events(count=2)
        assert len(recent_events) == 2, "应该返回最近2个事件"
        assert recent_events[-1] == "翻牌: As Kh Qd", "最后一个事件应该是最新的"
        
        print("[OK] 游戏事件管理测试通过")
    
    def test_game_statistics(self):
        """测试游戏统计信息"""
        print("测试游戏统计信息...")
        
        # 通过合法方式设置状态用于统计
        alice_action = ActionHelper.create_player_action(self.players[0], ActionType.BET, amount=50)
        self.controller.process_action(alice_action)
        
        bob_action = ActionHelper.create_player_action(self.players[1], ActionType.CALL)
        self.controller.process_action(bob_action)
        
        charlie_action = ActionHelper.create_player_action(self.players[2], ActionType.FOLD)
        self.controller.process_action(charlie_action)
        
        # 获取统计信息
        stats = self.controller.get_game_statistics()
        
        # 验证统计信息
        assert isinstance(stats, dict), "统计信息应该是字典"
        assert 'total_pot' in stats, "应该包含总底池"
        assert 'active_players_count' in stats, "应该包含活跃玩家数"
        assert 'folded_players_count' in stats, "应该包含弃牌玩家数"
        assert 'total_chips_in_play' in stats, "应该包含总筹码数"
        
        # 验证筹码守恒
        total_chips = stats['total_chips_in_play']
        expected_total = sum(p.chips + p.current_bet for p in self.players) + self.state.pot
        assert total_chips == expected_total, "总筹码应该守恒"
        
        print("[OK] 游戏统计信息测试通过")
    
    def test_player_action_validation(self):
        """测试玩家行动验证"""
        print("测试玩家行动验证...")
        
        # 设置游戏状态 - 当前玩家是0号位
        player = self.players[0]
        
        # 测试正常玩家（当前玩家）
        assert self.controller.can_player_act(player), "玩家应该可以行动"
        
        # 让当前玩家先行动（弃牌），然后测试弃牌玩家状态
        fold_action = ActionHelper.create_player_action(player, ActionType.FOLD)
        self.controller.process_action(fold_action)
        assert not self.controller.can_player_act(player), "弃牌玩家不应该可以行动"
        
        # 现在测试下一个当前玩家的全押
        current_player = self.state.get_current_player()
        if current_player:
            all_in_action = ActionHelper.create_player_action(current_player, ActionType.ALL_IN)
            self.controller.process_action(all_in_action)
            assert not self.controller.can_player_act(current_player), "全押玩家不应该可以行动"
        
        print("[OK] 玩家行动验证测试通过")
    
    def test_game_flow_control(self):
        """测试游戏流程控制"""
        print("测试游戏流程控制...")
        
        # 测试游戏是否可以继续
        assert self.controller.can_game_continue(), "游戏应该可以继续"
        
        # 测试只剩一个玩家的情况
        self.players[0].fold()
        self.players[1].fold()
        assert not self.controller.can_game_continue(), "只剩一个玩家时游戏不应该继续"
        
        # 重置状态测试所有玩家全押的情况
        for player in self.players:
            player.reset_for_new_hand()  # 重置状态
        
        # 设置全押状态
        self.players[0].bet(self.players[0].chips)  # 全押
        self.players[1].bet(self.players[1].chips)  # 全押
        self.players[2].bet(self.players[2].chips)  # 全押
        
        # 所有玩家全押时游戏应该可以继续（直到摊牌）
        assert self.controller.can_game_continue(), "所有玩家全押时游戏应该可以继续"
        
        print("[OK] 游戏流程控制测试通过")
    
    def test_error_handling(self):
        """测试错误处理"""
        print("测试错误处理...")
        
        # 测试无效座位号
        invalid_state = self.controller.get_game_state_for_player(seat_id=99)
        assert invalid_state is not None, "无效座位号应该返回默认状态"
        
        # 测试空事件列表
        empty_events = self.controller.get_recent_events(count=0)
        assert isinstance(empty_events, list), "应该返回空列表"
        assert len(empty_events) == 0, "空事件列表应该为空"
        
        # 测试过大的事件数量请求
        all_events = self.controller.get_recent_events(count=1000)
        assert len(all_events) <= len(self.state.events), "不应该超过实际事件数量"
        
        print("[OK] 错误处理测试通过")
    
    def test_state_consistency(self):
        """测试状态一致性"""
        print("测试状态一致性...")
        
        # 获取多次状态快照，验证一致性
        status1 = self.controller.get_game_status()
        status2 = self.controller.get_game_status()
        
        # 在没有状态变化的情况下，两次获取的状态应该相同
        assert status1['pot'] == status2['pot'], "底池应该一致"
        assert status1['current_bet'] == status2['current_bet'], "当前下注应该一致"
        assert status1['active_players'] == status2['active_players'], "活跃玩家数应该一致"
        
        # 修改状态后验证变化
        self.state.pot += 50
        status3 = self.controller.get_game_status()
        assert status3['pot'] != status1['pot'], "状态变化后应该不同"
        assert status3['pot'] == status1['pot'] + 50, "变化量应该正确"
        
        print("[OK] 状态一致性测试通过")


def run_tests():
    """运行所有测试"""
    print("=== 游戏控制器(GameController)类单元测试 ===\n")
    
    test_instance = TestGameController()
    
    test_methods = [
        ("控制器初始化", test_instance.test_controller_initialization),
        ("游戏状态报告", test_instance.test_game_status_reporting),
        ("玩家状态报告", test_instance.test_player_status_reporting),
        ("游戏状态序列化", test_instance.test_game_state_serialization),
        ("游戏事件管理", test_instance.test_game_events_management),
        ("游戏统计信息", test_instance.test_game_statistics),
        ("玩家行动验证", test_instance.test_player_action_validation),
        ("游戏流程控制", test_instance.test_game_flow_control),
        ("错误处理", test_instance.test_error_handling),
        ("状态一致性", test_instance.test_state_consistency),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in test_methods:
        try:
            test_instance.setup_method()
            test_func()
            print(f"[OK] {test_name}测试通过\n")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test_name}测试失败: {e}\n")
            failed += 1
    
    print(f"测试结果: {passed}通过, {failed}失败")
    
    if failed == 0:
        print("[SUCCESS] 所有GameController单元测试通过！")
        return True
    else:
        print("[ERROR] 部分测试失败，需要修复")
        return False


if __name__ == "__main__":
    run_tests() 