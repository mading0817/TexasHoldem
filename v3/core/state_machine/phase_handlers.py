"""
阶段处理器实现

提供各个游戏阶段的具体处理逻辑。
"""

from typing import Dict, Any, List
from .types import GamePhase, GameEvent, GameContext, PhaseHandler

__all__ = [
    'InitHandler',
    'PreFlopHandler', 
    'FlopHandler',
    'TurnHandler',
    'RiverHandler',
    'ShowdownHandler',
    'FinishedHandler'
]


class BasePhaseHandler:
    """基础阶段处理器，提供通用功能"""
    
    def __init__(self, phase: GamePhase):
        self.phase = phase
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入阶段的默认处理"""
        print(f"进入阶段: {self.phase.name}")
    
    def on_exit(self, ctx: GameContext) -> None:
        """退出阶段的默认处理"""
        print(f"退出阶段: {self.phase.name}")
    
    def can_transition_to(self, target_phase: GamePhase, ctx: GameContext) -> bool:
        """检查是否可以转换到目标阶段"""
        # 基本的转换规则
        valid_transitions = {
            GamePhase.INIT: [GamePhase.PRE_FLOP],
            GamePhase.PRE_FLOP: [GamePhase.FLOP, GamePhase.SHOWDOWN, GamePhase.FINISHED],
            GamePhase.FLOP: [GamePhase.TURN, GamePhase.SHOWDOWN, GamePhase.FINISHED],
            GamePhase.TURN: [GamePhase.RIVER, GamePhase.SHOWDOWN, GamePhase.FINISHED],
            GamePhase.RIVER: [GamePhase.SHOWDOWN, GamePhase.FINISHED],
            GamePhase.SHOWDOWN: [GamePhase.FINISHED],
            GamePhase.FINISHED: [GamePhase.PRE_FLOP, GamePhase.INIT]
        }
        
        return target_phase in valid_transitions.get(self.phase, [])


class InitHandler(BasePhaseHandler):
    """初始化阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.INIT)
    
    def on_enter(self, ctx: GameContext) -> None:
        """初始化游戏状态"""
        super().on_enter(ctx)
        # 重置游戏状态
        ctx.community_cards.clear()
        ctx.pot_total = 0
        ctx.current_bet = 0
        ctx.active_player_id = None
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """初始化阶段不处理玩家行动"""
        return GameEvent(
            event_type="INVALID_ACTION",
            data={"reason": "初始化阶段不能执行玩家行动"},
            source_phase=self.phase
        )


