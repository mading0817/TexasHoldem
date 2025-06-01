#!/usr/bin/env python3
"""
Streamlit UI流程验证测试 - Texas Hold'em Poker Game v2

专门测试修复后的Streamlit UI流程问题：
1. 验证阶段转换不再跳跃
2. 验证事件记录完整匹配
3. 验证AI行动正确记录
4. 模拟真实用户操作流程

Author: Texas Hold'em v2 Team
Version: 1.0
Date: 2024
"""

import sys
import os
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.enums import ActionType, Phase, SeatStatus
from v2.core.state import GameState
from v2.core.player import Player
from v2.core.enums import Action


class UIFlowValidator:
    """Streamlit UI流程验证器."""
    
    def __init__(self):
        """初始化验证器."""
        self.controller: Optional[PokerController] = None
        self.logger = logging.getLogger(__name__)
        self.test_results = []
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def setup_game(self) -> bool:
        """设置游戏环境."""
        try:
            # 创建游戏状态和控制器
            game_state = GameState()
            ai_strategy = SimpleAI()
            logger = logging.getLogger('poker_controller')
            
            self.controller = PokerController(
                game_state=game_state,
                ai_strategy=ai_strategy,
                logger=logger
            )
            
            # 添加4个玩家：1个人类玩家 + 3个AI玩家
            for i in range(4):
                name = "Human" if i == 0 else f"AI_{i}"
                player = Player(
                    seat_id=i,
                    name=name,
                    chips=1000
                )
                # 标记人类玩家
                if i == 0:
                    player.is_human = True
                
                self.controller._game_state.add_player(player)
            
            self.logger.info(f"游戏设置完成，{len(self.controller._game_state.players)}个玩家")
            return True
            
        except Exception as e:
            self.logger.error(f"游戏设置失败: {e}")
            return False
    
    def simulate_user_action(self, available_actions: List[ActionType]) -> Action:
        """模拟用户的合理行动选择."""
        # 获取当前游戏状态
        snapshot = self.controller.get_snapshot()
        human_player = snapshot.players[0]  # 假设玩家0是人类
        
        # 优先选择跟注或过牌，避免过于激进的行动
        if ActionType.CHECK in available_actions:
            return Action(ActionType.CHECK, 0, 0)
        
        if ActionType.CALL in available_actions:
            return Action(ActionType.CALL, 0, 0)
        
        # 如果必须下注，选择最小下注
        if ActionType.BET in available_actions:
            return Action(ActionType.BET, 10, 0)
        
        # 最后选择弃牌
        return Action(ActionType.FOLD, 0, 0)
    
    def get_available_actions(self, player_id: int) -> List[ActionType]:
        """获取玩家可用的行动类型."""
        snapshot = self.controller.get_snapshot()
        player = snapshot.players[player_id]
        available_actions = []
        
        # 总是可以弃牌
        available_actions.append(ActionType.FOLD)
        
        # 检查是否可以过牌或跟注
        if snapshot.current_bet == 0 or snapshot.current_bet == player.current_bet:
            available_actions.append(ActionType.CHECK)
        elif snapshot.current_bet > player.current_bet:
            available_actions.append(ActionType.CALL)
        
        # 检查是否可以下注或加注
        if player.chips > snapshot.current_bet - player.current_bet:
            if snapshot.current_bet == 0:
                available_actions.append(ActionType.BET)
            else:
                available_actions.append(ActionType.RAISE)
        
        return available_actions
    
    def test_single_hand_flow(self, hand_number: int) -> Dict[str, Any]:
        """测试单手牌的完整流程."""
        self.logger.info(f"开始测试第{hand_number}手牌流程")
        
        # 记录初始状态
        initial_snapshot = self.controller.get_snapshot()
        initial_phase = initial_snapshot.phase
        initial_events = len(initial_snapshot.events)
        
        # 开始新手牌
        success = self.controller.start_new_hand()
        if not success:
            return {
                'hand_number': hand_number,
                'success': False,
                'error': '无法开始新手牌',
                'phases_reached': [],
                'events_recorded': 0,
                'actions_taken': 0
            }
        
        phases_reached = []
        events_recorded = []
        actions_taken = 0
        max_actions = 50  # 防止无限循环
        
        # 游戏主循环
        while not self.controller.is_hand_over() and actions_taken < max_actions:
            current_snapshot = self.controller.get_snapshot()
            
            # 记录达到的阶段
            if current_snapshot.phase not in phases_reached:
                phases_reached.append(current_snapshot.phase)
                self.logger.info(f"第{hand_number}手牌进入{current_snapshot.phase.value}阶段")
            
            # 记录新事件
            if len(current_snapshot.events) > len(events_recorded):
                new_events = current_snapshot.events[len(events_recorded):]
                events_recorded.extend(new_events)
                for event in new_events:
                    self.logger.info(f"第{hand_number}手牌事件: {event}")
            
            current_player_id = self.controller.get_current_player_id()
            if current_player_id is None:
                break
            
            # 执行玩家行动
            if current_player_id == 0:  # 人类玩家
                available_actions = self.get_available_actions(current_player_id)
                action = self.simulate_user_action(available_actions)
                
                try:
                    self.controller.execute_action(action)
                    actions_taken += 1
                    self.logger.info(f"第{hand_number}手牌人类玩家执行{action.action_type.value}")
                except Exception as e:
                    self.logger.warning(f"第{hand_number}手牌人类玩家行动失败: {e}")
                    break
            else:  # AI玩家
                success = self.controller.process_ai_action()
                if success:
                    actions_taken += 1
                    self.logger.info(f"第{hand_number}手牌AI玩家{current_player_id}执行行动")
                else:
                    self.logger.warning(f"第{hand_number}手牌AI玩家{current_player_id}行动失败")
                    break
            
            time.sleep(0.01)  # 短暂延迟
        
        # 结束手牌
        if self.controller.is_hand_over():
            try:
                hand_result = self.controller.end_hand()
                winner_ids = hand_result.winner_ids if hand_result else []
                pot_amount = hand_result.pot_amount if hand_result else 0
            except Exception as e:
                self.logger.warning(f"第{hand_number}手牌结束时出错: {e}")
                winner_ids = []
                pot_amount = 0
        else:
            self.logger.warning(f"第{hand_number}手牌未正常结束")
            winner_ids = []
            pot_amount = 0
        
        # 记录最终事件
        final_snapshot = self.controller.get_snapshot()
        if len(final_snapshot.events) > len(events_recorded):
            new_events = final_snapshot.events[len(events_recorded):]
            events_recorded.extend(new_events)
        
        return {
            'hand_number': hand_number,
            'success': True,
            'phases_reached': [p.value for p in phases_reached],
            'events_recorded': len(events_recorded),
            'actions_taken': actions_taken,
            'winner_ids': winner_ids,
            'pot_amount': pot_amount,
            'phase_sequence_valid': self.validate_phase_sequence(phases_reached),
            'events_list': events_recorded
        }
    
    def validate_phase_sequence(self, phases: List[Phase]) -> bool:
        """验证阶段序列是否正确."""
        if not phases:
            return False
        
        # 检查是否以PRE_FLOP开始
        if phases[0] != Phase.PRE_FLOP:
            return False
        
        # 检查阶段顺序
        phase_order = [Phase.PRE_FLOP, Phase.FLOP, Phase.TURN, Phase.RIVER, Phase.SHOWDOWN]
        
        for i in range(1, len(phases)):
            prev_phase = phases[i-1]
            curr_phase = phases[i]
            
            prev_index = phase_order.index(prev_phase)
            curr_index = phase_order.index(curr_phase)
            
            # 检查是否按正确顺序进行
            if curr_index != prev_index + 1:
                return False
        
        return True
    
    def run_flow_validation(self, num_hands: int = 5) -> Dict[str, Any]:
        """运行完整的流程验证测试."""
        start_time = time.time()
        self.logger.info(f"开始Streamlit UI流程验证测试，计划进行{num_hands}手牌")
        
        # 设置游戏
        if not self.setup_game():
            return {
                'success': False,
                'error': '游戏设置失败',
                'total_time': time.time() - start_time
            }
        
        # 进行多手牌测试
        hand_results = []
        successful_hands = 0
        phase_jump_issues = 0
        event_recording_issues = 0
        
        for hand_num in range(1, num_hands + 1):
            try:
                result = self.test_single_hand_flow(hand_num)
                hand_results.append(result)
                
                if result['success']:
                    successful_hands += 1
                    
                    # 检查阶段跳跃问题
                    if not result['phase_sequence_valid']:
                        phase_jump_issues += 1
                        self.logger.warning(f"第{hand_num}手牌阶段序列无效: {result['phases_reached']}")
                    
                    # 检查事件记录问题
                    if result['events_recorded'] < result['actions_taken']:
                        event_recording_issues += 1
                        self.logger.warning(f"第{hand_num}手牌事件记录不足: {result['events_recorded']}/{result['actions_taken']}")
                    
                    # 检查是否有阶段跳跃（从PRE_FLOP直接到SHOWDOWN）
                    phases = result['phases_reached']
                    if len(phases) == 2 and 'PRE_FLOP' in phases and 'SHOWDOWN' in phases:
                        phase_jump_issues += 1
                        self.logger.warning(f"第{hand_num}手牌疑似阶段跳跃: {phases}")
                
            except Exception as e:
                self.logger.error(f"第{hand_num}手牌测试失败: {e}")
                hand_results.append({
                    'hand_number': hand_num,
                    'success': False,
                    'error': str(e)
                })
        
        # 统计结果
        total_time = time.time() - start_time
        
        # 计算得分
        base_score = (successful_hands / num_hands) * 100
        penalty = (phase_jump_issues * 20) + (event_recording_issues * 10)
        final_score = max(0, base_score - penalty)
        
        # 确定等级
        if final_score >= 90:
            grade = "🏆 优秀"
        elif final_score >= 80:
            grade = "✅ 良好"
        elif final_score >= 70:
            grade = "⚠️ 合格"
        else:
            grade = "❌ 不合格"
        
        result = {
            'success': successful_hands > 0,
            'total_hands': num_hands,
            'successful_hands': successful_hands,
            'phase_jump_issues': phase_jump_issues,
            'event_recording_issues': event_recording_issues,
            'score': final_score,
            'grade': grade,
            'total_time': total_time,
            'hand_results': hand_results
        }
        
        return result
    
    def generate_report(self, result: Dict[str, Any]) -> str:
        """生成详细的验证报告."""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("🎮 Streamlit UI流程验证报告")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # 总体评估
        report_lines.append("📊 总体评估")
        report_lines.append("-" * 40)
        report_lines.append(f"测试结果: {result['grade']}")
        report_lines.append(f"综合得分: {result['score']:.1f}/100")
        report_lines.append(f"成功手牌: {result['successful_hands']}/{result['total_hands']}")
        report_lines.append(f"执行时间: {result['total_time']:.2f}秒")
        report_lines.append("")
        
        # 问题统计
        report_lines.append("🐛 问题统计")
        report_lines.append("-" * 40)
        report_lines.append(f"阶段跳跃问题: {result['phase_jump_issues']}个")
        report_lines.append(f"事件记录问题: {result['event_recording_issues']}个")
        report_lines.append("")
        
        # 详细手牌结果
        if result['hand_results']:
            report_lines.append("📝 详细手牌结果")
            report_lines.append("-" * 40)
            
            for hand_result in result['hand_results']:
                if hand_result['success']:
                    phases_str = " → ".join(hand_result['phases_reached'])
                    valid_icon = "✅" if hand_result['phase_sequence_valid'] else "❌"
                    
                    report_lines.append(f"第{hand_result['hand_number']}手牌: {valid_icon}")
                    report_lines.append(f"  阶段序列: {phases_str}")
                    report_lines.append(f"  行动数量: {hand_result['actions_taken']}")
                    report_lines.append(f"  事件记录: {hand_result['events_recorded']}")
                    report_lines.append(f"  获胜者: {hand_result['winner_ids']}")
                    report_lines.append("")
                else:
                    report_lines.append(f"第{hand_result['hand_number']}手牌: ❌ 失败")
                    if 'error' in hand_result:
                        report_lines.append(f"  错误: {hand_result['error']}")
                    report_lines.append("")
        
        # 修复效果评估
        report_lines.append("🔧 修复效果评估")
        report_lines.append("-" * 40)
        
        if result['phase_jump_issues'] == 0:
            report_lines.append("✅ 阶段跳跃问题已完全修复")
        else:
            report_lines.append(f"⚠️ 仍有{result['phase_jump_issues']}个阶段跳跃问题")
        
        if result['event_recording_issues'] == 0:
            report_lines.append("✅ 事件记录问题已完全修复")
        else:
            report_lines.append(f"⚠️ 仍有{result['event_recording_issues']}个事件记录问题")
        
        report_lines.append("")
        
        # 建议和结论
        report_lines.append("💡 建议与结论")
        report_lines.append("-" * 40)
        
        if result['score'] >= 90:
            report_lines.append("🎉 恭喜！Streamlit UI流程问题已完全修复，可以发布！")
        elif result['score'] >= 80:
            report_lines.append("👍 Streamlit UI流程基本正常，建议修复剩余问题后发布。")
        elif result['score'] >= 70:
            report_lines.append("⚠️ Streamlit UI流程存在一些问题，建议继续修复。")
        else:
            report_lines.append("❌ Streamlit UI流程存在严重问题，必须修复后才能发布。")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)


def main():
    """主函数."""
    print("🚀 启动Streamlit UI流程验证测试...")
    
    # 创建验证器并运行测试
    validator = UIFlowValidator()
    result = validator.run_flow_validation(num_hands=5)
    
    # 生成并显示报告
    report = validator.generate_report(result)
    print(report)
    
    # 保存报告到文件
    with open('streamlit_ui_flow_validation_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n📄 详细报告已保存到 streamlit_ui_flow_validation_report.txt")
    
    # 返回退出码
    if result['score'] >= 80:
        return 0  # 成功
    else:
        return 1  # 失败


if __name__ == "__main__":
    exit(main()) 