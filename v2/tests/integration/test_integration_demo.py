"""
集成测试演示模块

展示完整闭环集成测试框架的各种功能和用法。
"""

import sys
import os
from pathlib import Path
import time
import pytest
from typing import List, Dict, Any

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
v2_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(v2_path))

from v2.core.state import GameState
from v2.core.enums import Phase, ActionType, SeatStatus, Action
from v2.core.player import Player
from v2.controller.poker_controller import PokerController
from .end_to_end_loop import EndToEndLoopTester, UserOperation, OperationType
from .performance_benchmarks import PerformanceBenchmarkSuite, BenchmarkType


class IntegrationTestDemo:
    """集成测试演示类"""
    
    def __init__(self):
        self.controller = None
        self.game_state = None
        self.results = []
    
    def reset_controller(self) -> None:
        """重置控制器状态"""
        if self.controller:
            # 强制结束当前手牌（如果有的话）
            if hasattr(self.controller, '_hand_in_progress'):
                self.controller._hand_in_progress = False
        
        # 重新创建控制器
        self.controller = None
        self.game_state = None
    
    def setup_game(self) -> None:
        """设置游戏环境"""
        # 先重置控制器状态
        self.reset_controller()
        
        # 创建游戏状态
        self.game_state = GameState()
        
        # 添加测试玩家
        players = [
            Player(seat_id=0, name="Alice", chips=1000, status=SeatStatus.ACTIVE),
            Player(seat_id=1, name="Bob", chips=1000, status=SeatStatus.ACTIVE),
            Player(seat_id=2, name="Charlie", chips=1000, status=SeatStatus.ACTIVE),
            Player(seat_id=3, name="Diana", chips=1000, status=SeatStatus.ACTIVE)
        ]
        
        for player in players:
            self.game_state.add_player(player)
        
        # 初始化牌组
        self.game_state.initialize_deck()
        
        # 创建控制器
        self.controller = PokerController(game_state=self.game_state)
    
    @pytest.mark.integration
    @pytest.mark.fast
    def test_complete_hand_simulation(self) -> Dict[str, Any]:
        """测试完整手牌模拟"""
        print("\n=== 完整手牌模拟测试 ===")
        
        # 确保控制器状态被重置
        self.reset_controller()
        self.setup_game()
        
        # 开始新手牌
        success = self.controller.start_new_hand()
        assert success, "无法开始新手牌"
        
        # 记录初始状态
        initial_snapshot = self.controller.get_snapshot()
        print(f"✅ 手牌开始: 阶段={initial_snapshot.phase.value}, 底池={initial_snapshot.pot}")
        
        # 模拟完整的手牌直到结束
        actions_executed = []
        max_actions = 50  # 防止无限循环的安全限制
        action_count = 0
        
        while not self.controller.is_hand_over() and action_count < max_actions:
            current_player = self.controller.get_current_player_id()
            if current_player is None:
                # 没有当前玩家，可能需要推进阶段或手牌已结束
                break
            
            # 简单策略：前两个玩家跟注，后两个玩家弃牌
            if current_player in [0, 1]:
                action = Action(ActionType.CALL, 0, current_player)
            else:
                action = Action(ActionType.FOLD, 0, current_player)
            
            try:
                success = self.controller.execute_action(action)
                if success:
                    actions_executed.append((current_player, action.action_type.value))
                    print(f"✅ 玩家{current_player} 执行 {action.action_type.value}")
                else:
                    print(f"❌ 玩家{current_player} 执行 {action.action_type.value} 失败")
                    break
            except Exception as e:
                print(f"❌ 执行行动时出错: {e}")
                break
            
            action_count += 1
        
        # 如果手牌还没结束，尝试手动结束
        if not self.controller.is_hand_over():
            print("⚠️ 手牌未自动结束，尝试手动结束")
            try:
                hand_result = self.controller.end_hand()
                if hand_result:
                    print(f"✅ 手动结束手牌成功: {hand_result.winning_hand_description}")
            except Exception as e:
                print(f"❌ 手动结束手牌失败: {e}")
        
        # 获取最终状态
        final_snapshot = self.controller.get_snapshot()
        
        result = {
            "test_name": "complete_hand_simulation",
            "success": len(actions_executed) > 0,
            "actions_executed": actions_executed,
            "initial_phase": initial_snapshot.phase.value,
            "final_phase": final_snapshot.phase.value,
            "initial_pot": initial_snapshot.pot,
            "final_pot": final_snapshot.pot,
            "hand_completed": self.controller.is_hand_over()
        }
        
        print(f"✅ 手牌模拟完成: 执行了{len(actions_executed)}个行动")
        print(f"   - 初始阶段: {initial_snapshot.phase.value}")
        print(f"   - 最终阶段: {final_snapshot.phase.value}")
        print(f"   - 手牌完成: {result['hand_completed']}")
        return result
    
    @pytest.mark.integration
    @pytest.mark.fast
    def test_user_operation_simulator(self) -> Dict[str, Any]:
        """测试用户操作模拟器"""
        print("\n=== 用户操作模拟器测试 ===")
        
        # 确保控制器状态被重置
        self.reset_controller()
        self.setup_game()
        
        # 开始游戏
        self.controller.start_new_hand()
        
        # 直接模拟用户操作序列
        operations = [
            (0, ActionType.CALL),
            (1, ActionType.CALL),
            (2, ActionType.FOLD),
            (3, ActionType.FOLD)
        ]
        
        successful_operations = 0
        for player_id, action_type in operations:
            current_player = self.controller.get_current_player_id()
            if current_player == player_id:
                try:
                    action = Action(action_type, 0, player_id)
                    success = self.controller.execute_action(action)
                    if success:
                        successful_operations += 1
                        print(f"✅ 模拟操作成功: 玩家{player_id} {action_type.value}")
                    else:
                        print(f"❌ 模拟操作失败: 玩家{player_id} {action_type.value}")
                except Exception as e:
                    print(f"❌ 执行操作时出错: {e}")
            else:
                print(f"⚠️ 跳过操作: 当前玩家{current_player}, 操作玩家{player_id}")
        
        result = {
            "test_name": "user_operation_simulator",
            "success": successful_operations > 0,
            "total_operations": len(operations),
            "successful_operations": successful_operations,
            "success_rate": successful_operations / len(operations) if operations else 0
        }
        
        print(f"✅ 用户操作模拟完成: {successful_operations}/{len(operations)} 成功")
        return result
    
    @pytest.mark.integration
    @pytest.mark.fast
    def test_performance_benchmarks(self) -> Dict[str, Any]:
        """测试性能基准"""
        print("\n=== 性能基准测试 ===")
        
        # 确保控制器状态被重置
        self.reset_controller()
        self.setup_game()
        
        try:
            # 创建性能基准测试套件
            benchmark_suite = PerformanceBenchmarkSuite()
            
            # 运行基准测试
            results = benchmark_suite.run_benchmarks(self.controller)
            
            # 分析结果
            total_benchmarks = len(results)
            passed_benchmarks = sum(1 for r in results if r.passed)
            
            print(f"✅ 性能基准测试完成: {passed_benchmarks}/{total_benchmarks} 通过")
            
            for result in results:
                status = "✅" if result.passed else "❌"
                print(f"{status} {result.benchmark_type.value}: {result.duration:.2f}ms")
            
            return {
                "test_name": "performance_benchmarks",
                "success": passed_benchmarks > 0,
                "total_benchmarks": total_benchmarks,
                "passed_benchmarks": passed_benchmarks,
                "results": [
                    {
                        "type": r.benchmark_type.value,
                        "duration": r.duration,
                        "passed": r.passed,
                        "threshold": r.threshold
                    }
                    for r in results
                ]
            }
        except Exception as e:
            print(f"❌ 性能基准测试执行失败: {e}")
            return {
                "test_name": "performance_benchmarks",
                "success": False,
                "error": str(e),
                "total_benchmarks": 0,
                "passed_benchmarks": 0,
                "results": []
            }
    
    @pytest.mark.integration
    @pytest.mark.fast
    def test_end_to_end_loop(self) -> Dict[str, Any]:
        """测试端到端循环"""
        print("\n=== 端到端循环测试 ===")
        
        # 确保控制器状态被重置
        self.reset_controller()
        self.setup_game()
        
        try:
            # 创建端到端循环测试器
            loop_tester = EndToEndLoopTester()
            
            # 运行端到端测试
            test_result = loop_tester.run_complete_test(self.controller)
            
            print(f"✅ 端到端循环测试完成: {'成功' if test_result.success else '失败'}")
            print(f"   - 执行步骤: {test_result.steps_executed}")
            print(f"   - 状态变更: {test_result.state_changes}")
            print(f"   - 总耗时: {test_result.total_duration:.2f}ms")
            
            return {
                "test_name": "end_to_end_loop",
                "success": test_result.success,
                "steps_executed": test_result.steps_executed,
                "state_changes": test_result.state_changes,
                "total_duration": test_result.total_duration,
                "performance_metrics": test_result.performance_metrics
            }
        except Exception as e:
            print(f"❌ 端到端循环测试执行失败: {e}")
            return {
                "test_name": "end_to_end_loop",
                "success": False,
                "error": str(e),
                "steps_executed": 0,
                "state_changes": 0,
                "total_duration": 0,
                "performance_metrics": {}
            }
    
    def run_all_demos(self) -> List[Dict[str, Any]]:
        """运行所有演示测试"""
        print("🎯 开始集成测试演示")
        print("=" * 60)
        
        demo_results = []
        
        # 运行各种演示测试，每个测试都重新设置环境
        try:
            demo_results.append(self.test_complete_hand_simulation())
        except Exception as e:
            print(f"❌ 完整手牌模拟测试失败: {e}")
            demo_results.append({"test_name": "complete_hand_simulation", "success": False, "error": str(e)})
        
        try:
            demo_results.append(self.test_user_operation_simulator())
        except Exception as e:
            print(f"❌ 用户操作模拟器测试失败: {e}")
            demo_results.append({"test_name": "user_operation_simulator", "success": False, "error": str(e)})
        
        try:
            demo_results.append(self.test_performance_benchmarks())
        except Exception as e:
            print(f"❌ 性能基准测试失败: {e}")
            demo_results.append({"test_name": "performance_benchmarks", "success": False, "error": str(e)})
        
        try:
            demo_results.append(self.test_end_to_end_loop())
        except Exception as e:
            print(f"❌ 端到端循环测试失败: {e}")
            demo_results.append({"test_name": "end_to_end_loop", "success": False, "error": str(e)})
        
        # 汇总结果
        total_tests = len(demo_results)
        passed_tests = sum(1 for r in demo_results if r["success"])
        
        print("\n" + "=" * 60)
        print("🏆 集成测试演示结果汇总")
        print("=" * 60)
        
        for result in demo_results:
            status = "✅" if result["success"] else "❌"
            print(f"{result['test_name']}: {status}")
            if not result["success"] and "error" in result:
                print(f"   错误: {result['error']}")
        
        print(f"\n总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {total_tests - passed_tests}")
        print(f"成功率: {passed_tests / total_tests * 100:.1f}%")
        
        if passed_tests == total_tests:
            print("\n🎉 所有演示测试通过！集成测试框架功能完整！")
        else:
            print(f"\n⚠️ 有 {total_tests - passed_tests} 个演示测试失败")
        
        return demo_results


def main():
    """主函数"""
    demo = IntegrationTestDemo()
    results = demo.run_all_demos()
    return results


if __name__ == "__main__":
    main()