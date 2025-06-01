"""德州扑克CLI输入处理模块.

这个模块负责处理用户输入，提供强校验和错误处理，
将用户输入转换为标准的ActionInput格式。
"""

import click
from typing import List, Tuple, Optional
from v2.core import ActionType, GameSnapshot, SeatStatus
from v2.controller import ActionInput


class CLIInputHandler:
    """CLI输入处理器.
    
    负责处理用户输入，提供强校验和错误处理。
    使用click库确保输入的有效性和用户体验。
    """
    
    @staticmethod
    def get_player_action(snapshot: GameSnapshot, player_id: int) -> ActionInput:
        """获取玩家行动输入.
        
        Args:
            snapshot: 当前游戏状态快照
            player_id: 玩家ID
            
        Returns:
            验证后的行动输入对象
            
        Raises:
            click.Abort: 用户取消输入
        """
        player = next(p for p in snapshot.players if p.seat_id == player_id)
        
        # 获取可用行动
        available_actions = CLIInputHandler._get_available_actions(player, snapshot)
        
        # 显示选项并获取选择
        click.echo(f"\n轮到 {player.name} 行动 (筹码: {player.chips})")
        click.echo("可用行动:")
        
        for i, (_, description, _) in enumerate(available_actions):
            click.echo(f"  {i + 1}. {description}")
        
        # 获取用户选择
        while True:
            try:
                choice = click.prompt(
                    "请选择行动",
                    type=click.IntRange(1, len(available_actions)),
                    show_choices=False
                )
                
                action_type, _, base_amount = available_actions[choice - 1]
                amount = base_amount
                
                # 如果是下注或加注，需要获取具体金额
                if action_type in [ActionType.BET, ActionType.RAISE]:
                    amount = CLIInputHandler._get_bet_amount(
                        action_type, snapshot, player
                    )
                
                return ActionInput(
                    player_id=player_id,
                    action_type=action_type,
                    amount=amount
                )
                
            except click.Abort:
                click.echo("用户取消操作")
                raise
            except Exception as e:
                click.echo(f"输入错误: {e}")
                click.echo("请重新选择")
    
    @staticmethod
    def get_continue_choice() -> bool:
        """获取是否继续游戏的选择.
        
        Returns:
            True表示继续，False表示退出
        """
        try:
            return click.confirm("是否继续下一手牌?", default=True)
        except click.Abort:
            return False
    
    @staticmethod
    def get_bet_amount_input(min_amount: int, max_amount: int, action_name: str) -> int:
        """获取下注金额输入.
        
        Args:
            min_amount: 最小金额
            max_amount: 最大金额  
            action_name: 行动名称（用于提示）
            
        Returns:
            验证后的下注金额
            
        Raises:
            click.Abort: 用户取消输入
        """
        prompt_text = f"请输入{action_name}金额 ({min_amount}-{max_amount})"
        
        return click.prompt(
            prompt_text,
            type=click.IntRange(min_amount, max_amount),
            show_choices=False
        )
    
    @staticmethod
    def _get_available_actions(player, snapshot: GameSnapshot) -> List[Tuple[ActionType, str, int]]:
        """获取玩家可用行动列表.
        
        Args:
            player: 玩家快照对象
            snapshot: 游戏状态快照
            
        Returns:
            可用行动列表 [(action_type, description, amount), ...]
        """
        actions = []
        
        # 弃牌 - 总是可用
        actions.append((ActionType.FOLD, "弃牌", 0))
        
        # 检查当前下注情况
        call_amount = snapshot.current_bet - player.current_bet
        
        if call_amount == 0:
            # 没有需要跟注的金额
            actions.append((ActionType.CHECK, "过牌", 0))
            
            # 可以下注
            if player.chips > 0:
                min_bet = snapshot.big_blind if hasattr(snapshot, 'big_blind') else 10
                if player.chips >= min_bet:
                    actions.append((ActionType.BET, f"下注 (最少 {min_bet})", min_bet))
                
                # 全押
                actions.append((ActionType.ALL_IN, f"全押 ({player.chips})", player.chips))
        else:
            # 需要跟注
            if player.chips >= call_amount:
                actions.append((ActionType.CALL, f"跟注 ({call_amount})", call_amount))
                
                # 可以加注
                min_raise = call_amount + (snapshot.last_raise_amount or snapshot.big_blind if hasattr(snapshot, 'big_blind') else 10)
                if player.chips > call_amount and player.chips >= min_raise:
                    actions.append((ActionType.RAISE, f"加注 (最少到 {min_raise})", min_raise))
            
            # 全押
            if player.chips > 0:
                actions.append((ActionType.ALL_IN, f"全押 ({player.chips})", player.chips))
        
        return actions
    
    @staticmethod
    def _get_bet_amount(action_type: ActionType, snapshot: GameSnapshot, player) -> int:
        """获取下注/加注的具体金额.
        
        Args:
            action_type: 行动类型
            snapshot: 游戏状态快照
            player: 玩家快照对象
            
        Returns:
            验证后的下注金额
            
        Raises:
            click.Abort: 用户取消输入
        """
        if action_type == ActionType.BET:
            min_amount = snapshot.big_blind if hasattr(snapshot, 'big_blind') else 10
            max_amount = player.chips
            action_name = "下注"
        elif action_type == ActionType.RAISE:
            call_amount = snapshot.current_bet - player.current_bet
            min_raise_amount = snapshot.last_raise_amount or (snapshot.big_blind if hasattr(snapshot, 'big_blind') else 10)
            min_amount = snapshot.current_bet + min_raise_amount
            max_amount = player.chips + player.current_bet
            action_name = "加注到"
        else:
            raise ValueError(f"不支持的行动类型: {action_type}")
        
        # 确保最小金额不超过玩家筹码
        min_amount = min(min_amount, max_amount)
        
        while True:
            try:
                amount = CLIInputHandler.get_bet_amount_input(
                    min_amount, max_amount, action_name
                )
                
                # 对于加注，返回总下注金额
                if action_type == ActionType.RAISE:
                    return amount
                else:
                    return amount
                    
            except click.Abort:
                # 用户取消，询问是否改为其他行动
                if click.confirm("取消下注，是否改为过牌/跟注?", default=True):
                    if snapshot.current_bet == player.current_bet:
                        return 0  # CHECK
                    else:
                        return snapshot.current_bet - player.current_bet  # CALL
                else:
                    raise
            except Exception as e:
                click.echo(f"输入错误: {e}")
                click.echo("请重新输入")


class InputValidationError(Exception):
    """输入验证错误."""
    
    pass 