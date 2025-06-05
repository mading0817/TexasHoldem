"""
筹码守恒检查器

检查德州扑克游戏中的筹码守恒不变量。
"""

from typing import Dict, Any, Optional
from ..snapshot.types import GameStateSnapshot
from .base_checker import BaseInvariantChecker
from .types import InvariantType

__all__ = ['ChipConservationChecker']


class ChipConservationChecker(BaseInvariantChecker):
    """筹码守恒检查器
    
    验证以下筹码守恒规则：
    1. 总筹码数量守恒：玩家筹码 + 奖池 = 初始总筹码
    2. 下注金额一致性：玩家下注总和 = 奖池总金额
    3. 筹码不能为负数
    4. 筹码交易记录一致性
    """
    
    def __init__(self, initial_total_chips: Optional[int] = None):
        """初始化筹码守恒检查器
        
        Args:
            initial_total_chips: 初始总筹码数量，如果为None则从第一次检查中推断
        """
        super().__init__(InvariantType.CHIP_CONSERVATION)
        self.initial_total_chips = initial_total_chips
        self._first_check = True
    
    def _perform_check(self, snapshot: GameStateSnapshot) -> bool:
        """执行筹码守恒检查
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        if not self._validate_snapshot(snapshot):
            return False
        
        # 如果是第一次检查，记录初始总筹码
        if self._first_check and self.initial_total_chips is None:
            self.initial_total_chips = self._calculate_total_chips(snapshot)
            self._first_check = False
        
        # 检查各项筹码守恒规则
        checks = [
            self._check_total_chip_conservation(snapshot),
            self._check_bet_pot_consistency(snapshot),
            self._check_no_negative_chips(snapshot),
            self._check_transaction_consistency(snapshot)
        ]
        
        return all(checks)
    
    def _calculate_total_chips(self, snapshot: GameStateSnapshot) -> int:
        """计算当前总筹码数量
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            int: 总筹码数量
        """
        player_chips = self._get_player_total_chips(snapshot)
        pot_chips = snapshot.pot.total_pot
        return player_chips + pot_chips
    
    def _check_total_chip_conservation(self, snapshot: GameStateSnapshot) -> bool:
        """检查总筹码守恒
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        if self.initial_total_chips is None:
            self._create_violation(
                "无法确定初始总筹码数量",
                'CRITICAL',
                {'current_total': self._calculate_total_chips(snapshot)}
            )
            return False
        
        current_total = self._calculate_total_chips(snapshot)
        
        if current_total != self.initial_total_chips:
            self._create_violation(
                f"总筹码不守恒: 初始{self.initial_total_chips}, 当前{current_total}",
                'CRITICAL',
                {
                    'initial_total': self.initial_total_chips,
                    'current_total': current_total,
                    'difference': current_total - self.initial_total_chips,
                    'player_chips': self._get_player_total_chips(snapshot),
                    'pot_chips': snapshot.pot.total_pot
                }
            )
            return False
        
        return True
    
    def _check_bet_pot_consistency(self, snapshot: GameStateSnapshot) -> bool:
        """检查下注与奖池一致性
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        from ..state_machine.types import GamePhase
        
        # 在SHOWDOWN和FINISHED阶段，奖池可能已经被分配，跳过此检查
        if snapshot.phase in [GamePhase.SHOWDOWN, GamePhase.FINISHED]:
            return True
        
        total_bets = self._get_player_total_bets(snapshot)
        pot_total = snapshot.pot.total_pot
        
        if total_bets != pot_total:
            self._create_violation(
                f"下注总额与奖池不一致: 下注{total_bets}, 奖池{pot_total}",
                'CRITICAL',
                {
                    'total_bets': total_bets,
                    'pot_total': pot_total,
                    'main_pot': snapshot.pot.main_pot,
                    'side_pots_count': len(snapshot.pot.side_pots),
                    'difference': total_bets - pot_total
                }
            )
            return False
        
        return True
    
    def _check_no_negative_chips(self, snapshot: GameStateSnapshot) -> bool:
        """检查筹码非负性
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        all_valid = True
        
        # 检查玩家筹码
        for player in snapshot.players:
            if player.chips < 0:
                self._create_violation(
                    f"玩家{player.name}({player.player_id})筹码为负数: {player.chips}",
                    'CRITICAL',
                    {
                        'player_id': player.player_id,
                        'player_name': player.name,
                        'chips': player.chips,
                        'current_bet': player.current_bet,
                        'total_bet_this_hand': player.total_bet_this_hand
                    }
                )
                all_valid = False
            
            if player.current_bet < 0:
                self._create_violation(
                    f"玩家{player.name}({player.player_id})当前下注为负数: {player.current_bet}",
                    'CRITICAL',
                    {
                        'player_id': player.player_id,
                        'player_name': player.name,
                        'current_bet': player.current_bet
                    }
                )
                all_valid = False
            
            if player.total_bet_this_hand < 0:
                self._create_violation(
                    f"玩家{player.name}({player.player_id})本手牌总下注为负数: {player.total_bet_this_hand}",
                    'CRITICAL',
                    {
                        'player_id': player.player_id,
                        'player_name': player.name,
                        'total_bet_this_hand': player.total_bet_this_hand
                    }
                )
                all_valid = False
        
        # 检查奖池
        if snapshot.pot.main_pot < 0:
            self._create_violation(
                f"主池为负数: {snapshot.pot.main_pot}",
                'CRITICAL',
                {'main_pot': snapshot.pot.main_pot}
            )
            all_valid = False
        
        if snapshot.pot.total_pot < 0:
            self._create_violation(
                f"总奖池为负数: {snapshot.pot.total_pot}",
                'CRITICAL',
                {'total_pot': snapshot.pot.total_pot}
            )
            all_valid = False
        
        return all_valid
    
    def _check_transaction_consistency(self, snapshot: GameStateSnapshot) -> bool:
        """检查筹码交易记录一致性
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        # 如果没有交易记录，跳过检查
        if not snapshot.recent_transactions:
            return True
        
        # 计算交易记录中的筹码变化
        transaction_changes: Dict[str, int] = {}
        
        for transaction in snapshot.recent_transactions:
            player_id = transaction.player_id
            if player_id not in transaction_changes:
                transaction_changes[player_id] = 0
            
            if transaction.transaction_type.name == 'DEDUCT':
                transaction_changes[player_id] -= transaction.amount
            elif transaction.transaction_type.name == 'ADD':
                transaction_changes[player_id] += transaction.amount
        
        # 验证交易记录的合理性
        all_valid = True
        for player_id, change in transaction_changes.items():
            player = snapshot.get_player_by_id(player_id)
            if player is None:
                self._create_violation(
                    f"交易记录中的玩家{player_id}不存在",
                    'WARNING',
                    {'player_id': player_id, 'change': change}
                )
                all_valid = False
        
        return all_valid
    
    def reset_initial_chips(self, initial_total_chips: int):
        """重置初始筹码数量
        
        Args:
            initial_total_chips: 新的初始总筹码数量
        """
        self.initial_total_chips = initial_total_chips
        self._first_check = True 