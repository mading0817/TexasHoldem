"""
PLAN 42: 核心行动逻辑测试

测试 v3/core/rules/action_logic.py 中的 determine_permissible_actions 函数。
"""

import pytest
from v3.core.state_machine.types import GameContext, GamePhase
from v3.core.betting.betting_types import BetType
from v3.core.rules import determine_permissible_actions, CorePermissibleActionsData, ActionConstraints
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class TestDeterminePermissibleActions:
    """测试determine_permissible_actions函数"""
    
    def setup_method(self):
        """设置测试环境"""
        # 创建基础游戏上下文
        self.game_context = GameContext(
            game_id="test_game",
            current_phase=GamePhase.PRE_FLOP,
            players={
                "player1": {
                    "chips": 1000,
                    "active": True,
                    "current_bet": 0
                },
                "player2": {
                    "chips": 500,
                    "active": True,
                    "current_bet": 0
                },
                "inactive_player": {
                    "chips": 200,
                    "active": False,
                    "current_bet": 0
                }
            },
            community_cards=[],
            pot_total=0,
            current_bet=0,
            small_blind=50,
            big_blind=100,
            active_player_id="player1"
        )
    
    def test_determine_permissible_actions_anti_cheat(self):
        """反作弊检查：确保使用真实核心对象"""
        result = determine_permissible_actions(self.game_context, "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "CorePermissibleActionsData")
        CoreUsageChecker.verify_real_objects(result.constraints, "ActionConstraints")
        assert isinstance(result.available_bet_types, list)
        assert all(isinstance(bet_type, BetType) for bet_type in result.available_bet_types)
    
    def test_determine_permissible_actions_no_current_bet(self):
        """测试没有当前下注时的可用行动"""
        result = determine_permissible_actions(self.game_context, "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "CorePermissibleActionsData")
        
        # 验证可用行动：fold, check, raise, all_in
        expected_actions = {BetType.FOLD, BetType.CHECK, BetType.RAISE, BetType.ALL_IN}
        assert set(result.available_bet_types) == expected_actions
        
        # 验证约束
        assert result.constraints.min_call_amount == 0
        assert result.constraints.min_raise_amount == 100  # current_bet(0) + big_blind(100)
        assert result.constraints.max_raise_amount == 1000  # player_current_bet(0) + player_chips(1000)
        assert result.constraints.big_blind_amount == 100
        assert result.is_player_active is True
    
    def test_determine_permissible_actions_with_current_bet(self):
        """测试有当前下注时的可用行动"""
        # 设置当前下注
        self.game_context.current_bet = 200
        self.game_context.players["player1"]["current_bet"] = 0  # 玩家还未跟注
        
        result = determine_permissible_actions(self.game_context, "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "CorePermissibleActionsData")
        
        # 验证可用行动：fold, call, raise, all_in
        expected_actions = {BetType.FOLD, BetType.CALL, BetType.RAISE, BetType.ALL_IN}
        assert set(result.available_bet_types) == expected_actions
        
        # 验证约束
        assert result.constraints.min_call_amount == 200  # current_bet - player_current_bet
        assert result.constraints.min_raise_amount == 300  # current_bet(200) + big_blind(100)
        assert result.constraints.max_raise_amount == 1000  # player_current_bet(0) + player_chips(1000)
    
    def test_determine_permissible_actions_insufficient_chips_for_raise(self):
        """测试筹码不足以加注时的可用行动"""
        # 设置适中的当前下注，玩家只能跟注但不能加注
        self.game_context.current_bet = 400
        self.game_context.players["player2"]["current_bet"] = 0  # player2有500筹码
        
        result = determine_permissible_actions(self.game_context, "player2")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "CorePermissibleActionsData")
        
        # 验证可用行动：只有fold, call, all_in（没有raise因为筹码不足）
        expected_actions = {BetType.FOLD, BetType.CALL, BetType.ALL_IN}
        assert set(result.available_bet_types) == expected_actions
        
        # 验证约束
        assert result.constraints.min_call_amount == 400  # current_bet - player_current_bet
        # needed_for_min_raise = 400 + 100 = 500, player_chips = 500, 所以不能加注（需要>500）
    
    def test_determine_permissible_actions_insufficient_chips_for_call(self):
        """测试筹码不足以跟注时的可用行动"""
        # 设置超高额当前下注，玩家连跟注都不够
        self.game_context.current_bet = 1500
        self.game_context.players["player2"]["current_bet"] = 0  # player2有500筹码
        
        result = determine_permissible_actions(self.game_context, "player2")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "CorePermissibleActionsData")
        
        # 验证可用行动：只有fold, all_in（没有call因为筹码不足）
        expected_actions = {BetType.FOLD, BetType.ALL_IN}
        assert set(result.available_bet_types) == expected_actions
    
    def test_determine_permissible_actions_inactive_player(self):
        """测试非活跃玩家的可用行动"""
        result = determine_permissible_actions(self.game_context, "inactive_player")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "CorePermissibleActionsData")
        
        # 验证无可用行动
        assert result.available_bet_types == []
        assert result.is_player_active is False
        assert "非活跃状态" in result.reasoning
    
    def test_determine_permissible_actions_invalid_phase(self):
        """测试非下注阶段的可用行动"""
        self.game_context.current_phase = GamePhase.SHOWDOWN
        
        result = determine_permissible_actions(self.game_context, "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "CorePermissibleActionsData")
        
        # 验证只能弃牌（活跃玩家至少能弃牌）
        assert result.available_bet_types == [BetType.FOLD]
        assert result.is_player_active is True
        assert "不允许玩家行动" in result.reasoning
    
    def test_determine_permissible_actions_no_chips(self):
        """测试没有筹码的玩家"""
        self.game_context.players["player1"]["chips"] = 0
        
        result = determine_permissible_actions(self.game_context, "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "CorePermissibleActionsData")
        
        # 验证只能弃牌或过牌（如果没有当前下注）
        expected_actions = {BetType.FOLD, BetType.CHECK}
        assert set(result.available_bet_types) == expected_actions
        assert result.constraints.is_all_in_available is False
    
    def test_determine_permissible_actions_player_not_found(self):
        """测试玩家不存在的情况"""
        with pytest.raises(ValueError, match="玩家 nonexistent 不在游戏中"):
            determine_permissible_actions(self.game_context, "nonexistent")
    
    def test_determine_permissible_actions_empty_player_id(self):
        """测试空玩家ID的情况"""
        with pytest.raises(ValueError, match="player_id不能为空"):
            determine_permissible_actions(self.game_context, "")
    
    def test_core_permissible_actions_data_methods(self):
        """测试CorePermissibleActionsData的便利方法"""
        result = determine_permissible_actions(self.game_context, "player1")
        
        # 反作弊验证
        CoreUsageChecker.verify_real_objects(result, "CorePermissibleActionsData")
        
        # 测试便利方法
        assert result.can_check() is True
        assert result.can_call() is False  # 没有当前下注
        assert result.can_raise() is True
        assert result.can_all_in() is True
        
        # 测试字符串转换
        action_strings = result.get_action_types_as_strings()
        expected_strings = ['fold', 'check', 'raise', 'all_in']
        assert set(action_strings) == set(expected_strings)
    
    def test_action_constraints_validation(self):
        """测试ActionConstraints的验证逻辑"""
        # 测试正常约束
        constraints = ActionConstraints(
            min_call_amount=100,
            min_raise_amount=200,
            max_raise_amount=1000,
            big_blind_amount=100
        )
        CoreUsageChecker.verify_real_objects(constraints, "ActionConstraints")
        
        # 测试无效约束
        with pytest.raises(ValueError, match="min_call_amount不能为负数"):
            ActionConstraints(min_call_amount=-1, big_blind_amount=100)
        
        with pytest.raises(ValueError, match="big_blind_amount必须大于0"):
            ActionConstraints(big_blind_amount=0)
    
    def test_core_permissible_actions_data_validation(self):
        """测试CorePermissibleActionsData的验证逻辑"""
        constraints = ActionConstraints(big_blind_amount=100)
        
        # 测试正常数据
        data = CorePermissibleActionsData(
            player_id="test_player",
            available_bet_types=[BetType.FOLD, BetType.CHECK],
            constraints=constraints,
            player_chips=1000,
            is_player_active=True
        )
        CoreUsageChecker.verify_real_objects(data, "CorePermissibleActionsData")
        
        # 测试无效数据
        with pytest.raises(ValueError, match="player_id不能为空"):
            CorePermissibleActionsData(
                player_id="",
                available_bet_types=[BetType.FOLD],
                constraints=constraints,
                player_chips=1000,
                is_player_active=True
            )
        
        with pytest.raises(ValueError, match="非活跃玩家不应有可用行动"):
            CorePermissibleActionsData(
                player_id="test_player",
                available_bet_types=[BetType.FOLD],
                constraints=constraints,
                player_chips=1000,
                is_player_active=False
            )
        
        with pytest.raises(ValueError, match="活跃玩家至少应该能够弃牌"):
            CorePermissibleActionsData(
                player_id="test_player",
                available_bet_types=[BetType.CHECK],  # 没有FOLD
                constraints=constraints,
                player_chips=1000,
                is_player_active=True
            )
        
        with pytest.raises(ValueError, match="CHECK和CALL不应同时存在"):
            CorePermissibleActionsData(
                player_id="test_player",
                available_bet_types=[BetType.FOLD, BetType.CHECK, BetType.CALL],
                constraints=constraints,
                player_chips=1000,
                is_player_active=True
            ) 