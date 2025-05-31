#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克CLI游戏界面 - 自动化测试版本
基于Phase 5 MVC纯化架构，专门配置为全AI自动对战测试
用于自动化测试、性能分析、统计收集和日志输出
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
    德州扑克CLI界面类 - 自动化测试版本
    
    配置：
    - 固定4个AI玩家：所有玩家都使用AI决策进行自动对战
    - 固定初始筹码：1000
    - 支持调试模式
    - 用于自动化测试、统计分析和日志输出
    """
    
    def __init__(self):
        """初始化CLI界面 - 自动化测试版本"""
        self.controller: Optional[PokerController] = None
        self.debug_mode = True  # 默认开启调试模式，便于测试观察
        self.human_seat = None  # 自动化测试版本不再需要人类玩家座位
        self.player_name = "TestAI_0"  # 默认AI玩家名
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
        """收集游戏配置，自动化测试版本 - 无需用户输入"""
        
        # 自动化测试配置 - 固定参数，便于测试
        num_players = 4  # 固定4个玩家进行测试
        starting_chips = 1000  # 固定初始筹码1000
        debug_mode = True  # 默认开启调试模式，便于观察测试过程
        player_name = "TestAI_0"  # 将原来的人类玩家也改为AI玩家
        
        print(f"\n=== 自动化测试配置 ===")
        print(f"玩家数量: {num_players} (全AI玩家)")
        print(f"初始筹码: {starting_chips}")
        print(f"调试模式: {'开启' if debug_mode else '关闭'}")
        print(f"测试配置: 4个AI玩家进行自动对战")
        print(f"========================")
        
        return num_players, starting_chips, debug_mode, player_name
    
    def create_game(self, num_players: int = 4, starting_chips: int = 1000, player_name: str = "TestAI_0") -> None:
        """创建游戏 - 自动化测试版本，所有玩家都是AI"""
        # 创建玩家列表：所有玩家都是AI，使用不同的AI策略配置
        players = []
        for i in range(num_players):
            if i == 0:
                name = player_name  # 第一个AI使用传入的名称
            else:
                name = f"TestAI_{i}"
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
        print(f"玩家数量: {num_players} (全AI自动对战)")
        print(f"初始筹码: {self.format_chips(starting_chips)}")
        print(f"盲注: {5}/{10}")
        print(f"AI玩家配置: {', '.join([f'{p.name}(座位{p.seat_id})' for p in players])}")
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
        
        # 显示当前行动AI玩家的手牌信息（自动化测试版本）
        if snapshot.current_player_seat is not None and snapshot.current_player_seat < len(snapshot.players):
            current_player = snapshot.players[snapshot.current_player_seat]
            if current_player.hole_cards_display and current_player.hole_cards_display != "隐藏":
                print(f"\n当前行动玩家 {current_player.name} 的手牌: {current_player.hole_cards_display}")
        
        if self.debug_mode:
            print(f"[DEBUG] 当前玩家座位: {snapshot.current_player_seat}")
            print(f"[DEBUG] 自动化测试模式 - 所有玩家都是AI")
    
    # ==============================================
    # 玩家行动处理
    # ==============================================
    
    def get_player_action(self, request: PlayerActionRequest) -> PlayerActionInput:
        """获取玩家行动 - PokerController回调方法 (自动化测试版本，所有玩家都使用AI决策)"""
        
        # 添加调试输出
        if self.debug_mode:
            print(f"[DEBUG] get_player_action被调用: 座位{request.seat_id} ({request.player_name})")
            print(f"[DEBUG] 自动化测试模式 - 所有玩家使用AI决策")
        
        # 显示当前游戏状态（每次行动前更新）
        self.display_game_state()
        
        # 自动化测试版本：所有玩家都使用AI决策
        # 原来的人类玩家(座位0)现在也使用AI决策，便于自动化测试
        if self.debug_mode:
            print(f"[DEBUG] 为座位{request.seat_id}获取AI决策")
        return self.get_ai_decision(request)
    
    # get_human_action方法已删除 - 自动化测试版本不再需要人类输入
    # 所有玩家现在都使用AI决策逻辑
    
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
        """显示最终统计 - 自动化测试版本"""
        print(f"\n" + "="*60)
        print(f"自动化测试统计报告")
        print(f"="*60)
        print(f"总手牌数: {self.stats['hands_played']}")
        print(f"TestAI_0获胜手牌: {self.stats['hands_won']}")
        if self.stats['hands_played'] > 0:
            win_rate = (self.stats['hands_won'] / self.stats['hands_played']) * 100
            print(f"TestAI_0胜率: {win_rate:.1f}%")
        print(f"TestAI_0总盈亏: {self.format_chips(self.stats['total_winnings'])}")
        
        # 显示最终游戏状态
        if self.controller:
            snapshot = self.controller.get_state_snapshot()
            print(f"\n最终玩家状态:")
            for player in snapshot.players:
                print(f"  {player.name}: {self.format_chips(player.chips)} 筹码")
        
        print(f"="*60)
        print(f"自动化测试完成")
    
    # ==============================================
    # 主运行方法
    # ==============================================
    
    def run(self):
        """运行CLI游戏 - 自动化测试版本"""
        try:
            # 获取游戏配置 (自动化测试配置)
            num_players, starting_chips, debug_mode, player_name = self.get_game_config()
            self.debug_mode = debug_mode
            
            # 创建游戏
            self.create_game(num_players, starting_chips, player_name)
            
            print(f"\n=== 开始自动化测试 ===")
            print(f"将自动运行多手牌进行测试...")
            
            # 自动化测试参数
            max_hands = 10  # 最多测试10手牌
            auto_delay = 1.0  # 每手牌之间的延迟（秒）
            
            # 游戏主循环 - 自动化版本
            hand_count = 0
            while self.check_game_continuation() and hand_count < max_hands:
                hand_count += 1
                print(f"\n{'='*60}")
                print(f"自动化测试 - 第 {hand_count}/{max_hands} 手牌")
                print(f"{'='*60}")
                
                self.play_hand()
                
                if self.check_game_continuation() and hand_count < max_hands:
                    print(f"\n等待 {auto_delay} 秒后继续下一手...")
                    time.sleep(auto_delay)
                else:
                    break
            
            # 显示最终统计
            print(f"\n=== 自动化测试完成 ===")
            print(f"总共完成 {hand_count} 手牌测试")
            self.display_final_stats()
            
        except KeyboardInterrupt:
            print(f"\n\n自动化测试被中断")
            if self.stats['hands_played'] > 0:
                self.display_final_stats()
        except Exception as e:
            print(f"\n自动化测试出现错误: {e}")
            if self.debug_mode:
                import traceback
                traceback.print_exc()


def main():
    """主函数"""
    game = TexasHoldemCLI()
    game.run()


if __name__ == "__main__":
    main() 