"""
游戏控制器
实现游戏主循环和阶段转换的集中管理
"""

from typing import Optional
from .game_state import GameState, phase_transition
from .phases.base_phase import BasePhase
from .exceptions import PhaseTransitionError


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
    
    def set_phase(self, phase: BasePhase):
        """
        设置当前游戏阶段
        
        Args:
            phase: 新的游戏阶段实例
        """
        self.current_phase = phase
    
    def next_phase(self) -> bool:
        """
        转换到下一个游戏阶段
        使用事务性转换确保状态一致性
        
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
        
        # 处理行动
        continue_round = self.current_phase.act(action)
        
        # 如果下注轮结束，尝试转换到下一阶段
        if not continue_round:
            return self.next_phase()
        
        return True
    
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