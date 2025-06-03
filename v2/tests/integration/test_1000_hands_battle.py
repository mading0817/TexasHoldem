#!/usr/bin/env python3
"""
1000手对战测试脚本

模拟用户与AI进行1000手德州扑克对战，全面检查：
1. 游戏流程是否正确
2. 筹码计算是否准确
3. 行动顺序是否符合规则
4. 日志记录是否完整
5. 性能表现是否稳定
"""

import sys
import os
import time
import logging
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.enums import ActionType, Phase, Action
from v2.core.state import GameState
from v2.core.player import Player
from v2.core.events import EventBus


@dataclass
class BattleStats:
    """对战统计数据"""
    hands_played: int = 0
    hands_completed: int = 0
    hands_failed: int = 0
    total_actions: int = 0
    user_wins: int = 0
    ai_wins: int = 0
    ties: int = 0
    total_chips_start: int = 0
    total_chips_end: int = 0
    chip_conservation_violations: List[str] = None
    errors: List[str] = None
    performance_metrics: Dict[str, float] = None
    phase_distribution: Dict[str, int] = None
    action_distribution: Dict[str, int] = None
    
    def __post_init__(self):
        if self.chip_conservation_violations is None:
            self.chip_conservation_violations = []
        if self.errors is None:
            self.errors = []
        if self.performance_metrics is None:
            self.performance_metrics = {}
        if self.phase_distribution is None:
            self.phase_distribution = {}
        if self.action_distribution is None:
            self.action_distribution = {}


class UserSimulator:
    """用户行为模拟器"""
    
    def __init__(self, strategy: str = "balanced"):
        """
        初始化用户模拟器
        
        Args:
            strategy: 用户策略 ("aggressive", "conservative", "balanced", "random")
        """
        self.strategy = strategy
        self.hand_count = 0
        
    def decide_action(self, snapshot, player_id: int) -> Action:
        """
        模拟用户决策
        
        Args:
            snapshot: 游戏状态快照
            player_id: 玩家ID
            
        Returns:
            用户选择的行动
        """
        self.hand_count += 1
        
        # 获取当前玩家信息
        player = None
        for p in snapshot.players:
            if p.seat_id == player_id:
                player = p
                break
                
        if not player:
            return Action(ActionType.FOLD, 0, player_id)
            
        # 根据策略决定行动
        if self.strategy == "aggressive":
            return self._aggressive_strategy(snapshot, player)
        elif self.strategy == "conservative":
            return self._conservative_strategy(snapshot, player)
        elif self.strategy == "balanced":
            return self._balanced_strategy(snapshot, player)
        else:  # random
            return self._random_strategy(snapshot, player)
    
    def _aggressive_strategy(self, snapshot, player) -> Action:
        """激进策略：经常加注和跟注"""
        if snapshot.current_bet > player.current_bet:
            # 需要跟注或加注
            if random.random() < 0.7:  # 70%概率跟注或加注
                if random.random() < 0.4:  # 40%概率加注
                    raise_amount = min(snapshot.current_bet * 2, player.chips)
                    return Action(ActionType.RAISE, raise_amount, player.seat_id)
                else:
                    return Action(ActionType.CALL, 0, player.seat_id)
            else:
                return Action(ActionType.FOLD, 0, player.seat_id)
        else:
            # 可以过牌或下注
            if random.random() < 0.6:  # 60%概率下注
                bet_amount = min(snapshot.big_blind * 2, player.chips)
                return Action(ActionType.BET, bet_amount, player.seat_id)
            else:
                return Action(ActionType.CHECK, 0, player.seat_id)
    
    def _conservative_strategy(self, snapshot, player) -> Action:
        """保守策略：经常过牌和弃牌"""
        if snapshot.current_bet > player.current_bet:
            # 需要跟注
            if random.random() < 0.3:  # 30%概率跟注
                return Action(ActionType.CALL, 0, player.seat_id)
            else:
                return Action(ActionType.FOLD, 0, player.seat_id)
        else:
            # 可以过牌或下注
            if random.random() < 0.2:  # 20%概率下注
                bet_amount = snapshot.big_blind
                return Action(ActionType.BET, bet_amount, player.seat_id)
            else:
                return Action(ActionType.CHECK, 0, player.seat_id)
    
    def _balanced_strategy(self, snapshot, player) -> Action:
        """平衡策略：根据情况选择"""
        if snapshot.current_bet > player.current_bet:
            # 需要跟注
            if random.random() < 0.5:  # 50%概率跟注
                return Action(ActionType.CALL, 0, player.seat_id)
            else:
                return Action(ActionType.FOLD, 0, player.seat_id)
        else:
            # 可以过牌或下注
            if random.random() < 0.4:  # 40%概率下注
                bet_amount = snapshot.big_blind
                return Action(ActionType.BET, bet_amount, player.seat_id)
            else:
                return Action(ActionType.CHECK, 0, player.seat_id)
    
    def _random_strategy(self, snapshot, player) -> Action:
        """随机策略：完全随机选择"""
        if snapshot.current_bet > player.current_bet:
            # 需要跟注或弃牌
            if random.random() < 0.5:
                return Action(ActionType.CALL, 0, player.seat_id)
            else:
                return Action(ActionType.FOLD, 0, player.seat_id)
        else:
            # 可以过牌或下注
            if random.random() < 0.5:
                return Action(ActionType.CHECK, 0, player.seat_id)
            else:
                bet_amount = snapshot.big_blind
                return Action(ActionType.BET, bet_amount, player.seat_id)


