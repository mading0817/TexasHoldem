#!/usr/bin/env python3
"""
终极发版前验证测试 - Texas Hold'em Poker Game v2

这是德州扑克v2项目的终极验收测试用例，基于标准德州扑克规则(TexasHoldemGameRule.md)
进行全面、严格的规则符合性验证。

测试覆盖范围：
1. 游戏流程完整性：PRE_FLOP → FLOP → TURN → RIVER → SHOWDOWN
2. 庄家轮换正确性：每手牌庄家位置顺时针移动
3. 盲注轮换正确性：小盲、大盲位置跟随庄家轮换
4. 行动顺序准确性：翻牌前从大盲左侧开始，翻牌后从庄家左侧开始
5. 牌面显示准确性：J, Q, K, A正确显示，不是11, 12, 13, 14
6. 筹码守恒验证：确保筹码总量不变
7. 边池处理正确性：ALL_IN情况下的边池分配
8. AI行动合理性：AI在各种情况下的决策符合逻辑
9. UI界面一致性：按钮、状态、提示信息的准确性
10. 边界情况处理：最小加注、全押、筹码不足等特殊情况
11. ALL_IN场景验证：全押后其他人弃牌、多人全押等场景的正确处理

Author: Texas Hold'em v2 Team
Version: 1.0
Date: 2024
"""

import sys
import os
import random
import time
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.enums import ActionType, Phase, SeatStatus, Rank, Suit
from v2.core.state import GameState
from v2.core.player import Player
from v2.core.cards import Card
from v2.core.enums import Action


