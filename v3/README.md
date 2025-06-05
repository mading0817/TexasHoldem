# V3 德州扑克项目

## 🎯 项目概述

V3版本是一个完全重构的德州扑克项目，严格遵循CQRS模式和分层架构，支持1000手牌的高强度终极测试。

## 🏗️ 核心架构

### CQRS分层设计
```
UI层 (Streamlit/CLI)
    ↓ 只允许调用
Application层 (CommandService, QueryService, GameFlowService...)
    ↓ 只允许调用  
Core层 (状态机, 筹码管理, 卡牌系统...)
```

### 🛡️ 反作弊系统
- **CoreUsageChecker**: 确保所有测试使用真实的core模块
- **StateConsistencyChecker**: 验证筹码守恒和游戏状态一致性
- **反作弊验证**: 所有测试必须通过anti-cheat检查

## 🎮 核心功能

### 游戏系统
- ✅ **完整德州扑克规则**: 支持2-10人游戏
- ✅ **状态机**: 精确的阶段管理 (INIT → PRE_FLOP → FLOP → TURN → RIVER → FINISHED)
- ✅ **筹码系统**: 严格的筹码守恒验证
- ✅ **下注引擎**: 支持fold、check、call、raise、all-in
- ✅ **边池计算**: 精确的边池分配算法
- ✅ **AI玩家**: 基于Treys的智能决策

### CQRS架构服务
- ✅ **GameCommandService**: 处理所有状态变更命令
- ✅ **GameQueryService**: 处理所有查询操作
- ✅ **GameFlowService**: 游戏流程控制服务
- ✅ **TestStatsService**: 测试统计服务

## 🏆 重大成就: 终测CQRS重构 (2024-12-05)

### 📊 Phase 1-2 成功指标
- ✅ **快速版终测**: 15手牌，100%完成率，105手/秒
- ✅ **完整版终测**: 50手牌，100%完成率，110手/秒
- ✅ **筹码守恒**: 完美守恒，0违反
- ✅ **架构合规**: UI层完全遵循CQRS模式
- ✅ **性能基准**: 远超预期5手/秒目标
- ✅ **AI决策重构**: UI层随机逻辑完全移除

### 🔄 架构重构成果

#### Phase 1: GameFlowService
**重构前 (违规)**:
- UI层包含200+行复杂业务逻辑
- 违规调用core/ai模块
- 直接控制游戏流程

**重构后 (合规)**:
- UI层调用一行`flow_service.run_hand()`
- 严格遵循CQRS模式
- 业务逻辑完全在Application层

#### Phase 2: AI决策服务
**重构前 (违规)**:
- UI层直接使用`random.choice()`
- AI决策逻辑分散在UI层
- 硬编码概率配置

**重构后 (合规)**:
- 使用`query_service.make_ai_decision()`
- 参数化AI配置
- 完善错误处理机制

### 🚀 新增核心服务

#### GameFlowService
游戏流程控制服务：
```python
class GameFlowService:
    def run_hand(self, game_id: str, config: HandFlowConfig) -> CommandResult
    def force_finish_hand(self, game_id: str, max_attempts: int = 10) -> CommandResult
    def advance_until_finished(self, game_id: str, max_attempts: int = 10) -> CommandResult
```

#### AI决策服务增强
```python
# Application层统一AI决策接口
def make_ai_decision(self, game_id: str, player_id: str, 
                    ai_config: Optional[Dict[str, Any]] = None) -> QueryResult
```

## 🧪 测试系统

### 测试层级
1. **单元测试**: 测试单个模块功能
2. **属性测试**: 验证数学不变量（筹码守恒等）
3. **集成测试**: 测试跨模块协作
4. **终极测试**: 1000手牌Streamlit模拟

### TDD开发规范
- ✅ **Red-Green-Refactor**: 严格TDD循环
- ✅ **反作弊验证**: 每个测试必须通过anti-cheat检查
- ✅ **95%+覆盖率**: Core模块高覆盖率要求
- ✅ **性能基准**: 所有测试必须满足性能要求

