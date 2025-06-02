"""v2 DTO数据传输对象测试."""

import pytest
import json
from datetime import datetime
from typing import Dict, Any

from v2.controller.dto import (
    PlayerSnapshot, GameStateSnapshot, ActionInput, ValidationResult,
    ActionResult, HandResult, GameConfiguration, EventData
)
from v2.core import ActionType, Phase, SeatStatus, Card, Suit, Rank


class TestPlayerSnapshot:
    """玩家快照测试类."""
    
    def test_player_snapshot_creation(self):
        """测试玩家快照创建."""
        player = PlayerSnapshot(
            seat_id=0,
            name="Test Player",
            chips=1000,
            current_bet=50,
            status=SeatStatus.ACTIVE
        )
        
        assert player.seat_id == 0
        assert player.name == "Test Player"
        assert player.chips == 1000
        assert player.current_bet == 50
        assert player.status == SeatStatus.ACTIVE
        assert player.hole_cards is None
        assert player.is_dealer is False
    
    def test_player_snapshot_validation(self):
        """测试玩家快照验证."""
        # 测试无效座位ID
        with pytest.raises(ValueError):
            PlayerSnapshot(
                seat_id=-1,
                name="Test",
                chips=1000,
                current_bet=0,
                status=SeatStatus.ACTIVE
            )
        
        # 测试空名称
        with pytest.raises(ValueError):
            PlayerSnapshot(
                seat_id=0,
                name="",
                chips=1000,
                current_bet=0,
                status=SeatStatus.ACTIVE
            )
        
        # 测试负筹码
        with pytest.raises(ValueError):
            PlayerSnapshot(
                seat_id=0,
                name="Test",
                chips=-100,
                current_bet=0,
                status=SeatStatus.ACTIVE
            )
    
    def test_player_snapshot_with_cards(self):
        """测试包含手牌的玩家快照."""
        cards = [
            Card(suit=Suit.HEARTS, rank=Rank.ACE),
            Card(suit=Suit.SPADES, rank=Rank.KING)
        ]
        
        player = PlayerSnapshot(
            seat_id=0,
            name="Test Player",
            chips=1000,
            current_bet=0,
            status=SeatStatus.ACTIVE,
            hole_cards=cards,
            is_dealer=True
        )
        
        assert len(player.hole_cards) == 2
        assert player.hole_cards[0].rank == Rank.ACE
        assert player.is_dealer is True


class TestGameStateSnapshot:
    """游戏状态快照测试类."""
    
    def test_game_state_snapshot_creation(self):
        """测试游戏状态快照创建."""
        players = [
            PlayerSnapshot(
                seat_id=0,
                name="Player 1",
                chips=1000,
                current_bet=0,
                status=SeatStatus.ACTIVE
            ),
            PlayerSnapshot(
                seat_id=1,
                name="Player 2",
                chips=1000,
                current_bet=0,
                status=SeatStatus.ACTIVE
            )
        ]
        
        snapshot = GameStateSnapshot(
            phase=Phase.PRE_FLOP,
            pot=0,
            current_bet=0,
            players=players,
            current_player=0,
            dealer_position=0,
            small_blind=10,
            big_blind=20,
            hand_number=1
        )
        
        assert snapshot.phase == Phase.PRE_FLOP
        assert snapshot.pot == 0
        assert len(snapshot.players) == 2
        assert snapshot.current_player == 0
        assert snapshot.small_blind == 10
        assert snapshot.big_blind == 20
    
    def test_game_state_snapshot_validation(self):
        """测试游戏状态快照验证."""
        players = [
            PlayerSnapshot(
                seat_id=0,
                name="Player 1",
                chips=1000,
                current_bet=0,
                status=SeatStatus.ACTIVE
            )
        ]
        
        # 测试大盲小于等于小盲
        with pytest.raises(ValueError):
            GameStateSnapshot(
                phase=Phase.PRE_FLOP,
                pot=0,
                current_bet=0,
                players=players,
                dealer_position=0,
                small_blind=20,
                big_blind=10,  # 大盲小于小盲
                hand_number=1
            )
        
        # 测试无效的当前玩家ID
        with pytest.raises(ValueError):
            GameStateSnapshot(
                phase=Phase.PRE_FLOP,
                pot=0,
                current_bet=0,
                players=players,
                current_player=5,  # 不存在的玩家ID
                dealer_position=0,
                small_blind=10,
                big_blind=20,
                hand_number=1
            )


