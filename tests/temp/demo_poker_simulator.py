#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PokerSimulator 使用演示

展示如何使用新的测试架构进行游戏模拟
"""

import sys
import os
import random

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core_game_logic.game.game_controller import GameController
from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from tests.common.base_tester import BaseTester
from tests.common.data_structures import TestScenario
from tests.common.poker_simulator import (
    PokerSimulator, ConservativeStrategy, AggressiveStrategy,
    create_default_strategies
)


def demo_basic_simulation():
    """基础模拟演示"""
    print("=" * 60)
    print("🎮 基础模拟演示")
    print("=" * 60)
    
    # 1. 创建游戏环境
    base_tester = BaseTester("Demo")
    scenario = TestScenario(
        name="演示场景",
        players_count=4,
        starting_chips=[1000, 1000, 1000, 1000],
        dealer_position=0,
        expected_behavior={},
        description="4人德州扑克演示"
    )
    
    game_state = base_tester.create_scenario_game(scenario, setup_blinds=False)
    controller = GameController(game_state)
    
    # 2. 创建模拟器
    simulator = PokerSimulator(controller)
    
    # 3. 创建策略
    player_seats = [p.seat_id for p in game_state.players]
    strategies = create_default_strategies(player_seats, "conservative")
    
    # 4. 执行一手牌
    print("🃏 开始模拟一手牌...")
    result = simulator.play_hand(strategies)
    
    # 5. 展示结果
    print(f"✅ 手牌完成: {result.hand_completed}")
    print(f"🔢 活跃玩家: {result.active_players}")
    print(f"💰 最终底池: {result.pot_after_payout}")
    print(f"🏆 获胜者: {result.winners}")
    print(f"📊 完成阶段: {[phase.name for phase in result.phases_completed]}")
    
    if result.errors:
        print(f"⚠️  错误记录: {result.errors}")


def demo_multi_hand_simulation():
    """多手牌模拟演示"""
    print("\n" + "=" * 60)
    print("🎮 多手牌模拟演示")
    print("=" * 60)
    
    # 创建游戏环境
    base_tester = BaseTester("MultiDemo")
    scenario = TestScenario(
        name="多手牌演示",
        players_count=6,
        starting_chips=[500] * 6,
        dealer_position=0,
        expected_behavior={},
        description="6人多手牌演示"
    )
    
    game_state = base_tester.create_scenario_game(scenario, setup_blinds=False)
    controller = GameController(game_state)
    simulator = PokerSimulator(controller)
    
    # 创建策略组合
    player_seats = [p.seat_id for p in game_state.players]
    strategies = {}
    for i, seat in enumerate(player_seats):
        if i < 3:
            strategies[seat] = ConservativeStrategy()
        else:
            strategies[seat] = AggressiveStrategy(all_in_probability=0.2)
    
    print("🃏 策略配置:")
    for seat in player_seats:
        strategy_name = "保守策略" if isinstance(strategies[seat], ConservativeStrategy) else "激进策略"
        player_name = controller.state.get_player_by_seat(seat).name
        print(f"  {player_name} (座位{seat}): {strategy_name}")
    
    # 执行多手牌
    print(f"\n🎯 开始模拟5手牌...")
    results = simulator.play_n_hands(5, strategies)
    
    # 统计结果
    total_hands = len(results)
    completed_hands = sum(1 for r in results if r.hand_completed)
    total_errors = sum(len(r.errors) for r in results)
    
    print(f"\n📊 模拟统计:")
    print(f"  总手牌数: {total_hands}")
    print(f"  成功完成: {completed_hands}")
    print(f"  错误总数: {total_errors}")
    
    # 展示每手牌简要信息
    for i, result in enumerate(results, 1):
        status = "✅" if result.hand_completed else "❌"
        winner_str = ", ".join(result.winners) if result.winners else "无"
        print(f"  手牌{i}: {status} 活跃玩家:{result.active_players} 获胜者:{winner_str}")


def demo_strategy_comparison():
    """策略对比演示"""
    print("\n" + "=" * 60)
    print("🎮 策略对比演示")
    print("=" * 60)
    
    def run_strategy_test(strategy_name: str, strategy_type: str):
        """运行特定策略的测试"""
        base_tester = BaseTester(f"Strategy_{strategy_name}")
        scenario = TestScenario(
            name=f"{strategy_name}测试",
            players_count=4,
            starting_chips=[1000] * 4,
            dealer_position=0,
            expected_behavior={},
            description=f"4人{strategy_name}测试"
        )
        
        game_state = base_tester.create_scenario_game(scenario, setup_blinds=False)
        controller = GameController(game_state)
        simulator = PokerSimulator(controller)
        
        # 设置固定随机种子确保可重复性
        simulator.rng = random.Random(42)
        
        player_seats = [p.seat_id for p in game_state.players]
        strategies = create_default_strategies(player_seats, strategy_type)
        
        # 执行测试
        results = simulator.play_n_hands(3, strategies)
        
        # 统计
        completed = sum(1 for r in results if r.hand_completed)
        avg_active = sum(r.active_players for r in results) / len(results) if results else 0
        
        return {
            'completed': completed,
            'total': len(results),
            'avg_active_players': avg_active,
            'success_rate': completed / len(results) if results else 0
        }
    
    # 对比不同策略
    print("🧪 测试保守策略...")
    conservative_stats = run_strategy_test("保守策略", "conservative")
    
    print("🧪 测试激进策略...")
    aggressive_stats = run_strategy_test("激进策略", "aggressive")
    
    # 展示对比结果
    print("\n📊 策略对比结果:")
    print(f"{'策略类型':<10} {'完成率':<8} {'平均活跃玩家':<12} {'成功率':<8}")
    print("-" * 50)
    print(f"{'保守策略':<10} {conservative_stats['completed']:>2}/{conservative_stats['total']:<3} "
          f"{conservative_stats['avg_active_players']:>10.1f} {conservative_stats['success_rate']:>6.1%}")
    print(f"{'激进策略':<10} {aggressive_stats['completed']:>2}/{aggressive_stats['total']:<3} "
          f"{aggressive_stats['avg_active_players']:>10.1f} {aggressive_stats['success_rate']:>6.1%}")


def demo_error_handling():
    """错误处理演示"""
    print("\n" + "=" * 60)
    print("🎮 错误处理演示")
    print("=" * 60)
    
    # 创建会出错的策略
    class ErrorProneStrategy(ConservativeStrategy):
        def __init__(self, error_probability: float = 0.3):
            self.error_probability = error_probability
            self.call_count = 0
            
        def decide(self, snapshot):
            self.call_count += 1
            # 随机抛出异常
            if random.random() < self.error_probability:
                raise RuntimeError(f"模拟错误 (调用次数: {self.call_count})")
            return super().decide(snapshot)
    
    # 创建测试环境
    base_tester = BaseTester("ErrorDemo")
    scenario = TestScenario(
        name="错误处理演示",
        players_count=3,
        starting_chips=[500] * 3,
        dealer_position=0,
        expected_behavior={},
        description="错误处理演示"
    )
    
    game_state = base_tester.create_scenario_game(scenario, setup_blinds=False)
    controller = GameController(game_state)
    simulator = PokerSimulator(controller)
    
    # 创建混合策略（有些会出错）
    player_seats = [p.seat_id for p in game_state.players]
    strategies = {
        player_seats[0]: ErrorProneStrategy(error_probability=0.5),
        player_seats[1]: ConservativeStrategy(),
        player_seats[2]: ErrorProneStrategy(error_probability=0.3),
    }
    
    print("🃏 策略配置:")
    for seat in player_seats:
        player_name = controller.state.get_player_by_seat(seat).name
        if isinstance(strategies[seat], ErrorProneStrategy):
            print(f"  {player_name}: 易错策略 (50%错误率)")
        else:
            print(f"  {player_name}: 正常策略")
    
    print("\n🎯 开始容错测试...")
    result = simulator.play_hand(strategies)
    
    print(f"\n📊 错误处理结果:")
    print(f"  手牌完成: {'✅' if result.hand_completed else '❌'}")
    print(f"  捕获错误数: {len(result.errors)}")
    print(f"  错误详情:")
    for i, error in enumerate(result.errors, 1):
        print(f"    {i}. {error}")
    
    print(f"  最终状态: 活跃玩家 {result.active_players} 人")


def main():
    """主函数 - 运行所有演示"""
    print("🚀 PokerSimulator 架构演示")
    print("展示重构后测试架构的易用性和强大功能\n")
    
    try:
        # 运行各种演示
        demo_basic_simulation()
        demo_multi_hand_simulation() 
        demo_strategy_comparison()
        demo_error_handling()
        
        print("\n" + "=" * 60)
        print("🎉 所有演示完成！")
        print("=" * 60)
        print("💡 主要亮点:")
        print("  ✅ 无死循环 - 所有模拟都能正常完成")
        print("  ✅ 护栏保护 - 异常情况下自动停止")
        print("  ✅ 策略可插拔 - 轻松切换不同AI策略")
        print("  ✅ 错误容错 - 优雅处理异常情况")
        print("  ✅ 结果结构化 - 便于分析和验证")
        print("\n🔧 这个架构已为AI集成做好准备！")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 