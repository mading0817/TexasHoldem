#!/usr/bin/env python3
"""
Phase 3 手动测试脚本
验证AI策略、事件系统和决策引擎功能

测试范围：
1. AI策略工厂和不同策略类型
2. 事件总线的发布订阅功能
3. AI决策引擎的完整工作流程
4. CLI与AI引擎的集成
"""

import os
import sys
import time
import random

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_players import (
    StrategyFactory, 
    AIDecisionEngine, 
    AIPlayerProfile, 
    EventBus, 
    EventLogger,
    get_global_event_bus,
    setup_demo_ais
)
from app_controller.dto_models import GameStateSnapshot, PlayerActionInput, GameEvent, GameEventType
from core_game_logic.core.enums import ActionType, GamePhase, SeatStatus
from core_game_logic.core.card import Card, Rank, Suit
from core_game_logic.core.player import Player


def test_strategy_factory():
    """测试AI策略工厂"""
    print("\n" + "="*60)
    print("🧪 测试1: AI策略工厂")
    print("="*60)
    
    try:
        # 测试创建不同类型的策略
        strategies = ['conservative', 'aggressive', 'random']
        for strategy_type in strategies:
            strategy = StrategyFactory.create_strategy(strategy_type)
            print(f"✅ 成功创建 {strategy_type} 策略: {strategy.name}")
            print(f"   策略配置: {strategy.personality_config}")
        
        # 测试获取可用策略列表
        available = StrategyFactory.get_available_strategies()
        print(f"✅ 可用策略类型: {available}")
        
        # 测试无效策略类型
        try:
            StrategyFactory.create_strategy('invalid_strategy')
            print("❌ 应该抛出异常，但没有抛出")
            return False
        except ValueError as e:
            print(f"✅ 正确处理无效策略类型: {e}")
        
        print("✅ 策略工厂测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 策略工厂测试失败: {e}")
        return False


def test_event_bus():
    """测试事件总线"""
    print("\n" + "="*60)
    print("🧪 测试2: 事件总线系统")
    print("="*60)
    
    try:
        # 创建事件总线
        event_bus = EventBus(enable_logging=False)  # 关闭日志避免混乱
        
        # 测试事件计数器
        event_count = 0
        
        def test_handler(event: GameEvent):
            nonlocal event_count
            event_count += 1
            print(f"  📢 收到事件: {event.event_type.value} - {event.message}")
        
        # 订阅事件
        subscription_id = event_bus.subscribe(GameEventType.PLAYER_ACTION, test_handler)
        print(f"✅ 成功订阅事件，订阅ID: {subscription_id}")
        
        # 发布测试事件
        test_event = GameEvent(
            event_type=GameEventType.PLAYER_ACTION,
            message="测试玩家行动事件",
            affected_seat_ids=[1],
            data={'test': True}
        )
        
        event_bus.publish(test_event)
        
        # 验证事件被处理
        if event_count == 1:
            print("✅ 事件成功发布和处理")
        else:
            print(f"❌ 事件处理失败，期望1个事件，实际{event_count}个")
            return False
        
        # 测试事件历史
        history = event_bus.get_event_history(GameEventType.PLAYER_ACTION)
        if len(history) == 1:
            print("✅ 事件历史记录正常")
        else:
            print(f"❌ 事件历史记录异常，期望1个，实际{len(history)}个")
            return False
        
        # 测试取消订阅
        if event_bus.unsubscribe(subscription_id):
            print("✅ 成功取消订阅")
        else:
            print("❌ 取消订阅失败")
            return False
        
        # 测试统计信息
        stats = event_bus.get_stats()
        print(f"✅ 事件总线统计: {stats}")
        
        print("✅ 事件总线测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 事件总线测试失败: {e}")
        return False


