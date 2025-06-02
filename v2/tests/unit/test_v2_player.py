"""
v2 Player类的单元测试。

测试玩家状态管理的核心功能，包括下注、弃牌、状态变更等。
"""

import pytest
from v2.core.player import Player
from v2.core.cards import Card
from v2.core.enums import SeatStatus, ActionType, Suit, Rank


class TestPlayerCreation:
    """测试Player对象的创建和初始化。"""
    
    def test_create_player_with_valid_data(self):
        """测试使用有效数据创建玩家。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        
        assert player.seat_id == 1
        assert player.name == "Alice"
        assert player.chips == 1000
        assert player.current_bet == 0
        assert player.status == SeatStatus.ACTIVE
        assert player.hole_cards == []
        assert not player.is_dealer
        assert not player.is_small_blind
        assert not player.is_big_blind
        assert player.last_action_type is None
        assert not player.is_human
    
    def test_create_player_with_negative_seat_id(self):
        """测试使用负数座位号创建玩家应该抛出异常。"""
        with pytest.raises(ValueError, match="座位号不能为负数"):
            Player(seat_id=-1, name="Alice", chips=1000)
    
    def test_create_player_with_negative_chips(self):
        """测试使用负数筹码创建玩家应该抛出异常。"""
        with pytest.raises(ValueError, match="筹码数量不能为负数"):
            Player(seat_id=1, name="Alice", chips=-100)
    
    def test_create_player_with_negative_current_bet(self):
        """测试使用负数当前下注创建玩家应该抛出异常。"""
        with pytest.raises(ValueError, match="当前下注不能为负数"):
            Player(seat_id=1, name="Alice", chips=1000, current_bet=-50)
    
    def test_create_player_with_too_many_hole_cards(self):
        """测试使用超过2张手牌创建玩家应该抛出异常。"""
        cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN)
        ]
        with pytest.raises(ValueError, match="手牌不能超过2张"):
            Player(seat_id=1, name="Alice", chips=1000, hole_cards=cards)


class TestPlayerEquality:
    """测试Player对象的相等性和哈希。"""
    
    def test_players_with_same_seat_id_are_equal(self):
        """测试相同座位号的玩家被认为是相等的。"""
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=1, name="Bob", chips=500)
        
        assert player1 == player2
        assert hash(player1) == hash(player2)
    
    def test_players_with_different_seat_id_are_not_equal(self):
        """测试不同座位号的玩家不相等。"""
        player1 = Player(seat_id=1, name="Alice", chips=1000)
        player2 = Player(seat_id=2, name="Alice", chips=1000)
        
        assert player1 != player2
        assert hash(player1) != hash(player2)
    
    def test_player_not_equal_to_non_player(self):
        """测试玩家对象与非玩家对象不相等。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        
        assert player != "not a player"
        assert player != 1
        assert player != None


class TestPlayerStatus:
    """测试玩家状态检查方法。"""
    
    def test_can_act_when_active_with_chips(self):
        """测试活跃状态且有筹码的玩家可以行动。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        assert player.can_act()
    
    def test_cannot_act_when_active_without_chips(self):
        """测试活跃状态但无筹码的玩家不能行动。"""
        player = Player(seat_id=1, name="Alice", chips=0)
        assert not player.can_act()
    
    def test_cannot_act_when_folded(self):
        """测试已弃牌的玩家不能行动。"""
        player = Player(seat_id=1, name="Alice", chips=1000, status=SeatStatus.FOLDED)
        assert not player.can_act()
    
    def test_cannot_act_when_all_in(self):
        """测试已全押的玩家不能行动。"""
        player = Player(seat_id=1, name="Alice", chips=0, status=SeatStatus.ALL_IN)
        assert not player.can_act()
    
    def test_is_all_in_when_status_all_in(self):
        """测试状态为ALL_IN时is_all_in返回True。"""
        player = Player(seat_id=1, name="Alice", chips=0, status=SeatStatus.ALL_IN)
        assert player.is_all_in()
    
    def test_is_all_in_when_no_chips_but_has_bet(self):
        """测试无筹码但有当前下注时is_all_in返回True。"""
        player = Player(seat_id=1, name="Alice", chips=0, current_bet=100)
        assert player.is_all_in()
    
    def test_is_not_all_in_when_has_chips(self):
        """测试有筹码时is_all_in返回False。"""
        player = Player(seat_id=1, name="Alice", chips=500, current_bet=100)
        assert not player.is_all_in()
    
    def test_is_folded(self):
        """测试is_folded方法。"""
        player = Player(seat_id=1, name="Alice", chips=1000, status=SeatStatus.FOLDED)
        assert player.is_folded()
        
        player.status = SeatStatus.ACTIVE
        assert not player.is_folded()
    
    def test_is_out(self):
        """测试is_out方法。"""
        player = Player(seat_id=1, name="Alice", chips=0, status=SeatStatus.OUT)
        assert player.is_out()
        
        player.status = SeatStatus.ACTIVE
        assert not player.is_out()
    
    def test_is_active_property(self):
        """测试is_active属性（兼容性方法）。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        assert player.is_active
        
        player.status = SeatStatus.FOLDED
        assert not player.is_active


