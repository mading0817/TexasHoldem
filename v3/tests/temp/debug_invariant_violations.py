"""
调试不变量违反问题的脚本
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def debug_invariant_violations():
    """调试不变量违反问题"""
    try:
        print("=== 调试不变量违反问题 ===")
        
        from v3.application.command_service import GameCommandService
        from v3.core.invariant import GameInvariants
        from v3.core.snapshot import SnapshotManager
        
        # 创建命令服务
        command_service = GameCommandService(enable_invariant_checks=False)  # 先禁用检查
        
        # 创建游戏
        result = command_service.create_new_game(game_id="debug_game")
        print(f"创建游戏结果: {result.success}, {result.message}")
        
        if not result.success:
            print("游戏创建失败，无法继续调试")
            return
        
        # 获取游戏会话
        session = command_service._get_session("debug_game")
        if session is None:
            print("无法获取游戏会话")
            return
        
        print(f"游戏状态: {session.context}")
        print(f"当前阶段: {session.state_machine.current_phase}")
        
        # 创建快照管理器和不变量检查器
        snapshot_manager = SnapshotManager()
        snapshot = snapshot_manager.create_snapshot(session.context)
        
        print(f"快照: {snapshot}")
        
        # 创建不变量检查器
        invariants = GameInvariants.create_for_game(snapshot)
        
        # 检查所有不变量
        print("\n=== 检查所有不变量 ===")
        results = invariants.check_all(snapshot)
        
        for invariant_type, result in results.items():
            print(f"\n{invariant_type.name}:")
            print(f"  有效: {result.is_valid}")
            print(f"  违反数量: {len(result.violations)}")
            
            for violation in result.violations:
                print(f"    - {violation.severity}: {violation.description}")
        
        # 尝试开始新手牌
        print("\n=== 尝试开始新手牌 ===")
        try:
            # 手动执行状态转换
            from v3.core.state_machine.types import GameEvent
            hand_event = GameEvent(
                event_type='HAND_START',
                data={'game_id': "debug_game"},
                source_phase=session.state_machine.current_phase
            )
            
            session.state_machine.transition(hand_event, session.context)
            print(f"状态转换成功，新阶段: {session.state_machine.current_phase}")
            
            # 重新创建快照并检查不变量
            new_snapshot = snapshot_manager.create_snapshot(session.context)
            print(f"新快照: {new_snapshot}")
            
            print("\n=== 检查转换后的不变量 ===")
            new_results = invariants.check_all(new_snapshot)
            
            for invariant_type, result in new_results.items():
                print(f"\n{invariant_type.name}:")
                print(f"  有效: {result.is_valid}")
                print(f"  违反数量: {len(result.violations)}")
                
                for violation in result.violations:
                    print(f"    - {violation.severity}: {violation.description}")
            
        except Exception as e:
            print(f"状态转换失败: {e}")
            import traceback
            traceback.print_exc()
    
    except Exception as e:
        print(f"调试脚本执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_invariant_violations() 