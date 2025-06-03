"""
德州扑克规则覆盖率监控器演示脚本

展示 PokerRulesCoverageMonitor 的主要功能，包括：
1. 扫描测试文件
2. 分析规则覆盖率
3. 生成详细报告
4. 识别缺失的测试场景
5. 提供测试用例建议
"""

import sys
from pathlib import Path
from v2.tests.meta.poker_rules_coverage import PokerRulesCoverageMonitor


def print_separator(title: str, char: str = "=", width: int = 60):
    """打印分隔符"""
    print(f"\n{char * width}")
    print(f" {title} ".center(width, char))
    print(f"{char * width}")


def demo_basic_functionality():
    """演示基本功能"""
    print_separator("🎯 德州扑克规则覆盖率监控器演示", "=", 70)
    
    # 创建监控器
    print("📋 创建规则覆盖率监控器...")
    monitor = PokerRulesCoverageMonitor()
    
    # 显示规则统计
    total_rules = len(monitor.rule_scenarios)
    categories = {}
    priorities = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    
    for scenario in monitor.rule_scenarios:
        category = scenario.category.value
        categories[category] = categories.get(category, 0) + 1
        priorities[scenario.priority] += 1
    
    print(f"✅ 监控器初始化完成")
    print(f"📊 总规则数: {total_rules}")
    print(f"📈 规则类别分布:")
    for category, count in categories.items():
        print(f"   • {category}: {count} 个规则")
    print(f"🎯 优先级分布:")
    for priority, count in priorities.items():
        print(f"   • {priority}: {count} 个规则")
    
    return monitor


def demo_test_file_scanning(monitor):
    """演示测试文件扫描"""
    print_separator("📁 测试文件扫描", "-", 50)
    
    print("🔍 扫描测试文件...")
    test_files = monitor.scan_test_files("v2/tests")
    
    print(f"✅ 扫描完成，发现 {len(test_files)} 个测试文件")
    
    # 按目录分组显示
    file_groups = {}
    for file_path in test_files:
        path = Path(file_path)
        parent = path.parent.name
        if parent not in file_groups:
            file_groups[parent] = []
        file_groups[parent].append(path.name)
    
    print("📂 测试文件分布:")
    for directory, files in file_groups.items():
        print(f"   📁 {directory}/: {len(files)} 个文件")
        # 显示前3个文件作为示例
        for file in files[:3]:
            print(f"      • {file}")
        if len(files) > 3:
            print(f"      ... 还有 {len(files) - 3} 个文件")


def demo_coverage_analysis(monitor):
    """演示覆盖率分析"""
    print_separator("📊 规则覆盖率分析", "-", 50)
    
    print("🔬 分析测试覆盖率...")
    report = monitor.analyze_test_coverage()
    
    print(f"✅ 分析完成")
    print(f"📈 覆盖率统计:")
    print(f"   • 总规则数: {report.total_rules}")
    print(f"   • 已覆盖: {report.covered_rules}")
    print(f"   • 部分覆盖: {report.partial_rules}")
    print(f"   • 未覆盖: {report.uncovered_rules}")
    print(f"   • 覆盖率: {report.coverage_percentage:.1f}%")
    
    # 显示类别覆盖率
    print("\n📋 按类别覆盖率:")
    for category, stats in report.category_coverage.items():
        status = "✅" if stats['percentage'] == 100 else "⚠️" if stats['percentage'] >= 80 else "❌"
        print(f"   {status} {category}: {stats['covered']}/{stats['total']} ({stats['percentage']:.1f}%)")
    
    # 显示优先级覆盖率
    print("\n🎯 按优先级覆盖率:")
    for priority, stats in report.priority_coverage.items():
        status = "✅" if stats['percentage'] == 100 else "⚠️" if stats['percentage'] >= 80 else "❌"
        print(f"   {status} {priority}: {stats['covered']}/{stats['total']} ({stats['percentage']:.1f}%)")
    
    return report


