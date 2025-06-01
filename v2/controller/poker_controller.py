"""
德州扑克游戏控制器 v2.

这个模块提供了德州扑克游戏的主要控制逻辑，作为核心逻辑层和UI层之间的桥梁。
控制器负责协调游戏状态、玩家行动、AI策略和事件处理。
"""

import logging
from typing import Optional, Protocol, runtime_checkable
from dataclasses import dataclass

from ..core import (
    GameState, GameSnapshot, Player, Action, ActionType, 
    ActionValidator, ValidationResultData, Phase, SeatStatus
)


@runtime_checkable
class AIStrategy(Protocol):
    """AI策略接口协议.
    
    定义AI玩家决策的标准接口，所有AI实现都应该遵循这个协议。
    """
    
    def decide(self, game_snapshot: GameSnapshot, player_id: int) -> Action:
        """根据游戏状态快照决定下一步行动.
        
        Args:
            game_snapshot: 当前游戏状态的不可变快照
            player_id: 需要做决策的玩家ID
            
        Returns:
            玩家决定的行动
            
        Raises:
            ValueError: 如果玩家ID无效或游戏状态不允许该玩家行动
        """
        ...


@dataclass(frozen=True)
class HandResult:
    """手牌结束结果.
    
    包含一手牌结束后的所有相关信息，用于统计和显示。
    
    Attributes:
        winner_ids: 获胜玩家ID列表
        pot_amount: 底池总金额
        winning_hand_description: 获胜牌型描述
        side_pots: 边池分配信息
    """
    
    winner_ids: list[int]
    pot_amount: int
    winning_hand_description: str
    side_pots: list[dict]


