#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克行动顺序测试
验证不同阶段的玩家行动顺序是否符合规则
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.core.enums import GamePhase, SeatStatus
from core_game_logic.phases import PreFlopPhase, FlopPhase, TurnPhase, RiverPhase


def test_betting_order():
    """测试各阶段的行动顺序"""
    print("=== 德州扑克行动顺序测试 ===\n")
    
    # 创建3个玩家的测试游戏
    players = [
        Player(seat_id=0, name="Alice", chips=100),  # 庄家
        Player(seat_id=1, name="Bob", chips=100),    # 小盲
        Player(seat_id=2, name="Charlie", chips=100) # 大盲
    ]
    
    state = GameState(
        players=players,
        dealer_position=0,  # Alice是庄家
        small_blind=1,
        big_blind=2
    )
    
    print("玩家设置:")
    print(f"座位0: Alice (庄家)")
    print(f"座位1: Bob (小盲)")
    print(f"座位2: Charlie (大盲)")
    print()
    
    # 测试翻牌前阶段
    print("1. 测试翻牌前(Pre-flop)阶段行动顺序:")
    print("   规则: 从大盲注左边的玩家开始行动")
    preflop_phase = PreFlopPhase(state)
    preflop_phase.enter()
    print(f"   翻牌前第一个行动玩家: 座位{state.current_player} ({state.get_current_player().name})")
    expected_preflop = 0  # 大盲(2)左边是Alice(0)
    if state.current_player == expected_preflop:
        print("   ✓ 翻牌前行动顺序正确")
    else:
        print(f"   ✗ 翻牌前行动顺序错误，应该是座位{expected_preflop}")
    print()
    
    # 重置状态，模拟进入翻牌阶段
    state.phase = GamePhase.FLOP
    state.community_cards = [state.deck.deal_card() for _ in range(3)]
    
    # 测试翻牌阶段
    print("2. 测试翻牌(Flop)阶段行动顺序:")
    print("   规则: 从小盲注开始行动（或第一个还在游戏中的玩家）")
    flop_phase = FlopPhase(state)
    flop_phase.enter()
    print(f"   翻牌第一个行动玩家: 座位{state.current_player} ({state.get_current_player().name})")
    expected_flop = 1  # 小盲是Bob(1)
    if state.current_player == expected_flop:
        print("   ✓ 翻牌行动顺序正确")
    else:
        print(f"   ✗ 翻牌行动顺序错误，应该是座位{expected_flop}")
    print()
    
    # 测试转牌阶段
    print("3. 测试转牌(Turn)阶段行动顺序:")
    print("   规则: 从小盲注开始行动")
    state.phase = GamePhase.TURN
    state.community_cards.append(state.deck.deal_card())
    turn_phase = TurnPhase(state)
    turn_phase.enter()
    print(f"   转牌第一个行动玩家: 座位{state.current_player} ({state.get_current_player().name})")
    expected_turn = 1  # 小盲是Bob(1)
    if state.current_player == expected_turn:
        print("   ✓ 转牌行动顺序正确")
    else:
        print(f"   ✗ 转牌行动顺序错误，应该是座位{expected_turn}")
    print()
    
    # 测试河牌阶段
    print("4. 测试河牌(River)阶段行动顺序:")
    print("   规则: 从小盲注开始行动")
    state.phase = GamePhase.RIVER
    state.community_cards.append(state.deck.deal_card())
    river_phase = RiverPhase(state)
    river_phase.enter()
    print(f"   河牌第一个行动玩家: 座位{state.current_player} ({state.get_current_player().name})")
    expected_river = 1  # 小盲是Bob(1)
    if state.current_player == expected_river:
        print("   ✓ 河牌行动顺序正确")
    else:
        print(f"   ✗ 河牌行动顺序错误，应该是座位{expected_river}")
    print()


