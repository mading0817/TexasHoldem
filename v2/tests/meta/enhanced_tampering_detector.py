"""
增强版私有状态篡改检测器

该模块实现更复杂的篡改模式识别，包括：
1. 间接状态篡改检测
2. 链式调用篡改检测
3. 动态属性篡改检测
4. 测试帮凶模式检测
"""

import ast
import re
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from v2.tests.meta.anti_cheat_supervisor import (
    AntiCheatSupervisor, 
    ViolationType, 
    Violation,
    CheatDetectionVisitor
)


@dataclass
class TamperingPattern:
    """篡改模式定义"""
    pattern_name: str
    description: str
    detection_method: str
    severity: str
    examples: List[str]


class EnhancedTamperingDetector(AntiCheatSupervisor):
    """
    增强版篡改检测器
    
    继承基础监督者，添加更复杂的篡改模式检测能力。
    """
    
    def __init__(self, project_root: str = None):
        """初始化增强版检测器"""
        super().__init__(project_root)
        
        # 增强的篡改模式
        self.tampering_patterns = self._initialize_tampering_patterns()
        
        # 间接篡改检测规则
        self.indirect_tampering_rules = {
            # 通过字典访问修改私有状态
            'dict_access': [
                r'__dict__\[.*_.*\]',
                r'vars\(.*\)\[.*_.*\]',
                r'getattr\(.*,.*_.*\)'
            ],
            
            # 通过循环修改私有状态
            'loop_tampering': [
                r'for.*in.*__dict__',
                r'for.*in.*vars\(',
                r'for.*in.*dir\('
            ],
            
            # 通过函数调用修改私有状态
            'function_tampering': [
                r'setattr\(.*,.*_.*,.*\)',
                r'delattr\(.*,.*_.*\)',
                r'hasattr\(.*,.*_.*\)'
            ]
        }
        
        # 测试帮凶模式（测试代码帮助其他测试作弊）
        self.helper_cheat_patterns = {
            # 创建带有私有状态的测试对象
            'malicious_factory': [
                r'def.*create.*\(.*\):.*',  # 简化模式，在函数体中单独检查
                r'def.*setup.*\(.*\):.*',
                r'def.*mock.*\(.*\):.*'
            ],
            
            # 提供私有状态访问的辅助方法
            'state_accessor': [
                r'def.*get_private.*\(.*\):.*',
                r'def.*access.*\(.*\):.*',
                r'def.*expose.*\(.*\):.*'
            ]
        }
        
        # 动态篡改检测
        self.dynamic_tampering_patterns = {
            # 使用字符串构造属性名
            'string_construction': [
                r'setattr\(.*,.*\+.*,.*\)',
                r'getattr\(.*,.*\+.*\)',
                r'hasattr\(.*,.*\+.*\)'
            ],
            
            # 使用格式化字符串
            'format_string': [
                r'getattr\(.*,.*\.format\(',
                r'setattr\(.*,.*\.format\(',
                r'getattr\(.*,.*%.*\)'
            ]
        }
    
    def _initialize_tampering_patterns(self) -> List[TamperingPattern]:
        """初始化篡改模式定义"""
        return [
            TamperingPattern(
                pattern_name="direct_private_assignment",
                description="直接赋值私有属性",
                detection_method="AST分析赋值节点",
                severity="HIGH",
                examples=["obj._private_attr = value", "self._game_state = new_state"]
            ),
            
            TamperingPattern(
                pattern_name="dict_access_tampering",
                description="通过__dict__访问私有属性",
                detection_method="正则表达式匹配",
                severity="HIGH",
                examples=["obj.__dict__['_private'] = value", "vars(obj)['_state'] = new"]
            ),
            
            TamperingPattern(
                pattern_name="reflection_tampering",
                description="使用反射API修改私有状态",
                detection_method="函数调用分析",
                severity="HIGH",
                examples=["setattr(obj, '_private', value)", "delattr(obj, '_state')"]
            ),
            
            TamperingPattern(
                pattern_name="loop_based_tampering",
                description="循环遍历修改私有属性",
                detection_method="循环结构分析",
                severity="MEDIUM",
                examples=["for attr in obj.__dict__: if attr.startswith('_'): ..."]
            ),
            
            TamperingPattern(
                pattern_name="helper_function_cheat",
                description="测试辅助函数包含篡改逻辑",
                detection_method="函数定义分析",
                severity="HIGH",
                examples=["def create_test_obj(): obj._private = 'hacked'; return obj"]
            ),
            
            TamperingPattern(
                pattern_name="dynamic_attribute_tampering",
                description="动态构造属性名进行篡改",
                detection_method="字符串操作分析",
                severity="MEDIUM",
                examples=["getattr(obj, '_' + attr_name)", "setattr(obj, prefix + '_state', val)"]
            )
        ]
    
    def scan_test_files(self, test_directory: str = None) -> List[Violation]:
        """
        增强版扫描，包含复杂篡改模式检测
        
        Args:
            test_directory: 测试目录路径
            
        Returns:
            违规记录列表
        """
        # 先执行基础扫描
        violations = super().scan_test_files(test_directory)
        
        # 添加增强检测
        if test_directory is None:
            test_directory = self.project_root / "v2" / "tests"
        else:
            test_directory = Path(test_directory)
        
        # 扫描间接篡改
        for py_file in test_directory.rglob("*.py"):
            if self._should_scan_file(py_file):
                self._scan_indirect_tampering(py_file)
                self._scan_helper_cheat_patterns(py_file)
                self._scan_dynamic_tampering(py_file)
        
        return self.violations
    
    def _scan_indirect_tampering(self, file_path: Path):
        """扫描间接篡改模式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                # 检查字典访问篡改
                for pattern in self.indirect_tampering_rules['dict_access']:
                    if re.search(pattern, line):
                        violation = Violation(
                            violation_type=ViolationType.PRIVATE_STATE_TAMPERING,
                            file_path=str(file_path),
                            line_number=line_num,
                            column_number=0,
                            description=f"间接篡改私有状态（字典访问）: {pattern}",
                            code_snippet=line.strip(),
                            severity="HIGH"
                        )
                        self.violations.append(violation)
                
                # 检查循环篡改
                for pattern in self.indirect_tampering_rules['loop_tampering']:
                    if re.search(pattern, line):
                        violation = Violation(
                            violation_type=ViolationType.PRIVATE_STATE_TAMPERING,
                            file_path=str(file_path),
                            line_number=line_num,
                            column_number=0,
                            description=f"循环遍历篡改私有状态: {pattern}",
                            code_snippet=line.strip(),
                            severity="MEDIUM"
                        )
                        self.violations.append(violation)
                
                # 检查函数篡改
                for pattern in self.indirect_tampering_rules['function_tampering']:
                    if re.search(pattern, line):
                        # 检查是否在白名单中
                        if not self._is_whitelisted_operation(str(file_path), line.strip()):
                            violation = Violation(
                                violation_type=ViolationType.DANGEROUS_OPERATION,
                                file_path=str(file_path),
                                line_number=line_num,
                                column_number=0,
                                description=f"函数调用篡改私有状态: {pattern}",
                                code_snippet=line.strip(),
                                severity="HIGH"
                            )
                            self.violations.append(violation)
        
        except Exception as e:
            # 记录扫描错误
            violation = Violation(
                violation_type=ViolationType.DANGEROUS_OPERATION,
                file_path=str(file_path),
                line_number=1,
                column_number=1,
                description=f"间接篡改扫描错误: {str(e)}",
                code_snippet="",
                severity="MEDIUM"
            )
            self.violations.append(violation)
    
    def _scan_helper_cheat_patterns(self, file_path: Path):
        """扫描测试帮凶模式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.splitlines()
            in_function = False
            current_function = ""
            
            for line_num, line in enumerate(lines, 1):
                # 检查是否进入函数定义
                for pattern in self.helper_cheat_patterns['malicious_factory']:
                    if re.search(pattern, line):
                        in_function = True
                        current_function = line.strip()
                        continue
                
                # 检查状态访问器模式
                for pattern in self.helper_cheat_patterns['state_accessor']:
                    if re.search(pattern, line):
                        violation = Violation(
                            violation_type=ViolationType.PRIVATE_STATE_TAMPERING,
                            file_path=str(file_path),
                            line_number=line_num,
                            column_number=0,
                            description=f"测试帮凶：提供私有状态访问的辅助方法",
                            code_snippet=line.strip(),
                            severity="MEDIUM"
                        )
                        self.violations.append(violation)
                
                # 如果在函数内，检查是否有私有状态篡改
                if in_function and line.strip():
                    # 检查是否有私有属性赋值
                    if re.search(r'\._\w+\s*=', line):
                        violation = Violation(
                            violation_type=ViolationType.PRIVATE_STATE_TAMPERING,
                            file_path=str(file_path),
                            line_number=line_num,
                            column_number=0,
                            description=f"测试帮凶：恶意工厂方法包含私有状态篡改",
                            code_snippet=line.strip(),
                            severity="HIGH"
                        )
                        self.violations.append(violation)
                
                # 检查函数结束（简单的缩进检测）
                if in_function and line and not line.startswith(' ') and not line.startswith('\t'):
                    in_function = False
                    current_function = ""
        
        except Exception as e:
            pass  # 静默处理错误
    
    def _scan_dynamic_tampering(self, file_path: Path):
        """扫描动态篡改模式"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                # 检查字符串构造模式
                for pattern in self.dynamic_tampering_patterns['string_construction']:
                    if re.search(pattern, line):
                        violation = Violation(
                            violation_type=ViolationType.PRIVATE_STATE_TAMPERING,
                            file_path=str(file_path),
                            line_number=line_num,
                            column_number=0,
                            description=f"动态篡改：字符串构造属性名",
                            code_snippet=line.strip(),
                            severity="MEDIUM"
                        )
                        self.violations.append(violation)
                
                # 检查格式化字符串模式
                for pattern in self.dynamic_tampering_patterns['format_string']:
                    if re.search(pattern, line):
                        violation = Violation(
                            violation_type=ViolationType.PRIVATE_STATE_TAMPERING,
                            file_path=str(file_path),
                            line_number=line_num,
                            column_number=0,
                            description=f"动态篡改：格式化字符串构造属性名",
                            code_snippet=line.strip(),
                            severity="MEDIUM"
                        )
                        self.violations.append(violation)
        
        except Exception as e:
            pass  # 静默处理错误
    
    def generate_enhanced_report(self, output_file: str = None) -> str:
        """
        生成增强版违规报告
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            报告内容
        """
        if not self.violations:
            report = "🎉 恭喜！未发现任何测试作弊行为（包括复杂篡改模式）！\n"
        else:
            report = self._generate_enhanced_detailed_report()
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report
    
    def _generate_enhanced_detailed_report(self) -> str:
        """生成增强版详细报告"""
        report_lines = [
            "🚨 增强版测试反作弊监督者报告",
            "=" * 60,
            f"扫描时间: {self._get_current_time()}",
            f"发现违规: {len(self.violations)} 个",
            ""
        ]
        
        # 按违规类型分组统计
        violation_stats = self._analyze_violation_patterns()
        
        report_lines.extend([
            "📊 违规模式统计:",
            "-" * 30
        ])
        
        for pattern_type, count in violation_stats.items():
            report_lines.append(f"  {pattern_type}: {count} 个")
        
        report_lines.append("")
        
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
        
        # 添加增强版修复建议
        report_lines.extend([
            "💡 增强版修复建议:",
            "-" * 30,
            "1. 移除所有直接和间接修改私有状态的代码",
            "2. 避免使用__dict__、vars()等访问私有属性",
            "3. 不要在测试辅助方法中包含篡改逻辑",
            "4. 避免动态构造私有属性名",
            "5. 使用公共API和正当的测试模式",
            "6. 如需特殊测试场景，请添加到白名单配置",
            ""
        ])
        
        # 添加篡改模式说明
        report_lines.extend([
            "📚 检测到的篡改模式说明:",
            "-" * 30
        ])
        
        for pattern in self.tampering_patterns:
            if any(pattern.pattern_name in v.description.lower() for v in self.violations):
                report_lines.extend([
                    f"🔍 {pattern.pattern_name}:",
                    f"   描述: {pattern.description}",
                    f"   检测方法: {pattern.detection_method}",
                    f"   严重程度: {pattern.severity}",
                    ""
                ])
        
        return "\n".join(report_lines)
    
    def _analyze_violation_patterns(self) -> Dict[str, int]:
        """分析违规模式统计"""
        stats = {}
        
        for violation in self.violations:
            violation_type = violation.violation_type.value
            if violation_type not in stats:
                stats[violation_type] = 0
            stats[violation_type] += 1
        
        return stats
    
    def get_tampering_patterns_summary(self) -> List[Dict[str, Any]]:
        """获取篡改模式摘要"""
        return [
            {
                "name": pattern.pattern_name,
                "description": pattern.description,
                "severity": pattern.severity,
                "examples": pattern.examples
            }
            for pattern in self.tampering_patterns
        ]


def main():
    """主函数，用于命令行执行增强版检测器"""
    import argparse
    
    parser = argparse.ArgumentParser(description="增强版测试反作弊监督者")
    parser.add_argument("--test-dir", help="测试目录路径")
    parser.add_argument("--output", help="输出报告文件路径")
    parser.add_argument("--project-root", help="项目根目录路径")
    parser.add_argument("--patterns", action="store_true", help="显示篡改模式说明")
    
    args = parser.parse_args()
    
    detector = EnhancedTamperingDetector(project_root=args.project_root)
    
    if args.patterns:
        print("🔍 支持的篡改模式:")
        print("=" * 50)
        for pattern in detector.get_tampering_patterns_summary():
            print(f"📍 {pattern['name']}")
            print(f"   描述: {pattern['description']}")
            print(f"   严重程度: {pattern['severity']}")
            print(f"   示例: {', '.join(pattern['examples'][:2])}")
            print()
        return
    
    violations = detector.scan_test_files(test_directory=args.test_dir)
    report = detector.generate_enhanced_report(output_file=args.output)
    
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