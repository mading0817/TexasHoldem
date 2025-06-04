---

## 📋 MILESTONE 1: 架构基础与测试框架 (PLAN 01-10)

### ✅ PLAN 01 创建v3目录结构与命名规范 【已完成】

**PLAN简述**: 建立v3标准目录结构，制定严格的命名规范和模块访问权限

**解决的具体问题**:
- v2模块边界不清晰，导致循环依赖和职责混乱
- 缺乏统一的命名规范，代码可读性差
- 没有明确的模块访问权限控制

**执行步骤**:
1. ✅ 创建标准目录结构：
   ```
   v3/
   ├── core/                 # 纯领域逻辑
   │   ├── state_machine/    # 状态机+相位处理器
   │   ├── betting/          # 下注引擎
   │   ├── pot/             # 边池管理
   │   ├── chips/           # 筹码账本
   │   ├── deck/            # 牌组管理
   │   ├── eval/            # 牌型评估
   │   ├── rules/           # 游戏规则
   │   ├── invariant/       # 数学不变量
   │   ├── events/          # 领域事件
   │   └── snapshot/        # 状态快照
   ├── application/          # 应用服务
   │   ├── command_service.py
   │   └── query_service.py
   └── tests/
       ├── unit/            # 单元测试 + 反作弊
       ├── property/        # 性质测试（筹码守恒等）
       ├── integration/     # 集成测试 + 反作弊
       └── anti_cheat/      # 专门的反作弊检查
   ```

2. ✅ 制定命名规范：
   ```python
   # 模块命名：snake_case
   core.state_machine, core.betting_engine

   # 类命名：PascalCase + 职责后缀
   GameStateMachine, BettingEngineService, ChipLedgerRepository

   # 方法命名：动词开头 + 明确意图
   def calculate_side_pot_distribution()  # ✅ 清晰
   def handle_betting()                   # ❌ 模糊

   # 常量：SCREAMING_SNAKE_CASE + 域前缀
   BETTING_MIN_RAISE_MULTIPLIER = 2
   POKER_MAX_PLAYERS_PER_TABLE = 10
   ```

3. ✅ 建立模块访问权限矩阵：
   | 模块 | 可访问 | 禁止访问 | 备注 |
   |------|--------|----------|------|
   | `core.*` | 只能访问其他core模块 | application/, tests/ | 纯领域逻辑 |
   | `application.*` | core.*, 自身 | ui.*, tests/ | 应用服务层 |
   | `tests.*` | 所有模块 | - | 测试特权 |

**测试验收**:
- ✅ 所有模块都有对应的`__init__.py`和`__all__`声明
- ✅ 静态分析工具验证模块依赖关系符合权限矩阵
- ✅ 命名规范检查脚本100%通过

**完成时间**: 2025-06-04
**验收测试**: `test_v3_naming_conventions.py` - 4/4 通过

---

### ✅ PLAN 02 TDD测试框架建立 【已完成】

**PLAN简述**: 建立完整的TDD测试框架，包含反作弊系统

**解决的具体问题**:
- v2测试覆盖不全面，缺乏边缘情况测试
- 没有反作弊机制，测试可能绕过真实业务逻辑
- 缺乏property-based testing保证数学不变量

**执行步骤**:
1. ✅ 建立测试基础设施：
   ```python
   # tests/conftest.py
   import pytest
   from v3.core.state_machine import GameStateMachine
   from v3.application.command_service import GameCommandService

   @pytest.fixture
   def game_state_machine():
       return GameStateMachine()

   @pytest.fixture
   def command_service():
       return GameCommandService()
   ```

2. ✅ 实现反作弊检查框架：
   ```python
   # tests/anti_cheat/core_usage_checker.py
   class CoreUsageChecker:
       """确保测试真正使用核心模块而非mock数据"""

       @staticmethod
       def verify_real_objects(obj, expected_type_name: str):
           assert type(obj).__name__ == expected_type_name, \
               f"必须使用真实的{expected_type_name}，当前类型: {type(obj).__name__}"

       @staticmethod
       def verify_chip_conservation(initial_total: int, final_total: int):
           assert initial_total == final_total, \
               f"筹码必须守恒: 初始{initial_total}, 最终{final_total}"
   ```

