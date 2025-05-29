"""
筹码守恒定律的单元测试
确保游戏中筹码总数保持不变
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
from core_game_logic.core.deck import Deck
from tests.common.test_helpers import ActionHelper


class TestChipConservation:
    """测试筹码守恒定律"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 创建测试玩家
        self.players = [
            Player(seat_id=0, name="Alice", chips=100),
            Player(seat_id=1, name="Bob", chips=100)
        ]
        
        # 创建游戏状态
        self.state = GameState(
            phase=GamePhase.PRE_FLOP,
            small_blind=1,
            big_blind=2,
            current_bet=0,
            current_player=0,
            deck=Deck()
        )
        self.state.players = self.players
        
        # 使用GameController管理游戏状态
        self.controller = GameController(self.state)
        
        # 计算初始筹码总数
        self.initial_total = sum(p.chips for p in self.players)
    
    def test_call_and_check_conservation(self):
        """测试跟注和过牌时的筹码守恒"""
        print("测试跟注和过牌的筹码守恒...")
        self.setup_method()
        
        # Alice是当前玩家（seat_id=0），她先行动 - 过牌
        alice = self.players[0]
        alice_action = ActionHelper.create_player_action(alice, ActionType.CHECK)
        # 通过GameController处理行动，而不是直接修改状态
        self.controller.process_action(alice_action)
        
        # Bob也过牌
        bob = self.players[1]
        bob_action = ActionHelper.create_player_action(bob, ActionType.CHECK)
        self.controller.process_action(bob_action)
        
        # 计算当前筹码总数
        current_total = sum(p.chips for p in self.players) + self.state.pot + sum(p.current_bet for p in self.players)
        
        print(f"初始筹码: {self.initial_total}, 当前筹码: {current_total}")
        assert current_total == self.initial_total, f"筹码不守恒！初始: {self.initial_total}, 当前: {current_total}"
        
        print("[OK] 跟注和过牌筹码守恒测试通过")
    
    def test_multiple_betting_rounds_conservation(self):
        """测试多轮下注的筹码守恒"""
        print("测试多轮下注的筹码守恒...")
        
        # 创建更多玩家进行复杂测试
        players = [
            Player(seat_id=0, name="Alice", chips=999),
            Player(seat_id=1, name="Bob", chips=999),
            Player(seat_id=2, name="Charlie", chips=999)
        ]
        
        # 重新创建游戏状态和控制器
        self.state = GameState(
            phase=GamePhase.PRE_FLOP,
            small_blind=1,
            big_blind=2,
            current_bet=0,
            current_player=0,
            deck=Deck()
        )
        self.state.players = players
        self.controller = GameController(self.state)
        
        initial_total = sum(p.chips for p in players)
        print(f"初始状态: Alice={players[0].chips}, Bob={players[1].chips}, Charlie={players[2].chips}, pot={self.state.pot}")
        
        # 第一轮：Alice过牌
        alice_action = ActionHelper.create_player_action(players[0], ActionType.CHECK)
        self.controller.process_action(alice_action)
        print(f"Alice过牌后: Alice={players[0].chips}, Bob={players[1].chips}, Charlie={players[2].chips}, pot={self.state.pot}")
        
        # Bob下注 - 通过GameController处理
        bob_action = ActionHelper.create_player_action(players[1], ActionType.BET, amount=20)
        self.controller.process_action(bob_action)
        
        print(f"Bob下注后: chips={players[1].chips}, current_bet={players[1].current_bet}, pot={self.state.pot}")
        
        # Charlie弃牌 - 通过GameController处理
        charlie_action = ActionHelper.create_player_action(players[2], ActionType.FOLD)
        self.controller.process_action(charlie_action)
        print(f"Charlie弃牌后: Alice={players[0].chips}, Bob={players[1].chips}, Charlie={players[2].chips}, pot={self.state.pot}")
        
        # 验证筹码守恒
        current_total = sum(p.chips for p in players) + self.state.pot + sum(p.current_bet for p in players)
        print(f"最终统计: 玩家筹码总计={sum(p.chips for p in players)}, 底池={self.state.pot}, 当前下注总计={sum(p.current_bet for p in players)}")
        
        print(f"初始筹码: {initial_total}, 当前筹码: {current_total}")
        assert current_total == initial_total, f"筹码不守恒！初始: {initial_total}, 当前: {current_total}"
        
        print("[OK] 多轮下注筹码守恒测试通过")


def run_chip_conservation_tests():
    """运行筹码守恒测试"""
    test_instance = TestChipConservation()
    
    print("开始运行筹码守恒测试...")
    print("=" * 50)
    
    tests = [
        ('跟注和过牌筹码守恒', test_instance.test_call_and_check_conservation),
        ('多轮下注筹码守恒', test_instance.test_multiple_betting_rounds_conservation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"[PASS] {test_name} - 通过")
            passed += 1
        except Exception as e:
            print(f"[ERROR] {test_name} - 失败: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"测试结果: {passed}个通过, {failed}个失败")
    
    if failed == 0:
        print("[SUCCESS] 所有筹码守恒测试通过！")
    else:
        print("[WARNING] 有测试失败，需要修复。")


if __name__ == "__main__":
    run_chip_conservation_tests() 