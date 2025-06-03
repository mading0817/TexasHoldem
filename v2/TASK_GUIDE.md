# 🃏 德州扑克v2重构 - 任务指南

## 🎯 项目目标

基于**Hybrid-Lite架构最佳实践**，重构项目代码为单机+本地AI逻辑+可选远端LLM API调用模式，目标平台：Windows/Android/iOS/Steam。通过**职责三分、事件溯源、UI双层接口**等先进架构模式，确保移动端开发的简单、快捷、高效、可靠、易测试。

## 🏆 验收标准

所有PLAN必须确保 `test_streamlit_ultimate_user_experience.py` 终极测试通过，包括：
- 1000手牌完成率 ≥ 99%
- 用户行动成功率 ≥ 99% 
- 筹码守恒 100% 无违规
- 严重错误数量 = 0
- 测试性能 ≥ 5手/秒

---

## 📋 MILESTONE 1: 核心架构重构 (PLAN 01-08)

### PLAN 01 移除核心对 Pydantic 依赖

**PLAN简述**: 将核心层从Pydantic依赖中解耦，为跨平台移植做准备

**解决的具体问题**: 
- `core` 层直接引用 Pydantic，导致Android/iOS打包时依赖冲突
- 核心逻辑必须随同第三方库一起编译，不利于移动端原生集成
- 单元测试需要加载不必要的验证库

**执行步骤**:
1. 将所有 `core.*` 数据模型改为 `@dataclass(frozen=True)`，移除 `BaseModel` 继承
2. 在 `controller.dto` 内保留 Pydantic 版本，新增转换函数：
   ```python
   def core_to_dto_snapshot(core_snapshot: CoreGameSnapshot) -> GameStateSnapshot
   def dto_to_core_action(action_input: ActionInput) -> Action
   ```
3. 更新所有 `core` 模块的导入和测试

**测试验收**:
- `pip uninstall pydantic` 后 `pytest v2/tests/unit/core/` 仍能全部通过
- `pip install pydantic && pytest v2/tests/` 全部测试通过
- 依赖分析确认 Pydantic 仅被 `controller.dto` 引用

---

### PLAN 02 统一状态快照架构

**PLAN简述**: 建立单一权威的状态表示，消除core与controller的双重状态

**解决的具体问题**:
- 存在 `core.GameSnapshot` 与 `controller.GameStateSnapshot` 字段重复
- UI代码混用两种快照，导致字段缺失或序列化错误
- 开发者困惑应该使用哪个状态对象

**执行步骤**:
1. 只保留 `GameStateSnapshot`（Pydantic）作为统一状态表示
2. 核心快照在控制器边界自动转换：
   ```python
   def get_snapshot(self) -> GameStateSnapshot:
       core_snapshot = self._game_state.create_snapshot()
       return core_to_dto_snapshot(core_snapshot)
   ```
3. 实现完整的 `to_dict()` 与 `from_dict()` JSON序列化
4. 更新所有UI调用路径使用统一快照

**测试验收**:
- 新增 `tests/integration/test_snapshot_consistency.py`：验证状态转换的完整性
- 随机状态→dict→对象往返，所有字段完全一致
- UI集成测试无任何 `AttributeError` 或字段缺失错误

---

### PLAN 03 职责三分：拆解控制器巨无霸

**PLAN简述**: 将1080行的poker_controller.py按职责拆分为三个专门控制器

**解决的具体问题**:
- 单一控制器承担过多职责：行动验证、状态管理、事件处理
- 代码维护困难，移动端开发者难以理解API边界
- 职责混合导致单元测试复杂，难以隔离错误

**执行步骤**:
1. 创建三个专门控制器：
   ```python
   class ActionController:
       """专注行动验证和执行"""
       def validate_action(self, state, action) -> ValidationResult
       def execute_action(self, action) -> ActionResult
   
   class StateController:
       """专注状态机和阶段管理"""
       def advance_phase(self) -> None
       def check_hand_over(self) -> bool
       def award_pot(self) -> HandResult
   
   class EventController:
       """专注事件发布和订阅"""
       def publish(self, event: DomainEvent) -> None
       def subscribe(self, listener: EventListener) -> None
   ```
