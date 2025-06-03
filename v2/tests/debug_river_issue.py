#!/usr/bin/env python3
"""
调试河牌阶段AI卡住问题的脚本

根据用户提供的游戏日志，重现河牌阶段玩家下注后AI卡住的问题。
"""

import sys
import os
import logging

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.state import GameState
from v2.core.player import Player
from v2.core.enums import ActionType, Phase, SeatStatus, Action
from v2.core.cards import Card, Suit, Rank


def setup_logging():
    """设置详细的日志记录"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('debug_river_issue.log', mode='w', encoding='utf-8')
        ]
    )


def create_river_scenario():
    """创建河牌阶段的测试场景
    
    根据用户提供的日志重现场景：
    - 河牌阶段
    - 公共牌: J♥️ 6♦️ 5♣️ 8♦️ 8♠️
    - You下注150后，AI_1应该行动但卡住了
    """
    # 创建游戏状态
    game_state = GameState()
    
    # 添加玩家
    players = [
        Player(seat_id=0, name="You", chips=741),      # 人类玩家
        Player(seat_id=1, name="AI_1", chips=891),     # AI玩家1 (当前应该行动)
        Player(seat_id=2, name="AI_2", chips=891),     # AI玩家2 (小盲)
        Player(seat_id=3, name="AI_3", chips=891),     # AI玩家3 (大盲)
    ]
    
    for player in players:
        game_state.add_player(player)
    
    # 设置游戏状态到河牌阶段
    game_state.phase = Phase.RIVER
    game_state.dealer_position = 0  # You是庄家
    game_state.small_blind = 5
    game_state.big_blind = 10
    
    # 设置公共牌: J♥️ 6♦️ 5♣️ 8♦️ 8♠️
    game_state.community_cards = [
        Card(Suit.HEARTS, Rank.JACK),    # J♥️
        Card(Suit.DIAMONDS, Rank.SIX),   # 6♦️
        Card(Suit.CLUBS, Rank.FIVE),     # 5♣️
        Card(Suit.DIAMONDS, Rank.EIGHT), # 8♦️
        Card(Suit.SPADES, Rank.EIGHT),   # 8♠️
    ]
    
    # 设置手牌
    players[0].hole_cards = [
        Card(Suit.DIAMONDS, Rank.SEVEN),  # 7♦️
        Card(Suit.DIAMONDS, Rank.FOUR),   # 4♦️
    ]
    
    # 为AI玩家设置一些手牌（不影响测试）
    players[1].hole_cards = [Card(Suit.HEARTS, Rank.ACE), Card(Suit.SPADES, Rank.KING)]
    players[2].hole_cards = [Card(Suit.CLUBS, Rank.QUEEN), Card(Suit.HEARTS, Rank.TEN)]
    players[3].hole_cards = [Card(Suit.SPADES, Rank.NINE), Card(Suit.CLUBS, Rank.EIGHT)]
    
    # 设置底池和下注状态
    game_state.pot = 436  # 之前收集的筹码
    game_state.current_bet = 150  # You下注了150
    
    # 设置玩家的当前下注状态
    players[0].current_bet = 150  # You已经下注150
    players[1].current_bet = 0    # AI_1还没有行动
    players[2].current_bet = 0    # AI_2已经过牌
    players[3].current_bet = 0    # AI_3已经过牌
    
    # 设置玩家状态
    for player in players:
        player.status = SeatStatus.ACTIVE
    
    # 设置当前行动玩家为AI_1
    game_state.current_player = 1
    
    # 设置下注轮信息
    game_state.last_raiser = 0  # You是最后的加注者
    game_state.last_raise_amount = 150  # 加注金额
    game_state.actions_this_round = 3  # AI_2过牌, AI_3过牌, You下注
    
    return game_state


def test_river_scenario():
    """测试河牌阶段场景"""
    print("=== 开始测试河牌阶段AI卡住问题 ===")
    
    # 创建游戏状态
    game_state = create_river_scenario()
    
    # 创建控制器
    ai_strategy = SimpleAI()
    logger = logging.getLogger(__name__)
    controller = PokerController(
        game_state=game_state,
        ai_strategy=ai_strategy,
        logger=logger
    )
    
    # 设置手牌进行中
    controller._hand_in_progress = True
    
    # 获取初始快照
    snapshot = controller.get_snapshot()
    print(f"\n初始状态:")
    print(f"阶段: {snapshot.phase}")
    print(f"底池: ${snapshot.pot}")
    print(f"当前下注: ${snapshot.current_bet}")
    print(f"当前玩家: {snapshot.current_player}")
    
    print(f"\n玩家状态:")
    for player in snapshot.players:
        print(f"  {player.name}: 筹码=${player.chips}, 当前下注=${player.current_bet}, 状态={player.status}")
    
    # 模拟连续的AI行动
    max_actions = 10
    action_count = 0
    
    while action_count < max_actions:
        current_player_id = controller.get_current_player_id()
        print(f"\n=== 行动 {action_count + 1} ===")
        print(f"当前需要行动的玩家ID: {current_player_id}")
        
        if current_player_id is None:
            print("❌ 当前玩家ID为None，游戏可能结束或卡住")
            
            # 检查手牌是否结束
            is_over = controller.is_hand_over()
            print(f"手牌是否结束: {is_over}")
            
            if is_over:
                print("手牌正常结束")
            else:
                print("游戏卡住了！")
                # 分析原因
                print("\n=== 问题分析 ===")
                try:
                    all_complete = controller._all_actions_complete()
                    print(f"所有行动是否完成: {all_complete}")
                except Exception as e:
                    print(f"检查行动完成状态时出错: {e}")
            break
        
        if current_player_id == 0:
            print("轮到人类玩家，停止自动处理")
            break
        
        # 处理AI行动
        print(f"处理AI_{current_player_id}的行动...")
        try:
            success = controller.process_ai_action()
            print(f"AI行动处理结果: {success}")
            
            if success:
                # 获取更新后的状态
                new_snapshot = controller.get_snapshot()
                print(f"行动后状态:")
                print(f"  当前玩家: {new_snapshot.current_player}")
                print(f"  当前下注: ${new_snapshot.current_bet}")
                print(f"  底池: ${new_snapshot.pot}")
                
                # 显示玩家状态变化
                for player in new_snapshot.players:
                    if player.seat_id == current_player_id:
                        print(f"  {player.name}: 筹码=${player.chips}, 当前下注=${player.current_bet}, 状态={player.status}")
            else:
                print("❌ AI行动处理失败")
                break
                
        except Exception as e:
            print(f"❌ AI行动处理失败: {e}")
            import traceback
            traceback.print_exc()
            break
        
        action_count += 1
    
    print(f"\n=== 最终状态 ===")
    final_snapshot = controller.get_snapshot()
    print(f"阶段: {final_snapshot.phase}")
    print(f"当前玩家: {final_snapshot.current_player}")
    print(f"手牌是否结束: {controller.is_hand_over()}")


def test_action_completion_logic():
    """专门测试行动完成逻辑"""
    print("\n=== 测试行动完成逻辑 ===")
    
    game_state = create_river_scenario()
    controller = PokerController(
        game_state=game_state,
        ai_strategy=SimpleAI(),
        logger=logging.getLogger(__name__)
    )
    controller._hand_in_progress = True
    
    # 获取活跃玩家
    active_players = game_state.get_active_players()
    print(f"活跃玩家数: {len(active_players)}")
    for player in active_players:
        print(f"  {player.name}: 下注=${player.current_bet}, 状态={player.status}")
    
    print(f"当前下注: ${game_state.current_bet}")
    print(f"行动数: {game_state.actions_this_round}")
    print(f"最后加注者: {game_state.last_raiser}")
    
    # 检查每个玩家是否匹配当前下注
    print("\n检查下注匹配:")
    for player in active_players:
        matches = player.current_bet >= game_state.current_bet
        print(f"  {player.name}: {player.current_bet} >= {game_state.current_bet} = {matches}")
    
    # 检查行动完成逻辑
    try:
        all_complete = controller._all_actions_complete()
        print(f"\n所有行动完成: {all_complete}")
    except Exception as e:
        print(f"检查行动完成时出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    setup_logging()
    test_river_scenario()
    test_action_completion_logic() 