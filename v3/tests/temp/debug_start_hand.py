#!/usr/bin/env python3
"""
调试 start_new_hand 方法行为
"""

import pytest
import logging
from v3.application.command_service import GameCommandService
from v3.application.query_service import GameQueryService
from v3.application.config_service import ConfigService
from v3.application.validation_service import ValidationService
from v3.core.events import get_event_bus
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker

def test_debug_start_new_hand():
    """调试测试：验证start_new_hand的完整流程"""
    
    # 设置日志
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
    
    # 反作弊检查
    CoreUsageChecker.verify_real_objects(command_service, "GameCommandService")
    CoreUsageChecker.verify_real_objects(query_service, "GameQueryService")
    
    game_id = "debug_game"
    player_ids = ["player_0", "player_1"]
    
    logger.info("=== 创建游戏 ===")
    # 1. 创建游戏
    create_result = command_service.create_new_game(game_id, player_ids)
    logger.info(f"创建游戏结果: success={create_result.success}, message={create_result.message}")
    if not create_result.success:
        logger.error(f"创建游戏失败: {create_result.message}")
        assert False, f"创建游戏失败: {create_result.message}"
    
    # 2. 检查创建后的游戏状态
    state_result = query_service.get_game_state(game_id)
    logger.info(f"创建后状态: success={state_result.success}")
    if state_result.success:
        logger.info(f"  - 当前阶段: {state_result.data.current_phase}")
        logger.info(f"  - 玩家数量: {len(state_result.data.players)}")
        logger.info(f"  - 底池: {state_result.data.pot_total}")
        for player_id, info in state_result.data.players.items():
            logger.info(f"  - {player_id}: 筹码={info.get('chips', 0)}, 活跃={info.get('active', False)}")
    
    assert state_result.data.current_phase == "INIT", f"创建后应该是INIT阶段，实际是{state_result.data.current_phase}"
    
    logger.info("=== 开始新手牌 ===")
    # 3. 开始新手牌
    start_result = command_service.start_new_hand(game_id)
    logger.info(f"开始手牌结果: success={start_result.success}, message={start_result.message}")
    if not start_result.success:
        logger.error(f"开始手牌失败: {start_result.message}")
        logger.error(f"错误代码: {start_result.error_code}")
        assert False, f"开始手牌失败: {start_result.message}"
    
    if start_result.data:
        logger.info(f"开始手牌后数据: {start_result.data}")
    
    # 4. 检查开始手牌后的游戏状态
    state_after_start = query_service.get_game_state(game_id)
    logger.info(f"开始手牌后状态: success={state_after_start.success}")
    if state_after_start.success:
        logger.info(f"  - 当前阶段: {state_after_start.data.current_phase}")
        logger.info(f"  - 活跃玩家: {state_after_start.data.active_player_id}")
        logger.info(f"  - 底池: {state_after_start.data.pot_total}")
        logger.info(f"  - 当前下注: {state_after_start.data.current_bet}")
        for player_id, info in state_after_start.data.players.items():
            logger.info(f"  - {player_id}: 筹码={info.get('chips', 0)}, 当前下注={info.get('current_bet', 0)}, 总下注={info.get('total_bet_this_hand', 0)}, 活跃={info.get('active', False)}")
    
    expected_phase = "PRE_FLOP"
    actual_phase = state_after_start.data.current_phase
    assert actual_phase == expected_phase, f"开始手牌后应该是{expected_phase}阶段，实际是{actual_phase}"
    
    # 5. 检查是否有活跃玩家
    active_player = state_after_start.data.active_player_id
    logger.info(f"活跃玩家: {active_player}")
    assert active_player is not None, "开始手牌后应该有活跃玩家"
    
    # 6. 检查盲注是否正确设置
    player_info = state_after_start.data.players
    total_bets = sum(info.get('current_bet', 0) for info in player_info.values())
    logger.info(f"玩家总下注: {total_bets}")
    logger.info(f"底池: {state_after_start.data.pot_total}")
    
    # 盲注应该已经设置（小盲5 + 大盲10 = 15）
    expected_total_bets = 15  # 默认配置：小盲5，大盲10
    assert total_bets == expected_total_bets, f"盲注总额应该是{expected_total_bets}，实际是{total_bets}"
    
    logger.info("=== 调试测试通过 ===")
    print("✅ 调试测试通过：start_new_hand 工作正常")

if __name__ == "__main__":
    test_debug_start_new_hand() 