2. 重构原 `PokerController` 为协调者角色，组合三个子控制器
3. 更新所有调用点使用新的职责明确的API

**测试验收**:
- 每个控制器都有独立的单元测试套件，覆盖率 ≥ 90%
- `test_streamlit_ultimate_user_experience.py` 通过，无功能回归
- 代码行数：ActionController ≤ 300行，StateController ≤ 400行，EventController ≤ 200行

---

### PLAN 04 统一 ActionInput 接口流

**PLAN简述**: 标准化玩家行动输入接口，消除UI直接构造核心Action的耦合

**解决的具体问题**:
- UI需要直接构造 `core.Action` 对象，容易漏掉合法性检查
- 错误加注金额会抛出深层核心异常而非友好提示
- 不同UI重复实现相同的行动构造逻辑

**执行步骤**:
1. 在ActionController中新增标准化接口：
   ```python
   def execute_action_input(self, action_input: ActionInput) -> ActionResult:
       # 内部处理验证、转换、执行的完整流程
       validation = self.validate_action_input(action_input)
       if not validation.is_valid:
           return ActionResult(success=False, error=validation.error)
       core_action = self.convert_to_core_action(action_input)
       return self.execute_core_action(core_action)
   ```
2. UI层改为只构造简单的 `ActionInput(seat_id, action_type, amount)`
3. 统一错误处理，返回友好的 `ActionResult` 而非抛异常

**测试验收**:
- 单元测试验证非法金额返回 `success=False` 而非抛异常
- UI端显示友好错误提示，无红色异常堆栈
- `grep` 确认UI代码中不再有 `Action(ActionType.` 构造

---

### PLAN 05 引入事件溯源架构

**PLAN简述**: 实现完整的事件记录和重放机制，支持游戏回放和状态恢复

**解决的具体问题**:
- 无法支持游戏回放功能，用户复盘需求无法满足
- 断线重连后状态丢失，移动端体验差
- 难以追踪状态变化的根本原因，调试困难

**执行步骤**:
1. 定义标准事件格式：
   ```python
   @dataclass
   class DomainEvent:
       version: int = 1
       timestamp: float = field(default_factory=time.time)
       event_type: str
       player_id: Optional[int] = None
       data: Dict[str, Any] = field(default_factory=dict)
   ```
2. 实现事件存储：
   ```python
   class EventStore:
       def append_event(self, event: DomainEvent) -> None
       def get_events_since(self, timestamp: float) -> List[DomainEvent]
       def create_snapshot(self, state: GameState) -> StateSnapshot
   ```
3. 在StateController中集成事件记录
4. 实现状态重建：`replay_events(events) -> GameState`

**测试验收**:
- 记录完整手牌→重放事件→状态完全一致
- 随机中断→从最近快照恢复→继续游戏无异常
- 事件JSON文件可以独立验证和分析

---

### PLAN 06 流程推进API：step()方法

**PLAN简述**: 提供统一的游戏推进接口，消除UI重复的循环控制逻辑

**解决的具体问题**:
- CLI和Streamlit都有冗长while循环，逻辑容易分叉
- AI连续行动处理分散在UI层，难以维护
- 新增游戏阶段时需要同步修改多个UI文件

**执行步骤**:
1. 在重构后的控制器中实现统一接口：
   ```python
   @dataclass
   class StepResult:
       state: GameStateSnapshot
       events: List[GameEvent]
       need_user_input: bool
       current_player: Optional[int]
       available_actions: List[ActionType]
   
   def step(self, user_action: Optional[ActionInput] = None) -> StepResult:
       # 统一处理：用户行动→AI调度→阶段转换→状态更新
   ```
2. UI主循环统一为：
   ```python
   while True:
       result = controller.step(user_action)
       render_state(result.state)
       show_events(result.events)
       if result.need_user_input:
           user_action = wait_for_user_input(result.available_actions)
       else:
           user_action = None
   ```
3. 删除UI中的游戏流程控制代码

**测试验收**:
- 脚本化全AI对局：连续 `step(None)` 至结算，事件顺序正确
- CLI与Streamlit主循环不再包含复杂的while循环
- 新增AI连续行动场景测试，性能提升 ≥ 20%

---