class TestPlayerBetting:
    """测试玩家下注相关功能。"""
    
    def test_bet_normal_amount(self):
        """测试正常下注。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        
        actual_amount = player.bet(200)
        
        assert actual_amount == 200
        assert player.chips == 800
        assert player.current_bet == 200
        assert player.status == SeatStatus.ACTIVE
    
    def test_bet_all_chips_sets_all_in_status(self):
        """测试下注全部筹码时自动设置为ALL_IN状态。"""
        player = Player(seat_id=1, name="Alice", chips=500)
        
        actual_amount = player.bet(500)
        
        assert actual_amount == 500
        assert player.chips == 0
        assert player.current_bet == 500
        assert player.status == SeatStatus.ALL_IN
    
    def test_bet_more_than_chips_results_in_all_in(self):
        """测试下注超过筹码数量时全押。"""
        player = Player(seat_id=1, name="Alice", chips=300)
        
        actual_amount = player.bet(500)
        
        assert actual_amount == 300
        assert player.chips == 0
        assert player.current_bet == 300
        assert player.status == SeatStatus.ALL_IN
    
    def test_bet_multiple_times_accumulates(self):
        """测试多次下注累积。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        
        player.bet(200)
        player.bet(150)
        
        assert player.chips == 650
        assert player.current_bet == 350
        assert player.status == SeatStatus.ACTIVE
    
    def test_bet_negative_amount_raises_error(self):
        """测试下注负数金额抛出异常。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        
        with pytest.raises(ValueError, match="下注金额不能为负数"):
            player.bet(-100)
    
    def test_bet_when_cannot_act_raises_error(self):
        """测试无法行动时下注抛出异常。"""
        player = Player(seat_id=1, name="Alice", chips=1000, status=SeatStatus.FOLDED)
        
        with pytest.raises(ValueError, match="玩家1无法行动"):
            player.bet(100)
    
    def test_can_bet_with_sufficient_chips(self):
        """测试有足够筹码时can_bet返回True。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        assert player.can_bet(500)
        assert player.can_bet(1000)
    
    def test_cannot_bet_with_insufficient_chips(self):
        """测试筹码不足时can_bet返回False。"""
        player = Player(seat_id=1, name="Alice", chips=500)
        assert not player.can_bet(600)
    
    def test_cannot_bet_when_cannot_act(self):
        """测试无法行动时can_bet返回False。"""
        player = Player(seat_id=1, name="Alice", chips=1000, status=SeatStatus.FOLDED)
        assert not player.can_bet(100)
    
    def test_can_call_with_sufficient_chips(self):
        """测试有足够筹码时can_call返回True。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        assert player.can_call(500)
    
    def test_can_call_with_some_chips_even_if_insufficient(self):
        """测试有部分筹码时即使不足也可以跟注（全押）。"""
        player = Player(seat_id=1, name="Alice", chips=300)
        assert player.can_call(500)
    
    def test_cannot_call_with_no_chips(self):
        """测试无筹码时不能跟注。"""
        player = Player(seat_id=1, name="Alice", chips=0)
        assert not player.can_call(100)
    
    def test_cannot_call_when_cannot_act(self):
        """测试无法行动时不能跟注。"""
        player = Player(seat_id=1, name="Alice", chips=1000, status=SeatStatus.FOLDED)
        assert not player.can_call(100)


class TestPlayerFolding:
    """测试玩家弃牌功能。"""
    
    def test_fold_when_can_act(self):
        """测试可以行动时弃牌。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        
        player.fold()
        
        assert player.status == SeatStatus.FOLDED
    
    def test_fold_when_all_in(self):
        """测试全押状态时可以弃牌。"""
        player = Player(seat_id=1, name="Alice", chips=0, status=SeatStatus.ALL_IN)
        
        player.fold()
        
        assert player.status == SeatStatus.FOLDED
    
    def test_fold_when_cannot_act_raises_error(self):
        """测试无法行动时弃牌抛出异常。"""
        player = Player(seat_id=1, name="Alice", chips=1000, status=SeatStatus.OUT)
        
        with pytest.raises(ValueError, match="玩家1无法弃牌"):
            player.fold()


