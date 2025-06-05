"""
Test Statistics Service - 测试统计服务

专门用于管理UI层测试的统计逻辑，遵循CQRS模式。
负责：
- 测试统计数据收集
- 性能指标计算
- 测试结果分析
- 统计报告生成
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from .types import QueryResult


@dataclass
class TestStatsSnapshot:
    """测试统计快照"""
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
    errors: List[str] = field(default_factory=list)
    critical_errors: int = 0
    warnings: int = 0
    
    # 不变量违反专用统计
    invariant_violations: List[str] = field(default_factory=list)
    critical_invariant_violations: int = 0
    
    # 性能统计
    total_test_time: float = 0
    average_hand_time: float = 0
    average_action_time: float = 0
    
    # 游戏流程统计
    action_distribution: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


class TestStatsService:
    """测试统计服务
    
    负责收集、计算和分析UI层测试的统计数据。
    """
    
    def __init__(self):
        self._stats_store: Dict[str, TestStatsSnapshot] = {}
        self._start_times: Dict[str, float] = {}
        self._hand_start_times: Dict[str, float] = {}
    
    def create_test_session(self, session_id: str, initial_config: Dict[str, Any] = None) -> QueryResult[str]:
        """
        创建测试会话
        
        Args:
            session_id: 测试会话ID
            initial_config: 初始配置
            
        Returns:
            查询结果，包含会话ID
        """
        try:
            if session_id in self._stats_store:
                return QueryResult.failure_result(
                    f"测试会话 {session_id} 已存在",
                    error_code="TEST_SESSION_EXISTS"
                )
            
            self._stats_store[session_id] = TestStatsSnapshot()
            self._start_times[session_id] = time.time()
            
            # 设置初始配置
            if initial_config:
                stats = self._stats_store[session_id]
                stats.initial_total_chips = initial_config.get('initial_total_chips', 0)
            
            return QueryResult.success_result(session_id)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"创建测试会话失败: {str(e)}",
                error_code="CREATE_TEST_SESSION_FAILED"
            )
    
    def get_test_stats(self, session_id: str) -> QueryResult[TestStatsSnapshot]:
        """
        获取测试统计
        
        Args:
            session_id: 测试会话ID
            
        Returns:
            查询结果，包含统计快照
        """
        try:
            if session_id not in self._stats_store:
                return QueryResult.failure_result(
                    f"测试会话 {session_id} 不存在",
                    error_code="TEST_SESSION_NOT_FOUND"
                )
            
            return QueryResult.success_result(self._stats_store[session_id])
            
        except Exception as e:
            return QueryResult.failure_result(
                f"获取测试统计失败: {str(e)}",
                error_code="GET_TEST_STATS_FAILED"
            )
    
    def record_hand_start(self, session_id: str) -> QueryResult[bool]:
        """
        记录手牌开始
        
        Args:
            session_id: 测试会话ID
            
        Returns:
            查询结果，表示是否成功
        """
        try:
            if session_id not in self._stats_store:
                return QueryResult.failure_result(
                    f"测试会话 {session_id} 不存在",
                    error_code="TEST_SESSION_NOT_FOUND"
                )
            
            stats = self._stats_store[session_id]
            stats.hands_attempted += 1
            self._hand_start_times[session_id] = time.time()
            
            return QueryResult.success_result(True)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"记录手牌开始失败: {str(e)}",
                error_code="RECORD_HAND_START_FAILED"
            )
    
    def record_hand_complete(self, session_id: str) -> QueryResult[bool]:
        """
        记录手牌完成
        
        Args:
            session_id: 测试会话ID
            
        Returns:
            查询结果，表示是否成功
        """
        try:
            if session_id not in self._stats_store:
                return QueryResult.failure_result(
                    f"测试会话 {session_id} 不存在",
                    error_code="TEST_SESSION_NOT_FOUND"
                )
            
            stats = self._stats_store[session_id]
            stats.hands_completed += 1
            
            # 计算手牌时间
            if session_id in self._hand_start_times:
                hand_time = time.time() - self._hand_start_times[session_id]
                if stats.hands_completed > 0:
                    stats.average_hand_time = ((stats.average_hand_time * (stats.hands_completed - 1)) + hand_time) / stats.hands_completed
                del self._hand_start_times[session_id]
            
            return QueryResult.success_result(True)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"记录手牌完成失败: {str(e)}",
                error_code="RECORD_HAND_COMPLETE_FAILED"
            )
    
    def record_hand_failed(self, session_id: str, error_message: str) -> QueryResult[bool]:
        """
        记录手牌失败
        
        Args:
            session_id: 测试会话ID
            error_message: 错误信息
            
        Returns:
            查询结果，表示是否成功
        """
        try:
            if session_id not in self._stats_store:
                return QueryResult.failure_result(
                    f"测试会话 {session_id} 不存在",
                    error_code="TEST_SESSION_NOT_FOUND"
                )
            
            stats = self._stats_store[session_id]
            stats.hands_failed += 1
            stats.errors.append(error_message)
            
            return QueryResult.success_result(True)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"记录手牌失败失败: {str(e)}",
                error_code="RECORD_HAND_FAILED_FAILED"
            )
    
    def record_user_action(self, session_id: str, action_type: str, success: bool, 
                          action_time: float = None, error_message: str = None) -> QueryResult[bool]:
        """
        记录用户行动
        
        Args:
            session_id: 测试会话ID
            action_type: 行动类型
            success: 是否成功
            action_time: 行动耗时
            error_message: 错误信息（如果失败）
            
        Returns:
            查询结果，表示是否成功
        """
        try:
            if session_id not in self._stats_store:
                return QueryResult.failure_result(
                    f"测试会话 {session_id} 不存在",
                    error_code="TEST_SESSION_NOT_FOUND"
                )
            
            stats = self._stats_store[session_id]
            stats.total_user_actions += 1
            
            if success:
                stats.successful_actions += 1
                # 记录行动分布
                stats.action_distribution[action_type] = stats.action_distribution.get(action_type, 0) + 1
            else:
                stats.failed_actions += 1
                if error_message:
                    stats.errors.append(error_message)
            
            # 更新平均行动时间
            if action_time and stats.total_user_actions > 0:
                stats.average_action_time = ((stats.average_action_time * (stats.total_user_actions - 1)) + action_time) / stats.total_user_actions
            
            return QueryResult.success_result(True)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"记录用户行动失败: {str(e)}",
                error_code="RECORD_USER_ACTION_FAILED"
            )
    
    def record_invariant_violation(self, session_id: str, violation_message: str, is_critical: bool = True) -> QueryResult[bool]:
        """
        记录不变量违反
        
        Args:
            session_id: 测试会话ID
            violation_message: 违反信息
            is_critical: 是否为严重违反
            
        Returns:
            查询结果，表示是否成功
        """
        try:
            if session_id not in self._stats_store:
                return QueryResult.failure_result(
                    f"测试会话 {session_id} 不存在",
                    error_code="TEST_SESSION_NOT_FOUND"
                )
            
            stats = self._stats_store[session_id]
            stats.invariant_violations.append(violation_message)
            
            if is_critical:
                stats.critical_invariant_violations += 1
                stats.critical_errors += 1
            
            return QueryResult.success_result(True)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"记录不变量违反失败: {str(e)}",
                error_code="RECORD_INVARIANT_VIOLATION_FAILED"
            )
    
    def record_chip_conservation_violation(self, session_id: str, violation_message: str) -> QueryResult[bool]:
        """
        记录筹码守恒违反
        
        Args:
            session_id: 测试会话ID
            violation_message: 违反信息
            
        Returns:
            查询结果，表示是否成功
        """
        try:
            if session_id not in self._stats_store:
                return QueryResult.failure_result(
                    f"测试会话 {session_id} 不存在",
                    error_code="TEST_SESSION_NOT_FOUND"
                )
            
            stats = self._stats_store[session_id]
            stats.chip_conservation_violations.append(violation_message)
            
            return QueryResult.success_result(True)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"记录筹码守恒违反失败: {str(e)}",
                error_code="RECORD_CHIP_CONSERVATION_VIOLATION_FAILED"
            )
    
    def finalize_test_session(self, session_id: str, final_total_chips: int = None) -> QueryResult[Dict[str, Any]]:
        """
        完成测试会话并计算最终统计
        
        Args:
            session_id: 测试会话ID
            final_total_chips: 最终总筹码
            
        Returns:
            查询结果，包含最终统计报告
        """
        try:
            if session_id not in self._stats_store:
                return QueryResult.failure_result(
                    f"测试会话 {session_id} 不存在",
                    error_code="TEST_SESSION_NOT_FOUND"
                )
            
            stats = self._stats_store[session_id]
            
            # 计算总测试时间
            if session_id in self._start_times:
                stats.total_test_time = time.time() - self._start_times[session_id]
            
            # 设置最终筹码
            if final_total_chips is not None:
                stats.final_total_chips = final_total_chips
            
            # 生成统计报告
            report = self._generate_test_report(stats)
            
            return QueryResult.success_result(report)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"完成测试会话失败: {str(e)}",
                error_code="FINALIZE_TEST_SESSION_FAILED"
            )
    
    def _generate_test_report(self, stats: TestStatsSnapshot) -> Dict[str, Any]:
        """
        生成测试报告
        
        Args:
            stats: 统计快照
            
        Returns:
            测试报告字典
        """
        # 计算基本指标
        completion_rate = (stats.hands_completed / stats.hands_attempted * 100) if stats.hands_attempted > 0 else 0
        action_success_rate = (stats.successful_actions / stats.total_user_actions * 100) if stats.total_user_actions > 0 else 0
        hands_per_second = stats.hands_completed / stats.total_test_time if stats.total_test_time > 0 else 0
        
        # 筹码守恒状态
        chip_conservation_ok = stats.initial_total_chips == stats.final_total_chips
        
        # 生成报告
        report = {
            'summary': {
                'hands_completed': stats.hands_completed,
                'hands_attempted': stats.hands_attempted,
                'completion_rate_percent': round(completion_rate, 1),
                'action_success_rate_percent': round(action_success_rate, 1),
                'hands_per_second': round(hands_per_second, 2)
            },
            'chip_conservation': {
                'initial_chips': stats.initial_total_chips,
                'final_chips': stats.final_total_chips,
                'conservation_ok': chip_conservation_ok,
                'violations_count': len(stats.chip_conservation_violations)
            },
            'invariant_violations': {
                'total_violations': len(stats.invariant_violations),
                'critical_violations': stats.critical_invariant_violations,
                'violations_list': stats.invariant_violations
            },
            'errors': {
                'total_errors': len(stats.errors),
                'critical_errors': stats.critical_errors,
                'warnings': stats.warnings
            },
            'performance': {
                'total_test_time_seconds': round(stats.total_test_time, 2),
                'average_hand_time_seconds': round(stats.average_hand_time, 3),
                'average_action_time_seconds': round(stats.average_action_time, 3)
            },
            'action_distribution': stats.action_distribution,
            'raw_stats': stats.to_dict()
        }
        
        return report
    
    def cleanup_session(self, session_id: str) -> QueryResult[bool]:
        """
        清理测试会话
        
        Args:
            session_id: 测试会话ID
            
        Returns:
            查询结果，表示是否成功
        """
        try:
            if session_id in self._stats_store:
                del self._stats_store[session_id]
            if session_id in self._start_times:
                del self._start_times[session_id]
            if session_id in self._hand_start_times:
                del self._hand_start_times[session_id]
            
            return QueryResult.success_result(True)
            
        except Exception as e:
            return QueryResult.failure_result(
                f"清理测试会话失败: {str(e)}",
                error_code="CLEANUP_TEST_SESSION_FAILED"
            ) 