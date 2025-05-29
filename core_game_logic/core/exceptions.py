"""
德州扑克游戏业务异常定义
区分业务异常(向上抛)和系统异常(内部回滚)
"""


class PokerGameError(Exception):
    """德州扑克游戏基础异常类"""
    pass


class InvalidActionError(PokerGameError):
    """无效玩家行动异常"""
    pass


class InsufficientChipsError(PokerGameError):
    """筹码不足异常"""
    pass


class GameStateError(PokerGameError):
    """游戏状态错误异常"""
    pass


class PhaseTransitionError(PokerGameError):
    """阶段转换错误异常"""
    pass


class GameConfigError(PokerGameError):
    """游戏配置错误异常"""
    pass 