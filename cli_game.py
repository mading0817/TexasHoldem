#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克CLI游戏界面 v3.0 - Phase 4 优化版
提供完整的德州扑克游戏体验，支持人类玩家与AI对战
包含详细的游戏信息显示、智能错误处理和丰富的用户交互

Phase 4 重构说明：
- 完全清理对Domain层的直接访问，全部通过Controller快照获取
- 优化性能和代码架构一致性
- 为多前端支持做准备
"""

import os
import sys
import random
import time
from typing import List, Optional, Tuple, Dict

# 应用控制器导入 - 核心接口
from app_controller.poker_controller import PokerController
from app_controller.dto_models import (
    GameStateSnapshot, 
    PlayerActionInput, 
    ActionResult, 
    ActionResultType,
    GameEvent, 
    GameEventType
)

# 核心枚举类型 - 仅导入必要的枚举
from core_game_logic.core.enums import ActionType, SeatStatus, GamePhase
from core_game_logic.core.exceptions import InvalidActionError

# Phase类导入 - 用于Phase判断
from core_game_logic.phases import (
    PreFlopPhase, FlopPhase, TurnPhase, RiverPhase, ShowdownPhase
)

# Phase 3: AI决策引擎
from ai_players import AIDecisionEngine, AIPlayerProfile, setup_demo_ais, get_global_event_bus, EventLogger

# 临时保留的Domain导入 - 仅用于创建初始状态
from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player


class EnhancedCLIGame:
    """增强版CLI德州扑克游戏 - Phase 4 优化版本
    
    Phase 4 优化重点：
    - 完全移除对Domain的直接访问，全部通过Controller快照
    - 所有游戏状态信息都从快照获取，确保数据一致性
    - 为多前端支持做准备的接口收敛
    """
    
    def __init__(self):
        # Controller将在create_game中初始化
        self.controller: Optional[PokerController] = None
        
        # Phase 3: AI决策引擎
        self.ai_engine: Optional[AIDecisionEngine] = None
        self.event_logger: Optional[EventLogger] = None
        
        # 保持UI相关属性
        self.human_seat = 0  # 人类玩家座位
        self.game_stats = {
            'hands_played': 0,
            'hands_won': 0,
            'biggest_pot': 0,
            'total_winnings': 0
        }
        self.debug_mode = False  # 可配置的调试模式
        
        # 缓存最后已知的状态版本，用于增量更新优化
        self._last_known_version: Optional[int] = None
        
        # Phase 4 新增：性能缓存
        self._cached_snapshot: Optional[GameStateSnapshot] = None
        
    def clear_screen(self):
        """清屏功能"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str):
        """打印格式化的标题"""
        print("\n" + "="*80)
        print(f"[*] {title.center(76)} [*]")
        print("="*80)
    
    def print_separator(self, char="-", length=60):
        """打印分隔线"""
        print(char * length)
    
    def debug_print(self, message: str):
        """条件调试输出"""
        if self.debug_mode:
            print(f"[DEBUG] {message}")
    
    def _get_current_snapshot(self, force_refresh: bool = False) -> Optional[GameStateSnapshot]:
        """获取当前游戏状态快照，支持缓存优化
        
        Args:
            force_refresh: 强制刷新快照，忽略缓存
            
        Returns:
            当前游戏状态快照，如果无变化则返回None
        """
        if not self.controller:
            return None
            
        if force_refresh or self._cached_snapshot is None:
            self._cached_snapshot = self.controller.get_state_snapshot(
                viewer_seat=self.human_seat,
                last_known_version=self._last_known_version
            )
            if self._cached_snapshot:
                self._last_known_version = self._cached_snapshot.version
        
        return self._cached_snapshot
    
    def _initialize_ai_engine(self, num_players: int):
        """初始化AI决策引擎
        
        Args:
            num_players: 总玩家数量，用于确定AI玩家座位
        """
        try:
            # 导入AI引擎工厂函数
            from ai_players import create_standard_ai_engine, setup_demo_ais
            
            # 创建AI决策引擎
            self.ai_engine = create_standard_ai_engine()
            
            # 设置事件日志器
            event_bus = get_global_event_bus()
            self.event_logger = EventLogger()
            event_bus.subscribe('*', self.event_logger.handle_event)
            
            # 为除人类玩家外的所有座位设置AI
            ai_seats = [i for i in range(num_players) if i != self.human_seat]
            setup_demo_ais(self.ai_engine, ai_seats)
            
            self.debug_print(f"AI引擎初始化完成，管理{len(ai_seats)}个AI玩家")
            
        except Exception as e:
            print(f"WARNING: AI引擎初始化失败: {e}")
            print("  游戏将使用简单AI回退策略")
            self.ai_engine = None
            self.event_logger = None
    
    def get_game_config(self) -> Tuple[int, int, bool]:
        """获取游戏配置"""
        self.print_header("游戏配置")
        
        # 获取玩家数量
        while True:
            try:
                num_str = input("> 请输入玩家数量 (2-10，默认4): ").strip()
                if not num_str:
                    num_players = 4
                else:
                    num_players = int(num_str)
                
                if 2 <= num_players <= 10:
                    break
                else:
                    print("ERROR: 玩家数量必须在2-10之间")
            except ValueError:
                print("ERROR: 请输入有效的数字")
        
        # 获取初始筹码
        while True:
            try:
                chips_str = input("> 请输入初始筹码 (默认1000): ").strip()
                if not chips_str:
                    starting_chips = 1000
                else:
                    starting_chips = int(chips_str)
                
                if starting_chips >= 10:  # 至少要能支付几轮盲注
                    break
                else:
                    print("ERROR: 初始筹码必须至少为10")
            except ValueError:
                print("ERROR: 请输入有效的数字")
        
        # 是否开启调试模式
        debug_str = input("> 是否开启调试模式？(y/N): ").strip().lower()
        debug_mode = debug_str in ['y', 'yes', '是']
        
        return num_players, starting_chips, debug_mode
        
    def create_game(self, num_players: int = 4, starting_chips: int = 1000) -> None:
        """创建新游戏，初始化PokerController
        
        Args:
            num_players: 玩家数量
            starting_chips: 初始筹码
            
        注意：重构后返回None，Controller存储在self.controller中
        """
        self.debug_print(f"创建游戏: {num_players}个玩家, 初始筹码{starting_chips}")
        
        players = []
        
        # 创建人类玩家
        human_name = input("> 请输入你的姓名 (默认'You'): ").strip()
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
        
        # 创建初始游戏状态
        initial_state = GameState(
            players=players,
            dealer_position=0,
            small_blind=5,  # 增加盲注让游戏更有趣
            big_blind=10
        )
        
        # 创建Controller并存储 - Phase 1 核心变更
        self.controller = PokerController(initial_state)
        
        # Phase 3 新增：初始化AI决策引擎
        self._initialize_ai_engine(num_players)
        
        # 重置版本缓存
        self._last_known_version = None
        
        self.debug_print(f"PokerController 创建完成, 庄家位置: {initial_state.dealer_position}")
        self.debug_print(f"盲注设置: 小盲{initial_state.small_blind}, 大盲{initial_state.big_blind}")
        self.debug_print(f"Controller版本: {self.controller.version}")
        
        # 显示AI配置
        if self.ai_engine:
            registered_ais = self.ai_engine.get_registered_ais()
            self.debug_print(f"已注册{len(registered_ais)}个AI玩家:")
            for ai_info in registered_ais:
                self.debug_print(f"  座位{ai_info['seat_id']}: {ai_info['name']} ({ai_info['strategy_type']})")
    
    def format_chips(self, amount: int) -> str:
        """格式化筹码显示"""
        if amount >= 1000:
            return f"{amount:,}"
        return str(amount)
    
    def get_position_name(self, player_snapshot: 'PlayerSnapshot', total_players: int) -> str:
        """获取玩家位置名称 - Phase 4 优化：从快照获取数据"""
        if player_snapshot.is_dealer:
            if total_players == 2:
                return "庄家/小盲"
            else:
                return "庄家"
        elif player_snapshot.is_small_blind:
            return "小盲"
        elif player_snapshot.is_big_blind:
            return "大盲"
        elif total_players > 6:
            # 在大桌子上提供更多位置信息（简化版）
            return ""
        return ""
    
    def display_pot_info(self, snapshot: GameStateSnapshot = None):
        """显示底池信息 - Phase 4 优化：从快照获取数据"""
        if snapshot is None:
            snapshot = self._get_current_snapshot()
            if snapshot is None:
                return
                
        current_round_bets = sum(p.current_bet for p in snapshot.players)
        total_pot = snapshot.pot + current_round_bets
        
        print(f"POT: {self.format_chips(total_pot)}")
        if current_round_bets > 0:
            print(f"   主池: {self.format_chips(snapshot.pot)} + 本轮下注: {self.format_chips(current_round_bets)}")
        
        if snapshot.current_bet > 0:
            print(f"当前下注线: {self.format_chips(snapshot.current_bet)}")
    
    def display_community_cards(self, snapshot: GameStateSnapshot = None):
        """显示公共牌 - Phase 4 优化：从快照获取数据"""
        if snapshot is None:
            snapshot = self._get_current_snapshot()
            if snapshot is None:
                return
                
        if not snapshot.community_cards:
            return
            
        phase_names = {
            3: "翻牌 (Flop)",
            4: "转牌 (Turn)", 
            5: "河牌 (River)"
        }
        
        phase_name = phase_names.get(len(snapshot.community_cards), "公共牌")
        cards_str = " ".join(snapshot.community_cards)  # 快照中已经是字符串格式
        print(f"CARDS {phase_name}: {cards_str}")
    
    def display_game_state(self, state: GameState):
        """显示游戏状态"""
        self.clear_screen()
        self.print_header(f"德州扑克 - 第{self.game_stats['hands_played'] + 1}手")
        
        # 显示底池和公共牌
        self.display_pot_info()
        self.display_community_cards()
        
        self.print_separator()
        
        # 显示所有玩家状态
        print("PLAYERS:")
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
            print(f"PHASE: {phase_name}")
        
        # 显示统计信息
        if self.game_stats['hands_played'] > 0:
            win_rate = (self.game_stats['hands_won'] / self.game_stats['hands_played']) * 100
            print(f"STATS: {self.game_stats['hands_won']}/{self.game_stats['hands_played']} 胜率{win_rate:.1f}%")
    
    def _display_player_info(self, player: Player, state: GameState):
        """显示单个玩家信息"""
        # 构建玩家状态字符串
        status_icons = {
            SeatStatus.ACTIVE: "[A]",
            SeatStatus.FOLDED: "[F]",
            SeatStatus.ALL_IN: "[*]",
            SeatStatus.OUT: "[X]"
        }
        
        status_icon = status_icons.get(player.status, "[?]")
        
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
    
    def get_human_action(self, snapshot: GameStateSnapshot = None) -> PlayerActionInput:
        """获取人类玩家的行动 - Phase 4 优化：通过快照获取数据"""
        if snapshot is None:
            snapshot = self._get_current_snapshot(force_refresh=True)
            if snapshot is None:
                print("ERROR: 无法获取游戏状态")
                return PlayerActionInput(
                    seat_id=self.human_seat,
                    action_type=ActionType.FOLD
                )
        
        current_player_snapshot = snapshot.get_player_snapshot(snapshot.current_player)
        if not current_player_snapshot:
            print("ERROR: 无法获取当前玩家信息")
            return PlayerActionInput(
                seat_id=self.human_seat,
                action_type=ActionType.FOLD
            )
        
        print(f"\n> 轮到你行动了！")
        
        # 通过Controller获取可用行动（而非计算）
        available_actions = self._get_available_actions_from_controller(snapshot.current_player)
        
        if not available_actions:
            print("ERROR: 没有可用行动！")
            return PlayerActionInput(
                seat_id=current_player_snapshot.seat_id,
                action_type=ActionType.FOLD
            )
        
        # 显示行动选项
        print("\n📋 可选行动:")
        for i, (action_type, description, amount) in enumerate(available_actions):
            print(f"  {i+1}. {description}")
        
        # 显示建议
        self._show_action_suggestions_from_snapshot(snapshot, current_player_snapshot)
        
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
                        amount = self._get_bet_amount_from_snapshot(snapshot, current_player_snapshot, action_type, default_amount)
                        return PlayerActionInput(
                            seat_id=current_player_snapshot.seat_id,
                            action_type=action_type,
                            amount=amount
                        )
                    else:
                        return PlayerActionInput(
                            seat_id=current_player_snapshot.seat_id,
                            action_type=action_type,
                            amount=default_amount if default_amount else 0
                        )
                else:
                    print("❌ 无效选择，请重新输入")
                    
            except ValueError:
                print("❌ 请输入数字，或输入 'h' 查看帮助")
            except KeyboardInterrupt:
                print("\n👋 退出游戏...")
                sys.exit(0)
    
    def _get_available_actions_from_controller(self, seat_id: int) -> List[Tuple[ActionType, str, Optional[int]]]:
        """通过Controller获取可用行动 - Phase 4 新增方法"""
        if not self.controller:
            return []
        
        try:
            actions_detail = self.controller.get_available_actions_detail(seat_id)
            
            # 转换为CLI需要的格式
            actions = []
            for action_info in actions_detail:
                action_type = action_info["action_type"]
                display_name = action_info["display_name"]
                amount = action_info.get("amount")
                
                actions.append((action_type, display_name, amount))
            
            return actions
        except Exception as e:
            self.debug_print(f"获取可用行动失败: {e}")
            return []
    
    def _get_bet_amount_from_snapshot(self, snapshot: GameStateSnapshot, player_snapshot: GameStateSnapshot, action_type: ActionType, min_amount: int) -> int:
        """获取下注金额 - Phase 4 新增方法"""
        max_amount = player_snapshot.chips
        
        if action_type == ActionType.BET:
            prompt = f"💰 请输入下注金额 ({self.format_chips(min_amount)}-{self.format_chips(max_amount)}): "
        else:  # RAISE
            prompt = f"💰 请输入加注到的总金额 ({self.format_chips(min_amount)}-{self.format_chips(max_amount)}): "
        
        # 提供快捷选项
        quick_options = []
        if min_amount <= max_amount:
            quick_options.append(("最小", min_amount))
        
        pot_bet = snapshot.pot + sum(p.current_bet for p in snapshot.players)
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
    
    def _show_action_suggestions_from_snapshot(self, snapshot: GameStateSnapshot, player_snapshot: GameStateSnapshot):
        """显示行动建议 - Phase 4 新增方法"""
        if not player_snapshot.hole_cards or len(player_snapshot.hole_cards) != 2:
            return
        
        # 简单的手牌力度评估
        card1, card2 = player_snapshot.hole_cards
        is_pair = card1.rank == card2.rank
        is_suited = card1.suit == card2.suit
        high_cards = sum(1 for card in player_snapshot.hole_cards if card.rank.value >= 11)  # J, Q, K, A
        
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
    
    def get_ai_action(self, player_snapshot: 'PlayerSnapshot', snapshot: GameStateSnapshot = None) -> PlayerActionInput:
        """获取AI玩家的行动 - Phase 4 优化：通过快照获取数据
        
        Args:
            player_snapshot: AI玩家的快照信息
            snapshot: 当前游戏状态快照（可选）
            
        Returns:
            AI决策的行动输入
        """
        if snapshot is None:
            snapshot = self._get_current_snapshot(force_refresh=True)
            if snapshot is None:
                return self._get_emergency_fallback_action_from_snapshot(player_snapshot)
        
        self.debug_print(f"AI {player_snapshot.name} (座位{player_snapshot.seat_id}) 开始决策...")
        
        try:
            # 优先使用AI决策引擎
            if self.ai_engine and player_snapshot.seat_id in self.ai_engine.ai_strategies:
                return self._get_ai_action_from_engine(player_snapshot, snapshot)
            else:
                # 回退到旧的简化AI逻辑
                self.debug_print(f"AI引擎不可用，使用回退策略")
                return self._get_ai_action_fallback_from_snapshot(player_snapshot, snapshot)
                
        except Exception as e:
            self.debug_print(f"AI决策出错: {e}")
            # 最终回退：保守策略
            return self._get_emergency_fallback_action_from_snapshot(player_snapshot)
    
    def _get_ai_action_from_engine(self, player_snapshot: 'PlayerSnapshot', snapshot: GameStateSnapshot) -> PlayerActionInput:
        """通过AI决策引擎获取AI行动 - Phase 4 优化"""
        if not self.controller:
            raise RuntimeError("Controller未初始化")
        
        # 获取AI的底牌（如果可用）
        hole_cards = player_snapshot.hole_cards if hasattr(player_snapshot, 'hole_cards') and player_snapshot.hole_cards else None
        
        # 通过AI引擎获取决策
        action_input = self.ai_engine.get_ai_decision(
            snapshot=snapshot,
            seat_id=player_snapshot.seat_id,
            hole_cards=hole_cards
        )
        
        self.debug_print(f"AI引擎决策结果: {action_input.action_type.name}"
                        + (f" {action_input.amount}" if action_input.amount else ""))
        
        # 显示AI决策的元数据（如果启用调试）
        if self.debug_mode and action_input.metadata:
            strategy_type = action_input.metadata.get('strategy_type', '未知')
            hand_strength = action_input.metadata.get('hand_strength', '未知')
            pot_odds = action_input.metadata.get('pot_odds', '未知')
            thinking_time = action_input.metadata.get('thinking_time', '未知')
            
            self.debug_print(f"  策略类型: {strategy_type}")
            self.debug_print(f"  手牌强度: {hand_strength}")
            self.debug_print(f"  底池赔率: {pot_odds}")
            self.debug_print(f"  思考时间: {thinking_time:.2f}秒" if isinstance(thinking_time, (int, float)) else f"  思考时间: {thinking_time}")
        
        return action_input
    
    def _get_ai_action_fallback_from_snapshot(self, player_snapshot: 'PlayerSnapshot', snapshot: GameStateSnapshot) -> PlayerActionInput:
        """回退到简化AI逻辑 - Phase 4 优化：从快照获取数据"""
        self.debug_print(f"使用回退AI策略为 {player_snapshot.name}")
        
        # 模拟思考时间
        time.sleep(0.5)
        
        # 简化的AI策略（使用快照数据）
        hand_strength = self._evaluate_hand_strength_from_snapshot(player_snapshot, snapshot.community_cards)
        pot_odds = self._calculate_pot_odds_from_snapshot(snapshot, player_snapshot)
        
        self.debug_print(f"回退策略分析 - 手牌强度: {hand_strength:.2f}, 底池赔率: {pot_odds:.2f}")
        
        # 基于手牌强度和底池赔率做决定
        required_amount = snapshot.current_bet - player_snapshot.current_bet
        
        if hand_strength >= 0.7:  # 强牌
            if required_amount == 0:
                return self._ai_choose_bet_or_check_from_snapshot(snapshot, player_snapshot, 0.6)
            else:
                if random.random() < 0.8:  # 80%概率跟注或加注
                    return self._ai_choose_call_or_raise_from_snapshot(snapshot, player_snapshot, 0.3)
                else:
                    return PlayerActionInput(
                        seat_id=player_snapshot.seat_id,
                        action_type=ActionType.FOLD
                    )
        elif hand_strength >= 0.4:  # 中等牌
            if required_amount == 0:
                return self._ai_choose_bet_or_check_from_snapshot(snapshot, player_snapshot, 0.3)
            else:
                call_amount = min(required_amount, player_snapshot.chips)
                action_type = ActionType.ALL_IN if call_amount == player_snapshot.chips else ActionType.CALL
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=action_type,
                    amount=call_amount
                )
        else:  # 弱牌
            # 根据底池赔率考虑是否跟注
            if required_amount == 0:
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=ActionType.CHECK
                )
            elif pot_odds > 4.0 and required_amount <= player_snapshot.chips * 0.1:  # 很好的赔率且花费不大
                call_amount = min(required_amount, player_snapshot.chips)
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=ActionType.CALL,
                    amount=call_amount
                )
            else:
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=ActionType.FOLD
                )
    
    def _get_emergency_fallback_action_from_snapshot(self, player_snapshot: 'PlayerSnapshot') -> PlayerActionInput:
        """紧急回退行动 - Phase 4 优化：从快照获取数据"""
        self.debug_print(f"使用紧急回退策略为 {player_snapshot.name}")
        
        # 最保守的策略：过牌或弃牌
        return PlayerActionInput(
            seat_id=player_snapshot.seat_id,
            action_type=ActionType.FOLD
        )
    
    def _rotate_dealer(self):
        """
        轮换庄家位置 - Phase 1 重构：通过Controller调用
        移除直接的状态操作，改为调用Controller API
        """
        if not self.controller:
            self.debug_print("Controller未初始化，无法轮换庄家")
            return
        
        try:
            result = self.controller.advance_dealer()
            if result.success:
                # 显示轮换结果信息
                for event in result.events:
                    if event.event_type == GameEventType.DEALER_ROTATION:
                        print(f"🔄 {event.message}")
                        break
                
                self.debug_print(f"庄家轮换成功: {result.message}")
            else:
                self.debug_print(f"庄家轮换失败: {result.message}")
                print(f"❌ 庄家轮换失败: {result.message}")
        except Exception as e:
            self.debug_print(f"庄家轮换异常: {e}")
            print(f"❌ 庄家轮换异常: {e}")
    
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
        self._run_betting_round()
        
        return phase.exit()
    
    def _run_betting_round(self) -> None:
        """
        运行下注轮 - Phase 4 优化：通过Controller处理整个下注轮
        现在只需要提供获取玩家行动的回调函数，完全不访问Controller.state
        """
        if not self.controller:
            raise ValueError("Controller未初始化")
        
        def get_player_action_callback(seat_id: int, snapshot: GameStateSnapshot) -> PlayerActionInput:
            """获取玩家行动的回调函数 - Phase 4 优化"""
            player_snapshot = snapshot.get_player_snapshot(seat_id)
            
            if seat_id == self.human_seat:
                # 人类玩家：获取用户输入
                action_input = self.get_human_action(snapshot)
                print(f"👤 你选择: {self._format_action_input(action_input)}")
                return action_input
            else:
                # AI玩家：调用AI策略
                if not player_snapshot:
                    # 回退行动
                    return PlayerActionInput(seat_id=seat_id, action_type=ActionType.FOLD)
                    
                action_input = self.get_ai_action(player_snapshot, snapshot)
                player_name = player_snapshot.name if player_snapshot else f"玩家{seat_id}"
                print(f"🤖 {player_name} 选择: {self._format_action_input(action_input)}")
                
                # AI行动后稍作停顿和更新显示
                time.sleep(1)
                self.display_game_state_from_controller()
                
                return action_input
        
        # 通过Controller处理整个下注轮
        try:
            result = self.controller.process_betting_round(get_player_action_callback)
            
            if result.success:
                self.debug_print(f"下注轮完成: {result.message}")
                if result.events:
                    for event in result.events:
                        if event.event_type == GameEventType.WARNING:
                            print(f"⚠️  {event.message}")
                        elif "转换" in event.message:
                            print(f"ℹ️  {event.message}")
            else:
                # 下注轮处理失败
                if result.result_type == ActionResultType.INVALID_ACTION:
                    print(f"❌ 行动无效: {result.message}")
                    print("请重新选择行动")
                    # 对于人类玩家的错误，可以重试
                    self._run_betting_round()
                else:
                    print(f"❌ 下注轮处理错误: {result.message}")
                    
        except Exception as e:
            print(f"❌ 下注轮发生意外错误: {e}")
            self.debug_print(f"下注轮异常: {e}")
    
    def _run_betting_round_legacy(self) -> None:
        """
        运行下注轮 - 原有实现（作为备用）
        
        !WARNING! 此方法直接访问Controller.state，应避免使用
        推荐使用_run_betting_round()方法
        """
        if not self.controller:
            raise ValueError("Controller未初始化")
        
        action_count = 0
        max_actions = 50  # 防止无限循环护栏 - Phase 4 硬编码数值而非依赖state
        
        while not self.controller.is_betting_round_complete() and action_count < max_actions:
            # 获取当前行动玩家的座位号
            current_seat = self.controller.get_current_player_seat()
            
            if current_seat is None:
                self.debug_print("没有当前玩家，下注轮结束")
                break
            
            # 从快照获取当前玩家信息（而非直接访问state）
            snapshot = self.controller.get_state_snapshot()
            current_player_snapshot = snapshot.get_player_snapshot(current_seat)
            
            if not current_player_snapshot or current_player_snapshot.status not in [SeatStatus.ACTIVE]:
                self.debug_print(f"玩家 {current_seat} 无法行动")
                # 这种情况应该由Controller内部处理，这里只是保护
                break
            
            # 获取玩家行动
            try:
                if current_seat == self.human_seat:
                    action_input = self.get_human_action(snapshot)
                    print(f"👤 你选择: {self._format_action_input(action_input)}")
                else:
                    action_input = self.get_ai_action(current_player_snapshot, snapshot)
                    player_name = current_player_snapshot.name
                    print(f"🤖 {player_name} 选择: {self._format_action_input(action_input)}")
                
                # 通过Controller执行行动（原子性操作）
                result = self.controller.execute_player_action(action_input)
                
                if result.success:
                    # 显示转换信息（如果有）
                    if result.events:
                        for event in result.events:
                            if "转换" in event.message:
                                print(f"ℹ️  行动被调整: {event.message}")
                    
                    action_count += 1
                    
                    # 短暂停顿让玩家看清楚
                    if current_seat != self.human_seat:
                        time.sleep(1)
                    
                    # 更新显示（除非是人类玩家刚刚行动）
                    if current_seat != self.human_seat:
                        self.display_game_state_from_controller()
                else:
                    # 行动执行失败
                    if result.result_type == ActionResultType.INVALID_ACTION:
                        print(f"❌ 行动无效: {result.message}")
                        print("请重新选择行动")
                        # 对于人类玩家的错误，可以重试（AI错误则跳过）
                        if current_seat == self.human_seat:
                            continue
                        else:
                            # AI行动出错，使用保守策略
                            fallback_action = PlayerActionInput(
                                seat_id=current_seat,
                                action_type=ActionType.FOLD
                            )
                            result = self.controller.execute_player_action(fallback_action)
                            if result.success:
                                print(f"🤖 玩家{current_seat} 由于错误自动弃牌")
                                action_count += 1
                    else:
                        print(f"❌ 行动处理错误: {result.message}")
                        break
                        
            except Exception as e:
                print(f"❌ 处理玩家行动时发生错误: {e}")
                self.debug_print(f"玩家行动异常: {e}")
                
                # 回退处理
                if current_seat != self.human_seat:
                    try:
                        fallback_action = PlayerActionInput(
                            seat_id=current_seat,
                            action_type=ActionType.FOLD
                        )
                        self.controller.execute_player_action(fallback_action)
                        print(f"🤖 玩家{current_seat} 由于错误自动弃牌")
                        action_count += 1
                    except:
                        break
                else:
                    break
        
        if action_count >= max_actions:
            self.debug_print("达到最大行动数限制，强制结束下注轮")
            print("⚠️  下注轮达到最大行动数限制")

    def display_game_state_from_controller(self):
        """从Controller获取快照并显示游戏状态 - Phase 1 新增方法"""
        if not self.controller:
            return
        
        snapshot = self.controller.get_state_snapshot(
            viewer_seat=self.human_seat,  # 只对人类玩家显示手牌
            last_known_version=self._last_known_version
        )
        
        if snapshot is None:
            # 状态无变化，无需重新显示
            return
        
        self._last_known_version = snapshot.version
        
        self.clear_screen()
        self.print_header(f"德州扑克 - 第{self.game_stats['hands_played'] + 1}手")
        
        # 显示底池信息
        self.display_pot_info(snapshot)
        self.display_community_cards(snapshot)
        
        self.print_separator()
        
        # 显示所有玩家状态
        print("PLAYERS:")
        for player_snapshot in snapshot.players:
            self._display_player_info_from_snapshot(player_snapshot, snapshot)
        
        self.print_separator()
        
        # 显示游戏阶段信息
        phase_names = {
            GamePhase.PRE_FLOP: "翻牌前",
            GamePhase.FLOP: "翻牌圈",
            GamePhase.TURN: "转牌圈", 
            GamePhase.RIVER: "河牌圈",
            GamePhase.SHOWDOWN: "摊牌"
        }
        phase_name = phase_names.get(snapshot.phase, str(snapshot.phase))
        print(f"PHASE: {phase_name}")
        
        # 显示统计信息
        if self.game_stats['hands_played'] > 0:
            win_rate = (self.game_stats['hands_won'] / self.game_stats['hands_played']) * 100
            print(f"STATS: {self.game_stats['hands_won']}/{self.game_stats['hands_played']} 胜率{win_rate:.1f}%")

    def _format_action_input(self, action_input: PlayerActionInput) -> str:
        """格式化行动输入显示 - Phase 1 新增方法"""
        action_names = {
            ActionType.FOLD: "弃牌",
            ActionType.CHECK: "过牌",
            ActionType.CALL: "跟注",
            ActionType.BET: "下注",
            ActionType.RAISE: "加注",
            ActionType.ALL_IN: "全下"
        }
        
        action_name = action_names.get(action_input.action_type, str(action_input.action_type))
        
        if action_input.amount and action_input.amount > 0:
            return f"{action_name} {self.format_chips(action_input.amount)}"
        else:
            return action_name

    def _display_player_info_from_snapshot(self, player_snapshot, game_snapshot):
        """从快照显示玩家信息 - Phase 1 新增方法"""
        # 状态指示符
        status_symbols = {
            SeatStatus.ACTIVE: "[A]",
            SeatStatus.FOLDED: "[F]",
            SeatStatus.ALL_IN: "[*]",
            SeatStatus.OUT: "[X]"
        }
        
        status_symbol = status_symbols.get(player_snapshot.status, "[?]")
        
        # 位置标记
        position_marks = []
        if player_snapshot.is_dealer:
            position_marks.append("D")
        if player_snapshot.is_small_blind:
            position_marks.append("SB")
        if player_snapshot.is_big_blind:
            position_marks.append("BB")
        
        position_str = f"[{'/'.join(position_marks)}]" if position_marks else ""
        
        # 当前玩家指示
        current_indicator = "👈" if game_snapshot.current_player_seat == player_snapshot.seat_id else "  "
        
        # 手牌显示
        hand_str = player_snapshot.hole_cards_display
        
        # 下注信息
        bet_info = ""
        if player_snapshot.current_bet > 0:
            bet_info = f" (本轮: {self.format_chips(player_snapshot.current_bet)})"
        
        print(f"{current_indicator} {status_symbol} 座位{player_snapshot.seat_id}: {player_snapshot.name} {position_str}")
        print(f"     💰 {self.format_chips(player_snapshot.chips)}{bet_info}")
        if hand_str != "** **":  # 只有在能看到手牌时才显示
            print(f"     🃏 {hand_str}")
        
        # 显示最后行动
        if player_snapshot.last_action:
            print(f"     ⚡ {player_snapshot.last_action}")

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
    
    def play_hand(self, hand_count: int = 1):
        """玩一手牌"""
        self.game_stats['hands_played'] = hand_count
        
        print(f"\n🎰 第 {hand_count} 手牌开始！")
        time.sleep(1)
        
        # 重置游戏状态  
        self._reset_hand(hand_count)
        
        # 运行各个阶段
        phases = [
            PreFlopPhase(self.controller.state),
            FlopPhase(self.controller.state),
            TurnPhase(self.controller.state),
            RiverPhase(self.controller.state),
            ShowdownPhase(self.controller.state)
        ]
        
        for phase in phases:
            try:
                next_phase = self.run_phase(phase)
                
                # 检查是否还有足够玩家继续
                active_players = self.controller.get_active_players()
                
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
        self._show_hand_results()
        
        # 检查游戏是否结束
        return self._check_game_continuation()
    
    def _reset_hand(self, hand_count: int):
        """
        重置手牌状态 - Phase 1 重构：通过Controller处理
        移除state参数，通过self.controller管理手牌重置
        """
        if not self.controller:
            self.debug_print("Controller未初始化，无法重置手牌")
            return
        
        self.debug_print("开始重置手牌状态...")
        
        # 轮换庄家（第一手牌除外）
        if hand_count > 1:
            self._rotate_dealer()
        
        # 通过Controller开始新手牌（原子性操作）
        result = self.controller.start_new_hand()
        
        if result.success:
            self.debug_print("手牌重置完成")
            # 显示事件信息
            if result.events:
                for event in result.events:
                    self.debug_print(f"事件: {event.message}")
        else:
            self.debug_print(f"手牌重置失败: {result.message}")
            print(f"❌ 手牌重置失败: {result.message}")
            raise RuntimeError(f"无法开始新手牌: {result.message}")
    
    def _show_hand_results(self):
        """显示手牌结果 - Phase 1 重构：通过Controller快照获取结果"""
        if not self.controller:
            return
        
        print("\n🎉 手牌结束！")
        self.print_separator("=")
        
        # 从Controller获取游戏状态快照
        snapshot = self.controller.get_state_snapshot()
        
        if not snapshot:
            print("❌ 无法获取游戏结果")
            return
        
        # 找出活跃玩家
        active_players = snapshot.get_active_players()
        
        # 更新统计
        human_snapshot = snapshot.get_player_snapshot(self.human_seat)
        if human_snapshot and human_snapshot.chips > 0:
            # 简化的胜利判断 - 如果玩家筹码增加则计为胜利
            initial_chips = 1000  # 应该记录初始筹码，这里使用默认值
            if human_snapshot.chips > initial_chips:
                self.game_stats['hands_won'] += 1
        
        # 显示结果
        if active_players:
            biggest_winner = max(active_players, key=lambda p: p.chips)
            print(f"🏆 本手最大赢家: {biggest_winner.name} ({self.format_chips(biggest_winner.chips)}筹码)")
        
        # 更新最大底池记录 
        if snapshot.pot > self.game_stats['biggest_pot']:
            self.game_stats['biggest_pot'] = snapshot.pot
        
        input("\n按回车继续...")
    
    def _check_game_continuation(self) -> bool:
        """检查游戏是否可以继续 - Phase 1 重构：通过Controller快照检查"""
        if not self.controller:
            return False
        
        # 从Controller获取当前状态快照
        snapshot = self.controller.get_state_snapshot()
        if not snapshot:
            return False
        
        # 获取活跃玩家（有筹码的玩家）
        active_players = [p for p in snapshot.players if p.chips > 0]
        
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
        
        # 检查人类玩家是否破产
        human_snapshot = snapshot.get_player_snapshot(self.human_seat)
        if human_snapshot and human_snapshot.chips == 0:
            print(f"\n💸 你的筹码用完了！游戏结束。")
            
            # 询问是否重新开始
            restart = input("是否重新开始游戏？(y/N): ").strip().lower()
            if restart in ['y', 'yes', '是']:
                # 通过Controller重新初始化游戏（这需要在Controller中实现reset方法）
                # 目前先用简单方式：重新创建游戏
                num_players = len(snapshot.players)
                self.create_game(num_players, 1000)  # 重置为初始筹码
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
        """运行游戏主循环 - Phase 4 优化：减少对Controller.state的直接访问"""
        try:
            # 获取游戏配置
            num_players, starting_chips, debug_mode = self.get_game_config()
            self.debug_mode = debug_mode
            
            # 创建游戏
            self.create_game(num_players, starting_chips)
            
            # 显示游戏信息
            snapshot = self._get_current_snapshot(force_refresh=True)
            if snapshot:
                print(f"\n🎮 游戏开始！")
                print(f"🎯 盲注: {snapshot.small_blind}/{snapshot.big_blind}")
                print(f"👥 玩家: {len(snapshot.players)}人")
                print(f"💰 初始筹码: {self.format_chips(starting_chips)}")
                
                if self.debug_mode:
                    print("🔧 调试模式已启用")
            
            # 游戏主循环
            hand_count = 0
            while True:
                hand_count += 1
                self.game_stats['hands_played'] = hand_count
                
                try:
                    print(f"\n{'='*60}")
                    print(f"🃏 第 {hand_count} 手牌开始")
                    print(f"{'='*60}")
                    
                    # 玩家手牌
                    self.play_hand(hand_count)
                    
                    # 显示手牌结果
                    self._show_hand_results()
                    
                    # 检查游戏是否继续
                    if not self._check_game_continuation():
                        break
                        
                except KeyboardInterrupt:
                    print("\n\n🛑 游戏被中断")
                    
                    # 询问是否保存并退出
                    save_choice = input("是否保存当前游戏状态？(y/N): ").strip().lower()
                    if save_choice in ['y', 'yes', '是']:
                        # TODO: 实现游戏状态保存功能
                        print("💾 游戏状态保存功能尚未实现")
                    
                    print("👋 感谢游戏！")
                    break
                    
                except Exception as e:
                    print(f"\n❌ 游戏过程中发生错误: {e}")
                    if self.debug_mode:
                        import traceback
                        traceback.print_exc()
                    
                    # 询问是否继续
                    continue_choice = input("是否继续游戏？(y/N): ").strip().lower()
                    if continue_choice not in ['y', 'yes', '是']:
                        break
                        
        except Exception as e:
            print(f"❌ 游戏初始化失败: {e}")
            if self.debug_mode:
                import traceback
                traceback.print_exc()
        
        finally:
            print("\n🎊 感谢游戏！再见！")

    def _evaluate_hand_strength_from_snapshot(self, player_snapshot: 'PlayerSnapshot', community_cards: List[str]) -> float:
        """评估手牌强度 - Phase 4 新增：从快照获取数据
        
        Args:
            player_snapshot: 玩家快照
            community_cards: 公共牌（字符串格式）
            
        Returns:
            手牌强度评分 (0.0-1.0)
        """
        if not player_snapshot.hole_cards or len(player_snapshot.hole_cards) != 2:
            return 0.0
        
        # 简化的手牌评估逻辑
        # 这里应该实现真正的牌型计算，目前使用简化版本
        card1, card2 = player_snapshot.hole_cards
        
        # 基础评分
        score = 0.0
        
        # 对子加分
        if card1.rank == card2.rank:
            score += 0.3
            # 高对加分
            if card1.rank.value >= 10:  # 10以上
                score += 0.2
        
        # 高牌加分
        high_card_value = max(card1.rank.value, card2.rank.value)
        score += min(high_card_value / 14.0, 0.3)  # 最多0.3分
        
        # 同花可能性
        if card1.suit == card2.suit:
            score += 0.1
        
        # 顺子可能性（简化版本）
        rank_diff = abs(card1.rank.value - card2.rank.value)
        if rank_diff <= 4:
            score += 0.05
        
        return min(score, 1.0)
    
    def _calculate_pot_odds_from_snapshot(self, snapshot: GameStateSnapshot, player_snapshot: 'PlayerSnapshot') -> float:
        """计算底池赔率 - Phase 4 新增：从快照获取数据"""
        required_call = snapshot.current_bet - player_snapshot.current_bet
        if required_call <= 0:
            return float('inf')  # 不需要跟注
        
        total_pot = snapshot.pot + sum(p.current_bet for p in snapshot.players)
        
        return total_pot / required_call if required_call > 0 else float('inf')
    
    def _ai_choose_bet_or_check_from_snapshot(self, snapshot: GameStateSnapshot, player_snapshot: 'PlayerSnapshot', aggression: float) -> PlayerActionInput:
        """AI选择下注或过牌 - Phase 4 新增：从快照获取数据"""
        if random.random() < aggression:
            # 选择下注
            bet_amount = min(snapshot.big_blind * 2, player_snapshot.chips)
            if bet_amount > 0:
                return PlayerActionInput(
                    seat_id=player_snapshot.seat_id,
                    action_type=ActionType.BET,
                    amount=bet_amount
                )
        
        # 选择过牌
        return PlayerActionInput(
            seat_id=player_snapshot.seat_id,
            action_type=ActionType.CHECK
        )
    
    def _ai_choose_call_or_raise_from_snapshot(self, snapshot: GameStateSnapshot, player_snapshot: 'PlayerSnapshot', raise_probability: float) -> PlayerActionInput:
        """AI选择跟注或加注 - Phase 4 新增：从快照获取数据"""
        required_call = snapshot.current_bet - player_snapshot.current_bet
        
        if random.random() < raise_probability and player_snapshot.chips > required_call + snapshot.big_blind:
            # 选择加注
            min_raise = snapshot.current_bet + snapshot.big_blind
            max_raise = min(min_raise * 3, player_snapshot.chips)
            raise_amount = random.randint(min_raise, max_raise)
            
            return PlayerActionInput(
                seat_id=player_snapshot.seat_id,
                action_type=ActionType.RAISE,
                amount=raise_amount
            )
        else:
            # 选择跟注
            call_amount = min(required_call, player_snapshot.chips)
            action_type = ActionType.ALL_IN if call_amount == player_snapshot.chips else ActionType.CALL
            
            return PlayerActionInput(
                seat_id=player_snapshot.seat_id,
                action_type=action_type,
                amount=call_amount
            )


def main():
    """主函数"""
    game = EnhancedCLIGame()
    game.run()


if __name__ == "__main__":
    main() 