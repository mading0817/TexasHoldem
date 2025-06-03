"""
用户操作模拟器

提供丰富的用户操作模拟功能，支持多种操作模式和策略。
"""

import time
import random
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
import sys

# 添加v2目录到Python路径
v2_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(v2_path))

from .end_to_end_loop import UserOperation, OperationType, StateChangeTracker
from v2.core.enums import ActionType, Phase
from v2.controller.poker_controller import PokerController


class SimulationStrategy(Enum):
    """模拟策略类型"""
    CONSERVATIVE = "conservative"  # 保守策略：主要check/call
    AGGRESSIVE = "aggressive"      # 激进策略：经常raise/bet
    RANDOM = "random"             # 随机策略
    TIGHT = "tight"               # 紧手策略：经常fold
    LOOSE = "loose"               # 松手策略：很少fold


@dataclass
class PlayerProfile:
    """玩家档案"""
    player_id: str
    strategy: SimulationStrategy
    aggression_level: float = 0.5  # 0.0-1.0
    fold_probability: float = 0.2   # 0.0-1.0
    raise_probability: float = 0.3  # 0.0-1.0
    bluff_probability: float = 0.1  # 0.0-1.0


class AdvancedUserOperationSimulator:
    """高级用户操作模拟器"""
    
    def __init__(self, controller: PokerController, tracker: StateChangeTracker):
        self.controller = controller
        self.tracker = tracker
        self.player_profiles: Dict[str, PlayerProfile] = {}
        self.operation_history: List[UserOperation] = []
        self.logger = logging.getLogger(__name__)
        
        # 设置默认玩家档案
        self._setup_default_profiles()
    
    def _setup_default_profiles(self):
        """设置默认玩家档案"""
        default_profiles = [
            PlayerProfile("Player1", SimulationStrategy.CONSERVATIVE, 0.3, 0.3, 0.2, 0.05),
            PlayerProfile("Player2", SimulationStrategy.AGGRESSIVE, 0.7, 0.1, 0.5, 0.2),
            PlayerProfile("AI1", SimulationStrategy.TIGHT, 0.4, 0.4, 0.2, 0.1),
            PlayerProfile("AI2", SimulationStrategy.LOOSE, 0.6, 0.1, 0.4, 0.15),
        ]
        
        for profile in default_profiles:
            self.player_profiles[profile.player_id] = profile
    
    def set_player_profile(self, player_id: str, profile: PlayerProfile):
        """设置玩家档案"""
        self.player_profiles[player_id] = profile
    
    def simulate_intelligent_action(self, player_id: str) -> Optional[UserOperation]:
        """模拟智能行动"""
        if player_id not in self.player_profiles:
            return self._simulate_random_action(player_id)
        
        profile = self.player_profiles[player_id]
        game_state = self.controller.game_state
        
        # 获取可用行动
        available_actions = self._get_available_actions(player_id)
        if not available_actions:
            return None
        
        # 根据策略选择行动
        if profile.strategy == SimulationStrategy.CONSERVATIVE:
            return self._simulate_conservative_action(player_id, available_actions, profile)
        elif profile.strategy == SimulationStrategy.AGGRESSIVE:
            return self._simulate_aggressive_action(player_id, available_actions, profile)
        elif profile.strategy == SimulationStrategy.TIGHT:
            return self._simulate_tight_action(player_id, available_actions, profile)
        elif profile.strategy == SimulationStrategy.LOOSE:
            return self._simulate_loose_action(player_id, available_actions, profile)
        else:
            return self._simulate_random_action(player_id)
    
    def _get_available_actions(self, player_id: str) -> List[OperationType]:
        """获取可用行动"""
        game_state = self.controller.game_state
        available_actions = []
        
        # 基本行动
        available_actions.append(OperationType.FOLD)
        
        # 检查是否可以check
        if game_state.current_bet == 0:
            available_actions.append(OperationType.CHECK)
        else:
            available_actions.append(OperationType.CALL)
        
        # 检查是否可以下注或加注
        player = next((p for p in game_state.players if p.id == player_id), None)
        if player and player.chips > 0:
            if game_state.current_bet == 0:
                available_actions.append(OperationType.BET)
            else:
                available_actions.append(OperationType.RAISE)
            
            available_actions.append(OperationType.ALL_IN)
        
        return available_actions
    
    def _simulate_conservative_action(self, player_id: str, available_actions: List[OperationType], 
                                    profile: PlayerProfile) -> UserOperation:
        """模拟保守行动"""
        # 保守策略：优先check/call，很少raise
        if OperationType.CHECK in available_actions and random.random() > 0.3:
            return UserOperation(OperationType.CHECK, player_id)
        elif OperationType.CALL in available_actions and random.random() > profile.fold_probability:
            return UserOperation(OperationType.CALL, player_id)
        elif random.random() < profile.raise_probability * 0.5:  # 降低加注概率
            if OperationType.RAISE in available_actions:
                amount = self._calculate_raise_amount(player_id, conservative=True)
                return UserOperation(OperationType.RAISE, player_id, amount)
            elif OperationType.BET in available_actions:
                amount = self._calculate_bet_amount(player_id, conservative=True)
                return UserOperation(OperationType.BET, player_id, amount)
        
        return UserOperation(OperationType.FOLD, player_id)
    
    def _simulate_aggressive_action(self, player_id: str, available_actions: List[OperationType], 
                                  profile: PlayerProfile) -> UserOperation:
        """模拟激进行动"""
        # 激进策略：经常raise/bet，很少fold
        if random.random() < profile.raise_probability:
            if OperationType.RAISE in available_actions:
                amount = self._calculate_raise_amount(player_id, aggressive=True)
                return UserOperation(OperationType.RAISE, player_id, amount)
            elif OperationType.BET in available_actions:
                amount = self._calculate_bet_amount(player_id, aggressive=True)
                return UserOperation(OperationType.BET, player_id, amount)
        
        if OperationType.CALL in available_actions and random.random() > profile.fold_probability * 0.5:
            return UserOperation(OperationType.CALL, player_id)
        elif OperationType.CHECK in available_actions:
            return UserOperation(OperationType.CHECK, player_id)
        
        return UserOperation(OperationType.FOLD, player_id)
    
    def _simulate_tight_action(self, player_id: str, available_actions: List[OperationType], 
                             profile: PlayerProfile) -> UserOperation:
        """模拟紧手行动"""
        # 紧手策略：经常fold，很少冒险
        if random.random() < profile.fold_probability * 1.5:
            return UserOperation(OperationType.FOLD, player_id)
        
        if OperationType.CHECK in available_actions:
            return UserOperation(OperationType.CHECK, player_id)
        elif OperationType.CALL in available_actions and random.random() > 0.6:
            return UserOperation(OperationType.CALL, player_id)
        
        return UserOperation(OperationType.FOLD, player_id)
    
    def _simulate_loose_action(self, player_id: str, available_actions: List[OperationType], 
                             profile: PlayerProfile) -> UserOperation:
        """模拟松手行动"""
        # 松手策略：很少fold，经常参与
        if OperationType.CALL in available_actions and random.random() > 0.1:
            return UserOperation(OperationType.CALL, player_id)
        elif OperationType.CHECK in available_actions:
            return UserOperation(OperationType.CHECK, player_id)
        elif random.random() < profile.raise_probability * 0.8:
            if OperationType.RAISE in available_actions:
                amount = self._calculate_raise_amount(player_id)
                return UserOperation(OperationType.RAISE, player_id, amount)
            elif OperationType.BET in available_actions:
                amount = self._calculate_bet_amount(player_id)
                return UserOperation(OperationType.BET, player_id, amount)
        
        return UserOperation(OperationType.FOLD, player_id)
    
    def _simulate_random_action(self, player_id: str) -> UserOperation:
        """模拟随机行动"""
        available_actions = self._get_available_actions(player_id)
        if not available_actions:
            return UserOperation(OperationType.FOLD, player_id)
        
        action_type = random.choice(available_actions)
        
        if action_type in [OperationType.RAISE, OperationType.BET]:
            amount = self._calculate_raise_amount(player_id) if action_type == OperationType.RAISE else self._calculate_bet_amount(player_id)
            return UserOperation(action_type, player_id, amount)
        
        return UserOperation(action_type, player_id)
    
    def _calculate_raise_amount(self, player_id: str, conservative: bool = False, aggressive: bool = False) -> int:
        """计算加注金额"""
        game_state = self.controller.game_state
        player = next((p for p in game_state.players if p.id == player_id), None)
        
        if not player:
            return 0
        
        min_raise = max(game_state.current_bet * 2, game_state.big_blind * 2)
        max_raise = min(player.chips, game_state.pot.total_amount)
        
        if conservative:
            # 保守：小额加注
            amount = min(min_raise, max_raise)
        elif aggressive:
            # 激进：大额加注
            amount = min(min_raise * 3, max_raise)
        else:
            # 中等加注
            amount = min(min_raise * 2, max_raise)
        
        return max(min_raise, amount)
    
    def _calculate_bet_amount(self, player_id: str, conservative: bool = False, aggressive: bool = False) -> int:
        """计算下注金额"""
        game_state = self.controller.game_state
        player = next((p for p in game_state.players if p.id == player_id), None)
        
        if not player:
            return 0
        
        pot_size = game_state.pot.total_amount
        
        if conservative:
            # 保守：小额下注
            amount = min(pot_size // 4, player.chips)
        elif aggressive:
            # 激进：大额下注
            amount = min(pot_size, player.chips)
        else:
            # 中等下注
            amount = min(pot_size // 2, player.chips)
        
        return max(game_state.big_blind, amount)
    
    def simulate_game_sequence(self, num_hands: int = 5) -> List[Dict[str, Any]]:
        """模拟游戏序列"""
        results = []
        
        for hand_num in range(num_hands):
            hand_result = self._simulate_single_hand(hand_num + 1)
            results.append(hand_result)
            
            # 如果游戏结束，重新开始
            if self.controller.game_state.phase == Phase.SHOWDOWN:
                self.controller.start_new_hand()
        
        return results
    
    def _simulate_single_hand(self, hand_number: int) -> Dict[str, Any]:
        """模拟单手牌"""
        start_time = time.time()
        actions_taken = []
        
        try:
            # 开始新手牌
            self.controller.start_new_hand()
            
            max_actions = 100  # 防止无限循环
            action_count = 0
            
            while (self.controller.game_state.phase != Phase.SHOWDOWN and 
                   action_count < max_actions):
                
                current_player = self.controller.game_state.current_player_id
                if not current_player:
                    break
                
                # 模拟玩家行动
                operation = self.simulate_intelligent_action(current_player)
                if operation:
                    success = self._execute_operation(operation)
                    actions_taken.append({
                        "player": current_player,
                        "action": operation.operation_type.value,
                        "amount": operation.amount,
                        "success": success
                    })
                    
                    if success:
                        action_count += 1
                        self.operation_history.append(operation)
                else:
                    break
            
            return {
                "hand_number": hand_number,
                "success": True,
                "duration": time.time() - start_time,
                "actions_taken": len(actions_taken),
                "final_phase": self.controller.game_state.phase.value,
                "actions_detail": actions_taken
            }
            
        except Exception as e:
            return {
                "hand_number": hand_number,
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time,
                "actions_taken": len(actions_taken)
            }
    
    def _execute_operation(self, operation: UserOperation) -> bool:
        """执行操作"""
        try:
            if operation.operation_type == OperationType.FOLD:
                return self.controller.handle_player_action(operation.player_id, ActionType.FOLD)
            elif operation.operation_type == OperationType.CALL:
                return self.controller.handle_player_action(operation.player_id, ActionType.CALL)
            elif operation.operation_type == OperationType.CHECK:
                return self.controller.handle_player_action(operation.player_id, ActionType.CHECK)
            elif operation.operation_type == OperationType.RAISE:
                return self.controller.handle_player_action(operation.player_id, ActionType.RAISE, operation.amount)
            elif operation.operation_type == OperationType.BET:
                return self.controller.handle_player_action(operation.player_id, ActionType.BET, operation.amount)
            elif operation.operation_type == OperationType.ALL_IN:
                return self.controller.handle_player_action(operation.player_id, ActionType.ALL_IN)
            else:
                return False
        except Exception as e:
            self.logger.error(f"Failed to execute operation {operation.operation_type.value} for {operation.player_id}: {e}")
            return False
    
    def get_simulation_statistics(self) -> Dict[str, Any]:
        """获取模拟统计信息"""
        if not self.operation_history:
            return {}
        
        # 按玩家统计
        player_stats = {}
        for operation in self.operation_history:
            player_id = operation.player_id
            if player_id not in player_stats:
                player_stats[player_id] = {
                    "total_actions": 0,
                    "action_types": {},
                    "total_amount_bet": 0
                }
            
            player_stats[player_id]["total_actions"] += 1
            action_type = operation.operation_type.value
            player_stats[player_id]["action_types"][action_type] = player_stats[player_id]["action_types"].get(action_type, 0) + 1
            
            if operation.amount:
                player_stats[player_id]["total_amount_bet"] += operation.amount
        
        # 总体统计
        total_operations = len(self.operation_history)
        action_type_counts = {}
        for operation in self.operation_history:
            action_type = operation.operation_type.value
            action_type_counts[action_type] = action_type_counts.get(action_type, 0) + 1
        
        return {
            "total_operations": total_operations,
            "action_type_distribution": action_type_counts,
            "player_statistics": player_stats,
            "average_actions_per_player": total_operations / len(player_stats) if player_stats else 0
        }


class ScenarioTester:
    """场景测试器"""
    
    def __init__(self, controller: PokerController, tracker: StateChangeTracker):
        self.controller = controller
        self.tracker = tracker
        self.simulator = AdvancedUserOperationSimulator(controller, tracker)
    
    def test_all_in_scenario(self) -> Dict[str, Any]:
        """测试全押场景"""
        start_time = time.time()
        
        try:
            # 设置激进档案
            aggressive_profile = PlayerProfile("Player1", SimulationStrategy.AGGRESSIVE, 0.9, 0.05, 0.8, 0.3)
            self.simulator.set_player_profile("Player1", aggressive_profile)
            
            # 开始游戏
            self.controller.start_new_hand()
            
            # 模拟全押场景
            current_player = self.controller.game_state.current_player_id
            if current_player:
                operation = UserOperation(OperationType.ALL_IN, current_player)
                success = self.simulator._execute_operation(operation)
                
                return {
                    "scenario": "all_in",
                    "success": success,
                    "duration": time.time() - start_time,
                    "final_state": {
                        "phase": self.controller.game_state.phase.value,
                        "pot_size": self.controller.game_state.pot.total_amount
                    }
                }
        
        except Exception as e:
            return {
                "scenario": "all_in",
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    def test_fold_cascade_scenario(self) -> Dict[str, Any]:
        """测试连续弃牌场景"""
        start_time = time.time()
        
        try:
            # 设置紧手档案
            tight_profile = PlayerProfile("Player1", SimulationStrategy.TIGHT, 0.2, 0.8, 0.1, 0.05)
            
            for player_id in ["Player1", "Player2", "AI1"]:
                self.simulator.set_player_profile(player_id, tight_profile)
            
            # 开始游戏
            self.controller.start_new_hand()
            
            fold_count = 0
            max_folds = 3
            
            while fold_count < max_folds:
                current_player = self.controller.game_state.current_player_id
                if not current_player:
                    break
                
                operation = UserOperation(OperationType.FOLD, current_player)
                success = self.simulator._execute_operation(operation)
                
                if success:
                    fold_count += 1
                else:
                    break
            
            return {
                "scenario": "fold_cascade",
                "success": True,
                "duration": time.time() - start_time,
                "folds_executed": fold_count,
                "final_state": {
                    "phase": self.controller.game_state.phase.value,
                    "active_players": len([p for p in self.controller.game_state.players if not p.folded])
                }
            }
        
        except Exception as e:
            return {
                "scenario": "fold_cascade",
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    def test_raise_war_scenario(self) -> Dict[str, Any]:
        """测试加注战场景"""
        start_time = time.time()
        
        try:
            # 设置激进档案
            aggressive_profile = PlayerProfile("Player1", SimulationStrategy.AGGRESSIVE, 0.9, 0.05, 0.9, 0.2)
            
            for player_id in ["Player1", "Player2"]:
                self.simulator.set_player_profile(player_id, aggressive_profile)
            
            # 开始游戏
            self.controller.start_new_hand()
            
            raise_count = 0
            max_raises = 5
            
            while raise_count < max_raises:
                current_player = self.controller.game_state.current_player_id
                if not current_player:
                    break
                
                # 尝试加注
                if current_player in ["Player1", "Player2"]:
                    amount = self.simulator._calculate_raise_amount(current_player, aggressive=True)
                    operation = UserOperation(OperationType.RAISE, current_player, amount)
                else:
                    operation = UserOperation(OperationType.CALL, current_player)
                
                success = self.simulator._execute_operation(operation)
                
                if success and operation.operation_type == OperationType.RAISE:
                    raise_count += 1
                elif not success:
                    break
            
            return {
                "scenario": "raise_war",
                "success": True,
                "duration": time.time() - start_time,
                "raises_executed": raise_count,
                "final_state": {
                    "phase": self.controller.game_state.phase.value,
                    "pot_size": self.controller.game_state.pot.total_amount,
                    "current_bet": self.controller.game_state.current_bet
                }
            }
        
        except Exception as e:
            return {
                "scenario": "raise_war",
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            } 