"""
Core Usage Checker - 核心模块使用检查器

该模块确保测试真正使用核心模块而非mock数据，是反作弊系统的核心组件。
所有测试都必须通过此检查器的验证。

Classes:
    CoreUsageChecker: 核心使用检查器
    
Functions:
    verify_real_objects: 验证对象是真实的核心对象
    verify_chip_conservation: 验证筹码守恒
    verify_module_boundaries: 验证模块边界
"""

from typing import Any, List, Dict, Type, Set, Optional
import inspect
import sys
import gc
import weakref
from dataclasses import dataclass


@dataclass
class AntiCheatReport:
    """反作弊检查报告"""
    passed: bool
    violations: List[str]
    warnings: List[str]
    object_count: int
    mock_objects_detected: int
    module_violations: int


class CoreUsageChecker:
    """核心模块使用检查器
    
    确保测试真正使用核心模块而非mock数据或绕过逻辑。
    这是v3反作弊系统的核心组件。
    """
    
    _verified_objects: Set[int] = set()
    _mock_detection_cache: Dict[str, bool] = {}
    
    @staticmethod
    def verify_real_objects(obj: Any, expected_type_name: str) -> None:
        """验证对象是真实的核心对象
        
        Args:
            obj: 要检查的对象
            expected_type_name: 期望的类型名称
            
        Raises:
            AssertionError: 如果对象不是期望的真实类型
        """
        # 基础类型检查
        actual_type_name = type(obj).__name__
        assert actual_type_name == expected_type_name, \
            f"必须使用真实的{expected_type_name}，当前类型: {actual_type_name}"
        
        # 增强的mock检测 - 7层检测机制
        assert not _is_mock_object_enhanced(obj), \
            f"禁止使用mock对象，必须使用真实的{expected_type_name}"
        
        # 模块来源验证
        module_name = obj.__class__.__module__
        assert module_name.startswith('v3.'), \
            f"对象必须来自v3模块，当前模块: {module_name}"
        
        # 对象实例验证
        _verify_object_instance(obj, expected_type_name)
        
        # 对象生命周期验证
        _verify_object_lifecycle(obj)
        
        # 记录已验证对象
        CoreUsageChecker._verified_objects.add(id(obj))
    
    @staticmethod
    def verify_chip_conservation(initial_total: int, final_total: int) -> None:
        """验证筹码守恒
        
        Args:
            initial_total: 初始筹码总量
            final_total: 最终筹码总量
            
        Raises:
            AssertionError: 如果筹码不守恒
        """
        assert isinstance(initial_total, int) and initial_total >= 0, \
            f"初始筹码必须是非负整数: {initial_total}"
        assert isinstance(final_total, int) and final_total >= 0, \
            f"最终筹码必须是非负整数: {final_total}"
        assert initial_total == final_total, \
            f"筹码必须守恒: 初始{initial_total}, 最终{final_total}, 差异{final_total - initial_total}"
    
    @staticmethod
    def verify_module_boundaries(obj: Any, allowed_modules: List[str]) -> None:
        """验证模块边界
        
        Args:
            obj: 要检查的对象
            allowed_modules: 允许的模块列表
            
        Raises:
            AssertionError: 如果对象来自不允许的模块
        """
        module_name = obj.__class__.__module__
        
        for allowed_module in allowed_modules:
            if module_name.startswith(allowed_module):
                return
        
        raise AssertionError(
            f"对象来自不允许的模块: {module_name}, "
            f"允许的模块: {allowed_modules}"
        )
    
    @staticmethod
    def verify_no_external_dependencies(module_name: str) -> None:
        """验证核心模块没有外部依赖
        
        Args:
            module_name: 要检查的模块名
            
        Raises:
            AssertionError: 如果核心模块有不允许的外部依赖
        """
        if not module_name.startswith('v3.core.'):
            return  # 只检查核心模块
        
        try:
            module = sys.modules[module_name]
        except KeyError:
            return  # 模块未加载
        
        # 获取模块的所有导入
        imports = _get_module_imports(module)
        
        # 检查是否有不允许的导入
        forbidden_imports = []
        for import_name in imports:
            if (import_name.startswith('v3.application.') or 
                import_name.startswith('v3.ui.') or
                import_name.startswith('v3.tests.')):
                forbidden_imports.append(import_name)
        
        assert not forbidden_imports, \
            f"核心模块 {module_name} 不能导入: {forbidden_imports}"
    
    @staticmethod
    def verify_test_isolation() -> None:
        """验证测试隔离性"""
        # 检查全局状态污染
        _check_global_state_pollution()
        
        # 检查内存泄漏
        _check_memory_leaks()
    
    @staticmethod
    def verify_object_lifecycle(obj: Any, expected_lifecycle: str) -> None:
        """验证对象生命周期
        
        Args:
            obj: 要检查的对象
            expected_lifecycle: 期望的生命周期状态
        """
        if expected_lifecycle == "active":
            assert obj is not None, "对象不应该为None"
            assert not _is_object_destroyed(obj), "对象不应该被销毁"
        elif expected_lifecycle == "destroyed":
            assert _is_object_destroyed(obj), "对象应该被销毁"
    
    @staticmethod
    def generate_anti_cheat_report() -> AntiCheatReport:
        """生成反作弊检查报告"""
        violations = []
        warnings = []
        mock_count = 0
        
        # 检查当前内存中的对象
        all_objects = gc.get_objects()
        for obj in all_objects:
            if _is_mock_object_enhanced(obj):
                mock_count += 1
                violations.append(f"检测到mock对象: {type(obj).__name__}")
        
        # 检查模块边界违反
        module_violations = _check_all_module_boundaries()
        
        return AntiCheatReport(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            object_count=len(all_objects),
            mock_objects_detected=mock_count,
            module_violations=module_violations
        )
    
    @staticmethod
    def clear_verification_cache() -> None:
        """清理验证缓存"""
        CoreUsageChecker._verified_objects.clear()
        CoreUsageChecker._mock_detection_cache.clear()


