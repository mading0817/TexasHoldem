#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI模拟测试
6个AI玩家进行10次牌局，验证游戏流程和结算正确性
"""

import random
from typing import List, Dict

from core_game_logic.game_state import GameState
from core_game_logic.player import Player
from core_game_logic.enums import ActionType, Action, SeatStatus
from core_game_logic.action_validator import ActionValidator
from core_game_logic.phases import PreFlopPhase, FlopPhase, TurnPhase, RiverPhase, ShowdownPhase
from core_game_logic.deck import Deck


class AISimulation:
    """AI模拟测试类"""
    
    def __init__(self):
        self.validator = ActionValidator()
        self.hand_count = 0
        self.total_chips_start = 0
        
    def create_ai_game(self, num_players: int = 6, starting_chips: int = 100) -> GameState:
        """创建AI游戏"""
        players = []
        
        ai_names = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Henry"]
        for i in range(num_players):
            ai_player = Player(
                seat_id=i,
                name=ai_names[i] if i < len(ai_names) else f"AI{i}",
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
        
        self.total_chips_start = sum(p.chips for p in players)
        print(f"游戏开始，总筹码: {self.total_chips_start}")
        
        return state
    
    def get_ai_action(self, state: GameState, player: Player) -> Action:
        """获取AI玩家的行动（改进的策略）"""
        # 更智能的AI策略
        
        # 根据手牌强度调整策略
        hand_strength = self._evaluate_hand_strength(player.hole_cards, state.community_cards)
        
        # 基于手牌强度的行动概率
        if hand_strength >= 0.8:  # 强牌
            fold_prob = 0.05
            aggressive_prob = 0.6
        elif hand_strength >= 0.6:  # 中等牌
            fold_prob = 0.2
            aggressive_prob = 0.3
        elif hand_strength >= 0.4:  # 弱牌
            fold_prob = 0.4
            aggressive_prob = 0.1
        else:  # 很弱的牌
            fold_prob = 0.7
            aggressive_prob = 0.05
        
        # 考虑筹码比例
        chip_ratio = player.chips / self.total_chips_start
        if chip_ratio < 0.1:  # 筹码不足，更保守
            fold_prob += 0.2
            aggressive_prob *= 0.5
        elif chip_ratio > 0.3:  # 筹码充足，更激进
            fold_prob *= 0.7
            aggressive_prob *= 1.3
        
        # 决定是否弃牌
        if random.random() < fold_prob:
            return Action(ActionType.FOLD)
        
        actions = []
        
        # 检查是否可以过牌
        if state.current_bet == player.current_bet:
            actions.append(ActionType.CHECK)
        else:
            # 需要跟注
            call_amount = state.current_bet - player.current_bet
            if call_amount <= player.chips:
                actions.append(ActionType.CALL)
        
        # 考虑下注/加注
        if random.random() < aggressive_prob:
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
        
        # 极少概率全押
        if random.random() < 0.02 and player.chips > 0:
            return Action(ActionType.ALL_IN)
        
        # 选择一个行动
        if actions:
            action_type = random.choice(actions)
            
            if action_type == ActionType.BET:
                max_bet = min(player.chips, state.big_blind * 5)
                amount = random.randint(state.big_blind, max_bet)
                return Action(action_type, amount)
            elif action_type == ActionType.RAISE:
                min_raise = state.current_bet * 2
                max_raise = min(player.chips, state.current_bet * 4)
                if max_raise >= min_raise:
                    amount = random.randint(min_raise, max_raise)
                    return Action(action_type, amount)
                else:
                    return Action(ActionType.CALL)
            else:
                return Action(action_type)
        
        # 默认弃牌
        return Action(ActionType.FOLD)
    
    def _evaluate_hand_strength(self, hole_cards: List, community_cards: List) -> float:
        """简单评估手牌强度（0-1之间）"""
        if not hole_cards or len(hole_cards) != 2:
            return 0.1
        
        # 简单的手牌强度评估
        card1, card2 = hole_cards
        
        # 对子加分
        if card1.rank == card2.rank:
            pair_strength = card1.rank.value / 14.0
            return min(0.9, 0.5 + pair_strength * 0.4)
        
        # 同花加分
        suited_bonus = 0.1 if card1.suit == card2.suit else 0
        
        # 高牌加分
        high_card = max(card1.rank.value, card2.rank.value) / 14.0
        low_card = min(card1.rank.value, card2.rank.value) / 14.0
        
        # 连牌加分
        gap = abs(card1.rank.value - card2.rank.value)
        connector_bonus = 0.1 if gap <= 2 else 0
        
        strength = (high_card * 0.6 + low_card * 0.2 + suited_bonus + connector_bonus)
        return min(0.8, strength)
    
    def display_detailed_state(self, state: GameState, phase_name: str):
        """显示详细的游戏状态"""
        print(f"\n{'='*80}")
        print(f"【{phase_name}】 底池: {state.pot} | 当前下注: {state.current_bet}")
        
        # 显示公共牌
        if state.community_cards:
            community_str = " ".join(card.to_str() for card in state.community_cards)
            print(f"公共牌: {community_str}")
        
        print(f"{'='*80}")
        
        # 显示所有玩家状态
        for player in state.players:
            status_str = ""
            if player.status == SeatStatus.FOLDED:
                status_str = " [弃牌]"
            elif player.status == SeatStatus.ALL_IN:
                status_str = " [全押]"
            elif player.status == SeatStatus.OUT:
                status_str = " [出局]"
            
            cards_str = player.get_hole_cards_str(hidden=False)
            current_marker = " <-- 当前" if player.seat_id == state.current_player else ""
            
            print(f"{player.name:8}: {player.chips:3d}筹码 | 当前下注: {player.current_bet:2d} | 手牌: {cards_str}{status_str}{current_marker}")
        
        print(f"{'='*80}")
    
    def run_phase_with_logging(self, state: GameState, phase, phase_name: str):
        """运行游戏阶段并记录详细日志"""
        print(f"\n🎯 进入{phase_name}")
        phase.enter()
        self.display_detailed_state(state, phase_name)
        
        # 如果是摊牌阶段，直接退出
        if isinstance(phase, ShowdownPhase):
            return phase.exit()
        
        # 处理玩家行动
        action_count = 0
        continuing = True
        while continuing:
            current_player = state.get_current_player()
            if not current_player or not current_player.can_act():
                break
            
            action_count += 1
            action = self.get_ai_action(state, current_player)
            
            print(f"\n第{action_count}个行动: {current_player.name} 选择 {action}")
            
            # 验证并执行行动
            try:
                validated_action = self.validator.validate(state, current_player, action)
                continuing = phase.act(validated_action)
                
                if validated_action.is_converted:
                    print(f"  ⚠️ 行动被转换: {validated_action.conversion_reason}")
                
                print(f"  ✅ 执行: {validated_action}")
                
                # 显示行动后的状态变化
                print(f"  📊 {current_player.name}: {current_player.chips}筹码, 当前下注: {current_player.current_bet}")
                
            except Exception as e:
                print(f"  ❌ 行动执行失败: {e}")
                # AI默认弃牌
                validated_action = self.validator.validate(state, current_player, Action(ActionType.FOLD))
                continuing = phase.act(validated_action)
                print(f"  🔄 默认弃牌")
        
        print(f"\n✅ {phase_name}结束")
        return phase.exit()
    
    def play_hand_with_logging(self, state: GameState):
        """玩一手牌并记录详细日志"""
        self.hand_count += 1
        print(f"\n{'🎰'*20} 第 {self.hand_count} 手牌开始 {'🎰'*20}")
        
        # 记录开始时的筹码
        chips_before = {p.seat_id: p.chips for p in state.players}
        total_before = sum(chips_before.values())
        
        print(f"开始前总筹码: {total_before}")
        for player in state.players:
            if player.chips > 0:
                print(f"  {player.name}: {player.chips}筹码")
        
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
        
        # 移动庄家位置
        active_players = [p for p in state.players if p.chips > 0]
        if len(active_players) <= 1:
            return False
        
        state.dealer_position = (state.dealer_position + 1) % len(state.players)
        while state.players[state.dealer_position].chips <= 0:
            state.dealer_position = (state.dealer_position + 1) % len(state.players)
        
        print(f"庄家: {state.players[state.dealer_position].name}")
        
        # 创建新牌组
        state.deck = Deck()
        state.deck.shuffle()
        
        # 运行各个阶段
        phase = PreFlopPhase(state)
        phase_names = ["翻牌前", "翻牌", "转牌", "河牌", "摊牌"]
        phase_index = 0
        
        while phase is not None:
            phase_name = phase_names[phase_index] if phase_index < len(phase_names) else "未知阶段"
            phase = self.run_phase_with_logging(state, phase, phase_name)
            phase_index += 1
        
        # 记录结束时的筹码
        chips_after = {p.seat_id: p.chips for p in state.players}
        total_after = sum(chips_after.values())
        
        print(f"\n{'🎉'*20} 第 {self.hand_count} 手牌结束 {'🎉'*20}")
        print(f"结束后总筹码: {total_after}")
        
        # 验证筹码守恒
        if total_before != total_after:
            print(f"❌ 筹码不守恒！开始: {total_before}, 结束: {total_after}, 差异: {total_after - total_before}")
        else:
            print(f"✅ 筹码守恒验证通过")
        
        # 显示筹码变化
        print(f"\n筹码变化:")
        for player in state.players:
            change = chips_after[player.seat_id] - chips_before[player.seat_id]
            if change != 0:
                print(f"  {player.name}: {chips_before[player.seat_id]} → {chips_after[player.seat_id]} ({change:+d})")
        
        # 检查是否有玩家出局
        remaining_players = [p for p in state.players if p.chips > 0]
        if len(remaining_players) <= 1:
            if remaining_players:
                print(f"\n🏆 游戏结束！{remaining_players[0].name} 获胜！")
            else:
                print(f"\n游戏结束！")
            return False
        
        return True
    
    def run_simulation(self, num_hands: int = 10):
        """运行AI模拟"""
        print(f"🤖 开始AI模拟测试：6个AI玩家，{num_hands}手牌")
        print(f"{'='*100}")
        
        # 创建游戏
        state = self.create_ai_game()
        
        # 模拟多手牌
        for hand_num in range(num_hands):
            if not self.play_hand_with_logging(state):
                print(f"游戏在第{hand_num + 1}手牌后结束")
                break
            
            # 自动继续下一手牌，不需要用户按回车
            # input(f"\n按回车继续下一手牌...")
        
        # 最终统计
        print(f"\n{'🏁'*20} 模拟测试完成 {'🏁'*20}")
        print(f"总共进行了 {self.hand_count} 手牌")
        
        final_chips = {p.name: p.chips for p in state.players}
        total_final = sum(final_chips.values())
        
        print(f"最终筹码分布:")
        for name, chips in sorted(final_chips.items(), key=lambda x: x[1], reverse=True):
            percentage = (chips / self.total_chips_start) * 100
            print(f"  {name}: {chips}筹码 ({percentage:.1f}%)")
        
        print(f"总筹码: {total_final} (应该等于 {self.total_chips_start})")
        
        if total_final == self.total_chips_start:
            print(f"✅ 整体筹码守恒验证通过！")
        else:
            print(f"❌ 整体筹码不守恒！差异: {total_final - self.total_chips_start}")


def main():
    """主函数"""
    simulation = AISimulation()
    simulation.run_simulation(10)


if __name__ == "__main__":
    main() 