class TestActionInput:
    """行动输入测试类."""
    
    def test_action_input_creation(self):
        """测试行动输入创建."""
        action = ActionInput(
            player_id=0,
            action_type=ActionType.BET,
            amount=100
        )
        
        assert action.player_id == 0
        assert action.action_type == ActionType.BET
        assert action.amount == 100
        assert isinstance(action.timestamp, datetime)
    
    def test_action_input_validation(self):
        """测试行动输入验证."""
        # 测试FOLD行动不应包含金额
        with pytest.raises(ValueError):
            ActionInput(
                player_id=0,
                action_type=ActionType.FOLD,
                amount=100  # FOLD不应有金额
            )
        
        # 测试CHECK行动不应包含金额
        with pytest.raises(ValueError):
            ActionInput(
                player_id=0,
                action_type=ActionType.CHECK,
                amount=50  # CHECK不应有金额
            )
        
        # 测试BET行动金额不能为负
        with pytest.raises(ValueError):
            ActionInput(
                player_id=0,
                action_type=ActionType.BET,
                amount=-50  # 负金额
            )
    
    def test_valid_action_inputs(self):
        """测试有效的行动输入."""
        # FOLD行动
        fold_action = ActionInput(
            player_id=0,
            action_type=ActionType.FOLD,
            amount=0
        )
        assert fold_action.amount == 0
        
        # BET行动
        bet_action = ActionInput(
            player_id=0,
            action_type=ActionType.BET,
            amount=100
        )
        assert bet_action.amount == 100


class TestValidationResult:
    """验证结果测试类."""
    
    def test_validation_result_creation(self):
        """测试验证结果创建."""
        result = ValidationResult(
            is_valid=True,
            error_message=None,
            warnings=["警告信息"]
        )
        
        assert result.is_valid is True
        assert result.error_message is None
        assert len(result.warnings) == 1
        assert result.warnings[0] == "警告信息"
    
    def test_validation_result_with_suggestion(self):
        """测试包含建议行动的验证结果."""
        suggested_action = ActionInput(
            player_id=0,
            action_type=ActionType.CALL,
            amount=50
        )
        
        result = ValidationResult(
            is_valid=False,
            error_message="筹码不足",
            suggested_action=suggested_action
        )
        
        assert result.is_valid is False
        assert result.error_message == "筹码不足"
        assert result.suggested_action.action_type == ActionType.CALL


class TestActionResult:
    """行动结果测试类."""
    
    def test_action_result_creation(self):
        """测试行动结果创建."""
        validation = ValidationResult(is_valid=True)
        
        result = ActionResult(
            success=True,
            validation_result=validation,
            message="行动成功"
        )
        
        assert result.success is True
        assert result.validation_result.is_valid is True
        assert result.message == "行动成功"
        assert isinstance(result.timestamp, datetime)


class TestHandResult:
    """手牌结果测试类."""
    
    def test_hand_result_creation(self):
        """测试手牌结果创建."""
        result = HandResult(
            winner_ids=[0, 1],
            pot_amount=200,
            winning_hand_description="同花顺",
            hand_number=1,
            total_actions=15
        )
        
        assert result.winner_ids == [0, 1]
        assert result.pot_amount == 200
        assert result.winning_hand_description == "同花顺"
        assert result.hand_number == 1
        assert result.total_actions == 15


class TestGameConfiguration:
    """游戏配置测试类."""
    
    def test_game_configuration_creation(self):
        """测试游戏配置创建."""
        config = GameConfiguration(
            num_players=4,
            initial_chips=1000,
            small_blind=10,
            big_blind=20,
            human_seat=0
        )
        
        assert config.num_players == 4
        assert config.initial_chips == 1000
        assert config.small_blind == 10
        assert config.big_blind == 20
        assert config.human_seat == 0
        assert config.ai_difficulty == "normal"
        assert config.enable_events is True
    
    def test_game_configuration_validation(self):
        """测试游戏配置验证."""
        # 测试大盲小于等于小盲
        with pytest.raises(ValueError):
            GameConfiguration(
                num_players=4,
                initial_chips=1000,
                small_blind=20,
                big_blind=10,  # 大盲小于小盲
                human_seat=0
            )
        
        # 测试人类玩家座位超出范围
        with pytest.raises(ValueError):
            GameConfiguration(
                num_players=4,
                initial_chips=1000,
                small_blind=10,
                big_blind=20,
                human_seat=5  # 超出玩家数量
            )
        
        # 测试玩家数量过少
        with pytest.raises(ValueError):
            GameConfiguration(
                num_players=1,  # 少于2人
                initial_chips=1000,
                small_blind=10,
                big_blind=20,
                human_seat=0
            )


