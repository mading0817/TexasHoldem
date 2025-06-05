"""
应用服务层单元测试

测试GameCommandService和GameQueryService的功能，
包含反作弊检查确保使用真实的应用服务对象。
"""

import pytest
import time
from typing import Dict, Any

from v3.application import (
    GameCommandService, GameQueryService, PlayerAction,
    CommandResult, QueryResult, ResultStatus,
    GameStateSnapshot, PlayerInfo, AvailableActions
)
from v3.core.events import EventBus, get_event_bus, set_event_bus
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestGameCommandService:
    """游戏命令服务测试"""
    
    def setup_method(self):
        """测试前设置"""
        # 创建独立的事件总线避免测试间干扰
        self.event_bus = EventBus()
        set_event_bus(self.event_bus)
        self.command_service = GameCommandService(self.event_bus)
    
    def test_command_service_creation(self):
        """测试命令服务创建"""
        # 反作弊检查：确保使用真实的命令服务对象
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        
        # 验证服务初始化
        assert self.command_service is not None
        assert len(self.command_service.get_active_games()) == 0
    
    def test_create_new_game_success(self):
        """测试成功创建新游戏"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        
        # 创建游戏
        result = self.command_service.create_new_game(
            game_id="test_game_001",
            player_ids=["player1", "player2"]
        )
        
        # 验证结果
        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        assert "test_game_001" in result.message
        assert result.data['game_id'] == "test_game_001"
        assert result.data['player_count'] == 2
        
        # 验证游戏已创建
        active_games = self.command_service.get_active_games()
        assert "test_game_001" in active_games
    
    def test_create_new_game_auto_id(self):
        """测试自动生成游戏ID"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        
        # 创建游戏（不指定ID）
        result = self.command_service.create_new_game(player_ids=["p1", "p2"])
        
        # 验证结果
        assert result.success is True
        assert result.data['game_id'].startswith("game_")
        assert len(result.data['game_id']) > 5  # 确保有UUID部分
    
    def test_create_game_invalid_player_count(self):
        """测试无效玩家数量"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        
        # 测试玩家太少
        result = self.command_service.create_new_game(
            game_id="test_game_002",
            player_ids=["player1"]  # 只有1个玩家
        )
        
        assert result.success is False
        assert result.status == ResultStatus.VALIDATION_ERROR
        assert result.error_code == "INVALID_PLAYER_COUNT"
        
        # 测试玩家太多
        result = self.command_service.create_new_game(
            game_id="test_game_003",
            player_ids=[f"player{i}" for i in range(11)]  # 11个玩家
        )
        
        assert result.success is False
        assert result.status == ResultStatus.VALIDATION_ERROR
        assert result.error_code == "INVALID_PLAYER_COUNT"
    
    def test_create_duplicate_game(self):
        """测试创建重复游戏"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        
        # 创建第一个游戏
        result1 = self.command_service.create_new_game(
            game_id="duplicate_game",
            player_ids=["p1", "p2"]
        )
        assert result1.success is True
        
        # 尝试创建重复游戏
        result2 = self.command_service.create_new_game(
            game_id="duplicate_game",
            player_ids=["p3", "p4"]
        )
        
        assert result2.success is False
        assert result2.status == ResultStatus.VALIDATION_ERROR
        assert result2.error_code == "GAME_ALREADY_EXISTS"
    
    def test_start_new_hand_success(self):
        """测试成功开始新手牌"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        
        # 先创建游戏
        create_result = self.command_service.create_new_game(
            game_id="hand_test_game",
            player_ids=["p1", "p2"]
        )
        assert create_result.success is True
        
        # 开始新手牌
        result = self.command_service.start_new_hand("hand_test_game")
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        assert "新手牌开始" in result.message
        assert result.data['current_phase'] == "PRE_FLOP"
    
    def test_start_hand_game_not_found(self):
        """测试在不存在的游戏中开始手牌"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        
        result = self.command_service.start_new_hand("nonexistent_game")
        
        assert result.success is False
        assert result.status == ResultStatus.VALIDATION_ERROR
        assert result.error_code == "GAME_NOT_FOUND"
    
    def test_execute_player_action_success(self):
        """测试成功执行玩家行动"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        
        # 创建游戏并开始手牌
        self.command_service.create_new_game("action_test", ["p1", "p2"])
        self.command_service.start_new_hand("action_test")
        
        # 执行玩家行动
        action = PlayerAction(action_type="call", amount=0, player_id="p1")
        result = self.command_service.execute_player_action("action_test", "p1", action)
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        assert "call" in result.message
        assert result.data['action_type'] == "call"
    
    def test_execute_action_invalid_player(self):
        """测试无效玩家执行行动"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        
        # 创建游戏
        self.command_service.create_new_game("invalid_player_test", ["p1", "p2"])
        
        # 尝试让不存在的玩家执行行动
        action = PlayerAction(action_type="call", amount=0, player_id="p3")
        result = self.command_service.execute_player_action("invalid_player_test", "p3", action)
        
        assert result.success is False
        assert result.status == ResultStatus.VALIDATION_ERROR
        assert result.error_code == "PLAYER_NOT_IN_GAME"
    
    def test_execute_action_invalid_type(self):
        """测试无效行动类型"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        
        # 创建游戏
        self.command_service.create_new_game("invalid_action_test", ["p1", "p2"])
        
        # 尝试执行无效行动
        action = PlayerAction(action_type="invalid_action", amount=0, player_id="p1")
        result = self.command_service.execute_player_action("invalid_action_test", "p1", action)
        
        assert result.success is False
        assert result.status == ResultStatus.VALIDATION_ERROR
        assert result.error_code == "INVALID_ACTION_TYPE"
    
    def test_advance_phase_success(self):
        """测试成功推进阶段"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        
        # 创建游戏并开始手牌
        self.command_service.create_new_game("phase_test", ["p1", "p2"])
        self.command_service.start_new_hand("phase_test")
        
        # 推进阶段
        result = self.command_service.advance_phase("phase_test")
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        assert "推进到" in result.message
        assert result.data['old_phase'] == "PRE_FLOP"
        assert result.data['new_phase'] == "FLOP"
    
    def test_remove_game_success(self):
        """测试成功移除游戏"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        
        # 创建游戏
        self.command_service.create_new_game("remove_test", ["p1", "p2"])
        assert "remove_test" in self.command_service.get_active_games()
        
        # 移除游戏
        result = self.command_service.remove_game("remove_test")
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        assert "已移除" in result.message
        assert "remove_test" not in self.command_service.get_active_games()
    
    def test_remove_nonexistent_game(self):
        """测试移除不存在的游戏"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        
        result = self.command_service.remove_game("nonexistent")
        
        assert result.success is False
        assert result.status == ResultStatus.VALIDATION_ERROR
        assert result.error_code == "GAME_NOT_FOUND"


