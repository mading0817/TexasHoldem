#!/usr/bin/env python3
"""
PLAN B: 游戏结束逻辑修复的单元测试

验证GameQueryService.is_game_over方法的正确行为：
- 游戏结束应该基于筹码分布，而不是当前手牌状态
- 只有当少于2个玩家有筹码时游戏才结束
- 手牌结束(如fold)不应影响游戏整体的结束状态
"""

import unittest
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v3.application import *
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestGameOverLogicFix(unittest.TestCase):
    """游戏结束逻辑修复测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.config = ConfigService()
        self.validation = ValidationService(self.config)
        self.cmd = GameCommandService(validation_service=self.validation, config_service=self.config)
        self.query = GameQueryService(command_service=self.cmd, config_service=self.config)
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.query, "GameQueryService")
        CoreUsageChecker.verify_real_objects(self.cmd, "GameCommandService")
    
    def test_game_not_over_when_both_players_have_chips(self):
        """测试：两个玩家都有筹码时游戏不结束"""
        # 创建游戏
        self.cmd.create_new_game('test', ['p0', 'p1'])
        self.cmd.start_new_hand('test')
        
        # 检查初始状态：游戏不应该结束
        result = self.query.is_game_over('test')
        self.assertTrue(result.success)
        self.assertFalse(result.data, "两个玩家都有筹码时游戏不应该结束")
        
        # 验证详情
        self.assertEqual(result.data_details['players_with_chips_count'], 2)
        self.assertEqual(result.data_details['reason'], 'ongoing')
    
    def test_game_not_over_after_fold_with_chips_remaining(self):
        """测试：fold后如果两个玩家都还有筹码，游戏不结束"""
        # 创建游戏并开始手牌
        self.cmd.create_new_game('test', ['p0', 'p1'])
        self.cmd.start_new_hand('test')
        
        # p0 fold
        action = PlayerAction(action_type="fold", amount=0)
        fold_result = self.cmd.execute_player_action('test', 'p0', action)
        self.assertTrue(fold_result.success)
        
        # 关键测试：fold后游戏不应该结束（因为两个玩家都还有筹码）
        result = self.query.is_game_over('test')
        self.assertTrue(result.success)
        self.assertFalse(result.data, "fold后两个玩家都有筹码时游戏不应该结束")
        
        # 验证有筹码的玩家数量
        self.assertEqual(result.data_details['players_with_chips_count'], 2)
        self.assertIn('p0', result.data_details['players_with_chips'])
        self.assertIn('p1', result.data_details['players_with_chips'])
    
    def test_game_over_when_only_one_player_has_chips(self):
        """测试：只有一个玩家有筹码时游戏结束"""
        # 创建游戏
        self.cmd.create_new_game('test', ['p0', 'p1'])
        
        # 人工设置一个玩家没有筹码的情况
        session = self.cmd._get_session('test')
        session.context.players['p0']['chips'] = 0  # p0没有筹码
        session.context.players['p1']['chips'] = 1000  # p1有筹码
        
        # 现在游戏应该结束
        result = self.query.is_game_over('test')
        self.assertTrue(result.success)
        self.assertTrue(result.data, "只有一个玩家有筹码时游戏应该结束")
        
        # 验证详情
        self.assertEqual(result.data_details['players_with_chips_count'], 1)
        self.assertEqual(result.data_details['reason'], 'insufficient_players_with_chips')
        self.assertIn('p1', result.data_details['players_with_chips'])
        self.assertNotIn('p0', result.data_details['players_with_chips'])
    
    def test_game_over_when_no_players_have_chips(self):
        """测试：没有玩家有筹码时游戏结束"""
        # 创建游戏
        self.cmd.create_new_game('test', ['p0', 'p1'])
        
        # 人工设置所有玩家都没有筹码
        session = self.cmd._get_session('test')
        session.context.players['p0']['chips'] = 0
        session.context.players['p1']['chips'] = 0
        
        # 游戏应该结束
        result = self.query.is_game_over('test')
        self.assertTrue(result.success)
        self.assertTrue(result.data, "没有玩家有筹码时游戏应该结束")
        
        # 验证详情
        self.assertEqual(result.data_details['players_with_chips_count'], 0)
        self.assertEqual(result.data_details['reason'], 'insufficient_players_with_chips')
    
    def test_multiple_hands_after_fold(self):
        """测试：fold后可以继续多手牌游戏"""
        # 创建游戏
        self.cmd.create_new_game('test', ['p0', 'p1'])
        
        # 进行多手牌测试
        for hand_num in range(3):
            self.cmd.start_new_hand('test')
            
            # 检查手牌开始时游戏状态
            result = self.query.is_game_over('test')
            self.assertFalse(result.data, f"第{hand_num+1}手开始时游戏不应该结束")
            
            # p0 fold
            action = PlayerAction(action_type="fold", amount=0)
            fold_result = self.cmd.execute_player_action('test', 'p0', action)
            self.assertTrue(fold_result.success)
            
            # fold后游戏仍然不应该结束
            result = self.query.is_game_over('test')
            self.assertFalse(result.data, f"第{hand_num+1}手fold后游戏不应该结束")
            
            # 验证两个玩家都还有筹码
            self.assertEqual(result.data_details['players_with_chips_count'], 2)
    
    def test_command_service_not_initialized_error(self):
        """测试：命令服务未初始化时的错误处理"""
        query_without_cmd = GameQueryService(command_service=None)
        
        result = query_without_cmd.is_game_over('test')
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "COMMAND_SERVICE_NOT_INITIALIZED")
    
    def test_nonexistent_game_error(self):
        """测试：不存在的游戏ID错误处理"""
        result = self.query.is_game_over('nonexistent_game')
        self.assertFalse(result.success)
        # 错误应该来自快照接口


if __name__ == '__main__':
    unittest.main() 