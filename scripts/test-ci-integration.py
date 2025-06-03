#!/usr/bin/env python3
"""
CI/CD集成测试脚本
模拟GitHub Actions工作流的本地执行
"""

import subprocess
import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime

class CIIntegrationTester:
    """CI/CD集成测试器"""
    
    def __init__(self):
        self.start_time = time.time()
        self.results = {
            'stages': {},
            'overall_success': True,
            'total_tests': 0,
            'failed_tests': 0
        }
        
    def run_command(self, command, stage_name, timeout=300):
        """运行命令并记录结果"""
        print(f"\n🔄 执行阶段: {stage_name}")
        print(f"命令: {command}")
        print("-" * 60)
        
        start_time = time.time()
        
        try:
            # 获取绝对路径
            python_path = Path.cwd() / ".venv" / "Scripts" / "python.exe"
            if not python_path.exists():
                raise FileNotFoundError(f"Python解释器不存在: {python_path}")
            
            # 替换命令中的相对路径为绝对路径
            command = command.replace(".venv/Scripts/python", str(python_path))
            
            # 在Windows上使用shell=True
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=Path.cwd()
            )
            
            duration = time.time() - start_time
            success = result.returncode == 0
            
            self.results['stages'][stage_name] = {
                'success': success,
                'duration': duration,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            if success:
                print(f"✅ {stage_name} 成功 (耗时: {duration:.2f}s)")
                if result.stdout.strip():
                    print("输出:")
                    print(result.stdout)
            else:
                print(f"❌ {stage_name} 失败 (耗时: {duration:.2f}s)")
                print("错误输出:")
                print(result.stderr)
                self.results['overall_success'] = False
                
            return success
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {stage_name} 超时")
            self.results['stages'][stage_name] = {
                'success': False,
                'duration': timeout,
                'error': 'timeout'
            }
            self.results['overall_success'] = False
            return False
            
        except Exception as e:
            print(f"💥 {stage_name} 异常: {e}")
            self.results['stages'][stage_name] = {
                'success': False,
                'duration': time.time() - start_time,
                'error': str(e)
            }
            self.results['overall_success'] = False
            return False
    
    def stage_1_supervisor_checks(self):
        """阶段1: 监督者检查"""
        print("\n" + "="*80)
        print("🛡️ 阶段1: 监督者检查 (最高优先级)")
        print("="*80)
        
        # 反作弊监督者检查
        success1 = self.run_command(
            ".venv/Scripts/python -m pytest v2/tests/meta/ -m supervisor -v --tb=short",
            "反作弊监督者检查"
        )
        
        # 私有状态篡改检测
        success2 = self.run_command(
            ".venv/Scripts/python -m pytest v2/tests/meta/ -m state_tamper -v --tb=short",
            "私有状态篡改检测"
        )
        
        return success1 and success2
    
    def stage_2_core_tests(self):
        """阶段2: 核心测试"""
        print("\n" + "="*80)
        print("🧪 阶段2: 核心测试 (快速反馈)")
        print("="*80)
        
        # 单元测试
        success1 = self.run_command(
            ".venv/Scripts/python -m pytest v2/tests/unit/ -v --tb=short --junitxml=test-reports/unit-junit.xml",
            "单元测试"
        )
        
        # 集成测试
        success2 = self.run_command(
            ".venv/Scripts/python -m pytest v2/tests/integration/ -v --tb=short --junitxml=test-reports/integration-junit.xml",
            "集成测试"
        )
        
        return success1 and success2
    
    def stage_3_advanced_testing(self):
        """阶段3: 高级测试体系"""
        print("\n" + "="*80)
        print("🚀 阶段3: 高级测试体系")
        print("="*80)
        
        # 规则覆盖率测试
        success1 = self.run_command(
            ".venv/Scripts/python -m pytest v2/tests/meta/ -m rule_coverage -v --tb=short",
            "规则覆盖率测试"
        )
        
        # AI公平性测试
        success2 = self.run_command(
            ".venv/Scripts/python -m pytest v2/tests/meta/ -m ai_fairness -v --tb=short",
            "AI公平性测试"
        )
        
        # 根因分析测试
        success3 = self.run_command(
            ".venv/Scripts/python -m pytest v2/tests/meta/ -m root_cause -v --tb=short",
            "根因分析测试"
        )
        
        # 端到端集成测试
        success4 = self.run_command(
            ".venv/Scripts/python -m pytest v2/tests/integration/ -m end_to_end -v --tb=short",
            "端到端集成测试"
        )
        
        return success1 and success2 and success3 and success4
    
    def stage_4_quality_gate(self):
        """阶段4: 质量门控"""
        print("\n" + "="*80)
        print("🎯 阶段4: 质量门控和结果聚合")
        print("="*80)
        
        # 创建测试报告目录
        os.makedirs('test-reports', exist_ok=True)
        
        # 统计测试结果
        total_stages = len(self.results['stages'])
        successful_stages = sum(1 for stage in self.results['stages'].values() if stage['success'])
        
        # 生成质量门控报告
        report = self.generate_quality_report(successful_stages, total_stages)
        
        # 保存报告
        with open('test-reports/ci-integration-report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        
        print("📊 质量门控报告:")
        print(report)
        
        # 质量门控条件
        quality_gates = {
            'all_stages_passed': successful_stages == total_stages,
            'supervisor_checks_passed': self.results['stages'].get('反作弊监督者检查', {}).get('success', False) and 
                                      self.results['stages'].get('私有状态篡改检测', {}).get('success', False),
            'core_tests_passed': self.results['stages'].get('单元测试', {}).get('success', False) and 
                               self.results['stages'].get('集成测试', {}).get('success', False)
        }
        
        all_gates_passed = all(quality_gates.values())
        
        if all_gates_passed:
            print("✅ 所有质量门控通过！")
        else:
            print("❌ 质量门控失败:")
            for gate, passed in quality_gates.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {gate}")
        
        return all_gates_passed
    
    def generate_quality_report(self, successful_stages, total_stages):
        """生成质量门控报告"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        total_duration = time.time() - self.start_time
        
        report = f"""# 🎯 CI/CD集成测试报告

**生成时间**: {timestamp}
**总耗时**: {total_duration:.2f}秒
**测试环境**: 本地模拟

## 📊 阶段执行统计

| 阶段 | 状态 | 耗时 |
|------|------|------|
"""
        
        for stage_name, stage_result in self.results['stages'].items():
            status = "✅ 通过" if stage_result['success'] else "❌ 失败"
            duration = stage_result.get('duration', 0)
            report += f"| {stage_name} | {status} | {duration:.2f}s |\n"
        
        success_rate = (successful_stages / total_stages * 100) if total_stages > 0 else 0
        
        report += f"""
## 🏆 总体结果

- **阶段总数**: {total_stages}
- **成功阶段**: {successful_stages}
- **失败阶段**: {total_stages - successful_stages}
- **成功率**: {success_rate:.1f}%

## 🚪 质量门控

"""
        
        # 检查关键阶段
        supervisor_passed = (
            self.results['stages'].get('反作弊监督者检查', {}).get('success', False) and
            self.results['stages'].get('私有状态篡改检测', {}).get('success', False)
        )
        
        core_passed = (
            self.results['stages'].get('单元测试', {}).get('success', False) and
            self.results['stages'].get('集成测试', {}).get('success', False)
        )
        
        report += f"- **监督者检查**: {'✅ 通过' if supervisor_passed else '❌ 失败'}\n"
        report += f"- **核心测试**: {'✅ 通过' if core_passed else '❌ 失败'}\n"
        report += f"- **整体成功率**: {'✅ 通过' if success_rate >= 95 else '❌ 失败'} ({success_rate:.1f}% >= 95%)\n"
        
        overall_status = "✅ 通过" if (supervisor_passed and core_passed and success_rate >= 95) else "❌ 失败"
        report += f"\n## 🏆 最终结果: {overall_status}\n"
        
        return report
    
    def run_full_pipeline(self):
        """运行完整的CI/CD流水线"""
        print("🚀 开始CI/CD集成测试")
        print(f"工作目录: {Path.cwd()}")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 检查虚拟环境
        if not Path('.venv/Scripts/python.exe').exists():
            print("❌ 虚拟环境不存在，请先创建虚拟环境")
            return False
        
        try:
            # 阶段1: 监督者检查
            if not self.stage_1_supervisor_checks():
                print("❌ 监督者检查失败，停止流水线")
                return False
            
            # 阶段2: 核心测试
            if not self.stage_2_core_tests():
                print("⚠️ 核心测试失败，但继续执行高级测试")
            
            # 阶段3: 高级测试体系
            self.stage_3_advanced_testing()
            
            # 阶段4: 质量门控
            quality_passed = self.stage_4_quality_gate()
            
            # 最终结果
            print("\n" + "="*80)
            print("🏁 CI/CD集成测试完成")
            print("="*80)
            
            total_duration = time.time() - self.start_time
            print(f"总耗时: {total_duration:.2f}秒")
            
            if quality_passed:
                print("🎉 CI/CD集成测试成功！所有质量门控通过。")
                return True
            else:
                print("💥 CI/CD集成测试失败！请检查失败的阶段。")
                return False
                
        except KeyboardInterrupt:
            print("\n⏹️ 用户中断测试")
            return False
        except Exception as e:
            print(f"\n💥 测试过程中发生异常: {e}")
            return False

def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
CI/CD集成测试脚本

用法:
    python scripts/test-ci-integration.py

功能:
    - 模拟GitHub Actions CI/CD流水线
    - 按优先级执行测试阶段
    - 生成质量门控报告
    - 验证测试体系集成效果

阶段:
    1. 监督者检查 (最高优先级)
    2. 核心测试 (快速反馈)
    3. 高级测试体系
    4. 质量门控和结果聚合
        """)
        return
    
    tester = CIIntegrationTester()
    success = tester.run_full_pipeline()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main() 