"""
德州扑克游戏控制器 v2.

这个模块提供了德州扑克游戏的主要控制逻辑，作为核心逻辑层和UI层之间的桥梁。
控制器负责协调游戏状态、玩家行动、AI策略和事件处理。
"""

import logging
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from ..core import (
    GameState, GameSnapshot, Player, Action, ActionType, 
    ActionValidator, ValidationResultData, Phase, SeatStatus,
    EventType, EventBus, get_event_bus, Card, Suit, Rank
)
from ..ai import AIStrategy
from .decorators import atomic


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
    
    winner_ids: List[int]
    pot_amount: int
    winning_hand_description: str
    side_pots: List[dict]


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
        logger: Optional[logging.Logger] = None,
        event_bus: Optional[EventBus] = None
    ):
        """初始化控制器.
        
        Args:
            game_state: 游戏状态对象，如果为None则创建默认状态
            ai_strategy: AI策略实现，如果为None则使用默认策略
            logger: 日志记录器，如果为None则创建默认记录器
            event_bus: 事件总线，如果为None则使用全局事件总线
        """
        self._game_state = game_state or GameState()
        self._ai_strategy = ai_strategy
        self._logger = logger or logging.getLogger(__name__)
        self._event_bus = event_bus or get_event_bus()
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
            
        # 预先重置游戏状态，以便正确检查活跃玩家
        self._advance_dealer_position()
        
        # 重置所有玩家状态为新手牌
        for player in self._game_state.players:
            player.reset_for_new_hand()
            player.is_dealer = False
            player.is_small_blind = False
            player.is_big_blind = False
            player.total_bet_this_hand = 0
        
        # 设置庄家标记
        if self._game_state.players:
            dealer_player = self._game_state.get_player_by_seat(self._game_state.dealer_position)
            if dealer_player:
                dealer_player.is_dealer = True
        
        # 检查是否有足够的活跃玩家（重置后检查）
        active_players = [p for p in self._game_state.players if p.status == SeatStatus.ACTIVE and p.chips > 0]
        if len(active_players) < 2:
            self._logger.info("活跃玩家不足2人，无法开始新手牌")
            return False
            
        # 发射手牌开始事件
        self._event_bus.emit_simple(
            EventType.HAND_STARTED,
            active_players=len(active_players),
            dealer_position=self._game_state.dealer_position
        )
        
        # 完成其余的重置工作
        self._complete_hand_reset()
        self._hand_in_progress = True
        
        self._logger.info(f"开始新手牌，活跃玩家数: {len(active_players)}")
        return True
        
    @atomic
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
        player = self._game_state.get_player_by_seat(action.player_id)
        if player is None:
            raise ValueError(f"找不到玩家 {action.player_id}")
            
        validated_action = self._validator.validate(self._game_state, player, action)
        
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
            
        # 只有在SHOWDOWN阶段才认为手牌结束
        if self._game_state.phase == Phase.SHOWDOWN:
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
            
        # 收集所有下注到底池
        self._game_state.collect_bets_to_pot()
        
        # 获取所有未弃牌的玩家
        active_players = [
            p for p in self._game_state.players 
            if p.status in [SeatStatus.ACTIVE, SeatStatus.ALL_IN]
        ]
        
        if len(active_players) == 0:
            # 没有活跃玩家，这种情况不应该发生
            self._hand_in_progress = False
            self._logger.warning("手牌结束时没有活跃玩家")
            # 移除庄家位置移动 - 应该在下一手牌开始时移动
            return HandResult(
                winner_ids=[],
                pot_amount=self._game_state.pot,
                winning_hand_description="无活跃玩家",
                side_pots=[]
            )
        
        if len(active_players) == 1:
            # 只有一个玩家，直接获胜
            winner = active_players[0]
            winner.chips += self._game_state.pot
            
            result = HandResult(
                winner_ids=[winner.seat_id],
                pot_amount=self._game_state.pot,
                winning_hand_description=f"{winner.name} 获胜（其他玩家弃牌）",
                side_pots=[]
            )
            
            self._game_state.pot = 0  # 清空底池
            self._hand_in_progress = False
            self._logger.info(f"{winner.name} 获胜，获得底池 {result.pot_amount}")
            
            # 移除庄家位置移动 - 应该在下一手牌开始时移动
            
            # 发射手牌结束事件
            self._event_bus.emit_simple(
                EventType.HAND_ENDED,
                winner_ids=result.winner_ids,
                pot_amount=result.pot_amount,
                winning_hand_description=result.winning_hand_description,
                side_pots=result.side_pots
            )
            
            return result
        
        # 多个玩家，需要比较牌型
        from v2.core.evaluator import SimpleEvaluator
        evaluator = SimpleEvaluator()
        
        # 评估每个玩家的牌型
        player_hands = []
        for player in active_players:
            try:
                hand_result = evaluator.evaluate_hand(
                    player.hole_cards, 
                    self._game_state.community_cards
                )
                player_hands.append((player, hand_result))
                self._logger.info(f"{player.name} 的牌型: {hand_result}")
            except Exception as e:
                self._logger.error(f"评估玩家 {player.name} 牌型失败: {e}")
                # 如果评估失败，给予最低牌型
                from v2.core.evaluator import HandResult as EvalHandResult
                from v2.core.enums import HandRank
                hand_result = EvalHandResult(HandRank.HIGH_CARD, 2)
                player_hands.append((player, hand_result))
        
        # 找出最佳牌型
        best_hand = max(player_hands, key=lambda x: (x[1].rank.value, x[1].primary_value, x[1].secondary_value, x[1].kickers))
        best_hand_result = best_hand[1]
        
        # 找出所有拥有最佳牌型的玩家（可能平局）
        winners = []
        for player, hand_result in player_hands:
            if hand_result.compare_to(best_hand_result) == 0:
                winners.append(player)
        
        # 分配底池
        pot_per_winner = self._game_state.pot // len(winners)
        remainder = self._game_state.pot % len(winners)
        
        winner_ids = []
        for i, winner in enumerate(winners):
            share = pot_per_winner
            if i < remainder:  # 余数分配给前几个获胜者
                share += 1
            winner.chips += share
            winner_ids.append(winner.seat_id)
            self._logger.info(f"{winner.name} 获得 {share} 筹码")
        
        # 构建获胜描述
        if len(winners) == 1:
            winning_description = f"{winners[0].name} 获胜 - {best_hand_result}"
        else:
            winner_names = [w.name for w in winners]
            winning_description = f"平局: {', '.join(winner_names)} - {best_hand_result}"
        
        result = HandResult(
            winner_ids=winner_ids,
            pot_amount=self._game_state.pot,
            winning_hand_description=winning_description,
            side_pots=[]  # TODO: 实现边池逻辑
        )
        
        # 清空底池
        self._game_state.pot = 0
        self._hand_in_progress = False
        self._logger.info(f"手牌结束: {winning_description}")
        
        # 移除庄家位置移动 - 应该在下一手牌开始时移动
        
        # 发射手牌结束事件
        self._event_bus.emit_simple(
            EventType.HAND_ENDED,
            winner_ids=result.winner_ids,
            pot_amount=result.pot_amount,
            winning_hand_description=result.winning_hand_description,
            side_pots=result.side_pots
        )
        
        return result
        
    def _complete_hand_reset(self) -> None:
        """完成手牌重置的剩余工作."""
        # 重置阶段
        self._game_state.phase = Phase.PRE_FLOP
        
        # 清空公共牌
        self._game_state.community_cards.clear()
        
        # 重置下注状态
        self._game_state.reset_betting_round()
        
        # 重置底池（在收集下注后应该已经为0）
        self._game_state.pot = 0
        
        # 初始化牌堆并发牌
        self._game_state.initialize_deck()
        self._game_state.deal_hole_cards()
        
        # 设置盲注和第一个行动玩家
        self._post_blinds()
        self._set_first_player()
        
        self._game_state.add_event("新手牌开始")
        
    def _reset_for_new_hand(self) -> None:
        """重置游戏状态为新手牌（已弃用，保留向后兼容）."""
        # 移动庄家位置
        self._advance_dealer_position()
        
        # 重置所有玩家状态为新手牌
        for player in self._game_state.players:
            # 使用Player的重置方法
            player.reset_for_new_hand()
            
            # 重置位置标记
            player.is_dealer = False
            player.is_small_blind = False
            player.is_big_blind = False
            
            # 重置hand统计
            player.total_bet_this_hand = 0
        
        # 设置庄家标记
        if self._game_state.players:
            dealer_player = self._game_state.get_player_by_seat(self._game_state.dealer_position)
            if dealer_player:
                dealer_player.is_dealer = True
        
        # 重置阶段
        self._game_state.phase = Phase.PRE_FLOP
        
        # 清空公共牌
        self._game_state.community_cards.clear()
        
        # 重置下注状态
        self._game_state.reset_betting_round()
        
        # 重置底池（在收集下注后应该已经为0）
        self._game_state.pot = 0
        
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
            
        # 发射盲注事件
        self._event_bus.emit_simple(
            EventType.BLINDS_POSTED,
            small_blind_player_id=small_blind_pos,
            small_blind_amount=self._game_state.small_blind,
            big_blind_player_id=big_blind_pos,
            big_blind_amount=self._game_state.big_blind
        )
        
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
            # 发射玩家弃牌事件
            self._event_bus.emit_simple(
                EventType.PLAYER_FOLDED,
                player_id=action.player_id,
                player_name=player.name
            )
            
        elif action.action_type == ActionType.CHECK:
            self._game_state.add_event(f"{player.name} 过牌")
            # 发射玩家行动事件
            self._event_bus.emit_simple(
                EventType.PLAYER_ACTION,
                player_id=action.player_id,
                player_name=player.name,
                action_type="check",
                amount=0
            )
            
        elif action.action_type == ActionType.CALL:
            call_amount = self._game_state.current_bet - player.current_bet
            if call_amount > 0:
                player.bet(call_amount)
                self._game_state.add_event(f"{player.name} 跟注 {call_amount}")
                # 发射玩家行动事件
                self._event_bus.emit_simple(
                    EventType.PLAYER_ACTION,
                    player_id=action.player_id,
                    player_name=player.name,
                    action_type="call",
                    amount=call_amount
                )
            else:
                self._game_state.add_event(f"{player.name} 过牌")
                # 发射玩家行动事件
                self._event_bus.emit_simple(
                    EventType.PLAYER_ACTION,
                    player_id=action.player_id,
                    player_name=player.name,
                    action_type="check",
                    amount=0
                )
                
        elif action.action_type == ActionType.BET:
            player.bet(action.amount)
            self._game_state.current_bet = action.amount
            self._game_state.last_raiser = action.player_id
            self._game_state.add_event(f"{player.name} 下注 {action.amount}")
            # 发射下注事件
            self._event_bus.emit_simple(
                EventType.BET_PLACED,
                player_id=action.player_id,
                player_name=player.name,
                action_type="bet",
                amount=action.amount,
                new_current_bet=self._game_state.current_bet
            )
            
        elif action.action_type == ActionType.RAISE:
            # 修复加注逻辑：action.amount应该是总下注金额，不是增量
            # 德州扑克规则：加注15意味着总下注15，不是当前下注+15
            total_bet = action.amount  # 直接使用用户输入的金额作为总下注
            bet_amount = total_bet - player.current_bet
            player.bet(bet_amount)
            self._game_state.current_bet = total_bet
            self._game_state.last_raiser = action.player_id
            # 计算实际加注增量（用于记录）
            raise_increment = total_bet - self._game_state.current_bet if hasattr(self._game_state, '_previous_bet') else action.amount
            self._game_state.last_raise_amount = raise_increment
            self._game_state.add_event(f"{player.name} 加注到 {total_bet}")
            # 发射下注事件
            self._event_bus.emit_simple(
                EventType.BET_PLACED,
                player_id=action.player_id,
                player_name=player.name,
                action_type="raise",
                amount=bet_amount,
                total_bet=total_bet,
                new_current_bet=self._game_state.current_bet
            )
            
        elif action.action_type == ActionType.ALL_IN:
            all_in_amount = player.chips
            player.bet(all_in_amount)
            player.status = SeatStatus.ALL_IN
            if player.current_bet > self._game_state.current_bet:
                self._game_state.current_bet = player.current_bet
                self._game_state.last_raiser = action.player_id
            self._game_state.add_event(f"{player.name} 全押 {all_in_amount}")
            # 发射全押事件
            self._event_bus.emit_simple(
                EventType.PLAYER_ALL_IN,
                player_id=action.player_id,
                player_name=player.name,
                amount=all_in_amount,
                new_current_bet=self._game_state.current_bet
            )
            
        # 移动到下一个玩家
        self._advance_to_next_player()
        
        # 增加行动计数
        self._game_state.increment_action_count()
        
        # 发射底池更新事件
        self._event_bus.emit_simple(
            EventType.POT_UPDATED,
            pot_amount=self._game_state.pot,
            current_bet=self._game_state.current_bet
        )
        
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
        """检查当前阶段是否所有行动都已完成.
        
        德州扑克规则：
        1. 每个活跃玩家在每个下注轮都必须有机会行动
        2. 只有当所有活跃玩家都匹配了当前下注且都已行动过时，下注轮才结束
        3. 如果只剩一个活跃玩家，手牌立即结束（不是阶段结束）
        4. 在PRE_FLOP阶段，大盲注玩家有最后行动权
        """
        active_players = self._game_state.get_active_players()
        
        # 如果没有活跃玩家，行动完成
        if not active_players:
            return True
        
        # 如果只有一个活跃玩家，手牌应该结束（不是阶段结束）
        # 这种情况应该在is_hand_over()中处理，而不是在这里
        if len(active_players) == 1:
            # 检查是否还有ALL_IN玩家
            all_in_players = [p for p in self._game_state.players if p.status == SeatStatus.ALL_IN]
            if not all_in_players:
                # 只有一个活跃玩家且没有ALL_IN玩家，手牌结束
                return True
        
        # 检查是否所有活跃玩家都已匹配当前下注
        for player in active_players:
            if player.current_bet < self._game_state.current_bet:
                return False
        
        # 使用更简单的逻辑：检查是否每个活跃玩家都至少行动过一次
        min_actions_needed = len(active_players)
        
        # 在PRE_FLOP阶段，需要考虑盲注已经是行动
        if self._game_state.phase == Phase.PRE_FLOP:
            # 盲注不算在行动计数中，所以需要确保每个玩家都有机会行动
            # 至少需要活跃玩家数量的行动
            if self._game_state.actions_this_round < min_actions_needed:
                return False
            
            # 特殊检查：如果没有加注，大盲注玩家应该有最后行动权
            if self._game_state.last_raiser is None:
                # 找到大盲注玩家
                big_blind_player = None
                for player in self._game_state.players:
                    if hasattr(player, 'is_big_blind') and player.is_big_blind:
                        big_blind_player = player
                        break
                
                if (big_blind_player and 
                    big_blind_player.status == SeatStatus.ACTIVE and 
                    self._game_state.current_player == big_blind_player.seat_id):
                    # 大盲注玩家还没有行动，需要等待
                    return False
        else:
            # 其他阶段：确保每个活跃玩家都至少行动过一次
            if self._game_state.actions_this_round < min_actions_needed:
                return False
        
        # 如果有加注者，检查是否轮回到加注者
        if self._game_state.last_raiser is not None:
            # 从加注者的下一个位置开始找第一个活跃玩家
            players = self._game_state.players
            raiser_pos = self._game_state.last_raiser
            
            for i in range(1, len(players) + 1):
                next_pos = (raiser_pos + i) % len(players)
                if players[next_pos].status == SeatStatus.ACTIVE:
                    # 如果当前玩家就是加注者后的第一个活跃玩家
                    if self._game_state.current_player == next_pos:
                        return True
                    break
        else:
            # 没有加注者的情况，检查是否轮回到第一个行动玩家
            first_player_pos = self._get_first_player_position()
            if self._game_state.current_player == first_player_pos:
                # 如果轮回到第一个玩家，且所有人都已匹配下注，则完成
                return True
        
        return False
    
    def _get_first_player_position(self) -> int:
        """获取当前下注轮的第一个行动玩家位置.
        
        Returns:
            第一个行动玩家的位置
        """
        if self._game_state.phase == Phase.PRE_FLOP:
            # 翻牌前：大盲注左侧第一位玩家开始
            players = self._game_state.players
            big_blind_pos = None
            
            # 找到大盲注位置
            for i, player in enumerate(players):
                if hasattr(player, 'is_big_blind') and player.is_big_blind:
                    big_blind_pos = i
                    break
            
            if big_blind_pos is not None:
                # 从大盲注左侧开始找第一个活跃玩家
                for i in range(1, len(players) + 1):
                    pos = (big_blind_pos + i) % len(players)
                    if players[pos].status == SeatStatus.ACTIVE:
                        return pos
        else:
            # 翻牌后：庄家左侧第一位活跃玩家开始
            players = self._game_state.players
            dealer_pos = self._game_state.dealer_position
            
            for i in range(1, len(players) + 1):
                pos = (dealer_pos + i) % len(players)
                if players[pos].status == SeatStatus.ACTIVE:
                    return pos
        
        # 如果找不到，返回当前玩家位置
        return self._game_state.current_player or 0
        
    def _advance_to_next_phase(self) -> None:
        """推进到下一个游戏阶段."""
        # 收集当前轮的下注到底池
        self._game_state.collect_bets_to_pot()
        
        # 记录当前阶段
        old_phase = self._game_state.phase
        
        # 推进阶段
        if self._game_state.phase == Phase.PRE_FLOP:
            self._game_state.advance_phase()  # 到FLOP
            self._game_state.deal_community_cards(3)
            # 发射阶段转换事件
            self._event_bus.emit_simple(
                EventType.PHASE_CHANGED,
                from_phase=old_phase.value,
                to_phase=self._game_state.phase.value
            )
            # 发射发牌事件
            self._event_bus.emit_simple(
                EventType.CARDS_DEALT,
                phase=self._game_state.phase.value,
                cards_count=3,
                community_cards_count=len(self._game_state.community_cards)
            )
        elif self._game_state.phase == Phase.FLOP:
            self._game_state.advance_phase()  # 到TURN
            self._game_state.deal_community_cards(1)
            # 发射阶段转换事件
            self._event_bus.emit_simple(
                EventType.PHASE_CHANGED,
                from_phase=old_phase.value,
                to_phase=self._game_state.phase.value
            )
            # 发射发牌事件
            self._event_bus.emit_simple(
                EventType.CARDS_DEALT,
                phase=self._game_state.phase.value,
                cards_count=1,
                community_cards_count=len(self._game_state.community_cards)
            )
        elif self._game_state.phase == Phase.TURN:
            self._game_state.advance_phase()  # 到RIVER
            self._game_state.deal_community_cards(1)
            # 发射阶段转换事件
            self._event_bus.emit_simple(
                EventType.PHASE_CHANGED,
                from_phase=old_phase.value,
                to_phase=self._game_state.phase.value
            )
            # 发射发牌事件
            self._event_bus.emit_simple(
                EventType.CARDS_DEALT,
                phase=self._game_state.phase.value,
                cards_count=1,
                community_cards_count=len(self._game_state.community_cards)
            )
        elif self._game_state.phase == Phase.RIVER:
            self._game_state.advance_phase()  # 到SHOWDOWN
            # 发射阶段转换事件
            self._event_bus.emit_simple(
                EventType.PHASE_CHANGED,
                from_phase=old_phase.value,
                to_phase=self._game_state.phase.value
            )
            
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
        
    def export_snapshot(self) -> Dict[str, Any]:
        """导出当前游戏状态为可序列化的字典.
        
        导出的数据包含完整的游戏状态信息，可以用于保存游戏进度、
        调试分析或状态恢复。
        
        Returns:
            包含完整游戏状态的字典，可以直接序列化为JSON
            
        Note:
            导出的数据包括：
            - 游戏阶段和公共牌
            - 底池和下注信息
            - 所有玩家的完整状态（包括手牌）
            - 位置和轮次信息
            - 事件日志
            - 控制器状态
        """
        snapshot = self.get_snapshot()
        
        # 序列化玩家数据
        players_data = []
        for player in snapshot.players:
            player_data = {
                'seat_id': player.seat_id,
                'name': player.name,
                'chips': player.chips,
                'current_bet': player.current_bet,
                'status': player.status.name,
                'is_dealer': player.is_dealer,
                'is_small_blind': player.is_small_blind,
                'is_big_blind': player.is_big_blind,
                'is_human': player.is_human,
                'total_bet_this_hand': player.total_bet_this_hand,
                'last_action_type': player.last_action_type.name if player.last_action_type else None,
                'hole_cards': [{'suit': card.suit.name, 'rank': card.rank.name} for card in player.hole_cards]
            }
            players_data.append(player_data)
        
        # 序列化公共牌
        community_cards_data = [
            {'suit': card.suit.name, 'rank': card.rank.name} 
            for card in snapshot.community_cards
        ]
        
        # 构建完整的导出数据
        export_data = {
            'version': '2.0',  # 版本标识，用于兼容性检查
            'timestamp': None,  # 可以在需要时添加时间戳
            'game_state': {
                'phase': snapshot.phase.name,
                'community_cards': community_cards_data,
                'pot': snapshot.pot,
                'current_bet': snapshot.current_bet,
                'last_raiser': snapshot.last_raiser,
                'last_raise_amount': snapshot.last_raise_amount,
                'players': players_data,
                'dealer_position': snapshot.dealer_position,
                'current_player': snapshot.current_player,
                'small_blind': snapshot.small_blind,
                'big_blind': snapshot.big_blind,
                'street_index': snapshot.street_index,
                'events': snapshot.events.copy()
            },
            'controller_state': {
                'hand_in_progress': self._hand_in_progress,
                'has_ai_strategy': self._ai_strategy is not None
            }
        }
        
        self._logger.info("游戏状态已导出")
        return export_data
    
    def import_snapshot(self, export_data: Dict[str, Any]) -> bool:
        """从导出的数据恢复游戏状态.
        
        完整恢复游戏状态，包括所有玩家信息、游戏阶段、
        底池状态等。恢复后的游戏可以继续正常进行。
        
        Args:
            export_data: 通过export_snapshot()导出的数据字典
            
        Returns:
            是否成功导入状态
            
        Raises:
            ValueError: 如果导入数据格式无效或版本不兼容
            
        Note:
            导入操作会完全替换当前的游戏状态，包括：
            - 重置所有玩家状态
            - 恢复游戏阶段和公共牌
            - 恢复底池和下注信息
            - 恢复事件日志
            - 恢复控制器状态
        """
        try:
            # 验证数据格式
            if not isinstance(export_data, dict):
                raise ValueError("导入数据必须是字典格式")
            
            if 'version' not in export_data:
                raise ValueError("导入数据缺少版本信息")
            
            if 'game_state' not in export_data:
                raise ValueError("导入数据缺少游戏状态信息")
            
            # 检查版本兼容性
            version = export_data['version']
            if not version.startswith('2.'):
                raise ValueError(f"不支持的数据版本: {version}")
            
            game_data = export_data['game_state']
            controller_data = export_data.get('controller_state', {})
            
            # 重建玩家列表
            players = []
            for player_data in game_data['players']:
                # 重建手牌
                hole_cards = []
                for card_data in player_data['hole_cards']:
                    suit = Suit[card_data['suit']]
                    rank = Rank[card_data['rank']]
                    hole_cards.append(Card(suit, rank))
                
                # 重建玩家对象
                player = Player(
                    seat_id=player_data['seat_id'],
                    name=player_data['name'],
                    chips=player_data['chips'],
                    hole_cards=hole_cards,
                    current_bet=player_data['current_bet'],
                    status=SeatStatus[player_data['status']],
                    is_dealer=player_data['is_dealer'],
                    is_small_blind=player_data['is_small_blind'],
                    is_big_blind=player_data['is_big_blind'],
                    is_human=player_data.get('is_human', False),
                    total_bet_this_hand=player_data.get('total_bet_this_hand', 0),
                    last_action_type=ActionType[player_data['last_action_type']] if player_data['last_action_type'] else None
                )
                players.append(player)
            
            # 重建公共牌
            community_cards = []
            for card_data in game_data['community_cards']:
                suit = Suit[card_data['suit']]
                rank = Rank[card_data['rank']]
                community_cards.append(Card(suit, rank))
            
            # 创建新的游戏状态
            new_game_state = GameState(
                phase=Phase[game_data['phase']],
                community_cards=community_cards,
                pot=game_data['pot'],
                current_bet=game_data['current_bet'],
                last_raiser=game_data['last_raiser'],
                last_raise_amount=game_data['last_raise_amount'],
                players=players,
                dealer_position=game_data['dealer_position'],
                current_player=game_data['current_player'],
                small_blind=game_data['small_blind'],
                big_blind=game_data['big_blind'],
                street_index=game_data['street_index'],
                events=game_data['events'].copy()
            )
            
            # 替换当前游戏状态
            self._game_state = new_game_state
            
            # 恢复控制器状态
            self._hand_in_progress = controller_data.get('hand_in_progress', False)
            
            # 发射状态导入事件
            self._event_bus.emit_simple(
                EventType.STATE_CHANGED,
                action="state_imported",
                players_count=len(players)
            )
            
            self._logger.info(f"成功导入游戏状态，包含{len(players)}个玩家")
            return True
            
        except (KeyError, ValueError, TypeError) as e:
            self._logger.error(f"导入游戏状态失败: {e}")
            raise ValueError(f"导入数据格式错误: {e}")
        except Exception as e:
            self._logger.error(f"导入游戏状态时发生未知错误: {e}")
            return False 

    def _advance_dealer_position(self) -> None:
        """移动庄家位置到下一个活跃玩家."""
        players = self._game_state.players
        if not players:
            return
            
        current_dealer = self._game_state.dealer_position
        
        # 简单地移动到下一个位置（不管是否活跃）
        # 这样确保庄家位置总是轮换，即使某些玩家暂时不活跃
        self._game_state.dealer_position = (current_dealer + 1) % len(players)
        
        self._logger.info(f"庄家位置从 {current_dealer} 移动到 {self._game_state.dealer_position}")
        
        # 发射状态变更事件
        self._event_bus.emit_simple(
            EventType.STATE_CHANGED,
            change_type="dealer_moved",
            old_dealer_position=current_dealer,
            new_dealer_position=self._game_state.dealer_position
        ) 