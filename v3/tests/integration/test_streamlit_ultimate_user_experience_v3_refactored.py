#!/usr/bin/env python3
"""
Streamlit UI 终极用户体验测试 v3 - 重构版本

基于CQRS架构的终极测试，严格遵循UI层职责分离。
展示如何将配置、统计、业务逻辑从UI层移动到Application层。

重构改进：
1. 配置管理 - 通过QueryService.get_ai_config()和get_ui_test_config()获取
2. 统计逻辑 - 通过TestStatsService管理
3. 状态哈希 - 通过QueryService.calculate_game_state_hash()计算
4. 硬编码消除 - 所有配置通过Application层获取
5. 业务逻辑分离 - UI层只负责界面逻辑和用户交互
"""

import sys
import os
import time
import logging
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import pytest

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v3.application import (
    GameCommandService, 
    GameQueryService, 
    PlayerAction,
    TestStatsService,
    TestStatsSnapshot
)
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class UIUserActionType(Enum):
    """UI层用户行动类型（仅用于界面逻辑）"""
    FOLD = "fold"
    CALL = "call"
    RAISE = "raise"
    CHECK = "check"
    BET = "bet"
    ALL_IN = "all_in"
    START_GAME = "start_game"
    START_HAND = "start_hand"


@dataclass
class UIUserAction:
    """UI层用户行动（仅用于界面交互）"""
    action_type: UIUserActionType
    player_id: str = "player_0"
    amount: Optional[int] = None
    timestamp: float = 0.0


