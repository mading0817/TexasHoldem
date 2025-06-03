"""
AI公平性约束验证系统演示脚本

演示AI公平性监控器的功能，包括：
1. 监控AI访问游戏状态
2. 检测作弊行为
3. 生成公平性报告
4. 大规模测试验证
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v2.tests.meta.ai_fairness_monitor import AIFairnessMonitor, AccessType, ViolationType
from v2.core import GameState, Player, Card, Suit, Rank, Phase, SeatStatus
from v2.ai.simple_ai import SimpleAI


class CheatingAI:
    """作弊AI示例 - 用于演示监控器检测能力"""
    
    def __init__(self):
        self.name = "CheatingAI"
        
    def decide(self, game_snapshot, player_id):
        """作弊AI决策 - 尝试访问不应该访问的信息"""
        from v2.core import Action, ActionType
        
        # 尝试访问私有信息（这会被监控器检测到）
        try:
            # 尝试访问对手底牌（模拟）
            for player in game_snapshot.players:
                if player.seat_id != player_id:
                    # 这里模拟尝试访问对手底牌
                    _ = getattr(player, '_secret_cards', None)
                    
            # 尝试访问私有游戏状态
            _ = getattr(game_snapshot, '_private_state', None)
            
            # 尝试访问牌堆信息
            _ = getattr(game_snapshot, 'deck_remaining', None)
            
        except AttributeError:
            pass  # 忽略属性不存在的错误
            
        # 最终还是要做出合法决策
        return Action(player_id=player_id, action_type=ActionType.FOLD)


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('ai_fairness_demo.log')
        ]
    )


def demo_basic_monitoring():
    """演示基本监控功能"""
    print("\n" + "="*60)
    print("🔍 演示1: 基本AI访问监控")
    print("="*60)
    
    monitor = AIFairnessMonitor()
    ai_strategy = SimpleAI()
    ai_player_id = 1
    
    # 注册AI
    monitor.register_ai(ai_player_id, ai_strategy)
    
    # 创建测试游戏状态
    game_state = GameState()
    
    # 添加玩家
    ai_player = Player(seat_id=ai_player_id, name="SimpleAI", chips=1000)
    opponent = Player(seat_id=2, name="Opponent", chips=1000)
    game_state.add_player(ai_player)
    game_state.add_player(opponent)
    
    # 初始化牌堆并发牌
    game_state.initialize_deck(seed=42)
    game_state.deal_hole_cards()
    
    # 创建快照并监控AI决策
    snapshot = game_state.create_snapshot()
    print(f"📊 游戏状态: {snapshot.phase.name}, 底池: {snapshot.pot}")
    
    # 监控AI决策
    decision = monitor.monitor_ai_decision(ai_strategy, snapshot, ai_player_id)
    print(f"🤖 AI决策: {decision.action_type.name}")
    
    # 生成报告
    report = monitor.generate_fairness_report(ai_player_id)
    print(f"📈 访问统计: 总计{report.total_accesses}, 合法{report.legal_accesses}, 非法{report.illegal_accesses}")
    print(f"🏆 公平性分数: {report.fairness_score:.2f} ({'公平' if report.is_fair else '不公平'})")
    
    return monitor, report


def demo_cheating_detection():
    """演示作弊检测功能"""
    print("\n" + "="*60)
    print("🚨 演示2: 作弊AI检测")
    print("="*60)
    
    monitor = AIFairnessMonitor()
    cheating_ai = CheatingAI()
    ai_player_id = 1
    
    # 注册作弊AI
    monitor.register_ai(ai_player_id, cheating_ai)
    
    # 创建测试游戏状态
    game_state = GameState()
    
    # 添加玩家
    ai_player = Player(seat_id=ai_player_id, name="CheatingAI", chips=1000)
    opponent = Player(seat_id=2, name="Opponent", chips=1000)
    game_state.add_player(ai_player)
    game_state.add_player(opponent)
    
    # 初始化牌堆并发牌
    game_state.initialize_deck(seed=42)
    game_state.deal_hole_cards()
    
    # 创建快照并监控AI决策
    snapshot = game_state.create_snapshot()
    print(f"📊 游戏状态: {snapshot.phase.name}, 底池: {snapshot.pot}")
    
    # 监控作弊AI决策
    try:
        decision = monitor.monitor_ai_decision(cheating_ai, snapshot, ai_player_id)
        print(f"🤖 作弊AI决策: {decision.action_type.name}")
    except Exception as e:
        print(f"❌ AI决策异常: {e}")
    
    # 生成报告
    report = monitor.generate_fairness_report(ai_player_id)
    print(f"📈 访问统计: 总计{report.total_accesses}, 合法{report.legal_accesses}, 非法{report.illegal_accesses}, 可疑{report.suspicious_accesses}")
    print(f"🏆 公平性分数: {report.fairness_score:.2f} ({'公平' if report.is_fair else '不公平'})")
    
    # 检测作弊模式
    patterns = monitor.detect_cheating_patterns(ai_player_id)
    if patterns:
        print(f"🚨 检测到 {len(patterns)} 种作弊模式:")
        for pattern in patterns:
            print(f"  - {pattern['type']}: {pattern['description']} (严重程度: {pattern['severity']})")
    else:
        print("✅ 未检测到明显的作弊模式")
    
    return monitor, report


def demo_large_scale_test():
    """演示大规模公平性测试"""
    print("\n" + "="*60)
    print("🎯 演示3: 大规模公平性测试")
    print("="*60)
    
    monitor = AIFairnessMonitor()
    ai_strategy = SimpleAI()
    
    print("🚀 开始大规模测试 (100手牌)...")
    
    # 运行大规模测试
    report = monitor.run_large_scale_fairness_test(ai_strategy, num_hands=100)
    
    print(f"📊 测试完成!")
    print(f"🎮 总决策次数: {report.total_decisions}")
    print(f"👁️ 总访问次数: {report.total_accesses}")
    print(f"✅ 合法访问: {report.legal_accesses} ({report.legal_accesses/report.total_accesses*100:.1f}%)")
    print(f"❌ 非法访问: {report.illegal_accesses} ({report.illegal_accesses/report.total_accesses*100:.1f}%)")
    print(f"⚠️ 可疑访问: {report.suspicious_accesses} ({report.suspicious_accesses/report.total_accesses*100:.1f}%)")
    print(f"🏆 公平性分数: {report.fairness_score:.3f}")
    print(f"🎖️ 公平性评级: {'公平' if report.is_fair else '不公平'}")
    
    # 违规类型统计
    if report.violations_by_type:
        print(f"\n📋 违规类型统计:")
        for violation_type, count in report.violations_by_type.items():
            print(f"  - {violation_type.value}: {count} 次")
    else:
        print("✨ 无违规行为检测到!")
    
    return monitor, report


def demo_report_export():
    """演示报告导出功能"""
    print("\n" + "="*60)
    print("📄 演示4: 公平性报告导出")
    print("="*60)
    
    monitor = AIFairnessMonitor()
    ai_strategy = SimpleAI()
    
    # 运行小规模测试
    report = monitor.run_large_scale_fairness_test(ai_strategy, num_hands=10)
    
    # 导出报告
    report_dir = Path("test-reports")
    report_dir.mkdir(exist_ok=True)
    
    report_file = report_dir / "ai_fairness_demo_report.json"
    monitor.export_fairness_report(report, str(report_file))
    
    print(f"📁 报告已导出到: {report_file}")
    print(f"📊 报告大小: {report_file.stat().st_size} 字节")
    
    # 显示报告摘要
    stats = monitor.get_summary_stats()
    print(f"\n📈 监控统计摘要:")
    print(f"  - 总记录数: {stats['total_records']}")
    print(f"  - 合法访问比例: {stats['legal_ratio']:.1%}")
    print(f"  - 非法访问比例: {stats['illegal_ratio']:.1%}")
    print(f"  - 可疑访问比例: {stats['suspicious_ratio']:.1%}")
    print(f"  - 监控AI数量: {len(stats['monitored_ais'])}")
    
    return report_file


def demo_access_pattern_analysis():
    """演示访问模式分析"""
    print("\n" + "="*60)
    print("🔬 演示5: 访问模式分析")
    print("="*60)
    
    monitor = AIFairnessMonitor()
    ai_strategy = SimpleAI()
    ai_player_id = 1
    
    # 注册AI并进行多次决策
    monitor.register_ai(ai_player_id, ai_strategy)
    
    for i in range(5):
        # 创建不同的游戏状态
        game_state = GameState()
        
        ai_player = Player(seat_id=ai_player_id, name="SimpleAI", chips=1000)
        opponent = Player(seat_id=2, name="Opponent", chips=1000)
        game_state.add_player(ai_player)
        game_state.add_player(opponent)
        
        game_state.initialize_deck(seed=i)
        game_state.deal_hole_cards()
        
        # 模拟不同阶段
        if i >= 2:
            game_state.advance_phase()
            game_state.deal_community_cards(3)
        if i >= 4:
            game_state.advance_phase()
            game_state.deal_community_cards(1)
            
        snapshot = game_state.create_snapshot()
        monitor.monitor_ai_decision(ai_strategy, snapshot, ai_player_id)
        
        print(f"🎮 第{i+1}次决策 - 阶段: {snapshot.phase.name}")
    
    # 分析访问模式
    report = monitor.generate_fairness_report(ai_player_id)
    
    print(f"\n📊 访问模式分析:")
    print(f"  - 平均每次决策访问次数: {report.total_accesses / max(1, report.total_decisions):.1f}")
    
    # 统计最常访问的属性
    attribute_counts = {}
    for record in report.access_records:
        attr = record.accessed_attribute
        attribute_counts[attr] = attribute_counts.get(attr, 0) + 1
    
    print(f"  - 最常访问的属性:")
    sorted_attrs = sorted(attribute_counts.items(), key=lambda x: x[1], reverse=True)
    for attr, count in sorted_attrs[:5]:
        print(f"    * {attr}: {count} 次")
    
    return monitor, report


def main():
    """主演示函数"""
    print("🎮 AI公平性约束验证系统演示")
    print("=" * 60)
    
    # 设置日志
    setup_logging()
    
    try:
        # 演示1: 基本监控
        demo_basic_monitoring()
        
        # 演示2: 作弊检测
        demo_cheating_detection()
        
        # 演示3: 大规模测试
        demo_large_scale_test()
        
        # 演示4: 报告导出
        report_file = demo_report_export()
        
        # 演示5: 访问模式分析
        demo_access_pattern_analysis()
        
        print("\n" + "="*60)
        print("🎉 所有演示完成!")
        print("="*60)
        print(f"📁 详细报告已保存到: {report_file}")
        print("📋 日志文件: ai_fairness_demo.log")
        print("\n✨ AI公平性约束验证系统演示成功!")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        logging.error(f"Demo error: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 