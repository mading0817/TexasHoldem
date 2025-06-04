"""
快照管理器单元测试

测试快照管理器的创建、恢复和管理功能。
包含反作弊验证，确保测试使用真实的核心模块。
"""

import pytest
import time
from unittest.mock import Mock

from v3.core.snapshot.snapshot_manager import (
    SnapshotManager, SnapshotCreationError, SnapshotRestoreError
)
from v3.core.snapshot.types import (
    GameStateSnapshot, PlayerSnapshot, PotSnapshot, SnapshotMetadata,
    SnapshotVersion
)
from v3.core.state_machine.types import GameContext, GamePhase
from v3.core.deck.card import Card
from v3.core.deck.types import Suit, Rank
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestSnapshotManager:
    """测试快照管理器"""
    
    def test_snapshot_manager_creation(self):
        """测试快照管理器的创建"""
        manager = SnapshotManager()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(manager, "SnapshotManager")
        
        # 验证初始状态
        assert len(manager._snapshots) == 0
        assert len(manager._snapshot_history) == 0
        assert manager._max_history_size == 100
    
    def test_create_snapshot_basic(self):
        """测试基本的快照创建"""
        manager = SnapshotManager()
        
        # 创建测试游戏上下文
        game_context = GameContext(
            game_id="test_game",
            current_phase=GamePhase.PRE_FLOP,
            players={
                "player1": {
                    "name": "Alice",
                    "chips": 1000,
                    "position": 0,
                    "is_active": True,
                    "is_all_in": False,
                    "current_bet": 50,
                    "total_bet_this_hand": 50,
                    "hole_cards": []
                },
                "player2": {
                    "name": "Bob", 
                    "chips": 950,
                    "position": 1,
                    "is_active": True,
                    "is_all_in": False,
                    "current_bet": 50,
                    "total_bet_this_hand": 50,
                    "hole_cards": []
                }
            },
            community_cards=[],
            pot_total=100,
            current_bet=50,
            active_player_id="player1"
        )
        
        # 创建快照
        snapshot = manager.create_snapshot(game_context, hand_number=1, description="测试快照")
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(snapshot, "GameStateSnapshot")
        
        # 验证快照内容
        assert snapshot.game_id == "test_game"
        assert snapshot.phase == GamePhase.PRE_FLOP
        assert len(snapshot.players) == 2
        assert snapshot.pot.total_pot == 100
        assert snapshot.current_bet == 50
        assert snapshot.metadata.hand_number == 1
        assert snapshot.metadata.description == "测试快照"
        
        # 验证快照已存储
        assert len(manager._snapshots) == 1
        assert len(manager._snapshot_history) == 1
        assert snapshot.metadata.snapshot_id in manager._snapshots
    
    def test_create_snapshot_with_cards(self):
        """测试包含卡牌的快照创建"""
        manager = SnapshotManager()
        
        # 创建测试卡牌
        card1 = Card(Suit.HEARTS, Rank.ACE)
        card2 = Card(Suit.SPADES, Rank.KING)
        community_card = Card(Suit.DIAMONDS, Rank.QUEEN)
        
        game_context = GameContext(
            game_id="test_game",
            current_phase=GamePhase.FLOP,
            players={
                "player1": {
                    "name": "Alice",
                    "chips": 1000,
                    "position": 0,
                    "is_active": True,
                    "is_all_in": False,
                    "current_bet": 0,
                    "total_bet_this_hand": 0,
                    "hole_cards": [card1, card2]
                }
            },
            community_cards=[community_card],
            pot_total=0,
            current_bet=0
        )
        
        snapshot = manager.create_snapshot(game_context)
        
        # 验证卡牌信息
        assert len(snapshot.players[0].hole_cards) == 2
        assert snapshot.players[0].hole_cards[0] == card1
        assert snapshot.players[0].hole_cards[1] == card2
        assert len(snapshot.community_cards) == 1
        assert snapshot.community_cards[0] == community_card
    
    def test_restore_from_snapshot(self):
        """测试从快照恢复游戏上下文"""
        manager = SnapshotManager()
        
        # 创建测试快照
        timestamp = time.time()
        metadata = SnapshotMetadata(
            snapshot_id="test_snapshot",
            version=SnapshotVersion.CURRENT,
            created_at=timestamp,
            game_duration=120.0,
            hand_number=5
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
            active_player_position=0,
            small_blind_amount=50,  # 添加小盲注金额
            big_blind_amount=100    # 添加大盲注金额
        )
        
        # 恢复游戏上下文
        restored_context = manager.restore_from_snapshot(snapshot)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(restored_context, "GameContext")
        
        # 验证恢复的上下文
        assert restored_context.game_id == "test_game"
        assert restored_context.current_phase == GamePhase.TURN
        assert len(restored_context.players) == 2
        assert restored_context.pot_total == 200
        assert restored_context.current_bet == 50
        assert restored_context.active_player_id == "player1"
        
        # 验证玩家信息
        assert "player1" in restored_context.players
        assert "player2" in restored_context.players
        assert restored_context.players["player1"]["name"] == "Alice"
        assert restored_context.players["player1"]["chips"] == 1000
        assert restored_context.players["player2"]["name"] == "Bob"
        assert restored_context.players["player2"]["chips"] == 950
    
    def test_get_snapshot(self):
        """测试获取指定快照"""
        manager = SnapshotManager()
        
        # 创建并存储快照
        game_context = GameContext(
            game_id="test_game",
            current_phase=GamePhase.INIT,
            players={"player1": {"name": "Alice", "chips": 1000, "position": 0}},
            community_cards=[],
            pot_total=0,
            current_bet=0,
            small_blind=50,
            big_blind=100
        )
        
        snapshot = manager.create_snapshot(game_context)
        snapshot_id = snapshot.metadata.snapshot_id
        
        # 获取快照
        retrieved_snapshot = manager.get_snapshot(snapshot_id)
        
        assert retrieved_snapshot is not None
        assert retrieved_snapshot.metadata.snapshot_id == snapshot_id
        assert retrieved_snapshot.game_id == "test_game"
        
        # 获取不存在的快照
        non_existent = manager.get_snapshot("non_existent_id")
        assert non_existent is None
    
    def test_get_latest_snapshot(self):
        """测试获取最新快照"""
        manager = SnapshotManager()
        
        # 空管理器应该返回None
        assert manager.get_latest_snapshot() is None
        
        # 创建多个快照
        game_context = GameContext(
            game_id="test_game",
            current_phase=GamePhase.INIT,
            players={"player1": {"name": "Alice", "chips": 1000, "position": 0}},
            community_cards=[],
            pot_total=0,
            current_bet=0
        )
        
        snapshot1 = manager.create_snapshot(game_context, hand_number=1)
        time.sleep(0.001)  # 确保时间戳不同
        snapshot2 = manager.create_snapshot(game_context, hand_number=2)
        
        # 获取最新快照
        latest = manager.get_latest_snapshot()
        assert latest is not None
        assert latest.metadata.snapshot_id == snapshot2.metadata.snapshot_id
        assert latest.metadata.hand_number == 2
    
    def test_get_snapshot_history(self):
        """测试获取快照历史"""
        manager = SnapshotManager()
        
        # 创建多个快照
        game_context = GameContext(
            game_id="test_game",
            current_phase=GamePhase.INIT,
            players={"player1": {"name": "Alice", "chips": 1000, "position": 0}},
            community_cards=[],
            pot_total=0,
            current_bet=0
        )
        
        snapshots = []
        for i in range(5):
            snapshot = manager.create_snapshot(game_context, hand_number=i+1)
            snapshots.append(snapshot)
            time.sleep(0.001)  # 确保时间戳不同
        
        # 获取历史记录（默认限制10个）
        history = manager.get_snapshot_history()
        assert len(history) == 5
        
        # 验证顺序（最新的在前）
        for i, snapshot in enumerate(history):
            expected_hand_number = 5 - i  # 倒序
            assert snapshot.metadata.hand_number == expected_hand_number
        
        # 测试限制数量
        limited_history = manager.get_snapshot_history(limit=3)
        assert len(limited_history) == 3
        assert limited_history[0].metadata.hand_number == 5
        assert limited_history[2].metadata.hand_number == 3
    
    def test_clear_old_snapshots(self):
        """测试清理旧快照"""
        manager = SnapshotManager()
        
        # 创建多个快照
        game_context = GameContext(
            game_id="test_game",
            current_phase=GamePhase.INIT,
            players={"player1": {"name": "Alice", "chips": 1000, "position": 0}},
            community_cards=[],
            pot_total=0,
            current_bet=0
        )
        
        snapshots = []
        for i in range(10):
            snapshot = manager.create_snapshot(game_context, hand_number=i+1)
            snapshots.append(snapshot)
            time.sleep(0.001)
        
        # 验证所有快照都存在
        assert len(manager._snapshots) == 10
        assert len(manager._snapshot_history) == 10
        
        # 清理旧快照，保留5个
        manager.clear_old_snapshots(keep_count=5)
        
        # 验证只保留了5个最新的快照
        assert len(manager._snapshots) == 5
        assert len(manager._snapshot_history) == 5
        
        # 验证保留的是最新的快照
        remaining_snapshots = manager.get_snapshot_history()
        assert len(remaining_snapshots) == 5
        assert remaining_snapshots[0].metadata.hand_number == 10  # 最新的
        assert remaining_snapshots[4].metadata.hand_number == 6   # 最旧的保留快照
    
    def test_snapshot_creation_error_handling(self):
        """测试快照创建的错误处理"""
        manager = SnapshotManager()
        
        # 测试无效的游戏上下文（空玩家列表）
        invalid_context = GameContext(
            game_id="test_game",
            current_phase=GamePhase.INIT,
            players={},  # 空玩家列表会导致快照验证失败
            community_cards=[],
            pot_total=0,
            current_bet=0
        )
        
        with pytest.raises(SnapshotCreationError):
            manager.create_snapshot(invalid_context)
    
    def test_snapshot_restore_error_handling(self):
        """测试快照恢复的错误处理"""
        manager = SnapshotManager()
        
        # 创建一个无效的快照（缺少必要字段）
        timestamp = time.time()
        metadata = SnapshotMetadata(
            snapshot_id="test_snapshot",
            version=SnapshotVersion.CURRENT,
            created_at=timestamp,
            game_duration=0.0,
            hand_number=1
        )
        
        # 创建空玩家列表的快照（这会在验证时失败）
        pot = PotSnapshot(
            main_pot=0,
            side_pots=(),
            total_pot=0,
            eligible_players=()
        )
        
        # 这个快照创建会失败，因为players为空
        with pytest.raises(ValueError):
            GameStateSnapshot(
                metadata=metadata,
                game_id="test_game",
                phase=GamePhase.INIT,
                players=(),  # 空玩家列表
                pot=pot,
                community_cards=(),
                current_bet=0,
                dealer_position=0,
                small_blind_position=0,
                big_blind_position=1
            )
    
    def test_max_history_size_enforcement(self):
        """测试历史记录大小限制的执行"""
        manager = SnapshotManager()
        manager._max_history_size = 5  # 设置较小的限制用于测试
        
        game_context = GameContext(
            game_id="test_game",
            current_phase=GamePhase.INIT,
            players={"player1": {"name": "Alice", "chips": 1000, "position": 0}},
            community_cards=[],
            pot_total=0,
            current_bet=0
        )
        
        # 创建超过限制的快照
        for i in range(8):
            manager.create_snapshot(game_context, hand_number=i+1)
            time.sleep(0.001)
        
        # 验证自动清理生效
        assert len(manager._snapshot_history) <= manager._max_history_size 