#!/usr/bin/env python3
"""
德州扑克规则修复测试

测试application层中新增的德州扑克规则验证功能，
确保修复后的系统正确执行德州扑克规则。
"""

import pytest
import time
from typing import Dict, Any

from v3.application import (
    GameCommandService, GameQueryService, PlayerAction,
    CommandResult, QueryResult, ResultStatus
)
from v3.core.events import EventBus, set_event_bus
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestTexasHoldemRulesFixes:
    """德州扑克规则修复测试"""
    
    def setup_method(self):
        """测试前设置"""
        # 创建独立的事件总线避免测试间干扰
        self.event_bus = EventBus()
        set_event_bus(self.event_bus)
        self.command_service = GameCommandService(self.event_bus)
        self.query_service = GameQueryService(self.command_service, self.event_bus)
        
        # 创建测试游戏
        self.game_id = "test_rules_game"
        self.player_ids = ["player_0", "player_1", "player_2", "player_3"]
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
    
    def test_zero_chips_player_cannot_act(self):
        """测试0筹码玩家不能参与行动"""
        # 创建游戏
        create_result = self.command_service.create_new_game(self.game_id, self.player_ids)
        assert create_result.success is True
        
        # 开始新手牌
        start_result = self.command_service.start_new_hand(self.game_id)
        assert start_result.success is True
        
        # 手动设置一个玩家筹码为0（模拟出局状态）
        session = self.command_service._get_session(self.game_id)
        session.context.players["player_2"]["chips"] = 0
        session.context.players["player_2"]["status"] = "out"
        session.context.players["player_2"]["active"] = False
        
        # 尝试让0筹码玩家行动
        action = PlayerAction(action_type="fold", amount=0)
        result = self.command_service.execute_player_action(self.game_id, "player_2", action)
        
        # 应该被拒绝
        assert result.success is False
        assert result.status == ResultStatus.BUSINESS_RULE_VIOLATION
        assert "筹码为0" in result.message
        assert result.error_code == "ZERO_CHIPS_CANNOT_ACT"
    
    def test_all_in_player_cannot_act(self):
        """测试All-In玩家不能再进行主动行动"""
        # 创建游戏
        create_result = self.command_service.create_new_game(self.game_id, self.player_ids)
        assert create_result.success is True
        
        # 开始新手牌
        start_result = self.command_service.start_new_hand(self.game_id)
        assert start_result.success is True
        
        # 手动设置一个玩家为All-In状态
        session = self.command_service._get_session(self.game_id)
        session.context.players["player_1"]["chips"] = 0
        session.context.players["player_1"]["status"] = "all_in"
        session.context.players["player_1"]["active"] = False
        
        # 尝试让All-In玩家行动
        action = PlayerAction(action_type="fold", amount=0)
        result = self.command_service.execute_player_action(self.game_id, "player_1", action)
        
        # 应该被拒绝
        assert result.success is False
        assert result.status == ResultStatus.BUSINESS_RULE_VIOLATION
        assert "已经All-In" in result.message
        assert result.error_code == "ALL_IN_CANNOT_ACT"
    
    def test_inactive_player_cannot_act(self):
        """测试非活跃玩家不能行动"""
        # 创建游戏
        create_result = self.command_service.create_new_game(self.game_id, self.player_ids)
        assert create_result.success is True
        
        # 开始新手牌
        start_result = self.command_service.start_new_hand(self.game_id)
        assert start_result.success is True
        
        # 手动设置一个玩家为非活跃状态
        session = self.command_service._get_session(self.game_id)
        session.context.players["player_3"]["active"] = False
        
        # 尝试让非活跃玩家行动
        action = PlayerAction(action_type="fold", amount=0)
        result = self.command_service.execute_player_action(self.game_id, "player_3", action)
        
        # 应该被拒绝
        assert result.success is False
        assert result.status == ResultStatus.BUSINESS_RULE_VIOLATION
        assert "不处于活跃状态" in result.message
        assert result.error_code == "INACTIVE_PLAYER_CANNOT_ACT"
    
    def test_insufficient_chips_for_bet(self):
        """测试筹码不足时不能下注"""
        # 创建游戏
        create_result = self.command_service.create_new_game(self.game_id, self.player_ids)
        assert create_result.success is True
        
        # 开始新手牌
        start_result = self.command_service.start_new_hand(self.game_id)
        assert start_result.success is True
        
        # 手动设置一个玩家筹码很少
        session = self.command_service._get_session(self.game_id)
        session.context.players["player_0"]["chips"] = 50
        
        # 尝试下注超过筹码的金额
        action = PlayerAction(action_type="raise", amount=100)
        result = self.command_service.execute_player_action(self.game_id, "player_0", action)
        
        # 应该被拒绝
        assert result.success is False
        assert result.status == ResultStatus.BUSINESS_RULE_VIOLATION
        assert "筹码不足" in result.message
        assert result.error_code == "INSUFFICIENT_CHIPS"
    
    def test_blinds_setup_for_new_hand(self):
        """测试新手牌的盲注设置"""
        # 创建游戏
        create_result = self.command_service.create_new_game(self.game_id, self.player_ids)
        assert create_result.success is True
        
        # 开始新手牌
        start_result = self.command_service.start_new_hand(self.game_id)
        assert start_result.success is True
        
        # 检查盲注是否正确设置
        state_result = self.query_service.get_game_state(self.game_id)
        assert state_result.success is True
        
        game_state = state_result.data
        
        # 检查底池中应该有盲注
        expected_blinds = 50 + 100  # 小盲 + 大盲
        assert game_state.pot_total >= expected_blinds
        
        # 检查至少有一个玩家下了小盲注，一个玩家下了大盲注
        small_blind_found = False
        big_blind_found = False
        
        for player_id, player_data in game_state.players.items():
            current_bet = player_data.get('current_bet', 0)
            if current_bet == 50:  # 小盲注
                small_blind_found = True
            elif current_bet == 100:  # 大盲注
                big_blind_found = True
        
        assert small_blind_found, "应该有玩家下小盲注"
        assert big_blind_found, "应该有玩家下大盲注"
    
    def test_insufficient_active_players_for_new_hand(self):
        """测试活跃玩家不足时不能开始新手牌"""
        # 创建游戏
        create_result = self.command_service.create_new_game(self.game_id, ["player_0", "player_1"])
        assert create_result.success is True
        
        # 手动设置所有玩家筹码为0（除了一个）
        session = self.command_service._get_session(self.game_id)
        session.context.players["player_1"]["chips"] = 0
        
        # 尝试开始新手牌
        start_result = self.command_service.start_new_hand(self.game_id)
        
        # 应该被拒绝
        assert start_result.success is False
        assert start_result.status == ResultStatus.BUSINESS_RULE_VIOLATION
        assert "至少需要2个有筹码的玩家" in start_result.message
        assert start_result.error_code == "INSUFFICIENT_ACTIVE_PLAYERS"
    
    def test_player_state_reset_for_new_hand(self):
        """测试新手牌时玩家状态正确重置"""
        # 创建游戏
        create_result = self.command_service.create_new_game(self.game_id, self.player_ids)
        assert create_result.success is True
        
        # 手动设置一些玩家状态（模拟上一手牌的状态）
        session = self.command_service._get_session(self.game_id)
        session.context.players["player_0"]["current_bet"] = 200
        session.context.players["player_0"]["total_bet_this_hand"] = 300
        session.context.players["player_1"]["chips"] = 0  # 出局玩家
        session.context.pot_total = 500
        
        # 开始新手牌
        start_result = self.command_service.start_new_hand(self.game_id)
        assert start_result.success is True
        
        # 检查状态是否正确重置
        state_result = self.query_service.get_game_state(self.game_id)
        assert state_result.success is True
        
        game_state = state_result.data
        
        # 检查有筹码的玩家状态
        for player_id, player_data in game_state.players.items():
            if player_data.get('chips', 0) > 0:
                # 有筹码的玩家应该是活跃的
                assert player_data.get('active', False) is True
                assert player_data.get('status') == 'active'
            else:
                # 无筹码的玩家应该是出局的
                assert player_data.get('active', False) is False
                assert player_data.get('status') == 'out'
    
    def test_wrong_player_turn_validation(self):
        """测试行动轮次验证"""
        # 创建游戏
        create_result = self.command_service.create_new_game(self.game_id, self.player_ids)
        assert create_result.success is True
        
        # 开始新手牌
        start_result = self.command_service.start_new_hand(self.game_id)
        assert start_result.success is True
        
        # 获取当前应该行动的玩家
        state_result = self.query_service.get_game_state(self.game_id)
        assert state_result.success is True
        
        current_player = state_result.data.active_player_id
        
        # 找一个不是当前玩家的其他玩家
        other_player = None
        for player_id in self.player_ids:
            if player_id != current_player:
                other_player = player_id
                break
        
        assert other_player is not None
        
        # 尝试让非当前玩家行动
        action = PlayerAction(action_type="fold", amount=0)
        result = self.command_service.execute_player_action(self.game_id, other_player, action)
        
        # 应该被拒绝
        assert result.success is False
        assert result.status == ResultStatus.BUSINESS_RULE_VIOLATION
        assert "当前轮到玩家" in result.message
        assert result.error_code == "NOT_PLAYER_TURN"


