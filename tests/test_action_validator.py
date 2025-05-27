"""
ActionValidator行动验证器的单元测试
测试行动验证和智能转换逻辑
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core_game_logic.action_validator import ActionValidator
from core_game_logic.game_state import GameState
from core_game_logic.player import Player
from core_game_logic.enums import ActionType, Action, ValidatedAction, GamePhase, SeatStatus
from core_game_logic.exceptions import InvalidActionError
from core_game_logic.deck import Deck


class TestActionValidator:
    """测试ActionValidator行动验证器"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.validator = ActionValidator()
        
        # 创建游戏状态
        self.state = GameState(
            phase=GamePhase.PRE_FLOP,
            small_blind=1,
            big_blind=2,
            current_bet=0,
            current_player=0,
            deck=Deck()
        )
        
        # 创建测试玩家
        self.players = [
            Player(seat_id=0, name="玩家A", chips=100),
            Player(seat_id=1, name="玩家B", chips=50),
            Player(seat_id=2, name="玩家C", chips=200)
        ]
        self.state.players = self.players
    
    def test_fold_action(self):
        """测试弃牌行动"""
        print("测试弃牌行动...")
        self.setup_method()
        
        action = Action(ActionType.FOLD)
        validated = self.validator.validate(self.state, self.players[0], action)
        
        assert validated.actual_action_type == ActionType.FOLD
        assert validated.actual_amount == 0
        assert validated.player_seat == 0
        assert not validated.is_converted
        
        print("✓ 弃牌行动测试通过")
    
    def test_check_action_valid(self):
        """测试有效的过牌行动"""
        print("测试有效的过牌行动...")
        self.setup_method()
        
        # 没有下注时可以过牌
        action = Action(ActionType.CHECK)
        validated = self.validator.validate(self.state, self.players[0], action)
        
        assert validated.actual_action_type == ActionType.CHECK
        assert validated.actual_amount == 0
        assert not validated.is_converted
        
        print("✓ 有效过牌行动测试通过")
    
    def test_call_action_normal(self):
        """测试正常跟注行动"""
        print("测试正常跟注行动...")
        self.setup_method()
        
        # 设置下注和玩家已投入
        self.state.current_bet = 20
        self.players[0].current_bet = 10  # 已投入10，需要再跟注10
        
        action = Action(ActionType.CALL)
        validated = self.validator.validate(self.state, self.players[0], action)
        
        assert validated.actual_action_type == ActionType.CALL
        assert validated.actual_amount == 10  # 需要跟注的金额
        assert not validated.is_converted
        
        print("✓ 正常跟注行动测试通过")
    
    def test_call_action_convert_to_check(self):
        """测试跟注转换为过牌"""
        print("测试跟注转换为过牌...")
        self.setup_method()
        
        # 没有需要跟注的金额
        action = Action(ActionType.CALL)
        validated = self.validator.validate(self.state, self.players[0], action)
        
        assert validated.actual_action_type == ActionType.CHECK
        assert validated.actual_amount == 0
        assert validated.is_converted
        assert "转为过牌" in validated.conversion_reason
        
        print("✓ 跟注转换为过牌测试通过")
    
    def test_bet_action_normal(self):
        """测试正常下注行动"""
        print("测试正常下注行动...")
        self.setup_method()
        
        action = Action(ActionType.BET, amount=10)
        validated = self.validator.validate(self.state, self.players[0], action)
        
        assert validated.actual_action_type == ActionType.BET
        assert validated.actual_amount == 10
        assert not validated.is_converted
        
        print("✓ 正常下注行动测试通过")
    
    def test_all_in_action(self):
        """测试全押行动"""
        print("测试全押行动...")
        self.setup_method()
        
        action = Action(ActionType.ALL_IN)
        validated = self.validator.validate(self.state, self.players[0], action)
        
        assert validated.actual_action_type == ActionType.ALL_IN
        assert validated.actual_amount == 100  # 玩家A的全部筹码
        assert not validated.is_converted
        
        print("✓ 全押行动测试通过")
    
    def test_get_available_actions_no_bet(self):
        """测试获取可用行动（无下注）"""
        print("测试获取可用行动（无下注）...")
        self.setup_method()
        
        actions = self.validator.get_available_actions(self.state, self.players[0])
        
        # 无下注时：可以弃牌、过牌、下注、全押
        expected = {ActionType.FOLD, ActionType.CHECK, ActionType.BET, ActionType.ALL_IN}
        assert set(actions) == expected
        
        print("✓ 获取可用行动（无下注）测试通过")


def run_tests():
    """运行所有测试"""
    print("开始运行ActionValidator行动验证器测试...")
    print("=" * 50)
    
    test_instance = TestActionValidator()
    
    try:
        test_instance.test_fold_action()
        test_instance.test_check_action_valid()
        test_instance.test_call_action_normal()
        test_instance.test_call_action_convert_to_check()
        test_instance.test_bet_action_normal()
        test_instance.test_all_in_action()
        test_instance.test_get_available_actions_no_bet()
        
        print("=" * 50)
        print("✅ 所有测试通过！ActionValidator行动验证器工作正常。")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_tests() 