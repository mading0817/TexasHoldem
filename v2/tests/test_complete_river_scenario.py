#!/usr/bin/env python3
"""
完整的河牌场景测试。

从河牌阶段开始，模拟所有AI行动，验证能够正确进入摊牌阶段并自动结束手牌。
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from v2.core.state import GameState
from v2.core.enums import Phase, ActionType, SeatStatus, Action
from v2.core.cards import Card, Suit, Rank
from v2.core.player import Player
from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.events import EventBus
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

def simulate_complete_scenario():
    """模拟完整的河牌到摊牌场景"""
    logger = setup_logging()
    logger.info("开始完整河牌场景测试")
    
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
        
        # 模拟UI的process_ai_actions_continuously逻辑
        logger.info("\n=== 步骤2：模拟UI的AI连续处理 ===")
        max_ai_actions = 10
        ai_actions_count = 0
        
        while ai_actions_count < max_ai_actions:
            if controller.is_hand_over():
                logger.info("手牌结束，退出AI处理循环")
                break
                
            current_player_id = controller.get_current_player_id()
            if current_player_id is None:
                logger.info("当前玩家为None，尝试检查阶段转换")
                try:
                    controller._check_phase_transition()
                    current_player_id = controller.get_current_player_id()
                    if current_player_id is None:
                        logger.info("阶段转换后仍无当前玩家，退出循环")
                        break
                except Exception as e:
                    logger.error(f"阶段转换检查失败: {e}")
                    break
                
            # 如果轮到人类玩家，停止AI处理
            if current_player_id == 0:
                logger.info("轮到人类玩家，停止AI处理")
                break
                
            # 处理AI行动
            logger.info(f"处理AI玩家{current_player_id}的行动")
            success = controller.process_ai_action()
            logger.info(f"AI行动结果: {success}")
            
            if success:
                ai_actions_count += 1
                
                # 检查阶段变化
                snapshot_after = controller.get_snapshot()
                logger.info(f"行动后阶段: {snapshot_after.phase.value}")
                logger.info(f"行动后当前玩家: {controller.get_current_player_id()}")
            else:
                logger.warning("AI行动失败，停止处理")
                break
        
        logger.info(f"AI处理循环结束，共处理了{ai_actions_count}次AI行动")
        
        # 检查最终状态
        final_snapshot = controller.get_snapshot()
        logger.info(f"\n=== 步骤3：检查最终状态 ===")
        logger.info(f"最终阶段: {final_snapshot.phase.value}")
        logger.info(f"最终当前玩家: {controller.get_current_player_id()}")
        logger.info(f"手牌是否结束: {controller.is_hand_over()}")
        
        # 模拟UI的摊牌阶段处理
        if controller.is_hand_over() and final_snapshot.phase == Phase.SHOWDOWN:
            logger.info("\n=== 步骤4：模拟UI摊牌阶段处理 ===")
            logger.info("🎯 摊牌阶段，正在计算结果...")
            
            try:
                result = controller.end_hand()
                if result:
                    logger.info("✅ 手牌成功结束")
                    logger.info(f"获胜者: {result.winner_ids}")
                    logger.info(f"底池金额: {result.pot_amount}")
                    logger.info(f"获胜描述: {result.winning_hand_description}")
                    
                    # 验证最终状态
                    final_final_snapshot = controller.get_snapshot()
                    logger.info(f"最终手牌进行状态: {controller._hand_in_progress}")
                    logger.info(f"最终底池: {final_final_snapshot.pot}")
                    
                    logger.info("\n🎉 完整河牌场景测试成功！")
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
            logger.error(f"❌ 未能正确进入摊牌阶段")
            logger.error(f"手牌结束: {controller.is_hand_over()}")
            logger.error(f"当前阶段: {final_snapshot.phase.value}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主函数"""
    success = simulate_complete_scenario()
    if success:
        print("\n🎉 完整河牌场景测试成功！修复有效！")
    else:
        print("\n❌ 完整河牌场景测试失败！")
    return success

if __name__ == "__main__":
    main() 