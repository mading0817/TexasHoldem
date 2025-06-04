"""
德州扑克牌组和评估器模块的单元测试.

测试Card、Deck和HandEvaluator类的功能，确保与v2版本100%兼容.
包含反作弊验证，确保测试使用真实的核心模块.
"""

import pytest
import random
from typing import List

from v3.core.deck import Card, Deck
from v3.core.deck.types import Suit, Rank
from v3.core.eval import HandEvaluator, HandRank, HandResult
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestCard:
    """Card类的单元测试."""

    def test_card_creation(self):
        """测试Card对象的创建."""
        card = Card(Suit.HEARTS, Rank.ACE)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(card, "Card")
        
        assert card.suit == Suit.HEARTS
        assert card.rank == Rank.ACE
        assert card.rank.value == 14

    def test_card_immutability(self):
        """测试Card对象的不可变性."""
        card = Card(Suit.SPADES, Rank.KING)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(card, "Card")
        
        # 尝试修改应该失败
        with pytest.raises(AttributeError):
            card.suit = Suit.HEARTS
        with pytest.raises(AttributeError):
            card.rank = Rank.ACE

    def test_card_string_representation(self):
        """测试Card的字符串表示."""
        test_cases = [
            (Card(Suit.HEARTS, Rank.ACE), "AH"),
            (Card(Suit.SPADES, Rank.KING), "KS"),
            (Card(Suit.DIAMONDS, Rank.TEN), "10D"),
            (Card(Suit.CLUBS, Rank.TWO), "2C"),
        ]
        
        for card, expected in test_cases:
            # 反作弊检查
            CoreUsageChecker.verify_real_objects(card, "Card")
            assert str(card) == expected

    def test_card_from_string(self):
        """测试从字符串创建Card对象."""
        test_cases = [
            ("AH", Card(Suit.HEARTS, Rank.ACE)),
            ("KS", Card(Suit.SPADES, Rank.KING)),
            ("10D", Card(Suit.DIAMONDS, Rank.TEN)),
            ("2c", Card(Suit.CLUBS, Rank.TWO)),
            ("Th", Card(Suit.HEARTS, Rank.TEN)),
        ]
        
        for card_str, expected in test_cases:
            card = Card.from_str(card_str)
            # 反作弊检查
            CoreUsageChecker.verify_real_objects(card, "Card")
            assert card == expected

    def test_card_from_string_invalid(self):
        """测试无效字符串创建Card对象."""
        invalid_strings = ["", "A", "XH", "AX", "123H"]
        
        for invalid_str in invalid_strings:
            with pytest.raises((ValueError, TypeError)):
                Card.from_str(invalid_str)

    def test_card_comparison(self):
        """测试Card对象的比较."""
        ace_hearts = Card(Suit.HEARTS, Rank.ACE)
        king_spades = Card(Suit.SPADES, Rank.KING)
        ace_spades = Card(Suit.SPADES, Rank.ACE)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ace_hearts, "Card")
        CoreUsageChecker.verify_real_objects(king_spades, "Card")
        CoreUsageChecker.verify_real_objects(ace_spades, "Card")
        
        # 测试大小比较
        assert ace_hearts > king_spades
        assert king_spades < ace_hearts
        
        # 测试相等性
        assert ace_hearts != ace_spades  # 不同花色
        assert ace_hearts == Card(Suit.HEARTS, Rank.ACE)  # 相同花色和点数

    def test_card_hash(self):
        """测试Card对象的哈希值."""
        card1 = Card(Suit.HEARTS, Rank.ACE)
        card2 = Card(Suit.HEARTS, Rank.ACE)
        card3 = Card(Suit.SPADES, Rank.ACE)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(card1, "Card")
        
        # 相同的牌应该有相同的哈希值
        assert hash(card1) == hash(card2)
        # 不同的牌应该有不同的哈希值
        assert hash(card1) != hash(card3)

    def test_card_validation(self):
        """测试Card对象的验证."""
        # 测试无效的花色类型
        with pytest.raises(TypeError):
            Card("invalid", Rank.ACE)
        
        # 测试无效的点数类型
        with pytest.raises(TypeError):
            Card(Suit.HEARTS, "invalid")