### PLAN 07 思考帧调度器

**PLAN简述**: 实现可配置的AI思考时间机制，提升游戏体验和性能

**解决的具体问题**:
- AI瞬间决策缺乏真实感，用户体验差
- AI连续行动阻塞UI，移动端会卡顿
- 无法根据场景调整AI响应速度

**执行步骤**:
1. 实现思考帧调度器：
   ```python
   class ThinkingScheduler:
       def __init__(self, config: ThinkingConfig):
           self.think_delay = config.think_delay_ms
           self.batch_after_human_fold = config.batch_after_human_fold
       
       async def schedule_ai_action(self, ctx: GameContext) -> ActionInput:
           if ctx.human_players_active():
               await self.simulate_thinking(ctx)
               return await self.compute_ai_action(ctx)
           else:
               # 人类弃牌后批量处理
               return self.compute_fast_action(ctx)
   ```
2. 在StateController中集成调度器
3. 提供配置选项：思考时间、批量模式、LLM超时等

**测试验收**:
- 人类在场时AI有合理思考延迟（500-2000ms）
- 人类弃牌后AI快速批量处理
- 移动端UI测试：无阻塞，流畅响应用户操作

---

### PLAN 08 错误结果标准化

**PLAN简述**: 建立统一的错误处理和结果返回机制

**解决的具体问题**:
- 目前通过抛异常向UI反馈错误，导致UI需要复杂的try/catch
- Streamlit控制台打印长异常堆栈，用户体验差
- 错误信息不统一，难以进行国际化

**执行步骤**:
1. 扩展统一结果类型：
   ```python
   @dataclass
   class Result:
       success: bool
       data: Any = None
       error_code: Optional[str] = None
       error_message: Optional[str] = None
       warnings: List[str] = field(default_factory=list)
   ```
2. 所有控制器方法返回Result而非抛异常
3. 建立错误码字典和国际化消息模板

**测试验收**:
- 单元测试：非法操作返回 `success=False` 且 `error_code` 准确
- UI测试：无红色异常堆栈，显示友好错误提示
- 错误覆盖测试：模拟各种异常场景，都有合适的错误处理

---

## 📋 MILESTONE 2: UI架构优化 (PLAN 09-14)

### PLAN 09 事件驱动UI更新

**PLAN简述**: 将UI从轮询模式改为事件驱动模式，提升响应性和性能

**解决的具体问题**:
- Streamlit手动调用 `get_snapshot()` 比对差异，性能低下
- UI全量刷新导致闪烁，用户体验差
- 事件系统存在但未真正用于UI通知

**执行步骤**:
1. 完善事件系统：
   ```python
   class GameEventBus:
       def subscribe_ui(self, handler: UIEventHandler) -> None
       def emit_game_event(self, event: GameEvent) -> None
       def emit_ui_event(self, event: UIEvent) -> None
   ```
2. UI层注册事件监听器：
   ```python
   def on_game_event(self, event: GameEvent):
       if event.type == "PLAYER_ACTION":
           self.update_player_display(event.player_id)
       elif event.type == "POT_UPDATED":
           self.update_pot_display(event.amount)
   ```
3. 移除UI中的状态比对代码

**测试验收**:
- Mock事件监听器收到的事件数量 ≥ 用户行动数量
- UI组件只在相关事件触发时更新，无不必要的全量刷新
- 事件响应延迟 ≤ 50ms

---

### PLAN 10 UI双层接口设计

**PLAN简述**: 设计平台无关的UI抽象接口，为移动端开发做准备

**解决的具体问题**:
- 当前UI代码与Streamlit强耦合，难以移植到Android
- 缺乏统一的UI抽象，移动端开发需要从零开始
- UI逻辑和渲染逻辑混合，难以复用

**执行步骤**:
1. 定义双层UI接口：
   ```typescript
   // 语义层（跨端统一）
   interface PokerGameUI {
       showState(state: GameStateSnapshot): void
       showEvent(event: GameEvent): void
       promptPlayerAction(playerId: number, actions: ActionType[]): Promise<ActionInput>
   }
   
   // 细粒度层（平台定制）
   interface PokerGameUIFx extends PokerGameUI {
       animateChipMovement(from: number, to: number, amount: number): void
       flashWinningHand(cards: Card[]): void
       playSound(sound: SoundType): void
   }
   ```