3. ✅ 建立property-based testing：
   ```python
   # tests/property/test_chip_conservation.py
   from hypothesis import given, strategies as st

   @given(st.lists(st.integers(min_value=100, max_value=10000), min_size=2, max_size=8))
   def test_chip_conservation_property(player_chips):
       """Property test: 无论如何操作，筹码总量必须守恒"""
       # 实现筹码守恒的property测试
   ```

**测试验收**:
- ✅ pytest配置完整，支持并行测试和覆盖率报告
- ✅ 反作弊检查框架能检测出mock对象的使用
- ✅ property-based testing能生成随机测试用例

**完成时间**: 2025-06-04
**验收测试**:
- `test_v3_tdd_framework.py` - 21/21 通过
- `test_chip_conservation.py` - 4/4 通过

---

### ✅ PLAN 03 核心状态机架构设计 【已完成】

**PLAN简述**: 设计并实现游戏状态机，支持所有德州扑克阶段

**解决的具体问题**:
- v2的状态转换逻辑隐式且分散，难以维护
- 新增游戏阶段需要修改多处代码
- 状态转换的合法性难以验证

**执行步骤**:
1. ✅ 定义状态机接口：
   ```python
   # core/state_machine/types.py - 基础类型定义
   class GamePhase(Enum):
       INIT = auto()
       PRE_FLOP = auto()
       FLOP = auto()
       TURN = auto()
       RIVER = auto()
       SHOWDOWN = auto()
       FINISHED = auto()

   class PhaseHandler(Protocol):
       def on_enter(self, ctx: GameContext) -> None: ...
       def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent: ...
       def on_exit(self, ctx: GameContext) -> None: ...
       def can_transition_to(self, target_phase: GamePhase, ctx: GameContext) -> bool: ...

   # core/state_machine/__init__.py - 状态机核心实现
   class GameStateMachine:
       def transition(self, event: GameEvent, ctx: GameContext) -> None:
           # 完整的状态转换逻辑
       def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
           # 玩家行动处理
   ```

2. ✅ 实现具体的阶段处理器：
   ```python
   # core/state_machine/phase_handlers.py
   class PreFlopHandler(BasePhaseHandler):
       def on_enter(self, ctx: GameContext) -> None:
           # 发手牌，设置盲注
       def handle_player_action(self, ctx: GameContext, player_id: str, action: Dict[str, Any]) -> GameEvent:
           # 处理翻牌前行动：fold, call, raise, check

   # 实现了所有阶段：InitHandler, PreFlopHandler, FlopHandler, TurnHandler, RiverHandler, ShowdownHandler, FinishedHandler
   ```

3. ✅ 创建状态机工厂：
   ```python
   # core/state_machine/state_machine_factory.py
   class StateMachineFactory:
       @staticmethod
       def create_default_state_machine() -> GameStateMachine:
           # 创建配置好的状态机实例
   ```

**测试验收**:
- ✅ 状态机能正确处理所有合法的状态转换
- ✅ 非法状态转换会抛出明确的异常
- ✅ 每个阶段处理器都有完整的单元测试
- ✅ 完整的游戏流程转换测试通过
- ✅ 反作弊检查全部通过

**完成时间**: 2025-06-04
**验收测试**: `test_state_machine.py` - 15/15 通过

---

### ✅ PLAN 04 筹码与下注引擎重构 【已完成】

**PLAN简述**: 重新设计筹码管理和下注引擎，确保数学正确性

**解决的具体问题**:
- v2的边池计算逻辑复杂且容易出错
- 筹码操作分散在多个类中，难以保证一致性
- 缺乏下注合法性的严格验证

