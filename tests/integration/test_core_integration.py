"""
核心游戏逻辑集成测试
验证Phase转换、PotManager、ActionValidator等组件的协同工作
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_game_logic.game.game_state import GameState, phase_transition
from core_game_logic.game.game_controller import GameController
from core_game_logic.betting.pot_manager import PotManager
from core_game_logic.betting.action_validator import ActionValidator
from core_game_logic.core.player import Player
from core_game_logic.core.enums import GamePhase, ActionType, Action, SeatStatus
from core_game_logic.core.deck import Deck
from tests.common.test_helpers import ActionHelper


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
        action = ActionHelper.create_player_action(self.players[0], ActionType.BET, amount=10)
        validated = self.validator.validate(self.state, self.players[0], action)
        assert validated.actual_action_type == ActionType.BET
        assert validated.actual_amount == 10
        
        # 3. 执行下注（使用合法API）
        self.players[0].bet(10)
        
        # 4. 手动更新游戏状态 - 在真实游戏中由GameController管理
        self.state.current_bet = max(self.state.current_bet, self.players[0].current_bet)
        self.state.pot += self.players[0].current_bet
        
        # 5. 验证状态更新
        assert self.players[0].current_bet == 10
        assert self.players[0].chips == 90
        assert self.state.current_bet == 10
        assert self.state.pot == 10
        
        print("[OK] 基础游戏流程测试通过")
    
    def test_phase_transition_with_pot_collection(self):
        """测试阶段转换与底池收集"""
        print("测试阶段转换与底池收集...")
        self.setup_method()
        
        # 1. 使用合法API设置玩家下注 - 不直接修改current_bet
        # 通过bet()方法进行下注
        for player in self.players:
            player.bet(20)
        
        # 2. 使用PotManager收集下注
        self.pot_manager.collect_from_players(self.players)
        
        # 3. 验证收集结果
        assert self.pot_manager.main_pot == 60
        assert self.pot_manager.get_total_pot() == 60
        for player in self.players:
            assert player.current_bet == 0
        
        # 4. 先将游戏阶段推进到FLOP，再在phase_transition中发牌
        # 这样符合德州扑克的正确流程
        # 使用phase_transition上下文管理器来合法地转换阶段
        with phase_transition(self.state):
            self.state.phase = GamePhase.FLOP
            # 现在在FLOP阶段发翻牌是合法的
            self.state.community_cards = self.state.deck.deal_cards(3)
        assert len(self.state.community_cards) == 3
        
        print("[OK] 阶段转换与底池收集测试通过")
    
    def test_all_in_side_pot_scenario(self):
        """测试全押边池场景"""
        print("测试全押边池场景...")
        self.setup_method()
        
        # 1. 在初始化时设置不同筹码量 - 合法的初始化设置
        # 重新创建玩家，这是合法的测试设置
        self.players = [
            Player(seat_id=0, name="Alice", chips=30),  # Alice全押30
            Player(seat_id=1, name="Bob", chips=60),    # Bob全押60  
            Player(seat_id=2, name="Charlie", chips=100) # Charlie下注100
        ]
        self.state.players = self.players
        
        # 2. 模拟全押行动
        alice_action = ActionHelper.create_player_action(self.players[0], ActionType.ALL_IN)
        bob_action = ActionHelper.create_player_action(self.players[1], ActionType.ALL_IN)
        charlie_action = ActionHelper.create_player_action(self.players[2], ActionType.BET, amount=100)
        
        # 3. 验证行动
        alice_validated = self.validator.validate(self.state, self.players[0], alice_action)
        assert alice_validated.actual_amount == 30
        
        # 4. 使用合法的bet()方法执行下注，而不是直接修改current_bet
        self.players[0].bet(30)  # Alice全押
        self.players[1].bet(60)  # Bob全押
        self.players[2].bet(100) # Charlie下注
        
        # 5. 收集到边池
        self.pot_manager.collect_from_players(self.players)
        
        # 6. 验证边池结构
        # 主池：30 × 3 = 90 (所有人竞争)
        # 边池1：(60-30) × 2 = 60 (Bob和Charlie竞争)
        # 剩余：100-60 = 40 (应该退还给Charlie)
        assert self.pot_manager.main_pot == 90
        assert len(self.pot_manager.side_pots) == 1
        assert self.pot_manager.side_pots[0].amount == 60
        
        print("[OK] 全押边池场景测试通过")
    
    def test_action_conversion_scenarios(self):
        """测试行动智能转换场景"""
        print("测试行动智能转换场景...")
        self.setup_method()
        
        # 设置当前玩家为0号位（测试环境下的初始化设置）
        self.state.current_player = 0
        current_player = self.players[0]
        
        # 1. 测试跟注转换为过牌
        call_action = ActionHelper.create_player_action(current_player, ActionType.CALL)
        validated = self.validator.validate(self.state, current_player, call_action)
        assert validated.actual_action_type == ActionType.CHECK
        assert validated.is_converted
        assert "转为过牌" in validated.conversion_reason
        
        # 2. 测试筹码不足的下注转换为全押
        # 重新设置游戏状态，让1号玩家成为当前玩家
        self.setup_method()
        self.state.current_player = 1
        
        # 重新创建玩家以设置合法的初始筹码量
        low_chip_player = Player(seat_id=1, name="Bob", chips=5)
        self.players[1] = low_chip_player
        self.state.players[1] = low_chip_player
        
        bet_action = ActionHelper.create_player_action(low_chip_player, ActionType.BET, amount=20)
        validated = self.validator.validate(self.state, low_chip_player, bet_action)
        assert validated.actual_action_type == ActionType.ALL_IN
        assert validated.actual_amount == 5
        assert validated.is_converted
        assert "转为全押" in validated.conversion_reason
        
        print("[OK] 行动智能转换场景测试通过")
    
    def test_game_controller_integration(self):
        """测试GameController集成"""
        print("测试GameController集成...")
        self.setup_method()
        
        # 使用GameController，传递必需的state参数
        controller = GameController(self.state)
        
        # 1. 验证初始化状态
        status = controller.get_game_status()
        assert status['game_phase'] == 'PRE_FLOP'
        assert status['active_players'] == 3
        assert status['pot'] == 0
        
        # 2. 测试事件日志
        initial_events = len(self.state.events)
        self.state.add_event("测试事件")
        assert len(self.state.events) == initial_events + 1
        
        print("[OK] GameController集成测试通过")
    
    def test_complete_betting_round(self):
        """测试完整的下注轮"""
        print("测试完整的下注轮...")
        self.setup_method()
        
        # 1. 使用GameState的set_blinds()方法来设置合法的初始下注状态
        # 这是德州扑克游戏的正确流程，会正确设置current_bet
        self.state.set_blinds()
        
        # 2. 验证盲注设置正确
        assert self.state.current_bet == self.state.big_blind
        
        # 3. 模拟其他玩家跟注 - 通过合法的游戏操作
        # 找到不是大盲的玩家进行跟注
        for player in self.players:
            if not player.is_big_blind:
                # 跟注到大盲水平
                call_amount = self.state.current_bet - player.current_bet
                if call_amount > 0:
                    player.bet(call_amount)
        
        # 4. 收集下注
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
        
        print("[OK] 完整下注轮测试通过")


def run_tests():
    """运行所有测试"""
    try:
        print("开始运行核心游戏逻辑集成测试...")
        print("=" * 50)
        
        test_instance = TestCoreIntegration()
        
        # 运行所有测试方法
        test_instance.test_basic_game_flow()
        test_instance.test_phase_transition_with_pot_collection()
        test_instance.test_all_in_side_pot_scenario()
        test_instance.test_action_conversion_scenarios()
        test_instance.test_game_controller_integration()
        test_instance.test_complete_betting_round()
        
        print("\n" + "=" * 50)
        print("[OK] 所有集成测试通过!")
        print("恭喜！我们已经成功实现了德州扑克的核心游戏逻辑：")
        print("   - [OK] Phase状态机转换")
        print("   - [OK] 边池计算与分配")
        print("   - [OK] 行动验证与智能转换")
        print("   - [OK] 游戏状态管理")
        print("   - [OK] 事务性状态转换")
        return True
        
    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_tests() 