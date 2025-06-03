#!/usr/bin/env python3
"""
Streamlit UI摊牌阶段修复的单元测试。

测试在摊牌阶段UI能够正确自动处理手牌结束逻辑。
"""

import unittest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from v2.core.state import GameState
from v2.core.enums import Phase, SeatStatus
from v2.core.cards import Card, Suit, Rank
from v2.core.player import Player
from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.events import EventBus
import logging

class TestStreamlitShowdownFix(unittest.TestCase):
    """测试Streamlit UI摊牌阶段修复"""
    
    def setUp(self):
        """设置测试环境"""
        self.logger = logging.getLogger(__name__)
        self.event_bus = EventBus()
        self.ai_strategy = SimpleAI()
        
    def create_showdown_scenario(self):
        """创建摊牌阶段的测试场景"""
        # 创建游戏状态
        game_state = GameState()
        
        # 创建并添加4个玩家
        player_you = Player(seat_id=0, name="You", chips=850, is_human=True)
        player_ai1 = Player(seat_id=1, name="AI_1", chips=850)
        player_ai2 = Player(seat_id=2, name="AI_2", chips=850)
        player_ai3 = Player(seat_id=3, name="AI_3", chips=850)
        
        game_state.add_player(player_you)
        game_state.add_player(player_ai1)
        game_state.add_player(player_ai2)
        game_state.add_player(player_ai3)
        
        # 设置庄家位置
        game_state.dealer_position = 3
        
        # 设置摊牌阶段
        game_state.phase = Phase.SHOWDOWN
        
        # 设置公共牌（5张）
        game_state.community_cards = [
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.KING, Suit.SPADES), 
            Card(Rank.QUEEN, Suit.DIAMONDS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.TEN, Suit.HEARTS)
        ]
        
        # 设置玩家手牌
        game_state.players[0].hole_cards = [Card(Rank.NINE, Suit.HEARTS), Card(Rank.EIGHT, Suit.HEARTS)]
        game_state.players[1].hole_cards = [Card(Rank.ACE, Suit.CLUBS), Card(Rank.KING, Suit.HEARTS)]
        game_state.players[2].hole_cards = [Card(Rank.QUEEN, Suit.HEARTS), Card(Rank.JACK, Suit.HEARTS)]
        game_state.players[3].hole_cards = [Card(Rank.TEN, Suit.CLUBS), Card(Rank.NINE, Suit.CLUBS)]
        
        # 设置底池（所有玩家都已下注$150）
        game_state.pot = 900  # 4 * 150 + 之前的底池300
        
        # 所有玩家当前下注都是150
        for player in game_state.players:
            player.current_bet = 150
            player.status = SeatStatus.ACTIVE
        
        # 摊牌阶段没有当前玩家
        game_state.current_player = None
        game_state.current_bet = 150
        
        return game_state
    
    def test_showdown_phase_detection(self):
        """测试摊牌阶段检测"""
        game_state = self.create_showdown_scenario()
        controller = PokerController(game_state, self.ai_strategy, self.logger, self.event_bus)
        controller._hand_in_progress = True
        
        # 验证摊牌阶段状态
        snapshot = controller.get_snapshot()
        self.assertEqual(snapshot.phase, Phase.SHOWDOWN)
        self.assertIsNone(controller.get_current_player_id())
        self.assertTrue(controller.is_hand_over())
    
    def test_ui_showdown_logic(self):
        """测试UI摊牌阶段处理逻辑"""
        game_state = self.create_showdown_scenario()
        controller = PokerController(game_state, self.ai_strategy, self.logger, self.event_bus)
        controller._hand_in_progress = True
        
        # 模拟UI的摊牌阶段检查逻辑
        game_started = True
        is_hand_over = controller.is_hand_over()
        
        # 验证条件满足
        self.assertTrue(game_started)
        self.assertTrue(is_hand_over)
        
        # 检查摊牌阶段
        snapshot = controller.get_snapshot()
        self.assertEqual(snapshot.phase, Phase.SHOWDOWN)
        
        # 模拟UI的自动结束手牌逻辑
        result = controller.end_hand()
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertIsInstance(result.winner_ids, list)
        self.assertGreater(len(result.winner_ids), 0)
        self.assertGreater(result.pot_amount, 0)
        self.assertIsInstance(result.winning_hand_description, str)
        
        # 验证手牌状态重置
        self.assertFalse(controller._hand_in_progress)
        final_snapshot = controller.get_snapshot()
        self.assertEqual(final_snapshot.pot, 0)
    
    def test_ui_condition_check(self):
        """测试UI条件检查逻辑"""
        game_state = self.create_showdown_scenario()
        controller = PokerController(game_state, self.ai_strategy, self.logger, self.event_bus)
        controller._hand_in_progress = True
        
        # 模拟UI的完整条件检查
        game_started = True
        
        # 第一个条件：game_started and controller.is_hand_over()
        condition1 = game_started and controller.is_hand_over()
        self.assertTrue(condition1)
        
        # 第二个条件：snapshot.phase == Phase.SHOWDOWN
        snapshot = controller.get_snapshot()
        condition2 = snapshot and snapshot.phase == Phase.SHOWDOWN
        self.assertTrue(condition2)
        
        # 组合条件
        should_auto_end = condition1 and condition2
        self.assertTrue(should_auto_end)
    
    def test_non_showdown_phase_skip(self):
        """测试非摊牌阶段不会触发自动结束"""
        game_state = self.create_showdown_scenario()
        # 修改为河牌阶段
        game_state.phase = Phase.RIVER
        game_state.current_player = 0  # 设置当前玩家
        
        controller = PokerController(game_state, self.ai_strategy, self.logger, self.event_bus)
        controller._hand_in_progress = True
        
        # 模拟UI的条件检查
        game_started = True
        is_hand_over = controller.is_hand_over()
        
        # 河牌阶段且有当前玩家，手牌不应该结束
        self.assertFalse(is_hand_over)
        
        # 即使手牌结束，也不是摊牌阶段
        snapshot = controller.get_snapshot()
        self.assertNotEqual(snapshot.phase, Phase.SHOWDOWN)
    
    def test_hand_not_in_progress_skip(self):
        """测试手牌未进行时不会触发自动结束"""
        game_state = self.create_showdown_scenario()
        controller = PokerController(game_state, self.ai_strategy, self.logger, self.event_bus)
        # 设置手牌未进行
        controller._hand_in_progress = False
        
        # 模拟UI的条件检查
        game_started = True
        is_hand_over = controller.is_hand_over()
        
        # 在摊牌阶段，即使手牌未进行，is_hand_over仍会返回True
        # 但是end_hand()应该返回None，因为没有手牌在进行中
        self.assertTrue(is_hand_over)  # 摊牌阶段总是返回True
        
        # 但是end_hand()应该返回None
        result = controller.end_hand()
        self.assertIsNone(result)  # 没有手牌在进行中时应该返回None

if __name__ == '__main__':
    # 设置日志级别
    logging.basicConfig(level=logging.WARNING)
    unittest.main() 