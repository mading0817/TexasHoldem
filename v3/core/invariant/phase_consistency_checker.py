"""
阶段一致性检查器

检查德州扑克游戏中的阶段一致性不变量。
"""

from typing import Dict, Any, Set
from ..snapshot.types import GameStateSnapshot
from ..state_machine.types import GamePhase
from .base_checker import BaseInvariantChecker
from .types import InvariantType

__all__ = ['PhaseConsistencyChecker']


class PhaseConsistencyChecker(BaseInvariantChecker):
    """阶段一致性检查器
    
    验证以下阶段一致性规则：
    1. 公共牌数量与阶段匹配
    2. 玩家手牌数量正确
    3. 阶段转换的合法性
    4. 活跃玩家状态与阶段匹配
    5. 奖池状态与阶段匹配
    """
    
    def __init__(self):
        """初始化阶段一致性检查器"""
        super().__init__(InvariantType.PHASE_CONSISTENCY)
        
        # 定义每个阶段应有的公共牌数量
        self.expected_community_cards = {
            GamePhase.INIT: 0,
            GamePhase.PRE_FLOP: 0,
            GamePhase.FLOP: 3,
            GamePhase.TURN: 4,
            GamePhase.RIVER: 5,
            GamePhase.SHOWDOWN: 5,
            GamePhase.FINISHED: 5
        }
        
        # 定义合法的阶段转换
        self.valid_transitions = {
            GamePhase.INIT: {GamePhase.PRE_FLOP},
            GamePhase.PRE_FLOP: {GamePhase.FLOP, GamePhase.SHOWDOWN, GamePhase.FINISHED},
            GamePhase.FLOP: {GamePhase.TURN, GamePhase.SHOWDOWN, GamePhase.FINISHED},
            GamePhase.TURN: {GamePhase.RIVER, GamePhase.SHOWDOWN, GamePhase.FINISHED},
            GamePhase.RIVER: {GamePhase.SHOWDOWN, GamePhase.FINISHED},
            GamePhase.SHOWDOWN: {GamePhase.FINISHED},
            GamePhase.FINISHED: set()  # 结束阶段不能转换到其他阶段
        }
    
    def _perform_check(self, snapshot: GameStateSnapshot) -> bool:
        """执行阶段一致性检查
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        if not self._validate_snapshot(snapshot):
            return False
        
        # 检查各项阶段一致性规则
        checks = [
            self._check_community_cards_count(snapshot),
            self._check_community_cards_uniqueness(snapshot),
            self._check_player_hole_cards(snapshot),
            self._check_active_players_consistency(snapshot),
            self._check_pot_consistency(snapshot),
            self._check_betting_consistency(snapshot)
        ]
        
        return all(checks)
    
    def _check_community_cards_count(self, snapshot: GameStateSnapshot) -> bool:
        """检查公共牌数量与阶段匹配
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        expected_count = self.expected_community_cards.get(snapshot.phase)
        if expected_count is None:
            self._create_violation(
                f"未知的游戏阶段: {snapshot.phase}",
                'CRITICAL',
                {'phase': snapshot.phase.name if snapshot.phase else 'None'}
            )
            return False
        
        actual_count = len(snapshot.community_cards)
        
        if actual_count != expected_count:
            self._create_violation(
                f"阶段{snapshot.phase.name}的公共牌数量不正确: "
                f"期望{expected_count}张, 实际{actual_count}张",
                'CRITICAL',
                {
                    'phase': snapshot.phase.name,
                    'expected_count': expected_count,
                    'actual_count': actual_count,
                    'community_cards': [str(card) for card in snapshot.community_cards]
                }
            )
            return False
        
        return True
    
    def _check_community_cards_uniqueness(self, snapshot: GameStateSnapshot) -> bool:
        """检查公共牌的唯一性（无重复牌）
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        if not snapshot.community_cards:
            return True  # 没有公共牌时无需检查
        
        # 检查公共牌中是否有重复
        seen_cards = set()
        duplicate_cards = []
        
        for card in snapshot.community_cards:
            card_key = (card.suit, card.rank)
            if card_key in seen_cards:
                duplicate_cards.append(str(card))
            else:
                seen_cards.add(card_key)
        
        if duplicate_cards:
            self._create_violation(
                f"公共牌中存在重复牌: {', '.join(duplicate_cards)}",
                'CRITICAL',
                {
                    'phase': snapshot.phase.name,
                    'duplicate_cards': duplicate_cards,
                    'community_cards': [str(card) for card in snapshot.community_cards],
                    'total_cards': len(snapshot.community_cards),
                    'unique_cards': len(seen_cards)
                }
            )
            return False
        
        return True
    
    def _check_player_hole_cards(self, snapshot: GameStateSnapshot) -> bool:
        """检查玩家手牌数量正确
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        all_valid = True
        
        for player in snapshot.players:
            hole_cards_count = len(player.hole_cards)
            
            # 活跃玩家应该有2张手牌（除非在某些特殊情况下）
            if player.is_active and hole_cards_count != 2:
                # 在INIT阶段，玩家可能还没有手牌
                if snapshot.phase != GamePhase.INIT:
                    self._create_violation(
                        f"活跃玩家{player.name}({player.player_id})手牌数量不正确: "
                        f"期望2张, 实际{hole_cards_count}张",
                        'CRITICAL',
                        {
                            'player_id': player.player_id,
                            'player_name': player.name,
                            'is_active': player.is_active,
                            'hole_cards_count': hole_cards_count,
                            'phase': snapshot.phase.name
                        }
                    )
                    all_valid = False
            
            # 检查手牌不能超过2张
            if hole_cards_count > 2:
                self._create_violation(
                    f"玩家{player.name}({player.player_id})手牌过多: {hole_cards_count}张",
                    'CRITICAL',
                    {
                        'player_id': player.player_id,
                        'player_name': player.name,
                        'hole_cards_count': hole_cards_count
                    }
                )
                all_valid = False
        
        return all_valid
    
    def _check_active_players_consistency(self, snapshot: GameStateSnapshot) -> bool:
        """检查活跃玩家状态与阶段匹配
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        all_valid = True
        active_players = self._get_active_players(snapshot)
        active_count = len(active_players)
        
        # 检查活跃玩家数量的合理性
        if snapshot.phase == GamePhase.FINISHED:
            # 结束阶段可能有0-1个活跃玩家
            if active_count > 1:
                # 这可能是平局情况，给出警告而不是错误
                self._create_violation(
                    f"结束阶段有多个活跃玩家({active_count})，可能是平局",
                    'INFO',
                    {
                        'phase': snapshot.phase.name,
                        'active_count': active_count,
                        'active_players': [p.player_id for p in active_players]
                    }
                )
        else:
            # 其他阶段至少应该有1个活跃玩家
            if active_count < 1:
                self._create_violation(
                    f"阶段{snapshot.phase.name}没有活跃玩家",
                    'CRITICAL',
                    {
                        'phase': snapshot.phase.name,
                        'active_count': active_count
                    }
                )
                all_valid = False
        
        # 检查活跃玩家的位置信息
        if snapshot.active_player_position is not None:
            if snapshot.active_player_position >= len(snapshot.players):
                self._create_violation(
                    f"活跃玩家位置({snapshot.active_player_position})超出玩家数量范围",
                    'CRITICAL',
                    {
                        'active_player_position': snapshot.active_player_position,
                        'player_count': len(snapshot.players)
                    }
                )
                all_valid = False
            else:
                # 修复：检查该位置的玩家是否可以行动或合理地被设为活跃玩家
                active_player = snapshot.players[snapshot.active_player_position]
                
                # 玩家应该满足以下条件之一：
                # 1. is_active=True 且 chips>0 (可行动)
                # 2. is_active=True 且 is_all_in=True (all-in但仍在游戏中)
                # 3. 所有其他玩家都不能行动的特殊情况
                
                can_be_active = (
                    active_player.is_active and 
                    (active_player.chips > 0 or active_player.is_all_in)
                )
                
                if not can_be_active:
                    # 检查是否是"无人可行动"的特殊情况
                    actionable_players = [
                        p for p in snapshot.players 
                        if p.is_active and p.chips > 0
                    ]
                    
                    if len(actionable_players) == 0:
                        # 特殊情况：所有玩家都all-in，active_player_position可以为None
                        if snapshot.active_player_position is not None:
                            self._create_violation(
                                f"所有玩家都all-in时，活跃玩家位置应为None",
                                'WARNING',
                                {
                                    'active_player_position': snapshot.active_player_position,
                                    'all_players_all_in': True
                                }
                            )
                            # 这是警告而不是严重错误
                    else:
                        # 严重错误：指向了无法行动且非all-in的玩家
                        self._create_violation(
                            f"活跃玩家位置({snapshot.active_player_position})的玩家"
                            f"{active_player.name}不能行动且非all-in",
                            'CRITICAL',
                            {
                                'active_player_position': snapshot.active_player_position,
                                'player_id': active_player.player_id,
                                'player_name': active_player.name,
                                'is_active': active_player.is_active,
                                'chips': active_player.chips,
                                'is_all_in': active_player.is_all_in,
                                'actionable_players_count': len(actionable_players)
                            }
                        )
                        all_valid = False
        
        return all_valid
    
    def _check_pot_consistency(self, snapshot: GameStateSnapshot) -> bool:
        """检查奖池状态与阶段匹配
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        all_valid = True
        
        # 检查奖池的基本一致性
        if snapshot.pot.total_pot < snapshot.pot.main_pot:
            self._create_violation(
                f"总奖池({snapshot.pot.total_pot})小于主池({snapshot.pot.main_pot})",
                'CRITICAL',
                {
                    'total_pot': snapshot.pot.total_pot,
                    'main_pot': snapshot.pot.main_pot
                }
            )
            all_valid = False
        
        # 检查边池的合理性
        side_pots_total = sum(side_pot.get('amount', 0) for side_pot in snapshot.pot.side_pots)
        expected_total = snapshot.pot.main_pot + side_pots_total
        
        if abs(snapshot.pot.total_pot - expected_total) > 0.01:  # 允许小的浮点误差
            self._create_violation(
                f"奖池总额计算不一致: 总池{snapshot.pot.total_pot}, "
                f"主池+边池{expected_total}",
                'CRITICAL',
                {
                    'total_pot': snapshot.pot.total_pot,
                    'main_pot': snapshot.pot.main_pot,
                    'side_pots_total': side_pots_total,
                    'expected_total': expected_total,
                    'side_pots_count': len(snapshot.pot.side_pots)
                }
            )
            all_valid = False
        
        return all_valid
    
    def _check_betting_consistency(self, snapshot: GameStateSnapshot) -> bool:
        """检查下注状态与阶段匹配
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        all_valid = True
        
        # 在INIT阶段，不应该有下注
        if snapshot.phase == GamePhase.INIT:
            if snapshot.current_bet > 0:
                self._create_violation(
                    f"初始阶段不应该有下注: {snapshot.current_bet}",
                    'WARNING',
                    {
                        'phase': snapshot.phase.name,
                        'current_bet': snapshot.current_bet
                    }
                )
            
            # 检查玩家下注
            for player in snapshot.players:
                if player.current_bet > 0 or player.total_bet_this_hand > 0:
                    self._create_violation(
                        f"初始阶段玩家{player.name}不应该有下注: "
                        f"当前{player.current_bet}, 总计{player.total_bet_this_hand}",
                        'WARNING',
                        {
                            'phase': snapshot.phase.name,
                            'player_id': player.player_id,
                            'current_bet': player.current_bet,
                            'total_bet': player.total_bet_this_hand
                        }
                    )
        
        # 在FINISHED阶段，检查是否有合理的获胜者
        elif snapshot.phase == GamePhase.FINISHED:
            if snapshot.pot.total_pot > 0:
                # 如果还有奖池，应该有明确的获胜者信息
                # 这里可以添加更详细的获胜者检查逻辑
                pass
        
        return all_valid
    
    def check_phase_transition(self, from_phase: GamePhase, to_phase: GamePhase) -> bool:
        """检查阶段转换是否合法
        
        Args:
            from_phase: 源阶段
            to_phase: 目标阶段
            
        Returns:
            bool: 转换是否合法
        """
        valid_targets = self.valid_transitions.get(from_phase, set())
        
        if to_phase not in valid_targets:
            self._create_violation(
                f"非法的阶段转换: {from_phase.name} -> {to_phase.name}",
                'CRITICAL',
                {
                    'from_phase': from_phase.name,
                    'to_phase': to_phase.name,
                    'valid_targets': [phase.name for phase in valid_targets]
                }
            )
            return False
        
        return True 