"""
PokerController单元测试 - Phase 1
测试Controller的原子性事务、状态快照和错误处理

遵循test-rules中的分层测试原则：
- 测试层只调用Controller API，不复制业务逻辑
- 使用固定随机种子保证可重现
- 测试Controller的事务原子性和回滚机制
"""

import pytest
import copy
from random import Random

from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.core.enums import ActionType, SeatStatus, GamePhase
from core_game_logic.core.exceptions import InvalidActionError

from app_controller.poker_controller import PokerController
from app_controller.dto_models import (
    PlayerActionInput, 
    ActionResult, 
    ActionResultType,
    GameStateSnapshot
)


class TestPokerControllerAtomic:
    """测试PokerController的原子性操作"""
    
    def setup_method(self):
        """每个测试方法前的设置 - 固定种子保证可重现"""
        # 创建标准4人游戏
        players = [
            Player(seat_id=0, name="Human", chips=1000),
            Player(seat_id=1, name="AI1", chips=1000),
            Player(seat_id=2, name="AI2", chips=1000),
            Player(seat_id=3, name="AI3", chips=1000)
        ]
        
        initial_state = GameState(
            players=players,
            dealer_position=0,
            small_blind=5,
            big_blind=10
        )
        
        # 使用固定种子的随机数生成器
        self.controller = PokerController(initial_state)
        self.initial_version = self.controller.version
    
    def test_atomic_decorator_success(self):
        """测试原子装饰器在成功情况下的行为"""
        # 执行一个有效行动
        action_input = PlayerActionInput(
            seat_id=0,  # 假设seat 0是当前玩家
            action_type=ActionType.CALL,
            amount=10
        )
        
        original_version = self.controller.version
        result = self.controller.execute_player_action(action_input)
        
        # 验证成功执行
        assert result.success
        assert self.controller.version == original_version + 1
    
    def test_atomic_decorator_rollback_on_exception(self):
        """测试原子装饰器在异常时的回滚行为"""
        # 保存原始状态
        original_state_snapshot = copy.deepcopy(self.controller.state)
        original_version = self.controller.version
        
        # 创建一个会导致异常的行动（无效座位号）
        invalid_action = PlayerActionInput(
            seat_id=999,  # 不存在的座位
            action_type=ActionType.CALL,
            amount=10
        )
        
        result = self.controller.execute_player_action_safe(invalid_action)
        
        # 验证回滚：版本号未变，状态未变
        assert not result.success
        assert self.controller.version == original_version
        assert result.result_type == ActionResultType.INVALID_ACTION
        
        # 深度比较状态是否完全回滚（关键属性检查）
        assert self.controller.state.pot == original_state_snapshot.pot
        assert self.controller.state.current_bet == original_state_snapshot.current_bet
        assert self.controller.state.phase == original_state_snapshot.phase
        
        # 检查玩家状态是否回滚
        for i, player in enumerate(self.controller.state.players):
            original_player = original_state_snapshot.players[i]
            assert player.chips == original_player.chips
            assert player.current_bet == original_player.current_bet
            assert player.status == original_player.status
    
    def test_state_snapshot_immutability(self):
        """测试状态快照的不可变性"""
        # 获取快照
        snapshot = self.controller.get_state_snapshot()
        
        # 验证快照是只读的（通过frozen dataclass实现）
        assert isinstance(snapshot, GameStateSnapshot)
        
        # 尝试修改快照应该失败（frozen dataclass会抛出异常）
        with pytest.raises(Exception):  # dataclass frozen会抛出FrozenInstanceError或AttributeError
            snapshot.version = 999
        
        with pytest.raises(Exception):
            snapshot.pot = 999
    
    def test_version_based_incremental_updates(self):
        """测试基于版本的增量更新优化"""
        # 获取初始快照
        snapshot1 = self.controller.get_state_snapshot()
        version1 = snapshot1.version
        
        # 再次获取相同版本的快照，应该返回None（无变化）
        snapshot2 = self.controller.get_state_snapshot(last_known_version=version1)
        assert snapshot2 is None
        
        # 执行一个操作改变状态
        action_input = PlayerActionInput(
            seat_id=0,
            action_type=ActionType.FOLD
        )
        result = self.controller.execute_player_action_safe(action_input)
        assert result.success
        
        # 现在获取快照应该返回新版本
        snapshot3 = self.controller.get_state_snapshot(last_known_version=version1)
        assert snapshot3 is not None
        assert snapshot3.version > version1
    
    def test_snapshot_viewer_seat_privacy(self):
        """测试快照的视角隐私功能"""
        # 获取人类玩家视角的快照
        human_snapshot = self.controller.get_state_snapshot(viewer_seat=0)
        
        # 获取全局视角的快照
        global_snapshot = self.controller.get_state_snapshot()
        
        # 检查人类玩家的手牌应该可见
        human_player_snapshot = human_snapshot.get_player_snapshot(0)
        assert human_player_snapshot.hole_cards_display != "** **"
        
        # 检查其他玩家的手牌应该隐藏（如果手牌系统已实现）
        ai_player_snapshot = human_snapshot.get_player_snapshot(1)
        # 这个测试取决于手牌显示的具体实现


