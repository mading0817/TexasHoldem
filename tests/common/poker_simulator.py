#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
德州扑克模拟器
提供可重用的游戏模拟和测试基础设施
"""

import random
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from core_game_logic.core.enums import ActionType, Action, GamePhase, SeatStatus
from core_game_logic.game.game_controller import GameController
from core_game_logic.core.card import Card
from core_game_logic.core.player import Player
from tests.common.test_helpers import ActionHelper

# 设置日志
logger = logging.getLogger("poker.sim")


@dataclass(frozen=True)
class SeatSnapshot:
    """座位快照 - 只读的玩家状态信息"""
    seat_id: int
    name: str
    chips: int
    current_bet: int
    hole_cards: Tuple[Card, ...] = field(default_factory=tuple)
    status: SeatStatus = SeatStatus.ACTIVE
    is_dealer: bool = False
    can_act: bool = True


@dataclass(frozen=True)  
class GameSnapshot:
    """游戏状态快照 - 只读的游戏状态信息"""
    phase: GamePhase
    pot: int
    current_bet: int
    community_cards: Tuple[Card, ...]
    seats: Tuple[SeatSnapshot, ...]
    current_seat: Optional[int]
    dealer_position: int
    small_blind: int
    big_blind: int
    
    def pretty(self) -> str:
        """返回格式化的快照信息，用于调试"""
        lines = [
            f"=== 游戏快照 ===",
            f"阶段: {self.phase.name}",
            f"底池: {self.pot}",
            f"当前下注: {self.current_bet}",
            f"公共牌: {[str(card) for card in self.community_cards]}",
            f"当前玩家: {self.current_seat}",
            f"庄家: {self.dealer_position}",
            f"盲注: {self.small_blind}/{self.big_blind}",
            "座位信息:"
        ]
        
        for seat in self.seats:
            status_info = f"筹码:{seat.chips} 下注:{seat.current_bet} 状态:{seat.status.name}"
            if seat.is_dealer:
                status_info += " [庄家]"
            if seat.seat_id == self.current_seat:
                status_info += " [当前]"
            lines.append(f"  座位{seat.seat_id}: {seat.name} - {status_info}")
        
        return "\n".join(lines)


@dataclass
class ActionResult:
    """行动执行结果"""
    success: bool
    action: Optional[Action] = None
    error_message: str = ""
    game_ended: bool = False


@dataclass
class BettingRoundResult:
    """下注轮结果"""
    round_completed: bool
    actions_taken: List[Action]
    final_pot: int
    active_players: int
    iterations: int
    errors: List[str] = field(default_factory=list)


@dataclass  
class HandResult:
    """手牌结果"""
    hand_completed: bool
    active_players: int
    pot_after_payout: int
    winners: List[str] = field(default_factory=list)
    phases_completed: List[GamePhase] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class Strategy(ABC):
    """策略接口 - 定义AI/测试策略的决策方法"""
    
    @abstractmethod
    def decide(self, snapshot: GameSnapshot) -> Action:
        """
        根据游戏快照做出决策
        
        Args:
            snapshot: 只读的游戏状态快照
            
        Returns:
            Action: 决策的行动
        """
        pass


class ConservativeStrategy(Strategy):
    """保守策略 - 倾向于过牌、跟注或弃牌，避免大额下注"""
    
    def decide(self, snapshot: GameSnapshot) -> Action:
        """保守决策逻辑"""
        current_seat = snapshot.current_seat
        if current_seat is None:
            raise ValueError("没有当前玩家，无法做决策")
        
        me = None
        for seat in snapshot.seats:
            if seat.seat_id == current_seat:
                me = seat
                break
        
        if not me:
            raise ValueError(f"找不到座位{current_seat}的玩家信息")
        
        # 计算需要跟注的金额
        call_amount = snapshot.current_bet - me.current_bet
        
        # 保守策略逻辑：
        # 1. 如果不需要跟注，就过牌
        if call_amount == 0:
            return ActionHelper.create_action(ActionType.CHECK, 0, me.seat_id)
        
        # 2. 如果跟注金额小于等于筹码的10%，就跟注
        if call_amount <= me.chips * 0.1 and call_amount <= me.chips:
            return ActionHelper.create_action(ActionType.CALL, call_amount, me.seat_id)
        
        # 3. 否则弃牌
        return ActionHelper.create_action(ActionType.FOLD, 0, me.seat_id)


class AggressiveStrategy(Strategy):
    """激进策略 - 用于快速结束游戏和淘汰测试"""
    
    def __init__(self, all_in_probability: float = 0.3):
        self.all_in_probability = all_in_probability
    
    def decide(self, snapshot: GameSnapshot) -> Action:
        """激进决策逻辑"""
        current_seat = snapshot.current_seat
        if current_seat is None:
            raise ValueError("没有当前玩家，无法做决策")
        
        me = None
        for seat in snapshot.seats:
            if seat.seat_id == current_seat:
                me = seat
                break
        
        if not me:
            raise ValueError(f"找不到座位{current_seat}的玩家信息")
        
        # 随机决定是否全押
        if random.random() < self.all_in_probability and me.chips > 0:
            return ActionHelper.create_action(ActionType.ALL_IN, me.chips, me.seat_id)
        
        # 否则使用保守策略
        call_amount = snapshot.current_bet - me.current_bet
        if call_amount == 0:
            return ActionHelper.create_action(ActionType.CHECK, 0, me.seat_id)
        elif call_amount <= me.chips:
            return ActionHelper.create_action(ActionType.CALL, call_amount, me.seat_id)
        else:
            return ActionHelper.create_action(ActionType.FOLD, 0, me.seat_id)


class PokerSimulator:
    """
    德州扑克模拟器
    组合GameController + Strategy + RNG，提供高级游戏模拟接口
    """
    
    # 护栏常量
    MAX_HAND_STEPS = 500
    MAX_ROUND_STEPS = 100
    MAX_PHASE_STEPS = 50
    
    def __init__(self, controller: GameController, rng: Optional[random.Random] = None):
        """
        初始化模拟器
        
        Args:
            controller: 游戏控制器
            rng: 随机数生成器，用于测试时的确定性
        """
        self.controller = controller
        self.rng = rng or random.Random()
        self.debug_mode = False
    
    def get_game_snapshot(self) -> GameSnapshot:
        """获取当前游戏状态的只读快照"""
        state = self.controller.state
        
        # 构建座位快照
        seat_snapshots = []
        for player in state.players:
            seat_snapshot = SeatSnapshot(
                seat_id=player.seat_id,
                name=player.name,
                chips=player.chips,
                current_bet=player.current_bet,
                hole_cards=tuple(player.hole_cards),
                status=player.status,
                is_dealer=player.is_dealer,
                can_act=player.can_act()
            )
            seat_snapshots.append(seat_snapshot)
        
        return GameSnapshot(
            phase=state.phase,
            pot=state.pot,
            current_bet=state.current_bet,
            community_cards=tuple(state.community_cards),
            seats=tuple(seat_snapshots),
            current_seat=state.get_current_player().seat_id if state.get_current_player() else None,
            dealer_position=state.dealer_position,
            small_blind=state.small_blind,
            big_blind=state.big_blind
        )
    
    def play_betting_round(self, strategies: Dict[int, Strategy]) -> BettingRoundResult:
        """
        模拟一个下注轮
        
        Args:
            strategies: 座位号到策略的映射
            
        Returns:
            BettingRoundResult: 下注轮结果
        """
        actions_taken = []
        errors = []
        iteration = 0
        
        try:
            while iteration < self.MAX_ROUND_STEPS:
                iteration += 1
                
                # 检查下注轮是否完成
                if self.controller.is_betting_round_complete():
                    logger.debug(f"下注轮完成，用了{iteration}次迭代")
                    break
                
                # 获取当前玩家
                current_player = self.controller.get_current_player()
                if current_player is None:
                    logger.debug("没有当前玩家，下注轮可能已完成")
                    break
                
                current_seat = current_player.seat_id
                
                # 获取策略
                strategy = strategies.get(current_seat)
                if not strategy:
                    # 没有策略，使用默认保守策略
                    strategy = ConservativeStrategy()
                
                try:
                    # 获取快照并做决策
                    snapshot = self.get_game_snapshot()
                    if self.debug_mode:
                        logger.debug(f"迭代{iteration}: 玩家{current_seat}行动\n{snapshot.pretty()}")
                    
                    action = strategy.decide(snapshot)
                    actions_taken.append(action)
                    
                    # 执行行动
                    result = self.controller.process_action(action)
                    if not result:
                        logger.debug(f"行动执行后下注轮结束")
                        break
                        
                except Exception as e:
                    error_msg = f"迭代{iteration}玩家{current_seat}行动失败: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    break
            
            if iteration >= self.MAX_ROUND_STEPS:
                error_msg = f"下注轮护栏触发: 超过{self.MAX_ROUND_STEPS}次迭代"
                errors.append(error_msg)
                raise RuntimeError(error_msg)
        
        except Exception as e:
            errors.append(str(e))
        
        return BettingRoundResult(
            round_completed=self.controller.is_betting_round_complete(),
            actions_taken=actions_taken,
            final_pot=self.controller.get_total_pot(),
            active_players=len([p for p in self.controller.state.players if p.can_act()]),
            iterations=iteration,
            errors=errors
        )
    
    def play_hand(self, strategies: Dict[int, Strategy]) -> HandResult:
        """
        模拟完整的一手牌
        
        Args:
            strategies: 座位号到策略的映射
            
        Returns:
            HandResult: 手牌结果
        """
        phases_completed = []
        errors = []
        winners = []
        
        try:
            # 开始新手牌
            self.controller.start_new_hand()
            initial_pot = self.controller.get_total_pot()
            
            # 遍历所有阶段
            for step in range(self.MAX_HAND_STEPS):
                current_phase = self.controller.state.phase
                phases_completed.append(current_phase)
                
                if self.debug_mode:
                    snapshot = self.get_game_snapshot()
                    logger.debug(f"手牌步骤{step}: 阶段{current_phase.name}\n{snapshot.pretty()}")
                
                # 执行当前阶段的下注轮
                betting_result = self.play_betting_round(strategies)
                if betting_result.errors:
                    errors.extend(betting_result.errors)
                
                # 检查是否所有玩家都弃牌或只剩一个玩家
                active_players = [p for p in self.controller.state.players 
                                if p.status not in [SeatStatus.FOLDED, SeatStatus.OUT]]
                
                if len(active_players) <= 1:
                    # 游戏提前结束
                    if active_players:
                        winners = [active_players[0].name]
                    break
                
                # 尝试推进到下一阶段
                try:
                    self.controller.advance_phase()
                    if self.controller.state.phase == GamePhase.SHOWDOWN:
                        # 到达摊牌阶段，确定胜者
                        game_winners = self.controller.determine_winners()
                        if game_winners:
                            winners = [w.name for w in game_winners]
                        break
                except Exception as e:
                    logger.debug(f"阶段推进完成或出错: {e}")
                    break
            
            if step >= self.MAX_HAND_STEPS - 1:
                error_msg = f"手牌护栏触发: 超过{self.MAX_HAND_STEPS}步骤"
                errors.append(error_msg)
                raise RuntimeError(error_msg)
        
        except Exception as e:
            errors.append(str(e))
        
        return HandResult(
            hand_completed=True,
            active_players=len([p for p in self.controller.state.players if p.chips > 0]),
            pot_after_payout=self.controller.get_total_pot(),
            winners=winners,
            phases_completed=phases_completed,
            errors=errors
        )
    
    def play_n_hands(self, n: int, strategies: Dict[int, Strategy]) -> List[HandResult]:
        """
        模拟多手牌游戏
        
        Args:
            n: 手牌数量
            strategies: 座位号到策略的映射
            
        Returns:
            List[HandResult]: 所有手牌的结果
        """
        results = []
        for hand_num in range(n):
            if self.debug_mode:
                logger.debug(f"开始第{hand_num + 1}手牌")
            
            try:
                result = self.play_hand(strategies)
                results.append(result)
                
                # 检查是否还有足够玩家继续游戏
                active_players = [p for p in self.controller.state.players if p.chips > 0]
                if len(active_players) < 2:
                    logger.debug(f"第{hand_num + 1}手牌后只剩{len(active_players)}个玩家，游戏结束")
                    break
                    
            except Exception as e:
                logger.error(f"第{hand_num + 1}手牌模拟失败: {e}")
                # 创建错误结果
                error_result = HandResult(
                    hand_completed=False,
                    active_players=0,
                    pot_after_payout=0,
                    winners=[],
                    phases_completed=[],
                    errors=[str(e)]
                )
                results.append(error_result)
                break
        
        return results


def create_default_strategies(player_seats: List[int], 
                            strategy_type: str = "conservative") -> Dict[int, Strategy]:
    """
    创建默认策略映射
    
    Args:
        player_seats: 玩家座位号列表
        strategy_type: 策略类型 ("conservative" 或 "aggressive")
        
    Returns:
        Dict[int, Strategy]: 座位号到策略的映射
    """
    if strategy_type == "conservative":
        strategy_class = ConservativeStrategy
    elif strategy_type == "aggressive":
        strategy_class = AggressiveStrategy
    else:
        raise ValueError(f"未知的策略类型: {strategy_type}")
    
    return {seat: strategy_class() for seat in player_seats} 