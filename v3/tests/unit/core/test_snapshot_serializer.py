"""
快照序列化器单元测试

测试快照序列化器的序列化和反序列化功能。
包含反作弊验证，确保测试使用真实的核心模块。
"""

import pytest
import json
import time
import tempfile
import os

from v3.core.snapshot.serializer import (
    SnapshotSerializer, SerializationError, DeserializationError
)
from v3.core.snapshot.types import (
    GameStateSnapshot, PlayerSnapshot, PotSnapshot, SnapshotMetadata,
    SnapshotVersion
)
from v3.core.state_machine.types import GamePhase
from v3.core.deck.card import Card
from v3.core.deck.types import Suit, Rank
from v3.core.chips.chip_transaction import ChipTransaction, TransactionType
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestSnapshotSerializer:
    """测试快照序列化器"""
    
    def test_serializer_creation(self):
        """测试序列化器的创建"""
        serializer = SnapshotSerializer()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(serializer, "SnapshotSerializer")
    
    def test_serialize_basic_snapshot(self):
        """测试基本快照的序列化"""
        # 创建测试快照
        timestamp = time.time()
        metadata = SnapshotMetadata(
            snapshot_id="test_snapshot",
            version=SnapshotVersion.CURRENT,
            created_at=timestamp,
            game_duration=120.0,
            hand_number=5,
            description="测试快照"
        )
        
        player1 = PlayerSnapshot(
            player_id="player1",
            name="Alice",
            chips=1000,
            hole_cards=(),
            position=0,
            is_active=True,
            is_all_in=False,
            current_bet=50,
            total_bet_this_hand=100
        )
        
        player2 = PlayerSnapshot(
            player_id="player2",
            name="Bob",
            chips=950,
            hole_cards=(),
            position=1,
            is_active=True,
            is_all_in=False,
            current_bet=50,
            total_bet_this_hand=100
        )
        
        pot = PotSnapshot(
            main_pot=200,
            side_pots=(),
            total_pot=200,
            eligible_players=("player1", "player2")
        )
        
        snapshot = GameStateSnapshot(
            metadata=metadata,
            game_id="test_game",
            phase=GamePhase.TURN,
            players=(player1, player2),
            pot=pot,
            community_cards=(),
            current_bet=50,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=0,
            small_blind_amount=10,
            big_blind_amount=20
        )
        
        # 序列化
        json_str = SnapshotSerializer.serialize(snapshot)
        
        # 验证序列化结果
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        
        # 验证JSON格式有效
        parsed_json = json.loads(json_str)
        assert "metadata" in parsed_json
        assert "game_id" in parsed_json
        assert "phase" in parsed_json
        assert "players" in parsed_json
        assert "pot" in parsed_json
        
        # 验证具体内容
        assert parsed_json["game_id"] == "test_game"
        assert parsed_json["phase"] == "TURN"
        assert len(parsed_json["players"]) == 2
        assert parsed_json["current_bet"] == 50
    
    def test_serialize_snapshot_with_cards(self):
        """测试包含卡牌的快照序列化"""
        # 创建测试卡牌
        card1 = Card(Suit.HEARTS, Rank.ACE)
        card2 = Card(Suit.SPADES, Rank.KING)
        community_card = Card(Suit.DIAMONDS, Rank.QUEEN)
        
        timestamp = time.time()
        metadata = SnapshotMetadata(
            snapshot_id="test_snapshot",
            version=SnapshotVersion.CURRENT,
            created_at=timestamp,
            game_duration=0.0,
            hand_number=1
        )
        
        player1 = PlayerSnapshot(
            player_id="player1",
            name="Alice",
            chips=1000,
            hole_cards=(card1, card2),
            position=0,
            is_active=True,
            is_all_in=False,
            current_bet=0,
            total_bet_this_hand=0
        )
        
        player2 = PlayerSnapshot(
            player_id="player2",
            name="Bob",
            chips=1000,
            hole_cards=(),
            position=1,
            is_active=True,
            is_all_in=False,
            current_bet=0,
            total_bet_this_hand=0
        )
        
        pot = PotSnapshot(
            main_pot=0,
            side_pots=(),
            total_pot=0,
            eligible_players=("player1", "player2")
        )
        
        snapshot = GameStateSnapshot(
            metadata=metadata,
            game_id="test_game",
            phase=GamePhase.FLOP,
            players=(player1, player2),
            pot=pot,
            community_cards=(community_card,),
            current_bet=0,
            dealer_position=0,
            small_blind_position=0,
            big_blind_position=0
        )
        
        # 序列化
        json_str = SnapshotSerializer.serialize(snapshot)
        parsed_json = json.loads(json_str)
        
        # 验证卡牌序列化
        player_data = parsed_json["players"][0]
        assert len(player_data["hole_cards"]) == 2
        assert player_data["hole_cards"][0]["suit"] == "HEARTS"
        assert player_data["hole_cards"][0]["rank"] == "ACE"
        assert player_data["hole_cards"][1]["suit"] == "SPADES"
        assert player_data["hole_cards"][1]["rank"] == "KING"
        
        assert len(parsed_json["community_cards"]) == 1
        assert parsed_json["community_cards"][0]["suit"] == "DIAMONDS"
        assert parsed_json["community_cards"][0]["rank"] == "QUEEN"
    
    def test_deserialize_basic_snapshot(self):
        """测试基本快照的反序列化"""
        # 创建测试JSON数据
        test_json = {
            "metadata": {
                "snapshot_id": "test_snapshot",
                "version": "1.1",
                "created_at": time.time(),
                "game_duration": 120.0,
                "hand_number": 5,
                "description": "测试快照"
            },
            "game_id": "test_game",
            "phase": "TURN",
            "players": [
                {
                    "player_id": "player1",
                    "name": "Alice",
                    "chips": 1000,
                    "hole_cards": [],
                    "position": 0,
                    "is_active": True,
                    "is_all_in": False,
                    "current_bet": 50,
                    "total_bet_this_hand": 100,
                    "last_action": None
                },
                {
                    "player_id": "player2",
                    "name": "Bob",
                    "chips": 950,
                    "hole_cards": [],
                    "position": 1,
                    "is_active": True,
                    "is_all_in": False,
                    "current_bet": 50,
                    "total_bet_this_hand": 100,
                    "last_action": None
                }
            ],
            "pot": {
                "main_pot": 200,
                "side_pots": [],
                "total_pot": 200,
                "eligible_players": ["player1", "player2"]
            },
            "community_cards": [],
            "current_bet": 50,
            "dealer_position": 0,
            "small_blind_position": 0,
            "big_blind_position": 0,
            "active_player_position": 0,
            "small_blind_amount": 10,
            "big_blind_amount": 20,
            "recent_transactions": []
        }
        
        json_str = json.dumps(test_json)
        
        # 反序列化
        snapshot = SnapshotSerializer.deserialize(json_str)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(snapshot, "GameStateSnapshot")
        
        # 验证反序列化结果
        assert snapshot.game_id == "test_game"
        assert snapshot.phase == GamePhase.TURN
        assert len(snapshot.players) == 2
        assert snapshot.players[0].player_id == "player1"
        assert snapshot.players[0].name == "Alice"
        assert snapshot.players[0].chips == 1000
        assert snapshot.players[1].player_id == "player2"
        assert snapshot.players[1].name == "Bob"
        assert snapshot.players[1].chips == 950
        assert snapshot.current_bet == 50
        assert snapshot.pot.total_pot == 200
    
    def test_deserialize_snapshot_with_cards(self):
        """测试包含卡牌的快照反序列化"""
        test_json = {
            "metadata": {
                "snapshot_id": "test_snapshot",
                "version": "1.1",
                "created_at": time.time(),
                "game_duration": 0.0,
                "hand_number": 1,
                "description": None
            },
            "game_id": "test_game",
            "phase": "FLOP",
            "players": [
                {
                    "player_id": "player1",
                    "name": "Alice",
                    "chips": 1000,
                    "hole_cards": [
                        {"suit": "HEARTS", "rank": "ACE"},
                        {"suit": "SPADES", "rank": "KING"}
                    ],
                    "position": 0,
                    "is_active": True,
                    "is_all_in": False,
                    "current_bet": 0,
                    "total_bet_this_hand": 0,
                    "last_action": None
                },
                {
                    "player_id": "player2",
                    "name": "Bob",
                    "chips": 1000,
                    "hole_cards": [],
                    "position": 1,
                    "is_active": True,
                    "is_all_in": False,
                    "current_bet": 0,
                    "total_bet_this_hand": 0,
                    "last_action": None
                }
            ],
            "pot": {
                "main_pot": 0,
                "side_pots": [],
                "total_pot": 0,
                "eligible_players": ["player1", "player2"]
            },
            "community_cards": [
                {"suit": "DIAMONDS", "rank": "QUEEN"}
            ],
            "current_bet": 0,
            "dealer_position": 0,
            "small_blind_position": 0,
            "big_blind_position": 0,
            "active_player_position": None,
            "small_blind_amount": 0,
            "big_blind_amount": 0,
            "recent_transactions": []
        }
        
        json_str = json.dumps(test_json)
        snapshot = SnapshotSerializer.deserialize(json_str)
        
        # 验证卡牌反序列化
        player = snapshot.players[0]
        assert len(player.hole_cards) == 2
        assert player.hole_cards[0].suit == Suit.HEARTS
        assert player.hole_cards[0].rank == Rank.ACE
        assert player.hole_cards[1].suit == Suit.SPADES
        assert player.hole_cards[1].rank == Rank.KING
        
        assert len(snapshot.community_cards) == 1
        assert snapshot.community_cards[0].suit == Suit.DIAMONDS
        assert snapshot.community_cards[0].rank == Rank.QUEEN
    
    def test_serialize_deserialize_roundtrip(self):
        """测试序列化和反序列化的往返转换"""
        # 创建复杂的测试快照
        timestamp = time.time()
        metadata = SnapshotMetadata(
            snapshot_id="roundtrip_test",
            version=SnapshotVersion.CURRENT,
            created_at=timestamp,
            game_duration=300.5,
            hand_number=10,
            description="往返测试"
        )
        
        card1 = Card(Suit.HEARTS, Rank.ACE)
        card2 = Card(Suit.SPADES, Rank.KING)
        community_cards = (
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK),
            Card(Suit.HEARTS, Rank.TEN)
        )
        
        player1 = PlayerSnapshot(
            player_id="player1",
            name="Alice",
            chips=1500,
            hole_cards=(card1, card2),
            position=0,
            is_active=True,
            is_all_in=False,
            current_bet=100,
            total_bet_this_hand=200,
            last_action="raise"
        )
        
        player2 = PlayerSnapshot(
            player_id="player2",
            name="Bob",
            chips=800,
            hole_cards=(),
            position=1,
            is_active=False,
            is_all_in=True,
            current_bet=0,
            total_bet_this_hand=150,
            last_action="fold"
        )
        
        side_pot = {"amount": 50, "eligible_players": ["player1"]}
        pot = PotSnapshot(
            main_pot=300,
            side_pots=(side_pot,),
            total_pot=350,
            eligible_players=("player1", "player2")
        )
        
        transaction = ChipTransaction.create_add_transaction(
            "player1", 100, "测试交易"
        )
        
        original_snapshot = GameStateSnapshot(
            metadata=metadata,
            game_id="roundtrip_game",
            phase=GamePhase.RIVER,
            players=(player1, player2),
            pot=pot,
            community_cards=community_cards,
            current_bet=100,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=0,
            active_player_position=0,
            small_blind_amount=25,
            big_blind_amount=50,
            recent_transactions=(transaction,)
        )
        
        # 序列化
        json_str = SnapshotSerializer.serialize(original_snapshot)
        
        # 反序列化
        restored_snapshot = SnapshotSerializer.deserialize(json_str)
        
        # 验证往返转换的一致性
        assert restored_snapshot.metadata.snapshot_id == original_snapshot.metadata.snapshot_id
        assert restored_snapshot.game_id == original_snapshot.game_id
        assert restored_snapshot.phase == original_snapshot.phase
        assert len(restored_snapshot.players) == len(original_snapshot.players)
        assert restored_snapshot.pot.total_pot == original_snapshot.pot.total_pot
        assert len(restored_snapshot.community_cards) == len(original_snapshot.community_cards)
        assert restored_snapshot.current_bet == original_snapshot.current_bet
        
        # 验证玩家信息
        for i, (orig_player, rest_player) in enumerate(zip(original_snapshot.players, restored_snapshot.players)):
            assert rest_player.player_id == orig_player.player_id
            assert rest_player.name == orig_player.name
            assert rest_player.chips == orig_player.chips
            assert len(rest_player.hole_cards) == len(orig_player.hole_cards)
            assert rest_player.is_active == orig_player.is_active
            assert rest_player.last_action == orig_player.last_action
        
        # 验证交易记录
        assert len(restored_snapshot.recent_transactions) == len(original_snapshot.recent_transactions)
        if restored_snapshot.recent_transactions:
            orig_tx = original_snapshot.recent_transactions[0]
            rest_tx = restored_snapshot.recent_transactions[0]
            assert rest_tx.transaction_id == orig_tx.transaction_id
            assert rest_tx.player_id == orig_tx.player_id
            assert rest_tx.amount == orig_tx.amount
    
    def test_serialize_to_file(self):
        """测试序列化到文件"""
        # 创建测试快照
        snapshot = GameStateSnapshot.create_initial_snapshot(
            game_id="file_test",
            players=(
                PlayerSnapshot(
                    player_id="player1",
                    name="Alice",
                    chips=1000,
                    hole_cards=(),
                    position=0,
                    is_active=True,
                    is_all_in=False,
                    current_bet=0,
                    total_bet_this_hand=0
                ),
                PlayerSnapshot(
                    player_id="player2",
                    name="Bob",
                    chips=1000,
                    hole_cards=(),
                    position=1,
                    is_active=True,
                    is_all_in=False,
                    current_bet=0,
                    total_bet_this_hand=0
                ),
            ),
            small_blind=10,
            big_blind=20
        )
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_path = temp_file.name
        
        try:
            # 序列化到文件
            SnapshotSerializer.serialize_to_file(snapshot, temp_path)
            
            # 验证文件存在且有内容
            assert os.path.exists(temp_path)
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert len(content) > 0
                
                # 验证JSON格式有效
                parsed = json.loads(content)
                assert parsed["game_id"] == "file_test"
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_deserialize_from_file(self):
        """测试从文件反序列化"""
        # 创建测试快照
        snapshot = GameStateSnapshot.create_initial_snapshot(
            game_id="file_test",
            players=(
                PlayerSnapshot(
                    player_id="player1",
                    name="Alice",
                    chips=1000,
                    hole_cards=(),
                    position=0,
                    is_active=True,
                    is_all_in=False,
                    current_bet=0,
                    total_bet_this_hand=0
                ),
                PlayerSnapshot(
                    player_id="player2",
                    name="Bob",
                    chips=1000,
                    hole_cards=(),
                    position=1,
                    is_active=True,
                    is_all_in=False,
                    current_bet=0,
                    total_bet_this_hand=0
                ),
            ),
            small_blind=10,
            big_blind=20
        )
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_path = temp_file.name
        
        try:
            # 先序列化到文件
            SnapshotSerializer.serialize_to_file(snapshot, temp_path)
            
            # 从文件反序列化
            restored_snapshot = SnapshotSerializer.deserialize_from_file(temp_path)
            
            # 验证反序列化结果
            assert restored_snapshot.game_id == snapshot.game_id
            assert restored_snapshot.phase == snapshot.phase
            assert len(restored_snapshot.players) == len(snapshot.players)
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_serialization_error_handling(self):
        """测试序列化错误处理"""
        # 测试无效对象序列化
        with pytest.raises(SerializationError):
            SnapshotSerializer.serialize(None)
    
    def test_deserialization_error_handling(self):
        """测试反序列化错误处理"""
        # 测试无效JSON
        with pytest.raises(DeserializationError):
            SnapshotSerializer.deserialize("invalid json")
        
        # 测试缺少必要字段的JSON
        invalid_json = json.dumps({"game_id": "test"})  # 缺少其他必要字段
        with pytest.raises(DeserializationError):
            SnapshotSerializer.deserialize(invalid_json)
    
    def test_file_error_handling(self):
        """测试文件操作错误处理"""
        snapshot = GameStateSnapshot.create_initial_snapshot(
            game_id="error_test",
            players=(
                PlayerSnapshot(
                    player_id="player1",
                    name="Alice",
                    chips=1000,
                    hole_cards=(),
                    position=0,
                    is_active=True,
                    is_all_in=False,
                    current_bet=0,
                    total_bet_this_hand=0
                ),
                PlayerSnapshot(
                    player_id="player2",
                    name="Bob",
                    chips=1000,
                    hole_cards=(),
                    position=1,
                    is_active=True,
                    is_all_in=False,
                    current_bet=0,
                    total_bet_this_hand=0
                ),
            ),
            small_blind=10,
            big_blind=20
        )
        
        # 测试写入无效路径
        with pytest.raises(SerializationError):
            SnapshotSerializer.serialize_to_file(snapshot, "/invalid/path/file.json")
        
        # 测试读取不存在的文件
        with pytest.raises(DeserializationError):
            SnapshotSerializer.deserialize_from_file("non_existent_file.json") 