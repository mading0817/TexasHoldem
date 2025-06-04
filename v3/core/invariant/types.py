"""
不变量检查器类型定义

定义数学不变量检查相关的基础类型和枚举。
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import time

__all__ = [
    'InvariantType',
    'InvariantViolation',
    'InvariantCheckResult',
    'InvariantError'
]


class InvariantType(Enum):
    """不变量类型枚举"""
    CHIP_CONSERVATION = auto()      # 筹码守恒
    BETTING_RULES = auto()          # 下注规则
    PHASE_CONSISTENCY = auto()      # 阶段一致性
    POT_INTEGRITY = auto()          # 奖池完整性
    PLAYER_STATE = auto()           # 玩家状态一致性
    CARD_DISTRIBUTION = auto()      # 牌分发一致性


@dataclass(frozen=True)
class InvariantViolation:
    """不变量违反记录"""
    invariant_type: InvariantType
    violation_id: str
    description: str
    severity: str  # 'CRITICAL', 'WARNING', 'INFO'
    timestamp: float
    context: Dict[str, Any]
    
    def __post_init__(self):
        """验证违反记录的有效性"""
        if not self.violation_id:
            raise ValueError("violation_id不能为空")
        if not self.description:
            raise ValueError("description不能为空")
        if self.severity not in ['CRITICAL', 'WARNING', 'INFO']:
            raise ValueError("severity必须是CRITICAL、WARNING或INFO之一")
        if self.timestamp <= 0:
            raise ValueError("timestamp必须为正数")


@dataclass(frozen=True)
class InvariantCheckResult:
    """不变量检查结果"""
    invariant_type: InvariantType
    is_valid: bool
    violations: List[InvariantViolation]
    check_duration: float  # 检查耗时（秒）
    timestamp: float
    
    def __post_init__(self):
        """验证检查结果的有效性"""
        if self.check_duration < 0:
            raise ValueError("check_duration不能为负数")
        if self.timestamp <= 0:
            raise ValueError("timestamp必须为正数")
        if not self.is_valid and len(self.violations) == 0:
            raise ValueError("检查失败时必须提供违反记录")
    
    @classmethod
    def create_success(cls, invariant_type: InvariantType, check_duration: float) -> 'InvariantCheckResult':
        """创建成功的检查结果"""
        return cls(
            invariant_type=invariant_type,
            is_valid=True,
            violations=[],
            check_duration=check_duration,
            timestamp=time.time()
        )
    
    @classmethod
    def create_failure(cls, invariant_type: InvariantType, violations: List[InvariantViolation], 
                      check_duration: float) -> 'InvariantCheckResult':
        """创建失败的检查结果"""
        return cls(
            invariant_type=invariant_type,
            is_valid=False,
            violations=violations,
            check_duration=check_duration,
            timestamp=time.time()
        )


class InvariantError(Exception):
    """不变量错误异常"""
    
    def __init__(self, message: str, violations: List[InvariantViolation]):
        super().__init__(message)
        self.violations = violations
    
    def get_critical_violations(self) -> List[InvariantViolation]:
        """获取严重违反记录"""
        return [v for v in self.violations if v.severity == 'CRITICAL']
    
    def get_warning_violations(self) -> List[InvariantViolation]:
        """获取警告违反记录"""
        return [v for v in self.violations if v.severity == 'WARNING'] 