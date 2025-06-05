"""
测试筹码守恒修复

验证修复后的筹码守恒检查是否正确工作。
"""

import pytest
from v3.core.state_machine.types import GameContext, GamePhase
from v3.core.invariant.chip_conservation_validator import ChipConservationValidator
from v3.core.state_machine.phase_handlers import FlopHandler, TurnHandler, RiverHandler
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker

__all__ = ['TestChipConservationFix']


class TestChipConservationFix:
    """测试筹码守恒修复"""
    
    def test_validator_detects_pot_inconsistency(self):
        """测试验证器能够检测到奖池不一致"""
        # 创建测试上下文
        ctx = GameContext(
            game_id="test_game",
            current_phase=GamePhase.FLOP,
            players={
                "player1": {
                    "chips": 1000,
                    "total_bet_this_hand": 100,
                    "current_bet": 0
                },
                "player2": {
                    "chips": 900,
                    "total_bet_this_hand": 200,
                    "current_bet": 0
                }
            },
            community_cards=[],
            pot_total=250,  # 故意设置错误的奖池金额（应该是300）
            current_bet=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ctx, "GameContext")
        
        # 验证器应该检测到不一致并抛出异常
        with pytest.raises(ValueError, match="筹码守恒违规"):
            ChipConservationValidator.validate_pot_consistency(ctx, "测试操作")
    
    def test_validator_passes_consistent_pot(self):
        """测试验证器在奖池一致时通过"""
        # 创建测试上下文
        ctx = GameContext(
            game_id="test_game",
            current_phase=GamePhase.FLOP,
            players={
                "player1": {
                    "chips": 1000,
                    "total_bet_this_hand": 100,
                    "current_bet": 0
                },
                "player2": {
                    "chips": 900,
                    "total_bet_this_hand": 200,
                    "current_bet": 0
                }
            },
            community_cards=[],
            pot_total=300,  # 正确的奖池金额
            current_bet=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ctx, "GameContext")
        
        # 验证器应该通过，不抛出异常
        ChipConservationValidator.validate_pot_consistency(ctx, "测试操作")
    
    def test_flop_handler_validates_pot_consistency(self):
        """测试FlopHandler在进入时验证奖池一致性"""
        # 创建有问题的上下文
        ctx = GameContext(
            game_id="test_game",
            current_phase=GamePhase.PRE_FLOP,
            players={
                "player1": {
                    "chips": 1000,
                    "total_bet_this_hand": 100,
                    "current_bet": 0
                },
                "player2": {
                    "chips": 900,
                    "total_bet_this_hand": 200,
                    "current_bet": 0
                }
            },
            community_cards=[],
            pot_total=250,  # 错误的奖池金额
            current_bet=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ctx, "GameContext")
        
        handler = FlopHandler()
        CoreUsageChecker.verify_real_objects(handler, "FlopHandler")
        
        # 进入FLOP阶段应该抛出异常
        with pytest.raises(ValueError, match="筹码守恒违规"):
            handler.on_enter(ctx)
    
    def test_turn_handler_validates_pot_consistency(self):
        """测试TurnHandler在进入时验证奖池一致性"""
        # 创建有问题的上下文
        ctx = GameContext(
            game_id="test_game",
            current_phase=GamePhase.FLOP,
            players={
                "player1": {
                    "chips": 1000,
                    "total_bet_this_hand": 150,
                    "current_bet": 0
                },
                "player2": {
                    "chips": 850,
                    "total_bet_this_hand": 250,
                    "current_bet": 0
                }
            },
            community_cards=[
                # 模拟已有的flop牌
            ],
            pot_total=350,  # 错误的奖池金额（应该是400）
            current_bet=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ctx, "GameContext")
        
        handler = TurnHandler()
        CoreUsageChecker.verify_real_objects(handler, "TurnHandler")
        
        # 进入TURN阶段应该抛出异常
        with pytest.raises(ValueError, match="筹码守恒违规"):
            handler.on_enter(ctx)
    
    def test_river_handler_validates_pot_consistency(self):
        """测试RiverHandler在进入时验证奖池一致性"""
        # 创建有问题的上下文
        ctx = GameContext(
            game_id="test_game",
            current_phase=GamePhase.TURN,
            players={
                "player1": {
                    "chips": 900,
                    "total_bet_this_hand": 200,
                    "current_bet": 0
                },
                "player2": {
                    "chips": 700,
                    "total_bet_this_hand": 400,
                    "current_bet": 0
                }
            },
            community_cards=[
                # 模拟已有的turn牌
            ],
            pot_total=500,  # 错误的奖池金额（应该是600）
            current_bet=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ctx, "GameContext")
        
        handler = RiverHandler()
        CoreUsageChecker.verify_real_objects(handler, "RiverHandler")
        
        # 进入RIVER阶段应该抛出异常
        with pytest.raises(ValueError, match="筹码守恒违规"):
            handler.on_enter(ctx)
    
    def test_validator_skips_check_in_showdown_phase(self):
        """测试验证器在SHOWDOWN阶段跳过检查"""
        # 创建SHOWDOWN阶段的上下文
        ctx = GameContext(
            game_id="test_game",
            current_phase=GamePhase.SHOWDOWN,
            players={
                "player1": {
                    "chips": 1500,  # 已经获得奖金
                    "total_bet_this_hand": 200,
                    "current_bet": 0
                },
                "player2": {
                    "chips": 800,
                    "total_bet_this_hand": 400,
                    "current_bet": 0
                }
            },
            community_cards=[],
            pot_total=0,  # 奖池已经被分配
            current_bet=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ctx, "GameContext")
        
        # 在SHOWDOWN阶段，验证器应该跳过检查，不抛出异常
        ChipConservationValidator.validate_pot_consistency(ctx, "SHOWDOWN测试")
    
    def test_validator_detects_negative_chips(self):
        """测试验证器能够检测到负数筹码"""
        ctx = GameContext(
            game_id="test_game",
            current_phase=GamePhase.FLOP,
            players={
                "player1": {
                    "chips": -100,  # 负数筹码
                    "total_bet_this_hand": 100,
                    "current_bet": 0
                }
            },
            community_cards=[],
            pot_total=100,
            current_bet=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ctx, "GameContext")
        
        # 验证器应该检测到负数筹码并抛出异常
        with pytest.raises(ValueError, match="筹码为负数"):
            ChipConservationValidator.validate_player_bet_consistency(ctx, "player1", "负数筹码测试")
    
    def test_validator_detects_insufficient_chips_for_bet(self):
        """测试验证器能够检测到筹码不足的下注"""
        ctx = GameContext(
            game_id="test_game",
            current_phase=GamePhase.FLOP,
            players={
                "player1": {
                    "chips": 50,  # 筹码不足
                    "total_bet_this_hand": 100,
                    "current_bet": 0
                }
            },
            community_cards=[],
            pot_total=100,
            current_bet=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ctx, "GameContext")
        
        # 验证器应该检测到筹码不足并抛出异常
        with pytest.raises(ValueError, match="筹码不足"):
            ChipConservationValidator.validate_betting_action(
                ctx, "player1", "raise", 100, "筹码不足测试"
            )
    
    def test_total_chip_conservation_validation(self):
        """测试总筹码守恒验证"""
        ctx = GameContext(
            game_id="test_game",
            current_phase=GamePhase.FLOP,
            players={
                "player1": {
                    "chips": 900,
                    "total_bet_this_hand": 100,
                    "current_bet": 0
                },
                "player2": {
                    "chips": 800,
                    "total_bet_this_hand": 200,
                    "current_bet": 0
                }
            },
            community_cards=[],
            pot_total=300,
            current_bet=0
        )
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(ctx, "GameContext")
        
        initial_total = 2000  # 初始总筹码
        
        # 当前总筹码：900 + 800 + 300 = 2000，应该通过
        ChipConservationValidator.validate_total_chip_conservation(
            ctx, initial_total, "总筹码守恒测试"
        )
        
        # 测试不守恒的情况
        wrong_initial = 2500
        with pytest.raises(ValueError, match="总筹码不守恒"):
            ChipConservationValidator.validate_total_chip_conservation(
                ctx, wrong_initial, "总筹码不守恒测试"
            ) 