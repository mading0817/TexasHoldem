#!/usr/bin/env python3
"""
调试Streamlit UI中AI处理逻辑的脚本。

模拟process_ai_actions_continuously函数的行为，
找出AI在河牌阶段卡住的具体原因。
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
import time

def setup_logging():
    """设置详细的日志记录"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('debug_ui_ai_processing.log', mode='w')
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
    game_state.pot = 300
    
    # 模拟用户报告的场景：You下注$150，AI_1跟注$150，现在轮到AI_2
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
    
    return game_state

def process_ai_actions_continuously_debug(controller, logger):
    """模拟Streamlit UI的process_ai_actions_continuously函数，添加详细调试"""
    max_ai_actions = 20  # 防止无限循环
    ai_actions_count = 0
    
    logger.info("\n=== 开始模拟UI的AI连续处理逻辑 ===")
    
    # 记录处理前的状态
    initial_snapshot = controller.get_snapshot()
    initial_phase = initial_snapshot.phase
    initial_events_count = len(initial_snapshot.events)
    
    logger.info(f"初始状态：阶段={initial_phase.value}, 事件数={initial_events_count}")
    
    while ai_actions_count < max_ai_actions:
        logger.info(f"\n--- 循环第{ai_actions_count + 1}次 ---")
        
        # 检查手牌是否结束
        if controller.is_hand_over():
            logger.info("手牌已结束，退出AI处理循环")
            break
            
        # 获取当前玩家
        current_player_id = controller.get_current_player_id()
        logger.info(f"当前玩家ID: {current_player_id}")
        
        if current_player_id is None:
            logger.info("当前玩家为None，尝试强制检查阶段转换")
            # 没有当前玩家，可能需要阶段转换
            try:
                controller._check_phase_transition()
                # 检查阶段转换后是否有新的当前玩家
                current_player_id = controller.get_current_player_id()
                logger.info(f"阶段转换后，当前玩家ID: {current_player_id}")
                if current_player_id is None:
                    logger.info("阶段转换后仍无当前玩家，退出循环")
                    break
            except Exception as e:
                logger.error(f"阶段转换检查失败: {e}")
                break
            
        # 如果轮到人类玩家（玩家0），停止AI处理
        if current_player_id == 0:
            logger.info("轮到人类玩家，停止AI处理")
            break
            
        # 记录行动前的状态
        snapshot_before = controller.get_snapshot()
        phase_before = snapshot_before.phase
        events_before_count = len(snapshot_before.events)
        
        logger.info(f"准备处理AI玩家{current_player_id}的行动")
        logger.info(f"行动前：阶段={phase_before.value}, 事件数={events_before_count}")
        
        # 处理AI行动
        success = controller.process_ai_action()
        logger.info(f"AI行动结果: {success}")
        
        if success:
            ai_actions_count += 1
            
            # 记录行动后的状态
            snapshot_after = controller.get_snapshot()
            phase_after = snapshot_after.phase
            events_after_count = len(snapshot_after.events)
            
            logger.info(f"行动后：阶段={phase_after.value}, 事件数={events_after_count}")
            logger.info(f"新增事件数: {events_after_count - events_before_count}")
            
            # 显示新增的事件
            if events_after_count > events_before_count:
                new_events = snapshot_after.events[events_before_count:]
                for event in new_events:
                    logger.info(f"  新事件: {event}")
            
            # 检查阶段是否发生变化
            if phase_after != phase_before:
                logger.info(f"阶段转换：{phase_before.value} -> {phase_after.value}")
                
                # 阶段转换后，重新检查当前玩家
                new_current_player_id = controller.get_current_player_id()
                logger.info(f"阶段转换后的当前玩家: {new_current_player_id}")
                if new_current_player_id == 0:
                    logger.info("阶段转换后轮到人类玩家，停止AI处理")
                    break
            
            # 检查下一个当前玩家
            next_current_player_id = controller.get_current_player_id()
            logger.info(f"下一个当前玩家: {next_current_player_id}")
            
        else:
            logger.warning("AI行动失败，停止处理")
            break
            
        # 短暂延迟，模拟UI的延迟
        logger.info("模拟UI延迟...")
        time.sleep(0.1)
    
    logger.info(f"\n=== AI处理循环结束 ===")
    logger.info(f"总共处理了{ai_actions_count}次AI行动")
    
    # 处理完成后，检查最终状态
    final_snapshot = controller.get_snapshot()
    final_events_count = len(final_snapshot.events)
    final_current_player = controller.get_current_player_id()
    
    logger.info(f"最终状态：")
    logger.info(f"  阶段: {final_snapshot.phase.value}")
    logger.info(f"  当前玩家: {final_current_player}")
    logger.info(f"  总事件数: {final_events_count}")
    logger.info(f"  手牌是否结束: {controller.is_hand_over()}")
    
    # 返回是否有AI行动被处理
    return ai_actions_count > 0

def main():
    """主函数"""
    logger = setup_logging()
    logger.info("开始调试UI的AI处理逻辑")
    
    try:
        # 创建测试场景
        game_state = create_river_scenario()
        
        # 创建控制器
        event_bus = EventBus()
        ai_strategy = SimpleAI()
        controller = PokerController(game_state, ai_strategy, logger, event_bus)
        controller._hand_in_progress = True
        
        # 模拟UI的AI处理逻辑
        ai_processed = process_ai_actions_continuously_debug(controller, logger)
        
        logger.info(f"\n=== 调试结果 ===")
        logger.info(f"AI处理是否成功: {ai_processed}")
        
        # 检查最终状态
        final_current_player = controller.get_current_player_id()
        if final_current_player is not None:
            player_name = controller._game_state.players[final_current_player].name
            logger.info(f"最终当前玩家: {player_name} (座位{final_current_player})")
            
            if final_current_player == 0:
                logger.info("[OK] 成功：最终轮到人类玩家")
            else:
                logger.warning(f"[PROBLEM] 问题：最终仍轮到AI玩家{player_name}")
        else:
            logger.info("最终没有当前玩家")
        
        logger.info("\n=== 调试完成 ===")
        
    except Exception as e:
        logger.error(f"调试过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 