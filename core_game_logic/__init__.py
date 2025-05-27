#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
德州扑克核心游戏逻辑模块
提供平台独立的游戏逻辑实现

新的模块化结构：
- core: 核心基础组件（枚举、卡牌、玩家、配置等）
- game: 游戏逻辑（状态管理、控制器、事件系统）
- betting: 下注系统（行动验证、底池管理、边池计算）
- phases: 游戏阶段（翻牌前、翻牌、转牌、河牌、摊牌）
- evaluator: 牌力评估（手牌排名、比较）
"""

# 从各子模块导入主要组件
from .core import (
    Suit, Rank, SeatStatus, GamePhase, ActionType, Action,
    Card, CardPool, Deck, Player,
    GameConfig, PlayerConfig,
    TexasHoldemError, InvalidActionError, GameStateError
)

from .game import (
    GameState, GameController,
    GameEvent, EventType, EventBus
)

from .betting import (
    ActionValidator, PotManager,
    SidePot, calculate_side_pots, validate_side_pot_calculation
)

from .phases import (
    BasePhase, PreFlopPhase, FlopPhase, TurnPhase, RiverPhase, ShowdownPhase
)

from .evaluator import (
    HandRank, SimpleEvaluator
)

__all__ = [
    # 核心基础组件
    'Suit', 'Rank', 'SeatStatus', 'GamePhase', 'ActionType', 'Action',
    'Card', 'CardPool', 'Deck', 'Player',
    'GameConfig', 'PlayerConfig',
    'TexasHoldemError', 'InvalidActionError', 'GameStateError',
    
    # 游戏逻辑
    'GameState', 'GameController',
    'GameEvent', 'EventType', 'EventBus',
    
    # 下注系统
    'ActionValidator', 'PotManager',
    'SidePot', 'calculate_side_pots', 'validate_side_pot_calculation',
    
    # 游戏阶段
    'BasePhase', 'PreFlopPhase', 'FlopPhase', 'TurnPhase', 'RiverPhase', 'ShowdownPhase',
    
    # 牌力评估
    'HandRank', 'SimpleEvaluator',
] 