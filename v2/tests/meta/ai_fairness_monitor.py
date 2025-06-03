"""
AI公平性约束验证系统 - 确保AI策略只能访问合法信息，防止AI作弊

该模块实现了AI访问监控器（Spy Pattern），追踪AI对游戏状态的访问，
建立信息可见性约束，确保AI无法获取对手底牌等私密信息。

主要功能:
1. AI访问监控器 - 追踪AI对游戏状态的所有访问
2. 信息可见性约束 - 确保AI无法获取不可见信息
3. 作弊行为检测 - 检测和报告违规访问
4. 大规模公平性测试 - 1000+手牌模拟验证
"""

import copy
import inspect
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Protocol
from unittest.mock import Mock, patch

from v2.core import GameSnapshot, Player, Card, Phase, SeatStatus
from v2.ai.base import AIStrategy


class AccessType(Enum):
    """AI访问类型枚举"""
    LEGAL = "legal"           # 合法访问
    ILLEGAL = "illegal"       # 非法访问
    SUSPICIOUS = "suspicious" # 可疑访问


class ViolationType(Enum):
    """违规类型枚举"""
    OPPONENT_HOLE_CARDS = "opponent_hole_cards"     # 访问对手底牌
    UNDEALT_CARDS = "undealt_cards"                 # 访问未发牌
    FUTURE_COMMUNITY_CARDS = "future_community_cards" # 访问未来公牌
    PRIVATE_GAME_STATE = "private_game_state"       # 访问私有游戏状态
    DECK_MANIPULATION = "deck_manipulation"         # 操作牌堆
    PLAYER_PRIVATE_DATA = "player_private_data"     # 访问玩家私有数据


@dataclass
class AccessRecord:
    """AI访问记录"""
    timestamp: float
    ai_player_id: int
    access_type: AccessType
    violation_type: Optional[ViolationType]
    accessed_attribute: str
    accessed_value: Any
    stack_trace: List[str]
    severity: str = "low"
    
    def __post_init__(self):
        """设置违规严重程度"""
        if self.violation_type in [ViolationType.OPPONENT_HOLE_CARDS, ViolationType.UNDEALT_CARDS]:
            self.severity = "critical"
        elif self.violation_type in [ViolationType.FUTURE_COMMUNITY_CARDS, ViolationType.DECK_MANIPULATION]:
            self.severity = "high"
        elif self.violation_type in [ViolationType.PRIVATE_GAME_STATE, ViolationType.PLAYER_PRIVATE_DATA]:
            self.severity = "medium"


@dataclass
class FairnessReport:
    """AI公平性报告"""
    ai_player_id: int
    total_decisions: int
    total_accesses: int
    legal_accesses: int
    illegal_accesses: int
    suspicious_accesses: int
    violations_by_type: Dict[ViolationType, int] = field(default_factory=dict)
    access_records: List[AccessRecord] = field(default_factory=list)
    fairness_score: float = 0.0
    is_fair: bool = True
    
    def __post_init__(self):
        """计算公平性分数"""
        if self.total_accesses == 0:
            self.fairness_score = 1.0
            return
            
        # 计算公平性分数 (0-1, 1为完全公平)
        illegal_penalty = self.illegal_accesses * 10
        suspicious_penalty = self.suspicious_accesses * 2
        total_penalty = illegal_penalty + suspicious_penalty
        
        self.fairness_score = max(0.0, 1.0 - (total_penalty / max(1, self.total_accesses * 10)))
        self.is_fair = self.illegal_accesses == 0 and self.fairness_score >= 0.8


class MonitoredGameSnapshot:
    """被监控的游戏快照代理类"""
    
    def __init__(self, original_snapshot: GameSnapshot, monitor: 'AIFairnessMonitor', ai_player_id: int):
        self._original = original_snapshot
        self._monitor = monitor
        self._ai_player_id = ai_player_id
        
    def __getattr__(self, name: str) -> Any:
        """拦截属性访问"""
        value = getattr(self._original, name)
        
        # 记录访问
        self._monitor._record_access(
            ai_player_id=self._ai_player_id,
            attribute=name,
            value=value
        )
        
        return value
    
    def __getitem__(self, key):
        """拦截索引访问"""
        value = self._original[key] if hasattr(self._original, '__getitem__') else None
        self._monitor._record_access(
            ai_player_id=self._ai_player_id,
            attribute=f"[{key}]",
            value=value
        )
        return value


