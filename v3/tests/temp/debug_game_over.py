#!/usr/bin/env python3
"""
诊断游戏结束逻辑问题
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v3.application import *


def test_game_over_after_fold():
    """测试fold后的游戏结束逻辑"""
    print("=== 诊断: fold后游戏结束逻辑 ===")
    
    # 创建服务
    config = ConfigService()
    validation = ValidationService(config)
    cmd = GameCommandService(validation_service=validation, config_service=config)
    query = GameQueryService(command_service=cmd, config_service=config)
    
    # 创建游戏并开始手牌
    cmd.create_new_game('test', ['p0', 'p1'])
    cmd.start_new_hand('test')
    
    print("手牌开始后:")
    state = query.get_game_state('test').data
    for pid, pdata in state.players.items():
        print(f"  {pid}: chips={pdata.get('chips', 0)}")
    
    game_over = query.is_game_over('test')
    print(f"游戏结束? {game_over.data}")
    
    # p0 fold
    action = PlayerAction(action_type="fold", amount=0)
    result = cmd.execute_player_action('test', 'p0', action)
    print(f"\np0 fold: {result.success}")
    
    print("fold后:")
    state = query.get_game_state('test').data
    for pid, pdata in state.players.items():
        chips = pdata.get('chips', 0)
        status = pdata.get('status', 'unknown')
        print(f"  {pid}: chips={chips}, status={status}")
    
    # 这里是关键：fold后游戏是否被错误标记为结束？
    game_over = query.is_game_over('test')
    print(f"fold后游戏结束? {game_over.data}")
    if hasattr(game_over, 'data_details'):
        print(f"详情: {game_over.data_details}")
    
    # 分析：两个玩家都还有筹码，游戏应该继续
    players_with_chips = sum(1 for _, pdata in state.players.items() if pdata.get('chips', 0) > 0)
    print(f"有筹码玩家数: {players_with_chips}")
    
    if game_over.data and players_with_chips >= 2:
        print("⚠️ 问题确认: 游戏被错误标记为结束！")
        return True
    else:
        print("✅ 游戏结束逻辑正常")
        return False


if __name__ == "__main__":
    has_problem = test_game_over_after_fold()
    if has_problem:
        print("\n需要修复游戏结束逻辑！")
    else:
        print("\n游戏结束逻辑正常！") 