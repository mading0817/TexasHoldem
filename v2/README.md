# Texas Hold'em Poker Game v2

这是德州扑克游戏的重构版本，采用了更好的架构设计和模块分离。

## 架构概览

### 核心层 (core/)
- **enums.py**: 游戏相关枚举定义 ✅
- **cards.py**: 扑克牌和牌堆对象 ✅
- **evaluator.py**: 牌型评估器 ✅
- **player.py**: 玩家状态管理 ✅
- **validator.py**: 行动验证器 ✅
- **pot.py**: 边池管理器 ✅
- **state.py**: 游戏状态管理 ✅

### 控制器层 (controller/)
- **poker_controller.py**: 游戏控制器 ✅
- **dto.py**: 数据传输对象 ✅
- **decorators.py**: 事务装饰器 ✅
- 核心逻辑与UI的桥梁 ✅

### AI层 (ai/)
- **base.py**: AI策略协议接口 ✅
- **simple_ai.py**: 简单AI实现 ✅

### 用户界面层 (ui/)
- **cli/**: 命令行界面 ✅
- **streamlit/**: Web界面 (Streamlit) 🚧

## 设计原则

1. **分层架构**: 清晰的职责分离
2. **依赖注入**: 松耦合设计，支持测试
3. **类型安全**: 使用枚举和类型注解
4. **不可变性**: 核心数据对象使用frozen dataclass
5. **Google Docstring**: 统一的文档字符串格式
6. **事件驱动**: 使用事件总线解耦组件通信

## 开发状态

### ✅ 已完成 (PLAN #1-28)
- v2目录结构建立
- 核心枚举定义 (Suit, Rank, ActionType, Phase等)
- 扑克牌对象 (Card, Deck)
- **牌型评估器 (SimpleEvaluator, HandResult)**
- **玩家状态管理 (Player)**
- **行动验证器 (ActionValidator)**
- **边池管理器 (PotManager, SidePot)**
- **游戏状态管理 (GameState, GameSnapshot)**
- **核心API统一入口 (v2.core公共API)**
- **确定性随机数控制 (固定种子测试)**
- **Google Docstring完善 (0个pydocstyle错误)**
- **文档生成 (pdoc自动更新)**
- **项目清理脚本 (cleanup.py)**
- **游戏控制器 (PokerController)**
- **AI策略系统 (AIStrategy协议, SimpleAI实现)**
- **事务原子性 (atomic装饰器)**
- **事件系统 (EventBus, EventType, GameEvent)**
- **CLI适配 (TexasHoldemCLI)**
- **数据传输对象 (DTO系统)**
- **10手牌筹码守恒验证**
- **CLI显示逻辑分离 (CLIRenderer)**
- **CLI输入处理强校验 (CLIInputHandler)**
- **CLI模块完整docstring**
- 基础测试框架 (327个测试用例全部通过)
- **文档生成**: 使用pdoc生成完整API文档，包含15个HTML文件

### 🚧 进行中
- Streamlit MVP (PLAN #29-37)

### 📋 计划中
- Streamlit MVP (PLAN #29-37)
- 测试体系完善 (PLAN #38-45)
- 收尾与维护 (PLAN #46-50)

## 测试覆盖

当前测试状态：
- `tests/unit/test_v2_enums.py`: 20个测试用例 ✅
- `tests/unit/test_v2_cards.py`: 24个测试用例 ✅
- `tests/unit/test_v2_evaluator.py`: 17个测试用例 ✅
- `tests/unit/test_v2_evaluator_compatibility.py`: 3个兼容性测试 ✅
- `tests/unit/test_v2_player.py`: 52个测试用例 ✅
- `tests/unit/test_v2_validator.py`: 34个测试用例 ✅
- `tests/unit/test_v2_pot.py`: 28个测试用例 ✅
- `tests/unit/test_v2_state.py`: 24个测试用例 ✅
- `tests/core/test_public_api.py`: 10个测试用例 ✅
- `tests/unit/test_v2_deterministic_random.py`: 8个测试用例 ✅
- `tests/unit/test_v2_controller.py`: 19个测试用例 ✅
- `tests/unit/test_v2_events.py`: 18个测试用例 ✅
- `tests/unit/test_v2_dto.py`: 20个测试用例 ✅
- `tests/unit/test_v2_cli_render.py`: 13个测试用例 ✅
- `tests/unit/test_v2_cli_input_handler.py`: 18个测试用例 ✅
- `tests/system/test_play_10_hands.py`: 筹码守恒系统测试 ✅

总计：327个测试用例，100%通过率

## 核心功能

### 牌型评估器
v2的牌型评估器提供以下功能：
- 支持所有标准德州扑克牌型（包括皇家同花顺）
- 从7张牌中选择最佳5张牌组合
- 牌型比较和排名
- 与v1评估器100%兼容

支持的牌型（按强度排序）：
1. 皇家同花顺 (Royal Flush)
2. 同花顺 (Straight Flush)
3. 四条 (Four of a Kind)
4. 葫芦 (Full House)
5. 同花 (Flush)
6. 顺子 (Straight)
7. 三条 (Three of a Kind)
8. 两对 (Two Pair)
9. 一对 (One Pair)
10. 高牌 (High Card)

### 玩家状态管理
v2的玩家状态管理提供以下功能：
- 完整的筹码管理（下注、扣除、增加）
- 手牌管理（设置、获取、隐藏显示）
- 状态管理（活跃、弃牌、全押、出局）
- 位置标记（庄家、小盲、大盲）
- 自动状态变更（全押时自动设置ALL_IN状态）
- 纯数据对象，不含UI打印功能

### 边池管理器
v2的边池管理器提供以下功能：
- 支持复杂的多边池场景（全押、不同金额）
- 自动计算边池分配和玩家资格
- 筹码完整性验证，确保筹码守恒
- 支持多个获胜者的奖金分配
- 边界情况处理（空贡献、单人场景等）

### 行动验证器
v2的行动验证器提供以下功能：
- 支持所有行动类型的验证（FOLD、CHECK、CALL、BET、RAISE、ALL_IN）
- 智能转换功能（筹码不足时自动转为ALL_IN，无下注时CALL转为CHECK）
- 详细的验证错误信息和建议
- 协议接口设计，支持不同的游戏状态实现

### 游戏控制器
v2的游戏控制器提供以下功能：
- 完整的游戏流程控制（开始新手牌、执行行动、阶段转换）
- AI策略协议接口，支持依赖注入设计
- 游戏状态快照功能，支持UI显示和调试
- 手牌结果统计和分析
- 原子API设计，确保操作的一致性
- 支持多种游戏模式和配置

## 文档

### API文档
完整的API文档已使用pdoc生成，位于 `docs/v2/` 目录：
- 主页: `docs/v2/index.html`
- 核心模块: `docs/v2/v2/core.html`
- 控制器模块: `docs/v2/v2/controller.html`
- 枚举定义: `docs/v2/v2/core/enums.html`
- 扑克牌对象: `docs/v2/v2/core/cards.html`
- 牌型评估器: `docs/v2/v2/core/evaluator.html`
- 玩家状态管理: `docs/v2/v2/core/player.html`
- 行动验证器: `docs/v2/v2/core/validator.html`
- 边池管理器: `docs/v2/v2/core/pot.html`
- 游戏状态管理: `docs/v2/v2/core/state.html`

所有模块都包含完整的Google格式docstring和类型注解。

## 使用方法

目前v2版本仍在开发中。完成后将提供：
- 命令行界面 (CLI)
- Web界面 (Streamlit)
- 完整的API文档

详细使用方法将在开发完成后提供。

## 开发指南

按照 `TASK_GUIDE.txt` 中的50条PLAN逐步实施，确保：
- 每个模块都有完整的单元测试
- 使用Google格式的docstring
- 通过pdoc生成文档
- 定期运行10手牌回归测试 