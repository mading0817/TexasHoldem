# TexasHoldem Project

## 项目目标

开发以LLM AI为对手的单人单机德州扑克游戏。初期完成基于Python的网页端Demo，后续支持多平台扩展。

## 第一阶段 (MVP) 范围

实现一个可玩的单手牌命令行版本，包含基础的德州扑克游戏逻辑和与AI的交互。

核心功能：
- 完整的单手牌流程（发牌、翻牌前、翻牌、转牌、河牌下注轮、比牌、结算）。
- 支持多玩家（1个人类玩家 + 多个AI玩家）。
- 实现标准的边池计算规则 **（已实现并验证）**。
- 人类玩家通过命令行输入数字选择动作。
- AI玩家进行基础决策（MVP阶段不考虑复杂策略和性格）。

已实现的核心游戏逻辑组件包括：
- 发牌 (Deck)
- **状态机基础 (BasePhase)**
- **下注轮控制 (GameState)**
- **标准边池计算和分配 (PotManager)**
- **具体Phase子类 (PreFlop, Flop, Turn, River, Showdown)**
- **行动验证与智能转换 (ActionValidator)**
- **游戏控制器 (GameController)**
- **应用服务层 (PokerController) - 新增**
- **玩家行动表示 (Action)**
- 基础牌型评估 (待实现)

## 使用方式

### 运行CLI游戏
```bash
# 方式1：直接运行CLI游戏
python cli_game.py

# 方式2：作为模块运行
python -m cli_game

# 方式3：在虚拟环境中运行（推荐）
.venv\Scripts\python.exe cli_game.py    # Windows
./venv/bin/python cli_game.py           # Linux/Mac
```

### 游戏控制
- 游戏开始时可配置玩家数量（2-10人）和初始筹码
- 人类玩家通过数字选择行动（1-6）
- 支持调试模式，显示详细的Controller状态信息
- 随时可按Ctrl+C退出游戏

### 测试验证
```bash
# 运行所有测试
python tests/run_all_tests.py

# 手动验证Phase 1功能
python tests/manual_test_phase1.py

# 快速CLI集成测试
python tests/quick_cli_test.py

# 运行特定测试类型
python -m pytest tests/unit/            # 单元测试
python -m pytest tests/test_controller/ # Controller测试
```

## 技术栈

- 后端 / 游戏逻辑: Python (FastAPI)
- 数据存储: SQLite (MVP阶段暂不涉及持久化，数据存内存)
- 前端: React + TypeScript (MVP阶段为命令行界面)
- AI集成: 通过适配器模式调用LLM API (如 Gemini, ChatGPT)
- 测试: pytest, pytest-cov, psutil

## 架构模式

基于MVC (Model-View-Controller) 模式，采用 **分层架构 + 应用服务层**：

- **应用服务层** (**PokerController**): 
  - 提供Copy-on-Write的原子性事务操作
  - 管理游戏状态的版本化和快照
  - 协调各阶段的游戏流程，为前端提供统一接口
- **Model**:
  - 核心游戏逻辑 (**Core Game Logic**, 包括 **GameState, ActionValidator, PotManager, Phases**等模块)
  - AI记忆 (AIMemory - 待实现)
- **View**: 用户界面 (**CLI界面 已重构完成**，通过PokerController交互)
- **Controller**: 已整合到应用服务层 (**PokerController**)

游戏逻辑采用**按GamePhase拆分的状态机模式**，每个阶段独立处理。

## 测试架构 (v2.0 - 已完成重构)

采用模块化测试架构，按功能分类组织：

```
tests/
├── common/          # 通用测试组件和基础设施
├── unit/            # 单元测试 - 快速验证单个组件
├── integration/     # 集成测试 - 验证组件协作
├── e2e/            # 端到端测试 - 完整用户场景
├── rules/          # 规则合规性测试 - 德州扑克规则验证
├── system/         # 系统级测试 - 复杂场景和完整性
├── performance/    # 性能测试 - 性能指标验证
├── security/       # 安全测试 - 反作弊和数据完整性
├── temp/           # 临时验证脚本
├── test_controller/ # PokerController单元测试 - Phase 1 新增
├── manual_test_phase1.py # 手动测试脚本 - Phase 1 验证
├── quick_cli_test.py     # 快速CLI测试 - Phase 1 验证
└── run_all_tests.py # 测试运行器
```

**测试运行方式**：
- 运行所有测试: `python tests/run_all_tests.py`
- 运行特定类型测试: `python -m pytest tests/[test_type]/` (例如 `tests/unit/`, `tests/rules/`, `tests/test_controller/`)
- Phase 1验证: `python tests/manual_test_phase1.py`

## 核心MVP设计决策

- **筹码单位**: 最小单位为 1，SB = 1，BB = 2。
- **游戏结束**: 所有筹码集中于一个玩家时游戏结束。筹码归零的玩家退出当前手牌。
- **玩家座位**: 人类玩家座位可配置，初期实现可能固定座位 0。
- **AI 类型**: 支持混合使用不同 LLM 模型（Gemini, ChatGPT, Random），通过适配器模式集成，MVP阶段不考虑AI性格。
- **LLM 接口**: JSON 格式输入/输出，无效动作抛出异常。
- **用户界面**: 极简命令行，玩家输入数字进行操作选择 (0-9) - **已重构完成，通过PokerController交互**。
- **手牌显示**: 人类玩家显示自己手牌，其他玩家显示为 XX。
- **历史记录**: 记录历史动作序列 (MVP阶段AI暂不使用)。
- **当前下注 (current_bet)**: 表示玩家在本轮已投入的筹码总额。
- **技术简化**: MVP阶段不包含网络层、并发控制、持久化。
- **边池计算**: 实现了标准的边池计算和分配逻辑，包括单人All-in多余筹码的返还机制。
- **行动处理**: 实现了行动的验证和智能转换（例如不足筹码加注自动转为All-in），并修复了Pre-flop阶段行动顺序的bug。玩家行动由 `Action` 类表示。
- **游戏状态管理**: 实现了带有事务性上下文管理器和clone方法的GameState，保证状态一致性，并修复了底池计算未实时更新的bug。通过**PokerController**提供Copy-on-Write的原子性事务。
- **异常处理**: 定义了PokerGameError、InvalidActionError等业务异常。

