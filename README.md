# 🃏 德州扑克游戏 (Texas Hold'em Poker)

一个功能完整的单人单机德州扑克游戏，支持人类玩家与AI对战。

## 🚀 快速开始

### 方法1：一键启动（推荐）
双击运行 `start_game.bat` 文件，自动启动Web界面。

### 方法2：命令行启动
```powershell
.venv\Scripts\streamlit.exe run v2\ui\streamlit\app.py
```

启动后在浏览器中访问：http://localhost:8501

## ✨ 主要特性

- **完整的德州扑克规则**：支持所有标准德州扑克玩法
- **智能AI对手**：多个AI玩家提供挑战
- **现代Web界面**：基于Streamlit的直观用户界面
- **命令行模式**：支持CLI模式游戏
- **调试功能**：内置调试模式和日志导出
- **筹码管理**：完整的筹码系统和边池计算

## 🎮 游戏功能

### 核心玩法
- 4人桌（1个人类玩家 + 3个AI）
- 标准德州扑克规则
- 完整的下注轮次（翻牌前、翻牌、转牌、河牌）
- 支持所有行动：弃牌、过牌、跟注、加注、全押

### 界面特性
- **响应式布局**：清晰的三列布局显示
- **实时更新**：游戏状态实时刷新
- **视觉元素**：Unicode扑克牌符号，红黑花色区分
- **智能提示**：动态显示可用行动和金额

### 调试工具
- **调试模式**：详细的游戏状态显示
- **自动测试**：一键运行10手牌测试
- **日志导出**：完整的游戏日志下载
- **状态快照**：游戏状态JSON导出

## 🏗️ 项目架构

本项目采用v2重构架构，具有清晰的分层设计：

```
v2/
├── core/           # 核心游戏逻辑
│   ├── cards.py    # 扑克牌和牌堆
│   ├── evaluator.py # 牌型评估器
│   ├── player.py   # 玩家状态管理
│   ├── pot.py      # 边池管理
│   └── state.py    # 游戏状态
├── controller/     # 游戏控制器
│   └── poker_controller.py
├── ai/            # AI策略
│   └── simple_ai.py
└── ui/            # 用户界面
    ├── streamlit/ # Web界面
    └── cli/       # 命令行界面
```

## 📖 详细文档

- **快速启动指南**：[QUICK_START.md](QUICK_START.md)
- **v2架构文档**：[v2/README.md](v2/README.md)
- **API文档**：[docs/v2/](docs/v2/)
- **游戏规则**：[TexasHoldemGameRule.md](TexasHoldemGameRule.md)

## 🧪 开发与测试

### 运行测试
```powershell
# 运行所有测试
.venv\Scripts\python -m pytest tests/ -v

# 运行特定模块测试
.venv\Scripts\python -m pytest tests/unit/test_v2_cards.py -v
```

### 生成文档
```powershell
.venv\Scripts\python scripts\build-docs.py
```

### 清理项目
```powershell
.venv\Scripts\python scripts\cleanup.py
```

## 🎯 版本信息

- **当前版本**：v2.0
- **架构**：重构版本，采用分层设计
- **测试覆盖**：327+个测试用例
- **文档状态**：完整的API文档和用户指南

## 🐛 问题反馈

如果遇到问题：

1. **开启调试模式**：在游戏界面勾选"🐛 调试模式"
2. **导出日志**：点击"📋 导出调试日志"
3. **导出快照**：点击"📸 导出游戏快照"
4. **查看文档**：参考详细文档和API说明

## 📄 许可证

本项目仅供学习和研究使用。

---

**🎉 立即开始游戏：双击 `start_game.bat` 或查看 [快速启动指南](QUICK_START.md)！** 