2. Streamlit实现语义层接口
3. 准备Android Native接口规范

**测试验收**:
- Streamlit通过语义层接口重新实现，功能无差异
- Mock Android UI可以通过接口完成基本游戏流程
- 接口文档完整，包含所有必要的方法和数据结构

---

### PLAN 11 拆解Streamlit巨无霸应用

**PLAN简述**: 将1127行的app.py拆分为职责明确的组件模块

**解决的具体问题**:
- 单一文件承担过多职责：渲染、交互、状态管理、事件处理
- 代码维护困难，添加新功能需要在巨大文件中定位
- 难以进行单元测试和代码复用

**执行步骤**:
1. 按职责拆分组件：
   ```python
   # components/game_table.py - 游戏桌面渲染
   # components/player_panel.py - 玩家信息显示
   # components/action_buttons.py - 操作按钮组件
   # components/debug_panel.py - 调试信息面板
   # layout/main_layout.py - 主布局管理
   # session/game_session.py - 会话状态管理
   ```
2. `app.py` 仅保留路由和主函数
3. 实现组件间清晰的数据传递接口

**测试验收**:
- `wc -l app.py` ≤ 200行
- 每个组件都有独立的单元测试
- `pytest` 导入各组件无循环依赖警告

---

### PLAN 12 Session State抽象封装

**PLAN简述**: 抽象Streamlit的session state，为跨平台状态管理做准备

**解决的具体问题**:
- 代码中到处散布 `st.session_state['key']` 字典操作
- 迁移到其他前端需要重写大量状态操作
- 状态管理逻辑与UI框架强耦合

**执行步骤**:
1. 创建状态管理抽象：
   ```python
   class UISessionManager:
       def get(self, key: str, default=None) -> Any
       def set(self, key: str, value: Any) -> None
       def clear(self, key: str) -> None
       def exists(self, key: str) -> bool
   
   class StreamlitSessionManager(UISessionManager):
       # Streamlit specific implementation
   
   class MemorySessionManager(UISessionManager):
       # For testing and other platforms
   ```
2. 替换所有直接的session state操作
3. 为Android端准备SharedPreferences实现

**测试验收**:
- Mock session manager运行UI组件无 `KeyError`
- `grep -r "st\.session_state"` 仅在SessionManager实现中出现
- 单元测试可以使用内存session manager独立运行

---

### PLAN 13 快照差分工具

**PLAN简述**: 实现高效的状态差分算法，支持增量UI更新

**解决的具体问题**:
- UI全量刷新性能低，移动端会有明显卡顿
- 无法实现精确的动画效果
- 难以追踪具体的状态变化

**执行步骤**:
1. 实现状态差分算法：
   ```python
   @dataclass
   class StateDiff:
       changed_fields: List[Tuple[str, Any, Any]]  # path, old, new
       added_items: Dict[str, Any]
       removed_items: Dict[str, Any]
   
   def compute_diff(old: GameStateSnapshot, new: GameStateSnapshot) -> StateDiff
   ```
2. UI组件根据diff进行增量更新
3. 优化动画效果：只对变化的元素进行动画

**测试验收**:
- 单元测试：只改变玩家筹码→diff仅包含筹码相关字段
- 性能测试：差分计算耗时 ≤ 5ms
- UI测试：公共牌不会重复闪烁

---

### PLAN 14 UI常量和主题管理

**PLAN简述**: 抽离硬编码的UI样式，支持主题切换

**解决的具体问题**:
- 颜色、文案硬编码在组件中，难以维护
- 无法支持暗黑模式等主题切换
- 国际化支持困难

**执行步骤**:
1. 创建UI常量文件：
   ```python
   # ui/constants.py
   class UITheme:
       PRIMARY_COLOR = "#1f77b4"
       SUCCESS_COLOR = "#2ca02c"
       WARNING_COLOR = "#ff7f0e"
       ERROR_COLOR = "#d62728"
   
   class UITexts:
       FOLD_BUTTON = "🚫 弃牌"
       CALL_BUTTON = "✅ 跟注"
       RAISE_BUTTON = "📈 加注"
   ```
