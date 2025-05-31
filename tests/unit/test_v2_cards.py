"""
v2/core/cards.py 的单元测试。

测试Card和Deck类的基本功能。
"""

import pytest
import random
from v2.core.cards import Card, Deck
from v2.core.enums import Suit, Rank


class TestCard:
    """测试Card类的功能。"""
    
    def test_card_creation(self):
        """测试Card对象的创建。"""
        card = Card(Suit.HEARTS, Rank.ACE)
        assert card.suit == Suit.HEARTS
        assert card.rank == Rank.ACE
    
    def test_card_string_representation(self):
        """测试Card的字符串表示。"""
        card = Card(Suit.SPADES, Rank.KING)
        assert str(card) == "KS"
        
        card2 = Card(Suit.HEARTS, Rank.TWO)
        assert str(card2) == "2H"
        
        card3 = Card(Suit.DIAMONDS, Rank.ACE)
        assert str(card3) == "AD"
    
    def test_card_repr(self):
        """测试Card的详细表示。"""
        card = Card(Suit.DIAMONDS, Rank.QUEEN)
        assert repr(card) == "Card(QUEEN, DIAMONDS)"
    
    def test_card_equality(self):
        """测试Card的相等性比较。"""
        card1 = Card(Suit.CLUBS, Rank.JACK)
        card2 = Card(Suit.CLUBS, Rank.JACK)
        card3 = Card(Suit.HEARTS, Rank.JACK)
        card4 = Card(Suit.CLUBS, Rank.QUEEN)
        
        assert card1 == card2
        assert card1 != card3  # 不同花色
        assert card1 != card4  # 不同点数
        assert card1 != "not a card"  # 不同类型
    
    def test_card_comparison(self):
        """测试Card的大小比较。"""
        two = Card(Suit.HEARTS, Rank.TWO)
        three = Card(Suit.SPADES, Rank.THREE)
        ace = Card(Suit.CLUBS, Rank.ACE)
        
        assert two < three
        assert three < ace
        assert not ace < two
    
    def test_card_hash(self):
        """测试Card可以用作字典键和集合元素。"""
        card1 = Card(Suit.HEARTS, Rank.ACE)
        card2 = Card(Suit.HEARTS, Rank.ACE)
        card3 = Card(Suit.SPADES, Rank.ACE)
        
        # 相同的牌应该有相同的哈希值
        assert hash(card1) == hash(card2)
        
        # 可以用作字典键
        card_dict = {card1: "red ace", card3: "black ace"}
        assert len(card_dict) == 2
        
        # 可以用作集合元素
        card_set = {card1, card2, card3}
        assert len(card_set) == 2  # card1和card2是同一张牌
    
    def test_card_immutable(self):
        """测试Card是不可变的。"""
        card = Card(Suit.HEARTS, Rank.ACE)
        with pytest.raises(AttributeError):
            card.suit = Suit.SPADES  # 应该无法修改


