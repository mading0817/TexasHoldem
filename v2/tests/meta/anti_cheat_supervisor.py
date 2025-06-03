"""
反作弊监督者核心模块

该模块负责检测和防范测试代码中的作弊行为，包括：
1. 直接篡改核心模块私有状态
2. 绕过构造函数的危险操作
3. API边界违规（如UI测试直接导入core模块）
4. 其他违反测试完整性的行为
"""

import ast
import os
import re
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ViolationType(Enum):
    """违规类型枚举"""
    PRIVATE_STATE_TAMPERING = "private_state_tampering"
    CONSTRUCTOR_BYPASS = "constructor_bypass"
    API_BOUNDARY_VIOLATION = "api_boundary_violation"
    DANGEROUS_OPERATION = "dangerous_operation"


@dataclass
class Violation:
    """违规记录"""
    violation_type: ViolationType
    file_path: str
    line_number: int
    column_number: int
    description: str
    code_snippet: str
    severity: str = "HIGH"  # HIGH, MEDIUM, LOW


class AntiCheatSupervisor:
    """
    反作弊监督者
    
    负责扫描测试文件，检测各种作弊行为并生成违规报告。
    """
    
    def __init__(self, project_root: str = None, config_file: str = None):
        """
        初始化反作弊监督者
        
        Args:
            project_root: 项目根目录路径
            config_file: 配置文件路径
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.violations: List[Violation] = []
        
        # 加载配置
        if config_file is None:
            config_file = self.project_root / "v2" / "tests" / "meta" / "supervisor_config.yaml"
        
        self.config = self._load_config(config_file)
        
        # 从配置中加载规则
        self.private_patterns = set(self.config.get('private_patterns', []))
        self.dangerous_operations = set(self.config.get('dangerous_operations', []))
        self.api_boundary_rules = self.config.get('api_boundary_rules', {})
        self.whitelist = self.config.get('whitelist', {})
    
    def _load_config(self, config_file: Path) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            配置字典
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"警告：无法加载配置文件 {config_file}: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'private_patterns': [
                '_game_state', '_players', '_deck', '_pot', '_current_player',
                '_dealer_position', '_small_blind', '_big_blind', '_community_cards'
            ],
            'dangerous_operations': [
                '__new__', '__setattr__', '__dict__', 'setattr', 'delattr',
                'exec', 'eval', 'globals', 'locals', 'vars'
            ],
            'api_boundary_rules': {
                'ui_tests': {
                    'forbidden_imports': [
                        r'v2\.core\.',
                        r'from v2\.core',
                        r'import.*v2\.core'
                    ]
                }
            },
            'whitelist': {
                'allowed_files': [
                    'test_helpers.py', 'conftest.py', 'fixtures.py',
                    'test_ai_fairness_monitor.py', 'test_streamlit_app.py'
                ],
                'special_cases': {
                    'ai_fairness_tests': ['setattr', '_private_data', 'unknown_attribute'],
                    'ui_tests': ['v2.core.state', 'v2.core.enums', 'v2.core.cards']
                }
            }
        }
    
    def scan_test_files(self, test_directory: str = None) -> List[Violation]:
        """
        扫描测试文件，检测违规行为
        
        Args:
            test_directory: 测试目录路径，默认为v2/tests
            
        Returns:
            违规记录列表
        """
        if test_directory is None:
            test_directory = self.project_root / "v2" / "tests"
        else:
            test_directory = Path(test_directory)
        
        self.violations.clear()
        
        # 递归扫描所有Python测试文件
        for py_file in test_directory.rglob("*.py"):
            if self._should_scan_file(py_file):
                self._scan_file(py_file)
        
        return self.violations
    
    def _should_scan_file(self, file_path: Path) -> bool:
        """
        判断是否应该扫描该文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否应该扫描
        """
        # 跳过__init__.py和非测试文件
        if file_path.name == "__init__.py":
            return False
        
        # 跳过监督者自身
        if "anti_cheat" in file_path.name.lower():
            return False
        
        # 只扫描测试文件
        return (file_path.name.startswith("test_") or 
                file_path.name.endswith("_test.py") or
                "test" in file_path.parts)
    
    def _scan_file(self, file_path: Path):
        """
        扫描单个文件
        
        Args:
            file_path: 文件路径
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析AST
            tree = ast.parse(content, filename=str(file_path))
            
            # 创建访问者并遍历AST
            visitor = CheatDetectionVisitor(
                file_path=str(file_path),
                content_lines=content.splitlines(),
                supervisor=self
            )
            visitor.visit(tree)
            
        except Exception as e:
            # 记录解析错误但不中断扫描
            violation = Violation(
                violation_type=ViolationType.DANGEROUS_OPERATION,
                file_path=str(file_path),
                line_number=1,
                column_number=1,
                description=f"文件解析错误: {str(e)}",
                code_snippet="",
                severity="MEDIUM"
            )
            self.violations.append(violation)
    
    def _is_ui_test_file(self, file_path: str) -> bool:
        """
        判断是否为UI测试文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为UI测试文件
        """
        return ("ui" in file_path.lower() or 
                "streamlit" in file_path.lower() or
                "cli" in file_path.lower())
    
    def _is_whitelisted_operation(self, file_path: str, operation: str) -> bool:
        """
        检查操作是否在白名单中
        
        Args:
            file_path: 文件路径
            operation: 操作名称
            
        Returns:
            是否在白名单中
        """
        file_name = Path(file_path).name
        
        # 检查文件白名单
        if file_name in self.whitelist.get('allowed_files', []):
            return True
        
        # 检查特殊情况白名单
        special_cases = self.whitelist.get('special_cases', {})
        
        # 测试框架常用操作
        test_framework_ops = special_cases.get('test_framework_operations', [])
        if operation in test_framework_ops:
            return True
        
        # AI公平性测试的特殊权限
        if 'ai_fairness' in file_name.lower() or 'fairness_monitor' in file_name.lower():
            ai_fairness_whitelist = special_cases.get('ai_fairness_tests', [])
            if operation in ai_fairness_whitelist:
                return True
        
        # UI测试的特殊权限
        if self._is_ui_test_file(file_path):
            ui_whitelist = special_cases.get('ui_tests', [])
            if any(pattern in operation for pattern in ui_whitelist):
                return True
        
        # 检查测试辅助方法白名单
        test_helper_methods = self.whitelist.get('test_helper_methods', [])
        if operation in test_helper_methods:
            return True
        
        return False
    
    def generate_report(self, output_file: str = None) -> str:
        """
        生成违规报告
        
        Args:
            output_file: 输出文件路径，如果为None则返回字符串
            
        Returns:
            报告内容
        """
        if not self.violations:
            report = "🎉 恭喜！未发现任何测试作弊行为！\n"
        else:
            report = self._generate_detailed_report()
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report
    
    def _generate_detailed_report(self) -> str:
        """生成详细的违规报告"""
        report_lines = [
            "🚨 测试反作弊监督者报告",
            "=" * 50,
            f"扫描时间: {self._get_current_time()}",
            f"发现违规: {len(self.violations)} 个",
            ""
        ]
        
        # 按严重程度分组
        high_violations = [v for v in self.violations if v.severity == "HIGH"]
        medium_violations = [v for v in self.violations if v.severity == "MEDIUM"]
        low_violations = [v for v in self.violations if v.severity == "LOW"]
        
        if high_violations:
            report_lines.extend([
                "🔴 高严重程度违规:",
                "-" * 30
            ])
            for violation in high_violations:
                report_lines.extend(self._format_violation(violation))
            report_lines.append("")
        
        if medium_violations:
            report_lines.extend([
                "🟡 中等严重程度违规:",
                "-" * 30
            ])
            for violation in medium_violations:
                report_lines.extend(self._format_violation(violation))
            report_lines.append("")
        
        if low_violations:
            report_lines.extend([
                "🟢 低严重程度违规:",
                "-" * 30
            ])
            for violation in low_violations:
                report_lines.extend(self._format_violation(violation))
            report_lines.append("")
        
        # 添加修复建议
        report_lines.extend([
            "💡 修复建议:",
            "-" * 30,
            "1. 移除所有直接修改私有状态的代码",
            "2. 使用公共API进行测试",
            "3. 遵守API边界约束",
            "4. 避免使用危险的反射操作",
            ""
        ])
        
        return "\n".join(report_lines)
    
    def _format_violation(self, violation: Violation) -> List[str]:
        """格式化单个违规记录"""
        return [
            f"📍 {violation.violation_type.value}",
            f"   文件: {violation.file_path}",
            f"   位置: 第{violation.line_number}行, 第{violation.column_number}列",
            f"   描述: {violation.description}",
            f"   代码: {violation.code_snippet}",
            ""
        ]
    
    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class CheatDetectionVisitor(ast.NodeVisitor):
    """
    AST访问者，用于检测作弊行为
    """
    
    def __init__(self, file_path: str, content_lines: List[str], supervisor: AntiCheatSupervisor):
        self.file_path = file_path
        self.content_lines = content_lines
        self.supervisor = supervisor
    
    def visit_Assign(self, node: ast.Assign):
        """检测赋值操作"""
        for target in node.targets:
            if isinstance(target, ast.Attribute):
                self._check_private_attribute_assignment(target, node)
        
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """检测函数调用"""
        if isinstance(node.func, ast.Name):
            self._check_dangerous_function_call(node)
        elif isinstance(node.func, ast.Attribute):
            self._check_dangerous_method_call(node)
        
        self.generic_visit(node)
    
    def visit_Import(self, node: ast.Import):
        """检测import语句"""
        for alias in node.names:
            self._check_api_boundary_violation(alias.name, node)
        
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """检测from...import语句"""
        if node.module:
            self._check_api_boundary_violation(node.module, node)
        
        self.generic_visit(node)
    
    def _check_private_attribute_assignment(self, target: ast.Attribute, node: ast.Assign):
        """检查私有属性赋值"""
        attr_name = target.attr
        
        # 检查是否为受保护的私有属性
        for pattern in self.supervisor.private_patterns:
            if re.match(pattern, attr_name):
                # 检查是否在白名单中
                if not self._is_whitelisted_operation(attr_name):
                    violation = Violation(
                        violation_type=ViolationType.PRIVATE_STATE_TAMPERING,
                        file_path=self.file_path,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        description=f"直接修改私有属性: {attr_name}",
                        code_snippet=self._get_code_snippet(node.lineno),
                        severity="HIGH"
                    )
                    self.supervisor.violations.append(violation)
    
    def _check_dangerous_function_call(self, node: ast.Call):
        """检查危险函数调用"""
        func_name = node.func.id
        
        if func_name in self.supervisor.dangerous_operations:
            if not self._is_whitelisted_operation(func_name):
                violation = Violation(
                    violation_type=ViolationType.DANGEROUS_OPERATION,
                    file_path=self.file_path,
                    line_number=node.lineno,
                    column_number=node.col_offset,
                    description=f"使用危险操作: {func_name}",
                    code_snippet=self._get_code_snippet(node.lineno),
                    severity="HIGH"
                )
                self.supervisor.violations.append(violation)
    
    def _check_dangerous_method_call(self, node: ast.Call):
        """检查危险方法调用"""
        if hasattr(node.func, 'attr'):
            method_name = node.func.attr
            
            if method_name in self.supervisor.dangerous_operations:
                if not self._is_whitelisted_operation(method_name):
                    violation = Violation(
                        violation_type=ViolationType.DANGEROUS_OPERATION,
                        file_path=self.file_path,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        description=f"使用危险方法: {method_name}",
                        code_snippet=self._get_code_snippet(node.lineno),
                        severity="HIGH"
                    )
                    self.supervisor.violations.append(violation)
    
    def _check_api_boundary_violation(self, module_name: str, node):
        """检查API边界违规"""
        if self.supervisor._is_ui_test_file(self.file_path):
            # UI测试文件不应直接导入core模块
            forbidden_patterns = self.supervisor.api_boundary_rules['ui_tests']['forbidden_imports']
            
            for pattern in forbidden_patterns:
                if re.search(pattern, module_name):
                    violation = Violation(
                        violation_type=ViolationType.API_BOUNDARY_VIOLATION,
                        file_path=self.file_path,
                        line_number=node.lineno,
                        column_number=node.col_offset,
                        description=f"UI测试违规导入core模块: {module_name}",
                        code_snippet=self._get_code_snippet(node.lineno),
                        severity="HIGH"
                    )
                    self.supervisor.violations.append(violation)
    
    def _is_whitelisted_operation(self, operation: str) -> bool:
        """检查操作是否在白名单中"""
        return self.supervisor._is_whitelisted_operation(self.file_path, operation)
    
    def _get_code_snippet(self, line_number: int) -> str:
        """获取代码片段"""
        if 1 <= line_number <= len(self.content_lines):
            return self.content_lines[line_number - 1].strip()
        return ""


def main():
    """主函数，用于命令行执行"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试反作弊监督者")
    parser.add_argument("--test-dir", help="测试目录路径")
    parser.add_argument("--output", help="输出报告文件路径")
    parser.add_argument("--project-root", help="项目根目录路径")
    
    args = parser.parse_args()
    
    supervisor = AntiCheatSupervisor(project_root=args.project_root)
    violations = supervisor.scan_test_files(test_directory=args.test_dir)
    
    report = supervisor.generate_report(output_file=args.output)
    
    if not args.output:
        print(report)
    
    # 如果发现高严重程度违规，返回非零退出码
    high_violations = [v for v in violations if v.severity == "HIGH"]
    if high_violations:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main() 