**执行步骤**:
1. ✅ 设计筹码账本：
   ```python
   # core/chips/chip_ledger.py
   class ChipLedger:
       """筹码账本，确保所有筹码操作的原子性和一致性"""

       def deduct_chips(self, player_id: str, amount: int) -> bool:
           """扣除筹码，失败时回滚"""

       def add_chips(self, player_id: str, amount: int) -> None:
           """增加筹码"""

       def get_total_chips(self) -> int:
           """获取系统总筹码，用于守恒检查"""
   ```

2. ✅ 实现下注引擎：
   ```python
   # core/betting/betting_engine.py
   class BettingEngine:
       """下注引擎，处理所有下注逻辑"""

       def validate_bet(self, player_id: str, amount: int) -> ValidationResult:
           """验证下注的合法性"""

       def place_bet(self, player_id: str, amount: int) -> BetResult:
           """执行下注操作"""
   ```

3. ✅ 重新设计边池管理：
   ```python
   # core/pot/pot_manager.py
   class PotManager:
       """边池管理器，处理复杂的边池分配"""

       def calculate_side_pots(self, bets: Dict[str, int]) -> List[SidePot]:
           """计算边池分配"""

       def distribute_winnings(self, winners: List[str], hand_strengths: Dict[str, int]) -> Dict[str, int]:
           """分配奖金"""
   ```

**测试验收**:
- ✅ 所有筹码操作都通过ChipLedger，确保原子性
- ✅ 边池计算通过大量随机测试验证正确性
- ✅ 筹码守恒在任何情况下都不被违反
- ✅ 盲注设置和下注验证逻辑正确
- ✅ 反作弊检查全部通过

**完成时间**: 2025-01-27
**验收测试**: `test_chips_and_betting.py` - 22/22 通过

---

### ✅ PLAN 05 牌型评估器迁移 【已完成】

**PLAN简述**: 从v2迁移牌型评估器，确保功能完全对等

**解决的具体问题**:
- v2的牌型评估器功能正确，需要保持兼容
- 需要增加更严格的类型检查和错误处理
- 性能需要进一步优化

**执行步骤**:
1. ✅ 迁移核心评估逻辑：
   ```python
   # core/eval/evaluator.py
   class HandEvaluator:
       """牌型评估器，从v2迁移并增强"""

       def evaluate_hand(self, hole_cards: List[Card], community_cards: List[Card]) -> HandResult:
           """评估手牌强度"""

       def compare_hands(self, hand1: HandResult, hand2: HandResult) -> int:
           """比较两手牌的强弱"""
   ```

2. ✅ 增加严格的类型检查：
   ```python
   from typing import List, Union
   from dataclasses import dataclass

   @dataclass(frozen=True)
   class Card:
       suit: Suit
       rank: Rank

       def __post_init__(self):
           if not isinstance(self.suit, Suit):
               raise TypeError(f"花色必须是Suit类型，实际: {type(self.suit)}")
   ```

3. ✅ 性能优化和测试：
   - 单次评估平均时间：0.671毫秒
   - 手牌比较平均时间：0.001毫秒
   - 完整工作流程平均时间：0.771毫秒

**测试验收**:
- ✅ 与v2评估器的结果100%一致
- ✅ 通过大量随机牌型测试验证正确性 (100局随机模拟)
- ✅ 性能测试：评估速度显著优于v2
- ✅ 反作弊检查：所有测试使用真实对象
- ✅ 集成测试：多玩家场景、边缘情况全覆盖

**完成时间**: 2025-01-XX
**验收测试**:
- `test_deck_and_eval.py` - 33/33 通过
- `test_deck_and_eval_performance.py` - 6/6 通过
- `test_deck_eval_integration.py` - 8/8 通过

---

### ✅ PLAN 06 领域事件系统 【已完成】

**PLAN简述**: 实现完整的领域事件系统，支持事件溯源

**解决的具体问题**:
- v2的事件系统不完整，UI更新依赖轮询
- 缺乏事件持久化，无法支持回放功能
- 事件类型不规范，难以扩展

