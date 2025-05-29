#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克测试通用数据结构
包含所有测试中使用的共同数据类定义
提取自原comprehensive_test.py，避免重复定义
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class CheatDetectionResult:
    """
    反作弊检测结果数据结构
    用于记录代码审查中发现的潜在作弊行为
    """
    is_suspicious: bool        # 是否可疑
    description: str          # 详细描述
    evidence: List[str]       # 证据列表
    method_name: str = ""     # 被检测的方法名（可选）
    severity: str = "low"     # 严重程度: "low", "medium", "high", "critical"
    
    @property
    def is_clean(self) -> bool:
        """检查是否没有发现违规行为"""
        return not self.is_suspicious and len(self.evidence) == 0


@dataclass  
class TestScenario:
    """
    测试场景数据结构
    定义具体的测试条件和预期行为
    """
    name: str                          # 场景名称
    players_count: int                 # 玩家数量
    starting_chips: List[int]          # 每个玩家的起始筹码
    dealer_position: int               # 庄家位置
    expected_behavior: Dict[str, Any]  # 预期行为字典
    description: str                   # 场景描述


@dataclass
class TestResult:
    """
    测试结果数据结构
    记录单个测试的执行结果
    """
    scenario_name: str    # 所属场景名称
    test_name: str       # 测试名称
    passed: bool         # 是否通过
    expected: Any        # 预期结果
    actual: Any          # 实际结果
    details: str         # 详细信息


@dataclass
class PerformanceMetrics:
    """
    性能测试指标数据结构
    记录性能测试的各项指标
    """
    test_name: str           # 测试名称
    execution_time: float    # 执行时间（秒）
    memory_usage: float      # 内存使用量（MB）
    operations_per_second: float  # 每秒操作数
    success_rate: float      # 成功率（百分比）


@dataclass
class TestSuite:
    """
    测试套件数据结构
    组织相关的测试并追踪整体状态
    """
    name: str                    # 套件名称
    category: str               # 测试类别
    results: List[TestResult]   # 测试结果列表
    total_tests: int = 0        # 总测试数
    passed_tests: int = 0       # 通过的测试数
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100.0
    
    @property
    def is_passed(self) -> bool:
        """检查整个套件是否通过"""
        return self.passed_tests == self.total_tests and self.total_tests > 0 