2. 所有组件使用常量而非硬编码
3. 支持主题切换功能

**测试验收**:
- `grep -r "#[0-9a-fA-F]"` 仅在常量文件中出现
- 主题切换后UI一键生效
- 支持至少2套完整主题（明亮、暗黑）

---

## 📋 MILESTONE 3: 移动端准备 (PLAN 15-20)

### PLAN 15 Android端接口规范设计

**PLAN简述**: 为Android开发设计清晰的JNI/FFI接口规范

**解决的具体问题**:
- 缺乏为Android设计的标准接口
- Python与Java/Kotlin的数据传递没有规范
- 移动端开发者不清楚如何集成游戏逻辑

**执行步骤**:
1. 设计Android接口规范：
   ```java
   // Android端接口定义
   public interface TexasHoldemGame {
       void startNewHand();
       GameStateData getCurrentState();
       ActionResult executeAction(ActionData action);
       void subscribeToEvents(GameEventListener listener);
   }
   ```
2. 使用Chaquopy或类似工具实现Python桥接
3. 创建示例Android项目验证接口

**测试验收**:
- Android示例项目可以调用Python游戏逻辑
- 数据序列化/反序列化正确无误
- 性能测试：接口调用延迟 ≤ 10ms

---

### PLAN 16 异步AI决策架构

**PLAN简述**: 将AI决策改为异步模式，防止阻塞UI线程

**解决的具体问题**:
- AI思考时间会阻塞UI，移动端体验差
- 无法同时处理多个AI的决策
- LLM API调用会导致长时间等待

**执行步骤**:
1. 改造AI策略接口：
   ```python
   class AsyncAIStrategy:
       async def compute_action(self, context: GameContext) -> ActionInput:
           if context.use_llm:
               return await self.call_llm_api(context)
           else:
               await asyncio.sleep(0.1)  # 模拟思考
               return self.rule_based_decision(context)
   ```
2. 在控制器中使用异步任务管理
3. UI层通过回调获取AI决策结果

**测试验收**:
- `pytest.mark.asyncio` 测试：AI思考不阻塞主循环
- 移动端模拟：UI保持响应，显示"AI思考中"状态
- LLM超时测试：自动降级到本地策略

---

### PLAN 17 多AI策略注册表

**PLAN简述**: 实现可插拔的AI策略系统，支持动态切换

**解决的具体问题**:
- 当前AI策略硬编码，难以扩展
- 测试时无法方便地切换不同难度的AI
- 用户无法选择AI对手的风格

**执行步骤**:
1. 实现策略注册系统：
   ```python
   @dataclass
   class AIStrategyInfo:
       name: str
       difficulty: str  # "easy", "medium", "hard"
       style: str      # "conservative", "aggressive", "balanced"
       description: str
   
   class AIStrategyRegistry:
       @staticmethod
       def register(name: str, strategy_class: Type[AIStrategy]):
           # 注册策略
       
       @staticmethod
       def create_strategy(name: str, **kwargs) -> AIStrategy:
           # 创建策略实例
   ```
2. 在配置中支持策略选择
3. UI中提供AI难度选择功能

**测试验收**:
- 参数化测试：不同策略名称→返回不同的决策模式
- 配置驱动测试：YAML配置→自动加载对应AI策略
- 策略热切换测试：游戏中切换AI策略无异常

---

### PLAN 18 跨平台资源管理

**PLAN简述**: 建立统一的资源管理系统，支持不同平台的资源加载

**解决的具体问题**:
- 卡牌图片、音效等资源没有统一管理
- 不同平台的资源路径和格式不同
- 缺乏资源版本管理和更新机制

**执行步骤**:
1. 设计资源管理接口：
   ```python
   class ResourceManager:
       def get_card_image(self, card: Card) -> ImageData
       def get_sound_effect(self, sound: SoundType) -> AudioData
       def get_ui_text(self, key: str, lang: str = "zh") -> str
   
   class PlatformResourceManager(ResourceManager):
       # Platform-specific implementations
   ```
2. 为不同平台实现资源加载器
3. 支持资源的懒加载和缓存

**测试验收**:
- 各平台都能正确加载所需资源
- 资源缓存机制有效，避免重复加载
- 支持至少中英文双语言

