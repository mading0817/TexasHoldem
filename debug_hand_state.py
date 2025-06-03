#!/usr/bin/env python3
"""调试手牌状态管理的脚本"""

import sys
import os

# 添加v2目录到Python路径
v2_path = os.path.join(os.path.dirname(__file__), 'v2')
sys.path.insert(0, v2_path)

# 现在可以直接导入模块
from controller.poker_controller import PokerController
from core.game_state import GameState
from ai.simple_ai import SimpleAI
import logging
from core.enums import SeatStatus
from core.player import Player

def test_hand_state():
    """测试手牌状态管理"""
    # 创建控制器
    controller = PokerController(GameState(), SimpleAI(), logging.getLogger())
    
    # 添加玩家
    players = [
        Player(seat_id=0, name='You', chips=1000),
        Player(seat_id=1, name='AI_1', chips=1000),
        Player(seat_id=2, name='AI_2', chips=1000),
        Player(seat_id=3, name='AI_3', chips=1000)
    ]
    
    for player in players:
        player.status = SeatStatus.ACTIVE
        controller._game_state.add_player(player)
    
    print("=== 手牌状态测试 ===")
    
    # 初始状态
    print(f"初始状态:")
    print(f"  _hand_in_progress: {controller._hand_in_progress}")
    print(f"  is_hand_over(): {controller.is_hand_over()}")
    
    # 开始新手牌
    print(f"\n开始新手牌...")
    success = controller.start_new_hand()
    print(f"  成功: {success}")
    print(f"  _hand_in_progress: {controller._hand_in_progress}")
    print(f"  is_hand_over(): {controller.is_hand_over()}")
    
    # 获取快照
    snapshot = controller.get_snapshot()
    print(f"  当前阶段: {snapshot.phase}")
    print(f"  当前玩家: {snapshot.current_player}")
    
    # 结束手牌
    print(f"\n结束手牌...")
    result = controller.end_hand()
    print(f"  结果存在: {result is not None}")
    print(f"  _hand_in_progress: {controller._hand_in_progress}")
    print(f"  is_hand_over(): {controller.is_hand_over()}")
    
    # 再次尝试开始新手牌
    print(f"\n再次开始新手牌...")
    try:
        success2 = controller.start_new_hand()
        print(f"  成功: {success2}")
        print(f"  _hand_in_progress: {controller._hand_in_progress}")
        print(f"  is_hand_over(): {controller.is_hand_over()}")
    except Exception as e:
        print(f"  错误: {e}")
        print(f"  _hand_in_progress: {controller._hand_in_progress}")
        print(f"  is_hand_over(): {controller.is_hand_over()}")

if __name__ == "__main__":
    test_hand_state() 