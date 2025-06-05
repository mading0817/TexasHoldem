"""
反作弊集成测试 - 验证所有服务使用真实核心对象
"""
import pytest
from v3.application.command_service import GameCommandService
from v3.application.query_service import GameQueryService
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestAntiCheatIntegration:
    """反作弊集成测试类"""
    
    def test_command_service_uses_real_core_objects(self):
        """测试命令服务使用真实核心对象"""
        service = GameCommandService()
        CoreUsageChecker.verify_real_objects(service, "GameCommandService")
        
    def test_query_service_uses_real_core_objects(self):
        """测试查询服务使用真实核心对象"""
        service = GameQueryService()
        CoreUsageChecker.verify_real_objects(service, "GameQueryService")
        
    def test_command_service_create_game_uses_real_objects(self):
        """测试命令服务创建游戏使用真实对象"""
        service = GameCommandService()
        result = service.create_new_game(player_ids=["Alice", "Bob"])
        CoreUsageChecker.verify_real_objects(result, "CommandResult")
        
    def test_query_service_get_game_state_uses_real_objects(self):
        """测试查询服务获取游戏状态使用真实对象"""
        command_service = GameCommandService()
        query_service = GameQueryService(command_service=command_service)
        
        # 创建游戏
        result = command_service.create_new_game(player_ids=["Alice", "Bob"])
        game_id = result.data['game_id']
        
        # 获取游戏状态
        state = query_service.get_game_state(game_id)
        CoreUsageChecker.verify_real_objects(state, "QueryResult")
        
    def test_query_service_get_available_actions_uses_real_objects(self):
        """测试查询服务获取可用行动使用真实对象"""
        command_service = GameCommandService()
        query_service = GameQueryService(command_service=command_service)
        
        # 创建游戏并开始手牌
        result = command_service.create_new_game(player_ids=["Alice", "Bob"])
        game_id = result.data['game_id']
        command_service.start_new_hand(game_id)
        
        # 获取可用行动
        actions = query_service.get_available_actions(game_id, "Alice")
        CoreUsageChecker.verify_real_objects(actions, "QueryResult")
        
    def test_command_service_player_action_uses_real_objects(self):
        """测试命令服务玩家行动使用真实对象"""
        command_service = GameCommandService()
        query_service = GameQueryService(command_service=command_service)
        
        # 创建游戏并开始手牌
        result = command_service.create_new_game(player_ids=["Alice", "Bob"])
        game_id = result.data['game_id']
        command_service.start_new_hand(game_id)
        
        # 获取当前玩家和可用行动
        state = query_service.get_game_state(game_id)
        actions = query_service.get_available_actions(game_id, "Alice")
        
        if actions.success and actions.data.actions:
            from v3.application.types import PlayerAction
            action = PlayerAction(action_type=actions.data.actions[0])
            result = command_service.execute_player_action(game_id, "Alice", action)
            CoreUsageChecker.verify_real_objects(result, "CommandResult")
            
    def test_query_service_get_player_info_uses_real_objects(self):
        """测试查询服务获取玩家信息使用真实对象"""
        command_service = GameCommandService()
        query_service = GameQueryService(command_service=command_service)
        
        # 创建游戏
        result = command_service.create_new_game(player_ids=["Alice", "Bob"])
        game_id = result.data['game_id']
        
        # 获取玩家信息
        player_info = query_service.get_player_info(game_id, "Alice")
        CoreUsageChecker.verify_real_objects(player_info, "QueryResult")
        
    def test_all_services_integration_anti_cheat(self):
        """测试所有服务集成的反作弊检查"""
        command_service = GameCommandService()
        query_service = GameQueryService(command_service=command_service)
        
        # 验证服务本身
        CoreUsageChecker.verify_real_objects(command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(query_service, "GameQueryService")
        
        # 创建游戏并验证结果
        start_result = command_service.create_new_game(player_ids=["Alice", "Bob", "Charlie"])
        CoreUsageChecker.verify_real_objects(start_result, "CommandResult")
        
        game_id = start_result.data['game_id']
        
        # 获取各种信息并验证
        state = query_service.get_game_state(game_id)
        player_info = query_service.get_player_info(game_id, "Alice")
        
        CoreUsageChecker.verify_real_objects(state, "QueryResult")
        CoreUsageChecker.verify_real_objects(player_info, "QueryResult")
        
        # 开始手牌并获取可用行动
        command_service.start_new_hand(game_id)
        actions = query_service.get_available_actions(game_id, "Alice")
        CoreUsageChecker.verify_real_objects(actions, "QueryResult") 