**执行步骤**:
1. ✅ 定义标准事件格式：
   ```python
   # core/events/domain_events.py
   @dataclass(frozen=True)
   class DomainEvent:
       event_id: str
       event_type: EventType
       aggregate_id: str
       timestamp: float
       data: Dict[str, Any]
       version: int = 1
       correlation_id: Optional[str] = None
   ```

2. ✅ 实现事件总线：
   ```python
   # core/events/event_bus.py
   class EventBus:
       def publish(self, event: DomainEvent) -> None:
           """发布事件"""

       def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
           """订阅事件"""

       def subscribe_async(self, event_type: EventType, handler: AsyncEventHandler) -> None:
           """订阅异步事件处理器"""
   ```

3. ✅ 实现具体事件类型：
   - GameStartedEvent: 游戏开始事件
   - HandStartedEvent: 手牌开始事件
   - PhaseChangedEvent: 阶段转换事件
   - PlayerActionExecutedEvent: 玩家行动执行事件
   - PotUpdatedEvent: 边池更新事件
   - CardsDealtEvent: 发牌事件
   - CommunityCardsRevealedEvent: 公共牌揭示事件

4. ✅ 支持同步和异步事件处理
5. ✅ 事件历史记录和过滤功能
6. ✅ 事件序列化和反序列化
7. ✅ 全局事件总线管理

**测试验收**:
- ✅ 事件发布和订阅机制工作正常
- ✅ 事件数据完整且可序列化
- ✅ 支持事件重放功能
- ✅ 反作弊检查：所有测试使用真实对象
- ✅ 集成测试：多组件事件流、错误处理、性能测试
- ✅ 性能测试：1000个事件处理时间 < 1秒

**完成时间**: 2025-01-XX
**验收测试**:
- `test_events.py` - 22/22 通过
- `test_events_integration.py` - 9/9 通过

---

### ✅ PLAN 07 应用服务层设计 【已完成】

**PLAN简述**: 实现CQRS模式的应用服务层

**解决的具体问题**:
- v2的控制器职责过重，难以测试
- 命令和查询混合，违反CQRS原则
- 缺乏统一的错误处理机制

**执行步骤**:
1. ✅ 创建应用服务类型定义：
   ```python
   # application/types.py
   @dataclass(frozen=True)
   class CommandResult:
       success: bool
       status: ResultStatus
       message: str
       error_code: Optional[str] = None
       data: Optional[Dict[str, Any]] = None
   ```

2. ✅ 实现命令服务：
   ```python
   # application/command_service.py
   class GameCommandService:
       """游戏命令服务，处理所有状态变更操作"""

       def create_new_game(self, game_id: Optional[str] = None, player_ids: Optional[List[str]] = None) -> CommandResult
       def start_new_hand(self, game_id: str) -> CommandResult
       def execute_player_action(self, game_id: str, player_id: str, action: PlayerAction) -> CommandResult
       def advance_phase(self, game_id: str) -> CommandResult
       def remove_game(self, game_id: str) -> CommandResult
   ```

3. ✅ 实现查询服务：
   ```python
   # application/query_service.py
   class GameQueryService:
       """游戏查询服务，处理所有只读操作"""

       def get_game_state(self, game_id: str) -> QueryResult
       def get_player_info(self, game_id: str, player_id: str) -> QueryResult
       def get_available_actions(self, game_id: str, player_id: str) -> QueryResult
       def get_game_list(self) -> QueryResult
       def get_game_history(self, game_id: str) -> QueryResult
   ```

4. ✅ 编写TDD测试：包含反作弊验证的完整测试
5. ✅ 集成测试：测试命令和查询服务的协作
6. ✅ 性能测试：确保应用服务层不影响性能
7. ✅ 文档更新：使用pdoc更新API文档
8. ✅ 项目清理：清理临时文件

**测试验收**:
- ✅ 命令和查询严格分离
- ✅ 所有操作都有明确的返回结果
- ✅ 错误处理统一且友好
- ✅ 反作弊检查：所有测试使用真实对象
- ✅ 集成测试：CQRS分离验证、完整工作流测试
- ✅ 性能测试：应用服务层开销最小化

