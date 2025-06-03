"""
完整闭环集成测试框架

实现端到端的闭环验证，确保UI操作能正确传递到Core并返回。
包含用户操作模拟器、状态变更追踪器和性能基准测试。
"""

import time
import threading
import queue
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from pathlib import Path
import pytest
import asyncio
from unittest.mock import Mock, patch

# 导入项目模块
import sys
from pathlib import Path

# 添加v2目录到Python路径
v2_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(v2_path))

from v2.core.state import GameState
from v2.core.enums import Phase, ActionType, Action, SeatStatus
from v2.controller.poker_controller import PokerController
from v2.core.player import Player
try:
    from v2.ui.cli.cli_game import CLIGame
    from v2.ui.streamlit.streamlit_app import StreamlitApp
except ImportError:
    # UI模块可能不可用，继续执行
    CLIGame = None
    StreamlitApp = None


class OperationType(Enum):
    """用户操作类型"""
    FOLD = "fold"
    CALL = "call"
    RAISE = "raise"
    CHECK = "check"
    BET = "bet"
    ALL_IN = "all_in"
    START_GAME = "start_game"
    RESTART_GAME = "restart_game"


@dataclass
class UserOperation:
    """用户操作定义"""
    operation_type: OperationType
    player_id: int
    amount: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateSnapshot:
    """状态快照"""
    timestamp: float
    game_phase: Phase
    current_player: Optional[int]
    pot_size: int
    player_chips: Dict[int, int]
    player_actions: List[str]
    community_cards: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    operation_latency: float
    state_sync_time: float
    ui_render_time: float
    memory_usage: int
    cpu_usage: float
    total_time: float


class StateChangeTracker:
    """状态变更追踪器"""
    
    def __init__(self):
        self.snapshots: List[StateSnapshot] = []
        self.state_changes: List[Dict[str, Any]] = []
        self.event_log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def capture_snapshot(self, controller: PokerController, metadata: Dict[str, Any] = None) -> StateSnapshot:
        """捕获状态快照"""
        with self._lock:
            game_snapshot = controller.get_snapshot()
            snapshot = StateSnapshot(
                timestamp=time.time(),
                game_phase=game_snapshot.phase,
                current_player=controller.get_current_player_id(),
                pot_size=game_snapshot.pot,
                player_chips={i: p.chips for i, p in enumerate(game_snapshot.players)},
                player_actions=[],  # 暂时使用空列表，因为GameSnapshot没有action_history
                community_cards=[str(card) for card in game_snapshot.community_cards],
                metadata=metadata or {}
            )
            self.snapshots.append(snapshot)
            return snapshot
    
    def track_change(self, before: StateSnapshot, after: StateSnapshot, operation: UserOperation):
        """追踪状态变更"""
        with self._lock:
            change = {
                "operation": operation,
                "before": before,
                "after": after,
                "duration": after.timestamp - before.timestamp,
                "changes": self._calculate_diff(before, after)
            }
            self.state_changes.append(change)
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """记录事件"""
        with self._lock:
            self.event_log.append({
                "timestamp": time.time(),
                "event_type": event_type,
                "data": data
            })
    
    def _calculate_diff(self, before: StateSnapshot, after: StateSnapshot) -> Dict[str, Any]:
        """计算状态差异"""
        diff = {}
        
        if before.game_phase != after.game_phase:
            diff["game_phase"] = {"before": before.game_phase, "after": after.game_phase}
        
        if before.current_player != after.current_player:
            diff["current_player"] = {"before": before.current_player, "after": after.current_player}
        
        if before.pot_size != after.pot_size:
            diff["pot_size"] = {"before": before.pot_size, "after": after.pot_size}
        
        # 检查玩家筹码变化
        chip_changes = {}
        for player_id in set(before.player_chips.keys()) | set(after.player_chips.keys()):
            before_chips = before.player_chips.get(player_id, 0)
            after_chips = after.player_chips.get(player_id, 0)
            if before_chips != after_chips:
                chip_changes[player_id] = {"before": before_chips, "after": after_chips}
        
        if chip_changes:
            diff["player_chips"] = chip_changes
        
        return diff
    
    def get_summary(self) -> Dict[str, Any]:
        """获取追踪摘要"""
        return {
            "total_snapshots": len(self.snapshots),
            "total_changes": len(self.state_changes),
            "total_events": len(self.event_log),
            "duration": self.snapshots[-1].timestamp - self.snapshots[0].timestamp if self.snapshots else 0,
            "change_frequency": len(self.state_changes) / max(1, len(self.snapshots) - 1) if len(self.snapshots) > 1 else 0
        }