class TestDeck:
    """Deck类的单元测试."""

    def test_deck_creation(self):
        """测试Deck对象的创建."""
        deck = Deck()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        
        assert len(deck) == 52
        assert deck.cards_remaining == 52
        assert not deck.is_empty

    def test_deck_with_custom_rng(self):
        """测试使用自定义随机数生成器的Deck."""
        rng = random.Random(42)
        deck = Deck(rng)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        
        assert len(deck) == 52

    def test_deck_deal_card(self):
        """测试发牌功能."""
        deck = Deck()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        
        initial_count = len(deck)
        card = deck.deal_card()
        
        # 反作弊检查发出的牌
        CoreUsageChecker.verify_real_objects(card, "Card")
        
        assert isinstance(card, Card)
        assert len(deck) == initial_count - 1

    def test_deck_deal_multiple_cards(self):
        """测试发多张牌功能."""
        deck = Deck()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        
        cards = deck.deal_cards(5)
        
        assert len(cards) == 5
        assert len(deck) == 47
        
        # 检查所有发出的牌都是Card对象
        for card in cards:
            CoreUsageChecker.verify_real_objects(card, "Card")

    def test_deck_deal_from_empty(self):
        """测试从空牌组发牌."""
        deck = Deck()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        
        # 发完所有牌
        deck.deal_cards(52)
        assert deck.is_empty
        
        # 尝试从空牌组发牌应该失败
        with pytest.raises(IndexError):
            deck.deal_card()

    def test_deck_deal_too_many_cards(self):
        """测试发牌数量超过剩余牌数."""
        deck = Deck()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        
        with pytest.raises(IndexError):
            deck.deal_cards(53)

    def test_deck_deal_negative_count(self):
        """测试发牌数量为负数."""
        deck = Deck()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        
        with pytest.raises(ValueError):
            deck.deal_cards(-1)

    def test_deck_shuffle(self):
        """测试洗牌功能."""
        # 使用固定种子确保可重现性
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        
        deck1 = Deck(rng1)
        deck2 = Deck(rng2)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck1, "Deck")
        CoreUsageChecker.verify_real_objects(deck2, "Deck")
        
        # 洗牌前两个牌组应该相同
        cards1_before = deck1.deal_cards(52)
        deck1.reset()
        cards2_before = deck2.deal_cards(52)
        deck2.reset()
        
        assert cards1_before == cards2_before
        
        # 洗牌后应该相同（因为使用相同种子）
        deck1.shuffle()
        deck2.shuffle()
        
        cards1_after = deck1.deal_cards(52)
        cards2_after = deck2.deal_cards(52)
        
        assert cards1_after == cards2_after
        # 洗牌后的顺序应该与洗牌前不同
        assert cards1_after != cards1_before

    def test_deck_reset(self):
        """测试重置牌组功能."""
        deck = Deck()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        
        # 发一些牌
        deck.deal_cards(10)
        assert len(deck) == 42
        
        # 重置牌组
        deck.reset()
        assert len(deck) == 52
        assert not deck.is_empty

    def test_deck_peek_top(self):
        """测试查看顶牌功能."""
        deck = Deck()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        
        top_card = deck.peek_top()
        assert top_card is not None
        
        # 反作弊检查查看的牌
        CoreUsageChecker.verify_real_objects(top_card, "Card")
        
        # 查看不应该改变牌组大小
        assert len(deck) == 52
        
        # 发出的牌应该与查看的牌相同
        dealt_card = deck.deal_card()
        assert dealt_card == top_card

    def test_deck_peek_empty(self):
        """测试查看空牌组的顶牌."""
        deck = Deck()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(deck, "Deck")
        
        # 发完所有牌
        deck.deal_cards(52)
        
        # 查看空牌组应该返回None
        assert deck.peek_top() is None


