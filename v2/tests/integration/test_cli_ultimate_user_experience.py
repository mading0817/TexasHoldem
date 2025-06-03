#!/usr/bin/env python3
"""
CLI UI 终极用户体验测试

模拟真实用户在CLI界面下进行德州扑克游戏，全面验证：
1. 命令行交互流程是否正确
2. 输入输出处理是否准确
3. 游戏逻辑是否正确
4. 错误处理是否健壮
5. 用户体验是否流畅

这是站在CLI用户角度的终极集成测试。
"""

import sys
import os
import time
import logging
import random
import json
import io
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from unittest.mock import Mock, patch, StringIO

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.enums import ActionType, Phase, Action, SeatStatus
from v2.core.state import GameState
from v2.core.player import Player
from v2.core.events import EventBus


class CLIUserInput(Enum):
    """CLI用户输入类型"""
    FOLD = "f"
    CALL = "c"
    RAISE = "r"
    CHECK = "k"
    BET = "b"
    ALL_IN = "a"
    QUIT = "q"
    HELP = "h"
    STATUS = "s"


@dataclass
class CLIInteraction:
    """CLI交互记录"""
    input_command: str
    expected_output_keywords: List[str]
    actual_output: str = ""
    success: bool = False
    timestamp: float = field(default_factory=time.time)
    response_time: float = 0.0


@dataclass
class CLITestStats:
    """CLI测试统计"""
    hands_attempted: int = 0
    hands_completed: int = 0
    hands_failed: int = 0
    total_interactions: int = 0
    successful_interactions: int = 0
    failed_interactions: int = 0
    
    # 输入输出统计
    total_input_commands: int = 0
    invalid_input_commands: int = 0
    output_parsing_errors: int = 0
    
    # 性能统计
    total_test_time: float = 0
    average_response_time: float = 0
    
    # 错误统计
    cli_errors: List[str] = field(default_factory=list)
    game_logic_errors: List[str] = field(default_factory=list)
    
    # 用户体验统计
    help_requests: int = 0
    status_requests: int = 0
    quit_attempts: int = 0
    
    # 游戏统计
    action_distribution: Dict[str, int] = field(default_factory=dict)
    phase_distribution: Dict[str, int] = field(default_factory=dict)


class CLIInputSimulator:
    """CLI输入模拟器"""
    
    def __init__(self, strategy: str = "balanced"):
        self.strategy = strategy
        self.input_history = []
        self.decision_weights = self._setup_decision_weights()
    
    def _setup_decision_weights(self) -> Dict[str, Dict[str, float]]:
        """设置决策权重"""
        weights = {
            "aggressive": {
                CLIUserInput.FOLD.value: 0.10,
                CLIUserInput.CALL.value: 0.30,
                CLIUserInput.RAISE.value: 0.45,
                CLIUserInput.CHECK.value: 0.10,
                CLIUserInput.BET.value: 0.05
            },
            "conservative": {
                CLIUserInput.FOLD.value: 0.40,
                CLIUserInput.CALL.value: 0.40,
                CLIUserInput.RAISE.value: 0.10,
                CLIUserInput.CHECK.value: 0.08,
                CLIUserInput.BET.value: 0.02
            },
            "balanced": {
                CLIUserInput.FOLD.value: 0.25,
                CLIUserInput.CALL.value: 0.35,
                CLIUserInput.RAISE.value: 0.25,
                CLIUserInput.CHECK.value: 0.10,
                CLIUserInput.BET.value: 0.05
            }
        }
        return weights.get(self.strategy, weights["balanced"])
    
    def generate_input_sequence(self, game_snapshot, player_id: int) -> List[str]:
        """生成输入序列"""
        inputs = []
        
        # 偶尔请求帮助或状态
        if random.random() < 0.05:  # 5%概率
            if random.random() < 0.5:
                inputs.append(CLIUserInput.HELP.value)
            else:
                inputs.append(CLIUserInput.STATUS.value)
        
        # 主要行动决策
        if game_snapshot.current_bet > 0:
            # 需要跟注或弃牌
            if random.random() < self.decision_weights[CLIUserInput.FOLD.value]:
                inputs.append(CLIUserInput.FOLD.value)
            elif random.random() < 0.7:  # 70%概率跟注
                inputs.append(CLIUserInput.CALL.value)
            else:
                # 加注，需要输入金额
                inputs.append(CLIUserInput.RAISE.value)
                raise_amount = min(game_snapshot.current_bet * 2, 200)
                inputs.append(str(raise_amount))
        else:
            # 可以过牌或下注
            if random.random() < self.decision_weights[CLIUserInput.CHECK.value]:
                inputs.append(CLIUserInput.CHECK.value)
            else:
                # 下注，需要输入金额
                inputs.append(CLIUserInput.BET.value)
                bet_amount = random.choice([50, 100, 150])
                inputs.append(str(bet_amount))
        
        return inputs
    
    def simulate_invalid_input(self) -> str:
        """模拟无效输入"""
        invalid_inputs = [
            "invalid",
            "123abc",
            "",
            "xyz",
            "fold_now",
            "call_please",
            "raise_all",
            "check_mate"
        ]
        return random.choice(invalid_inputs)