---

### PLAN 19 性能监控和诊断

**PLAN简述**: 建立性能监控体系，确保移动端流畅运行

**解决的具体问题**:
- 缺乏性能数据，难以优化移动端体验
- 内存泄漏和性能瓶颈难以发现
- 用户反馈的卡顿问题难以复现

**执行步骤**:
1. 实现性能监控：
   ```python
   class PerformanceMonitor:
       def start_timing(self, operation: str) -> None
       def end_timing(self, operation: str) -> float
       def log_memory_usage(self) -> None
       def export_performance_report(self) -> Dict[str, Any]
   ```
2. 在关键路径添加性能埋点
3. 建立性能基线和告警机制

**测试验收**:
- 单手牌处理时间 ≤ 100ms
- 内存使用稳定，无明显泄漏
- 性能报告包含详细的时间分布

---

### PLAN 20 Android端原生集成验证

**PLAN简述**: 开发Android端原型，验证架构设计的可行性

**解决的具体问题**:
- 理论设计可能在实际移动端开发中遇到问题
- 需要验证性能、兼容性、用户体验
- 为后续iOS开发提供参考

**执行步骤**:
1. 创建Android Studio项目
2. 集成Python游戏逻辑（通过Chaquopy或JNI）
3. 实现基础的游戏界面：
   ```kotlin
   class MainActivity : AppCompatActivity(), GameEventListener {
       private lateinit var gameEngine: TexasHoldemGame
       
       override fun onCreate(savedInstanceState: Bundle?) {
           super.onCreate(savedInstanceState)
           gameEngine = TexasHoldemGameFactory.create()
           gameEngine.subscribeToEvents(this)
       }
   }
   ```
4. 验证完整的游戏流程

**测试验收**:
- Android应用可以完成完整的德州扑克游戏
- 性能测试：界面响应时间 ≤ 100ms
- 兼容性测试：支持Android 8.0+主流设备

---

## 📋 MILESTONE 4: 质量保证 (PLAN 21-24)

### PLAN 21 测试数据工厂

**PLAN简述**: 使用工厂模式生成测试数据，提高测试质量和维护性

**解决的具体问题**:
- 测试中重复手写测试数据，维护成本高
- 修改数据结构后需要同步修改多个测试
- 缺乏边界情况的测试数据生成

**执行步骤**:
1. 使用 `factory_boy` 创建数据工厂：
   ```python
   class PlayerFactory(factory.Factory):
       class Meta:
           model = Player
       
       seat_id = factory.Sequence(lambda n: n)
       name = factory.LazyAttribute(lambda obj: f"Player_{obj.seat_id}")
       chips = factory.Faker('random_int', min=100, max=10000)
   
   class GameStateFactory(factory.Factory):
       class Meta:
           model = GameState
       
       players = factory.SubFactoryList(PlayerFactory, size=4)
   ```
2. 所有测试改用工厂生成数据
3. 提供边界情况的专门工厂

**测试验收**:
- 修改Player字段后只需更新工厂，所有测试自动适配
- Property-based测试：随机生成的数据都符合业务规则
- 覆盖率提升：工厂生成的边界情况发现新的bug

---

### PLAN 22 终极集成测试强化

**PLAN简述**: 强化现有的终极测试，确保重构后的稳定性

**解决的具体问题**:
- 需要确保重构不会影响用户体验
- 验证新架构在高强度使用下的稳定性
- 为移动端开发提供质量基线

**执行步骤**:
1. 扩展 `test_streamlit_ultimate_user_experience.py`：
   ```python
   # 增加更多场景测试
   def test_extreme_scenarios():
       # 极端情况：全员all-in、超长游戏等
   
   def test_error_recovery():
       # 错误恢复：网络中断、异常输入等
   
   def test_performance_stress():
       # 性能压力：连续10000手牌
   ```
2. 添加移动端特定的测试场景
3. 建立持续集成中的自动回归测试

**测试验收**:
- 10000手牌测试：完成率 ≥ 99.5%，性能 ≥ 10手/秒
- 错误恢复测试：各种异常都能正确处理
- 内存稳定性：长时间运行无内存泄漏

---

