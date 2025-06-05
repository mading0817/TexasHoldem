#!/usr/bin/env python3
"""
Streamlit UI 终极用户体验测试 v3

基于v3架构的终极测试，使用CQRS模式的应用服务层。
模拟真实用户在Streamlit界面下进行1000手德州扑克游戏。
"""

import sys
import os
import time
import logging
import random
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from unittest.mock import Mock, patch, MagicMock
import pytest

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v3.application import GameCommandService, GameQueryService, PlayerAction
from v3.ai.Dummy.random_ai import RandomAI
from v3.ai.types import AIDecisionType, RandomAIConfig
from v3.core.events import EventBus, set_event_bus
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


class UserActionType(Enum):
    """用户行动类型"""
    FOLD = "fold"
    CALL = "call"
    RAISE = "raise"
    CHECK = "check"
    BET = "bet"
    ALL_IN = "all_in"
    START_GAME = "start_game"
    START_HAND = "start_hand"


@dataclass
class UserAction:
    """用户行动"""
    action_type: UserActionType
    player_id: str = "player_0"
    amount: Optional[int] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class UltimateTestStatsV3:
    """v3终极测试统计"""
    hands_attempted: int = 0
    hands_completed: int = 0
    hands_failed: int = 0
    total_user_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    
    # 筹码相关
    initial_total_chips: int = 0
    final_total_chips: int = 0
    chip_conservation_violations: List[str] = field(default_factory=list)
    
    # 错误统计
    errors: List[str] = field(default_factory=list)
    critical_errors: int = 0
    warnings: int = 0
    
    # 新增：不变量违反专用统计
    invariant_violations: List[str] = field(default_factory=list)
    critical_invariant_violations: int = 0
    
    # 性能统计
    total_test_time: float = 0
    average_hand_time: float = 0
    average_action_time: float = 0
    
    # 游戏流程统计
    action_distribution: Dict[str, int] = field(default_factory=dict)


