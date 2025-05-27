"""
简单的下注测试
专门测试边池计算问题
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core_game_logic.pot_manager import PotManager
from core_game_logic.player import Player


def test_simple_betting():
    """测试简单的下注收集"""
    print("测试简单的下注收集...")
    
    # 创建玩家
    players = [
        Player(seat_id=0, name="Alice", chips=100),
        Player(seat_id=1, name="Bob", chips=100),
        Player(seat_id=2, name="Charlie", chips=100)
    ]
    
    # 设置下注
    players[0].current_bet = 10
    players[1].current_bet = 10  
    players[2].current_bet = 20
    
    total_before = sum(p.current_bet for p in players)
    print(f"下注前总额: {total_before}")
    
    # 创建PotManager并收集
    pot_manager = PotManager()
    returns = pot_manager.collect_from_players(players)
    
    total_after = pot_manager.get_total_pot()
    print(f"收集后总额: {total_after}")
    print(f"主池: {pot_manager.main_pot}")
    print(f"边池数: {len(pot_manager.side_pots)}")
    print(f"返还: {returns}")
    
    if pot_manager.side_pots:
        for i, side_pot in enumerate(pot_manager.side_pots):
            print(f"边池{i+1}: {side_pot.amount}, 参与者: {side_pot.eligible_players}")
    
    # 验证总额（底池 + 返还 = 原始投入）
    total_returned = sum(returns.values())
    total_accounted = total_after + total_returned
    if total_accounted == total_before:
        print("✓ 总额匹配（底池 + 返还 = 原始投入）")
    else:
        print(f"❌ 总额不匹配: 期望{total_before}, 实际{total_accounted}")
        
    # 验证玩家下注已重置
    for i, player in enumerate(players):
        if player.current_bet == 0:
            print(f"✓ 玩家{i}下注已重置")
        else:
            print(f"❌ 玩家{i}下注未重置: {player.current_bet}")
            
    # 验证返还逻辑
    if returns:
        for seat_id, amount in returns.items():
            print(f"✓ 玩家{seat_id}获得返还{amount}筹码")
    else:
        print("✓ 无需返还筹码")


if __name__ == "__main__":
    test_simple_betting() 