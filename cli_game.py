#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克CLI游戏界面 - 3AI+1用户玩家配置版本
基于Phase 5 MVC纯化架构，专门配置为固定4人游戏
"""

import os
import sys
import time
from typing import List, Optional, Tuple

# 应用控制器导入 - 核心接口
from app_controller.poker_controller import PokerController
from app_controller.dto_models import (
    GameStateSnapshot, 
    PlayerActionInput, 
    PlayerActionRequest,
    HandResult,
    GameEvent, 
    GameEventType,
    PlayerSnapshot
)

# 核心枚举类型
from core_game_logic.core.enums import ActionType, SeatStatus, GamePhase
from core_game_logic.core.exceptions import InvalidActionError

# 临时导入用于初始化
from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player


class TexasHoldemCLI:
    """
    德州扑克CLI界面类 - 固定配置版本
    
    配置：
    - 固定4个玩家：1个用户玩家(座位0) + 3个AI玩家(座位1,2,3)
    - 固定初始筹码：1000
    - 支持调试模式
    """
    
    def __init__(self):
        """初始化CLI界面"""
        self.controller: Optional[PokerController] = None
        self.debug_mode = False
        self.human_seat = 0  # 用户玩家固定座位0
        self.player_name = "TestPlayer"  # 默认玩家名
        self.stats = {
            'hands_played': 0,
            'hands_won': 0,
            'total_winnings': 0
        }
    
    # ==============================================
    # UI工具方法
    # ==============================================
    
    def clear_screen(self):
        """清空屏幕"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str):
        """打印标题"""
        print(f"\n{'='*60}")
        print(f"{title:^60}")
        print(f"{'='*60}")
    
    def print_separator(self, char="-", length=60):
        """打印分隔线"""
        print(char * length)
    
    def debug_print(self, message: str):
        """调试输出"""
        if self.debug_mode:
            print(f"[DEBUG] {message}")
    
    def format_chips(self, amount: int) -> str:
        """格式化筹码显示"""
        return f"{amount:,}" if amount else "0"
    
    # ==============================================
    # 游戏配置收集 - 兼容test_input.txt
    # ==============================================
    
    def get_game_config(self) -> Tuple[int, int, bool, str]:
        """收集游戏配置，兼容test_input.txt格式"""
        
        # 获取玩家数量 (test_input.txt第1行: 4)
        while True:
            try:
                num_players_input = input("请输入玩家数量 (2-8，默认4): ").strip()
                if not num_players_input:
                    num_players = 4
                else:
                    num_players = int(num_players_input)
                if 2 <= num_players <= 8:
                    break
                print("玩家数量必须在2-8之间")
            except ValueError:
                print("请输入有效数字")
        
        # 获取初始筹码 (test_input.txt第2行: 1000)
        while True:
            try:
                chips_input = input("请输入初始筹码 (默认1000): ").strip()
                if not chips_input:
                    starting_chips = 1000
                else:
                    starting_chips = int(chips_input)
                if starting_chips > 0:
                    break
                print("初始筹码必须大于0")
            except ValueError:
                print("请输入有效数字")
        
        # 调试模式 (test_input.txt第3行: y/n)
        debug_choice = input("是否开启调试模式？(y/N): ").strip().lower()
        debug_mode = debug_choice in ['y', 'yes']
        
        # 玩家名称 (test_input.txt第4行: TestPlayer)
        player_name = input("请输入您的玩家名称 (默认TestPlayer): ").strip()
        if not player_name:
            player_name = "TestPlayer"
        
        return num_players, starting_chips, debug_mode, player_name
    
    def create_game(self, num_players: int = 4, starting_chips: int = 1000, player_name: str = "TestPlayer") -> None:
        """创建游戏"""
        # 创建玩家列表：座位0为用户，其他为AI
        players = []
        for i in range(num_players):
            if i == 0:
                name = player_name
            else:
                name = f"AI_{i}"
            players.append(Player(seat_id=i, name=name, chips=starting_chips))
        
        # 创建初始状态，设置标准盲注
        initial_state = GameState(players=players, small_blind=5, big_blind=10)
        
        # 设置初始庄家（默认选择座位0作为第一个庄家）
        initial_state.dealer_position = 0
        if players:
            players[0].is_dealer = True
        
        # 创建Controller
        self.controller = PokerController(initial_state)
        self.player_name = player_name
        
        print(f"\n游戏创建成功！")
        print(f"玩家数量: {num_players}")
        print(f"初始筹码: {self.format_chips(starting_chips)}")
        print(f"盲注: {5}/{10}")
        print(f"{player_name} (座位0) vs {num_players-1}个AI对手")
        print(f"初始庄家: {player_name} (座位0)")
    
    # ==============================================
    # 游戏状态显示
    # ==============================================
    
    def display_game_state(self):
        """显示当前游戏状态"""
        snapshot = self.controller.get_state_snapshot()
        
        print(f"\n当前阶段: {snapshot.phase}")
        print(f"有效底池: {self.format_chips(snapshot.pot)}")
        
        if snapshot.current_bet > 0:
            print(f"当前下注: {self.format_chips(snapshot.current_bet)}")
        
        # 显示公共牌 - 修复Unicode显示问题
        if snapshot.community_cards:
            # 使用to_str()而不是to_display_str()避免Unicode符号
            cards_str = " ".join(snapshot.community_cards)
            print(f"公共牌: {cards_str}")
        
        print(f"\n玩家状态:")
        
        for player in snapshot.players:
            status_mark = " <- 当前玩家" if player.seat_id == snapshot.current_player_seat else ""
            action_mark = ""
            # 游戏开始就在PRE_FLOP阶段，可以显示弃牌和全下状态
            if player.status == SeatStatus.FOLDED:
                action_mark = " [已弃牌]"
            elif player.status == SeatStatus.ALL_IN:
                action_mark = " [全下]"
            
            # 显示玩家的当前下注信息
            bet_info = ""
            if player.current_bet > 0:
                bet_info = f" (下注:{self.format_chips(player.current_bet)})"
            
            print(f"  座位{player.seat_id}: {player.name} - 筹码:{self.format_chips(player.chips)}{bet_info}{action_mark}{status_mark}")
        
        # 显示用户手牌 - 修复Unicode显示问题
        if self.human_seat < len(snapshot.players):
            human_player = snapshot.players[self.human_seat]
            if human_player.hole_cards_display and human_player.hole_cards_display != "隐藏":
                print(f"\n您的手牌: {human_player.hole_cards_display}")
        
        if self.debug_mode:
            print(f"[DEBUG] 当前玩家座位: {snapshot.current_player_seat}")
            print(f"[DEBUG] 人类玩家座位: {self.human_seat}")
    
    # ==============================================
    # 玩家行动处理
    # ==============================================
    
    def get_player_action(self, request: PlayerActionRequest) -> PlayerActionInput:
        """获取玩家行动 - PokerController回调方法"""
        
        # 添加调试输出
        if self.debug_mode:
            print(f"[DEBUG] get_player_action被调用: 座位{request.seat_id} ({request.player_name})")
            print(f"[DEBUG] human_seat = {self.human_seat}")
            print(f"[DEBUG] request.seat_id == self.human_seat: {request.seat_id == self.human_seat}")
        
        # 显示当前游戏状态（每次行动前更新）
        self.display_game_state()
        
        if request.seat_id == self.human_seat:
            # 用户玩家
            if self.debug_mode:
                print(f"[DEBUG] 进入人类玩家分支")
            return self.get_human_action(request)
        else:
            # AI玩家
            if self.debug_mode:
                print(f"[DEBUG] 进入AI玩家分支")
            return self.get_ai_decision(request)
    
    def get_human_action(self, request: PlayerActionRequest) -> PlayerActionInput:
        """获取用户行动输入"""
        
        # 显示可用行动
        print(f"\n您的回合 - 可用行动:")
        action_map = {}
        for i, action_type in enumerate(request.available_actions, 1):
            action_name = {
                ActionType.FOLD: "弃牌",
                ActionType.CHECK: "过牌", 
                ActionType.CALL: "跟注",
                ActionType.BET: "下注",
                ActionType.RAISE: "加注",
                ActionType.ALL_IN: "全下"
            }.get(action_type, str(action_type))
            
            action_map[i] = action_type
            
            # 显示额外信息
            extra_info = ""
            if action_type == ActionType.CALL:
                call_amount = request.current_bet_to_call
                extra_info = f" ({self.format_chips(call_amount)})"
            elif action_type in [ActionType.BET, ActionType.RAISE]:
                min_bet = max(request.snapshot.current_bet * 2, 
                             request.snapshot.big_blind) if action_type == ActionType.RAISE else request.snapshot.big_blind
                extra_info = f" (最少{self.format_chips(min_bet)})"
            
            print(f"  {i}. {action_name}{extra_info}")
        
        # 获取用户选择 (兼容test_input.txt第5-6行)
        while True:
            try:
                choice_input = input(f"请选择行动 (1-{len(action_map)}): ").strip()
                if not choice_input:
                    continue
                    
                choice = int(choice_input)
                if choice in action_map:
                    selected_action = action_map[choice]
                    break
                print(f"请选择1-{len(action_map)}之间的数字")
            except ValueError:
                print("请输入有效数字")
        
        # 处理需要金额的行动
        amount = 0
        if selected_action in [ActionType.BET, ActionType.RAISE]:
            while True:
                try:
                    amount_input = input("请输入金额: ").strip()
                    if not amount_input:
                        continue
                    amount = int(amount_input)
                    if amount > 0:
                        break
                    print("金额必须大于0")
                except ValueError:
                    print("请输入有效数字")
        
        return PlayerActionInput(seat_id=request.seat_id, action_type=selected_action, amount=amount)
    
    def get_ai_decision(self, request: PlayerActionRequest) -> PlayerActionInput:
        """获取AI决策"""
        
        try:
            # 添加调试输出
            if self.debug_mode:
                print(f"[DEBUG] 获取AI决策: 座位{request.seat_id}")
                print(f"[DEBUG] 可用行动: {request.available_actions}")
            
            # 使用Controller的AI决策方法
            decision = self.controller.get_ai_decision(request.seat_id, request.snapshot)
            
            # 显示AI决策
            ai_player = request.snapshot.get_player_snapshot(request.seat_id)
            ai_name = ai_player.name if ai_player else f"AI_{request.seat_id}"
            
            action_name = {
                ActionType.FOLD: "弃牌",
                ActionType.CHECK: "过牌",
                ActionType.CALL: "跟注", 
                ActionType.BET: "下注",
                ActionType.RAISE: "加注",
                ActionType.ALL_IN: "全下"
            }.get(decision.action_type, str(decision.action_type))
            
            print(f"{ai_name} 选择: {action_name}" + (f" {self.format_chips(decision.amount)}" if decision.amount else ""))
            
            if self.debug_mode:
                print(f"[DEBUG] AI决策完成: {decision.action_type}")
            
            return decision
            
        except Exception as e:
            print(f"[ERROR] AI决策异常: {e}")
            if self.debug_mode:
                import traceback
                traceback.print_exc()
            # 返回弃牌作为安全选择
            return PlayerActionInput(seat_id=request.seat_id, action_type=ActionType.FOLD)
    
    # ==============================================
    # 游戏流程控制
    # ==============================================
    
    def play_hand(self):
        """游戏一手牌"""
        if not self.controller:
            print("游戏未初始化")
            return
        
        try:
            print(f"\n" + "="*60)
            print(f"开始第 {self.stats['hands_played'] + 1} 手牌")
            print(f"="*60)
            
            # 使用Controller的高级API
            result = self.controller.play_full_hand(self.get_player_action)
            
            # 显示结果
            self.display_hand_result(result)
            
            # 更新统计
            self.stats['hands_played'] += 1
            if result.winners and self.human_seat in result.winners:
                self.stats['hands_won'] += 1
                if self.human_seat in result.pot_distribution:
                    self.stats['total_winnings'] += result.pot_distribution[self.human_seat]
            
        except Exception as e:
            print(f"手牌过程出错: {e}")
            if self.debug_mode:
                import traceback
                traceback.print_exc()
    
    def display_hand_result(self, result: HandResult):
        """显示手牌结果"""
        print(f"\n" + "="*60)
        print(f"手牌结束")
        print(f"="*60)
        
        if result.winners:
            print(f"获胜者:")
            snapshot = self.controller.get_state_snapshot()
            for winner_seat in result.winners:
                # 从pot_distribution中获取该座位的奖金
                winning_amount = result.pot_distribution.get(winner_seat, 0)
                # 从快照中获取玩家名称
                winner_player = next((p for p in snapshot.players if p.seat_id == winner_seat), None)
                winner_name = winner_player.name if winner_player else f"玩家{winner_seat}"
                print(f"  座位{winner_seat}: {winner_name} - 赢得 {self.format_chips(winning_amount)}")
        
        # 显示最终状态
        self.display_game_state()
    
    def check_game_continuation(self) -> bool:
        """检查游戏是否应该继续"""
        if not self.controller:
            return False
        
        snapshot = self.controller.get_state_snapshot()
        active_players = [p for p in snapshot.players if p.chips > 0]
        
        if len(active_players) < 2:
            print(f"\n游戏结束 - 只剩{len(active_players)}个有筹码的玩家")
            return False
        
        return True
    
    def display_final_stats(self):
        """显示最终统计"""
        print(f"\n" + "="*60)
        print(f"游戏统计")
        print(f"="*60)
        print(f"总手牌数: {self.stats['hands_played']}")
        print(f"获胜手牌: {self.stats['hands_won']}")
        if self.stats['hands_played'] > 0:
            win_rate = (self.stats['hands_won'] / self.stats['hands_played']) * 100
            print(f"胜率: {win_rate:.1f}%")
        print(f"总盈亏: {self.format_chips(self.stats['total_winnings'])}")
    
    # ==============================================
    # 主运行方法
    # ==============================================
    
    def run(self):
        """运行CLI游戏"""
        try:
            # 获取游戏配置 (兼容test_input.txt)
            num_players, starting_chips, debug_mode, player_name = self.get_game_config()
            self.debug_mode = debug_mode
            
            # 创建游戏
            self.create_game(num_players, starting_chips, player_name)
            
            print(f"\n按Enter开始游戏，按Ctrl+C退出...")
            start_choice = input().strip().lower()
            
            # 游戏主循环
            while self.check_game_continuation():
                self.play_hand()
                
                if self.check_game_continuation():
                    print(f"\n按Enter继续下一手，按Ctrl+C退出...")
                    continue_choice = input().strip().lower()
                    # test_input.txt第7行: n (不继续)
                    if continue_choice == 'n':
                        print("游戏结束")
                        break
            
            # 显示最终统计
            self.display_final_stats()
            
        except KeyboardInterrupt:
            print(f"\n\n游戏退出")
            if self.stats['hands_played'] > 0:
                self.display_final_stats()
        except Exception as e:
            print(f"\n游戏出现错误: {e}")
            if self.debug_mode:
                import traceback
                traceback.print_exc()


def main():
    """主函数"""
    game = TexasHoldemCLI()
    game.run()


if __name__ == "__main__":
    main() 