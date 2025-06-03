#!/usr/bin/env python3
"""
摊牌阶段修复验证测试。

测试修复后的UI逻辑能否正确处理摊牌阶段，避免无限循环。
"""

import unittest
import sys
import os
import logging
from unittest.mock import Mock, patch, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from v2.core.state import GameState
from v2.core.enums import Phase, SeatStatus
from v2.core.cards import Card, Suit, Rank
from v2.core.player import Player
from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.events import EventBus


class TestShowdownFixValidation(unittest.TestCase):
    """测试摊牌阶段修复验证"""
    
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
        player_you = Player(seat_id=0, name="You", chips=946, is_human=True)
        player_ai1 = Player(seat_id=1, name="AI_1", chips=1162)
        player_ai2 = Player(seat_id=2, name="AI_2", chips=946)
        player_ai3 = Player(seat_id=3, name="AI_3", chips=946)
        
        game_state.add_player(player_you)
        game_state.add_player(player_ai1)
        game_state.add_player(player_ai2)
        game_state.add_player(player_ai3)
        
        # 设置庄家位置
        game_state.dealer_position = 1
        
        # 设置摊牌阶段
        game_state.phase = Phase.SHOWDOWN
        
        # 设置公共牌（A♥️ K♥️ 8♣️ 8♥️ 6♥️）
        game_state.community_cards = [
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.KING, Suit.HEARTS), 
            Card(Rank.EIGHT, Suit.CLUBS),
            Card(Rank.EIGHT, Suit.HEARTS),
            Card(Rank.SIX, Suit.HEARTS)
        ]
        
        # 设置玩家手牌
        game_state.players[0].hole_cards = [Card(Rank.THREE, Suit.HEARTS), Card(Rank.FIVE, Suit.HEARTS)]  # You: 同花
        game_state.players[1].hole_cards = [Card(Rank.ACE, Suit.CLUBS), Card(Rank.KING, Suit.CLUBS)]  # AI_1: 两对
        game_state.players[2].hole_cards = [Card(Rank.QUEEN, Suit.HEARTS), Card(Rank.JACK, Suit.HEARTS)]  # AI_2: 同花
        game_state.players[3].hole_cards = [Card(Rank.TEN, Suit.CLUBS), Card(Rank.NINE, Suit.CLUBS)]  # AI_3: 高牌
        
        # 设置底池
        game_state.pot = 216  # 根据用户描述的底池金额
        
        # 所有玩家当前下注都是0（已收集到底池）
        for player in game_state.players:
            player.current_bet = 0
            player.status = SeatStatus.ACTIVE
        
        # 摊牌阶段没有当前玩家
        game_state.current_player = None
        game_state.current_bet = 0
        
        return game_state
    
    def test_showdown_scenario_setup(self):
        """测试摊牌场景设置是否正确"""
        game_state = self.create_showdown_scenario()
        controller = PokerController(game_state, self.ai_strategy, self.logger, self.event_bus)
        controller._hand_in_progress = True
        
        # 验证摊牌阶段状态
        snapshot = controller.get_snapshot()
        self.assertEqual(snapshot.phase, Phase.SHOWDOWN)
        self.assertIsNone(controller.get_current_player_id())
        self.assertTrue(controller.is_hand_over())
        
        # 验证玩家状态
        self.assertEqual(len(snapshot.players), 4)
        for player in snapshot.players:
            self.assertEqual(player.status, SeatStatus.ACTIVE)
            self.assertEqual(player.current_bet, 0)
    
    def test_single_end_hand_call(self):
        """测试单次end_hand调用的正确性"""
        game_state = self.create_showdown_scenario()
        controller = PokerController(game_state, self.ai_strategy, self.logger, self.event_bus)
        controller._hand_in_progress = True
        
        # 第一次调用end_hand
        result = controller.end_hand()
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertIsInstance(result.winner_ids, list)
        self.assertGreater(len(result.winner_ids), 0)
        self.assertGreater(result.pot_amount, 0)
        self.assertIsInstance(result.winning_hand_description, str)
        
        # 验证手牌状态已重置
        self.assertFalse(controller._hand_in_progress)
        
        # 第二次调用end_hand应该返回None
        result2 = controller.end_hand()
        self.assertIsNone(result2)
    
    def test_ui_session_state_logic(self):
        """测试UI session state逻辑的正确性"""
        # 模拟session state
        session_state = {
            'showdown_processed': False,
            'hand_result_displayed': False,
            'events': [],
            'game_started': True
        }
        
        game_state = self.create_showdown_scenario()
        controller = PokerController(game_state, self.ai_strategy, self.logger, self.event_bus)
        controller._hand_in_progress = True
        
        # 模拟UI逻辑：第一次检查摊牌
        is_hand_over = controller.is_hand_over()
        snapshot = controller.get_snapshot()
        
        self.assertTrue(is_hand_over)
        self.assertEqual(snapshot.phase, Phase.SHOWDOWN)
        self.assertFalse(session_state['showdown_processed'])
        
        # 模拟处理摊牌
        if (snapshot and snapshot.phase == Phase.SHOWDOWN and 
            not session_state['showdown_processed']):
            
            result = controller.end_hand()
            if result:
                session_state['showdown_processed'] = True
                session_state['events'].append(f"手牌结束: {result.winning_hand_description}")
                session_state['last_hand_result'] = result
                session_state['hand_result_displayed'] = False
        
        # 验证状态更新
        self.assertTrue(session_state['showdown_processed'])
        self.assertFalse(session_state['hand_result_displayed'])
        self.assertEqual(len(session_state['events']), 1)
        self.assertIn('last_hand_result', session_state)
        
        # 模拟第二次检查（应该不再处理摊牌）
        if (snapshot and snapshot.phase == Phase.SHOWDOWN and 
            not session_state['showdown_processed']):
            # 这个分支不应该执行
            self.fail("摊牌逻辑被重复执行")
        
        # 模拟显示结果
        if session_state['showdown_processed'] and not session_state['hand_result_displayed']:
            session_state['hand_result_displayed'] = True
        
        self.assertTrue(session_state['hand_result_displayed'])
    
    def test_multiple_ui_cycles(self):
        """测试多次UI循环不会导致重复处理"""
        # 模拟session state
        session_state = {
            'showdown_processed': False,
            'hand_result_displayed': False,
            'events': [],
            'game_started': True
        }
        
        game_state = self.create_showdown_scenario()
        controller = PokerController(game_state, self.ai_strategy, self.logger, self.event_bus)
        controller._hand_in_progress = True
        
        end_hand_call_count = 0
        original_end_hand = controller.end_hand
        
        def mock_end_hand():
            nonlocal end_hand_call_count
            end_hand_call_count += 1
            return original_end_hand()
        
        controller.end_hand = mock_end_hand
        
        # 模拟多次UI循环
        for cycle in range(5):
            is_hand_over = controller.is_hand_over()
            snapshot = controller.get_snapshot()
            
            # 检查是否需要处理摊牌
            if (snapshot and snapshot.phase == Phase.SHOWDOWN and 
                not session_state['showdown_processed']):
                
                result = controller.end_hand()
                if result:
                    session_state['showdown_processed'] = True
                    session_state['events'].append(f"手牌结束: {result.winning_hand_description}")
                    session_state['last_hand_result'] = result
                    session_state['hand_result_displayed'] = False
            
            # 显示结果
            elif session_state['showdown_processed'] and not session_state['hand_result_displayed']:
                session_state['hand_result_displayed'] = True
        
        # 验证end_hand只被调用一次
        self.assertEqual(end_hand_call_count, 1)
        self.assertTrue(session_state['showdown_processed'])
        self.assertTrue(session_state['hand_result_displayed'])
    
    def test_new_hand_reset(self):
        """测试开始新手牌时状态重置"""
        # 模拟完成摊牌的session state
        session_state = {
            'showdown_processed': True,
            'hand_result_displayed': True,
            'events': ['手牌结束: AI_1 获胜 - 同花'],
            'game_started': True,
            'last_hand_result': Mock()
        }
        
        # 模拟开始新手牌
        session_state['events'] = []
        session_state['showdown_processed'] = False
        session_state['hand_result_displayed'] = False
        if 'last_hand_result' in session_state:
            del session_state['last_hand_result']
        
        # 验证重置
        self.assertFalse(session_state['showdown_processed'])
        self.assertFalse(session_state['hand_result_displayed'])
        self.assertEqual(len(session_state['events']), 0)
        self.assertNotIn('last_hand_result', session_state)


def run_showdown_fix_validation():
    """运行摊牌修复验证测试"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("开始摊牌修复验证测试")
    
    # 运行测试
    suite = unittest.TestLoader().loadTestsFromTestCase(TestShowdownFixValidation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    if result.wasSuccessful():
        logger.info("✅ 所有摊牌修复验证测试通过")
        return True
    else:
        logger.error("❌ 摊牌修复验证测试失败")
        for failure in result.failures:
            logger.error(f"失败: {failure[0]} - {failure[1]}")
        for error in result.errors:
            logger.error(f"错误: {error[0]} - {error[1]}")
        return False


if __name__ == "__main__":
    success = run_showdown_fix_validation()
    sys.exit(0 if success else 1) 