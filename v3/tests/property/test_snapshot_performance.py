"""
快照系统性能测试

测试快照系统的性能表现，确保快照操作不影响游戏性能。
包含反作弊验证，确保测试使用真实的核心模块。
"""

import pytest
import time
import tempfile
import os
from typing import List

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


class TestSnapshotPerformance:
    """测试快照系统性能"""
    
    def test_snapshot_creation_performance(self):
        """测试快照创建性能"""
        # 创建大量玩家的游戏状态
        players = []
        for i in range(10):  # 10个玩家
            player = PlayerSnapshot(
                player_id=f"player_{i}",
                name=f"Player{i}",
                chips=1000 + i * 100,
                hole_cards=(
                    Card(Suit.HEARTS, Rank.ACE),
                    Card(Suit.SPADES, Rank.KING)
                ),
                position=i,
                is_active=True,
                is_all_in=False,
                current_bet=50,
                total_bet_this_hand=100,
                last_action="CALL"
            )
            players.append(player)
        
        # 创建复杂的游戏状态
        community_cards = (
            Card(Suit.HEARTS, Rank.TEN),
            Card(Suit.SPADES, Rank.NINE),
            Card(Suit.DIAMONDS, Rank.EIGHT),
            Card(Suit.CLUBS, Rank.SEVEN),
            Card(Suit.HEARTS, Rank.SIX)
        )
        
        transactions = []
        for i in range(20):  # 20个交易记录
            transaction = ChipTransaction(
                transaction_id=f"tx_{i}",
                player_id=f"player_{i % 10}",
                transaction_type=TransactionType.DEDUCT,
                amount=50,
                timestamp=time.time() - i,
                description=f"交易{i}"
            )
            transactions.append(transaction)
        
        timestamp = time.time()
        metadata = SnapshotMetadata(
            snapshot_id="performance_test",
            version=SnapshotVersion.CURRENT,
            created_at=timestamp,
            game_duration=300.0,
            hand_number=50,
            description="性能测试快照"
        )
        
        pot = PotSnapshot(
            main_pot=1000,
            side_pots=(),
            total_pot=1000,
            eligible_players=tuple(f"player_{i}" for i in range(10))
        )
        
        # 测试快照创建性能
        start_time = time.time()
        
        snapshot = GameStateSnapshot(
            metadata=metadata,
            game_id="performance_test_game",
            phase=GamePhase.RIVER,
            players=tuple(players),
            pot=pot,
            community_cards=community_cards,
            current_bet=50,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=2,
            active_player_position=3,
            small_blind_amount=25,
            big_blind_amount=50,
            recent_transactions=tuple(transactions)
        )
        
        creation_time = time.time() - start_time
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(snapshot, "GameStateSnapshot")
        
        # 验证创建时间应该很快（小于10毫秒）
        assert creation_time < 0.01, f"快照创建时间过长: {creation_time:.4f}秒"
        
        # 验证快照内容完整性
        assert len(snapshot.players) == 10
        assert len(snapshot.community_cards) == 5
        assert len(snapshot.recent_transactions) == 20
    
    def test_snapshot_serialization_performance(self):
        """测试快照序列化性能"""
        # 创建复杂快照
        snapshot = self._create_complex_snapshot()
        
        # 测试序列化性能
        start_time = time.time()
        json_str = SnapshotSerializer.serialize(snapshot)
        serialization_time = time.time() - start_time
        
        # 验证序列化时间应该很快（小于50毫秒）
        assert serialization_time < 0.05, f"序列化时间过长: {serialization_time:.4f}秒"
        
        # 验证序列化结果
        assert isinstance(json_str, str)
        assert len(json_str) > 1000  # 复杂快照应该有足够的数据
        
        # 测试反序列化性能
        start_time = time.time()
        restored_snapshot = SnapshotSerializer.deserialize(json_str)
        deserialization_time = time.time() - start_time
        
        # 验证反序列化时间应该很快（小于50毫秒）
        assert deserialization_time < 0.05, f"反序列化时间过长: {deserialization_time:.4f}秒"
        
        # 验证反序列化结果
        assert restored_snapshot.game_id == snapshot.game_id
        assert len(restored_snapshot.players) == len(snapshot.players)
    
    def test_snapshot_manager_performance(self):
        """测试快照管理器性能"""
        manager = SnapshotManager()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(manager, "SnapshotManager")
        
        # 创建多个快照
        snapshots = []
        for i in range(50):  # 50个快照
            snapshot = GameStateSnapshot.create_initial_snapshot(
                game_id=f"perf_test_{i}",
                players=(
                    PlayerSnapshot(
                        player_id="player1",
                        name="Alice",
                        chips=1000 + i * 10,
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
                        chips=1000 + i * 10,
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
        
        # 测试批量存储性能
        start_time = time.time()
        for snapshot in snapshots:
            manager._store_snapshot(snapshot)
        storage_time = time.time() - start_time
        
        # 验证存储时间应该合理（小于100毫秒）
        assert storage_time < 0.1, f"批量存储时间过长: {storage_time:.4f}秒"
        
        # 测试批量获取性能
        start_time = time.time()
        for snapshot in snapshots:
            retrieved = manager.get_snapshot(snapshot.metadata.snapshot_id)
            assert retrieved is not None
        retrieval_time = time.time() - start_time
        
        # 验证获取时间应该合理（小于50毫秒）
        assert retrieval_time < 0.05, f"批量获取时间过长: {retrieval_time:.4f}秒"
        
        # 测试历史记录获取性能
        start_time = time.time()
        history = manager.get_snapshot_history(20)
        history_time = time.time() - start_time
        
        # 验证历史记录获取时间应该很快（小于10毫秒）
        assert history_time < 0.01, f"历史记录获取时间过长: {history_time:.4f}秒"
        assert len(history) == 20
        
        # 清理
        manager.clear_old_snapshots(keep_count=0)
    
    def test_file_operations_performance(self):
        """测试文件操作性能"""
        # 创建复杂快照
        snapshot = self._create_complex_snapshot()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_path = temp_file.name
        
        try:
            # 测试文件写入性能
            start_time = time.time()
            SnapshotSerializer.serialize_to_file(snapshot, temp_path)
            write_time = time.time() - start_time
            
            # 验证写入时间应该合理（小于100毫秒）
            assert write_time < 0.1, f"文件写入时间过长: {write_time:.4f}秒"
            
            # 验证文件大小
            file_size = os.path.getsize(temp_path)
            assert file_size > 1000, "文件大小应该足够大"
            
            # 测试文件读取性能
            start_time = time.time()
            loaded_snapshot = SnapshotSerializer.deserialize_from_file(temp_path)
            read_time = time.time() - start_time
            
            # 验证读取时间应该合理（小于100毫秒）
            assert read_time < 0.1, f"文件读取时间过长: {read_time:.4f}秒"
            
            # 验证读取结果
            assert loaded_snapshot.game_id == snapshot.game_id
            assert len(loaded_snapshot.players) == len(snapshot.players)
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_memory_usage_efficiency(self):
        """测试内存使用效率"""
        import gc
        import sys
        
        # 强制垃圾回收
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # 创建大量快照
        snapshots = []
        for i in range(100):
            snapshot = GameStateSnapshot.create_initial_snapshot(
                game_id=f"memory_test_{i}",
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
            snapshots.append(snapshot)
        
        # 检查对象数量增长
        gc.collect()
        after_creation_objects = len(gc.get_objects())
        object_growth = after_creation_objects - initial_objects
        
        # 验证对象增长应该合理（每个快照不应该创建过多对象）
        max_expected_objects = len(snapshots) * 50  # 每个快照最多50个对象
        assert object_growth < max_expected_objects, f"对象增长过多: {object_growth}"
        
        # 清理快照
        snapshots.clear()
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # 验证内存清理效果（对象数量应该接近初始值）
        remaining_growth = final_objects - initial_objects
        assert remaining_growth < 100, f"内存清理不彻底: {remaining_growth}个对象未清理"
    
    def test_concurrent_operations_performance(self):
        """测试并发操作性能（模拟）"""
        manager = SnapshotManager()
        
        # 创建基础快照
        base_snapshot = GameStateSnapshot.create_initial_snapshot(
            game_id="concurrent_test",
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
        
        # 模拟并发操作：快速连续的存储和获取
        start_time = time.time()
        
        for i in range(20):
            # 存储快照
            manager._store_snapshot(base_snapshot)
            
            # 立即获取快照
            retrieved = manager.get_snapshot(base_snapshot.metadata.snapshot_id)
            assert retrieved is not None
            
            # 序列化和反序列化
            json_str = SnapshotSerializer.serialize(retrieved)
            deserialized = SnapshotSerializer.deserialize(json_str)
            assert deserialized.game_id == base_snapshot.game_id
        
        concurrent_time = time.time() - start_time
        
        # 验证并发操作时间应该合理（小于200毫秒）
        assert concurrent_time < 0.2, f"并发操作时间过长: {concurrent_time:.4f}秒"
    
    def _create_complex_snapshot(self) -> GameStateSnapshot:
        """创建复杂的测试快照"""
        # 创建多个玩家
        players = []
        for i in range(8):
            player = PlayerSnapshot(
                player_id=f"player_{i}",
                name=f"Player{i}",
                chips=1000 + i * 100,
                hole_cards=(
                    Card(Suit.HEARTS, Rank.ACE),
                    Card(Suit.SPADES, Rank.KING)
                ) if i % 2 == 0 else (),
                position=i,
                is_active=i < 6,
                is_all_in=i == 7,
                current_bet=50 if i < 6 else 0,
                total_bet_this_hand=100 + i * 10,
                last_action="CALL" if i < 6 else "FOLD"
            )
            players.append(player)
        
        # 创建社区牌
        community_cards = (
            Card(Suit.HEARTS, Rank.TEN),
            Card(Suit.SPADES, Rank.NINE),
            Card(Suit.DIAMONDS, Rank.EIGHT),
            Card(Suit.CLUBS, Rank.SEVEN),
            Card(Suit.HEARTS, Rank.SIX)
        )
        
        # 创建交易记录
        transactions = []
        for i in range(15):
            transaction = ChipTransaction(
                transaction_id=f"complex_tx_{i}",
                player_id=f"player_{i % 8}",
                transaction_type=TransactionType.DEDUCT if i % 2 == 0 else TransactionType.ADD,
                amount=25 + i * 5,
                timestamp=time.time() - i * 10,
                description=f"复杂交易{i}"
            )
            transactions.append(transaction)
        
        # 创建元数据
        timestamp = time.time()
        metadata = SnapshotMetadata(
            snapshot_id=f"complex_snapshot_{int(timestamp * 1000000)}",
            version=SnapshotVersion.CURRENT,
            created_at=timestamp,
            game_duration=450.5,
            hand_number=25,
            description="复杂性能测试快照"
        )
        
        # 创建奖池
        pot = PotSnapshot(
            main_pot=800,
            side_pots=(
                {"amount": 200, "eligible_players": ["player_0", "player_1", "player_2"]},
                {"amount": 150, "eligible_players": ["player_3", "player_4"]}
            ),
            total_pot=1150,
            eligible_players=tuple(f"player_{i}" for i in range(6))
        )
        
        return GameStateSnapshot(
            metadata=metadata,
            game_id="complex_performance_test",
            phase=GamePhase.RIVER,
            players=tuple(players),
            pot=pot,
            community_cards=community_cards,
            current_bet=50,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=2,
            active_player_position=3,
            small_blind_amount=25,
            big_blind_amount=50,
            recent_transactions=tuple(transactions)
        ) 