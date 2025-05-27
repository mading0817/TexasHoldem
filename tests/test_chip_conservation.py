"""
筹码守恒性测试
验证游戏过程中筹码总量保持不变
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core_game_logic.game.game_state import GameState
from core_game_logic.core.player import Player
from core_game_logic.phases.preflop import PreFlopPhase
from core_game_logic.core.deck import Deck
from core_game_logic.core.enums import ActionType, Action
from core_game_logic.betting.action_validator import ActionValidator


class TestChipConservation:
    """测试筹码守恒性"""
    
    def test_preflop_chip_conservation(self):
        """测试翻牌前阶段的筹码守恒"""
        # 创建2个玩家
        players = [
            Player(seat_id=0, name="Alice", chips=100),
            Player(seat_id=1, name="Bob", chips=100)
        ]
        
        state = GameState(
            players=players,
            dealer_position=0,
            small_blind=1,
            big_blind=2
        )
        
        # 记录开始时的筹码总量 - 正确的守恒公式
        total_before = sum(p.chips for p in players) + sum(p.current_bet for p in players) + state.pot
        
        # 创建牌组并发牌
        state.deck = Deck(seed=42)
        state.deck.shuffle()
        
        # 开始翻牌前阶段
        preflop = PreFlopPhase(state)
        preflop.enter()
        
        # 验证发牌后筹码守恒 - 使用正确的守恒公式
        total_after_deal = sum(p.chips for p in players) + sum(p.current_bet for p in players) + state.pot
        assert total_before == total_after_deal, f"发牌后筹码不守恒！差异: {total_after_deal - total_before}"
        
        # 模拟行动：Alice跟注，Bob过牌
        validator = ActionValidator()
        
        # Alice跟注
        alice = players[0]
        alice_action = validator.validate(state, alice, Action(ActionType.CALL))
        continuing = preflop.act(alice_action)
        
        # 验证Alice行动后筹码守恒
        total_after_alice = sum(p.chips for p in players) + sum(p.current_bet for p in players) + state.pot
        assert total_before == total_after_alice, f"Alice行动后筹码不守恒！差异: {total_after_alice - total_before}"
        
        # Bob过牌
        bob = players[1]
        bob_action = validator.validate(state, bob, Action(ActionType.CHECK))
        continuing = preflop.act(bob_action)
        
        # 验证Bob行动后筹码守恒
        total_after_bob = sum(p.chips for p in players) + sum(p.current_bet for p in players) + state.pot
        assert total_before == total_after_bob, f"Bob行动后筹码不守恒！差异: {total_after_bob - total_before}"
        
        # 退出翻牌前阶段
        next_phase = preflop.exit()
        
        # 验证最终筹码守恒
        total_final = sum(p.chips for p in players) + sum(p.current_bet for p in players) + state.pot
        assert total_before == total_final, f"最终筹码不守恒！差异: {total_final - total_before}"
    
    def test_multi_player_chip_conservation(self):
        """测试多玩家场景下的筹码守恒"""
        # 创建3个玩家
        players = [
            Player(seat_id=0, name="Alice", chips=150),
            Player(seat_id=1, name="Bob", chips=200),
            Player(seat_id=2, name="Charlie", chips=100)
        ]
        
        state = GameState(
            players=players,
            dealer_position=0,
            small_blind=5,
            big_blind=10
        )
        
        # 记录开始时的筹码总量 - 正确的守恒公式
        total_before = sum(p.chips for p in players) + sum(p.current_bet for p in players) + state.pot
        
        # 创建牌组并发牌
        state.deck = Deck(seed=123)
        state.deck.shuffle()
        
        # 开始翻牌前阶段
        preflop = PreFlopPhase(state)
        preflop.enter()
        
        # 验证发牌后筹码守恒 - 使用正确的守恒公式
        total_after_deal = sum(p.chips for p in players) + sum(p.current_bet for p in players) + state.pot
        assert total_before == total_after_deal, f"多玩家发牌后筹码不守恒！差异: {total_after_deal - total_before}"
        
        # 模拟一轮下注
        validator = ActionValidator()
        
        # Alice跟注
        alice_action = validator.validate(state, players[0], Action(ActionType.CALL))
        preflop.act(alice_action)
        
        # 验证筹码守恒
        total_after_alice = sum(p.chips for p in players) + sum(p.current_bet for p in players) + state.pot
        assert total_before == total_after_alice, f"Alice行动后筹码不守恒！"
        
        # Bob加注
        bob_action = validator.validate(state, players[1], Action(ActionType.RAISE, amount=20))
        preflop.act(bob_action)
        
        # 验证筹码守恒
        total_after_bob = sum(p.chips for p in players) + sum(p.current_bet for p in players) + state.pot
        assert total_before == total_after_bob, f"Bob行动后筹码不守恒！"
        
        # Charlie弃牌
        charlie_action = validator.validate(state, players[2], Action(ActionType.FOLD))
        preflop.act(charlie_action)
        
        # 验证筹码守恒
        total_after_charlie = sum(p.chips for p in players) + sum(p.current_bet for p in players) + state.pot
        assert total_before == total_after_charlie, f"Charlie行动后筹码不守恒！"


def run_chip_conservation_tests():
    """运行筹码守恒测试"""
    test_instance = TestChipConservation()
    
    print("开始运行筹码守恒测试...")
    print("=" * 50)
    
    tests = [
        ('翻牌前筹码守恒', test_instance.test_preflop_chip_conservation),
        ('多玩家筹码守恒', test_instance.test_multi_player_chip_conservation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✅ {test_name} - 通过")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} - 失败: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"测试结果: {passed}个通过, {failed}个失败")
    
    if failed == 0:
        print("🎉 所有筹码守恒测试通过！")
    else:
        print("⚠️  有测试失败，需要修复。")


if __name__ == "__main__":
    run_chip_conservation_tests() 