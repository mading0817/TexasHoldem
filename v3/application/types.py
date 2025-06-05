"""
Application Layer Types - 应用层类型定义

定义应用服务层使用的基础类型，包括命令结果、查询结果等。
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union, Generic, TypeVar
from enum import Enum, auto

T = TypeVar('T')


class ResultStatus(Enum):
    """操作结果状态"""
    SUCCESS = auto()
    FAILURE = auto()
    VALIDATION_ERROR = auto()
    BUSINESS_RULE_VIOLATION = auto()
    SYSTEM_ERROR = auto()


@dataclass(frozen=True)
class CommandResult:
    """命令执行结果"""
    success: bool
    status: ResultStatus
    message: str = ""
    error_code: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def success_result(cls, message: str = "操作成功", data: Optional[Dict[str, Any]] = None) -> 'CommandResult':
        """创建成功结果"""
        return cls(
            success=True,
            status=ResultStatus.SUCCESS,
            message=message,
            data=data
        )
    
    @classmethod
    def failure_result(cls, message: str, error_code: Optional[str] = None, 
                      status: ResultStatus = ResultStatus.FAILURE) -> 'CommandResult':
        """创建失败结果"""
        return cls(
            success=False,
            status=status,
            message=message,
            error_code=error_code
        )
    
    @classmethod
    def validation_error(cls, message: str, error_code: Optional[str] = None) -> 'CommandResult':
        """创建验证错误结果"""
        return cls.failure_result(message, error_code, ResultStatus.VALIDATION_ERROR)
    
    @classmethod
    def business_rule_violation(cls, message: str, error_code: Optional[str] = None) -> 'CommandResult':
        """创建业务规则违反结果"""
        return cls.failure_result(message, error_code, ResultStatus.BUSINESS_RULE_VIOLATION)


@dataclass(frozen=True)
class QueryResult(Generic[T]):
    """查询结果"""
    success: bool
    status: ResultStatus
    data: Optional[T] = None
    message: str = ""
    error_code: Optional[str] = None
    
    @classmethod
    def success_result(cls, data: T, message: str = "查询成功") -> 'QueryResult[T]':
        """创建成功结果"""
        return cls(
            success=True,
            status=ResultStatus.SUCCESS,
            data=data,
            message=message
        )
    
    @classmethod
    def failure_result(cls, message: str, error_code: Optional[str] = None,
                      status: ResultStatus = ResultStatus.FAILURE) -> 'QueryResult[T]':
        """创建失败结果"""
        return cls(
            success=False,
            status=status,
            message=message,
            error_code=error_code
        )
    
    @classmethod
    def business_rule_violation(cls, message: str, error_code: Optional[str] = None) -> 'QueryResult[T]':
        """创建业务规则违反结果"""
        return cls.failure_result(message, error_code, ResultStatus.BUSINESS_RULE_VIOLATION)


@dataclass(frozen=True)
class PlayerAction:
    """玩家行动"""
    action_type: str  # 'fold', 'call', 'raise', 'check', 'all_in'
    amount: int = 0
    player_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'action_type': self.action_type,
            'amount': self.amount,
            'player_id': self.player_id
        }


class ApplicationError(Exception):
    """应用层异常基类"""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ValidationError(ApplicationError):
    """验证错误"""
    pass


class BusinessRuleViolationError(ApplicationError):
    """业务规则违反错误"""
    pass


class SystemError(ApplicationError):
    """系统错误"""
    pass 