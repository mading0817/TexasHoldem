"""
核心游戏逻辑集成测试
验证Phase转换、PotManager、ActionValidator等组件的协同工作
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core_game_logic.game_state import GameState, phase_transition
from core_game_logic.game_controller import GameController
from core_game_logic.pot_manager import PotManager
from core_game_logic.action_validator import ActionValidator
from core_game_logic.player import Player
from core_game_logic.enums import GamePhase, ActionType, Action, SeatStatus
from core_game_logic.deck import Deck


class TestCoreIntegration:
    """测试核心游戏逻辑集成"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 创建游戏状态
        self.state = GameState(
            phase=GamePhase.PRE_FLOP,
            small_blind=1,
            big_blind=2,
            deck=Deck()
        )
        
        # 创建玩家
        self.players = [
            Player(seat_id=0, name="Alice", chips=100),
            Player(seat_id=1, name="Bob", chips=100),
            Player(seat_id=2, name="Charlie", chips=100)
        ]
        self.state.players = self.players
        self.state.dealer_position = 0
        self.state.current_player = 0
        
        # 创建组件
        self.controller = GameController(self.state)
        self.pot_manager = PotManager()
        self.validator = ActionValidator()
    
    def test_basic_game_flow(self):
        """测试基础游戏流程"""
        print("测试基础游戏流程...")
        self.setup_method()
        
        # 1. 验证初始状态
        assert self.state.phase == GamePhase.PRE_FLOP
        assert len(self.state.players) == 3
        assert self.state.pot == 0
        
        # 2. 测试行动验证
        # 玩家0尝试下注
        action = Action(ActionType.BET, amount=10)
        validated = self.validator.validate(self.state, self.players[0], action)
        assert validated.actual_action_type == ActionType.BET
        assert validated.actual_amount == 10
        
        # 3. 执行下注（模拟）
        self.players[0].bet(10)
        self.state.current_bet = 10
        self.state.pot += 10
        
        # 4. 验证状态更新
        assert self.players[0].current_bet == 10
        assert self.players[0].chips == 90
        assert self.state.current_bet == 10
        assert self.state.pot == 10
        
        print("✓ 基础游戏流程测试通过")
    
    def test_phase_transition_with_pot_collection(self):
        """测试阶段转换与底池收集"""
        print("测试阶段转换与底池收集...")
        self.setup_method()
        
        # 1. 设置玩家下注
        self.players[0].current_bet = 20
        self.players[1].current_bet = 20
        self.players[2].current_bet = 20
        
        # 2. 使用PotManager收集下注
        self.pot_manager.collect_from_players(self.players)
        
        # 3. 验证收集结果
        assert self.pot_manager.main_pot == 60
        assert self.pot_manager.get_total_pot() == 60
        for player in self.players:
            assert player.current_bet == 0
        
        # 4. 测试阶段转换
        with phase_transition(self.state):
            # 发翻牌
            self.state.community_cards = self.state.deck.deal_cards(3)
            self.state.phase = GamePhase.FLOP
        
        # 5. 验证转换成功
        assert self.state.phase == GamePhase.FLOP
        assert len(self.state.community_cards) == 3
        
        print("✓ 阶段转换与底池收集测试通过")
    
    def test_all_in_side_pot_scenario(self):
        """测试全押边池场景"""
        print("测试全押边池场景...")
        self.setup_method()
        
        # 1. 设置不同筹码量的全押
        self.players[0].chips = 30  # Alice全押30
        self.players[1].chips = 60  # Bob全押60
        self.players[2].chips = 100 # Charlie下注100
        
        # 2. 模拟全押行动
        alice_action = Action(ActionType.ALL_IN)
        bob_action = Action(ActionType.ALL_IN)
        charlie_action = Action(ActionType.BET, amount=100)
        
        # 3. 验证行动
        alice_validated = self.validator.validate(self.state, self.players[0], alice_action)
        assert alice_validated.actual_amount == 30
        
        # 4. 执行下注
        self.players[0].current_bet = 30
        self.players[1].current_bet = 60
        self.players[2].current_bet = 100
        
        # 5. 收集到边池
        self.pot_manager.collect_from_players(self.players)
        
        # 6. 验证边池结构
        # 主池：30 × 3 = 90 (所有人竞争)
        # 边池1：(60-30) × 2 = 60 (Bob和Charlie竞争)
        # 剩余：100-60 = 40 (应该退还给Charlie)
        assert self.pot_manager.main_pot == 90
        assert len(self.pot_manager.side_pots) == 1
        assert self.pot_manager.side_pots[0].amount == 60
        
        print("✓ 全押边池场景测试通过")
    
    def test_action_conversion_scenarios(self):
        """测试行动智能转换场景"""
        print("测试行动智能转换场景...")
        self.setup_method()
        
        # 1. 测试跟注转换为过牌
        call_action = Action(ActionType.CALL)
        validated = self.validator.validate(self.state, self.players[0], call_action)
        assert validated.actual_action_type == ActionType.CHECK
        assert validated.is_converted
        assert "转为过牌" in validated.conversion_reason
        
        # 2. 测试筹码不足的下注转换为全押
        self.players[1].chips = 5  # Bob只有5筹码
        self.state.current_player = 1  # 设置当前玩家为Bob
        self.state.current_bet = 0  # 确保没有当前下注，可以下注
        bet_action = Action(ActionType.BET, amount=10)  # 想下注10
        validated = self.validator.validate(self.state, self.players[1], bet_action)
        assert validated.actual_action_type == ActionType.ALL_IN
        assert validated.actual_amount == 5
        assert validated.is_converted
        assert "转为全押" in validated.conversion_reason
        
        print("✓ 行动智能转换场景测试通过")
    
    def test_game_controller_integration(self):
        """测试GameController集成"""
        print("测试GameController集成...")
        self.setup_method()
        
        # 1. 验证控制器状态
        status = self.controller.get_game_status()
        assert status['game_phase'] == 'PRE_FLOP'
        assert status['active_players'] == 3
        assert status['pot'] == 0
        
        # 2. 测试事件日志
        initial_events = len(self.state.events)
        self.state.add_event("测试事件")
        assert len(self.state.events) == initial_events + 1
        
        print("✓ GameController集成测试通过")
    
    def test_complete_betting_round(self):
        """测试完整的下注轮"""
        print("测试完整的下注轮...")
        self.setup_method()
        
        # 1. 模拟一个简单的下注场景：所有玩家都下注相同金额
        for player in self.players:
            player.bet(10)
        self.state.current_bet = 10
        
        # 2. 验证下注状态
        for player in self.players:
            assert player.current_bet == 10
        assert self.state.current_bet == 10
        
        # 3. 收集下注
        total_before = sum(p.current_bet for p in self.players)
        print(f"下注前总额: {total_before}")
        
        # 重置PotManager确保清空状态
        self.pot_manager.reset()
        self.pot_manager.collect_from_players(self.players)
        
        total_after = self.pot_manager.get_total_pot()
        print(f"收集后总额: {total_after}")
        print(f"主池: {self.pot_manager.main_pot}, 边池数: {len(self.pot_manager.side_pots)}")
        
        # 验证筹码守恒和正确分配
        assert self.pot_manager.get_total_pot() == total_before, f"期望{total_before}，实际{total_after}"
        assert self.pot_manager.main_pot == total_before, "所有筹码应该在主池中"
        assert len(self.pot_manager.side_pots) == 0, "应该没有边池"
        
        # 验证玩家current_bet被重置
        for player in self.players:
            assert player.current_bet == 0, "收集后玩家current_bet应该被重置"
        
        print("✓ 完整下注轮测试通过")


def run_tests():
    """运行所有测试"""
    print("开始运行核心游戏逻辑集成测试...")
    print("=" * 50)
    
    test_instance = TestCoreIntegration()
    
    try:
        test_instance.test_basic_game_flow()
        test_instance.test_phase_transition_with_pot_collection()
        test_instance.test_all_in_side_pot_scenario()
        test_instance.test_action_conversion_scenarios()
        test_instance.test_game_controller_integration()
        test_instance.test_complete_betting_round()
        
        print("=" * 50)
        print("✅ 所有集成测试通过！核心游戏逻辑框架工作正常。")
        print("🎉 恭喜！我们已经成功实现了德州扑克的核心游戏逻辑：")
        print("   - ✅ Phase状态机转换")
        print("   - ✅ 边池计算与分配")
        print("   - ✅ 行动验证与智能转换")
        print("   - ✅ 游戏状态管理")
        print("   - ✅ 事务性状态转换")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_tests() 