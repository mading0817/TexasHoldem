"""
调试游戏流程问题的测试脚本.

用于重现和分析以下问题：
1. 游戏进程卡在"等待AI玩家行动"
2. 玩家加注后筹码消失，AI没有跟注，但游戏没有正确结束
"""

import sys
import os
import logging

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.state import GameState
from v2.core.player import Player
from v2.core.enums import ActionType, Phase, SeatStatus, Action


def setup_logging():
    """设置详细的日志记录."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('v2/tests/temp/debug_game_flow.log', mode='w', encoding='utf-8')
        ]
    )


def create_test_game():
    """创建测试游戏."""
    game_state = GameState()
    ai_strategy = SimpleAI()
    controller = PokerController(game_state, ai_strategy)
    
    # 添加4个玩家
    for i in range(4):
        if i == 0:
            name = "Human"
        else:
            name = f"AI_{i}"
        
        player = Player(seat_id=i, name=name, chips=1000)
        controller._game_state.add_player(player)
    
    return controller


def print_game_state(controller, title="游戏状态"):
    """打印当前游戏状态."""
    print(f"\n=== {title} ===")
    snapshot = controller.get_snapshot()
    
    print(f"阶段: {snapshot.phase.value}")
    print(f"底池: {snapshot.pot}")
    print(f"当前下注: {snapshot.current_bet}")
    print(f"当前玩家: {snapshot.current_player}")
    print(f"手牌进行中: {controller._hand_in_progress}")
    print(f"行动数: {controller._game_state.actions_this_round}")
    print(f"最后加注者: {snapshot.last_raiser}")
    
    print("\n玩家状态:")
    for player in snapshot.players:
        print(f"  {player.name}: 筹码={player.chips}, 当前下注={player.current_bet}, 状态={player.status.value}")
    
    print(f"\n公共牌: {[str(card) for card in snapshot.community_cards]}")
    
    # 检查手牌是否结束
    is_hand_over = controller.is_hand_over()
    print(f"手牌是否结束: {is_hand_over}")
    
    # 检查行动是否完成
    actions_complete = controller._all_actions_complete()
    print(f"行动是否完成: {actions_complete}")


def test_scenario_1_ai_stuck():
    """测试场景1: AI玩家卡住的情况."""
    print("\n" + "="*50)
    print("测试场景1: AI玩家卡住")
    print("="*50)
    
    controller = create_test_game()
    
    # 开始新手牌
    success = controller.start_new_hand()
    print(f"开始新手牌: {success}")
    
    print_game_state(controller, "手牌开始后")
    
    # 模拟几轮AI行动
    max_actions = 20
    action_count = 0
    
    while action_count < max_actions:
        current_player_id = controller.get_current_player_id()
        
        if current_player_id is None:
            print(f"\n第{action_count+1}轮: 当前玩家为None")
            # 尝试检查阶段转换
            controller._check_phase_transition()
            current_player_id = controller.get_current_player_id()
            if current_player_id is None:
                print("阶段转换后仍无当前玩家，可能手牌结束")
                break
        
        if controller.is_hand_over():
            print(f"\n第{action_count+1}轮: 手牌结束")
            break
        
        print(f"\n第{action_count+1}轮: 当前玩家 {current_player_id}")
        
        if current_player_id == 0:
            # 人类玩家，模拟弃牌
            action = Action(player_id=0, action_type=ActionType.FOLD)
            controller.execute_action(action)
            print("人类玩家弃牌")
        else:
            # AI玩家
            success = controller.process_ai_action()
            print(f"AI玩家行动: {success}")
            if not success:
                print("AI行动失败，停止测试")
                break
        
        action_count += 1
        print_game_state(controller, f"第{action_count}轮行动后")
    
    print(f"\n测试完成，总共执行了{action_count}轮行动")


def test_scenario_2_chips_disappear():
    """测试场景2: 玩家加注后筹码消失的情况."""
    print("\n" + "="*50)
    print("测试场景2: 筹码消失问题")
    print("="*50)
    
    controller = create_test_game()
    
    # 开始新手牌
    success = controller.start_new_hand()
    print(f"开始新手牌: {success}")
    
    print_game_state(controller, "手牌开始后")
    
    # 等待轮到人类玩家
    while True:
        current_player_id = controller.get_current_player_id()
        
        if current_player_id is None:
            print("当前玩家为None，检查阶段转换")
            controller._check_phase_transition()
            continue
        
        if controller.is_hand_over():
            print("手牌结束")
            break
        
        if current_player_id == 0:
            # 人类玩家，模拟加注500
            print("\n人类玩家加注500")
            action = Action(player_id=0, action_type=ActionType.RAISE, amount=500)
            try:
                controller.execute_action(action)
                print("加注成功")
                print_game_state(controller, "人类玩家加注后")
                break
            except Exception as e:
                print(f"加注失败: {e}")
                break
        else:
            # AI玩家先行动
            success = controller.process_ai_action()
            print(f"AI玩家{current_player_id}行动: {success}")
    
    # 继续处理AI行动，看看是否会卡住或筹码消失
    max_ai_actions = 10
    ai_action_count = 0
    
    while ai_action_count < max_ai_actions:
        current_player_id = controller.get_current_player_id()
        
        if current_player_id is None:
            print("当前玩家为None，检查阶段转换")
            controller._check_phase_transition()
            current_player_id = controller.get_current_player_id()
            if current_player_id is None:
                print("阶段转换后仍无当前玩家")
                break
        
        if controller.is_hand_over():
            print("手牌结束")
            break
        
        if current_player_id == 0:
            print("轮到人类玩家，停止AI处理")
            break
        
        # AI玩家行动
        success = controller.process_ai_action()
        print(f"AI玩家{current_player_id}行动: {success}")
        ai_action_count += 1
        
        print_game_state(controller, f"AI行动{ai_action_count}后")
        
        if not success:
            print("AI行动失败")
            break
    
    # 检查最终状态
    print_game_state(controller, "最终状态")
    
    # 检查筹码总和是否正确
    snapshot = controller.get_snapshot()
    total_chips = sum(p.chips for p in snapshot.players)
    total_bets = sum(p.current_bet for p in snapshot.players)
    total_in_game = total_chips + total_bets + snapshot.pot
    
    print(f"\n筹码检查:")
    print(f"玩家总筹码: {total_chips}")
    print(f"玩家总下注: {total_bets}")
    print(f"底池: {snapshot.pot}")
    print(f"游戏中总筹码: {total_in_game}")
    print(f"预期总筹码: 4000")
    
    if total_in_game != 4000:
        print("⚠️ 筹码不平衡！")
    else:
        print("✅ 筹码平衡正常")


def test_scenario_3_detailed_flow():
    """测试场景3: 详细的游戏流程分析."""
    print("\n" + "="*50)
    print("测试场景3: 详细游戏流程分析")
    print("="*50)
    
    controller = create_test_game()
    
    # 开始新手牌
    success = controller.start_new_hand()
    print(f"开始新手牌: {success}")
    
    print_game_state(controller, "手牌开始后")
    
    # 逐步执行每个行动，详细分析
    step = 0
    while step < 50:  # 最多50步
        step += 1
        print(f"\n--- 步骤 {step} ---")
        
        current_player_id = controller.get_current_player_id()
        print(f"当前玩家ID: {current_player_id}")
        
        if current_player_id is None:
            print("当前玩家为None，检查游戏状态")
            
            # 检查手牌是否结束
            if controller.is_hand_over():
                print("手牌已结束")
                break
            
            # 检查是否需要阶段转换
            actions_complete = controller._all_actions_complete()
            print(f"行动是否完成: {actions_complete}")
            
            if actions_complete:
                print("尝试阶段转换")
                controller._check_phase_transition()
                new_current_player = controller.get_current_player_id()
                print(f"阶段转换后当前玩家: {new_current_player}")
                if new_current_player is None:
                    print("阶段转换后仍无当前玩家，可能需要结束手牌")
                    break
            else:
                print("行动未完成但无当前玩家，这是异常状态")
                break
        
        # 获取当前玩家信息
        snapshot = controller.get_snapshot()
        if current_player_id is not None and current_player_id < len(snapshot.players):
            current_player = snapshot.players[current_player_id]
            print(f"当前玩家: {current_player.name} (筹码: {current_player.chips}, 当前下注: {current_player.current_bet})")
        
        # 执行行动
        if current_player_id == 0:
            # 人类玩家，根据情况选择行动
            if snapshot.current_bet > current_player.current_bet:
                # 需要跟注或弃牌
                if step <= 3:  # 前几步跟注
                    action = Action(player_id=0, action_type=ActionType.CALL)
                    print("人类玩家选择跟注")
                else:  # 后面弃牌
                    action = Action(player_id=0, action_type=ActionType.FOLD)
                    print("人类玩家选择弃牌")
            else:
                # 可以过牌或下注
                if step == 5:  # 第5步加注
                    action = Action(player_id=0, action_type=ActionType.RAISE, amount=200)
                    print("人类玩家选择加注到200")
                else:
                    action = Action(player_id=0, action_type=ActionType.CHECK)
                    print("人类玩家选择过牌")
            
            try:
                controller.execute_action(action)
                print("人类玩家行动成功")
            except Exception as e:
                print(f"人类玩家行动失败: {e}")
                break
        else:
            # AI玩家
            success = controller.process_ai_action()
            print(f"AI玩家行动: {success}")
            if not success:
                print("AI行动失败")
                break
        
        print_game_state(controller, f"步骤{step}后")
    
    print(f"\n详细流程测试完成，总共执行了{step}步")


def main():
    """主函数."""
    setup_logging()
    
    print("开始游戏流程调试测试")
    
    # 运行测试场景
    test_scenario_1_ai_stuck()
    test_scenario_2_chips_disappear()
    test_scenario_3_detailed_flow()
    
    print("\n所有测试完成")


if __name__ == "__main__":
    main() 