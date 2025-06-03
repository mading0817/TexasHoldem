#!/usr/bin/env python3
"""
Streamlit UI 终极用户体验测试

模拟真实用户在Streamlit界面下进行1000手德州扑克游戏，全面验证：
1. UI操作流程是否正确
2. 游戏逻辑是否准确
3. 筹码计算是否正确
4. 日志显示是否完整
5. 错误处理是否健壮
6. 性能表现是否稳定

这是站在玩家角度的终极集成测试。
"""

import sys
import os
import time
import logging
import random
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from unittest.mock import Mock, patch, MagicMock
import pytest

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.enums import ActionType, Phase, Action, SeatStatus
from v2.core.state import GameState
from v2.core.player import Player
from v2.core.events import EventBus


class UserActionType(Enum):
    """用户行动类型"""
    FOLD = "fold"
    CALL = "call"
    RAISE = "raise"
    CHECK = "check"
    BET = "bet"
    ALL_IN = "all_in"
    START_GAME = "start_game"
    TOGGLE_DEBUG = "toggle_debug"
    VIEW_LOGS = "view_logs"


@dataclass
class UserAction:
    """用户行动"""
    action_type: UserActionType
    player_id: int = 0
    amount: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    ui_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GameError:
    """游戏错误记录"""
    error_type: str
    error_message: str
    hand_number: int
    action_context: Optional[UserAction] = None
    timestamp: float = field(default_factory=time.time)
    severity: str = "ERROR"  # ERROR, WARNING, CRITICAL


@dataclass
class UltimateTestStats:
    """终极测试统计"""
    hands_attempted: int = 0
    hands_completed: int = 0
    hands_failed: int = 0
    total_user_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    
    # 筹码相关
    initial_total_chips: int = 0
    final_total_chips: int = 0
    chip_conservation_violations: List[str] = field(default_factory=list)
    
    # 错误统计
    errors: List[GameError] = field(default_factory=list)
    critical_errors: int = 0
    warnings: int = 0
    
    # 性能统计
    total_test_time: float = 0
    average_hand_time: float = 0
    average_action_time: float = 0
    
    # UI相关统计
    ui_render_errors: int = 0
    session_state_errors: int = 0
    debug_mode_toggles: int = 0
    
    # 游戏流程统计
    phase_transitions: Dict[str, int] = field(default_factory=dict)
    action_distribution: Dict[str, int] = field(default_factory=dict)
    winner_distribution: Dict[str, int] = field(default_factory=dict)


class StreamlitUISimulator:
    """Streamlit UI模拟器"""
    
    def __init__(self):
        self.session_state = {}
        self.ui_components = {}
        self.render_history = []
        self.logger = logging.getLogger(__name__)
        
    def setup_mock_streamlit(self):
        """设置模拟的Streamlit环境"""
        # 模拟session state
        mock_session_state = MagicMock()
        mock_session_state.__contains__ = lambda key: key in self.session_state
        mock_session_state.__getitem__ = lambda key: self.session_state.get(key)
        mock_session_state.__setitem__ = lambda key, value: self.session_state.update({key: value})
        
        # 模拟UI组件
        self.ui_components = {
            'title': Mock(),
            'markdown': Mock(),
            'button': Mock(return_value=False),
            'selectbox': Mock(return_value="INFO"),
            'checkbox': Mock(return_value=False),
            'columns': Mock(return_value=[Mock(), Mock(), Mock()]),
            'sidebar': Mock(),
            'success': Mock(),
            'error': Mock(),
            'warning': Mock(),
            'info': Mock(),
            'rerun': Mock()
        }
        
        return mock_session_state, self.ui_components
    
    def simulate_user_click(self, button_name: str) -> bool:
        """模拟用户点击按钮"""
        if button_name in self.ui_components:
            self.ui_components[button_name].return_value = True
            return True
        return False
    
    def simulate_debug_toggle(self) -> bool:
        """模拟调试模式切换"""
        current_debug = self.session_state.get('debug_mode', False)
        self.session_state['debug_mode'] = not current_debug
        return not current_debug
    
    def get_session_state_snapshot(self) -> Dict[str, Any]:
        """获取session state快照"""
        return self.session_state.copy()


