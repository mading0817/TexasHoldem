#!/usr/bin/env python3
"""
专门调试AI决策过程的脚本

分析AI在特定情况下的决策逻辑和可能的卡住原因。
"""

import sys
import os
import logging

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.state import GameState
from v2.core.player import Player
from v2.core.enums import ActionType, Phase, SeatStatus, Action
from v2.core.cards import Card, Suit, Rank
from v2.controller.dto import GameStateSnapshot, PlayerSnapshot


def setup_logging():
    """设置详细的日志记录"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('debug_ai_decision.log', mode='w', encoding='utf-8')
        ]
    )


def create_test_scenario():
    """创建测试场景：AI_2需要面对$150的下注"""
    # 创建玩家快照
    players = [
        PlayerSnapshot(
            seat_id=0, name="You", chips=741, current_bet=150, 
            status=SeatStatus.ACTIVE, hole_cards=None
        ),
        PlayerSnapshot(
            seat_id=1, name="AI_1", chips=741, current_bet=150, 
            status=SeatStatus.ACTIVE, hole_cards=None
        ),
        PlayerSnapshot(
            seat_id=2, name="AI_2", chips=891, current_bet=0, 
            status=SeatStatus.ACTIVE, hole_cards=None
        ),
        PlayerSnapshot(
            seat_id=3, name="AI_3", chips=891, current_bet=0, 
            status=SeatStatus.ACTIVE, hole_cards=None
        ),
    ]
    
    # 创建游戏状态快照
    snapshot = GameStateSnapshot(
        phase=Phase.RIVER,
        pot=436,
        current_bet=150,
        players=players,
        community_cards=[
            Card(Suit.HEARTS, Rank.JACK),
            Card(Suit.DIAMONDS, Rank.SIX),
            Card(Suit.CLUBS, Rank.FIVE),
            Card(Suit.DIAMONDS, Rank.EIGHT),
            Card(Suit.SPADES, Rank.EIGHT),
        ],
        current_player=2,  # AI_2应该行动
        dealer_position=0,
        small_blind=5,
        big_blind=10,
        hand_number=1
    )
    
    return snapshot


def test_ai_decision():
    """测试AI决策过程"""
    print("=== 测试AI决策过程 ===")
    
    # 创建测试场景
    snapshot = create_test_scenario()
    
    # 创建AI策略
    ai_strategy = SimpleAI()
    
    # 获取AI_2玩家
    ai_player = None
    for player in snapshot.players:
        if player.seat_id == 2:
            ai_player = player
            break
    
    if ai_player is None:
        print("❌ 找不到AI_2玩家")
        return
    
    print(f"AI_2状态:")
    print(f"  筹码: ${ai_player.chips}")
    print(f"  当前下注: ${ai_player.current_bet}")
    print(f"  状态: {ai_player.status}")
    
    print(f"\n游戏状态:")
    print(f"  当前下注: ${snapshot.current_bet}")
    print(f"  底池: ${snapshot.pot}")
    print(f"  阶段: {snapshot.phase}")
    
    # 计算跟注成本
    call_cost = snapshot.current_bet - ai_player.current_bet
    cost_ratio = call_cost / ai_player.chips if ai_player.chips > 0 else 1.0
    
    print(f"\n成本分析:")
    print(f"  跟注成本: ${call_cost}")
    print(f"  成本比例: {cost_ratio:.1%}")
    print(f"  AI弃牌阈值: {ai_strategy.config.fold_threshold:.1%}")
    
    # 测试AI分析
    print(f"\n=== AI分析过程 ===")
    try:
        context = ai_strategy._analyze_situation(ai_player, snapshot)
        print(f"分析结果:")
        for key, value in context.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"❌ AI分析失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 测试AI决策
    print(f"\n=== AI决策过程 ===")
    try:
        action = ai_strategy.decide(snapshot, 2)
        print(f"AI决策结果:")
        print(f"  玩家ID: {action.player_id}")
        print(f"  行动类型: {action.action_type}")
        print(f"  金额: {action.amount}")
    except Exception as e:
        print(f"❌ AI决策失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 验证Action对象
    print(f"\n=== Action对象验证 ===")
    print(f"Action类型: {type(action)}")
    print(f"Action属性:")
    for attr in dir(action):
        if not attr.startswith('_'):
            try:
                value = getattr(action, attr)
                print(f"  {attr}: {value}")
            except Exception as e:
                print(f"  {attr}: 获取失败 - {e}")


def test_action_creation():
    """测试Action对象的创建"""
    print("\n=== 测试Action对象创建 ===")
    
    try:
        # 测试各种Action创建
        actions = [
            Action(player_id=2, action_type=ActionType.FOLD),
            Action(player_id=2, action_type=ActionType.CHECK),
            Action(player_id=2, action_type=ActionType.CALL, amount=150),
            Action(player_id=2, action_type=ActionType.BET, amount=100),
        ]
        
        for i, action in enumerate(actions):
            print(f"Action {i+1}: {action.action_type} - 成功创建")
            
    except Exception as e:
        print(f"❌ Action创建失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    setup_logging()
    test_ai_decision()
    test_action_creation() 