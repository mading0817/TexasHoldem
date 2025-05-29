"""
游戏阶段抽象基类
定义每个游戏阶段的标准生命周期接口
"""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING, Callable, List, Any

if TYPE_CHECKING:
    from ..game_state import GameState
    from ..action_validator import ValidatedAction


class BasePhase(ABC):
    """
    游戏阶段抽象基类
    每个具体阶段(PreFlop, Flop, Turn, River, Showdown)都继承此类
    """
    
    def __init__(self, state: 'GameState'):
        """
        初始化阶段
        
        Args:
            state: 游戏状态对象
        """
        self.state = state
    
    @abstractmethod
    def enter(self):
        """
        进入阶段时的一次性操作
        例如：发牌、设置盲注、重置下注轮等
        """
        pass
    
    @abstractmethod
    def act(self, action: 'ValidatedAction') -> bool:
        """
        处理玩家行动
        
        Args:
            action: 经过验证的玩家行动
            
        Returns:
            True如果下注轮继续，False如果下注轮结束
        """
        pass
    
    @abstractmethod
    def process_betting_round(self, get_player_action_callback: Callable[[int], Any]) -> List[str]:
        """
        处理整个下注轮的核心业务逻辑
        各个阶段可以有不同的下注轮处理策略
        
        Args:
            get_player_action_callback: 获取玩家行动的回调函数
        
        Returns:
            产生的事件列表
        """
        pass
    
    @abstractmethod
    def exit(self) -> Optional['BasePhase']:
        """
        退出当前阶段时的清理操作
        
        Returns:
            下一个阶段的实例，如果游戏结束则返回None
        """
        pass
    
    def is_round_complete(self) -> bool:
        """
        检查当前下注轮是否完成
        复用GameState现有逻辑
        
        Returns:
            True如果下注轮完成
        """
        return self.state.is_betting_round_complete()
    
    def advance_player(self) -> bool:
        """
        推进到下一个玩家
        复用GameState现有逻辑
        
        Returns:
            True如果成功推进
        """
        return self.state.advance_current_player()
    
    def execute_action(self, player, action: 'ValidatedAction'):
        """
        执行玩家行动的通用方法
        所有阶段都复用此方法，减少代码重复
        
        Args:
            player: 执行行动的玩家
            action: 经过验证的玩家行动
        """
        from ..core.enums import ActionType
        
        if action.actual_action_type == ActionType.FOLD:
            player.fold()
        
        elif action.actual_action_type == ActionType.CHECK:
            # 过牌不需要额外操作
            pass
        
        elif action.actual_action_type == ActionType.CALL:
            # 跟注
            call_amount = max(0, self.state.current_bet - player.current_bet)
            player.bet(call_amount)
        
        elif action.actual_action_type == ActionType.BET:
            # 下注
            previous_current_bet = self.state.current_bet # Should be 0 for a BET
            player.bet(action.actual_amount)
            self.state.current_bet = player.current_bet
            self.state.last_raiser = player.seat_id
            self.state.last_raise_amount = action.actual_amount - previous_current_bet # Amount of this bet/raise
        
        elif action.actual_action_type == ActionType.RAISE:
            # 加注
            previous_current_bet_on_street = self.state.current_bet
            call_amount = max(0, previous_current_bet_on_street - player.current_bet)
            # total_needed is the amount of chips player must add to their current_bet on street to reach action.actual_amount
            # action.actual_amount is the new total bet for the player for this street.
            # The amount of chips to physically add from their stack:
            chips_to_add = action.actual_amount - player.current_bet
            player.bet(chips_to_add)
            
            self.state.current_bet = action.actual_amount # New highest bet on the table
            self.state.last_raiser = player.seat_id
            self.state.last_raise_amount = action.actual_amount - previous_current_bet_on_street # Amount of this raise increment
        
        elif action.actual_action_type == ActionType.ALL_IN:
            # 全押
            previous_current_bet_on_street = self.state.current_bet
            amount_all_in = player.chips # The amount of chips player is adding to their current bet
            player.bet(amount_all_in)
            # player.current_bet is now their total bet for the street after going all-in
            
            if player.current_bet > previous_current_bet_on_street:
                self.state.current_bet = player.current_bet
                self.state.last_raiser = player.seat_id
                self.state.last_raise_amount = player.current_bet - previous_current_bet_on_street # Amount of this all-in raise increment
            # If all-in is just a call or less, last_raise_amount is not updated by this player.
        
        # 记录玩家的最后行动类型
        player.last_action_type = action.actual_action_type
        
        # 增加行动计数
        self.state.street_index += 1
    
    def process_standard_action(self, action: 'ValidatedAction') -> bool:
        """
        处理标准玩家行动的通用流程
        适用于除摊牌外的所有阶段
        
        Args:
            action: 经过验证的玩家行动
            
        Returns:
            True如果下注轮继续，False如果下注轮结束
        """
        player = self.state.get_player_by_seat(action.player_seat)
        if not player:
            raise ValueError(f"找不到座位{action.player_seat}的玩家")
        
        # 执行行动
        self.execute_action(player, action)
        
        # 记录事件
        self.state.add_event(f"{player.name} {action}")
        
        # 推进到下一个玩家
        if not self.state.advance_current_player():
            # 没有更多玩家可行动，下注轮结束
            return False
        
        # 检查下注轮是否完成
        if self.state.is_betting_round_complete():
            return False
        
        return True
    
    def standard_exit_to_next_phase(self, next_phase_class, phase_name: str):
        """
        标准的阶段退出流程
        适用于除摊牌外的所有阶段
        
        Args:
            next_phase_class: 下一阶段的类
            phase_name: 当前阶段的名称（用于日志）
            
        Returns:
            下一个阶段的实例
        """
        # 收集所有下注到底池
        self.state.collect_bets_to_pot()
        
        # 推进游戏阶段
        self.state.advance_phase()
        
        # 记录事件
        self.state.add_event(f"{phase_name}结束，底池: {self.state.pot}")
        
        # 检查是否只剩一个玩家（其他都弃牌了）
        players_in_hand = self.state.get_players_in_hand()
        if len(players_in_hand) <= 1:
            # 直接进入摊牌阶段
            from .showdown import ShowdownPhase
            self.state.phase = next_phase_class._phase_enum_value
            return ShowdownPhase(self.state)
        
        # 正常进入下一阶段
        return next_phase_class(self.state)

    def _standard_process_betting_round(self, get_player_action_callback: Callable[[int], Any], max_actions_multiplier: int = 4) -> List[str]:
        """
        标准下注轮处理逻辑
        大部分阶段可以直接使用这个通用实现
        
        Args:
            get_player_action_callback: 获取玩家行动的回调函数
            max_actions_multiplier: 最大行动数的倍数（防护栏）
        
        Returns:
            产生的事件列表
        """
        from ..core.enums import ActionType, SeatStatus
        from ..betting.action_validator import ActionValidator
        
        events = []
        action_count = 0
        max_actions = len(self.state.players) * max_actions_multiplier  # 防护栏
        validator = ActionValidator()
        
        while not self.state.is_betting_round_complete() and action_count < max_actions:
            current_seat = self.state.current_player
            
            if current_seat is None:
                break
            
            current_player = self.state.get_player_by_seat(current_seat)
            if not current_player or current_player.status not in [SeatStatus.ACTIVE]:
                if not self.state.advance_current_player():
                    break
                continue
            
            try:
                # 通过回调获取玩家行动输入
                action_input = get_player_action_callback(current_seat)
                
                # 创建基础行动对象
                from ..core.enums import Action
                action = Action(
                    action_type=action_input.action_type,
                    amount=action_input.amount or 0,
                    player_seat=current_seat
                )
                
                # 验证行动
                validated_action = validator.validate(self.state, current_player, action)
                
                # 执行行动（使用现有的act方法）
                continue_round = self.act(validated_action)
                
                events.append(f"玩家 {current_player.name} 执行了 {validated_action}")
                action_count += 1
                
                if not continue_round:
                    break
                    
            except Exception as e:
                # 处理异常：如果是AI玩家，强制弃牌；如果是人类玩家，重新抛出
                if current_seat != 0:  # 假设0是人类玩家
                    try:
                        # 创建弃牌行动
                        from ..core.enums import Action
                        fold_action = Action(
                            action_type=ActionType.FOLD,
                            amount=0,
                            player_seat=current_seat
                        )
                        validated_fold = validator.validate(self.state, current_player, fold_action)
                        self.act(validated_fold)
                        
                        events.append(f"玩家 {current_player.name} 因异常强制弃牌: {str(e)}")
                        action_count += 1
                    except:
                        break
                else:
                    # 人类玩家的异常向外抛出
                    raise
        
        if action_count >= max_actions:
            events.append("达到最大行动数限制，强制结束下注轮")
        
        return events