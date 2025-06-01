"""德州扑克CLI渲染模块.

这个模块负责将游戏状态快照渲染为命令行界面显示，
实现显示逻辑与核心游戏逻辑的分离。
"""

from typing import List, Optional
from v2.core import GameSnapshot, SeatStatus, Phase, Card, Suit, Rank
from v2.controller import HandResult


class CLIRenderer:
    """CLI渲染器.
    
    负责将游戏状态快照渲染为命令行界面显示。
    所有渲染方法都是纯函数，仅依赖传入的快照数据。
    """
    
    @staticmethod
    def render_game_header(hand_count: int, num_players: int, initial_chips: int, human_seat: int) -> str:
        """渲染游戏头部信息.
        
        Args:
            hand_count: 手牌计数
            num_players: 玩家数量
            initial_chips: 初始筹码
            human_seat: 人类玩家座位号
            
        Returns:
            格式化的头部信息字符串
        """
        lines = [
            "=== 德州扑克 v2 CLI ===",
            f"玩家数: {num_players}, 初始筹码: {initial_chips}",
            f"您是玩家 {human_seat}",
            "",
            f"=== 第 {hand_count} 手牌 ==="
        ]
        return "\n".join(lines)
    
    @staticmethod
    def render_game_state(snapshot: GameSnapshot, human_seat: int) -> str:
        """渲染当前游戏状态.
        
        Args:
            snapshot: 游戏状态快照
            human_seat: 人类玩家座位号
            
        Returns:
            格式化的游戏状态字符串
        """
        lines = []
        
        # 基本信息
        lines.append(f"阶段: {snapshot.phase.name}")
        lines.append(f"底池: {snapshot.pot}")
        lines.append(f"当前最高下注: {snapshot.current_bet}")
        
        # 公共牌
        if snapshot.community_cards:
            cards_str = " ".join([CLIRenderer._format_card(card) 
                                for card in snapshot.community_cards])
            lines.append(f"公共牌: {cards_str}")
        
        # 玩家状态
        lines.append("")
        lines.append("玩家状态:")
        for player in snapshot.players:
            player_line = CLIRenderer._render_player_status(
                player, snapshot.current_player, human_seat
            )
            lines.append(f"  {player_line}")
        
        return "\n".join(lines)
    
    @staticmethod
    def render_action_prompt(player_name: str, chips: int, available_actions: List[tuple]) -> str:
        """渲染行动提示.
        
        Args:
            player_name: 玩家名称
            chips: 玩家筹码
            available_actions: 可用行动列表 [(action_type, description, amount), ...]
            
        Returns:
            格式化的行动提示字符串
        """
        lines = [
            f"轮到 {player_name} 行动 (筹码: {chips})",
            "可用行动:"
        ]
        
        for i, (_, description, _) in enumerate(available_actions):
            lines.append(f"  {i + 1}. {description}")
        
        return "\n".join(lines)
    
    @staticmethod
    def render_hand_result(result: HandResult, snapshot: GameSnapshot) -> str:
        """渲染手牌结果.
        
        Args:
            result: 手牌结果
            snapshot: 最终游戏状态快照
            
        Returns:
            格式化的结果字符串
        """
        lines = [
            "",
            "=== 手牌结果 ===",
            f"底池总额: {result.pot_amount}"
        ]
        
        if result.winner_ids:
            if len(result.winner_ids) == 1:
                winner = next(p for p in snapshot.players if p.seat_id == result.winner_ids[0])
                lines.append(f"获胜者: {winner.name}")
            else:
                winner_names = [p.name for p in snapshot.players if p.seat_id in result.winner_ids]
                lines.append(f"平局获胜者: {', '.join(winner_names)}")
            
            if result.winning_hand_description:
                lines.append(f"获胜牌型: {result.winning_hand_description}")
        
        # 显示边池信息
        if result.side_pots:
            lines.append("")
            lines.append("边池分配:")
            for i, side_pot in enumerate(result.side_pots):
                lines.append(f"  边池 {i+1}: {side_pot.amount} 筹码")
                eligible_names = [p.name for p in snapshot.players 
                                if p.seat_id in side_pot.eligible_players]
                lines.append(f"    参与者: {', '.join(eligible_names)}")
        
        return "\n".join(lines)
    
    @staticmethod
    def render_ai_action(player_name: str, action_description: str) -> str:
        """渲染AI行动信息.
        
        Args:
            player_name: AI玩家名称
            action_description: 行动描述
            
        Returns:
            格式化的AI行动字符串
        """
        return f"{player_name} {action_description}"
    
    @staticmethod
    def render_phase_transition(old_phase: Phase, new_phase: Phase) -> str:
        """渲染阶段转换信息.
        
        Args:
            old_phase: 旧阶段
            new_phase: 新阶段
            
        Returns:
            格式化的阶段转换字符串
        """
        return f"阶段转换: {old_phase.name} -> {new_phase.name}"
    
    @staticmethod
    def render_error_message(error: str) -> str:
        """渲染错误信息.
        
        Args:
            error: 错误描述
            
        Returns:
            格式化的错误信息字符串
        """
        return f"错误: {error}"
    
    @staticmethod
    def render_game_over(reason: str) -> str:
        """渲染游戏结束信息.
        
        Args:
            reason: 结束原因
            
        Returns:
            格式化的游戏结束字符串
        """
        return f"游戏结束: {reason}"
    
    @staticmethod
    def _format_card(card: Card) -> str:
        """格式化单张牌的显示.
        
        Args:
            card: 扑克牌对象
            
        Returns:
            格式化的牌面字符串
        """
        # 使用Unicode符号美化显示
        suit_symbols = {
            Suit.HEARTS: '♥',
            Suit.DIAMONDS: '♦', 
            Suit.CLUBS: '♣',
            Suit.SPADES: '♠'
        }
        
        rank_symbols = {
            Rank.ACE: 'A',
            Rank.KING: 'K', 
            Rank.QUEEN: 'Q',
            Rank.JACK: 'J',
            Rank.TEN: '10',
            Rank.NINE: '9',
            Rank.EIGHT: '8',
            Rank.SEVEN: '7',
            Rank.SIX: '6',
            Rank.FIVE: '5',
            Rank.FOUR: '4',
            Rank.THREE: '3',
            Rank.TWO: '2'
        }
        
        suit_symbol = suit_symbols.get(card.suit, card.suit.value)
        rank_symbol = rank_symbols.get(card.rank, str(card.rank.value))
        
        return f"{rank_symbol}{suit_symbol}"
    
    @staticmethod
    def _render_player_status(player, current_player_id: Optional[int], human_seat: int) -> str:
        """渲染单个玩家状态.
        
        Args:
            player: 玩家快照对象
            current_player_id: 当前行动玩家ID
            human_seat: 人类玩家座位号
            
        Returns:
            格式化的玩家状态字符串
        """
        # 状态标记
        status_str = ""
        if player.status == SeatStatus.FOLDED:
            status_str = " [弃牌]"
        elif player.status == SeatStatus.ALL_IN:
            status_str = " [全押]"
        elif player.status == SeatStatus.OUT:
            status_str = " [出局]"
        
        # 当前玩家标记
        current_marker = " <-- 当前" if current_player_id == player.seat_id else ""
        
        # 手牌显示（仅对人类玩家）
        cards_str = ""
        if player.seat_id == human_seat and player.hole_cards:
            cards = [CLIRenderer._format_card(card) for card in player.hole_cards]
            cards_str = f" 手牌: {' '.join(cards)}"
        
        return f"{player.name}: 筹码={player.chips}, 当前下注={player.current_bet}{status_str}{current_marker}{cards_str}" 