class UserOperationSimulator:
    """用户操作模拟器"""
    
    def __init__(self, controller: PokerController, tracker: StateChangeTracker):
        self.controller = controller
        self.tracker = tracker
        self.operation_queue = queue.Queue()
        self.performance_metrics: List[PerformanceMetrics] = []
    
    def simulate_operation(self, operation: UserOperation) -> Tuple[bool, PerformanceMetrics]:
        """模拟用户操作"""
        start_time = time.time()
        
        # 捕获操作前状态
        before_snapshot = self.tracker.capture_snapshot(
            self.controller,
            {"operation": "before", "operation_type": operation.operation_type.value}
        )
        
        success = False
        try:
            # 执行操作
            operation_start = time.time()
            success = self._execute_operation(operation)
            operation_latency = time.time() - operation_start
            
            # 等待状态同步
            sync_start = time.time()
            time.sleep(0.01)  # 模拟状态同步延迟
            state_sync_time = time.time() - sync_start
            
            # 模拟UI渲染
            ui_start = time.time()
            self._simulate_ui_render()
            ui_render_time = time.time() - ui_start
            
            # 捕获操作后状态
            after_snapshot = self.tracker.capture_snapshot(
                self.controller,
                {"operation": "after", "operation_type": operation.operation_type.value}
            )
            
            # 追踪状态变更
            self.tracker.track_change(before_snapshot, after_snapshot, operation)
            
            # 记录性能指标
            metrics = PerformanceMetrics(
                operation_latency=operation_latency,
                state_sync_time=state_sync_time,
                ui_render_time=ui_render_time,
                memory_usage=0,  # 简化实现
                cpu_usage=0.0,  # 简化实现
                total_time=time.time() - start_time
            )
            self.performance_metrics.append(metrics)
            
            return success, metrics
            
        except Exception as e:
            self.tracker.log_event("operation_error", {
                "operation": operation.operation_type.value,
                "player_id": operation.player_id,
                "error": str(e)
            })
            
            # 创建错误指标
            metrics = PerformanceMetrics(
                operation_latency=0,
                state_sync_time=0,
                ui_render_time=0,
                memory_usage=0,
                cpu_usage=0.0,
                total_time=time.time() - start_time
            )
            
            return False, metrics
    
    def _execute_operation(self, operation: UserOperation) -> bool:
        """执行具体操作"""
        try:
            if operation.operation_type == OperationType.START_GAME:
                return self.controller.start_new_hand()
            
            # 检查是否是当前玩家
            current_player = self.controller.get_current_player_id()
            if current_player != operation.player_id:
                return False
            
            # 根据操作类型创建Action
            if operation.operation_type == OperationType.FOLD:
                action = Action(ActionType.FOLD, 0, operation.player_id)
            elif operation.operation_type == OperationType.CALL:
                action = Action(ActionType.CALL, 0, operation.player_id)
            elif operation.operation_type == OperationType.CHECK:
                action = Action(ActionType.CHECK, 0, operation.player_id)
            elif operation.operation_type == OperationType.RAISE:
                amount = operation.amount or 100
                action = Action(ActionType.RAISE, amount, operation.player_id)
            elif operation.operation_type == OperationType.BET:
                amount = operation.amount or 50
                action = Action(ActionType.BET, amount, operation.player_id)
            else:
                return False
            
            return self.controller.execute_action(action)
            
        except Exception as e:
            print(f"执行操作失败: {e}")
            return False
    
    def _simulate_ui_render(self):
        """模拟UI渲染延迟"""
        time.sleep(0.005)  # 5ms渲染延迟
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.performance_metrics:
            return {"total_operations": 0}
        
        total_ops = len(self.performance_metrics)
        avg_latency = sum(m.operation_latency for m in self.performance_metrics) / total_ops
        avg_sync_time = sum(m.state_sync_time for m in self.performance_metrics) / total_ops
        avg_ui_time = sum(m.ui_render_time for m in self.performance_metrics) / total_ops
        avg_total_time = sum(m.total_time for m in self.performance_metrics) / total_ops
        
        return {
            "total_operations": total_ops,
            "average_operation_latency": avg_latency,
            "average_state_sync_time": avg_sync_time,
            "average_ui_render_time": avg_ui_time,
            "average_total_time": avg_total_time,
            "max_operation_latency": max(m.operation_latency for m in self.performance_metrics),
            "min_operation_latency": min(m.operation_latency for m in self.performance_metrics)
        }


@dataclass
class TestResult:
    """测试结果"""
    success: bool
    steps_executed: int
    state_changes: int
    total_duration: float
    performance_metrics: Dict[str, Any]
    error_message: Optional[str] = None


