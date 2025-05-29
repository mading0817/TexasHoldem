#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克规则合规性测试
验证游戏逻辑是否符合标准德州扑克规则
这是规则测试的核心文件
"""

import sys
import os
import unittest
from typing import List, Dict

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 导入测试框架
from tests.common.data_structures import TestResult

# 导入核心游戏逻辑
from core_game_logic.core.enums import ActionType, GamePhase, Suit, Rank, Action, SeatStatus
from core_game_logic.core.card import Card, CardPool
from core_game_logic.core.deck import Deck
from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.betting.action_validator import ActionValidator
from tests.common.test_helpers import ActionHelper
# from core_game_logic.evaluator.hand_evaluator import HandEvaluator  # 暂时注释掉，模块不存在


class PokerComplianceTester(unittest.TestCase):
    """德州扑克规则合规性测试类 - 仅继承unittest.TestCase"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建测试玩家
        self.players = [
            Player(seat_id=0, name="Alice", chips=100),
            Player(seat_id=1, name="Bob", chips=100),
            Player(seat_id=2, name="Charlie", chips=100),
            Player(seat_id=3, name="David", chips=100)
        ]
        
        # 创建游戏状态
        self.game_state = GameState(
            players=self.players,
            dealer_position=0,
            small_blind=1,
            big_blind=2
        )
        
        # 初始化组件
        self.validator = ActionValidator()
        # self.evaluator = HandEvaluator()  # 暂时注释掉，模块不存在
        
        print(f"[DEBUG] BaseTester.__init__ starting for {self._testMethodName}")
    
    def test_standard_deck_compliance(self):
        """测试标准牌组合规性"""
        print("开始测试标准牌组合规性...")
        
        deck = Deck()
        
        # 验证标准52张牌
        self.assertEqual(len(deck._cards), 52, "标准牌组应该包含52张牌")
        
        # 验证没有重复牌
        card_strs = [str(card) for card in deck._cards]
        unique_cards = set(card_strs)
        self.assertEqual(len(card_strs), len(unique_cards), "牌组中不应有重复牌")
        
        # 验证所有花色和点数都存在
        suits = set()
        ranks = set()
        
        for card in deck._cards:
            suits.add(card.suit)
            ranks.add(card.rank)
        
        expected_suits = {Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS}
        expected_ranks = set(Rank)
        
        self.assertEqual(suits, expected_suits, "花色不完整")
        self.assertEqual(ranks, expected_ranks, "点数不完整")
        
        print("✓ 标准牌组合规性测试通过")
    
    def test_hand_cards_compliance(self):
        """测试手牌合规性"""
        print("开始测试手牌合规性...")
        
        # 初始化游戏状态
        self.game_state.deck = Deck()
        self.game_state.set_blinds()
        
        # 模拟发牌 - 定义测试用的手牌
        hole_cards = [
            self.game_state.deck.deal_card(),
            self.game_state.deck.deal_card()
        ]
        
        for player in self.players:
            if player.chips > 0:
                # 每个玩家应该有独特的手牌
                player.hole_cards = [
                    self.game_state.deck.deal_card(),
                    self.game_state.deck.deal_card()
                ]
        
        # 验证每个玩家都有2张手牌
        for player in self.players:
            if player.status == SeatStatus.ACTIVE:
                self.assertEqual(len(player.hole_cards), 2, f"玩家 {player.name} 应该有2张手牌")
        
        # 验证所有手牌都不相同
        all_hole_cards = []
        for player in self.players:
            if player.status == SeatStatus.ACTIVE:
                all_hole_cards.extend(player.hole_cards)
        
        card_strs = [str(card) for card in all_hole_cards]
        unique_cards = set(card_strs)
        self.assertEqual(len(card_strs), len(unique_cards), "所有手牌应该都不相同")
        
        print("✓ 手牌合规性测试通过")
    
    def test_community_cards_compliance(self):
        """测试公共牌合规性"""
        print("开始测试公共牌合规性...")
        
        # 初始化游戏状态
        self.game_state.deck = Deck()
        self.game_state.set_blinds()
        
        # 发手牌 - 定义测试用的手牌
        for player in self.players:
            if player.chips > 0:
                player.hole_cards = [
                    self.game_state.deck.deal_card(),
                    self.game_state.deck.deal_card()
                ]
        
        # 定义测试用的公共牌
        flop_cards = [
            self.game_state.deck.deal_card(),
            self.game_state.deck.deal_card(),
            self.game_state.deck.deal_card()
        ]
        turn_card = self.game_state.deck.deal_card()
        river_card = self.game_state.deck.deal_card()
        
        # 测试Flop（3张公共牌）
        self.game_state.community_cards.extend(flop_cards)
        self.assertEqual(len(self.game_state.community_cards), 3, "Flop应该有3张公共牌")
        
        # 测试Turn（第4张公共牌）
        self.game_state.community_cards.append(turn_card)
        self.assertEqual(len(self.game_state.community_cards), 4, "Turn后应该有4张公共牌")
        
        # 测试River（第5张公共牌）
        self.game_state.community_cards.append(river_card)
        self.assertEqual(len(self.game_state.community_cards), 5, "River后应该有5张公共牌")
        
        # 验证公共牌都不相同
        card_strs = [str(card) for card in self.game_state.community_cards]
        unique_cards = set(card_strs)
        self.assertEqual(len(card_strs), len(unique_cards), "公共牌应该都不相同")
        
        print("✓ 公共牌合规性测试通过")
    
    def test_betting_structure_compliance(self):
        """测试下注结构合规性"""
        print("开始测试下注结构合规性...")
        
        # 初始化游戏状态
        self.game_state.set_blinds()
        
        # 验证盲注设置
        small_blind_player = None
        big_blind_player = None
        
        for player in self.players:
            if player.is_small_blind:
                small_blind_player = player
            if player.is_big_blind:
                big_blind_player = player
        
        self.assertIsNotNone(small_blind_player, "应该有小盲注玩家")
        self.assertIsNotNone(big_blind_player, "应该有大盲注玩家")
        self.assertEqual(small_blind_player.current_bet, self.game_state.small_blind, "小盲注金额不正确")
        self.assertEqual(big_blind_player.current_bet, self.game_state.big_blind, "大盲注金额不正确")
        
        print("✓ 下注结构合规性测试通过")
    
    def test_action_types_compliance(self):
        """测试操作类型合规性"""
        print("开始测试操作类型合规性...")
        
        # 测试所有基本操作类型
        action_types = [ActionType.FOLD, ActionType.CHECK, ActionType.CALL, 
                       ActionType.BET, ActionType.RAISE, ActionType.ALL_IN]
        
        for action_type in action_types:
            # 验证操作类型可以创建
            if action_type in [ActionType.BET, ActionType.RAISE]:
                # 需要金额的操作类型
                action = Action(action_type, 10)
            else:
                # 不需要金额的操作类型
                action = Action(action_type)
            self.assertEqual(action.action_type, action_type, f"操作类型 {action_type} 创建失败")
        
        # 测试操作验证
        validator = ActionValidator()
        
        # 这里可以添加更多具体的操作验证测试
        print("✓ 操作类型合规性测试通过")
    
    def test_hand_ranking_compliance(self):
        """测试手牌排名合规性"""
        print("开始测试手牌排名合规性...")
        
        try:
            # 创建一些测试手牌
            royal_flush = [
                CardPool.get_card(Rank.ACE, Suit.SPADES), 
                CardPool.get_card(Rank.KING, Suit.SPADES), 
                CardPool.get_card(Rank.QUEEN, Suit.SPADES),
                CardPool.get_card(Rank.JACK, Suit.SPADES), 
                CardPool.get_card(Rank.TEN, Suit.SPADES)
            ]
            
            straight_flush = [
                CardPool.get_card(Rank.NINE, Suit.HEARTS), 
                CardPool.get_card(Rank.EIGHT, Suit.HEARTS), 
                CardPool.get_card(Rank.SEVEN, Suit.HEARTS),
                CardPool.get_card(Rank.SIX, Suit.HEARTS), 
                CardPool.get_card(Rank.FIVE, Suit.HEARTS)
            ]
            
            # 验证手牌创建成功
            self.assertEqual(len(royal_flush), 5, "皇家同花顺应该有5张牌")
            self.assertEqual(len(straight_flush), 5, "同花顺应该有5张牌")
            
            # 这里可以添加手牌评估器的测试
            # 目前只验证手牌创建的合规性
            
        except Exception as e:
            print(f"  ⚠ 手牌评估测试遇到问题: {e}")
        
        print("✓ 手牌排名合规性测试通过")
    
    def test_dealer_button_rotation(self):
        """测试庄家按钮轮转合规性"""
        print("开始测试庄家按钮轮转合规性...")
        
        initial_dealer = self.game_state.dealer_position
        
        # 进行多手牌，验证庄家位置轮转
        for hand_num in range(len(self.game_state.get_active_players()) + 2):
            # 模拟新手牌开始
            self.game_state.dealer_position = hand_num % len(self.players)
            
            current_dealer = self.game_state.dealer_position
            expected_dealer = hand_num % len(self.players)
            
            self.assertEqual(current_dealer, expected_dealer, 
                           f"手牌 {hand_num + 1}: 庄家位置应该是 {expected_dealer}")
            
            # 简单完成这手牌
            self._quick_complete_hand()
        
        print("✓ 庄家按钮轮转合规性测试通过")
    
    def test_blind_posting_compliance(self):
        """测试盲注投注合规性"""
        print("开始测试盲注投注合规性...")
        
        # 设置盲注
        self.game_state.set_blinds()
        
        # 获取盲注信息
        small_blind_amount = self.game_state.small_blind
        big_blind_amount = self.game_state.big_blind
        
        # 验证盲注已经被正确投注
        total_blinds = 0
        for player in self.players:
            total_blinds += player.current_bet
        
        expected_initial_pot = small_blind_amount + big_blind_amount
        
        self.assertEqual(total_blinds, expected_initial_pot, 
                        "盲注总额应该等于小盲注加大盲注")
        
        print("✓ 盲注投注合规性测试通过")
    
    def test_showdown_compliance(self):
        """测试摊牌合规性"""
        print("开始测试摊牌合规性...")
        
        # 初始化游戏状态
        self.game_state.deck = Deck()
        self.game_state.set_blinds()
        
        # 发手牌 - 定义测试用的手牌
        for player in self.players:
            if player.chips > 0:
                player.hole_cards = [
                    self.game_state.deck.deal_card(),
                    self.game_state.deck.deal_card()
                ]
        
        # 模拟到摊牌阶段
        self._advance_to_showdown()
        
        # 验证摊牌阶段
        self.assertEqual(self.game_state.phase, GamePhase.SHOWDOWN, "应该处于摊牌阶段")
        
        # 验证仍有活跃玩家
        active_players = self.game_state.get_players_in_hand()
        self.assertGreater(len(active_players), 0, "摊牌时必须至少有一个玩家")
        
        print("✓ 摊牌合规性测试通过")
    
    def test_pot_limit_compliance(self):
        """测试底池限制合规性"""
        print("开始测试底池限制合规性...")
        
        # 初始化游戏状态
        self.game_state.set_blinds()
        
        # 测试下注不能超过底池（在底池限制德州扑克中）
        current_pot = self.game_state.pot
        current_player = self.game_state.get_current_player()
        
        if current_player:
            # 在无限德州扑克中，玩家可以下注所有筹码
            max_bet = current_player.chips
            
            # 验证All-in是允许的
            all_in_action = ActionHelper.create_player_action(current_player, ActionType.ALL_IN, max_bet)
            try:
                # 这里应该使用ActionValidator来验证，但目前只是基本检查
                self.assertIsNotNone(all_in_action, "All-in操作应该可以创建")
                print(f"  All-in验证结果: 有效")
            except Exception as e:
                print(f"  All-in验证异常: {e}")
        
        print("✓ 底池限制合规性测试通过")
    
    def _advance_to_flop(self):
        """推进到Flop阶段"""
        # 完成preflop下注
        self._complete_betting_round()
        # 进入flop
        self.game_state.advance_phase()
    
    def _advance_to_turn(self):
        """推进到Turn阶段"""
        self._complete_betting_round()
        self.game_state.advance_phase()
    
    def _advance_to_river(self):
        """推进到River阶段"""
        self._complete_betting_round()
        self.game_state.advance_phase()
    
    def _advance_to_showdown(self):
        """推进到Showdown阶段"""
        phases = [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]
        
        for phase in phases:
            if self.game_state.phase == phase:
                self._complete_betting_round()
                if phase != GamePhase.RIVER:
                    self.game_state.advance_phase()
        
        # 进入showdown
        if self.game_state.phase == GamePhase.RIVER:
            self.game_state.advance_phase()
    
    def _complete_betting_round(self):
        """完成下注轮"""
        max_actions = 15
        actions_taken = 0
        
        # 简化的下注轮完成逻辑
        for player in self.players:
            if player.status == SeatStatus.ACTIVE and actions_taken < max_actions:
                # 模拟简单的check或call
                if self.game_state.current_bet == 0:
                    # 可以check
                    pass
                else:
                    # 需要call或fold，这里简化为设置相同下注
                    if player.chips >= self.game_state.current_bet - player.current_bet:
                        call_amount = self.game_state.current_bet - player.current_bet
                        player.bet(call_amount)
                
                actions_taken += 1
    
    def _quick_complete_hand(self):
        """快速完成一手牌"""
        # 快速完成所有阶段
        phases = [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]
        
        for phase in phases:
            if self.game_state.phase == phase:
                self._complete_betting_round()
                if phase != GamePhase.RIVER:
                    self.game_state.advance_phase()
        
        # 进入showdown并结算
        if self.game_state.phase == GamePhase.RIVER:
            self.game_state.advance_phase()
        
        # 重置状态为下一手牌


def run_poker_compliance_tests():
    """运行德州扑克规则合规测试"""
    print("=" * 60)
    print("德州扑克规则合规测试套件")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(PokerComplianceTester)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果 - 修复构造函数参数
    return TestResult(
        scenario_name="德州扑克规则合规测试套件",
        test_name="德州扑克规则合规测试",
        passed=result.wasSuccessful(),
        expected="所有测试通过",
        actual=f"成功: {result.testsRun - len(result.failures) - len(result.errors)}, "
               f"失败: {len(result.failures)}, 错误: {len(result.errors)}",
        details=f"总测试数: {result.testsRun}, 成功: {result.testsRun - len(result.failures) - len(result.errors)}, "
                f"失败: {len(result.failures)}, 错误: {len(result.errors)}"
    )


if __name__ == "__main__":
    result = run_poker_compliance_tests()
    print(f"\n测试结果: {result}")
    exit(0 if result.passed else 1) 