class TestPlayerCards:
    """测试玩家手牌管理。"""
    
    def test_set_hole_cards(self):
        """测试设置手牌。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        cards = [Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.KING)]
        
        player.set_hole_cards(cards)
        
        assert len(player.hole_cards) == 2
        assert player.hole_cards[0] == Card(Suit.HEARTS, Rank.ACE)
        assert player.hole_cards[1] == Card(Suit.SPADES, Rank.KING)
    
    def test_set_hole_cards_makes_copy(self):
        """测试设置手牌时创建副本。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        cards = [Card(Suit.HEARTS, Rank.ACE)]
        
        player.set_hole_cards(cards)
        cards.append(Card(Suit.SPADES, Rank.KING))
        
        assert len(player.hole_cards) == 1
    
    def test_set_too_many_hole_cards_raises_error(self):
        """测试设置超过2张手牌抛出异常。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN)
        ]
        
        with pytest.raises(ValueError, match="手牌不能超过2张"):
            player.set_hole_cards(cards)
    
    def test_get_hole_cards_str_visible(self):
        """测试获取可见手牌字符串。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        cards = [Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.KING)]
        player.set_hole_cards(cards)
        
        cards_str = player.get_hole_cards_str()
        
        assert cards_str == "AH KS"
    
    def test_get_hole_cards_str_hidden(self):
        """测试获取隐藏手牌字符串。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        cards = [Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.KING)]
        player.set_hole_cards(cards)
        
        cards_str = player.get_hole_cards_str(hidden=True)
        
        assert cards_str == "XX XX"
    
    def test_get_hole_cards_str_one_card_hidden(self):
        """测试一张牌时的隐藏字符串。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        cards = [Card(Suit.HEARTS, Rank.ACE)]
        player.set_hole_cards(cards)
        
        cards_str = player.get_hole_cards_str(hidden=True)
        
        assert cards_str == "XX"
    
    def test_get_hand_cards_compatibility(self):
        """测试兼容性方法get_hand_cards。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        cards = [Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.KING)]
        player.set_hole_cards(cards)
        
        hand_cards = player.get_hand_cards()
        
        assert hand_cards == cards
        assert hand_cards is not player.hole_cards  # 应该是副本


class TestPlayerReset:
    """测试玩家重置功能。"""
    
    def test_reset_for_new_hand(self):
        """测试为新手牌重置玩家状态。"""
        player = Player(seat_id=1, name="Alice", chips=1000, current_bet=200)
        player.set_hole_cards([Card(Suit.HEARTS, Rank.ACE)])
        player.last_action_type = ActionType.BET
        player.is_dealer = True
        
        player.reset_for_new_hand()
        
        assert player.hole_cards == []
        assert player.current_bet == 0
        assert player.last_action_type is None
        assert player.status == SeatStatus.ACTIVE
        assert player.is_dealer  # 位置标记不应该被重置
    
    def test_reset_for_new_hand_out_player_stays_out(self):
        """测试已出局玩家重置后仍然出局。"""
        player = Player(seat_id=1, name="Alice", chips=0, status=SeatStatus.OUT)
        
        player.reset_for_new_hand()
        
        assert player.status == SeatStatus.OUT
    
    def test_reset_for_new_hand_no_chips_becomes_out(self):
        """测试无筹码玩家重置后变为出局。"""
        player = Player(seat_id=1, name="Alice", chips=0, status=SeatStatus.FOLDED)
        
        player.reset_for_new_hand()
        
        assert player.status == SeatStatus.OUT
    
    def test_reset_current_bet(self):
        """测试重置当前下注。"""
        player = Player(seat_id=1, name="Alice", chips=1000, current_bet=200)
        player.last_action_type = ActionType.BET
        
        player.reset_current_bet()
        
        assert player.current_bet == 0
        assert player.last_action_type is None


class TestPlayerChips:
    """测试玩家筹码管理。"""
    
    def test_get_effective_stack(self):
        """测试获取有效筹码数。"""
        player = Player(seat_id=1, name="Alice", chips=800, current_bet=200)
        
        assert player.get_effective_stack() == 1000
    
    def test_add_chips(self):
        """测试增加筹码。"""
        player = Player(seat_id=1, name="Alice", chips=500)
        
        player.add_chips(300)
        
        assert player.chips == 800
    
    def test_add_chips_reactivates_out_player(self):
        """测试增加筹码重新激活已出局玩家。"""
        player = Player(seat_id=1, name="Alice", chips=0, status=SeatStatus.OUT)
        
        player.add_chips(500)
        
        assert player.chips == 500
        assert player.status == SeatStatus.ACTIVE
    
    def test_add_negative_chips_raises_error(self):
        """测试增加负数筹码抛出异常。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        
        with pytest.raises(ValueError, match="增加的筹码数量不能为负数"):
            player.add_chips(-100)


class TestPlayerStringRepresentation:
    """测试玩家字符串表示。"""
    
    def test_str_basic(self):
        """测试基本字符串表示。"""
        player = Player(seat_id=1, name="Alice", chips=1000, current_bet=200)
        player.set_hole_cards([Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.KING)])
        
        result = str(player)
        
        assert "Alice" in result
        assert "1000筹码" in result
        assert "当前下注200" in result
        assert "AH KS" in result
        assert "ACTIVE" in result
    
    def test_str_with_positions(self):
        """测试包含位置信息的字符串表示。"""
        player = Player(seat_id=1, name="Alice", chips=1000)
        player.is_dealer = True
        player.is_small_blind = True
        
        result = str(player)
        
        assert "(庄家, 小盲)" in result
    
    def test_repr(self):
        """测试调试字符串表示。"""
        player = Player(seat_id=1, name="Alice", chips=1000, status=SeatStatus.FOLDED)
        
        result = repr(player)
        
        assert result == "Player(seat=1, name='Alice', chips=1000, status=FOLDED)" 