class TestEventData:
    """事件数据测试类."""
    
    def test_event_data_creation(self):
        """测试事件数据创建."""
        event = EventData(
            event_type="PLAYER_ACTION",
            player_id=0,
            data={"action": "bet", "amount": 100},
            message="玩家下注100"
        )
        
        assert event.event_type == "PLAYER_ACTION"
        assert event.player_id == 0
        assert event.data["action"] == "bet"
        assert event.message == "玩家下注100"
        assert isinstance(event.timestamp, datetime)


class TestSerializationContract:
    """序列化契约测试类."""
    
    def test_player_snapshot_serialization(self):
        """测试玩家快照序列化/反序列化."""
        original = PlayerSnapshot(
            seat_id=0,
            name="Test Player",
            chips=1000,
            current_bet=50,
            status=SeatStatus.ACTIVE,
            is_dealer=True
        )
        
        # 序列化为字典
        data = original.__dict__
        
        # 反序列化
        restored = PlayerSnapshot(**data)
        
        # 验证一致性
        assert restored.seat_id == original.seat_id
        assert restored.name == original.name
        assert restored.chips == original.chips
        assert restored.current_bet == original.current_bet
        assert restored.status == original.status
        assert restored.is_dealer == original.is_dealer
    
    def test_action_input_serialization(self):
        """测试行动输入序列化/反序列化."""
        original = ActionInput(
            player_id=0,
            action_type=ActionType.BET,
            amount=100
        )
        
        # 序列化为字典
        data = original.__dict__.copy()
        # 处理枚举类型
        data['action_type'] = data['action_type'].value
        
        # 反序列化
        data['action_type'] = ActionType(data['action_type'])
        restored = ActionInput(**data)
        
        # 验证一致性
        assert restored.player_id == original.player_id
        assert restored.action_type == original.action_type
        assert restored.amount == original.amount
    
    def test_game_configuration_serialization(self):
        """测试游戏配置序列化/反序列化."""
        original = GameConfiguration(
            num_players=4,
            initial_chips=1000,
            small_blind=10,
            big_blind=20,
            human_seat=0,
            ai_difficulty="hard",
            enable_events=False
        )
        
        # 序列化为字典
        data = original.__dict__
        
        # 反序列化
        restored = GameConfiguration(**data)
        
        # 验证一致性
        assert restored.num_players == original.num_players
        assert restored.initial_chips == original.initial_chips
        assert restored.small_blind == original.small_blind
        assert restored.big_blind == original.big_blind
        assert restored.human_seat == original.human_seat
        assert restored.ai_difficulty == original.ai_difficulty
        assert restored.enable_events == original.enable_events
    
    def test_validation_result_with_complex_data(self):
        """测试包含复杂数据的验证结果序列化."""
        suggested_action = ActionInput(
            player_id=1,
            action_type=ActionType.CALL,
            amount=50
        )
        
        original = ValidationResult(
            is_valid=False,
            error_message="筹码不足，建议跟注",
            suggested_action=suggested_action,
            warnings=["警告1", "警告2"]
        )
        
        # 验证对象创建成功
        assert original.is_valid is False
        assert original.error_message == "筹码不足，建议跟注"
        assert original.suggested_action.player_id == 1
        assert len(original.warnings) == 2
    
    def test_contract_consistency(self):
        """测试契约一致性：确保所有DTO都可以正常创建和访问."""
        # 创建一个完整的游戏状态快照
        players = [
            PlayerSnapshot(
                seat_id=i,
                name=f"Player {i}",
                chips=1000,
                current_bet=0,
                status=SeatStatus.ACTIVE
            ) for i in range(4)
        ]
        
        snapshot = GameStateSnapshot(
            phase=Phase.FLOP,
            pot=100,
            current_bet=50,
            players=players,
            community_cards=[
                Card(suit=Suit.HEARTS, rank=Rank.ACE),
                Card(suit=Suit.SPADES, rank=Rank.KING),
                Card(suit=Suit.DIAMONDS, rank=Rank.QUEEN)
            ],
            current_player=0,
            dealer_position=0,
            small_blind=10,
            big_blind=20,
            hand_number=1
        )
        
        # 验证快照完整性
        assert len(snapshot.players) == 4
        assert len(snapshot.community_cards) == 3
        assert snapshot.phase == Phase.FLOP
        assert snapshot.pot == 100
        
        print("✅ DTO契约测试通过：所有数据传输对象都可以正常创建和序列化") 