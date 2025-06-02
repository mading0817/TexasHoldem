"""
测试快照导出导入功能.

验证PokerController的export_snapshot和import_snapshot方法的正确性，
确保游戏状态可以完整地导出和恢复。
"""

import json
import pytest
from unittest.mock import Mock

from v2.controller.poker_controller import PokerController
from v2.core import (
    GameState, Player, Card, Suit, Rank, Phase, SeatStatus, ActionType,
    EventBus
)
from v2.ai.simple_ai import SimpleAI


class TestSnapshotExportImport:
    """测试快照导出导入功能."""
    
    def setup_method(self):
        """设置测试环境."""
        self.event_bus = EventBus()
        self.ai_strategy = SimpleAI()
        self.controller = PokerController(
            ai_strategy=self.ai_strategy,
            event_bus=self.event_bus
        )
        
        # 创建测试玩家
        self.players = [
            Player(seat_id=0, name="Alice", chips=1000, is_human=True),
            Player(seat_id=1, name="Bob", chips=800, is_human=False),
            Player(seat_id=2, name="Charlie", chips=1200, is_human=False)
        ]
        
        # 添加玩家到游戏
        for player in self.players:
            self.controller._game_state.add_player(player)
    
    def test_export_snapshot_basic(self):
        """测试基本的快照导出功能."""
        # 开始新手牌
        self.controller.start_new_hand()
        
        # 导出快照
        export_data = self.controller.export_snapshot()
        
        # 验证导出数据结构
        assert isinstance(export_data, dict)
        assert 'version' in export_data
        assert 'game_state' in export_data
        assert 'controller_state' in export_data
        
        # 验证版本信息
        assert export_data['version'] == '2.0'
        
        # 验证游戏状态数据
        game_state = export_data['game_state']
        assert 'phase' in game_state
        assert 'players' in game_state
        assert 'pot' in game_state
        assert 'current_bet' in game_state
        assert 'community_cards' in game_state
        assert 'events' in game_state
        
        # 验证控制器状态
        controller_state = export_data['controller_state']
        assert 'hand_in_progress' in controller_state
        assert 'has_ai_strategy' in controller_state
        assert controller_state['hand_in_progress'] is True
        assert controller_state['has_ai_strategy'] is True
    
    def test_export_snapshot_with_cards(self):
        """测试包含手牌和公共牌的快照导出."""
        # 开始新手牌
        self.controller.start_new_hand()
        
        # 手动设置一些公共牌用于测试
        test_cards = [
            Card(Suit.HEARTS, Rank.ACE),
            Card(Suit.SPADES, Rank.KING),
            Card(Suit.DIAMONDS, Rank.QUEEN)
        ]
        self.controller._game_state.community_cards = test_cards
        self.controller._game_state.phase = Phase.FLOP
        
        # 导出快照
        export_data = self.controller.export_snapshot()
        
        # 验证公共牌数据
        community_cards = export_data['game_state']['community_cards']
        assert len(community_cards) == 3
        assert community_cards[0] == {'suit': 'HEARTS', 'rank': 'ACE'}
        assert community_cards[1] == {'suit': 'SPADES', 'rank': 'KING'}
        assert community_cards[2] == {'suit': 'DIAMONDS', 'rank': 'QUEEN'}
        
        # 验证玩家手牌数据
        players_data = export_data['game_state']['players']
        for player_data in players_data:
            assert 'hole_cards' in player_data
            assert isinstance(player_data['hole_cards'], list)
            # 每个玩家应该有2张手牌
            assert len(player_data['hole_cards']) == 2
            for card_data in player_data['hole_cards']:
                assert 'suit' in card_data
                assert 'rank' in card_data
    
    def test_export_snapshot_serializable(self):
        """测试导出的数据可以序列化为JSON."""
        # 开始新手牌
        self.controller.start_new_hand()
        
        # 导出快照
        export_data = self.controller.export_snapshot()
        
        # 尝试序列化为JSON
        json_str = json.dumps(export_data, indent=2)
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        
        # 尝试反序列化
        parsed_data = json.loads(json_str)
        assert parsed_data == export_data
    
    def test_import_snapshot_basic(self):
        """测试基本的快照导入功能."""
        # 开始新手牌并导出
        self.controller.start_new_hand()
        original_snapshot = self.controller.get_snapshot()
        export_data = self.controller.export_snapshot()
        
        # 创建新的控制器
        new_controller = PokerController(event_bus=self.event_bus)
        
        # 导入快照
        success = new_controller.import_snapshot(export_data)
        assert success is True
        
        # 验证导入后的状态
        imported_snapshot = new_controller.get_snapshot()
        
        # 比较关键状态
        assert imported_snapshot.phase == original_snapshot.phase
        assert imported_snapshot.pot == original_snapshot.pot
        assert imported_snapshot.current_bet == original_snapshot.current_bet
        assert imported_snapshot.dealer_position == original_snapshot.dealer_position
        assert imported_snapshot.current_player == original_snapshot.current_player
        assert len(imported_snapshot.players) == len(original_snapshot.players)
    
    def test_import_snapshot_deep_equality(self):
        """测试导入后的状态深度相等."""
        # 开始新手牌
        self.controller.start_new_hand()
        
        # 设置一些特定状态用于测试
        self.controller._game_state.pot = 100
        self.controller._game_state.current_bet = 20
        self.controller._game_state.phase = Phase.FLOP
        
        # 设置公共牌
        test_cards = [
            Card(Suit.CLUBS, Rank.TEN),
            Card(Suit.HEARTS, Rank.JACK),
            Card(Suit.SPADES, Rank.QUEEN)
        ]
        self.controller._game_state.community_cards = test_cards
        
        # 导出和导入
        export_data = self.controller.export_snapshot()
        new_controller = PokerController(event_bus=self.event_bus)
        success = new_controller.import_snapshot(export_data)
        assert success is True
        
        # 获取快照进行比较
        original_snapshot = self.controller.get_snapshot()
        imported_snapshot = new_controller.get_snapshot()
        
        # 详细比较各个字段
        assert imported_snapshot.phase == original_snapshot.phase
        assert imported_snapshot.pot == original_snapshot.pot
        assert imported_snapshot.current_bet == original_snapshot.current_bet
        assert imported_snapshot.last_raiser == original_snapshot.last_raiser
        assert imported_snapshot.last_raise_amount == original_snapshot.last_raise_amount
        assert imported_snapshot.dealer_position == original_snapshot.dealer_position
        assert imported_snapshot.current_player == original_snapshot.current_player
        assert imported_snapshot.small_blind == original_snapshot.small_blind
        assert imported_snapshot.big_blind == original_snapshot.big_blind
        assert imported_snapshot.street_index == original_snapshot.street_index
        
        # 比较公共牌
        assert len(imported_snapshot.community_cards) == len(original_snapshot.community_cards)
        for i, card in enumerate(imported_snapshot.community_cards):
            original_card = original_snapshot.community_cards[i]
            assert card.suit == original_card.suit
            assert card.rank == original_card.rank
        
        # 比较玩家状态
        assert len(imported_snapshot.players) == len(original_snapshot.players)
        for i, player in enumerate(imported_snapshot.players):
            original_player = original_snapshot.players[i]
            assert player.seat_id == original_player.seat_id
            assert player.name == original_player.name
            assert player.chips == original_player.chips
            assert player.current_bet == original_player.current_bet
            assert player.status == original_player.status
            assert player.is_dealer == original_player.is_dealer
            assert player.is_small_blind == original_player.is_small_blind
            assert player.is_big_blind == original_player.is_big_blind
            assert player.is_human == original_player.is_human
            assert player.last_action_type == original_player.last_action_type
            
            # 比较手牌
            assert len(player.hole_cards) == len(original_player.hole_cards)
            for j, card in enumerate(player.hole_cards):
                original_card = original_player.hole_cards[j]
                assert card.suit == original_card.suit
                assert card.rank == original_card.rank
    
    def test_import_snapshot_invalid_data(self):
        """测试导入无效数据的错误处理."""
        new_controller = PokerController(event_bus=self.event_bus)
        
        # 测试非字典数据
        with pytest.raises(ValueError, match="导入数据必须是字典格式"):
            new_controller.import_snapshot("invalid_data")
        
        # 测试缺少版本信息
        with pytest.raises(ValueError, match="导入数据缺少版本信息"):
            new_controller.import_snapshot({})
        
        # 测试缺少游戏状态信息
        with pytest.raises(ValueError, match="导入数据缺少游戏状态信息"):
            new_controller.import_snapshot({'version': '2.0'})
        
        # 测试不支持的版本
        with pytest.raises(ValueError, match="不支持的数据版本"):
            new_controller.import_snapshot({
                'version': '1.0',
                'game_state': {}
            })
    
    def test_import_snapshot_malformed_data(self):
        """测试导入格式错误数据的处理."""
        new_controller = PokerController(event_bus=self.event_bus)
        
        # 测试缺少必要字段的游戏状态
        malformed_data = {
            'version': '2.0',
            'game_state': {
                'phase': 'PRE_FLOP',
                # 缺少players字段
                'pot': 0,
                'current_bet': 0
            }
        }
        
        with pytest.raises(ValueError, match="导入数据格式错误"):
            new_controller.import_snapshot(malformed_data)
    
    def test_export_import_round_trip(self):
        """测试完整的导出导入往返过程."""
        # 开始新手牌
        self.controller.start_new_hand()
        
        # 执行一些行动来改变游戏状态
        # 这里我们手动修改状态来模拟游戏进行
        self.controller._game_state.pot = 50
        self.controller._game_state.current_bet = 10
        self.controller._game_state.phase = Phase.TURN
        
        # 添加一些事件
        self.controller._game_state.add_event("测试事件1")
        self.controller._game_state.add_event("测试事件2")
        
        # 导出状态
        export_data = self.controller.export_snapshot()
        
        # 创建新控制器并导入
        new_controller = PokerController(event_bus=self.event_bus)
        success = new_controller.import_snapshot(export_data)
        assert success is True
        
        # 再次导出新控制器的状态
        second_export = new_controller.export_snapshot()
        
        # 比较两次导出的数据（应该相同）
        assert export_data['game_state']['phase'] == second_export['game_state']['phase']
        assert export_data['game_state']['pot'] == second_export['game_state']['pot']
        assert export_data['game_state']['current_bet'] == second_export['game_state']['current_bet']
        assert export_data['game_state']['events'] == second_export['game_state']['events']
        
        # 验证玩家数据
        original_players = export_data['game_state']['players']
        imported_players = second_export['game_state']['players']
        assert len(original_players) == len(imported_players)
        
        for i, (orig_player, imp_player) in enumerate(zip(original_players, imported_players)):
            assert orig_player['seat_id'] == imp_player['seat_id']
            assert orig_player['name'] == imp_player['name']
            assert orig_player['chips'] == imp_player['chips']
            assert orig_player['status'] == imp_player['status']
            assert orig_player['hole_cards'] == imp_player['hole_cards']
    
    def test_export_import_with_different_phases(self):
        """测试不同游戏阶段的导出导入."""
        phases_to_test = [Phase.PRE_FLOP, Phase.FLOP, Phase.TURN, Phase.RIVER, Phase.SHOWDOWN]
        
        for phase in phases_to_test:
            # 重置控制器
            self.controller = PokerController(event_bus=self.event_bus)
            for player in self.players:
                self.controller._game_state.add_player(player)
            
            # 设置特定阶段
            self.controller._game_state.phase = phase
            
            # 导出导入
            export_data = self.controller.export_snapshot()
            new_controller = PokerController(event_bus=self.event_bus)
            success = new_controller.import_snapshot(export_data)
            
            assert success is True
            imported_snapshot = new_controller.get_snapshot()
            assert imported_snapshot.phase == phase
    
    def test_export_import_preserves_controller_state(self):
        """测试导出导入保持控制器状态."""
        # 开始新手牌
        self.controller.start_new_hand()
        assert self.controller._hand_in_progress is True
        
        # 导出状态
        export_data = self.controller.export_snapshot()
        
        # 创建新控制器（初始状态hand_in_progress为False）
        new_controller = PokerController(event_bus=self.event_bus)
        assert new_controller._hand_in_progress is False
        
        # 导入状态
        success = new_controller.import_snapshot(export_data)
        assert success is True
        
        # 验证控制器状态被正确恢复
        assert new_controller._hand_in_progress is True
    
    def test_export_import_with_events(self):
        """测试事件日志的导出导入."""
        # 清空初始事件（玩家加入事件）
        self.controller._game_state.clear_events()
        
        # 添加一些事件
        test_events = [
            "游戏开始",
            "Alice 下注 10",
            "Bob 跟注",
            "Charlie 弃牌"
        ]
        
        for event in test_events:
            self.controller._game_state.add_event(event)
        
        # 导出导入
        export_data = self.controller.export_snapshot()
        new_controller = PokerController(event_bus=self.event_bus)
        success = new_controller.import_snapshot(export_data)
        assert success is True
        
        # 验证事件日志
        imported_snapshot = new_controller.get_snapshot()
        assert imported_snapshot.events == test_events 