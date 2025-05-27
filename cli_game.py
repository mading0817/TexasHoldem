#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克CLI游戏界面
支持人类玩家与AI玩家对战
"""

import random
from typing import List, Optional

from core_game_logic.game_state import GameState
from core_game_logic.player import Player
from core_game_logic.enums import ActionType, Action, SeatStatus
from core_game_logic.action_validator import ActionValidator
from core_game_logic.phases import PreFlopPhase, FlopPhase, TurnPhase, RiverPhase, ShowdownPhase
from core_game_logic.deck import Deck


class CLIGame:
    """CLI德州扑克游戏"""
    
    def __init__(self):
        self.validator = ActionValidator()
        self.human_seat = 0  # 人类玩家座位
        
    def create_game(self, num_players: int = 3, starting_chips: int = 100) -> GameState:
        """创建新游戏"""
        players = []
        
        # 创建人类玩家
        human_player = Player(
            seat_id=self.human_seat,
            name="You",
            chips=starting_chips
        )
        players.append(human_player)
        
        # 创建AI玩家
        ai_names = ["Alice", "Bob", "Charlie", "David", "Eve"]
        for i in range(1, num_players):
            ai_player = Player(
                seat_id=i,
                name=ai_names[i-1] if i-1 < len(ai_names) else f"AI{i}",
                chips=starting_chips
            )
            players.append(ai_player)
        
        # 创建游戏状态
        state = GameState(
            players=players,
            dealer_position=0,
            small_blind=1,
            big_blind=2
        )
        
        return state
    
    def display_game_state(self, state: GameState):
        """显示游戏状态"""
        print("\n" + "="*60)
        print(f"底池: {state.pot} | 当前下注: {state.current_bet}")
        
        # 显示公共牌
        if state.community_cards:
            community_str = " ".join(card.to_str() for card in state.community_cards)
            print(f"公共牌: {community_str}")
        
        print("-" * 60)
        
        # 显示所有玩家状态
        for player in state.players:
            status_str = ""
            if player.status == SeatStatus.FOLDED:
                status_str = " [弃牌]"
            elif player.status == SeatStatus.ALL_IN:
                status_str = " [全押]"
            
            # 人类玩家显示手牌，AI玩家隐藏
            if player.seat_id == self.human_seat:
                cards_str = player.get_hole_cards_str(hidden=False)
            else:
                cards_str = player.get_hole_cards_str(hidden=True)
            
            current_marker = " <-- 当前玩家" if player.seat_id == state.current_player else ""
            
            print(f"{player.name}: {player.chips}筹码 | 当前下注: {player.current_bet} | 手牌: {cards_str}{status_str}{current_marker}")
        
        print("="*60)
    
    def get_human_action(self, state: GameState) -> Action:
        """获取人类玩家的行动"""
        current_player = state.get_current_player()
        
        print(f"\n轮到你行动！")
        print("可选行动:")
        
        # 显示可用行动
        actions = []
        
        # 弃牌总是可用
        actions.append((ActionType.FOLD, "弃牌"))
        
        # 检查是否可以过牌
        if state.current_bet == current_player.current_bet:
            actions.append((ActionType.CHECK, "过牌"))
        else:
            # 需要跟注
            call_amount = state.current_bet - current_player.current_bet
            if call_amount <= current_player.chips:
                actions.append((ActionType.CALL, f"跟注 ({call_amount})"))
        
        # 下注/加注
        if state.current_bet == 0:
            # 可以下注
            min_bet = state.big_blind
            if min_bet <= current_player.chips:
                actions.append((ActionType.BET, f"下注 (最少{min_bet})"))
        else:
            # 可以加注
            min_raise = state.current_bet * 2
            if min_raise <= current_player.chips:
                actions.append((ActionType.RAISE, f"加注 (最少到{min_raise})"))
        
        # 全押
        if current_player.chips > 0:
            actions.append((ActionType.ALL_IN, f"全押 ({current_player.chips})"))
        
        # 显示选项
        for i, (action_type, description) in enumerate(actions):
            print(f"{i+1}. {description}")
        
        # 获取用户输入
        while True:
            try:
                choice = input("请选择行动 (输入数字): ").strip()
                choice_idx = int(choice) - 1
                
                if 0 <= choice_idx < len(actions):
                    action_type, _ = actions[choice_idx]
                    
                    # 如果是下注或加注，需要输入金额
                    if action_type in [ActionType.BET, ActionType.RAISE]:
                        amount_str = input("请输入金额: ").strip()
                        amount = int(amount_str)
                        return Action(action_type, amount)
                    else:
                        return Action(action_type)
                else:
                    print("无效选择，请重新输入")
            except (ValueError, KeyboardInterrupt):
                print("无效输入，请输入数字")
    
    def get_ai_action(self, state: GameState, player: Player) -> Action:
        """获取AI玩家的行动（简单随机策略）"""
        # 简单的随机策略
        actions = []
        
        # 30%概率弃牌
        if random.random() < 0.3:
            return Action(ActionType.FOLD)
        
        # 检查是否可以过牌
        if state.current_bet == player.current_bet:
            actions.append(ActionType.CHECK)
        else:
            # 需要跟注
            call_amount = state.current_bet - player.current_bet
            if call_amount <= player.chips:
                actions.append(ActionType.CALL)
        
        # 20%概率下注/加注
        if random.random() < 0.2:
            if state.current_bet == 0:
                # 下注
                min_bet = state.big_blind
                if min_bet <= player.chips:
                    actions.append(ActionType.BET)
            else:
                # 加注
                min_raise = state.current_bet * 2
                if min_raise <= player.chips:
                    actions.append(ActionType.RAISE)
        
        # 5%概率全押
        if random.random() < 0.05 and player.chips > 0:
            return Action(ActionType.ALL_IN)
        
        # 选择一个行动
        if actions:
            action_type = random.choice(actions)
            
            if action_type == ActionType.BET:
                amount = random.randint(state.big_blind, min(player.chips, state.big_blind * 3))
                return Action(action_type, amount)
            elif action_type == ActionType.RAISE:
                min_raise = state.current_bet * 2
                max_raise = min(player.chips, state.current_bet * 3)
                amount = random.randint(min_raise, max_raise)
                return Action(action_type, amount)
            else:
                return Action(action_type)
        
        # 默认弃牌
        return Action(ActionType.FOLD)
    
    def run_phase(self, state: GameState, phase) -> Optional:
        """运行一个游戏阶段"""
        phase.enter()
        self.display_game_state(state)
        
        # 如果是摊牌阶段，直接退出
        if isinstance(phase, ShowdownPhase):
            return phase.exit()
        
        # 处理玩家行动
        continuing = True
        while continuing:
            current_player = state.get_current_player()
            if not current_player or not current_player.can_act():
                break
            
            # 获取玩家行动
            if current_player.seat_id == self.human_seat:
                action = self.get_human_action(state)
            else:
                action = self.get_ai_action(state, current_player)
                print(f"\n{current_player.name} 选择: {action}")
            
            # 验证并执行行动
            try:
                validated_action = self.validator.validate(state, current_player, action)
                continuing = phase.act(validated_action)
                
                if validated_action.is_converted:
                    print(f"行动被转换: {validated_action.conversion_reason}")
                
                # 更新显示
                if continuing:
                    self.display_game_state(state)
                
            except Exception as e:
                print(f"行动执行失败: {e}")
                if current_player.seat_id == self.human_seat:
                    continue  # 人类玩家重新选择
                else:
                    # AI玩家默认弃牌
                    validated_action = self.validator.validate(state, current_player, Action(ActionType.FOLD))
                    continuing = phase.act(validated_action)
        
        return phase.exit()
    
    def play_hand(self, state: GameState):
        """玩一手牌"""
        print("\n🎰 开始新的一手牌！")
        
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
        
        # 创建新牌组
        state.deck = Deck()
        state.deck.shuffle()
        
        # 运行各个阶段
        phase = PreFlopPhase(state)
        
        while phase is not None:
            phase = self.run_phase(state, phase)
        
        print("\n🎉 这手牌结束！")
        
        # 显示最终结果
        self.display_game_state(state)
        
        # 检查是否有玩家筹码耗尽
        active_players = [p for p in state.players if p.chips > 0]
        if len(active_players) <= 1:
            if active_players:
                print(f"\n🏆 游戏结束！{active_players[0].name} 获胜！")
            else:
                print("\n游戏结束！")
            return False
        
        return True
    
    def run(self):
        """运行游戏主循环"""
        print("🃏 欢迎来到德州扑克！")
        print("你将与AI玩家对战")
        
        # 创建游戏
        state = self.create_game()
        
        # 游戏主循环
        hand_count = 0
        while True:
            hand_count += 1
            print(f"\n第 {hand_count} 手牌")
            
            if not self.play_hand(state):
                break
            
            # 询问是否继续
            try:
                continue_game = input("\n按回车继续下一手牌，输入 'q' 退出: ").strip().lower()
                if continue_game == 'q':
                    break
            except KeyboardInterrupt:
                break
        
        print("\n感谢游戏！再见！")


def main():
    """主函数"""
    game = CLIGame()
    game.run()


if __name__ == "__main__":
    main() 