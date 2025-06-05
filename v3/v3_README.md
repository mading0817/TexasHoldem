# Rule: Total lines in this file must not exceed 100.

# 🃏 德州扑克 v3 - 架构重构版

## 📖 项目概述与目标

基于**DDD+状态机+CQRS**架构的完全重构版本。

### 🎯 核心目标
- **Streamlit端到端1000手牌测试**：确保用户体验完整可靠。
- **架构清晰**：模块化、职责明确。
- **扩展性强**：支持未来扑克变体和新功能。
- **测试完备**：TDD驱动，反作弊系统保障。

## 🏗️ 核心架构

### 分层
- UI Layer: Streamlit界面
- Application Layer: 命令/查询服务 (CQRS)
- Domain Layer: 核心业务逻辑 (DDD)

### 主要模块
- `core/`: 领域核心，零外部依赖。
  - `deck/`: 牌组管理 (Card, Deck) ✅
  - `eval/`: 牌型评估 (HandEvaluator) ✅
  - `events/`: 领域事件系统 (EventBus, DomainEvent) ✅
  - `state_machine/`: 游戏状态机 ✅
  - `betting/`, `pot/`, `chips/`: 下注和筹码管理 ✅
  - `snapshot/`: 状态快照系统 (GameStateSnapshot, SnapshotManager) ✅
- `application/`: 应用服务，协调核心。
- `ui/streamlit/`: Streamlit UI实现。
- `tests/`: 测试（单元、性质、集成、反作弊）。

## 📏 开发原则

- **TDD优先**: 先写测试，再写代码 (Red → Green → Refactor)。
- **反作弊必须**: 所有测试通过反作弊检查。
- **模块访问权限**: 遵循定义好的模块导入规则。
- **类型安全**: 强制类型注解 (mypy)。
- **代码规范**: 遵循命名约定。

## 🧪 测试策略与运行

### 测试分层
- Unit Tests
- Property Tests
- Integration Tests
- Ultimate Test (Streamlit 1000手)

### 运行测试
```bash
# 安装依赖
pip install -r requirements.txt -r requirements-dev.txt

# 运行所有测试
pytest v3/tests/ -v

# 运行终极测试 (完整版)
pytest v3/tests/integration/test_streamlit_ultimate_user_experience_v3.py::test_full -v
```

## 🛡️ 反作弊系统 (Anti-Cheat)

确保测试不绕过真实业务逻辑。

### 主要检查项
1. 对象真实性 (CoreUsageChecker)
2. 状态一致性 (StateConsistencyChecker)
3. 代码覆盖率 (CoverageVerifier)
4. 模块依赖 (DependencyChecker)

### 覆盖范围
Unit, Property, Integration, Ultimate 所有测试。

## 📚 相关文档

- **详细任务指南**: [v3_TASK_GUIDE.md](v3_TASK_GUIDE.md)
- **终极测试**: [test_streamlit_ultimate_user_experience_v3.py](mdc:v3/tests/integration/test_streamlit_ultimate_user_experience_v3.py)
- **反作弊系统**: `v3/tests/anti_cheat/` 目录

## 🚀 快速开始

请参考"运行测试"中的环境设置和命令。

## ✅ 最新完成任务

### 🎉 Fold操作不变量检查修复 (2025-06-05 完成)
- ✅ 深入分析发现all_in玩家状态处理的语义混淆问题
- ✅ 修复了SnapshotManager._get_active_player_position方法
- ✅ 实现了PhaseHandler中fold操作的原子性
- ✅ 修正了_advance_to_next_player的all_in玩家判断逻辑
- ✅ 分离了"在手牌中"和"可以行动"两个概念
- ✅ 从结构和设计层面根本性解决问题
- 📊 Ultimate Test结果：手牌完成率100% (2/2)，行动成功率100% (11/11)，零错误

### PLAN 12: 筹码系统实现 (2025-01-27 完成)
- ✅ 完善了筹码账本 (ChipLedger) 的原子性操作
- ✅ 增强了下注引擎 (BettingEngine) 的验证逻辑
- ✅ 优化了边池管理器 (PotManager) 的计算准确性
- ✅ 新增13个边缘情况测试，覆盖并发操作、全押场景等
- ✅ 总计39个筹码相关测试全部通过
- ✅ 反作弊检查全部通过

### PLAN 11: 状态机核心实现 (2025-01-20 完成)
- ✅ 完成 PreFlopHandler 的盲注设置和发牌逻辑
- ✅ 完成 FlopHandler 的下注重置和翻牌发牌逻辑
- ✅ 修复不变量违反问题，确保筹码守恒和阶段一致性
- ✅ 所有应用服务测试通过 (24/24)
- ✅ 所有状态机单元测试通过 (15/15)
- ✅ 所有核心模块测试通过 (125/125)

### PLAN 10: 反作弊测试系统 (2025-01-27 完成)
- ✅ 增强了核心模块使用检查器 (CoreUsageChecker)
- ✅ 完善了状态一致性检查 (StateConsistencyChecker)  
- ✅ 实现了代码覆盖率验证 (CoverageVerifier)
- ✅ 修复了Python内置类型误报问题
- ✅ 所有反作弊集成测试通过 (9/9)

### 测试套件全面Review与验证 (已完成)
已完成对v3项目现有单元测试、性质测试和集成测试的全面Review。
所有测试文件均已根据v3开发指南和反作弊要求进行了检查和必要的修正。
反作弊系统现已完全建立并验证，确保所有测试的可靠性和真实性。

下一个主要任务将记录在 `v3_TASK_GUIDE.md` 中。

---

**德州扑克v3** - 架构清晰 · 测试完备 · 扩展性强 