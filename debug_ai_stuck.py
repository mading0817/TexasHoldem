#!/usr/bin/env python3
"""调试AI卡住问题的脚本"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'v2'))

from v2.core.state import GameState
from v2.ai.simple_ai import SimpleAI
from v2.controller.poker_controller import PokerController
from v2.core.events import EventBus
from v2.core.player import Player
from v2.core.enums import Phase, SeatStatus, ActionType, Action
import logging

def setup_logging():
    """设置详细的日志记录"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('debug_ai_stuck.log', mode='w', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

def create_test_scenario():
    """创建测试场景：模拟用户描述的情况"""
    logger = setup_logging()
    
    # 创建游戏组件
    game_state = GameState()
    ai_strategy = SimpleAI()
    event_bus = EventBus()
    controller = PokerController(game_state, ai_strategy, logger, event_bus)
    
    # 添加玩家
    players = [
        Player(seat_id=0, name="You", chips=981),
        Player(seat_id=1, name="AI_1", chips=985), 
        Player(seat_id=2, name="AI_2", chips=989),
        Player(seat_id=3, name="AI_3", chips=1017)
    ]
    
    for player in players:
        game_state.add_player(player)
    
    logger.info("=== 开始调试AI卡住问题 ===")
    
    # 开始新手牌
    if not controller.start_new_hand():
        logger.error("无法开始新手牌")
        return
    
    logger.info("新手牌开始成功")
    
    # 模拟完整的游戏流程到用户描述的状态
    logger.info("\n=== 模拟游戏流程到翻牌阶段 ===")
    
    # 1. 模拟翻牌前的行动（简化处理）
    # 让游戏自然进行到翻牌阶段
    max_preflop_actions = 20
    preflop_actions = 0
    
    while game_state.phase == Phase.PRE_FLOP and preflop_actions < max_preflop_actions:
        current_player_id = controller.get_current_player_id()
        if current_player_id is None:
            controller._check_phase_transition()
            continue
            
        if current_player_id == 0:
            # 人类玩家简单跟注
            action = Action(action_type=ActionType.CALL, amount=0, player_id=0)
            controller.execute_action(action)
            logger.info("人类玩家跟注")
        else:
            # AI玩家行动
            controller.process_ai_action()
            
        preflop_actions += 1
    
    # 检查是否成功进入翻牌阶段
    if game_state.phase != Phase.FLOP:
        logger.error(f"未能进入翻牌阶段，当前阶段: {game_state.phase}")
        return
    
    logger.info(f"成功进入翻牌阶段")
    logger.info(f"翻牌: {[str(card) for card in game_state.community_cards]}")
    
    # 2. 模拟翻牌阶段的行动，重现用户描述的状态
    logger.info("\n=== 模拟翻牌阶段行动 ===")
    
    # 根据用户描述的日志：
    # 4. [flop] You 过牌
    # 5. [flop] AI_1 过牌  
    # 6. [flop] AI_2 下注 4
    # 7. [flop] AI_3 跟注到 4
    # 8. [flop] You 跟注到 4
    
    flop_actions = []
    
    # 模拟这些行动
    while game_state.phase == Phase.FLOP:
        current_player_id = controller.get_current_player_id()
        if current_player_id is None:
            logger.info("当前玩家为None，检查阶段转换")
            controller._check_phase_transition()
            break
            
        current_player = game_state.players[current_player_id]
        logger.info(f"当前轮到: {current_player.name} (ID: {current_player_id})")
        logger.info(f"  筹码: {current_player.chips}, 当前下注: {current_player.current_bet}")
        logger.info(f"  游戏当前下注: {game_state.current_bet}")
        
        if current_player_id == 0:
            # 人类玩家的行动
            if game_state.current_bet > current_player.current_bet:
                # 需要跟注
                action = Action(action_type=ActionType.CALL, amount=0, player_id=0)
                controller.execute_action(action)
                logger.info(f"人类玩家跟注到 {game_state.current_bet}")
                flop_actions.append(f"You 跟注到 {game_state.current_bet}")
            else:
                # 可以过牌
                action = Action(action_type=ActionType.CHECK, amount=0, player_id=0)
                controller.execute_action(action)
                logger.info("人类玩家过牌")
                flop_actions.append("You 过牌")
        else:
            # AI玩家行动
            logger.info(f"处理AI玩家 {current_player.name} 的行动")
            success = controller.process_ai_action()
            if success:
                # 获取行动后的状态来记录行动
                new_snapshot = controller.get_snapshot()
                if len(new_snapshot.events) > 0:
                    last_event = new_snapshot.events[-1]
                    flop_actions.append(last_event)
                    logger.info(f"AI行动: {last_event}")
            else:
                logger.error(f"AI玩家 {current_player.name} 行动失败")
                break
        
        # 检查是否所有玩家都行动过
        if len(flop_actions) >= 8:  # 假设每个玩家最多行动2次
            break
    
    logger.info(f"\n翻牌阶段行动记录:")
    for i, action in enumerate(flop_actions, 1):
        logger.info(f"{i}. {action}")
    
    # 3. 现在测试AI卡住的情况
    logger.info("\n=== 测试AI处理逻辑（模拟UI的process_ai_actions_continuously） ===")
    
    # 模拟UI的AI连续处理逻辑
    max_iterations = 10
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        logger.info(f"\n--- UI处理迭代 {iteration} ---")
        
        # 检查手牌是否结束
        if controller.is_hand_over():
            logger.info("手牌已结束")
            break
        
        # 获取当前玩家
        current_player_id = controller.get_current_player_id()
        logger.info(f"当前玩家ID: {current_player_id}")
        
        if current_player_id is None:
            logger.warning("当前玩家为None，尝试检查阶段转换")
            try:
                controller._check_phase_transition()
                new_current_player_id = controller.get_current_player_id()
                logger.info(f"阶段转换后当前玩家ID: {new_current_player_id}")
                if new_current_player_id is None:
                    logger.error("阶段转换后仍无当前玩家，可能存在问题")
                    break
                current_player_id = new_current_player_id
            except Exception as e:
                logger.error(f"阶段转换失败: {e}")
                break
        
        # 如果是人类玩家，停止AI处理
        if current_player_id == 0:
            logger.info("轮到人类玩家，UI应该显示行动按钮")
            break
        
        # 处理AI行动
        current_player = game_state.players[current_player_id]
        logger.info(f"UI准备处理AI玩家 {current_player.name} 的行动")
        
        try:
            success = controller.process_ai_action()
            logger.info(f"AI行动结果: {success}")
            
            if not success:
                logger.error("AI行动失败")
                break
                
            # 获取更新后的状态
            snapshot = controller.get_snapshot()
            logger.info(f"行动后状态:")
            logger.info(f"  阶段: {snapshot.phase}")
            logger.info(f"  当前玩家: {snapshot.current_player}")
            logger.info(f"  当前下注: {snapshot.current_bet}")
            logger.info(f"  底池: {snapshot.pot}")
            
        except Exception as e:
            logger.error(f"AI行动异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            break
    
    logger.info(f"\n=== 调试完成，共进行了{iteration}次UI迭代 ===")
    
    # 最终状态报告
    final_snapshot = controller.get_snapshot()
    logger.info(f"\n=== 最终状态报告 ===")
    logger.info(f"阶段: {final_snapshot.phase}")
    logger.info(f"当前玩家: {final_snapshot.current_player}")
    logger.info(f"手牌是否结束: {controller.is_hand_over()}")
    logger.info(f"底池: {final_snapshot.pot}")
    logger.info(f"当前下注: {final_snapshot.current_bet}")
    
    for player in final_snapshot.players:
        logger.info(f"玩家 {player.name}: 筹码={player.chips}, 当前下注={player.current_bet}, 状态={player.status}")

if __name__ == "__main__":
    create_test_scenario() 