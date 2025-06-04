"""
游戏不变量检查器

整合所有不变量检查器，提供统一的检查接口。
"""

from typing import List, Dict, Any, Optional
import time

from ..snapshot.types import GameStateSnapshot
from .types import InvariantType, InvariantCheckResult, InvariantError
from .chip_conservation_checker import ChipConservationChecker
from .betting_rules_checker import BettingRulesChecker
from .phase_consistency_checker import PhaseConsistencyChecker

__all__ = ['GameInvariants']


class GameInvariants:
    """游戏不变量检查器
    
    整合所有不变量检查器，提供统一的检查接口。
    支持单独检查和批量检查。
    """
    
    def __init__(self, initial_total_chips: Optional[int] = None, 
                 min_raise_multiplier: float = 2.0):
        """初始化游戏不变量检查器
        
        Args:
            initial_total_chips: 初始总筹码数量
            min_raise_multiplier: 最小加注倍数
        """
        self.chip_checker = ChipConservationChecker(initial_total_chips)
        self.betting_checker = BettingRulesChecker(min_raise_multiplier)
        self.phase_checker = PhaseConsistencyChecker()
        
        self._checkers = {
            InvariantType.CHIP_CONSERVATION: self.chip_checker,
            InvariantType.BETTING_RULES: self.betting_checker,
            InvariantType.PHASE_CONSISTENCY: self.phase_checker
        }
    
    def check_all(self, snapshot: GameStateSnapshot, 
                  raise_on_violation: bool = False) -> Dict[InvariantType, InvariantCheckResult]:
        """检查所有不变量
        
        Args:
            snapshot: 游戏状态快照
            raise_on_violation: 是否在违反时抛出异常
            
        Returns:
            Dict[InvariantType, InvariantCheckResult]: 检查结果字典
            
        Raises:
            InvariantError: 当raise_on_violation=True且有违反时
        """
        results = {}
        all_violations = []
        
        for invariant_type, checker in self._checkers.items():
            result = checker.check(snapshot)
            results[invariant_type] = result
            
            if not result.is_valid:
                all_violations.extend(result.violations)
        
        if raise_on_violation and all_violations:
            critical_violations = [v for v in all_violations if v.severity == 'CRITICAL']
            if critical_violations:
                raise InvariantError(
                    f"发现{len(critical_violations)}个严重不变量违反",
                    all_violations
                )
        
        return results
    
    def check_chip_conservation(self, snapshot: GameStateSnapshot) -> InvariantCheckResult:
        """检查筹码守恒
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            InvariantCheckResult: 检查结果
        """
        return self.chip_checker.check(snapshot)
    
    def check_betting_rules(self, snapshot: GameStateSnapshot) -> InvariantCheckResult:
        """检查下注规则
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            InvariantCheckResult: 检查结果
        """
        return self.betting_checker.check(snapshot)
    
    def check_phase_consistency(self, snapshot: GameStateSnapshot) -> InvariantCheckResult:
        """检查阶段一致性
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            InvariantCheckResult: 检查结果
        """
        return self.phase_checker.check(snapshot)
    
    def is_valid_state(self, snapshot: GameStateSnapshot) -> bool:
        """检查游戏状态是否有效
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            bool: 状态是否有效
        """
        results = self.check_all(snapshot)
        return all(result.is_valid for result in results.values())
    
    def get_violations(self, snapshot: GameStateSnapshot) -> List:
        """获取所有违反记录
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            List[InvariantViolation]: 违反记录列表
        """
        results = self.check_all(snapshot)
        violations = []
        
        for result in results.values():
            violations.extend(result.violations)
        
        return violations
    
    def get_critical_violations(self, snapshot: GameStateSnapshot) -> List:
        """获取严重违反记录
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            List[InvariantViolation]: 严重违反记录列表
        """
        violations = self.get_violations(snapshot)
        return [v for v in violations if v.severity == 'CRITICAL']
    
    def reset_chip_conservation(self, initial_total_chips: int):
        """重置筹码守恒检查器
        
        Args:
            initial_total_chips: 新的初始总筹码数量
        """
        self.chip_checker.reset_initial_chips(initial_total_chips)
    
    def get_performance_stats(self, snapshot: GameStateSnapshot) -> Dict[str, Any]:
        """获取性能统计信息
        
        Args:
            snapshot: 游戏状态快照
            
        Returns:
            Dict[str, Any]: 性能统计信息
        """
        start_time = time.time()
        results = self.check_all(snapshot)
        total_time = time.time() - start_time
        
        stats = {
            'total_check_time': total_time,
            'individual_times': {},
            'total_violations': 0,
            'critical_violations': 0,
            'warning_violations': 0,
            'info_violations': 0
        }
        
        for invariant_type, result in results.items():
            stats['individual_times'][invariant_type.name] = result.check_duration
            stats['total_violations'] += len(result.violations)
            
            for violation in result.violations:
                if violation.severity == 'CRITICAL':
                    stats['critical_violations'] += 1
                elif violation.severity == 'WARNING':
                    stats['warning_violations'] += 1
                elif violation.severity == 'INFO':
                    stats['info_violations'] += 1
        
        return stats
    
    @classmethod
    def create_for_game(cls, snapshot: GameStateSnapshot, 
                       min_raise_multiplier: float = 2.0) -> 'GameInvariants':
        """为特定游戏创建不变量检查器
        
        Args:
            snapshot: 初始游戏状态快照
            min_raise_multiplier: 最小加注倍数
            
        Returns:
            GameInvariants: 配置好的不变量检查器
        """
        # 从快照中计算初始总筹码
        initial_chips = sum(player.chips for player in snapshot.players) + snapshot.pot.total_pot
        
        return cls(
            initial_total_chips=initial_chips,
            min_raise_multiplier=min_raise_multiplier
        )
    
    def validate_and_raise(self, snapshot: GameStateSnapshot, 
                          context: str = "游戏操作") -> None:
        """验证状态并在违反时抛出异常
        
        Args:
            snapshot: 游戏状态快照
            context: 操作上下文描述
            
        Raises:
            InvariantError: 当有严重违反时
        """
        violations = self.get_critical_violations(snapshot)
        
        if violations:
            raise InvariantError(
                f"{context}后发现{len(violations)}个严重不变量违反",
                violations
            ) 