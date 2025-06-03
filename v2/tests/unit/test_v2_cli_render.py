"""CLI渲染器单元测试.

测试CLI渲染器的各种渲染功能，确保Snapshot数据能正确转换为显示字符串。
"""

import pytest
from v2.ui.cli.render import CLIRenderer
from v2.core import (
    GameSnapshot, Card, Rank, Suit, Phase, SeatStatus,
    Player
)
from v2.controller import HandResult


@pytest.mark.unit
@pytest.mark.fast
class TestCLIRenderer:
    """CLI渲染器测试类."""
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_render_game_header(self):
        """测试游戏头部渲染."""
        header = CLIRenderer.render_game_header(
            hand_count=1,
            num_players=4,
            initial_chips=1000,
            human_seat=0
        )
        
        assert "德州扑克 v2 CLI" in header
        assert "玩家数: 4" in header
        assert "初始筹码: 1000" in header
        assert "您是玩家 0" in header
        assert "第 1 手牌" in header
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_render_game_state_basic(self):
        """测试基本游戏状态渲染."""
        # 创建测试快照
        players = [
            type('Player', (), {
                'seat_id': 0,
                'name': 'You',
                'chips': 1000,
                'current_bet': 0,
                'status': SeatStatus.ACTIVE,
                'hole_cards': []
            })(),
            type('Player', (), {
                'seat_id': 1,
                'name': 'AI_1',
                'chips': 950,
                'current_bet': 50,
                'status': SeatStatus.ACTIVE,
                'hole_cards': []
            })()
        ]
        
        snapshot = type('GameSnapshot', (), {
            'phase': Phase.PRE_FLOP,
            'pot': 75,
            'current_bet': 50,
            'current_player': 0,
            'community_cards': [],
            'players': players
        })()
        
        result = CLIRenderer.render_game_state(snapshot, human_seat=0)
        
        assert "阶段: PRE_FLOP" in result
        assert "底池: 75" in result
        assert "当前最高下注: 50" in result
        assert "玩家状态:" in result
        assert "You: 筹码=1000" in result
        assert "AI_1: 筹码=950" in result
        assert "<-- 当前" in result
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_render_game_state_with_community_cards(self):
        """测试包含公共牌的游戏状态渲染."""
        community_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN)
        ]
        
        players = [
            type('Player', (), {
                'seat_id': 0,
                'name': 'You',
                'chips': 1000,
                'current_bet': 0,
                'status': SeatStatus.ACTIVE,
                'hole_cards': [
                    Card(Suit.CLUBS, Rank.JACK),
                    Card(Suit.HEARTS, Rank.TEN)
                ]
            })()
        ]
        
        snapshot = type('GameSnapshot', (), {
            'phase': Phase.FLOP,
            'pot': 150,
            'current_bet': 0,
            'current_player': 0,
            'community_cards': community_cards,
            'players': players
        })()
        
        result = CLIRenderer.render_game_state(snapshot, human_seat=0)
        
        assert "阶段: FLOP" in result
        assert "公共牌:" in result
        assert "A♥" in result
        assert "K♠" in result
        assert "Q♦" in result
        assert "手牌: J♣ 10♥" in result
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_render_player_status_variations(self):
        """测试不同玩家状态的渲染."""
        # 测试弃牌状态
        folded_player = type('Player', (), {
            'seat_id': 1,
            'name': 'Folded_Player',
            'chips': 900,
            'current_bet': 0,
            'status': SeatStatus.FOLDED,
            'hole_cards': []
        })()
        
        result = CLIRenderer._render_player_status(folded_player, None, 0)
        assert "[弃牌]" in result
        
        # 测试全押状态
        allin_player = type('Player', (), {
            'seat_id': 2,
            'name': 'AllIn_Player',
            'chips': 0,
            'current_bet': 500,
            'status': SeatStatus.ALL_IN,
            'hole_cards': []
        })()
        
        result = CLIRenderer._render_player_status(allin_player, None, 0)
        assert "[全押]" in result
        
        # 测试当前玩家标记
        current_player = type('Player', (), {
            'seat_id': 3,
            'name': 'Current_Player',
            'chips': 800,
            'current_bet': 50,
            'status': SeatStatus.ACTIVE,
            'hole_cards': []
        })()
        
        result = CLIRenderer._render_player_status(current_player, 3, 0)
        assert "<-- 当前" in result
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_format_card(self):
        """测试扑克牌格式化."""
        # 测试各种牌面
        ace_hearts = Card(Suit.HEARTS, Rank.ACE)
        assert CLIRenderer._format_card(ace_hearts) == "A♥"
        
        king_spades = Card(Suit.SPADES, Rank.KING)
        assert CLIRenderer._format_card(king_spades) == "K♠"
        
        ten_diamonds = Card(Suit.DIAMONDS, Rank.TEN)
        assert CLIRenderer._format_card(ten_diamonds) == "10♦"
        
        two_clubs = Card(Suit.CLUBS, Rank.TWO)
        assert CLIRenderer._format_card(two_clubs) == "2♣"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_render_action_prompt(self):
        """测试行动提示渲染."""
        available_actions = [
            ('FOLD', '弃牌', 0),
            ('CALL', '跟注 (50)', 50),
            ('RAISE', '加注', 0)
        ]
        
        result = CLIRenderer.render_action_prompt(
            player_name="You",
            chips=1000,
            available_actions=available_actions
        )
        
        assert "轮到 You 行动" in result
        assert "筹码: 1000" in result
        assert "可用行动:" in result
        assert "1. 弃牌" in result
        assert "2. 跟注 (50)" in result
        assert "3. 加注" in result
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_render_hand_result_single_winner(self):
        """测试单个获胜者的手牌结果渲染."""
        players = [
            type('Player', (), {
                'seat_id': 0,
                'name': 'Winner',
                'chips': 1500,
                'current_bet': 0,
                'status': SeatStatus.ACTIVE,
                'hole_cards': []
            })(),
            type('Player', (), {
                'seat_id': 1,
                'name': 'Loser',
                'chips': 500,
                'current_bet': 0,
                'status': SeatStatus.FOLDED,
                'hole_cards': []
            })()
        ]
        
        snapshot = type('GameSnapshot', (), {
            'players': players
        })()
        
        result_obj = HandResult(
            winner_ids=[0],
            pot_amount=200,
            winning_hand_description="一对A",
            side_pots=[]
        )
        
        result = CLIRenderer.render_hand_result(result_obj, snapshot)
        
        assert "手牌结果" in result
        assert "底池总额: 200" in result
        assert "获胜者: Winner" in result
        assert "获胜牌型: 一对A" in result
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_render_hand_result_multiple_winners(self):
        """测试多个获胜者的手牌结果渲染."""
        players = [
            type('Player', (), {
                'seat_id': 0,
                'name': 'Winner1',
                'chips': 1000,
                'current_bet': 0,
                'status': SeatStatus.ACTIVE,
                'hole_cards': []
            })(),
            type('Player', (), {
                'seat_id': 1,
                'name': 'Winner2',
                'chips': 1000,
                'current_bet': 0,
                'status': SeatStatus.ACTIVE,
                'hole_cards': []
            })()
        ]
        
        snapshot = type('GameSnapshot', (), {
            'players': players
        })()
        
        result_obj = HandResult(
            winner_ids=[0, 1],
            pot_amount=200,
            winning_hand_description="同花",
            side_pots=[]
        )
        
        result = CLIRenderer.render_hand_result(result_obj, snapshot)
        
        assert "平局获胜者: Winner1, Winner2" in result
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_render_ai_action(self):
        """测试AI行动渲染."""
        result = CLIRenderer.render_ai_action("AI_1", "跟注 50")
        assert result == "AI_1 跟注 50"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_render_phase_transition(self):
        """测试阶段转换渲染."""
        result = CLIRenderer.render_phase_transition(Phase.PRE_FLOP, Phase.FLOP)
        assert result == "阶段转换: PRE_FLOP -> FLOP"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_render_error_message(self):
        """测试错误信息渲染."""
        result = CLIRenderer.render_error_message("无效的行动")
        assert result == "错误: 无效的行动"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_render_game_over(self):
        """测试游戏结束渲染."""
        result = CLIRenderer.render_game_over("活跃玩家不足")
        assert result == "游戏结束: 活跃玩家不足"
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_render_game_state_public_cards_count(self):
        """测试公共牌数量正确渲染."""
        # 测试FLOP阶段（3张公共牌）
        flop_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN)
        ]
        
        players = [
            type('Player', (), {
                'seat_id': 0,
                'name': 'Test',
                'chips': 1000,
                'current_bet': 0,
                'status': SeatStatus.ACTIVE,
                'hole_cards': []
            })()
        ]
        
        snapshot = type('GameSnapshot', (), {
            'phase': Phase.FLOP,
            'pot': 150,
            'current_bet': 0,
            'current_player': 0,
            'community_cards': flop_cards,
            'players': players
        })()
        
        result = CLIRenderer.render_game_state(snapshot, human_seat=0)
        
        # 验证包含3张公共牌
        public_cards_section = result.split("公共牌:")[1].split("\n")[0] if "公共牌:" in result else ""
        public_card_symbols = public_cards_section.count('♥') + public_cards_section.count('♠') + public_cards_section.count('♦') + public_cards_section.count('♣')
        assert public_card_symbols == 3
        
        # 测试TURN阶段（4张公共牌）
        turn_cards = flop_cards + [Card(Suit.CLUBS, Rank.JACK)]
        snapshot.community_cards = turn_cards
        snapshot.phase = Phase.TURN
        
        result = CLIRenderer.render_game_state(snapshot, human_seat=0)
        public_cards_section = result.split("公共牌:")[1].split("\n")[0] if "公共牌:" in result else ""
        public_card_symbols = public_cards_section.count('♥') + public_cards_section.count('♠') + public_cards_section.count('♦') + public_cards_section.count('♣')
        assert public_card_symbols == 4
        
        # 测试RIVER阶段（5张公共牌）
        river_cards = turn_cards + [Card(Suit.HEARTS, Rank.NINE)]
        snapshot.community_cards = river_cards
        snapshot.phase = Phase.RIVER
        
        result = CLIRenderer.render_game_state(snapshot, human_seat=0)
        public_cards_section = result.split("公共牌:")[1].split("\n")[0] if "公共牌:" in result else ""
        public_card_symbols = public_cards_section.count('♥') + public_cards_section.count('♠') + public_cards_section.count('♦') + public_cards_section.count('♣')
        assert public_card_symbols == 5 