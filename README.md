# 🃏 德州扑克游戏项目

一个高质量的德州扑克游戏实现，采用模块化架构设计，支持CLI和Web界面。

## 📁 项目结构

```
TexasHoldem/
├── v2/                    # 项目v2版本（当前版本）
│   ├── core/             # 核心游戏逻辑
│   ├── controller/       # 控制器层
│   ├── ui/               # 用户界面（CLI + Web）
│   ├── ai/               # AI策略
│   ├── tests/            # 测试用例
│   ├── README.md         # v2详细文档
│   ├── TASK_GUIDE.md     # 任务指南
│   └── TASK_DONE.md      # 完成记录
├── docs/                 # API文档
├── scripts/              # 自动化脚本
│   ├── build-docs.py     # 文档生成
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

#### Web界面（推荐）
```bash
.venv/Scripts/streamlit run v2/ui/streamlit/app.py
```
访问 http://localhost:8501 开始游戏

#### 命令行界面
```bash
.venv/Scripts/python -m v2.ui.cli.cli_game
```

## 🎮 游戏特性

- ✅ **100%符合标准德州扑克规则**
- ✅ **智能AI对手，完全自动化**
- ✅ **现代化Web界面 + 经典CLI界面**
- ✅ **完整的事件记录和日志系统**
- ✅ **高质量代码，全面测试覆盖**
- ✅ **模块化架构，易于扩展**

## 📊 项目状态

- **版本**: v2
- **状态**: 完全发布就绪 ✅
- **完成任务**: 77/77 (100%)
- **测试结果**: 100/100分（完美）
- **代码质量**: 生产级别

## 📚 文档

- **详细文档**: [v2/README.md](v2/README.md)
- **API文档**: [docs/](docs/)
- **游戏规则**: [TexasHoldemGameRule.md](TexasHoldemGameRule.md)
- **任务指南**: [v2/TASK_GUIDE.md](v2/TASK_GUIDE.md)

## 🛠️ 开发工具

```bash
# 运行测试
.venv/Scripts/python -m pytest v2/tests/ -v

# 生成文档
.venv/Scripts/python scripts/build-docs.py

# 清理项目
.venv/Scripts/python scripts/cleanup.py
```

## 🎯 版本说明

- **v2**: 当前版本，完全重构，生产就绪
- **v1**: 历史版本（已移除，保持版本独立）

每个版本完全独立，零耦合，可以安全删除任一版本而不影响其他版本。

---

**🚀 开始您的德州扑克之旅！** 