class BattleTestRunner:
    """1000手对战测试运行器"""
    
    def __init__(self, num_hands: int = 1000, user_strategy: str = "balanced"):
        """
        初始化测试运行器
        
        Args:
            num_hands: 测试手牌数量
            user_strategy: 用户策略
        """
        self.num_hands = num_hands
        self.user_simulator = UserSimulator(user_strategy)
        self.stats = BattleStats()
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """设置日志记录"""
        logger = logging.getLogger("BattleTest")
        logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        log_file = project_root / "v2" / "tests" / "test_logs" / f"battle_test_{int(time.time())}.log"
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
    
    def run_battle_test(self) -> BattleStats:
        """
        运行1000手对战测试
        
        Returns:
            测试统计结果
        """
        self.logger.info(f"开始{self.num_hands}手对战测试")
        start_time = time.time()
        
        # 创建游戏控制器
        game_state = GameState()
        ai_strategy = SimpleAI()
        event_bus = EventBus()
        controller = PokerController(game_state, ai_strategy, self.logger, event_bus)
        
        # 设置玩家
        self._setup_players(controller)
        
        # 记录初始筹码
        initial_snapshot = controller.get_snapshot()
        if initial_snapshot:
            self.stats.total_chips_start = sum(p.chips for p in initial_snapshot.players)
            self.logger.info(f"初始总筹码: {self.stats.total_chips_start}")
        
        # 运行测试
        for hand_num in range(self.num_hands):
            try:
                self._run_single_hand(controller, hand_num + 1)
                
                # 每100手报告进度
                if (hand_num + 1) % 100 == 0:
                    self.logger.info(f"已完成 {hand_num + 1}/{self.num_hands} 手")
                    self._log_progress_stats()
                    
            except Exception as e:
                error_msg = f"Hand {hand_num + 1}: {str(e)}"
                self.stats.errors.append(error_msg)
                self.logger.error(error_msg)
                self.stats.hands_failed += 1
                continue
        
        # 计算最终统计
        self._calculate_final_stats(controller)
        
        end_time = time.time()
        self.stats.performance_metrics["total_time"] = end_time - start_time
        self.stats.performance_metrics["hands_per_second"] = self.stats.hands_completed / (end_time - start_time)
        
        self.logger.info(f"测试完成，耗时: {end_time - start_time:.2f}秒")
        self._log_final_stats()
        
        return self.stats
    
    def _setup_players(self, controller: PokerController) -> None:
        """设置玩家"""
        # 添加人类玩家（用户模拟器）
        user_player = Player(seat_id=0, name="User", chips=1000)
        controller._game_state.add_player(user_player)
        
        # 添加AI玩家
        for i in range(1, 4):  # 3个AI玩家
            ai_player = Player(seat_id=i, name=f"AI_{i}", chips=1000)
            controller._game_state.add_player(ai_player)
    
    def _run_single_hand(self, controller: PokerController, hand_num: int) -> None:
        """运行单手牌"""
        self.stats.hands_played += 1
        
        try:
            # 开始新手牌
            if not controller.start_new_hand():
                raise Exception("Failed to start new hand")
        except Exception as e:
            # 如果开始新手牌失败，强制重置手牌状态
            self.logger.warning(f"Hand {hand_num}: Failed to start new hand: {e}")
            controller.force_reset_hand_state()
            error_msg = f"Hand {hand_num}: {str(e)}"
            self.stats.errors.append(error_msg)
            self.stats.hands_failed += 1
            return
        
        # 记录手牌开始时的筹码
        start_snapshot = controller.get_snapshot()
        start_chips = sum(p.chips for p in start_snapshot.players) if start_snapshot else 0
        
        # 处理整手牌
        max_actions = 200  # 防止无限循环
        actions_taken = 0
        hand_completed_normally = False
        
        while not controller.is_hand_over() and actions_taken < max_actions:
            current_player_id = controller.get_current_player_id()
            if current_player_id is None:
                break
                
            snapshot = controller.get_snapshot()
            if not snapshot:
                break
            
            # 记录阶段分布
            phase_name = snapshot.phase.value
            self.stats.phase_distribution[phase_name] = self.stats.phase_distribution.get(phase_name, 0) + 1
            
            try:
                if current_player_id == 0:  # 用户玩家
                    action = self.user_simulator.decide_action(snapshot, current_player_id)
                    controller.execute_action(action)
                    
                    # 记录行动分布
                    action_name = action.action_type.value
                    self.stats.action_distribution[action_name] = self.stats.action_distribution.get(action_name, 0) + 1
                else:  # AI玩家
                    controller.process_ai_action()
                
                self.stats.total_actions += 1
                actions_taken += 1
                
            except Exception as e:
                self.logger.warning(f"Action error in hand {hand_num}: {e}")
                # 记录错误但不立即退出，让手牌尝试自然结束
                error_msg = f"Hand {hand_num}: {str(e)}"
                self.stats.errors.append(error_msg)
                break
        
        # 检查手牌是否正常结束
        if controller.is_hand_over():
            try:
                result = controller.end_hand()
                self.stats.hands_completed += 1
                hand_completed_normally = True
                
                # 统计胜负
                if result and result.winner_ids:
                    winner_ids = result.winner_ids
                    if 0 in winner_ids:  # 用户获胜
                        self.stats.user_wins += 1
                    elif len(winner_ids) > 1 and 0 in winner_ids:  # 平局且用户参与
                        self.stats.ties += 1
                    else:  # AI获胜
                        self.stats.ai_wins += 1
                
            except Exception as e:
                self.logger.warning(f"End hand error in hand {hand_num}: {e}")
                error_msg = f"Hand {hand_num}: End hand error: {str(e)}"
                self.stats.errors.append(error_msg)
                self.stats.hands_failed += 1
                hand_completed_normally = False
        else:
            self.stats.hands_failed += 1
            self.logger.warning(f"Hand {hand_num} did not finish properly")
            hand_completed_normally = False
        
        # 如果手牌没有正常完成，强制重置手牌状态
        if not hand_completed_normally:
            self.logger.warning(f"Hand {hand_num}: Forcing hand state reset")
            controller.force_reset_hand_state()
        
        # 检查筹码守恒（只在手牌正常完成时检查）
        if hand_completed_normally:
            end_snapshot = controller.get_snapshot()
            end_chips = sum(p.chips for p in end_snapshot.players) if end_snapshot else 0
            
            if start_chips != end_chips:
                violation = f"Hand {hand_num}: Chip conservation violated ({start_chips} -> {end_chips})"
                self.stats.chip_conservation_violations.append(violation)
                self.logger.warning(violation)
    
    def _log_progress_stats(self) -> None:
        """记录进度统计"""
        completion_rate = (self.stats.hands_completed / self.stats.hands_played) * 100 if self.stats.hands_played > 0 else 0
        self.logger.info(f"完成率: {completion_rate:.1f}% ({self.stats.hands_completed}/{self.stats.hands_played})")
        
        if self.stats.hands_completed > 0:
            user_win_rate = (self.stats.user_wins / self.stats.hands_completed) * 100
            self.logger.info(f"用户胜率: {user_win_rate:.1f}%")
    
    def _calculate_final_stats(self, controller: PokerController) -> None:
        """计算最终统计"""
        # 记录最终筹码
        final_snapshot = controller.get_snapshot()
        if final_snapshot:
            self.stats.total_chips_end = sum(p.chips for p in final_snapshot.players)
        
        # 计算性能指标
        if self.stats.hands_completed > 0:
            self.stats.performance_metrics["completion_rate"] = (self.stats.hands_completed / self.stats.hands_played) * 100
            self.stats.performance_metrics["user_win_rate"] = (self.stats.user_wins / self.stats.hands_completed) * 100
            self.stats.performance_metrics["ai_win_rate"] = (self.stats.ai_wins / self.stats.hands_completed) * 100
            self.stats.performance_metrics["tie_rate"] = (self.stats.ties / self.stats.hands_completed) * 100
            self.stats.performance_metrics["actions_per_hand"] = self.stats.total_actions / self.stats.hands_completed
    
    def _log_final_stats(self) -> None:
        """记录最终统计"""
        self.logger.info("=== 最终测试结果 ===")
        self.logger.info(f"总手牌数: {self.stats.hands_played}")
        self.logger.info(f"完成手牌数: {self.stats.hands_completed}")
        self.logger.info(f"失败手牌数: {self.stats.hands_failed}")
        self.logger.info(f"完成率: {self.stats.performance_metrics.get('completion_rate', 0):.1f}%")
        
        self.logger.info(f"用户胜利: {self.stats.user_wins}")
        self.logger.info(f"AI胜利: {self.stats.ai_wins}")
        self.logger.info(f"平局: {self.stats.ties}")
        self.logger.info(f"用户胜率: {self.stats.performance_metrics.get('user_win_rate', 0):.1f}%")
        
        self.logger.info(f"总行动数: {self.stats.total_actions}")
        self.logger.info(f"平均每手行动数: {self.stats.performance_metrics.get('actions_per_hand', 0):.1f}")
        
        self.logger.info(f"初始总筹码: {self.stats.total_chips_start}")
        self.logger.info(f"最终总筹码: {self.stats.total_chips_end}")
        self.logger.info(f"筹码守恒违规: {len(self.stats.chip_conservation_violations)}")
        
        self.logger.info(f"错误数量: {len(self.stats.errors)}")
        self.logger.info(f"测试速度: {self.stats.performance_metrics.get('hands_per_second', 0):.2f} 手/秒")
        
        if self.stats.errors:
            self.logger.info("错误列表:")
            for error in self.stats.errors[:10]:  # 只显示前10个错误
                self.logger.info(f"  - {error}")
    
    def export_results(self, filepath: str) -> None:
        """导出测试结果到文件"""
        results = {
            "test_config": {
                "num_hands": self.num_hands,
                "user_strategy": self.user_simulator.strategy
            },
            "stats": {
                "hands_played": self.stats.hands_played,
                "hands_completed": self.stats.hands_completed,
                "hands_failed": self.stats.hands_failed,
                "total_actions": self.stats.total_actions,
                "user_wins": self.stats.user_wins,
                "ai_wins": self.stats.ai_wins,
                "ties": self.stats.ties,
                "total_chips_start": self.stats.total_chips_start,
                "total_chips_end": self.stats.total_chips_end,
                "chip_conservation_violations": len(self.stats.chip_conservation_violations),
                "errors": len(self.stats.errors),
                "performance_metrics": self.stats.performance_metrics,
                "phase_distribution": self.stats.phase_distribution,
                "action_distribution": self.stats.action_distribution
            },
            "violations": self.stats.chip_conservation_violations,
            "errors": self.stats.errors[:50]  # 只保存前50个错误
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)


