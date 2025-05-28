"""
游戏状态管理类
包含游戏阶段、玩家状态、底池等核心信息
"""

import copy
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from ..core.card import Card
from ..core.player import Player
from ..core.enums import GamePhase, SeatStatus
from ..core.deck import Deck
from ..core.exceptions import GameStateError, PhaseTransitionError


@dataclass
class GameState:
    """
    德州扑克游戏状态类
    管理游戏的所有核心状态信息
    """
    # 游戏基础信息
    phase: GamePhase = GamePhase.PRE_FLOP          # 当前游戏阶段
    community_cards: List[Card] = field(default_factory=list)  # 公共牌
    pot: int = 0                                   # 当前底池总额
    
    # 玩家和座位信息
    players: List[Player] = field(default_factory=list)  # 所有玩家
    dealer_position: int = 0                       # 庄家位置
    current_player: int = 0                        # 当前行动玩家
    
    # 下注轮次信息
    current_bet: int = 0                          # 当前轮最高下注额
    last_raiser: Optional[int] = None             # 最后加注的玩家
    street_index: int = 0                         # 当前阶段的行动次数
    
    # 游戏控制信息
    small_blind: int = 1                          # 小盲注金额
    big_blind: int = 2                            # 大盲注金额
    deck: Optional[Deck] = None                   # 牌组
    
    # 事件和状态管理
    events: List[str] = field(default_factory=list)  # 游戏事件日志

    def __post_init__(self):
        """初始化后的验证和设置"""
        if self.pot < 0:
            raise ValueError(f"底池金额不能为负数: {self.pot}")
        
        if self.current_bet < 0:
            raise ValueError(f"当前下注不能为负数: {self.current_bet}")
        
        if self.small_blind <= 0:
            raise ValueError(f"小盲注必须大于0: {self.small_blind}")
        
        if self.big_blind <= self.small_blind:
            raise ValueError(f"大盲注({self.big_blind})必须大于小盲注({self.small_blind})")

    def get_active_players(self) -> List[Player]:
        """
        获取所有可以行动的玩家
        
        Returns:
            可以行动的玩家列表
        """
        return [p for p in self.players if p.status == SeatStatus.ACTIVE]

    def get_players_in_hand(self) -> List[Player]:
        """
        获取仍在手牌中的玩家（未弃牌且未出局）
        
        Returns:
            仍在手牌中的玩家列表
        """
        return [p for p in self.players if p.status in [SeatStatus.ACTIVE, SeatStatus.ALL_IN]]

    def get_player_by_seat(self, seat_id: int) -> Optional[Player]:
        """
        根据座位号获取玩家
        
        Args:
            seat_id: 座位号
            
        Returns:
            对应的玩家对象，如果不存在则返回None
        """
        for player in self.players:
            if player.seat_id == seat_id:
                return player
        return None

    def get_current_player(self) -> Optional[Player]:
        """
        获取当前行动的玩家
        
        Returns:
            当前行动的玩家，如果无效则返回None
        """
        return self.get_player_by_seat(self.current_player)

    def advance_current_player(self) -> bool:
        """
        推进到下一个可行动的玩家
        
        Returns:
            True如果成功推进，False如果没有更多玩家可行动
        """
        active_players = self.get_active_players()
        if not active_players:
            return False
        
        # 获取所有玩家的座位号，按顺序排列
        all_seats = sorted([p.seat_id for p in self.players])
        current_index = all_seats.index(self.current_player)
        
        # 从下一个座位开始查找可行动的玩家
        for i in range(1, len(all_seats)):
            next_index = (current_index + i) % len(all_seats)
            next_seat = all_seats[next_index]
            next_player = self.get_player_by_seat(next_seat)
            
            if next_player and next_player.can_act():
                self.current_player = next_seat
                return True
        
        return False

    def is_betting_round_complete(self) -> bool:
        """
        检查当前下注轮是否完成
        
        Returns:
            True如果下注轮完成，False否则
        """
        active_players = self.get_active_players()
        
        # 如果没有可行动的玩家，下注轮结束
        if not active_players:
            return True
        
        # 如果只有一个玩家可行动，下注轮结束
        if len(active_players) == 1:
            return True
        
        # 检查所有可行动玩家的下注是否相等
        current_bets = [p.current_bet for p in active_players]
        if len(set(current_bets)) > 1:
            return False
        
        # 如果有最后加注者，检查是否轮回到加注者
        if self.last_raiser is not None:
            return self.current_player == self.last_raiser
        
        # Pre-flop阶段特殊处理：大盲注玩家有行动权利
        if self.phase == GamePhase.PRE_FLOP:
            # 找到大盲注玩家
            big_blind_player = None
            for player in self.players:
                if player.is_big_blind and player.can_act():
                    big_blind_player = player
                    break
            
            # 如果大盲注玩家还可以行动且没有被加注过，检查大盲权利
            if (big_blind_player and 
                self.current_bet == big_blind_player.current_bet and
                self.last_raiser is None):
                # 如果大盲玩家还没有行动过，他有权利行动
                if big_blind_player.last_action_type is None:
                    return False
                # 如果大盲玩家已经行动过了（比如check），下注轮完成
                else:
                    return True
        
        # 如果没有加注者，检查是否所有人都行动过
        return self.street_index >= len(active_players)

    def start_new_betting_round(self, starting_player: Optional[int] = None):
        """
        开始新的下注轮
        
        Args:
            starting_player: 指定开始行动的玩家，如果为None则使用默认规则
        """
        # 重置下注轮信息
        self.current_bet = 0
        self.last_raiser = None
        self.street_index = 0
        
        # 重置所有玩家的当前下注
        for player in self.players:
            player.reset_current_bet()
        
        # 设置开始行动的玩家
        if starting_player is not None:
            self.current_player = starting_player
        else:
            # 根据游戏阶段使用不同的规则
            if self.phase == GamePhase.PRE_FLOP:
                # 翻牌前：使用现有的_set_first_to_act逻辑（从庄家左边开始）
                self._set_first_to_act()
            else:
                # 翻牌后：从小盲注开始行动
                self._set_postflop_first_to_act()

    def _set_first_to_act(self):
        """设置第一个行动的玩家（翻牌前专用）"""
        all_seats = sorted([p.seat_id for p in self.players])
        dealer_index = all_seats.index(self.dealer_position)
        
        # 从庄家左边开始找第一个可行动的玩家
        for i in range(1, len(all_seats) + 1):
            next_index = (dealer_index + i) % len(all_seats)
            next_seat = all_seats[next_index]
            next_player = self.get_player_by_seat(next_seat)
            
            if next_player and next_player.can_act():
                self.current_player = next_seat
                return
        
        # 如果没有找到可行动的玩家，设置为庄家
        self.current_player = self.dealer_position

    def _set_postflop_first_to_act(self):
        """设置翻牌后阶段第一个行动的玩家（从小盲注开始）"""
        all_seats = sorted([p.seat_id for p in self.players if p.status != SeatStatus.OUT])
        if not all_seats:
            return
        
        dealer_index = all_seats.index(self.dealer_position)
        
        # 找到小盲注位置
        if len(all_seats) == 2:
            # 单挑：翻牌后非庄家（大盲）先行动
            big_blind_index = 1 - dealer_index
            start_seat = all_seats[big_blind_index]
        else:
            # 多人：庄家左边是小盲，从小盲开始
            small_blind_index = (dealer_index + 1) % len(all_seats)
            start_seat = all_seats[small_blind_index]
        
        # 从起始位置开始找第一个可行动的玩家
        start_index = all_seats.index(start_seat)
        for i in range(len(all_seats)):
            check_index = (start_index + i) % len(all_seats)
            check_seat = all_seats[check_index]
            check_player = self.get_player_by_seat(check_seat)
            
            if check_player and check_player.can_act():
                self.current_player = check_seat
                return
        
        # 如果没有找到可行动的玩家，设置为庄家
        self.current_player = self.dealer_position

    def advance_phase(self):
        """推进到下一个游戏阶段"""
        phase_order = [GamePhase.PRE_FLOP, GamePhase.FLOP, GamePhase.TURN, GamePhase.RIVER, GamePhase.SHOWDOWN]
        
        try:
            current_index = phase_order.index(self.phase)
            if current_index < len(phase_order) - 1:
                self.phase = phase_order[current_index + 1]
        except ValueError:
            # 如果当前阶段不在列表中，设置为摊牌
            self.phase = GamePhase.SHOWDOWN

    def collect_bets_to_pot(self):
        """将所有玩家的当前下注收集到底池中"""
        for player in self.players:
            self.pot += player.current_bet
            player.reset_current_bet()

    def set_blinds(self):
        """设置盲注（在发牌前调用）"""
        if len(self.players) < 2:
            return
        
        # 首先重置所有玩家的位置标记
        for player in self.players:
            player.is_small_blind = False
            player.is_big_blind = False
            # 庄家标记保持不变，由外部管理
        
        all_seats = sorted([p.seat_id for p in self.players if p.status != SeatStatus.OUT])
        dealer_index = all_seats.index(self.dealer_position)
        
        # 单挑时的特殊规则
        if len(all_seats) == 2:
            # 庄家是小盲，另一个是大盲
            small_blind_seat = self.dealer_position
            big_blind_seat = all_seats[1 - dealer_index]
        else:
            # 多人游戏：庄家左边是小盲，小盲左边是大盲
            small_blind_seat = all_seats[(dealer_index + 1) % len(all_seats)]
            big_blind_seat = all_seats[(dealer_index + 2) % len(all_seats)]
        
        # 设置小盲注
        small_blind_player = self.get_player_by_seat(small_blind_seat)
        if small_blind_player:
            small_blind_player.is_small_blind = True
            small_blind_player.bet(self.small_blind)
        
        # 设置大盲注
        big_blind_player = self.get_player_by_seat(big_blind_seat)
        if big_blind_player:
            big_blind_player.is_big_blind = True
            big_blind_player.bet(self.big_blind)
            self.current_bet = self.big_blind

    def to_dict(self, viewer_seat: Optional[int] = None) -> Dict[str, Any]:
        """
        将游戏状态转换为字典格式
        用于AI状态编码和序列化
        
        Args:
            viewer_seat: 观察者的座位号，用于隐藏其他玩家手牌
            
        Returns:
            游戏状态字典
        """
        players_data = []
        for player in self.players:
            # 决定是否隐藏手牌
            hide_cards = viewer_seat is not None and player.seat_id != viewer_seat
            
            player_data = {
                'seat_id': player.seat_id,
                'name': player.name,
                'chips': player.chips,
                'current_bet': player.current_bet,
                'status': player.status.name,
                'hole_cards': player.get_hole_cards_str(hidden=hide_cards),
                'is_dealer': player.is_dealer,
                'is_small_blind': player.is_small_blind,
                'is_big_blind': player.is_big_blind
            }
            players_data.append(player_data)
        
        return {
            'phase': self.phase.name,
            'community_cards': [card.to_str() for card in self.community_cards],
            'pot': self.pot,
            'current_bet': self.current_bet,
            'current_player': self.current_player,
            'dealer_position': self.dealer_position,
            'players': players_data,
            'small_blind': self.small_blind,
            'big_blind': self.big_blind
        }

    def __str__(self) -> str:
        """返回游戏状态的可读表示"""
        community_str = " ".join(card.to_display_str() for card in self.community_cards)
        active_count = len(self.get_active_players())
        
        return (f"阶段: {self.phase.name}, "
                f"公共牌: [{community_str}], "
                f"底池: {self.pot}, "
                f"当前下注: {self.current_bet}, "
                f"活跃玩家: {active_count}")

    def __repr__(self) -> str:
        """返回游戏状态的调试表示"""
        return f"GameState(phase={self.phase.name}, pot={self.pot}, players={len(self.players)})"
    
    def clone(self) -> 'GameState':
        """
        创建游戏状态的深拷贝
        用于COW(Copy-on-Write)模式的状态管理
        
        Returns:
            游戏状态的深拷贝
        """
        return copy.deepcopy(self)
    
    def add_event(self, event: str):
        """
        添加游戏事件到日志
        
        Args:
            event: 事件描述
        """
        self.events.append(event)


