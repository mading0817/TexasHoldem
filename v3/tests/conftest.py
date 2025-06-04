"""
V3 Test Configuration - pytest配置文件

该文件提供v3测试的基础设施，包括：
- 通用的测试fixture
- 反作弊检查配置
- 测试环境设置
- 性能测试配置

所有测试都会自动加载这些配置。
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import patch

# 添加v3模块到Python路径
v3_path = Path(__file__).parent.parent
if str(v3_path) not in sys.path:
    sys.path.insert(0, str(v3_path))

# 导入反作弊检查器
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker
from v3.tests.anti_cheat.state_consistency_checker import (
    StateConsistencyChecker, 
    GameStateSnapshot
)


@pytest.fixture(scope="session")
def anti_cheat_enabled():
    """反作弊检查启用标志"""
    return True


@pytest.fixture
def core_usage_checker():
    """核心使用检查器fixture"""
    return CoreUsageChecker()


@pytest.fixture
def state_consistency_checker():
    """状态一致性检查器fixture"""
    return StateConsistencyChecker()


@pytest.fixture
def sample_game_state():
    """示例游戏状态fixture"""
    return GameStateSnapshot(
        total_chips=10000,
        pot_size=0,
        player_chips={
            "player1": 5000,
            "player2": 3000,
            "player3": 2000
        },
        current_phase="PRE_FLOP",
        current_bet=0,
        active_players=["player1", "player2", "player3"]
    )


@pytest.fixture
def mock_detector():
    """Mock对象检测器fixture"""
    def _detect_mocks(*objects):
        """检测对象中是否包含mock"""
        for obj in objects:
            if hasattr(obj, '_mock_name') or hasattr(obj, 'call_count'):
                pytest.fail(f"检测到mock对象: {obj}, 测试必须使用真实对象")
    return _detect_mocks


@pytest.fixture(autouse=True)
def prevent_mock_usage(request):
    """自动防止mock使用的fixture"""
    # 只在标记为需要反作弊检查的测试中启用
    if request.node.get_closest_marker("anti_cheat"):
        # 禁用常见的mock模块
        mock_modules = ['unittest.mock', 'mock', 'pytest_mock']
        
        for module_name in mock_modules:
            if module_name in sys.modules:
                # 暂时移除mock模块（测试结束后恢复）
                original_module = sys.modules[module_name]
                del sys.modules[module_name]
                
                def restore_module():
                    sys.modules[module_name] = original_module
                
                request.addfinalizer(restore_module)


@pytest.fixture
def chip_conservation_tracker():
    """筹码守恒跟踪器fixture"""
    class ChipTracker:
        def __init__(self):
            self.snapshots = []
        
        def record_snapshot(self, snapshot: GameStateSnapshot):
            """记录状态快照"""
            self.snapshots.append(snapshot)
        
        def verify_conservation(self):
            """验证整个测试过程中的筹码守恒"""
            if len(self.snapshots) < 2:
                return
            
            initial_total = self.snapshots[0].total_chips
            for i, snapshot in enumerate(self.snapshots[1:], 1):
                assert snapshot.total_chips == initial_total, \
                    f"第{i}个快照筹码不守恒: 初始{initial_total}, 当前{snapshot.total_chips}"
    
    return ChipTracker()


@pytest.fixture
def performance_monitor():
    """性能监控器fixture"""
    import time
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.operations = []
        
        def start_timing(self):
            """开始计时"""
            self.start_time = time.perf_counter()
        
        def record_operation(self, operation_name: str):
            """记录操作"""
            if self.start_time is None:
                self.start_timing()
            
            current_time = time.perf_counter()
            duration = current_time - self.start_time
            self.operations.append((operation_name, duration))
            self.start_time = current_time
        
        def verify_performance(self, max_duration: float = 1.0):
            """验证性能要求"""
            total_duration = sum(duration for _, duration in self.operations)
            assert total_duration <= max_duration, \
                f"测试执行时间过长: {total_duration:.3f}s > {max_duration}s"
    
    return PerformanceMonitor()


# 测试标记定义
def pytest_configure(config):
    """pytest配置"""
    config.addinivalue_line(
        "markers", "anti_cheat: 标记需要反作弊检查的测试"
    )
    config.addinivalue_line(
        "markers", "property_test: 标记基于属性的测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记集成测试"
    )
    config.addinivalue_line(
        "markers", "performance: 标记性能测试"
    )


def pytest_runtest_setup(item):
    """测试运行前的设置"""
    # 为所有测试启用反作弊检查
    if not item.get_closest_marker("no_anti_cheat"):
        # 默认启用反作弊检查
        pass


def pytest_runtest_teardown(item, nextitem):
    """测试运行后的清理"""
    # 清理可能的状态污染
    pass


# 自定义断言帮助函数
def assert_real_object(obj, expected_type_name: str):
    """断言对象是真实的核心对象"""
    CoreUsageChecker.verify_real_objects(obj, expected_type_name)


def assert_chip_conservation(before: GameStateSnapshot, after: GameStateSnapshot):
    """断言筹码守恒"""
    StateConsistencyChecker.verify_chip_conservation(before, after)


def assert_valid_state_transition(before: GameStateSnapshot, after: GameStateSnapshot):
    """断言状态转换合法"""
    StateConsistencyChecker.verify_phase_transitions(before, after)


# 导出到pytest命名空间
pytest.assert_real_object = assert_real_object
pytest.assert_chip_conservation = assert_chip_conservation
pytest.assert_valid_state_transition = assert_valid_state_transition 