def _is_mock_object_enhanced(obj: Any) -> bool:
    """增强的mock对象检测 - 7层检测机制"""
    obj_id = str(id(obj))
    
    # 使用缓存提高性能
    if obj_id in CoreUsageChecker._mock_detection_cache:
        return CoreUsageChecker._mock_detection_cache[obj_id]
    
    # 反作弊模块白名单 - 这些类不应被视为mock对象
    anti_cheat_whitelist = [
        'ModuleUsageTracker', 'CoverageVerifier', 'StateConsistencyChecker',
        'CoreUsageChecker', 'AntiCheatReport'
    ]
    
    # 核心模块数据类白名单 - 这些核心模块的dataclass不应被视为mock对象
    core_dataclass_whitelist = [
        'ActionConstraints', 'CorePermissibleActionsData', 'GameContext',
        'GameEvent', 'BetAction', 'GameStateSnapshot', 'PhaseTransition',
        'CorePhaseLogicData'
    ]
    
    # Python内置类型白名单 - 这些类型不应被视为mock对象
    builtin_types_whitelist = [
        'type', 'module', 'ABCMeta', '_ProtocolMeta', 'GenericAlias',
        'DistFacade', 'MarkGenerator', '_Sentinel', '_SentinelObject',
        '_ANY', '_Call', 'settingsMeta', 'function', 'method',
        'builtin_function_or_method', 'wrapper_descriptor', 'method_descriptor',
        'classmethod', 'staticmethod', 'property', '_patch'
    ]
    
    obj_type_name = type(obj).__name__
    obj_module_name = type(obj).__module__
    
    # 如果是Python内置类型，直接返回False
    if obj_type_name in builtin_types_whitelist:
        CoreUsageChecker._mock_detection_cache[obj_id] = False
        return False
    
    # 如果是builtins模块的对象，直接返回False
    if obj_module_name == 'builtins':
        CoreUsageChecker._mock_detection_cache[obj_id] = False
        return False
    
    # 如果是反作弊模块的类，直接返回False
    if (obj_type_name in anti_cheat_whitelist and 
        'anti_cheat' in obj_module_name):
        CoreUsageChecker._mock_detection_cache[obj_id] = False
        return False
    
    # 如果是核心模块的dataclass，直接返回False
    if (obj_type_name in core_dataclass_whitelist and 
        obj_module_name.startswith('v3.core.')):
        CoreUsageChecker._mock_detection_cache[obj_id] = False
        return False
    
    is_mock = False
    
    # 检查常见的mock类型
    mock_indicators = [
        'Mock', 'MagicMock', 'AsyncMock', 'NonCallableMock',
        'mock', 'patch', 'spy', 'Stub', 'Fake', 'Double'
    ]
    
    # 1. 检查类型名称
    for indicator in mock_indicators:
        if indicator in obj_type_name:
            is_mock = True
            break
    
    # 2. 检查模块名称
    if not is_mock and 'mock' in obj_module_name.lower():
        is_mock = True
    
    # 3. 检查mock特有的属性
    if not is_mock:
        mock_attributes = [
            'call_count', 'call_args', 'return_value', 'side_effect',
            '_mock_name', '_mock_parent', '_mock_methods', '_spec_class'
        ]
        mock_attr_count = 0
        for attr in mock_attributes:
            if hasattr(obj, attr):
                mock_attr_count += 1
        
        # 如果有多个mock特有属性，很可能是mock对象
        if mock_attr_count >= 2:
            is_mock = True
    
    # 4. 检查是否是unittest.mock的实例
    if not is_mock:
        try:
            import unittest.mock
            if isinstance(obj, (unittest.mock.Mock, unittest.mock.MagicMock, 
                              unittest.mock.NonCallableMock, unittest.mock.AsyncMock)):
                is_mock = True
        except ImportError:
            pass
    
    # 5. 检查对象的字符串表示
    if not is_mock:
        obj_str = str(type(obj))
        if 'mock' in obj_str.lower() or 'fake' in obj_str.lower():
            is_mock = True
    
    # 6. 检查对象的MRO（方法解析顺序）
    if not is_mock:
        try:
            mro = type(obj).__mro__
            for cls in mro:
                if 'mock' in cls.__name__.lower():
                    is_mock = True
                    break
        except AttributeError:
            pass
    
    # 7. 检查对象的__dict__中是否有mock相关属性
    if not is_mock:
        try:
            obj_dict = getattr(obj, '__dict__', {})
            mock_keys = ['_mock_', '_call_', '_return_', '_side_effect']
            for key in obj_dict.keys():
                for mock_key in mock_keys:
                    if mock_key in str(key).lower():
                        is_mock = True
                        break
                if is_mock:
                    break
        except (AttributeError, TypeError):
            pass
    
    # 缓存结果
    CoreUsageChecker._mock_detection_cache[obj_id] = is_mock
    return is_mock


