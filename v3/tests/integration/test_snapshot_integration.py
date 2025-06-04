"""
快照系统集成测试

测试快照系统与其他核心模块的集成和协作。
包含反作弊验证，确保测试使用真实的核心模块。
"""

import pytest
import time
import tempfile
import os

from v3.core.snapshot.types import (
    GameStateSnapshot, PlayerSnapshot, PotSnapshot, SnapshotMetadata,
    SnapshotVersion
)
from v3.core.snapshot.snapshot_manager import SnapshotManager
from v3.core.snapshot.serializer import SnapshotSerializer
from v3.core.state_machine.types import GamePhase
from v3.core.deck.card import Card
from v3.core.deck.types import Suit, Rank
from v3.core.chips.chip_transaction import ChipTransaction, TransactionType
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestSnapshotIntegration:
    """测试快照系统集成"""
    
    def test_snapshot_manager_with_serializer(self):
        """测试快照管理器与序列化器的集成"""
        manager = SnapshotManager()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(manager, "SnapshotManager")
        
        # 创建测试快照
        snapshot = GameStateSnapshot.create_initial_snapshot(
            game_id="integration_test",
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
        
        # 通过管理器存储快照
        manager._store_snapshot(snapshot)
        
        # 通过管理器获取快照
        restored_snapshot = manager.get_snapshot(snapshot.metadata.snapshot_id)
        assert restored_snapshot is not None
        assert restored_snapshot.game_id == snapshot.game_id
        assert len(restored_snapshot.players) == len(snapshot.players)
        
        # 验证序列化一致性
        json_str = SnapshotSerializer.serialize(restored_snapshot)
        deserialized_snapshot = SnapshotSerializer.deserialize(json_str)
        assert deserialized_snapshot.game_id == snapshot.game_id
    
    def test_snapshot_with_complex_game_state(self):
        """测试复杂游戏状态的快照"""
        # 创建复杂的游戏状态
        card1 = Card(Suit.HEARTS, Rank.ACE)
        card2 = Card(Suit.SPADES, Rank.KING)
        card3 = Card(Suit.DIAMONDS, Rank.QUEEN)
        card4 = Card(Suit.CLUBS, Rank.JACK)
        
        community_cards = (
            Card(Suit.HEARTS, Rank.TEN),
            Card(Suit.SPADES, Rank.NINE),
            Card(Suit.DIAMONDS, Rank.EIGHT)
        )
        
        transaction = ChipTransaction(
            transaction_id="tx_001",
            player_id="player1",
            transaction_type=TransactionType.DEDUCT,
            amount=100,
            timestamp=time.time(),
            description="下注"
        )
        
        timestamp = time.time()
        metadata = SnapshotMetadata(
            snapshot_id="complex_test",
            version=SnapshotVersion.CURRENT,
            created_at=timestamp,
            game_duration=180.5,
            hand_number=15,
            description="复杂状态测试"
        )
        
        player1 = PlayerSnapshot(
            player_id="player1",
            name="Alice",
            chips=900,
            hole_cards=(card1, card2),
            position=0,
            is_active=True,
            is_all_in=False,
            current_bet=100,
            total_bet_this_hand=150,
            last_action="BET"
        )
        
        player2 = PlayerSnapshot(
            player_id="player2",
            name="Bob",
            chips=850,
            hole_cards=(card3, card4),
            position=1,
            is_active=True,
            is_all_in=False,
            current_bet=100,
            total_bet_this_hand=150,
            last_action="CALL"
        )
        
        pot = PotSnapshot(
            main_pot=300,
            side_pots=(),
            total_pot=300,
            eligible_players=("player1", "player2")
        )
        
        complex_snapshot = GameStateSnapshot(
            metadata=metadata,
            game_id="complex_game",
            phase=GamePhase.TURN,
            players=(player1, player2),
            pot=pot,
            community_cards=community_cards,
            current_bet=100,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=0,
            active_player_position=1,
            small_blind_amount=25,
            big_blind_amount=50,
            recent_transactions=(transaction,)
        )
        
        # 测试序列化和反序列化
        json_str = SnapshotSerializer.serialize(complex_snapshot)
        restored_snapshot = SnapshotSerializer.deserialize(json_str)
        
        # 验证复杂状态的完整性
        assert restored_snapshot.game_id == complex_snapshot.game_id
        assert restored_snapshot.phase == complex_snapshot.phase
        assert len(restored_snapshot.players) == 2
        assert len(restored_snapshot.community_cards) == 3
        assert len(restored_snapshot.recent_transactions) == 1
        
        # 验证玩家状态
        for orig_player, rest_player in zip(complex_snapshot.players, restored_snapshot.players):
            assert rest_player.player_id == orig_player.player_id
            assert rest_player.chips == orig_player.chips
            assert len(rest_player.hole_cards) == len(orig_player.hole_cards)
            assert rest_player.last_action == orig_player.last_action
        
        # 验证交易记录
        orig_tx = complex_snapshot.recent_transactions[0]
        rest_tx = restored_snapshot.recent_transactions[0]
        assert rest_tx.transaction_id == orig_tx.transaction_id
        assert rest_tx.amount == orig_tx.amount
    
    def test_snapshot_manager_persistence(self):
        """测试快照管理器的持久化功能"""
        manager = SnapshotManager()
        
        # 创建多个快照
        snapshots = []
        for i in range(3):
            snapshot = GameStateSnapshot.create_initial_snapshot(
                game_id=f"persistence_test_{i}",
                players=(
                    PlayerSnapshot(
                        player_id="player1",
                        name="Alice",
                        chips=1000 + i * 100,
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
                        chips=1000 + i * 100,
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
            snapshots.append(snapshot)
        
        # 存储所有快照
        snapshot_ids = []
        for snapshot in snapshots:
            manager._store_snapshot(snapshot)
            snapshot_ids.append(snapshot.metadata.snapshot_id)
        
        # 验证所有快照都能获取
        for i, snapshot_id in enumerate(snapshot_ids):
            restored_snapshot = manager.get_snapshot(snapshot_id)
            assert restored_snapshot is not None
            assert restored_snapshot.game_id == f"persistence_test_{i}"
            assert restored_snapshot.players[0].chips == 1000 + i * 100
        
        # 验证快照历史
        all_snapshots = manager.get_snapshot_history(10)
        assert len(all_snapshots) >= 3
        
        # 清理快照（通过清理旧快照功能）
        manager.clear_old_snapshots(keep_count=0)
    
    def test_snapshot_file_integration(self):
        """测试快照文件操作集成"""
        manager = SnapshotManager()
        
        # 创建测试快照
        snapshot = GameStateSnapshot.create_initial_snapshot(
            game_id="file_integration_test",
            players=(
                PlayerSnapshot(
                    player_id="player1",
                    name="Alice",
                    chips=1500,
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
                    chips=1500,
                    hole_cards=(),
                    position=1,
                    is_active=True,
                    is_all_in=False,
                    current_bet=0,
                    total_bet_this_hand=0
                ),
            ),
            small_blind=25,
            big_blind=50
        )
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_path = temp_file.name
        
        try:
            # 通过序列化器保存到文件
            SnapshotSerializer.serialize_to_file(snapshot, temp_path)
            
            # 通过序列化器从文件加载
            loaded_snapshot = SnapshotSerializer.deserialize_from_file(temp_path)
            
            # 验证加载的快照
            assert loaded_snapshot.game_id == snapshot.game_id
            assert len(loaded_snapshot.players) == len(snapshot.players)
            
            # 通过管理器存储加载的快照
            manager._store_snapshot(loaded_snapshot)
            
            # 通过管理器获取并验证
            restored_snapshot = manager.get_snapshot(loaded_snapshot.metadata.snapshot_id)
            assert restored_snapshot.game_id == snapshot.game_id
            assert restored_snapshot.small_blind_amount == 25
            assert restored_snapshot.big_blind_amount == 50
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_snapshot_version_compatibility(self):
        """测试快照版本兼容性"""
        # 创建不同版本的快照元数据
        metadata_v1 = SnapshotMetadata(
            snapshot_id="version_test",
            version=SnapshotVersion.V1_0,
            created_at=time.time(),
            game_duration=60.0,
            hand_number=1
        )
        
        metadata_current = SnapshotMetadata(
            snapshot_id="version_test",
            version=SnapshotVersion.CURRENT,
            created_at=time.time(),
            game_duration=60.0,
            hand_number=1
        )
        
        # 验证版本信息
        assert metadata_v1.version != metadata_current.version
        assert metadata_current.version == SnapshotVersion.CURRENT
        
        # 创建快照并测试序列化
        snapshot = GameStateSnapshot.create_initial_snapshot(
            game_id="version_test",
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
        
        # 验证当前版本快照可以正常序列化和反序列化
        json_str = SnapshotSerializer.serialize(snapshot)
        restored_snapshot = SnapshotSerializer.deserialize(json_str)
        assert restored_snapshot.metadata.version == SnapshotVersion.CURRENT
    
    def test_snapshot_error_recovery(self):
        """测试快照系统的错误恢复"""
        manager = SnapshotManager()
        
        # 测试获取不存在的快照
        non_existent_snapshot = manager.get_snapshot("non_existent_id")
        assert non_existent_snapshot is None
        
        # 创建有效快照
        snapshot = GameStateSnapshot.create_initial_snapshot(
            game_id="error_recovery_test",
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
        
        # 存储快照
        manager._store_snapshot(snapshot)
        snapshot_id = snapshot.metadata.snapshot_id
        
        # 验证可以正常获取
        restored_snapshot = manager.get_snapshot(snapshot_id)
        assert restored_snapshot is not None
        
        # 清理快照
        manager.clear_old_snapshots(keep_count=0)
        
        # 验证清理后无法获取
        deleted_snapshot = manager.get_snapshot(snapshot_id)
        assert deleted_snapshot is None 