def _validate_state_invariants(state: GameState):
    """
    验证游戏状态不变式
    确保状态的一致性和合法性
    
    Args:
        state: 要验证的游戏状态
        
    Raises:
        GameStateError: 当状态不一致时
    """
    # 验证底池和下注的一致性
    total_current_bets = sum(p.current_bet for p in state.players)
    if total_current_bets < 0:
        raise GameStateError(f"玩家当前下注总和不能为负数: {total_current_bets}")
    
    # 验证筹码数量的合理性
    for player in state.players:
        if player.chips < 0:
            raise GameStateError(f"玩家{player.seat_id}筹码不能为负数: {player.chips}")
    
    # 验证游戏阶段与公共牌的一致性
    expected_cards = {
        GamePhase.PRE_FLOP: 0,
        GamePhase.FLOP: 3,
        GamePhase.TURN: 4,
        GamePhase.RIVER: 5,
        GamePhase.SHOWDOWN: 5
    }
    
    if state.phase in expected_cards:
        expected_count = expected_cards[state.phase]
        actual_count = len(state.community_cards)
        if actual_count != expected_count:
            raise GameStateError(
                f"阶段{state.phase.name}应有{expected_count}张公共牌，实际{actual_count}张"
            )
    
    state.add_event(f"状态验证通过: {state.phase.name}")


@contextmanager
def phase_transition(state: GameState):
    """
    阶段转换上下文管理器
    提供事务性的状态转换，支持自动回滚
    
    Args:
        state: 游戏状态对象
        
    Yields:
        None
        
    Raises:
        PhaseTransitionError: 当转换失败时
    """
    # 创建状态快照用于回滚
    snapshot = state.clone()
    
    try:
        state.add_event(f"开始阶段转换: {state.phase.name}")
        yield
        
        # 验证转换后的状态
        _validate_state_invariants(state)
        state.add_event(f"阶段转换完成: {state.phase.name}")
        
    except Exception as e:
        # 发生异常时回滚状态
        state.__dict__.update(snapshot.__dict__)
        state.add_event(f"阶段转换回滚: {str(e)}")
        
        # 区分业务异常和系统异常
        if isinstance(e, (GameStateError, PhaseTransitionError)):
            raise  # 业务异常向上抛出
        else:
            # 系统异常包装后抛出
            raise PhaseTransitionError(f"阶段转换失败: {str(e)}") from e 