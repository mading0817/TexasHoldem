"""
AI玩家模块
包含AI策略、事件系统和决策引擎
Phase 3: 事件系统 & AI策略 实现
"""

# 导出AI策略相关类
from .ai_strategy import (
    AIStrategy,
    AIDecisionContext,
    ConservativeStrategy,
    AggressiveStrategy,
    RandomStrategy,
    StrategyFactory
)

# 导出事件总线相关类
from .event_bus import (
    EventBus,
    EventSubscription,
    EventLogger,
    EventAggregator,
    get_global_event_bus,
    set_global_event_bus,
    event_handler
)

# 导出AI决策引擎相关类
from .ai_engine import (
    AIDecisionEngine,
    AIPlayerProfile,
    HandStrengthEvaluator,
    create_standard_ai_engine,
    setup_demo_ais
)

__all__ = [
    # AI策略
    'AIStrategy',
    'AIDecisionContext', 
    'ConservativeStrategy',
    'AggressiveStrategy',
    'RandomStrategy',
    'StrategyFactory',
    
    # 事件总线
    'EventBus',
    'EventSubscription',
    'EventLogger',
    'EventAggregator',
    'get_global_event_bus',
    'set_global_event_bus',
    'event_handler',
    
    # AI决策引擎
    'AIDecisionEngine',
    'AIPlayerProfile', 
    'HandStrengthEvaluator',
    'create_standard_ai_engine',
    'setup_demo_ais'
] 