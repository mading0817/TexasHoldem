# 🃏 德州扑克游戏项目

一个高质量的德州扑克游戏实现，采用模块化架构设计，支持CLI和Web界面。当前正在进行v3版本的重构工作。

## 📁 项目结构

```
TexasHoldem/
├── v3/                    # 项目v3版本（当前开发版本）
│   ├── core/             # 核心游戏逻辑
│   ├── application/      # 应用服务层
│   ├── ui/               # 用户界面（待实现）
│   ├── ai/               # AI策略
│   ├── tests/            # 测试用例
│   └── v3_TASK_GUIDE.md  # v3任务指南
├── v2/                    # 项目v2版本（已完成，作为参考）
│   ├── core/             # 核心游戏逻辑
│   ├── controller/       # 控制器层
│   ├── ui/               # 用户界面（CLI + Web）
│   ├── ai/               # AI策略
│   ├── tests/            # 测试用例
│   ├── README.md         # v2详细文档
│   ├── TASK_GUIDE.md     # 任务指南
│   └── TASK_DONE.md      # 完成记录
├── docs/                 # API文档 (待更新至v3)
├── scripts/              # 自动化脚本
│   ├── build-docs.py     # 文档生成 (待更新至v3)
│   └── cleanup.py        # 项目清理
├── .venv/                # 虚拟环境
├── requirements.txt      # 依赖包
└── TexasHoldemGameRule.md # 游戏规则
```

## 🚀 快速开始

### 环境准备
```bash
# 激活虚拟环境
.venv/Scripts/activate

# 安装依赖（如果需要）
pip install -r requirements.txt
```

### 启动游戏

目前v3版本还在开发中，暂无完整的启动方式。请参考v2的启动方式（见v2/README.md）。

#### Web界面（v2）
```bash
.venv/Scripts/streamlit run v2/ui/streamlit/app.py
```
访问 http://localhost:8501 开始游戏

#### 命令行界面（v2）
```bash
.venv/Scripts/python -m v2.ui.cli.cli_game
```

## 🎮 游戏特性

- ✅ **基于DDD+状态机+CQRS架构进行v3重构**
- ✅ **模块化架构，易于扩展**
- ✅ **高质量代码，遵循TDD，全面测试覆盖**
- ✅ **强大的反作弊和不变量检查系统**

*更多v3特性将在开发完成后更新。以下是v2已完成的特性：*

- ✅ **100%符合标准德州扑克规则**
- ✅ **智能AI对手，完全自动化**
- ✅ **现代化Web界面 + 经典CLI界面**
- ✅ **完整的事件记录和日志系统**

## 📊 项目状态

- **版本**: v3 (重构中)
- **状态**: 积极开发中 🏗️
- **v2状态**: 完全发布就绪 ✅
- **测试结果**: 请参考v3任务指南和测试报告
- **代码质量**: 生产级别 (v2), 建设中 (v3)
- **AI公平性**: 建设中 (v3), 已验证 (v2)

## 📚 文档

- **v3任务指南**: [v3/v3_TASK_GUIDE.md](v3/v3_TASK_GUIDE.md)
- **v2详细文档**: [v2/README.md](v2/README.md)
- **游戏规则**: [TexasHoldemGameRule.md](TexasHoldemGameRule.md)

## 🛠️ 开发工具

```bash
# 运行v3测试 (示例，具体请参考v3任务指南)
.venv/Scripts/python -m pytest v3/tests/unit/test_random_ai_refactored.py -v

# 生成文档 (待更新至v3)
.venv/Scripts/python scripts/build-docs.py

# 清理项目
.venv/Scripts/python scripts/cleanup.py
```

## 🎯 版本说明

- **v3**: 当前积极开发的版本，基于DDD+状态机+CQRS架构重构。
- **v2**: 已完成版本，作为参考和基准。每个版本完全独立，零耦合，可以安全删除任一版本而不影响其他版本。

---

**🏗️ v3版本正在建设中，敬请期待更完善的德州扑克体验！** 