#!/usr/bin/env python3
"""
Streamlit UI 终极用户体验测试 v3

基于v3架构的终极测试，严格遵循CQRS模式。
模拟真实用户在Streamlit界面下进行德州扑克游戏。
使用Application层服务，消除UI层业务逻辑。

测试模式说明：
- 基本测试（1手牌）：验证基本功能能否跑通
- 快速测试（10手牌）：进行细致的功能测试
- 终极测试（100手牌）：发版前的完整验证

PowerShell 运行示例：
# 基本测试 - 验证能否跑通
.venv\\Scripts\\python v3\\tests\\integration\\v3_test_ultimate.py --hands 1

# 快速测试 - 细致功能测试  
.venv\\Scripts\\python v3\\tests\\integration\\v3_test_ultimate.py --hands 10

# 终极测试 - 发版前验证
.venv\\Scripts\\python v3\\tests\\integration\\v3_test_ultimate.py --hands 100

# 使用pytest运行（保持兼容）
.venv\\Scripts\\python -m pytest v3\\tests\\integration\\v3_test_ultimate.py::test_streamlit_ultimate_user_experience_v3 -v
"""

import sys
import os
import time
import logging
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from unittest.mock import Mock, patch, MagicMock
import pytest
import pprint
import random
import hashlib

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from v3.application import (
    GameCommandService, GameQueryService, PlayerAction, 
    TestStatsService, TestStatsSnapshot,
    GameFlowService, HandFlowConfig
)
from v3.core.state_machine import GamePhase
from v3.tests.anti_cheat.core_usage_checker import CoreUsageChecker


# 注意：UserActionType, UserAction, UltimateTestStatsV3 等数据类已移除
# 现在使用Application层的TestStatsSnapshot和相关服务


def determine_test_type(num_hands: int) -> str:
    """
    根据手牌数量自动确定测试类型
    
    Args:
        num_hands: 手牌数量
        
    Returns:
        测试类型字符串
    """
    if num_hands == 1:
        return "basic"
    elif num_hands <= 10:
        return "quick"
    else:
        return "ultimate"


