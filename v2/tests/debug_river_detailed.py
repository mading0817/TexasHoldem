#!/usr/bin/env python3
"""
详细调试河牌阶段AI卡住问题的脚本。

重现用户报告的场景：
- 河牌阶段，AI_2和AI_3过牌，AI_1跟注，然后玩家"You"下注$150
- 此时应该轮到AI_2行动，但游戏卡住

重点分析：
1. 下注轮的推进逻辑
2. _all_actions_complete的判断逻辑
3. 当有玩家下注后，之前已行动的玩家是否能重新行动
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from v2.core.state import GameState
from v2.core.enums import Phase, ActionType, SeatStatus
from v2.core.cards import Card, Suit, Rank
from v2.core.player import Player
from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.events import EventBus
import logging

def setup_logging():
    """设置详细的日志记录"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('debug_river_detailed.log', mode='w')
        ]
    )
    return logging.getLogger(__name__)

def create_river_scenario():
    """创建河牌阶段的测试场景"""
    logger = logging.getLogger(__name__)
    
    # 创建游戏状态
    game_state = GameState()
    
    # 创建并添加4个玩家
    player_you = Player(seat_id=0, name="You", chips=1000, is_human=True)
    player_ai1 = Player(seat_id=1, name="AI_1", chips=1000)
    player_ai2 = Player(seat_id=2, name="AI_2", chips=1000)
    player_ai3 = Player(seat_id=3, name="AI_3", chips=1000)
    
    game_state.add_player(player_you)
    game_state.add_player(player_ai1)
    game_state.add_player(player_ai2)
    game_state.add_player(player_ai3)
    
    # 设置庄家位置（AI_3为庄家）
    game_state.dealer_position = 3
    
    # 设置河牌阶段
    game_state.phase = Phase.RIVER
    
    # 设置公共牌（5张）
    game_state.community_cards = [
        Card(Rank.ACE, Suit.HEARTS),
        Card(Rank.KING, Suit.SPADES), 
        Card(Rank.QUEEN, Suit.DIAMONDS),
        Card(Rank.JACK, Suit.CLUBS),
        Card(Rank.TEN, Suit.HEARTS)
    ]
    
    # 设置玩家手牌
    game_state.players[0].hole_cards = [Card(Rank.NINE, Suit.HEARTS), Card(Rank.EIGHT, Suit.HEARTS)]
    game_state.players[1].hole_cards = [Card(Rank.ACE, Suit.CLUBS), Card(Rank.KING, Suit.HEARTS)]
    game_state.players[2].hole_cards = [Card(Rank.QUEEN, Suit.HEARTS), Card(Rank.JACK, Suit.HEARTS)]
    game_state.players[3].hole_cards = [Card(Rank.TEN, Suit.CLUBS), Card(Rank.NINE, Suit.CLUBS)]
    
    # 模拟之前的下注情况
    # 假设前面阶段已经有一些下注，底池有300
    game_state.pot = 300
    
    # 模拟用户报告的场景：
    # 河牌阶段，You下注$150，AI_1跟注$150，现在轮到AI_2
    # 设置当前状态为：You和AI_1已经下注，轮到AI_2
    game_state.current_bet = 150
    game_state.current_player = 2  # 轮到AI_2
    game_state.actions_this_round = 2  # You下注，AI_1跟注
    game_state.last_raiser = 0  # You是最后的加注者
    game_state.last_raise_amount = 150
    
    # 设置玩家的当前下注状态
    game_state.players[0].current_bet = 150  # You已下注$150
    game_state.players[1].current_bet = 150  # AI_1已跟注$150
    game_state.players[2].current_bet = 0    # AI_2还未行动
    game_state.players[3].current_bet = 0    # AI_3还未行动
    
    # 更新玩家筹码（减去已下注的金额）
    game_state.players[0].chips = 850  # 1000 - 150
    game_state.players[1].chips = 850  # 1000 - 150
    
    # 所有玩家都是活跃状态
    for player in game_state.players:
        player.status = SeatStatus.ACTIVE
    
    logger.info("=== 河牌阶段场景设置完成 ===")
    logger.info("模拟场景：You下注$150，AI_1跟注$150，现在轮到AI_2")
    logger.info(f"底池: {game_state.pot}")
    logger.info(f"当前下注: {game_state.current_bet}")
    logger.info(f"当前玩家: {game_state.current_player} ({game_state.players[game_state.current_player].name})")
    logger.info(f"本轮行动数: {game_state.actions_this_round}")
    logger.info(f"最后加注者: {game_state.last_raiser} ({game_state.players[game_state.last_raiser].name})")
    # 避免使用Card的__str__方法，直接显示rank和suit的name
    community_cards_str = [f"{card.rank.name}-{card.suit.name}" for card in game_state.community_cards]
    logger.info(f"公共牌: {community_cards_str}")
    
    logger.info("玩家下注状态:")
    for i, player in enumerate(game_state.players):
        logger.info(f"  {i}: {player.name} - 筹码:{player.chips}, 当前下注:{player.current_bet}")
    
    return game_state

