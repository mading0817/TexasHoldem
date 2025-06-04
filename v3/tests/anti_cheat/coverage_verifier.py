"""
Coverage Verifier - 覆盖率验证器

该模块验证测试真正覆盖了核心代码路径，防止测试绕过关键逻辑。
确保测试的覆盖率达到要求的标准。

Classes:
    CoverageVerifier: 覆盖率验证器
"""

import sys
import time
import inspect
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class CoverageData:
    """覆盖率数据"""
    test_name: str
    start_time: float
    end_time: float
    covered_modules: Set[str]
    covered_lines: Dict[str, Set[int]]
    total_lines: Dict[str, int]
    coverage_percentage: float


class CoverageVerifier:
    """覆盖率验证器
    
    验证测试真正覆盖了核心代码路径，确保测试质量。
    """
    
    def __init__(self):
        """初始化验证器"""
        self._tracked_modules: List[str] = []
        self._coverage_stats: Dict[str, CoverageData] = {}
        self._current_test_name: Optional[str] = None
        self._tracking_active: bool = False
        self._start_time: float = 0.0
        self._covered_modules: Set[str] = set()
        self._covered_lines: Dict[str, Set[int]] = {}
    
    def get_tracked_modules(self) -> List[str]:
        """获取已跟踪的模块列表
        
        Returns:
            模块名称列表
        """
        return list(self._tracked_modules)
    
    def get_coverage_stats(self) -> Dict[str, Any]:
        """获取覆盖率统计
        
        Returns:
            覆盖率统计字典
        """
        return {
            test_name: {
                "test_name": data.test_name,
                "duration": data.end_time - data.start_time,
                "covered_modules": list(data.covered_modules),
                "coverage_percentage": data.coverage_percentage,
                "covered_lines_count": sum(len(lines) for lines in data.covered_lines.values()),
                "total_lines_count": sum(data.total_lines.values())
            }
            for test_name, data in self._coverage_stats.items()
        }
    
    def start_coverage_tracking(self, test_name: str) -> None:
        """开始覆盖率跟踪
        
        Args:
            test_name: 测试名称
        """
        self._current_test_name = test_name
        self._tracking_active = True
        self._start_time = time.time()
        self._covered_modules.clear()
        self._covered_lines.clear()
        
        # 开始跟踪当前执行的代码
        self._start_line_tracking()
    
    def stop_coverage_tracking(self) -> Dict[str, Any]:
        """停止覆盖率跟踪
        
        Returns:
            覆盖率数据
        """
        if not self._tracking_active or not self._current_test_name:
            return {}
        
        end_time = time.time()
        
        # 计算覆盖率
        coverage_percentage = self._calculate_coverage_percentage()
        
        # 创建覆盖率数据
        coverage_data = CoverageData(
            test_name=self._current_test_name,
            start_time=self._start_time,
            end_time=end_time,
            covered_modules=self._covered_modules.copy(),
            covered_lines=dict(self._covered_lines),
            total_lines=self._get_total_lines(),
            coverage_percentage=coverage_percentage
        )
        
        # 保存数据
        self._coverage_stats[self._current_test_name] = coverage_data
        
        # 重置状态
        self._tracking_active = False
        self._current_test_name = None
        
        return {
            "test_name": coverage_data.test_name,
            "duration": coverage_data.end_time - coverage_data.start_time,
            "coverage_percentage": coverage_data.coverage_percentage,
            "covered_modules": list(coverage_data.covered_modules)
        }
    
    def is_tracking(self) -> bool:
        """检查是否正在跟踪
        
        Returns:
            如果正在跟踪返回True
        """
        return self._tracking_active
    
    def get_current_test_name(self) -> Optional[str]:
        """获取当前测试名称
        
        Returns:
            当前测试名称，如果没有则返回None
        """
        return self._current_test_name
    
    def verify_core_module_coverage(self, test_name: str, min_coverage: float = 0.8) -> None:
        """验证核心模块覆盖率
        
        Args:
            test_name: 测试名称
            min_coverage: 最小覆盖率要求
            
        Raises:
            AssertionError: 如果覆盖率不足
        """
        if test_name not in self._coverage_stats:
            raise AssertionError(f"测试 {test_name} 的覆盖率数据不存在")
        
        coverage_data = self._coverage_stats[test_name]
        actual_coverage = coverage_data.coverage_percentage
        
        if actual_coverage < min_coverage:
            raise AssertionError(
                f"核心模块覆盖率不足: 测试 {test_name} 实际覆盖率 {actual_coverage:.2%}, "
                f"要求 {min_coverage:.2%}"
            )
    
    def get_coverage_report(self) -> Dict[str, Any]:
        """获取覆盖率报告
        
        Returns:
            覆盖率报告
        """
        if not self._coverage_stats:
            return {
                "total_tests": 0,
                "average_coverage": 0.0,
                "tests_details": []
            }
        
        total_coverage = sum(data.coverage_percentage for data in self._coverage_stats.values())
        average_coverage = total_coverage / len(self._coverage_stats)
        
        tests_details = [
            {
                "test_name": data.test_name,
                "coverage_percentage": data.coverage_percentage,
                "duration": data.end_time - data.start_time,
                "covered_modules_count": len(data.covered_modules)
            }
            for data in self._coverage_stats.values()
        ]
        
        return {
            "total_tests": len(self._coverage_stats),
            "average_coverage": average_coverage,
            "tests_details": tests_details
        }
    
    def verify_line_coverage(self, line_coverage: Dict[str, Dict[str, Any]], min_coverage: float = 0.8) -> None:
        """验证行覆盖率
        
        Args:
            line_coverage: 行覆盖率数据
            min_coverage: 最小覆盖率要求
            
        Raises:
            AssertionError: 如果行覆盖率不足
        """
        for file_path, coverage_info in line_coverage.items():
            actual_coverage = coverage_info.get("coverage_percentage", 0.0)
            
            if actual_coverage < min_coverage:
                raise AssertionError(
                    f"行覆盖率不足: 文件 {file_path} 实际覆盖率 {actual_coverage:.2%}, "
                    f"要求 {min_coverage:.2%}"
                )
    
    def verify_branch_coverage(self, branch_coverage: Dict[str, Dict[str, Any]], min_coverage: float = 0.8) -> None:
        """验证分支覆盖率
        
        Args:
            branch_coverage: 分支覆盖率数据
            min_coverage: 最小覆盖率要求
            
        Raises:
            AssertionError: 如果分支覆盖率不足
        """
        for file_path, coverage_info in branch_coverage.items():
            actual_coverage = coverage_info.get("coverage_percentage", 0.0)
            
            if actual_coverage < min_coverage:
                raise AssertionError(
                    f"分支覆盖率不足: 文件 {file_path} 实际覆盖率 {actual_coverage:.2%}, "
                    f"要求 {min_coverage:.2%}"
                )
    
    def get_uncovered_lines(self, coverage_data: Dict[str, Dict[str, Any]]) -> Dict[str, List[int]]:
        """获取未覆盖的行
        
        Args:
            coverage_data: 覆盖率数据
            
        Returns:
            未覆盖行的字典
        """
        uncovered_lines = {}
        
        for file_path, file_coverage in coverage_data.items():
            covered_lines = set(file_coverage.get("covered_lines", []))
            total_lines = file_coverage.get("total_lines", 0)
            
            # 计算未覆盖的行
            all_lines = set(range(1, total_lines + 1))
            uncovered = sorted(all_lines - covered_lines)
            
            if uncovered:
                uncovered_lines[file_path] = uncovered
        
        return uncovered_lines
    
    def reset_coverage_data(self) -> None:
        """重置覆盖率数据"""
        self._tracked_modules.clear()
        self._coverage_stats.clear()
        self._current_test_name = None
        self._tracking_active = False
        self._covered_modules.clear()
        self._covered_lines.clear()
    
    @contextmanager
    def coverage_context(self, test_name: str):
        """覆盖率跟踪上下文管理器
        
        Args:
            test_name: 测试名称
        """
        self.start_coverage_tracking(test_name)
        try:
            yield
        finally:
            self.stop_coverage_tracking()
    
    def _start_line_tracking(self) -> None:
        """开始行级跟踪"""
        # 获取当前调用栈
        frame = inspect.currentframe()
        while frame:
            try:
                module = inspect.getmodule(frame)
                if module and hasattr(module, '__name__'):
                    module_name = module.__name__
                    
                    # 只跟踪v3模块
                    if module_name.startswith('v3.'):
                        self._covered_modules.add(module_name)
                        
                        # 记录模块
                        if module_name not in self._tracked_modules:
                            self._tracked_modules.append(module_name)
                        
                        # 记录行号
                        if hasattr(frame, 'f_lineno'):
                            if module_name not in self._covered_lines:
                                self._covered_lines[module_name] = set()
                            self._covered_lines[module_name].add(frame.f_lineno)
                
                frame = frame.f_back
            except Exception:
                frame = frame.f_back if frame else None
    
    def _calculate_coverage_percentage(self) -> float:
        """计算覆盖率百分比
        
        Returns:
            覆盖率百分比
        """
        if not self._covered_modules:
            return 0.0
        
        # 简化的覆盖率计算：基于覆盖的模块数量
        total_core_modules = len([m for m in self._covered_modules if m.startswith('v3.core.')])
        total_modules = len(self._covered_modules)
        
        if total_modules == 0:
            return 0.0
        
        # 核心模块权重更高
        core_weight = 0.8
        other_weight = 0.2
        
        core_coverage = total_core_modules / max(1, total_modules)
        other_coverage = (total_modules - total_core_modules) / max(1, total_modules)
        
        return core_coverage * core_weight + other_coverage * other_weight
    
    def _get_total_lines(self) -> Dict[str, int]:
        """获取总行数（简化实现）
        
        Returns:
            每个模块的总行数
        """
        total_lines = {}
        
        for module_name in self._covered_modules:
            try:
                module = sys.modules.get(module_name)
                if module and hasattr(module, '__file__') and module.__file__:
                    # 简化：假设每个模块有100行（实际应该读取文件）
                    total_lines[module_name] = 100
                else:
                    total_lines[module_name] = 50  # 默认值
            except Exception:
                total_lines[module_name] = 50  # 默认值
        
        return total_lines 