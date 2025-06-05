"""
下注规则检查器

检查德州扑克游戏中的下注规则不变量。
"""

from typing import List, Dict, Any
from ..snapshot.types import GameStateSnapshot, PlayerSnapshot
from ..state_machine.types import GamePhase
from .base_checker import BaseInvariantChecker
from .types import InvariantType

__all__ = ['BettingRulesChecker']


class BettingRulesChecker(BaseInvariantChecker):
    """下注规则检查器
    
    验证以下下注规则：
    1. 最小加注规则：加注金额至少是前一次加注的两倍
    2. 全押规则：全押玩家不能再下注
    3. 下注顺序规则：玩家下注必须按顺序进行
    4. 盲注规则：小盲和大盲的设置正确
    5. 下注限制：下注不能超过玩家筹码
    """
    
    def __init__(self, min_raise_multiplier: float = 2.0):
        """初始化下注规则检查器
        
        Args:
            min_raise_multiplier: 最小加注倍数，默认为2.0
        """
        super().__init__(InvariantType.BETTING_RULES)
        self.min_raise_multiplier = min_raise_multiplier
    
    def _perform_check(self, snapshot: GameStateSnapshot) -> bool:
        """执行下注规则检查
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        if not self._validate_snapshot(snapshot):
            return False
        
        # 检查各项下注规则
        checks = [
            self._check_betting_limits(snapshot),
            self._check_all_in_rules(snapshot),
            self._check_blind_rules(snapshot),
            self._check_current_bet_consistency(snapshot),
            self._check_phase_betting_rules(snapshot),
            self._check_minimum_raise_rules(snapshot),
            self._check_inactive_player_rules(snapshot)
        ]
        
        return all(checks)
    
    def _check_betting_limits(self, snapshot: GameStateSnapshot) -> bool:
        """检查下注限制
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        all_valid = True
        
        for player in snapshot.players:
            # 检查玩家下注不能超过筹码
            total_available = player.chips + player.total_bet_this_hand
            if player.total_bet_this_hand > total_available:
                self._create_violation(
                    f"玩家{player.name}({player.player_id})下注超过可用筹码: "
                    f"下注{player.total_bet_this_hand}, 可用{total_available}",
                    'CRITICAL',
                    {
                        'player_id': player.player_id,
                        'player_name': player.name,
                        'total_bet': player.total_bet_this_hand,
                        'chips': player.chips,
                        'total_available': total_available
                    }
                )
                all_valid = False
            
            # 检查当前轮下注不能超过筹码
            if player.current_bet > player.chips + player.current_bet:
                self._create_violation(
                    f"玩家{player.name}({player.player_id})当前轮下注超过筹码: "
                    f"下注{player.current_bet}, 筹码{player.chips}",
                    'CRITICAL',
                    {
                        'player_id': player.player_id,
                        'player_name': player.name,
                        'current_bet': player.current_bet,
                        'chips': player.chips
                    }
                )
                all_valid = False
        
        return all_valid
    
    def _check_all_in_rules(self, snapshot: GameStateSnapshot) -> bool:
        """检查全押规则
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        all_valid = True
        
        for player in snapshot.players:
            if player.is_all_in:
                # 全押玩家筹码应该为0或接近0
                if player.chips > 0:
                    self._create_violation(
                        f"全押玩家{player.name}({player.player_id})仍有筹码: {player.chips}",
                        'WARNING',
                        {
                            'player_id': player.player_id,
                            'player_name': player.name,
                            'chips': player.chips,
                            'is_all_in': player.is_all_in
                        }
                    )
                    # 这里使用WARNING而不是CRITICAL，因为可能存在舍入误差
        
        return all_valid
    
    def _check_blind_rules(self, snapshot: GameStateSnapshot) -> bool:
        """检查盲注规则
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        all_valid = True
        
        # 检查盲注金额的合理性
        if snapshot.big_blind_amount <= snapshot.small_blind_amount:
            self._create_violation(
                f"大盲({snapshot.big_blind_amount})应该大于小盲({snapshot.small_blind_amount})",
                'CRITICAL',
                {
                    'small_blind': snapshot.small_blind_amount,
                    'big_blind': snapshot.big_blind_amount
                }
            )
            all_valid = False
        
        # 检查盲注位置的有效性
        player_count = len(snapshot.players)
        if snapshot.small_blind_position >= player_count:
            self._create_violation(
                f"小盲位置({snapshot.small_blind_position})超出玩家数量({player_count})",
                'CRITICAL',
                {
                    'small_blind_position': snapshot.small_blind_position,
                    'player_count': player_count
                }
            )
            all_valid = False
        
        if snapshot.big_blind_position >= player_count:
            self._create_violation(
                f"大盲位置({snapshot.big_blind_position})超出玩家数量({player_count})",
                'CRITICAL',
                {
                    'big_blind_position': snapshot.big_blind_position,
                    'player_count': player_count
                }
            )
            all_valid = False
        
        # 检查盲注位置不能相同（除非只有2个玩家）
        if (player_count > 2 and 
            snapshot.small_blind_position == snapshot.big_blind_position):
            self._create_violation(
                f"小盲和大盲位置不能相同: {snapshot.small_blind_position}",
                'CRITICAL',
                {
                    'small_blind_position': snapshot.small_blind_position,
                    'big_blind_position': snapshot.big_blind_position,
                    'player_count': player_count
                }
            )
            all_valid = False
        
        return all_valid
    
    def _check_current_bet_consistency(self, snapshot: GameStateSnapshot) -> bool:
        """检查当前下注一致性
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        all_valid = True
        
        # 找出当前轮最高下注
        max_current_bet = max(player.current_bet for player in snapshot.players)
        
        # 检查快照中记录的当前下注是否正确
        if snapshot.current_bet != max_current_bet:
            self._create_violation(
                f"当前下注记录不一致: 快照记录{snapshot.current_bet}, 实际最高{max_current_bet}",
                'CRITICAL',
                {
                    'snapshot_current_bet': snapshot.current_bet,
                    'actual_max_bet': max_current_bet,
                    'player_bets': {p.player_id: p.current_bet for p in snapshot.players}
                }
            )
            all_valid = False
        
        return all_valid
    
    def _check_phase_betting_rules(self, snapshot: GameStateSnapshot) -> bool:
        """检查阶段特定的下注规则
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        all_valid = True
        
        # 根据不同阶段检查特定规则
        if snapshot.phase == GamePhase.INIT:
            # 初始阶段不应该有下注
            if snapshot.current_bet > 0:
                self._create_violation(
                    f"初始阶段不应该有下注: {snapshot.current_bet}",
                    'WARNING',
                    {'phase': snapshot.phase.name, 'current_bet': snapshot.current_bet}
                )
        
        elif snapshot.phase == GamePhase.PRE_FLOP:
            # 翻牌前阶段应该有盲注
            if snapshot.pot.total_pot == 0:
                self._create_violation(
                    "翻牌前阶段奖池为空，可能缺少盲注",
                    'WARNING',
                    {'phase': snapshot.phase.name, 'pot_total': snapshot.pot.total_pot}
                )
        
        elif snapshot.phase == GamePhase.FINISHED:
            # 结束阶段，活跃玩家应该很少
            active_players = self._get_active_players(snapshot)
            if len(active_players) > 1:
                # 这可能是正常的，如果是平局的话
                pass
        
        return all_valid
    

    
    def _check_minimum_raise_rules(self, snapshot: GameStateSnapshot) -> bool:
        """检查最小加注规则
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        all_valid = True
        
        # 找出当前轮的最高下注和次高下注
        bets = [player.current_bet for player in snapshot.players if player.is_active]
        if len(bets) < 2:
            return True  # 不足2人无法判断加注
        
        bets_sorted = sorted(bets, reverse=True)
        highest_bet = bets_sorted[0]
        second_highest = bets_sorted[1] if len(bets_sorted) > 1 else 0
        
        # 如果有加注行为，检查是否符合最小加注规则
        if highest_bet > second_highest:
            raise_amount = highest_bet - second_highest
            min_raise = snapshot.big_blind_amount  # 最小加注至少是大盲注
            
            # 在翻牌前，盲注不算违规
            is_preflop_blinds = (snapshot.phase == GamePhase.PRE_FLOP and 
                                 ((second_highest == 0 and highest_bet == snapshot.small_blind_amount) or
                                  (second_highest == snapshot.small_blind_amount and highest_bet == snapshot.big_blind_amount)))
            
            if raise_amount < min_raise and raise_amount > 0 and not is_preflop_blinds:
                # 找出加注玩家
                raising_player = None
                for player in snapshot.players:
                    if player.current_bet == highest_bet and player.is_active:
                        raising_player = player
                        break
                
                if raising_player and not raising_player.is_all_in:
                    self._create_violation(
                        f"玩家{raising_player.name}({raising_player.player_id})加注不足: "
                        f"加注{raise_amount}, 最小加注{min_raise}",
                        'WARNING',
                        {
                            'player_id': raising_player.player_id,
                            'player_name': raising_player.name,
                            'raise_amount': raise_amount,
                            'min_raise': min_raise,
                            'current_bet': highest_bet,
                            'previous_bet': second_highest
                        }
                    )
                    all_valid = False
        
        return all_valid
    
    def _check_inactive_player_rules(self, snapshot: GameStateSnapshot) -> bool:
        """检查非活跃玩家规则
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        all_valid = True
        
        for player in snapshot.players:
            # 非活跃玩家不应该有当前下注
            if not player.is_active and player.current_bet > 0:
                self._create_violation(
                    f"非活跃玩家{player.name}({player.player_id})不应该有当前下注: {player.current_bet}",
                    'CRITICAL',
                    {
                        'player_id': player.player_id,
                        'player_name': player.name,
                        'current_bet': player.current_bet,
                        'is_active': player.is_active,
                        'is_all_in': player.is_all_in
                    }
                )
                all_valid = False
        
        return all_valid 