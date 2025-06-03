"""
性能基准测试模块

提供全面的性能监控和基准测试功能，包括延迟、吞吐量、内存使用等指标。
"""

import time
import psutil
import threading
import statistics
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from pathlib import Path
import gc
import sys

# 添加v2目录到Python路径
v2_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(v2_path))

from v2.controller.poker_controller import PokerController
from v2.core.state import GameState
from v2.core.enums import ActionType, Action, SeatStatus
from v2.core.player import Player


class BenchmarkType(Enum):
    """基准测试类型"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    STRESS = "stress"
    ENDURANCE = "endurance"


@dataclass
class PerformanceBenchmark:
    """性能基准"""
    name: str
    benchmark_type: BenchmarkType
    target_value: float
    tolerance: float = 0.1  # 10% tolerance
    unit: str = "ms"
    description: str = ""


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    benchmark_type: BenchmarkType
    measured_value: float
    passed: bool
    threshold: float
    duration: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.monitoring = False
        self.metrics_history: List[Dict[str, Any]] = []
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def start_monitoring(self, interval: float = 0.1):
        """开始性能监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """停止性能监控"""
        self.monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self, interval: float):
        """监控循环"""
        while self.monitoring:
            try:
                metrics = self._collect_metrics()
                with self._lock:
                    self.metrics_history.append(metrics)
                time.sleep(interval)
            except Exception as e:
                logging.error(f"Error in performance monitoring: {e}")
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """收集性能指标"""
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()
            
            return {
                "timestamp": time.time(),
                "memory_rss": memory_info.rss,
                "memory_vms": memory_info.vms,
                "cpu_percent": cpu_percent,
                "num_threads": self.process.num_threads(),
            }
        except Exception as e:
            logging.error(f"Error collecting metrics: {e}")
            return {"timestamp": time.time(), "error": str(e)}
    
    def get_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        with self._lock:
            if not self.metrics_history:
                return {}
            
            # 过滤有效数据
            valid_metrics = [m for m in self.metrics_history if "error" not in m]
            if not valid_metrics:
                return {"error": "No valid metrics collected"}
            
            # 计算统计信息
            memory_rss_values = [m["memory_rss"] for m in valid_metrics]
            cpu_values = [m["cpu_percent"] for m in valid_metrics]
            
            return {
                "duration": valid_metrics[-1]["timestamp"] - valid_metrics[0]["timestamp"],
                "samples": len(valid_metrics),
                "memory": {
                    "avg_rss_mb": statistics.mean(memory_rss_values) / 1024 / 1024,
                    "max_rss_mb": max(memory_rss_values) / 1024 / 1024,
                    "min_rss_mb": min(memory_rss_values) / 1024 / 1024
                },
                "cpu": {
                    "avg_percent": statistics.mean(cpu_values),
                    "max_percent": max(cpu_values),
                    "min_percent": min(cpu_values)
                }
            }