**完成时间**: 2025-01-XX
**验收测试**: `test_application_services.py` - 24/24 通过

---

### ✅ PLAN 08 状态快照系统 【已完成】

**PLAN简述**: 设计不可变的状态快照系统

**解决的具体问题**:
- v2的状态对象可变，容易被意外修改
- 缺乏版本控制，难以追踪状态变化
- 序列化格式不统一

**执行步骤**:
1. 设计不可变快照：
   ```python
   # core/snapshot/game_snapshot.py
   @dataclass(frozen=True)
   class GameStateSnapshot:
       game_id: str
       phase: GamePhase
       players: Tuple[PlayerSnapshot, ...]
       pot: int
       community_cards: Tuple[Card, ...]
       current_bet: int
       timestamp: float
       version: int
   ```

2. 实现快照管理器：
   ```python
   # core/snapshot/snapshot_manager.py
   class SnapshotManager:
       def create_snapshot(self, game_state: GameState) -> GameStateSnapshot:
           """创建状态快照"""

       def restore_from_snapshot(self, snapshot: GameStateSnapshot) -> GameState:
           """从快照恢复状态"""
   ```

**测试验收**:
- ✅ 快照对象完全不可变
- ✅ 快照序列化和反序列化无损
- ✅ 支持快照版本管理
- ✅ 性能测试通过（创建、序列化、反序列化、文件操作）

**完成时间**: 2025-01-27
**验收测试**:
- `test_snapshot_types.py` - 6/6 通过
- `test_snapshot_manager.py` - 5/5 通过
- `test_snapshot_serializer.py` - 4/4 通过
- `test_snapshot_integration.py` - 3/3 通过
- `test_snapshot_performance.py` - 6/6 通过

---

### ✅ PLAN 09 数学不变量验证 【已完成】

**PLAN简述**: 实现完整的数学不变量检查系统

**解决的具体问题**:
- v2缺乏系统性的不变量检查
- 筹码守恒等关键约束可能被违反
- 难以发现边缘情况下的逻辑错误

**执行步骤**:
1. ✅ 定义不变量类型系统：
   ```python
   # core/invariant/invariant_types.py
   class InvariantType(Enum):
       CHIP_CONSERVATION = "chip_conservation"
       BETTING_RULES = "betting_rules"
       PHASE_CONSISTENCY = "phase_consistency"

   @dataclass(frozen=True)
   class InvariantViolation:
       violation_id: str
       invariant_type: InvariantType
       severity: str
       description: str
       timestamp: float
   ```

2. ✅ 实现具体不变量检查器：
   ```python
   # core/invariant/chip_conservation_checker.py
   class ChipConservationChecker:
       def check(self, snapshot: GameStateSnapshot) -> InvariantCheckResult

   # core/invariant/betting_rules_checker.py
   class BettingRulesChecker:
       def check(self, snapshot: GameStateSnapshot) -> InvariantCheckResult

   # core/invariant/phase_consistency_checker.py
   class PhaseConsistencyChecker:
       def check(self, snapshot: GameStateSnapshot) -> InvariantCheckResult
   ```

3. ✅ 实现统一的不变量管理器：
   ```python
   # core/invariant/game_invariants.py
   class GameInvariants:
       def check_all(self, snapshot: GameStateSnapshot) -> InvariantCheckResult
       def is_valid_state(self, snapshot: GameStateSnapshot) -> bool
       def get_violations(self, snapshot: GameStateSnapshot) -> List[InvariantViolation]
   ```

4. ✅ 集成到应用服务层：
   ```python
   # application/command_service.py
   class GameCommandService:
       def __init__(self, enable_invariant_checks: bool = True):
           self._invariant_checks_enabled = enable_invariant_checks
           if enable_invariant_checks:
               self._game_invariants = GameInvariants()

       def _check_invariants_if_enabled(self, game_id: str) -> None:
           if self._invariant_checks_enabled:
               snapshot = self._get_game_snapshot(game_id)
               self._game_invariants.validate_and_raise(snapshot)
   ```