def demo_detailed_analysis(monitor, report):
    """演示详细分析"""
    print_separator("🔍 详细分析结果", "-", 50)
    
    # 显示未覆盖的高优先级规则
    high_priority_uncovered = [
        s for s in monitor.rule_scenarios 
        if s.priority == "HIGH" and s.coverage_status.value == "not_covered"
    ]
    
    if high_priority_uncovered:
        print("🚨 未覆盖的高优先级规则:")
        for scenario in high_priority_uncovered:
            print(f"   • {scenario.rule_id}: {scenario.description}")
            print(f"     类别: {scenario.category.value}")
            print(f"     要求: {', '.join(scenario.requirements)}")
    else:
        print("✅ 所有高优先级规则都已覆盖！")
    
    # 显示部分覆盖的规则
    partial_covered = [
        s for s in monitor.rule_scenarios 
        if s.coverage_status.value == "partial"
    ]
    
    if partial_covered:
        print(f"\n⚠️ 部分覆盖的规则 ({len(partial_covered)} 个):")
        for scenario in partial_covered[:3]:  # 只显示前3个
            print(f"   • {scenario.rule_id}: {scenario.description}")
            print(f"     覆盖测试: {', '.join(scenario.covered_by[:2])}")
            if len(scenario.covered_by) > 2:
                print(f"     ... 还有 {len(scenario.covered_by) - 2} 个测试")
        if len(partial_covered) > 3:
            print(f"   ... 还有 {len(partial_covered) - 3} 个部分覆盖的规则")
    
    # 显示覆盖最好的规则类别
    best_category = max(report.category_coverage.items(), key=lambda x: x[1]['percentage'])
    print(f"\n🏆 覆盖率最高的类别: {best_category[0]} ({best_category[1]['percentage']:.1f}%)")
    
    # 显示需要改进的类别
    worst_category = min(report.category_coverage.items(), key=lambda x: x[1]['percentage'])
    if worst_category[1]['percentage'] < 100:
        print(f"📈 需要改进的类别: {worst_category[0]} ({worst_category[1]['percentage']:.1f}%)")


def demo_missing_scenarios(monitor):
    """演示缺失场景识别"""
    print_separator("🔍 缺失测试场景识别", "-", 50)
    
    missing_scenarios = monitor.get_missing_test_scenarios()
    
    if missing_scenarios:
        print(f"❌ 发现 {len(missing_scenarios)} 个缺失的测试场景:")
        
        # 按优先级分组
        by_priority = {"HIGH": [], "MEDIUM": [], "LOW": []}
        for scenario in missing_scenarios:
            by_priority[scenario.priority].append(scenario)
        
        for priority in ["HIGH", "MEDIUM", "LOW"]:
            scenarios = by_priority[priority]
            if scenarios:
                icon = "🚨" if priority == "HIGH" else "⚠️" if priority == "MEDIUM" else "💡"
                print(f"\n{icon} {priority} 优先级 ({len(scenarios)} 个):")
                for scenario in scenarios:
                    print(f"   • {scenario.rule_id}: {scenario.description}")
                    print(f"     类别: {scenario.category.value}")
                    print(f"     模式: {', '.join(scenario.test_patterns[:3])}")
                    if len(scenario.test_patterns) > 3:
                        print(f"     ... 还有 {len(scenario.test_patterns) - 3} 个模式")
    else:
        print("✅ 所有规则场景都已覆盖！")


def demo_test_suggestions(monitor):
    """演示测试用例建议"""
    print_separator("💡 测试用例建议", "-", 50)
    
    suggestions = monitor.suggest_test_cases()
    
    if suggestions:
        print("📝 建议添加的测试用例:")
        # 只显示前5个建议
        suggestion_lines = suggestions[:20]  # 每个建议大约4行
        for line in suggestion_lines:
            if line.strip():
                print(f"   {line}")
        
        if len(suggestions) > 20:
            print(f"   ... 还有更多建议 (总共 {len(suggestions)} 行)")
    else:
        print("✅ 当前不需要添加新的测试用例！")


