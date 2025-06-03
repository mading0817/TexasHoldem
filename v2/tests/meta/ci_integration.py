#!/usr/bin/env python3
"""
CI/CD集成脚本

将反作弊监督者集成到CI/CD流水线中，确保每次提交都通过反作弊检查。
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v2.tests.meta.enhanced_tampering_detector import EnhancedTamperingDetector
from v2.tests.meta.anti_cheat_supervisor import ViolationType


class CIIntegration:
    """
    CI/CD集成管理器
    
    负责在CI/CD环境中运行反作弊检查，并生成适合CI系统的报告。
    """
    
    def __init__(self, project_root: str = None, config: Dict[str, Any] = None):
        """
        初始化CI集成管理器
        
        Args:
            project_root: 项目根目录
            config: CI配置
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.config = config or self._load_default_config()
        self.detector = EnhancedTamperingDetector(project_root=str(self.project_root))
        
        # CI环境检测
        self.is_ci = self._detect_ci_environment()
        self.ci_system = self._detect_ci_system()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认CI配置"""
        return {
            "fail_on_high_violations": True,
            "fail_on_medium_violations": False,
            "fail_on_low_violations": False,
            "max_violations_allowed": 0,
            "generate_junit_report": True,
            "generate_checkstyle_report": True,
            "output_directory": "test-reports",
            "exclude_files": [],
            "exclude_directories": ["__pycache__", ".git", ".pytest_cache"],
            "notification": {
                "enabled": True,
                "webhook_url": None,
                "slack_channel": None
            }
        }
    
    def _detect_ci_environment(self) -> bool:
        """检测是否在CI环境中运行"""
        ci_indicators = [
            "CI", "CONTINUOUS_INTEGRATION", "BUILD_NUMBER",
            "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL",
            "TRAVIS", "CIRCLECI", "APPVEYOR"
        ]
        
        return any(os.getenv(indicator) for indicator in ci_indicators)
    
    def _detect_ci_system(self) -> str:
        """检测CI系统类型"""
        if os.getenv("GITHUB_ACTIONS"):
            return "github_actions"
        elif os.getenv("GITLAB_CI"):
            return "gitlab_ci"
        elif os.getenv("JENKINS_URL"):
            return "jenkins"
        elif os.getenv("TRAVIS"):
            return "travis"
        elif os.getenv("CIRCLECI"):
            return "circleci"
        elif os.getenv("APPVEYOR"):
            return "appveyor"
        else:
            return "unknown"
    
    def run_anti_cheat_check(self, test_directory: str = None) -> Dict[str, Any]:
        """
        运行反作弊检查
        
        Args:
            test_directory: 测试目录路径
            
        Returns:
            检查结果
        """
        print("🔍 启动CI反作弊检查...")
        
        if self.is_ci:
            print(f"📍 检测到CI环境: {self.ci_system}")
        
        # 运行检测
        violations = self.detector.scan_test_files(test_directory=test_directory)
        
        # 分析结果
        result = self._analyze_violations(violations)
        
        # 生成报告
        self._generate_reports(violations, result)
        
        # 发送通知（如果配置了）
        if self.config.get("notification", {}).get("enabled"):
            self._send_notification(result)
        
        return result
    
    def _analyze_violations(self, violations: List) -> Dict[str, Any]:
        """分析违规结果"""
        high_violations = [v for v in violations if v.severity == "HIGH"]
        medium_violations = [v for v in violations if v.severity == "MEDIUM"]
        low_violations = [v for v in violations if v.severity == "LOW"]
        
        # 判断是否应该失败
        should_fail = False
        failure_reasons = []
        
        if self.config["fail_on_high_violations"] and high_violations:
            should_fail = True
            failure_reasons.append(f"{len(high_violations)} 个高严重程度违规")
        
        if self.config["fail_on_medium_violations"] and medium_violations:
            should_fail = True
            failure_reasons.append(f"{len(medium_violations)} 个中等严重程度违规")
        
        if self.config["fail_on_low_violations"] and low_violations:
            should_fail = True
            failure_reasons.append(f"{len(low_violations)} 个低严重程度违规")
        
        if len(violations) > self.config["max_violations_allowed"]:
            should_fail = True
            failure_reasons.append(f"违规总数 {len(violations)} 超过允许的 {self.config['max_violations_allowed']}")
        
        return {
            "total_violations": len(violations),
            "high_violations": len(high_violations),
            "medium_violations": len(medium_violations),
            "low_violations": len(low_violations),
            "should_fail": should_fail,
            "failure_reasons": failure_reasons,
            "violations": violations,
            "ci_system": self.ci_system,
            "is_ci": self.is_ci
        }
    
    def _generate_reports(self, violations: List, result: Dict[str, Any]):
        """生成CI报告"""
        output_dir = Path(self.config["output_directory"])
        output_dir.mkdir(exist_ok=True)
        
        # 生成JUnit格式报告
        if self.config["generate_junit_report"]:
            self._generate_junit_report(violations, result, output_dir)
        
        # 生成Checkstyle格式报告
        if self.config["generate_checkstyle_report"]:
            self._generate_checkstyle_report(violations, result, output_dir)
        
        # 生成JSON报告
        self._generate_json_report(violations, result, output_dir)
        
        # 生成文本报告
        self._generate_text_report(violations, result, output_dir)
    
    def _generate_junit_report(self, violations: List, result: Dict[str, Any], output_dir: Path):
        """生成JUnit格式报告"""
        junit_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="AntiCheatSupervisor" tests="1" failures="{1 if result['should_fail'] else 0}" errors="0" time="0">
    <testcase name="anti_cheat_check" classname="v2.tests.meta.AntiCheatSupervisor">
'''
        
        if result['should_fail']:
            junit_content += f'''        <failure message="反作弊检查失败" type="ViolationError">
发现 {result['total_violations']} 个违规:
- 高严重程度: {result['high_violations']} 个
- 中等严重程度: {result['medium_violations']} 个  
- 低严重程度: {result['low_violations']} 个

失败原因: {', '.join(result['failure_reasons'])}
        </failure>
'''
        
        junit_content += '''    </testcase>
</testsuite>'''
        
        with open(output_dir / "anti-cheat-junit.xml", 'w', encoding='utf-8') as f:
            f.write(junit_content)
    
    def _generate_checkstyle_report(self, violations: List, result: Dict[str, Any], output_dir: Path):
        """生成Checkstyle格式报告"""
        checkstyle_content = '''<?xml version="1.0" encoding="UTF-8"?>
<checkstyle version="8.0">
'''
        
        # 按文件分组违规
        violations_by_file = {}
        for violation in violations:
            file_path = violation.file_path
            if file_path not in violations_by_file:
                violations_by_file[file_path] = []
            violations_by_file[file_path].append(violation)
        
        for file_path, file_violations in violations_by_file.items():
            checkstyle_content += f'    <file name="{file_path}">\n'
            
            for violation in file_violations:
                severity_map = {"HIGH": "error", "MEDIUM": "warning", "LOW": "info"}
                severity = severity_map.get(violation.severity, "error")
                
                checkstyle_content += f'''        <error line="{violation.line_number}" 
                      column="{violation.column_number}" 
                      severity="{severity}" 
                      message="{violation.description}" 
                      source="AntiCheatSupervisor.{violation.violation_type.value}"/>
'''
            
            checkstyle_content += '    </file>\n'
        
        checkstyle_content += '</checkstyle>'
        
        with open(output_dir / "anti-cheat-checkstyle.xml", 'w', encoding='utf-8') as f:
            f.write(checkstyle_content)
    
    def _generate_json_report(self, violations: List, result: Dict[str, Any], output_dir: Path):
        """生成JSON报告"""
        json_data = {
            "summary": {
                "total_violations": result["total_violations"],
                "high_violations": result["high_violations"],
                "medium_violations": result["medium_violations"],
                "low_violations": result["low_violations"],
                "should_fail": result["should_fail"],
                "failure_reasons": result["failure_reasons"],
                "ci_system": result["ci_system"],
                "is_ci": result["is_ci"]
            },
            "violations": [
                {
                    "type": v.violation_type.value,
                    "file": v.file_path,
                    "line": v.line_number,
                    "column": v.column_number,
                    "severity": v.severity,
                    "description": v.description,
                    "code": v.code_snippet
                }
                for v in violations
            ]
        }
        
        with open(output_dir / "anti-cheat-report.json", 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    def _generate_text_report(self, violations: List, result: Dict[str, Any], output_dir: Path):
        """生成文本报告"""
        report = self.detector.generate_enhanced_report()
        
        with open(output_dir / "anti-cheat-report.txt", 'w', encoding='utf-8') as f:
            f.write(report)
    
    def _send_notification(self, result: Dict[str, Any]):
        """发送通知"""
        # 这里可以实现Slack、Teams、邮件等通知
        # 目前只是打印到控制台
        if result["should_fail"]:
            print("🚨 反作弊检查失败通知已发送")
        else:
            print("✅ 反作弊检查通过通知已发送")
    
    def get_exit_code(self, result: Dict[str, Any]) -> int:
        """获取退出码"""
        return 1 if result["should_fail"] else 0


def create_github_actions_workflow():
    """创建GitHub Actions工作流文件"""
    workflow_content = '''name: Anti-Cheat Check

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  anti-cheat:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run Anti-Cheat Check
      run: |
        python v2/tests/meta/ci_integration.py --test-dir v2/tests --output test-reports
    
    - name: Upload test reports
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: anti-cheat-reports
        path: test-reports/
    
    - name: Publish Test Results
      uses: dorny/test-reporter@v1
      if: always()
      with:
        name: Anti-Cheat Test Results
        path: test-reports/anti-cheat-junit.xml
        reporter: java-junit
'''
    
    workflow_dir = Path(".github/workflows")
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    with open(workflow_dir / "anti-cheat.yml", 'w', encoding='utf-8') as f:
        f.write(workflow_content)
    
    print("✅ GitHub Actions工作流文件已创建: .github/workflows/anti-cheat.yml")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="CI/CD反作弊集成")
    parser.add_argument("--test-dir", default="v2/tests", help="测试目录路径")
    parser.add_argument("--output", default="test-reports", help="报告输出目录")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--create-workflow", action="store_true", help="创建GitHub Actions工作流")
    parser.add_argument("--fail-on-medium", action="store_true", help="中等严重程度违规时失败")
    parser.add_argument("--max-violations", type=int, default=0, help="允许的最大违规数")
    
    args = parser.parse_args()
    
    if args.create_workflow:
        create_github_actions_workflow()
        return
    
    # 加载配置
    config = None
    if args.config and Path(args.config).exists():
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    # 创建CI集成管理器
    ci = CIIntegration(config=config)
    
    # 更新配置
    if args.fail_on_medium:
        ci.config["fail_on_medium_violations"] = True
    
    if args.max_violations is not None:
        ci.config["max_violations_allowed"] = args.max_violations
    
    ci.config["output_directory"] = args.output
    
    # 运行检查
    result = ci.run_anti_cheat_check(test_directory=args.test_dir)
    
    # 打印结果摘要
    print("\n" + "="*60)
    print("🔍 CI反作弊检查结果摘要")
    print("="*60)
    print(f"总违规数: {result['total_violations']}")
    print(f"高严重程度: {result['high_violations']}")
    print(f"中等严重程度: {result['medium_violations']}")
    print(f"低严重程度: {result['low_violations']}")
    print(f"CI系统: {result['ci_system']}")
    print(f"检查状态: {'❌ 失败' if result['should_fail'] else '✅ 通过'}")
    
    if result['failure_reasons']:
        print(f"失败原因: {', '.join(result['failure_reasons'])}")
    
    print(f"报告已生成到: {args.output}/")
    
    # 返回适当的退出码
    sys.exit(ci.get_exit_code(result))


if __name__ == "__main__":
    main() 