class PreFlopHandler(BasePhaseHandler):
    """翻牌前阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.PRE_FLOP)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入翻牌前阶段"""
        super().on_enter(ctx)
        # 发手牌，设置盲注等逻辑
        self._setup_blinds(ctx)
        self._deal_hole_cards(ctx)
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理翻牌前的玩家行动"""
        action_type = action.get('type')
        
        if action_type == 'fold':
            return self._handle_fold(ctx, player_id, action)
        elif action_type == 'call':
            return self._handle_call(ctx, player_id, action)
        elif action_type == 'raise':
            return self._handle_raise(ctx, player_id, action)
        elif action_type == 'check':
            return self._handle_check(ctx, player_id, action)
        else:
            return GameEvent(
                event_type="INVALID_ACTION",
                data={"reason": f"未知的行动类型: {action_type}"},
                source_phase=self.phase
            )
    
    def _setup_blinds(self, ctx: GameContext) -> None:
        """设置盲注"""
        # 获取玩家列表
        player_ids = list(ctx.players.keys())
        if len(player_ids) < 2:
            return
        
        # 初始化所有玩家的下注字段
        for player_id in player_ids:
            player = ctx.players[player_id]
            if 'current_bet' not in player:
                player['current_bet'] = 0
            if 'total_bet_this_hand' not in player:
                player['total_bet_this_hand'] = 0
        
        # 确定盲注位置 (简化：第一个玩家小盲，第二个玩家大盲)
        small_blind_player = player_ids[0]
        big_blind_player = player_ids[1]
        
        # 扣除小盲注
        if ctx.players[small_blind_player]['chips'] >= ctx.small_blind:
            ctx.players[small_blind_player]['chips'] -= ctx.small_blind
            ctx.players[small_blind_player]['current_bet'] = ctx.small_blind
            ctx.players[small_blind_player]['total_bet_this_hand'] = ctx.small_blind
            ctx.pot_total += ctx.small_blind
        
        # 扣除大盲注
        if ctx.players[big_blind_player]['chips'] >= ctx.big_blind:
            ctx.players[big_blind_player]['chips'] -= ctx.big_blind
            ctx.players[big_blind_player]['current_bet'] = ctx.big_blind
            ctx.players[big_blind_player]['total_bet_this_hand'] = ctx.big_blind
            ctx.pot_total += ctx.big_blind
        
        # 设置当前下注为大盲注
        ctx.current_bet = ctx.big_blind
    
    def _deal_hole_cards(self, ctx: GameContext) -> None:
        """发手牌"""
        # 简化的发牌逻辑：给每个活跃玩家发2张牌
        from v3.core.deck import Card
        from v3.core.deck.types import Suit, Rank
        
        # 创建一些测试用的牌
        test_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN),
            Card(Suit.CLUBS, Rank.JACK)
        ]
        
        card_index = 0
        for player_id in ctx.players:
            if ctx.players[player_id].get('active', True):
                # 给每个玩家发2张牌
                ctx.players[player_id]['hole_cards'] = [
                    test_cards[card_index % len(test_cards)],
                    test_cards[(card_index + 1) % len(test_cards)]
                ]
                card_index += 2
    
    def _handle_fold(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理弃牌行动"""
        if player_id in ctx.players:
            ctx.players[player_id]['status'] = 'folded'
        
        return GameEvent(
            event_type="PLAYER_FOLDED",
            data={"player_id": player_id},
            source_phase=self.phase
        )
    
    def _handle_call(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理跟注行动"""
        call_amount = ctx.current_bet
        return GameEvent(
            event_type="PLAYER_CALLED",
            data={"player_id": player_id, "amount": call_amount},
            source_phase=self.phase
        )
    
    def _handle_raise(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理加注行动"""
        raise_amount = action.get('amount', 0)
        if raise_amount <= ctx.current_bet:
            return GameEvent(
                event_type="INVALID_ACTION",
                data={"reason": "加注金额必须大于当前下注"},
                source_phase=self.phase
            )
        
        ctx.current_bet = raise_amount
        return GameEvent(
            event_type="PLAYER_RAISED",
            data={"player_id": player_id, "amount": raise_amount},
            source_phase=self.phase
        )
    
    def _handle_check(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理过牌行动"""
        if ctx.current_bet > 0:
            return GameEvent(
                event_type="INVALID_ACTION",
                data={"reason": "有下注时不能过牌"},
                source_phase=self.phase
            )
        
        return GameEvent(
            event_type="PLAYER_CHECKED",
            data={"player_id": player_id},
            source_phase=self.phase
        )


class FlopHandler(BasePhaseHandler):
    """翻牌阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.FLOP)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入翻牌阶段"""
        super().on_enter(ctx)
        # 发三张公共牌
        self._deal_flop_cards(ctx)
        # 重置下注轮
        self._reset_betting_round(ctx)
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理翻牌阶段的玩家行动"""
        # 复用PreFlopHandler的行动处理逻辑
        pre_flop_handler = PreFlopHandler()
        event = pre_flop_handler.handle_player_action(ctx, player_id, action)
        # 更新事件的源阶段
        return GameEvent(
            event_type=event.event_type,
            data=event.data,
            source_phase=self.phase
        )
    
    def _deal_flop_cards(self, ctx: GameContext) -> None:
        """发翻牌（三张公共牌）"""
        from v3.core.deck import Card
        from v3.core.deck.types import Suit, Rank
        
        # 简化的发牌逻辑
        if len(ctx.community_cards) == 0:
            flop_cards = [
                Card(Suit.HEARTS, Rank.TEN),
                Card(Suit.DIAMONDS, Rank.NINE),
                Card(Suit.CLUBS, Rank.EIGHT)
            ]
            ctx.community_cards.extend(flop_cards)
    
    def _reset_betting_round(self, ctx: GameContext) -> None:
        """重置下注轮"""
        # 重置全局下注
        ctx.current_bet = 0
        
        # 重置所有玩家的当前下注
        for player_id in ctx.players:
            ctx.players[player_id]['current_bet'] = 0


class TurnHandler(BasePhaseHandler):
    """转牌阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.TURN)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入转牌阶段"""
        super().on_enter(ctx)
        # 发第四张公共牌
        self._deal_turn_card(ctx)
        # 重置下注轮
        ctx.current_bet = 0
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理转牌阶段的玩家行动"""
        pre_flop_handler = PreFlopHandler()
        event = pre_flop_handler.handle_player_action(ctx, player_id, action)
        return GameEvent(
            event_type=event.event_type,
            data=event.data,
            source_phase=self.phase
        )
    
    def _deal_turn_card(self, ctx: GameContext) -> None:
        """发转牌（第四张公共牌）"""
        if len(ctx.community_cards) == 3:
            ctx.community_cards.append('Card4')


class RiverHandler(BasePhaseHandler):
    """河牌阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.RIVER)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入河牌阶段"""
        super().on_enter(ctx)
        # 发第五张公共牌
        self._deal_river_card(ctx)
        # 重置下注轮
        ctx.current_bet = 0
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """处理河牌阶段的玩家行动"""
        pre_flop_handler = PreFlopHandler()
        event = pre_flop_handler.handle_player_action(ctx, player_id, action)
        return GameEvent(
            event_type=event.event_type,
            data=event.data,
            source_phase=self.phase
        )
    
    def _deal_river_card(self, ctx: GameContext) -> None:
        """发河牌（第五张公共牌）"""
        if len(ctx.community_cards) == 4:
            ctx.community_cards.append('Card5')


class ShowdownHandler(BasePhaseHandler):
    """摊牌阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.SHOWDOWN)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入摊牌阶段"""
        super().on_enter(ctx)
        # 比较手牌，确定胜者
        self._determine_winners(ctx)
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """摊牌阶段不处理玩家行动"""
        return GameEvent(
            event_type="INVALID_ACTION",
            data={"reason": "摊牌阶段不能执行玩家行动"},
            source_phase=self.phase
        )
    
    def _determine_winners(self, ctx: GameContext) -> None:
        """确定胜者并分配奖池"""
        # 简化的胜者确定逻辑
        active_players = [pid for pid, pdata in ctx.players.items() 
                         if pdata.get('status') != 'folded']
        
        if active_players:
            # 简单地选择第一个活跃玩家作为胜者
            winner = active_players[0]
            ctx.players[winner]['winnings'] = ctx.pot_total
            ctx.pot_total = 0


class FinishedHandler(BasePhaseHandler):
    """结束阶段处理器"""
    
    def __init__(self):
        super().__init__(GamePhase.FINISHED)
    
    def on_enter(self, ctx: GameContext) -> None:
        """进入结束阶段"""
        super().on_enter(ctx)
        # 清理本手牌的状态
        self._cleanup_hand(ctx)
    
    def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
        """结束阶段处理新手牌开始"""
        action_type = action.get('type')
        
        if action_type == 'start_new_hand':
            return GameEvent(
                event_type="HAND_START",
                data={"new_hand": True},
                source_phase=self.phase
            )
        
        return GameEvent(
            event_type="INVALID_ACTION",
            data={"reason": f"结束阶段不支持行动: {action_type}"},
            source_phase=self.phase
        )
    
    def _cleanup_hand(self, ctx: GameContext) -> None:
        """清理本手牌的状态"""
        # 重置玩家状态
        for player_data in ctx.players.values():
            player_data.pop('hole_cards', None)
            player_data.pop('status', None)
            player_data.pop('winnings', None) 