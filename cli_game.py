#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克CLI游戏界面 v2.0 - 增强版
提供完整的德州扑克游戏体验，支持人类玩家与AI对战
包含详细的游戏信息显示、智能错误处理和丰富的用户交互
"""

import os
import sys
import random
import time
from typing import List, Optional, Tuple, Dict

from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.core.enums import ActionType, Action, SeatStatus, GamePhase
from core_game_logic.betting.action_validator import ActionValidator
from core_game_logic.phases import PreFlopPhase, FlopPhase, TurnPhase, RiverPhase, ShowdownPhase
from core_game_logic.core.deck import Deck
from core_game_logic.core.exceptions import InvalidActionError


class EnhancedCLIGame:
    """增强版CLI德州扑克游戏"""
    
    def __init__(self):
        self.validator = ActionValidator()
        self.human_seat = 0  # 人类玩家座位
        self.game_stats = {
            'hands_played': 0,
            'hands_won': 0,
            'biggest_pot': 0,
            'total_winnings': 0
        }
        self.debug_mode = False  # 可配置的调试模式
        
    def clear_screen(self):
        """清屏功能"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str):
        """打印格式化的标题"""
        print("\n" + "="*80)
        print(f"🃏 {title.center(76)} 🃏")
        print("="*80)
    
    def print_separator(self, char="-", length=60):
        """打印分隔线"""
        print(char * length)
    
    def debug_print(self, message: str):
        """条件调试输出"""
        if self.debug_mode:
            print(f"[DEBUG] {message}")
    
    def get_game_config(self) -> Tuple[int, int, bool]:
        """获取游戏配置"""
        self.print_header("游戏配置")
        
        # 获取玩家数量
        while True:
            try:
                num_str = input("🎮 请输入玩家数量 (2-10，默认4): ").strip()
                if not num_str:
                    num_players = 4
                else:
                    num_players = int(num_str)
                
                if 2 <= num_players <= 10:
                    break
                else:
                    print("❌ 玩家数量必须在2-10之间")
            except ValueError:
                print("❌ 请输入有效的数字")
        
        # 获取初始筹码
        while True:
            try:
                chips_str = input("💰 请输入初始筹码 (默认1000): ").strip()
                if not chips_str:
                    starting_chips = 1000
                else:
                    starting_chips = int(chips_str)
                
                if starting_chips >= 10:  # 至少要能支付几轮盲注
                    break
                else:
                    print("❌ 初始筹码必须至少为10")
            except ValueError:
                print("❌ 请输入有效的数字")
        
        # 是否开启调试模式
        debug_str = input("🔧 是否开启调试模式？(y/N): ").strip().lower()
        debug_mode = debug_str in ['y', 'yes', '是']
        
        return num_players, starting_chips, debug_mode
        
    def create_game(self, num_players: int = 4, starting_chips: int = 1000) -> GameState:
        """创建新游戏"""
        self.debug_print(f"创建游戏: {num_players}个玩家, 初始筹码{starting_chips}")
        
        players = []
        
        # 创建人类玩家
        human_name = input("👤 请输入你的姓名 (默认'You'): ").strip()
        if not human_name:
            human_name = "You"
        
        human_player = Player(
            seat_id=self.human_seat,
            name=human_name,
            chips=starting_chips
        )
        players.append(human_player)
        
        # 创建AI玩家
        ai_names = [
            "Alice", "Bob", "Charlie", "David", "Eve", 
            "Frank", "Grace", "Henry", "Ivy", "Jack"
        ]
        
        for i in range(1, num_players):
            ai_player = Player(
                seat_id=i,
                name=ai_names[i-1] if i-1 < len(ai_names) else f"AI-{i}",
                chips=starting_chips
            )
            players.append(ai_player)
        
        # 创建游戏状态
        state = GameState(
            players=players,
            dealer_position=0,
            small_blind=5,  # 增加盲注让游戏更有趣
            big_blind=10
        )
        
        self.debug_print(f"游戏状态创建完成, 庄家位置: {state.dealer_position}")
        self.debug_print(f"盲注设置: 小盲{state.small_blind}, 大盲{state.big_blind}")
        
        return state
    
    def format_chips(self, amount: int) -> str:
        """格式化筹码显示"""
        if amount >= 1000:
            return f"{amount:,}"
        return str(amount)
    
    def get_position_name(self, player: Player, total_players: int) -> str:
        """获取玩家位置名称"""
        if player.is_dealer:
            if total_players == 2:
                return "庄家/小盲"
            else:
                return "庄家"
        elif player.is_small_blind:
            return "小盲"
        elif player.is_big_blind:
            return "大盲"
        elif total_players > 6:
            # 在大桌子上提供更多位置信息
            dealer_pos = next((p.seat_id for p in player.hole_cards[0] if hasattr(p, 'is_dealer') and p.is_dealer), 0)
            # 简化版位置名称
            return ""
        return ""
    
    def display_pot_info(self, state: GameState):
        """显示底池信息"""
        current_round_bets = sum(p.current_bet for p in state.players)
        total_pot = state.pot + current_round_bets
        
        print(f"💰 当前底池: {self.format_chips(total_pot)}")
        if current_round_bets > 0:
            print(f"   主池: {self.format_chips(state.pot)} + 本轮下注: {self.format_chips(current_round_bets)}")
        
        if state.current_bet > 0:
            print(f"🎯 当前下注线: {self.format_chips(state.current_bet)}")
    
    def display_community_cards(self, state: GameState):
        """显示公共牌"""
        if not state.community_cards:
            return
            
        phase_names = {
            3: "翻牌 (Flop)",
            4: "转牌 (Turn)", 
            5: "河牌 (River)"
        }
        
        phase_name = phase_names.get(len(state.community_cards), "公共牌")
        cards_str = " ".join(card.to_display_str() for card in state.community_cards)
        print(f"🃏 {phase_name}: {cards_str}")
    
    def display_game_state(self, state: GameState):
        """显示游戏状态"""
        self.clear_screen()
        self.print_header(f"德州扑克 - 第{self.game_stats['hands_played'] + 1}手")
        
        # 显示底池和公共牌
        self.display_pot_info(state)
        self.display_community_cards(state)
        
        self.print_separator()
        
        # 显示所有玩家状态
        print("👥 玩家状态:")
        for player in state.players:
            self._display_player_info(player, state)
        
        self.print_separator()
        
        # 显示游戏阶段信息
        if state.phase:
            phase_names = {
                GamePhase.PRE_FLOP: "翻牌前",
                GamePhase.FLOP: "翻牌圈",
                GamePhase.TURN: "转牌圈", 
                GamePhase.RIVER: "河牌圈",
                GamePhase.SHOWDOWN: "摊牌"
            }
            phase_name = phase_names.get(state.phase, str(state.phase))
            print(f"🎮 当前阶段: {phase_name}")
        
        # 显示统计信息
        if self.game_stats['hands_played'] > 0:
            win_rate = (self.game_stats['hands_won'] / self.game_stats['hands_played']) * 100
            print(f"📊 你的统计: {self.game_stats['hands_won']}/{self.game_stats['hands_played']} 胜率{win_rate:.1f}%")
    
    def _display_player_info(self, player: Player, state: GameState):
        """显示单个玩家信息"""
        # 构建玩家状态字符串
        status_icons = {
            SeatStatus.ACTIVE: "🟢",
            SeatStatus.FOLDED: "🔴",
            SeatStatus.ALL_IN: "⭐",
            SeatStatus.OUT: "⚫"
        }
        
        status_icon = status_icons.get(player.status, "❓")
        
        # 位置信息
        position = self.get_position_name(player, len(state.players))
        position_str = f" ({position})" if position else ""
        
        # 当前玩家标记
        current_marker = " ← 当前" if player.seat_id == state.current_player else ""
        
        # 行动信息
        action_str = ""
        if player.last_action_type:
            action_names = {
                ActionType.FOLD: "弃牌",
                ActionType.CHECK: "过牌", 
                ActionType.CALL: "跟注",
                ActionType.BET: "下注",
                ActionType.RAISE: "加注",
                ActionType.ALL_IN: "全押"
            }
            action_name = action_names.get(player.last_action_type, str(player.last_action_type))
            action_str = f" | {action_name}"
        
        # 筹码和下注信息
        chips_str = self.format_chips(player.chips)
        bet_str = f" | 下注: {self.format_chips(player.current_bet)}" if player.current_bet > 0 else ""
        
        # 手牌信息（仅对人类玩家显示）
        if player.seat_id == self.human_seat and player.hole_cards and len(player.hole_cards) == 2:
            cards_str = f" | 手牌: {player.get_hole_cards_str(hidden=False)}"
        elif player.hole_cards and player.status != SeatStatus.OUT:
            cards_str = f" | 手牌: 🂠🂠"  # 隐藏的牌
        else:
            cards_str = ""
        
        print(f"  {status_icon} {player.name}{position_str}: {chips_str}筹码{bet_str}{cards_str}{action_str}{current_marker}")
    
    def get_human_action(self, state: GameState) -> Action:
        """获取人类玩家的行动"""
        current_player = state.get_current_player()
        
        print(f"\n🎯 轮到你行动了！")
        
        # 计算可用行动
        available_actions = self._calculate_available_actions(state, current_player)
        
        if not available_actions:
            print("❌ 没有可用行动！")
            return Action(ActionType.FOLD)
        
        # 显示行动选项
        print("\n📋 可选行动:")
        for i, (action_type, description, amount) in enumerate(available_actions):
            print(f"  {i+1}. {description}")
        
        # 显示建议
        self._show_action_suggestions(state, current_player)
        
        # 获取用户选择
        while True:
            try:
                choice = input("\n👉 请选择行动 (输入数字): ").strip()
                
                if choice.lower() in ['h', 'help', '帮助']:
                    self._show_help()
                    continue
                
                choice_idx = int(choice) - 1
                
                if 0 <= choice_idx < len(available_actions):
                    action_type, _, default_amount = available_actions[choice_idx]
                    
                    # 处理需要输入金额的行动
                    if action_type in [ActionType.BET, ActionType.RAISE]:
                        amount = self._get_bet_amount(state, current_player, action_type, default_amount)
                        return Action(action_type, amount)
                    else:
                        return Action(action_type, default_amount if default_amount else 0)
                else:
                    print("❌ 无效选择，请重新输入")
                    
            except ValueError:
                print("❌ 请输入数字，或输入 'h' 查看帮助")
            except KeyboardInterrupt:
                print("\n👋 退出游戏...")
                sys.exit(0)
    
    def _calculate_available_actions(self, state: GameState, player: Player) -> List[Tuple[ActionType, str, Optional[int]]]:
        """计算可用行动"""
        actions = []
        
        # 弃牌总是可用（除非已经全押且无需追加）
        if not (player.status == SeatStatus.ALL_IN):
            actions.append((ActionType.FOLD, "弃牌", None))
        
        required_amount = state.current_bet - player.current_bet
        
        # 过牌
        if required_amount == 0:
            actions.append((ActionType.CHECK, "过牌", None))
        else:
            # 跟注
            call_amount = min(required_amount, player.chips)
            if call_amount > 0:
                if call_amount == player.chips:
                    actions.append((ActionType.ALL_IN, f"全押跟注 ({self.format_chips(call_amount)})", call_amount))
                else:
                    actions.append((ActionType.CALL, f"跟注 ({self.format_chips(call_amount)})", call_amount))
        
        # 下注/加注
        if required_amount == 0:
            # 可以下注
            min_bet = state.big_blind
            if player.chips >= min_bet:
                actions.append((ActionType.BET, f"下注 (最少{self.format_chips(min_bet)})", min_bet))
        else:
            # 可以加注
            min_raise_amount = state.current_bet + state.big_blind
            if player.chips >= min_raise_amount:
                actions.append((ActionType.RAISE, f"加注 (最少到{self.format_chips(min_raise_amount)})", min_raise_amount))
        
        # 全押（如果不是在跟注全押）
        if player.chips > 0 and required_amount < player.chips:
            actions.append((ActionType.ALL_IN, f"全押 ({self.format_chips(player.chips)})", player.chips))
        
        return actions
    
    def _get_bet_amount(self, state: GameState, player: Player, action_type: ActionType, min_amount: int) -> int:
        """获取下注金额"""
        max_amount = player.chips
        
        if action_type == ActionType.BET:
            prompt = f"💰 请输入下注金额 ({self.format_chips(min_amount)}-{self.format_chips(max_amount)}): "
        else:  # RAISE
            prompt = f"💰 请输入加注到的总金额 ({self.format_chips(min_amount)}-{self.format_chips(max_amount)}): "
        
        # 提供快捷选项
        quick_options = []
        if min_amount <= max_amount:
            quick_options.append(("最小", min_amount))
        
        pot_bet = state.pot + sum(p.current_bet for p in state.players)
        if pot_bet <= max_amount and pot_bet >= min_amount:
            quick_options.append(("底池", pot_bet))
        
        if max_amount >= min_amount:
            quick_options.append(("全押", max_amount))
        
        if quick_options:
            print("💡 快捷选项:", end=" ")
            for i, (name, amount) in enumerate(quick_options):
                print(f"{name}({self.format_chips(amount)})", end="")
                if i < len(quick_options) - 1:
                    print(", ", end="")
            print()
        
        while True:
            try:
                amount_str = input(prompt).strip()
                
                # 检查快捷选项
                for name, amount in quick_options:
                    if amount_str.lower() in [name.lower(), name]:
                        return amount
                
                amount = int(amount_str)
                
                if min_amount <= amount <= max_amount:
                    return amount
                else:
                    print(f"❌ 金额必须在{self.format_chips(min_amount)}-{self.format_chips(max_amount)}之间")
                    
            except ValueError:
                print("❌ 请输入有效的数字或快捷选项")
    
    def _show_action_suggestions(self, state: GameState, player: Player):
        """显示行动建议"""
        if not player.hole_cards or len(player.hole_cards) != 2:
            return
        
        # 简单的手牌力度评估
        card1, card2 = player.hole_cards
        is_pair = card1.rank == card2.rank
        is_suited = card1.suit == card2.suit
        high_cards = sum(1 for card in player.hole_cards if card.rank.value >= 11)  # J, Q, K, A
        
        suggestions = []
        
        if is_pair:
            if card1.rank.value >= 10:  # TT+
                suggestions.append("💪 强牌：建议激进游戏")
            else:
                suggestions.append("👍 中等牌：谨慎游戏")
        elif high_cards == 2:
            suggestions.append("💪 高牌：可以考虑加注")
        elif is_suited and abs(card1.rank.value - card2.rank.value) <= 4:
            suggestions.append("🌈 同花听牌：有潜力")
        elif abs(card1.rank.value - card2.rank.value) <= 4:
            suggestions.append("📈 顺子听牌：有潜力")
        else:
            suggestions.append("😐 普通牌：建议保守")
        
        if suggestions:
            print(f"💡 建议: {suggestions[0]}")
    
    def _show_help(self):
        """显示帮助信息"""
        print("\n" + "="*50)
        print("🆘 德州扑克帮助")
        print("="*50)
        print("基本行动：")
        print("  弃牌(Fold) - 放弃这手牌")
        print("  过牌(Check) - 不下注但继续游戏")
        print("  跟注(Call) - 跟上当前下注")
        print("  下注(Bet) - 主动下注")
        print("  加注(Raise) - 增加下注金额")
        print("  全押(All-in) - 押上所有筹码")
        print("\n游戏阶段：")
        print("  翻牌前 - 只有手牌，进行第一轮下注")
        print("  翻牌 - 发出3张公共牌")
        print("  转牌 - 发出第4张公共牌")
        print("  河牌 - 发出第5张公共牌")
        print("  摊牌 - 比较手牌决定胜负")
        print("="*50)
    
    def get_ai_action(self, state: GameState, player: Player) -> Action:
        """获取AI玩家的行动（改进的策略）"""
        self.debug_print(f"AI {player.name} 开始思考...")
        
        # 模拟思考时间
        time.sleep(0.5)
        
        # 简化的AI策略
        hand_strength = self._evaluate_hand_strength(player, state.community_cards)
        pot_odds = self._calculate_pot_odds(state, player)
        
        self.debug_print(f"AI {player.name} 手牌强度: {hand_strength}, 底池赔率: {pot_odds:.2f}")
        
        # 基于手牌强度和底池赔率做决定
        required_amount = state.current_bet - player.current_bet
        
        if hand_strength >= 0.8:  # 强牌
            if required_amount == 0:
                return self._ai_choose_bet_or_check(state, player, 0.8)
            else:
                if random.random() < 0.9:  # 90%概率跟注或加注
                    return self._ai_choose_call_or_raise(state, player, 0.3)
                else:
                    return Action(ActionType.FOLD)
        
        elif hand_strength >= 0.6:  # 中等牌
            if required_amount == 0:
                return self._ai_choose_bet_or_check(state, player, 0.4)
            else:
                if pot_odds > 2.0:  # 好的底池赔率
                    return self._ai_choose_call_or_raise(state, player, 0.1)
                else:
                    return Action(ActionType.CALL, min(required_amount, player.chips)) if random.random() < 0.6 else Action(ActionType.FOLD)
        
        elif hand_strength >= 0.4:  # 弱牌
            if required_amount == 0:
                return Action(ActionType.CHECK)  # 免费看牌
            else:
                if pot_odds > 3.0 and required_amount <= player.chips * 0.1:  # 很好的赔率且花费不大
                    return Action(ActionType.CALL, min(required_amount, player.chips))
                else:
                    return Action(ActionType.FOLD)
        
        else:  # 很弱的牌
            if required_amount == 0:
                return Action(ActionType.CHECK)  # 免费看牌
            else:
                return Action(ActionType.FOLD)  # 弃牌
    
    def _evaluate_hand_strength(self, player: Player, community_cards: List) -> float:
        """评估手牌强度（简化版）"""
        if not player.hole_cards:
            return 0.0
        
        # 这里应该使用真正的手牌评估器，现在用简化版本
        card1, card2 = player.hole_cards
        
        strength = 0.0
        
        # 对子
        if card1.rank == card2.rank:
            strength += 0.3 + (card1.rank.value / 14.0) * 0.4
        
        # 高牌
        high_card_bonus = max(card1.rank.value, card2.rank.value) / 14.0 * 0.2
        strength += high_card_bonus
        
        # 同花
        if card1.suit == card2.suit:
            strength += 0.1
        
        # 连牌
        if abs(card1.rank.value - card2.rank.value) <= 4:
            strength += 0.1
        
        # 随机因素
        strength += random.uniform(-0.1, 0.1)
        
        return max(0.0, min(1.0, strength))
    
    def _calculate_pot_odds(self, state: GameState, player: Player) -> float:
        """计算底池赔率"""
        required_amount = state.current_bet - player.current_bet
        if required_amount <= 0:
            return float('inf')  # 免费游戏
        
        total_pot = state.pot + sum(p.current_bet for p in state.players)
        return total_pot / required_amount if required_amount > 0 else float('inf')
    
    def _ai_choose_bet_or_check(self, state: GameState, player: Player, aggression: float) -> Action:
        """AI选择下注或过牌"""
        if random.random() < aggression:
            # 选择下注
            min_bet = state.big_blind
            max_bet = min(player.chips, state.pot)  # 最多下注底池大小
            bet_amount = random.randint(min_bet, max(min_bet, max_bet))
            return Action(ActionType.BET, bet_amount)
        else:
            return Action(ActionType.CHECK)
    
    def _ai_choose_call_or_raise(self, state: GameState, player: Player, raise_probability: float) -> Action:
        """AI选择跟注或加注"""
        required_amount = state.current_bet - player.current_bet
        
        if random.random() < raise_probability:
            # 选择加注
            min_raise = state.current_bet + state.big_blind
            if min_raise <= player.chips:
                max_raise = min(player.chips, state.current_bet * 3)
                raise_amount = random.randint(min_raise, max_raise)
                return Action(ActionType.RAISE, raise_amount)
        
        # 默认跟注
        call_amount = min(required_amount, player.chips)
        if call_amount == player.chips:
            return Action(ActionType.ALL_IN, call_amount)
        else:
            return Action(ActionType.CALL, call_amount)
    
    def _rotate_dealer(self, state: GameState):
        """轮换庄家位置到下一个有筹码的玩家"""
        active_players = [p for p in state.players if p.chips > 0]
        if len(active_players) <= 1:
            return
        
        # 按座位号排序
        all_seats = sorted([p.seat_id for p in active_players])
        
        try:
            current_dealer_index = all_seats.index(state.dealer_position)
        except ValueError:
            # 当前庄家已出局，从第一个开始
            current_dealer_index = -1
        
        # 移动到下一个位置
        next_dealer_index = (current_dealer_index + 1) % len(all_seats)
        state.dealer_position = all_seats[next_dealer_index]
        
        # 更新庄家标记
        for player in state.players:
            player.is_dealer = (player.seat_id == state.dealer_position)
        
        new_dealer = state.get_player_by_seat(state.dealer_position)
        self.debug_print(f"庄家轮换到: {new_dealer.name}")
        print(f"🔄 庄家轮换到: {new_dealer.name}")
    
    def run_phase(self, state: GameState, phase) -> Optional:
        """运行一个游戏阶段"""
        phase_names = {
            PreFlopPhase: "翻牌前",
            FlopPhase: "翻牌圈",
            TurnPhase: "转牌圈",
            RiverPhase: "河牌圈",
            ShowdownPhase: "摊牌"
        }
        
        phase_name = phase_names.get(type(phase), type(phase).__name__)
        self.debug_print(f"开始阶段: {phase_name}")
        
        # 进入阶段
        try:
            phase.enter()
        except Exception as e:
            print(f"❌ 阶段初始化失败: {e}")
            return None
        
        # 显示状态
        self.display_game_state(state)
        
        # 如果是摊牌阶段，显示结果并退出
        if isinstance(phase, ShowdownPhase):
            self._display_showdown_results(state)
            return phase.exit()
        
        # 处理下注轮
        self._run_betting_round(state, phase)
        
        return phase.exit()
    
    def _run_betting_round(self, state: GameState, phase):
        """运行下注轮"""
        action_count = 0
        max_actions = len(state.players) * 4  # 防止无限循环
        
        while not state.is_betting_round_complete() and action_count < max_actions:
            current_player = state.get_current_player()
            
            if not current_player:
                self.debug_print("没有当前玩家，下注轮结束")
                break
            
            if not current_player.can_act():
                self.debug_print(f"玩家 {current_player.name} 无法行动")
                if not state.advance_current_player():
                    break
                continue
            
            # 获取玩家行动
            try:
                if current_player.seat_id == self.human_seat:
                    action = self.get_human_action(state)
                    print(f"👤 你选择: {self._format_action(action)}")
                else:
                    action = self.get_ai_action(state, current_player)
                    print(f"🤖 {current_player.name} 选择: {self._format_action(action)}")
                
                # 验证并执行行动
                validated_action = self.validator.validate(state, current_player, action)
                phase.execute_action(current_player, validated_action)
                
                if validated_action.is_converted:
                    print(f"ℹ️  行动被调整: {validated_action.conversion_reason}")
                
                action_count += 1
                
                # 短暂停顿让玩家看清楚
                if current_player.seat_id != self.human_seat:
                    time.sleep(1)
                
                # 推进到下一个玩家
                if not state.advance_current_player():
                    self.debug_print("无法推进到下一个玩家")
                    break
                
                # 更新显示（除非是人类玩家刚刚行动）
                if current_player.seat_id != self.human_seat:
                    self.display_game_state(state)
                
            except InvalidActionError as e:
                if current_player.seat_id == self.human_seat:
                    print(f"❌ 行动无效: {e}")
                    print("请重新选择行动")
                    continue
                else:
                    # AI行动失败，强制弃牌
                    self.debug_print(f"AI {current_player.name} 行动失败，强制弃牌: {e}")
                    fold_action = Action(ActionType.FOLD)
                    try:
                        validated_fold = self.validator.validate(state, current_player, fold_action)
                        phase.execute_action(current_player, validated_fold)
                        state.advance_current_player()
                        action_count += 1
                    except:
                        break
            
            except Exception as e:
                print(f"❌ 意外错误: {e}")
                if current_player.seat_id == self.human_seat:
                    continue
                else:
                    break
        
        if action_count >= max_actions:
            self.debug_print("达到最大行动数限制，强制结束下注轮")
    
    def _format_action(self, action: Action) -> str:
        """格式化行动显示"""
        action_names = {
            ActionType.FOLD: "弃牌",
            ActionType.CHECK: "过牌",
            ActionType.CALL: "跟注",
            ActionType.BET: "下注",
            ActionType.RAISE: "加注",
            ActionType.ALL_IN: "全押"
        }
        
        name = action_names.get(action.action_type, str(action.action_type))
        
        if action.amount and action.amount > 0:
            return f"{name} {self.format_chips(action.amount)}"
        else:
            return name
    
    def _display_showdown_results(self, state: GameState):
        """显示摊牌结果"""
        print("\n🎊 摊牌时刻！")
        self.print_separator("=")
        
        # 显示所有未弃牌玩家的手牌
        active_players = [p for p in state.players if not p.is_folded() and p.status != SeatStatus.OUT]
        
        if len(active_players) > 1:
            print("👥 玩家手牌:")
            for player in active_players:
                if player.hole_cards:
                    cards_str = player.get_hole_cards_str(hidden=False)
                    print(f"  {player.name}: {cards_str}")
        
        # 等待一下让玩家看清楚
        input("\n按回车继续查看结果...")
    
    def play_hand(self, state: GameState, hand_count: int = 1):
        """玩一手牌"""
        self.game_stats['hands_played'] = hand_count
        
        print(f"\n🎰 第 {hand_count} 手牌开始！")
        time.sleep(1)
        
        # 重置游戏状态  
        self._reset_hand(state, hand_count)
        
        # 运行各个阶段
        phases = [
            PreFlopPhase(state),
            FlopPhase(state),
            TurnPhase(state),
            RiverPhase(state),
            ShowdownPhase(state)
        ]
        
        for phase in phases:
            try:
                next_phase = self.run_phase(state, phase)
                
                # 检查是否还有足够玩家继续
                active_players = [p for p in state.players 
                                if not p.is_folded() and p.status != SeatStatus.OUT]
                
                if len(active_players) <= 1:
                    self.debug_print("只剩一个玩家，直接进入摊牌")
                    break
                
                if next_phase is None:
                    break
                    
            except Exception as e:
                print(f"❌ 游戏阶段错误: {e}")
                self.debug_print(f"错误详情: {e}")
                break
        
        # 显示最终结果
        self._show_hand_results(state)
        
        # 检查游戏是否结束
        return self._check_game_continuation(state)
    
    def _reset_hand(self, state: GameState, hand_count: int):
        """重置手牌状态"""
        self.debug_print("重置手牌状态...")
        
        # 重置玩家状态
        for player in state.players:
            player.reset_for_new_hand()
        
        # 重置游戏状态
        state.pot = 0
        state.current_bet = 0
        state.community_cards = []
        state.phase = None
        state.current_player = None
        state.street_index = 0
        state.last_raiser = None
        
        # 轮换庄家（第一手牌除外）
        if hand_count > 1:
            self._rotate_dealer(state)
        else:
            # 第一手牌确保庄家标记正确
            for player in state.players:
                player.is_dealer = (player.seat_id == state.dealer_position)
        
        # 创建新牌组
        state.deck = Deck()
        state.deck.shuffle()
        
        self.debug_print("手牌重置完成")
    
    def _show_hand_results(self, state: GameState):
        """显示手牌结果"""
        print("\n🎉 手牌结束！")
        self.print_separator("=")
        
        # 找出获胜者（简化版）
        winners = []
        for player in state.players:
            if player.chips > 0:
                winners.append(player)
        
        # 更新统计
        human_player = state.get_player_by_seat(self.human_seat)
        if human_player and human_player.chips > 0:
            # 简化的胜利判断
            initial_chips = 1000  # 应该记录初始筹码
            if human_player.chips > initial_chips:
                self.game_stats['hands_won'] += 1
        
        # 显示结果
        biggest_winner = max(state.players, key=lambda p: p.chips)
        if biggest_winner.chips > 0:
            print(f"🏆 本手最大赢家: {biggest_winner.name} ({self.format_chips(biggest_winner.chips)}筹码)")
        
        # 更新最大底池记录
        total_pot = state.pot + sum(p.current_bet for p in state.players)
        if total_pot > self.game_stats['biggest_pot']:
            self.game_stats['biggest_pot'] = total_pot
        
        input("\n按回车继续...")
    
    def _check_game_continuation(self, state: GameState) -> bool:
        """检查游戏是否可以继续"""
        active_players = [p for p in state.players if p.chips > 0]
        
        if len(active_players) <= 1:
            if active_players:
                winner = active_players[0]
                print(f"\n🏆 游戏结束！{winner.name} 赢得了所有筹码！")
                
                if winner.seat_id == self.human_seat:
                    print("🎉 恭喜你获得最终胜利！")
                else:
                    print("😢 很遗憾，你被淘汰了。")
                    
            else:
                print("\n🤔 所有玩家都没有筹码了？这不应该发生...")
            
            self._show_final_stats()
            return False
        
        # 检查是否有玩家破产
        human_player = state.get_player_by_seat(self.human_seat)
        if human_player.chips == 0:
            print(f"\n💸 你的筹码用完了！游戏结束。")
            
            # 询问是否重新开始
            restart = input("是否重新开始游戏？(y/N): ").strip().lower()
            if restart in ['y', 'yes', '是']:
                # 重置所有玩家筹码
                for player in state.players:
                    player.chips = 1000  # 重置为初始筹码
                self.game_stats = {'hands_played': 0, 'hands_won': 0, 'biggest_pot': 0, 'total_winnings': 0}
                return True
            else:
                self._show_final_stats()
                return False
        
        return True
    
    def _show_final_stats(self):
        """显示最终统计"""
        print("\n📊 游戏统计:")
        print(f"  总手数: {self.game_stats['hands_played']}")
        print(f"  胜利手数: {self.game_stats['hands_won']}")
        if self.game_stats['hands_played'] > 0:
            win_rate = (self.game_stats['hands_won'] / self.game_stats['hands_played']) * 100
            print(f"  胜率: {win_rate:.1f}%")
        print(f"  最大底池: {self.format_chips(self.game_stats['biggest_pot'])}")
    
    def run(self):
        """运行游戏主循环"""
        try:
            self.print_header("欢迎来到德州扑克")
            print("🎮 你将与AI玩家进行德州扑克对战")
            print("💡 输入 'h' 或 'help' 查看游戏帮助")
            print("\n准备开始游戏...")
            
            # 获取游戏配置
            num_players, starting_chips, debug_mode = self.get_game_config()
            self.debug_mode = debug_mode
            
            # 创建游戏
            state = self.create_game(num_players, starting_chips)
            
            print(f"\n🎊 游戏创建成功！")
            print(f"👥 玩家: {num_players}人")
            print(f"💰 初始筹码: {self.format_chips(starting_chips)}")
            print(f"🎯 盲注: {state.small_blind}/{state.big_blind}")
            
            input("\n按回车开始游戏...")
            
            # 游戏主循环
            hand_count = 0
            while True:
                hand_count += 1
                
                if not self.play_hand(state, hand_count):
                    break
                
                # 询问是否继续
                try:
                    continue_choice = input("\n🎮 继续下一手牌？(Y/n): ").strip().lower()
                    if continue_choice in ['n', 'no', '否', 'q', 'quit']:
                        break
                except KeyboardInterrupt:
                    print("\n👋 收到退出信号...")
                    break
            
        except KeyboardInterrupt:
            print("\n👋 游戏被中断")
        except Exception as e:
            print(f"\n❌ 游戏出现错误: {e}")
            if self.debug_mode:
                import traceback
                traceback.print_exc()
        finally:
            print("\n🎊 感谢游戏！再见！")


def main():
    """主函数"""
    game = EnhancedCLIGame()
    game.run()


if __name__ == "__main__":
    main() 