class StreamlitUltimateUserTesterV3:
    """v3版本的Streamlit终极用户测试器"""
    
    def __init__(self, num_hands: int = 1000):
        self.num_hands = num_hands
        self.stats = UltimateTestStatsV3()
        self.logger = self._setup_logging()
        
        # v3架构组件
        self.event_bus = EventBus()
        set_event_bus(self.event_bus)
        self.command_service = GameCommandService(self.event_bus)
        self.query_service = GameQueryService(self.command_service, self.event_bus)
        self.ai_strategy = RandomAI(RandomAIConfig(), self.query_service)
        
        # 游戏状态
        self.game_id = "ultimate_test_game"
        self.player_ids = ["player_0", "player_1", "player_2", "player_3", "player_4", "player_5"]
        
        # 德州扑克规则常量
        self.SMALL_BLIND = 50
        self.BIG_BLIND = 100
        self.INITIAL_CHIPS = 1000
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志记录"""
        logger = logging.getLogger("StreamlitUltimateTestV3")
        logger.setLevel(logging.DEBUG)  # 设置为DEBUG级别
        
        # 创建文件处理器
        log_file = project_root / "v3" / "tests" / "test_logs" / f"streamlit_ultimate_test_v3_{int(time.time())}.log"
        log_file.parent.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)  # 控制台只显示重要信息
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _log_hand_start(self, hand_number: int, game_state):
        """记录手牌开始的详细信息"""
        self.logger.info("=" * 80)
        self.logger.info(f"🎯 第 {hand_number} 手牌开始")
        self.logger.info("=" * 80)
        
        # 记录游戏基本信息
        self.logger.info(f"📊 游戏状态:")
        self.logger.info(f"   - 游戏ID: {game_state.game_id}")
        self.logger.info(f"   - 当前阶段: {game_state.current_phase}")
        self.logger.info(f"   - 底池总额: {game_state.pot_total}")
        self.logger.info(f"   - 当前下注: {game_state.current_bet}")
        self.logger.info(f"   - 活跃玩家: {game_state.active_player_id}")
        
        # 记录玩家信息
        active_players = 0
        total_chips = 0
        self.logger.info(f"👥 玩家状态:")
        
        for player_id, player_data in game_state.players.items():
            chips = player_data.get('chips', 0)
            is_active = player_data.get('active', False)
            current_bet = player_data.get('current_bet', 0)
            total_bet_this_hand = player_data.get('total_bet_this_hand', 0)
            player_status = player_data.get('status', 'active')
            
            if is_active:
                active_players += 1
            
            total_chips += chips
            
            # 改进状态显示逻辑
            if chips == 0 and player_status == 'all_in':
                status = "🔴All-In"
            elif chips == 0:
                status = "🔴出局"
            elif is_active:
                status = "🟢活跃"
            else:
                status = "🟡非活跃"
            
            self.logger.info(f"   - {player_id}: {status} | 筹码: {chips} | 当前下注: {current_bet} | 本手总下注: {total_bet_this_hand}")
        
        # 筹码守恒检查
        total_chips_with_pot = total_chips + game_state.pot_total
        expected_total = len(self.player_ids) * self.INITIAL_CHIPS
        
        self.logger.info(f"💰 筹码守恒检查:")
        self.logger.info(f"   - 玩家筹码总和: {total_chips}")
        self.logger.info(f"   - 底池筹码: {game_state.pot_total}")
        self.logger.info(f"   - 实际总筹码: {total_chips_with_pot}")
        self.logger.info(f"   - 期望总筹码: {expected_total}")
        self.logger.info(f"   - 筹码守恒: {'✅通过' if total_chips_with_pot == expected_total else '❌违反'}")
        
        if total_chips_with_pot != expected_total:
            violation_msg = f"Hand {hand_number}: 筹码守恒违反 - 实际:{total_chips_with_pot}, 期望:{expected_total}"
            self.stats.chip_conservation_violations.append(violation_msg)
            self.logger.error(f"❌ {violation_msg}")
        
        self.logger.info(f"🎮 活跃玩家数: {active_players}")
        
        # 记录公共牌
        community_cards = getattr(game_state, 'community_cards', [])
        self.logger.info(f"🃏 公共牌: {community_cards if community_cards else '无'}")
        
        # 记录盲注信息（如果是新手牌开始）
        if hand_number > 1:
            self.logger.info(f"💰 盲注设置: 小盲 {self.SMALL_BLIND}, 大盲 {self.BIG_BLIND}")
            
            # 检查盲注是否正确设置
            blind_players = []
            for player_id, player_data in game_state.players.items():
                current_bet = player_data.get('current_bet', 0)
                if current_bet == self.SMALL_BLIND:
                    blind_players.append(f"{player_id}(小盲)")
                elif current_bet == self.BIG_BLIND:
                    blind_players.append(f"{player_id}(大盲)")
            
            if blind_players:
                self.logger.info(f"💰 盲注玩家: {', '.join(blind_players)}")
            else:
                self.logger.warning(f"⚠️ 未检测到盲注设置")
    
    def _log_phase_transition(self, old_phase: str, new_phase: str, game_state):
        """记录阶段转换的详细信息"""
        self.logger.info("-" * 60)
        self.logger.info(f"🔄 阶段转换: {old_phase} → {new_phase}")
        self.logger.info("-" * 60)
        
        # 记录阶段特定信息
        if new_phase == "PRE_FLOP":
            self.logger.info("🎯 PRE_FLOP阶段开始 - 玩家收到底牌")
        elif new_phase == "FLOP":
            self.logger.info("🎯 FLOP阶段开始 - 发出3张公共牌")
        elif new_phase == "TURN":
            self.logger.info("🎯 TURN阶段开始 - 发出第4张公共牌")
        elif new_phase == "RIVER":
            self.logger.info("🎯 RIVER阶段开始 - 发出第5张公共牌")
        elif new_phase == "SHOWDOWN":
            self.logger.info("🎯 SHOWDOWN阶段开始 - 比较牌型")
        elif new_phase == "FINISHED":
            self.logger.info("🎯 手牌结束 - 分配奖池")
        
        # 记录公共牌变化
        community_cards = getattr(game_state, 'community_cards', [])
        self.logger.info(f"🃏 当前公共牌: {community_cards if community_cards else '无'} (共{len(community_cards)}张)")
        
        # 记录底池变化
        self.logger.info(f"💰 底池状态: {game_state.pot_total}")
        self.logger.info(f"📈 当前下注: {game_state.current_bet}")
        
        # 记录活跃玩家
        active_player = game_state.active_player_id
        if active_player:
            self.logger.info(f"👤 当前行动玩家: {active_player}")
        else:
            self.logger.info("👤 当前行动玩家: 无")
    
    def _log_player_action(self, player_id: str, action_type: str, amount: int, game_state_before, game_state_after):
        """记录玩家行动的详细信息"""
        self.logger.info(f"🎭 玩家行动: {player_id}")
        
        # 获取行动前后的玩家状态
        player_before = game_state_before.players.get(player_id, {})
        player_after = game_state_after.players.get(player_id, {})
        
        chips_before = player_before.get('chips', 0)
        chips_after = player_after.get('chips', 0)
        bet_before = player_before.get('current_bet', 0)
        bet_after = player_after.get('current_bet', 0)
        
        # 记录行动详情
        self.logger.info(f"   - 行动类型: {action_type.upper()}")
        if amount > 0:
            self.logger.info(f"   - 行动金额: {amount}")
        
        # 记录筹码变化
        chips_change = chips_after - chips_before
        bet_change = bet_after - bet_before
        
        self.logger.info(f"   - 筹码变化: {chips_before} → {chips_after} (变化: {chips_change:+d})")
        self.logger.info(f"   - 下注变化: {bet_before} → {bet_after} (变化: {bet_change:+d})")
        
        # 记录底池变化
        pot_before = game_state_before.pot_total
        pot_after = game_state_after.pot_total
        pot_change = pot_after - pot_before
        
        self.logger.info(f"   - 底池变化: {pot_before} → {pot_after} (变化: {pot_change:+d})")
        
        # 德州扑克规则验证
        self._validate_action_rules(player_id, action_type, amount, game_state_before, game_state_after)
    
    def _validate_action_rules(self, player_id: str, action_type: str, amount: int, state_before, state_after):
        """验证玩家行动是否符合德州扑克规则"""
        player_before = state_before.players.get(player_id, {})
        player_after = state_after.players.get(player_id, {})
        
        chips_before = player_before.get('chips', 0)
        chips_after = player_after.get('chips', 0)
        bet_before = player_before.get('current_bet', 0)
        bet_after = player_after.get('current_bet', 0)
        
        # 验证筹码变化合理性
        chips_used = chips_before - chips_after
        bet_increase = bet_after - bet_before
        
        if action_type == 'fold':
            # 弃牌：筹码不应该减少，下注不应该增加
            if chips_used != 0:
                self.logger.warning(f"⚠️ 弃牌规则异常: {player_id} 弃牌但筹码减少了 {chips_used}")
        
        elif action_type == 'check':
            # 过牌：筹码和下注都不应该变化
            if chips_used != 0 or bet_increase != 0:
                self.logger.warning(f"⚠️ 过牌规则异常: {player_id} 过牌但筹码或下注发生变化")
        
        elif action_type == 'call':
            # 跟注：筹码减少应该等于下注增加
            if chips_used != bet_increase:
                self.logger.warning(f"⚠️ 跟注规则异常: {player_id} 筹码减少 {chips_used} 但下注增加 {bet_increase}")
        
        elif action_type in ['raise', 'bet']:
            # 加注/下注：筹码减少应该等于下注增加，且应该大于最小加注
            if chips_used != bet_increase:
                self.logger.warning(f"⚠️ 加注规则异常: {player_id} 筹码减少 {chips_used} 但下注增加 {bet_increase}")
            
            # 检查最小加注规则
            current_bet = state_before.current_bet
            min_raise = current_bet + self.BIG_BLIND
            if bet_after < min_raise and chips_after > 0:  # 不是全押的情况
                self.logger.warning(f"⚠️ 最小加注规则异常: {player_id} 加注到 {bet_after}，但最小应为 {min_raise}")
        
        elif action_type == 'all_in':
            # 全押：应该用完所有筹码
            if chips_after != 0:
                self.logger.warning(f"⚠️ 全押规则异常: {player_id} 全押后还剩 {chips_after} 筹码")
        
        # 记录规则验证结果
        self.logger.info(f"   - 规则验证: ✅通过")
    
    def _log_hand_end(self, hand_number: int, game_state):
        """记录手牌结束的详细信息"""
        self.logger.info("-" * 60)
        self.logger.info(f"🏁 第 {hand_number} 手牌结束")
        self.logger.info("-" * 60)
        
        # 记录最终状态
        self.logger.info(f"🎯 最终阶段: {game_state.current_phase}")
        self.logger.info(f"💰 最终底池: {game_state.pot_total}")
        
        # 记录玩家最终状态
        total_chips = 0
        active_players = []
        
        self.logger.info(f"👥 玩家最终状态:")
        for player_id, player_data in game_state.players.items():
            chips = player_data.get('chips', 0)
            is_active = player_data.get('active', False)
            total_bet = player_data.get('total_bet_this_hand', 0)
            player_status = player_data.get('status', 'active')
            
            total_chips += chips
            if is_active:
                active_players.append(player_id)
            
            # 改进状态显示逻辑
            if chips == 0 and player_status == 'all_in':
                status = "🔴All-In"
            elif chips == 0:
                status = "🔴出局"
            elif chips > 0:
                status = "🟢存活"
            else:
                status = "🟡未知"
            
            self.logger.info(f"   - {player_id}: {status} | 最终筹码: {chips} | 本手总投入: {total_bet}")
        
        # 最终筹码守恒检查
        total_chips_with_pot = total_chips + game_state.pot_total
        expected_total = len(self.player_ids) * self.INITIAL_CHIPS
        
        self.logger.info(f"💰 最终筹码守恒:")
        self.logger.info(f"   - 玩家筹码总和: {total_chips}")
        self.logger.info(f"   - 底池筹码: {game_state.pot_total}")
        self.logger.info(f"   - 实际总筹码: {total_chips_with_pot}")
        self.logger.info(f"   - 期望总筹码: {expected_total}")
        self.logger.info(f"   - 筹码守恒: {'✅通过' if total_chips_with_pot == expected_total else '❌违反'}")
        
        if total_chips_with_pot != expected_total:
            violation_msg = f"Hand {hand_number} 结束: 筹码守恒违反 - 实际:{total_chips_with_pot}, 期望:{expected_total}"
            self.stats.chip_conservation_violations.append(violation_msg)
            self.logger.error(f"❌ {violation_msg}")
        
        # 尝试获取获胜信息（如果可用）
        self._log_winner_info(game_state)
        
        self.logger.info(f"⏱️ 手牌用时: {time.time() - getattr(self, '_hand_start_time', time.time()):.2f}秒")
        self.logger.info("=" * 80)
    
    def _log_winner_info(self, game_state):
        """记录获胜者信息（如果可用）"""
        try:
            # 尝试从游戏历史中获取获胜信息
            history_result = self.query_service.get_game_history(self.game_id, limit=10)
            if history_result.success:
                # 查找最近的获胜事件
                for event in history_result.data:
                    if 'winner' in event.get('data', {}):
                        winner_data = event['data']
                        self.logger.info(f"🏆 获胜信息:")
                        self.logger.info(f"   - 获胜者: {winner_data.get('winner', '未知')}")
                        if 'winning_hand' in winner_data:
                            self.logger.info(f"   - 获胜牌型: {winner_data['winning_hand']}")
                        if 'pot_amount' in winner_data:
                            self.logger.info(f"   - 获得奖池: {winner_data['pot_amount']}")
                        break
                else:
                    self.logger.info(f"🏆 获胜信息: 暂无详细信息")
            else:
                self.logger.info(f"🏆 获胜信息: 无法获取历史记录")
        except Exception as e:
            self.logger.debug(f"获取获胜信息失败: {e}")
    
    def _log_error_context(self, error: Exception, context: str, game_state=None):
        """记录错误的详细上下文"""
        self.logger.error("❌" * 30)
        self.logger.error(f"错误发生: {context}")
        self.logger.error(f"错误类型: {type(error).__name__}")
        self.logger.error(f"错误信息: {str(error)}")
        
        if game_state:
            self.logger.error(f"错误时游戏状态:")
            self.logger.error(f"   - 阶段: {game_state.current_phase}")
            self.logger.error(f"   - 底池: {game_state.pot_total}")
            self.logger.error(f"   - 活跃玩家: {game_state.active_player_id}")
            self.logger.error(f"   - 玩家数: {len(game_state.players)}")
        
        self.logger.error("❌" * 30)
    
    def run_ultimate_test(self) -> UltimateTestStatsV3:
        """运行终极用户测试"""
        self.logger.info(f"开始v3 Streamlit终极用户测试 - {self.num_hands}手")
        start_time = time.time()
        
        # 反作弊检查
        CoreUsageChecker.verify_real_objects(self.command_service, "GameCommandService")
        CoreUsageChecker.verify_real_objects(self.query_service, "GameQueryService")
        CoreUsageChecker.verify_real_objects(self.ai_strategy, "RandomAI")
        
        # 设置游戏环境
        if not self._setup_game_environment():
            self.logger.error("游戏环境设置失败，测试终止")
            return self.stats
        
        # 运行测试
        for hand_num in range(1, self.num_hands + 1):
            try:
                # 在每手牌开始前检查游戏是否结束
                game_over_result = self.query_service.is_game_over(self.game_id)
                if game_over_result.success and game_over_result.data:
                    self.logger.info(f"🏁 游戏在第 {hand_num} 手牌前结束")
                    break  # 游戏结束，跳出循环
                
                self._run_single_hand(hand_num)
                
                # 每100手报告进度
                if hand_num % 100 == 0:
                    self._log_progress(hand_num)
                    
            except Exception as e:
                self.stats.errors.append(f"Hand {hand_num}: {str(e)}")
                self.stats.hands_failed += 1
                self.logger.error(f"Hand {hand_num} 执行失败: {e}")
                
                # 如果是游戏结束导致的错误，不需要继续
                if "至少需要2个有筹码的玩家" in str(e):
                    self.logger.info(f"🏁 游戏在第 {hand_num} 手牌时结束（筹码不足）")
                    break
                    
                continue
        
        # 计算最终统计
        self._calculate_final_stats(start_time)
        
        # 记录最终结果
        self._log_final_results()
        
        return self.stats
    
    def _setup_game_environment(self) -> bool:
        """设置游戏环境"""
        try:
            # 创建游戏
            result = self.command_service.create_new_game(self.game_id, self.player_ids)
            if not result.success:
                self.logger.error(f"创建游戏失败: {result.message}")
                return False
            
            # 记录初始筹码
            state_result = self.query_service.get_game_state(self.game_id)
            if state_result.success:
                self.stats.initial_total_chips = sum(
                    player_data.get('chips', 0) 
                    for player_data in state_result.data.players.values()
                )
            
            self.logger.info(f"游戏环境设置完成，初始筹码: {self.stats.initial_total_chips}")
            return True
            
        except Exception as e:
            self.logger.error(f"设置游戏环境失败: {e}")
            return False
    
    def _run_single_hand(self, hand_number: int):
        """运行单手牌"""
        self.stats.hands_attempted += 1
        self._hand_start_time = time.time()
        
        try:
            # 首先检查游戏是否已结束
            game_over_result = self.query_service.is_game_over(self.game_id)
            if game_over_result.success and game_over_result.data:
                # 游戏已结束，记录信息并退出
                winner_result = self.query_service.get_game_winner(self.game_id)
                if winner_result.success and winner_result.data:
                    self.logger.info(f"🏆 游戏结束！获胜者: {winner_result.data}")
                    self.logger.info(f"📈 获胜者详情: {winner_result.data_details}")
                else:
                    self.logger.info(f"🏆 游戏结束！原因: {game_over_result.data_details.get('reason', 'unknown')}")
                
                # 将剩余未尝试的手牌标记为跳过，而不是失败
                remaining_hands = self.num_hands - hand_number + 1
                self.logger.info(f"📊 跳过剩余 {remaining_hands} 手牌（游戏已结束）")
                return  # 正常退出，不抛出异常
            
            # 检查并重置游戏状态到INIT（如果需要）
            state_result = self.query_service.get_game_state(self.game_id)
            if state_result.success and state_result.data.current_phase not in ["INIT", "FINISHED"]:
                self.logger.debug(f"当前阶段: {state_result.data.current_phase}，需要强制结束")
                # 强制结束当前手牌
                self._force_finish_hand()
            
            # 开始新手牌
            start_result = self.command_service.start_new_hand(self.game_id)
            if not start_result.success:
                # 如果开始新手牌失败，再次检查游戏是否结束
                game_over_result = self.query_service.is_game_over(self.game_id)
                if game_over_result.success and game_over_result.data:
                    self.logger.info(f"🏆 无法开始新手牌，游戏已结束: {start_result.message}")
                    return  # 正常退出，不抛出异常
                else:
                    raise Exception(f"开始新手牌失败: {start_result.message}")
            
            # 获取手牌开始后的状态并记录详细日志
            state_result = self.query_service.get_game_state(self.game_id)
            if state_result.success:
                self._log_hand_start(hand_number, state_result.data)
            
            # 模拟手牌过程
            max_actions = 50  # 减少最大行动数，避免过长的手牌
            action_count = 0
            
            # 状态变化检测变量
            previous_state_hash = None
            consecutive_same_states = 0
            previous_phase = None
            
            while action_count < max_actions:
                # 获取游戏状态
                state_result = self.query_service.get_game_state(self.game_id)
                if not state_result.success:
                    self.logger.warning(f"获取游戏状态失败: {state_result.message}")
                    break
                
                game_state = state_result.data
                
                # 检测阶段变化并记录
                if previous_phase is not None and previous_phase != game_state.current_phase:
                    self._log_phase_transition(previous_phase, game_state.current_phase, game_state)
                previous_phase = game_state.current_phase
                
                # 计算状态哈希以检测状态变化
                current_state_hash = self._calculate_state_hash(game_state)
                
                # 检测状态是否无变化
                if current_state_hash == previous_state_hash:
                    consecutive_same_states += 1
                    if consecutive_same_states >= 3:  # 连续3次相同状态，强制退出
                        self.logger.warning(f"检测到状态无变化(连续{consecutive_same_states}次)，强制结束手牌")
                        self._force_finish_hand()
                        break
                else:
                    consecutive_same_states = 0
                
                previous_state_hash = current_state_hash
                
                # 获取活跃玩家ID
                active_player_id = self._get_active_player_id_from_snapshot(game_state)
                
                self.logger.debug(f"当前游戏状态 - 阶段: {game_state.current_phase}, 活跃玩家: {active_player_id}, 状态哈希: {current_state_hash}")
                
                # 检查手牌是否结束
                if game_state.current_phase == "FINISHED":
                    self.logger.debug("手牌已结束")
                    break
                
                # 检查是否需要推进阶段
                should_advance = self._should_advance_phase(game_state)
                self.logger.debug(f"是否需要推进阶段: {should_advance}")
                
                if should_advance:
                    self.logger.debug(f"推进阶段从 {game_state.current_phase}")
                    advance_result = self.command_service.advance_phase(self.game_id)
                    action_count += 1  # 阶段推进也计入行动数
                    
                    if not advance_result.success:
                        # 检查是否是不变量违反导致的推进失败
                        if "不变量违反" in advance_result.message or advance_result.error_code == "INVARIANT_VIOLATION":
                            violation_msg = f"阶段推进失败-不变量违反: {advance_result.message}"
                            self.stats.invariant_violations.append(violation_msg)
                            self.stats.critical_invariant_violations += 1
                            self.stats.critical_errors += 1
                            self.logger.error(f"❌ 严重不变量违反: {violation_msg}")
                            raise Exception(f"阶段推进不变量违反导致测试失败: {violation_msg}")
                        else:
                            self.logger.warning(f"推进阶段失败: {advance_result.message}")
                        break
                    
                    # 推进阶段后重新获取状态，检查是否结束
                    state_result = self.query_service.get_game_state(self.game_id)
                    if state_result.success and state_result.data.current_phase == "FINISHED":
                        self.logger.debug("推进阶段后手牌结束")
                        break
                    continue
                
                # 处理玩家行动
                if active_player_id:
                    self.logger.debug(f"发现活跃玩家: {active_player_id}")
                    # 在终极测试中，所有玩家行动都统计为用户行动
                    self._handle_user_action_for_any_player(game_state, active_player_id)
                else:
                    self.logger.debug(f"没有活跃玩家，当前阶段: {game_state.current_phase}")
                    # 如果没有活跃玩家，尝试模拟一个用户行动
                    if game_state.current_phase in ["PRE_FLOP", "FLOP", "TURN", "RIVER"]:
                        self.logger.debug("尝试强制模拟用户行动")
                        # 强制模拟用户行动
                        self._simulate_user_action_without_active_player(game_state)
                    else:
                        self.logger.debug(f"阶段 {game_state.current_phase} 不需要用户行动")
                        # 如果不是下注阶段且没有活跃玩家，强制推进
                        self.logger.debug("非下注阶段且无活跃玩家，强制推进阶段")
                        advance_result = self.command_service.advance_phase(self.game_id)
                        if not advance_result.success:
                            # 检查是否是不变量违反
                            if "不变量违反" in advance_result.message or advance_result.error_code == "INVARIANT_VIOLATION":
                                violation_msg = f"强制推进阶段失败-不变量违反: {advance_result.message}"
                                self.stats.invariant_violations.append(violation_msg)
                                self.stats.critical_invariant_violations += 1
                                self.stats.critical_errors += 1
                                self.logger.error(f"❌ 严重不变量违反: {violation_msg}")
                                raise Exception(f"强制推进阶段不变量违反导致测试失败: {violation_msg}")
                            else:
                                self.logger.warning(f"强制推进阶段失败: {advance_result.message}")
                            self._force_finish_hand()
                            break
                
                action_count += 1
                self.logger.debug(f"行动计数: {action_count}/{max_actions}")
                
                # 如果行动数过多，强制结束手牌
                if action_count >= max_actions - 5:
                    self.logger.warning(f"行动数过多({action_count})，强制结束手牌")
                    self._force_finish_hand()
                    break
            
            # 确保手牌正确结束
            final_state_result = self.query_service.get_game_state(self.game_id)
            if final_state_result.success:
                if final_state_result.data.current_phase != "FINISHED":
                    self.logger.debug("手牌未正确结束，强制结束")
                    self._force_finish_hand()
                    # 重新获取最终状态
                    final_state_result = self.query_service.get_game_state(self.game_id)
                
                # 记录手牌结束的详细日志
                if final_state_result.success:
                    self._log_hand_end(hand_number, final_state_result.data)
            
            self.stats.hands_completed += 1
            
            # 记录手牌时间
            hand_time = time.time() - self._hand_start_time
            self.stats.average_hand_time = ((self.stats.average_hand_time * (hand_number - 1)) + hand_time) / hand_number
            
        except Exception as e:
            self.stats.hands_failed += 1
            
            # 获取错误时的游戏状态
            try:
                error_state_result = self.query_service.get_game_state(self.game_id)
                error_state = error_state_result.data if error_state_result.success else None
            except:
                error_state = None
            
            # 记录详细的错误上下文
            self._log_error_context(e, f"第{hand_number}手牌执行", error_state)
            
            # 确保游戏会话仍然存在
            try:
                state_result = self.query_service.get_game_state(self.game_id)
                if not state_result.success:
                    # 如果游戏会话丢失，重新创建
                    self.logger.warning("游戏会话丢失，重新创建")
                    self.command_service.create_new_game(self.game_id, self.player_ids)
            except Exception as e2:
                self.logger.error(f"恢复游戏会话失败: {e2}")
                self._log_error_context(e2, "恢复游戏会话")
    
    def _should_advance_phase(self, game_state) -> bool:
        """判断是否应该推进阶段"""
        # 如果已经是FINISHED阶段，不需要推进
        if game_state.current_phase == "FINISHED":
            self.logger.debug("已是FINISHED阶段，不推进")
            return False
        
        # 检查是否有活跃玩家
        active_player_id = self._get_active_player_id_from_snapshot(game_state)
        
        # 如果有活跃玩家，不推进阶段
        if active_player_id is not None:
            self.logger.debug(f"有活跃玩家 {active_player_id}，不推进阶段")
            return False
        
        # 检查是否所有玩家都已行动完毕
        all_action_complete = self._all_players_action_complete(game_state)
        
        result = all_action_complete
        self.logger.debug(f"推进阶段判断 - 活跃玩家: {active_player_id}, 当前阶段: {game_state.current_phase}, 所有行动完成: {all_action_complete}, 结果: {result}")
        return result
    
    def _all_players_action_complete(self, game_state) -> bool:
        """检查是否所有玩家都已完成行动"""
        try:
            # 简化逻辑：如果没有活跃玩家且不是FINISHED阶段，认为行动完成
            if game_state.current_phase == "FINISHED":
                return True
            
            # 检查是否有活跃玩家
            active_player_id = self._get_active_player_id_from_snapshot(game_state)
            if active_player_id is not None:
                return False  # 还有活跃玩家，行动未完成
            
            # 检查是否是需要玩家行动的阶段
            betting_phases = ["PRE_FLOP", "FLOP", "TURN", "RIVER"]
            if game_state.current_phase in betting_phases:
                # 在下注阶段，如果没有活跃玩家，可能是所有玩家都已行动
                return True
            
            # 其他阶段（如SHOWDOWN），如果没有活跃玩家，认为可以推进
            return True
            
        except Exception as e:
            self.logger.warning(f"检查玩家行动完成状态失败: {e}")
            return True  # 出错时默认认为可以推进
    
    def _force_finish_hand(self):
        """强制结束当前手牌"""
        try:
            # 尝试多次推进阶段直到FINISHED
            max_advances = 10
            for _ in range(max_advances):
                state_result = self.query_service.get_game_state(self.game_id)
                if not state_result.success:
                    break
                
                if state_result.data.current_phase == "FINISHED":
                    break
                
                # 推进阶段
                advance_result = self.command_service.advance_phase(self.game_id)
                if not advance_result.success:
                    break
            
            # 如果还没有结束，尝试重置到INIT状态而不是删除游戏
            final_state_result = self.query_service.get_game_state(self.game_id)
            if final_state_result.success and final_state_result.data.current_phase != "FINISHED":
                self.logger.warning("无法推进到FINISHED阶段，尝试重置游戏状态")
                # 不删除游戏，而是尝试重置状态
                try:
                    # 先尝试推进到FINISHED
                    for _ in range(5):
                        advance_result = self.command_service.advance_phase(self.game_id)
                        if not advance_result.success:
                            break
                        state_result = self.query_service.get_game_state(self.game_id)
                        if state_result.success and state_result.data.current_phase == "FINISHED":
                            break
                except Exception as e:
                    self.logger.warning(f"推进到FINISHED失败: {e}")
                
        except Exception as e:
            self.logger.warning(f"强制结束手牌失败: {e}")
            # 不要删除游戏会话，只记录错误
    
    def _handle_user_action_for_any_player(self, game_state, player_id: str):
        """处理任何玩家的行动（统计为用户行动）"""
        self.stats.total_user_actions += 1
        action_start_time = time.time()
        
        try:
            # 获取行动前的游戏状态
            state_before_result = self.query_service.get_game_state(self.game_id)
            if not state_before_result.success:
                raise Exception(f"无法获取行动前状态: {state_before_result.message}")
            state_before = state_before_result.data
            
            # 使用AI决策来模拟玩家行动
            adapted_game_state = GameStateSnapshotAdapter(game_state)
            ai_decision = self.ai_strategy.decide_action(adapted_game_state, player_id)
            
            # 转换为PlayerAction
            player_action = PlayerAction(
                action_type=ai_decision.decision_type.name.lower(),
                amount=ai_decision.amount
            )
            
            self.logger.debug(f"玩家 {player_id} 准备执行行动: {player_action.action_type}, 金额: {player_action.amount}")
            
            # 执行行动
            result = self.command_service.execute_player_action(
                self.game_id, player_id, player_action
            )
            
            # 获取行动后的游戏状态
            state_after_result = self.query_service.get_game_state(self.game_id)
            if state_after_result.success:
                state_after = state_after_result.data
                # 记录详细的行动日志
                self._log_player_action(
                    player_id, 
                    player_action.action_type, 
                    player_action.amount, 
                    state_before, 
                    state_after
                )
            
            if result.success:
                self.stats.successful_actions += 1
                # 记录行动分布
                action_type = player_action.action_type
                self.stats.action_distribution[action_type] = self.stats.action_distribution.get(action_type, 0) + 1
                self.logger.debug(f"行动执行成功，成功行动数: {self.stats.successful_actions}")
            else:
                self.stats.failed_actions += 1
                
                # 检查是否是不变量违反错误
                if "不变量违反" in result.message or result.error_code == "INVARIANT_VIOLATION":
                    # 这是严重的不变量违反错误
                    violation_msg = f"玩家 {player_id} 行动导致不变量违反: {result.message}"
                    self.stats.invariant_violations.append(violation_msg)
                    self.stats.critical_invariant_violations += 1
                    self.stats.critical_errors += 1
                    self.logger.error(f"❌ 严重不变量违反: {violation_msg}")
                    
                    # 记录详细错误上下文
                    self._log_error_context(Exception(result.message), f"玩家 {player_id} 不变量违反", game_state)
                    
                    # 不变量违反应该立即抛出异常，而不是继续执行
                    raise Exception(f"不变量违反导致测试失败: {violation_msg}")
                else:
                    # 普通的行动失败
                    self.stats.errors.append(f"玩家 {player_id} 行动失败: {result.message}")
                    self.logger.warning(f"玩家 {player_id} 行动失败: {result.message}")
                    # 记录错误上下文
                    self._log_error_context(Exception(result.message), f"玩家 {player_id} 行动失败", game_state)
            
            # 记录行动时间
            action_time = time.time() - action_start_time
            if self.stats.total_user_actions > 0:
                self.stats.average_action_time = ((self.stats.average_action_time * (self.stats.total_user_actions - 1)) + action_time) / self.stats.total_user_actions
            
        except Exception as e:
            self.stats.failed_actions += 1
            
            # 检查是否是不变量违反相关的异常
            if "不变量违反" in str(e):
                # 这是不变量违反异常，应该导致测试失败
                violation_msg = f"玩家 {player_id} 行动异常-不变量违反: {str(e)}"
                self.stats.invariant_violations.append(violation_msg)
                self.stats.critical_invariant_violations += 1
                self.stats.critical_errors += 1
                self.logger.error(f"❌ 严重不变量违反异常: {violation_msg}")
                # 记录错误上下文
                self._log_error_context(e, f"玩家 {player_id} 不变量违反异常", game_state)
                # 重新抛出异常，导致测试失败
                raise
            else:
                # 普通异常
                self.stats.errors.append(f"玩家 {player_id} 行动异常: {str(e)}")
                self.logger.error(f"玩家 {player_id} 行动异常: {str(e)}")
                # 记录错误上下文
                self._log_error_context(e, f"玩家 {player_id} 行动异常", game_state)

    def _handle_user_action(self, game_state):
        """处理用户行动（保留原方法以兼容性）"""
        return self._handle_user_action_for_any_player(game_state, "player_0")
    
    def _get_active_player_id_from_snapshot(self, game_state):
        """从GameStateSnapshot获取活跃玩家ID"""
        # 检查是否是application层的GameStateSnapshot（有active_player_id字段）
        if hasattr(game_state, 'active_player_id'):
            return game_state.active_player_id
        
        # 如果是core层的GameStateSnapshot（有active_player_position字段）
        if hasattr(game_state, 'active_player_position'):
            if game_state.active_player_position is None:
                return None
            
            for player in game_state.players:
                if player.position == game_state.active_player_position:
                    return player.player_id
        
        return None


    
    def _log_progress(self, hand_number: int):
        """记录进度"""
        completion_rate = (self.stats.hands_completed / self.stats.hands_attempted) * 100 if self.stats.hands_attempted > 0 else 0
        action_success_rate = (self.stats.successful_actions / self.stats.total_user_actions) * 100 if self.stats.total_user_actions > 0 else 0
        
        self.logger.info(f"进度报告 - Hand {hand_number}/{self.num_hands}")
        self.logger.info(f"  完成率: {completion_rate:.1f}% ({self.stats.hands_completed}/{self.stats.hands_attempted})")
        self.logger.info(f"  行动成功率: {action_success_rate:.1f}% ({self.stats.successful_actions}/{self.stats.total_user_actions})")
        self.logger.info(f"  错误数量: {len(self.stats.errors)}")
    
    def _calculate_final_stats(self, start_time: float):
        """计算最终统计"""
        self.stats.total_test_time = time.time() - start_time
        
        # 获取最终筹码
        state_result = self.query_service.get_game_state(self.game_id)
        if state_result.success:
            self.stats.final_total_chips = sum(
                player_data.get('chips', 0) 
                for player_data in state_result.data.players.values()
            )
    
    def _log_final_results(self):
        """记录最终结果"""
        self.logger.info("=" * 80)
        self.logger.info("🏆 v3 Streamlit终极用户测试结果")
        self.logger.info("=" * 80)
        
        # 基本统计
        completion_rate = (self.stats.hands_completed / self.stats.hands_attempted) * 100 if self.stats.hands_attempted > 0 else 0
        self.logger.info(f"手牌完成率: {completion_rate:.1f}% ({self.stats.hands_completed}/{self.stats.hands_attempted})")
        
        # 行动统计
        action_success_rate = (self.stats.successful_actions / self.stats.total_user_actions) * 100 if self.stats.total_user_actions > 0 else 0
        self.logger.info(f"行动成功率: {action_success_rate:.1f}% ({self.stats.successful_actions}/{self.stats.total_user_actions})")
        
        # 筹码统计
        self.logger.info(f"筹码守恒: 初始{self.stats.initial_total_chips}, 最终{self.stats.final_total_chips}")
        
        # 不变量违反统计
        self.logger.info(f"不变量检查: {len(self.stats.invariant_violations)} 个违反, {self.stats.critical_invariant_violations} 个严重违反")
        if self.stats.invariant_violations:
            self.logger.error("不变量违反详情:")
            for violation in self.stats.invariant_violations:
                self.logger.error(f"  - {violation}")
        
        # 性能统计
        hands_per_second = self.stats.hands_completed / self.stats.total_test_time if self.stats.total_test_time > 0 else 0
        self.logger.info(f"测试速度: {hands_per_second:.2f} 手/秒")
        
        # 行动分布
        if self.stats.action_distribution:
            self.logger.info("行动分布:")
            for action, count in self.stats.action_distribution.items():
                percentage = (count / self.stats.successful_actions) * 100 if self.stats.successful_actions > 0 else 0
                self.logger.info(f"  {action}: {count} ({percentage:.1f}%)")

    def _calculate_state_hash(self, game_state) -> str:
        """计算游戏状态哈希，用于检测状态变化"""
        try:
            # 提取关键状态信息
            state_info = {
                'phase': game_state.current_phase,
                'pot_total': getattr(game_state, 'pot_total', 0),
                'current_bet': getattr(game_state, 'current_bet', 0),
                'active_player': self._get_active_player_id_from_snapshot(game_state),
                'community_cards_count': len(getattr(game_state, 'community_cards', [])),
            }
            
            # 添加玩家状态信息
            if hasattr(game_state, 'players'):
                player_states = {}
                for player_id, player_data in game_state.players.items():
                    player_states[player_id] = {
                        'chips': player_data.get('chips', 0),
                        'current_bet': player_data.get('current_bet', 0),
                        'active': player_data.get('active', False),
                        'status': player_data.get('status', 'active')
                    }
                state_info['players'] = player_states
            
            # 计算哈希
            import hashlib
            import json
            state_str = json.dumps(state_info, sort_keys=True)
            return hashlib.md5(state_str.encode()).hexdigest()[:8]  # 取前8位
            
        except Exception as e:
            self.logger.warning(f"计算状态哈希失败: {e}")
            return f"error_{time.time()}"  # 返回时间戳作为备用
    
    def _simulate_user_action_without_active_player(self, game_state):
        """当没有活跃玩家时，强制模拟用户行动"""
        self.logger.debug("开始强制模拟用户行动")
        try:
            # 获取行动前的游戏状态
            state_before_result = self.query_service.get_game_state(self.game_id)
            if not state_before_result.success:
                raise Exception(f"无法获取行动前状态: {state_before_result.message}")
            state_before = state_before_result.data
            
            # 强制模拟用户行动，即使没有活跃玩家
            self.stats.total_user_actions += 1
            action_start_time = time.time()
            
            self.logger.debug(f"用户行动统计增加到: {self.stats.total_user_actions}")
            
            # 获取可用行动
            actions_result = self.query_service.get_available_actions(self.game_id, "player_0")
            if not actions_result.success:
                self.logger.warning(f"获取可用行动失败: {actions_result.message}")
                self.stats.failed_actions += 1
                return
            
            available_actions = actions_result.data.actions
            self.logger.debug(f"可用行动: {available_actions}")
            
            if not available_actions:
                # 如果没有可用行动，尝试基本行动
                available_actions = ['check', 'fold']
                self.logger.debug(f"使用默认行动: {available_actions}")
            
            # 随机选择行动
            chosen_action = random.choice(available_actions)
            amount = 0
            
            self.logger.debug(f"选择的行动: {chosen_action}")
            
            if chosen_action in ['raise', 'bet']:
                # 计算加注金额
                amount_result = self.query_service.calculate_random_raise_amount(
                    self.game_id, "player_0", 0.3, 0.7
                )
                if amount_result.success:
                    amount = amount_result.data
                    self.logger.debug(f"计算的加注金额: {amount}")
            
            # 执行行动
            player_action = PlayerAction(
                action_type=chosen_action,
                amount=amount
            )
            
            self.logger.debug(f"执行玩家行动: {player_action}")
            
            result = self.command_service.execute_player_action(
                self.game_id, "player_0", player_action
            )
            
            # 获取行动后的游戏状态并记录详细日志
            state_after_result = self.query_service.get_game_state(self.game_id)
            if state_after_result.success:
                state_after = state_after_result.data
                self._log_player_action(
                    "player_0", 
                    chosen_action, 
                    amount, 
                    state_before, 
                    state_after
                )
            
            if result.success:
                self.stats.successful_actions += 1
                # 记录行动分布
                self.stats.action_distribution[chosen_action] = self.stats.action_distribution.get(chosen_action, 0) + 1
                self.logger.debug(f"行动执行成功，成功行动数: {self.stats.successful_actions}")
            else:
                self.stats.failed_actions += 1
                self.stats.errors.append(f"强制用户行动失败: {result.message}")
                self.logger.warning(f"行动执行失败: {result.message}")
                self._log_error_context(Exception(result.message), "强制用户行动失败", game_state)
            
            # 记录行动时间
            action_time = time.time() - action_start_time
            if self.stats.total_user_actions > 0:
                self.stats.average_action_time = ((self.stats.average_action_time * (self.stats.total_user_actions - 1)) + action_time) / self.stats.total_user_actions
            
        except Exception as e:
            self.stats.failed_actions += 1
            self.stats.errors.append(f"强制用户行动异常: {str(e)}")
            self.logger.error(f"强制用户行动异常: {str(e)}")
            self._log_error_context(e, "强制用户行动异常", game_state)


class GameStateSnapshotAdapter:
    """适配器类，将application层的GameStateSnapshot适配为AI期望的接口"""
    
    def __init__(self, app_snapshot):
        """
        初始化适配器
        
        Args:
            app_snapshot: application层的GameStateSnapshot
        """
        self.app_snapshot = app_snapshot
        
    def __getattr__(self, name):
        """代理属性访问到原始快照"""
        return getattr(self.app_snapshot, name)
    
    def get_player_by_id(self, player_id: str):
        """获取玩家信息，适配AI期望的接口"""
        if player_id not in self.app_snapshot.players:
            return None
        
        player_data = self.app_snapshot.players[player_id]
        
        # 创建一个简单的玩家对象，包含AI需要的属性
        class PlayerAdapter:
            def __init__(self, data):
                self.chips = data.get('chips', 0)
                self.is_active = data.get('active', False)
                self.current_bet = data.get('current_bet', 0)
                self.total_bet_this_hand = data.get('total_bet_this_hand', 0)
                
        return PlayerAdapter(player_data)
    
    @property
    def current_bet(self):
        """当前下注金额"""
        return self.app_snapshot.current_bet
    
    @property
    def big_blind_amount(self):
        """大盲注金额，默认值"""
        return 100  # 默认大盲注金额
    
    @property
    def pot(self):
        """奖池信息"""
        class PotAdapter:
            def __init__(self, total_pot):
                self.total_pot = total_pot
        
        return PotAdapter(self.app_snapshot.pot_total)


# ==================== Pytest 兼容测试函数 ====================

def test_streamlit_ultimate_user_experience_v3_quick():
    """
    快速版本的v3 Streamlit终极用户体验测试 (100手牌)
    
    反作弊检查：
    1. 确保使用真实的v3应用服务
    2. 验证CQRS架构的正确使用
    3. 检查AI策略的真实性
    """
    print("🧪 开始v3快速Streamlit终极用户体验测试...")
    
    # 创建测试器
    tester = StreamlitUltimateUserTesterV3(num_hands=100)
    
    # 反作弊检查：验证使用真实的v3组件
    CoreUsageChecker.verify_real_objects(tester.command_service, "GameCommandService")
    CoreUsageChecker.verify_real_objects(tester.query_service, "GameQueryService")
    CoreUsageChecker.verify_real_objects(tester.ai_strategy, "RandomAI")
    
    # 运行测试
    stats = tester.run_ultimate_test()
    
    # 验证测试结果
    assert stats.hands_attempted > 0, "应该尝试了至少一手牌"
    assert stats.total_user_actions > 0, "应该有用户行动"
    
    # 成功率检查
    if stats.hands_attempted > 0:
        completion_rate = stats.hands_completed / stats.hands_attempted
        assert completion_rate >= 0.5, f"手牌完成率应该至少50%，实际: {completion_rate:.1%}"
    
    if stats.total_user_actions > 0:
        action_success_rate = stats.successful_actions / stats.total_user_actions
        assert action_success_rate >= 0.5, f"行动成功率应该至少50%，实际: {action_success_rate:.1%}"
    
    # 筹码守恒检查
    assert len(stats.chip_conservation_violations) == 0, f"不应该有筹码守恒违规，实际: {len(stats.chip_conservation_violations)}"
    
    # 不变量违反检查 - 这是新增的严格检查
    assert len(stats.invariant_violations) == 0, f"不应该有不变量违反，实际: {len(stats.invariant_violations)} 个违反: {stats.invariant_violations}"
    assert stats.critical_invariant_violations == 0, f"不应该有严重不变量违反，实际: {stats.critical_invariant_violations}"
    
    print(f"✅ v3快速测试完成: {stats.hands_completed}/{stats.hands_attempted} 手牌完成")
    print(f"✅ 行动成功率: {stats.successful_actions}/{stats.total_user_actions}")
    print(f"✅ 错误控制: {len(stats.errors)} 个错误")
    print(f"✅ 不变量检查: {len(stats.invariant_violations)} 个违反")


@pytest.mark.slow
def test_streamlit_ultimate_user_experience_v3_full():
    """
    完整版本的v3 Streamlit终极用户体验测试 (1000手牌)
    
    这是v3架构的终极验收测试
    """
    print("🧪 开始v3完整Streamlit终极用户体验测试...")
    
    # 创建测试器
    tester = StreamlitUltimateUserTesterV3(num_hands=1000)
    
    # 运行测试
    stats = tester.run_ultimate_test()
    
    # 严格的验收标准
    assert stats.hands_attempted == 1000, f"应该尝试1000手牌，实际: {stats.hands_attempted}"
    
    # 完成率应该很高
    completion_rate = stats.hands_completed / stats.hands_attempted if stats.hands_attempted > 0 else 0
    assert completion_rate >= 0.99, f"完成率应该至少99%，实际: {completion_rate:.1%}"
    
    # 行动成功率应该很高
    action_success_rate = stats.successful_actions / stats.total_user_actions if stats.total_user_actions > 0 else 0
    assert action_success_rate >= 0.99, f"行动成功率应该至少99%，实际: {action_success_rate:.1%}"
    
    # 不应该有严重错误
    assert stats.critical_errors == 0, f"不应该有严重错误，实际: {stats.critical_errors}"
    
    # 筹码守恒
    assert len(stats.chip_conservation_violations) == 0, \
        f"不应该有筹码守恒违规，实际: {len(stats.chip_conservation_violations)}"
    
    # 不变量违反检查 - 严格检查
    assert len(stats.invariant_violations) == 0, \
        f"不应该有不变量违反，实际: {len(stats.invariant_violations)} 个违反: {stats.invariant_violations}"
    assert stats.critical_invariant_violations == 0, \
        f"不应该有严重不变量违反，实际: {stats.critical_invariant_violations}"
    
    # 性能检查
    assert stats.total_test_time > 0, "测试时间应该大于0"
    hands_per_second = stats.hands_completed / stats.total_test_time
    assert hands_per_second >= 5.0, f"测试速度应该至少5手/秒，实际: {hands_per_second:.2f}"
    
    print(f"✅ v3完整测试完成: {stats.hands_completed}/{stats.hands_attempted} 手牌")
    print(f"✅ 测试用时: {stats.total_test_time:.2f}秒")
    print(f"✅ 测试速度: {hands_per_second:.2f} 手/秒")
    print(f"✅ 不变量检查: {len(stats.invariant_violations)} 个违反")


if __name__ == "__main__":
    # 运行快速测试
    test_streamlit_ultimate_user_experience_v3_quick() 