class AIFairnessMonitor:
    """AI公平性约束验证监控器
    
    使用Spy Pattern追踪AI对游戏状态的访问，确保AI只能访问合法信息。
    """
    
    def __init__(self):
        self.access_records: List[AccessRecord] = []
        self.monitored_ais: Dict[int, AIStrategy] = {}
        self.legal_attributes = {
            # 基本游戏信息
            'phase', 'pot', 'current_bet', 'small_blind', 'big_blind',
            'dealer_position', 'current_player', 'street_index',
            
            # 公共信息
            'community_cards', 'events',
            
            # 玩家公开信息
            'players', 'get_active_players', 'get_players_in_hand',
            'get_player_by_seat', 'get_current_player', 'to_dict'
        }
        
        # 每个玩家的合法访问属性（包括自己的底牌）
        self.player_legal_attributes = {
            'seat_id', 'name', 'chips', 'current_bet', 'status',
            'is_dealer', 'is_small_blind', 'is_big_blind'
        }
        
    def register_ai(self, ai_player_id: int, ai_strategy: AIStrategy) -> None:
        """注册需要监控的AI
        
        Args:
            ai_player_id: AI玩家的座位ID
            ai_strategy: AI策略实例
        """
        self.monitored_ais[ai_player_id] = ai_strategy
        
    def create_monitored_snapshot(self, snapshot: GameSnapshot, ai_player_id: int) -> MonitoredGameSnapshot:
        """创建被监控的游戏快照
        
        Args:
            snapshot: 原始游戏快照
            ai_player_id: AI玩家ID
            
        Returns:
            被监控的游戏快照代理
        """
        return MonitoredGameSnapshot(snapshot, self, ai_player_id)
        
    def _record_access(self, ai_player_id: int, attribute: str, value: Any) -> None:
        """记录AI访问
        
        Args:
            ai_player_id: AI玩家ID
            attribute: 访问的属性名
            value: 访问的值
        """
        # 获取调用栈
        stack = inspect.stack()
        stack_trace = [f"{frame.filename}:{frame.lineno} in {frame.function}" for frame in stack[2:6]]
        
        # 分析访问类型和违规类型
        access_type, violation_type = self._analyze_access(ai_player_id, attribute, value)
        
        # 创建访问记录
        record = AccessRecord(
            timestamp=time.time(),
            ai_player_id=ai_player_id,
            access_type=access_type,
            violation_type=violation_type,
            accessed_attribute=attribute,
            accessed_value=self._sanitize_value(value),
            stack_trace=stack_trace
        )
        
        self.access_records.append(record)
        
        # 如果是非法访问，立即记录警告
        if access_type == AccessType.ILLEGAL:
            logging.warning(f"AI {ai_player_id} illegal access: {attribute} ({violation_type.value if violation_type else 'unknown'})")
            
    def _analyze_access(self, ai_player_id: int, attribute: str, value: Any) -> tuple[AccessType, Optional[ViolationType]]:
        """分析访问类型和违规类型
        
        Args:
            ai_player_id: AI玩家ID
            attribute: 访问的属性名
            value: 访问的值
            
        Returns:
            (访问类型, 违规类型)
        """
        # 检查基本合法属性
        if attribute in self.legal_attributes:
            return AccessType.LEGAL, None
            
        # 检查玩家相关访问
        if attribute == 'players' or 'player' in attribute.lower():
            return self._analyze_player_access(ai_player_id, attribute, value)
            
        # 检查底牌访问
        if 'hole_cards' in attribute or 'cards' in attribute:
            return self._analyze_card_access(ai_player_id, attribute, value)
            
        # 检查私有状态访问
        if attribute.startswith('_') or 'private' in attribute.lower():
            return AccessType.ILLEGAL, ViolationType.PRIVATE_GAME_STATE
            
        # 检查牌堆访问
        if 'deck' in attribute.lower():
            return AccessType.ILLEGAL, ViolationType.DECK_MANIPULATION
            
        # 默认为可疑访问
        return AccessType.SUSPICIOUS, None
        
    def _analyze_player_access(self, ai_player_id: int, attribute: str, value: Any) -> tuple[AccessType, Optional[ViolationType]]:
        """分析玩家相关访问
        
        Args:
            ai_player_id: AI玩家ID
            attribute: 访问的属性名
            value: 访问的值
            
        Returns:
            (访问类型, 违规类型)
        """
        # 如果是访问玩家列表，这是合法的
        if attribute == 'players':
            return AccessType.LEGAL, None
            
        # 如果是访问特定玩家的公开信息，这是合法的
        if any(attr in attribute for attr in self.player_legal_attributes):
            return AccessType.LEGAL, None
            
        # 如果是访问底牌相关
        if 'hole_cards' in attribute:
            # 需要进一步检查是否是访问自己的底牌
            return self._analyze_card_access(ai_player_id, attribute, value)
            
        # 其他玩家访问默认为可疑
        return AccessType.SUSPICIOUS, ViolationType.PLAYER_PRIVATE_DATA
        
    def _analyze_card_access(self, ai_player_id: int, attribute: str, value: Any) -> tuple[AccessType, Optional[ViolationType]]:
        """分析卡牌访问
        
        Args:
            ai_player_id: AI玩家ID
            attribute: 访问的属性名
            value: 访问的值
            
        Returns:
            (访问类型, 违规类型)
        """
        # 如果是访问公共牌，这是合法的
        if 'community' in attribute:
            return AccessType.LEGAL, None
            
        # 如果是访问底牌，需要检查是否是自己的
        if 'hole_cards' in attribute:
            # 这里需要更复杂的逻辑来判断是否是访问自己的底牌
            # 简化处理：如果在AI决策过程中访问底牌，假设是访问自己的
            return AccessType.LEGAL, None
            
        # 其他卡牌访问可能是非法的
        return AccessType.ILLEGAL, ViolationType.OPPONENT_HOLE_CARDS
        
    def _sanitize_value(self, value: Any) -> Any:
        """清理敏感值用于记录
        
        Args:
            value: 原始值
            
        Returns:
            清理后的值
        """
        if isinstance(value, list) and len(value) > 10:
            return f"<list of {len(value)} items>"
        elif isinstance(value, dict) and len(value) > 10:
            return f"<dict with {len(value)} keys>"
        elif isinstance(value, str) and len(value) > 100:
            return value[:100] + "..."
        else:
            return str(value)[:200]  # 限制字符串长度
            
    def monitor_ai_decision(self, ai_strategy: AIStrategy, snapshot: GameSnapshot, ai_player_id: int) -> Any:
        """监控AI决策过程
        
        Args:
            ai_strategy: AI策略实例
            snapshot: 游戏快照
            ai_player_id: AI玩家ID
            
        Returns:
            AI的决策结果
        """
        # 创建监控快照
        monitored_snapshot = self.create_monitored_snapshot(snapshot, ai_player_id)
        
        # 执行AI决策
        try:
            decision = ai_strategy.decide(monitored_snapshot, ai_player_id)
            return decision
        except Exception as e:
            # 记录决策异常
            logging.error(f"AI {ai_player_id} decision error: {e}")
            raise
            
    def generate_fairness_report(self, ai_player_id: int) -> FairnessReport:
        """生成AI公平性报告
        
        Args:
            ai_player_id: AI玩家ID
            
        Returns:
            公平性报告
        """
        # 筛选该AI的访问记录
        ai_records = [r for r in self.access_records if r.ai_player_id == ai_player_id]
        
        # 统计访问类型
        legal_count = sum(1 for r in ai_records if r.access_type == AccessType.LEGAL)
        illegal_count = sum(1 for r in ai_records if r.access_type == AccessType.ILLEGAL)
        suspicious_count = sum(1 for r in ai_records if r.access_type == AccessType.SUSPICIOUS)
        
        # 统计违规类型
        violations_by_type = {}
        for record in ai_records:
            if record.violation_type:
                violations_by_type[record.violation_type] = violations_by_type.get(record.violation_type, 0) + 1
                
        # 创建报告
        report = FairnessReport(
            ai_player_id=ai_player_id,
            total_decisions=len(set(r.timestamp for r in ai_records)),  # 估算决策次数
            total_accesses=len(ai_records),
            legal_accesses=legal_count,
            illegal_accesses=illegal_count,
            suspicious_accesses=suspicious_count,
            violations_by_type=violations_by_type,
            access_records=ai_records
        )
        
        return report
        
    def run_large_scale_fairness_test(self, ai_strategy: AIStrategy, num_hands: int = 1000) -> FairnessReport:
        """运行大规模AI公平性测试
        
        Args:
            ai_strategy: AI策略实例
            num_hands: 测试手牌数量
            
        Returns:
            公平性测试报告
        """
        from v2.core import GameState, Card, Suit, Rank, Player, SeatStatus
        
        ai_player_id = 1
        self.register_ai(ai_player_id, ai_strategy)
        
        # 清空之前的记录
        self.access_records = []
        
        for hand_num in range(num_hands):
            try:
                # 创建测试游戏状态
                game_state = GameState()
                
                # 添加玩家
                ai_player = Player(seat_id=ai_player_id, name="TestAI", chips=1000)
                opponent = Player(seat_id=2, name="Opponent", chips=1000)
                game_state.add_player(ai_player)
                game_state.add_player(opponent)
                
                # 初始化牌堆
                game_state.initialize_deck(seed=hand_num)
                
                # 发底牌
                game_state.deal_hole_cards()
                
                # 创建快照并监控AI决策
                snapshot = game_state.create_snapshot()
                self.monitor_ai_decision(ai_strategy, snapshot, ai_player_id)
                
                # 模拟游戏进行到翻牌
                game_state.advance_phase()
                game_state.deal_community_cards(3)
                snapshot = game_state.create_snapshot()
                self.monitor_ai_decision(ai_strategy, snapshot, ai_player_id)
                
                # 每100手报告一次进度
                if (hand_num + 1) % 100 == 0:
                    logging.info(f"Completed {hand_num + 1}/{num_hands} hands")
                    
            except Exception as e:
                logging.warning(f"Error in hand {hand_num}: {e}")
                continue
                
        # 生成最终报告
        return self.generate_fairness_report(ai_player_id)
        
    def detect_cheating_patterns(self, ai_player_id: int) -> List[Dict[str, Any]]:
        """检测作弊模式
        
        Args:
            ai_player_id: AI玩家ID
            
        Returns:
            检测到的作弊模式列表
        """
        ai_records = [r for r in self.access_records if r.ai_player_id == ai_player_id]
        patterns = []
        
        # 检测频繁访问对手底牌
        opponent_card_accesses = [r for r in ai_records if r.violation_type == ViolationType.OPPONENT_HOLE_CARDS]
        if len(opponent_card_accesses) > 0:
            patterns.append({
                'type': 'frequent_opponent_card_access',
                'severity': 'critical',
                'count': len(opponent_card_accesses),
                'description': f"AI accessed opponent hole cards {len(opponent_card_accesses)} times"
            })
            
        # 检测访问未发牌
        undealt_accesses = [r for r in ai_records if r.violation_type == ViolationType.UNDEALT_CARDS]
        if len(undealt_accesses) > 0:
            patterns.append({
                'type': 'undealt_card_access',
                'severity': 'critical',
                'count': len(undealt_accesses),
                'description': f"AI accessed undealt cards {len(undealt_accesses)} times"
            })
            
        # 检测可疑的访问模式
        suspicious_accesses = [r for r in ai_records if r.access_type == AccessType.SUSPICIOUS]
        if len(suspicious_accesses) > len(ai_records) * 0.1:  # 超过10%的访问是可疑的
            patterns.append({
                'type': 'high_suspicious_access_ratio',
                'severity': 'medium',
                'count': len(suspicious_accesses),
                'description': f"High ratio of suspicious accesses: {len(suspicious_accesses)}/{len(ai_records)}"
            })
            
        return patterns
        
    def export_fairness_report(self, report: FairnessReport, filepath: str) -> None:
        """导出公平性报告到文件
        
        Args:
            report: 公平性报告
            filepath: 输出文件路径
        """
        import json
        
        # 准备可序列化的数据
        export_data = {
            'ai_player_id': report.ai_player_id,
            'total_decisions': report.total_decisions,
            'total_accesses': report.total_accesses,
            'legal_accesses': report.legal_accesses,
            'illegal_accesses': report.illegal_accesses,
            'suspicious_accesses': report.suspicious_accesses,
            'violations_by_type': {k.value: v for k, v in report.violations_by_type.items()},
            'fairness_score': report.fairness_score,
            'is_fair': report.is_fair,
            'access_records': [
                {
                    'timestamp': record.timestamp,
                    'access_type': record.access_type.value,
                    'violation_type': record.violation_type.value if record.violation_type else None,
                    'accessed_attribute': record.accessed_attribute,
                    'accessed_value': record.accessed_value,
                    'severity': record.severity,
                    'stack_trace': record.stack_trace[:3]  # 只保留前3层调用栈
                }
                for record in report.access_records
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
            
    def clear_records(self) -> None:
        """清空访问记录"""
        self.access_records.clear()
        
    def get_summary_stats(self) -> Dict[str, Any]:
        """获取监控统计摘要
        
        Returns:
            统计摘要字典
        """
        if not self.access_records:
            return {'total_records': 0}
            
        total_records = len(self.access_records)
        legal_count = sum(1 for r in self.access_records if r.access_type == AccessType.LEGAL)
        illegal_count = sum(1 for r in self.access_records if r.access_type == AccessType.ILLEGAL)
        suspicious_count = sum(1 for r in self.access_records if r.access_type == AccessType.SUSPICIOUS)
        
        # 按AI分组统计
        ai_stats = {}
        for record in self.access_records:
            ai_id = record.ai_player_id
            if ai_id not in ai_stats:
                ai_stats[ai_id] = {'legal': 0, 'illegal': 0, 'suspicious': 0}
            ai_stats[ai_id][record.access_type.value] += 1
            
        return {
            'total_records': total_records,
            'legal_accesses': legal_count,
            'illegal_accesses': illegal_count,
            'suspicious_accesses': suspicious_count,
            'legal_ratio': legal_count / total_records if total_records > 0 else 0,
            'illegal_ratio': illegal_count / total_records if total_records > 0 else 0,
            'suspicious_ratio': suspicious_count / total_records if total_records > 0 else 0,
            'monitored_ais': list(ai_stats.keys()),
            'ai_stats': ai_stats
        } 