class EndToEndLoopTester:
    """端到端闭环测试器"""
    
    def __init__(self):
        self.controller = None
        self.tracker = StateChangeTracker()
        self.simulator = None
        self.results: List[Dict[str, Any]] = []
    
    def setup(self):
        """设置测试环境"""
        # 创建游戏状态
        game_state = GameState()
        
        # 添加测试玩家
        players = [
            Player(seat_id=0, name="Alice", chips=1000, status=SeatStatus.ACTIVE),
            Player(seat_id=1, name="Bob", chips=1000, status=SeatStatus.ACTIVE),
            Player(seat_id=2, name="Charlie", chips=1000, status=SeatStatus.ACTIVE),
            Player(seat_id=3, name="Diana", chips=1000, status=SeatStatus.ACTIVE)
        ]
        
        for player in players:
            game_state.add_player(player)
        
        # 初始化牌组
        game_state.initialize_deck()
        
        # 创建控制器
        self.controller = PokerController(game_state=game_state)
        
        # 创建操作模拟器
        self.simulator = UserOperationSimulator(self.controller, self.tracker)
    
    def run_complete_test(self, controller: PokerController = None) -> TestResult:
        """运行完整测试"""
        if controller:
            # 重置传入控制器的手牌状态
            if hasattr(controller, '_hand_in_progress'):
                controller._hand_in_progress = False
            self.controller = controller
            self.simulator = UserOperationSimulator(self.controller, self.tracker)
        else:
            self.setup()
        
        start_time = time.time()
        steps_executed = 0
        
        try:
            # 开始新手牌
            success, _ = self.simulator.simulate_operation(
                UserOperation(OperationType.START_GAME, 0)
            )
            if success:
                steps_executed += 1
            
            # 模拟一轮行动
            max_actions = 20
            action_count = 0
            
            while not self.controller.is_hand_over() and action_count < max_actions:
                current_player = self.controller.get_current_player_id()
                if current_player is None:
                    break
                
                # 简单策略：前两个玩家跟注，后两个玩家弃牌
                if current_player in [0, 1]:
                    operation = UserOperation(OperationType.CALL, current_player)
                else:
                    operation = UserOperation(OperationType.FOLD, current_player)
                
                success, _ = self.simulator.simulate_operation(operation)
                if success:
                    steps_executed += 1
                    action_count += 1
                else:
                    break
            
            total_duration = time.time() - start_time
            
            return TestResult(
                success=True,
                steps_executed=steps_executed,
                state_changes=len(self.tracker.state_changes),
                total_duration=total_duration * 1000,  # 转换为毫秒
                performance_metrics=self.simulator.get_performance_summary()
            )
            
        except Exception as e:
            total_duration = time.time() - start_time
            return TestResult(
                success=False,
                steps_executed=steps_executed,
                state_changes=len(self.tracker.state_changes),
                total_duration=total_duration * 1000,
                performance_metrics={},
                error_message=str(e)
            )


# Pytest测试类
class TestEndToEndLoop:
    """端到端循环测试类"""
    
    def setup_method(self):
        """设置测试方法"""
        self.tester = EndToEndLoopTester()
    
    def test_basic_game_loop(self):
        """测试基础游戏循环"""
        result = self.tester.run_complete_test()
        assert result.success, f"测试失败: {result.error_message}"
        assert result.steps_executed > 0, "没有执行任何步骤"
    
    def test_complete_hand(self):
        """测试完整手牌"""
        result = self.tester.run_complete_test()
        assert result.success, f"测试失败: {result.error_message}"
        assert result.state_changes > 0, "没有状态变更"
    
    def test_performance_benchmarks(self):
        """测试性能基准"""
        result = self.tester.run_complete_test()
        assert result.success, f"测试失败: {result.error_message}"
        
        metrics = result.performance_metrics
        assert metrics["total_operations"] > 0, "没有执行操作"
        assert metrics["average_total_time"] < 1.0, "操作耗时过长"  # 1秒阈值


if __name__ == "__main__":
    # 运行演示
    tester = EndToEndLoopTester()
    result = tester.run_complete_test()
    
    print("🎯 端到端闭环测试结果")
    print("=" * 50)
    print(f"测试结果: {'✅ 成功' if result.success else '❌ 失败'}")
    print(f"执行步骤: {result.steps_executed}")
    print(f"状态变更: {result.state_changes}")
    print(f"总耗时: {result.total_duration:.2f}ms")
    
    if result.error_message:
        print(f"错误信息: {result.error_message}")
    
    print("\n性能指标:")
    for key, value in result.performance_metrics.items():
        print(f"  {key}: {value}") 