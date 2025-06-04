"""
Module Usage Tracker - 模块使用跟踪器

该模块跟踪测试是否真正使用了核心模块，防止测试绕过真实业务逻辑。
确保所有测试都真正执行核心代码路径。

Classes:
    ModuleUsageTracker: 模块使用跟踪器
"""

import sys
import inspect
import functools
import time
from typing import List, Dict, Any, Callable, Set
from dataclasses import dataclass
from unittest.mock import Mock, MagicMock


@dataclass
class ModuleCallInfo:
    """模块调用信息"""
    module_name: str
    function_name: str
    timestamp: float
    call_count: int = 1


class ModuleUsageTracker:
    """模块使用跟踪器
    
    跟踪测试是否真正使用了核心模块，防止测试绕过真实业务逻辑。
    """
    
    def __init__(self):
        """初始化跟踪器"""
        self._tracked_modules: List[str] = []
        self._call_info: Dict[str, ModuleCallInfo] = {}
        self._total_calls: int = 0
        self._core_module_calls: int = 0
        self._tracking_enabled: bool = False
    
    def track_core_module_calls(self, func: Callable) -> Callable:
        """装饰器：跟踪核心模块调用
        
        Args:
            func: 要跟踪的函数
            
        Returns:
            装饰后的函数
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 启用跟踪
            self._tracking_enabled = True
            
            # 记录调用前的状态
            initial_frame = inspect.currentframe()
            
            try:
                # 执行原函数
                result = func(*args, **kwargs)
                
                # 分析调用栈，记录模块使用
                self._analyze_call_stack(initial_frame)
                
                # 分析返回结果中的对象
                self._analyze_result_objects(result)
                
                return result
            finally:
                self._tracking_enabled = False
                
        return wrapper
    
    def verify_real_objects_used(self, objects: List[Any]) -> None:
        """验证使用的是真实对象而非mock
        
        Args:
            objects: 要验证的对象列表
            
        Raises:
            AssertionError: 如果检测到mock对象或None值
        """
        for obj in objects:
            # 检查None值
            if obj is None:
                raise AssertionError("对象列表中不能包含None值")
            
            if self._is_mock_object(obj):
                raise AssertionError(
                    f"检测到mock对象: {type(obj).__name__}，必须使用真实对象"
                )
            
            # 验证对象来源模块
            if hasattr(obj, '__class__'):
                module_name = obj.__class__.__module__
                if module_name and module_name.startswith('v3.core.'):
                    self._record_core_module_usage(module_name)
    
    def get_tracked_modules(self) -> List[str]:
        """获取已跟踪的模块列表
        
        Returns:
            模块名称列表
        """
        return list(self._tracked_modules)
    
    def get_call_count(self) -> int:
        """获取总调用次数
        
        Returns:
            总调用次数
        """
        return self._total_calls
    
    def get_module_usage_stats(self) -> Dict[str, Any]:
        """获取模块使用统计
        
        Returns:
            统计信息字典
        """
        total_modules = len(self._tracked_modules)
        core_modules = len([m for m in self._tracked_modules if m.startswith('v3.core.')])
        
        core_percentage = (
            (core_modules / total_modules) if total_modules > 0 else 0.0
        )
        
        return {
            "total_calls": self._total_calls,
            "modules_used": self._tracked_modules.copy(),
            "core_modules_count": core_modules,
            "total_modules_count": total_modules,
            "core_modules_percentage": core_percentage,
            "call_details": dict(self._call_info)
        }
    
    def reset_tracking(self) -> None:
        """重置跟踪数据"""
        self._tracked_modules.clear()
        self._call_info.clear()
        self._total_calls = 0
        self._core_module_calls = 0
        self._tracking_enabled = False
    
    def verify_core_module_usage_percentage(self, min_percentage: float) -> None:
        """验证核心模块使用百分比
        
        Args:
            min_percentage: 最小百分比要求
            
        Raises:
            AssertionError: 如果核心模块使用百分比不足或参数无效
        """
        # 验证参数有效性
        if min_percentage < 0.0 or min_percentage > 1.0:
            raise AssertionError(
                f"百分比要求必须在0.0-1.0之间: {min_percentage}"
            )
        
        stats = self.get_module_usage_stats()
        actual_percentage = stats["core_modules_percentage"]
        
        if actual_percentage < min_percentage:
            raise AssertionError(
                f"核心模块使用百分比不足: 实际{actual_percentage:.2%}, "
                f"要求{min_percentage:.2%}"
            )
    
    def _analyze_call_stack(self, initial_frame) -> None:
        """分析调用栈，记录模块使用"""
        frame = initial_frame
        
        while frame:
            try:
                # 获取模块信息
                module = inspect.getmodule(frame)
                if module and hasattr(module, '__name__'):
                    module_name = module.__name__
                    
                    # 记录模块使用
                    if module_name not in self._tracked_modules:
                        self._tracked_modules.append(module_name)
                    
                    # 记录调用信息
                    function_name = frame.f_code.co_name
                    call_key = f"{module_name}.{function_name}"
                    
                    if call_key in self._call_info:
                        self._call_info[call_key].call_count += 1
                    else:
                        self._call_info[call_key] = ModuleCallInfo(
                            module_name=module_name,
                            function_name=function_name,
                            timestamp=time.time()
                        )
                    
                    self._total_calls += 1
                    
                    # 统计核心模块调用
                    if module_name.startswith('v3.core.'):
                        self._core_module_calls += 1
                
                frame = frame.f_back
                
            except Exception:
                # 忽略分析错误，继续处理下一帧
                frame = frame.f_back if frame else None
    
    def _analyze_result_objects(self, result: Any) -> None:
        """分析返回结果中的对象"""
        if result is None:
            return
        
        # 分析单个对象
        if hasattr(result, '__class__'):
            module_name = result.__class__.__module__
            if module_name and module_name.startswith('v3.'):
                self._record_module_usage(module_name)
        
        # 分析容器对象
        if isinstance(result, (list, tuple)):
            for item in result:
                self._analyze_result_objects(item)
        elif isinstance(result, dict):
            for value in result.values():
                self._analyze_result_objects(value)
    
    def _record_module_usage(self, module_name: str) -> None:
        """记录模块使用"""
        if module_name not in self._tracked_modules:
            self._tracked_modules.append(module_name)
    
    def _record_core_module_usage(self, module_name: str) -> None:
        """记录核心模块使用"""
        self._record_module_usage(module_name)
        if module_name.startswith('v3.core.'):
            self._core_module_calls += 1
    
    def _is_mock_object(self, obj: Any) -> bool:
        """检查对象是否为mock对象
        
        Args:
            obj: 要检查的对象
            
        Returns:
            如果是mock对象返回True
        """
        # 检查常见的mock类型
        if isinstance(obj, (Mock, MagicMock)):
            return True
        
        # 检查类名
        class_name = type(obj).__name__
        mock_indicators = ['Mock', 'MagicMock', 'NonCallableMock', 'AsyncMock']
        if any(indicator in class_name for indicator in mock_indicators):
            return True
        
        # 检查模块来源
        module_name = type(obj).__module__
        if module_name and 'mock' in module_name.lower():
            return True
        
        # 检查特殊属性（mock对象的特征）
        mock_attributes = ['_mock_name', '_mock_return_value', '_mock_side_effect']
        if any(hasattr(obj, attr) for attr in mock_attributes):
            return True
        
        return False 