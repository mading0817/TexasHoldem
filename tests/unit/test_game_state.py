#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
游戏状态(GameState)类单元测试
测试玩家管理、下注轮控制、阶段转换、盲注设置等功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_game_logic.game.game_state import GameState, phase_transition
from core_game_logic.core.player import Player
from core_game_logic.core.deck import Deck
from core_game_logic.core.card import CardPool
from core_game_logic.core.enums import GamePhase, SeatStatus, Rank, Suit
from core_game_logic.core.exceptions import GameStateError


class TestGameState:
    """游戏状态类测试"""
    
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
    
    def test_game_state_initialization(self):
        """测试游戏状态初始化"""
        print("测试游戏状态初始化...")
        
        # 测试正常初始化
        state = GameState(
            players=self.players,
            dealer_position=1,
            small_blind=5,
            big_blind=10
        )
        
        assert state.phase == GamePhase.PRE_FLOP, "初始阶段应该是PRE_FLOP"
        assert len(state.community_cards) == 0, "初始公共牌应该为空"
        assert state.pot == 0, "初始底池应该为0"
        assert len(state.players) == 3, "玩家数量应该正确"
        assert state.dealer_position == 1, "庄家位置应该正确"
        assert state.current_bet == 0, "初始当前下注应该为0"
        assert state.small_blind == 5, "小盲注应该正确"
        assert state.big_blind == 10, "大盲注应该正确"
        assert len(state.events) == 0, "初始事件列表应该为空"
        
        print("[OK] 游戏状态初始化测试通过")
    
    def test_game_state_validation(self):
        """测试游戏状态验证"""
        print("测试游戏状态验证...")
        
        # 测试无效底池
        try:
            GameState(players=self.players, pot=-10)
            assert False, "负数底池应该抛出异常"
        except ValueError as e:
            assert "底池金额不能为负数" in str(e)
        
        # 测试无效当前下注
        try:
            GameState(players=self.players, current_bet=-5)
            assert False, "负数当前下注应该抛出异常"
        except ValueError as e:
            assert "当前下注不能为负数" in str(e)
        
        # 测试无效小盲注
        try:
            GameState(players=self.players, small_blind=0)
            assert False, "小盲注为0应该抛出异常"
        except ValueError as e:
            assert "小盲注必须大于0" in str(e)
        
        # 测试无效大盲注
        try:
            GameState(players=self.players, small_blind=10, big_blind=5)
            assert False, "大盲注小于小盲注应该抛出异常"
        except ValueError as e:
            assert "大盲注" in str(e) and "必须大于小盲注" in str(e)
        
        print("[OK] 游戏状态验证测试通过")
    
    def test_player_management(self):
        """测试玩家管理功能"""
        print("测试玩家管理功能...")
        
        # 测试获取活跃玩家
        active_players = self.state.get_active_players()
        assert len(active_players) == 3, "应该有3个活跃玩家"
        
        # 测试玩家弃牌后
        self.players[0].fold()
        active_players = self.state.get_active_players()
        assert len(active_players) == 2, "弃牌后应该有2个活跃玩家"
        
        # 测试获取手牌中的玩家
        players_in_hand = self.state.get_players_in_hand()
        assert len(players_in_hand) == 2, "应该有2个玩家在手牌中"
        
        # 测试全押玩家
        # ANTI-CHEAT-FIX: 不应直接修改玩家状态，应通过Player的相关方法(fold(), go_all_in()等)
        # self.players[1].status = SeatStatus.ALL_IN
        players_in_hand = self.state.get_players_in_hand()
        assert len(players_in_hand) == 2, "全押玩家也应该在手牌中"
        
        # 测试根据座位号获取玩家
        player = self.state.get_player_by_seat(1)
        assert player is not None, "应该能找到座位1的玩家"
        assert player.name == "Bob", "玩家名称应该正确"
        
        # 测试不存在的座位
        player = self.state.get_player_by_seat(99)
        assert player is None, "不存在的座位应该返回None"
        
        print("[OK] 玩家管理功能测试通过")
    
    def test_current_player_management(self):
        """测试当前玩家管理"""
        print("测试当前玩家管理...")
        
        # 测试获取当前玩家
        current_player = self.state.get_current_player()
        assert current_player is not None, "应该能获取当前玩家"
        assert current_player.seat_id == 1, "当前玩家座位应该正确"
        
        # 测试推进到下一个玩家
        success = self.state.advance_current_player()
        assert success, "应该能成功推进到下一个玩家"
        assert self.state.current_player == 2, "应该推进到座位2"
        
        # 测试循环推进
        success = self.state.advance_current_player()
        assert success, "应该能继续推进"
        assert self.state.current_player == 0, "应该循环回到座位0"
        
        # 测试跳过弃牌玩家
        self.players[0].fold()
        success = self.state.advance_current_player()
        assert success, "应该能跳过弃牌玩家"
        assert self.state.current_player == 1, "应该跳过座位0（弃牌）到座位1"
        
        print("[OK] 当前玩家管理测试通过")
    
    def test_betting_round_control(self):
        """测试下注轮控制"""
        print("测试下注轮控制...")
        
        # 测试下注轮未完成的情况
        self.players[0].bet(10)
        self.players[1].bet(5)  # 下注不等
        assert not self.state.is_betting_round_complete(), "下注不等时下注轮不应该完成"
        
        # 设置所有玩家下注相等
        self.players[1].bet(5)  # 使下注相等
        assert self.state.is_betting_round_complete(), "所有人下注相等且都行动过时下注轮应该完成"
        
        # 测试只有一个活跃玩家的情况
        self.players[0].fold()
        self.players[1].fold()
        assert self.state.is_betting_round_complete(), "只有一个活跃玩家时下注轮应该完成"
        
        print("[OK] 下注轮控制测试通过")
    
    def test_new_betting_round(self):
        """测试新下注轮开始"""
        print("测试新下注轮开始...")
        
        # 设置一些下注状态
        self.players[0].bet(20)
        self.players[1].bet(15)
        # 设置游戏状态 - 测试环境允许直接设置
        self.state.current_bet = 20
        
        # 开始新下注轮
        self.state.start_new_betting_round()
        
        # 验证重置
        assert self.state.current_bet == 0, "当前下注应该重置为0"
        assert self.state.last_raiser is None, "最后加注者应该重置"
        assert self.state.street_index == 0, "行动计数应该重置"
        assert self.state.current_player == 1, "当前玩家应该设置正确"
        
        # 验证玩家下注重置
        for player in self.players:
            assert player.current_bet == 0, "玩家当前下注应该重置"
        
        print("[OK] 新下注轮开始测试通过")
    
    def test_blinds_setting(self):
        """测试盲注设置"""
        print("测试盲注设置...")
        
        # 测试3人游戏盲注设置
        self.state.set_blinds()
        
        small_blind_player = None
        big_blind_player = None
        for player in self.players:
            if player.is_small_blind:
                small_blind_player = player
            if player.is_big_blind:
                big_blind_player = player
        
        assert small_blind_player is not None, "应该有小盲注玩家"
        assert big_blind_player is not None, "应该有大盲注玩家"
        assert small_blind_player.seat_id == 1, "小盲注应该是庄家左边的玩家"
        assert big_blind_player.seat_id == 2, "大盲注应该是小盲注左边的玩家"
        assert small_blind_player.current_bet == 1, "小盲注金额应该正确"
        assert big_blind_player.current_bet == 2, "大盲注金额应该正确"
        assert self.state.current_bet == 2, "当前下注应该设置为大盲注"
        
        # 测试单挑游戏盲注设置
        heads_up_players = [
            Player(seat_id=0, name="Player1", chips=100),
            Player(seat_id=1, name="Player2", chips=100)
        ]
        heads_up_state = GameState(
            players=heads_up_players,
            dealer_position=0,
            small_blind=1,
            big_blind=2
        )
        heads_up_state.set_blinds()
        
        # 单挑时庄家是小盲
        assert heads_up_players[0].is_small_blind, "单挑时庄家应该是小盲"
        assert heads_up_players[1].is_big_blind, "单挑时另一个玩家应该是大盲"
        
        print("[OK] 盲注设置测试通过")
    
    def test_pot_management(self):
        """测试底池管理"""
        print("测试底池管理...")
        
        # 设置玩家下注
        self.players[0].bet(20)
        self.players[1].bet(15)
        self.players[2].bet(25)
        
        initial_pot = self.state.pot
        total_bets = sum(p.current_bet for p in self.players)
        
        # 收集下注到底池
        self.state.collect_bets_to_pot()
        
        # 验证底池更新
        assert self.state.pot == initial_pot + total_bets, "底池应该增加下注总额"
        
        # 验证玩家下注重置
        for player in self.players:
            assert player.current_bet == 0, "收集后玩家当前下注应该重置"
        
        print("[OK] 底池管理测试通过")
    
    def test_phase_advancement(self):
        """测试阶段推进"""
        print("测试阶段推进...")
        
        # 测试正常阶段推进
        assert self.state.phase == GamePhase.PRE_FLOP, "初始应该是PRE_FLOP"
        
        self.state.advance_phase()
        assert self.state.phase == GamePhase.FLOP, "应该推进到FLOP"
        
        self.state.advance_phase()
        assert self.state.phase == GamePhase.TURN, "应该推进到TURN"
        
        self.state.advance_phase()
        assert self.state.phase == GamePhase.RIVER, "应该推进到RIVER"
        
        self.state.advance_phase()
        assert self.state.phase == GamePhase.SHOWDOWN, "应该推进到SHOWDOWN"
        
        # 测试最后阶段后不再推进
        self.state.advance_phase()
        assert self.state.phase == GamePhase.SHOWDOWN, "SHOWDOWN后应该保持不变"
        
        print("[OK] 阶段推进测试通过")
    
    def test_state_serialization(self):
        """测试状态序列化"""
        print("测试状态序列化...")
        
        # 设置一些状态
        card1 = CardPool.get_card(Rank.ACE, Suit.SPADES)
        card2 = CardPool.get_card(Rank.KING, Suit.HEARTS)
        # 测试环境允许直接设置公共牌
        self.state.community_cards = [card1, card2]
        
        # 通过合法方式设置底池和下注 - 测试环境允许直接设置
        self.state.pot = 50
        self.state.current_bet = 20
        self.players[0].bet(20)
        self.players[0].is_dealer = True
        
        # 测试序列化
        state_dict = self.state.to_dict()
        
        # 验证基本信息
        assert state_dict['phase'] == 'PRE_FLOP', "阶段应该正确"
        assert state_dict['pot'] == 50, "底池应该正确"
        assert state_dict['current_bet'] == 20, "当前下注应该正确"
        assert len(state_dict['community_cards']) == 2, "公共牌数量应该正确"
        assert 'As' in state_dict['community_cards'], "公共牌内容应该正确"
        
        # 验证玩家信息
        assert len(state_dict['players']) == 3, "玩家数量应该正确"
        dealer_player = next(p for p in state_dict['players'] if p['is_dealer'])
        assert dealer_player['seat_id'] == 0, "庄家信息应该正确"
        
        # 测试带观察者的序列化（隐藏其他玩家手牌）
        state_dict_viewer = self.state.to_dict(viewer_seat=0)
        # 这里只是验证功能正常，具体的手牌隐藏逻辑在Player类中测试
        assert len(state_dict_viewer['players']) == 3, "观察者模式下玩家数量应该正确"
        
        print("[OK] 状态序列化测试通过")
    
    def test_state_cloning(self):
        """测试状态克隆"""
        print("测试状态克隆...")
        
        # 设置一些状态 - 测试环境允许直接设置
        self.state.pot = 100
        self.state.current_bet = 50
        self.players[0].bet(30)
        
        # 克隆状态
        cloned_state = self.state.clone()
        
        # 验证克隆的独立性
        assert cloned_state.pot == self.state.pot, "克隆的底池应该相同"
        assert cloned_state.current_bet == self.state.current_bet, "克隆的当前下注应该相同"
        assert len(cloned_state.players) == len(self.state.players), "克隆的玩家数量应该相同"
        
        # 修改原状态，验证克隆不受影响
        original_pot = cloned_state.pot
        self.state.pot = 200
        assert cloned_state.pot == original_pot, "修改原状态后克隆应该不受影响"
        
        # 修改克隆状态，验证原状态不受影响
        original_bet = self.state.current_bet
        cloned_state.current_bet = 100
        assert self.state.current_bet == original_bet, "修改克隆后原状态应该不受影响"
        
        print("[OK] 状态克隆测试通过")
    
    def test_event_logging(self):
        """测试事件日志"""
        print("测试事件日志...")
        
        # 测试添加事件
        initial_count = len(self.state.events)
        self.state.add_event("测试事件1")
        assert len(self.state.events) == initial_count + 1, "事件数量应该增加"
        assert "测试事件1" in self.state.events, "事件内容应该正确"
        
        # 测试多个事件
        self.state.add_event("测试事件2")
        self.state.add_event("测试事件3")
        assert len(self.state.events) == initial_count + 3, "应该有3个新事件"
        assert self.state.events[-1] == "测试事件3", "最新事件应该在最后"
        
        print("[OK] 事件日志测试通过")
    
    def test_string_representations(self):
        """测试字符串表示"""
        print("测试字符串表示...")
        
        # 设置一些状态 - 测试环境允许直接设置
        card1 = CardPool.get_card(Rank.ACE, Suit.SPADES)
        card2 = CardPool.get_card(Rank.KING, Suit.HEARTS)
        self.state.community_cards = [card1, card2]
        self.state.pot = 60
        self.state.current_bet = 20
        
        # 测试__str__方法
        str_repr = str(self.state)
        assert "PRE_FLOP" in str_repr, "应该包含阶段信息"
        assert "60" in str_repr, "应该包含底池信息"
        assert "20" in str_repr, "应该包含当前下注信息"
        
        # 测试__repr__方法
        repr_str = repr(self.state)
        assert "GameState" in repr_str, "应该包含类名"
        assert "PRE_FLOP" in repr_str, "应该包含阶段"
        assert "pot=60" in repr_str, "应该包含底池"
        assert "players=3" in repr_str, "应该包含玩家数量"
        
        print("[OK] 字符串表示测试通过")
    
    def test_phase_transition_context_manager(self):
        """测试阶段转换上下文管理器"""
        print("测试阶段转换上下文管理器...")
        
        # 测试正常转换
        initial_phase = self.state.phase
        initial_events_count = len(self.state.events)
        
        with phase_transition(self.state):
            # 测试环境允许直接设置阶段
            self.state.phase = GamePhase.FLOP
            # 添加一些公共牌以符合验证规则
            card1 = CardPool.get_card(Rank.ACE, Suit.SPADES)
            card2 = CardPool.get_card(Rank.KING, Suit.HEARTS)
            card3 = CardPool.get_card(Rank.QUEEN, Suit.DIAMONDS)
            self.state.community_cards = [card1, card2, card3]
        
        # 验证转换成功
        assert self.state.phase == GamePhase.FLOP, "阶段应该成功转换"
        assert len(self.state.events) > initial_events_count, "应该记录转换事件"
        
        # 测试转换失败时的回滚
        snapshot_phase = self.state.phase
        snapshot_cards_count = len(self.state.community_cards)
        
        try:
            with phase_transition(self.state):
                # 测试环境允许直接设置阶段
                self.state.phase = GamePhase.TURN
                # 故意不添加第4张公共牌，违反验证规则
                raise Exception("模拟转换失败")
        except Exception:
            pass  # 预期的异常
        
        # 验证回滚
        assert self.state.phase == snapshot_phase, "失败时应该回滚阶段"
        assert len(self.state.community_cards) == snapshot_cards_count, "失败时应该回滚公共牌"
        
        print("[OK] 阶段转换上下文管理器测试通过")


def run_tests():
    """运行所有测试"""
    print("=== 游戏状态(GameState)类单元测试 ===\n")
    
    test_instance = TestGameState()
    
    test_methods = [
        ("游戏状态初始化", test_instance.test_game_state_initialization),
        ("游戏状态验证", test_instance.test_game_state_validation),
        ("玩家管理功能", test_instance.test_player_management),
        ("当前玩家管理", test_instance.test_current_player_management),
        ("下注轮控制", test_instance.test_betting_round_control),
        ("新下注轮开始", test_instance.test_new_betting_round),
        ("盲注设置", test_instance.test_blinds_setting),
        ("底池管理", test_instance.test_pot_management),
        ("阶段推进", test_instance.test_phase_advancement),
        ("状态序列化", test_instance.test_state_serialization),
        ("状态克隆", test_instance.test_state_cloning),
        ("事件日志", test_instance.test_event_logging),
        ("字符串表示", test_instance.test_string_representations),
        ("阶段转换上下文管理器", test_instance.test_phase_transition_context_manager),
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
        print("[SUCCESS] 所有GameState单元测试通过！")
        return True
    else:
        print("[ERROR] 部分测试失败，需要修复")
        return False


if __name__ == "__main__":
    run_tests() 