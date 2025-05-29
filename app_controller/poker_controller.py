"""
德州扑克应用控制器
实现Copy-on-Write模式的应用服务层，提供原子性事务和游戏流程管理
"""

import copy
import logging
from functools import wraps
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime

from core_game_logic.game.game_state import GameState
from core_game_logic.core.enums import Action, ActionType, GamePhase, SeatStatus
from core_game_logic.core.player import Player
from core_game_logic.betting.action_validator import ActionValidator
from core_game_logic.phases import PreFlopPhase, FlopPhase, TurnPhase, RiverPhase, ShowdownPhase
from core_game_logic.core.exceptions import InvalidActionError, GameStateError

from .dto_models import (
    GameStateSnapshot, 
    PlayerActionInput, 
    ActionResult, 
    ActionResultType,
    GameEvent, 
    GameEventType
)


# 原子性装饰器
def atomic(fn: Callable) -> Callable:
    """
    原子性装饰器，实现Copy-on-Write模式
    方法执行前创建状态快照，异常时自动回滚
    """
    @wraps(fn)
    def wrapper(self: 'PokerController', *args, **kwargs):
        # 保存当前状态的深拷贝（Copy-on-Write）
        state_snapshot = copy.deepcopy(self.state)
        original_version = self.version
        
        try:
            # 执行方法并返回结果
            result = fn(self, *args, **kwargs)
            # 如果成功，增加版本号
            self.version += 1
            return result
        except Exception as e:
            # 异常发生时回滚到快照状态
            self.state = state_snapshot
            self.version = original_version
            self._log_error(f"事务回滚: {fn.__name__} - {str(e)}")
            # 重新抛出异常
            raise
    
    return wrapper


