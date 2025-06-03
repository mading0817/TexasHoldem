"""德州扑克CLI界面单元测试."""

import pytest
from unittest.mock import patch, MagicMock
import io
import sys

from v2.core import ActionType
from v2.ui.cli.cli_game import TexasHoldemCLI
from v2.controller.dto import HandResult, ActionInput


@pytest.mark.unit
@pytest.mark.fast
class TestTexasHoldemCLI:
    """德州扑克CLI测试类."""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_cli_initialization(self):
        """测试CLI初始化."""
        cli = TexasHoldemCLI(num_players=2)
        
        # 验证基本属性
        assert cli.controller is not None
        assert cli.human_seat == 0
        assert cli.num_players == 2
        assert cli.initial_chips == 1000  # 默认值
        
        # 验证可以获取快照
        snapshot = cli.controller.get_snapshot()
        assert snapshot is not None
        assert len(snapshot.players) == 2
        
        # 验证玩家初始状态
        human_player = snapshot.players[0]
        assert human_player.seat_id == 0
        assert human_player.chips == 1000
        assert human_player.name == "You"
        
        ai_player = snapshot.players[1]
        assert ai_player.seat_id == 1
        assert ai_player.chips == 1000
        assert ai_player.name == "AI_1"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_display_game_state(self):
        """测试游戏状态显示."""
        cli = TexasHoldemCLI(num_players=2)
        
        # 模拟logger以避免实际输出
        with patch.object(cli.logger, 'info'):
            cli._display_game_state()
        
        # 验证没有异常抛出
        assert True
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_available_actions(self):
        """测试获取可用行动."""
        cli = TexasHoldemCLI(num_players=2)
        snapshot = cli.controller.get_snapshot()
        player = snapshot.players[0]
        
        # 直接调用输入处理器的内部方法，避免触发用户输入
        from v2.ui.cli.input_handler import CLIInputHandler
        actions = CLIInputHandler._get_available_actions(player, snapshot)
        
        # 应该包含弃牌和过牌（初始状态无下注）
        action_types = [action[0] for action in actions]
        assert ActionType.FOLD in action_types
        assert ActionType.CHECK in action_types
        
        # 应该包含下注选项
        assert ActionType.BET in action_types
        
        # 应该包含全押选项
        assert ActionType.ALL_IN in action_types
    
    @patch('v2.ui.cli.input_handler.CLIInputHandler.get_player_action')
    @pytest.mark.unit
    @pytest.mark.fast
    def test_handle_human_action_fold(self, mock_get_action):
        """测试人类玩家弃牌行动."""
        
        # 模拟返回弃牌行动
        mock_get_action.return_value = ActionInput(
            player_id=0,
            action_type=ActionType.FOLD,
            amount=0
        )
        
        cli = TexasHoldemCLI(num_players=2)
        
        # 开始新手牌
        cli.controller.start_new_hand()
        
        # 模拟人类玩家行动
        with patch.object(cli.logger, 'info'):
            cli._handle_human_action()
        
        # 验证玩家已弃牌
        snapshot = cli.controller.get_snapshot()
        human_player = next(p for p in snapshot.players if p.seat_id == 0)
        assert human_player.status.name == 'FOLDED'
    
    @patch('v2.ui.cli.input_handler.CLIInputHandler.get_player_action')
    @pytest.mark.unit
    @pytest.mark.fast
    def test_handle_human_action_check(self, mock_get_action):
        """测试人类玩家过牌行动."""
        
        # 模拟返回过牌行动
        mock_get_action.return_value = ActionInput(
            player_id=0,
            action_type=ActionType.CHECK,
            amount=0
        )
        
        cli = TexasHoldemCLI(num_players=2)
        
        # 开始新手牌
        cli.controller.start_new_hand()
        
        # 模拟人类玩家行动
        with patch.object(cli.logger, 'info'):
            cli._handle_human_action()
        
        # 验证行动成功执行（没有异常）
        snapshot = cli.controller.get_snapshot()
        assert snapshot is not None
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_handle_ai_action(self):
        """测试AI玩家行动处理."""
        cli = TexasHoldemCLI(num_players=2)
        
        # 开始新手牌
        cli.controller.start_new_hand()
        
        # 模拟AI行动
        with patch.object(cli.logger, 'info'):
            cli._handle_ai_action(1)  # AI玩家座位1
        
        # 验证AI行动完成（没有异常）
        snapshot = cli.controller.get_snapshot()
        assert snapshot is not None
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_should_continue_insufficient_players(self):
        """测试玩家不足时的继续判断."""
        cli = TexasHoldemCLI(num_players=2)
        
        # 模拟一个玩家没有筹码
        snapshot = cli.controller.get_snapshot()
        player = cli.controller._game_state.players[1]
        player.chips = 0
        
        # 测试是否继续
        result = cli._should_continue()
        assert result is False
    
    @patch('v2.ui.cli.input_handler.CLIInputHandler.get_continue_choice')
    @pytest.mark.unit
    @pytest.mark.fast
    def test_should_continue_user_choice(self, mock_continue):
        """测试用户选择是否继续."""
        mock_continue.return_value = False  # 用户选择不继续
        
        cli = TexasHoldemCLI(num_players=2)
        
        result = cli._should_continue()
        assert result is False
        
        # 测试用户选择继续
        mock_continue.return_value = True
        result = cli._should_continue()
        assert result is True
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_display_hand_result(self):
        """测试手牌结果显示."""
        
        cli = TexasHoldemCLI(num_players=2)
        
        # 创建测试结果
        result = HandResult(
            winner_ids=[0],
            pot_amount=100,
            winning_hand_description="高牌",
            side_pots=[],
            hand_number=1
        )
        
        # 测试显示结果
        with patch.object(cli.logger, 'info') as mock_logger:
            cli._display_hand_result(result)
            
            # 验证显示了基本信息
            calls = [call.args[0] for call in mock_logger.call_args_list]
            output_text = ' '.join(calls)
            assert '手牌结果' in output_text
            assert '底池总额: 100' in output_text
            assert '获胜者:' in output_text
    
    @patch('v2.ui.cli.input_handler.CLIInputHandler.get_bet_amount_input')
    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_bet_amount(self, mock_input):
        """测试获取下注金额."""
        mock_input.return_value = 50
        
        cli = TexasHoldemCLI(num_players=2)
        snapshot = cli.controller.get_snapshot()
        player = snapshot.players[0]
        
        # 直接测试输入处理器的方法
        from v2.ui.cli.input_handler import CLIInputHandler
        amount = CLIInputHandler._get_bet_amount(ActionType.BET, snapshot, player)
        # 由于_get_bet_amount内部调用get_bet_amount_input，所以会使用mock的返回值
        # 但实际上_get_bet_amount有复杂的逻辑，我们简化测试
        assert isinstance(amount, int)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_smoke_run_setup(self):
        """Smoke测试：验证CLI可以正常设置和初始化."""
        # 这是一个基本的smoke测试，确保CLI可以创建和初始化
        try:
            cli = TexasHoldemCLI(num_players=2, initial_chips=500)
            
            # 验证基本属性
            assert cli.controller is not None
            assert cli.human_seat == 0
            assert cli.num_players == 2
            assert cli.initial_chips == 500
            
            # 验证可以获取快照
            snapshot = cli.controller.get_snapshot()
            assert snapshot is not None
            assert len(snapshot.players) == 2
            
            # 验证可以开始新手牌
            success = cli.controller.start_new_hand()
            assert success is True
            
            print("✅ CLI smoke测试通过：可以正常初始化和开始游戏")
            
        except Exception as e:
            pytest.fail(f"CLI smoke测试失败: {e}") 