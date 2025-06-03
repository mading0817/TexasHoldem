#!/usr/bin/env python3
"""
测试摊牌阶段修复的脚本。

验证在河牌阶段所有玩家跟注后，游戏能够正确进入摊牌阶段并自动结束手牌。
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
from v2.core.enums import Action
import logging

class TestAI:
    """测试用的简单AI，只会跟注或过牌"""
    
    def decide(self, snapshot, player_id):
        """简单决策：如果需要跟注就跟注，否则过牌"""
        player = snapshot.players[player_id]
        
        if snapshot.current_bet > player.current_bet:
            # 需要跟注
            return Action(
                action_type=ActionType.CALL,
                amount=0,
                player_id=player_id
            )
        else:
            # 过牌
            return Action(
                action_type=ActionType.CHECK,
                amount=0,
                player_id=player_id
            )

def setup_logging():
    """设置日志记录"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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

def test_showdown_transition():
    """测试摊牌阶段转换和自动结束"""
    logger = setup_logging()
    logger.info("开始测试摊牌阶段修复")
    
    try:
        # 创建测试场景
        game_state = create_river_scenario()
        
        # 创建控制器
        event_bus = EventBus()
        ai_strategy = TestAI()  # 使用简单的测试AI
        controller = PokerController(game_state, ai_strategy, logger, event_bus)
        controller._hand_in_progress = True
        
        logger.info("\n=== 步骤1：验证初始状态 ===")
        initial_snapshot = controller.get_snapshot()
        logger.info(f"初始阶段: {initial_snapshot.phase.value}")
        logger.info(f"当前玩家: {controller.get_current_player_id()}")
        logger.info(f"手牌是否结束: {controller.is_hand_over()}")
        
        logger.info("\n=== 步骤2：处理AI_2行动 ===")
        success = controller.process_ai_action()
        logger.info(f"AI_2行动结果: {success}")
        
        snapshot_after_ai2 = controller.get_snapshot()
        logger.info(f"AI_2行动后阶段: {snapshot_after_ai2.phase.value}")
        logger.info(f"AI_2行动后当前玩家: {controller.get_current_player_id()}")
        
        logger.info("\n=== 步骤3：处理AI_3行动 ===")
        success = controller.process_ai_action()
        logger.info(f"AI_3行动结果: {success}")
        
        snapshot_after_ai3 = controller.get_snapshot()
        logger.info(f"AI_3行动后阶段: {snapshot_after_ai3.phase.value}")
        logger.info(f"AI_3行动后当前玩家: {controller.get_current_player_id()}")
        logger.info(f"手牌是否结束: {controller.is_hand_over()}")
        
        logger.info("\n=== 步骤4：验证摊牌阶段 ===")
        if snapshot_after_ai3.phase == Phase.SHOWDOWN:
            logger.info("✅ 成功转换到摊牌阶段")
            
            # 测试自动结束手牌
            logger.info("\n=== 步骤5：测试自动结束手牌 ===")
            result = controller.end_hand()
            
            if result:
                logger.info("✅ 手牌成功结束")
                logger.info(f"获胜者: {result.winner_ids}")
                logger.info(f"底池金额: {result.pot_amount}")
                logger.info(f"获胜描述: {result.winning_hand_description}")
                
                # 验证手牌状态
                final_snapshot = controller.get_snapshot()
                logger.info(f"最终手牌进行状态: {controller._hand_in_progress}")
                logger.info(f"最终底池: {final_snapshot.pot}")
                
                logger.info("\n=== 测试结果 ===")
                logger.info("✅ 摊牌阶段修复测试通过")
                return True
            else:
                logger.error("❌ 手牌结束失败")
                return False
        else:
            logger.error(f"❌ 未能转换到摊牌阶段，当前阶段: {snapshot_after_ai3.phase.value}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主函数"""
    success = test_showdown_transition()
    if success:
        print("\n🎉 摊牌阶段修复测试成功！")
    else:
        print("\n❌ 摊牌阶段修复测试失败！")
    return success

if __name__ == "__main__":
    main() 