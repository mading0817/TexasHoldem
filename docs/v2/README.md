# Texas Hold'em Poker Game v2 Documentation

## 概览

这是德州扑克游戏v2版本的技术文档。v2版本采用了重构的架构设计，提供更好的模块分离和可维护性。

## 已完成的模块

### 核心枚举 (v2/core/enums.py)
- **Suit**: 扑克牌花色枚举 (♥♦♣♠)
- **Rank**: 扑克牌点数枚举 (2-A，内部值2-14)
- **HandRank**: 牌型强度枚举 (高牌到皇家同花顺)
- **ActionType**: 玩家行动类型 (fold, check, call, bet, raise, all_in)
- **Phase**: 游戏阶段 (pre_flop, flop, turn, river, showdown)
- **SeatStatus**: 座位状态 (active, folded, all_in, out, sitting_out)
- **GameEventType**: 游戏事件类型
- **ValidationResult**: 行动验证结果

### 扑克牌对象 (v2/core/cards.py)
- **Card**: 不可变的扑克牌数据类
  - 支持比较、哈希、字符串表示
  - 格式：如"AH"表示红桃A，"KS"表示黑桃K
- **Deck**: 牌堆管理类
  - 52张牌的完整牌堆
  - 支持洗牌、发牌、重置
  - 可注入随机数生成器用于确定性测试

## 测试覆盖

- `tests/unit/test_v2_enums.py`: 20个测试用例，覆盖所有枚举类型
- `tests/unit/test_v2_cards.py`: 24个测试用例，覆盖Card和Deck功能

## 设计原则

1. **类型安全**: 使用枚举和类型注解
2. **不可变性**: 核心数据对象使用frozen dataclass
3. **可测试性**: 支持依赖注入，特别是随机数生成器
4. **Google Docstring**: 统一的文档字符串格式

## 开发状态

🚧 正在开发中 - 按照 TASK_GUIDE.txt 中的50条PLAN逐步实施

### 已完成
- ✅ PLAN #1-6: v2目录骨架与基础设施

### 进行中
- 🚧 PLAN #7-18: 核心逻辑层重塑

## 下一步计划

1. 实现牌型评估器 (evaluator.py)
2. 创建玩家状态管理 (player.py)
3. 实现行动验证器 (validator.py)
4. 构建边池管理器 (pot.py)
5. 设计游戏状态管理 (state.py) 