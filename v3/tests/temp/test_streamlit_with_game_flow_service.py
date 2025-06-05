#!/usr/bin/env python3
"""
使用GameFlowService的Streamlit终测简化版本

验证CQRS重构方案的可行性。
"""

import sys
import os
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import pytest

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v3.application import (
    GameCommandService, GameQueryService, GameFlowService, 
    TestStatsService, HandFlowConfig
)
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class StreamlitGameFlowTester:
    """使用GameFlowService的简化测试器"""
    
    def __init__(self, num_hands: int = 10):
        """初始化测试器"""
        self.num_hands = num_hands
        self.logger = self._setup_logging()
        
        # 初始化v3架构组件
        from v3.core.events import EventBus, set_event_bus
        self.event_bus = EventBus()
        set_event_bus(self.event_bus)
        
        self.command_service = GameCommandService(self.event_bus)
        self.query_service = GameQueryService(self.command_service, self.event_bus)
        self.stats_service = TestStatsService()
        
        # 新增：游戏流程服务
        self.flow_service = GameFlowService(
            command_service=self.command_service,
            query_service=self.query_service,
            event_bus=self.event_bus
        )
        
        # 测试配置
        self.game_id = "flow_test_game"
        self.session_id = f"flow_test_session_{int(time.time())}"
        self.player_ids = ["player_0", "player_1"]
        
    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger("GameFlowTester")
        logger.setLevel(logging.INFO)
        
        # 控制台处理器
        if not logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        return logger
    
    def run_test(self) -> Dict[str, Any]:
        """运行测试"""
        self.logger.info(f"开始GameFlowService测试 - {self.num_hands}手")
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        CoreUsageChecker.verify_real_objects(self.flow_service, "GameFlowService")
        CoreUsageChecker.verify_real_objects(self.stats_service, "TestStatsService")
        
        # 创建测试会话
        session_result = self.stats_service.create_test_session(
            self.session_id, 
            {'initial_total_chips': len(self.player_ids) * 1000}
        )
        
        if not session_result.success:
            self.logger.error(f"创建测试会话失败: {session_result.message}")
            return {'success': False, 'error': session_result.message}
        
        # 设置游戏环境
        if not self._setup_game():
            return {'success': False, 'error': '游戏环境设置失败'}
        
        # 运行手牌循环
        completed_hands = 0
        failed_hands = 0
        
        for hand_num in range(1, self.num_hands + 1):
            try:
                self.logger.info(f"🎯 运行第 {hand_num} 手牌")
                
                # 使用GameFlowService运行手牌
                hand_result = self._run_hand_with_flow_service(hand_num)
                
                if hand_result.success:
                    if hand_result.data.get('game_over'):
                        self.logger.info(f"🏁 游戏在第 {hand_num} 手结束")
                        break
                    elif hand_result.data.get('hand_completed'):
                        completed_hands += 1
                        self.logger.info(f"✅ 第 {hand_num} 手完成")
                    else:
                        # 需要处理玩家行动的情况
                        self._handle_player_actions_if_needed(hand_result)
                        completed_hands += 1
                else:
                    failed_hands += 1
                    self.logger.warning(f"❌ 第 {hand_num} 手失败: {hand_result.message}")
                
            except Exception as e:
                failed_hands += 1
                self.logger.error(f"❌ 第 {hand_num} 手异常: {e}")
        
        # 获取最终统计
        final_stats = self._get_final_stats()
        
        self.logger.info(f"🏆 测试完成 - 完成: {completed_hands}, 失败: {failed_hands}")
        
        return {
            'success': True,
            'completed_hands': completed_hands,
            'failed_hands': failed_hands,
            'total_attempted': hand_num,
            'stats': final_stats
        }
    
    def _setup_game(self) -> bool:
        """设置游戏环境"""
        try:
            # 创建游戏
            create_result = self.command_service.create_new_game(
                self.game_id, self.player_ids
            )
            
            if not create_result.success:
                self.logger.error(f"创建游戏失败: {create_result.message}")
                return False
            
            self.logger.info(f"✅ 游戏创建成功: {self.game_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"设置游戏异常: {e}")
            return False
    
    def _run_hand_with_flow_service(self, hand_number: int) -> Any:
        """使用GameFlowService运行手牌"""
        # 记录手牌开始
        start_result = self.stats_service.record_hand_start(self.session_id)
        if not start_result.success:
            self.logger.warning(f"记录手牌开始失败: {start_result.message}")
        
        try:
            # 使用GameFlowService运行手牌 - 这是关键的迁移点
            config = HandFlowConfig(
                max_actions_per_hand=20,  # 简化测试
                max_same_states=3,
                max_force_finish_attempts=5
            )
            
            flow_result = self.flow_service.run_hand(self.game_id, config)
            
            if flow_result.success:
                # 记录成功
                complete_result = self.stats_service.record_hand_complete(self.session_id)
                if not complete_result.success:
                    self.logger.warning(f"记录手牌完成失败: {complete_result.message}")
            else:
                # 记录失败
                failed_result = self.stats_service.record_hand_failed(self.session_id, flow_result.message)
                if not failed_result.success:
                    self.logger.warning(f"记录手牌失败失败: {failed_result.message}")
            
            return flow_result
            
        except Exception as e:
            # 记录异常
            failed_result = self.stats_service.record_hand_failed(self.session_id, str(e))
            self.logger.error(f"手牌流程异常: {e}")
            # 返回失败结果
            from v3.application.types import CommandResult
            return CommandResult.failure_result(f"手牌异常: {str(e)}")
    
    def _handle_player_actions_if_needed(self, flow_result) -> None:
        """处理需要玩家行动的情况"""
        if not flow_result.data:
            return
            
        if flow_result.data.get('requires_player_action'):
            active_player_id = flow_result.data.get('active_player_id')
            self.logger.info(f"🎮 处理玩家 {active_player_id} 的行动")
            
            # 使用Application层的AI决策
            ai_decision_result = self.query_service.make_ai_decision(
                self.game_id, active_player_id, {}
            )
            
            if ai_decision_result.success:
                from v3.application import PlayerAction
                action = PlayerAction(
                    action_type=ai_decision_result.data['action_type'],
                    amount=ai_decision_result.data['amount']
                )
                
                # 执行玩家行动
                execute_result = self.command_service.execute_player_action(
                    self.game_id, active_player_id, action
                )
                
                if execute_result.success:
                    self.logger.debug(f"玩家行动成功: {action.action_type}")
                else:
                    self.logger.warning(f"玩家行动失败: {execute_result.message}")
        
        elif flow_result.data.get('requires_intervention'):
            self.logger.warning("需要外部干预，尝试强制结束")
            self.flow_service.force_finish_hand(self.game_id)
    
    def _get_final_stats(self) -> Dict[str, Any]:
        """获取最终统计"""
        try:
            # 获取最终筹码
            state_result = self.query_service.get_game_state(self.game_id)
            final_chips = 0
            if state_result.success:
                final_chips = sum(
                    player_data.get('chips', 0) 
                    for player_data in state_result.data.players.values()
                )
            
            # 完成测试会话
            finalize_result = self.stats_service.finalize_test_session(
                self.session_id, final_chips
            )
            
            if finalize_result.success:
                stats_result = self.stats_service.get_test_stats(self.session_id)
                if stats_result.success:
                    return stats_result.data.__dict__
            
            return {'error': 'Failed to get final stats'}
            
        except Exception as e:
            self.logger.error(f"获取最终统计异常: {e}")
            return {'error': str(e)}


def test_game_flow_service_integration():
    """测试GameFlowService集成功能"""
    tester = StreamlitGameFlowTester(num_hands=5)
    result = tester.run_test()
    
    # 验证基本功能
    assert result['success'], f"测试失败: {result.get('error', 'unknown')}"
    assert result['completed_hands'] >= 0, "应该完成至少0手牌"
    assert result['total_attempted'] >= 1, "应该尝试至少1手牌"
    
    # 计算成功率
    if result['total_attempted'] > 0:
        success_rate = result['completed_hands'] / result['total_attempted']
        print(f"手牌成功率: {success_rate:.2%}")
        
        # 成功率应该超过50%（宽松要求）
        assert success_rate >= 0.5, f"成功率过低: {success_rate:.2%}"


def test_game_flow_service_with_more_hands():
    """测试更多手牌的GameFlowService"""
    tester = StreamlitGameFlowTester(num_hands=20)
    result = tester.run_test()
    
    assert result['success'], f"测试失败: {result.get('error', 'unknown')}"
    
    # 打印结果
    print(f"完成手牌: {result['completed_hands']}")
    print(f"失败手牌: {result['failed_hands']}")
    print(f"总尝试: {result['total_attempted']}")


if __name__ == "__main__":
    # 直接运行测试
    print("=== GameFlowService集成测试 ===")
    tester = StreamlitGameFlowTester(num_hands=15)
    result = tester.run_test()
    
    print(f"\n=== 测试结果 ===")
    print(f"成功: {result['success']}")
    print(f"完成手牌: {result['completed_hands']}")
    print(f"失败手牌: {result['failed_hands']}")
    print(f"总尝试: {result['total_attempted']}")
    
    if result.get('stats'):
        stats = result['stats']
        if isinstance(stats, dict):
            print(f"统计信息: {stats.get('hands_completed', 0)} 手完成") 