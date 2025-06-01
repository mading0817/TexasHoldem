"""
ActionValidator行动验证器的单元测试
测试行动验证和智能转换逻辑
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_game_logic.betting.action_validator import ActionValidator
from core_game_logic.game.game_state import GameState
from core_game_logic.game.game_controller import GameController
from core_game_logic.core.player import Player
from core_game_logic.core.enums import ActionType, Action, GamePhase, SeatStatus
from core_game_logic.core.exceptions import InvalidActionError
from core_game_logic.core.deck import Deck
from tests.common.test_helpers import ActionHelper
from tests.common.base_tester import BaseTester
from tests.common.data_structures import TestScenario


class TestActionValidator:
    """测试ActionValidator行动验证器"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.validator = ActionValidator()
        
        # 创建游戏状态 - 使用合法的初始化方式
        players = [
            Player(seat_id=0, name="玩家A", chips=100),
            Player(seat_id=1, name="玩家B", chips=50),
            Player(seat_id=2, name="玩家C", chips=200)
        ]
        
        self.state = GameState(
            phase=GamePhase.PRE_FLOP,
            small_blind=1,
            big_blind=2,
            current_bet=0,
            current_player=0,
            deck=Deck(),
            players=players
        )
        
        # 创建GameController来管理状态变更
        self.controller = GameController(self.state)
        self.players = players
    
    def test_fold_action(self):
        """测试弃牌行动"""
        print("测试弃牌行动...")
        self.setup_method()
        
        action = ActionHelper.create_player_action(self.players[0], ActionType.FOLD)
        validated = self.validator.validate(self.state, self.players[0], action)
        
        assert validated.actual_action_type == ActionType.FOLD
        assert validated.actual_amount == 0
        assert validated.player_seat == 0
        assert not validated.is_converted
        
        print("[OK] 弃牌行动测试通过")
    
    def test_check_action(self):
        """测试过牌行动"""
        print("测试过牌行动...")
        self.setup_method()
        
        # 在没有下注的情况下过牌
        action = ActionHelper.create_player_action(self.players[0], ActionType.CHECK)
        validated = self.validator.validate(self.state, self.players[0], action)
        
        assert validated.actual_action_type == ActionType.CHECK
        assert validated.actual_amount == 0
        assert not validated.is_converted
        
        print("[OK] 过牌行动测试通过")
    
    def test_call_action_with_no_bet(self):
        """测试在没有下注时跟注（应转为过牌）"""
        print("测试无下注跟注（转为过牌）...")
        self.setup_method()
        
        action = ActionHelper.create_player_action(self.players[0], ActionType.CALL)
        validated = self.validator.validate(self.state, self.players[0], action)
        
        assert validated.actual_action_type == ActionType.CHECK
        assert validated.is_converted
        assert "转为过牌" in validated.conversion_reason
        
        print("[OK] 无下注跟注转换测试通过")
    
    def test_call_action_insufficient_chips(self):
        """测试筹码不足跟注（应转为全押）"""
        print("测试筹码不足跟注（转为全押）...")
        
        # 创建专门的测试场景：模拟一个玩家已经下注，另一个玩家筹码不足跟注
        # 使用ActionValidator的内部逻辑来测试，而不是依赖实际的游戏状态
        
        # 创建一个简单的测试状态
        players = [
            Player(seat_id=0, name="玩家A", chips=100),
            Player(seat_id=1, name="玩家B", chips=30),  # 筹码较少的玩家
            Player(seat_id=2, name="玩家C", chips=200)
        ]
        
        # 创建有下注的游戏状态（通过构造函数合法设置）
        test_state = GameState(
            phase=GamePhase.PRE_FLOP,
            small_blind=1,
            big_blind=2,
            current_bet=50,  # 构造函数参数，合法设置
            current_player=1,  # 设置为玩家B的回合
            deck=Deck(),
            players=players
        )
        
        # 模拟玩家A已经下注50的情况（通过设置玩家的current_bet）
        players[0].current_bet = 50  # 这是合法的，因为是模拟之前的下注结果
        
        # 现在测试玩家B（30筹码）尝试跟注50
        player_b = players[1]
        action = ActionHelper.create_player_action(player_b, ActionType.CALL)
        validated = self.validator.validate(test_state, player_b, action)
        
        assert validated.actual_action_type == ActionType.ALL_IN
        assert validated.is_converted
        assert "转为全押" in validated.conversion_reason
        assert validated.actual_amount == 30  # 玩家B的所有筹码
        
        print("[OK] 筹码不足跟注转换测试通过")
    
    def test_bet_action(self):
        """测试下注行动"""
        print("测试下注行动...")
        self.setup_method()
        
        action = ActionHelper.create_player_action(self.players[0], ActionType.BET, amount=10)
        validated = self.validator.validate(self.state, self.players[0], action)
        
        assert validated.actual_action_type == ActionType.BET
        assert validated.actual_amount == 10
        assert not validated.is_converted
        
        print("[OK] 下注行动测试通过")
    
    def test_all_in_action(self):
        """测试全押行动"""
        print("测试全押行动...")
        self.setup_method()
        
        action = ActionHelper.create_player_action(self.players[0], ActionType.ALL_IN)
        validated = self.validator.validate(self.state, self.players[0], action)
        
        assert validated.actual_action_type == ActionType.ALL_IN
        assert validated.actual_amount == self.players[0].chips
        assert not validated.is_converted
        
        print("[OK] 全押行动测试通过")
    
    def test_get_available_actions_no_bet(self):
        """测试获取可用行动（无下注）"""
        print("测试获取可用行动（无下注）...")
        self.setup_method()
        
        actions = self.validator.get_available_actions(self.state, self.players[0])
        
        # 无下注时：可以弃牌、过牌、下注、全押
        expected = {ActionType.FOLD, ActionType.CHECK, ActionType.BET, ActionType.ALL_IN}
        assert set(actions) == expected
        
        print("[OK] 获取可用行动（无下注）测试通过")


def run_tests():
    """运行所有测试"""
    print("开始运行ActionValidator行动验证器测试...")
    print("=" * 50)
    
    test_instance = TestActionValidator()
    
    try:
        test_instance.test_fold_action()
        test_instance.test_check_action()
        test_instance.test_call_action_with_no_bet()
        test_instance.test_call_action_insufficient_chips()
        test_instance.test_bet_action()
        test_instance.test_all_in_action()
        test_instance.test_get_available_actions_no_bet()
        
        print("=" * 50)
        print("[PASS] 所有测试通过！ActionValidator行动验证器工作正常。")
        return True
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_tests() 