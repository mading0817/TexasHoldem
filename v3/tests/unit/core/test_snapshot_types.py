"""
快照类型单元测试

测试快照相关的数据类型，确保不可变性和数据完整性。
包含反作弊验证，确保测试使用真实的核心模块。
"""

import pytest
import time
from typing import Tuple

from v3.core.snapshot.types import (
    SnapshotVersion, PlayerSnapshot, PotSnapshot, 
    GameStateSnapshot, SnapshotMetadata
)
from v3.core.state_machine.types import GamePhase
from v3.core.deck.card import Card
from v3.core.deck.types import Suit, Rank
from v3.core.chips.chip_transaction import ChipTransaction, TransactionType
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestSnapshotVersion:
    """测试快照版本枚举"""
    
    def test_snapshot_version_values(self):
        """测试快照版本的值"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(SnapshotVersion.V1_0, "SnapshotVersion")
        
        assert SnapshotVersion.V1_0.value == "1.0"
        assert SnapshotVersion.V1_1.value == "1.1"
        assert SnapshotVersion.CURRENT == SnapshotVersion.V1_1
    
    def test_snapshot_version_immutable(self):
        """测试快照版本的不可变性"""
        version = SnapshotVersion.CURRENT
        CoreUsageChecker.verify_real_objects(version, "SnapshotVersion")
        
        # 枚举本身就是不可变的
        assert version.value == "1.1"


class TestPlayerSnapshot:
    """测试玩家快照"""
    
    def test_player_snapshot_creation(self):
        """测试玩家快照的创建"""
        # 创建测试数据
        card1 = Card(Suit.HEARTS, Rank.ACE)
        card2 = Card(Suit.SPADES, Rank.KING)
        hole_cards = (card1, card2)
        
        player = PlayerSnapshot(
            player_id="player1",
            name="Alice",
            chips=1000,
            hole_cards=hole_cards,
            position=0,
            is_active=True,
            is_all_in=False,
            current_bet=50,
            total_bet_this_hand=100,
            last_action="raise"
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(player, "PlayerSnapshot")
        
        # 验证属性
        assert player.player_id == "player1"
        assert player.name == "Alice"
        assert player.chips == 1000
        assert player.hole_cards == hole_cards
        assert player.position == 0
        assert player.is_active is True
        assert player.is_all_in is False
        assert player.current_bet == 50
        assert player.total_bet_this_hand == 100
        assert player.last_action == "raise"
    
    def test_player_snapshot_immutable(self):
        """测试玩家快照的不可变性"""
        player = PlayerSnapshot(
            player_id="player1",
            name="Alice",
            chips=1000,
            hole_cards=(),
            position=0,
            is_active=True,
            is_all_in=False,
            current_bet=0,
            total_bet_this_hand=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(player, "PlayerSnapshot")
        
        # 尝试修改属性应该失败
        with pytest.raises(AttributeError):
            player.chips = 2000
    
    def test_player_snapshot_validation(self):
        """测试玩家快照的数据验证"""
        # 测试空player_id
        with pytest.raises(ValueError, match="player_id不能为空"):
            PlayerSnapshot(
                player_id="",
                name="Alice",
                chips=1000,
                hole_cards=(),
                position=0,
                is_active=True,
                is_all_in=False,
                current_bet=0,
                total_bet_this_hand=0
            )
        
        # 测试负数chips
        with pytest.raises(ValueError, match="chips不能为负数"):
            PlayerSnapshot(
                player_id="player1",
                name="Alice",
                chips=-100,
                hole_cards=(),
                position=0,
                is_active=True,
                is_all_in=False,
                current_bet=0,
                total_bet_this_hand=0
            )
        
        # 测试过多手牌
        card1 = Card(Suit.HEARTS, Rank.ACE)
        card2 = Card(Suit.SPADES, Rank.KING)
        card3 = Card(Suit.DIAMONDS, Rank.QUEEN)
        
        with pytest.raises(ValueError, match="手牌不能超过2张"):
            PlayerSnapshot(
                player_id="player1",
                name="Alice",
                chips=1000,
                hole_cards=(card1, card2, card3),
                position=0,
                is_active=True,
                is_all_in=False,
                current_bet=0,
                total_bet_this_hand=0
            )


class TestPotSnapshot:
    """测试奖池快照"""
    
    def test_pot_snapshot_creation(self):
        """测试奖池快照的创建"""
        side_pot = {"amount": 200, "eligible_players": ["player1", "player2"]}
        
        pot = PotSnapshot(
            main_pot=500,
            side_pots=(side_pot,),
            total_pot=700,
            eligible_players=("player1", "player2", "player3")
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(pot, "PotSnapshot")
        
        # 验证属性
        assert pot.main_pot == 500
        assert pot.side_pots == (side_pot,)
        assert pot.total_pot == 700
        assert pot.eligible_players == ("player1", "player2", "player3")
    
    def test_pot_snapshot_immutable(self):
        """测试奖池快照的不可变性"""
        pot = PotSnapshot(
            main_pot=500,
            side_pots=(),
            total_pot=500,
            eligible_players=("player1", "player2")
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(pot, "PotSnapshot")
        
        # 尝试修改属性应该失败
        with pytest.raises(AttributeError):
            pot.main_pot = 1000
    
    def test_pot_snapshot_validation(self):
        """测试奖池快照的数据验证"""
        # 测试负数main_pot
        with pytest.raises(ValueError, match="main_pot不能为负数"):
            PotSnapshot(
                main_pot=-100,
                side_pots=(),
                total_pot=0,
                eligible_players=()
            )
        
        # 测试total_pot小于main_pot
        with pytest.raises(ValueError, match="total_pot不能小于main_pot"):
            PotSnapshot(
                main_pot=500,
                side_pots=(),
                total_pot=300,
                eligible_players=()
            )


class TestSnapshotMetadata:
    """测试快照元数据"""
    
    def test_metadata_creation(self):
        """测试元数据的创建"""
        timestamp = time.time()
        
        metadata = SnapshotMetadata(
            snapshot_id="snapshot_123",
            version=SnapshotVersion.CURRENT,
            created_at=timestamp,
            game_duration=120.5,
            hand_number=5,
            description="测试快照"
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(metadata, "SnapshotMetadata")
        
        # 验证属性
        assert metadata.snapshot_id == "snapshot_123"
        assert metadata.version == SnapshotVersion.CURRENT
        assert metadata.created_at == timestamp
        assert metadata.game_duration == 120.5
        assert metadata.hand_number == 5
        assert metadata.description == "测试快照"
    
    def test_metadata_validation(self):
        """测试元数据的数据验证"""
        timestamp = time.time()
        
        # 测试空snapshot_id
        with pytest.raises(ValueError, match="snapshot_id不能为空"):
            SnapshotMetadata(
                snapshot_id="",
                version=SnapshotVersion.CURRENT,
                created_at=timestamp,
                game_duration=0.0,
                hand_number=1
            )
        
        # 测试负数game_duration
        with pytest.raises(ValueError, match="game_duration不能为负数"):
            SnapshotMetadata(
                snapshot_id="snapshot_123",
                version=SnapshotVersion.CURRENT,
                created_at=timestamp,
                game_duration=-10.0,
                hand_number=1
            )


class TestGameStateSnapshot:
    """测试游戏状态快照"""
    
    def test_game_state_snapshot_creation(self):
        """测试游戏状态快照的创建"""
        # 创建测试数据
        timestamp = time.time()
        metadata = SnapshotMetadata(
            snapshot_id="snapshot_123",
            version=SnapshotVersion.CURRENT,
            created_at=timestamp,
            game_duration=0.0,
            hand_number=1
        )
        
        player1 = PlayerSnapshot(
            player_id="player1",
            name="Alice",
            chips=1000,
            hole_cards=(),
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
            game_id="game_123",
            phase=GamePhase.INIT,
            players=(player1, player2),
            pot=pot,
            community_cards=(),
            current_bet=0,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=0,
            small_blind_amount=10,
            big_blind_amount=20
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(snapshot, "GameStateSnapshot")
        
        # 验证属性
        assert snapshot.game_id == "game_123"
        assert snapshot.phase == GamePhase.INIT
        assert len(snapshot.players) == 2
        assert snapshot.current_bet == 0
        assert snapshot.small_blind_amount == 10
        assert snapshot.big_blind_amount == 20
    
    def test_create_initial_snapshot(self):
        """测试创建初始快照"""
        player1 = PlayerSnapshot(
            player_id="player1",
            name="Alice",
            chips=1000,
            hole_cards=(),
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
        
        snapshot = GameStateSnapshot.create_initial_snapshot(
            game_id="game_123",
            players=(player1, player2),
            small_blind=10,
            big_blind=20
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(snapshot, "GameStateSnapshot")
        
        # 验证初始状态
        assert snapshot.game_id == "game_123"
        assert snapshot.phase == GamePhase.INIT
        assert snapshot.small_blind_amount == 10
        assert snapshot.big_blind_amount == 20
        assert snapshot.pot.total_pot == 0
        assert len(snapshot.community_cards) == 0
    
    def test_get_player_by_id(self):
        """测试根据ID获取玩家"""
        player1 = PlayerSnapshot(
            player_id="player1",
            name="Alice",
            chips=1000,
            hole_cards=(),
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
        
        snapshot = GameStateSnapshot.create_initial_snapshot(
            game_id="game_123",
            players=(player1, player2),
            small_blind=10,
            big_blind=20
        )
        
        # 测试获取存在的玩家
        found_player = snapshot.get_player_by_id("player1")
        assert found_player is not None
        assert found_player.player_id == "player1"
        assert found_player.name == "Alice"
        
        # 测试获取不存在的玩家
        not_found = snapshot.get_player_by_id("player3")
        assert not_found is None
    
    def test_get_total_chips(self):
        """测试获取总筹码数"""
        player1 = PlayerSnapshot(
            player_id="player1",
            name="Alice",
            chips=1000,
            hole_cards=(),
            position=0,
            is_active=True,
            is_all_in=False,
            current_bet=0,
            total_bet_this_hand=0
        )
        
        player2 = PlayerSnapshot(
            player_id="player2",
            name="Bob",
            chips=1500,
            hole_cards=(),
            position=1,
            is_active=True,
            is_all_in=False,
            current_bet=0,
            total_bet_this_hand=0
        )
        
        snapshot = GameStateSnapshot.create_initial_snapshot(
            game_id="game_123",
            players=(player1, player2),
            small_blind=10,
            big_blind=20
        )
        
        # 总筹码 = 玩家筹码 + 奖池
        total_chips = snapshot.get_total_chips()
        assert total_chips == 1000 + 1500 + 0  # 玩家筹码 + 奖池
    
    def test_snapshot_validation(self):
        """测试快照的数据验证"""
        # 测试空玩家列表
        timestamp = time.time()
        metadata = SnapshotMetadata(
            snapshot_id="snapshot_123",
            version=SnapshotVersion.CURRENT,
            created_at=timestamp,
            game_duration=0.0,
            hand_number=1
        )
        
        pot = PotSnapshot(
            main_pot=0,
            side_pots=(),
            total_pot=0,
            eligible_players=()
        )
        
        with pytest.raises(ValueError, match="players不能为空"):
            GameStateSnapshot(
                metadata=metadata,
                game_id="game_123",
                phase=GamePhase.INIT,
                players=(),
                pot=pot,
                community_cards=(),
                current_bet=0,
                dealer_position=0,
                small_blind_position=0,
                big_blind_position=1
            ) 