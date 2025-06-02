"""v2 CLI游戏界面测试."""

import pytest
from unittest.mock import patch, MagicMock
import io
import sys

from v2.ui.cli.cli_game import TexasHoldemCLI
from v2.core import ActionType


class TestTexasHoldemCLI:
    """CLI游戏界面测试类."""
    
    def test_cli_initialization(self):
        """测试CLI初始化."""
        cli = TexasHoldemCLI(human_seat=0, num_players=4, initial_chips=1000)
        
        assert cli.human_seat == 0
        assert cli.num_players == 4
        assert cli.initial_chips == 1000
        assert cli.controller is not None
        
        # 验证玩家已添加
        snapshot = cli.controller.get_snapshot()
        assert len(snapshot.players) == 4
        
        # 验证人类玩家名称
        human_player = next(p for p in snapshot.players if p.seat_id == 0)
        assert human_player.name == "You"
        
        # 验证AI玩家名称
        ai_player = next(p for p in snapshot.players if p.seat_id == 1)
        assert ai_player.name == "AI_1"
    
    def test_display_game_state(self):
        """测试游戏状态显示."""
        cli = TexasHoldemCLI(num_players=2)
        
        # 捕获输出
        captured_output = io.StringIO()
        with patch('sys.stdout', captured_output):
            with patch.object(cli.logger, 'info') as mock_logger:
                cli._display_game_state()
                
                # 验证日志调用
                assert mock_logger.call_count > 0
                
                # 验证包含基本信息
                calls = [call.args[0] for call in mock_logger.call_args_list]
                output_text = ' '.join(calls)
                assert '阶段:' in output_text
                assert '底池:' in output_text
                assert '玩家状态:' in output_text
    
    def test_get_available_actions(self):
        """测试获取可用行动."""
        cli = TexasHoldemCLI(num_players=2)
        snapshot = cli.controller.get_snapshot()
        player = snapshot.players[0]
        
        # 测试初始状态的可用行动
        actions = cli._get_available_actions(player, snapshot)
        
        # 应该包含弃牌和过牌（初始状态无下注）
        action_types = [action[0] for action in actions]
        assert ActionType.FOLD in action_types
        assert ActionType.CHECK in action_types
        
        # 应该包含下注选项
        assert ActionType.BET in action_types
        
        # 应该包含全押选项
        assert ActionType.ALL_IN in action_types
    
    @patch('builtins.input')
    def test_handle_human_action_fold(self, mock_input):
        """测试人类玩家弃牌行动."""
        mock_input.return_value = '1'  # 选择第一个选项（弃牌）
        
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
    
    @patch('builtins.input')
    def test_handle_human_action_check(self, mock_input):
        """测试人类玩家过牌行动."""
        mock_input.return_value = '2'  # 选择第二个选项（过牌）
        
        cli = TexasHoldemCLI(num_players=2)
        
        # 开始新手牌
        cli.controller.start_new_hand()
        
        # 模拟人类玩家行动
        with patch.object(cli.logger, 'info'):
            cli._handle_human_action()
        
        # 验证行动成功执行（没有异常）
        snapshot = cli.controller.get_snapshot()
        assert snapshot is not None
    
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
    
    @patch('builtins.input')
    def test_should_continue_user_choice(self, mock_input):
        """测试用户选择是否继续."""
        mock_input.return_value = 'n'  # 用户选择不继续
        
        cli = TexasHoldemCLI(num_players=2)
        
        result = cli._should_continue()
        assert result is False
        
        # 测试用户选择继续
        mock_input.return_value = 'y'
        result = cli._should_continue()
        assert result is True
    
    def test_display_hand_result(self):
        """测试手牌结果显示."""
        from v2.controller import HandResult
        
        cli = TexasHoldemCLI(num_players=2)
        
        # 创建测试结果
        result = HandResult(
            winner_ids=[0],
            pot_amount=100,
            winning_hand_description="高牌",
            side_pots=[]
        )
        
        # 测试显示结果
        with patch.object(cli.logger, 'info') as mock_logger:
            cli._display_hand_result(result)
            
            # 验证显示了基本信息
            calls = [call.args[0] for call in mock_logger.call_args_list]
            output_text = ' '.join(calls)
            assert '手牌结束' in output_text
            assert '底池: 100' in output_text
            assert '获胜者:' in output_text
    
    @patch('builtins.input')
    def test_get_bet_amount(self, mock_input):
        """测试获取下注金额."""
        mock_input.return_value = '50'
        
        cli = TexasHoldemCLI(num_players=2)
        snapshot = cli.controller.get_snapshot()
        
        # 测试下注金额输入
        amount = cli._get_bet_amount(ActionType.BET, snapshot)
        assert amount == 50
    
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