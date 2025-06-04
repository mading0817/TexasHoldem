"""
不变量类型单元测试

测试不变量相关的基础类型定义。
"""

import pytest
import time
from unittest.mock import Mock

from v3.core.invariant.types import (
    InvariantType,
    InvariantViolation,
    InvariantCheckResult,
    InvariantError
)
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestInvariantType:
    """测试不变量类型枚举"""
    
    def test_invariant_type_enum_values(self):
        """测试不变量类型枚举值"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(InvariantType.CHIP_CONSERVATION, "InvariantType")
        
        # 测试所有枚举值存在
        assert InvariantType.CHIP_CONSERVATION
        assert InvariantType.BETTING_RULES
        assert InvariantType.PHASE_CONSISTENCY
        assert InvariantType.POT_INTEGRITY
        assert InvariantType.PLAYER_STATE
        assert InvariantType.CARD_DISTRIBUTION
        
        # 测试枚举值唯一性
        all_values = list(InvariantType)
        assert len(all_values) == len(set(all_values))


class TestInvariantViolation:
    """测试不变量违反记录"""
    
    def test_create_valid_violation(self):
        """测试创建有效的违反记录"""
        violation = InvariantViolation(
            invariant_type=InvariantType.CHIP_CONSERVATION,
            violation_id="test_violation_001",
            description="测试违反描述",
            severity="CRITICAL",
            timestamp=time.time(),
            context={"test_key": "test_value"}
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(violation, "InvariantViolation")
        
        assert violation.invariant_type == InvariantType.CHIP_CONSERVATION
        assert violation.violation_id == "test_violation_001"
        assert violation.description == "测试违反描述"
        assert violation.severity == "CRITICAL"
        assert violation.timestamp > 0
        assert violation.context["test_key"] == "test_value"
    
    def test_violation_validation_empty_id(self):
        """测试违反记录验证 - 空ID"""
        with pytest.raises(ValueError, match="violation_id不能为空"):
            InvariantViolation(
                invariant_type=InvariantType.CHIP_CONSERVATION,
                violation_id="",
                description="测试描述",
                severity="CRITICAL",
                timestamp=time.time(),
                context={}
            )
    
    def test_violation_validation_empty_description(self):
        """测试违反记录验证 - 空描述"""
        with pytest.raises(ValueError, match="description不能为空"):
            InvariantViolation(
                invariant_type=InvariantType.CHIP_CONSERVATION,
                violation_id="test_001",
                description="",
                severity="CRITICAL",
                timestamp=time.time(),
                context={}
            )
    
    def test_violation_validation_invalid_severity(self):
        """测试违反记录验证 - 无效严重程度"""
        with pytest.raises(ValueError, match="severity必须是CRITICAL、WARNING或INFO之一"):
            InvariantViolation(
                invariant_type=InvariantType.CHIP_CONSERVATION,
                violation_id="test_001",
                description="测试描述",
                severity="INVALID",
                timestamp=time.time(),
                context={}
            )
    
    def test_violation_validation_invalid_timestamp(self):
        """测试违反记录验证 - 无效时间戳"""
        with pytest.raises(ValueError, match="timestamp必须为正数"):
            InvariantViolation(
                invariant_type=InvariantType.CHIP_CONSERVATION,
                violation_id="test_001",
                description="测试描述",
                severity="CRITICAL",
                timestamp=0,
                context={}
            )


class TestInvariantCheckResult:
    """测试不变量检查结果"""
    
    def test_create_success_result(self):
        """测试创建成功的检查结果"""
        result = InvariantCheckResult.create_success(
            invariant_type=InvariantType.CHIP_CONSERVATION,
            check_duration=0.001
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(result, "InvariantCheckResult")
        
        assert result.invariant_type == InvariantType.CHIP_CONSERVATION
        assert result.is_valid is True
        assert len(result.violations) == 0
        assert result.check_duration == 0.001
        assert result.timestamp > 0
    
    def test_create_failure_result(self):
        """测试创建失败的检查结果"""
        violation = InvariantViolation(
            invariant_type=InvariantType.CHIP_CONSERVATION,
            violation_id="test_001",
            description="测试违反",
            severity="CRITICAL",
            timestamp=time.time(),
            context={}
        )
        
        result = InvariantCheckResult.create_failure(
            invariant_type=InvariantType.CHIP_CONSERVATION,
            violations=[violation],
            check_duration=0.002
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(result, "InvariantCheckResult")
        
        assert result.invariant_type == InvariantType.CHIP_CONSERVATION
        assert result.is_valid is False
        assert len(result.violations) == 1
        assert result.violations[0] == violation
        assert result.check_duration == 0.002
    
    def test_result_validation_negative_duration(self):
        """测试检查结果验证 - 负数持续时间"""
        with pytest.raises(ValueError, match="check_duration不能为负数"):
            InvariantCheckResult(
                invariant_type=InvariantType.CHIP_CONSERVATION,
                is_valid=True,
                violations=[],
                check_duration=-0.001,
                timestamp=time.time()
            )
    
    def test_result_validation_invalid_failure(self):
        """测试检查结果验证 - 失败但无违反记录"""
        with pytest.raises(ValueError, match="检查失败时必须提供违反记录"):
            InvariantCheckResult(
                invariant_type=InvariantType.CHIP_CONSERVATION,
                is_valid=False,
                violations=[],
                check_duration=0.001,
                timestamp=time.time()
            )


class TestInvariantError:
    """测试不变量错误异常"""
    
    def test_create_invariant_error(self):
        """测试创建不变量错误"""
        violations = [
            InvariantViolation(
                invariant_type=InvariantType.CHIP_CONSERVATION,
                violation_id="critical_001",
                description="严重违反",
                severity="CRITICAL",
                timestamp=time.time(),
                context={}
            ),
            InvariantViolation(
                invariant_type=InvariantType.BETTING_RULES,
                violation_id="warning_001",
                description="警告违反",
                severity="WARNING",
                timestamp=time.time(),
                context={}
            )
        ]
        
        error = InvariantError("测试错误消息", violations)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(error, "InvariantError")
        
        assert str(error) == "测试错误消息"
        assert error.violations == violations
    
    def test_get_critical_violations(self):
        """测试获取严重违反记录"""
        violations = [
            InvariantViolation(
                invariant_type=InvariantType.CHIP_CONSERVATION,
                violation_id="critical_001",
                description="严重违反",
                severity="CRITICAL",
                timestamp=time.time(),
                context={}
            ),
            InvariantViolation(
                invariant_type=InvariantType.BETTING_RULES,
                violation_id="warning_001",
                description="警告违反",
                severity="WARNING",
                timestamp=time.time(),
                context={}
            )
        ]
        
        error = InvariantError("测试错误", violations)
        critical_violations = error.get_critical_violations()
        
        assert len(critical_violations) == 1
        assert critical_violations[0].severity == "CRITICAL"
        assert critical_violations[0].violation_id == "critical_001"
    
    def test_get_warning_violations(self):
        """测试获取警告违反记录"""
        violations = [
            InvariantViolation(
                invariant_type=InvariantType.CHIP_CONSERVATION,
                violation_id="critical_001",
                description="严重违反",
                severity="CRITICAL",
                timestamp=time.time(),
                context={}
            ),
            InvariantViolation(
                invariant_type=InvariantType.BETTING_RULES,
                violation_id="warning_001",
                description="警告违反",
                severity="WARNING",
                timestamp=time.time(),
                context={}
            )
        ]
        
        error = InvariantError("测试错误", violations)
        warning_violations = error.get_warning_violations()
        
        assert len(warning_violations) == 1
        assert warning_violations[0].severity == "WARNING"
        assert warning_violations[0].violation_id == "warning_001" 