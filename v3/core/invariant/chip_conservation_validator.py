"""
筹码守恒验证器

在游戏流程的关键点进行严格的筹码守恒检查。
"""

from typing import Dict, Any, List, Optional
from ..state_machine.types import GameContext, GamePhase

__all__ = ['ChipConservationValidator']


class ChipConservationValidator:
    """筹码守恒验证器
    
    在游戏流程的关键点进行严格的筹码守恒检查，
    确保奖池与玩家下注始终保持一致。
    """
    
    @staticmethod
    def validate_pot_consistency(ctx: GameContext, operation_name: str = "未知操作") -> None:
        """验证奖池与玩家下注的一致性
        
        Args:
            ctx: 游戏上下文
            operation_name: 操作名称，用于错误报告
            
        Raises:
            ValueError: 当筹码守恒被违反时
        """
        # 计算所有玩家的总下注
        total_bets = sum(player.get('total_bet_this_hand', 0) for player in ctx.players.values())
        
        # 在SHOWDOWN和FINISHED阶段，奖池可能已经被分配，跳过检查
        if ctx.current_phase in [GamePhase.SHOWDOWN, GamePhase.FINISHED]:
            return
        
        # 严格验证奖池与总下注的一致性
        if ctx.pot_total != total_bets:
            ChipConservationValidator._raise_conservation_error(
                ctx, total_bets, operation_name
            )
    
    @staticmethod
    def validate_player_bet_consistency(ctx: GameContext, player_id: str, operation_name: str = "未知操作") -> None:
        """验证单个玩家的下注一致性
        
        Args:
            ctx: 游戏上下文
            player_id: 玩家ID
            operation_name: 操作名称，用于错误报告
            
        Raises:
            ValueError: 当玩家下注不一致时
        """
        if player_id not in ctx.players:
            raise ValueError(f"玩家 {player_id} 不存在")
        
        player = ctx.players[player_id]
        current_bet = player.get('current_bet', 0)
        total_bet = player.get('total_bet_this_hand', 0)
        chips = player.get('chips', 0)
        
        # 验证下注金额非负
        if current_bet < 0:
            raise ValueError(
                f"{operation_name}: 玩家 {player_id} 的当前下注为负数: {current_bet}"
            )
        
        if total_bet < 0:
            raise ValueError(
                f"{operation_name}: 玩家 {player_id} 的本手牌总下注为负数: {total_bet}"
            )
        
        if chips < 0:
            raise ValueError(
                f"{operation_name}: 玩家 {player_id} 的筹码为负数: {chips}"
            )
        
        # 验证total_bet_this_hand >= current_bet（在大多数情况下）
        # 注意：在某些阶段重置后，current_bet可能被重置为0
        if ctx.current_phase == GamePhase.PRE_FLOP and total_bet < current_bet:
            raise ValueError(
                f"{operation_name}: 玩家 {player_id} 的本手牌总下注({total_bet}) < 当前下注({current_bet})"
            )
    
    @staticmethod
    def validate_betting_action(
        ctx: GameContext, 
        player_id: str, 
        action_type: str, 
        amount: int,
        operation_name: str = "下注行动"
    ) -> None:
        """验证下注行动的有效性
        
        Args:
            ctx: 游戏上下文
            player_id: 玩家ID
            action_type: 行动类型
            amount: 下注金额
            operation_name: 操作名称，用于错误报告
            
        Raises:
            ValueError: 当下注行动无效时
        """
        if player_id not in ctx.players:
            raise ValueError(f"{operation_name}: 玩家 {player_id} 不存在")
        
        player = ctx.players[player_id]
        chips = player.get('chips', 0)
        
        # 验证下注金额
        if amount < 0:
            raise ValueError(f"{operation_name}: 下注金额不能为负数: {amount}")
        
        # 验证玩家有足够的筹码
        if amount > chips:
            raise ValueError(
                f"{operation_name}: 玩家 {player_id} 筹码不足，需要 {amount}，只有 {chips}"
            )
    
    @staticmethod
    def validate_total_chip_conservation(
        ctx: GameContext, 
        initial_total_chips: int,
        operation_name: str = "总筹码守恒检查"
    ) -> None:
        """验证总筹码守恒
        
        Args:
            ctx: 游戏上下文
            initial_total_chips: 初始总筹码数量
            operation_name: 操作名称，用于错误报告
            
        Raises:
            ValueError: 当总筹码不守恒时
        """
        # 计算当前总筹码
        current_player_chips = sum(player.get('chips', 0) for player in ctx.players.values())
        current_total = current_player_chips + ctx.pot_total
        
        if current_total != initial_total_chips:
            player_details = {
                player_id: {
                    'chips': player.get('chips', 0),
                    'total_bet_this_hand': player.get('total_bet_this_hand', 0)
                }
                for player_id, player in ctx.players.items()
            }
            
            error_msg = (
                f"{operation_name}: 总筹码不守恒\n"
                f"初始总筹码: {initial_total_chips}\n"
                f"当前玩家筹码: {current_player_chips}\n"
                f"当前奖池: {ctx.pot_total}\n"
                f"当前总筹码: {current_total}\n"
                f"差额: {current_total - initial_total_chips}\n"
                f"玩家详情: {player_details}"
            )
            
            raise ValueError(error_msg)
    
    @staticmethod
    def _raise_conservation_error(ctx: GameContext, total_bets: int, operation_name: str) -> None:
        """抛出筹码守恒错误
        
        Args:
            ctx: 游戏上下文
            total_bets: 玩家总下注
            operation_name: 操作名称
            
        Raises:
            ValueError: 筹码守恒错误
        """
        # 收集详细的调试信息
        player_bets_detail = {
            player_id: {
                'total_bet_this_hand': player.get('total_bet_this_hand', 0),
                'current_bet': player.get('current_bet', 0),
                'chips': player.get('chips', 0),
                'status': player.get('status', 'unknown')
            }
            for player_id, player in ctx.players.items()
        }
        
        error_msg = (
            f"{operation_name}: 筹码守恒违规\n"
            f"奖池总额: {ctx.pot_total}\n"
            f"玩家总下注: {total_bets}\n"
            f"差额: {ctx.pot_total - total_bets}\n"
            f"当前阶段: {ctx.current_phase}\n"
            f"玩家下注详情: {player_bets_detail}"
        )
        
        raise ValueError(error_msg) 