5. ✅ 编写全面的TDD测试：
   - 单元测试：每个检查器的独立测试
   - 集成测试：不变量系统与应用服务的集成
   - 边缘情况测试：各种违反场景的测试
   - 性能测试：不变量检查的性能影响

6. ✅ 解决集成过程中发现的问题：
   - 修复GameContext缺少盲注字段的问题
   - 更新SnapshotManager以正确处理盲注信息
   - 确保所有测试通过反作弊检查

**测试验收**:
- ✅ 所有不变量检查都有对应的测试 (52个单元测试通过)
- ✅ 不变量违反时能准确定位问题
- ✅ 性能影响最小化
- ✅ 集成测试验证不变量系统正常工作 (7个集成测试通过)
- ✅ 反作弊检查：所有测试使用真实对象

**完成时间**: 2025-01-28
**验收测试**:
- `test_invariant_types.py` - 13/13 通过
- `test_chip_conservation_checker.py` - 11/11 通过
- `test_betting_rules_checker.py` - 13/13 通过
- `test_phase_consistency_checker.py` - 13/13 通过
- `test_game_invariants.py` - 21/21 通过
- `test_invariant_integration.py` - 7/7 通过
- 总计：105个v3核心测试全部通过

---

### ✅ PLAN 10 反作弊测试系统 【已完成】

**PLAN简述**: 建立全面的反作弊测试系统

**解决的具体问题**:
- 测试可能绕过真实业务逻辑，产生虚假的通过结果
- 缺乏对测试质量的验证机制
- 难以确保测试覆盖了真实的代码路径

**执行步骤**:
1. ✅ 分析当前反作弊系统状态
2. ✅ 增强核心模块使用检查：
   ```python
   # tests/anti_cheat/core_usage_checker.py
   class CoreUsageChecker:
       """核心模块使用检查器，确保测试真正使用核心模块而非mock数据"""

       @staticmethod
       def verify_real_objects(obj: Any, expected_type_name: str) -> None:
           """验证对象是真实的核心对象，包含7层检测机制"""
           # 基础类型检查、增强mock检测、模块来源验证等

       @staticmethod
       def verify_chip_conservation(initial_total: int, final_total: int) -> None:
           """验证筹码守恒"""

       @staticmethod
       def generate_anti_cheat_report() -> AntiCheatReport:
           """生成反作弊检查报告"""
   ```

3. ✅ 实现状态一致性检查：
   ```python
   # tests/anti_cheat/state_consistency_checker.py
   class StateConsistencyChecker:
       """检查状态变化的一致性"""

       @staticmethod
       def verify_chip_conservation(initial_state, final_state) -> None:
           """验证筹码守恒不变量"""

       @staticmethod
       def verify_player_count_consistency(initial_state, final_state) -> None:
           """验证玩家数量一致性"""
   ```

4. ✅ 实现代码覆盖率验证：
   ```python
   # tests/anti_cheat/coverage_verifier.py
   class CoverageVerifier:
       """验证测试真正覆盖了核心代码路径"""

       @staticmethod
       def verify_core_module_coverage(test_name: str, min_coverage: float = 0.9) -> bool:
           """验证核心模块覆盖率"""

       @staticmethod
       def generate_coverage_report() -> CoverageReport:
           """生成覆盖率报告"""
   ```

5. ✅ 编写TDD测试并验证：
   - 单元测试：`test_core_usage_checker.py`, `test_module_usage_tracker.py`, `test_state_consistency_checker.py`, `test_coverage_verifier.py`
   - 集成测试：`test_anti_cheat_integration.py` - 9/9 通过
   - 修复了Python内置类型误报问题，优化了mock检测逻辑

6. ✅ 项目清理和文档更新：
   - 使用 `cleanup.py` 清理了55个临时文件和14个目录
   - 更新了 `pytest.ini` 配置，添加了必要的测试标记
   - 完善了反作弊系统的白名单机制

**测试验收**:
- ✅ 所有反作弊测试都通过检查（9/9 通过）
- ✅ 能准确检测出绕过核心逻辑的测试
- ✅ 覆盖率验证准确可靠
- ✅ Python内置类型不再被误报为mock对象