def test_heads_up_betting_order():
    """测试单挑(2人)情况下的行动顺序"""
    print("=== 单挑(2人)行动顺序测试 ===\n")
    
    # 创建2个玩家的测试游戏
    players = [
        Player(seat_id=0, name="Alice", chips=100),  # 庄家+小盲
        Player(seat_id=1, name="Bob", chips=100)     # 大盲
    ]
    
    state = GameState(
        players=players,
        dealer_position=0,  # Alice是庄家
        small_blind=1,
        big_blind=2
    )
    
    print("玩家设置:")
    print(f"座位0: Alice (庄家+小盲)")
    print(f"座位1: Bob (大盲)")
    print()
    
    # 测试翻牌前阶段
    print("1. 测试单挑翻牌前行动顺序:")
    print("   规则: 庄家(小盲)先行动")
    preflop_phase = PreFlopPhase(state)
    preflop_phase.enter()
    print(f"   翻牌前第一个行动玩家: 座位{state.current_player} ({state.get_current_player().name})")
    expected_preflop = 0  # 庄家Alice先行动
    if state.current_player == expected_preflop:
        print("   ✓ 单挑翻牌前行动顺序正确")
    else:
        print(f"   ✗ 单挑翻牌前行动顺序错误，应该是座位{expected_preflop}")
    print()
    
    # 测试翻牌后阶段
    print("2. 测试单挑翻牌后行动顺序:")
    print("   规则: 非庄家(大盲)先行动")
    state.phase = GamePhase.FLOP
    state.community_cards = [state.deck.deal_card() for _ in range(3)]
    flop_phase = FlopPhase(state)
    flop_phase.enter()
    print(f"   翻牌第一个行动玩家: 座位{state.current_player} ({state.get_current_player().name})")
    expected_flop = 1  # 非庄家Bob先行动
    if state.current_player == expected_flop:
        print("   ✓ 单挑翻牌后行动顺序正确")
    else:
        print(f"   ✗ 单挑翻牌后行动顺序错误，应该是座位{expected_flop}")
    print()


def test_complex_scenarios():
    """测试复杂场景下的行动顺序"""
    print("=== 复杂场景行动顺序测试 ===\n")
    
    # 测试一个玩家弃牌后的行动顺序
    print("1. 测试玩家弃牌后的行动顺序:")
    players = [
        Player(seat_id=0, name="Alice", chips=100),  # 庄家
        Player(seat_id=1, name="Bob", chips=100),    # 小盲
        Player(seat_id=2, name="Charlie", chips=100) # 大盲
    ]
    
    state = GameState(
        players=players,
        dealer_position=0,
        small_blind=1,
        big_blind=2
    )
    
    # 初始化牌组
    from core_game_logic.core.deck import Deck
    state.deck = Deck()
    state.deck.shuffle()
    
    # 让小盲弃牌
    players[1].fold()
    
    print("   小盲Bob弃牌后")
    print("   剩余玩家: Alice(庄家), Charlie(大盲)")
    
    # 测试翻牌后阶段（小盲弃牌后，应该从大盲开始）
    state.phase = GamePhase.FLOP
    state.community_cards = [state.deck.deal_card() for _ in range(3)]
    
    flop_phase = FlopPhase(state)
    flop_phase.enter()
    print(f"   翻牌第一个行动玩家: 座位{state.current_player} ({state.get_current_player().name})")
    expected = 2  # 小盲弃牌后，应该从大盲Charlie开始
    if state.current_player == expected:
        print("   ✓ 弃牌后行动顺序正确")
    else:
        print(f"   ✗ 弃牌后行动顺序错误，应该是座位{expected}")
    print()


def test_refactored_phases():
    """测试重构后的阶段是否正常工作"""
    print("=== 重构后阶段功能测试 ===\n")
    
    players = [
        Player(seat_id=0, name="Alice", chips=100),
        Player(seat_id=1, name="Bob", chips=100),
        Player(seat_id=2, name="Charlie", chips=100)
    ]
    
    state = GameState(
        players=players,
        dealer_position=0,
        small_blind=1,
        big_blind=2
    )
    
    print("测试各阶段是否能正常创建和进入:")
    
    # 测试PreFlop
    try:
        preflop = PreFlopPhase(state)
        preflop.enter()
        print("   ✓ PreFlopPhase正常工作")
    except Exception as e:
        print(f"   ✗ PreFlopPhase错误: {e}")
    
    # 测试Flop
    try:
        state.phase = GamePhase.FLOP
        flop = FlopPhase(state)
        flop.enter()
        print("   ✓ FlopPhase正常工作")
    except Exception as e:
        print(f"   ✗ FlopPhase错误: {e}")
    
    # 测试Turn
    try:
        state.phase = GamePhase.TURN
        turn = TurnPhase(state)
        turn.enter()
        print("   ✓ TurnPhase正常工作")
    except Exception as e:
        print(f"   ✗ TurnPhase错误: {e}")
    
    # 测试River
    try:
        state.phase = GamePhase.RIVER
        river = RiverPhase(state)
        river.enter()
        print("   ✓ RiverPhase正常工作")
    except Exception as e:
        print(f"   ✗ RiverPhase错误: {e}")
    
    print()


if __name__ == "__main__":
    test_betting_order()
    test_heads_up_betting_order()
    test_complex_scenarios()
    test_refactored_phases()
    print("🎉 所有测试完成！") 