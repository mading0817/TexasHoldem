"""
临时调试文件：验证状态同步问题
测试状态机处理玩家行动后，筹码和total_bet_this_hand是否正确更新
"""

import pytest
from v3.application.command_service import GameCommandService
from v3.application.query_service import GameQueryService  
from v3.application.types import PlayerAction
from v3.core.events import get_event_bus
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


def test_state_sync_after_player_action():
    """测试玩家行动后状态同步"""
    print("\n=== 状态同步调试测试 ===")
    
    # 创建服务
    command_service = GameCommandService()
    query_service = GameQueryService(command_service=command_service)
    
    # 反作弊检查
    CoreUsageChecker.verify_real_objects(command_service, "GameCommandService")
    CoreUsageChecker.verify_real_objects(query_service, "GameQueryService")
    
    # 创建游戏并开始手牌
    game_id = "state_sync_test"
    create_result = command_service.create_new_game(game_id, ["player_0", "player_1"])
    assert create_result.success, f"创建游戏失败: {create_result.message}"
    
    start_result = command_service.start_new_hand(game_id)
    assert start_result.success, f"开始手牌失败: {start_result.message}"
    
    # 获取初始状态
    initial_state_result = query_service.get_game_state(game_id)
    assert initial_state_result.success, f"获取初始状态失败: {initial_state_result.message}"
    initial_state = initial_state_result.data
    
    print(f"初始状态:")
    for player_id, player_data in initial_state.players.items():
        chips = player_data.get('chips', 0)
        current_bet = player_data.get('current_bet', 0)
        total_bet = player_data.get('total_bet_this_hand', 0)
        print(f"  {player_id}: chips={chips}, current_bet={current_bet}, total_bet_this_hand={total_bet}")
    print(f"  底池: {initial_state.pot_total}")
    print(f"  当前下注: {initial_state.current_bet}")
    
    # 立即获取内部状态 (直接访问session)
    session = command_service._get_session(game_id)
    print(f"\n直接从Session获取的状态:")
    for player_id, player_data in session.context.players.items():
        chips = player_data.get('chips', 0)
        current_bet = player_data.get('current_bet', 0)
        total_bet = player_data.get('total_bet_this_hand', 0)
        print(f"  {player_id}: chips={chips}, current_bet={current_bet}, total_bet_this_hand={total_bet}")
    print(f"  底池: {session.context.pot_total}")
    print(f"  当前下注: {session.context.current_bet}")
    
    # 检查初始状态的player_0筹码（应该被小盲注扣除了5）
    initial_player0_chips = initial_state.players['player_0'].get('chips', 0)
    initial_player0_total_bet = initial_state.players['player_0'].get('total_bet_this_hand', 0)
    initial_player0_current_bet = initial_state.players['player_0'].get('current_bet', 0)
    
    # 计算正确的CALL金额：当前下注 - 玩家已下注
    required_call_amount = initial_state.current_bet - initial_player0_current_bet
    print(f"\n计算CALL金额: {initial_state.current_bet} - {initial_player0_current_bet} = {required_call_amount}")
    
    print(f"\n执行player_0 CALL行动 (金额: {required_call_amount})...")
    
    # 执行player_0的CALL行动，使用正确的金额
    call_action = PlayerAction(action_type="call", amount=required_call_amount)
    action_result = command_service.execute_player_action(game_id, "player_0", call_action)
    print(f"行动结果: success={action_result.success}, message={action_result.message}")
    
    if not action_result.success:
        print(f"行动失败，错误码: {action_result.error_code}")
        return
    
    # 立即获取行动后状态
    after_state_result = query_service.get_game_state(game_id)
    assert after_state_result.success, f"获取行动后状态失败: {after_state_result.message}"
    after_state = after_state_result.data
    
    print(f"\n行动后状态 (通过QueryService):")
    for player_id, player_data in after_state.players.items():
        chips = player_data.get('chips', 0)
        current_bet = player_data.get('current_bet', 0) 
        total_bet = player_data.get('total_bet_this_hand', 0)
        print(f"  {player_id}: chips={chips}, current_bet={current_bet}, total_bet_this_hand={total_bet}")
    print(f"  底池: {after_state.pot_total}")
    print(f"  当前下注: {after_state.current_bet}")
    
    # 立即获取内部状态 (直接访问session)
    print(f"\n行动后状态 (直接从Session):")
    for player_id, player_data in session.context.players.items():
        chips = player_data.get('chips', 0)
        current_bet = player_data.get('current_bet', 0)
        total_bet = player_data.get('total_bet_this_hand', 0)
        print(f"  {player_id}: chips={chips}, current_bet={current_bet}, total_bet_this_hand={total_bet}")
    print(f"  底池: {session.context.pot_total}")
    print(f"  当前下注: {session.context.current_bet}")
    
    # 分析差异
    after_player0_chips = after_state.players['player_0'].get('chips', 0)
    after_player0_total_bet = after_state.players['player_0'].get('total_bet_this_hand', 0)
    
    chips_change = after_player0_chips - initial_player0_chips
    total_bet_change = after_player0_total_bet - initial_player0_total_bet
    
    print(f"\n变化分析:")
    print(f"  player_0筹码变化: {initial_player0_chips} → {after_player0_chips} (变化: {chips_change:+d})")
    print(f"  player_0总投入变化: {initial_player0_total_bet} → {after_player0_total_bet} (变化: {total_bet_change:+d})")
    print(f"  底池变化: {initial_state.pot_total} → {after_state.pot_total} (变化: {after_state.pot_total - initial_state.pot_total:+d})")
    
    # 验证状态一致性 
    session_player0_chips = session.context.players['player_0'].get('chips', 0)
    session_player0_total_bet = session.context.players['player_0'].get('total_bet_this_hand', 0)
    
    print(f"\n状态一致性检查:")
    print(f"  QueryService vs Session 筹码一致: {after_player0_chips == session_player0_chips}")
    print(f"  QueryService vs Session 总投入一致: {after_player0_total_bet == session_player0_total_bet}")
    print(f"  QueryService vs Session 底池一致: {after_state.pot_total == session.context.pot_total}")
    
    print(f"\n期望分析:")
    print(f"  期望扣除筹码: {required_call_amount}")
    print(f"  实际扣除筹码: {-chips_change}")
    print(f"  筹码扣除正确: {-chips_change == required_call_amount}")
    print(f"  总投入增加正确: {total_bet_change == required_call_amount}")


if __name__ == "__main__":
    test_state_sync_after_player_action() 