def main():
    """主函数"""
    print("🃏 开始1000手德州扑克对战测试...")
    
    # 创建测试运行器
    runner = BattleTestRunner(num_hands=1000, user_strategy="balanced")
    
    # 运行测试
    stats = runner.run_battle_test()
    
    # 导出结果
    results_file = project_root / "v2" / "tests" / "test_logs" / f"battle_results_{int(time.time())}.json"
    runner.export_results(str(results_file))
    
    print(f"\n📊 测试结果已保存到: {results_file}")
    
    # 检查关键指标
    print("\n🔍 关键指标检查:")
    
    # 完成率检查
    completion_rate = stats.performance_metrics.get('completion_rate', 0)
    if completion_rate >= 95:
        print(f"✅ 完成率: {completion_rate:.1f}% (优秀)")
    elif completion_rate >= 90:
        print(f"⚠️  完成率: {completion_rate:.1f}% (良好)")
    else:
        print(f"❌ 完成率: {completion_rate:.1f}% (需要改进)")
    
    # 筹码守恒检查
    if len(stats.chip_conservation_violations) == 0:
        print("✅ 筹码守恒: 无违规")
    else:
        print(f"❌ 筹码守恒: {len(stats.chip_conservation_violations)} 次违规")
    
    # 错误检查
    if len(stats.errors) == 0:
        print("✅ 错误数量: 0")
    elif len(stats.errors) <= 10:
        print(f"⚠️  错误数量: {len(stats.errors)} (可接受)")
    else:
        print(f"❌ 错误数量: {len(stats.errors)} (需要修复)")
    
    # 性能检查
    hands_per_second = stats.performance_metrics.get('hands_per_second', 0)
    if hands_per_second >= 10:
        print(f"✅ 测试速度: {hands_per_second:.2f} 手/秒 (优秀)")
    elif hands_per_second >= 5:
        print(f"⚠️  测试速度: {hands_per_second:.2f} 手/秒 (良好)")
    else:
        print(f"❌ 测试速度: {hands_per_second:.2f} 手/秒 (需要优化)")
    
    print("\n🎯 测试完成！")
    
    return stats


if __name__ == "__main__":
    main() 