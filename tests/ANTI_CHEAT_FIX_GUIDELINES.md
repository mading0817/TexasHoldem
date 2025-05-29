
# 测试作弊行为修复指导

## 常见作弊模式和修复方案

### 1. 直接修改游戏阶段
**作弊代码:**
```python
state.phase = GamePhase.FLOP
```

**正确做法:**
```python
game_controller.advance_phase()  # 让GameController处理阶段转换
```

### 2. 直接修改当前玩家
**作弊代码:**
```python
state.current_player = 1
```

**正确做法:**
```python
# 通过正常的游戏流程让玩家轮转，或者重新创建游戏状态
action = ActionHelper.create_player_action(current_player, ActionType.FOLD)
game_controller.process_action(action)  # 让下一个玩家成为当前玩家
```

### 3. 直接修改下注金额
**作弊代码:**
```python
state.current_bet = 50
```

**正确做法:**
```python
# 通过玩家下注行为修改
action = ActionHelper.create_player_action(player, ActionType.BET, 50)
game_controller.process_action(action)
```

### 4. 直接修改底池
**作弊代码:**
```python
state.pot = 100
```

**正确做法:**
```python
# 通过模拟下注行为来增加底池
# 或在测试场景创建时设置合理的初始状态
```

### 5. 直接设置公共牌
**作弊代码:**
```python
state.community_cards = [Card(...), Card(...)]
```

**正确做法:**
```python
# 让游戏自然进展到相应阶段，由GameController发牌
game_controller.advance_phase()  # 从pre-flop到flop会发3张公共牌
```

## 修复原则

1. **使用合法API**: 所有状态变更必须通过GameController、Player等提供的公共方法
2. **模拟真实流程**: 通过模拟真实的游戏行为来达到测试目的
3. **场景创建**: 在测试初始化时创建合适的测试场景，而不是在测试过程中作弊
4. **隔离测试**: 每个测试应该独立，使用fresh的游戏状态

## 推荐的测试模式

```python
class TestExample:
    def setUp(self):
        # 使用BaseTester创建合法的游戏状态
        scenario = TestScenario(
            name="测试场景",
            players_count=4,
            starting_chips=[100, 200, 150, 300],  # 合法的初始化
            dealer_position=0,
            expected_behavior={},
            description="测试描述"
        )
        self.state = self.base_tester.create_scenario_game(scenario)
        self.game_controller = GameController(self.state)
    
    def test_something(self):
        # 通过合法API测试
        action = ActionHelper.create_player_action(player, ActionType.BET, 20)
        result = self.game_controller.process_action(action)
        # 验证结果...
```
