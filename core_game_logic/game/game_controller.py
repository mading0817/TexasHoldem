"""
游戏控制器
实现游戏主循环和阶段转换的集中管理
"""

from typing import Optional
from .game_state import GameState, phase_transition
from ..phases.base_phase import BasePhase
from ..core.exceptions import PhaseTransitionError
from ..core.deck import Deck
from ..phases.preflop import PreFlopPhase
from ..core.enums import GamePhase, Action, SeatStatus
from ..betting.action_validator import ActionValidator


class GameController:
    """
    德州扑克游戏控制器
    负责游戏流程的顶层调度和阶段转换管理
    """
    
    def __init__(self, state: GameState):
        """
        初始化游戏控制器
        
        Args:
            state: 游戏状态对象
        """
        self.state = state
        self.current_phase: Optional[BasePhase] = None
        self._is_running = False
        self.action_validator = ActionValidator()  # 添加ActionValidator
        
        # 直接设置phase为第一个阶段
        if state.phase == GamePhase.PRE_FLOP:
            self.current_phase = PreFlopPhase(state)
    
    # === 测试兼容性方法 ===
    @property
    def game_state(self):
        """为了向后兼容，提供game_state属性访问"""
        return self.state
    
    @game_state.setter
    def game_state(self, value):
        """为了向后兼容，提供game_state属性设置"""
        self.state = value
    
    def start_new_hand(self):
        """为测试提供的手牌开始方法包装"""
        # 重置游戏状态为新手牌
        self.state.add_event("开始新手牌")
        
        # 首先将所有当前下注收集到底池中（重要：避免筹码丢失）
        self.state.collect_bets_to_pot()
        
        # 处理前一轮的剩余底池（如果有的话）
        if self.state.pot > 0:
            # 找到仍在游戏中的玩家
            players_in_hand = self.state.get_players_in_hand()
            if players_in_hand:
                # 如果只有一个玩家仍在游戏中，将底池给他
                if len(players_in_hand) == 1:
                    winner = players_in_hand[0]
                    winner.add_chips(self.state.pot)
                    self.state.add_event(f"{winner.name}获得剩余底池{self.state.pot}")
                else:
                    # 如果有多个玩家，平分底池（简化处理）
                    pot_per_player = self.state.pot // len(players_in_hand)
                    remainder = self.state.pot % len(players_in_hand)
                    for i, player in enumerate(players_in_hand):
                        amount = pot_per_player + (1 if i < remainder else 0)
                        if amount > 0:
                            player.add_chips(amount)
                    self.state.add_event(f"剩余底池{self.state.pot}被平分给{len(players_in_hand)}名玩家")
        
        # 重置玩家状态（现在安全了，因为current_bet已被收集到底池）
        for player in self.state.players:
            player.reset_for_new_hand()
        
        # 重置游戏状态
        self.state.pot = 0
        self.state.current_bet = 0
        self.state.community_cards = []
        self.state.current_player = None
        self.state.street_index = 0
        self.state.last_raiser = None
        
        # 移动庄家位置并设置盲注
        active_players = [p for p in self.state.players if p.chips > 0]
        if len(active_players) >= 2:
            # 找到下一个有筹码的玩家作为庄家
            all_player_seats = [p.seat_id for p in self.state.players]
            current_dealer_index = all_player_seats.index(self.state.dealer_position)
            
            # 循环寻找下一个有筹码的玩家
            for i in range(1, len(all_player_seats) + 1):
                next_index = (current_dealer_index + i) % len(all_player_seats)
                next_seat = all_player_seats[next_index]
                next_player = self.state.get_player_by_seat(next_seat)
                
                if next_player and next_player.chips > 0:
                    self.state.dealer_position = next_seat
                    break
            else:
                # 如果没找到，保持当前庄家（这种情况不应该发生，因为我们已经检查了有足够玩家）
                pass
            
            # 设置所有玩家的庄家标记
            for player in self.state.players:
                player.is_dealer = (player.seat_id == self.state.dealer_position)
            
            # 设置盲注
            self.state.set_blinds()
            
            # 创建新牌组并发牌
            self.state.deck = Deck()
            self.state.deck.shuffle()
            
            # 发手牌
            for _ in range(2):
                for player in active_players:
                    if player.chips > 0:
                        card = self.state.deck.deal_card()
                        player.hole_cards.append(card)
            
            # 初始化PreFlop阶段
            self.current_phase = PreFlopPhase(self.state)
            self.state.phase = GamePhase.PRE_FLOP
        
    def get_current_player(self):
        """获取当前行动玩家"""
        return self.state.get_current_player()
        
    def get_small_blind(self):
        """获取小盲注数值"""
        return self.state.small_blind
        
    def get_big_blind(self):
        """获取大盲注数值"""
        return self.state.big_blind
    # === 测试兼容性方法结束 ===
    
    def set_phase(self, phase: BasePhase):
        """
        设置当前游戏阶段
        
        Args:
            phase: 新的游戏阶段实例
        """
        self.current_phase = phase
    
    def next_phase(self) -> bool:
        """
        转换到下一个游戏阶段 - 修复版本控制问题
        使用事务性转换确保状态一致性，统一处理阶段推进
        
        Returns:
            True如果成功转换，False如果游戏结束
            
        Raises:
            PhaseTransitionError: 当转换失败时
        """
        if not self.current_phase:
            return False
        
        with phase_transition(self.state):
            # 退出当前阶段并获取下一阶段
            next_phase = self.current_phase.exit()
            
            if next_phase is None:
                # 游戏结束
                self.current_phase = None
                self.state.add_event("游戏结束")
                return False
            
            # *** 重要修复：统一在Controller层处理阶段推进 ***
            # 因为Phase层不再直接调用 state.advance_phase()
            old_phase = self.state.phase
            self.state.advance_phase()
            self.state.add_event(f"阶段转换: {old_phase.name} -> {self.state.phase.name}")
            
            # 设置新阶段并进入
            self.current_phase = next_phase
            self.current_phase.enter()
            
            return True
    
    def process_action(self, action) -> bool:
        """
        处理玩家行动
        
        Args:
            action: 玩家行动（待实现ActionValidator后完善类型）
            
        Returns:
            True如果行动处理成功，False如果下注轮结束
        """
        if not self.current_phase:
            raise PhaseTransitionError("没有活跃的游戏阶段")
        
        # 确保action是Action类型
        if not isinstance(action, Action):
            raise ValueError(f"无效的行动类型: {type(action)}")
        
        # 获取执行行动的玩家
        if action.player_seat is None:
            # 如果没有指定玩家座位，使用当前玩家
            action.player_seat = self.state.current_player
        
        player = self.state.get_player_by_seat(action.player_seat)
        if not player:
            raise ValueError(f"找不到座位{action.player_seat}的玩家")
        
        # 使用ActionValidator验证和转换行动
        try:
            validated_action = self.action_validator.validate(self.state, player, action)
        except Exception as e:
            raise ValueError(f"行动验证失败: {e}")
        
        # 处理验证后的行动
        continue_round = self.current_phase.act(validated_action)
        
        # 如果下注轮结束，尝试转换到下一阶段
        if not continue_round:
            return self.next_phase()
        
        return True
    
    def validate_action(self, action) -> 'ActionValidationResult':
        """
        验证玩家行动但不执行
        用于测试和预检查
        
        Args:
            action: 玩家行动
            
        Returns:
            ActionValidationResult: 验证结果对象
        """
        try:
            # 确保action是Action类型
            if not isinstance(action, Action):
                return ActionValidationResult(False, f"无效的行动类型: {type(action)}")
            
            # 获取执行行动的玩家
            if action.player_seat is None:
                action.player_seat = self.state.current_player
            
            player = self.state.get_player_by_seat(action.player_seat)
            if not player:
                return ActionValidationResult(False, f"找不到座位{action.player_seat}的玩家")
            
            # 使用ActionValidator验证
            validated_action = self.action_validator.validate(self.state, player, action)
            return ActionValidationResult(True, "验证通过", validated_action)
            
        except Exception as e:
            return ActionValidationResult(False, f"验证失败: {e}")

    def run_game_loop(self):
        """
        运行游戏主循环
        这是一个基础框架，具体的输入处理将在CLI模块中实现
        """
        if not self.current_phase:
            raise PhaseTransitionError("游戏阶段未初始化")
        
        self._is_running = True
        self.state.add_event("游戏开始")
        
        # 进入初始阶段
        self.current_phase.enter()
        
        while self._is_running and self.current_phase:
            # 这里是游戏主循环的核心
            # 具体的玩家输入处理将在CLI模块中实现
            # 现在只是一个框架
            
            # 检查是否需要转换阶段
            if self.current_phase.is_round_complete():
                if not self.next_phase():
                    break  # 游戏结束
        
        self.state.add_event("游戏循环结束")
    
    def stop_game(self):
        """停止游戏循环"""
        self._is_running = False
        self.state.add_event("游戏被停止")
    
    def get_game_status(self) -> dict:
        """
        获取游戏状态摘要
        
        Returns:
            游戏状态摘要字典
        """
        return {
            'is_running': self._is_running,
            'current_phase': self.current_phase.__class__.__name__ if self.current_phase else None,
            'game_phase': self.state.phase.name,
            'active_players': len(self.state.get_active_players()),
            'total_players': len(self.state.players),
            'pot': self.state.pot,
            'current_bet': self.state.current_bet,
            'dealer_position': self.state.dealer_position,
            'small_blind': self.state.small_blind,
            'big_blind': self.state.big_blind,
            'events_count': len(self.state.events)
        }
    
    def get_players_status(self) -> list:
        """
        获取所有玩家的状态信息
        
        Returns:
            玩家状态列表
        """
        players_status = []
        for player in self.state.players:
            player_info = {
                'seat_id': player.seat_id,
                'name': player.name,
                'chips': player.chips,
                'current_bet': player.current_bet,
                'status': player.status.name,
                'is_dealer': player.is_dealer,
                'is_small_blind': player.is_small_blind,
                'is_big_blind': player.is_big_blind,
                'can_act': player.can_act()
            }
            players_status.append(player_info)
        return players_status
    
    def get_full_game_state(self) -> dict:
        """
        获取完整的游戏状态（用于序列化）
        
        Returns:
            完整的游戏状态字典
        """
        return self.state.to_dict()
    
    def get_game_state_for_player(self, seat_id: int) -> dict:
        """
        获取特定玩家视角的游戏状态
        
        Args:
            seat_id: 玩家座位号
            
        Returns:
            玩家视角的游戏状态字典
        """
        return self.state.to_dict(viewer_seat=seat_id)
    
    def get_game_events(self) -> list:
        """
        获取所有游戏事件
        
        Returns:
            游戏事件列表
        """
        return self.state.events.copy()
    
    def get_recent_events(self, count: int) -> list:
        """
        获取最近的游戏事件
        
        Args:
            count: 要获取的事件数量
            
        Returns:
            最近的游戏事件列表
        """
        if count <= 0:
            return []
        return self.state.events[-count:] if self.state.events else []
    
    def get_game_statistics(self) -> dict:
        """
        获取游戏统计信息
        
        Returns:
            游戏统计信息字典
        """
        active_players = self.state.get_active_players()
        folded_players = [p for p in self.state.players if p.status.name == 'FOLDED']
        all_in_players = [p for p in self.state.players if p.status.name == 'ALL_IN']
        
        total_chips_in_play = sum(p.chips + p.current_bet for p in self.state.players) + self.state.pot
        
        return {
            'total_pot': self.state.pot,
            'current_bet': self.state.current_bet,
            'active_players_count': len(active_players),
            'folded_players_count': len(folded_players),
            'all_in_players_count': len(all_in_players),
            'total_players': len(self.state.players),
            'total_chips_in_play': total_chips_in_play,
            'game_phase': self.state.phase.name,
            'events_count': len(self.state.events)
        }
    
    def is_valid_player_turn(self, seat_id: int) -> bool:
        """
        检查是否是指定玩家的回合
        
        Args:
            seat_id: 玩家座位号
            
        Returns:
            True如果是该玩家的回合
        """
        return self.state.current_player == seat_id
    
    def can_player_act(self, player) -> bool:
        """
        检查玩家是否可以行动
        
        Args:
            player: 玩家对象
            
        Returns:
            True如果玩家可以行动
        """
        return player.can_act()
    
    def can_game_continue(self) -> bool:
        """
        检查游戏是否可以继续
        
        Returns:
            True如果游戏可以继续
        """
        players_in_hand = self.state.get_players_in_hand()
        return len(players_in_hand) > 1
    
    # === 测试兼容性方法 ===
    
    def get_current_phase(self):
        """
        获取当前游戏阶段
        返回阶段枚举值，兼容测试代码
        """
        # 返回GamePhase枚举值而不是阶段对象
        return self.state.phase
    
    def is_betting_round_complete(self) -> bool:
        """
        检查当前下注轮是否完成
        
        Returns:
            True如果下注轮完成
        """
        if not self.current_phase:
            return True
        return self.current_phase.is_round_complete()
    
    def get_dealer_position(self) -> int:
        """
        获取庄家位置
        
        Returns:
            庄家座位号
        """
        return self.state.dealer_position
    
    def get_total_pot(self) -> int:
        """
        获取总底池数量（包括玩家的当前下注）
        
        Returns:
            底池总数（中央底池 + 所有玩家当前下注）
        """
        # 中央底池 + 所有玩家的当前下注
        total_current_bets = sum(player.current_bet for player in self.state.players)
        return self.state.pot + total_current_bets
    
    def advance_phase(self):
        """为测试兼容性添加的阶段推进方法"""
        return self.next_phase()
    
    def get_community_cards(self):
        """获取公共牌"""
        return self.state.community_cards
    
    def determine_winners(self):
        """确定获胜者 - 实际实现"""
        players_in_hand = self.state.get_players_in_hand()
        
        # 如果只有一个玩家，直接返回
        if len(players_in_hand) <= 1:
            return players_in_hand
        
        # 如果没有公共牌（可能出现在极端情况），返回所有玩家
        if len(self.state.community_cards) < 5:
            return players_in_hand
        
        try:
            # 导入评估器
            from ..evaluator import SimpleEvaluator
            evaluator = SimpleEvaluator()
            
            # 评估每个玩家的手牌
            player_hands = {}
            for player in players_in_hand:
                if len(player.hole_cards) == 2:  # 确保玩家有完整手牌
                    try:
                        hand_result = evaluator.evaluate_hand(
                            player.hole_cards, 
                            self.state.community_cards
                        )
                        player_hands[player] = hand_result
                    except Exception as e:
                        # 如果评估失败，给予最低牌型
                        print(f"玩家{player.name}手牌评估失败: {e}")
                        from ..evaluator import HandResult, HandRank
                        player_hands[player] = HandResult(HandRank.HIGH_CARD, 2)
            
            if not player_hands:
                return []
            
            # 找出最佳牌型
            best_hand = None
            winners = []
            
            for player, hand in player_hands.items():
                if best_hand is None or hand.compare_to(best_hand) > 0:
                    best_hand = hand
                    winners = [player]
                elif hand.compare_to(best_hand) == 0:
                    winners.append(player)
            
            return winners
            
        except ImportError as e:
            print(f"无法导入评估器: {e}")
            # 降级到简单实现：返回第一个玩家
            return [players_in_hand[0]] if players_in_hand else []
        except Exception as e:
            print(f"胜负判定出错: {e}")
            # 出错时返回所有玩家（平分）
            return players_in_hand
    
    # === 新增快照查询方法 ===
    
    def get_game_snapshot(self):
        """
        获取游戏状态快照（只读）
        用于Strategy接口和测试
        
        Returns:
            包含完整游戏状态的快照对象，从PokerSimulator导入
        """
        # 注意：这里我们将在测试中通过PokerSimulator来访问快照
        # 这个方法主要用于接口一致性
        return {
            'phase': self.state.phase,
            'pot': self.state.pot,
            'current_bet': self.state.current_bet,
            'community_cards': tuple(self.state.community_cards),
            'current_player': self.state.get_current_player(),
            'dealer_position': self.state.dealer_position,
            'small_blind': self.state.small_blind,
            'big_blind': self.state.big_blind,
            'players': [
                {
                    'seat_id': p.seat_id,
                    'name': p.name,
                    'chips': p.chips,
                    'current_bet': p.current_bet,
                    'hole_cards': tuple(p.hole_cards),
                    'status': p.status,
                    'is_dealer': p.is_dealer,
                    'can_act': p.can_act()
                }
                for p in self.state.players
            ]
        }
    
    def is_hand_over(self) -> bool:
        """
        判断当前手牌是否已结束
        
        Returns:
            True如果手牌已结束
        """
        # 检查是否只剩一个或零个活跃玩家
        active_players = [p for p in self.state.players 
                         if p.status not in [SeatStatus.FOLDED, SeatStatus.OUT]]
        
        if len(active_players) <= 1:
            return True
        
        # 检查是否已到达摊牌阶段且下注轮完成
        if (self.state.phase == GamePhase.SHOWDOWN and 
            self.is_betting_round_complete()):
            return True
        
        return False
    
    def finish_hand(self):
        """
        完成当前手牌并返回结果
        清理状态为下一手牌做准备
        
        Returns:
            dict: 手牌结果信息
        """
        # 收集结果信息
        result = {
            'completed': True,
            'final_pot': self.get_total_pot(),
            'active_players': len([p for p in self.state.players if p.chips > 0]),
            'winners': [],
            'phase_reached': self.state.phase
        }
        
        # 确定胜者
        winners = self.determine_winners()
        if winners:
            result['winners'] = [w.name for w in winners]
        
        # 清理当前手牌状态（为下一手牌做准备）
        # 收集所有当前下注到底池
        self.state.collect_bets_to_pot()
        
        # 重置玩家手牌状态
        for player in self.state.players:
            player.reset_for_new_hand()
        
        # 重置游戏状态
        self.state.current_player = None
        self.state.last_raiser = None
        self.state.street_index = 0
        
        return result
    
    def debug_method_for_cache_test(self):
        """调试方法 - 用于测试文件是否被重新加载"""
        return "GameController cache test - file reloaded successfully!"


class ActionValidationResult:
    """Action验证结果"""
    def __init__(self, is_valid: bool, message: str = "", validated_action=None):
        self.is_valid = is_valid
        self.message = message
        self.validated_action = validated_action 