## 开发优先级 (MVP)

1. ✅ **基础数据结构** (Card, Deck, Player, GameState, SeatStatus, ActionEvent) - **已完成并充分测试**。
2. ✅ **核心游戏逻辑** (发牌、状态机、下注轮控制、标准边池计算、牌型评估基础框架) - **已实现基础框架，通过模块化测试验证**。
3. ✅ **测试架构重构和关键测试修复** - **已完成模块化重构，并修复了unittest集成、Player和TestResult构造函数问题**。
4. ✅ **Controller抽离 (Phase 1)** - **已完成应用服务层PokerController的创建和CLI的完整重构，通过手动测试验证功能正常**。
5. ✅ **Domain纯化 (Phase 2)** - **已完成核心业务逻辑向Phase/Domain层的下沉，Controller简化为纯应用服务协调器**。
6. ✅ **事件系统 & AI策略 (Phase 3)** - **已完成AI策略系统、事件总线和决策引擎的实现，支持保守、激进、随机三种AI策略**。
7. 🔄 **牌型评估系统** - 正在实现中。
8. 🔄 **命令行界面完善** (状态显示, 数字输入处理) - CLI基础功能已通过Controller重构完成，需要进一步优化用户体验。
9. 🔄 **接口收敛 & 清理 (Phase 4)** - 计划中：优化性能、清理遗留代码、准备多前端支持。
10. ⏳ **整合与测试** (端到端单手牌流程, 边池边界测试) - 持续进行。

## 最近更新

**v2.3 Phase 1 Controller抽离完成 (2024年5月29日)**:
- ✅ 成功完成应用服务层 `app_controller.poker_controller` 和完整的DTOs `app_controller.dto_models`
- ✅ 完全重构 CLI `cli_game.py`，移除直接GameState访问，全部通过 PokerController 进行游戏状态管理
- ✅ 实现Copy-on-Write原子性事务机制，支持自动回滚和版本控制
- ✅ 建立完整的状态快照系统，支持增量更新优化和视角限制
- ✅ 创建 `tests/test_controller`, `tests/manual_test_phase1.py`, `tests/quick_cli_test.py` 等测试文件
- ✅ 修复关键问题：Player类方法调用（add_hole_card → set_hole_cards）
- ✅ 所有手动测试通过，验证了重构的正确性和功能完整性
- ✅ 为Phase 2（Domain纯化）做好准备，建立了事件模型基础

**v2.4 Phase 2 Domain纯化完成 (2024年6月5日)**:
- ✅ 成功完成核心业务逻辑向Phase/Domain层的下沉
- ✅ Controller作为纯粹的应用服务层，将逻辑委托给Domain层处理
- ✅ manual_test_phase2.py 手动测试执行成功，验证了Domain纯化的效果

**v2.5 Phase 3 事件系统 & AI策略完成 (2024年5月29日)**:
- ✅ 成功实现完整的AI策略系统（`ai_players/ai_strategy.py`）
- ✅ 支持保守型、激进型、随机三种AI策略，各具不同决策特征
- ✅ 建立了线程安全的事件总线系统（`ai_players/event_bus.py`）
- ✅ 实现了统一的AI决策引擎（`ai_players/ai_engine.py`）
- ✅ 完成CLI与AI引擎的深度集成，重构`get_ai_action`方法
- ✅ 建立了完整的手牌强度评估器和多层回退机制
- ✅ 创建了详细的测试验证（`tests/manual_test_phase3.py`）
- ✅ 所有5项测试全部通过，验证了AI策略的差异性和决策有效性
- ✅ 为Phase 4（接口收敛 & 清理）做好准备

**v2.6 Phase 4 接口收敛 & 清理完成 (2024年5月29日)**:
- ✅ 成功完成CLI层的完全清理，移除了所有对Domain层的直接访问
- ✅ 重构`cli_game.py`为v3.0版本，实现了完全通过Controller快照获取数据
- ✅ 建立了高效的缓存机制，包括`_cached_snapshot`和版本控制
- ✅ 重构了所有关键方法为快照版本（display、AI决策、用户交互等）
- ✅ 实现了智能缓存和增量更新，提升了性能表现
- ✅ 创建了完整的测试验证（`tests/manual_test_phase4.py`）
- ✅ 所有15项测试全部通过，验证了架构收敛的成功
- ✅ 为多前端支持做好准备，完成了应用架构的完全重构

**当前状态**: **Phase 4 接口收敛 & 清理已完成**，CLI层完全通过Controller快照获取数据，消除了对Domain层的直接访问。应用架构重构全部完成（4/4 Phases），为多前端支持做好了准备。

**下一阶段计划**: 
- 完善牌型评估系统
- 接口稳定性测试
- 准备多前端支持