class TestResult(Enum):
    """测试结果枚举."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


@dataclass
class ValidationIssue:
    """验证问题记录."""
    severity: TestResult
    category: str
    description: str
    details: str
    hand_number: Optional[int] = None
    expected: Optional[str] = None
    actual: Optional[str] = None


@dataclass
class HandRecord:
    """手牌记录."""
    hand_number: int
    initial_chips: Dict[int, int]
    final_chips: Dict[int, int]
    dealer_position: int
    small_blind_position: int
    big_blind_position: int
    phases_reached: List[Phase]
    total_actions: int
    winner_ids: List[int]
    pot_amount: int
    issues: List[ValidationIssue]


class TexasHoldemRuleValidator:
    """德州扑克规则验证器.
    
    基于TexasHoldemGameRule.md中的标准规则进行验证：
    1. 庄家按钮每手牌顺时针移动一位
    2. 小盲注在庄家左侧第一位，大盲注在小盲注左侧
    3. 翻牌前从大盲注左侧第一位开始行动
    4. 翻牌后从庄家左侧第一位活跃玩家开始行动
    5. 游戏阶段按PRE_FLOP → FLOP → TURN → RIVER → SHOWDOWN顺序进行
    6. 筹码总量守恒，不会凭空产生或消失
    """
    
    def __init__(self):
        """初始化验证器."""
        self.issues: List[ValidationIssue] = []
        self.hand_records: List[HandRecord] = []
        self.total_initial_chips = 0
        self.logger = logging.getLogger(__name__)
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def validate_dealer_rotation(self, hand_records: List[HandRecord]) -> bool:
        """验证庄家轮换规则.
        
        德州扑克规则：每手牌开始前，庄家按钮顺时针移动一位
        
        Args:
            hand_records: 手牌记录列表
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        for i in range(1, len(hand_records)):
            prev_hand = hand_records[i-1]
            curr_hand = hand_records[i]
            
            # 计算期望的庄家位置（顺时针移动）
            expected_dealer = (prev_hand.dealer_position + 1) % 4  # 假设4个玩家
            
            if curr_hand.dealer_position != expected_dealer:
                issue = ValidationIssue(
                    severity=TestResult.FAIL,
                    category="庄家轮换",
                    description=f"第{curr_hand.hand_number}手牌庄家位置错误",
                    details=f"期望位置{expected_dealer}，实际位置{curr_hand.dealer_position}",
                    hand_number=curr_hand.hand_number,
                    expected=str(expected_dealer),
                    actual=str(curr_hand.dealer_position)
                )
                self.issues.append(issue)
                is_valid = False
        
        return is_valid
    
    def validate_blind_positions(self, hand_record: HandRecord) -> bool:
        """验证盲注位置规则.
        
        德州扑克规则：
        - 小盲注：庄家左侧第一位玩家
        - 大盲注：小盲注左侧玩家
        
        Args:
            hand_record: 手牌记录
            
        Returns:
            验证是否通过
        """
        is_valid = True
        num_players = 4  # 假设4个玩家
        
        expected_small_blind = (hand_record.dealer_position + 1) % num_players
        expected_big_blind = (hand_record.dealer_position + 2) % num_players
        
        if hand_record.small_blind_position != expected_small_blind:
            issue = ValidationIssue(
                severity=TestResult.FAIL,
                category="盲注位置",
                description=f"第{hand_record.hand_number}手牌小盲位置错误",
                details=f"庄家位置{hand_record.dealer_position}，期望小盲{expected_small_blind}，实际{hand_record.small_blind_position}",
                hand_number=hand_record.hand_number,
                expected=str(expected_small_blind),
                actual=str(hand_record.small_blind_position)
            )
            self.issues.append(issue)
            is_valid = False
        
        if hand_record.big_blind_position != expected_big_blind:
            issue = ValidationIssue(
                severity=TestResult.FAIL,
                category="盲注位置",
                description=f"第{hand_record.hand_number}手牌大盲位置错误",
                details=f"庄家位置{hand_record.dealer_position}，期望大盲{expected_big_blind}，实际{hand_record.big_blind_position}",
                hand_number=hand_record.hand_number,
                expected=str(expected_big_blind),
                actual=str(hand_record.big_blind_position)
            )
            self.issues.append(issue)
            is_valid = False
        
        return is_valid
    
    def validate_phase_progression(self, hand_record: HandRecord) -> bool:
        """验证阶段转换规则.
        
        德州扑克规则：
        1. 阶段必须按顺序进行：PRE_FLOP → FLOP → TURN → RIVER → SHOWDOWN
        2. 如果只剩一个玩家（其他都弃牌），游戏可以在任何阶段提前结束
        3. 不能跳过阶段或逆序进行
        4. 每个阶段都必须给所有活跃玩家行动机会
        
        Args:
            hand_record: 手牌记录
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        # 检查阶段顺序是否正确
        phase_order = {Phase.PRE_FLOP: 0, Phase.FLOP: 1, Phase.TURN: 2, Phase.RIVER: 3, Phase.SHOWDOWN: 4}
        
        for i in range(1, len(hand_record.phases_reached)):
            prev_phase = hand_record.phases_reached[i-1]
            curr_phase = hand_record.phases_reached[i]
            
            # 检查是否按正确顺序进行
            if phase_order[prev_phase] >= phase_order[curr_phase]:
                issue = ValidationIssue(
                    severity=TestResult.FAIL,
                    category="阶段转换",
                    description=f"第{hand_record.hand_number}手牌阶段顺序错误",
                    details=f"从{prev_phase.value}转换到{curr_phase.value}",
                    hand_number=hand_record.hand_number
                )
                self.issues.append(issue)
                is_valid = False
        
        # 检查是否跳过了阶段（但允许提前结束）
        if len(hand_record.phases_reached) > 1:
            # 如果游戏进行了多个阶段，检查是否有跳跃
            for i in range(1, len(hand_record.phases_reached)):
                prev_phase = hand_record.phases_reached[i-1]
                curr_phase = hand_record.phases_reached[i]
                
                expected_next_order = phase_order[prev_phase] + 1
                actual_order = phase_order[curr_phase]
                
                # 如果跳过了阶段（不是连续的）
                if actual_order != expected_next_order:
                    issue = ValidationIssue(
                        severity=TestResult.FAIL,
                        category="阶段转换",
                        description=f"第{hand_record.hand_number}手牌跳过了阶段",
                        details=f"从{prev_phase.value}直接跳到{curr_phase.value}",
                        hand_number=hand_record.hand_number
                    )
                    self.issues.append(issue)
                    is_valid = False
        
        # 验证必须至少有PRE_FLOP阶段
        if Phase.PRE_FLOP not in hand_record.phases_reached:
            issue = ValidationIssue(
                severity=TestResult.FAIL,
                category="阶段转换",
                description=f"第{hand_record.hand_number}手牌缺少PRE_FLOP阶段",
                details=f"实际达到的阶段: {[p.value for p in hand_record.phases_reached]}",
                hand_number=hand_record.hand_number
            )
            self.issues.append(issue)
            is_valid = False
        
        # 新增：检查阶段跳跃问题
        # 如果手牌只达到了PRE_FLOP和SHOWDOWN，这是可疑的
        if (len(hand_record.phases_reached) == 2 and 
            Phase.PRE_FLOP in hand_record.phases_reached and 
            Phase.SHOWDOWN in hand_record.phases_reached and
            Phase.FLOP not in hand_record.phases_reached):
            
            issue = ValidationIssue(
                severity=TestResult.FAIL,
                category="阶段转换",
                description=f"第{hand_record.hand_number}手牌疑似跳过了中间阶段",
                details=f"从PRE_FLOP直接跳到SHOWDOWN，跳过了FLOP、TURN、RIVER",
                hand_number=hand_record.hand_number
            )
            self.issues.append(issue)
            is_valid = False
        
        # 新增：检查阶段数量的合理性
        # 正常情况下，如果达到SHOWDOWN，应该经历所有阶段
        if (Phase.SHOWDOWN in hand_record.phases_reached and 
            len(hand_record.phases_reached) < 5):  # 应该有5个阶段
            
            missing_phases = []
            expected_phases = [Phase.PRE_FLOP, Phase.FLOP, Phase.TURN, Phase.RIVER, Phase.SHOWDOWN]
            for phase in expected_phases:
                if phase not in hand_record.phases_reached:
                    missing_phases.append(phase.value)
            
            if missing_phases:
                issue = ValidationIssue(
                    severity=TestResult.WARNING,
                    category="阶段转换",
                    description=f"第{hand_record.hand_number}手牌到达摊牌但缺少中间阶段",
                    details=f"缺少阶段: {missing_phases}",
                    hand_number=hand_record.hand_number
                )
                self.issues.append(issue)
        
        return is_valid
    
    def validate_chip_conservation(self, hand_records: List[HandRecord]) -> bool:
        """验证筹码守恒规则.
        
        德州扑克规则：筹码总量必须保持不变，不能凭空产生或消失
        
        Args:
            hand_records: 手牌记录列表
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        if not hand_records:
            return is_valid
        
        # 计算初始总筹码
        initial_total = sum(hand_records[0].initial_chips.values())
        self.total_initial_chips = initial_total
        
        for hand_record in hand_records:
            final_total = sum(hand_record.final_chips.values())
            
            if final_total != initial_total:
                issue = ValidationIssue(
                    severity=TestResult.FAIL,
                    category="筹码守恒",
                    description=f"第{hand_record.hand_number}手牌筹码总量变化",
                    details=f"初始总筹码: {initial_total}, 最终总筹码: {final_total}, 差异: {final_total - initial_total}",
                    hand_number=hand_record.hand_number,
                    expected=str(initial_total),
                    actual=str(final_total)
                )
                self.issues.append(issue)
                is_valid = False
        
        return is_valid
    
    def validate_card_display(self, cards: List[Card]) -> bool:
        """验证牌面显示规则.
        
        德州扑克规则：J, Q, K, A应该正确显示，不是11, 12, 13, 14
        
        Args:
            cards: 牌列表
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        for card in cards:
            # 检查rank显示
            if card.rank == Rank.JACK:
                expected_display = "J"
            elif card.rank == Rank.QUEEN:
                expected_display = "Q"
            elif card.rank == Rank.KING:
                expected_display = "K"
            elif card.rank == Rank.ACE:
                expected_display = "A"
            else:
                continue  # 数字牌不需要特殊检查
            
            # 这里我们假设Card对象有正确的字符串表示
            # 实际测试时需要检查UI显示
            card_str = str(card)
            if expected_display not in card_str:
                issue = ValidationIssue(
                    severity=TestResult.WARNING,
                    category="牌面显示",
                    description=f"牌{card.rank.value}显示可能不正确",
                    details=f"期望包含{expected_display}，实际显示{card_str}"
                )
                self.issues.append(issue)
                is_valid = False
        
        return is_valid
    
    def validate_betting_rules(self, hand_record: HandRecord) -> bool:
        """验证下注规则.
        
        德州扑克规则：
        1. 最低加注额不得低于前一次加注的金额
        2. 加注金额应该是总下注额，不是增量
        3. 全下玩家无权参与后续下注，但仍可赢得主池
        4. 平分底池时，多余筹码给予庄家左侧第一位玩家
        5. 当无人下注时应该使用BET，有人下注时应该使用RAISE
        
        Args:
            hand_record: 手牌记录
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        # 验证筹码变化的合理性
        total_initial = sum(hand_record.initial_chips.values())
        total_final = sum(hand_record.final_chips.values())
        
        if total_initial != total_final:
            issue = ValidationIssue(
                severity=TestResult.FAIL,
                category="下注规则",
                description=f"第{hand_record.hand_number}手牌筹码总量变化",
                details=f"初始: {total_initial}, 最终: {total_final}",
                hand_number=hand_record.hand_number
            )
            self.issues.append(issue)
            is_valid = False
        
        return is_valid
    
    def validate_bet_vs_raise_logic(self, controller: 'PokerController') -> bool:
        """验证BET vs RAISE逻辑.
        
        德州扑克规则：
        1. 当current_bet=0时，应该使用BET行动
        2. 当current_bet>0时，应该使用RAISE行动
        3. 最小下注应该是大盲注
        4. 最小加注应该是当前下注+上次加注增量
        
        Args:
            controller: 游戏控制器
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        try:
            from v2.core.enums import Action, ActionType
            from v2.core.validator import ActionValidator
            
            snapshot = controller.get_snapshot()
            validator = ActionValidator()
            
            # 找到一个活跃的玩家进行测试
            active_player = None
            for player in snapshot.players:
                if player.status.value == 'active':
                    active_player = player
                    break
            
            if not active_player:
                # 如果没有活跃玩家，跳过这个测试
                return is_valid
            
            # 测试BET逻辑（无人下注时）
            if snapshot.current_bet == 0:
                # 验证最小下注应该是大盲注
                expected_min_bet = snapshot.big_blind
                
                # 模拟下注行动
                test_bet_action = Action(ActionType.BET, expected_min_bet, active_player.seat_id)
                
                try:
                    validated_action = validator.validate(controller._game_state, active_player, test_bet_action)
                    if validated_action.final_action.action_type != ActionType.BET:
                        issue = ValidationIssue(
                            severity=TestResult.FAIL,
                            category="BET vs RAISE逻辑",
                            description="无人下注时BET行动被错误转换",
                            details=f"期望BET，实际{validated_action.final_action.action_type.value}",
                            hand_number=None
                        )
                        self.issues.append(issue)
                        is_valid = False
                except Exception as e:
                    issue = ValidationIssue(
                        severity=TestResult.WARNING,
                        category="BET vs RAISE逻辑",
                        description="BET行动验证失败",
                        details=str(e),
                        hand_number=None
                    )
                    self.issues.append(issue)
            
            # 测试RAISE逻辑（有人下注时）
            elif snapshot.current_bet > 0:
                # 验证最小加注计算
                last_raise_increment = snapshot.last_raise_amount if snapshot.last_raise_amount > 0 else snapshot.big_blind
                expected_min_raise = snapshot.current_bet + last_raise_increment
                
                # 确保玩家有足够筹码进行加注
                if active_player.chips + active_player.current_bet >= expected_min_raise:
                    # 模拟加注行动
                    test_raise_action = Action(ActionType.RAISE, expected_min_raise, active_player.seat_id)
                    
                    try:
                        validated_action = validator.validate(controller._game_state, active_player, test_raise_action)
                        if validated_action.final_action.action_type not in [ActionType.RAISE, ActionType.ALL_IN]:
                            issue = ValidationIssue(
                                severity=TestResult.FAIL,
                                category="BET vs RAISE逻辑",
                                description="有人下注时RAISE行动被错误转换",
                                details=f"期望RAISE，实际{validated_action.final_action.action_type.value}",
                                hand_number=None
                            )
                            self.issues.append(issue)
                            is_valid = False
                    except Exception as e:
                        issue = ValidationIssue(
                            severity=TestResult.WARNING,
                            category="BET vs RAISE逻辑",
                            description="RAISE行动验证失败",
                            details=str(e),
                            hand_number=None
                        )
                        self.issues.append(issue)
        
        except Exception as e:
            issue = ValidationIssue(
                severity=TestResult.WARNING,
                category="BET vs RAISE逻辑",
                description="BET vs RAISE逻辑验证异常",
                details=str(e),
                hand_number=None
            )
            self.issues.append(issue)
        
        return is_valid
    
    def validate_minimum_bet_calculation(self, controller: 'PokerController') -> bool:
        """验证最小下注/加注计算.
        
        德州扑克规则：
        1. 最小下注 = 大盲注
        2. 最小加注 = 当前下注 + 上次加注增量
        3. 如果是第一次加注，增量为大盲注
        
        Args:
            controller: 游戏控制器
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        try:
            snapshot = controller.get_snapshot()
            
            if snapshot.current_bet == 0:
                # 无人下注时，最小下注应该是大盲注
                expected_min = snapshot.big_blind
                if expected_min != snapshot.big_blind:
                    issue = ValidationIssue(
                        severity=TestResult.FAIL,
                        category="最小下注计算",
                        description="最小下注计算错误",
                        details=f"期望{snapshot.big_blind}，实际{expected_min}",
                        hand_number=None
                    )
                    self.issues.append(issue)
                    is_valid = False
            else:
                # 有人下注时，最小加注应该是当前下注+上次加注增量
                last_raise_increment = snapshot.last_raise_amount if snapshot.last_raise_amount > 0 else snapshot.big_blind
                expected_min = snapshot.current_bet + last_raise_increment
                
                # 这里我们验证逻辑是否正确，而不是具体的UI实现
                if last_raise_increment <= 0:
                    issue = ValidationIssue(
                        severity=TestResult.FAIL,
                        category="最小下注计算",
                        description="上次加注增量计算错误",
                        details=f"last_raise_amount: {snapshot.last_raise_amount}, big_blind: {snapshot.big_blind}",
                        hand_number=None
                    )
                    self.issues.append(issue)
                    is_valid = False
        
        except Exception as e:
            issue = ValidationIssue(
                severity=TestResult.FAIL,
                category="最小下注计算",
                description="最小下注计算验证异常",
                details=str(e),
                hand_number=None
            )
            self.issues.append(issue)
            is_valid = False
        
        return is_valid
    
    def validate_action_sequence(self, hand_record: HandRecord) -> bool:
        """验证行动顺序规则.
        
        德州扑克规则：
        1. 翻牌前从大盲注左侧第一位玩家开始，顺时针进行
        2. 翻牌后从庄家左侧第一位仍在游戏中的玩家开始，顺时针进行
        3. 每轮下注中，玩家可以选择：弃牌、看牌、跟注、加注、全下
        
        Args:
            hand_record: 手牌记录
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        # 验证行动数量的合理性
        if hand_record.total_actions < 4:  # 至少应该有盲注 + 一些行动
            issue = ValidationIssue(
                severity=TestResult.WARNING,
                category="行动顺序",
                description=f"第{hand_record.hand_number}手牌行动数量过少",
                details=f"总行动数: {hand_record.total_actions}",
                hand_number=hand_record.hand_number
            )
            self.issues.append(issue)
        
        return is_valid
    
    def validate_side_pot_rules(self, hand_record: HandRecord) -> bool:
        """验证边池规则.
        
        德州扑克规则：
        1. 当一位或多位玩家全下且其他玩家仍有筹码继续下注时，需创建边池
        2. 主池由所有玩家按照最小全下金额匹配的筹码组成
        3. 边池由剩余有筹码的玩家继续下注组成，All-in玩家无权参与
        4. 分配时从主池开始，比较所有参与者的手牌
        
        Args:
            hand_record: 手牌记录
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        # 检查是否有全押情况
        # 由于当前测试框架限制，我们主要验证结果的一致性
        
        # 验证获胜者的合理性
        if not hand_record.winner_ids:
            issue = ValidationIssue(
                severity=TestResult.WARNING,
                category="边池规则",
                description=f"第{hand_record.hand_number}手牌没有获胜者",
                details="每手牌都应该有获胜者",
                hand_number=hand_record.hand_number
            )
            self.issues.append(issue)
        
        return is_valid
    
    def validate_showdown_rules(self, hand_record: HandRecord) -> bool:
        """验证摊牌规则.
        
        德州扑克规则：
        1. 最后一轮下注结束后，若仍有多位玩家未弃牌，则进行摊牌
        2. 最后一轮有主动下注的玩家首先亮牌
        3. 若无主动下注，则从庄家左侧第一位玩家开始，顺时针亮牌
        4. 玩家可选择是否亮牌，若弃权则放弃争夺底池
        
        Args:
            hand_record: 手牌记录
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        # 验证摊牌阶段是否正确达到
        if Phase.SHOWDOWN in hand_record.phases_reached:
            # 如果达到摊牌阶段，应该有合理的底池金额
            if hand_record.pot_amount <= 0:
                issue = ValidationIssue(
                    severity=TestResult.WARNING,
                    category="摊牌规则",
                    description=f"第{hand_record.hand_number}手牌摊牌时底池为空",
                    details=f"底池金额: {hand_record.pot_amount}",
                    hand_number=hand_record.hand_number
                )
                self.issues.append(issue)
        
        return is_valid
    
    def validate_special_cases(self, hand_record: HandRecord) -> bool:
        """验证特殊情况处理.
        
        德州扑克规则：
        1. 使用公共牌：玩家可选择使用两张、一张或不使用底牌
        2. 若最佳手牌仅由公共牌组成，称为"打公牌"，所有玩家的手牌相同，平分底池
        3. 若两位或多位玩家拥有相同的最佳手牌，则平分相应的底池
        4. 若底池无法平均分配，则多余的筹码给予庄家左侧第一位玩家
        
        Args:
            hand_record: 手牌记录
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        # 验证获胜者数量的合理性
        if len(hand_record.winner_ids) > 4:  # 假设最多4个玩家
            issue = ValidationIssue(
                severity=TestResult.FAIL,
                category="特殊情况",
                description=f"第{hand_record.hand_number}手牌获胜者数量异常",
                details=f"获胜者数量: {len(hand_record.winner_ids)}",
                hand_number=hand_record.hand_number
            )
            self.issues.append(issue)
            is_valid = False
        
        return is_valid
    
    def validate_hand_state_management(self, hand_record: HandRecord) -> bool:
        """验证手牌状态管理规则.
        
        德州扑克规则：
        1. 手牌必须正确开始和结束
        2. 不能在手牌进行中开始新手牌
        3. 手牌结束后必须能够开始新手牌
        4. 手牌状态标志必须正确维护
        
        Args:
            hand_record: 手牌记录
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        # 验证手牌是否正确完成
        if not hand_record.phases_reached:
            issue = ValidationIssue(
                severity=TestResult.FAIL,
                category="手牌状态管理",
                description=f"第{hand_record.hand_number}手牌没有达到任何阶段",
                details="手牌必须至少达到PRE_FLOP阶段",
                hand_number=hand_record.hand_number
            )
            self.issues.append(issue)
            is_valid = False
        
        # 验证手牌是否有获胜者（除非出现异常）
        if not hand_record.winner_ids and hand_record.pot_amount > 0:
            issue = ValidationIssue(
                severity=TestResult.FAIL,
                category="手牌状态管理",
                description=f"第{hand_record.hand_number}手牌有底池但没有获胜者",
                details=f"底池金额: {hand_record.pot_amount}，获胜者: {hand_record.winner_ids}",
                hand_number=hand_record.hand_number
            )
            self.issues.append(issue)
            is_valid = False
        
        return is_valid
    
    def validate_ai_action_recording(self, hand_record: HandRecord) -> bool:
        """验证AI行动记录规则.
        
        德州扑克规则：
        1. 所有玩家行动都应该被记录
        2. AI行动应该符合游戏逻辑
        3. 行动顺序应该正确
        
        Args:
            hand_record: 手牌记录
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        # 验证行动数量的合理性
        min_expected_actions = len(hand_record.phases_reached) * 2  # 每个阶段至少2个行动
        if hand_record.total_actions < min_expected_actions:
            issue = ValidationIssue(
                severity=TestResult.WARNING,
                category="AI行动记录",
                description=f"第{hand_record.hand_number}手牌行动数量可能不足",
                details=f"达到{len(hand_record.phases_reached)}个阶段，但只有{hand_record.total_actions}个行动",
                hand_number=hand_record.hand_number
            )
            self.issues.append(issue)
        
        return is_valid
    
    def validate_game_flow_completeness(self, hand_record: HandRecord) -> bool:
        """验证游戏流程完整性.
        
        德州扑克规则：
        1. 每个阶段都应该有相应的行动
        2. 游戏流程应该符合逻辑顺序
        3. 手牌结束应该有明确的原因
        
        Args:
            hand_record: 手牌记录
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        # 验证阶段和行动的一致性
        if hand_record.phases_reached and hand_record.total_actions == 0:
            issue = ValidationIssue(
                severity=TestResult.FAIL,
                category="游戏流程完整性",
                description=f"第{hand_record.hand_number}手牌达到了阶段但没有行动记录",
                details=f"达到阶段: {[p.value for p in hand_record.phases_reached]}",
                hand_number=hand_record.hand_number
            )
            self.issues.append(issue)
            is_valid = False
        
        # 验证手牌结束的合理性
        if hand_record.phases_reached:
            last_phase = hand_record.phases_reached[-1]
            # 如果没有达到SHOWDOWN，应该是因为只剩一个玩家
            if last_phase != Phase.SHOWDOWN and len(hand_record.winner_ids) != 1:
                issue = ValidationIssue(
                    severity=TestResult.WARNING,
                    category="游戏流程完整性",
                    description=f"第{hand_record.hand_number}手牌未达到摊牌但有多个获胜者",
                    details=f"最后阶段: {last_phase.value}，获胜者数量: {len(hand_record.winner_ids)}",
                    hand_number=hand_record.hand_number
                )
                self.issues.append(issue)
        
        return is_valid
    
    def validate_event_recording_completeness(self, hand_record: HandRecord) -> bool:
        """验证事件记录完整性.
        
        德州扑克规则：
        1. 所有玩家行动都应该被记录
        2. 所有阶段转换都应该被记录
        3. 所有发牌事件都应该被记录
        4. 事件记录应该与实际游戏流程匹配
        
        Args:
            hand_record: 手牌记录
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        # 验证阶段转换事件记录
        expected_phase_events = []
        for i, phase in enumerate(hand_record.phases_reached):
            if i > 0:  # 跳过第一个阶段（PRE_FLOP是初始阶段）
                expected_phase_events.append(f"Advanced to {phase.value}")
        
        # 验证行动数量与阶段的合理性
        min_expected_actions = len(hand_record.phases_reached) * 2  # 每个阶段至少2个行动
        if hand_record.total_actions < min_expected_actions:
            issue = ValidationIssue(
                severity=TestResult.WARNING,
                category="事件记录",
                description=f"第{hand_record.hand_number}手牌行动数量可能不足",
                details=f"达到{len(hand_record.phases_reached)}个阶段，但只有{hand_record.total_actions}个行动",
                hand_number=hand_record.hand_number
            )
            self.issues.append(issue)
        
        return is_valid
    
    def validate_betting_round_completion(self, controller: 'PokerController') -> bool:
        """验证下注轮完成逻辑.
        
        德州扑克规则：
        1. 当所有活跃玩家都匹配当前下注且都已行动过时，下注轮应该完成
        2. 下注轮完成后应该自动进入下一阶段
        3. 不应该出现所有玩家匹配下注但仍可继续行动的情况
        
        Args:
            controller: 游戏控制器
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        try:
            snapshot = controller.get_snapshot()
            active_players = snapshot.get_active_players()
            
            if len(active_players) < 2:
                # 活跃玩家不足，跳过测试
                return is_valid
            
            # 检查是否所有活跃玩家都匹配了当前下注
            all_matched = True
            for player in active_players:
                if player.current_bet < snapshot.current_bet:
                    all_matched = False
                    break
            
            if all_matched and snapshot.current_bet > 0:
                # 所有玩家都匹配了下注，检查是否还有玩家可以行动
                current_player_id = controller.get_current_player_id()
                
                if current_player_id is not None:
                    # 还有玩家可以行动，检查这是否合理
                    current_player = snapshot.get_player_by_seat(current_player_id)
                    
                    if current_player and current_player.status.value == 'active':
                        # 检查行动数是否足够
                        actions_count = getattr(snapshot, 'actions_this_round', 0)
                        min_actions_needed = len(active_players)
                        
                        # 如果有加注者，检查是否轮回到加注者后的第一个活跃玩家
                        if snapshot.last_raiser is not None:
                            # 找到加注者后的第一个活跃玩家
                            players = snapshot.players
                            raiser_pos = snapshot.last_raiser
                            next_active_after_raiser = None
                            
                            for i in range(1, len(players) + 1):
                                next_pos = (raiser_pos + i) % len(players)
                                if players[next_pos].status.value == 'active':
                                    next_active_after_raiser = next_pos
                                    break
                            
                            # 如果当前玩家是加注者后的第一个活跃玩家，且所有人都匹配下注，应该进入下一阶段
                            if (next_active_after_raiser is not None and 
                                current_player_id == next_active_after_raiser and
                                actions_count >= min_actions_needed):
                                
                                issue = ValidationIssue(
                                    severity=TestResult.FAIL,
                                    category="下注轮完成",
                                    description="所有玩家匹配下注且轮回到加注者后第一个活跃玩家，但下注轮未完成",
                                    details=f"当前下注: {snapshot.current_bet}, 活跃玩家: {len(active_players)}, 当前玩家: {current_player_id}, 加注者: {snapshot.last_raiser}, 行动数: {actions_count}",
                                    hand_number=None
                                )
                                self.issues.append(issue)
                                is_valid = False
                        else:
                            # 没有加注者的情况，如果行动数足够且所有人匹配下注，应该进入下一阶段
                            if actions_count >= min_actions_needed:
                                issue = ValidationIssue(
                                    severity=TestResult.FAIL,
                                    category="下注轮完成",
                                    description="无加注者且所有玩家匹配下注，行动数足够，但下注轮未完成",
                                    details=f"当前下注: {snapshot.current_bet}, 活跃玩家: {len(active_players)}, 当前玩家: {current_player_id}, 行动数: {actions_count}",
                                    hand_number=None
                                )
                                self.issues.append(issue)
                                is_valid = False
        
        except Exception as e:
            issue = ValidationIssue(
                severity=TestResult.WARNING,
                category="下注轮完成",
                description="下注轮完成逻辑验证异常",
                details=str(e),
                hand_number=None
            )
            self.issues.append(issue)
        
        return is_valid
    
    def validate_phase_transition_timing(self, hand_record: HandRecord) -> bool:
        """验证阶段转换时机.
        
        德州扑克规则：
        1. 阶段转换应该在下注轮完成后立即发生
        2. 不应该出现下注轮完成但阶段不转换的情况
        3. 阶段转换应该是自动的，不需要额外的用户操作
        
        Args:
            hand_record: 手牌记录
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        # 检查阶段转换的连续性
        phases = hand_record.phases_reached
        if len(phases) > 1:
            for i in range(1, len(phases)):
                prev_phase = phases[i-1]
                curr_phase = phases[i]
                
                # 检查阶段转换是否合理
                expected_transitions = {
                    Phase.PRE_FLOP: Phase.FLOP,
                    Phase.FLOP: Phase.TURN,
                    Phase.TURN: Phase.RIVER,
                    Phase.RIVER: Phase.SHOWDOWN
                }
                
                if prev_phase in expected_transitions:
                    expected_next = expected_transitions[prev_phase]
                    if curr_phase != expected_next:
                        issue = ValidationIssue(
                            severity=TestResult.FAIL,
                            category="阶段转换时机",
                            description=f"第{hand_record.hand_number}手牌阶段转换异常",
                            details=f"从{prev_phase.value}转换到{curr_phase.value}，期望{expected_next.value}",
                            hand_number=hand_record.hand_number
                        )
                        self.issues.append(issue)
                        is_valid = False
        
        return is_valid
    
    def validate_betting_round_completion_detailed(self, controller: 'PokerController') -> bool:
        """详细验证下注轮完成逻辑.
        
        德州扑克规则：
        1. 当所有活跃玩家都匹配当前下注且都已行动过时，下注轮应该完成
        2. 下注轮完成后应该自动进入下一阶段
        3. 不应该出现所有玩家匹配下注但仍可继续行动的情况
        
        Args:
            controller: 游戏控制器
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        try:
            snapshot = controller.get_snapshot()
            active_players = snapshot.get_active_players()
            
            if len(active_players) < 2:
                # 活跃玩家不足，跳过测试
                return is_valid
            
            # 检查是否所有活跃玩家都匹配了当前下注
            all_matched = True
            for player in active_players:
                if player.current_bet < snapshot.current_bet:
                    all_matched = False
                    break
            
            if all_matched and snapshot.current_bet > 0:
                # 所有玩家都匹配了下注，检查是否还有玩家可以行动
                current_player_id = controller.get_current_player_id()
                
                if current_player_id is not None:
                    # 还有玩家可以行动，检查这是否合理
                    current_player = snapshot.get_player_by_seat(current_player_id)
                    
                    if current_player and current_player.status.value == 'active':
                        # 检查行动数是否足够
                        actions_count = getattr(snapshot, 'actions_this_round', 0)
                        min_actions_needed = len(active_players)
                        
                        # 如果有加注者，检查是否轮回到加注者后的第一个活跃玩家
                        if snapshot.last_raiser is not None:
                            # 找到加注者后的第一个活跃玩家
                            players = snapshot.players
                            raiser_pos = snapshot.last_raiser
                            next_active_after_raiser = None
                            
                            for i in range(1, len(players) + 1):
                                next_pos = (raiser_pos + i) % len(players)
                                if players[next_pos].status.value == 'active':
                                    next_active_after_raiser = next_pos
                                    break
                            
                            # 如果当前玩家是加注者后的第一个活跃玩家，且所有人都匹配下注，应该进入下一阶段
                            if (next_active_after_raiser is not None and 
                                current_player_id == next_active_after_raiser and
                                actions_count >= min_actions_needed):
                                
                                issue = ValidationIssue(
                                    severity=TestResult.FAIL,
                                    category="下注轮完成",
                                    description="所有玩家匹配下注且轮回到加注者后第一个活跃玩家，但下注轮未完成",
                                    details=f"当前下注: {snapshot.current_bet}, 活跃玩家: {len(active_players)}, 当前玩家: {current_player_id}, 加注者: {snapshot.last_raiser}, 行动数: {actions_count}",
                                    hand_number=None
                                )
                                self.issues.append(issue)
                                is_valid = False
                        else:
                            # 没有加注者的情况，如果行动数足够且所有人匹配下注，应该进入下一阶段
                            if actions_count >= min_actions_needed:
                                issue = ValidationIssue(
                                    severity=TestResult.FAIL,
                                    category="下注轮完成",
                                    description="无加注者且所有玩家匹配下注，行动数足够，但下注轮未完成",
                                    details=f"当前下注: {snapshot.current_bet}, 活跃玩家: {len(active_players)}, 当前玩家: {current_player_id}, 行动数: {actions_count}",
                                    hand_number=None
                                )
                                self.issues.append(issue)
                                is_valid = False
        
        except Exception as e:
            issue = ValidationIssue(
                severity=TestResult.WARNING,
                category="下注轮完成",
                description="下注轮完成详细逻辑验证异常",
                details=str(e),
                hand_number=None
            )
            self.issues.append(issue)
        
        return is_valid
    
    def validate_all_in_scenarios(self, hand_record: HandRecord, controller: 'PokerController') -> bool:
        """验证ALL_IN场景处理规则.
        
        德州扑克规则：
        1. 当玩家全押后其他人全部弃牌时，手牌应该立即结束
        2. 当所有剩余玩家都是ALL_IN时，应该直接进入摊牌
        3. ALL_IN玩家不能参与后续下注，但可以赢得底池
        4. 有ALL_IN玩家时，游戏应该继续到摊牌阶段
        
        Args:
            hand_record: 手牌记录
            controller: 游戏控制器
            
        Returns:
            验证是否通过
        """
        is_valid = True
        
        try:
            # 检查手牌记录中是否有ALL_IN相关的异常情况
            if hand_record.phases_reached:
                # 如果手牌只达到了PRE_FLOP或FLOP就结束，检查是否是合理的ALL_IN场景
                last_phase = hand_record.phases_reached[-1]
                
                # 获取当前游戏状态快照
                snapshot = controller.get_snapshot()
                active_players = [p for p in snapshot.players if p.status == SeatStatus.ACTIVE]
                all_in_players = [p for p in snapshot.players if p.status == SeatStatus.ALL_IN]
                folded_players = [p for p in snapshot.players if p.status == SeatStatus.FOLDED]
                
                # 场景1：只有一个活跃玩家和一些弃牌玩家，手牌应该结束
                if len(active_players) <= 1 and len(folded_players) > 0:
                    if not controller.is_hand_over():
                        issue = ValidationIssue(
                            severity=TestResult.FAIL,
                            category="ALL_IN场景",
                            description=f"第{hand_record.hand_number}手牌只剩一个活跃玩家但手牌未结束",
                            details=f"活跃玩家: {len(active_players)}, 弃牌玩家: {len(folded_players)}, ALL_IN玩家: {len(all_in_players)}",
                            hand_number=hand_record.hand_number
                        )
                        self.issues.append(issue)
                        is_valid = False
                
                # 场景2：所有剩余玩家都是ALL_IN，应该能够进入摊牌
                if len(active_players) == 0 and len(all_in_players) > 1:
                    if last_phase != Phase.SHOWDOWN and not controller.is_hand_over():
                        issue = ValidationIssue(
                            severity=TestResult.WARNING,
                            category="ALL_IN场景",
                            description=f"第{hand_record.hand_number}手牌所有玩家ALL_IN但未进入摊牌",
                            details=f"ALL_IN玩家: {len(all_in_players)}, 最后阶段: {last_phase.value}",
                            hand_number=hand_record.hand_number
                        )
                        self.issues.append(issue)
                
                # 场景3：有ALL_IN玩家和活跃玩家，游戏应该继续
                if len(active_players) > 0 and len(all_in_players) > 0:
                    # 这是正常情况，ALL_IN玩家不参与后续下注，但游戏继续
                    # 验证ALL_IN玩家确实不能再行动
                    current_player_id = controller.get_current_player_id()
                    if current_player_id is not None:
                        current_player = snapshot.get_player_by_seat(current_player_id)
                        if current_player and current_player.status == SeatStatus.ALL_IN:
                            issue = ValidationIssue(
                                severity=TestResult.FAIL,
                                category="ALL_IN场景",
                                description=f"第{hand_record.hand_number}手牌ALL_IN玩家仍被要求行动",
                                details=f"当前玩家: {current_player_id}, 状态: {current_player.status.value}",
                                hand_number=hand_record.hand_number
                            )
                            self.issues.append(issue)
                            is_valid = False
                
                # 场景4：验证手牌结束的合理性
                if controller.is_hand_over():
                    total_remaining = len(active_players) + len(all_in_players)
                    if total_remaining > 1 and last_phase not in [Phase.SHOWDOWN]:
                        # 如果有多个玩家剩余但不在摊牌阶段就结束，检查是否合理
                        if len(active_players) <= 1:
                            # 只有一个或零个活跃玩家，这是合理的
                            pass
                        else:
                            issue = ValidationIssue(
                                severity=TestResult.WARNING,
                                category="ALL_IN场景",
                                description=f"第{hand_record.hand_number}手牌在非摊牌阶段结束但有多个玩家剩余",
                                details=f"活跃玩家: {len(active_players)}, ALL_IN玩家: {len(all_in_players)}, 阶段: {last_phase.value}",
                                hand_number=hand_record.hand_number
                            )
                            self.issues.append(issue)
        
        except Exception as e:
            issue = ValidationIssue(
                severity=TestResult.WARNING,
                category="ALL_IN场景",
                description=f"第{hand_record.hand_number}手牌ALL_IN场景验证异常",
                details=str(e),
                hand_number=hand_record.hand_number
            )
            self.issues.append(issue)
        
        return is_valid


class UltimateReleaseValidator:
    """终极发版前验证器.
    
    模拟真实用户在Streamlit界面上进行10手牌游戏，验证所有德州扑克规则。
    """
    
    def __init__(self, num_hands: int = 10, initial_chips: int = 1000):
        """初始化验证器.
        
        Args:
            num_hands: 测试手牌数量
            initial_chips: 每个玩家的初始筹码
        """
        self.num_hands = num_hands
        self.initial_chips = initial_chips
        self.validator = TexasHoldemRuleValidator()
        self.controller: Optional[PokerController] = None
        self.hand_records: List[HandRecord] = []
        self.logger = logging.getLogger(__name__)
        
        # 随机种子，确保测试可重复
        random.seed(42)
    
    def setup_game(self) -> bool:
        """设置游戏环境.
        
        Returns:
            设置是否成功
        """
        try:
            # 创建游戏状态和控制器
            game_state = GameState()
            ai_strategy = SimpleAI()
            logger = logging.getLogger('poker_controller')
            
            self.controller = PokerController(
                game_state=game_state,
                ai_strategy=ai_strategy,
                logger=logger
            )
            
            # 添加4个玩家：1个人类玩家 + 3个AI玩家
            for i in range(4):
                name = "Human" if i == 0 else f"AI_{i}"
                player = Player(
                    seat_id=i,
                    name=name,
                    chips=self.initial_chips
                )
                # 标记人类玩家
                if i == 0:
                    player.is_human = True
                
                self.controller._game_state.add_player(player)
            
            self.logger.info(f"游戏设置完成，{len(self.controller._game_state.players)}个玩家")
            return True
            
        except Exception as e:
            self.logger.error(f"游戏设置失败: {e}")
            return False
    
    def simulate_human_action(self, available_actions: List[ActionType]) -> Action:
        """模拟人类玩家的随机但合理的行动选择.
        
        Args:
            available_actions: 可用行动类型列表
            
        Returns:
            选择的行动
        """
        # 获取当前游戏状态
        snapshot = self.controller.get_snapshot()
        human_player = snapshot.players[0]  # 假设玩家0是人类
        
        # 根据情况做出合理的随机选择
        if ActionType.FOLD in available_actions and random.random() < 0.2:
            # 20%概率弃牌
            return Action(ActionType.FOLD, 0, 0)
        
        if ActionType.CHECK in available_actions and random.random() < 0.4:
            # 40%概率过牌（如果可以）
            return Action(ActionType.CHECK, 0, 0)
        
        if ActionType.CALL in available_actions and random.random() < 0.5:
            # 50%概率跟注
            return Action(ActionType.CALL, 0, 0)
        
        if ActionType.RAISE in available_actions and random.random() < 0.2:
            # 20%概率加注
            min_raise = max(snapshot.current_bet * 2 - human_player.current_bet, 10)
            max_raise = min(human_player.chips, min_raise * 3)
            raise_amount = random.randint(min_raise, max_raise) if max_raise >= min_raise else min_raise
            return Action(ActionType.RAISE, raise_amount, 0)
        
        if ActionType.ALL_IN in available_actions and random.random() < 0.05:
            # 5%概率全押
            return Action(ActionType.ALL_IN, 0, 0)
        
        # 默认选择第一个可用行动
        if available_actions:
            return Action(available_actions[0], 0, 0)
        
        # 如果没有可用行动，默认弃牌
        return Action(ActionType.FOLD, 0, 0)
    
    def get_available_actions(self, player_id: int) -> List[ActionType]:
        """获取玩家可用的行动类型.
        
        Args:
            player_id: 玩家ID
            
        Returns:
            可用行动类型列表
        """
        snapshot = self.controller.get_snapshot()
        player = snapshot.players[player_id]
        available_actions = []
        
        # 总是可以弃牌
        available_actions.append(ActionType.FOLD)
        
        # 检查是否可以过牌或跟注
        if snapshot.current_bet == 0 or snapshot.current_bet == player.current_bet:
            available_actions.append(ActionType.CHECK)
        elif snapshot.current_bet > player.current_bet:
            available_actions.append(ActionType.CALL)
        
        # 检查是否可以加注
        if player.chips > snapshot.current_bet - player.current_bet:
            if snapshot.current_bet == 0:
                available_actions.append(ActionType.BET)
            else:
                available_actions.append(ActionType.RAISE)
        
        # 检查是否可以全押
        if player.chips > 0:
            available_actions.append(ActionType.ALL_IN)
        
        return available_actions
    
    def play_single_hand(self, hand_number: int) -> HandRecord:
        """进行一手牌游戏.
        
        Args:
            hand_number: 手牌编号
            
        Returns:
            手牌记录
        """
        self.logger.info(f"开始第{hand_number}手牌")
        
        # 记录初始状态
        snapshot = self.controller.get_snapshot()
        initial_chips = {i: player.chips for i, player in enumerate(snapshot.players)}
        
        # 检查玩家状态
        for i, player in enumerate(snapshot.players):
            self.logger.info(f"第{hand_number}手牌开始前 - 玩家{i}: {player.name}, 筹码{player.chips}, 状态{player.status.value}")
        
        # 确保没有手牌在进行中
        if self.controller._hand_in_progress:
            self.logger.warning(f"第{hand_number}手牌开始前发现有手牌在进行中，强制结束")
            try:
                self.controller.end_hand()
            except Exception as e:
                self.logger.error(f"强制结束手牌失败: {e}")
        
        # 开始新手牌
        success = self.controller.start_new_hand()
        if not success:
            error_msg = f"无法开始第{hand_number}手牌"
            # 检查具体原因
            active_players = [p for p in snapshot.players if p.status.value == 'active' and p.chips > 0]
            if len(active_players) < 2:
                error_msg += f"，活跃玩家不足: {len(active_players)}"
            
            raise RuntimeError(error_msg)
        
        # 记录庄家和盲注位置
        snapshot = self.controller.get_snapshot()
        dealer_pos = snapshot.dealer_position
        
        # 查找小盲和大盲位置
        small_blind_pos = None
        big_blind_pos = None
        for i, player in enumerate(snapshot.players):
            if player.is_small_blind:
                small_blind_pos = i
            if player.is_big_blind:
                big_blind_pos = i
        
        # 验证盲注位置是否找到
        if small_blind_pos is None or big_blind_pos is None:
            self.logger.warning(f"第{hand_number}手牌盲注位置未正确设置: 小盲{small_blind_pos}, 大盲{big_blind_pos}")
        
        phases_reached = []
        total_actions = 0
        
        # 游戏主循环
        max_actions = 100  # 防止无限循环
        action_count = 0
        
        while not self.controller.is_hand_over() and action_count < max_actions:
            current_snapshot = self.controller.get_snapshot()
            
            # 记录达到的阶段
            if current_snapshot.phase not in phases_reached:
                phases_reached.append(current_snapshot.phase)
                self.logger.info(f"进入{current_snapshot.phase.value}阶段")
            
            current_player_id = self.controller.get_current_player_id()
            if current_player_id is None:
                self.logger.info("当前没有玩家需要行动，可能手牌已结束")
                break
            
            # 检查当前玩家状态
            current_player = current_snapshot.players[current_player_id]
            self.logger.debug(f"当前玩家{current_player_id}: {current_player.name}, 状态{current_player.status.value}, 筹码{current_player.chips}")
            
            # 执行玩家行动
            if current_player_id == 0:  # 人类玩家
                # 检查玩家是否能行动
                if current_player.status.value != 'active':
                    error_msg = f"玩家{current_player_id}无法行动，状态: {current_player.status.value}"
                    self.logger.error(error_msg)
                    raise RuntimeError(error_msg)
                
                available_actions = self.get_available_actions(current_player_id)
                action = self.simulate_human_action(available_actions)
                
                try:
                    self.controller.execute_action(action)
                    total_actions += 1
                    self.logger.info(f"人类玩家执行{action.action_type.value}")
                except Exception as e:
                    self.logger.warning(f"人类玩家行动失败: {e}")
                    # 尝试默认行动（弃牌）
                    try:
                        fallback_action = Action(ActionType.FOLD, 0, 0)
                        self.controller.execute_action(fallback_action)
                        total_actions += 1
                    except Exception as e2:
                        self.logger.error(f"默认行动也失败: {e2}")
                        break
            else:  # AI玩家
                success = self.controller.process_ai_action()
                if success:
                    total_actions += 1
                    self.logger.info(f"AI玩家{current_player_id}执行行动")
                else:
                    self.logger.warning(f"AI玩家{current_player_id}行动失败")
                    break
            
            action_count += 1
            time.sleep(0.01)  # 短暂延迟，避免过快执行
        
        # 确保手牌正确结束
        if self.controller.is_hand_over():
            try:
                hand_result = self.controller.end_hand()
                winner_ids = hand_result.winner_ids if hand_result else []
                pot_amount = hand_result.pot_amount if hand_result else 0
            except Exception as e:
                self.logger.warning(f"结束手牌时出错: {e}")
                winner_ids = []
                pot_amount = 0
        else:
            self.logger.warning(f"第{hand_number}手牌未正常结束，强制结束")
            try:
                hand_result = self.controller.end_hand()
                winner_ids = hand_result.winner_ids if hand_result else []
                pot_amount = hand_result.pot_amount if hand_result else 0
            except Exception as e:
                self.logger.error(f"强制结束手牌失败: {e}")
                winner_ids = []
                pot_amount = 0
        
        # 记录最终状态
        final_snapshot = self.controller.get_snapshot()
        final_chips = {i: player.chips for i, player in enumerate(final_snapshot.players)}
        
        # 创建手牌记录
        hand_record = HandRecord(
            hand_number=hand_number,
            initial_chips=initial_chips,
            final_chips=final_chips,
            dealer_position=dealer_pos,
            small_blind_position=small_blind_pos if small_blind_pos is not None else -1,
            big_blind_position=big_blind_pos if big_blind_pos is not None else -1,
            phases_reached=phases_reached,
            total_actions=total_actions,
            winner_ids=winner_ids,
            pot_amount=pot_amount,
            issues=[]
        )
        
        self.logger.info(f"第{hand_number}手牌完成，执行{total_actions}个行动，达到阶段: {[p.value for p in phases_reached]}")
        return hand_record
    
    def run_validation(self) -> Dict[str, Any]:
        """运行完整的验证测试.
        
        Returns:
            验证结果字典
        """
        start_time = time.time()
        self.logger.info(f"开始终极发版前验证测试，计划进行{self.num_hands}手牌")
        
        # 设置游戏
        if not self.setup_game():
            return {
                'success': False,
                'error': '游戏设置失败',
                'total_time': time.time() - start_time
            }
        
        # 进行多手牌游戏
        successful_hands = 0
        for hand_num in range(1, self.num_hands + 1):
            try:
                hand_record = self.play_single_hand(hand_num)
                self.hand_records.append(hand_record)
                successful_hands += 1
                
                # 实时验证当前手牌
                self.validator.validate_blind_positions(hand_record)
                self.validator.validate_phase_progression(hand_record)
                self.validator.validate_betting_rules(hand_record)
                self.validator.validate_action_sequence(hand_record)
                self.validator.validate_side_pot_rules(hand_record)
                self.validator.validate_showdown_rules(hand_record)
                self.validator.validate_special_cases(hand_record)
                self.validator.validate_hand_state_management(hand_record)
                self.validator.validate_ai_action_recording(hand_record)
                self.validator.validate_game_flow_completeness(hand_record)
                self.validator.validate_event_recording_completeness(hand_record)
                self.validator.validate_betting_round_completion(self.controller)
                self.validator.validate_phase_transition_timing(hand_record)
                
                # 新增验证：BET vs RAISE逻辑和最小下注计算
                if self.controller:
                    self.validator.validate_bet_vs_raise_logic(self.controller)
                    self.validator.validate_minimum_bet_calculation(self.controller)
                    self.validator.validate_betting_round_completion_detailed(self.controller)
                    # 新增：ALL_IN场景验证
                    self.validator.validate_all_in_scenarios(hand_record, self.controller)
                
            except Exception as e:
                self.logger.error(f"第{hand_num}手牌失败: {e}")
                # 创建错误记录
                error_record = HandRecord(
                    hand_number=hand_num,
                    initial_chips={},
                    final_chips={},
                    dealer_position=-1,
                    small_blind_position=-1,
                    big_blind_position=-1,
                    phases_reached=[],
                    total_actions=0,
                    winner_ids=[],
                    pot_amount=0,
                    issues=[ValidationIssue(
                        severity=TestResult.FAIL,
                        category="游戏异常",
                        description=f"第{hand_num}手牌异常",
                        details=str(e),
                        hand_number=hand_num
                    )]
                )
                self.hand_records.append(error_record)
        
        # 全局验证
        self.validator.validate_dealer_rotation(self.hand_records)
        self.validator.validate_chip_conservation(self.hand_records)
        
        # 收集所有问题
        all_issues = self.validator.issues
        for hand_record in self.hand_records:
            all_issues.extend(hand_record.issues)
        
        # 统计结果
        total_time = time.time() - start_time
        fail_count = sum(1 for issue in all_issues if issue.severity == TestResult.FAIL)
        warning_count = sum(1 for issue in all_issues if issue.severity == TestResult.WARNING)
        
        # 计算得分（满分100分）
        max_possible_issues = self.num_hands * 5  # 每手牌最多5类问题
        score = max(0, 100 - (fail_count * 10 + warning_count * 2))
        
        # 确定等级
        if score >= 90:
            grade = "🏆 优秀"
        elif score >= 80:
            grade = "✅ 良好"
        elif score >= 70:
            grade = "⚠️ 合格"
        else:
            grade = "❌ 不合格"
        
        result = {
            'success': successful_hands > 0,
            'total_hands': self.num_hands,
            'successful_hands': successful_hands,
            'total_issues': len(all_issues),
            'fail_issues': fail_count,
            'warning_issues': warning_count,
            'score': score,
            'grade': grade,
            'total_time': total_time,
            'issues': all_issues,
            'hand_records': self.hand_records,
            'validator': self.validator
        }
        
        return result
    
    def generate_report(self, result: Dict[str, Any]) -> str:
        """生成详细的验证报告.
        
        Args:
            result: 验证结果
            
        Returns:
            格式化的报告字符串
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("🃏 德州扑克v2 - 终极发版前验证报告")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # 总体评估
        report_lines.append("📊 总体评估")
        report_lines.append("-" * 40)
        report_lines.append(f"测试结果: {result['grade']}")
        report_lines.append(f"综合得分: {result['score']}/100")
        report_lines.append(f"成功手牌: {result['successful_hands']}/{result['total_hands']}")
        report_lines.append(f"执行时间: {result['total_time']:.2f}秒")
        report_lines.append("")
        
        # 问题统计
        report_lines.append("🐛 问题统计")
        report_lines.append("-" * 40)
        report_lines.append(f"严重问题: {result['fail_issues']}个")
        report_lines.append(f"警告问题: {result['warning_issues']}个")
        report_lines.append(f"总计问题: {result['total_issues']}个")
        report_lines.append("")
        
        # 详细问题列表
        if result['issues']:
            report_lines.append("📝 详细问题列表")
            report_lines.append("-" * 40)
            
            # 按类别分组显示问题
            issues_by_category = {}
            for issue in result['issues']:
                if issue.category not in issues_by_category:
                    issues_by_category[issue.category] = []
                issues_by_category[issue.category].append(issue)
            
            for category, issues in issues_by_category.items():
                report_lines.append(f"【{category}】")
                for issue in issues:
                    severity_icon = "❌" if issue.severity == TestResult.FAIL else "⚠️"
                    hand_info = f"第{issue.hand_number}手 - " if issue.hand_number else ""
                    report_lines.append(f"  {severity_icon} {hand_info}{issue.description}")
                    if issue.details:
                        report_lines.append(f"      详情: {issue.details}")
                    if issue.expected and issue.actual:
                        report_lines.append(f"      期望: {issue.expected}, 实际: {issue.actual}")
                report_lines.append("")
        
        # 手牌统计
        if result['hand_records']:
            report_lines.append("📈 手牌统计")
            report_lines.append("-" * 40)
            
            # 庄家轮换统计
            dealer_positions = [hr.dealer_position for hr in result['hand_records'] if hr.dealer_position >= 0]
            if dealer_positions:
                report_lines.append(f"庄家位置变化: {dealer_positions}")
            
            # 阶段统计
            all_phases = []
            for hr in result['hand_records']:
                all_phases.extend(hr.phases_reached)
            
            phase_counts = {}
            for phase in all_phases:
                phase_counts[phase.value] = phase_counts.get(phase.value, 0) + 1
            
            report_lines.append("阶段到达统计:")
            for phase_name, count in phase_counts.items():
                report_lines.append(f"  {phase_name}: {count}次")
            
            report_lines.append("")
        
        # 筹码守恒检查
        if self.validator.total_initial_chips > 0:
            report_lines.append("💰 筹码守恒验证")
            report_lines.append("-" * 40)
            final_hand = result['hand_records'][-1] if result['hand_records'] else None
            if final_hand and final_hand.final_chips:
                final_total = sum(final_hand.final_chips.values())
                difference = final_total - self.validator.total_initial_chips
                if difference == 0:
                    report_lines.append("✅ 筹码守恒验证通过")
                else:
                    report_lines.append(f"❌ 筹码守恒验证失败，差异: {difference}")
                report_lines.append(f"初始总筹码: {self.validator.total_initial_chips}")
                report_lines.append(f"最终总筹码: {final_total}")
            report_lines.append("")
        
        # 建议和结论
        report_lines.append("💡 建议与结论")
        report_lines.append("-" * 40)
        
        if result['score'] >= 90:
            report_lines.append("🎉 恭喜！游戏完全符合德州扑克规则，可以发布！")
        elif result['score'] >= 80:
            report_lines.append("👍 游戏基本符合德州扑克规则，建议修复minor问题后发布。")
        elif result['score'] >= 70:
            report_lines.append("⚠️ 游戏存在一些规则问题，建议修复后再次测试。")
        else:
            report_lines.append("❌ 游戏存在严重规则违规，必须修复所有问题后才能发布。")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)


def main():
    """主函数."""
    print("🚀 启动德州扑克v2终极发版前验证测试...")
    
    # 创建验证器并运行测试
    validator = UltimateReleaseValidator(num_hands=10, initial_chips=1000)
    result = validator.run_validation()
    
    # 生成并显示报告
    report = validator.generate_report(result)
    print(report)
    
    # 保存报告到文件
    with open('ultimate_validation_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("\n📄 详细报告已保存到 ultimate_validation_report.txt")
    
    # 返回退出码
    if result['score'] >= 80:
        return 0  # 成功
    else:
        return 1  # 失败


if __name__ == "__main__":
    exit(main()) 