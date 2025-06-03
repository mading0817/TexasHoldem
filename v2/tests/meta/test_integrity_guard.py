"""
测试完整性守护测试

该模块测试反作弊监督者的各项功能，确保能正确检测测试作弊行为。
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import List

from v2.tests.meta.anti_cheat_supervisor import (
    AntiCheatSupervisor, 
    ViolationType, 
    Violation
)


@pytest.mark.supervisor
@pytest.mark.anti_cheat
@pytest.mark.critical
class TestAntiCheatSupervisor:
    """测试反作弊监督者功能"""
    
    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.supervisor = AntiCheatSupervisor(project_root=self.temp_dir)
    
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
    
    @pytest.mark.supervisor
    @pytest.mark.fast
    def test_detect_private_state_tampering(self):
        """测试检测私有状态篡改"""
        # 创建包含私有状态篡改的测试文件
        content = '''
def test_cheat_example():
    game = GameController()
    # 这是作弊行为：直接修改私有状态
    game._game_state = "INVALID_STATE"
    game._players[0].chips = 9999
    assert game.get_current_state() == "INVALID_STATE"
'''
        
        self._create_test_file("test_cheat_private.py", content)
        
        # 扫描并检查结果
        violations = self.supervisor.scan_test_files()
        
        # 应该检测到私有状态篡改
        private_violations = [v for v in violations 
                            if v.violation_type == ViolationType.PRIVATE_STATE_TAMPERING]
        
        assert len(private_violations) >= 1
        assert any("_game_state" in v.description for v in private_violations)
    
    @pytest.mark.supervisor
    @pytest.mark.fast
    def test_detect_dangerous_operations(self):
        """测试检测危险操作"""
        content = '''
def test_dangerous_operations():
    # 这些都是危险操作
    setattr(game, "_private_attr", "hacked")
    exec("game._deck = []")
    eval("game._pot = 0")
    
    # 使用__new__绕过构造函数
    obj = object.__new__(GameState)
'''
        
        self._create_test_file("test_dangerous.py", content)
        
        violations = self.supervisor.scan_test_files()
        
        # 应该检测到危险操作
        dangerous_violations = [v for v in violations 
                              if v.violation_type == ViolationType.DANGEROUS_OPERATION]
        
        assert len(dangerous_violations) >= 3
        assert any("setattr" in v.description for v in dangerous_violations)
        assert any("exec" in v.description for v in dangerous_violations)
        assert any("eval" in v.description for v in dangerous_violations)
    
    @pytest.mark.supervisor
    @pytest.mark.fast
    def test_detect_api_boundary_violation(self):
        """测试检测API边界违规"""
        # 创建UI测试文件（路径包含ui）
        content = '''
# UI测试不应直接导入core模块
from v2.core.game_state import GameState
import v2.core.deck
from v2.core import Card

def test_ui_functionality():
    # 这违反了API边界
    state = GameState()
    assert state is not None
'''
        
        self._create_test_file("ui/test_streamlit_ui.py", content)
        
        violations = self.supervisor.scan_test_files()
        
        # 应该检测到API边界违规
        boundary_violations = [v for v in violations 
                             if v.violation_type == ViolationType.API_BOUNDARY_VIOLATION]
        
        assert len(boundary_violations) >= 1
        assert any("core" in v.description for v in boundary_violations)
    
    @pytest.mark.supervisor
    @pytest.mark.fast
    def test_whitelist_functionality(self):
        """测试白名单功能"""
        # 创建白名单文件
        content = '''
def create_test_game_state():
    """这是白名单中的测试辅助方法"""
    game = GameController()
    game._game_state = "TEST_STATE"  # 这应该被允许
    return game

def test_normal_operation():
    state = create_test_game_state()
    assert state is not None
'''
        
        self._create_test_file("test_helpers.py", content)
        
        violations = self.supervisor.scan_test_files()
        
        # 白名单文件中的操作不应被检测为违规
        helper_violations = [v for v in violations 
                           if "test_helpers.py" in v.file_path]
        
        assert len(helper_violations) == 0
    
    @pytest.mark.supervisor
    @pytest.mark.fast
    def test_clean_test_file(self):
        """测试干净的测试文件"""
        content = '''
import pytest
from v2.controller.poker_controller import PokerController

def test_proper_testing():
    """正确的测试方式"""
    controller = PokerController()
    
    # 使用公共API
    result = controller.start_new_game()
    assert result.success
    
    # 通过公共方法获取状态
    state = controller.get_game_state()
    assert state is not None
'''
        
        self._create_test_file("test_clean.py", content)
        
        violations = self.supervisor.scan_test_files()
        
        # 干净的测试文件不应有违规
        clean_violations = [v for v in violations 
                          if "test_clean.py" in v.file_path]
        
        assert len(clean_violations) == 0
    
    @pytest.mark.supervisor
    @pytest.mark.fast
    def test_report_generation(self):
        """测试报告生成"""
        # 创建包含违规的测试文件
        content = '''
def test_with_violations():
    game._private_state = "hacked"
    setattr(game, "_another_private", "value")
'''
        
        self._create_test_file("test_violations.py", content)
        
        violations = self.supervisor.scan_test_files()
        report = self.supervisor.generate_report()
        
        # 检查报告内容
        assert "测试反作弊监督者报告" in report
        assert "发现违规" in report
        
        if violations:
            assert "高严重程度违规" in report or "中等严重程度违规" in report
            assert "修复建议" in report
    
    @pytest.mark.supervisor
    @pytest.mark.fast
    def test_no_violations_report(self):
        """测试无违规时的报告"""
        # 创建干净的测试文件
        content = '''
import pytest

def test_clean_operation():
    assert True
'''
        
        self._create_test_file("test_no_violations.py", content)
        
        violations = self.supervisor.scan_test_files()
        report = self.supervisor.generate_report()
        
        # 无违规时应该显示恭喜信息
        assert "恭喜！未发现任何测试作弊行为！" in report
    
    def test_file_filtering(self):
        """测试文件过滤功能"""
        # 创建不应被扫描的文件
        init_content = '''# __init__.py should be skipped'''
        self._create_test_file("__init__.py", init_content)
        
        # 创建监督者自身文件（应被跳过）
        supervisor_content = '''# anti_cheat files should be skipped'''
        self._create_test_file("test_anti_cheat_something.py", supervisor_content)
        
        # 创建非测试文件
        non_test_content = '''# non-test files should be skipped'''
        self._create_test_file("helper_module.py", non_test_content)
        
        violations = self.supervisor.scan_test_files()
        
        # 这些文件不应被扫描，所以不应有来自它们的违规
        init_violations = [v for v in violations if "__init__.py" in v.file_path]
        supervisor_violations = [v for v in violations if "anti_cheat" in v.file_path]
        non_test_violations = [v for v in violations if "helper_module.py" in v.file_path]
        
        assert len(init_violations) == 0
        assert len(supervisor_violations) == 0
        assert len(non_test_violations) == 0
    
    def test_violation_severity_classification(self):
        """测试违规严重程度分类"""
        content = '''
def test_severity_levels():
    # 高严重程度：直接篡改私有状态
    game._game_state = "hacked"
    
    # 高严重程度：危险操作
    exec("malicious_code")
    
    # 中等严重程度：可能的问题（通过解析错误模拟）
'''
        
        self._create_test_file("test_severity.py", content)
        
        violations = self.supervisor.scan_test_files()
        
        # 检查严重程度分类
        high_violations = [v for v in violations if v.severity == "HIGH"]
        medium_violations = [v for v in violations if v.severity == "MEDIUM"]
        
        assert len(high_violations) >= 1  # 应该有高严重程度违规
    
    def test_code_snippet_extraction(self):
        """测试代码片段提取"""
        content = '''
def test_code_snippet():
    game._private_attr = "test"  # 这行应该被提取
'''
        
        self._create_test_file("test_snippet.py", content)
        
        violations = self.supervisor.scan_test_files()
        
        # 检查代码片段是否正确提取
        if violations:
            violation = violations[0]
            assert violation.code_snippet
            assert "game._private_attr" in violation.code_snippet


class TestIntegrationWithExistingTests:
    """测试与现有测试的集成"""
    
    def test_scan_existing_test_directory(self):
        """测试扫描现有的测试目录"""
        supervisor = AntiCheatSupervisor()
        
        # 扫描实际的测试目录
        violations = supervisor.scan_test_files("v2/tests")
        
        # 现有的测试应该是干净的（没有作弊行为）
        high_violations = [v for v in violations if v.severity == "HIGH"]
        
        # 如果发现高严重程度违规，打印详细信息用于调试
        if high_violations:
            report = supervisor.generate_report()
            print(f"\n发现违规行为:\n{report}")
        
        # 现有测试应该通过反作弊检查
        assert len(high_violations) == 0, f"现有测试中发现{len(high_violations)}个高严重程度违规"
    
    def test_performance_on_large_codebase(self):
        """测试在大型代码库上的性能"""
        supervisor = AntiCheatSupervisor()
        
        import time
        start_time = time.time()
        
        violations = supervisor.scan_test_files("v2/tests")
        
        end_time = time.time()
        scan_time = end_time - start_time
        
        # 扫描时间应该在合理范围内（小于5秒）
        assert scan_time < 5.0, f"扫描时间过长: {scan_time:.2f}秒"
        
        # 生成报告也应该很快
        start_time = time.time()
        report = supervisor.generate_report()
        end_time = time.time()
        report_time = end_time - start_time
        
        assert report_time < 1.0, f"报告生成时间过长: {report_time:.2f}秒"


def test_command_line_interface():
    """测试命令行接口"""
    # 这个测试验证main函数的基本功能
    # 实际的CLI测试需要在集成测试中进行
    
    from v2.tests.meta.anti_cheat_supervisor import main
    import sys
    from unittest.mock import patch
    
    # 模拟命令行参数
    test_args = ['anti_cheat_supervisor.py', '--project-root', '.']
    
    with patch.object(sys, 'argv', test_args):
        with patch('sys.exit') as mock_exit:
            try:
                main()
            except SystemExit:
                pass  # 预期的退出
            
            # 验证退出码调用
            mock_exit.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])