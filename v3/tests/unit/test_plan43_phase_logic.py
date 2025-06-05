"""
PLAN 43: 核心层"下一阶段"判断逻辑 - 单元测试

测试核心阶段逻辑模块的功能，确保德州扑克游戏的阶段转换逻辑正确。
"""

import unittest
from unittest.mock import Mock, MagicMock
from typing import List

# 反作弊检查
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker

# 核心模块导入
from v3.core.state_machine.types import GamePhase, GameContext
from v3.core.rules.phase_logic import (
    get_possible_next_phases,
    get_defined_next_phase_for_event,
    get_next_phase_in_sequence,
    get_core_phase_logic_data
)
from v3.core.rules.types import PhaseTransition, CorePhaseLogicData


class TestCorePhaseLogic(unittest.TestCase):
    """测试核心阶段逻辑功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_context = self._create_test_context()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.test_context, "GameContext")
        
    def _create_test_context(self) -> GameContext:
        """创建测试用的游戏上下文"""
        players = {
            'player_1': {'active': True, 'chips': 1000},
            'player_2': {'active': True, 'chips': 1500}
        }
        
        return GameContext(
            game_id="test_game",
            current_phase=GamePhase.PRE_FLOP,
            players=players,
            community_cards=[],
            pot_total=0,
            current_bet=0
        )
    
    def test_get_possible_next_phases_pre_flop(self):
        """测试翻前阶段的可能下一阶段"""
        possible_phases = get_possible_next_phases(GamePhase.PRE_FLOP)
        
        # 反作弊检查
        assert isinstance(possible_phases, list), "必须返回列表类型"
        for phase in possible_phases:
            CoreUsageChecker.verify_real_objects(phase, "GamePhase")
        
        # 翻前可以到翻牌圈或直接结束
        expected_phases = [GamePhase.FLOP, GamePhase.FINISHED]
        self.assertEqual(possible_phases, expected_phases)
    
    def test_get_possible_next_phases_flop(self):
        """测试翻牌阶段的可能下一阶段"""
        possible_phases = get_possible_next_phases(GamePhase.FLOP)
        
        # 反作弊检查
        for phase in possible_phases:
            CoreUsageChecker.verify_real_objects(phase, "GamePhase")
        
        # 翻牌可以到转牌或直接结束
        expected_phases = [GamePhase.TURN, GamePhase.FINISHED]
        self.assertEqual(possible_phases, expected_phases)
    
    def test_get_possible_next_phases_turn(self):
        """测试转牌阶段的可能下一阶段"""
        possible_phases = get_possible_next_phases(GamePhase.TURN)
        
        # 反作弊检查
        for phase in possible_phases:
            CoreUsageChecker.verify_real_objects(phase, "GamePhase")
        
        # 转牌可以到河牌或直接结束
        expected_phases = [GamePhase.RIVER, GamePhase.FINISHED]
        self.assertEqual(possible_phases, expected_phases)
    
    def test_get_possible_next_phases_river(self):
        """测试河牌阶段的可能下一阶段"""
        possible_phases = get_possible_next_phases(GamePhase.RIVER)
        
        # 反作弊检查
        for phase in possible_phases:
            CoreUsageChecker.verify_real_objects(phase, "GamePhase")
        
        # 河牌可以到摊牌或直接结束
        expected_phases = [GamePhase.SHOWDOWN, GamePhase.FINISHED]
        self.assertEqual(possible_phases, expected_phases)
    
    def test_get_possible_next_phases_showdown(self):
        """测试摊牌阶段的可能下一阶段"""
        possible_phases = get_possible_next_phases(GamePhase.SHOWDOWN)
        
        # 反作弊检查
        for phase in possible_phases:
            CoreUsageChecker.verify_real_objects(phase, "GamePhase")
        
        # 摊牌只能结束
        expected_phases = [GamePhase.FINISHED]
        self.assertEqual(possible_phases, expected_phases)
    
    def test_get_possible_next_phases_finished(self):
        """测试结束阶段的可能下一阶段"""
        possible_phases = get_possible_next_phases(GamePhase.FINISHED)
        
        # 反作弊检查
        assert isinstance(possible_phases, list), "必须返回列表类型"
        
        # 结束阶段没有下一阶段
        self.assertEqual(possible_phases, [])
    
    def test_get_possible_next_phases_with_context_one_player(self):
        """测试在只有一个活跃玩家时的阶段转换"""
        # 创建只有一个活跃玩家的上下文
        single_player_context = GameContext(
            game_id="single_player_test",
            current_phase=GamePhase.PRE_FLOP,
            players={'player_1': {'active': True, 'chips': 1000}},
            community_cards=[],
            pot_total=0,
            current_bet=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(single_player_context, "GameContext")
        
        possible_phases = get_possible_next_phases(GamePhase.PRE_FLOP, single_player_context)
        
        # 只有一个玩家时，应该直接结束
        self.assertEqual(possible_phases, [GamePhase.FINISHED])
    
    def test_get_defined_next_phase_for_event_betting_round_complete(self):
        """测试下注轮完成事件的阶段转换"""
        # 测试各个阶段的下注轮完成
        test_cases = [
            (GamePhase.PRE_FLOP, GamePhase.FLOP),
            (GamePhase.FLOP, GamePhase.TURN),
            (GamePhase.TURN, GamePhase.RIVER),
            (GamePhase.RIVER, GamePhase.SHOWDOWN),
            (GamePhase.SHOWDOWN, GamePhase.FINISHED)
        ]
        
        for current_phase, expected_next in test_cases:
            with self.subTest(current_phase=current_phase):
                next_phase = get_defined_next_phase_for_event(
                    current_phase, 'BETTING_ROUND_COMPLETE'
                )
                
                # 反作弊检查
                if next_phase is not None:
                    CoreUsageChecker.verify_real_objects(next_phase, "GamePhase")
                
                self.assertEqual(next_phase, expected_next)
    
    def test_get_defined_next_phase_for_event_hand_start(self):
        """测试新手牌开始事件的阶段转换"""
        # INIT -> PRE_FLOP
        next_phase = get_defined_next_phase_for_event(GamePhase.INIT, 'HAND_START')
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(next_phase, "GamePhase")
        
        self.assertEqual(next_phase, GamePhase.PRE_FLOP)
        
        # FINISHED -> PRE_FLOP (新一轮开始)
        next_phase = get_defined_next_phase_for_event(GamePhase.FINISHED, 'HAND_START')
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(next_phase, "GamePhase")
        
        self.assertEqual(next_phase, GamePhase.PRE_FLOP)
    
    def test_get_defined_next_phase_for_event_showdown_complete(self):
        """测试摊牌完成事件的阶段转换"""
        next_phase = get_defined_next_phase_for_event(GamePhase.SHOWDOWN, 'SHOWDOWN_COMPLETE')
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(next_phase, "GamePhase")
        
        self.assertEqual(next_phase, GamePhase.FINISHED)
    
    def test_get_defined_next_phase_for_event_hand_auto_finish(self):
        """测试手牌自动结束事件的阶段转换"""
        auto_finish_phases = [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]
        
        for current_phase in auto_finish_phases:
            with self.subTest(current_phase=current_phase):
                next_phase = get_defined_next_phase_for_event(
                    current_phase, 'HAND_AUTO_FINISH'
                )
                
                # 反作弊检查
                CoreUsageChecker.verify_real_objects(next_phase, "GamePhase")
                
                self.assertEqual(next_phase, GamePhase.FINISHED)
    
    def test_get_defined_next_phase_for_event_all_players_fold(self):
        """测试所有玩家弃牌事件的阶段转换"""
        fold_phases = [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER]
        
        for current_phase in fold_phases:
            with self.subTest(current_phase=current_phase):
                next_phase = get_defined_next_phase_for_event(
                    current_phase, 'ALL_PLAYERS_FOLD'
                )
                
                # 反作弊检查
                CoreUsageChecker.verify_real_objects(next_phase, "GamePhase")
                
                self.assertEqual(next_phase, GamePhase.FINISHED)
    
    def test_get_defined_next_phase_for_event_unknown_event(self):
        """测试未知事件类型"""
        next_phase = get_defined_next_phase_for_event(GamePhase.PRE_FLOP, 'UNKNOWN_EVENT')
        
        # 未知事件应该返回None
        self.assertIsNone(next_phase)
    
    def test_get_next_phase_in_sequence(self):
        """测试标准序列中的下一阶段"""
        sequence_tests = [
            (GamePhase.INIT, GamePhase.PRE_FLOP),
            (GamePhase.PRE_FLOP, GamePhase.FLOP),
            (GamePhase.FLOP, GamePhase.TURN),
            (GamePhase.TURN, GamePhase.RIVER),
            (GamePhase.RIVER, GamePhase.SHOWDOWN),
            (GamePhase.SHOWDOWN, GamePhase.FINISHED),
            (GamePhase.FINISHED, None)  # 已是最后阶段
        ]
        
        for current_phase, expected_next in sequence_tests:
            with self.subTest(current_phase=current_phase):
                next_phase = get_next_phase_in_sequence(current_phase)
                
                # 反作弊检查
                if next_phase is not None:
                    CoreUsageChecker.verify_real_objects(next_phase, "GamePhase")
                
                self.assertEqual(next_phase, expected_next)
    
    def test_get_core_phase_logic_data(self):
        """测试获取完整的核心阶段逻辑数据"""
        logic_data = get_core_phase_logic_data(GamePhase.PRE_FLOP, self.test_context)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(logic_data, "CorePhaseLogicData")
        CoreUsageChecker.verify_real_objects(logic_data.current_phase, "GamePhase")
        CoreUsageChecker.verify_real_objects(logic_data.default_next_phase, "GamePhase")
        
        for phase in logic_data.possible_next_phases:
            CoreUsageChecker.verify_real_objects(phase, "GamePhase")
        
        for transition in logic_data.valid_transitions:
            CoreUsageChecker.verify_real_objects(transition, "PhaseTransition")
            CoreUsageChecker.verify_real_objects(transition.from_phase, "GamePhase")
            CoreUsageChecker.verify_real_objects(transition.to_phase, "GamePhase")
        
        # 验证数据的正确性
        self.assertEqual(logic_data.current_phase, GamePhase.PRE_FLOP)
        self.assertEqual(logic_data.default_next_phase, GamePhase.FLOP)
        self.assertEqual(logic_data.possible_next_phases, [GamePhase.FLOP, GamePhase.FINISHED])
        self.assertEqual(len(logic_data.valid_transitions), 2)
        
        # 验证转换信息
        transitions_dict = {
            transition.to_phase: transition for transition in logic_data.valid_transitions
        }
        
        self.assertIn(GamePhase.FLOP, transitions_dict)
        self.assertIn(GamePhase.FINISHED, transitions_dict)
        
        # 验证转换条件
        flop_transition = transitions_dict[GamePhase.FLOP]
        self.assertEqual(flop_transition.condition, "翻前下注轮结束")
        
        finished_transition = transitions_dict[GamePhase.FINISHED]
        self.assertEqual(finished_transition.condition, "所有玩家弃牌或只剩一人")
    
    def test_phase_transition_data_immutability(self):
        """测试阶段转换数据的不可变性"""
        logic_data = get_core_phase_logic_data(GamePhase.FLOP)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(logic_data, "CorePhaseLogicData")
        
        # 尝试修改数据应该失败（frozen=True）
        with self.assertRaises(AttributeError):
            logic_data.current_phase = GamePhase.TURN
        
        with self.assertRaises(AttributeError):
            logic_data.possible_next_phases = []
    
    def test_phase_transition_creation(self):
        """测试阶段转换对象的创建"""
        transition = PhaseTransition(
            from_phase=GamePhase.FLOP,
            to_phase=GamePhase.TURN,
            event_type='BETTING_ROUND_COMPLETE',
            condition='翻牌下注轮结束'
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(transition, "PhaseTransition")
        CoreUsageChecker.verify_real_objects(transition.from_phase, "GamePhase")
        CoreUsageChecker.verify_real_objects(transition.to_phase, "GamePhase")
        
        # 验证属性
        self.assertEqual(transition.from_phase, GamePhase.FLOP)
        self.assertEqual(transition.to_phase, GamePhase.TURN)
        self.assertEqual(transition.event_type, 'BETTING_ROUND_COMPLETE')
        self.assertEqual(transition.condition, '翻牌下注轮结束')
    
    def test_edge_case_no_context(self):
        """测试边缘情况：无上下文"""
        # 在没有上下文的情况下获取可能的下一阶段
        possible_phases = get_possible_next_phases(GamePhase.PRE_FLOP, None)
        
        # 反作弊检查
        for phase in possible_phases:
            CoreUsageChecker.verify_real_objects(phase, "GamePhase")
        
        # 没有上下文时应该返回默认的可能阶段
        expected_phases = [GamePhase.FLOP, GamePhase.FINISHED]
        self.assertEqual(possible_phases, expected_phases)
    
    def test_edge_case_empty_players_context(self):
        """测试边缘情况：空玩家上下文"""
        empty_context = GameContext(
            game_id="empty_test",
            current_phase=GamePhase.PRE_FLOP,
            players={},
            community_cards=[],
            pot_total=0,
            current_bet=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(empty_context, "GameContext")
        
        possible_phases = get_possible_next_phases(GamePhase.PRE_FLOP, empty_context)
        
        # 没有玩家时应该直接结束
        self.assertEqual(possible_phases, [GamePhase.FINISHED])


if __name__ == '__main__':
    unittest.main() 