#!/usr/bin/env python3
"""
PLAN B 诊断脚本 - 分析核心问题

用于分析和修复日志中暴露的问题：
1. 筹码状态更新问题
2. 游戏过早结束问题  
3. 获胜事件缺失问题
"""

import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v3.application import (
    GameCommandService, GameQueryService, PlayerAction,
    ConfigService, ValidationService
)


def create_services():
    """创建应用服务"""
    config_service = ConfigService()
    validation_service = ValidationService(config_service)
    command_service = GameCommandService(
        validation_service=validation_service,
        config_service=config_service
    )
    query_service = GameQueryService(
        command_service=command_service,
        config_service=config_service
    )
    return command_service, query_service


def test_basic_game_creation():
    """测试基本游戏创建功能"""
    print("=== 测试1: 基本游戏创建 ===")
    
    command_service, query_service = create_services()
    
    # 创建游戏
    result = command_service.create_new_game('debug_game', ['player_0', 'player_1'])
    print(f"创建游戏: success={result.success}, message={result.message}")
    
    # 获取游戏状态
    state_result = query_service.get_game_state('debug_game')
    if state_result.success:
        state = state_result.data
        print(f"游戏状态:")
        print(f"  - 阶段: {state.current_phase}")
        print(f"  - 底池: {state.pot_total}")
        print(f"  - 当前下注: {state.current_bet}")
        print(f"  - 活跃玩家: {state.active_player_id}")
        
        print(f"  - 玩家状态:")
        for pid, pdata in state.players.items():
            print(f"    * {pid}: chips={pdata.get('chips', 0)}, active={pdata.get('active', False)}, current_bet={pdata.get('current_bet', 0)}")
    
    # 检查是否游戏结束 - 这里应该是False
    game_over_result = query_service.is_game_over('debug_game')
    print(f"游戏结束检查: success={game_over_result.success}, data={game_over_result.data}")
    if hasattr(game_over_result, 'data_details'):
        print(f"  详情: {game_over_result.data_details}")
    
    print()
    return command_service, query_service


def test_hand_start_and_chips():
    """测试手牌开始和筹码状态"""
    print("=== 测试2: 手牌开始和筹码状态 ===")
    
    command_service, query_service = create_services()
    
    # 创建游戏
    command_service.create_new_game('debug_game2', ['player_0', 'player_1'])
    
    # 开始新手牌
    start_result = command_service.start_new_hand('debug_game2')
    print(f"开始手牌: success={start_result.success}, message={start_result.message}")
    
    # 获取手牌开始后的状态
    state_result = query_service.get_game_state('debug_game2')
    if state_result.success:
        state = state_result.data
        print(f"手牌开始后状态:")
        print(f"  - 阶段: {state.current_phase}")
        print(f"  - 底池: {state.pot_total}")
        print(f"  - 当前下注: {state.current_bet}")
        print(f"  - 活跃玩家: {state.active_player_id}")
        
        print(f"  - 玩家状态:")
        for pid, pdata in state.players.items():
            chips = pdata.get('chips', 0)
            current_bet = pdata.get('current_bet', 0)
            total_bet = pdata.get('total_bet_this_hand', 0)
            print(f"    * {pid}: chips={chips}, current_bet={current_bet}, total_bet_this_hand={total_bet}")
            
            # 问题分析：检查筹码是否正确扣除盲注
            if total_bet > 0 and chips == 1000:
                print(f"      ⚠️ 问题发现: {pid}下注了{total_bet}但筹码仍是1000，未正确扣除！")
    
    # 再次检查游戏是否结束
    game_over_result = query_service.is_game_over('debug_game2')
    print(f"手牌开始后游戏结束检查: data={game_over_result.data}")
    if hasattr(game_over_result, 'data_details'):
        print(f"  详情: {game_over_result.data_details}")
        
    print()
    return command_service, query_service


