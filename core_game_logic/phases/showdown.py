"""
摊牌阶段实现
进行牌型比较和底池分配
"""

from typing import Optional, Dict, List, TYPE_CHECKING
from .base_phase import BasePhase
from ..core.enums import GamePhase, SeatStatus
from ..evaluator import SimpleEvaluator

if TYPE_CHECKING:
    from ..action_validator import ValidatedAction
    from ..player import Player


class ShowdownPhase(BasePhase):
    """
    摊牌阶段
    负责牌型比较和底池分配
    """
    
    def __init__(self, state):
        super().__init__(state)
        self.evaluator = SimpleEvaluator()
    
    def enter(self):
        """
        进入摊牌阶段的初始化操作
        1. 设置游戏阶段
        2. 准备摊牌
        """
        # 确保游戏状态正确
        if self.state.phase != GamePhase.SHOWDOWN:
            self.state.phase = GamePhase.SHOWDOWN
        
        # 记录事件
        players_in_hand = self.state.get_players_in_hand()
        self.state.add_event(f"摊牌阶段开始，{len(players_in_hand)}名玩家参与")
        
        # 只有在多人摊牌时才显示手牌，单人获胜不显示
        if len(players_in_hand) > 1:
            # 显示所有玩家手牌
            for player in players_in_hand:
                cards_str = player.get_hole_cards_str(hidden=False)
                print(f"{player.name}手牌: {cards_str}")
            
            # 显示公共牌
            community_str = " ".join(card.to_display_str() for card in self.state.community_cards)
            print(f"公共牌: {community_str}")
    
    def act(self, action: 'ValidatedAction') -> bool:
        """
        摊牌阶段不需要玩家行动
        
        Args:
            action: 经过验证的玩家行动
            
        Returns:
            False，摊牌阶段不需要行动
        """
        # 摊牌阶段不需要玩家行动
        return False
    
    def exit(self) -> Optional['BasePhase']:
        """
        退出摊牌阶段
        进行牌型比较和底池分配
        
        Returns:
            None，游戏结束
        """
        # 进行摊牌和底池分配
        self._conduct_showdown()
        
        # 游戏结束，返回None
        return None
    
    def _conduct_showdown(self):
        """进行摊牌和底池分配"""
        players_in_hand = self.state.get_players_in_hand()
        
        if len(players_in_hand) == 0:
            self.state.add_event("没有玩家参与摊牌")
            return
        
        if len(players_in_hand) == 1:
            # 只有一个玩家，直接获得所有底池
            winner = players_in_hand[0]
            winner.add_chips(self.state.pot)
            self.state.add_event(f"{winner.name}获得底池{self.state.pot}（其他玩家弃牌）")
            self.state.pot = 0
            return
        
        # 多个玩家摊牌
        self._evaluate_and_award()
    
    def _evaluate_and_award(self):
        """评估牌型并分配底池"""
        players_in_hand = self.state.get_players_in_hand()
        
        # 评估每个玩家的牌型
        player_hands = {}
        for player in players_in_hand:
            try:
                hand_result = self.evaluator.evaluate_hand(
                    player.hole_cards, 
                    self.state.community_cards
                )
                player_hands[player.seat_id] = hand_result
                print(f"{player.name}: {hand_result}")
            except Exception as e:
                print(f"{player.name}牌型评估失败: {e}")
                # 给予最低牌型（高牌2）
                from ..evaluator import HandResult, HandRank
                player_hands[player.seat_id] = HandResult(HandRank.HIGH_CARD, 2)
        
        # 直接分配底池（简化版本，不使用边池）
        self._award_simple_pot(player_hands, players_in_hand)
    
    def _award_simple_pot(self, player_hands: Dict[int, 'HandResult'], players_in_hand: List['Player']):
        """简单分配底池（MVP版本，不考虑边池）"""
        if self.state.pot == 0:
            return
        
        # 找出最佳牌型
        best_hand = None
        winners = []
        
        for player in players_in_hand:
            hand = player_hands.get(player.seat_id)
            if hand is None:
                continue
            
            if best_hand is None or hand.compare_to(best_hand) > 0:
                best_hand = hand
                winners = [player]
            elif hand.compare_to(best_hand) == 0:
                winners.append(player)
        
        if winners:
            # 记录分配前的底池总额
            total_pot = self.state.pot
            
            # 分配底池
            pot_per_winner = total_pot // len(winners)
            remainder = total_pot % len(winners)
            
            for i, winner in enumerate(winners):
                award = pot_per_winner + (1 if i < remainder else 0)
                winner.add_chips(award)
                print(f"{winner.name}获得主池{award}")
            
            # 清空底池
            self.state.pot = 0 