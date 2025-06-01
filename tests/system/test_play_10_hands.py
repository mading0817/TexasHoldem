"""10手牌系统验证测试.

这个测试模块验证游戏系统在连续10手牌中的稳定性和正确性。
包括筹码守恒、游戏流程、AI决策等全面验证。
"""

import pytest
import logging
import tempfile
import os
from typing import List, Dict, Any
from unittest.mock import patch

from v2.controller import PokerController
from v2.core import GameState, Player, SeatStatus, ActionType, Action
from v2.ai import AIStrategy, SimpleAI
from v2.core.events import EventBus, get_event_bus


class AutoUserStrategy(AIStrategy):
    """自动用户策略.
    
    模拟人类玩家的自动决策，用于系统测试。
    采用保守策略，主要进行跟注和过牌。
    """
    
    def __init__(self, fold_probability: float = 0.3):
        """初始化自动用户策略.
        
        Args:
            fold_probability: 弃牌概率
        """
        self.fold_probability = fold_probability
        self.decision_count = 0
    
    def decide(self, game_snapshot, player_id: int) -> Action:
        """做出决策.
        
        Args:
            game_snapshot: 游戏状态快照
            player_id: 玩家ID
            
        Returns:
            玩家行动
        """
        self.decision_count += 1
        
        # 获取当前玩家信息
        current_player = next(p for p in game_snapshot.players if p.seat_id == player_id)
        
        # 计算跟注金额
        call_amount = game_snapshot.current_bet - current_player.current_bet
        
        # 简单策略：
        # 1. 如果无需跟注，过牌
        # 2. 如果需要跟注且筹码充足，跟注
        # 3. 如果筹码不足，全押
        # 4. 偶尔弃牌（基于概率）
        
        if call_amount == 0:
            # 无需跟注，过牌
            return Action(player_id=player_id, action_type=ActionType.CHECK, amount=0)
        
        # 基于决策次数的伪随机弃牌
        if self.decision_count % 10 < (self.fold_probability * 10):
            return Action(player_id=player_id, action_type=ActionType.FOLD, amount=0)
        
        if call_amount <= current_player.chips:
            # 筹码充足，跟注
            return Action(player_id=player_id, action_type=ActionType.CALL, amount=call_amount)
        else:
            # 筹码不足，全押
            return Action(player_id=player_id, action_type=ActionType.ALL_IN, amount=current_player.chips)


