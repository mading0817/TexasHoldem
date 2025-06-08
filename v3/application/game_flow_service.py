#!/usr/bin/env python3
"""
GameFlowService - 游戏流程服务

负责管理游戏手牌的完整流程，包括：
- 运行完整手牌流程
- 强制结束手牌
- 状态循环检测
- 异常恢复

严格遵循CQRS模式，UI层通过此服务控制游戏流程。
"""

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .types import CommandResult, QueryResult
from .command_service import GameCommandService
from v3.core.events import EventBus
from v3.core.state_machine.types import GamePhase


@dataclass
class HandFlowConfig:
    """手牌流程配置"""
    max_actions_per_hand: int = 50
    max_same_states: int = 3
    max_force_finish_attempts: int = 10


class GameFlowService:
    """
    游戏流程服务
    
    负责控制游戏手牌的完整生命周期，从UI层抽离出的业务流程逻辑。
    """
    
    def __init__(self, command_service: GameCommandService,
                 event_bus: Optional[EventBus] = None):
        """
        初始化游戏流程服务
        
        Args:
            command_service: 命令服务
            event_bus: 事件总线（可选）
        """
        self.command_service = command_service
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
    def run_hand(self, game_id: str, config: Optional[HandFlowConfig] = None) -> CommandResult:
        """
        运行完整的手牌流程
        
        Args:
            game_id: 游戏ID
            config: 流程配置
            
        Returns:
            命令执行结果
        """
        if config is None:
            config = HandFlowConfig()
            
        try:
            # 检查并重置游戏状态（如果需要）
            reset_result = self._ensure_proper_state(game_id)
            if not reset_result.success:
                return reset_result
            
            # 开始新手牌
            start_result = self.command_service.start_new_hand(game_id)
            if not start_result.success:
                # 如果开始失败（例如，因为游戏结束），直接返回结果
                return CommandResult.failure_result(
                    f"开始新手牌失败: {start_result.message}",
                    error_code=start_result.error_code or "START_HAND_FAILED"
                )
            
            # 执行手牌流程
            flow_result = self._execute_hand_flow(game_id, config)
            if not flow_result.success:
                return flow_result
            
            # 检查是否需要玩家行动
            if flow_result.data and flow_result.data.get('requires_player_action', False):
                # 需要玩家行动，直接返回结果，不要强制结束手牌
                return flow_result
            
            # 只有在不需要玩家行动时，才确保手牌正确结束
            finish_result = self._ensure_hand_finished(game_id)
            if not finish_result.success:
                return finish_result
                
            return CommandResult.success_result(
                "手牌完成",
                data={'hand_completed': True}
            )
            
        except Exception as e:
            self.logger.error(f"运行手牌流程异常: {e}", exc_info=True)
            return CommandResult.failure_result(
                f"手牌流程异常: {str(e)}",
                error_code="HAND_FLOW_EXCEPTION"
            )
    
    def force_finish_hand(self, game_id: str, max_attempts: int = 10) -> CommandResult:
        """
        强制结束当前手牌
        
        Args:
            game_id: 游戏ID
            max_attempts: 最大尝试次数
            
        Returns:
            命令执行结果
        """
        try:
            attempts = 0
            
            while attempts < max_attempts:
                # 获取当前状态
                context_result = self.command_service.get_live_context(game_id)
                if not context_result.success:
                    return CommandResult.failure_result(
                        f"获取游戏状态失败: {context_result.message}",
                        error_code="GET_STATE_FAILED"
                    )
                
                # 检查是否已经结束
                if context_result.data.current_phase == GamePhase.FINISHED:
                    return CommandResult.success_result(
                        f"强制结束完成，用了{attempts}次尝试",
                        data={'attempts': attempts, 'final_phase': 'FINISHED'}
                    )
                
                # 尝试推进阶段
                advance_result = self.command_service.advance_phase(game_id)
                if not advance_result.success:
                    # 如果是不变量违反，立即返回错误
                    if "不变量违反" in advance_result.message or advance_result.error_code == "INVARIANT_VIOLATION":
                        return CommandResult.failure_result(
                            f"强制结束失败-不变量违反: {advance_result.message}",
                            error_code="INVARIANT_VIOLATION"
                        )
                    # 其他错误继续尝试
                    self.logger.warning(f"推进阶段失败，尝试{attempts+1}: {advance_result.message}")
                
                attempts += 1
            
            # 达到最大尝试次数
            return CommandResult.failure_result(
                f"达到最大尝试次数({max_attempts})，无法强制结束手牌",
                error_code="MAX_ATTEMPTS_EXCEEDED"
            )
            
        except Exception as e:
            self.logger.error(f"强制结束手牌异常: {e}", exc_info=True)
            return CommandResult.failure_result(
                f"强制结束异常: {str(e)}",
                error_code="FORCE_FINISH_EXCEPTION"
            )
    
    def advance_until_finished(self, game_id: str, max_attempts: int = 10) -> CommandResult:
        """
        推进阶段直到手牌结束
        
        Args:
            game_id: 游戏ID
            max_attempts: 最大尝试次数
            
        Returns:
            命令执行结果
        """
        return self.force_finish_hand(game_id, max_attempts)
    
    def _ensure_proper_state(self, game_id: str) -> CommandResult:
        """确保游戏处于正确状态，如果需要则重置"""
        try:
            context_result = self.command_service.get_live_context(game_id)
            if not context_result.success:
                return CommandResult.failure_result(
                    f"获取游戏状态失败: {context_result.message}",
                    error_code="GET_STATE_FAILED"
                )
            
            game_context = context_result.data
            current_phase = game_context.current_phase
            if current_phase not in [GamePhase.INIT, GamePhase.FINISHED]:
                self.logger.debug(f"当前阶段 {current_phase.name} 需要重置，强制结束当前手牌")
                # 强制结束当前手牌
                force_result = self.force_finish_hand(game_id)
                if not force_result.success:
                    return CommandResult.failure_result(
                        f"重置游戏状态失败: {force_result.message}",
                        error_code="RESET_STATE_FAILED"
                    )
            
            return CommandResult.success_result("游戏状态正常")
            
        except Exception as e:
            self.logger.error(f"确保游戏状态异常: {e}", exc_info=True)
            return CommandResult.failure_result(
                f"确保游戏状态异常: {str(e)}",
                error_code="ENSURE_STATE_EXCEPTION"
            )
    
    def _execute_hand_flow(self, game_id: str, config: HandFlowConfig) -> CommandResult:
        """执行手牌主流程"""
        action_count = 0
        previous_state_hash = None
        consecutive_same_states = 0
        
        while action_count < config.max_actions_per_hand:
            # 获取当前游戏状态
            context_result = self.command_service.get_live_context(game_id)
            if not context_result.success:
                return CommandResult.failure_result(
                    f"获取游戏状态失败: {context_result.message}",
                    error_code="GET_STATE_FAILED"
                )
            
            game_context = context_result.data
            
            # 检查手牌是否结束
            if game_context.current_phase == GamePhase.FINISHED:
                return CommandResult.success_result("手牌流程完成")
            
            # 检测状态循环
            hash_result = self.command_service.calculate_live_hash(game_id)
            if not hash_result.success:
                self.logger.warning(f"无法计算状态哈希: {hash_result.message}")
            else:
                current_hash = hash_result.data
                if current_hash == previous_state_hash:
                    consecutive_same_states += 1
                    if consecutive_same_states >= config.max_same_states:
                        self.logger.warning(f"检测到状态循环，强制结束手牌。哈希: {current_hash}")
                        return self.force_finish_hand(game_id)
                else:
                    consecutive_same_states = 0
                previous_state_hash = current_hash
            
            action_count += 1
            
            # 检查是否需要玩家行动
            players_to_act = self.command_service._find_players_needing_action(game_context)
            if players_to_act:
                return CommandResult.success_result(
                    f"等待玩家 {players_to_act} 行动",
                    data={'requires_player_action': True, 'players_to_act': players_to_act}
                )

            # 如果没有玩家需要行动，检查是否应该自动推进阶段
            should_advance_result = self.command_service.should_advance_phase_query(game_id)
            if should_advance_result.success and should_advance_result.data.get('should_advance'):
                self.logger.debug(
                    f"自动推进阶段 from {game_context.current_phase.name}, "
                    f"原因: {should_advance_result.data.get('reason')}"
                )
                advance_result = self.command_service.advance_phase(game_id)
                if not advance_result.success:
                    return CommandResult.failure_result(
                        f"自动推进阶段失败: {advance_result.message}",
                        error_code="AUTO_ADVANCE_FAILED"
                    )
                # 推进阶段后继续循环
                continue
            
            # 如果不能自动推进，记录一个警告并中断流程
            # 这可能表示一个意外的游戏状态，例如，没有玩家行动，但阶段也无法推进
            self.logger.warning(
                f"手牌流程在阶段 {game_context.current_phase.name} 中断。 "
                f"没有玩家需要行动，且无法自动推进阶段。"
                f"推进检查信息: {should_advance_result.message}"
            )
            return CommandResult.failure_result(
                f"手牌流程在阶段 {game_context.current_phase.name} 中断",
                error_code="HAND_FLOW_STALLED"
            )
            
        return CommandResult.failure_result(
            f"手牌操作超过最大限制 ({config.max_actions_per_hand})",
            error_code="MAX_ACTIONS_EXCEEDED"
        )
        
    def _ensure_hand_finished(self, game_id: str) -> CommandResult:
        """确保手牌在流程结束后处于 FINISHED 状态"""
        try:
            context_result = self.command_service.get_live_context(game_id)
            if not context_result.success:
                return CommandResult.failure_result("无法在收尾阶段获取游戏状态")
            
            current_phase = context_result.data.current_phase
            if current_phase != GamePhase.FINISHED:
                self.logger.warning(
                    f"手牌流程结束，但最终阶段是 {current_phase.name} 而不是 FINISHED, "
                    f"尝试强制结束手牌。"
                )
                return self.force_finish_hand(game_id)
            
            return CommandResult.success_result("手牌已在 FINISHED 状态")
            
        except Exception as e:
            self.logger.error(f"确保手牌结束时异常: {e}", exc_info=True)
            return CommandResult.failure_result(
                f"确保手牌结束时异常: {str(e)}",
                error_code="ENSURE_FINISH_EXCEPTION"
            ) 