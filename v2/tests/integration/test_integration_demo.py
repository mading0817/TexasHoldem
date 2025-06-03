"""
集成测试演示模块

展示核心集成测试功能，验证Controller→Core→Controller的基本流程。
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


class IntegrationTestDemo:
    """集成测试演示类"""
    
    def __init__(self):
        self.controller = None
        self.game_state = None
        self.results = []
    
    def setup_game(self) -> None:
        """设置游戏环境"""
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
    def test_basic_controller_integration(self) -> Dict[str, Any]:
        """测试基本控制器集成"""
        print("\n=== 基本控制器集成测试 ===")
        
        self.setup_game()
        
        # 开始新手牌
        success = self.controller.start_new_hand()
        assert success, "无法开始新手牌"
        
        # 记录初始状态
        initial_snapshot = self.controller.get_snapshot()
        print(f"✅ 手牌开始: 阶段={initial_snapshot.phase.value}, 底池={initial_snapshot.pot}")
        
        # 执行基本行动序列
        actions_executed = []
        max_actions = 10
        action_count = 0
        
        while not self.controller.is_hand_over() and action_count < max_actions:
            current_player = self.controller.get_current_player_id()
            if current_player is None:
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
        
        # 获取最终状态
        final_snapshot = self.controller.get_snapshot()
        
        result = {
            "test_name": "basic_controller_integration",
            "success": len(actions_executed) > 0,
            "actions_executed": actions_executed,
            "initial_phase": initial_snapshot.phase.value,
            "final_phase": final_snapshot.phase.value,
            "initial_pot": initial_snapshot.pot,
            "final_pot": final_snapshot.pot,
            "hand_completed": self.controller.is_hand_over()
        }
        
        print(f"✅ 控制器集成测试完成: 执行了{len(actions_executed)}个行动")
        return result
    
    def run_basic_integration_demo(self) -> List[Dict[str, Any]]:
        """运行基本集成演示"""
        print("🎯 开始基本集成测试演示")
        print("=" * 60)
        
        demo_results = []
        
        try:
            demo_results.append(self.test_basic_controller_integration())
        except Exception as e:
            print(f"❌ 基本控制器集成测试失败: {e}")
            demo_results.append({"test_name": "basic_controller_integration", "success": False, "error": str(e)})
        
        # 汇总结果
        total_tests = len(demo_results)
        passed_tests = sum(1 for r in demo_results if r["success"])
        
        print("\n" + "=" * 60)
        print("🏆 基本集成测试演示结果")
        print("=" * 60)
        
        for result in demo_results:
            status = "✅" if result["success"] else "❌"
            print(f"{result['test_name']}: {status}")
            if not result["success"] and "error" in result:
                print(f"   错误: {result['error']}")
        
        print(f"\n总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"成功率: {passed_tests / total_tests * 100:.1f}%")
        
        return demo_results


def main():
    """主函数"""
    demo = IntegrationTestDemo()
    results = demo.run_basic_integration_demo()
    return results


if __name__ == "__main__":
    main()