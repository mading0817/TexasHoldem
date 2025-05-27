#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
游戏控制器(GameController)类单元测试
测试游戏控制、状态管理、事件处理等功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core_game_logic.game.game_controller import GameController
from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.core.deck import Deck
from core_game_logic.core.enums import GamePhase, SeatStatus


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
        
        self.state = GameState(
            players=self.players,
            dealer_position=0,
            small_blind=1,
            big_blind=2
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
        
        print("✓ 控制器初始化测试通过")
    
    def test_game_status_reporting(self):
        """测试游戏状态报告"""
        print("测试游戏状态报告...")
        
        # 设置一些游戏状态
        self.state.pot = 50
        self.state.current_bet = 20
        self.state.phase = GamePhase.FLOP
        self.players[0].fold()  # 一个玩家弃牌
        
        # 获取游戏状态
        status = self.controller.get_game_status()
        
        # 验证状态报告
        assert isinstance(status, dict), "状态应该是字典格式"
        assert status['game_phase'] == 'FLOP', "游戏阶段应该正确"
        assert status['pot'] == 50, "底池应该正确"
        assert status['current_bet'] == 20, "当前下注应该正确"
        assert status['active_players'] == 2, "活跃玩家数应该正确"
        assert status['total_players'] == 3, "总玩家数应该正确"
        assert 'dealer_position' in status, "应该包含庄家位置"
        assert 'small_blind' in status, "应该包含小盲注"
        assert 'big_blind' in status, "应该包含大盲注"
        
        print("✓ 游戏状态报告测试通过")
    
    def test_player_status_reporting(self):
        """测试玩家状态报告"""
        print("测试玩家状态报告...")
        
        # 设置一些玩家状态
        self.players[0].bet(30)
        self.players[0].is_dealer = True
        self.players[1].fold()
        self.players[2].status = SeatStatus.ALL_IN
        
        # 获取玩家状态
        players_status = self.controller.get_players_status()
        
        # 验证玩家状态报告
        assert isinstance(players_status, list), "玩家状态应该是列表"
        assert len(players_status) == 3, "应该有3个玩家的状态"
        
        # 验证第一个玩家（庄家，有下注）
        alice_status = next(p for p in players_status if p['seat_id'] == 0)
        assert alice_status['name'] == 'Alice', "玩家名称应该正确"
        assert alice_status['chips'] == 70, "筹码应该正确（100-30）"
        assert alice_status['current_bet'] == 30, "当前下注应该正确"
        assert alice_status['status'] == 'ACTIVE', "状态应该正确"
        assert alice_status['is_dealer'] == True, "庄家标记应该正确"
        
        # 验证第二个玩家（弃牌）
        bob_status = next(p for p in players_status if p['seat_id'] == 1)
        assert bob_status['status'] == 'FOLDED', "弃牌状态应该正确"
        
        # 验证第三个玩家（全押）
        charlie_status = next(p for p in players_status if p['seat_id'] == 2)
        assert charlie_status['status'] == 'ALL_IN', "全押状态应该正确"
        
        print("✓ 玩家状态报告测试通过")
    
    def test_game_state_serialization(self):
        """测试游戏状态序列化"""
        print("测试游戏状态序列化...")
        
        # 设置一些状态
        self.state.pot = 100
        self.state.current_bet = 25
        self.players[0].bet(25)
        
        # 测试完整序列化
        full_state = self.controller.get_full_game_state()
        assert isinstance(full_state, dict), "完整状态应该是字典"
        assert 'phase' in full_state, "应该包含阶段信息"
        assert 'players' in full_state, "应该包含玩家信息"
        assert 'pot' in full_state, "应该包含底池信息"
        
        # 测试带观察者的序列化
        viewer_state = self.controller.get_game_state_for_player(seat_id=0)
        assert isinstance(viewer_state, dict), "观察者状态应该是字典"
        assert viewer_state['pot'] == 100, "底池信息应该正确"
        
        # 验证观察者看到的玩家信息
        players_info = viewer_state['players']
        viewer_player = next(p for p in players_info if p['seat_id'] == 0)
        other_player = next(p for p in players_info if p['seat_id'] == 1)
        
        # 观察者应该能看到自己的手牌，但看不到其他人的
        # 注意：这里的逻辑依赖于Player类的get_hole_cards_str方法
        
        print("✓ 游戏状态序列化测试通过")
    
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
        
        print("✓ 游戏事件管理测试通过")
    
    def test_game_statistics(self):
        """测试游戏统计信息"""
        print("测试游戏统计信息...")
        
        # 设置一些状态用于统计
        self.players[0].bet(50)
        self.players[1].bet(30)
        self.players[2].fold()
        self.state.pot = 100
        
        # 获取统计信息
        stats = self.controller.get_game_statistics()
        
        # 验证统计信息
        assert isinstance(stats, dict), "统计信息应该是字典"
        assert 'total_pot' in stats, "应该包含总底池"
        assert 'active_players_count' in stats, "应该包含活跃玩家数"
        assert 'folded_players_count' in stats, "应该包含弃牌玩家数"
        assert 'total_chips_in_play' in stats, "应该包含总筹码数"
        
        # 验证具体数值
        assert stats['total_pot'] == 100, "总底池应该正确"
        assert stats['active_players_count'] == 2, "活跃玩家数应该正确"
        assert stats['folded_players_count'] == 1, "弃牌玩家数应该正确"
        
        # 验证筹码守恒
        total_chips = stats['total_chips_in_play']
        expected_total = sum(p.chips + p.current_bet for p in self.players) + self.state.pot
        assert total_chips == expected_total, "总筹码应该守恒"
        
        print("✓ 游戏统计信息测试通过")
    
    def test_player_action_validation(self):
        """测试玩家行动验证"""
        print("测试玩家行动验证...")
        
        # 设置游戏状态
        self.state.current_bet = 20
        self.state.current_player = 0
        
        # 测试有效玩家检查
        assert self.controller.is_valid_player_turn(0), "应该是有效的玩家回合"
        assert not self.controller.is_valid_player_turn(1), "不应该是其他玩家的回合"
        
        # 测试玩家行动能力
        player = self.players[0]
        assert self.controller.can_player_act(player), "玩家应该可以行动"
        
        # 测试弃牌玩家
        self.players[1].fold()
        assert not self.controller.can_player_act(self.players[1]), "弃牌玩家不应该可以行动"
        
        # 测试全押玩家
        self.players[2].status = SeatStatus.ALL_IN
        assert not self.controller.can_player_act(self.players[2]), "全押玩家不应该可以行动"
        
        print("✓ 玩家行动验证测试通过")
    
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
            player.status = SeatStatus.ACTIVE
        self.players[0].status = SeatStatus.ALL_IN
        self.players[1].status = SeatStatus.ALL_IN
        self.players[2].status = SeatStatus.ALL_IN
        
        # 所有玩家全押时游戏应该可以继续（直到摊牌）
        assert self.controller.can_game_continue(), "所有玩家全押时游戏应该可以继续"
        
        print("✓ 游戏流程控制测试通过")
    
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
        
        print("✓ 错误处理测试通过")
    
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
        
        print("✓ 状态一致性测试通过")


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
            print(f"✓ {test_name}测试通过\n")
            passed += 1
        except Exception as e:
            print(f"✗ {test_name}测试失败: {e}\n")
            failed += 1
    
    print(f"测试结果: {passed}通过, {failed}失败")
    
    if failed == 0:
        print("🎉 所有GameController单元测试通过！")
        return True
    else:
        print("❌ 部分测试失败，需要修复")
        return False


if __name__ == "__main__":
    run_tests() 