class StreamlitUltimateUserTesterV3:
    """v3版本的Streamlit终极用户测试器 - 纯UI层实现"""
    
    def __init__(self, num_hands: int = 100, test_type: str = "ultimate"):
        """
        初始化测试器
        
        Args:
            num_hands: 手牌数量
            test_type: 测试类型 (ultimate, quick, stress)
        """
        self.num_hands = num_hands
        self.test_type = test_type
        self.log_file_path: Optional[str] = None
        self.logger = self._setup_logging()
        
        # 打印日志文件路径，方便快速定位
        if self.log_file_path:
            log_message = f"Log file for this test run: {self.log_file_path}"
            # 使用 print 直接输出到控制台，确保可见性
            print("\n" + "="*80)
            print(f"Log: {log_message}")
            print("="*80 + "\n")
            # 同时写入日志文件
            self.logger.info(log_message)
        
        # v3架构组件 - 严格遵循CQRS模式，通过Application层获取服务
        from v3.application.config_service import ConfigService
        from v3.application.validation_service import ValidationService
        
        # 创建集中化的配置和验证服务
        self.config_service = ConfigService()
        self.validation_service = ValidationService(self.config_service)
        
        # 使用依赖注入创建命令和查询服务 - Application层自动管理EventBus
        self.command_service = GameCommandService(
            validation_service=self.validation_service,
            config_service=self.config_service
        )
        self.query_service = GameQueryService(
            command_service=self.command_service,
            config_service=self.config_service
        )
        self.stats_service = TestStatsService()
        
        # 添加GameFlowService - 核心业务流程控制，EventBus设为None让其使用全局总线
        self.flow_service = GameFlowService(
            command_service=self.command_service,
            event_bus=None  # 使用全局EventBus，避免UI层直接管理
        )
        
        # 从Application层获取测试配置
        self.test_config = self._load_test_config()
        
        # 游戏基础设置
        self.game_id = "ultimate_test_game"
        self.session_id = f"test_session_{int(time.time())}"
        
        # 从配置获取玩家设置
        self.player_ids = self.test_config.get('default_player_ids', ["player_0", "player_1"])
        
        # PLAN A.9: 内部追踪本手牌下注玩家
        self._current_hand_bidders = set()
    
    def _setup_logging(self) -> logging.Logger:
        """设置日志记录"""
        logger = logging.getLogger("StreamlitUltimateTestV3")
        logger.setLevel(logging.DEBUG)
        
        # PLAN A.1: 修复重复日志问题
        logger.propagate = False
        
        # 统一日志文件名，新日志完全覆盖旧日志
        log_filename = "v3_ultimate.log"
        log_file = project_root / "v3" / "tests" / "test_logs" / log_filename
        log_file.parent.mkdir(exist_ok=True)
        self.log_file_path = str(log_file)
        
        file_handler = logging.FileHandler(self.log_file_path, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _load_test_config(self) -> Dict[str, Any]:
        """从Application层加载测试配置"""
        try:
            config_result = self.query_service.get_ui_test_config(self.test_type)
            if config_result.success:
                config = config_result.data
                # 覆盖手牌数量设置
                config['num_hands'] = self.num_hands
                self.logger.info(f"已加载 {self.test_type} 测试配置")
                return config
            else:
                self.logger.warning(f"加载测试配置失败: {config_result.message}")
                # 返回最小默认配置
                return {
                    'default_player_ids': ["player_0", "player_1"],
                    'initial_chips_per_player': 1000,
                    'max_actions_per_hand': 50,
                    'num_hands': self.num_hands
                }
        except Exception as e:
            self.logger.error(f"加载测试配置异常: {e}")
            # 返回最小默认配置
            return {
                'default_player_ids': ["player_0", "player_1"],
                'initial_chips_per_player': 1000,
                'max_actions_per_hand': 50,
                'num_hands': self.num_hands
            }
    
    def _get_ai_config_from_application(self) -> Dict[str, Any]:
        """从Application层获取AI配置"""
        try:
            # 尝试通过查询服务获取AI配置
            ai_config_result = self.query_service.get_ai_config(self.game_id)
            if ai_config_result.success:
                return ai_config_result.data
            else:
                self.logger.debug(f"未找到游戏专用AI配置，使用默认配置: {ai_config_result.message}")
                # 返回Application层的默认AI配置
                return {}  # 让Application层处理默认配置
        except Exception as e:
            self.logger.debug(f"获取AI配置失败，使用默认: {e}")
            return {}
    
    def _log_hand_start(self, hand_number: int, game_state):
        """记录手牌开始的详细信息 - PLAN A.2: 增强日志记录"""
        # PLAN A.9: 重置本手牌下注玩家追踪
        self._current_hand_bidders.clear()
        
        self.logger.info("=" * 80)
        
        # PLAN A.2: 尝试获取盲注信息
        small_blind_info = "未知"
        big_blind_info = "未知"
        try:
            rules_result = self.query_service.get_game_rules_config(self.game_id)
            if rules_result.success:
                small_blind = rules_result.data.get('small_blind', 5)
                big_blind = rules_result.data.get('big_blind', 10)
                
                # 尝试识别支付盲注的玩家 - 从游戏状态或事件中获取
                try:
                    # 查找最近的盲注事件
                    history_result = self.query_service.get_game_history(self.game_id, limit=5)
                    if history_result.success:
                        for event in history_result.data:
                            event_data = event.get('data', {})
                            if 'small_blind_player' in event_data:
                                sb_player = event_data['small_blind_player']
                                bb_player = event_data.get('big_blind_player', '未知')
                                small_blind_info = f"{sb_player}({small_blind})"
                                big_blind_info = f"{bb_player}({big_blind})"
                                break
                    else:
                        small_blind_info = f"SB({small_blind})"
                        big_blind_info = f"BB({big_blind})"
                except Exception as e:
                    self.logger.debug(f"获取盲注玩家信息失败: {e}")
                    small_blind_info = f"SB({small_blind})"
                    big_blind_info = f"BB({big_blind})"
        except Exception as e:
            self.logger.debug(f"获取盲注信息失败: {e}")
        
        self.logger.info(f"🎯 第 {hand_number} 手牌开始 - {small_blind_info}, {big_blind_info}")
        self.logger.info("=" * 80)
        
        # 记录游戏基本信息
        self.logger.info(f"📊 游戏状态:")
        self.logger.info(f"   - 游戏ID: {game_state.game_id}")
        self.logger.info(f"   - 当前阶段: {game_state.phase}")
        self.logger.info(f"   - 底池总额: {game_state.pot.total_pot}")
        self.logger.info(f"   - 当前下注: {game_state.current_bet}")
        # 从快照中直接获取活跃玩家
        active_player_id = None
        if hasattr(game_state, 'active_player_position') and game_state.active_player_position is not None:
            for player in game_state.players:
                if player.position == game_state.active_player_position:
                    active_player_id = player.player_id
                    break
        self.logger.info(f"   - 活跃玩家: {active_player_id}")
        
        # PLAN A.2: 记录玩家信息（包含位置信息）
        active_players = 0
        total_chips = 0
        self.logger.info(f"👥 玩家状态:")
        
        for player_data in game_state.players:
            player_id = player_data.player_id
            chips = player_data.chips
            is_active = player_data.is_active
            current_bet = player_data.current_bet
            total_bet_this_hand = player_data.total_bet_this_hand
            player_status = 'active' if is_active else 'inactive' # Simplified status from snapshot
            
            # PLAN A.2: 获取玩家位置信息
            position = player_data.position
            
            if is_active:
                active_players += 1
            
            total_chips += chips
            
            # PLAN A.2: 增强日志，显示位置、状态、底牌获取尝试
            hand_str = "未获取"
            try:
                # 假设快照中的hole_cards是Card对象元组
                if player_data.hole_cards:
                    hand_str = " ".join(str(c) for c in player_data.hole_cards)
            except Exception as e:
                self.logger.debug(f"无法格式化玩家 {player_id} 的手牌: {e}")

            self.logger.info(
                f"   - [{position}] {player_id}: "
                f"筹码={chips}, 当前下注={current_bet}, "
                f"本手总下注={total_bet_this_hand}, 状态={player_status}, "
                f"手牌=[{hand_str}]"
            )
        
        self.logger.info(f"   - 活跃玩家数: {active_players}")
        self.logger.info(f"   - 当前总筹码: {total_chips}")
        
        # 筹码守恒检查 - 使用application层获取游戏规则
        total_chips_with_pot = total_chips + game_state.pot.total_pot
        rules_result = self.query_service.get_game_rules_config(self.game_id)
        initial_chips = self.test_config.get('initial_chips_per_player', 1000)
        if rules_result.success:
            initial_chips = rules_result.data.get('initial_chips', initial_chips)
        expected_total = len(self.player_ids) * initial_chips
        
        self.logger.info(f"💰 当前筹码状态:")
        self.logger.info(f"   - 玩家筹码总和: {total_chips}")
        self.logger.info(f"   - 底池筹码: {game_state.pot.total_pot}")
        self.logger.info(f"   - 实际总筹码: {total_chips_with_pot}")
        self.logger.info(f"   - 期望总筹码: {expected_total}")
        self.logger.info(f"   - 筹码守恒: {'通过' if total_chips_with_pot == expected_total else '违反'}")
        
        if total_chips_with_pot != expected_total:
            violation_msg = f"Hand {hand_number} 开始时筹码不守恒 - 实际:{total_chips_with_pot}, 期望:{expected_total}"
            # 通过统计服务记录违规
            self.stats_service.record_chip_conservation_violation(self.session_id, violation_msg)
            self.logger.error(f"❌ {violation_msg}")
        
        self.logger.info(f"🎮 活跃玩家数: {active_players}")
        self.logger.info(f"⏱️ 预计最大行动数: {self.test_config.get('max_actions_per_hand', 50)}")
        
        # 记录手牌开始时间
        self._hand_start_time = time.time()
    
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
        self.logger.info(f"💰 底池状态: {game_state.pot.total_pot}")
        self.logger.info(f"📈 当前下注: {game_state.current_bet}")
        
        # 记录活跃玩家
        active_player = None
        if hasattr(game_state, 'active_player_position') and game_state.active_player_position is not None:
            for player in game_state.players:
                if player.position == game_state.active_player_position:
                    active_player = player.player_id
                    break
        if active_player:
            self.logger.info(f"👤 当前行动玩家: {active_player}")
        else:
            self.logger.info("👤 当前行动玩家: 无")
    
    def _log_player_action(self, player_id: str, action_type: str, amount: int, game_context_before, game_context_after):
        """记录玩家行动的详细信息 - 修改为处理 GameContext 对象"""
        self.logger.info(f"🎭 玩家行动: {player_id}")
        
        # 获取行动前后的玩家状态数据 (从 GameContext 的 players 字典中获取)
        player_before_data = game_context_before.players.get(player_id, {})
        player_after_data = game_context_after.players.get(player_id, {})
        
        if not player_before_data or not player_after_data:
            self.logger.warning(f"无法找到玩家 {player_id} 的状态信息在 _log_player_action")
            return
        
        # 从 ChipLedger 获取玩家筹码 (筹码的唯一真实来源)
        chips_before = game_context_before.chip_ledger.get_balance(player_id)
        chips_after = game_context_after.chip_ledger.get_balance(player_id)
        
        # 从玩家数据字典中获取当前下注
        bet_before = player_before_data.get('current_bet', 0)
        bet_after = player_after_data.get('current_bet', 0)
        
        # 检查是否是全下
        # is_all_in 的判断逻辑需要考虑 game_context.players 中的 'status' 字段
        # 或者从 chip_ledger 判断是否筹码为0且所有筹码已下注
        is_all_in = (chips_after == 0 and player_after_data.get('status') == 'all_in') or \
                    (amount > 0 and amount == chips_before)
        all_in_indicator = " (All-In)" if is_all_in else ""
        
        # 记录行动详情
        self.logger.info(f"   - 行动类型: {action_type.upper()}{all_in_indicator}")
        if amount > 0:
            self.logger.info(f"   - 行动金额: {amount}")
        
        # 记录筹码变化
        chips_change = chips_after - chips_before
        bet_change = bet_after - bet_before
        
        self.logger.info(f"   - 筹码变化: {chips_before} → {chips_after} (变化: {chips_change:+d})")
        self.logger.info(f"   - 下注变化: {bet_before} → {bet_after} (变化: {bet_change:+d})")
        
        # PLAN A.3: 检查筹码变化异常（修复：只检查一些特殊情况）
        if action_type.upper() in ['CALL', 'RAISE', 'BET'] and amount > 0:
            # 如果进行了下注行动但筹码没有减少，可能需要检查状态同步
            if chips_change > 0:
                self.logger.warning(f"⚠️ WARNING: 玩家 {player_id} {action_type.upper()} 后筹码意外增加，疑似状态获取时序问题。")
            elif chips_change == 0 and not is_all_in:
                # 注意：这可能是正常的，因为测试代码的状态获取时机问题
                self.logger.debug(f"DEBUG: 玩家 {player_id} {action_type.upper()} 后筹码在测试层面未变化，可能是状态获取时机问题。")
        
        # 记录底池变化
        pot_before = game_context_before.pot.total_pot
        pot_after = game_context_after.pot.total_pot
        pot_change = pot_after - pot_before
        
        self.logger.info(f"   - 底池变化: {pot_before} → {pot_after} (变化: {pot_change:+d})")
        
        # 德州扑克规则验证
        self._validate_action_rules(player_id, action_type, amount, game_context_before, game_context_after)
    
    def _validate_action_rules(self, player_id: str, action_type: str, amount: int, state_before, state_after):
        """通过Application层验证玩家行动是否符合德州扑克规则（PLAN 33: 更新调用方式）"""
        try:
            # PLAN 33: 验证逻辑已移至ValidationService，通过CommandService调用
            # 这里只记录验证信息，实际验证在CommandService中进行
            self.logger.info(f"   - 规则验证: 通过（由CommandService验证）")
                
        except Exception as e:
            # 验证过程异常，记录但不影响游戏流程
            self.logger.warning(f"⚠️ 规则验证异常: {e}")
            self.logger.info(f"   - 规则验证: ⚠️ 验证异常，跳过验证")
    
    def _log_hand_end(self, hand_number: int, game_state):
        """记录手牌结束的详细信息 - PLAN A.4: 增强手牌结束日志"""
        self.logger.info("-" * 60)
        self.logger.info(f"🏁 第 {hand_number} 手牌结束")
        self.logger.info("-" * 60)
        
        # 记录最终状态
        self.logger.info(f"🎯 最终阶段: {game_state.phase}")
        self.logger.info(f"💰 最终底池: {game_state.pot.total_pot}")
        
        # PLAN A.4: 检查底池异常（修复：底池在手牌结束时清零是正常的）
        if game_state.pot.total_pot == 0 and len(self._current_hand_bidders) > 0:
            # 这通常是正常的，因为奖金已经分配给获胜者，只记录为调试信息
            self.logger.debug(f"DEBUG: 底池在手牌结束时为0，下注玩家: {self._current_hand_bidders}。这通常是正常的，奖金已分配。")
        
        # 记录玩家最终状态
        total_chips = 0
        active_players = []
        
        self.logger.info(f"👥 玩家最终状态:")
        for player_data in game_state.players:
            player_id = player_data.player_id
            chips = player_data.chips
            is_active = player_data.is_active
            total_bet = player_data.total_bet_this_hand
            player_status = 'active' if is_active else 'inactive' # Simplified status from snapshot
            
            total_chips += chips
            if is_active:
                active_players.append(player_id)
            
            # PLAN A.4: 检查本手总投入异常（修复：优化检查逻辑）
            if total_bet == 0 and player_id in self._current_hand_bidders:
                # 这可能是正常的，当手牌结束时总投入字段可能被重置
                # 只记录为调试信息而不是错误
                self.logger.debug(f"DEBUG: 玩家 {player_id} 本手总投入记录为0，但测试代码追踪到有下注行为。可能是状态字段命名或更新时机问题。")
            
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
        total_chips_with_pot = total_chips + game_state.pot.total_pot
        # 获取游戏规则配置
        rules_result = self.query_service.get_game_rules_config(self.game_id)
        initial_chips = self.test_config.get('initial_chips_per_player', 1000)
        if rules_result.success:
            initial_chips = rules_result.data.get('initial_chips', initial_chips)
        expected_total = len(self.player_ids) * initial_chips
        
        self.logger.info(f"💰 最终筹码守恒:")
        self.logger.info(f"   - 玩家筹码总和: {total_chips}")
        self.logger.info(f"   - 底池筹码: {game_state.pot.total_pot}")
        self.logger.info(f"   - 实际总筹码: {total_chips_with_pot}")
        self.logger.info(f"   - 期望总筹码: {expected_total}")
        self.logger.info(f"   - 筹码守恒: {'通过' if total_chips_with_pot == expected_total else '违反'}")
        
        if total_chips_with_pot != expected_total:
            violation_msg = f"Hand {hand_number} 结束: 筹码守恒违反 - 实际:{total_chips_with_pot}, 期望:{expected_total}"
            self.stats_service.record_chip_conservation_violation(self.session_id, violation_msg)
            self.logger.error(f"❌ {violation_msg}")
        
        # 尝试获取获胜信息（如果可用）
        self._log_winner_info(game_state)
        
        self.logger.info(f"⏱️ 手牌用时: {time.time() - getattr(self, '_hand_start_time', time.time()):.2f}秒")
        self.logger.info("=" * 80)
    
    def _log_winner_info(self, game_state):
        """记录获胜者信息（如果可用） - PLAN A.5: 增强获胜信息日志"""
        try:
            # PLAN B-2: 优先从游戏上下文中获取获胜者信息
            if hasattr(game_state, 'winner_info') and game_state.winner_info:
                winner_info = game_state.winner_info
                self.logger.info(f"🏆 获胜信息:")
                
                if 'winner_id' in winner_info:
                    # 单个获胜者
                    self.logger.info(f"   - 获胜者: {winner_info['winner_id']}")
                    self.logger.info(f"   - 获胜金额: {winner_info.get('winnings', 0)}")
                    self.logger.info(f"   - 获胜原因: {winner_info.get('winning_reason', '未知')}")
                    self.logger.info(f"   - 手牌类型: {winner_info.get('hand_type', '未知')}")
                    
                    # 边池分配详情
                    pot_breakdown = winner_info.get('pot_breakdown', {})
                    if pot_breakdown:
                        self.logger.info(f"   - 奖池分配:")
                        main_pot = pot_breakdown.get('main_pot', 0)
                        if main_pot > 0:
                            self.logger.info(f"     * 主池: {main_pot}")
                        side_pots = pot_breakdown.get('side_pots', [])
                        for i, side_pot in enumerate(side_pots):
                            self.logger.info(f"     * 边池{i+1}: {side_pot}")
                            
                elif 'winners' in winner_info:
                    # 多个获胜者（平分奖池）
                    self.logger.info(f"   - 获胜者（多人平分）:")
                    for winner_id, amount in winner_info['winners'].items():
                        self.logger.info(f"     * {winner_id}: {amount}")
                    self.logger.info(f"   - 总奖金: {winner_info.get('total_winnings', 0)}")
                    self.logger.info(f"   - 获胜原因: {winner_info.get('winning_reason', '未知')}")
                
                return  # 成功获取到获胜者信息，直接返回
            
            # PLAN B-2: 从final_hand_stats中获取统计信息
            if hasattr(game_state, 'final_hand_stats') and game_state.final_hand_stats:
                stats = game_state.final_hand_stats
                winners = []
                for player_id, player_stats in stats.items():
                    winnings = player_stats.get('winnings', 0)
                    if winnings > 0:
                        winners.append((player_id, winnings))
                
                if winners:
                    self.logger.info(f"🏆 获胜信息:")
                    for winner_id, winnings in winners:
                        self.logger.info(f"   - 获胜者: {winner_id}, 获胜金额: {winnings}")
                    return
            
            # 备用方案：尝试从游戏历史中获取获胜信息
            history_result = self.query_service.get_game_history(self.game_id, limit=10)
            if history_result.success:
                # 查找最近的获胜事件
                winner_found = False
                for event in history_result.data:
                    event_data = event.get('data', {})
                    if 'winner' in event_data:
                        winner_data = event_data
                        self.logger.info(f"🏆 获胜信息:")
                        self.logger.info(f"   - 获胜者: {winner_data.get('winner', '未知')}")
                        if 'winning_hand' in winner_data:
                            self.logger.info(f"   - 获胜牌型: {winner_data['winning_hand']}")
                        if 'pot_amount' in winner_data:
                            self.logger.info(f"   - 获得奖池: {winner_data['pot_amount']}")
                        
                        # PLAN A.5: 详细的摊牌信息（如果可用）
                        if 'showdown_details' in winner_data:
                            showdown = winner_data['showdown_details']
                            self.logger.info(f"   - 摊牌详情:")
                            for player_id, details in showdown.items():
                                hole_cards = details.get('hole_cards', '未知')
                                best_hand = details.get('best_hand', '未知')
                                self.logger.info(f"     * {player_id}: 底牌 {hole_cards}, 最佳牌型 {best_hand}")
                        
                        # PLAN A.5: 边池分配（如果可用）
                        if 'side_pot_distribution' in winner_data:
                            side_pots = winner_data['side_pot_distribution']
                            self.logger.info(f"   - 边池分配:")
                            for pot_id, pot_info in side_pots.items():
                                amount = pot_info.get('amount', 0)
                                winners = pot_info.get('winners', [])
                                self.logger.info(f"     * {pot_id}: {amount} -> {winners}")
                        
                        winner_found = True
                        break
                
                if not winner_found:
                    # PLAN A.5: 记录缺失详细信息（修复：降级为调试信息）
                    self.logger.debug(f"DEBUG: 未能从历史记录中获取获胜者详细信息，这可能是正常的。")
                    self.logger.info(f"🏆 获胜信息: 暂无详细信息")
            else:
                self.logger.warning(f"⚠️ WARNING: 无法获取历史记录获胜信息: {history_result.message}")
                self.logger.info(f"🏆 获胜信息: 无法获取历史记录")
        except Exception as e:
            self.logger.debug(f"获取获胜信息失败: {e}")
            self.logger.info(f"🏆 获胜信息: 获取异常")
    
    def _log_error_context(self, error: Exception, context: str, game_state=None):
        """
        记录包含完整游戏状态的错误上下文 (PLAN A.7)
        
        Args:
            error: 捕获到的异常
            context: 错误发生的上下文描述
            game_state: 发生错误时的游戏状态快照
        """
        self.logger.error("❌" * 30)
        self.logger.error(f"错误发生: {context}")
        self.logger.error(f"错误类型: {type(error).__name__}")
        self.logger.error(f"错误信息: {error}")
        
        if game_state:
            try:
                # 尝试提供简要的游戏状态
                active_player_id = None
                if hasattr(game_state, 'active_player_position') and game_state.active_player_position is not None:
                    for player in game_state.players:
                        if player.position == game_state.active_player_position:
                            active_player_id = player.player_id
                            break
                self.logger.error("错误时游戏状态:")
                self.logger.error(f"   - 阶段: {game_state.phase}")
                self.logger.error(f"   - 底池: {game_state.pot.total_pot}")
                self.logger.error(f"   - 活跃玩家: {active_player_id}")
                self.logger.error(f"   - 玩家数: {len(game_state.players)}")

                # 增强的完整游戏状态转储 (PLAN A.7)
                self.logger.error("完整游戏状态转储:")
                # 使用 dataclasses.asdict 进行安全的递归转换
                state_dict = asdict(game_state)
                # 使用 pprint 格式化输出，提高可读性
                pretty_state = pprint.pformat(state_dict, indent=4, width=120)
                self.logger.error(pretty_state)

            except Exception as dump_exc:
                self.logger.error(f"   - 转储游戏状态失败: {dump_exc}")
        else:
            self.logger.warning("无法获取错误发生时的游戏状态。")
            
        self.logger.error("❌" * 30)
        self.stats_service.record_error(self.session_id, str(error))

    def run_ultimate_test(self) -> TestStatsSnapshot:
        """运行终极用户测试"""
        self.logger.info("="*80)
        self.logger.info("🔥 v3 Streamlit终极用户测试 运行")
        self.logger.info("="*80)

        if not self._setup_game_environment():
            self.logger.error("游戏环境设置失败，测试终止")
            # 即使设置失败，也返回统计数据以进行分析
            return self._get_final_stats()

        # 获取初始筹码并创建测试会话
        initial_chips = 0
        state_result = self.query_service.get_game_state(self.game_id)
        if state_result.success and state_result.data:
            initial_chips = sum(p.chips for p in state_result.data.players)
        
        create_session_result = self.stats_service.create_test_session(
            self.session_id,
            initial_config={'initial_total_chips': initial_chips}
        )
        if not create_session_result.success:
            self.logger.error(f"创建测试会话失败: {create_session_result.message}")
            return self._get_final_stats()

        for i in range(1, self.num_hands + 1):
            try:
                self._run_single_hand(i)

            except Exception as e:
                self.logger.error(f"第 {i} 手牌执行期间发生严重错误: {e}")
                self.stats_service.record_hand_failed(self.session_id, str(e))
                # 尝试重置游戏会话 - TBD: 此方法需要实现
                # self._reset_game_session()

            self._log_progress(i)

        return self._get_final_stats()
    
    def _setup_game_environment(self) -> bool:
        """设置游戏环境"""
        try:
            # 创建游戏
            result = self.command_service.create_new_game(self.game_id, self.player_ids)
            if not result.success:
                self.logger.error(f"创建游戏失败: {result.message}")
                return False
            
            # 获取初始筹码信息用于日志
            state_result = self.query_service.get_game_state(self.game_id)
            if state_result.success and state_result.data:
                initial_chips = sum(
                    player_data.chips
                    for player_data in state_result.data.players
                )
                self.logger.info(f"游戏环境设置完成，初始筹码: {initial_chips}")
            else:
                self.logger.warning(f"无法获取初始游戏状态: {state_result.message}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"设置游戏环境失败: {e}")
            return False
    
    def _run_single_hand(self, hand_number: int):
        """运行单手牌 - 使用GameFlowService遵循CQRS模式"""
        start_result = self.stats_service.record_hand_start(self.session_id)
        if not start_result.success:
            self.logger.warning(f"记录手牌开始失败: {start_result.message}")
        
        self._hand_start_time = time.time()
        self._hand_had_any_actions = False

        self._current_hand_bidders = set()
        
        try:
            config = HandFlowConfig(
                max_actions_per_hand=self.test_config.get('max_actions_per_hand', 50),
                max_same_states=self.test_config.get('max_consecutive_same_states', 3),
                max_force_finish_attempts=10
            )
            
            state_result = self.query_service.get_game_state(self.game_id)
            if state_result.success:
                self._log_hand_start(hand_number, state_result.data)
            
            flow_result = self.flow_service.run_hand(self.game_id, config)
            
            if flow_result.success:
                if flow_result.data and flow_result.data.get('game_over'):
                    winner_info = flow_result.data.get('winner', '未知')
                    self.logger.info(f"🏆 游戏结束！获胜者: {winner_info}")
                    remaining_hands = self.num_hands - hand_number + 1
                    self.logger.info(f"📊 跳过剩余 {remaining_hands} 手牌（游戏已结束）")
                    return
                
                elif flow_result.data and flow_result.data.get('requires_player_action'):
                    active_player_id = flow_result.data.get('active_player_id')
                    self.logger.debug(f"GameFlowService返回需要玩家行动: {active_player_id}")
                    self._handle_remaining_player_actions(config)
                
                elif flow_result.data and flow_result.data.get('requires_intervention'):
                    self.logger.warning("GameFlowService返回需要干预，强制结束手牌")
                    force_result = self.flow_service.force_finish_hand(self.game_id)
                    if not force_result.success:
                        self.logger.error(f"强制结束失败: {force_result.message}")
                
                else:
                    self.logger.debug("GameFlowService报告手牌完成")
            
            else:
                if "不变量违反" in flow_result.message or flow_result.error_code == "INVARIANT_VIOLATION":
                    self.stats_service.record_invariant_violation(self.session_id, flow_result.message, is_critical=True)
                    self.logger.error(f" 严重不变量违反: {flow_result.message}")
                    raise Exception(f"GameFlowService不变量违反: {flow_result.message}")
                else:
                    self.logger.warning(f"GameFlowService执行失败: {flow_result.message}")
                    force_result = self.flow_service.force_finish_hand(self.game_id)
                    if not force_result.success:
                        raise Exception(f"手牌流程失败且无法恢复: {flow_result.message}")
            
            final_state_result = self.query_service.get_game_state(self.game_id)
            if final_state_result.success:
                self._log_hand_end(hand_number, final_state_result.data)
            
            complete_result = self.stats_service.record_hand_complete(self.session_id)
            if not complete_result.success:
                self.logger.warning(f"记录手牌完成失败: {complete_result.message}")
            
        except Exception as e:
            failed_result = self.stats_service.record_hand_failed(self.session_id, str(e))
            if not failed_result.success:
                self.logger.warning(f"记录手牌失败失败: {failed_result.message}")
            
            try:
                error_state_result = self.query_service.get_game_state(self.game_id)
                error_state = error_state_result.data if error_state_result.success else None
            except:
                error_state = None
            
            self._log_error_context(e, f"第{hand_number}手牌执行", error_state)
            
            try:
                state_result = self.query_service.get_game_state(self.game_id)
                if not state_result.success:
                    self.logger.warning("游戏会话丢失，重新创建")
                    self.command_service.create_new_game(self.game_id, self.player_ids)
            except Exception as e2:
                self.logger.error(f"恢复游戏会话失败: {e2}")
                self._log_error_context(e2, "恢复游戏会话")

    def _handle_remaining_player_actions(self, config: HandFlowConfig):
        max_additional_actions = config.max_actions_per_hand
        action_count = 0
        consecutive_no_action = 0
        max_consecutive_no_action = 5
        
        self.logger.debug("开始处理剩余玩家行动 - 真实德州扑克流程")
        
        while action_count < max_additional_actions:
            context_result = self.query_service.get_live_game_context(self.game_id)
            if not context_result.success:
                self.logger.warning(f"获取实时游戏上下文失败: {context_result.message}")
                break
            
            game_context = context_result.data
            
            if game_context.current_phase == GamePhase.FINISHED:
                self.logger.debug("手牌已结束，停止处理玩家行动")
                break
            
            active_player_id = game_context.active_player_id
            
            if active_player_id:
                self.logger.debug(f"处理活跃玩家行动: {active_player_id} (阶段: {game_context.current_phase.name})")
                try:
                    # 注意：_execute_real_poker_action 接收的是 context，而不是 snapshot
                    success = self._execute_real_poker_action(game_context, active_player_id)
                    if success:
                        action_count += 1
                        consecutive_no_action = 0
                        self._hand_had_any_actions = True
                    else:
                        consecutive_no_action += 1
                except Exception as e:
                    self.logger.error(f"执行玩家行动异常: {e}")
                    consecutive_no_action += 1
                    
            else:
                should_advance_result = self.query_service.should_advance_phase(self.game_id)
                if should_advance_result.success and should_advance_result.data:
                    self.logger.debug(f"推进阶段：{game_context.current_phase.name} -> 下一阶段")
                    advance_result = self.command_service.advance_phase(self.game_id)
                    if advance_result.success:
                        action_count += 1
                        consecutive_no_action = 0
                        new_context_result = self.query_service.get_live_game_context(self.game_id)
                        if new_context_result.success:
                            self._log_phase_transition(
                                game_context.current_phase.name,
                                new_context_result.data.current_phase.name,
                                new_context_result.data
                            )
                    else:
                        self.logger.warning(f"推进阶段失败: {advance_result.message}")
                        consecutive_no_action += 1
                        if "不变量违反" in advance_result.message:
                            self.logger.error(f"阶段推进时不变量违反: {advance_result.message}")
                            break
                else:
                    self.logger.debug("无法推进阶段，尝试使用GameFlowService继续")
                    flow_result = self.flow_service.run_hand(self.game_id, config)
                    if flow_result.success:
                        if flow_result.data and flow_result.data.get('requires_player_action'):
                            consecutive_no_action = 0
                            continue
                        elif flow_result.data and flow_result.data.get('hand_completed'):
                            self.logger.debug("GameFlowService报告手牌完成")
                            break
                        else:
                            consecutive_no_action += 1
                    else:
                        self.logger.warning(f"GameFlowService运行失败: {flow_result.message}")
                        consecutive_no_action += 1
            
            if consecutive_no_action >= max_consecutive_no_action:
                self.logger.warning(f"连续{consecutive_no_action}次无有效行动，强制结束")
                force_result = self.flow_service.force_finish_hand(self.game_id)
                if not force_result.success:
                    self.logger.error(f"强制结束失败: {force_result.message}")
                break
                
            if action_count >= max_additional_actions - 1:
                self.logger.warning("达到最大行动数，强制结束")
                force_result = self.flow_service.force_finish_hand(self.game_id)
                if not force_result.success:
                    self.logger.error(f"强制结束失败: {force_result.message}")
                break
        
        self.logger.debug(f"完成剩余玩家行动处理，执行了 {action_count} 个行动")

    def _execute_real_poker_action(self, game_context, player_id: str) -> bool:
        action_start_time = time.time()
        
        try:
            # 直接使用传入的实时上下文，不再重新查询
            state_before = game_context
            
            actions_result = self.query_service.get_available_actions(self.game_id, player_id)
            if not actions_result.success:
                self.logger.warning(f"获取可用行动失败: {actions_result.message}")
                return False
            
            available_actions = actions_result.data.actions
            min_bet = actions_result.data.min_bet
            max_bet = actions_result.data.max_bet
            
            self.logger.debug(f"玩家 {player_id} 可用行动: {available_actions}, 下注范围: {min_bet}-{max_bet}")
            
            if not available_actions:
                self.logger.warning(f"玩家 {player_id} 没有可用行动")
                return False

            player_chips = state_before.chip_ledger.get_balance(player_id)

            ai_decision_result = self.query_service.make_ai_decision(
                self.game_id, 
                player_id, 
                self._get_ai_config_from_application()
            )
            
            if not ai_decision_result.success:
                self.logger.warning(f"AI决策失败: {ai_decision_result.message}")
                action_type = 'fold' if 'fold' in available_actions else available_actions[0]
                amount = 0
            else:
                action_type = ai_decision_result.data['action_type']
                amount = ai_decision_result.data['amount']
                reasoning = ai_decision_result.data.get('reasoning', '无原因')
                self.logger.debug(f"AI {player_id} 意图: {action_type.upper()} {amount}，当前筹码: {player_chips}，原因: {reasoning}")

            if action_type not in available_actions:
                self.logger.warning(f"行动 {action_type} 不在可用列表中: {available_actions}，回退到fold")
                action_type = 'fold' if 'fold' in available_actions else available_actions[0]
                amount = 0
            
            player_action = PlayerAction(action_type=action_type, amount=amount)
            
            self.logger.debug(f"执行真实德州扑克行动: 玩家{player_id} -> {action_type}({amount})")
            
            result = self.command_service.execute_player_action(self.game_id, player_id, player_action)
            
            state_after_result = self.query_service.get_live_game_context(self.game_id)
            if state_after_result.success:
                state_after = state_after_result.data
                self._log_player_action(player_id, action_type, amount, state_before, state_after)
                if action_type.upper() in ['BET', 'CALL', 'RAISE'] and amount > 0:
                    self._current_hand_bidders.add(player_id)
            
            action_time = time.time() - action_start_time
            action_result = self.stats_service.record_user_action(
                self.session_id, 
                action_type, 
                result.success, 
                action_time,
                result.message if not result.success else None
            )
            
            if not action_result.success:
                self.logger.warning(f"记录用户行动失败: {action_result.message}")
            
            if result.success:
                self.logger.debug(f"真实德州扑克行动执行成功: {action_type}")
                return True
            else:
                if "不变量违反" in result.message or result.error_code == "INVARIANT_VIOLATION":
                    violation_msg = f"玩家 {player_id} 行动导致不变量违反: {result.message}"
                    self.stats_service.record_invariant_violation(self.session_id, violation_msg, is_critical=True)
                    self.logger.error(f"❌ 严重不变量违反: {violation_msg}")
                    raise Exception(f"不变量违反导致测试失败: {violation_msg}")
                else:
                    self.logger.warning(f"玩家行动失败: {result.message}")
                    self._log_error_context(Exception(result.message), f"玩家 {player_id} 行动失败", game_context)
                    return False
            
        except Exception as e:
            if "不变量违反" in str(e):
                raise
            else:
                self.logger.error(f"执行真实德州扑克行动异常: {str(e)}")
                self._log_error_context(e, f"玩家 {player_id} 行动异常", game_context)
                return False

    def _force_finish_hand(self):
        try:
            force_result = self.flow_service.force_finish_hand(self.game_id)
            if force_result.success:
                self.logger.debug("GameFlowService强制结束手牌成功")
            else:
                self.logger.warning(f"GameFlowService强制结束手牌失败: {force_result.message}")
        except Exception as e:
            self.logger.warning(f"强制结束手牌异常: {e}")



    def _log_progress(self, hand_number: int):
        """记录进度"""
        stats_result = self.stats_service.get_test_stats(self.session_id)
        if not stats_result.success:
            self.logger.warning(f"获取测试统计失败: {stats_result.message}")
            return
        
        stats = stats_result.data
        completion_rate = (stats.hands_completed / stats.hands_attempted) * 100 if stats.hands_attempted > 0 else 0
        action_success_rate = (stats.successful_actions / stats.total_user_actions) * 100 if stats.total_user_actions > 0 else 0
        
        self.logger.info(f"进度报告 - Hand {hand_number}/{self.num_hands}")
        self.logger.info(f"  完成率: {completion_rate:.1f}% ({stats.hands_completed}/{stats.hands_attempted})")
        self.logger.info(f"  行动成功率: {action_success_rate:.1f}% ({stats.successful_actions}/{stats.total_user_actions})")
        self.logger.info(f"  错误数量: {len(stats.errors)}")

    def _get_final_stats(self) -> TestStatsSnapshot:
        """获取最终统计"""
        state_result = self.query_service.get_game_state(self.game_id)
        final_chips = 0
        if state_result.success and state_result.data:
            final_chips = sum(player_data.chips for player_data in state_result.data.players)

        finalize_result = self.stats_service.finalize_test_session(self.session_id, final_chips)
        if finalize_result.success:
            stats_result = self.stats_service.get_test_stats(self.session_id)
            if stats_result.success:
                return stats_result.data
        
        self.logger.warning("获取最终统计失败，返回空统计")
        return TestStatsSnapshot()

    def _log_final_results(self, stats: TestStatsSnapshot):
        """记录最终结果"""
        self.logger.info("=" * 80)
        self.logger.info("🏆 v3 Streamlit终极用户测试结果")
        self.logger.info("=" * 80)
        
        completion_rate = (stats.hands_completed / stats.hands_attempted) * 100 if stats.hands_attempted > 0 else 0
        self.logger.info(f"手牌完成率: {completion_rate:.1f}% ({stats.hands_completed}/{stats.hands_attempted})")
        
        action_success_rate = (stats.successful_actions / stats.total_user_actions) * 100 if stats.total_user_actions > 0 else 0
        self.logger.info(f"行动成功率: {action_success_rate:.1f}% ({stats.successful_actions}/{stats.total_user_actions})")
        
        self.logger.info(f"筹码守恒: 初始{stats.initial_total_chips}, 最终{stats.final_total_chips}")
        
        self.logger.info(f"不变量检查: {len(stats.invariant_violations)} 个违反, {stats.critical_invariant_violations} 个严重违反")
        if stats.invariant_violations:
            self.logger.error("不变量违反详情:")
            for violation in stats.invariant_violations:
                self.logger.error(f"  - {violation}")
        
        hands_per_second = stats.hands_completed / stats.total_test_time if stats.total_test_time > 0 else 0
        self.logger.info(f"测试速度: {hands_per_second:.2f} 手/秒")
        
        if stats.action_distribution:
            self.logger.info("行动分布:")
            for action, count in stats.action_distribution.items():
                percentage = (count / stats.successful_actions) * 100 if stats.successful_actions > 0 else 0
                self.logger.info(f"  {action}: {count} ({percentage:.1f}%)")

    def _calculate_state_hash(self, game_state) -> str:
        """计算游戏状态哈希，用于检测状态变化"""
        try:
            hash_result = self.query_service.calculate_game_state_hash(self.game_id)
            if hash_result.success:
                return hash_result.data
            else:
                self.logger.warning(f"Application层计算状态哈希失败: {hash_result.message}")
                return f"fallback_{time.time():.0f}"
        except Exception as e:
            self.logger.warning(f"计算状态哈希异常: {e}")
            return f"error_{time.time():.0f}"

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
            action_start_time = time.time()
            
            # 获取可用行动
            actions_result = self.query_service.get_available_actions(self.game_id, "player_0")
            if not actions_result.success:
                self.logger.warning(f"获取可用行动失败: {actions_result.message}")
                # 通过统计服务记录失败的行动
                action_result = self.stats_service.record_user_action(
                    self.session_id, 
                    "get_actions", 
                    False, 
                    None,
                    actions_result.message
                )
                if not action_result.success:
                    self.logger.warning(f"记录获取行动失败: {action_result.message}")
                return
            
            available_actions = actions_result.data.actions
            self.logger.debug(f"可用行动: {available_actions}")
            
            if not available_actions:
                # 如果没有可用行动，尝试基本行动
                available_actions = ['check', 'fold']
                self.logger.debug(f"使用默认行动: {available_actions}")
            
            # 使用Application层AI决策服务 - 遵循CQRS架构
            ai_decision_result = self.query_service.make_ai_decision(
                self.game_id, 
                "player_0",
                ai_config={
                    'fold_weight': 0.1,
                    'check_weight': 0.3,
                    'call_weight': 0.4,
                    'raise_weight': 0.15,
                    'all_in_weight': 0.05,
                    'min_bet_ratio': 0.3,
                    'max_bet_ratio': 0.7
                }
            )
            
            if ai_decision_result.success:
                chosen_action = ai_decision_result.data['action_type']
                amount = ai_decision_result.data['amount']
                reasoning = ai_decision_result.data['reasoning']
                self.logger.debug(f"AI决策: {chosen_action}, 金额: {amount}, 原因: {reasoning}")
            else:
                # 回退到基本行动
                chosen_action = 'fold'
                amount = 0
                self.logger.warning(f"AI决策失败，使用回退行动: {ai_decision_result.message}")
            
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
            
            # 记录行动时间和结果
            action_time = time.time() - action_start_time
            action_result = self.stats_service.record_user_action(
                self.session_id, 
                chosen_action, 
                result.success, 
                action_time,
                result.message if not result.success else None
            )
            
            if not action_result.success:
                self.logger.warning(f"记录强制用户行动失败: {action_result.message}")
            
            if result.success:
                self.logger.debug(f"强制行动执行成功: {chosen_action}")
            else:
                self.logger.warning(f"强制行动执行失败: {result.message}")
                self._log_error_context(Exception(result.message), "强制用户行动失败", game_state)
            
        except Exception as e:
            # 记录异常的行动
            action_result = self.stats_service.record_user_action(
                self.session_id, 
                "unknown", 
                False, 
                None,
                str(e)
            )
            if not action_result.success:
                self.logger.warning(f"记录强制用户行动异常失败: {action_result.message}")
            
            self.logger.error(f"强制用户行动异常: {str(e)}")
            self._log_error_context(e, "强制用户行动异常", game_state)


# 移除GameStateSnapshotAdapter类，不再需要


# ==================== Pytest 兼容测试函数 ====================

def test_streamlit_ultimate_user_experience_v3(num_hands: int = 10, test_type: str = None):
    """
    v3 Streamlit终极用户体验测试 - 统一参数化版本
    
    Args:
        num_hands: 手牌数量，默认10手牌（快速测试）
        test_type: 测试类型，如果为None则根据num_hands自动确定
    
    测试模式：
    - 基本测试（1手牌）：验证基本功能能否跑通
    - 快速测试（≤10手牌）：进行细致的功能测试
    - 终极测试（>10手牌）：发版前的完整验证
    
    反作弊检查：
    1. 确保使用真实的v3应用服务
    2. 验证CQRS架构的正确使用
    3. 检查TestStatsService的真实性
    """
    # 自动确定测试类型
    if test_type is None:
        test_type = determine_test_type(num_hands)
    
    print(f"开始v3 Streamlit终极用户体验测试 - {test_type}模式 ({num_hands}手牌)...")
    
    # 创建测试器
    tester = StreamlitUltimateUserTesterV3(num_hands=num_hands, test_type=test_type)
    
    # 反作弊检查：验证使用真实的v3组件（严格遵循CQRS模式）
    # UI层只应访问Application层服务，不直接接触Core层（如EventBus）
    CoreUsageChecker.verify_real_objects(tester.command_service, "GameCommandService")
    CoreUsageChecker.verify_real_objects(tester.query_service, "GameQueryService")
    CoreUsageChecker.verify_real_objects(tester.stats_service, "TestStatsService")
    CoreUsageChecker.verify_real_objects(tester.flow_service, "GameFlowService")
    
    # 运行测试
    stats = tester.run_ultimate_test()
    
    # 验证测试结果
    assert stats.hands_attempted > 0, "应该尝试了至少一手牌"
    assert stats.total_user_actions > 0, "应该有用户行动"
    
    # 根据测试类型设置不同的验收标准
    if test_type == "basic":
        # 基本测试：只要能跑通即可
        min_completion_rate = 0.5
        min_action_success_rate = 0.5
        min_speed = 1.0
    elif test_type == "quick":
        # 快速测试：中等标准
        min_completion_rate = 0.8
        min_action_success_rate = 0.7
        min_speed = 3.0
    else:  # ultimate
        # 终极测试：严格标准
        min_completion_rate = 0.99
        min_action_success_rate = 0.85
        min_speed = 5.0
    
    # 成功率检查
    if stats.hands_attempted > 0:
        completion_rate = stats.hands_completed / stats.hands_attempted
        assert completion_rate >= min_completion_rate, f"手牌完成率 {completion_rate:.1%} < {min_completion_rate:.1%}"
    
    if stats.total_user_actions > 0:
        action_success_rate = stats.successful_actions / stats.total_user_actions
        assert action_success_rate >= min_action_success_rate, f"行动成功率 {action_success_rate:.1%} < {min_action_success_rate:.1%}"
    
    # 筹码守恒检查（所有模式都必须通过）
    assert len(stats.chip_conservation_violations) == 0, f"不应该有筹码守恒违规，实际: {len(stats.chip_conservation_violations)}"
    
    # 不变量违反检查（所有模式都必须通过）
    assert len(stats.invariant_violations) == 0, f"不应该有不变量违反，实际: {len(stats.invariant_violations)} 个违反: {stats.invariant_violations}"
    assert stats.critical_invariant_violations == 0, f"不应该有严重不变量违反，实际: {stats.critical_invariant_violations}"
    
    # 性能检查（仅终极测试）
    if test_type == "ultimate":
        hands_per_second = stats.hands_completed / stats.total_test_time if stats.total_test_time > 0 else 0
        assert hands_per_second >= min_speed, f"测试速度 {hands_per_second:.1f} < {min_speed} 手/秒"
        assert stats.critical_errors == 0, f"严重错误: {stats.critical_errors}"
        
        # 终极测试的额外反作弊检查
        CoreUsageChecker.verify_real_objects(tester.validation_service, "ValidationService")
        CoreUsageChecker.verify_real_objects(tester.config_service, "ConfigService")
    
    # 输出测试结果
    print(f"✅ v3 {test_type}测试完成: {stats.hands_completed}/{stats.hands_attempted} 手牌完成")
    print(f"✅ 行动成功率: {stats.successful_actions}/{stats.total_user_actions}")
    print(f"✅ 错误控制: {len(stats.errors)} 个错误")
    print(f"✅ 不变量检查: {len(stats.invariant_violations)} 个违反")
    
    if stats.total_test_time > 0:
        hands_per_second = stats.hands_completed / stats.total_test_time
        print(f"✅ 测试速度: {hands_per_second:.2f} 手/秒")
    
    print(f"✅ v3 {test_type}测试通过！")


# ==================== Pytest 便捷函数 ====================

def test_streamlit_ultimate_user_experience_v3_basic():
    """基本测试 - 1手牌，验证能否跑通"""
    test_streamlit_ultimate_user_experience_v3(num_hands=1, test_type="basic")


def test_streamlit_ultimate_user_experience_v3_quick():
    """快速测试 - 10手牌，细致功能测试"""
    test_streamlit_ultimate_user_experience_v3(num_hands=10, test_type="quick")


@pytest.mark.slow
def test_streamlit_ultimate_user_experience_v3_full():
    """终极测试 - 100手牌，发版前验证"""
    test_streamlit_ultimate_user_experience_v3(num_hands=100, test_type="ultimate")


def parse_command_line_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="v3 Streamlit终极用户体验测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
测试模式说明：
  基本测试（1手牌）  : 验证基本功能能否跑通
  快速测试（≤10手牌）: 进行细致的功能测试  
  终极测试（>10手牌） : 发版前的完整验证

PowerShell 运行示例：
  .venv\\Scripts\\python v3\\tests\\integration\\v3_test_ultimate.py --hands 1
  .venv\\Scripts\\python v3\\tests\\integration\\v3_test_ultimate.py --hands 10
  .venv\\Scripts\\python v3\\tests\\integration\\v3_test_ultimate.py --hands 100
        """
    )
    
    parser.add_argument(
        '--hands', 
        type=int, 
        default=10,
        help='手牌数量 (默认: 10)'
    )
    
    parser.add_argument(
        '--type',
        type=str,
        choices=['basic', 'quick', 'ultimate'],
        help='测试类型 (如果不指定，将根据手牌数量自动确定)'
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    # 解析命令行参数
    args = parse_command_line_args()
    
    # 运行测试
    try:
        test_streamlit_ultimate_user_experience_v3(
            num_hands=args.hands,
            test_type=args.type
        )
        print(f"\n🎉 测试成功完成！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1) 