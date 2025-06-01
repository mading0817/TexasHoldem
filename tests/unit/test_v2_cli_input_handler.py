"""CLI输入处理器单元测试.

测试CLI输入处理器的各种输入处理功能，包括行动选择、金额输入和校验。
"""

import pytest
from unittest.mock import patch, MagicMock
import click
from v2.ui.cli.input_handler import CLIInputHandler, InputValidationError
from v2.core import ActionType, Phase, SeatStatus
from v2.controller import ActionInput


class TestCLIInputHandler:
    """CLI输入处理器测试类."""
    
    def test_get_available_actions_preflop_no_bet(self):
        """测试翻牌前无下注时的可用行动."""
        # 创建测试快照
        player = type('Player', (), {
            'seat_id': 0,
            'name': 'Test',
            'chips': 1000,
            'current_bet': 0,
            'status': SeatStatus.ACTIVE
        })()
        
        snapshot = type('GameSnapshot', (), {
            'current_bet': 0,
            'big_blind': 20,
            'last_raise_amount': None
        })()
        
        actions = CLIInputHandler._get_available_actions(player, snapshot)
        
        # 应该包含：弃牌、过牌、下注、全押
        action_types = [action[0] for action in actions]
        assert ActionType.FOLD in action_types
        assert ActionType.CHECK in action_types
        assert ActionType.BET in action_types
        assert ActionType.ALL_IN in action_types
        assert ActionType.CALL not in action_types
        assert ActionType.RAISE not in action_types
    
    def test_get_available_actions_with_bet_to_call(self):
        """测试有下注需要跟注时的可用行动."""
        player = type('Player', (), {
            'seat_id': 0,
            'name': 'Test',
            'chips': 1000,
            'current_bet': 0,
            'status': SeatStatus.ACTIVE
        })()
        
        snapshot = type('GameSnapshot', (), {
            'current_bet': 50,
            'big_blind': 20,
            'last_raise_amount': 30
        })()
        
        actions = CLIInputHandler._get_available_actions(player, snapshot)
        
        # 应该包含：弃牌、跟注、加注、全押
        action_types = [action[0] for action in actions]
        assert ActionType.FOLD in action_types
        assert ActionType.CALL in action_types
        assert ActionType.RAISE in action_types
        assert ActionType.ALL_IN in action_types
        assert ActionType.CHECK not in action_types
        assert ActionType.BET not in action_types
    
    def test_get_available_actions_insufficient_chips_for_call(self):
        """测试筹码不足跟注时的可用行动."""
        player = type('Player', (), {
            'seat_id': 0,
            'name': 'Test',
            'chips': 30,
            'current_bet': 0,
            'status': SeatStatus.ACTIVE
        })()
        
        snapshot = type('GameSnapshot', (), {
            'current_bet': 50,
            'big_blind': 20,
            'last_raise_amount': 30
        })()
        
        actions = CLIInputHandler._get_available_actions(player, snapshot)
        
        # 应该包含：弃牌、全押（但不能跟注或加注）
        action_types = [action[0] for action in actions]
        assert ActionType.FOLD in action_types
        assert ActionType.ALL_IN in action_types
        assert ActionType.CALL not in action_types
        assert ActionType.RAISE not in action_types
    
    def test_get_available_actions_small_stack(self):
        """测试小筹码时的可用行动."""
        player = type('Player', (), {
            'seat_id': 0,
            'name': 'Test',
            'chips': 5,
            'current_bet': 0,
            'status': SeatStatus.ACTIVE
        })()
        
        snapshot = type('GameSnapshot', (), {
            'current_bet': 0,
            'big_blind': 20,
            'last_raise_amount': None
        })()
        
        actions = CLIInputHandler._get_available_actions(player, snapshot)
        
        # 筹码不足最小下注，应该只有：弃牌、过牌、全押
        action_types = [action[0] for action in actions]
        assert ActionType.FOLD in action_types
        assert ActionType.CHECK in action_types
        assert ActionType.ALL_IN in action_types
        assert ActionType.BET not in action_types
    
    @patch('click.prompt')
    @patch('click.echo')
    def test_get_player_action_fold(self, mock_echo, mock_prompt):
        """测试玩家选择弃牌."""
        mock_prompt.return_value = 1  # 选择第一个选项（弃牌）
        
        player = type('Player', (), {
            'seat_id': 0,
            'name': 'Test',
            'chips': 1000,
            'current_bet': 0,
            'status': SeatStatus.ACTIVE
        })()
        
        snapshot = type('GameSnapshot', (), {
            'players': [player],
            'current_bet': 0,
            'big_blind': 20,
            'last_raise_amount': None
        })()
        
        result = CLIInputHandler.get_player_action(snapshot, 0)
        
        assert result.player_id == 0
        assert result.action_type == ActionType.FOLD
        assert result.amount == 0
    
    @patch('click.prompt')
    @patch('click.echo')
    def test_get_player_action_call(self, mock_echo, mock_prompt):
        """测试玩家选择跟注."""
        mock_prompt.return_value = 2  # 选择第二个选项（跟注）
        
        player = type('Player', (), {
            'seat_id': 0,
            'name': 'Test',
            'chips': 1000,
            'current_bet': 0,
            'status': SeatStatus.ACTIVE
        })()
        
        snapshot = type('GameSnapshot', (), {
            'players': [player],
            'current_bet': 50,
            'big_blind': 20,
            'last_raise_amount': 30
        })()
        
        result = CLIInputHandler.get_player_action(snapshot, 0)
        
        assert result.player_id == 0
        assert result.action_type == ActionType.CALL
        assert result.amount == 50
    
    @patch('v2.ui.cli.input_handler.CLIInputHandler.get_bet_amount_input')
    @patch('click.prompt')
    @patch('click.echo')
    def test_get_player_action_bet(self, mock_echo, mock_prompt, mock_bet_input):
        """测试玩家选择下注."""
        mock_prompt.return_value = 3  # 选择第三个选项（下注）
        mock_bet_input.return_value = 100
        
        player = type('Player', (), {
            'seat_id': 0,
            'name': 'Test',
            'chips': 1000,
            'current_bet': 0,
            'status': SeatStatus.ACTIVE
        })()
        
        snapshot = type('GameSnapshot', (), {
            'players': [player],
            'current_bet': 0,
            'big_blind': 20,
            'last_raise_amount': None
        })()
        
        result = CLIInputHandler.get_player_action(snapshot, 0)
        
        assert result.player_id == 0
        assert result.action_type == ActionType.BET
        assert result.amount == 100
        mock_bet_input.assert_called_once()
    
    @patch('v2.ui.cli.input_handler.CLIInputHandler.get_bet_amount_input')
    @patch('click.prompt')
    @patch('click.echo')
    def test_get_player_action_raise(self, mock_echo, mock_prompt, mock_bet_input):
        """测试玩家选择加注."""
        mock_prompt.return_value = 3  # 选择第三个选项（加注）
        mock_bet_input.return_value = 150
        
        player = type('Player', (), {
            'seat_id': 0,
            'name': 'Test',
            'chips': 1000,
            'current_bet': 0,
            'status': SeatStatus.ACTIVE
        })()
        
        snapshot = type('GameSnapshot', (), {
            'players': [player],
            'current_bet': 50,
            'big_blind': 20,
            'last_raise_amount': 30
        })()
        
        result = CLIInputHandler.get_player_action(snapshot, 0)
        
        assert result.player_id == 0
        assert result.action_type == ActionType.RAISE
        assert result.amount == 150
        mock_bet_input.assert_called_once()
    
    @patch('click.prompt')
    @patch('click.echo')
    def test_get_player_action_invalid_choice_retry(self, mock_echo, mock_prompt):
        """测试无效选择后重试."""
        # 第一次输入无效，第二次选择弃牌
        mock_prompt.side_effect = [99, 1]  # 99是无效选择，1是弃牌
        
        player = type('Player', (), {
            'seat_id': 0,
            'name': 'Test',
            'chips': 1000,
            'current_bet': 0,
            'status': SeatStatus.ACTIVE
        })()
        
        snapshot = type('GameSnapshot', (), {
            'players': [player],
            'current_bet': 0,
            'big_blind': 20,
            'last_raise_amount': None
        })()
        
        result = CLIInputHandler.get_player_action(snapshot, 0)
        
        assert result.action_type == ActionType.FOLD
        # 应该调用了两次prompt
        assert mock_prompt.call_count == 2
    
    @patch('click.confirm')
    def test_get_continue_choice_yes(self, mock_confirm):
        """测试选择继续游戏."""
        mock_confirm.return_value = True
        
        result = CLIInputHandler.get_continue_choice()
        
        assert result is True
        mock_confirm.assert_called_once_with("是否继续下一手牌?", default=True)
    
    @patch('click.confirm')
    def test_get_continue_choice_no(self, mock_confirm):
        """测试选择退出游戏."""
        mock_confirm.return_value = False
        
        result = CLIInputHandler.get_continue_choice()
        
        assert result is False
    
    @patch('click.confirm')
    def test_get_continue_choice_abort(self, mock_confirm):
        """测试用户取消选择."""
        mock_confirm.side_effect = click.Abort()
        
        result = CLIInputHandler.get_continue_choice()
        
        assert result is False
    
    @patch('click.prompt')
    def test_get_bet_amount_input_valid(self, mock_prompt):
        """测试有效的下注金额输入."""
        mock_prompt.return_value = 100
        
        result = CLIInputHandler.get_bet_amount_input(50, 200, "下注")
        
        assert result == 100
        mock_prompt.assert_called_once()
    
    @patch('click.prompt')
    def test_get_bet_amount_input_with_range(self, mock_prompt):
        """测试带范围限制的下注金额输入."""
        mock_prompt.return_value = 75
        
        result = CLIInputHandler.get_bet_amount_input(50, 100, "加注")
        
        assert result == 75
        # 验证调用参数包含正确的范围
        args, kwargs = mock_prompt.call_args
        assert kwargs['type'].min == 50
        assert kwargs['type'].max == 100
    
    def test_get_bet_amount_bet_action(self):
        """测试下注行动的金额计算."""
        player = type('Player', (), {
            'chips': 1000,
            'current_bet': 0
        })()
        
        snapshot = type('GameSnapshot', (), {
            'big_blind': 20,
            'current_bet': 0
        })()
        
        with patch.object(CLIInputHandler, 'get_bet_amount_input', return_value=100) as mock_input:
            result = CLIInputHandler._get_bet_amount(ActionType.BET, snapshot, player)
            
            assert result == 100
            mock_input.assert_called_once_with(20, 1000, "下注")
    
    def test_get_bet_amount_raise_action(self):
        """测试加注行动的金额计算."""
        player = type('Player', (), {
            'chips': 1000,
            'current_bet': 20
        })()
        
        snapshot = type('GameSnapshot', (), {
            'big_blind': 20,
            'current_bet': 50,
            'last_raise_amount': 30
        })()
        
        with patch.object(CLIInputHandler, 'get_bet_amount_input', return_value=150) as mock_input:
            result = CLIInputHandler._get_bet_amount(ActionType.RAISE, snapshot, player)
            
            assert result == 150
            # 最小加注到80 (50 + 30)，最大到1020 (1000 + 20)
            mock_input.assert_called_once_with(80, 1020, "加注到")
    
    def test_get_bet_amount_invalid_action_type(self):
        """测试无效的行动类型."""
        player = type('Player', (), {
            'chips': 1000,
            'current_bet': 0
        })()
        
        snapshot = type('GameSnapshot', (), {
            'big_blind': 20
        })()
        
        with pytest.raises(ValueError, match="不支持的行动类型"):
            CLIInputHandler._get_bet_amount(ActionType.FOLD, snapshot, player)
    
    def test_input_validation_error(self):
        """测试输入验证错误异常."""
        error = InputValidationError("测试错误")
        assert str(error) == "测试错误"
        assert isinstance(error, Exception) 