def simulate_river_actions(controller, logger):
    """模拟河牌阶段的行动序列"""
    
    logger.info("\n=== 分析当前状态 ===")
    
    # 检查当前玩家
    current_player = controller.get_current_player_id()
    logger.info(f"当前玩家ID: {current_player}")
    if current_player is not None:
        player_name = controller._game_state.players[current_player].name
        logger.info(f"当前玩家: {player_name}")
        
        # 检查是否是AI_2
        if current_player == 2:
            logger.info("[OK] 正确：轮到AI_2行动")
        else:
            logger.warning(f"[ERROR] 错误：应该轮到AI_2(座位2)，但当前是{player_name}(座位{current_player})")
    else:
        logger.warning("[ERROR] 错误：当前玩家为None！这就是问题所在")
    
    # 检查下注轮是否完成
    actions_complete = controller._all_actions_complete()
    logger.info(f"下注轮是否完成: {actions_complete}")
    
    # 如果下注轮完成，这就是问题
    if actions_complete:
        logger.warning("[ERROR] 问题确认：下注轮被错误地认为已完成")
        logger.info("按德州扑克规则，AI_2和AI_3还需要响应You的$150下注")
        if controller._game_state.phase == Phase.RIVER:
            logger.info("但仍在河牌阶段，说明阶段转换逻辑是正确的")
        else:
            logger.info(f"阶段已转换到{controller._game_state.phase}，这是错误的")
    else:
        logger.info("[OK] 正确：下注轮未完成，应该继续等待玩家行动")
    
    # 测试AI_2的行动
    if current_player == 2:
        logger.info("\n=== 测试AI_2行动 ===")
        try:
            # 让AI_2做决策
            ai_success = controller.process_ai_action()
            logger.info(f"AI_2自动行动结果: {ai_success}")
            if ai_success:
                log_game_state(controller, logger)
                
                # 检查下一个玩家
                next_player = controller.get_current_player_id()
                if next_player is not None:
                    next_player_name = controller._game_state.players[next_player].name
                    logger.info(f"下一个玩家: {next_player_name}")
                else:
                    logger.info("没有下一个玩家，可能下注轮已完成")
            else:
                logger.warning("AI_2行动失败")
        except Exception as e:
            logger.error(f"AI_2行动时发生错误: {e}")
            import traceback
            logger.error(traceback.format_exc())

def log_game_state(controller, logger):
    """记录当前游戏状态的详细信息"""
    state = controller._game_state
    
    logger.info(f"  阶段: {state.phase.value}")
    logger.info(f"  当前玩家: {state.current_player}")
    logger.info(f"  当前下注: {state.current_bet}")
    logger.info(f"  底池: {state.pot}")
    logger.info(f"  本轮行动数: {state.actions_this_round}")
    logger.info(f"  最后加注者: {state.last_raiser}")
    logger.info(f"  最后加注金额: {state.last_raise_amount}")
    
    logger.info("  玩家状态:")
    for i, player in enumerate(state.players):
        logger.info(f"    {i}: {player.name} - 状态:{player.status.value}, 筹码:{player.chips}, 当前下注:{player.current_bet}")
    
    # 检查活跃玩家
    active_players = state.get_active_players()
    logger.info(f"  活跃玩家数: {len(active_players)}")
    for player in active_players:
        logger.info(f"    活跃: {player.seat_id} ({player.name})")

def analyze_betting_round_logic(controller, logger):
    """分析下注轮完成逻辑"""
    logger.info("\n=== 分析下注轮完成逻辑 ===")
    
    state = controller._game_state
    active_players = state.get_active_players()
    
    logger.info(f"活跃玩家数: {len(active_players)}")
    logger.info(f"当前下注: {state.current_bet}")
    logger.info(f"本轮行动数: {state.actions_this_round}")
    
    # 检查每个活跃玩家是否匹配当前下注
    logger.info("检查玩家下注匹配情况:")
    all_matched = True
    for player in active_players:
        matched = player.current_bet >= state.current_bet
        logger.info(f"  {player.name}: 当前下注={player.current_bet}, 需要={state.current_bet}, 匹配={matched}")
        if not matched:
            all_matched = False
    
    logger.info(f"所有玩家都匹配下注: {all_matched}")
    
    # 检查最小行动数
    min_actions = len(active_players)
    logger.info(f"最小行动数需求: {min_actions}")
    logger.info(f"实际行动数: {state.actions_this_round}")
    logger.info(f"行动数足够: {state.actions_this_round >= min_actions}")
    
    # 分析问题
    logger.info("\n=== 问题分析 ===")
    logger.info("根据德州扑克规则，当有玩家下注或加注后：")
    logger.info("1. 所有在此之前已经行动过的玩家都需要重新有机会响应")
    logger.info("2. 只有当所有玩家都响应了最新的下注后，下注轮才能结束")
    
    logger.info(f"\n当前情况：")
    logger.info(f"- You 下注 $150 (成为最后加注者)")
    logger.info(f"- AI_1 跟注了 $150")
    logger.info(f"- AI_2 和 AI_3 在 You 下注之前已经过牌")
    logger.info(f"- 按规则，AI_2 和 AI_3 都需要重新行动来响应 $150 的下注")
    logger.info(f"- 但当前逻辑可能认为下注轮已完成，因为行动数足够且所有人都匹配了下注")

def main():
    """主函数"""
    logger = setup_logging()
    logger.info("开始详细调试河牌阶段问题")
    
    try:
        # 创建测试场景
        game_state = create_river_scenario()
        
        # 创建控制器
        event_bus = EventBus()
        ai_strategy = SimpleAI()
        controller = PokerController(game_state, ai_strategy, logger, event_bus)
        controller._hand_in_progress = True
        
        # 模拟行动序列
        simulate_river_actions(controller, logger)
        
        # 分析下注轮逻辑
        analyze_betting_round_logic(controller, logger)
        
        logger.info("\n=== 调试完成 ===")
        
    except Exception as e:
        logger.error(f"调试过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 