def test_ai_decision_engine():
    """测试AI决策引擎"""
    print("\n" + "="*60)
    print("🧪 测试3: AI决策引擎")
    print("="*60)
    
    try:
        # 创建AI决策引擎
        engine = AIDecisionEngine()
        
        # 注册AI玩家
        profile = AIPlayerProfile(
            seat_id=1,
            name="测试AI",
            strategy_type="conservative",
            thinking_time_range=(0.1, 0.3)  # 缩短思考时间
        )
        
        engine.register_ai_player(profile)
        print(f"✅ 成功注册AI玩家: {profile.name}")
        
        # 验证AI注册
        registered_ais = engine.get_registered_ais()
        if len(registered_ais) == 1:
            print(f"✅ AI注册验证通过: {registered_ais[0]}")
        else:
            print(f"❌ AI注册验证失败，期望1个，实际{len(registered_ais)}个")
            return False
        
        # 创建模拟游戏状态快照
        snapshot = create_mock_game_snapshot()
        
        # 模拟底牌
        hole_cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.SPADES)  # 强牌：AK同花
        ]
        
        # 获取AI决策
        print("📋 开始AI决策...")
        decision_start = time.time()
        action = engine.get_ai_decision(snapshot, seat_id=1, hole_cards=hole_cards)
        decision_time = time.time() - decision_start
        
        print(f"✅ AI决策完成，用时 {decision_time:.2f}秒")
        print(f"   决策结果: {action.action_type.name}")
        if action.amount:
            print(f"   金额: {action.amount}")
        if action.metadata:
            print(f"   元数据: {action.metadata}")
        
        # 验证决策的有效性
        if action.validate():
            print("✅ AI决策验证通过")
        else:
            print("❌ AI决策验证失败")
            return False
        
        # 测试AI统计信息
        stats = engine.get_ai_statistics(1)
        if stats and 'decision_count' in stats:
            print(f"✅ AI统计信息: {stats}")
        else:
            print("❌ AI统计信息获取失败")
            return False
        
        # 测试注销AI
        if engine.unregister_ai_player(1):
            print("✅ 成功注销AI玩家")
        else:
            print("❌ 注销AI玩家失败")
            return False
        
        print("✅ AI决策引擎测试通过")
        return True
        
    except Exception as e:
        print(f"❌ AI决策引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_ai_strategies():
    """测试多种AI策略的决策差异"""
    print("\n" + "="*60)
    print("🧪 测试4: 多种AI策略决策差异")
    print("="*60)
    
    try:
        # 创建AI决策引擎
        engine = AIDecisionEngine()
        
        # 注册不同类型的AI
        strategies = ['conservative', 'aggressive', 'random']
        ai_profiles = []
        
        for i, strategy_type in enumerate(strategies):
            profile = AIPlayerProfile(
                seat_id=i + 1,
                name=f"AI-{strategy_type}",
                strategy_type=strategy_type,
                thinking_time_range=(0.05, 0.1)  # 快速决策用于测试
            )
            engine.register_ai_player(profile)
            ai_profiles.append(profile)
            print(f"✅ 注册 {strategy_type} AI")
        
        # 创建测试场景
        snapshot = create_mock_game_snapshot()
        hole_cards = [
            Card(Rank.SEVEN, Suit.HEARTS),
            Card(Rank.TWO, Suit.CLUBS)  # 弱牌：7-2 不同花
        ]
        
        print("\n📊 使用弱牌(7♥ 2♣)测试不同策略:")
        
        # 测试每种策略的决策
        decisions = {}
        for profile in ai_profiles:
            try:
                action = engine.get_ai_decision(snapshot, profile.seat_id, hole_cards)
                decisions[profile.strategy_type] = action
                
                decision_str = action.action_type.name
                if action.amount:
                    decision_str += f"({action.amount})"
                
                print(f"  {profile.strategy_type:12}: {decision_str}")
                
            except Exception as e:
                print(f"  ❌ {profile.strategy_type} 决策失败: {e}")
                return False
        
        # 验证策略间的差异性
        action_types = set(d.action_type for d in decisions.values())
        if len(action_types) >= 2:
            print(f"✅ 策略显示出差异性，共{len(action_types)}种不同决策")
        else:
            print("⚠️  所有策略做出了相同决策（可能正常，取决于场景）")
        
        print("✅ 多策略测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 多策略测试失败: {e}")
        return False


def test_cli_integration():
    """测试CLI与AI引擎的集成"""
    print("\n" + "="*60)
    print("🧪 测试5: CLI与AI引擎集成")
    print("="*60)
    
    try:
        # 这个测试主要验证导入和初始化
        from cli_game import EnhancedCLIGame
        
        print("✅ 成功导入增强CLI游戏类")
        
        # 创建CLI实例
        cli_game = EnhancedCLIGame()
        print("✅ 成功创建CLI游戏实例")
        
        # 验证AI引擎初始化（在创建游戏前应为None）
        if cli_game.ai_engine is None:
            print("✅ AI引擎初始状态正确（未初始化）")
        else:
            print("❌ AI引擎初始状态异常")
            return False
        
        print("✅ CLI集成测试通过")
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ CLI集成测试失败: {e}")
        return False


def create_mock_game_snapshot():
    """创建模拟游戏状态快照用于测试"""
    from app_controller.dto_models import GameStateSnapshot, PlayerSnapshot
    
    # 创建模拟玩家快照
    players = [
        PlayerSnapshot(
            seat_id=0,
            name="Human",
            chips=1000,
            current_bet=0,
            status=SeatStatus.ACTIVE,
            hole_cards_display="A♠ K♠",
            is_dealer=False,
            is_small_blind=False,
            is_big_blind=True
        ),
        PlayerSnapshot(
            seat_id=1,
            name="AI-Test",
            chips=950,
            current_bet=10,  # 大盲
            status=SeatStatus.ACTIVE,
            hole_cards_display="🂠🂠",
            is_dealer=False,
            is_small_blind=True,
            is_big_blind=False
        ),
        PlayerSnapshot(
            seat_id=2,
            name="AI-Other",
            chips=1000,
            current_bet=0,
            status=SeatStatus.ACTIVE,
            hole_cards_display="🂠🂠",
            is_dealer=True,
            is_small_blind=False,
            is_big_blind=False
        )
    ]
    
    return GameStateSnapshot(
        version=1,
        phase=GamePhase.PRE_FLOP,
        community_cards=(),
        pot=0,
        current_bet=10,
        current_player_seat=2,  # 庄家先行动（翻牌前）
        dealer_position=2,
        small_blind=5,
        big_blind=10,
        players=tuple(players),
        is_betting_round_complete=False
    )


def run_all_tests():
    """运行所有Phase 3测试"""
    print("🚀 开始Phase 3 AI系统测试")
    print("="*60)
    
    tests = [
        ("策略工厂", test_strategy_factory),
        ("事件总线", test_event_bus),
        ("AI决策引擎", test_ai_decision_engine),
        ("多策略差异", test_multiple_ai_strategies),
        ("CLI集成", test_cli_integration)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 测试通过\n")
            else:
                failed += 1
                print(f"❌ {test_name} 测试失败\n")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} 测试异常: {e}\n")
    
    # 总结
    print("="*60)
    print("📋 Phase 3 测试总结")
    print("="*60)
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📊 总计: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！Phase 3 AI系统实现成功！")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，需要检查和修复")
        return False


if __name__ == "__main__":
    # 设置随机种子保证可重现性
    random.seed(42)
    
    success = run_all_tests()
    sys.exit(0 if success else 1) 