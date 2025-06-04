# 🃏 德州扑克v3重构 - 任务指南

## 🎯 项目目标

基于**DDD+状态机+CQRS**架构，重构v2代码为高度模块化的v3版本。核心目标：**实现streamlit端到端1000手牌测试**，确保架构清晰、扩展性强、测试覆盖完整。

## 🏆 验收标准

所有PLAN必须确保 `test_streamlit_ultimate_user_experience_v3.py` 终极测试通过，包括：
- 1000手牌完成率 ≥ 99%
- 用户行动成功率 ≥ 99% 
- 筹码守恒 100% 无违规
- 严重错误数量 = 0
- 测试性能 ≥ 5手/秒
- **反作弊系统**：所有测试层级都必须通过反作弊检查

---

## ✅ 测试套件全面Review与验证 【已完成】

已对v3项目当前的单元测试、性质测试和集成测试进行了全面的Review和验证，确保其符合v3开发指南、TDD原则和反作弊系统的严格要求。

**主要工作与成果**:
- 检查并移除了所有 `pytest.skip` 调用。
- 增强了反作弊系统 (`CoreUsageChecker`)，包括多层mock检测、对象生命周期及模块边界验证。
- 分析并修复了测试代码中发现的问题，特别是与核心数据结构使用和TDD原则不符的情况。
- 验证了主要测试文件（如 `test_game_invariants.py`, `test_application_services.py`, `test_chips_and_betting.py`, `test_deck_and_eval.py`, `test_state_machine.py` 等）均已通过，且符合规范。
- 确保了性质测试 (`test_chip_conservation.py`, `test_snapshot_performance.py`) 的有效性和反作弊检查。
- 修复了集成测试 (`test_events_integration.py`, `test_snapshot_integration.py`, `test_deck_eval_integration.py`) 中的辅助类引用问题。
- 最终运行所有v3测试，确认所有285个测试均通过。

此里程碑的完成为后续开发奠定了坚实的基础，确保了核心逻辑的可靠性。
每个PLAN都遵循：**测试先行 → 反作弊检查 → 实现代码 → 重构优化**

***PLAN 1-12 已经迁移到 v3_TASK_DONE***

---

## 📋 MILESTONE 3: Streamlit集成与终极测试 (PLAN 21-30)

### PLAN 21 Streamlit适配器设计

**PLAN简述**: 设计Streamlit UI适配器，连接v3应用服务

**解决的具体问题**:
- v2的UI直接调用控制器，耦合度高
- 需要适配v3的CQRS架构
- 保持UI代码简洁清晰

**执行步骤**:
1. 设计UI适配器：
   ```python
   # ui/streamlit/adapters/game_adapter.py
   class StreamlitGameAdapter:
       """Streamlit游戏适配器"""
       
       def __init__(self, command_service: GameCommandService, query_service: GameQueryService):
           self.command_service = command_service
           self.query_service = query_service
       
       def start_new_hand(self) -> bool:
           """开始新手牌"""
           result = self.command_service.start_new_hand(self.game_id)
           return result.success
       
       def execute_player_action(self, player_id: str, action_type: str, amount: int = 0) -> bool:
           """执行玩家行动"""
           action = PlayerAction(action_type, amount, player_id)
           result = self.command_service.execute_player_action(self.game_id, player_id, action)
           return result.success
       
       def get_game_state(self) -> GameStateSnapshot:
           """获取游戏状态"""
           return self.query_service.get_game_state(self.game_id)
   ```

**测试验收**:
- 适配器正确调用应用服务
- UI操作映射到正确的命令
- 错误处理友好

---

### PLAN 22 终极测试框架迁移

**PLAN简述**: 将v2的终极测试迁移到v3架构

**解决的具体问题**:
- v2的测试代码需要适配v3架构
- 需要增强反作弊检查
- 保持测试的完整性和严格性

**执行步骤**:
1. 迁移测试框架：
   ```python
   # tests/integration/test_streamlit_ultimate_user_experience_v3.py
   class StreamlitUltimateUserTesterV3:
       """v3版本的终极用户测试器"""
       
       def __init__(self, num_hands: int = 1000):
           self.num_hands = num_hands
           self.command_service = GameCommandService()
           self.query_service = GameQueryService()
           self.adapter = StreamlitGameAdapter(self.command_service, self.query_service)
   ```

2. 增强反作弊检查：
   ```python
   def test_anti_cheating_v3_core_module_usage():
       """v3反作弊检查：确保使用真实的v3核心模块"""
       tester = StreamlitUltimateUserTesterV3(num_hands=3)
       
       # 检查应用服务类型
       CoreUsageChecker.verify_real_objects(tester.command_service, "GameCommandService")
       CoreUsageChecker.verify_real_objects(tester.query_service, "GameQueryService")
       
       # 检查状态机类型
       game_state = tester.query_service.get_game_state("test_game")
       assert isinstance(game_state, GameStateSnapshot)
       
       # 检查筹码守恒
       # ...
   ```

**测试验收**:
- 1000手牌测试完成率 ≥ 99%
- 所有反作弊检查通过
- 性能不低于v2版本

---

### PLAN 23-30 完整测试实现

**简化描述**: 
- PLAN 23: UI组件测试
- PLAN 24: 集成测试完善
- PLAN 25: 性能测试
- PLAN 26: 压力测试
- PLAN 27: 边缘情况测试
- PLAN 28: 回归测试
- PLAN 29: 文档完善
- PLAN 30: 最终验收

---

## 🏁 验收里程碑

**最终验收标准**：
1. ✅ `test_streamlit_ultimate_user_experience_v3.py` 通过（1000手牌，完成率≥99%）
2. ✅ 所有反作弊检查通过
3. ✅ 筹码守恒100%无违规
4. ✅ 严重错误数量 = 0
5. ✅ 测试性能 ≥ 5手/秒
6. ✅ 代码覆盖率 ≥ 90%

**TDD工作流程**：
```
分析PLAN → 设计测试 → 反作弊检查 → 实现代码 → 重构优化 → PLAN完成
```

**反作弊覆盖范围**：
- ✅ Unit Tests: 确保使用真实核心对象
- ✅ Property Tests: 验证数学不变量
- ✅ Integration Tests: 检查端到端流程
- ✅ Ultimate Test: 验证完整用户体验

---

## 📚 相关文档

- **v3架构说明**: `v3_README.md`
- **终极测试**: `tests/integration/test_streamlit_ultimate_user_experience_v3.py`
- **反作弊系统**: `tests/anti_cheat/`
- **开发规范**: `v3_README.md#开发规范` 