**完成时间**: 2025-01-27
**验收测试**: `test_anti_cheat_integration.py` - 9/9 通过

---

## 📋 MILESTONE 2: 核心业务逻辑实现 (PLAN 11-20)

### ✅ PLAN 11 状态机核心实现 【已完成】

**PLAN简述**: 实现完整的游戏状态机逻辑

**TDD流程**:
1. ✅ 先写失败测试：测试状态转换、事件处理、阶段管理
2. ✅ 运行反作弊检查：确保测试使用真实的状态机对象
3. ✅ 实现最小代码：让测试通过
4. ✅ 重构优化：保持测试通过的前提下优化代码

**执行步骤**:
1. ✅ 编写状态机测试：
   ```python
   # tests/unit/core/test_state_machine.py
   def test_state_machine_transitions():
       """测试状态机转换逻辑"""
       # 反作弊检查
       machine = GameStateMachine()
       CoreUsageChecker.verify_real_objects(machine, "GameStateMachine")

       # 测试逻辑
       assert machine.current_state == GamePhase.INIT
       machine.transition_to(GamePhase.PRE_FLOP)
       assert machine.current_state == GamePhase.PRE_FLOP
   ```

2. ✅ 实现状态机核心逻辑
   - 完成 PreFlopHandler 的盲注设置和发牌逻辑
   - 完成 FlopHandler 的下注重置和翻牌发牌逻辑
   - 修复不变量违反问题，确保筹码守恒和阶段一致性
3. ✅ 集成测试验证
   - 所有应用服务测试通过 (24/24)
   - 所有状态机单元测试通过 (15/15)
   - 所有核心模块测试通过 (125/125)

**测试验收**:
- ✅ 所有状态转换测试通过
- ✅ 反作弊检查通过
- ✅ 状态机性能满足要求

**完成时间**: 2025-01-20
**验收测试**:
- `test_state_machine.py` - 15/15 通过
- `test_application_services.py` - 24/24 通过
- `v3/tests/unit/core/` - 125/125 通过

---

### ✅ PLAN 12 筹码系统实现 【已完成】

**PLAN简述**: 实现筹码账本和下注引擎

**解决的具体问题**:
- 筹码操作分散且缺乏原子性保证
- 边池计算逻辑复杂且容易出错
- 下注合法性验证不够严格
- 缺乏全面的边缘情况测试

**执行步骤**:
1. ✅ 分析现有筹码、下注、边池模块状态
2. ✅ 运行现有相关测试，确认基础功能正常
3. ✅ 编写筹码系统核心逻辑测试
4. ✅ 实现和完善筹码系统核心逻辑
5. ✅ 编写边池计算相关测试
6. ✅ 实现和完善边池计算逻辑
7. ✅ 编写下注引擎核心逻辑测试
8. ✅ 实现和完善下注引擎逻辑
9. ✅ 集成测试验证筹码、下注、边池系统的交互
10. ✅ 重构优化
11. ✅ 项目清理和文档更新

**主要成果**:
- 完善了筹码账本 (ChipLedger) 的原子性操作
- 增强了下注引擎 (BettingEngine) 的验证逻辑
- 优化了边池管理器 (PotManager) 的计算准确性
- 新增了13个边缘情况测试，覆盖并发操作、全押场景、单玩家场景等
- 修复了多个边缘情况下的逻辑问题

**测试验收**:
- ✅ 筹码守恒property测试100%通过 (4/4)
- ✅ 基础筹码和下注测试全部通过 (22/22)
- ✅ 边缘情况测试全部通过 (13/13)
- ✅ 总计39个测试全部通过，覆盖所有核心场景
- ✅ 反作弊检查全部通过

**完成时间**: 2025-01-27
**验收测试**:
- `test_chips_and_betting.py` - 22/22 通过
- `test_chip_conservation.py` - 4/4 通过
- `test_chips_and_betting_edge_cases.py` - 13/13 通过

---