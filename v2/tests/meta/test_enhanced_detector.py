"""
增强版篡改检测器测试

测试增强版检测器的复杂篡改模式识别能力。
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import List

from v2.tests.meta.enhanced_tampering_detector import (
    EnhancedTamperingDetector,
    TamperingPattern
)
from v2.tests.meta.anti_cheat_supervisor import ViolationType


@pytest.mark.state_tamper
@pytest.mark.supervisor
@pytest.mark.critical
class TestEnhancedTamperingDetector:
    """测试增强版篡改检测器"""
    
    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.detector = EnhancedTamperingDetector(project_root=self.temp_dir)
    
    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_file(self, filename: str, content: str) -> str:
        """创建测试文件"""
        file_path = Path(self.temp_dir) / "v2" / "tests" / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(file_path)
    
    @pytest.mark.state_tamper
    @pytest.mark.fast
    def test_dict_access_tampering_detection(self):
        """测试字典访问篡改检测"""
        content = '''
def test_dict_tampering():
    game = GameController()
    # 这些都是字典访问篡改
    game.__dict__['_game_state'] = "hacked"
    vars(game)['_players'] = []
    obj.__dict__['_private_attr'] = "value"
'''
        
        self._create_test_file("test_dict_tampering.py", content)
        violations = self.detector.scan_test_files()
        
        # 应该检测到字典访问篡改
        dict_violations = [v for v in violations 
                          if "字典访问" in v.description]
        
        assert len(dict_violations) >= 2
        assert any("__dict__" in v.code_snippet for v in dict_violations)
        assert any("vars(" in v.code_snippet for v in dict_violations)
    
    @pytest.mark.state_tamper
    @pytest.mark.fast
    def test_loop_based_tampering_detection(self):
        """测试循环篡改检测"""
        content = '''
def test_loop_tampering():
    game = GameController()
    
    # 循环遍历修改私有属性
    for attr in game.__dict__:
        if attr.startswith('_'):
            game.__dict__[attr] = "hacked"
    
    # 使用vars()的循环篡改
    for key in vars(game):
        if key.startswith('_'):
            setattr(game, key, "modified")
'''
        
        self._create_test_file("test_loop_tampering.py", content)
        violations = self.detector.scan_test_files()
        
        # 应该检测到循环篡改
        loop_violations = [v for v in violations 
                          if "循环" in v.description]
        
        assert len(loop_violations) >= 1
        assert any("__dict__" in v.code_snippet for v in loop_violations)
    
    @pytest.mark.state_tamper
    @pytest.mark.fast
    def test_helper_cheat_patterns_detection(self):
        """测试测试帮凶模式检测"""
        content = '''
def create_hacked_game():
    """恶意工厂方法"""
    game = GameController()
    game._game_state = "HACKED_STATE"  # 这是帮凶行为
    return game

def setup_cheated_players():
    """恶意设置方法"""
    players = []
    for i in range(4):
        player = Player(f"Player{i}")
        player._chips = 9999  # 这也是帮凶行为
        players.append(player)
    return players

def get_private_state(obj):
    """提供私有状态访问"""
    return obj._private_data
'''
        
        self._create_test_file("test_helper_cheats.py", content)
        violations = self.detector.scan_test_files()
        
        # 应该检测到测试帮凶模式
        helper_violations = [v for v in violations 
                           if "帮凶" in v.description]
        
        assert len(helper_violations) >= 1
    
    @pytest.mark.state_tamper
    @pytest.mark.fast
    def test_dynamic_tampering_detection(self):
        """测试动态篡改检测"""
        content = '''
def test_dynamic_tampering():
    game = GameController()
    
    # 字符串构造属性名
    attr_name = "_game" + "_state"
    setattr(game, attr_name, "hacked")
    
    # 更简单的模式
    setattr(game, "_" + "dynamic", "value")
    getattr(game, "_" + "attr")
'''
        
        self._create_test_file("test_dynamic_tampering.py", content)
        violations = self.detector.scan_test_files()
        
        # 应该检测到动态篡改或setattr调用
        dynamic_violations = [v for v in violations 
                            if ("动态篡改" in v.description or 
                                "setattr" in v.code_snippet)]
        
        assert len(dynamic_violations) >= 1
    
    @pytest.mark.state_tamper
    @pytest.mark.fast
    def test_function_tampering_detection(self):
        """测试函数篡改检测"""
        content = '''
def test_function_tampering():
    game = GameController()
    
    # 使用setattr篡改私有状态
    setattr(game, "_game_state", "hacked")
    setattr(game, "_players", [])
    
    # 使用delattr删除私有属性
    delattr(game, "_deck")
    
    # 使用hasattr检查私有属性
    if hasattr(game, "_private_data"):
        print("Found private data")
'''
        
        self._create_test_file("test_function_tampering.py", content)
        violations = self.detector.scan_test_files()
        
        # 应该检测到函数篡改
        function_violations = [v for v in violations 
                             if ("setattr" in v.code_snippet or 
                                 "delattr" in v.code_snippet or
                                 "hasattr" in v.code_snippet)]
        
        assert len(function_violations) >= 3
    
    @pytest.mark.state_tamper
    @pytest.mark.fast
    def test_enhanced_report_generation(self):
        """测试增强版报告生成"""
        # 创建包含多种违规的测试文件
        content = '''
def test_multiple_violations():
    game = GameController()
    
    # 直接篡改
    game._game_state = "hacked"
    
    # 字典访问篡改
    game.__dict__['_players'] = []
    
    # 函数篡改
    setattr(game, "_deck", [])

def create_malicious_object():
    obj = TestObject()
    obj._private = "hacked"
    return obj
'''
        
        self._create_test_file("test_multiple_violations.py", content)
        violations = self.detector.scan_test_files()
        report = self.detector.generate_enhanced_report()
        
        # 检查增强版报告内容
        assert "增强版测试反作弊监督者报告" in report
        assert "违规模式统计" in report
        assert "增强版修复建议" in report
        
        if violations:
            assert "高严重程度违规" in report or "中等严重程度违规" in report
    
    def test_tampering_patterns_summary(self):
        """测试篡改模式摘要"""
        patterns = self.detector.get_tampering_patterns_summary()
        
        assert len(patterns) >= 6  # 至少6种篡改模式
        
        # 检查模式结构
        for pattern in patterns:
            assert "name" in pattern
            assert "description" in pattern
            assert "severity" in pattern
            assert "examples" in pattern
            assert isinstance(pattern["examples"], list)
    
    def test_violation_pattern_analysis(self):
        """测试违规模式分析"""
        # 创建包含不同类型违规的测试文件
        content = '''
def test_analysis():
    game = GameController()
    game._state = "hacked"  # 私有状态篡改
    setattr(game, "_data", "value")  # 危险操作
'''
        
        self._create_test_file("test_analysis.py", content)
        violations = self.detector.scan_test_files()
        stats = self.detector._analyze_violation_patterns()
        
        # 应该有统计信息
        assert isinstance(stats, dict)
        assert len(stats) > 0
        
        # 检查统计的准确性
        total_violations = sum(stats.values())
        assert total_violations == len(violations)
    
    def test_enhanced_vs_basic_detection(self):
        """测试增强版与基础版检测的差异"""
        # 创建只有增强版能检测到的复杂篡改
        content = '''
def test_complex_tampering():
    game = GameController()
    
    # 基础版能检测到的
    game._simple_state = "hacked"
    
    # 只有增强版能检测到的
    for attr in game.__dict__:
        if attr.startswith('_'):
            game.__dict__[attr] = "complex_hack"
    
    # 动态构造属性名
    attr_name = "_" + "dynamic" + "_state"
    setattr(game, attr_name, "value")
'''
        
        self._create_test_file("test_complex.py", content)
        
        # 使用增强版检测器
        enhanced_violations = self.detector.scan_test_files()
        
        # 使用基础版检测器
        from v2.tests.meta.anti_cheat_supervisor import AntiCheatSupervisor
        basic_detector = AntiCheatSupervisor(project_root=self.temp_dir)
        basic_violations = basic_detector.scan_test_files()
        
        # 增强版应该检测到更多违规
        assert len(enhanced_violations) >= len(basic_violations)
    
    def test_whitelist_respect_in_enhanced_detection(self):
        """测试增强版检测是否尊重白名单"""
        # 创建白名单文件
        content = '''
def create_test_game_state():
    """这是白名单中的方法"""
    game = GameController()
    game._game_state = "TEST_STATE"  # 应该被允许
    return game

def test_normal():
    state = create_test_game_state()
    assert state is not None
'''
        
        self._create_test_file("test_helpers.py", content)
        violations = self.detector.scan_test_files()
        
        # 白名单文件中的操作不应被检测为违规
        helper_violations = [v for v in violations 
                           if "test_helpers.py" in v.file_path]
        
        assert len(helper_violations) == 0
    
    def test_performance_of_enhanced_detection(self):
        """测试增强版检测的性能"""
        # 创建较大的测试文件
        content = '''
def test_performance():
    game = GameController()
    
    # 添加一些正常代码
    for i in range(100):
        player = Player(f"Player{i}")
        game.add_player(player)
    
    # 添加一些违规代码
    game._state = "hacked"
    setattr(game, "_data", "value")
    
    # 更多正常代码
    for j in range(50):
        game.process_action(Action.FOLD)
'''
        
        self._create_test_file("test_performance.py", content)
        
        import time
        start_time = time.time()
        
        violations = self.detector.scan_test_files()
        
        end_time = time.time()
        scan_time = end_time - start_time
        
        # 增强版扫描时间应该在合理范围内（小于3秒）
        assert scan_time < 3.0, f"增强版扫描时间过长: {scan_time:.2f}秒"
        
        # 应该检测到违规
        assert len(violations) > 0


class TestTamperingPattern:
    """测试篡改模式数据结构"""
    
    def test_tampering_pattern_creation(self):
        """测试篡改模式创建"""
        pattern = TamperingPattern(
            pattern_name="test_pattern",
            description="测试模式",
            detection_method="测试方法",
            severity="HIGH",
            examples=["example1", "example2"]
        )
        
        assert pattern.pattern_name == "test_pattern"
        assert pattern.description == "测试模式"
        assert pattern.detection_method == "测试方法"
        assert pattern.severity == "HIGH"
        assert len(pattern.examples) == 2


def test_enhanced_detector_command_line():
    """测试增强版检测器命令行接口"""
    from v2.tests.meta.enhanced_tampering_detector import main
    import sys
    from unittest.mock import patch
    
    # 测试显示篡改模式
    test_args = ['enhanced_tampering_detector.py', '--patterns']
    
    with patch.object(sys, 'argv', test_args):
        with patch('builtins.print') as mock_print:
            try:
                main()
            except SystemExit:
                pass  # 预期的退出
            
            # 验证打印了篡改模式信息
            if mock_print.call_args_list:
                print_calls = []
                for call in mock_print.call_args_list:
                    if call[0]:  # 检查是否有位置参数
                        print_calls.append(call[0][0])
                
                assert any("支持的篡改模式" in call for call in print_calls if isinstance(call, str))


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 