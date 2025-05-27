#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
完整游戏流程端到端测试
验证从发牌到摊牌的整个德州扑克游戏流程
"""

from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.core.enums import SeatStatus, GamePhase, ActionType, Action
from core_game_logic.betting.action_validator import ActionValidator
from core_game_logic.phases import PreFlopPhase, FlopPhase, TurnPhase, RiverPhase, ShowdownPhase
from core_game_logic.core.deck import Deck


class TestFullGame:
    """完整游戏流程测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.validator = ActionValidator()
    
    def create_test_game(self, player_configs=None):
        """创建测试游戏"""
        if player_configs is None:
            player_configs = [
                {"seat_id": 0, "name": "Alice", "chips": 100},
                {"seat_id": 1, "name": "Bob", "chips": 100},
                {"seat_id": 2, "name": "Charlie", "chips": 100}
            ]
        
        # 创建玩家
        players = []
        for config in player_configs:
            player = Player(
                seat_id=config["seat_id"],
                name=config["name"],
                chips=config["chips"]
            )
            players.append(player)
        
        # 创建游戏状态
        state = GameState(
            players=players,
            dealer_position=0,
            small_blind=1,
            big_blind=2
        )
        
        return state
    
    def test_basic_game_flow(self):
        """测试基础游戏流程"""
        print("=== 测试基础游戏流程 ===")
        
        # 创建3人游戏
        state = self.create_test_game()
        
        # 设置固定种子确保可重现
        deck = Deck(seed=42)
        state.deck = deck
        
        print(f"初始状态: {len(state.players)}名玩家")
        for player in state.players:
            print(f"  {player.name}: {player.chips}筹码")
        
        # 开始翻牌前阶段
        phase = PreFlopPhase(state)
        phase.enter()
        
        print(f"\n翻牌前阶段:")
        print(f"  底池: {state.pot}")
        print(f"  当前下注: {state.current_bet}")
        print(f"  当前玩家: {state.current_player}")
        
        # 验证盲注设置 - 盲注在current_bet中，不是底池中
        # 底池在下注轮结束时才收集盲注
        small_blind_player = None
        big_blind_player = None
        for player in state.players:
            if player.is_small_blind:
                small_blind_player = player
            if player.is_big_blind:
                big_blind_player = player
        
        assert small_blind_player is not None, "应该有小盲注玩家"
        assert big_blind_player is not None, "应该有大盲注玩家"
        assert small_blind_player.current_bet == 1, "小盲注应该是1"
        assert big_blind_player.current_bet == 2, "大盲注应该是2"
        assert state.current_bet == 2, "当前下注应该是大盲注"
        
        # 验证手牌发放
        for player in state.players:
            assert len(player.hole_cards) == 2, f"玩家{player.name}应该有2张手牌"
            print(f"  {player.name}手牌: {player.get_hole_cards_str()}")
        
        # 模拟翻牌前行动（所有人跟注）
        self._simulate_preflop_actions(state, phase)
        
        # 进入翻牌阶段
        next_phase = phase.exit()
        assert isinstance(next_phase, FlopPhase), "应该进入翻牌阶段"
        
        phase = next_phase
        phase.enter()
        
        print(f"\n翻牌阶段:")
        print(f"  公共牌: {' '.join(card.to_str() for card in state.community_cards)}")
        print(f"  底池: {state.pot}")
        
        # 验证翻牌
        assert len(state.community_cards) == 3, "应该有3张翻牌"
        assert state.phase == GamePhase.FLOP, "游戏阶段应该是翻牌"
        
        # 模拟翻牌行动（所有人过牌）
        self._simulate_betting_round_check_all(state, phase)
        
        # 进入转牌阶段
        next_phase = phase.exit()
        assert isinstance(next_phase, TurnPhase), "应该进入转牌阶段"
        
        phase = next_phase
        phase.enter()
        
        print(f"\n转牌阶段:")
        print(f"  公共牌: {' '.join(card.to_str() for card in state.community_cards)}")
        
        # 验证转牌
        assert len(state.community_cards) == 4, "应该有4张公共牌"
        assert state.phase == GamePhase.TURN, "游戏阶段应该是转牌"
        
        # 模拟转牌行动（所有人过牌）
        self._simulate_betting_round_check_all(state, phase)
        
        # 进入河牌阶段
        next_phase = phase.exit()
        assert isinstance(next_phase, RiverPhase), "应该进入河牌阶段"
        
        phase = next_phase
        phase.enter()
        
        print(f"\n河牌阶段:")
        print(f"  公共牌: {' '.join(card.to_str() for card in state.community_cards)}")
        
        # 验证河牌
        assert len(state.community_cards) == 5, "应该有5张公共牌"
        assert state.phase == GamePhase.RIVER, "游戏阶段应该是河牌"
        
        # 模拟河牌行动（所有人过牌）
        self._simulate_betting_round_check_all(state, phase)
        
        # 进入摊牌阶段
        next_phase = phase.exit()
        assert isinstance(next_phase, ShowdownPhase), "应该进入摊牌阶段"
        
        phase = next_phase
        phase.enter()
        
        print(f"\n摊牌阶段:")
        print(f"  游戏阶段: {state.phase.name}")
        
        # 验证摊牌
        assert state.phase == GamePhase.SHOWDOWN, "游戏阶段应该是摊牌"
        
        # 记录摊牌前筹码
        chips_before = {p.seat_id: p.chips for p in state.players}
        pot_before = state.pot
        
        # 执行摊牌
        final_phase = phase.exit()
        assert final_phase is None, "摊牌后游戏应该结束"
        
        print(f"\n游戏结束:")
        total_chips_after = sum(p.chips for p in state.players)
        total_chips_before = sum(chips_before.values()) + pot_before
        
        print(f"  底池分配前总筹码: {total_chips_before}")
        print(f"  底池分配后总筹码: {total_chips_after}")
        print(f"  最终底池: {state.pot}")
        
        for player in state.players:
            change = player.chips - chips_before[player.seat_id]
            print(f"  {player.name}: {player.chips}筹码 ({change:+d})")
        
        # 验证筹码守恒
        assert total_chips_after == total_chips_before, "筹码总数应该守恒"
        assert state.pot == 0, "游戏结束后底池应该为0"
        
        print("✓ 基础游戏流程测试通过")
    
    def test_fold_scenario(self):
        """测试弃牌场景"""
        print("\n=== 测试弃牌场景 ===")
        
        state = self.create_test_game()
        state.deck = Deck(seed=123)
        
        # 开始翻牌前
        phase = PreFlopPhase(state)
        phase.enter()
        
        print(f"翻牌前，当前玩家: {state.current_player}")
        
        # 第一个玩家弃牌
        current_player = state.get_current_player()
        fold_action = Action(ActionType.FOLD)
        validated_action = self.validator.validate(state, current_player, fold_action)
        
        continuing = phase.act(validated_action)
        print(f"玩家{current_player.seat_id}弃牌")
        
        # 验证弃牌效果
        assert current_player.status == SeatStatus.FOLDED, "玩家应该处于弃牌状态"
        
        # 继续游戏直到只剩一个玩家
        while continuing and len(state.get_active_players()) > 1:
            current_player = state.get_current_player()
            if current_player and current_player.can_act():
                # 其他玩家也弃牌
                fold_action = Action(ActionType.FOLD)
                validated_action = self.validator.validate(state, current_player, fold_action)
                continuing = phase.act(validated_action)
                print(f"玩家{current_player.seat_id}弃牌")
            else:
                break
        
        # 应该直接进入摊牌
        next_phase = phase.exit()
        assert isinstance(next_phase, ShowdownPhase), "只剩一个玩家时应该直接摊牌"
        
        # 执行摊牌
        next_phase.enter()
        final_phase = next_phase.exit()
        assert final_phase is None, "游戏应该结束"
        
        # 验证获胜者获得底池
        players_in_hand = state.get_players_in_hand()
        assert len(players_in_hand) == 1, "应该只有一个玩家未弃牌"
        
        print("✓ 弃牌场景测试通过")
    
    def test_all_in_scenario(self):
        """测试全押场景"""
        print("\n=== 测试全押场景 ===")
        
        # 创建筹码不等的玩家
        player_configs = [
            {"seat_id": 0, "name": "Alice", "chips": 50},
            {"seat_id": 1, "name": "Bob", "chips": 100},
            {"seat_id": 2, "name": "Charlie", "chips": 25}
        ]
        
        state = self.create_test_game(player_configs)
        state.deck = Deck(seed=456)
        
        # 开始翻牌前
        phase = PreFlopPhase(state)
        phase.enter()
        
        print(f"翻牌前，底池: {state.pot}")
        
        # 模拟全押场景
        continuing = True
        while continuing:
            current_player = state.get_current_player()
            if current_player and current_player.can_act():
                # 让玩家全押
                all_in_action = Action(ActionType.ALL_IN)
                validated_action = self.validator.validate(state, current_player, all_in_action)
                continuing = phase.act(validated_action)
                print(f"玩家{current_player.seat_id}全押{validated_action.actual_amount}")
            else:
                break
        
        # 验证全押状态
        all_in_players = [p for p in state.players if p.status == SeatStatus.ALL_IN]
        print(f"全押玩家数: {len(all_in_players)}")
        
        # 继续游戏流程到摊牌
        current_phase = phase
        while current_phase is not None:
            next_phase = current_phase.exit()
            if next_phase is None:
                break
            
            current_phase = next_phase
            current_phase.enter()
            
            # 如果不是摊牌阶段，跳过行动（全押玩家无需行动）
            if not isinstance(current_phase, ShowdownPhase):
                print(f"跳过{current_phase.__class__.__name__}行动（全押场景）")
        
        print("✓ 全押场景测试通过")
    
    def _simulate_preflop_actions(self, state, phase):
        """模拟翻牌前行动"""
        continuing = True
        while continuing:
            current_player = state.get_current_player()
            if not current_player or not current_player.can_act():
                break
            
            # 简单策略：跟注
            call_action = Action(ActionType.CALL)
            validated_action = self.validator.validate(state, current_player, call_action)
            continuing = phase.act(validated_action)
            
            print(f"  玩家{current_player.seat_id} {validated_action}")
    
    def _simulate_betting_round_check_all(self, state, phase):
        """模拟下注轮所有人过牌"""
        continuing = True
        while continuing:
            current_player = state.get_current_player()
            if not current_player or not current_player.can_act():
                break
            
            # 所有人过牌
            check_action = Action(ActionType.CHECK)
            validated_action = self.validator.validate(state, current_player, check_action)
            continuing = phase.act(validated_action)
            
            print(f"  玩家{current_player.seat_id}过牌")


def main():
    """运行测试"""
    print("=== 完整游戏流程端到端测试 ===\n")
    
    # 创建测试实例
    test_instance = TestFullGame()
    
    # 运行所有测试
    test_methods = [
        ("基础游戏流程", test_instance.test_basic_game_flow),
        ("弃牌场景", test_instance.test_fold_scenario),
        ("全押场景", test_instance.test_all_in_scenario),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in test_methods:
        try:
            test_instance.setup_method()
            test_func()
            print(f"✓ {test_name}测试通过\n")
            passed += 1
        except Exception as e:
            print(f"✗ {test_name}测试失败: {e}\n")
            failed += 1
    
    print(f"测试结果: {passed}通过, {failed}失败")
    
    if failed == 0:
        print("🎉 所有端到端测试通过！")
        return True
    else:
        print("❌ 部分测试失败，需要修复")
        return False


if __name__ == "__main__":
    main() 