### 测试命令
```bash
# 单元测试
.venv\Scripts\python -m pytest v3\tests\unit\ -v

# GameFlowService测试
.venv\Scripts\python -m pytest v3\tests\unit\test_game_flow_service.py -v

# Phase 2 AI决策重构验证
.venv\Scripts\python -m pytest v3\tests\unit\test_phase2_ai_decision_refactor.py -v

# 终极测试 (快速版)
.venv\Scripts\python -m pytest v3\tests\integration\test_streamlit_ultimate_user_experience_v3.py::test_streamlit_ultimate_user_experience_v3_quick -v

# 终极测试 (完整版)
.venv\Scripts\python -m pytest v3\tests\integration\test_streamlit_ultimate_user_experience_v3.py::test_streamlit_ultimate_user_experience_v3_full -v
```

## 📁 项目结构

```
v3/
├── core/                   # 核心业务逻辑
│   ├── state_machine/     # 游戏状态机
│   ├── betting/           # 下注引擎
│   ├── chips/             # 筹码管理
│   ├── deck/              # 卡牌系统
│   ├── pot/               # 底池计算
│   ├── eval/              # 牌力评估
│   ├── rules/             # 游戏规则
│   ├── invariant/         # 不变量检查
│   ├── events/            # 领域事件
│   └── snapshot/          # 状态快照
├── application/           # 应用服务层
│   ├── command_service.py # 命令服务
│   ├── query_service.py   # 查询服务
│   ├── game_flow_service.py # 游戏流程服务
│   └── test_stats_service.py # 测试统计服务
├── ai/                    # AI玩家
│   ├── Treys/            # Treys AI实现
│   └── Dummy/            # 简单AI实现
├── tests/                 # 测试套件
│   ├── unit/             # 单元测试
│   ├── property/         # 属性测试
│   ├── integration/      # 集成测试
│   └── anti_cheat/       # 反作弊检查
└── docs/                  # 项目文档
```

## 🚀 快速开始

### 环境设置
```bash
# 激活虚拟环境
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 运行游戏
```bash
# 运行终极测试（推荐）
.venv\Scripts\python -m pytest v3\tests\integration\test_streamlit_ultimate_user_experience_v3.py::test_streamlit_ultimate_user_experience_v3_quick -v
```

## 📚 开发指南

### 新功能开发流程
1. **分析架构**: 确定功能属于哪个层级
2. **TDD开发**: 先写测试，再写实现
3. **反作弊验证**: 确保测试通过CoreUsageChecker
4. **集成测试**: 验证与现有系统集成
5. **性能验证**: 确保满足性能要求

### 代码规范
- **模块访问**: core只能导入core，application可导入core，UI只能导入application
- **命名规范**: PascalCase类名，snake_case方法名
- **类型注解**: 所有公共方法必须有类型注解
- **文档字符串**: 使用Google格式docstring

## 🔬 关键特性

### 1. 筹码守恒
严格的筹码守恒验证，确保游戏中筹码总数永远不变：
```python
总筹码 = 玩家筹码之和 + 底池筹码 + 边池筹码
```

### 2. 状态机管理
精确的游戏阶段控制，每个状态转换都经过验证。

### 3. 反作弊系统
所有测试必须使用真实的core模块，防止mock或stub影响测试有效性。

### 4. CQRS模式
严格分离命令(Command)和查询(Query)操作，确保架构清晰。

## 🏁 项目目标

**终极目标**: 通过1000手牌的终极测试，达到以下指标：
- ✅ 完成率 ≥99%
- ✅ 用户行动成功率 ≥99%
- ✅ 零筹码守恒违反
- ✅ 零不变量违反
- ✅ 性能 ≥5手/秒

**当前状态**: Phase 1-2 完成，GameFlowService + AI决策重构成功，准备Phase 3

---

**更新时间**: 2024-12-05  
**版本**: V3.1.0 (CQRS重构版) 