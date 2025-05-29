#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试作弊行为修复脚本
系统性修复测试代码中直接修改游戏状态的作弊行为
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class TestCheatFixer:
    """测试作弊行为修复器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.fixes_applied = 0
        self.files_modified = 0
        
        # 作弊模式和对应的修复方案
        self.cheat_patterns = {
            # 直接修改游戏阶段
            r'(\s*)(\w+)\.phase\s*=\s*GamePhase\.(\w+)': (
                r'\1# ANTI-CHEAT-FIX: 使用GameController.advance_phase()而不是直接修改阶段\n'
                r'\1# \2.phase = GamePhase.\3  # 原作弊代码'
            ),
            
            # 直接修改当前玩家
            r'(\s*)(\w+)\.current_player\s*=\s*(\d+)': (
                r'\1# ANTI-CHEAT-FIX: 使用GameController提供的方法而不是直接修改当前玩家\n'
                r'\1# \2.current_player = \3  # 原作弊代码'
            ),
            
            # 直接修改当前下注
            r'(\s*)(\w+)\.current_bet\s*=\s*(\d+)': (
                r'\1# ANTI-CHEAT-FIX: 使用Player.bet()或GameController.process_action()而不是直接修改下注\n'
                r'\1# \2.current_bet = \3  # 原作弊代码'
            ),
            
            # 直接修改底池
            r'(\s*)(\w+)\.pot\s*=\s*(\d+)': (
                r'\1# ANTI-CHEAT-FIX: 使用PotManager或GameController提供的方法而不是直接修改底池\n'
                r'\1# \2.pot = \3  # 原作弊代码'
            ),
            
            # 直接设置公共牌 - 列表形式
            r'(\s*)(\w+)\.community_cards\s*=\s*\[([^\]]*)\]': (
                r'\1# ANTI-CHEAT-FIX: 使用GameController的发牌方法而不是直接设置公共牌\n'
                r'\1# \2.community_cards = [\3]  # 原作弊代码'
            ),
            
            # 直接设置公共牌 - 变量赋值
            r'(\s*)(\w+)\.community_cards\s*=\s*([^#\n]+)': (
                r'\1# ANTI-CHEAT-FIX: 使用GameController的发牌方法而不是直接设置公共牌\n'
                r'\1# \2.community_cards = \3  # 原作弊代码'
            ),
            
            # 直接修改玩家筹码 (非初始化情况)
            r'(\s*)(\w+)\.chips\s*=\s*(\d+)(?![^#]*#[^#]*初始|[^#]*#[^#]*合法|[^#]*#[^#]*ANTI-CHEAT)': (
                r'\1# ANTI-CHEAT-FIX: 使用Player.add_chips()或Player.bet()而不是直接修改筹码\n'
                r'\1# \2.chips = \3  # 原作弊代码'
            ),
        }
    
    def fix_file(self, file_path: Path) -> bool:
        """修复单个文件中的作弊行为"""
        if not file_path.exists() or not file_path.suffix == '.py':
            return False
            
        try:
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            # 应用所有修复模式
            for pattern, replacement in self.cheat_patterns.items():
                matches = re.finditer(pattern, content, re.MULTILINE)
                if matches:
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
            # 如果内容有变化，写回文件
            if content != original_content:
                file_path.write_text(content, encoding='utf-8')
                fixes_count = len(re.findall(r'# ANTI-CHEAT-FIX:', content)) - len(re.findall(r'# ANTI-CHEAT-FIX:', original_content))
                print(f"修复 {file_path.relative_to(self.project_root)}: {fixes_count} 处作弊行为")
                self.fixes_applied += fixes_count
                return True
            
        except Exception as e:
            print(f"修复文件 {file_path} 时出错: {e}")
            
        return False
    
    def fix_all_test_files(self):
        """修复所有测试文件中的作弊行为"""
        print("开始系统性修复测试代码作弊行为...")
        print("=" * 60)
        
        test_dirs = [
            self.project_root / "tests" / "unit",
            self.project_root / "tests" / "integration", 
            self.project_root / "tests" / "e2e",
            self.project_root / "tests" / "performance",
        ]
        
        for test_dir in test_dirs:
            if test_dir.exists():
                print(f"\n处理目录: {test_dir.relative_to(self.project_root)}")
                
                for file_path in test_dir.glob("test_*.py"):
                    if self.fix_file(file_path):
                        self.files_modified += 1
        
        print(f"\n修复完成:")
        print(f"- 修改文件数: {self.files_modified}")
        print(f"- 修复作弊行为数: {self.fixes_applied}")
        
        if self.fixes_applied > 0:
            print("\n⚠️  重要提示:")
            print("- 被注释的原作弊代码需要手动重构为合法API调用")
            print("- 测试逻辑可能需要调整以使用GameController而不是直接状态访问")
            print("- 建议重新运行测试以验证修复效果")
    
    def create_fix_guidelines(self):
        """创建修复指导文档"""
        guidelines = """
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
"""
        
        guidelines_file = self.project_root / "tests" / "ANTI_CHEAT_FIX_GUIDELINES.md"
        guidelines_file.write_text(guidelines, encoding='utf-8')
        print(f"创建修复指导文档: {guidelines_file.relative_to(self.project_root)}")


def main():
    """主函数"""
    fixer = TestCheatFixer()
    fixer.fix_all_test_files()
    fixer.create_fix_guidelines()
    
    print("\n" + "=" * 60)
    print("测试作弊行为修复完成！")
    print("请查看被注释的代码，手动重构为合法的API调用。")


if __name__ == "__main__":
    main() 