class UserBehaviorSimulator:
    """用户行为模拟器"""
    
    def __init__(self, strategy: str = "balanced"):
        self.strategy = strategy
        self.action_history = []
        self.decision_patterns = self._setup_decision_patterns()
    
    def _setup_decision_patterns(self) -> Dict[str, Dict[str, float]]:
        """设置决策模式"""
        patterns = {
            "aggressive": {
                "fold_probability": 0.15,
                "call_probability": 0.35,
                "raise_probability": 0.40,
                "check_probability": 0.10
            },
            "conservative": {
                "fold_probability": 0.40,
                "call_probability": 0.45,
                "raise_probability": 0.10,
                "check_probability": 0.05
            },
            "balanced": {
                "fold_probability": 0.25,
                "call_probability": 0.40,
                "raise_probability": 0.25,
                "check_probability": 0.10
            },
            "random": {
                "fold_probability": 0.25,
                "call_probability": 0.25,
                "raise_probability": 0.25,
                "check_probability": 0.25
            }
        }
        return patterns.get(self.strategy, patterns["balanced"])
    
    def decide_action(self, game_snapshot, player_id: int) -> UserAction:
        """决定用户行动"""
        # 获取当前玩家
        player = None
        for p in game_snapshot.players:
            if p.seat_id == player_id:
                player = p
                break
        
        if not player or player.is_folded():
            return UserAction(UserActionType.FOLD, player_id)
        
        # 根据游戏状态决定行动
        if game_snapshot.current_bet > 0:
            # 需要跟注或弃牌
            rand = random.random()
            if rand < self.decision_patterns["fold_probability"]:
                return UserAction(UserActionType.FOLD, player_id)
            elif rand < self.decision_patterns["fold_probability"] + self.decision_patterns["call_probability"]:
                return UserAction(UserActionType.CALL, player_id)
            else:
                # 加注
                raise_amount = min(game_snapshot.current_bet * 2, player.chips)
                return UserAction(UserActionType.RAISE, player_id, raise_amount)
        else:
            # 可以过牌或下注
            rand = random.random()
            if rand < self.decision_patterns["check_probability"]:
                return UserAction(UserActionType.CHECK, player_id)
            elif rand < self.decision_patterns["check_probability"] + self.decision_patterns["raise_probability"]:
                # 下注
                bet_amount = min(game_snapshot.big_blind * 2, player.chips)
                return UserAction(UserActionType.BET, player_id, bet_amount)
            else:
                return UserAction(UserActionType.CHECK, player_id)