### PLAN 23 CI/CD移动端集成

**PLAN简述**: 将移动端构建和测试集成到CI/CD流程

**解决的具体问题**:
- 移动端代码变更缺乏自动化验证
- 跨平台兼容性问题发现较晚
- 发布流程复杂，容易出错

**执行步骤**:
1. 配置GitHub Actions的移动端构建：
   ```yaml
   - name: Build Android APK
     run: |
       cd android_client
       ./gradlew assembleDebug
   
   - name: Run Android Tests
     run: |
       ./gradlew test
   ```
2. 添加跨平台兼容性测试
3. 自动化版本号管理和发布

**测试验收**:
- PR提交后自动触发移动端构建
- 构建失败时自动阻止合并
- 自动生成可测试的APK文件

---

### PLAN 24 文档和API规范完善

**PLAN简述**: 完善技术文档，为移动端开发者提供清晰的集成指南

**解决的具体问题**:
- 移动端开发者缺乏详细的集成文档
- API变更后文档更新不及时
- 缺乏最佳实践和示例代码

**执行步骤**:
1. 自动生成API文档：
   ```python
   # 使用pdoc生成完整的API文档
   # 包含接口定义、参数说明、示例代码
   ```
2. 编写移动端集成指南：
   - Android集成步骤
   - 性能优化建议
   - 常见问题解答
3. 提供完整的示例项目

**测试验收**:
- 新开发者能根据文档在2小时内完成基础集成
- API文档覆盖率 ≥ 95%
- 示例代码能正确编译和运行

---

## 🏁 验收里程碑

**最终验收标准**：
1. ✅ `test_streamlit_ultimate_user_experience.py` 通过（1000手牌，完成率≥98%）
2. ✅ 所有单元测试和集成测试通过
3. ✅ Android原型应用可以完成完整游戏
4. ✅ 代码架构清晰：三分控制器、事件驱动、双层UI接口
5. ✅ 性能达标：手牌处理≤100ms，UI响应≤50ms
6. ✅ 文档完善：API文档、集成指南、示例代码

**后续发展方向**：
- iOS端开发（基于Android端经验）
- LLM AI增强（GPT-4o/Claude集成）
- Steam平台发布（桌面端优化）
- 多人在线模式（微服务架构扩展）

---

## 📚 相关文档

- **终极测试**: `v2/tests/integration/test_streamlit_ultimate_user_experience.py`
- **API文档**: `docs/` 目录包含完整的API文档
- **游戏规则**: `TexasHoldemGameRule.md` 详细的德州扑克规则说明
- **完成记录**: `TASK_DONE.md` 详细的完成任务记录
- **Android集成**: `docs/android_integration.md` Android开发指南

## 🛠️ 开发工具

### 运行终极测试
```bash
# 运行终极用户体验测试（1000手牌）
.venv/Scripts/python -m pytest v2/tests/integration/test_streamlit_ultimate_user_experience.py::test_streamlit_ultimate_user_experience_full -v

# 快速版本（10手牌）
.venv/Scripts/python -m pytest v2/tests/integration/test_streamlit_ultimate_user_experience.py::test_streamlit_ultimate_user_experience_quick -v

# 防作弊检查
.venv/Scripts/python -m pytest v2/tests/integration/test_streamlit_ultimate_user_experience.py::test_anti_cheating_core_module_usage -v
```

### 运行所有测试
```bash
# 运行所有测试
.venv/Scripts/python -m pytest v2/tests/ -v

# 运行性能测试
.venv/Scripts/python -m pytest v2/tests/ -m "not slow" -v

# 运行慢速测试
.venv/Scripts/python -m pytest v2/tests/ -m "slow" -v
```

### 生成文档
```bash
# 使用pdoc生成API文档
.venv/Scripts/python scripts/build-docs.py
```

### 清理项目
```bash
# 清理临时文件和缓存
.venv/Scripts/python scripts/cleanup.py
```

### 启动游戏
```bash
# Web界面（推荐）
.venv/Scripts/streamlit run v2/ui/streamlit/app.py

# CLI界面
.venv/Scripts/python -m v2.ui.cli.cli_game
```

详细的完成记录请查看 `v2/TASK_DONE.md` 