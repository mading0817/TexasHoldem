"""
快照序列化器

实现游戏状态快照的序列化和反序列化功能。
支持JSON格式的序列化，确保数据的完整性和版本兼容性。
"""

import json
from typing import Dict, Any, Optional
from dataclasses import asdict

from .types import (
    GameStateSnapshot, PlayerSnapshot, PotSnapshot, SnapshotMetadata,
    SnapshotVersion
)
from ..state_machine.types import GamePhase
from ..deck.card import Card
from ..deck.types import Suit, Rank
from ..chips.chip_transaction import ChipTransaction, TransactionType

__all__ = ['SnapshotSerializer', 'SerializationError', 'DeserializationError']


class SerializationError(Exception):
    """序列化错误"""
    pass


class DeserializationError(Exception):
    """反序列化错误"""
    pass


class SnapshotSerializer:
    """
    快照序列化器
    
    负责游戏状态快照的序列化和反序列化。
    支持JSON格式，确保数据完整性和版本兼容性。
    """
    
    @staticmethod
    def serialize(snapshot: GameStateSnapshot) -> str:
        """
        将快照序列化为JSON字符串
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            str: JSON格式的序列化字符串
            
        Raises:
            SerializationError: 序列化失败时抛出
        """
        try:
            # 转换为字典
            snapshot_dict = SnapshotSerializer._snapshot_to_dict(snapshot)
            
            # 序列化为JSON
            return json.dumps(snapshot_dict, ensure_ascii=False, indent=2)
            
        except Exception as e:
            raise SerializationError(f"快照序列化失败: {str(e)}") from e
    
    @staticmethod
    def deserialize(json_str: str) -> GameStateSnapshot:
        """
        从JSON字符串反序列化快照
        
        Args:
            json_str: JSON格式的序列化字符串
            
        Returns:
            GameStateSnapshot: 反序列化的游戏状态快照
            
        Raises:
            DeserializationError: 反序列化失败时抛出
        """
        try:
            # 解析JSON
            snapshot_dict = json.loads(json_str)
            
            # 转换为快照对象
            return SnapshotSerializer._dict_to_snapshot(snapshot_dict)
            
        except Exception as e:
            raise DeserializationError(f"快照反序列化失败: {str(e)}") from e
    
    @staticmethod
    def serialize_to_file(snapshot: GameStateSnapshot, file_path: str):
        """
        将快照序列化并保存到文件
        
        Args:
            snapshot: 游戏状态快照
            file_path: 文件路径
            
        Raises:
            SerializationError: 序列化或文件写入失败时抛出
        """
        try:
            json_str = SnapshotSerializer.serialize(snapshot)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
        except Exception as e:
            raise SerializationError(f"快照保存到文件失败: {str(e)}") from e
    
    @staticmethod
    def deserialize_from_file(file_path: str) -> GameStateSnapshot:
        """
        从文件读取并反序列化快照
        
        Args:
            file_path: 文件路径
            
        Returns:
            GameStateSnapshot: 反序列化的游戏状态快照
            
        Raises:
            DeserializationError: 文件读取或反序列化失败时抛出
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_str = f.read()
            return SnapshotSerializer.deserialize(json_str)
        except Exception as e:
            raise DeserializationError(f"从文件读取快照失败: {str(e)}") from e
    
    @staticmethod
    def _snapshot_to_dict(snapshot: GameStateSnapshot) -> Dict[str, Any]:
        """将快照对象转换为字典"""
        return {
            'metadata': SnapshotSerializer._metadata_to_dict(snapshot.metadata),
            'game_id': snapshot.game_id,
            'phase': snapshot.phase.name,
            'players': [SnapshotSerializer._player_to_dict(p) for p in snapshot.players],
            'pot': SnapshotSerializer._pot_to_dict(snapshot.pot),
            'community_cards': [SnapshotSerializer._card_to_dict(c) for c in snapshot.community_cards],
            'current_bet': snapshot.current_bet,
            'dealer_position': snapshot.dealer_position,
            'small_blind_position': snapshot.small_blind_position,
            'big_blind_position': snapshot.big_blind_position,
            'active_player_position': snapshot.active_player_position,
            'small_blind_amount': snapshot.small_blind_amount,
            'big_blind_amount': snapshot.big_blind_amount,
            'recent_transactions': [SnapshotSerializer._transaction_to_dict(t) for t in snapshot.recent_transactions]
        }
    
    @staticmethod
    def _dict_to_snapshot(data: Dict[str, Any]) -> GameStateSnapshot:
        """将字典转换为快照对象"""
        metadata = SnapshotSerializer._dict_to_metadata(data['metadata'])
        players = tuple(SnapshotSerializer._dict_to_player(p) for p in data['players'])
        pot = SnapshotSerializer._dict_to_pot(data['pot'])
        community_cards = tuple(SnapshotSerializer._dict_to_card(c) for c in data['community_cards'])
        recent_transactions = tuple(SnapshotSerializer._dict_to_transaction(t) for t in data['recent_transactions'])
        
        return GameStateSnapshot(
            metadata=metadata,
            game_id=data['game_id'],
            phase=GamePhase[data['phase']],
            players=players,
            pot=pot,
            community_cards=community_cards,
            current_bet=data['current_bet'],
            dealer_position=data['dealer_position'],
            small_blind_position=data['small_blind_position'],
            big_blind_position=data['big_blind_position'],
            active_player_position=data.get('active_player_position'),
            small_blind_amount=data['small_blind_amount'],
            big_blind_amount=data['big_blind_amount'],
            recent_transactions=recent_transactions
        )
    
    @staticmethod
    def _metadata_to_dict(metadata: SnapshotMetadata) -> Dict[str, Any]:
        """将元数据转换为字典"""
        return {
            'snapshot_id': metadata.snapshot_id,
            'version': metadata.version.value,
            'created_at': metadata.created_at,
            'game_duration': metadata.game_duration,
            'hand_number': metadata.hand_number,
            'description': metadata.description
        }
    
    @staticmethod
    def _dict_to_metadata(data: Dict[str, Any]) -> SnapshotMetadata:
        """将字典转换为元数据"""
        return SnapshotMetadata(
            snapshot_id=data['snapshot_id'],
            version=SnapshotVersion(data['version']),
            created_at=data['created_at'],
            game_duration=data['game_duration'],
            hand_number=data['hand_number'],
            description=data.get('description')
        )
    
    @staticmethod
    def _player_to_dict(player: PlayerSnapshot) -> Dict[str, Any]:
        """将玩家快照转换为字典"""
        return {
            'player_id': player.player_id,
            'name': player.name,
            'chips': player.chips,
            'hole_cards': [SnapshotSerializer._card_to_dict(c) for c in player.hole_cards],
            'position': player.position,
            'is_active': player.is_active,
            'is_all_in': player.is_all_in,
            'current_bet': player.current_bet,
            'total_bet_this_hand': player.total_bet_this_hand,
            'last_action': player.last_action
        }
    
    @staticmethod
    def _dict_to_player(data: Dict[str, Any]) -> PlayerSnapshot:
        """将字典转换为玩家快照"""
        hole_cards = tuple(SnapshotSerializer._dict_to_card(c) for c in data['hole_cards'])
        
        return PlayerSnapshot(
            player_id=data['player_id'],
            name=data['name'],
            chips=data['chips'],
            hole_cards=hole_cards,
            position=data['position'],
            is_active=data['is_active'],
            is_all_in=data['is_all_in'],
            current_bet=data['current_bet'],
            total_bet_this_hand=data['total_bet_this_hand'],
            last_action=data.get('last_action')
        )
    
    @staticmethod
    def _pot_to_dict(pot: PotSnapshot) -> Dict[str, Any]:
        """将奖池快照转换为字典"""
        return {
            'main_pot': pot.main_pot,
            'side_pots': list(pot.side_pots),
            'total_pot': pot.total_pot,
            'eligible_players': list(pot.eligible_players)
        }
    
    @staticmethod
    def _dict_to_pot(data: Dict[str, Any]) -> PotSnapshot:
        """将字典转换为奖池快照"""
        return PotSnapshot(
            main_pot=data['main_pot'],
            side_pots=tuple(data['side_pots']),
            total_pot=data['total_pot'],
            eligible_players=tuple(data['eligible_players'])
        )
    
    @staticmethod
    def _card_to_dict(card: Card) -> Dict[str, str]:
        """将卡牌转换为字典"""
        return {
            'suit': card.suit.name,
            'rank': card.rank.name
        }
    
    @staticmethod
    def _dict_to_card(data: Dict[str, str]) -> Card:
        """将字典转换为卡牌"""
        return Card(
            suit=Suit[data['suit']],
            rank=Rank[data['rank']]
        )
    
    @staticmethod
    def _transaction_to_dict(transaction: ChipTransaction) -> Dict[str, Any]:
        """将交易记录转换为字典"""
        return {
            'transaction_id': transaction.transaction_id,
            'transaction_type': transaction.transaction_type.name,
            'player_id': transaction.player_id,
            'amount': transaction.amount,
            'timestamp': transaction.timestamp,
            'description': transaction.description,
            'metadata': transaction.metadata
        }
    
    @staticmethod
    def _dict_to_transaction(data: Dict[str, Any]) -> ChipTransaction:
        """将字典转换为交易记录"""
        return ChipTransaction(
            transaction_id=data['transaction_id'],
            transaction_type=TransactionType[data['transaction_type']],
            player_id=data['player_id'],
            amount=data['amount'],
            timestamp=data['timestamp'],
            description=data['description'],
            metadata=data.get('metadata')
        ) 