class TestGameQueryService:
    """游戏查询服务测试"""
    
    def setup_method(self):
        """测试前设置"""
        # 创建独立的事件总线避免测试间干扰
        self.event_bus = EventBus()
        set_event_bus(self.event_bus)
        self.command_service = GameCommandService(self.event_bus)
        self.query_service = GameQueryService(self.command_service, self.event_bus)
    
    def test_query_service_creation(self):
        """测试查询服务创建"""
        # 反作弊检查：确保使用真实的查询服务对象
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 验证服务初始化
        assert self.query_service is not None
    
    def test_get_game_state_success(self):
        """测试成功获取游戏状态"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏
        self.command_service.create_new_game("state_test", ["p1", "p2"])
        
        # 获取游戏状态
        result = self.query_service.get_game_state("state_test")
        
        assert isinstance(result, QueryResult)
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        
        # 验证状态快照
        snapshot = result.data
        assert isinstance(snapshot, GameStateSnapshot)
        assert snapshot.game_id == "state_test"
        assert snapshot.current_phase == "INIT"
        assert len(snapshot.players) == 2
        assert "p1" in snapshot.players
        assert "p2" in snapshot.players
    
    def test_get_game_state_not_found(self):
        """测试获取不存在游戏的状态"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        result = self.query_service.get_game_state("nonexistent")
        
        assert result.success is False
        assert result.status == ResultStatus.FAILURE
        assert result.error_code == "GAME_NOT_FOUND"
    
    def test_get_player_info_success(self):
        """测试成功获取玩家信息"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏
        self.command_service.create_new_game("player_info_test", ["p1", "p2"])
        
        # 获取玩家信息
        result = self.query_service.get_player_info("player_info_test", "p1")
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        
        # 验证玩家信息
        player_info = result.data
        assert isinstance(player_info, PlayerInfo)
        assert player_info.player_id == "p1"
        assert player_info.chips == 1000  # 默认筹码
        assert player_info.active is True
    
    def test_get_player_info_not_found(self):
        """测试获取不存在玩家的信息"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏
        self.command_service.create_new_game("player_not_found_test", ["p1", "p2"])
        
        # 尝试获取不存在玩家的信息
        result = self.query_service.get_player_info("player_not_found_test", "p3")
        
        assert result.success is False
        assert result.status == ResultStatus.FAILURE
        assert result.error_code == "PLAYER_NOT_IN_GAME"
    
    def test_get_available_actions_success(self):
        """测试成功获取可用行动"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏并开始手牌
        self.command_service.create_new_game("actions_test", ["p1", "p2"])
        self.command_service.start_new_hand("actions_test")
        
        # 获取可用行动
        result = self.query_service.get_available_actions("actions_test", "p1")
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        
        # 验证可用行动
        actions = result.data
        assert isinstance(actions, AvailableActions)
        assert actions.player_id == "p1"
        assert len(actions.actions) > 0
        assert "fold" in actions.actions
        assert "call" in actions.actions
    
    def test_get_game_list_success(self):
        """测试成功获取游戏列表"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建多个游戏
        self.command_service.create_new_game("list_test_1", ["p1", "p2"])
        self.command_service.create_new_game("list_test_2", ["p3", "p4"])
        
        # 获取游戏列表
        result = self.query_service.get_game_list()
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        
        # 验证游戏列表
        game_list = result.data
        assert isinstance(game_list, list)
        assert "list_test_1" in game_list
        assert "list_test_2" in game_list
    
    def test_get_game_history_success(self):
        """测试成功获取游戏历史"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏并执行一些操作
        self.command_service.create_new_game("history_test", ["p1", "p2"])
        self.command_service.start_new_hand("history_test")
        
        # 获取游戏历史
        result = self.query_service.get_game_history("history_test")
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        
        # 验证历史记录
        history = result.data
        assert isinstance(history, list)
        assert len(history) >= 2  # 至少有游戏开始和手牌开始事件
        
        # 验证事件格式
        for event in history:
            assert 'event_id' in event
            assert 'event_type' in event
            assert 'timestamp' in event
            assert 'data' in event
    
    def test_get_phase_info_success(self):
        """测试成功获取阶段信息"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏并开始手牌
        self.command_service.create_new_game("phase_info_test", ["p1", "p2"])
        self.command_service.start_new_hand("phase_info_test")
        
        # 获取阶段信息
        result = self.query_service.get_phase_info("phase_info_test")
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        
        # 验证阶段信息
        phase_info = result.data
        assert isinstance(phase_info, dict)
        assert 'current_phase' in phase_info
        assert 'transition_history' in phase_info
        assert 'can_advance' in phase_info
        assert 'next_phase' in phase_info
        
        assert phase_info['current_phase'] == "PRE_FLOP"
        assert phase_info['next_phase'] == "FLOP"
    
    def test_is_game_over_ongoing_game(self):
        """测试正在进行的游戏未结束"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏，所有玩家都有筹码
        self.command_service.create_new_game("game_over_test", ["p1", "p2", "p3"])
        
        # 检查游戏是否结束
        result = self.query_service.is_game_over("game_over_test")
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        assert result.data is False  # 游戏未结束
        assert result.data_details['players_with_chips_count'] == 3
        assert result.data_details['reason'] == 'ongoing'
    
    def test_is_game_over_finished_game(self):
        """测试只剩一个玩家时游戏结束"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏
        self.command_service.create_new_game("finished_game_test", ["p1", "p2", "p3"])
        
        # 手动设置玩家筹码，模拟只剩一个玩家有筹码的情况
        session = self.command_service._get_session("finished_game_test")
        session.context.players["p2"]['chips'] = 0
        session.context.players["p3"]['chips'] = 0
        # p1仍有筹码
        
        # 检查游戏是否结束
        result = self.query_service.is_game_over("finished_game_test")
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        assert result.data is True  # 游戏已结束
        assert result.data_details['players_with_chips_count'] == 1
        assert result.data_details['reason'] == 'insufficient_players'
    
    def test_is_game_over_no_players_with_chips(self):
        """测试没有玩家有筹码时游戏结束"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏
        self.command_service.create_new_game("no_chips_test", ["p1", "p2"])
        
        # 手动设置所有玩家筹码为0
        session = self.command_service._get_session("no_chips_test")
        session.context.players["p1"]['chips'] = 0
        session.context.players["p2"]['chips'] = 0
        
        # 检查游戏是否结束
        result = self.query_service.is_game_over("no_chips_test")
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        assert result.data is True  # 游戏已结束
        assert result.data_details['players_with_chips_count'] == 0
        assert result.data_details['reason'] == 'insufficient_players'
    
    def test_get_game_winner_ongoing_game(self):
        """测试正在进行的游戏没有获胜者"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏，所有玩家都有筹码
        self.command_service.create_new_game("winner_test_ongoing", ["p1", "p2", "p3"])
        
        # 获取游戏获胜者
        result = self.query_service.get_game_winner("winner_test_ongoing")
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        assert result.data is None  # 没有获胜者
        assert result.data_details['reason'] == 'game_not_over'
    
    def test_get_game_winner_finished_game(self):
        """测试只剩一个玩家时的获胜者"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 创建游戏
        self.command_service.create_new_game("winner_test_finished", ["p1", "p2", "p3"])
        
        # 手动设置玩家筹码，模拟只剩p1有筹码的情况
        session = self.command_service._get_session("winner_test_finished")
        session.context.players["p1"]['chips'] = 2500  # 获胜者有所有筹码
        session.context.players["p2"]['chips'] = 0
        session.context.players["p3"]['chips'] = 0
        
        # 获取游戏获胜者
        result = self.query_service.get_game_winner("winner_test_finished")
        
        assert result.success is True
        assert result.status == ResultStatus.SUCCESS
        assert result.data == "p1"  # p1是获胜者
        assert result.data_details['winner_chips'] == 2500
        assert result.data_details['reason'] == 'last_player_standing'
    
    def test_is_game_over_game_not_found(self):
        """测试检查不存在游戏的结束状态"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        result = self.query_service.is_game_over("nonexistent_game")
        
        assert result.success is False
        assert result.status == ResultStatus.FAILURE
        assert result.error_code == "GAME_NOT_FOUND"
    
    def test_get_game_winner_game_not_found(self):
        """测试获取不存在游戏的获胜者"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        result = self.query_service.get_game_winner("nonexistent_game")
        
        assert result.success is False
        assert result.status == ResultStatus.FAILURE
        assert result.error_code == "GAME_NOT_FOUND"


class TestApplicationServiceIntegration:
    """应用服务集成测试"""
    
    def setup_method(self):
        """测试前设置"""
        self.event_bus = EventBus()
        set_event_bus(self.event_bus)
        self.command_service = GameCommandService(self.event_bus)
        self.query_service = GameQueryService(self.command_service, self.event_bus)
    
    def test_complete_game_workflow(self):
        """测试完整的游戏工作流程"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 1. 创建游戏
        create_result = self.command_service.create_new_game("workflow_test", ["p1", "p2"])
        assert create_result.success is True
        
        # 2. 查询游戏状态
        state_result = self.query_service.get_game_state("workflow_test")
        assert state_result.success is True
        assert state_result.data.current_phase == "INIT"
        
        # 3. 开始新手牌
        hand_result = self.command_service.start_new_hand("workflow_test")
        assert hand_result.success is True
        
        # 4. 再次查询游戏状态
        state_result2 = self.query_service.get_game_state("workflow_test")
        assert state_result2.success is True
        assert state_result2.data.current_phase == "PRE_FLOP"
        
        # 5. 执行玩家行动
        action = PlayerAction(action_type="call", amount=0, player_id="p1")
        action_result = self.command_service.execute_player_action("workflow_test", "p1", action)
        assert action_result.success is True
        
        # 6. 查询游戏历史
        history_result = self.query_service.get_game_history("workflow_test")
        assert history_result.success is True
        assert len(history_result.data) >= 3  # 游戏开始、手牌开始、玩家行动
        
        # 7. 推进阶段
        advance_result = self.command_service.advance_phase("workflow_test")
        assert advance_result.success is True
        
        # 8. 最终状态检查
        final_state = self.query_service.get_game_state("workflow_test")
        assert final_state.success is True
        assert final_state.data.current_phase == "FLOP"
    
    def test_cqrs_separation(self):
        """测试CQRS分离原则"""
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        
        # 命令服务应该只有状态变更方法
        command_methods = [method for method in dir(self.command_service) 
                          if not method.startswith('_') and callable(getattr(self.command_service, method))]
        
        # 查询服务应该只有只读方法
        query_methods = [method for method in dir(self.query_service) 
                        if not method.startswith('_') and callable(getattr(self.query_service, method))]
        
        # 验证方法命名符合CQRS原则
        for method in command_methods:
            # 命令方法应该是动词开头（create, start, execute, advance, remove等）
            assert any(method.startswith(verb) for verb in ['create', 'start', 'execute', 'advance', 'remove', 'get'])
        
        for method in query_methods:
            # 查询方法应该是get开头
            assert method.startswith('get') or method.startswith('_')


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 