class PokerController:
    """德州扑克游戏控制器.
    
    这个类是游戏的主要控制器，负责：
    - 管理游戏状态和生命周期
    - 处理玩家行动和AI决策
    - 协调各个游戏阶段的转换
    - 提供游戏状态快照给UI层
    - 记录游戏事件和日志
    
    控制器采用依赖注入设计，支持自定义AI策略和日志记录器。
    """
    
    def __init__(
        self, 
        game_state: Optional[GameState] = None,
        ai_strategy: Optional[AIStrategy] = None,
        logger: Optional[logging.Logger] = None
    ):
        """初始化控制器.
        
        Args:
            game_state: 游戏状态对象，如果为None则创建默认状态
            ai_strategy: AI策略实现，如果为None则使用默认策略
            logger: 日志记录器，如果为None则创建默认记录器
        """
        self._game_state = game_state or GameState()
        self._ai_strategy = ai_strategy
        self._logger = logger or logging.getLogger(__name__)
        self._validator = ActionValidator()
        self._hand_in_progress = False
        
    def start_new_hand(self) -> bool:
        """开始新的一手牌.
        
        初始化新手牌的所有必要状态，包括：
        - 重置玩家状态
        - 发放底牌
        - 收取盲注
        - 设置第一个行动玩家
        
        Returns:
            是否成功开始新手牌
            
        Raises:
            RuntimeError: 如果当前已有手牌在进行中
        """
        if self._hand_in_progress:
            raise RuntimeError("当前已有手牌在进行中，无法开始新手牌")
            
        # 检查是否有足够的活跃玩家
        active_players = [p for p in self._game_state.players if p.status == SeatStatus.ACTIVE and p.chips > 0]
        if len(active_players) < 2:
            self._logger.info("活跃玩家不足2人，无法开始新手牌")
            return False
            
        # 重置游戏状态为新手牌
        self._reset_for_new_hand()
        self._hand_in_progress = True
        
        self._logger.info(f"开始新手牌，活跃玩家数: {len(active_players)}")
        return True
        
    def execute_action(self, action: Action) -> bool:
        """执行玩家行动.
        
        验证并执行玩家的行动，更新游戏状态。
        
        Args:
            action: 玩家要执行的行动
            
        Returns:
            是否成功执行行动
            
        Raises:
            ValueError: 如果行动无效
        """
        if not self._hand_in_progress:
            raise RuntimeError("当前没有手牌在进行中")
            
        # 验证行动
        validated_action = self._validator.validate_action(self._game_state, action)
        
        if not validated_action.validation_result.is_valid:
            error_msg = validated_action.validation_result.error_message or "行动无效"
            self._logger.warning(f"行动验证失败: {error_msg}")
            raise ValueError(error_msg)
            
        # 执行验证后的行动
        final_action = validated_action.final_action
        self._apply_action(final_action)
        
        self._logger.info(f"玩家{final_action.player_id}执行行动: {final_action.action_type.value}")
        
        # 检查是否需要进入下一阶段或结束手牌
        self._check_phase_transition()
        
        return True
        
    def get_snapshot(self) -> GameSnapshot:
        """获取当前游戏状态的不可变快照.
        
        Returns:
            当前游戏状态的快照，可以安全地传递给UI层
        """
        return self._game_state.create_snapshot()
        
    def is_hand_over(self) -> bool:
        """检查当前手牌是否已结束.
        
        Returns:
            当前手牌是否已结束
        """
        if not self._hand_in_progress:
            return True
            
        # 检查是否只剩一个活跃玩家
        active_players = [
            p for p in self._game_state.players 
            if p.status in [SeatStatus.ACTIVE, SeatStatus.ALL_IN]
        ]
        
        if len(active_players) <= 1:
            return True
            
        # 检查是否已到摊牌阶段且所有行动完成
        if (self._game_state.phase == Phase.SHOWDOWN or 
            self._game_state.phase == Phase.RIVER and self._all_actions_complete()):
            return True
            
        return False
        
    def get_current_player_id(self) -> Optional[int]:
        """获取当前需要行动的玩家ID.
        
        Returns:
            当前玩家ID，如果没有玩家需要行动则返回None
        """
        if not self._hand_in_progress or self.is_hand_over():
            return None
            
        return self._game_state.current_player
        
    def process_ai_action(self) -> bool:
        """处理AI玩家的自动行动.
        
        如果当前玩家是AI，则自动获取AI决策并执行。
        
        Returns:
            是否成功处理AI行动
        """
        current_player_id = self.get_current_player_id()
        if current_player_id is None:
            return False
            
        if self._ai_strategy is None:
            self._logger.warning("没有配置AI策略，无法处理AI行动")
            return False
            
        try:
            snapshot = self.get_snapshot()
            ai_action = self._ai_strategy.decide(snapshot, current_player_id)
            return self.execute_action(ai_action)
        except Exception as e:
            self._logger.error(f"AI行动处理失败: {e}")
            return False
            
    def end_hand(self) -> Optional[HandResult]:
        """结束当前手牌并计算结果.
        
        Returns:
            手牌结果，如果没有手牌在进行中则返回None
        """
        if not self._hand_in_progress:
            return None
            
        # TODO: 实现手牌结算逻辑
        # 这里需要实现牌型比较、边池分配等逻辑
        
        self._hand_in_progress = False
        self._logger.info("手牌结束")
        
        # 临时返回空结果
        return HandResult(
            winner_ids=[],
            pot_amount=self._game_state.pot,
            winning_hand_description="",
            side_pots=[]
        )
        
    def _reset_for_new_hand(self) -> None:
        """重置游戏状态为新手牌."""
        # 重置阶段
        self._game_state.phase = Phase.PRE_FLOP
        
        # 清空公共牌
        self._game_state.community_cards.clear()
        
        # 重置下注状态
        self._game_state.reset_betting_round()
        
        # 初始化牌堆并发牌
        self._game_state.initialize_deck()
        self._game_state.deal_hole_cards()
        
        # 设置盲注和第一个行动玩家
        self._post_blinds()
        self._set_first_player()
        
        self._game_state.add_event("新手牌开始")
        
    def _post_blinds(self) -> None:
        """收取盲注."""
        players = self._game_state.players
        if len(players) < 2:
            return
            
        # 找到小盲和大盲位置
        dealer_pos = self._game_state.dealer_position
        small_blind_pos = (dealer_pos + 1) % len(players)
        big_blind_pos = (dealer_pos + 2) % len(players)
        
        # 收取小盲注
        small_blind_player = players[small_blind_pos]
        if small_blind_player.chips >= self._game_state.small_blind:
            small_blind_player.bet(self._game_state.small_blind)
            small_blind_player.is_small_blind = True
            self._game_state.add_event(f"{small_blind_player.name} 下小盲注 {self._game_state.small_blind}")
        
        # 收取大盲注
        big_blind_player = players[big_blind_pos]
        if big_blind_player.chips >= self._game_state.big_blind:
            big_blind_player.bet(self._game_state.big_blind)
            big_blind_player.is_big_blind = True
            self._game_state.current_bet = self._game_state.big_blind
            self._game_state.add_event(f"{big_blind_player.name} 下大盲注 {self._game_state.big_blind}")
            
    def _set_first_player(self) -> None:
        """设置第一个行动玩家."""
        players = self._game_state.players
        if len(players) < 3:
            # 如果只有两个玩家，小盲先行动
            self._game_state.current_player = (self._game_state.dealer_position + 1) % len(players)
        else:
            # 如果有三个或更多玩家，大盲后面的玩家先行动
            self._game_state.current_player = (self._game_state.dealer_position + 3) % len(players)
            
    def _apply_action(self, action: Action) -> None:
        """应用玩家行动到游戏状态."""
        player = self._game_state.get_player_by_seat(action.player_id)
        if player is None:
            raise ValueError(f"找不到玩家 {action.player_id}")
            
        if action.action_type == ActionType.FOLD:
            player.status = SeatStatus.FOLDED
            self._game_state.add_event(f"{player.name} 弃牌")
            
        elif action.action_type == ActionType.CHECK:
            self._game_state.add_event(f"{player.name} 过牌")
            
        elif action.action_type == ActionType.CALL:
            call_amount = self._game_state.current_bet - player.current_bet
            if call_amount > 0:
                player.bet(call_amount)
                self._game_state.add_event(f"{player.name} 跟注 {call_amount}")
            else:
                self._game_state.add_event(f"{player.name} 过牌")
                
        elif action.action_type == ActionType.BET:
            player.bet(action.amount)
            self._game_state.current_bet = action.amount
            self._game_state.last_raiser = action.player_id
            self._game_state.add_event(f"{player.name} 下注 {action.amount}")
            
        elif action.action_type == ActionType.RAISE:
            total_bet = self._game_state.current_bet + action.amount
            bet_amount = total_bet - player.current_bet
            player.bet(bet_amount)
            self._game_state.current_bet = total_bet
            self._game_state.last_raiser = action.player_id
            self._game_state.last_raise_amount = action.amount
            self._game_state.add_event(f"{player.name} 加注到 {total_bet}")
            
        elif action.action_type == ActionType.ALL_IN:
            all_in_amount = player.chips
            player.bet(all_in_amount)
            player.status = SeatStatus.ALL_IN
            if player.current_bet > self._game_state.current_bet:
                self._game_state.current_bet = player.current_bet
                self._game_state.last_raiser = action.player_id
            self._game_state.add_event(f"{player.name} 全押 {all_in_amount}")
            
        # 移动到下一个玩家
        self._advance_to_next_player()
        
    def _advance_to_next_player(self) -> None:
        """移动到下一个需要行动的玩家."""
        if self._game_state.current_player is None:
            return
            
        players = self._game_state.players
        start_pos = self._game_state.current_player
        
        # 寻找下一个可以行动的玩家
        for i in range(1, len(players) + 1):
            next_pos = (start_pos + i) % len(players)
            next_player = players[next_pos]
            
            if next_player.status == SeatStatus.ACTIVE:
                self._game_state.current_player = next_pos
                return
                
        # 如果没有找到活跃玩家，设置为None
        self._game_state.current_player = None
        
    def _check_phase_transition(self) -> None:
        """检查并处理游戏阶段转换."""
        if self._all_actions_complete():
            self._advance_to_next_phase()
            
    def _all_actions_complete(self) -> bool:
        """检查当前阶段是否所有行动都已完成."""
        active_players = self._game_state.get_active_players()
        
        # 如果没有活跃玩家，行动完成
        if not active_players:
            return True
            
        # 检查是否所有活跃玩家都已匹配当前下注
        for player in active_players:
            if player.current_bet < self._game_state.current_bet:
                return False
                
        return True
        
    def _advance_to_next_phase(self) -> None:
        """推进到下一个游戏阶段."""
        # 收集当前轮的下注到底池
        self._game_state.collect_bets_to_pot()
        
        # 推进阶段
        if self._game_state.phase == Phase.PRE_FLOP:
            self._game_state.advance_phase()  # 到FLOP
            self._game_state.deal_community_cards(3)
        elif self._game_state.phase == Phase.FLOP:
            self._game_state.advance_phase()  # 到TURN
            self._game_state.deal_community_cards(1)
        elif self._game_state.phase == Phase.TURN:
            self._game_state.advance_phase()  # 到RIVER
            self._game_state.deal_community_cards(1)
        elif self._game_state.phase == Phase.RIVER:
            self._game_state.advance_phase()  # 到SHOWDOWN
            
        # 重置下注轮并设置第一个行动玩家
        if self._game_state.phase != Phase.SHOWDOWN:
            self._game_state.reset_betting_round()
            self._set_first_player_for_new_round()
            
    def _set_first_player_for_new_round(self) -> None:
        """为新的下注轮设置第一个行动玩家."""
        # 从庄家后面开始找第一个活跃玩家
        players = self._game_state.players
        dealer_pos = self._game_state.dealer_position
        
        for i in range(1, len(players) + 1):
            pos = (dealer_pos + i) % len(players)
            player = players[pos]
            if player.status == SeatStatus.ACTIVE:
                self._game_state.current_player = pos
                return
                
        self._game_state.current_player = None 