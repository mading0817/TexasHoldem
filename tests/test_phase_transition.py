"""
Phase转换机制的单元测试
测试事务性转换和状态回滚功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core_game_logic.game.game_state import GameState, phase_transition, _validate_state_invariants
from core_game_logic.core.player import Player
from core_game_logic.core.enums import GamePhase, SeatStatus
from core_game_logic.core.exceptions import GameStateError, PhaseTransitionError
from core_game_logic.core.deck import Deck


class TestPhaseTransition:
    """测试Phase转换机制"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.state = GameState(
            phase=GamePhase.PRE_FLOP,
            small_blind=1,
            big_blind=2,
            deck=Deck()
        )
        
        # 添加测试玩家
        self.state.players = [
            Player(seat_id=0, name="玩家1", chips=100),
            Player(seat_id=1, name="玩家2", chips=100),
            Player(seat_id=2, name="玩家3", chips=100)
        ]
    
    def test_successful_phase_transition(self):
        """测试成功的阶段转换"""
        print("测试成功的阶段转换...")
        self.setup_method()
        
        initial_events_count = len(self.state.events)
        
        with phase_transition(self.state):
            # 模拟发3张翻牌
            self.state.community_cards = self.state.deck.deal_cards(3)
            self.state.phase = GamePhase.FLOP
        
        # 验证转换成功
        assert self.state.phase == GamePhase.FLOP
        assert len(self.state.community_cards) == 3
        assert len(self.state.events) > initial_events_count
        
        # 检查事件日志
        events_text = " ".join(self.state.events)
        assert "开始阶段转换" in events_text
        assert "状态验证通过" in events_text
        assert "阶段转换完成" in events_text
        print("✓ 成功的阶段转换测试通过")
    
    def test_phase_transition_rollback_on_invalid_state(self):
        """测试无效状态时的自动回滚"""
        print("测试无效状态时的自动回滚...")
        self.setup_method()
        
        original_phase = self.state.phase
        original_cards_count = len(self.state.community_cards)
        
        try:
            with phase_transition(self.state):
                # 创建无效状态：FLOP阶段但没有公共牌
                self.state.phase = GamePhase.FLOP
                # 不发牌，导致状态不一致
        except GameStateError:
            pass  # 预期的异常
        
        # 验证状态已回滚
        assert self.state.phase == original_phase
        assert len(self.state.community_cards) == original_cards_count
        
        # 检查回滚事件
        events_text = " ".join(self.state.events)
        assert "阶段转换回滚" in events_text
        print("✓ 无效状态回滚测试通过")
    
    def test_phase_transition_rollback_on_exception(self):
        """测试异常时的自动回滚"""
        print("测试异常时的自动回滚...")
        self.setup_method()
        
        original_pot = self.state.pot
        
        try:
            with phase_transition(self.state):
                self.state.pot = 50
                # 人为抛出异常
                raise ValueError("测试异常")
        except PhaseTransitionError:
            pass  # 预期的异常
        
        # 验证状态已回滚
        assert self.state.pot == original_pot
        print("✓ 异常回滚测试通过")
    
    def test_state_invariants_validation(self):
        """测试状态不变式验证"""
        print("测试状态不变式验证...")
        self.setup_method()
        
        # 测试正常状态
        _validate_state_invariants(self.state)
        
        # 测试负筹码异常
        self.state.players[0].chips = -10
        try:
            _validate_state_invariants(self.state)
            assert False, "应该抛出异常"
        except GameStateError as e:
            assert "筹码不能为负数" in str(e)
        
        # 恢复正常状态
        self.state.players[0].chips = 100
        
        # 测试阶段与公共牌不一致
        self.state.phase = GamePhase.FLOP
        # FLOP阶段应该有3张公共牌，但现在是0张
        try:
            _validate_state_invariants(self.state)
            assert False, "应该抛出异常"
        except GameStateError as e:
            assert "应有3张公共牌" in str(e)
        
        print("✓ 状态不变式验证测试通过")
    
    def test_clone_functionality(self):
        """测试状态克隆功能"""
        print("测试状态克隆功能...")
        self.setup_method()
        
        # 修改原始状态
        self.state.pot = 100
        self.state.players[0].chips = 50
        
        # 创建克隆
        cloned_state = self.state.clone()
        
        # 验证克隆的独立性
        assert cloned_state.pot == self.state.pot
        assert cloned_state.players[0].chips == self.state.players[0].chips
        
        # 修改克隆不应影响原始状态
        cloned_state.pot = 200
        cloned_state.players[0].chips = 25
        
        assert self.state.pot == 100
        assert self.state.players[0].chips == 50
        print("✓ 状态克隆功能测试通过")
    
    def test_event_logging(self):
        """测试事件日志功能"""
        print("测试事件日志功能...")
        self.setup_method()
        
        initial_count = len(self.state.events)
        
        self.state.add_event("测试事件1")
        self.state.add_event("测试事件2")
        
        assert len(self.state.events) == initial_count + 2
        assert "测试事件1" in self.state.events
        assert "测试事件2" in self.state.events
        print("✓ 事件日志功能测试通过")


def run_tests():
    """运行所有测试"""
    print("开始运行Phase转换机制测试...")
    print("=" * 50)
    
    test_instance = TestPhaseTransition()
    
    try:
        test_instance.test_successful_phase_transition()
        test_instance.test_phase_transition_rollback_on_invalid_state()
        test_instance.test_phase_transition_rollback_on_exception()
        test_instance.test_state_invariants_validation()
        test_instance.test_clone_functionality()
        test_instance.test_event_logging()
        
        print("=" * 50)
        print("✅ 所有测试通过！Phase转换机制工作正常。")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_tests() 
 