def test_player_action_chips():
    """测试玩家行动后的筹码变化"""
    print("=== 测试3: 玩家行动后筹码变化 ===")
    
    command_service, query_service = create_services()
    
    # 创建游戏并开始手牌
    command_service.create_new_game('debug_game3', ['player_0', 'player_1'])
    command_service.start_new_hand('debug_game3')
    
    # 获取行动前状态
    state_before_result = query_service.get_game_state('debug_game3')
    if state_before_result.success:
        state_before = state_before_result.data
        print("行动前状态:")
        for pid, pdata in state_before.players.items():
            print(f"  {pid}: chips={pdata.get('chips', 0)}")
    
    # 执行玩家行动
    action = PlayerAction(action_type="fold", amount=0)
    action_result = command_service.execute_player_action('debug_game3', 'player_0', action)
    print(f"玩家行动: success={action_result.success}, message={action_result.message}")
    
    # 获取行动后状态
    state_after_result = query_service.get_game_state('debug_game3')
    if state_after_result.success:
        state_after = state_after_result.data
        print("行动后状态:")
        print(f"  - 阶段: {state_after.current_phase}")
        print(f"  - 底池: {state_after.pot_total}")
        
        for pid, pdata in state_after.players.items():
            chips_after = pdata.get('chips', 0)
            print(f"  {pid}: chips={chips_after}")
            
            # 比较前后筹码变化
            if state_before_result.success:
                chips_before = state_before.players[pid].get('chips', 0)
                chips_change = chips_after - chips_before
                print(f"    筹码变化: {chips_before} → {chips_after} (变化: {chips_change:+d})")
                
                # 分析问题：fold应该不会改变筹码，除非之前有未正确处理的下注
                if pid == 'player_0' and action.action_type == 'fold' and chips_change != 0:
                    print(f"    ⚠️ 问题发现: fold行动不应该改变筹码，但筹码变化了{chips_change}")
    
    # 检查fold后游戏是否结束
    game_over_result = query_service.is_game_over('debug_game3')
    print(f"fold后游戏结束检查: data={game_over_result.data}")
    if hasattr(game_over_result, 'data_details'):
        print(f"  详情: {game_over_result.data_details}")
    
    print()


def test_game_over_logic():
    """测试游戏结束逻辑"""
    print("=== 测试4: 游戏结束逻辑 ===")
    
    command_service, query_service = create_services()
    
    # 创建游戏并开始手牌
    command_service.create_new_game('debug_game4', ['player_0', 'player_1'])
    command_service.start_new_hand('debug_game4')
    
    # 让player_0 fold
    action = PlayerAction(action_type="fold", amount=0)
    command_service.execute_player_action('debug_game4', 'player_0', action)
    
    # 检查现在的状态
    state_result = query_service.get_game_state('debug_game4')
    if state_result.success:
        state = state_result.data
        print(f"fold后状态:")
        print(f"  - 阶段: {state.current_phase}")
        print(f"  - 底池: {state.pot_total}")
        
        # 计算还有筹码的玩家
        players_with_chips = []
        for pid, pdata in state.players.items():
            chips = pdata.get('chips', 0)
            active = pdata.get('active', False)
            status = pdata.get('status', 'unknown')
            print(f"  {pid}: chips={chips}, active={active}, status={status}")
            if chips > 0:
                players_with_chips.append(pid)
        
        print(f"  有筹码的玩家: {players_with_chips} (数量: {len(players_with_chips)})")
        
        # 游戏应该还没结束，因为两个玩家都还有筹码
        if len(players_with_chips) >= 2:
            print("  ✅ 正确: 游戏应该继续，因为多个玩家还有筹码")
        else:
            print("  ⚠️ 问题: 游戏可能会被错误地标记为结束")
    
    # 检查is_game_over的判断
    game_over_result = query_service.is_game_over('debug_game4')
    print(f"is_game_over判断: data={game_over_result.data}")
    if hasattr(game_over_result, 'data_details'):
        print(f"  详情: {game_over_result.data_details}")
        
        # 分析问题：如果data=True但应该是False，说明is_game_over逻辑有问题
        if game_over_result.data and len(players_with_chips) >= 2:
            print("  ⚠️ 问题发现: is_game_over返回True，但实际上多个玩家还有筹码，游戏应该继续！")
    
    print()


def main():
    """主函数"""
    print("PLAN B 核心问题诊断")
    print("=" * 50)
    
    try:
        test_basic_game_creation()
        test_hand_start_and_chips()
        test_player_action_chips()
        test_game_over_logic()
        
        print("诊断完成！")
        
    except Exception as e:
        print(f"诊断过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 