class PokerController:
    """
    德州扑克应用控制器
    
    职责：
    1. 提供Copy-on-Write的原子性事务操作
    2. 管理游戏状态的版本化和快照
    3. 协调各阶段的游戏流程
    4. 集成行动验证和事件发布
    5. 为CLI/Web等前端提供统一接口
    """
    
    def __init__(self, initial_state: GameState, logger: Optional[logging.Logger] = None):
        """
        初始化控制器
        
        Args:
            initial_state: 初始游戏状态
            logger: 可选的日志记录器
        """
        self.state = initial_state
        self.version = 0  # 状态版本号，用于增量更新优化
        self.validator = ActionValidator()
        self.logger = logger or logging.getLogger(__name__)
        
        # 缓存上一次的快照，用于优化
        self._last_snapshot: Optional[GameStateSnapshot] = None
        self._last_snapshot_version: int = -1
        
        # 事件收集器（暂时存储在内存中，Phase 3时将接入EventBus）
        self.pending_events: List[GameEvent] = []
        
        self._log_info(f"PokerController 初始化完成，初始版本: {self.version}")
    
    def get_state_snapshot(self, viewer_seat: Optional[int] = None, 
                          last_known_version: Optional[int] = None) -> Optional[GameStateSnapshot]:
        """
        获取游戏状态快照
        
        Args:
            viewer_seat: 观察者座位号，用于隐藏其他玩家手牌
            last_known_version: 客户端已知的最后版本号，用于增量更新
        
        Returns:
            游戏状态快照，如果版本无变化则返回None
        """
        # 增量更新优化：如果版本无变化，返回None
        if last_known_version is not None and last_known_version == self.version:
            return None
        
        # 缓存优化：如果viewer_seat为None且版本无变化，复用缓存
        if (viewer_seat is None and 
            self._last_snapshot is not None and 
            self._last_snapshot_version == self.version):
            return self._last_snapshot
        
        # 创建新快照
        snapshot = GameStateSnapshot.from_game_state(self.state, self.version, viewer_seat)
        
        # 缓存无视角限制的快照
        if viewer_seat is None:
            self._last_snapshot = snapshot
            self._last_snapshot_version = self.version
        
        return snapshot
    
    @atomic
    def execute_player_action(self, action_input: PlayerActionInput) -> ActionResult:
        """
        执行玩家行动（原子性操作）
        
        Args:
            action_input: 玩家行动输入
        
        Returns:
            行动执行结果
        """
        # 验证输入
        if not action_input.validate():
            raise InvalidActionError(f"无效的行动输入: {action_input}")
        
        # 获取玩家对象
        player = self.state.get_player_by_seat(action_input.seat_id)
        if player is None:
            raise InvalidActionError(f"玩家座位 {action_input.seat_id} 不存在")
        
        # 创建行动对象
        action = Action(
            action_type=action_input.action_type,
            amount=action_input.amount or 0,
            player_seat=action_input.seat_id
        )
        
        try:
            # 验证和转换行动
            validated_action = self.validator.validate(self.state, player, action)
            
            # 执行行动
            events = self._execute_validated_action(player, validated_action)
            
            # 检查是否需要推进游戏状态
            self._check_and_advance_game_state()
            
            # 创建成功结果
            result = ActionResult.success_result(
                message=f"玩家 {player.name} 执行了 {validated_action}",
                events=events
            )
            
            self._log_info(f"行动执行成功: {result.message}")
            return result
            
        except InvalidActionError as e:
            # 重新抛出InvalidActionError，让装饰器处理回滚
            raise
        except Exception as e:
            # 其他异常也重新抛出
            raise GameStateError(f"执行行动时发生错误: {str(e)}")

    def execute_player_action_safe(self, action_input: PlayerActionInput) -> ActionResult:
        """
        安全执行玩家行动的包装方法，捕获异常并返回ActionResult
        
        Args:
            action_input: 玩家行动输入
        
        Returns:
            行动执行结果
        """
        try:
            return self.execute_player_action(action_input)
        except InvalidActionError as e:
            return ActionResult.error_result(
                ActionResultType.INVALID_ACTION,
                str(e)
            )
        except GameStateError as e:
            return ActionResult.error_result(
                ActionResultType.GAME_ERROR,
                str(e)
            )
        except Exception as e:
            return ActionResult.error_result(
                ActionResultType.GAME_ERROR,
                f"未知错误: {str(e)}"
            )
    
    def _execute_validated_action(self, player: Player, validated_action) -> List[GameEvent]:
        """
        执行已验证的行动
        
        Args:
            player: 执行行动的玩家
            validated_action: 已验证的行动
        
        Returns:
            产生的事件列表
        """
        events = []
        
        # 记录玩家执行的行动
        original_chips = player.chips
        original_current_bet = player.current_bet
        
        # 根据行动类型执行相应逻辑
        action_type = validated_action.actual_action_type
        amount = validated_action.actual_amount
        
        if action_type == ActionType.FOLD:
            player.fold()
            events.append(GameEvent.player_action_event(player.seat_id, action_type))
            
        elif action_type == ActionType.CHECK:
            # 过牌不需要额外操作，只记录事件
            events.append(GameEvent.player_action_event(player.seat_id, action_type))
            
        elif action_type in [ActionType.CALL, ActionType.BET, ActionType.RAISE]:
            # 计算实际需要投入的金额
            additional_bet = amount - player.current_bet
            player.bet(additional_bet)
            
            # 更新游戏状态的当前下注线
            if amount > self.state.current_bet:
                # 记录加注信息
                if action_type == ActionType.RAISE:
                    self.state.last_raise_amount = amount - self.state.current_bet
                    self.state.last_raiser = player.seat_id
                self.state.current_bet = amount
            
            events.append(GameEvent.player_action_event(player.seat_id, action_type, amount))
            
        elif action_type == ActionType.ALL_IN:
            # 全押：玩家投入所有筹码
            additional_bet = player.chips
            player.bet(additional_bet)
            total_bet = player.current_bet
            
            # 如果全押超过当前下注线，更新状态
            if total_bet > self.state.current_bet:
                self.state.last_raise_amount = total_bet - self.state.current_bet
                self.state.last_raiser = player.seat_id
                self.state.current_bet = total_bet
            
            events.append(GameEvent.player_action_event(player.seat_id, action_type, total_bet))
        
        # 推进到下一个玩家
        if not self.state.advance_current_player():
            # 没有下一个可行动的玩家，下注轮结束
            events.append(GameEvent(
                event_type=GameEventType.BETTING_ROUND_COMPLETE,
                message=f"{self.state.phase.name} 下注轮结束"
            ))
        
        return events
    
    def _check_and_advance_game_state(self):
        """检查并推进游戏状态"""
        # 检查下注轮是否完成
        if self.state.is_betting_round_complete():
            self._advance_to_next_phase()
    
    def _advance_to_next_phase(self):
        """推进到下一个游戏阶段"""
        current_phase = self.state.phase
        
        # 收集当前轮的下注到底池
        self.state.collect_bets_to_pot()
        
        # 推进阶段
        self.state.advance_phase()
        
        # 发布阶段转换事件
        self.pending_events.append(
            GameEvent.phase_transition_event(current_phase, self.state.phase)
        )
        
        # 根据新阶段执行相应逻辑
        if self.state.phase == GamePhase.FLOP:
            self._deal_flop()
        elif self.state.phase == GamePhase.TURN:
            self._deal_turn()
        elif self.state.phase == GamePhase.RIVER:
            self._deal_river()
        elif self.state.phase == GamePhase.SHOWDOWN:
            self._enter_showdown()
        
        # 如果不是摊牌阶段，开始新的下注轮
        if self.state.phase != GamePhase.SHOWDOWN:
            self.state.start_new_betting_round()
    
    def _deal_flop(self):
        """发翻牌"""
        if self.state.deck and len(self.state.community_cards) == 0:
            # 烧一张牌（实际游戏中的规则）
            self.state.deck.deal_card()
            # 发三张翻牌
            for _ in range(3):
                card = self.state.deck.deal_card()
                self.state.community_cards.append(card)
            
            self.pending_events.append(GameEvent(
                event_type=GameEventType.CARDS_DEALT,
                message=f"翻牌发出: {' '.join(card.to_display_str() for card in self.state.community_cards[-3:])}"
            ))
    
    def _deal_turn(self):
        """发转牌"""
        if self.state.deck and len(self.state.community_cards) == 3:
            # 烧一张牌
            self.state.deck.deal_card()
            # 发转牌
            card = self.state.deck.deal_card()
            self.state.community_cards.append(card)
            
            self.pending_events.append(GameEvent(
                event_type=GameEventType.CARDS_DEALT,
                message=f"转牌发出: {card.to_display_str()}"
            ))
    
    def _deal_river(self):
        """发河牌"""
        if self.state.deck and len(self.state.community_cards) == 4:
            # 烧一张牌
            self.state.deck.deal_card()
            # 发河牌
            card = self.state.deck.deal_card()
            self.state.community_cards.append(card)
            
            self.pending_events.append(GameEvent(
                event_type=GameEventType.CARDS_DEALT,
                message=f"河牌发出: {card.to_display_str()}"
            ))
    
    def _enter_showdown(self):
        """进入摊牌阶段"""
        self.pending_events.append(GameEvent(
            event_type=GameEventType.HAND_COMPLETE,
            message="手牌结束，进入摊牌阶段"
        ))
    
    @atomic
    def start_new_hand(self) -> ActionResult:
        """
        开始新一手牌（原子性操作）
        
        Returns:
            操作结果
        """
        try:
            # 重置游戏状态为新手牌
            self._reset_for_new_hand()
            
            # 设置盲注
            self.state.set_blinds()
            
            # 发起始手牌
            self._deal_hole_cards()
            
            # 开始翻牌前下注轮
            self.state.start_new_betting_round()
            
            events = [GameEvent(
                event_type=GameEventType.CARDS_DEALT,
                message="新一手牌开始，手牌已发出"
            )]
            
            return ActionResult.success_result(
                message="新一手牌开始",
                events=events
            )
            
        except Exception as e:
            return ActionResult.error_result(
                ActionResultType.GAME_ERROR,
                f"开始新手牌时发生错误: {str(e)}"
            )
    
    def _reset_for_new_hand(self):
        """重置游戏状态准备新手牌"""
        # 重置游戏阶段
        self.state.phase = GamePhase.PRE_FLOP
        
        # 清空公共牌
        self.state.community_cards.clear()
        
        # 重置底池和下注信息
        self.state.pot = 0
        self.state.current_bet = 0
        self.state.last_raiser = None
        self.state.last_raise_amount = 0
        
        # 重置所有玩家状态
        for player in self.state.players:
            if player.chips > 0:
                player.reset_for_new_hand()
            # 筹码为0的玩家保持OUT状态
        
        # 创建新牌组（如果需要）
        if self.state.deck is None:
            from core_game_logic.core.deck import Deck
            self.state.deck = Deck()
            self.state.deck.shuffle()
    
    def _deal_hole_cards(self):
        """为活跃玩家发手牌"""
        if not self.state.deck:
            raise GameStateError("牌组未初始化")
        
        active_players = self.state.get_active_players()
        
        # 为每个活跃玩家发两张手牌
        for player in active_players:
            hole_cards = []
            for _ in range(2):
                card = self.state.deck.deal_card()
                hole_cards.append(card)
            player.set_hole_cards(hole_cards)
    
    @atomic
    def advance_dealer(self) -> ActionResult:
        """
        推进庄家位置（原子性操作）
        
        Returns:
            操作结果
        """
        try:
            old_dealer = self.state.dealer_position
            
            # 清除当前庄家标记
            old_dealer_player = self.state.get_player_by_seat(old_dealer)
            if old_dealer_player:
                old_dealer_player.is_dealer = False
            
            # 找到下一个有效的庄家位置
            all_seats = sorted([p.seat_id for p in self.state.players if p.chips > 0])
            if not all_seats:
                return ActionResult.error_result(
                    ActionResultType.GAME_ERROR,
                    "没有有效玩家可以担任庄家"
                )
            
            try:
                current_index = all_seats.index(old_dealer)
                new_dealer_index = (current_index + 1) % len(all_seats)
            except ValueError:
                # 如果当前庄家不在有效座位中，选择第一个有效座位
                new_dealer_index = 0
            
            new_dealer = all_seats[new_dealer_index]
            self.state.dealer_position = new_dealer
            
            # 设置新庄家标记
            new_dealer_player = self.state.get_player_by_seat(new_dealer)
            if new_dealer_player:
                new_dealer_player.is_dealer = True
            
            event = GameEvent(
                event_type=GameEventType.DEALER_ROTATION,
                message=f"庄家从位置 {old_dealer} 转移到位置 {new_dealer}",
                affected_seat_ids=[old_dealer, new_dealer]
            )
            
            return ActionResult.success_result(
                message=f"庄家已转移到位置 {new_dealer}",
                events=[event]
            )
            
        except Exception as e:
            return ActionResult.error_result(
                ActionResultType.GAME_ERROR,
                f"推进庄家时发生错误: {str(e)}"
            )
    
    def get_available_actions(self, seat_id: int) -> List[ActionType]:
        """
        获取指定玩家的可用行动列表
        
        Args:
            seat_id: 玩家座位号
        
        Returns:
            可用行动类型列表
        """
        player = self.state.get_player_by_seat(seat_id)
        if player is None or not player.can_act():
            return []
        
        return self.validator.get_available_actions(self.state, player)
    
    def get_available_actions_detail(self, seat_id: int) -> List[Dict[str, Any]]:
        """
        获取指定玩家的详细可用行动信息
        
        Args:
            seat_id: 玩家座位号
        
        Returns:
            详细行动信息列表，格式为:
            [
                {
                    "action_type": ActionType.FOLD,
                    "display_name": "弃牌",
                    "amount": None,
                    "description": "放弃此手牌"
                },
                ...
            ]
        """
        player = self.state.get_player_by_seat(seat_id)
        if player is None or not player.can_act():
            return []
        
        actions = []
        required_amount = self.state.current_bet - player.current_bet
        
        # 弃牌总是可用（除非已经全押且无需追加）
        if not (player.status == SeatStatus.ALL_IN):
            actions.append({
                "action_type": ActionType.FOLD,
                "display_name": "弃牌",
                "amount": None,
                "description": "放弃此手牌"
            })
        
        # 过牌或跟注
        if required_amount == 0:
            # 可以过牌
            actions.append({
                "action_type": ActionType.CHECK,
                "display_name": "过牌",
                "amount": None,
                "description": "不下注但继续游戏"
            })
        else:
            # 需要跟注
            call_amount = min(required_amount, player.chips)
            if call_amount > 0:
                if call_amount == player.chips:
                    actions.append({
                        "action_type": ActionType.ALL_IN,
                        "display_name": f"全押跟注 ({call_amount})",
                        "amount": call_amount,
                        "description": f"全押跟注 {call_amount} 筹码"
                    })
                else:
                    actions.append({
                        "action_type": ActionType.CALL,
                        "display_name": f"跟注 ({call_amount})",
                        "amount": call_amount,
                        "description": f"跟注 {call_amount} 筹码"
                    })
        
        # 下注/加注
        if required_amount == 0:
            # 可以下注
            min_bet = self.state.big_blind
            if player.chips >= min_bet:
                actions.append({
                    "action_type": ActionType.BET,
                    "display_name": f"下注 (最少{min_bet})",
                    "amount": min_bet,
                    "description": f"主动下注，最少 {min_bet} 筹码",
                    "min_amount": min_bet,
                    "max_amount": player.chips
                })
        else:
            # 可以加注
            min_raise_amount = self.state.current_bet + self.state.big_blind
            if player.chips >= min_raise_amount:
                actions.append({
                    "action_type": ActionType.RAISE,
                    "display_name": f"加注 (最少到{min_raise_amount})",
                    "amount": min_raise_amount,
                    "description": f"加注到 {min_raise_amount} 筹码",
                    "min_amount": min_raise_amount,
                    "max_amount": player.chips
                })
        
        # 全押（如果不是在跟注全押的情况下）
        if player.chips > 0 and required_amount < player.chips:
            actions.append({
                "action_type": ActionType.ALL_IN,
                "display_name": f"全押 ({player.chips})",
                "amount": player.chips,
                "description": f"全押 {player.chips} 筹码"
            })
        
        return actions
    
    def is_hand_over(self) -> bool:
        """检查当前手牌是否结束"""
        return self.state.phase == GamePhase.SHOWDOWN
    
    def is_betting_round_complete(self) -> bool:
        """检查当前下注轮是否完成"""
        return self.state.is_betting_round_complete()
    
    def get_current_player_seat(self) -> Optional[int]:
        """获取当前行动玩家的座位号"""
        return self.state.current_player
    
    @atomic
    def process_betting_round(self, get_player_action_callback) -> ActionResult:
        """
        处理整个下注轮（原子性操作）
        现在委托给当前Phase的process_betting_round方法，实现Domain纯化
        
        Args:
            get_player_action_callback: 获取玩家行动的回调函数
                签名: (seat_id: int, snapshot: GameStateSnapshot) -> PlayerActionInput
        
        Returns:
            下注轮处理结果
        """
        try:
            # 获取当前阶段实例
            current_phase = self._get_current_phase()
            if not current_phase:
                return ActionResult.error_result(
                    ActionResultType.GAME_ERROR,
                    "无法获取当前游戏阶段"
                )
            
            # 创建适配器函数，将Controller的回调适配为Phase期望的格式
            def phase_callback(seat_id: int):
                # 获取当前状态快照
                snapshot = self.get_state_snapshot(viewer_seat=seat_id)
                if not snapshot:
                    raise ValueError(f"无法获取座位{seat_id}的状态快照")
                
                # 调用原始回调获取行动输入
                return get_player_action_callback(seat_id, snapshot)
            
            # 委托给Phase层处理下注轮
            events = current_phase.process_betting_round(phase_callback)
            
            # 将字符串事件转换为GameEvent对象
            game_events = []
            for event_msg in events:
                game_events.append(GameEvent(
                    event_type=GameEventType.PLAYER_ACTION,
                    message=event_msg
                ))
            
            return ActionResult.success_result(
                message=f"下注轮完成，共产生了 {len(events)} 个事件",
                events=game_events
            )
            
        except Exception as e:
            return ActionResult.error_result(
                ActionResultType.GAME_ERROR,
                f"处理下注轮时发生错误: {str(e)}"
            )

    def _get_current_phase(self):
        """
        获取当前游戏阶段的实例
        
        Returns:
            当前阶段的实例，如果无法确定则返回None
        """
        from core_game_logic.phases import PreFlopPhase, FlopPhase, TurnPhase, RiverPhase, ShowdownPhase
        from core_game_logic.core.enums import GamePhase
        
        phase_map = {
            GamePhase.PRE_FLOP: PreFlopPhase,
            GamePhase.FLOP: FlopPhase,
            GamePhase.TURN: TurnPhase,
            GamePhase.RIVER: RiverPhase,
            GamePhase.SHOWDOWN: ShowdownPhase
        }
        
        phase_class = phase_map.get(self.state.phase)
        if phase_class:
            return phase_class(self.state)
        
        return None
    
    def _log_info(self, message: str):
        """记录信息日志"""
        self.logger.info(f"[PokerController v{self.version}] {message}")
    
    def _log_error(self, message: str):
        """记录错误日志"""
        self.logger.error(f"[PokerController v{self.version}] {message}")
    
    def __str__(self) -> str:
        """返回控制器状态的字符串表示"""
        return f"PokerController(version={self.version}, phase={self.state.phase.name}, players={len(self.state.players)})" 