class TestDeck:
    """测试Deck类的功能。"""
    
    def test_deck_creation(self):
        """测试Deck的创建。"""
        deck = Deck()
        assert len(deck) == 52
        assert deck.cards_remaining() == 52
        assert not deck.is_empty()
    
    def test_deck_with_custom_rng(self):
        """测试使用自定义随机数生成器的Deck。"""
        rng = random.Random(42)
        deck = Deck(rng=rng)
        assert len(deck) == 52
    
    def test_deck_contains_all_cards(self):
        """测试Deck包含所有52张牌且无重复。"""
        deck = Deck()
        dealt_cards = deck.deal_cards(52)
        
        # 检查数量
        assert len(dealt_cards) == 52
        
        # 检查无重复
        assert len(set(dealt_cards)) == 52
        
        # 检查包含所有花色和点数的组合
        expected_cards = {Card(suit, rank) for suit in Suit for rank in Rank}
        actual_cards = set(dealt_cards)
        assert actual_cards == expected_cards
    
    def test_deal_single_card(self):
        """测试发单张牌。"""
        deck = Deck()
        initial_count = len(deck)
        
        card = deck.deal_card()
        assert isinstance(card, Card)
        assert len(deck) == initial_count - 1
        assert deck.cards_remaining() == initial_count - 1
    
    def test_deal_multiple_cards(self):
        """测试发多张牌。"""
        deck = Deck()
        cards = deck.deal_cards(5)
        
        assert len(cards) == 5
        assert len(deck) == 47
        assert all(isinstance(card, Card) for card in cards)
        
        # 检查发出的牌不重复
        assert len(set(cards)) == 5
    
    def test_deal_from_empty_deck(self):
        """测试从空牌堆发牌应该抛出异常。"""
        deck = Deck()
        deck.deal_cards(52)  # 发完所有牌
        
        assert deck.is_empty()
        
        with pytest.raises(IndexError, match="Cannot deal from empty deck"):
            deck.deal_card()
    
    def test_deal_too_many_cards(self):
        """测试发牌数量超过剩余牌数应该抛出异常。"""
        deck = Deck()
        
        with pytest.raises(ValueError, match="Cannot deal 53 cards, only 52 remaining"):
            deck.deal_cards(53)
    
    def test_deal_negative_cards(self):
        """测试发负数张牌应该抛出异常。"""
        deck = Deck()
        
        with pytest.raises(ValueError, match="Count must be non-negative"):
            deck.deal_cards(-1)
    
    def test_shuffle(self):
        """测试洗牌功能。"""
        # 使用固定种子确保测试可重现
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        
        deck1 = Deck(rng=rng1)
        deck2 = Deck(rng=rng2)
        
        # 洗牌前两个牌堆应该相同
        cards1_before = deck1.deal_cards(52)
        cards2_before = deck2.deal_cards(52)
        assert cards1_before == cards2_before
        
        # 重置并洗牌
        deck1.reset()
        deck2.reset()
        deck1.shuffle()
        deck2.shuffle()
        
        # 洗牌后使用相同种子的两个牌堆应该相同
        cards1_after = deck1.deal_cards(52)
        cards2_after = deck2.deal_cards(52)
        assert cards1_after == cards2_after
    
    def test_peek_top(self):
        """测试查看顶部牌功能。"""
        deck = Deck()
        
        # 查看顶部牌不应该改变牌堆大小
        top_card = deck.peek_top()
        assert isinstance(top_card, Card)
        assert len(deck) == 52
        
        # 发出的牌应该与查看的顶部牌相同
        dealt_card = deck.deal_card()
        assert dealt_card == top_card
        assert len(deck) == 51
    
    def test_peek_empty_deck(self):
        """测试查看空牌堆的顶部牌。"""
        deck = Deck()
        deck.deal_cards(52)  # 发完所有牌
        
        assert deck.peek_top() is None
    
    def test_reset(self):
        """测试重置牌堆功能。"""
        deck = Deck()
        
        # 发一些牌
        deck.deal_cards(10)
        assert len(deck) == 42
        
        # 重置
        deck.reset()
        assert len(deck) == 52
        assert not deck.is_empty()
    
    def test_deck_string_representation(self):
        """测试Deck的字符串表示。"""
        deck = Deck()
        assert str(deck) == "Deck(52 cards)"
        
        deck.deal_cards(10)
        assert str(deck) == "Deck(42 cards)"
    
    def test_deck_repr(self):
        """测试Deck的详细表示。"""
        deck = Deck()
        assert repr(deck) == "Deck(cards_remaining=52)"
        
        deck.deal_cards(5)
        assert repr(deck) == "Deck(cards_remaining=47)"


class TestCardDeckIntegration:
    """测试Card和Deck的集成功能。"""
    
    def test_deterministic_shuffle(self):
        """测试使用固定种子的确定性洗牌。"""
        # 使用相同种子的两个牌堆洗牌后应该产生相同的顺序
        deck1 = Deck(rng=random.Random(123))
        deck2 = Deck(rng=random.Random(123))
        
        deck1.shuffle()
        deck2.shuffle()
        
        for _ in range(52):
            card1 = deck1.deal_card()
            card2 = deck2.deal_card()
            assert card1 == card2
    
    def test_card_uniqueness_in_deck(self):
        """测试牌堆中每张牌的唯一性。"""
        deck = Deck()
        all_cards = deck.deal_cards(52)
        
        # 检查每张牌只出现一次
        for i, card1 in enumerate(all_cards):
            for j, card2 in enumerate(all_cards):
                if i != j:
                    assert card1 != card2, f"Duplicate card found: {card1}"
    
    def test_deal_zero_cards(self):
        """测试发0张牌。"""
        deck = Deck()
        cards = deck.deal_cards(0)
        
        assert cards == []
        assert len(deck) == 52  # 牌堆大小不变 