class StreamlitUltimateUserTesterV3Refactored:
    """v3版本的Streamlit终极用户测试器 - 重构版本
    
    重构原则：
    1. UI层只负责用户界面逻辑和交互
    2. 所有配置通过Application层获取
    3. 所有统计通过TestStatsService管理
    4. 所有业务逻辑委托给Application层
    5. 遵循CQRS模式，严格分离查询和命令
    """
    
    def __init__(self, test_type: str = "ultimate"):
        """
        初始化测试器
        
        Args:
            test_type: 测试类型 (ultimate, quick, stress等)
        """
        self.test_type = test_type
        self.logger = self._setup_logging()
        
        # v3架构组件 - 严格遵循CQRS模式
        from v3.core.events import EventBus, set_event_bus
        self.event_bus = EventBus()
        set_event_bus(self.event_bus)
        self.command_service = GameCommandService(self.event_bus)
        self.query_service = GameQueryService(self.command_service, self.event_bus)
        self.stats_service = TestStatsService()
        
        # 从Application层获取配置（而不是硬编码）
        self.test_config = self._load_test_config()
        self.ai_config = self._load_ai_config()
        
        # 游戏状态
        self.game_id = "ultimate_test_game"
        self.test_session_id = f"test_session_{int(time.time())}"
        
        # UI层状态追踪
        self._current_hand = 0
        self._previous_state_hashes: List[str] = []
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志记录（UI层职责）"""
        logger = logging.getLogger(f"StreamlitUltimateTestV3Refactored_{self.test_type}")
        logger.setLevel(logging.DEBUG)
        
        # 创建文件处理器
        log_file = project_root / "v3" / "tests" / "test_logs" / f"streamlit_ultimate_test_v3_refactored_{int(time.time())}.log"
        log_file.parent.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _load_test_config(self) -> Dict[str, Any]:
        """
        从Application层加载测试配置
        
        Returns:
            测试配置字典
        """
        try:
            config_result = self.query_service.get_ui_test_config(self.test_type)
            if config_result.success:
                self.logger.info(f"成功加载{self.test_type}测试配置")
                return config_result.data
            else:
                self.logger.warning(f"加载测试配置失败: {config_result.message}，使用默认配置")
                return self._get_fallback_test_config()
        except Exception as e:
            self.logger.error(f"加载测试配置异常: {e}，使用默认配置")
            return self._get_fallback_test_config()
    
    def _get_fallback_test_config(self) -> Dict[str, Any]:
        """回退配置（UI层最小化硬编码）"""
        return {
            'default_player_ids': ["player_0", "player_1"],
            'num_hands': 5,
            'max_actions_per_hand': 20,
            'max_consecutive_same_states': 3,
            'log_level': 'INFO'
        }
    
    def _load_ai_config(self) -> Dict[str, Any]:
        """
        从Application层加载AI配置
        
        Returns:
            AI配置字典
        """
        try:
            config_result = self.query_service.get_ai_config("default")
            if config_result.success:
                self.logger.info("成功加载AI配置")
                return config_result.data
            else:
                self.logger.warning(f"加载AI配置失败: {config_result.message}，使用默认配置")
                return {'fold_weight': 0.25, 'call_weight': 0.5, 'raise_weight': 0.25}
        except Exception as e:
            self.logger.error(f"加载AI配置异常: {e}，使用默认配置")
            return {'fold_weight': 0.25, 'call_weight': 0.5, 'raise_weight': 0.25}
    
    def run_ultimate_test(self) -> Dict[str, Any]:
        """
        运行终极测试
        
        Returns:
            测试结果报告
        """
        self.logger.info("🚀 开始运行终极用户体验测试")
        
        try:
            # 1. 创建测试统计会话（委托给Application层）
            session_result = self.stats_service.create_test_session(
                self.test_session_id,
                initial_config={
                    'initial_total_chips': len(self.test_config['default_player_ids']) * self.test_config.get('initial_chips_per_player', 1000)
                }
            )
            
            if not session_result.success:
                raise Exception(f"创建测试会话失败: {session_result.message}")
            
            # 2. 设置游戏环境
            if not self._setup_game_environment():
                raise Exception("游戏环境设置失败")
            
            # 3. 运行测试手牌
            num_hands = self.test_config.get('num_hands', 5)
            for hand_number in range(1, num_hands + 1):
                self._current_hand = hand_number
                
                try:
                    # 记录手牌开始（委托给统计服务）
                    self.stats_service.record_hand_start(self.test_session_id)
                    
                    # 运行单手牌
                    self._run_single_hand(hand_number)
                    
                    # 记录手牌完成（委托给统计服务）
                    self.stats_service.record_hand_complete(self.test_session_id)
                    
                    self.logger.info(f"✅ 第 {hand_number} 手牌完成")
                    
                except Exception as e:
                    # 记录手牌失败（委托给统计服务）
                    self.stats_service.record_hand_failed(self.test_session_id, str(e))
                    self.logger.error(f"❌ 第 {hand_number} 手牌失败: {e}")
                    break
            
            # 4. 获取最终筹码并完成测试会话
            final_chips = self._get_final_total_chips()
            report_result = self.stats_service.finalize_test_session(
                self.test_session_id, 
                final_total_chips=final_chips
            )
            
            if report_result.success:
                self._log_final_results(report_result.data)
                return report_result.data
            else:
                raise Exception(f"生成最终报告失败: {report_result.message}")
                
        except Exception as e:
            self.logger.error(f"测试执行失败: {e}")
            return {'error': str(e), 'success': False}
            
        finally:
            # 清理资源
            self.stats_service.cleanup_session(self.test_session_id)
    
    def _setup_game_environment(self) -> bool:
        """
        设置游戏环境（UI层职责，配置从Application层获取）
        
        Returns:
            是否设置成功
        """
        try:
            # 从配置获取玩家列表
            player_ids = self.test_config.get('default_player_ids', ["player_0", "player_1"])
            
            # 创建游戏
            result = self.command_service.create_new_game(self.game_id, player_ids)
            if not result.success:
                self.logger.error(f"创建游戏失败: {result.message}")
                return False
            
            self.logger.info(f"游戏环境设置完成，玩家: {player_ids}")
            return True
            
        except Exception as e:
            self.logger.error(f"设置游戏环境失败: {e}")
            return False
    
    def _run_single_hand(self, hand_number: int):
        """
        运行单手牌（UI层职责）
        
        Args:
            hand_number: 手牌编号
        """
        self.logger.info(f"🎯 开始第 {hand_number} 手牌")
        
        # 检查游戏是否结束
        game_over_result = self.query_service.is_game_over(self.game_id)
        if game_over_result.success and game_over_result.data:
            self.logger.info("🏆 游戏已结束")
            return
        
        # 开始新手牌
        start_result = self.command_service.start_new_hand(self.game_id)
        if not start_result.success:
            raise Exception(f"开始新手牌失败: {start_result.message}")
        
        # 模拟手牌过程
        max_actions = self.test_config.get('max_actions_per_hand', 20)
        max_same_states = self.test_config.get('max_consecutive_same_states', 3)
        
        self._simulate_hand_process(max_actions, max_same_states)
    
    def _simulate_hand_process(self, max_actions: int, max_same_states: int):
        """
        模拟手牌过程（UI层逻辑）
        
        Args:
            max_actions: 最大行动数
            max_same_states: 最大相同状态数
        """
        action_count = 0
        consecutive_same_states = 0
        
        while action_count < max_actions:
            # 获取游戏状态
            state_result = self.query_service.get_game_state(self.game_id)
            if not state_result.success:
                self.logger.warning(f"获取游戏状态失败: {state_result.message}")
                break
            
            game_state = state_result.data
            
            # 检查手牌是否结束
            if game_state.current_phase == "FINISHED":
                self.logger.debug("手牌已结束")
                break
            
            # 检测状态变化（使用Application层的状态哈希服务）
            hash_result = self.query_service.calculate_game_state_hash(self.game_id)
            if hash_result.success:
                current_hash = hash_result.data
                if self._previous_state_hashes and self._previous_state_hashes[-1] == current_hash:
                    consecutive_same_states += 1
                    if consecutive_same_states >= max_same_states:
                        self.logger.warning(f"检测到状态无变化(连续{consecutive_same_states}次)，强制结束手牌")
                        self._force_finish_hand()
                        break
                else:
                    consecutive_same_states = 0
                
                self._previous_state_hashes.append(current_hash)
                # 只保留最近几个状态哈希
                if len(self._previous_state_hashes) > 5:
                    self._previous_state_hashes.pop(0)
            
            # 检查是否需要推进阶段
            should_advance_result = self.query_service.should_advance_phase(self.game_id)
            if should_advance_result.success and should_advance_result.data:
                advance_result = self.command_service.advance_phase(self.game_id)
                if not advance_result.success:
                    if "不变量违反" in advance_result.message:
                        self.stats_service.record_invariant_violation(
                            self.test_session_id, 
                            f"阶段推进不变量违反: {advance_result.message}",
                            is_critical=True
                        )
                        raise Exception(f"不变量违反: {advance_result.message}")
                    else:
                        self.logger.warning(f"推进阶段失败: {advance_result.message}")
                        break
                action_count += 1
                continue
            
            # 处理玩家行动
            active_player_id = game_state.active_player_id
            if active_player_id:
                self._handle_player_action(active_player_id)
            
            action_count += 1
            
            if action_count >= max_actions - 5:
                self.logger.warning(f"行动数过多({action_count})，强制结束手牌")
                self._force_finish_hand()
                break
    
    def _handle_player_action(self, player_id: str):
        """
        处理玩家行动（UI层逻辑，业务逻辑委托给Application层）
        
        Args:
            player_id: 玩家ID
        """
        action_start_time = time.time()
        
        try:
            # 使用Application层的AI决策服务
            ai_decision_result = self.query_service.make_ai_decision(
                self.game_id, player_id, self.ai_config
            )
            
            if not ai_decision_result.success:
                raise Exception(f"AI决策生成失败: {ai_decision_result.message}")
            
            ai_decision = ai_decision_result.data
            
            # 转换为PlayerAction
            player_action = PlayerAction(
                action_type=ai_decision['action_type'],
                amount=ai_decision['amount']
            )
            
            # 执行行动
            result = self.command_service.execute_player_action(
                self.game_id, player_id, player_action
            )
            
            # 记录行动统计（委托给统计服务）
            action_time = time.time() - action_start_time
            self.stats_service.record_user_action(
                self.test_session_id,
                player_action.action_type,
                success=result.success,
                action_time=action_time,
                error_message=result.message if not result.success else None
            )
            
            if result.success:
                self.logger.debug(f"玩家 {player_id} 执行 {player_action.action_type} 成功")
            else:
                if "不变量违反" in result.message:
                    self.stats_service.record_invariant_violation(
                        self.test_session_id,
                        f"玩家 {player_id} 行动不变量违反: {result.message}",
                        is_critical=True
                    )
                    raise Exception(f"不变量违反: {result.message}")
                else:
                    self.logger.warning(f"玩家 {player_id} 行动失败: {result.message}")
            
        except Exception as e:
            action_time = time.time() - action_start_time
            
            # 记录失败的行动
            self.stats_service.record_user_action(
                self.test_session_id,
                "unknown",
                success=False,
                action_time=action_time,
                error_message=str(e)
            )
            
            if "不变量违反" in str(e):
                # 重新抛出不变量违反异常
                raise
            else:
                self.logger.error(f"玩家 {player_id} 行动异常: {e}")
    
    def _force_finish_hand(self):
        """
        强制结束手牌（UI层逻辑）
        """
        try:
            # 这里可以添加强制结束的逻辑
            # 例如推进到FINISHED阶段
            self.logger.debug("尝试强制结束手牌")
            # 实际实现根据需要添加
        except Exception as e:
            self.logger.error(f"强制结束手牌失败: {e}")
    
    def _get_final_total_chips(self) -> int:
        """
        获取最终总筹码（UI层逻辑，数据从Application层获取）
        
        Returns:
            最终总筹码
        """
        try:
            state_result = self.query_service.get_game_state(self.game_id)
            if state_result.success:
                return sum(
                    player_data.get('chips', 0) 
                    for player_data in state_result.data.players.values()
                )
            else:
                self.logger.warning(f"获取最终游戏状态失败: {state_result.message}")
                return 0
        except Exception as e:
            self.logger.error(f"获取最终筹码失败: {e}")
            return 0
    
    def _log_final_results(self, report: Dict[str, Any]):
        """
        记录最终结果（UI层展示逻辑）
        
        Args:
            report: 来自统计服务的测试报告
        """
        self.logger.info("=" * 80)
        self.logger.info("🏆 v3 Streamlit终极用户测试结果 - 重构版")
        self.logger.info("=" * 80)
        
        # 展示摘要
        summary = report.get('summary', {})
        self.logger.info(f"手牌完成率: {summary.get('completion_rate_percent', 0)}% "
                        f"({summary.get('hands_completed', 0)}/{summary.get('hands_attempted', 0)})")
        self.logger.info(f"行动成功率: {summary.get('action_success_rate_percent', 0)}% "
                        f"({summary.get('hands_completed', 0)})")
        
        # 展示筹码守恒
        chip_info = report.get('chip_conservation', {})
        self.logger.info(f"筹码守恒: {'✅' if chip_info.get('conservation_ok', False) else '❌'} "
                        f"初始{chip_info.get('initial_chips', 0)}, 最终{chip_info.get('final_chips', 0)}")
        
        # 展示不变量违反
        invariant_info = report.get('invariant_violations', {})
        self.logger.info(f"不变量检查: {invariant_info.get('total_violations', 0)} 个违反, "
                        f"{invariant_info.get('critical_violations', 0)} 个严重违反")
        
        # 展示性能
        performance = report.get('performance', {})
        self.logger.info(f"测试速度: {summary.get('hands_per_second', 0)} 手/秒")


def test_streamlit_ultimate_user_experience_v3_refactored_quick():
    """快速重构版终极测试"""
    # 反作弊检查
    tester = StreamlitUltimateUserTesterV3Refactored("quick")
    CoreUsageChecker.verify_real_objects(tester.command_service, "GameCommandService")
    CoreUsageChecker.verify_real_objects(tester.query_service, "GameQueryService")
    CoreUsageChecker.verify_real_objects(tester.stats_service, "TestStatsService")
    
    # 运行测试
    result = tester.run_ultimate_test()
    
    # 验证测试成功
    assert 'error' not in result or not result.get('error'), f"测试失败: {result.get('error', 'Unknown error')}"
    
    # 验证基本指标
    summary = result.get('summary', {})
    assert summary.get('hands_completed', 0) > 0, "没有完成任何手牌"
    assert summary.get('completion_rate_percent', 0) >= 80, f"完成率过低: {summary.get('completion_rate_percent', 0)}%"
    assert summary.get('action_success_rate_percent', 0) >= 90, f"行动成功率过低: {summary.get('action_success_rate_percent', 0)}%"
    
    # 验证筹码守恒
    chip_info = result.get('chip_conservation', {})
    assert chip_info.get('conservation_ok', False), "筹码守恒违反"
    
    # 验证不变量
    invariant_info = result.get('invariant_violations', {})
    assert invariant_info.get('critical_violations', 0) == 0, f"发现严重不变量违反: {invariant_info.get('critical_violations', 0)}"


if __name__ == "__main__":
    # 用于调试的直接运行
    tester = StreamlitUltimateUserTesterV3Refactored("quick")
    result = tester.run_ultimate_test()
    print("测试完成，结果:", result.get('summary', {})) 