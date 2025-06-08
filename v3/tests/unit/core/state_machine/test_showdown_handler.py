"""
单元测试: ShowdownHandler
"""
import unittest
from unittest.mock import MagicMock

from v3.core.state_machine.phase_handlers import ShowdownHandler
from v3.core.state_machine.types import GameContext, GamePhase
from v3.core.deck.card import Card
from v3.core.deck.types import Suit, Rank
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker

class TestShowdownHandler(unittest.TestCase):
    """测试 ShowdownHandler 的功能"""

    def setUp(self):
        """测试设置"""
        self.handler = ShowdownHandler()
        # 遵循TDD，我们使用真实对象
        CoreUsageChecker.verify_real_objects(self.handler, "ShowdownHandler")

    def test_simple_winner_determination(self):
        """测试：简单场景，一个赢家，无边池"""
        # 1. 设置: 玩家筹码应反映下注后的状态
        ctx = GameContext(
            game_id='test_game_simple',
            current_phase=GamePhase.SHOWDOWN,
            players={
                'player1': { # Winner
                    'chips': 50, 'total_bet_this_hand': 50, 'status': 'active',
                    'hole_cards': [Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.ACE)]
                },
                'player2': { # Loser
                    'chips': 50, 'total_bet_this_hand': 50, 'status': 'active',
                    'hole_cards': [Card(Suit.HEARTS, Rank.KING), Card(Suit.SPADES, Rank.KING)]
                }
            },
            community_cards=[
                Card(Suit.CLUBS, Rank.TWO), Card(Suit.CLUBS, Rank.THREE), Card(Suit.CLUBS, Rank.FOUR),
                Card(Suit.DIAMONDS, Rank.TEN), Card(Suit.DIAMONDS, Rank.NINE)
            ],
            pot_total=100,
            current_bet=50
        )
        
        # 2. 执行
        self.handler._determine_winners(ctx)

        # 3. 断言
        self.assertEqual(ctx.players['player1']['chips'], 150) # 50 remaining + 100 winnings
        self.assertEqual(ctx.players['player1']['winnings'], 100)
        self.assertEqual(ctx.players['player2']['chips'], 50) # No winnings
        self.assertNotIn('winnings', ctx.players['player2'])
        self.assertEqual(ctx.pot_total, 0)
        self.assertIn('player1', ctx.winner_info['winners'])
        self.assertEqual(ctx.winner_info['winners']['player1']['hand'], 'ONE_PAIR')

    def test_split_pot_determination(self):
        """测试：平分底池，两个赢家手牌相同"""
        # 1. 设置: 玩家筹码应反映下注后的状态
        ctx = GameContext(
            game_id='test_game_split',
            current_phase=GamePhase.SHOWDOWN,
            players={
                'player1': {
                    'chips': 50, 'total_bet_this_hand': 50, 'status': 'active',
                    'hole_cards': [Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.KING)]
                },
                'player2': {
                    'chips': 50, 'total_bet_this_hand': 50, 'status': 'active',
                    'hole_cards': [Card(Suit.DIAMONDS, Rank.ACE), Card(Suit.CLUBS, Rank.KING)]
                }
            },
            community_cards=[
                Card(Suit.CLUBS, Rank.TWO), Card(Suit.CLUBS, Rank.THREE), Card(Suit.CLUBS, Rank.FOUR),
                Card(Suit.DIAMONDS, Rank.FIVE), Card(Suit.DIAMONDS, Rank.SIX) # This is a straight
            ],
            pot_total=100,
            current_bet=50
        )

        # 2. 执行
        self.handler._determine_winners(ctx)

        # 3. 断言
        self.assertEqual(ctx.players['player1']['chips'], 100) # 50 remaining + 50 winnings
        self.assertEqual(ctx.players['player1']['winnings'], 50)
        self.assertEqual(ctx.players['player2']['chips'], 100) # 50 remaining + 50 winnings
        self.assertEqual(ctx.players['player2']['winnings'], 50)
        self.assertEqual(ctx.pot_total, 0)
        self.assertIn('player1', ctx.winner_info['winners'])
        self.assertIn('player2', ctx.winner_info['winners'])
        self.assertEqual(ctx.winner_info['winners']['player1']['hand'], 'STRAIGHT')
        self.assertEqual(ctx.winner_info['winners']['player2']['hand'], 'STRAIGHT')


    def test_side_pot_determination(self):
        """测试：复杂的边池场景"""
        # 1. 设置
        # Player3 all-in for 25. Main pot = 25*3=75.
        # Player1 and Player2 continue betting another 75. Side pot = 75*2=150.
        # Total pot = 225.
        # Player3 has the best hand overall (Full House) and wins the main pot.
        # Player1 has the second best hand (Flush) and wins the side pot.
        ctx = GameContext(
            game_id='test_game_sidepot',
            current_phase=GamePhase.SHOWDOWN,
            players={
                'player1': { # Wins side pot
                    'chips': 0, 'total_bet_this_hand': 100, 'status': 'active',
                    'hole_cards': [Card(Suit.HEARTS, Rank.ACE), Card(Suit.HEARTS, Rank.KING)] # Flush
                },
                'player2': { # Loser
                    'chips': 0, 'total_bet_this_hand': 100, 'status': 'active',
                    'hole_cards': [Card(Suit.SPADES, Rank.ACE), Card(Suit.SPADES, Rank.KING)] # High Card
                },
                'player3': { # Wins main pot (all-in)
                    'chips': 0, 'total_bet_this_hand': 25, 'status': 'all_in',
                    'hole_cards': [Card(Suit.DIAMONDS, Rank.TEN), Card(Suit.CLUBS, Rank.TEN)] # Full House
                }
            },
            community_cards=[
                Card(Suit.HEARTS, Rank.TEN), Card(Suit.HEARTS, Rank.SEVEN), Card(Suit.HEARTS, Rank.TWO),
                Card(Suit.DIAMONDS, Rank.KING), Card(Suit.SPADES, Rank.TEN)
            ],
            pot_total=225,
            current_bet=100
        )

        # 2. 执行
        self.handler._determine_winners(ctx)

        # 3. 断言
        # Player1: 0(remaining) + 150(side pot win) = 150
        self.assertEqual(ctx.players['player1']['chips'], 150)
        self.assertEqual(ctx.players['player1']['winnings'], 150)
        
        # Player2: 0(remaining) + 0 = 0
        self.assertEqual(ctx.players['player2']['chips'], 0)
        self.assertNotIn('winnings', ctx.players['player2'])

        # Player3: 0(remaining) + 75(main pot win) = 75
        self.assertEqual(ctx.players['player3']['chips'], 75)
        self.assertEqual(ctx.players['player3']['winnings'], 75)

        self.assertEqual(ctx.pot_total, 0)
        self.assertIn('player1', ctx.winner_info['winners'])
        self.assertIn('player3', ctx.winner_info['winners'])
        self.assertEqual(ctx.winner_info['winners']['player1']['hand'], 'FLUSH')
        self.assertEqual(ctx.winner_info['winners']['player3']['hand'], 'FOUR_OF_A_KIND')


if __name__ == '__main__':
    unittest.main() 