class TestHandEvaluator:
    """HandEvaluator类的单元测试."""

    def test_evaluator_creation(self):
        """测试HandEvaluator对象的创建."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")

    def test_evaluate_royal_flush(self):
        """测试皇家同花顺的评估."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        hole_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.HEARTS, Rank.KING)
        ]
        community_cards = [
            Card(Suit.HEARTS, Rank.QUEEN),
            Card(Suit.HEARTS, Rank.JACK),
            Card(Suit.HEARTS, Rank.TEN),
            Card(Suit.SPADES, Rank.TWO),
            Card(Suit.CLUBS, Rank.THREE)
        ]
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        assert result.rank == HandRank.ROYAL_FLUSH
        assert result.primary_value == 14  # A高

    def test_evaluate_straight_flush(self):
        """测试同花顺的评估."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        hole_cards = [
            Card(Suit.HEARTS, Rank.NINE),
            Card(Suit.HEARTS, Rank.EIGHT)
        ]
        community_cards = [
            Card(Suit.HEARTS, Rank.SEVEN),
            Card(Suit.HEARTS, Rank.SIX),
            Card(Suit.HEARTS, Rank.FIVE),
            Card(Suit.SPADES, Rank.TWO),
            Card(Suit.CLUBS, Rank.THREE)
        ]
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        assert result.rank == HandRank.STRAIGHT_FLUSH
        assert result.primary_value == 9  # 9高

    def test_evaluate_four_of_a_kind(self):
        """测试四条的评估."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        hole_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.ACE)
        ]
        community_cards = [
            Card(Suit.DIAMONDS, Rank.ACE),
            Card(Suit.CLUBS, Rank.ACE),
            Card(Suit.HEARTS, Rank.KING),
            Card(Suit.SPADES, Rank.TWO),
            Card(Suit.CLUBS, Rank.THREE)
        ]
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        assert result.rank == HandRank.FOUR_OF_A_KIND
        assert result.primary_value == 14  # A的四条
        assert result.kickers == (13,)  # K踢脚

    def test_evaluate_full_house(self):
        """测试葫芦的评估."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        hole_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.ACE)
        ]
        community_cards = [
            Card(Suit.DIAMONDS, Rank.ACE),
            Card(Suit.CLUBS, Rank.KING),
            Card(Suit.HEARTS, Rank.KING),
            Card(Suit.SPADES, Rank.TWO),
            Card(Suit.CLUBS, Rank.THREE)
        ]
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        assert result.rank == HandRank.FULL_HOUSE
        assert result.primary_value == 14  # A的三条
        assert result.secondary_value == 13  # K的对子

    def test_evaluate_flush(self):
        """测试同花的评估."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        hole_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.HEARTS, Rank.KING)
        ]
        community_cards = [
            Card(Suit.HEARTS, Rank.QUEEN),
            Card(Suit.HEARTS, Rank.NINE),
            Card(Suit.HEARTS, Rank.SEVEN),
            Card(Suit.SPADES, Rank.TWO),
            Card(Suit.CLUBS, Rank.THREE)
        ]
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        assert result.rank == HandRank.FLUSH
        assert result.primary_value == 14  # A高
        assert result.kickers == (13, 12, 9, 7)  # 其他牌

    def test_evaluate_straight(self):
        """测试顺子的评估."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        hole_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING)
        ]
        community_cards = [
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK),
            Card(Suit.HEARTS, Rank.TEN),
            Card(Suit.SPADES, Rank.TWO),
            Card(Suit.CLUBS, Rank.THREE)
        ]
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        assert result.rank == HandRank.STRAIGHT
        assert result.primary_value == 14  # A高

    def test_evaluate_wheel_straight(self):
        """测试A-2-3-4-5顺子的评估."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        hole_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.TWO)
        ]
        community_cards = [
            Card(Suit.DIAMONDS, Rank.THREE),
            Card(Suit.CLUBS, Rank.FOUR),
            Card(Suit.HEARTS, Rank.FIVE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.CLUBS, Rank.QUEEN)
        ]
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        assert result.rank == HandRank.STRAIGHT
        assert result.primary_value == 5  # 5高（A-2-3-4-5）

    def test_evaluate_three_of_a_kind(self):
        """测试三条的评估."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        hole_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.ACE)
        ]
        community_cards = [
            Card(Suit.DIAMONDS, Rank.ACE),
            Card(Suit.CLUBS, Rank.KING),
            Card(Suit.HEARTS, Rank.QUEEN),
            Card(Suit.SPADES, Rank.TWO),
            Card(Suit.CLUBS, Rank.THREE)
        ]
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        assert result.rank == HandRank.THREE_OF_A_KIND
        assert result.primary_value == 14  # A的三条
        assert result.kickers == (13, 12)  # K, Q踢脚

    def test_evaluate_two_pair(self):
        """测试两对的评估."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        hole_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.ACE)
        ]
        community_cards = [
            Card(Suit.DIAMONDS, Rank.KING),
            Card(Suit.CLUBS, Rank.KING),
            Card(Suit.HEARTS, Rank.QUEEN),
            Card(Suit.SPADES, Rank.TWO),
            Card(Suit.CLUBS, Rank.THREE)
        ]
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        assert result.rank == HandRank.TWO_PAIR
        assert result.primary_value == 14  # A对
        assert result.secondary_value == 13  # K对
        assert result.kickers == (12,)  # Q踢脚

    def test_evaluate_one_pair(self):
        """测试一对的评估."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        hole_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.ACE)
        ]
        community_cards = [
            Card(Suit.DIAMONDS, Rank.KING),
            Card(Suit.CLUBS, Rank.QUEEN),
            Card(Suit.HEARTS, Rank.JACK),
            Card(Suit.SPADES, Rank.TWO),
            Card(Suit.CLUBS, Rank.THREE)
        ]
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        assert result.rank == HandRank.ONE_PAIR
        assert result.primary_value == 14  # A对
        assert result.kickers == (13, 12, 11)  # K, Q, J踢脚

    def test_evaluate_high_card(self):
        """测试高牌的评估."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        hole_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING)
        ]
        community_cards = [
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK),
            Card(Suit.HEARTS, Rank.NINE),
            Card(Suit.SPADES, Rank.TWO),
            Card(Suit.CLUBS, Rank.THREE)
        ]
        
        result = evaluator.evaluate_hand(hole_cards, community_cards)
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(result, "HandResult")
        
        assert result.rank == HandRank.HIGH_CARD
        assert result.primary_value == 14  # A高
        assert result.kickers == (13, 12, 11, 9)  # 其他牌

    def test_compare_hands(self):
        """测试牌型比较功能."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        # 创建两个不同的牌型
        hand1 = HandResult(HandRank.ONE_PAIR, 14, 0, (13, 12, 11))
        hand2 = HandResult(HandRank.TWO_PAIR, 13, 12, (11,))
        
        # 反作弊检查结果
        CoreUsageChecker.verify_real_objects(hand1, "HandResult")
        CoreUsageChecker.verify_real_objects(hand2, "HandResult")
        
        # 两对应该比一对强
        assert evaluator.compare_hands(hand2, hand1) == 1
        assert evaluator.compare_hands(hand1, hand2) == -1
        assert evaluator.compare_hands(hand1, hand1) == 0

    def test_evaluate_hand_validation(self):
        """测试evaluate_hand的输入验证."""
        evaluator = HandEvaluator()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(evaluator, "HandEvaluator")
        
        valid_hole_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING)
        ]
        valid_community_cards = [
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK),
            Card(Suit.HEARTS, Rank.TEN)
        ]
        
        # 测试无效的手牌数量
        with pytest.raises(ValueError):
            evaluator.evaluate_hand([Card(Suit.HEARTS, Rank.ACE)], valid_community_cards)
        
        # 测试过多的公共牌
        with pytest.raises(ValueError):
            evaluator.evaluate_hand(valid_hole_cards, valid_community_cards + [
                Card(Suit.SPADES, Rank.NINE),
                Card(Suit.CLUBS, Rank.EIGHT),
                Card(Suit.DIAMONDS, Rank.SEVEN)
            ])
        
        # 测试总牌数不足
        with pytest.raises(ValueError):
            evaluator.evaluate_hand(valid_hole_cards, [Card(Suit.DIAMONDS, Rank.QUEEN)])
        
        # 测试无效的输入类型
        with pytest.raises(TypeError):
            evaluator.evaluate_hand("invalid", valid_community_cards)
        
        with pytest.raises(TypeError):
            evaluator.evaluate_hand(valid_hole_cards, "invalid")
        
        # 测试无效的牌类型
        with pytest.raises(TypeError):
            evaluator.evaluate_hand(["invalid_card", valid_hole_cards[1]], valid_community_cards) 