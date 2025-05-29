#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克测试辅助函数
包含各种测试中使用的工具函数和实用方法
"""

import time
import random
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from dataclasses import dataclass

# 确保正确的编码输出
import sys
import os
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_game_logic.core.enums import ActionType, GamePhase, SeatStatus, Action
from core_game_logic.core.player import Player
from core_game_logic.game.game_state import GameState


class ActionHelper:
    """
    Action创建辅助类
    确保所有Action对象都有正确的player_seat参数，防止测试中的"作弊"行为
    """
    
    @staticmethod
    def create_action(action_type: ActionType, amount: int = 0, player_seat: Optional[int] = None) -> Action:
        """
        创建标准Action对象
        
        Args:
            action_type: 行动类型
            amount: 金额（默认为0）
            player_seat: 玩家座位号（必须提供）
            
        Returns:
            正确初始化的Action对象
            
        Raises:
            ValueError: 如果player_seat为None
        """
        if player_seat is None:
            raise ValueError("测试中的Action必须指定player_seat，防止作弊行为")
        
        return Action(action_type=action_type, amount=amount, player_seat=player_seat)
    
    @staticmethod
    def create_current_player_action(game_state: GameState, action_type: ActionType, amount: int = 0) -> Action:
        """
        为当前玩家创建Action对象
        
        Args:
            game_state: 当前游戏状态
            action_type: 行动类型
            amount: 金额（默认为0）
            
        Returns:
            正确设置player_seat的Action对象
            
        Raises:
            ValueError: 如果没有当前玩家
        """
        current_player = game_state.get_current_player()
        if current_player is None:
            raise ValueError("当前没有行动的玩家，无法创建Action")
        
        return Action(action_type=action_type, amount=amount, player_seat=current_player.seat_id)
    
    @staticmethod
    def create_player_action(player: Player, action_type: ActionType, amount: int = 0) -> Action:
        """
        为指定玩家创建Action对象
        
        Args:
            player: 目标玩家
            action_type: 行动类型
            amount: 金额（默认为0）
            
        Returns:
            正确设置player_seat的Action对象
        """
        return Action(action_type=action_type, amount=amount, player_seat=player.seat_id)


class TestValidator:
    """
    测试验证器
    检查测试数据的合规性，防止作弊行为
    """
    
    @staticmethod
    def validate_chip_conservation(initial_total: int, current_total: int, pot_total: int, 
                                 tolerance: int = 0) -> bool:
        """
        验证筹码守恒定律
        
        Args:
            initial_total: 初始筹码总数
            current_total: 当前玩家筹码总数
            pot_total: 底池总数
            tolerance: 允许的误差（通常应为0）
            
        Returns:
            True如果筹码守恒，False否则
        """
        actual_total = current_total + pot_total
        difference = abs(actual_total - initial_total)
        
        if difference > tolerance:
            print(f"筹码守恒检查失败：初始{initial_total}, 当前{current_total}, 底池{pot_total}, 差异{difference}")
            return False
        
        return True
    
    @staticmethod
    def validate_texas_holdem_rules(game_state: GameState) -> Dict[str, bool]:
        """
        验证德州扑克基本规则合规性
        
        Args:
            game_state: 游戏状态
            
        Returns:
            规则检查结果字典
        """
        results = {}
        
        # 1. 玩家手牌数量检查
        results['hand_cards'] = True
        for player in game_state.players:
            if player.is_active and len(player.get_hand_cards()) != 2:
                results['hand_cards'] = False
                break
        
        # 2. 社区牌数量检查
        community_count = len(game_state.community_cards)
        phase = game_state.phase
        
        expected_community = {
            GamePhase.PRE_FLOP: 0,
            GamePhase.FLOP: 3,
            GamePhase.TURN: 4,
            GamePhase.RIVER: 5,
            GamePhase.SHOWDOWN: 5
        }
        
        results['community_cards'] = community_count == expected_community.get(phase, 0)
        
        # 3. 盲注设置检查
        results['blinds'] = True
        if game_state.small_blind <= 0 or game_state.big_blind <= game_state.small_blind:
            results['blinds'] = False
        
        # 4. 位置有效性检查
        results['positions'] = True
        if not (0 <= game_state.dealer_position < len(game_state.players)):
            results['positions'] = False
        
        # 5. 活跃玩家数量检查
        active_players = [p for p in game_state.players if p.is_active]
        results['active_players'] = len(active_players) >= 2
        
        return results
    
    @staticmethod
    def detect_test_cheating(game_state: GameState, actions_history: List[Action]) -> List[str]:
        """
        检测测试中的潜在作弊行为
        
        Args:
            game_state: 游戏状态
            actions_history: 行动历史
            
        Returns:
            发现的作弊行为列表
        """
        cheats = []
        
        # 1. 检查Action对象的合规性
        for i, action in enumerate(actions_history):
            if action.player_seat is None:
                cheats.append(f"Action {i}: player_seat为None，可能绕过了正常验证")
            
            if action.player_seat is not None and action.player_seat >= len(game_state.players):
                cheats.append(f"Action {i}: player_seat {action.player_seat} 超出玩家范围")
        
        # 2. 检查筹码操作的合规性
        total_chips = sum(p.chips for p in game_state.players)
        pot_total = game_state.pot_manager.get_total_pot() if hasattr(game_state, 'pot_manager') else 0
        
        # 这里可以添加更多的合规性检查
        
        return cheats


class GameStateHelper:
    """游戏状态辅助类 - 提供合规的状态设置方法"""
    
    @staticmethod
    def setup_player_chips(game_state, player_chips_map):
        """
        合规地设置玩家筹码
        
        Args:
            game_state: 游戏状态
            player_chips_map: {player_index: chips} 映射
        """
        # 这应该通过合法的游戏API设置，而不是直接修改
        # 在实际游戏中，这种设置只能在游戏初始化时进行
        for player_index, chips in player_chips_map.items():
            if 0 <= player_index < len(game_state.players):
                # 临时允许在测试环境中设置初始筹码
                # 但需要记录这种操作用于审计
                game_state.players[player_index].chips = chips
    
    @staticmethod
    def setup_betting_state(game_state, current_bet=0, player_bets=None):
        """
        合规地设置下注状态
        
        Args:
            game_state: 游戏状态
            current_bet: 当前最高下注
            player_bets: {player_index: bet_amount} 映射
        """
        # 只能在测试初始化时使用
        game_state.current_bet = current_bet
        
        if player_bets:
            for player_index, bet in player_bets.items():
                if 0 <= player_index < len(game_state.players):
                    game_state.players[player_index].current_bet = bet
    
    @staticmethod
    def create_test_scenario_state(scenario_config):
        """
        根据场景配置创建合规的测试状态
        
        Args:
            scenario_config: 包含玩家筹码、下注等配置的字典
        
        Returns:
            GameState: 配置好的游戏状态
        """
        # 这是创建测试状态的合法方法
        from core_game_logic.core.game_state import GameState
        from core_game_logic.core.player import Player
        from core_game_logic.core.deck import Deck
        
        players = []
        for i, chips in enumerate(scenario_config.get('player_chips', [1000] * 4)):
            player = Player(f"Player{i}", i, chips)
            players.append(player)
        
        state = GameState(
            players=players,
            deck=Deck(),
            small_blind=scenario_config.get('small_blind', 1),
            big_blind=scenario_config.get('big_blind', 2),
            dealer_position=scenario_config.get('dealer_position', 0)
        )
        
        # 设置下注状态（如果需要）
        if 'current_bet' in scenario_config:
            state.current_bet = scenario_config['current_bet']
        
        if 'player_bets' in scenario_config:
            for i, bet in enumerate(scenario_config['player_bets']):
                if i < len(state.players):
                    state.players[i].current_bet = bet
        
        return state

    @staticmethod
    def validate_chip_conservation(game_state, expected_total):
        """
        验证筹码守恒定律
        
        Args:
            game_state: 游戏状态
            expected_total: 期望的总筹码数
        
        Returns:
            bool: 筹码是否守恒
        """
        current_total = sum(player.chips for player in game_state.players)
        pot_total = getattr(game_state, 'pot', 0)
        total_chips = current_total + pot_total
        
        return abs(total_chips - expected_total) < 0.01  # 允许浮点误差

    @staticmethod
    def print_game_state_summary(game_state: GameState, title: str = "游戏状态"):
        """打印游戏状态摘要，用于调试"""
        print(f"\n=== {title} ===")
        print(f"阶段: {game_state.phase.name if hasattr(game_state.phase, 'name') else str(game_state.phase)}")
        print(f"庄家位置: {game_state.dealer_position}")
        print(f"社区牌: {[str(card) for card in game_state.community_cards]}")
        
        print("玩家状态:")
        for player in game_state.players:
            status = "ACTIVE" if player.is_active else "INACTIVE"
            current = " <-- 当前" if game_state.get_current_player() == player else ""
            print(f"  {player.name}(座位{player.seat_id}): {player.chips}筹码, {status}{current}")
        
        if hasattr(game_state, 'pot_manager'):
            print(f"底池: {game_state.pot_manager.get_total_pot()}")
        print("=" * 40)
    
    @staticmethod
    def validate_phase_transition(from_phase: GamePhase, to_phase: GamePhase) -> bool:
        """
        验证阶段转换的合规性
        
        Args:
            from_phase: 起始阶段
            to_phase: 目标阶段
            
        Returns:
            True如果转换合法，False否则
        """
        valid_transitions = {
            GamePhase.PRE_FLOP: [GamePhase.FLOP, GamePhase.SHOWDOWN],
            GamePhase.FLOP: [GamePhase.TURN, GamePhase.SHOWDOWN],
            GamePhase.TURN: [GamePhase.RIVER, GamePhase.SHOWDOWN],
            GamePhase.RIVER: [GamePhase.SHOWDOWN],
            GamePhase.SHOWDOWN: [GamePhase.PRE_FLOP]  # 新手牌
        }
        
        return to_phase in valid_transitions.get(from_phase, [])


def performance_timer(func):
    """性能计时装饰器"""
    import time
    
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        duration = (end_time - start_time) * 1000  # 转换为毫秒
        print(f"  {func.__name__} 耗时: {duration:.3f}ms")
        
        return result
    
    return wrapper


def format_test_header(title: str, width: int = 60) -> str:
    """格式化测试标题"""
    return f"\n{'=' * width}\n{title.center(width)}\n{'=' * width}"


def create_test_players(count: int, starting_chips: int = 100) -> List[Player]:
    """
    创建测试用的玩家列表
    
    Args:
        count: 玩家数量
        starting_chips: 每个玩家的起始筹码
        
    Returns:
        玩家对象列表
    """
    names = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack"]
    players = []
    
    for i in range(count):
        name = names[i] if i < len(names) else f"Player{i}"
        player = Player(seat_id=i, name=name, chips=starting_chips)
        players.append(player)
    
    return players


def setup_basic_game_state(players: List[Player], dealer_pos: int = 0) -> GameState:
    """
    设置基础的游戏状态
    
    Args:
        players: 玩家列表
        dealer_pos: 庄家位置
        
    Returns:
        配置好的游戏状态
    """
    state = GameState(
        players=players,
        dealer_position=dealer_pos,
        small_blind=1,
        big_blind=2
    )
    
    # 重置玩家状态
    for player in state.players:
        player.reset_for_new_hand()
        player.is_dealer = (player.seat_id == dealer_pos)
    
    return state


def collect_action_order(game_state: GameState, phase_obj) -> List[int]:
    """
    收集下注轮中的行动顺序
    
    Args:
        game_state: 游戏状态
        phase_obj: 游戏阶段对象
        
    Returns:
        行动顺序的座位号列表
    """
    action_order = []
    max_actions = 20  # 防止无限循环
    action_count = 0
    
    while not phase_obj.is_round_complete() and action_count < max_actions:
        current_seat = game_state.current_player
        action_order.append(current_seat)
        
        # 模拟玩家行动（简单的过牌或跟注）
        current_player = game_state.get_current_player()
        if current_player and current_player.can_act():
            if game_state.current_bet == 0:
                # 没有下注时过牌
                action = ActionType.CHECK
            else:
                # 有下注时跟注
                action = ActionType.CALL
                
            # 这里需要更复杂的逻辑来模拟真实的行动
            # 为了测试行动顺序，我们只需要推进到下一个玩家
            if not phase_obj.advance_player():
                break
        else:
            break
            
        action_count += 1
    
    return action_order


@contextmanager
def performance_timer():
    """
    性能计时器上下文管理器
    用于测量代码块的执行时间
    """
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        print(f"执行时间: {end_time - start_time:.4f} 秒")


def validate_chip_conservation(initial_chips: Dict[int, int], 
                             final_chips: Dict[int, int], 
                             pot_total: int) -> bool:
    """
    验证筹码守恒定律
    
    Args:
        initial_chips: 初始筹码分布 {seat_id: chips}
        final_chips: 最终筹码分布 {seat_id: chips}
        pot_total: 底池总额
        
    Returns:
        筹码是否守恒
    """
    initial_total = sum(initial_chips.values())
    final_total = sum(final_chips.values()) + pot_total
    
    return abs(initial_total - final_total) < 0.01  # 允许小的浮点误差


def simulate_simple_betting_round(state: GameState, phase) -> bool:
    """
    模拟简单的下注轮
    所有玩家都选择过牌或跟注
    
    Args:
        state: 游戏状态
        phase: 游戏阶段对象
        
    Returns:
        下注轮是否成功完成
    """
    max_actions = 50  # 防止无限循环
    action_count = 0
    
    while not phase.is_round_complete() and action_count < max_actions:
        current_player = state.get_current_player()
        if not current_player or not current_player.can_act():
            break
            
        # 简单策略：过牌或跟注
        if state.current_bet == 0:
            # 如果没有下注，选择过牌
            try:
                action = ActionHelper.create_player_action(current_player, ActionType.CHECK, 0)
                validated_action = state.validator.validate(state, current_player, action)
                phase.act(validated_action)
            except Exception as e:
                print(f"模拟行动失败: {e}")
                break
        else:
            # 如果有下注，选择跟注
            try:
                call_amount = state.current_bet - current_player.current_bet
                action = ActionHelper.create_player_action(current_player, ActionType.CALL, call_amount)
                validated_action = state.validator.validate(state, current_player, action)
                phase.act(validated_action)
            except Exception as e:
                print(f"模拟跟注失败: {e}")
                break
                
        action_count += 1
    
    return action_count < max_actions


def print_game_state_summary(state: GameState, title: str = "游戏状态"):
    """
    打印游戏状态摘要
    
    Args:
        state: 游戏状态
        title: 摘要标题
    """
    print(f"\n{title}:")
    print(f"  阶段: {state.phase.name}")
    print(f"  底池: {state.pot}")
    print(f"  当前下注: {state.current_bet}")
    print(f"  当前玩家: {state.current_player}")
    print(f"  庄家位置: {state.dealer_position}")
    
    print("  玩家状态:")
    for player in state.players:
        status_info = []
        if player.is_dealer:
            status_info.append("庄家")
        if player.is_small_blind:
            status_info.append("小盲")
        if player.is_big_blind:
            status_info.append("大盲")
        
        status_str = f"({', '.join(status_info)})" if status_info else ""
        print(f"    座位{player.seat_id} {player.name}{status_str}: "
              f"{player.chips}筹码, 当前下注{player.current_bet}, "
              f"状态{player.status.name}")


def setup_random_seed(seed: Optional[int] = None) -> int:
    """
    设置随机种子，用于可重现的测试
    
    Args:
        seed: 随机种子，如果为None则使用当前时间
        
    Returns:
        使用的种子值
    """
    if seed is None:
        seed = int(time.time())
    
    random.seed(seed)
    print(f"随机种子设置为: {seed}")
    return seed


def count_active_players(state: GameState) -> int:
    """
    计算活跃玩家数量
    
    Args:
        state: 游戏状态
        
    Returns:
        活跃玩家数量
    """
    return len([p for p in state.players if p.status == SeatStatus.ACTIVE])


def find_player_by_position(state: GameState, position: str) -> Optional[Player]:
    """
    根据位置查找玩家
    
    Args:
        state: 游戏状态
        position: 位置类型 ("dealer", "small_blind", "big_blind")
        
    Returns:
        对应位置的玩家，如果不存在则返回None
    """
    for player in state.players:
        if position == "dealer" and player.is_dealer:
            return player
        elif position == "small_blind" and player.is_small_blind:
            return player
        elif position == "big_blind" and player.is_big_blind:
            return player
    
    return None 