def demo_report_export(monitor):
    """演示报告导出"""
    print_separator("📄 报告导出", "-", 50)
    
    # 导出JSON报告
    json_file = "test-reports/demo-poker-rules-coverage.json"
    monitor.export_coverage_report(json_file)
    print(f"📊 JSON报告已导出到: {json_file}")
    
    # 生成文本报告
    text_report = monitor.generate_coverage_report_text()
    
    # 保存文本报告
    text_file = "test-reports/demo-poker-rules-coverage.txt"
    Path(text_file).parent.mkdir(parents=True, exist_ok=True)
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(text_report)
    print(f"📝 文本报告已保存到: {text_file}")
    
    # 显示报告摘要
    lines = text_report.split('\n')
    summary_lines = lines[:15]  # 显示前15行作为摘要
    print("\n📋 报告摘要:")
    for line in summary_lines:
        if line.strip():
            print(f"   {line}")


def demo_performance_metrics(monitor):
    """演示性能指标"""
    print_separator("⚡ 性能指标", "-", 50)
    
    import time
    
    # 测量扫描性能
    start_time = time.time()
    test_files = monitor.scan_test_files("v2/tests")
    scan_time = time.time() - start_time
    
    # 测量分析性能
    start_time = time.time()
    report = monitor.analyze_test_coverage()
    analysis_time = time.time() - start_time
    
    # 测量报告生成性能
    start_time = time.time()
    text_report = monitor.generate_coverage_report_text()
    report_time = time.time() - start_time
    
    print(f"📊 性能统计:")
    print(f"   • 文件扫描: {scan_time:.3f}s ({len(test_files)} 个文件)")
    print(f"   • 覆盖率分析: {analysis_time:.3f}s ({len(monitor.rule_scenarios)} 个规则)")
    print(f"   • 报告生成: {report_time:.3f}s ({len(text_report)} 字符)")
    print(f"   • 总耗时: {scan_time + analysis_time + report_time:.3f}s")
    
    # 计算效率指标
    files_per_second = len(test_files) / scan_time if scan_time > 0 else 0
    rules_per_second = len(monitor.rule_scenarios) / analysis_time if analysis_time > 0 else 0
    
    print(f"📈 效率指标:")
    print(f"   • 文件扫描速度: {files_per_second:.1f} 文件/秒")
    print(f"   • 规则分析速度: {rules_per_second:.1f} 规则/秒")


def main():
    """主演示函数"""
    try:
        # 基本功能演示
        monitor = demo_basic_functionality()
        
        # 测试文件扫描演示
        demo_test_file_scanning(monitor)
        
        # 覆盖率分析演示
        report = demo_coverage_analysis(monitor)
        
        # 详细分析演示
        demo_detailed_analysis(monitor, report)
        
        # 缺失场景识别演示
        demo_missing_scenarios(monitor)
        
        # 测试用例建议演示
        demo_test_suggestions(monitor)
        
        # 报告导出演示
        demo_report_export(monitor)
        
        # 性能指标演示
        demo_performance_metrics(monitor)
        
        # 总结
        print_separator("🎉 演示完成", "=", 70)
        print("✅ 德州扑克规则覆盖率监控器演示成功完成！")
        print("📊 主要功能:")
        print("   • ✅ 规则场景管理 (29个规则)")
        print("   • ✅ 测试文件扫描")
        print("   • ✅ 覆盖率分析")
        print("   • ✅ 缺失场景识别")
        print("   • ✅ 测试用例建议")
        print("   • ✅ 多格式报告导出")
        print("   • ✅ 性能监控")
        print("\n💡 建议:")
        if report.coverage_percentage >= 95:
            print("   🏆 覆盖率优秀！继续保持测试质量")
        elif report.coverage_percentage >= 80:
            print("   📈 覆盖率良好，建议补充缺失的测试场景")
        else:
            print("   🚨 覆盖率偏低，建议优先补充高优先级规则的测试")
        
        print(f"\n📈 当前覆盖率: {report.coverage_percentage:.1f}%")
        print("🎯 目标覆盖率: 95%+")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 