"""
不变量检查器基础类

定义不变量检查器的抽象基类和通用功能。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import time
import uuid

from ..snapshot.types import GameStateSnapshot
from .types import InvariantType, InvariantViolation, InvariantCheckResult

__all__ = ['BaseInvariantChecker']


class BaseInvariantChecker(ABC):
    """不变量检查器基础抽象类"""
    
    def __init__(self, invariant_type: InvariantType):
        """初始化检查器
        
        Args:
            invariant_type: 不变量类型
        """
        self.invariant_type = invariant_type
        self._violations: List[InvariantViolation] = []
    
    @abstractmethod
    def _perform_check(self, snapshot: GameStateSnapshot) -> bool:
        """执行具体的不变量检查逻辑
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 检查是否通过
        """
        pass
    
    def check(self, snapshot: GameStateSnapshot) -> InvariantCheckResult:
        """执行不变量检查
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            InvariantCheckResult: 检查结果
        """
        start_time = time.time()
        self._violations.clear()
        
        try:
            is_valid = self._perform_check(snapshot)
            check_duration = time.time() - start_time
            
            if is_valid:
                return InvariantCheckResult.create_success(
                    invariant_type=self.invariant_type,
                    check_duration=check_duration
                )
            else:
                return InvariantCheckResult.create_failure(
                    invariant_type=self.invariant_type,
                    violations=self._violations.copy(),
                    check_duration=check_duration
                )
        except Exception as e:
            check_duration = time.time() - start_time
            # 创建异常违反记录
            violation = self._create_violation(
                description=f"检查过程中发生异常: {str(e)}",
                severity='CRITICAL',
                context={'exception_type': type(e).__name__, 'exception_message': str(e)}
            )
            return InvariantCheckResult.create_failure(
                invariant_type=self.invariant_type,
                violations=[violation],
                check_duration=check_duration
            )
    
    def _create_violation(self, description: str, severity: str = 'CRITICAL', 
                         context: Dict[str, Any] = None) -> InvariantViolation:
        """创建违反记录
        
        Args:
            description: 违反描述
            severity: 严重程度
            context: 上下文信息
            
        Returns:
            InvariantViolation: 违反记录
        """
        if context is None:
            context = {}
            
        violation = InvariantViolation(
            invariant_type=self.invariant_type,
            violation_id=f"{self.invariant_type.name.lower()}_{uuid.uuid4().hex[:8]}",
            description=description,
            severity=severity,
            timestamp=time.time(),
            context=context
        )
        
        self._violations.append(violation)
        return violation
    
    def _get_player_total_chips(self, snapshot: GameStateSnapshot) -> int:
        """获取所有玩家的筹码总和
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            int: 筹码总和
        """
        return sum(player.chips for player in snapshot.players)
    
    def _get_player_total_bets(self, snapshot: GameStateSnapshot) -> int:
        """获取所有玩家的下注总和
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            int: 下注总和
        """
        return sum(player.total_bet_this_hand for player in snapshot.players)
    
    def _get_active_players(self, snapshot: GameStateSnapshot) -> List:
        """获取活跃玩家列表
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            List: 活跃玩家列表
        """
        return [player for player in snapshot.players if player.is_active]
    
    def _validate_snapshot(self, snapshot: GameStateSnapshot) -> bool:
        """验证快照的基本有效性
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 快照是否有效
        """
        if not snapshot:
            self._create_violation("快照为空", 'CRITICAL')
            return False
            
        if not snapshot.players:
            self._create_violation("玩家列表为空", 'CRITICAL')
            return False
            
        if len(snapshot.players) < 2:
            self._create_violation("玩家数量少于2人", 'CRITICAL')
            return False
            
        return True 