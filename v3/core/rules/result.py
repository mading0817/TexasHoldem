"""
定义通用的操作结果对象
"""
from dataclasses import dataclass
from typing import Any, Optional, TypeVar, Generic

T = TypeVar('T')

@dataclass
class OperationResult(Generic[T]):
    """
    一个通用的操作结果类，用于封装服务或函数调用的返回信息。

    Attributes:
        success (bool): 表示操作是否成功。
        data (Optional[T]): 操作成功时返回的数据。
        message (Optional[str]): 操作失败时提供的可读错误信息。
        error_code (Optional[str]): 机器可读的错误代码。
    """
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    error_code: Optional[str] = None

    @staticmethod
    def success_result(data: Optional[T] = None, message: Optional[str] = None) -> 'OperationResult[T]':
        """创建一个表示成功的实例"""
        return OperationResult(success=True, data=data, message=message)

    @staticmethod
    def failure_result(message: str, error_code: Optional[str] = None, data: Optional[T] = None) -> 'OperationResult[T]':
        """创建一个表示失败的实例"""
        return OperationResult(success=False, data=data, message=message, error_code=error_code)

    def is_successful(self) -> bool:
        """检查操作是否成功"""
        return self.success 