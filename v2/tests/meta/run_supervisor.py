#!/usr/bin/env python3
"""
反作弊监督者运行工具

简化的命令行接口，用于快速运行反作弊检查。
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v2.tests.meta.anti_cheat_supervisor import AntiCheatSupervisor


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="德州扑克v2测试反作弊监督者",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python run_supervisor.py                    # 扫描默认测试目录
  python run_supervisor.py --strict           # 严格模式
  python run_supervisor.py --output report.txt # 输出到文件
  python run_supervisor.py --fix              # 显示修复建议
        """
    )
    
    parser.add_argument(
        "--test-dir", 
        default="v2/tests",
        help="测试目录路径 (默认: v2/tests)"
    )
    
    parser.add_argument(
        "--output", 
        help="输出报告文件路径"
    )
    
    parser.add_argument(
        "--strict", 
        action="store_true",
        help="启用严格模式（更严格的检查）"
    )
    
    parser.add_argument(
        "--fix", 
        action="store_true",
        help="显示详细的修复建议"
    )
    
    parser.add_argument(
        "--quiet", 
        action="store_true",
        help="静默模式（只显示违规数量）"
    )
    
    parser.add_argument(
        "--exclude-low", 
        action="store_true",
        help="排除低严重程度违规"
    )
    
    args = parser.parse_args()
    
    # 创建监督者
    supervisor = AntiCheatSupervisor(project_root=str(project_root))
    
    if not args.quiet:
        print("🔍 启动测试反作弊监督者...")
        print(f"📁 扫描目录: {args.test_dir}")
        if args.strict:
            print("⚠️  严格模式已启用")
    
    # 扫描测试文件
    violations = supervisor.scan_test_files(test_directory=args.test_dir)
    
    # 过滤违规（如果需要）
    if args.exclude_low:
        violations = [v for v in violations if v.severity != "LOW"]
    
    # 生成报告
    if args.quiet:
        # 静默模式：只显示统计
        high_count = len([v for v in violations if v.severity == "HIGH"])
        medium_count = len([v for v in violations if v.severity == "MEDIUM"])
        low_count = len([v for v in violations if v.severity == "LOW"])
        
        print(f"违规统计: 高={high_count}, 中={medium_count}, 低={low_count}")
    else:
        # 正常模式：显示完整报告
        report = supervisor.generate_report(output_file=args.output)
        
        if not args.output:
            print(report)
        else:
            print(f"📄 报告已保存到: {args.output}")
    
    # 显示修复建议（如果需要）
    if args.fix and violations:
        print("\n" + "="*60)
        print("🔧 详细修复建议:")
        print("="*60)
        
        # 按违规类型分组显示修复建议
        api_violations = [v for v in violations if "api_boundary" in v.violation_type.value]
        private_violations = [v for v in violations if "private_state" in v.violation_type.value]
        dangerous_violations = [v for v in violations if "dangerous" in v.violation_type.value]
        
        if api_violations:
            print("\n🚫 API边界违规修复:")
            print("- 将UI测试中的core模块导入改为controller模块导入")
            print("- 使用公共API而不是直接访问内部实现")
            print("- 示例: 将 'from v2.core.state import GameState' 改为通过controller获取状态")
        
        if private_violations:
            print("\n🔒 私有状态篡改修复:")
            print("- 移除所有直接修改私有属性的代码")
            print("- 使用公共方法来设置状态")
            print("- 创建专门的测试辅助方法来构造测试状态")
        
        if dangerous_violations:
            print("\n⚠️  危险操作修复:")
            print("- 避免使用setattr、exec、eval等反射操作")
            print("- 使用正常的对象构造和方法调用")
            print("- 如果必须使用，请添加到白名单配置中")
    
    # 设置退出码
    high_violations = [v for v in violations if v.severity == "HIGH"]
    if high_violations:
        if not args.quiet:
            print(f"\n❌ 发现 {len(high_violations)} 个高严重程度违规，测试质量检查失败！")
        sys.exit(1)
    else:
        if not args.quiet:
            print("\n✅ 测试反作弊检查通过！")
        sys.exit(0)


if __name__ == "__main__":
    main() 