class StreamlitUltimateUserTester:
    """Streamlit终极用户测试器"""
    
    def __init__(self, num_hands: int = 1000):
        self.num_hands = num_hands
        self.stats = UltimateTestStats()
        self.ui_simulator = StreamlitUISimulator()
        self.user_simulator = UserBehaviorSimulator("balanced")
        self.logger = self._setup_logging()
        
        # 游戏组件
        self.controller = None
        self.game_state = None
        self.ai_strategy = None
        self.event_bus = None
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志记录"""
        logger = logging.getLogger("StreamlitUltimateTest")
        logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        log_file = project_root / "v2" / "tests" / "test_logs" / f"streamlit_ultimate_test_{int(time.time())}.log"
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
    
    def setup_game_environment(self):
        """设置游戏环境"""
        # 创建游戏状态
        self.game_state = GameState()
        self.ai_strategy = SimpleAI()
        self.event_bus = EventBus()
        
        # 添加玩家
        players = [
            Player(seat_id=0, name="User", chips=1000, status=SeatStatus.ACTIVE),
            Player(seat_id=1, name="AI_Alice", chips=1000, status=SeatStatus.ACTIVE),
            Player(seat_id=2, name="AI_Bob", chips=1000, status=SeatStatus.ACTIVE),
            Player(seat_id=3, name="AI_Charlie", chips=1000, status=SeatStatus.ACTIVE)
        ]
        
        for player in players:
            self.game_state.add_player(player)
        
        # 初始化牌组
        self.game_state.initialize_deck()
        
        # 创建控制器
        self.controller = PokerController(
            game_state=self.game_state,
            ai_strategy=self.ai_strategy,
            logger=self.logger,
            event_bus=self.event_bus
        )
        
        # 记录初始筹码
        self.stats.initial_total_chips = sum(p.chips for p in self.game_state.players)
        
        self.logger.info(f"游戏环境设置完成，初始总筹码: {self.stats.initial_total_chips}")
    
    def simulate_streamlit_app_initialization(self):
        """模拟Streamlit应用初始化"""
        try:
            mock_session_state, ui_components = self.ui_simulator.setup_mock_streamlit()
            
            # 模拟应用初始化过程
            with patch('streamlit.session_state', mock_session_state), \
                 patch('streamlit.title', ui_components['title']), \
                 patch('streamlit.markdown', ui_components['markdown']), \
                 patch('streamlit.button', ui_components['button']), \
                 patch('streamlit.sidebar', ui_components['sidebar']):
                
                # 模拟初始化session state
                self.ui_simulator.session_state.update({
                    'controller': self.controller,
                    'game_started': False,
                    'events': [],
                    'debug_mode': False,
                    'show_logs': False,
                    'show_raise_input': False,
                    'show_bet_input': False
                })
                
                self.logger.info("Streamlit应用初始化模拟完成")
                return True
                
        except Exception as e:
            error = GameError(
                error_type="UI_INITIALIZATION_ERROR",
                error_message=f"Streamlit初始化失败: {str(e)}",
                hand_number=0,
                severity="CRITICAL"
            )
            self.stats.errors.append(error)
            self.stats.critical_errors += 1
            return False
    
    def run_ultimate_test(self) -> UltimateTestStats:
        """运行终极用户测试"""
        self.logger.info(f"开始Streamlit终极用户测试 - {self.num_hands}手")
        start_time = time.time()
        
        # 设置游戏环境
        self.setup_game_environment()
        
        # 模拟Streamlit应用初始化
        if not self.simulate_streamlit_app_initialization():
            self.logger.error("应用初始化失败，测试终止")
            return self.stats
        
        # 运行测试
        for hand_num in range(1, self.num_hands + 1):
            try:
                self._run_single_hand_with_ui_simulation(hand_num)
                
                # 每100手报告进度
                if hand_num % 100 == 0:
                    self._log_progress(hand_num)
                    
            except Exception as e:
                error = GameError(
                    error_type="HAND_EXECUTION_ERROR",
                    error_message=f"Hand {hand_num}: {str(e)}",
                    hand_number=hand_num,
                    severity="ERROR"
                )
                self.stats.errors.append(error)
                self.stats.hands_failed += 1
                self.logger.error(f"Hand {hand_num} 执行失败: {e}")
                continue
        
        # 计算最终统计
        self._calculate_final_stats(start_time)
        
        # 记录最终结果
        self._log_final_results()
        
        return self.stats
    
    def _run_single_hand_with_ui_simulation(self, hand_number: int):
        """运行单手牌并模拟UI交互"""
        self.stats.hands_attempted += 1
        hand_start_time = time.time()
        
        try:
            # 模拟用户开始新手牌
            start_action = UserAction(UserActionType.START_GAME, 0)
            if not self._execute_user_action(start_action, hand_number):
                raise Exception("无法开始新手牌")
            
            # 记录手牌开始时的筹码（包含底池和当前下注）
            start_chips = sum(p.chips for p in self.game_state.players)
            start_current_bets = sum(p.current_bet for p in self.game_state.players)
            start_pot = self.game_state.pot
            
            # 模拟手牌过程
            max_actions = 200  # 防止无限循环
            action_count = 0
            
            while not self.controller.is_hand_over() and action_count < max_actions:
                current_player_id = self.controller.get_current_player_id()
                if current_player_id is None:
                    break
                
                # 记录阶段转换
                current_phase = self.controller.get_snapshot().phase.value
                self.stats.phase_transitions[current_phase] = self.stats.phase_transitions.get(current_phase, 0) + 1
                
                if current_player_id == 0:  # 用户玩家
                    # 模拟用户决策和UI交互
                    user_action = self._simulate_user_decision_with_ui(current_player_id, hand_number)
                    if user_action:
                        self._execute_user_action(user_action, hand_number)
                else:  # AI玩家
                    # 处理AI行动
                    self.controller.process_ai_action()
                
                action_count += 1
                
                # 偶尔模拟调试模式切换
                if random.random() < 0.05:  # 5%概率
                    self._simulate_debug_mode_toggle()
            
            # 结束手牌
            if self.controller.is_hand_over():
                try:
                    result = self.controller.end_hand()
                    self.stats.hands_completed += 1
                    
                    # 记录获胜者
                    if result and result.winner_ids:
                        for winner_id in result.winner_ids:
                            winner_name = f"Player_{winner_id}"
                            self.stats.winner_distribution[winner_name] = self.stats.winner_distribution.get(winner_name, 0) + 1
                    
                except Exception as e:
                    error = GameError(
                        error_type="HAND_END_ERROR",
                        error_message=f"结束手牌失败: {str(e)}",
                        hand_number=hand_number,
                        severity="ERROR"
                    )
                    self.stats.errors.append(error)
            else:
                self.stats.hands_failed += 1
                # 强制重置手牌状态
                if hasattr(self.controller, 'force_reset_hand_state'):
                    self.controller.force_reset_hand_state()
            
            # 检查筹码守恒（包含底池和当前下注）
            end_chips = sum(p.chips for p in self.game_state.players)
            end_current_bets = sum(p.current_bet for p in self.game_state.players)
            end_pot = self.game_state.pot
            start_total = start_chips + start_current_bets + start_pot
            end_total = end_chips + end_current_bets + end_pot
            
            if start_total != end_total:
                violation = f"Hand {hand_number}: 筹码守恒违规 ({start_total} -> {end_total})"
                self.stats.chip_conservation_violations.append(violation)
                self.logger.warning(violation)
            
            # 记录手牌时间
            hand_time = time.time() - hand_start_time
            self.stats.average_hand_time = ((self.stats.average_hand_time * (hand_number - 1)) + hand_time) / hand_number
            
        except Exception as e:
            self.stats.hands_failed += 1
            error = GameError(
                error_type="HAND_SIMULATION_ERROR",
                error_message=str(e),
                hand_number=hand_number,
                severity="ERROR"
            )
            self.stats.errors.append(error)
            raise
    
    def _simulate_user_decision_with_ui(self, player_id: int, hand_number: int) -> Optional[UserAction]:
        """模拟用户决策和UI交互"""
        try:
            # 获取游戏状态
            game_snapshot = self.controller.get_snapshot()
            
            # 模拟UI渲染延迟
            time.sleep(0.01)  # 10ms UI渲染延迟
            
            # 用户决策
            user_action = self.user_simulator.decide_action(game_snapshot, player_id)
            
            # 模拟UI交互（按钮点击等）
            self._simulate_ui_interaction(user_action)
            
            return user_action
            
        except Exception as e:
            error = GameError(
                error_type="USER_DECISION_ERROR",
                error_message=f"用户决策模拟失败: {str(e)}",
                hand_number=hand_number,
                severity="WARNING"
            )
            self.stats.errors.append(error)
            self.stats.warnings += 1
            return None
    
    def _simulate_ui_interaction(self, user_action: UserAction):
        """模拟UI交互"""
        try:
            # 模拟按钮点击
            button_name = f"{user_action.action_type.value}_button"
            self.ui_simulator.simulate_user_click(button_name)
            
            # 如果是加注或下注，模拟输入金额
            if user_action.action_type in [UserActionType.RAISE, UserActionType.BET] and user_action.amount:
                self.ui_simulator.session_state[f'{user_action.action_type.value}_amount'] = user_action.amount
            
        except Exception as e:
            self.stats.ui_render_errors += 1
            self.logger.warning(f"UI交互模拟失败: {e}")
    
    def _simulate_debug_mode_toggle(self):
        """模拟调试模式切换"""
        try:
            self.ui_simulator.simulate_debug_toggle()
            self.stats.debug_mode_toggles += 1
        except Exception as e:
            self.stats.session_state_errors += 1
            self.logger.warning(f"调试模式切换失败: {e}")
    
    def _execute_user_action(self, user_action: UserAction, hand_number: int) -> bool:
        """执行用户行动"""
        action_start_time = time.time()
        self.stats.total_user_actions += 1
        
        try:
            success = False
            
            if user_action.action_type == UserActionType.START_GAME:
                success = self.controller.start_new_hand()
            elif user_action.action_type == UserActionType.FOLD:
                action = Action(ActionType.FOLD, 0, user_action.player_id)
                success = self.controller.execute_action(action)
            elif user_action.action_type == UserActionType.CALL:
                action = Action(ActionType.CALL, 0, user_action.player_id)
                success = self.controller.execute_action(action)
            elif user_action.action_type == UserActionType.CHECK:
                action = Action(ActionType.CHECK, 0, user_action.player_id)
                success = self.controller.execute_action(action)
            elif user_action.action_type == UserActionType.RAISE:
                amount = user_action.amount or 100
                action = Action(ActionType.RAISE, amount, user_action.player_id)
                success = self.controller.execute_action(action)
            elif user_action.action_type == UserActionType.BET:
                amount = user_action.amount or 50
                action = Action(ActionType.BET, amount, user_action.player_id)
                success = self.controller.execute_action(action)
            elif user_action.action_type == UserActionType.ALL_IN:
                action = Action(ActionType.ALL_IN, 0, user_action.player_id)
                success = self.controller.execute_action(action)
            
            if success:
                self.stats.successful_actions += 1
                # 记录行动分布
                action_name = user_action.action_type.value
                self.stats.action_distribution[action_name] = self.stats.action_distribution.get(action_name, 0) + 1
            else:
                self.stats.failed_actions += 1
                error = GameError(
                    error_type="ACTION_EXECUTION_FAILED",
                    error_message=f"行动执行失败: {user_action.action_type.value}",
                    hand_number=hand_number,
                    action_context=user_action,
                    severity="WARNING"
                )
                self.stats.errors.append(error)
                self.stats.warnings += 1
            
            # 记录行动时间
            action_time = time.time() - action_start_time
            self.stats.average_action_time = ((self.stats.average_action_time * (self.stats.total_user_actions - 1)) + action_time) / self.stats.total_user_actions
            
            return success
            
        except Exception as e:
            self.stats.failed_actions += 1
            error = GameError(
                error_type="ACTION_EXECUTION_ERROR",
                error_message=f"行动执行异常: {str(e)}",
                hand_number=hand_number,
                action_context=user_action,
                severity="ERROR"
            )
            self.stats.errors.append(error)
            self.logger.error(f"执行用户行动失败: {e}")
            return False
    
    def _log_progress(self, hand_number: int):
        """记录进度"""
        completion_rate = (self.stats.hands_completed / self.stats.hands_attempted) * 100 if self.stats.hands_attempted > 0 else 0
        action_success_rate = (self.stats.successful_actions / self.stats.total_user_actions) * 100 if self.stats.total_user_actions > 0 else 0
        
        self.logger.info(f"进度报告 - Hand {hand_number}/{self.num_hands}")
        self.logger.info(f"  完成率: {completion_rate:.1f}% ({self.stats.hands_completed}/{self.stats.hands_attempted})")
        self.logger.info(f"  行动成功率: {action_success_rate:.1f}% ({self.stats.successful_actions}/{self.stats.total_user_actions})")
        self.logger.info(f"  错误数量: {len(self.stats.errors)} (严重: {self.stats.critical_errors}, 警告: {self.stats.warnings})")
    
    def _calculate_final_stats(self, start_time: float):
        """计算最终统计"""
        self.stats.total_test_time = time.time() - start_time
        self.stats.final_total_chips = sum(p.chips for p in self.game_state.players)
        
        # 计算错误统计
        for error in self.stats.errors:
            if error.severity == "CRITICAL":
                self.stats.critical_errors += 1
            elif error.severity == "WARNING":
                self.stats.warnings += 1
    
    def _log_final_results(self):
        """记录最终结果"""
        self.logger.info("=" * 80)
        self.logger.info("🏆 Streamlit终极用户测试结果")
        self.logger.info("=" * 80)
        
        # 基本统计
        self.logger.info(f"总手牌数: {self.stats.hands_attempted}")
        self.logger.info(f"完成手牌数: {self.stats.hands_completed}")
        self.logger.info(f"失败手牌数: {self.stats.hands_failed}")
        completion_rate = (self.stats.hands_completed / self.stats.hands_attempted) * 100 if self.stats.hands_attempted > 0 else 0
        self.logger.info(f"完成率: {completion_rate:.1f}%")
        
        # 行动统计
        self.logger.info(f"总用户行动数: {self.stats.total_user_actions}")
        self.logger.info(f"成功行动数: {self.stats.successful_actions}")
        self.logger.info(f"失败行动数: {self.stats.failed_actions}")
        action_success_rate = (self.stats.successful_actions / self.stats.total_user_actions) * 100 if self.stats.total_user_actions > 0 else 0
        self.logger.info(f"行动成功率: {action_success_rate:.1f}%")
        
        # 筹码统计
        self.logger.info(f"初始总筹码: {self.stats.initial_total_chips}")
        self.logger.info(f"最终总筹码: {self.stats.final_total_chips}")
        self.logger.info(f"筹码守恒违规: {len(self.stats.chip_conservation_violations)}")
        
        # 错误统计
        self.logger.info(f"总错误数: {len(self.stats.errors)}")
        self.logger.info(f"严重错误: {self.stats.critical_errors}")
        self.logger.info(f"警告: {self.stats.warnings}")
        self.logger.info(f"UI渲染错误: {self.stats.ui_render_errors}")
        self.logger.info(f"Session State错误: {self.stats.session_state_errors}")
        
        # 性能统计
        self.logger.info(f"总测试时间: {self.stats.total_test_time:.2f}秒")
        self.logger.info(f"平均手牌时间: {self.stats.average_hand_time:.3f}秒")
        self.logger.info(f"平均行动时间: {self.stats.average_action_time:.3f}秒")
        hands_per_second = self.stats.hands_completed / self.stats.total_test_time if self.stats.total_test_time > 0 else 0
        self.logger.info(f"测试速度: {hands_per_second:.2f} 手/秒")
        
        # UI统计
        self.logger.info(f"调试模式切换次数: {self.stats.debug_mode_toggles}")
        
        # 行动分布
        if self.stats.action_distribution:
            self.logger.info("行动分布:")
            for action, count in self.stats.action_distribution.items():
                percentage = (count / self.stats.successful_actions) * 100 if self.stats.successful_actions > 0 else 0
                self.logger.info(f"  {action}: {count} ({percentage:.1f}%)")
        
        # 获胜者分布
        if self.stats.winner_distribution:
            self.logger.info("获胜者分布:")
            for winner, count in self.stats.winner_distribution.items():
                percentage = (count / self.stats.hands_completed) * 100 if self.stats.hands_completed > 0 else 0
                self.logger.info(f"  {winner}: {count} ({percentage:.1f}%)")
    
    def export_results(self, filepath: str):
        """导出测试结果"""
        results = {
            "test_config": {
                "num_hands": self.num_hands,
                "test_type": "streamlit_ultimate_user_experience"
            },
            "stats": {
                "hands_attempted": self.stats.hands_attempted,
                "hands_completed": self.stats.hands_completed,
                "hands_failed": self.stats.hands_failed,
                "total_user_actions": self.stats.total_user_actions,
                "successful_actions": self.stats.successful_actions,
                "failed_actions": self.stats.failed_actions,
                "initial_total_chips": self.stats.initial_total_chips,
                "final_total_chips": self.stats.final_total_chips,
                "chip_conservation_violations": len(self.stats.chip_conservation_violations),
                "total_errors": len(self.stats.errors),
                "critical_errors": self.stats.critical_errors,
                "warnings": self.stats.warnings,
                "ui_render_errors": self.stats.ui_render_errors,
                "session_state_errors": self.stats.session_state_errors,
                "debug_mode_toggles": self.stats.debug_mode_toggles,
                "total_test_time": self.stats.total_test_time,
                "average_hand_time": self.stats.average_hand_time,
                "average_action_time": self.stats.average_action_time,
                "phase_transitions": self.stats.phase_transitions,
                "action_distribution": self.stats.action_distribution,
                "winner_distribution": self.stats.winner_distribution
            },
            "violations": self.stats.chip_conservation_violations,
            "errors": [
                {
                    "type": error.error_type,
                    "message": error.error_message,
                    "hand_number": error.hand_number,
                    "severity": error.severity,
                    "timestamp": error.timestamp
                }
                for error in self.stats.errors[:100]  # 只保存前100个错误
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)


def main():
    """主函数"""
    print("🎮 开始Streamlit终极用户体验测试...")
    
    # 创建测试器
    tester = StreamlitUltimateUserTester(num_hands=1000)
    
    # 运行测试
    stats = tester.run_ultimate_test()
    
    # 导出结果
    results_file = project_root / "v2" / "tests" / "test_logs" / f"streamlit_ultimate_test_{int(time.time())}.json"
    tester.export_results(str(results_file))
    
    print(f"\n📊 测试结果已保存到: {results_file}")
    
    # 评估测试结果
    print("\n🔍 终极测试评估:")
    
    # 完成率评估
    completion_rate = (stats.hands_completed / stats.hands_attempted) * 100 if stats.hands_attempted > 0 else 0
    if completion_rate >= 98:
        print(f"✅ 手牌完成率: {completion_rate:.1f}% (优秀)")
    elif completion_rate >= 95:
        print(f"⚠️  手牌完成率: {completion_rate:.1f}% (良好)")
    else:
        print(f"❌ 手牌完成率: {completion_rate:.1f}% (需要改进)")
    
    # 行动成功率评估
    action_success_rate = (stats.successful_actions / stats.total_user_actions) * 100 if stats.total_user_actions > 0 else 0
    if action_success_rate >= 98:
        print(f"✅ 行动成功率: {action_success_rate:.1f}% (优秀)")
    elif action_success_rate >= 95:
        print(f"⚠️  行动成功率: {action_success_rate:.1f}% (良好)")
    else:
        print(f"❌ 行动成功率: {action_success_rate:.1f}% (需要改进)")
    
    # 筹码守恒评估
    if len(stats.chip_conservation_violations) == 0:
        print("✅ 筹码守恒: 完美")
    elif len(stats.chip_conservation_violations) <= 5:
        print(f"⚠️  筹码守恒: {len(stats.chip_conservation_violations)} 次违规 (可接受)")
    else:
        print(f"❌ 筹码守恒: {len(stats.chip_conservation_violations)} 次违规 (需要修复)")
    
    # 错误评估
    if stats.critical_errors == 0 and len(stats.errors) <= 10:
        print(f"✅ 错误控制: 优秀 (严重: {stats.critical_errors}, 总计: {len(stats.errors)})")
    elif stats.critical_errors <= 2 and len(stats.errors) <= 50:
        print(f"⚠️  错误控制: 良好 (严重: {stats.critical_errors}, 总计: {len(stats.errors)})")
    else:
        print(f"❌ 错误控制: 需要改进 (严重: {stats.critical_errors}, 总计: {len(stats.errors)})")
    
    # 性能评估
    hands_per_second = stats.hands_completed / stats.total_test_time if stats.total_test_time > 0 else 0
    if hands_per_second >= 5:
        print(f"✅ 测试性能: {hands_per_second:.2f} 手/秒 (优秀)")
    elif hands_per_second >= 2:
        print(f"⚠️  测试性能: {hands_per_second:.2f} 手/秒 (良好)")
    else:
        print(f"❌ 测试性能: {hands_per_second:.2f} 手/秒 (需要优化)")
    
    # UI稳定性评估
    ui_error_rate = (stats.ui_render_errors + stats.session_state_errors) / stats.total_user_actions * 100 if stats.total_user_actions > 0 else 0
    if ui_error_rate <= 1:
        print(f"✅ UI稳定性: {ui_error_rate:.2f}% 错误率 (优秀)")
    elif ui_error_rate <= 5:
        print(f"⚠️  UI稳定性: {ui_error_rate:.2f}% 错误率 (良好)")
    else:
        print(f"❌ UI稳定性: {ui_error_rate:.2f}% 错误率 (需要改进)")
    
    print("\n🎯 Streamlit终极用户体验测试完成！")
    
    return stats


# ==================== Pytest 兼容测试函数 ====================

def test_streamlit_ultimate_user_experience_quick():
    """
    快速版本的Streamlit终极用户体验测试 (10手牌)
    
    防作弊检查：
    1. 确保使用真实的PokerController而非模拟数据
    2. 验证筹码计算使用核心模块
    3. 检查游戏状态变化的真实性
    4. 确保AI决策来自SimpleAI模块
    """
    print("🧪 开始快速Streamlit终极用户体验测试...")
    
    # 创建测试器 - 使用较少手牌数进行快速测试
    tester = StreamlitUltimateUserTester(num_hands=10)
    
    # 防作弊检查1: 验证使用真实的核心模块
    assert tester.controller is None, "控制器应该在setup前为None"
    
    # 运行测试
    stats = tester.run_ultimate_test()
    
    # 防作弊检查2: 验证控制器确实被创建且使用核心模块
    assert tester.controller is not None, "控制器应该被正确创建"
    assert isinstance(tester.controller, PokerController), "必须使用真实的PokerController"
    assert isinstance(tester.ai_strategy, SimpleAI), "必须使用真实的SimpleAI"
    assert isinstance(tester.game_state, GameState), "必须使用真实的GameState"
    
    # 防作弊检查3: 验证游戏状态的真实性
    assert len(tester.game_state.players) == 4, "应该有4个玩家"
    assert all(isinstance(p, Player) for p in tester.game_state.players), "所有玩家必须是真实的Player对象"
    
    # 防作弊检查4: 验证筹码守恒（核心业务逻辑验证）
    total_chips = sum(p.chips for p in tester.game_state.players)
    assert total_chips == stats.initial_total_chips, f"筹码必须守恒: 初始{stats.initial_total_chips}, 最终{total_chips}"
    
    # 基本断言
    assert stats.hands_attempted > 0, "应该尝试了至少一手牌"
    assert stats.total_user_actions > 0, "应该有用户行动"
    
    # 成功率检查
    if stats.hands_attempted > 0:
        completion_rate = stats.hands_completed / stats.hands_attempted
        assert completion_rate >= 0.8, f"手牌完成率应该至少80%，实际: {completion_rate:.1%}"
    
    if stats.total_user_actions > 0:
        action_success_rate = stats.successful_actions / stats.total_user_actions
        assert action_success_rate >= 0.8, f"行动成功率应该至少80%，实际: {action_success_rate:.1%}"
    
    # 错误控制检查
    assert stats.critical_errors == 0, f"不应该有严重错误，实际: {stats.critical_errors}"
    assert len(stats.chip_conservation_violations) == 0, f"不应该有筹码守恒违规，实际: {len(stats.chip_conservation_violations)}"
    
    print(f"✅ 快速测试完成: {stats.hands_completed}/{stats.hands_attempted} 手牌完成")
    print(f"✅ 行动成功率: {stats.successful_actions}/{stats.total_user_actions}")
    print(f"✅ 错误控制: 严重{stats.critical_errors}, 警告{stats.warnings}")


def test_streamlit_ui_simulator_functionality():
    """
    测试Streamlit UI模拟器的功能
    
    防作弊检查：
    1. 确保UI模拟器不绕过真实的游戏逻辑
    2. 验证session state管理的正确性
    3. 检查UI交互的真实性
    """
    print("🧪 测试Streamlit UI模拟器功能...")
    
    # 创建UI模拟器
    ui_simulator = StreamlitUISimulator()
    
    # 测试初始状态
    assert ui_simulator.session_state == {}, "初始session state应该为空"
    assert ui_simulator.ui_components == {}, "初始UI组件应该为空"
    
    # 测试mock streamlit设置
    mock_session_state, ui_components = ui_simulator.setup_mock_streamlit()
    
    # 验证mock对象的正确性
    assert mock_session_state is not None, "mock session state应该被创建"
    assert len(ui_components) > 0, "UI组件应该被创建"
    
    # 测试session state操作
    ui_simulator.session_state['test_key'] = 'test_value'
    assert ui_simulator.session_state['test_key'] == 'test_value', "session state应该正确存储值"
    
    # 测试调试模式切换
    initial_debug = ui_simulator.session_state.get('debug_mode', False)
    toggled_debug = ui_simulator.simulate_debug_toggle()
    final_debug = ui_simulator.session_state.get('debug_mode', False)
    
    assert toggled_debug != initial_debug, "调试模式应该被切换"
    assert final_debug != initial_debug, "session state中的调试模式应该被更新"
    
    # 测试快照功能
    snapshot = ui_simulator.get_session_state_snapshot()
    assert isinstance(snapshot, dict), "快照应该是字典类型"
    assert snapshot == ui_simulator.session_state, "快照应该与当前状态一致"
    
    print("✅ UI模拟器功能测试通过")


def test_user_behavior_simulator():
    """
    测试用户行为模拟器
    
    防作弊检查：
    1. 确保决策基于真实的游戏状态
    2. 验证行动类型的合理性
    3. 检查决策逻辑的一致性
    """
    print("🧪 测试用户行为模拟器...")
    
    # 创建用户行为模拟器
    user_simulator = UserBehaviorSimulator("balanced")
    
    # 验证决策模式设置
    assert user_simulator.strategy == "balanced", "策略应该被正确设置"
    assert user_simulator.decision_patterns is not None, "决策模式应该被初始化"
    
    # 验证决策模式的概率总和
    patterns = user_simulator.decision_patterns
    total_probability = sum(patterns.values())
    assert abs(total_probability - 1.0) < 0.01, f"概率总和应该接近1.0，实际: {total_probability}"
    
    # 创建模拟游戏状态进行决策测试
    game_state = GameState()
    players = [
        Player(seat_id=0, name="User", chips=1000, status=SeatStatus.ACTIVE),
        Player(seat_id=1, name="AI_1", chips=1000, status=SeatStatus.ACTIVE)
    ]
    
    for player in players:
        game_state.add_player(player)
    
    # 防作弊检查：确保使用真实的游戏状态对象
    assert isinstance(game_state, GameState), "必须使用真实的GameState对象"
    assert len(game_state.players) == 2, "游戏状态应该有正确的玩家数量"
    
    # 测试决策功能
    game_state.current_bet = 0  # 无当前下注
    action = user_simulator.decide_action(game_state, 0)
    
    # 验证决策结果
    assert isinstance(action, UserAction), "决策结果应该是UserAction对象"
    assert action.player_id == 0, "玩家ID应该正确"
    assert action.action_type in UserActionType, "行动类型应该有效"
    
    # 测试有下注情况下的决策
    game_state.current_bet = 100
    action_with_bet = user_simulator.decide_action(game_state, 0)
    
    assert isinstance(action_with_bet, UserAction), "有下注时的决策结果应该是UserAction对象"
    assert action_with_bet.action_type in [UserActionType.FOLD, UserActionType.CALL, UserActionType.RAISE], \
        "有下注时应该只能弃牌、跟注或加注"
    
    print("✅ 用户行为模拟器测试通过")


def test_anti_cheating_core_module_usage():
    """
    防作弊专项测试：确保测试真正使用核心模块
    
    这个测试专门检查测试代码是否绕过核心模块而自造数据
    """
    print("🔍 执行防作弊检查...")
    
    # 创建测试器
    tester = StreamlitUltimateUserTester(num_hands=3)
    
    # 检查1: 确保使用真实的核心模块类
    tester.setup_game_environment()
    
    # 验证控制器类型
    assert type(tester.controller).__name__ == "PokerController", \
        f"必须使用真实的PokerController，当前类型: {type(tester.controller).__name__}"
    
    # 验证AI策略类型
    assert type(tester.ai_strategy).__name__ == "SimpleAI", \
        f"必须使用真实的SimpleAI，当前类型: {type(tester.ai_strategy).__name__}"
    
    # 验证游戏状态类型
    assert type(tester.game_state).__name__ == "GameState", \
        f"必须使用真实的GameState，当前类型: {type(tester.game_state).__name__}"
    
    # 检查2: 验证玩家对象的真实性
    for player in tester.game_state.players:
        assert type(player).__name__ == "Player", \
            f"必须使用真实的Player对象，当前类型: {type(player).__name__}"
        assert hasattr(player, 'chips'), "Player对象必须有chips属性"
        assert hasattr(player, 'seat_id'), "Player对象必须有seat_id属性"
        assert hasattr(player, 'status'), "Player对象必须有status属性"
    
    # 检查3: 验证枚举类型的使用
    test_action = Action(ActionType.FOLD, 0, 0)
    assert type(test_action.action_type).__name__ == "ActionType", \
        "必须使用真实的ActionType枚举"
    
    # 检查4: 验证事件总线的真实性
    assert type(tester.event_bus).__name__ == "EventBus", \
        f"必须使用真实的EventBus，当前类型: {type(tester.event_bus).__name__}"
    
    # 检查5: 执行一手牌并验证状态变化的真实性
    initial_chips = [p.chips for p in tester.game_state.players]
    initial_pot = tester.game_state.pot  # pot是整数属性
    
    # 开始新手牌
    success = tester.controller.start_new_hand()
    assert success, "开始新手牌应该成功"
    
    # 验证游戏状态确实发生了变化
    snapshot = tester.controller.get_snapshot()
    assert snapshot is not None, "应该能获取游戏快照"
    assert hasattr(snapshot, 'phase'), "快照应该有phase属性"
    assert hasattr(snapshot, 'players'), "快照应该有players属性"
    
    # 检查6: 验证筹码变化的真实性（盲注应该被扣除）
    current_chips = [p.chips for p in tester.game_state.players]
    current_pot = tester.game_state.pot  # pot是整数属性
    
    total_initial = sum(initial_chips) + initial_pot
    total_current = sum(current_chips) + current_pot
    
    # 应该有玩家的筹码发生了变化（支付盲注）
    chips_changed = any(initial != current for initial, current in zip(initial_chips, current_chips))
    assert chips_changed, "应该有玩家支付了盲注，筹码发生变化"
    
    # 检查筹码守恒
    assert total_initial == total_current, \
        f"筹码必须守恒: 初始{total_initial}(玩家{sum(initial_chips)}+底池{initial_pot}), 当前{total_current}(玩家{sum(current_chips)}+底池{current_pot})"
    
    print("✅ 筹码守恒正常")


@pytest.mark.slow
def test_streamlit_ultimate_user_experience_full():
    """
    完整版本的Streamlit终极用户体验测试 (100手牌)
    
    标记为slow测试，只在需要时运行
    """
    print("🧪 开始完整Streamlit终极用户体验测试...")
    
    # 创建测试器
    tester = StreamlitUltimateUserTester(num_hands=100)
    
    # 运行测试
    stats = tester.run_ultimate_test()
    
    # 严格的完整测试断言
    assert stats.hands_attempted == 100, f"应该尝试100手牌，实际: {stats.hands_attempted}"
    
    # 完成率应该很高
    completion_rate = stats.hands_completed / stats.hands_attempted if stats.hands_attempted > 0 else 0
    assert completion_rate >= 0.95, f"完成率应该至少95%，实际: {completion_rate:.1%}"
    
    # 行动成功率应该很高
    action_success_rate = stats.successful_actions / stats.total_user_actions if stats.total_user_actions > 0 else 0
    assert action_success_rate >= 0.95, f"行动成功率应该至少95%，实际: {action_success_rate:.1%}"
    
    # 不应该有严重错误
    assert stats.critical_errors == 0, f"不应该有严重错误，实际: {stats.critical_errors}"
    
    # 筹码守恒
    assert len(stats.chip_conservation_violations) == 0, \
        f"不应该有筹码守恒违规，实际: {len(stats.chip_conservation_violations)}"
    
    # 性能检查
    assert stats.total_test_time > 0, "测试时间应该大于0"
    hands_per_second = stats.hands_completed / stats.total_test_time
    assert hands_per_second >= 1.0, f"测试速度应该至少1手/秒，实际: {hands_per_second:.2f}"
    
    print(f"✅ 完整测试完成: {stats.hands_completed}/{stats.hands_attempted} 手牌")
    print(f"✅ 测试用时: {stats.total_test_time:.2f}秒")
    print(f"✅ 测试速度: {hands_per_second:.2f} 手/秒")


if __name__ == "__main__":
    main() 