class PerformanceBenchmarkSuite:
    """性能基准测试套件"""
    
    def __init__(self):
        self.benchmarks: List[PerformanceBenchmark] = []
        self.results: List[BenchmarkResult] = []
        self.monitor = PerformanceMonitor()
        self.logger = logging.getLogger(__name__)
        
        # 设置默认基准
        self._setup_default_benchmarks()
    
    def _setup_default_benchmarks(self):
        """设置默认性能基准"""
        self.benchmarks = [
            PerformanceBenchmark(
                "operation_latency",
                BenchmarkType.LATENCY,
                100.0,  # 100ms
                0.5,    # 50% tolerance
                "ms",
                "单个操作的平均延迟"
            ),
            PerformanceBenchmark(
                "game_setup_time",
                BenchmarkType.LATENCY,
                50.0,   # 50ms
                0.5,    # 50% tolerance
                "ms",
                "游戏设置时间"
            ),
            PerformanceBenchmark(
                "action_execution_time",
                BenchmarkType.LATENCY,
                20.0,   # 20ms
                0.5,    # 50% tolerance
                "ms",
                "行动执行时间"
            ),
        ]
    
    def _create_test_controller(self) -> PokerController:
        """创建测试控制器"""
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
        
        return PokerController(game_state=game_state)
    
    def run_benchmarks(self, controller: PokerController = None) -> List[BenchmarkResult]:
        """运行所有基准测试"""
        # 总是创建新的控制器来避免状态冲突
        # 传入的控制器参数保留用于兼容性，但不使用
        
        results = []
        
        # 运行延迟基准测试
        results.extend(self._run_latency_benchmarks(None))
        
        # 运行内存基准测试
        results.extend(self._run_memory_benchmarks(None))
        
        self.results = results
        return results
    
    def _run_latency_benchmarks(self, controller: PokerController) -> List[BenchmarkResult]:
        """运行延迟基准测试"""
        results = []
        
        # 测试游戏设置时间
        setup_times = []
        for _ in range(5):
            start_time = time.time()
            test_controller = self._create_test_controller()
            setup_time = (time.time() - start_time) * 1000  # 转换为毫秒
            setup_times.append(setup_time)
        
        avg_setup_time = statistics.mean(setup_times)
        setup_benchmark = next((b for b in self.benchmarks if b.name == "game_setup_time"), None)
        if setup_benchmark:
            passed = avg_setup_time <= setup_benchmark.target_value * (1 + setup_benchmark.tolerance)
            results.append(BenchmarkResult(
                benchmark_type=setup_benchmark.benchmark_type,
                measured_value=avg_setup_time,
                passed=passed,
                threshold=setup_benchmark.target_value,
                duration=avg_setup_time
            ))
        
        # 测试行动执行时间 - 总是使用新的控制器
        action_test_controller = self._create_test_controller()
        # 确保控制器状态被重置
        if hasattr(action_test_controller, '_hand_in_progress'):
            action_test_controller._hand_in_progress = False
        action_test_controller.start_new_hand()
        action_times = []
        
        for _ in range(10):
            current_player = action_test_controller.get_current_player_id()
            if current_player is not None:
                start_time = time.time()
                action = Action(ActionType.CALL, 0, current_player)
                action_test_controller.execute_action(action)
                action_time = (time.time() - start_time) * 1000
                action_times.append(action_time)
            else:
                break
        
        if action_times:
            avg_action_time = statistics.mean(action_times)
            action_benchmark = next((b for b in self.benchmarks if b.name == "action_execution_time"), None)
            if action_benchmark:
                passed = avg_action_time <= action_benchmark.target_value * (1 + action_benchmark.tolerance)
                results.append(BenchmarkResult(
                    benchmark_type=action_benchmark.benchmark_type,
                    measured_value=avg_action_time,
                    passed=passed,
                    threshold=action_benchmark.target_value,
                    duration=avg_action_time
                ))
        
        return results
    
    def _run_memory_benchmarks(self, controller: PokerController) -> List[BenchmarkResult]:
        """运行内存基准测试"""
        results = []
        
        # 使用新的控制器避免状态冲突
        test_controller = self._create_test_controller()
        
        # 开始内存监控
        self.monitor.start_monitoring(0.1)
        
        try:
            # 执行一系列操作
            for i in range(10):
                # 检查是否需要开始新手牌
                if test_controller.is_hand_over():
                    # 确保控制器状态被重置
                    if hasattr(test_controller, '_hand_in_progress'):
                        test_controller._hand_in_progress = False
                    test_controller.start_new_hand()
                
                # 执行一些行动
                for _ in range(5):
                    current_player = test_controller.get_current_player_id()
                    if current_player is not None:
                        action = Action(ActionType.CALL, 0, current_player)
                        test_controller.execute_action(action)
                    else:
                        break
                
                # 如果手牌结束，继续下一轮
                if test_controller.is_hand_over():
                    continue
            
            time.sleep(1.0)  # 等待监控数据
            
        finally:
            self.monitor.stop_monitoring()
        
        # 分析内存使用
        summary = self.monitor.get_summary()
        if summary and "memory" in summary:
            avg_memory_mb = summary["memory"]["avg_rss_mb"]
            
            # 创建内存基准结果
            memory_threshold = 200.0  # 200MB阈值
            passed = avg_memory_mb <= memory_threshold
            results.append(BenchmarkResult(
                benchmark_type=BenchmarkType.MEMORY,
                measured_value=avg_memory_mb,
                passed=passed,
                threshold=memory_threshold,
                duration=summary["duration"] * 1000,  # 转换为毫秒
                metadata={"max_memory_mb": summary["memory"]["max_rss_mb"]}
            ))
        
        return results
    
    def get_benchmark_summary(self) -> Dict[str, Any]:
        """获取基准测试摘要"""
        if not self.results:
            return {"error": "No benchmark results available"}
        
        total_benchmarks = len(self.results)
        passed_benchmarks = sum(1 for r in self.results if r.passed)
        
        return {
            "total_benchmarks": total_benchmarks,
            "passed_benchmarks": passed_benchmarks,
            "failed_benchmarks": total_benchmarks - passed_benchmarks,
            "success_rate": passed_benchmarks / total_benchmarks if total_benchmarks > 0 else 0,
            "results": [
                {
                    "type": r.benchmark_type.value,
                    "measured_value": r.measured_value,
                    "threshold": r.threshold,
                    "passed": r.passed,
                    "duration": r.duration
                }
                for r in self.results
            ]
        }


if __name__ == "__main__":
    # 运行演示
    suite = PerformanceBenchmarkSuite()
    results = suite.run_benchmarks()
    
    print("🎯 性能基准测试结果")
    print("=" * 50)
    
    for result in results:
        status = "✅" if result.passed else "❌"
        print(f"{status} {result.benchmark_type.value}: {result.measured_value:.2f}ms (阈值: {result.threshold:.2f}ms)")
    
    summary = suite.get_benchmark_summary()
    print(f"\n总结: {summary['passed_benchmarks']}/{summary['total_benchmarks']} 通过")
    print(f"成功率: {summary['success_rate']*100:.1f}%") 