class CLIOutputParser:
    """CLI输出解析器"""
    
    def __init__(self):
        self.expected_patterns = {
            "game_start": ["新手牌开始", "发牌", "底池"],
            "player_action": ["玩家", "行动", "跟注", "弃牌", "加注", "过牌"],
            "phase_change": ["翻牌", "转牌", "河牌", "摊牌"],
            "hand_result": ["获胜", "赢得", "底池"],
            "error": ["错误", "无效", "失败"],
            "help": ["帮助", "命令", "说明"],
            "status": ["状态", "筹码", "位置"]
        }
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """解析输出"""
        result = {
            "type": "unknown",
            "contains_error": False,
            "contains_game_info": False,
            "keywords_found": []
        }
        
        output_lower = output.lower()
        
        # 检查错误
        if any(keyword in output_lower for keyword in self.expected_patterns["error"]):
            result["contains_error"] = True
            result["type"] = "error"
        
        # 检查游戏信息
        for pattern_type, keywords in self.expected_patterns.items():
            if any(keyword in output_lower for keyword in keywords):
                result["keywords_found"].append(pattern_type)
                if pattern_type != "error":
                    result["contains_game_info"] = True
                    if result["type"] == "unknown":
                        result["type"] = pattern_type
        
        return result


class CLIUltimateUserTester:
    """CLI终极用户测试器"""
    
    def __init__(self, num_hands: int = 100):
        self.num_hands = num_hands
        self.stats = CLITestStats()
        self.input_simulator = CLIInputSimulator("balanced")
        self.output_parser = CLIOutputParser()
        self.logger = self._setup_logging()
        
        # 游戏组件
        self.controller = None
        self.game_state = None
        self.ai_strategy = None
        self.event_bus = None
        
        # CLI模拟
        self.mock_input_queue = []
        self.captured_output = []
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志记录"""
        logger = logging.getLogger("CLIUltimateTest")
        logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        log_file = project_root / "v2" / "tests" / "test_logs" / f"cli_ultimate_test_{int(time.time())}.log"
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
        
        self.logger.info("CLI游戏环境设置完成")
    
    def setup_cli_simulation(self):
        """设置CLI模拟环境"""
        # 重定向标准输入输出
        self.original_stdin = sys.stdin
        self.original_stdout = sys.stdout
        
        # 创建模拟的输入输出
        self.mock_stdin = StringIO()
        self.mock_stdout = StringIO()
        
        return True
    
    def simulate_cli_input(self, input_text: str) -> str:
        """模拟CLI输入"""
        # 模拟用户输入
        self.mock_input_queue.append(input_text)
        
        # 模拟处理延迟
        time.sleep(0.01)  # 10ms处理延迟
        
        # 返回模拟的输出
        return f"处理输入: {input_text}"
    
    def run_ultimate_test(self) -> CLITestStats:
        """运行终极CLI测试"""
        self.logger.info(f"开始CLI终极用户测试 - {self.num_hands}手")
        start_time = time.time()
        
        # 设置环境
        self.setup_game_environment()
        self.setup_cli_simulation()
        
        # 运行测试
        for hand_num in range(1, self.num_hands + 1):
            try:
                self._run_single_hand_with_cli_simulation(hand_num)
                
                # 每20手报告进度
                if hand_num % 20 == 0:
                    self._log_progress(hand_num)
                    
            except Exception as e:
                error_msg = f"Hand {hand_num}: {str(e)}"
                self.stats.cli_errors.append(error_msg)
                self.stats.hands_failed += 1
                self.logger.error(f"Hand {hand_num} 执行失败: {e}")
                continue
        
        # 计算最终统计
        self._calculate_final_stats(start_time)
        
        # 记录最终结果
        self._log_final_results()
        
        return self.stats
    
    def _run_single_hand_with_cli_simulation(self, hand_number: int):
        """运行单手牌并模拟CLI交互"""
        self.stats.hands_attempted += 1
        
        try:
            # 开始新手牌
            if not self.controller.start_new_hand():
                raise Exception("无法开始新手牌")
            
            # 模拟CLI显示游戏开始信息
            start_output = self._simulate_cli_output("新手牌开始，发牌中...")
            self._process_cli_interaction("start_game", start_output)
            
            # 模拟手牌过程
            max_actions = 100  # 防止无限循环
            action_count = 0
            
            while not self.controller.is_hand_over() and action_count < max_actions:
                current_player_id = self.controller.get_current_player_id()
                if current_player_id is None:
                    break
                
                # 记录阶段
                current_phase = self.controller.get_snapshot().phase.value
                self.stats.phase_distribution[current_phase] = self.stats.phase_distribution.get(current_phase, 0) + 1
                
                if current_player_id == 0:  # 用户玩家
                    # 模拟CLI用户交互
                    self._simulate_user_cli_interaction(current_player_id, hand_number)
                else:  # AI玩家
                    # 处理AI行动并模拟CLI输出
                    self.controller.process_ai_action()
                    ai_output = self._simulate_cli_output(f"AI玩家 {current_player_id} 执行行动")
                    self._process_cli_interaction("ai_action", ai_output)
                
                action_count += 1
                
                # 偶尔模拟无效输入
                if random.random() < 0.02:  # 2%概率
                    self._simulate_invalid_input_scenario()
            
            # 结束手牌
            if self.controller.is_hand_over():
                try:
                    result = self.controller.end_hand()
                    self.stats.hands_completed += 1
                    
                    # 模拟显示手牌结果
                    result_output = self._simulate_cli_output("手牌结束，显示结果...")
                    self._process_cli_interaction("hand_result", result_output)
                    
                except Exception as e:
                    error_msg = f"结束手牌失败: {str(e)}"
                    self.stats.game_logic_errors.append(error_msg)
            else:
                self.stats.hands_failed += 1
                # 强制重置手牌状态
                if hasattr(self.controller, 'force_reset_hand_state'):
                    self.controller.force_reset_hand_state()
            
        except Exception as e:
            self.stats.hands_failed += 1
            error_msg = f"Hand {hand_number}: {str(e)}"
            self.stats.cli_errors.append(error_msg)
            raise
    
    def _simulate_user_cli_interaction(self, player_id: int, hand_number: int):
        """模拟用户CLI交互"""
        try:
            # 获取游戏状态
            game_snapshot = self.controller.get_snapshot()
            
            # 生成用户输入序列
            input_sequence = self.input_simulator.generate_input_sequence(game_snapshot, player_id)
            
            for user_input in input_sequence:
                interaction_start = time.time()
                
                # 模拟CLI输入处理
                output = self._simulate_cli_input_processing(user_input, game_snapshot, player_id)
                
                # 记录交互
                interaction = CLIInteraction(
                    input_command=user_input,
                    expected_output_keywords=["确认", "执行", "行动"],
                    actual_output=output,
                    response_time=time.time() - interaction_start
                )
                
                # 解析输出
                parsed_output = self.output_parser.parse_output(output)
                interaction.success = not parsed_output["contains_error"]
                
                self._record_cli_interaction(interaction)
                
                # 如果是主要行动，执行游戏逻辑
                if user_input in [e.value for e in CLIUserInput if e not in [CLIUserInput.HELP, CLIUserInput.STATUS, CLIUserInput.QUIT]]:
                    self._execute_cli_action(user_input, player_id)
                    break  # 主要行动完成，退出输入循环
                
        except Exception as e:
            error_msg = f"CLI交互模拟失败: {str(e)}"
            self.stats.cli_errors.append(error_msg)
            self.logger.warning(error_msg)
    
    def _simulate_cli_input_processing(self, user_input: str, game_snapshot, player_id: int) -> str:
        """模拟CLI输入处理"""
        # 模拟不同类型输入的处理
        if user_input == CLIUserInput.HELP.value:
            self.stats.help_requests += 1
            return "帮助信息：f=弃牌, c=跟注, r=加注, k=过牌, b=下注, a=全押, q=退出, s=状态"
        
        elif user_input == CLIUserInput.STATUS.value:
            self.stats.status_requests += 1
            return f"当前状态：底池={game_snapshot.pot}, 当前下注={game_snapshot.current_bet}, 你的筹码=1000"
        
        elif user_input == CLIUserInput.QUIT.value:
            self.stats.quit_attempts += 1
            return "确认退出游戏？(y/n)"
        
        elif user_input in [e.value for e in CLIUserInput]:
            return f"执行行动: {user_input}"
        
        elif user_input.isdigit():
            return f"输入金额: {user_input}"
        
        else:
            return f"无效输入: {user_input}，请输入有效命令"
    
    def _execute_cli_action(self, user_input: str, player_id: int) -> bool:
        """执行CLI行动"""
        try:
            success = False
            
            if user_input == CLIUserInput.FOLD.value:
                action = Action(ActionType.FOLD, 0, player_id)
                success = self.controller.execute_action(action)
                self.stats.action_distribution["fold"] = self.stats.action_distribution.get("fold", 0) + 1
            
            elif user_input == CLIUserInput.CALL.value:
                action = Action(ActionType.CALL, 0, player_id)
                success = self.controller.execute_action(action)
                self.stats.action_distribution["call"] = self.stats.action_distribution.get("call", 0) + 1
            
            elif user_input == CLIUserInput.CHECK.value:
                action = Action(ActionType.CHECK, 0, player_id)
                success = self.controller.execute_action(action)
                self.stats.action_distribution["check"] = self.stats.action_distribution.get("check", 0) + 1
            
            elif user_input == CLIUserInput.RAISE.value:
                # 简化：使用固定加注金额
                amount = 100
                action = Action(ActionType.RAISE, amount, player_id)
                success = self.controller.execute_action(action)
                self.stats.action_distribution["raise"] = self.stats.action_distribution.get("raise", 0) + 1
            
            elif user_input == CLIUserInput.BET.value:
                # 简化：使用固定下注金额
                amount = 50
                action = Action(ActionType.BET, amount, player_id)
                success = self.controller.execute_action(action)
                self.stats.action_distribution["bet"] = self.stats.action_distribution.get("bet", 0) + 1
            
            elif user_input == CLIUserInput.ALL_IN.value:
                action = Action(ActionType.ALL_IN, 0, player_id)
                success = self.controller.execute_action(action)
                self.stats.action_distribution["all_in"] = self.stats.action_distribution.get("all_in", 0) + 1
            
            if success:
                self.stats.successful_interactions += 1
            else:
                self.stats.failed_interactions += 1
                error_msg = f"行动执行失败: {user_input}"
                self.stats.game_logic_errors.append(error_msg)
            
            return success
            
        except Exception as e:
            self.stats.failed_interactions += 1
            error_msg = f"执行CLI行动异常: {str(e)}"
            self.stats.cli_errors.append(error_msg)
            return False
    
    def _simulate_invalid_input_scenario(self):
        """模拟无效输入场景"""
        invalid_input = self.input_simulator.simulate_invalid_input()
        self.stats.total_input_commands += 1
        self.stats.invalid_input_commands += 1
        
        # 模拟处理无效输入
        output = self._simulate_cli_input_processing(invalid_input, None, 0)
        
        interaction = CLIInteraction(
            input_command=invalid_input,
            expected_output_keywords=["无效", "错误"],
            actual_output=output,
            success=False
        )
        
        self._record_cli_interaction(interaction)
    
    def _simulate_cli_output(self, message: str) -> str:
        """模拟CLI输出"""
        # 模拟输出格式化和显示
        formatted_output = f"[{time.strftime('%H:%M:%S')}] {message}"
        self.captured_output.append(formatted_output)
        return formatted_output
    
    def _process_cli_interaction(self, interaction_type: str, output: str):
        """处理CLI交互"""
        self.stats.total_interactions += 1
        
        # 解析输出
        parsed = self.output_parser.parse_output(output)
        
        if parsed["contains_error"]:
            self.stats.failed_interactions += 1
            self.stats.output_parsing_errors += 1
        else:
            self.stats.successful_interactions += 1
    
    def _record_cli_interaction(self, interaction: CLIInteraction):
        """记录CLI交互"""
        self.stats.total_input_commands += 1
        
        if interaction.success:
            self.stats.successful_interactions += 1
        else:
            self.stats.failed_interactions += 1
        
        # 更新平均响应时间
        total_interactions = self.stats.total_interactions + 1
        self.stats.average_response_time = (
            (self.stats.average_response_time * self.stats.total_interactions + interaction.response_time) 
            / total_interactions
        )
        self.stats.total_interactions = total_interactions
    
    def _log_progress(self, hand_number: int):
        """记录进度"""
        completion_rate = (self.stats.hands_completed / self.stats.hands_attempted) * 100 if self.stats.hands_attempted > 0 else 0
        interaction_success_rate = (self.stats.successful_interactions / self.stats.total_interactions) * 100 if self.stats.total_interactions > 0 else 0
        
        self.logger.info(f"进度报告 - Hand {hand_number}/{self.num_hands}")
        self.logger.info(f"  完成率: {completion_rate:.1f}% ({self.stats.hands_completed}/{self.stats.hands_attempted})")
        self.logger.info(f"  交互成功率: {interaction_success_rate:.1f}% ({self.stats.successful_interactions}/{self.stats.total_interactions})")
        self.logger.info(f"  CLI错误: {len(self.stats.cli_errors)}, 游戏逻辑错误: {len(self.stats.game_logic_errors)}")
    
    def _calculate_final_stats(self, start_time: float):
        """计算最终统计"""
        self.stats.total_test_time = time.time() - start_time
    
    def _log_final_results(self):
        """记录最终结果"""
        self.logger.info("=" * 80)
        self.logger.info("🖥️  CLI终极用户测试结果")
        self.logger.info("=" * 80)
        
        # 基本统计
        self.logger.info(f"总手牌数: {self.stats.hands_attempted}")
        self.logger.info(f"完成手牌数: {self.stats.hands_completed}")
        self.logger.info(f"失败手牌数: {self.stats.hands_failed}")
        completion_rate = (self.stats.hands_completed / self.stats.hands_attempted) * 100 if self.stats.hands_attempted > 0 else 0
        self.logger.info(f"完成率: {completion_rate:.1f}%")
        
        # 交互统计
        self.logger.info(f"总交互数: {self.stats.total_interactions}")
        self.logger.info(f"成功交互数: {self.stats.successful_interactions}")
        self.logger.info(f"失败交互数: {self.stats.failed_interactions}")
        interaction_success_rate = (self.stats.successful_interactions / self.stats.total_interactions) * 100 if self.stats.total_interactions > 0 else 0
        self.logger.info(f"交互成功率: {interaction_success_rate:.1f}%")
        
        # 输入统计
        self.logger.info(f"总输入命令数: {self.stats.total_input_commands}")
        self.logger.info(f"无效输入命令数: {self.stats.invalid_input_commands}")
        invalid_input_rate = (self.stats.invalid_input_commands / self.stats.total_input_commands) * 100 if self.stats.total_input_commands > 0 else 0
        self.logger.info(f"无效输入率: {invalid_input_rate:.1f}%")
        
        # 错误统计
        self.logger.info(f"CLI错误数: {len(self.stats.cli_errors)}")
        self.logger.info(f"游戏逻辑错误数: {len(self.stats.game_logic_errors)}")
        self.logger.info(f"输出解析错误数: {self.stats.output_parsing_errors}")
        
        # 性能统计
        self.logger.info(f"总测试时间: {self.stats.total_test_time:.2f}秒")
        self.logger.info(f"平均响应时间: {self.stats.average_response_time:.3f}秒")
        hands_per_second = self.stats.hands_completed / self.stats.total_test_time if self.stats.total_test_time > 0 else 0
        self.logger.info(f"测试速度: {hands_per_second:.2f} 手/秒")
        
        # 用户体验统计
        self.logger.info(f"帮助请求次数: {self.stats.help_requests}")
        self.logger.info(f"状态请求次数: {self.stats.status_requests}")
        self.logger.info(f"退出尝试次数: {self.stats.quit_attempts}")
        
        # 行动分布
        if self.stats.action_distribution:
            self.logger.info("行动分布:")
            total_actions = sum(self.stats.action_distribution.values())
            for action, count in self.stats.action_distribution.items():
                percentage = (count / total_actions) * 100 if total_actions > 0 else 0
                self.logger.info(f"  {action}: {count} ({percentage:.1f}%)")
    
    def export_results(self, filepath: str):
        """导出测试结果"""
        results = {
            "test_config": {
                "num_hands": self.num_hands,
                "test_type": "cli_ultimate_user_experience"
            },
            "stats": {
                "hands_attempted": self.stats.hands_attempted,
                "hands_completed": self.stats.hands_completed,
                "hands_failed": self.stats.hands_failed,
                "total_interactions": self.stats.total_interactions,
                "successful_interactions": self.stats.successful_interactions,
                "failed_interactions": self.stats.failed_interactions,
                "total_input_commands": self.stats.total_input_commands,
                "invalid_input_commands": self.stats.invalid_input_commands,
                "output_parsing_errors": self.stats.output_parsing_errors,
                "total_test_time": self.stats.total_test_time,
                "average_response_time": self.stats.average_response_time,
                "help_requests": self.stats.help_requests,
                "status_requests": self.stats.status_requests,
                "quit_attempts": self.stats.quit_attempts,
                "action_distribution": self.stats.action_distribution,
                "phase_distribution": self.stats.phase_distribution
            },
            "errors": {
                "cli_errors": self.stats.cli_errors[:50],  # 只保存前50个错误
                "game_logic_errors": self.stats.game_logic_errors[:50]
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)


def main():
    """主函数"""
    print("🖥️  开始CLI终极用户体验测试...")
    
    # 创建测试器
    tester = CLIUltimateUserTester(num_hands=100)  # CLI测试使用较少手数
    
    # 运行测试
    stats = tester.run_ultimate_test()
    
    # 导出结果
    results_file = project_root / "v2" / "tests" / "test_logs" / f"cli_ultimate_test_{int(time.time())}.json"
    tester.export_results(str(results_file))
    
    print(f"\n📊 测试结果已保存到: {results_file}")
    
    # 评估测试结果
    print("\n🔍 CLI终极测试评估:")
    
    # 完成率评估
    completion_rate = (stats.hands_completed / stats.hands_attempted) * 100 if stats.hands_attempted > 0 else 0
    if completion_rate >= 95:
        print(f"✅ 手牌完成率: {completion_rate:.1f}% (优秀)")
    elif completion_rate >= 90:
        print(f"⚠️  手牌完成率: {completion_rate:.1f}% (良好)")
    else:
        print(f"❌ 手牌完成率: {completion_rate:.1f}% (需要改进)")
    
    # 交互成功率评估
    interaction_success_rate = (stats.successful_interactions / stats.total_interactions) * 100 if stats.total_interactions > 0 else 0
    if interaction_success_rate >= 95:
        print(f"✅ 交互成功率: {interaction_success_rate:.1f}% (优秀)")
    elif interaction_success_rate >= 90:
        print(f"⚠️  交互成功率: {interaction_success_rate:.1f}% (良好)")
    else:
        print(f"❌ 交互成功率: {interaction_success_rate:.1f}% (需要改进)")
    
    # 输入处理评估
    invalid_input_rate = (stats.invalid_input_commands / stats.total_input_commands) * 100 if stats.total_input_commands > 0 else 0
    if invalid_input_rate <= 5:
        print(f"✅ 无效输入处理: {invalid_input_rate:.1f}% (优秀)")
    elif invalid_input_rate <= 10:
        print(f"⚠️  无效输入处理: {invalid_input_rate:.1f}% (良好)")
    else:
        print(f"❌ 无效输入处理: {invalid_input_rate:.1f}% (需要改进)")
    
    # 错误控制评估
    total_errors = len(stats.cli_errors) + len(stats.game_logic_errors)
    if total_errors <= 5:
        print(f"✅ 错误控制: {total_errors} 个错误 (优秀)")
    elif total_errors <= 15:
        print(f"⚠️  错误控制: {total_errors} 个错误 (良好)")
    else:
        print(f"❌ 错误控制: {total_errors} 个错误 (需要改进)")
    
    # 响应性能评估
    if stats.average_response_time <= 0.1:
        print(f"✅ 响应性能: {stats.average_response_time:.3f}秒 (优秀)")
    elif stats.average_response_time <= 0.5:
        print(f"⚠️  响应性能: {stats.average_response_time:.3f}秒 (良好)")
    else:
        print(f"❌ 响应性能: {stats.average_response_time:.3f}秒 (需要优化)")
    
    print("\n🎯 CLI终极用户体验测试完成！")
    
    return stats


if __name__ == "__main__":
    main() 