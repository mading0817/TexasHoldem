# Texas Hold'em Poker Game v2

这是德州扑克游戏的重构版本，采用了更好的架构设计和模块分离。

## 架构概览

### 核心层 (core/)
- **enums.py**: 游戏相关枚举定义 ✅
- **cards.py**: 扑克牌和牌堆对象 ✅
- **evaluator.py**: 牌型评估器 🚧
- **player.py**: 玩家状态管理 🚧
- **validator.py**: 行动验证器 🚧
- **pot.py**: 边池管理器 🚧
- **state.py**: 游戏状态管理 🚧

### 控制器层 (controller/)
- 应用控制逻辑 🚧
- 数据传输对象 (DTO) 🚧
- 核心逻辑与UI的桥梁 🚧

### 用户界面层 (ui/)
- **cli/**: 命令行界面 🚧
- **streamlit/**: Web界面 (Streamlit) 🚧

## 设计原则

1. **分层架构**: 清晰的职责分离
2. **依赖注入**: 松耦合设计，支持测试
3. **类型安全**: 使用枚举和类型注解
4. **不可变性**: 核心数据对象使用frozen dataclass
5. **Google Docstring**: 统一的文档字符串格式

## 开发状态

### ✅ 已完成 (PLAN #1-6)
- v2目录结构建立
- 核心枚举定义 (Suit, Rank, ActionType, Phase等)
- 扑克牌对象 (Card, Deck)
- 基础测试框架 (44个测试用例全部通过)
- **文档生成**: 使用pdoc生成完整API文档，包含4个HTML文件

### 🚧 进行中 (PLAN #7-18)
- 牌型评估器迁移
- 玩家状态管理
- 行动验证器
- 边池计算
- 游戏状态管理

### 📋 计划中
- 控制器层重构 (PLAN #19-25)
- CLI适配 (PLAN #26-28)
- Streamlit MVP (PLAN #29-37)
- 测试体系完善 (PLAN #38-45)
- 收尾与维护 (PLAN #46-50)

## 测试覆盖

当前测试状态：
- `tests/unit/test_v2_enums.py`: 20个测试用例 ✅
- `tests/unit/test_v2_cards.py`: 24个测试用例 ✅

总计：44个测试用例，100%通过率

## 文档

### API文档
完整的API文档已使用pdoc生成，位于 `docs/v2/` 目录：
- 主页: `docs/v2/index.html`
- 核心模块: `docs/v2/v2/core.html`
- 枚举定义: `docs/v2/v2/core/enums.html`
- 扑克牌对象: `docs/v2/v2/core/cards.html`

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