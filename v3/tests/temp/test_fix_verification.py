#!/usr/bin/env python3
"""
验证游戏结束逻辑修复
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v3.application import *


def test_fixed_game_flow():
    """测试修复后的游戏流程"""
    print("=== 验证修复后的游戏流程 ===")
    
    # 创建服务
    config = ConfigService()
    validation = ValidationService(config)
    cmd = GameCommandService(validation_service=validation, config_service=config)
    query = GameQueryService(command_service=cmd, config_service=config)
    
    # 创建游戏并开始手牌
    cmd.create_new_game('test', ['p0', 'p1'])
    cmd.start_new_hand('test')
    
    print("游戏开始，两个玩家:")
    state = query.get_game_state('test').data
    for pid, pdata in state.players.items():
        print(f"  {pid}: chips={pdata.get('chips', 0)}")
    
    game_over = query.is_game_over('test')
    print(f"游戏开始时 - 游戏结束? {game_over.data}")
    
    # p0 fold
    action = PlayerAction(action_type="fold", amount=0)
    result = cmd.execute_player_action('test', 'p0', action)
    print(f"\np0 fold结果: {result.success}")
    
    # 检查fold后的状态
    print("fold后状态:")
    state = query.get_game_state('test').data
    for pid, pdata in state.players.items():
        chips = pdata.get('chips', 0)
        status = pdata.get('status', 'unknown')
        print(f"  {pid}: chips={chips}, status={status}")
    
    # 关键检查：fold后游戏不应该结束
    game_over = query.is_game_over('test')
    print(f"fold后 - 游戏结束? {game_over.data}")
    if hasattr(game_over, 'data_details'):
        print(f"  详情: {game_over.data_details}")
    
    # 尝试开始新手牌
    print("\n尝试开始新手牌...")
    new_hand_result = cmd.start_new_hand('test')
    print(f"开始新手牌结果: {new_hand_result.success}")
    if not new_hand_result.success:
        print(f"  错误: {new_hand_result.message}")
    
    if new_hand_result.success:
        print("新手牌成功开始!")
        state = query.get_game_state('test').data
        print(f"新手牌阶段: {state.current_phase}")
        for pid, pdata in state.players.items():
            chips = pdata.get('chips', 0)
            status = pdata.get('status', 'unknown')
            print(f"  {pid}: chips={chips}, status={status}")
        
        # 继续游戏流程测试
        print("\n测试第二手牌中的fold...")
        action = PlayerAction(action_type="fold", amount=0)
        result = cmd.execute_player_action('test', 'p0', action)
        print(f"p0 再次fold: {result.success}")
        
        game_over = query.is_game_over('test')
        print(f"第二手fold后 - 游戏结束? {game_over.data}")
        
        # 尝试第三手牌
        print("\n尝试开始第三手牌...")
        third_hand_result = cmd.start_new_hand('test')
        print(f"开始第三手牌结果: {third_hand_result.success}")
        if third_hand_result.success:
            print("第三手牌成功开始! 修复验证成功!")
        else:
            print(f"第三手牌失败: {third_hand_result.message}")
    
    return new_hand_result.success if new_hand_result else False


if __name__ == "__main__":
    success = test_fixed_game_flow()
    if success:
        print("\n✅ 游戏流程修复验证成功!")
    else:
        print("\n❌ 游戏流程仍有问题!") 