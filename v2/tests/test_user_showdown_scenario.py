#!/usr/bin/env python3
"""
用户摊牌场景测试。

模拟用户在http://localhost:8501/遇到的具体摊牌卡住问题。
"""

import unittest
import sys
import os
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from v2.core.state import GameState
from v2.core.enums import Phase, SeatStatus
from v2.core.cards import Card, Suit, Rank
from v2.core.player import Player
from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.events import EventBus


class TestUserShowdownScenario(unittest.TestCase):
    """测试用户摊牌场景"""
    
    def setUp(self):
        """设置测试环境"""
        self.logger = logging.getLogger(__name__)
        self.event_bus = EventBus()
        self.ai_strategy = SimpleAI()
        
    def create_user_scenario(self):
        """创建用户遇到的具体摊牌场景"""
        # 创建游戏状态
        game_state = GameState()
        
        # 创建并添加4个玩家，筹码数量与用户描述一致
        player_you = Player(seat_id=0, name="You", chips=946, is_human=True)
        player_ai1 = Player(seat_id=1, name="AI_1", chips=1162)  # 庄家
        player_ai2 = Player(seat_id=2, name="AI_2", chips=946)   # 当前行动（小盲）
        player_ai3 = Player(seat_id=3, name="AI_3", chips=946)   # 大盲
        
        game_state.add_player(player_you)
        game_state.add_player(player_ai1)
        game_state.add_player(player_ai2)
        game_state.add_player(player_ai3)
        
        # 设置庄家位置（AI_1是庄家）
        game_state.dealer_position = 1
        player_ai1.is_dealer = True
        
        # 设置盲注位置
        player_ai2.is_small_blind = True
        player_ai3.is_big_blind = True
        
        # 设置摊牌阶段
        game_state.phase = Phase.SHOWDOWN
        
        # 设置公共牌：A♥️ K♥️ 8♣️ 8♥️ 6♥️
        game_state.community_cards = [
            Card(Rank.ACE, Suit.HEARTS),
            Card(Rank.KING, Suit.HEARTS), 
            Card(Rank.EIGHT, Suit.CLUBS),
            Card(Rank.EIGHT, Suit.HEARTS),
            Card(Rank.SIX, Suit.HEARTS)
        ]
        
        # 设置玩家手牌：You: 3♥️ 5♥️ (同花)
        game_state.players[0].hole_cards = [Card(Rank.THREE, Suit.HEARTS), Card(Rank.FIVE, Suit.HEARTS)]
        game_state.players[1].hole_cards = [Card(Rank.ACE, Suit.CLUBS), Card(Rank.KING, Suit.CLUBS)]  # AI_1: 两对
        game_state.players[2].hole_cards = [Card(Rank.QUEEN, Suit.HEARTS), Card(Rank.JACK, Suit.HEARTS)]  # AI_2: 同花
        game_state.players[3].hole_cards = [Card(Rank.TEN, Suit.CLUBS), Card(Rank.NINE, Suit.CLUBS)]  # AI_3: 高牌
        
        # 设置底池（用户描述显示底池为$0，已收集$0，但实际应该有底池）
        # 根据日志"Collected 200 chips to pot (total: 216)"
        game_state.pot = 216
        
        # 所有玩家当前下注都是0（已收集到底池）
        for player in game_state.players:
            player.current_bet = 0
            player.status = SeatStatus.ACTIVE
        
        # 摊牌阶段没有当前玩家
        game_state.current_player = None
        game_state.current_bet = 0
        
        return game_state
    
    def test_user_scenario_setup(self):
        """测试用户场景设置是否正确"""
        game_state = self.create_user_scenario()
        controller = PokerController(game_state, self.ai_strategy, self.logger, self.event_bus)
        controller._hand_in_progress = True
        
        # 验证摊牌阶段状态
        snapshot = controller.get_snapshot()
        self.assertEqual(snapshot.phase, Phase.SHOWDOWN)
        self.assertIsNone(controller.get_current_player_id())
        self.assertTrue(controller.is_hand_over())
        
        # 验证玩家筹码
        self.assertEqual(snapshot.players[0].chips, 946)  # You
        self.assertEqual(snapshot.players[1].chips, 1162)  # AI_1
        self.assertEqual(snapshot.players[2].chips, 946)  # AI_2
        self.assertEqual(snapshot.players[3].chips, 946)  # AI_3
        
        # 验证底池
        self.assertEqual(snapshot.pot, 216)
        
        # 验证公共牌
        self.assertEqual(len(snapshot.community_cards), 5)
        
        # 验证手牌
        self.assertEqual(len(snapshot.players[0].hole_cards), 2)
    
    def test_showdown_calculation(self):
        """测试摊牌计算是否正确"""
        game_state = self.create_user_scenario()
        controller = PokerController(game_state, self.ai_strategy, self.logger, self.event_bus)
        controller._hand_in_progress = True
        
        # 执行摊牌
        result = controller.end_hand()
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertIsInstance(result.winner_ids, list)
        self.assertGreater(len(result.winner_ids), 0)
        self.assertEqual(result.pot_amount, 216)
        self.assertIsInstance(result.winning_hand_description, str)
        
        # 验证获胜者（应该是同花获胜）
        # You (3♥️ 5♥️) 和 AI_2 (Q♥️ J♥️) 都有同花，但AI_2的同花更大
        self.assertIn("同花", result.winning_hand_description)
        
        # 验证手牌状态已重置
        self.assertFalse(controller._hand_in_progress)
        
        # 验证底池已清空
        final_snapshot = controller.get_snapshot()
        self.assertEqual(final_snapshot.pot, 0)
    
    def test_ui_logic_simulation(self):
        """模拟UI逻辑处理摊牌场景"""
        # 模拟session state
        session_state = {
            'controller': None,
            'game_started': True,
            'showdown_processed': False,
            'hand_result_displayed': False,
            'events': []
        }
        
        game_state = self.create_user_scenario()
        controller = PokerController(game_state, self.ai_strategy, self.logger, self.event_bus)
        controller._hand_in_progress = True
        session_state['controller'] = controller
        
        # 模拟UI主循环逻辑
        def simulate_ui_main_loop():
            """模拟UI主循环"""
            controller = session_state['controller']
            
            # 检查手牌是否结束
            is_hand_over = controller.is_hand_over()
            
            if session_state['game_started'] and is_hand_over:
                # 手牌结束，处理摊牌逻辑
                snapshot = controller.get_snapshot()
                
                # 检查是否需要处理摊牌
                if (snapshot and snapshot.phase == Phase.SHOWDOWN and 
                    not session_state['showdown_processed']):
                    
                    # 摊牌阶段，计算结果
                    result = controller.end_hand()
                    if result:
                        # 标记摊牌已处理
                        session_state['showdown_processed'] = True
                        
                        # 记录手牌结束事件
                        session_state['events'].append(f"手牌结束: {result.winning_hand_description}")
                        
                        # 存储结果用于显示
                        session_state['last_hand_result'] = result
                        session_state['hand_result_displayed'] = False
                        
                        return "showdown_processed"
                    else:
                        session_state['showdown_processed'] = True
                        return "showdown_failed"
                
                # 显示手牌结果
                elif session_state['showdown_processed'] and not session_state['hand_result_displayed']:
                    session_state['hand_result_displayed'] = True
                    return "result_displayed"
                
                # 如果不在摊牌阶段但手牌已结束
                elif not snapshot or snapshot.phase != Phase.SHOWDOWN:
                    return "hand_ended_non_showdown"
            
            return "no_action"
        
        # 第一次循环：应该处理摊牌
        result1 = simulate_ui_main_loop()
        self.assertEqual(result1, "showdown_processed")
        self.assertTrue(session_state['showdown_processed'])
        self.assertFalse(session_state['hand_result_displayed'])
        self.assertEqual(len(session_state['events']), 1)
        
        # 第二次循环：应该显示结果
        result2 = simulate_ui_main_loop()
        self.assertEqual(result2, "result_displayed")
        self.assertTrue(session_state['hand_result_displayed'])
        
        # 第三次循环：应该无操作（避免无限循环）
        result3 = simulate_ui_main_loop()
        self.assertEqual(result3, "no_action")
    
    def test_multiple_cycles_no_infinite_loop(self):
        """测试多次循环不会产生无限循环"""
        # 模拟session state
        session_state = {
            'controller': None,
            'game_started': True,
            'showdown_processed': False,
            'hand_result_displayed': False,
            'events': []
        }
        
        game_state = self.create_user_scenario()
        controller = PokerController(game_state, self.ai_strategy, self.logger, self.event_bus)
        controller._hand_in_progress = True
        session_state['controller'] = controller
        
        # 计数器
        end_hand_calls = 0
        original_end_hand = controller.end_hand
        
        def counting_end_hand():
            nonlocal end_hand_calls
            end_hand_calls += 1
            return original_end_hand()
        
        controller.end_hand = counting_end_hand
        
        # 模拟多次UI循环（模拟用户看到的"Running... Running..."）
        actions = []
        for i in range(10):  # 模拟10次循环
            controller = session_state['controller']
            is_hand_over = controller.is_hand_over()
            
            if session_state['game_started'] and is_hand_over:
                snapshot = controller.get_snapshot()
                
                if (snapshot and snapshot.phase == Phase.SHOWDOWN and 
                    not session_state['showdown_processed']):
                    
                    result = controller.end_hand()
                    if result:
                        session_state['showdown_processed'] = True
                        session_state['events'].append(f"手牌结束: {result.winning_hand_description}")
                        session_state['last_hand_result'] = result
                        session_state['hand_result_displayed'] = False
                        actions.append(f"cycle_{i}_showdown_processed")
                    else:
                        session_state['showdown_processed'] = True
                        actions.append(f"cycle_{i}_showdown_failed")
                
                elif session_state['showdown_processed'] and not session_state['hand_result_displayed']:
                    session_state['hand_result_displayed'] = True
                    actions.append(f"cycle_{i}_result_displayed")
                
                else:
                    actions.append(f"cycle_{i}_no_action")
            else:
                actions.append(f"cycle_{i}_not_hand_over")
        
        # 验证end_hand只被调用一次
        self.assertEqual(end_hand_calls, 1, f"end_hand被调用了{end_hand_calls}次，应该只调用1次")
        
        # 验证状态正确
        self.assertTrue(session_state['showdown_processed'])
        self.assertTrue(session_state['hand_result_displayed'])
        
        # 验证操作序列
        self.assertIn("cycle_0_showdown_processed", actions)
        # 后续循环应该是no_action或result_displayed
        later_actions = [a for a in actions if not a.startswith("cycle_0")]
        for action in later_actions:
            self.assertIn("no_action", action, f"后续循环应该无操作，但发现: {action}")


def run_user_showdown_scenario_test():
    """运行用户摊牌场景测试"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("开始用户摊牌场景测试")
    
    # 运行测试
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUserShowdownScenario)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    if result.wasSuccessful():
        logger.info("✅ 所有用户摊牌场景测试通过")
        return True
    else:
        logger.error("❌ 用户摊牌场景测试失败")
        for failure in result.failures:
            logger.error(f"失败: {failure[0]} - {failure[1]}")
        for error in result.errors:
            logger.error(f"错误: {error[0]} - {error[1]}")
        return False


if __name__ == "__main__":
    success = run_user_showdown_scenario_test()
    sys.exit(0 if success else 1) 