class TestTexasHoldemRulesIntegration:
    """德州扑克规则集成测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.event_bus = EventBus()
        set_event_bus(self.event_bus)
        self.command_service = GameCommandService(self.event_bus)
        self.query_service = GameQueryService(self.command_service, self.event_bus)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
    
    def test_complete_hand_with_rules_validation(self):
        """测试完整手牌流程中的规则验证"""
        game_id = "integration_test_game"
        player_ids = ["player_0", "player_1", "player_2"]
        
        # 创建游戏
        create_result = self.command_service.create_new_game(game_id, player_ids)
        assert create_result.success is True
        
        # 开始新手牌
        start_result = self.command_service.start_new_hand(game_id)
        assert start_result.success is True
        
        # 验证盲注设置
        state_result = self.query_service.get_game_state(game_id)
        assert state_result.success is True
        
        game_state = state_result.data
        assert game_state.pot_total >= 150  # 至少有盲注
        
        # 验证有活跃玩家
        assert game_state.active_player_id is not None
        
        # 模拟一些合法的玩家行动
        current_player = game_state.active_player_id
        
        # 当前玩家弃牌
        fold_action = PlayerAction(action_type="fold", amount=0)
        fold_result = self.command_service.execute_player_action(game_id, current_player, fold_action)
        assert fold_result.success is True
        
        # 验证游戏状态更新
        state_result = self.query_service.get_game_state(game_id)
        assert state_result.success is True
        
        # 验证筹码守恒
        total_chips = sum(
            player_data.get('chips', 0) 
            for player_data in state_result.data.players.values()
        ) + state_result.data.pot_total
        
        expected_total = len(player_ids) * 1000  # 初始筹码
        assert total_chips == expected_total, f"筹码守恒违反: 实际{total_chips}, 期望{expected_total}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 