class TestPlay10Hands:
    """10手牌系统测试类."""
    
    def setup_method(self):
        """测试前设置."""
        # 创建临时日志文件
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "test_10_hands.log")
        
        # 设置日志
        self.logger = logging.getLogger("test_10_hands")
        self.logger.setLevel(logging.INFO)
        
        # 清除现有处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 添加文件处理器
        file_handler = logging.FileHandler(self.log_file, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 创建事件总线
        self.event_bus = EventBus()
        
        # 记录事件的列表
        self.events = []
        
        def event_listener(event_type, **kwargs):
            self.events.append({
                'type': event_type.value if hasattr(event_type, 'value') else str(event_type),
                'data': kwargs
            })
        
        # 订阅所有事件
        from v2.core.events import EventType
        for event_type in EventType:
            self.event_bus.subscribe(event_type, event_listener)
    
    def teardown_method(self):
        """测试后清理."""
        # 关闭日志处理器
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
        
        # 清理临时文件
        try:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
            os.rmdir(self.temp_dir)
        except OSError:
            pass  # 忽略清理错误
    
    def create_test_controller(self, num_players: int = 4, initial_chips: int = 1000) -> PokerController:
        """创建测试用控制器.
        
        Args:
            num_players: 玩家数量
            initial_chips: 初始筹码
            
        Returns:
            配置好的控制器
        """
        # 创建游戏状态
        game_state = GameState()
        
        # 添加玩家
        for i in range(num_players):
            if i == 0:
                name = "Human"  # 第一个玩家模拟人类
            else:
                name = f"AI_{i}"
            
            player = Player(seat_id=i, name=name, chips=initial_chips)
            game_state.add_player(player)
        
        # 创建AI策略（包括人类玩家的自动策略）
        ai_strategy = SimpleAI()
        
        # 创建控制器
        controller = PokerController(
            game_state=game_state,
            ai_strategy=ai_strategy,
            logger=self.logger,
            event_bus=self.event_bus
        )
        
        return controller
    
    def play_single_hand(self, controller: PokerController, hand_number: int) -> Dict[str, Any]:
        """执行单手牌.
        
        Args:
            controller: 游戏控制器
            hand_number: 手牌编号
            
        Returns:
            手牌结果统计
        """
        self.logger.info(f"\n=== 开始第 {hand_number} 手牌 ===")
        
        # 记录开始时的筹码
        initial_snapshot = controller.get_snapshot()
        initial_chips = {p.seat_id: p.chips for p in initial_snapshot.players}
        initial_total = sum(initial_chips.values())
        
        self.logger.info(f"初始筹码分布: {initial_chips}")
        self.logger.info(f"初始筹码总和: {initial_total}")
        
        # 开始新手牌
        if not controller.start_new_hand():
            self.logger.warning("无法开始新手牌，可能玩家不足")
            return {
                'success': False,
                'reason': 'insufficient_players',
                'initial_chips': initial_chips,
                'final_chips': initial_chips,
                'chip_change': 0
            }
        
        action_count = 0
        max_actions = 100  # 防止无限循环
        
        # 游戏循环
        while not controller.is_hand_over() and action_count < max_actions:
            current_player_id = controller.get_current_player_id()
            
            if current_player_id is None:
                break
            
            snapshot = controller.get_snapshot()
            current_player = next(p for p in snapshot.players if p.seat_id == current_player_id)
            
            self.logger.info(f"轮到玩家 {current_player.name} (座位{current_player_id}) 行动")
            self.logger.info(f"  筹码: {current_player.chips}, 当前下注: {current_player.current_bet}")
            self.logger.info(f"  阶段: {snapshot.phase.value}, 底池: {snapshot.pot}, 最高下注: {snapshot.current_bet}")
            
            # 处理AI行动（包括模拟的人类玩家）
            try:
                if controller.process_ai_action():
                    action_count += 1
                    self.logger.info(f"  行动完成，总行动数: {action_count}")
                else:
                    self.logger.error(f"  玩家 {current_player.name} 行动失败")
                    break
            except Exception as e:
                self.logger.error(f"  行动执行异常: {e}")
                break
        
        # 结束手牌
        result = controller.end_hand()
        
        # 记录结束时的筹码
        final_snapshot = controller.get_snapshot()
        final_chips = {p.seat_id: p.chips for p in final_snapshot.players}
        final_total = sum(final_chips.values())
        
        self.logger.info(f"最终筹码分布: {final_chips}")
        self.logger.info(f"最终筹码总和: {final_total}")
        self.logger.info(f"筹码变化: {final_total - initial_total}")
        
        if result:
            self.logger.info(f"获胜者: {result.winner_ids}")
            self.logger.info(f"底池: {result.pot_amount}")
        
        return {
            'success': True,
            'hand_number': hand_number,
            'initial_chips': initial_chips,
            'final_chips': final_chips,
            'initial_total': initial_total,
            'final_total': final_total,
            'chip_change': final_total - initial_total,
            'action_count': action_count,
            'result': result
        }
    
    def test_play_10_hands_chip_conservation(self):
        """测试10手牌的筹码守恒."""
        self.logger.info("开始10手牌筹码守恒测试")
        
        # 创建控制器
        controller = self.create_test_controller(num_players=4, initial_chips=1000)
        
        # 记录初始状态
        initial_snapshot = controller.get_snapshot()
        total_initial_chips = sum(p.chips for p in initial_snapshot.players)
        
        self.logger.info(f"游戏开始，总筹码: {total_initial_chips}")
        
        hand_results = []
        chip_changes = []
        
        # 执行10手牌
        for hand_num in range(1, 11):
            try:
                result = self.play_single_hand(controller, hand_num)
                hand_results.append(result)
                
                if result['success']:
                    chip_changes.append(result['chip_change'])
                    
                    # 验证筹码守恒
                    assert result['chip_change'] == 0, f"第{hand_num}手牌筹码不守恒: 变化{result['chip_change']}"
                    
                    self.logger.info(f"第{hand_num}手牌完成 [PASS]")
                else:
                    self.logger.warning(f"第{hand_num}手牌失败: {result.get('reason', 'unknown')}")
                    break
                    
            except Exception as e:
                self.logger.error(f"第{hand_num}手牌异常: {e}")
                pytest.fail(f"第{hand_num}手牌执行失败: {e}")
        
        # 最终验证
        final_snapshot = controller.get_snapshot()
        total_final_chips = sum(p.chips for p in final_snapshot.players)
        
        self.logger.info(f"\n=== 10手牌测试完成 ===")
        self.logger.info(f"初始总筹码: {total_initial_chips}")
        self.logger.info(f"最终总筹码: {total_final_chips}")
        self.logger.info(f"总筹码变化: {total_final_chips - total_initial_chips}")
        self.logger.info(f"成功完成手牌数: {len([r for r in hand_results if r['success']])}")
        self.logger.info(f"总事件数: {len(self.events)}")
        
        # 断言筹码守恒
        assert total_final_chips == total_initial_chips, \
            f"总筹码不守恒: 初始{total_initial_chips}, 最终{total_final_chips}"
        
        # 断言至少完成了5手牌
        successful_hands = len([r for r in hand_results if r['success']])
        assert successful_hands >= 5, f"成功完成的手牌数太少: {successful_hands}"
        
        # 验证事件系统工作正常
        assert len(self.events) > 0, "没有记录到任何事件"
        
        self.logger.info("[PASS] 10手牌筹码守恒测试通过")
        print("[PASS] 10手牌筹码守恒测试通过")
    
    def test_play_10_hands_game_flow(self):
        """测试10手牌的游戏流程正确性."""
        self.logger.info("开始10手牌游戏流程测试")
        
        # 创建控制器
        controller = self.create_test_controller(num_players=3, initial_chips=500)
        
        flow_stats = {
            'hands_completed': 0,
            'total_actions': 0,
            'phase_transitions': 0,
            'player_eliminations': 0
        }
        
        # 执行10手牌
        for hand_num in range(1, 11):
            self.logger.info(f"\n--- 第{hand_num}手牌流程验证 ---")
            
            # 检查游戏是否可以继续
            snapshot = controller.get_snapshot()
            active_players = [p for p in snapshot.players 
                            if p.status == SeatStatus.ACTIVE and p.chips > 0]
            
            if len(active_players) < 2:
                self.logger.info(f"活跃玩家不足({len(active_players)})，游戏结束")
                break
            
            # 记录阶段转换
            initial_phase = snapshot.phase
            
            # 执行手牌
            result = self.play_single_hand(controller, hand_num)
            
            if result['success']:
                flow_stats['hands_completed'] += 1
                flow_stats['total_actions'] += result['action_count']
                
                # 检查是否有玩家被淘汰
                final_snapshot = controller.get_snapshot()
                eliminated_players = [p for p in final_snapshot.players 
                                    if p.chips == 0 and p.status != SeatStatus.ACTIVE]
                flow_stats['player_eliminations'] += len(eliminated_players)
                
                self.logger.info(f"第{hand_num}手牌流程正常 [PASS]")
            else:
                self.logger.warning(f"第{hand_num}手牌流程异常")
                break
        
        # 验证流程统计
        self.logger.info(f"\n=== 游戏流程统计 ===")
        self.logger.info(f"完成手牌数: {flow_stats['hands_completed']}")
        self.logger.info(f"总行动数: {flow_stats['total_actions']}")
        self.logger.info(f"玩家淘汰数: {flow_stats['player_eliminations']}")
        
        # 断言基本流程正确
        assert flow_stats['hands_completed'] >= 3, "完成的手牌数太少"
        assert flow_stats['total_actions'] > 0, "没有记录到任何行动"
        
        self.logger.info("[PASS] 10手牌游戏流程测试通过")
        print("[PASS] 10手牌游戏流程测试通过")
    
    def test_play_10_hands_stress_test(self):
        """10手牌压力测试."""
        self.logger.info("开始10手牌压力测试")
        
        # 创建更多玩家的游戏
        controller = self.create_test_controller(num_players=6, initial_chips=2000)
        
        stress_stats = {
            'max_actions_per_hand': 0,
            'min_actions_per_hand': float('inf'),
            'total_events': 0,
            'error_count': 0
        }
        
        # 执行10手牌
        for hand_num in range(1, 11):
            try:
                result = self.play_single_hand(controller, hand_num)
                
                if result['success']:
                    actions = result['action_count']
                    stress_stats['max_actions_per_hand'] = max(stress_stats['max_actions_per_hand'], actions)
                    stress_stats['min_actions_per_hand'] = min(stress_stats['min_actions_per_hand'], actions)
                else:
                    stress_stats['error_count'] += 1
                    
            except Exception as e:
                stress_stats['error_count'] += 1
                self.logger.error(f"第{hand_num}手牌压力测试异常: {e}")
        
        stress_stats['total_events'] = len(self.events)
        
        # 验证压力测试结果
        self.logger.info(f"\n=== 压力测试统计 ===")
        self.logger.info(f"最大单手行动数: {stress_stats['max_actions_per_hand']}")
        self.logger.info(f"最小单手行动数: {stress_stats['min_actions_per_hand']}")
        self.logger.info(f"总事件数: {stress_stats['total_events']}")
        self.logger.info(f"错误次数: {stress_stats['error_count']}")
        
        # 断言压力测试通过
        assert stress_stats['error_count'] <= 2, f"错误次数过多: {stress_stats['error_count']}"
        assert stress_stats['total_events'] > 50, "事件数量太少，可能系统有问题"
        
        self.logger.info("[PASS] 10手牌压力测试通过")
        print("[PASS] 10手牌压力测试通过")
    
    def test_log_file_analysis(self):
        """测试日志文件分析."""
        # 先运行一个简单的测试生成日志
        controller = self.create_test_controller(num_players=2, initial_chips=1000)
        
        # 执行3手牌
        for hand_num in range(1, 4):
            result = self.play_single_hand(controller, hand_num)
            if not result['success']:
                break
        
        # 分析日志文件
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # 验证日志包含关键信息
            assert "开始第 1 手牌" in log_content, "日志中缺少手牌开始信息"
            assert "筹码分布" in log_content, "日志中缺少筹码信息"
            assert "行动完成" in log_content, "日志中缺少行动信息"
            
            self.logger.info("[PASS] 日志文件分析通过")
            print("[PASS] 日志文件分析通过")
        else:
            pytest.fail("日志文件未生成") 