"""
快照管理器

实现游戏状态快照的创建、恢复和管理功能。
"""

from typing import Dict, List, Optional, Any
import time
import copy

from .types import (
    GameStateSnapshot, PlayerSnapshot, PotSnapshot, SnapshotMetadata, 
    SnapshotVersion
)
from ..state_machine.types import GameContext, GamePhase
from ..deck.card import Card
from ..chips.chip_transaction import ChipTransaction
from ..chips.chip_ledger import ChipLedger

__all__ = ['SnapshotManager', 'SnapshotCreationError', 'SnapshotRestoreError', 'get_snapshot_manager']


class SnapshotCreationError(Exception):
    """快照创建错误"""
    pass


class SnapshotRestoreError(Exception):
    """快照恢复错误"""
    pass


class SnapshotManager:
    """
    快照管理器
    
    负责游戏状态快照的创建、恢复和管理。
    支持版本控制和快照历史记录。
    """
    
    def __init__(self):
        """初始化快照管理器"""
        self._snapshots: Dict[str, GameStateSnapshot] = {}
        self._snapshot_history: List[str] = []  # 按时间顺序存储快照ID
        self._max_history_size: int = 100  # 最大历史记录数量
    
    def create_snapshot(self, game_context: GameContext, 
                       hand_number: int = 1,
                       description: Optional[str] = None) -> GameStateSnapshot:
        """
        从游戏上下文创建状态快照
        
        Args:
            game_context: 当前游戏上下文
            hand_number: 手牌编号
            description: 快照描述
            
        Returns:
            GameStateSnapshot: 创建的游戏状态快照
            
        Raises:
            SnapshotCreationError: 快照创建失败时抛出
        """
        try:
            # 创建元数据
            timestamp = time.time()
            metadata = SnapshotMetadata(
                snapshot_id=f"snapshot_{game_context.game_id}_{int(timestamp * 1000000)}",
                version=SnapshotVersion.CURRENT,
                created_at=timestamp,
                game_duration=0.0,  # 需要从游戏上下文计算
                hand_number=hand_number,
                description=description or f"游戏快照 - {game_context.current_phase.name}"
            )
            
            # 创建玩家快照
            players = self._create_player_snapshots(game_context)
            
            # 创建奖池快照
            pot = self._create_pot_snapshot(game_context)
            
            # 创建社区牌快照
            community_cards = tuple(game_context.community_cards) if game_context.community_cards else ()
            
            # 计算位置信息
            player_count = len(players)
            dealer_position = 0
            small_blind_position = 1 % player_count if player_count > 1 else 0
            big_blind_position = 2 % player_count if player_count > 2 else (1 if player_count > 1 else 0)
            
            # 创建游戏状态快照
            snapshot = GameStateSnapshot(
                metadata=metadata,
                game_id=game_context.game_id,
                phase=game_context.current_phase,
                players=players,
                pot=pot,
                community_cards=community_cards,
                current_bet=game_context.current_bet,
                dealer_position=dealer_position,
                small_blind_position=small_blind_position,
                big_blind_position=big_blind_position,
                active_player_position=self._get_active_player_position(game_context),
                small_blind_amount=game_context.small_blind,  # 从游戏上下文获取小盲注
                big_blind_amount=game_context.big_blind,      # 从游戏上下文获取大盲注
                recent_transactions=()  # 需要从游戏上下文获取
            )
            
            # 存储快照
            self._store_snapshot(snapshot)
            
            return snapshot
            
        except Exception as e:
            raise SnapshotCreationError(f"创建快照失败: {str(e)}") from e
    
    def restore_from_snapshot(self, snapshot: GameStateSnapshot) -> GameContext:
        """
        从快照恢复游戏上下文
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            GameContext: 恢复的游戏上下文
            
        Raises:
            SnapshotRestoreError: 快照恢复失败时抛出
        """
        try:
            # 恢复玩家信息
            players = self._restore_players_from_snapshot(snapshot.players)
            
            # 从快照恢复筹码账本和当前手牌下注
            initial_balances = {p.player_id: p.chips for p in snapshot.players}
            ledger = ChipLedger(initial_balances)
            current_hand_bets = {p.player_id: p.total_bet_this_hand for p in snapshot.players if p.total_bet_this_hand > 0}
            
            # 恢复社区牌
            community_cards = list(snapshot.community_cards)
            
            # 创建游戏上下文
            context = GameContext(
                game_id=snapshot.game_id,
                current_phase=snapshot.phase,
                players=players,
                chip_ledger=ledger,
                community_cards=community_cards,
                current_bet=snapshot.current_bet,
                current_hand_bets=current_hand_bets,
                small_blind=snapshot.small_blind_amount,
                big_blind=snapshot.big_blind_amount,
                active_player_id=self._get_active_player_id(snapshot)
            )
            
            return context
            
        except Exception as e:
            raise SnapshotRestoreError(f"从快照恢复失败: {str(e)}") from e
    
    def get_snapshot(self, snapshot_id: str) -> Optional[GameStateSnapshot]:
        """
        获取指定ID的快照
        
        Args:
            snapshot_id: 快照ID
            
        Returns:
            Optional[GameStateSnapshot]: 快照对象，如果不存在则返回None
        """
        return self._snapshots.get(snapshot_id)
    
    def get_latest_snapshot(self) -> Optional[GameStateSnapshot]:
        """
        获取最新的快照
        
        Returns:
            Optional[GameStateSnapshot]: 最新的快照，如果没有则返回None
        """
        if not self._snapshot_history:
            return None
        
        latest_id = self._snapshot_history[-1]
        return self._snapshots.get(latest_id)
    
    def get_snapshot_history(self, limit: int = 10) -> List[GameStateSnapshot]:
        """
        获取快照历史记录
        
        Args:
            limit: 返回的快照数量限制
            
        Returns:
            List[GameStateSnapshot]: 快照列表，按时间倒序排列
        """
        history_ids = self._snapshot_history[-limit:] if limit > 0 else self._snapshot_history
        snapshots = []
        
        for snapshot_id in reversed(history_ids):
            snapshot = self._snapshots.get(snapshot_id)
            if snapshot:
                snapshots.append(snapshot)
        
        return snapshots
    
    def clear_old_snapshots(self, keep_count: int = 50):
        """
        清理旧的快照，保留指定数量的最新快照
        
        Args:
            keep_count: 保留的快照数量
        """
        if len(self._snapshot_history) <= keep_count:
            return
        
        # 计算需要删除的快照数量
        to_remove_count = len(self._snapshot_history) - keep_count
        to_remove_ids = self._snapshot_history[:to_remove_count]
        
        # 删除旧快照
        for snapshot_id in to_remove_ids:
            self._snapshots.pop(snapshot_id, None)
        
        # 更新历史记录
        self._snapshot_history = self._snapshot_history[to_remove_count:]
    
    def _create_player_snapshots(self, game_context: GameContext) -> tuple:
        """从游戏上下文的玩家信息创建玩家快照
        
        平衡修复：is_active表示"在游戏中且未弃牌"，但增强active_player_position逻辑
        这保持了原有语义的同时，通过active_player_position确保状态一致性
        """
        player_snapshots = []
        
        for player_id, player_data in game_context.players.items():
            # 处理手牌
            hole_cards = ()
            if 'hole_cards' in player_data and player_data['hole_cards']:
                hole_cards = tuple(player_data['hole_cards'])
            
            # 平衡修复：is_active保持原有语义（在游戏中且未弃牌），
            # 但通过增强的active_player_position逻辑确保状态一致性
            base_active = player_data.get('active', False)
            player_status = player_data.get('status', 'active')
            
            # is_active表示"在游戏中且未弃牌"
            is_in_hand = base_active and player_status not in ['folded', 'out']
            
            # (Phase 4 Fix) 从ChipLedger获取筹码的唯一真实来源
            chips = game_context.chip_ledger.get_balance(player_id)
            
            player_snapshot = PlayerSnapshot(
                player_id=player_id,
                name=player_data.get('name', player_id),
                chips=chips, # 修复：使用ChipLedger的真实筹码
                hole_cards=hole_cards,
                position=player_data.get('position', 0),
                is_active=is_in_hand,  # 修复：在游戏中且未弃牌
                is_all_in=player_data.get('is_all_in', False),
                current_bet=player_data.get('current_bet', 0),
                total_bet_this_hand=player_data.get('total_bet_this_hand', 0),
                last_action=player_data.get('last_action')
            )
            player_snapshots.append(player_snapshot)
        
        return tuple(player_snapshots)
    
    def _create_pot_snapshot(self, game_context: GameContext) -> PotSnapshot:
        """从游戏上下文创建奖池快照"""
        total_pot = sum(game_context.current_hand_bets.values())
        
        eligible_players = set(game_context.current_hand_bets.keys())
        for p_id, p_data in game_context.players.items():
            if p_data.get('status') not in ['folded', 'out']:
                eligible_players.add(p_id)

        return PotSnapshot(
            main_pot=total_pot,  # 简化，真实边池由PotManager在结算时计算
            side_pots=(),
            total_pot=total_pot,
            eligible_players=tuple(sorted(list(eligible_players)))
        )
    
    def _get_active_player_position(self, game_context: GameContext) -> Optional[int]:
        """获取当前活跃玩家的位置
        
        修复：与状态机保持完全一致的可行动性检查逻辑
        """
        # 首先尝试使用game_context.active_player_id，但要严格验证
        if game_context.active_player_id:
            player_data = game_context.players.get(game_context.active_player_id)
            if player_data and self._is_player_actionable(game_context, game_context.active_player_id):
                return player_data.get('position', 0)
        
        # 如果active_player_id指向的玩家不活跃，或者没有active_player_id，
        # 则寻找第一个真正活跃的玩家
        for player_id, player_data in game_context.players.items():
            if self._is_player_actionable(game_context, player_id):
                return player_data.get('position', 0)
        
        return None
    
    def _is_player_actionable(self, game_context: GameContext, player_id: str) -> bool:
        """检查玩家是否可以行动（与状态机逻辑完全一致）
        
        可行动条件：
        1. 玩家存在于游戏中
        2. active=True（仍在手牌中）
        3. chips > 0（有筹码可下注）
        4. status不是folded/out（未弃牌或出局）
        
        注意：all_in玩家虽然active=True，但chips=0，所以不可行动
        """
        if player_id not in game_context.players:
            return False
            
        player_data = game_context.players[player_id]
        
        return (
            player_data.get('active', False) and 
            player_data.get('chips', 0) > 0 and 
            player_data.get('status', 'active') not in ['folded', 'out']
        )
    
    def _restore_players_from_snapshot(self, player_snapshots: tuple) -> Dict[str, Any]:
        """从玩家快照恢复玩家信息
        
        修复：正确处理is_active到active字段的映射
        is_active现在表示"可行动性"，需要正确恢复到GameContext结构
        """
        players = {}
        
        for player_snapshot in player_snapshots:
            # 恢复基础active状态：如果玩家可行动，肯定active=True
            # 如果玩家不可行动，可能是all-in（active=True, chips=0）或者folded（active=False）
            # 根据is_all_in和chips来判断真实的active状态
            base_active = player_snapshot.is_active or player_snapshot.is_all_in
            
            players[player_snapshot.player_id] = {
                'name': player_snapshot.name,
                'chips': player_snapshot.chips,
                'hole_cards': list(player_snapshot.hole_cards),
                'position': player_snapshot.position,
                'active': base_active,  # 修复：正确恢复active状态
                'is_all_in': player_snapshot.is_all_in,
                'current_bet': player_snapshot.current_bet,
                'total_bet_this_hand': player_snapshot.total_bet_this_hand,
                'last_action': player_snapshot.last_action,
                'status': 'all_in' if player_snapshot.is_all_in else 'active'  # 确保状态一致
            }
        
        return players
    
    def _get_active_player_id(self, snapshot: GameStateSnapshot) -> Optional[str]:
        """从快照获取当前活跃玩家ID"""
        if snapshot.active_player_position is None:
            return None
        
        for player in snapshot.players:
            if player.position == snapshot.active_player_position:
                return player.player_id
        
        return None
    
    def _store_snapshot(self, snapshot: GameStateSnapshot):
        """存储快照并管理历史记录"""
        if len(self._snapshot_history) >= self._max_history_size:
            # 移除最旧的快照ID和对象
            oldest_id = self._snapshot_history.pop(0)
            self._snapshots.pop(oldest_id, None)
            
        self._snapshots[snapshot.metadata.snapshot_id] = snapshot
        self._snapshot_history.append(snapshot.metadata.snapshot_id)

# 全局单例
_snapshot_manager_instance: Optional[SnapshotManager] = None

def get_snapshot_manager() -> SnapshotManager:
    """
    获取快照管理器的单例实例
    
    Returns:
        SnapshotManager: 快照管理器实例
    """
    global _snapshot_manager_instance
    if _snapshot_manager_instance is None:
        _snapshot_manager_instance = SnapshotManager()
    return _snapshot_manager_instance 