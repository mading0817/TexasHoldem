#!/usr/bin/env python3
"""
调试 GameFlowService.run_hand 方法行为
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import pytest
import logging
from v3.application.command_service import GameCommandService
from v3.application.query_service import GameQueryService
from v3.application.config_service import ConfigService
from v3.application.validation_service import ValidationService
from v3.application.game_flow_service import GameFlowService, HandFlowConfig
from v3.core.events import get_event_bus
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker

def test_debug_flow_service():
    """调试测试：详细分析GameFlowService.run_hand的行为"""
    
    # 设置详细日志
    logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # 创建服务
    event_bus = get_event_bus()
    config_service = ConfigService()
    validation_service = ValidationService(config_service)
    command_service = GameCommandService(
        event_bus=event_bus,
        validation_service=validation_service,
        config_service=config_service
    )
    query_service = GameQueryService(command_service)
    flow_service = GameFlowService(command_service, query_service, event_bus)
    
    # 反作弊检查
    CoreUsageChecker.verify_real_objects(command_service, "GameCommandService")
    CoreUsageChecker.verify_real_objects(query_service, "GameQueryService")
    
    game_id = "debug_flow_game"
    player_ids = ["player_0", "player_1"]
    
    logger.info("=== 创建游戏 ===")
    # 1. 创建游戏
    create_result = command_service.create_new_game(game_id, player_ids)
    logger.info(f"创建游戏结果: success={create_result.success}, message={create_result.message}")
    assert create_result.success, f"创建游戏失败: {create_result.message}"
    
    # 2. 检查创建后的游戏状态
    state_result = query_service.get_game_state(game_id)
    logger.info(f"创建后状态: {state_result.data.current_phase}")
    assert state_result.data.current_phase == "INIT"
    
    logger.info("=== 调用 GameFlowService.run_hand ===")
    # 3. 调用 GameFlowService.run_hand
    config = HandFlowConfig(max_actions_per_hand=50, max_same_states=3, max_force_finish_attempts=10)
    
    # 模拟监听 run_hand 的详细过程
    logger.info("开始调用 flow_service.run_hand...")
    flow_result = flow_service.run_hand(game_id, config)
    
    logger.info(f"=== GameFlowService.run_hand 结果 ===")
    logger.info(f"success: {flow_result.success}")
    logger.info(f"message: {flow_result.message}")
    logger.info(f"error_code: {flow_result.error_code}")
    if flow_result.data:
        logger.info(f"data: {flow_result.data}")
        
        # 分析返回的数据
        if flow_result.data.get('game_over'):
            logger.info("  -> 游戏已结束")
        elif flow_result.data.get('requires_player_action'):
            logger.info(f"  -> 需要玩家行动: {flow_result.data.get('active_player_id')}")
            logger.info(f"  -> 当前阶段: {flow_result.data.get('current_phase')}")
        elif flow_result.data.get('requires_intervention'):
            logger.info("  -> 需要外部干预")
        elif flow_result.data.get('hand_completed'):
            logger.info("  -> 手牌完成")
        else:
            logger.info(f"  -> 其他情况，数据: {flow_result.data}")
    else:
        logger.info("data: None")
    
    # 4. 检查 run_hand 后的游戏状态
    final_state_result = query_service.get_game_state(game_id)
    logger.info(f"=== run_hand 后的游戏状态 ===")
    if final_state_result.success:
        logger.info(f"当前阶段: {final_state_result.data.current_phase}")
        logger.info(f"活跃玩家: {final_state_result.data.active_player_id}")
        logger.info(f"底池: {final_state_result.data.pot_total}")
        logger.info(f"当前下注: {final_state_result.data.current_bet}")
        for player_id, info in final_state_result.data.players.items():
            logger.info(f"  - {player_id}: 筹码={info.get('chips', 0)}, 当前下注={info.get('current_bet', 0)}, 活跃={info.get('active', False)}")
    
    logger.info("=== 分析结果 ===")
    
    # 分析为什么没有返回 requires_player_action
    if not flow_result.success:
        logger.error(f"❌ GameFlowService.run_hand 失败: {flow_result.message}")
        assert False, f"GameFlowService.run_hand 失败: {flow_result.message}"
    
    # 期望：应该返回 requires_player_action
    if flow_result.data and flow_result.data.get('requires_player_action'):
        logger.info("✅ 正常：GameFlowService 返回需要玩家行动")
        assert final_state_result.data.current_phase == "PRE_FLOP", f"期望PRE_FLOP阶段，实际是{final_state_result.data.current_phase}"
        assert final_state_result.data.active_player_id is not None, "期望有活跃玩家"
    elif flow_result.data and flow_result.data.get('hand_completed'):
        logger.warning("⚠️ 异常：GameFlowService 直接报告手牌完成")
        logger.warning(f"最终阶段: {final_state_result.data.current_phase}")
        assert False, "GameFlowService不应该直接完成手牌，应该返回requires_player_action"
    else:
        logger.error(f"❌ 未知情况：GameFlowService 返回: {flow_result.data}")
        assert False, f"GameFlowService 返回未知结果: {flow_result.data}"

if __name__ == "__main__":
    test_debug_flow_service() 