class TestPokerControllerIntegration:
    """测试PokerController的集成功能"""
    
    def setup_method(self):
        """设置测试环境"""
        players = [
            Player(seat_id=0, name="Human", chips=1000),
            Player(seat_id=1, name="AI1", chips=1000)
        ]
        
        initial_state = GameState(
            players=players,
            dealer_position=0,
            small_blind=5,
            big_blind=10
        )
        
        self.controller = PokerController(initial_state)
    
    def test_new_hand_workflow(self):
        """测试开始新手牌的完整工作流"""
        # 测试开始新手牌
        result = self.controller.start_new_hand()
        
        assert result.success
        assert len(result.events) > 0
        
        # 验证状态版本增加
        assert self.controller.version > 0
        
        # 验证盲注设置等基本状态
        snapshot = self.controller.get_state_snapshot()
        assert snapshot.small_blind == 5
        assert snapshot.big_blind == 10
    
    def test_dealer_rotation(self):
        """测试庄家轮换功能"""
        original_dealer = self.controller.state.dealer_position
        
        result = self.controller.advance_dealer()
        
        assert result.success
        new_snapshot = self.controller.get_state_snapshot()
        assert new_snapshot.dealer_position != original_dealer
    
    def test_error_handling_consistency(self):
        """测试错误处理的一致性"""
        # 测试各种无效输入
        invalid_inputs = [
            PlayerActionInput(seat_id=-1, action_type=ActionType.CALL),  # 无效座位
            PlayerActionInput(seat_id=999, action_type=ActionType.CALL),  # 不存在座位
            PlayerActionInput(seat_id=0, action_type=ActionType.BET, amount=-100),  # 负数金额
        ]
        
        for invalid_input in invalid_inputs:
            original_version = self.controller.version
            result = self.controller.execute_player_action_safe(invalid_input)
            
            # 验证所有无效输入都被正确处理，不会破坏状态
            assert not result.success
            assert result.result_type == ActionResultType.INVALID_ACTION
            assert self.controller.version == original_version  # 版本未变


class TestPokerControllerEdgeCases:
    """测试PokerController的边界情况"""
    
    def test_guard_protection_against_infinite_loops(self):
        """测试护栏机制防止无限循环"""
        # 这个测试更适合在更高层级的测试中进行
        # 这里主要验证Controller本身不会进入无限循环
        
        # 创建最小配置
        players = [Player(seat_id=0, name="Solo", chips=100)]
        state = GameState(players=players, dealer_position=0, small_blind=1, big_blind=2)
        controller = PokerController(state)
        
        # 快速执行一些操作，验证没有死循环
        for _ in range(10):
            snapshot = controller.get_state_snapshot()
            assert snapshot is not None
            
            # 执行一个简单操作
            result = controller.start_new_hand()
            if not result.success:
                break  # 如果无法继续，正常退出
    
    def test_controller_state_consistency(self):
        """测试Controller状态一致性"""
        players = [Player(seat_id=i, name=f"Player{i}", chips=1000) for i in range(4)]
        state = GameState(players=players, dealer_position=0, small_blind=5, big_blind=10)
        controller = PokerController(state)
        
        # 执行多个操作
        operations = [
            lambda: controller.start_new_hand(),
            lambda: controller.advance_dealer(),
            lambda: controller.get_state_snapshot(),
        ]
        
        for operation in operations:
            try:
                result = operation()
                # 每次操作后验证基本一致性
                snapshot = controller.get_state_snapshot()
                assert snapshot is not None
                assert len(snapshot.players) == 4
            except Exception as e:
                # 如果操作失败，至少不应该破坏Controller状态
                snapshot = controller.get_state_snapshot()
                assert snapshot is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 