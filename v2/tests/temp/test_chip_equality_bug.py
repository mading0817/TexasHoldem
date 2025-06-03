#!/usr/bin/env python3
"""
测试筹码相等性问题

验证在没有人加注的情况下，第一手牌时所有玩家的筹码应该相等的问题。
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.enums import ActionType, Phase, Action, SeatStatus
from v2.core.state import GameState
from v2.core.player import Player
from v2.core.events import EventBus


def test_chip_equality_after_no_raises():
    """
    测试在没有人加注的情况下，第一手牌时所有玩家筹码应该相等
    
    场景：
    1. 所有玩家初始筹码1000
    2. 第一手牌，只有盲注，没有人加注
    3. 手牌结束后，所有玩家筹码应该相等（除了获胜者）
    """
    print("🧪 测试筹码相等性问题...")
    
    # 创建游戏环境
    game_state = GameState()
    ai_strategy = SimpleAI()
    event_bus = EventBus()
    
    # 添加4个玩家，初始筹码都是1000
    players = [
        Player(seat_id=0, name="User", chips=1000, status=SeatStatus.ACTIVE),
        Player(seat_id=1, name="AI_1", chips=1000, status=SeatStatus.ACTIVE),
        Player(seat_id=2, name="AI_2", chips=1000, status=SeatStatus.ACTIVE),
        Player(seat_id=3, name="AI_3", chips=1000, status=SeatStatus.ACTIVE)
    ]
    
    for player in players:
        game_state.add_player(player)
    
    game_state.initialize_deck()
    
    controller = PokerController(
        game_state=game_state,
        ai_strategy=ai_strategy,
        event_bus=event_bus
    )
    
    print(f"初始筹码: {[p.chips for p in game_state.players]}")
    
    # 开始第一手牌
    success = controller.start_new_hand()
    assert success, "应该能成功开始新手牌"
    
    print(f"开始手牌后筹码: {[p.chips for p in game_state.players]}")
    print(f"底池: {game_state.pot}")
    print(f"当前下注: {game_state.current_bet}")
    
    # 模拟所有玩家都只是跟注（没有加注）
    max_actions = 50
    action_count = 0
    
    while not controller.is_hand_over() and action_count < max_actions:
        current_player_id = controller.get_current_player_id()
        if current_player_id is None:
            break
        
        current_player = game_state.players[current_player_id]
        
        # 决定行动：只跟注或过牌，不加注
        if game_state.current_bet > current_player.current_bet:
            # 需要跟注
            call_amount = game_state.current_bet - current_player.current_bet
            if current_player.chips >= call_amount:
                action = Action(ActionType.CALL, 0, current_player_id)
                print(f"玩家{current_player_id} 跟注")
            else:
                action = Action(ActionType.FOLD, 0, current_player_id)
                print(f"玩家{current_player_id} 弃牌")
        else:
            # 可以过牌
            action = Action(ActionType.CHECK, 0, current_player_id)
            print(f"玩家{current_player_id} 过牌")
        
        success = controller.execute_action(action)
        if not success:
            print(f"行动失败: {action}")
            break
        
        action_count += 1
        
        # 打印当前状态
        snapshot = controller.get_snapshot()
        print(f"阶段: {snapshot.phase.value}, 筹码: {[p.chips for p in game_state.players]}, 底池: {game_state.pot}")
    
    # 结束手牌
    if controller.is_hand_over():
        result = controller.end_hand()
        print(f"手牌结束，获胜者: {result.winner_ids if result else 'None'}")
    
    # 检查筹码分配
    final_chips = [p.chips for p in game_state.players]
    print(f"最终筹码: {final_chips}")
    
    # 计算筹码差异
    total_chips = sum(final_chips)
    print(f"总筹码: {total_chips} (应该是4000)")
    
    # 检查筹码守恒
    assert total_chips == 4000, f"筹码守恒违规: 总筹码{total_chips}，应该是4000"
    
    # 分析筹码分布
    unique_chips = set(final_chips)
    print(f"不同的筹码值: {unique_chips}")
    
    # 如果没有人加注，除了获胜者外，其他玩家的筹码应该相等
    # 但这里我们发现了问题：即使没有加注，筹码也不相等
    
    # 让我们检查盲注的影响
    small_blind = game_state.small_blind
    big_blind = game_state.big_blind
    print(f"小盲注: {small_blind}, 大盲注: {big_blind}")
    
    # 理论上，如果没有人加注：
    # - 小盲注玩家应该损失小盲注金额
    # - 大盲注玩家应该损失大盲注金额  
    # - 其他玩家应该损失大盲注金额（跟注）
    # - 获胜者获得所有底池
    
    # 但问题是：在某些阶段，玩家的筹码分布不均匀
    
    return final_chips


def test_detailed_chip_tracking():
    """
    详细跟踪筹码变化过程
    """
    print("🔍 详细跟踪筹码变化...")
    
    # 创建游戏环境
    game_state = GameState()
    ai_strategy = SimpleAI()
    event_bus = EventBus()
    
    # 添加4个玩家
    players = [
        Player(seat_id=0, name="User", chips=1000, status=SeatStatus.ACTIVE),
        Player(seat_id=1, name="AI_1", chips=1000, status=SeatStatus.ACTIVE),
        Player(seat_id=2, name="AI_2", chips=1000, status=SeatStatus.ACTIVE),
        Player(seat_id=3, name="AI_3", chips=1000, status=SeatStatus.ACTIVE)
    ]
    
    for player in players:
        game_state.add_player(player)
    
    game_state.initialize_deck()
    
    controller = PokerController(
        game_state=game_state,
        ai_strategy=ai_strategy,
        event_bus=event_bus
    )
    
    def print_detailed_state(label):
        chips = [p.chips for p in game_state.players]
        current_bets = [p.current_bet for p in game_state.players]
        print(f"\n{label}:")
        print(f"  筹码: {chips}")
        print(f"  当前下注: {current_bets}")
        print(f"  底池: {game_state.pot}")
        print(f"  当前下注要求: {game_state.current_bet}")
        print(f"  总筹码: {sum(chips) + game_state.pot}")
        
        # 显示每个玩家的详细状态
        for i, player in enumerate(game_state.players):
            blind_info = ""
            if hasattr(player, 'is_small_blind') and player.is_small_blind:
                blind_info += " [小盲]"
            if hasattr(player, 'is_big_blind') and player.is_big_blind:
                blind_info += " [大盲]"
            print(f"    玩家{i}: 筹码={player.chips}, 当前下注={player.current_bet}{blind_info}")
        print()
    
    print_detailed_state("初始状态")
    
    # 开始手牌
    controller.start_new_hand()
    print_detailed_state("开始手牌后（盲注已下）")
    
    # 模拟PRE_FLOP阶段所有玩家都跟注
    action_count = 0
    while controller.get_snapshot().phase == Phase.PRE_FLOP and not controller.is_hand_over():
        current_player_id = controller.get_current_player_id()
        if current_player_id is None:
            break
        
        current_player = game_state.players[current_player_id]
        
        print(f"\n轮到玩家{current_player_id}行动:")
        print(f"  玩家筹码: {current_player.chips}")
        print(f"  玩家当前下注: {current_player.current_bet}")
        print(f"  游戏当前下注要求: {game_state.current_bet}")
        print(f"  需要补齐: {game_state.current_bet - current_player.current_bet}")
        
        # 只跟注，不加注
        if game_state.current_bet > current_player.current_bet:
            action = Action(ActionType.CALL, 0, current_player_id)
            print(f"  决定: 跟注")
        else:
            action = Action(ActionType.CHECK, 0, current_player_id)
            print(f"  决定: 过牌")
        
        success = controller.execute_action(action)
        if not success:
            print(f"  ❌ 行动失败!")
            break
        
        print_detailed_state(f"玩家{current_player_id}行动后")
        
        action_count += 1
        if action_count > 10:  # 防止无限循环
            print("行动次数过多，停止测试")
            break
    
    # 检查FLOP阶段开始时的状态
    if controller.get_snapshot().phase == Phase.FLOP:
        print_detailed_state("FLOP阶段开始")
        
        # 这里应该检查：所有玩家的筹码是否相等？
        chips = [p.chips for p in game_state.players]
        unique_chips = set(chips)
        
        if len(unique_chips) > 1:
            print(f"❌ 发现问题：FLOP阶段开始时玩家筹码不相等: {chips}")
            print(f"   不同的筹码值: {unique_chips}")
            
            # 分析每个玩家在PRE_FLOP阶段的总投入
            print("\n分析每个玩家的总投入:")
            for i, player in enumerate(game_state.players):
                initial_chips = 1000
                current_chips = player.chips
                total_invested = initial_chips - current_chips
                print(f"   玩家{i}: 初始1000 -> 当前{current_chips} = 投入{total_invested}")
                
            print(f"\n底池总额: {game_state.pot}")
            print(f"所有投入总和: {sum(1000 - p.chips for p in game_state.players)}")
            
            # 检查是否有投入不等的情况
            investments = [1000 - p.chips for p in game_state.players]
            unique_investments = set(investments)
            if len(unique_investments) > 1:
                print(f"❌ 投入不等: {investments}")
                print(f"   不同的投入值: {unique_investments}")
            else:
                print(f"✅ 所有玩家投入相等: {investments[0]}")
        else:
            print(f"✅ FLOP阶段开始时玩家筹码相等: {chips[0]}")


def test_step_by_step_analysis():
    """
    逐步分析问题
    """
    print("\n🔬 逐步分析问题...")
    
    # 创建游戏环境
    game_state = GameState()
    ai_strategy = SimpleAI()
    event_bus = EventBus()
    
    # 添加4个玩家
    players = [
        Player(seat_id=0, name="User", chips=1000, status=SeatStatus.ACTIVE),
        Player(seat_id=1, name="AI_1", chips=1000, status=SeatStatus.ACTIVE),
        Player(seat_id=2, name="AI_2", chips=1000, status=SeatStatus.ACTIVE),
        Player(seat_id=3, name="AI_3", chips=1000, status=SeatStatus.ACTIVE)
    ]
    
    for player in players:
        game_state.add_player(player)
    
    game_state.initialize_deck()
    
    controller = PokerController(
        game_state=game_state,
        ai_strategy=ai_strategy,
        event_bus=event_bus
    )
    
    print("步骤1: 开始手牌")
    controller.start_new_hand()
    
    # 检查庄家位置和盲注位置
    dealer_pos = game_state.dealer_position
    small_blind_pos = (dealer_pos + 1) % 4
    big_blind_pos = (dealer_pos + 2) % 4
    
    print(f"庄家位置: {dealer_pos}")
    print(f"小盲注位置: {small_blind_pos}")
    print(f"大盲注位置: {big_blind_pos}")
    print(f"小盲注金额: {game_state.small_blind}")
    print(f"大盲注金额: {game_state.big_blind}")
    
    # 检查盲注后的状态
    print("\n步骤2: 盲注后状态")
    for i, player in enumerate(game_state.players):
        print(f"玩家{i}: 筹码={player.chips}, 当前下注={player.current_bet}")
    print(f"底池: {game_state.pot}")
    print(f"当前下注要求: {game_state.current_bet}")
    
    # 模拟每个玩家的行动
    print("\n步骤3: 模拟每个玩家行动")
    
    # 找到第一个行动的玩家
    first_player = controller.get_current_player_id()
    print(f"第一个行动的玩家: {first_player}")
    
    # 模拟所有玩家跟注
    players_to_act = []
    current_id = first_player
    for _ in range(4):  # 最多4个玩家
        if current_id is not None:
            players_to_act.append(current_id)
            # 找下一个玩家
            for i in range(1, 4):
                next_id = (current_id + i) % 4
                if game_state.players[next_id].status == SeatStatus.ACTIVE:
                    current_id = next_id
                    break
            else:
                break
        else:
            break
    
    print(f"行动顺序: {players_to_act}")
    
    # 逐个执行行动
    for player_id in players_to_act:
        if controller.get_current_player_id() != player_id:
            print(f"警告: 期望玩家{player_id}行动，但当前玩家是{controller.get_current_player_id()}")
            break
            
        player = game_state.players[player_id]
        call_amount = game_state.current_bet - player.current_bet
        
        print(f"\n玩家{player_id}行动前:")
        print(f"  筹码: {player.chips}")
        print(f"  当前下注: {player.current_bet}")
        print(f"  需要补齐: {call_amount}")
        
        if call_amount > 0:
            action = Action(ActionType.CALL, 0, player_id)
            print(f"  执行: 跟注 {call_amount}")
        else:
            action = Action(ActionType.CHECK, 0, player_id)
            print(f"  执行: 过牌")
        
        success = controller.execute_action(action)
        
        print(f"玩家{player_id}行动后:")
        print(f"  筹码: {player.chips}")
        print(f"  当前下注: {player.current_bet}")
        print(f"  底池: {game_state.pot}")
        
        if not success:
            print(f"  ❌ 行动失败!")
            break
            
        # 检查是否进入下一阶段
        if controller.get_snapshot().phase != Phase.PRE_FLOP:
            print(f"  进入{controller.get_snapshot().phase.value}阶段")
            break


if __name__ == "__main__":
    test_chip_equality_after_no_raises()
    test_detailed_chip_tracking()
    test_step_by_step_analysis() 