def _verify_object_instance(obj: Any, expected_type_name: str) -> None:
    """验证对象实例的完整性"""
    # 检查对象是否有必要的属性和方法
    if hasattr(obj, '__class__'):
        cls = obj.__class__
        
        # 检查类是否有正确的模块路径
        if hasattr(cls, '__module__'):
            module_path = cls.__module__
            assert module_path.startswith('v3.'), \
                f"类{expected_type_name}必须来自v3模块，当前: {module_path}"
    
    # 检查对象是否被正确初始化
    if hasattr(obj, '__init__'):
        # 确保__init__方法存在且可调用
        assert callable(obj.__init__), f"{expected_type_name}的__init__方法必须可调用"


def _verify_object_lifecycle(obj: Any) -> None:
    """验证对象生命周期"""
    # 检查对象是否处于有效状态
    try:
        # 尝试访问对象的基本属性
        _ = type(obj)
        _ = id(obj)
        _ = str(obj)
    except (ReferenceError, AttributeError) as e:
        raise AssertionError(f"对象生命周期验证失败: {e}")


def _check_global_state_pollution() -> None:
    """检查全局状态污染"""
    # 检查sys.modules中是否有异常的mock模块
    for module_name, module in sys.modules.items():
        if 'mock' in module_name.lower() and module_name.startswith('v3.'):
            raise AssertionError(f"检测到v3模块中的mock污染: {module_name}")


def _check_memory_leaks() -> None:
    """检查内存泄漏"""
    # 强制垃圾回收
    gc.collect()
    
    # 检查是否有过多的对象实例
    object_counts = {}
    for obj in gc.get_objects():
        obj_type = type(obj).__name__
        if obj_type.startswith(('GameState', 'Player', 'Card', 'Deck')):
            object_counts[obj_type] = object_counts.get(obj_type, 0) + 1
    
    # 警告：如果某种类型的对象过多
    for obj_type, count in object_counts.items():
        if count > 1000:  # 阈值可调整
            import warnings
            warnings.warn(f"检测到可能的内存泄漏: {obj_type} 对象数量 {count}")


def _is_object_destroyed(obj: Any) -> bool:
    """检查对象是否被销毁"""
    try:
        # 尝试访问对象的基本属性
        _ = type(obj)
        _ = id(obj)
        return False
    except (ReferenceError, AttributeError):
        return True


def _check_all_module_boundaries() -> int:
    """检查所有模块边界违反"""
    violations = 0
    
    for module_name, module in sys.modules.items():
        if module_name.startswith('v3.core.'):
            try:
                CoreUsageChecker.verify_no_external_dependencies(module_name)
            except AssertionError:
                violations += 1
    
    return violations


def _get_module_imports(module) -> List[str]:
    """获取模块的所有导入"""
    imports = []
    
    # 检查模块的全局变量
    for name, value in vars(module).items():
        if inspect.ismodule(value):
            imports.append(value.__name__)
        elif hasattr(value, '__module__'):
            imports.append(value.__module__)
    
    return list(set(imports))


__all__ = [
    'CoreUsageChecker',
    'AntiCheatReport',
] 