#!/usr/bin/env python3
"""
测试Streamlit UI摊牌阶段修复的脚本。

模拟UI的摊牌阶段处理逻辑，验证修复是否有效。
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
    """设置日志记录"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def create_showdown_scenario():
    """创建摊牌阶段的测试场景"""
    logger = logging.getLogger(__name__)
    
    # 创建游戏状态
    game_state = GameState()
    
    # 创建并添加4个玩家
    player_you = Player(seat_id=0, name="You", chips=850, is_human=True)
    player_ai1 = Player(seat_id=1, name="AI_1", chips=850)
    player_ai2 = Player(seat_id=2, name="AI_2", chips=850)
    player_ai3 = Player(seat_id=3, name="AI_3", chips=850)
    
    game_state.add_player(player_you)
    game_state.add_player(player_ai1)
    game_state.add_player(player_ai2)
    game_state.add_player(player_ai3)
    
    # 设置庄家位置
    game_state.dealer_position = 3
    
    # 设置摊牌阶段
    game_state.phase = Phase.SHOWDOWN
    
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
    
    # 设置底池（所有玩家都已下注$150）
    game_state.pot = 900  # 4 * 150 + 之前的底池300
    
    # 所有玩家当前下注都是150
    for player in game_state.players:
        player.current_bet = 150
        player.status = SeatStatus.ACTIVE
    
    # 摊牌阶段没有当前玩家
    game_state.current_player = None
    game_state.current_bet = 150
    
    logger.info("=== 摊牌阶段场景设置完成 ===")
    logger.info("所有玩家都已跟注$150，进入摊牌阶段")
    
    return game_state

def simulate_ui_showdown_logic(controller):
    """模拟Streamlit UI的摊牌阶段处理逻辑"""
    logger = logging.getLogger(__name__)
    
    logger.info("\n=== 模拟UI摊牌阶段处理逻辑 ===")
    
    # 模拟UI的检查逻辑
    game_started = True
    
    # 检查手牌是否结束
    is_hand_over = controller.is_hand_over()
    logger.info(f"手牌是否结束: {is_hand_over}")
    
    if game_started and is_hand_over:
        # 手牌结束，检查是否在摊牌阶段需要自动处理
        snapshot = controller.get_snapshot()
        logger.info(f"当前阶段: {snapshot.phase.value}")
        
        if snapshot and snapshot.phase == Phase.SHOWDOWN:
            # 在摊牌阶段，自动结束手牌
            logger.info("🎯 摊牌阶段，正在计算结果...")
            try:
                result = controller.end_hand()
                if result:
                    logger.info("✅ 手牌成功结束")
                    logger.info(f"获胜者: {result.winner_ids}")
                    logger.info(f"底池金额: {result.pot_amount}")
                    logger.info(f"获胜描述: {result.winning_hand_description}")
                    
                    # 模拟记录事件
                    events = []
                    events.append(f"手牌结束: {result.winning_hand_description}")
                    logger.info(f"记录事件: {events[-1]}")
                    
                    return True
                else:
                    logger.error("❌ end_hand() 返回了 None")
                    return False
            except Exception as e:
                logger.error(f"❌ 摊牌阶段处理失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return False
        else:
            logger.warning(f"手牌结束但不在摊牌阶段，当前阶段: {snapshot.phase.value}")
            return False
    else:
        logger.info("不满足摊牌阶段处理条件")
        return False

def main():
    """主函数"""
    logger = setup_logging()
    logger.info("开始测试UI摊牌阶段修复")
    
    try:
        # 创建摊牌阶段场景
        game_state = create_showdown_scenario()
        
        # 创建控制器
        event_bus = EventBus()
        ai_strategy = SimpleAI()
        controller = PokerController(game_state, ai_strategy, logger, event_bus)
        controller._hand_in_progress = True
        
        # 验证初始状态
        logger.info("\n=== 验证初始状态 ===")
        snapshot = controller.get_snapshot()
        logger.info(f"阶段: {snapshot.phase.value}")
        logger.info(f"当前玩家: {controller.get_current_player_id()}")
        logger.info(f"手牌是否结束: {controller.is_hand_over()}")
        logger.info(f"底池: {snapshot.pot}")
        
        # 模拟UI的摊牌阶段处理
        success = simulate_ui_showdown_logic(controller)
        
        if success:
            logger.info("\n🎉 UI摊牌阶段修复测试成功！")
            
            # 验证最终状态
            final_snapshot = controller.get_snapshot()
            logger.info(f"最终手牌进行状态: {controller._hand_in_progress}")
            logger.info(f"最终底池: {final_snapshot.pot}")
            
            return True
        else:
            logger.error("\n❌ UI摊牌阶段修复测试失败！")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    main() 