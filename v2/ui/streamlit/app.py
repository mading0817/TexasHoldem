"""
Streamlit web interface for Texas Hold'em poker game.

This module provides a web-based user interface using Streamlit for playing
Texas Hold'em poker against AI opponents.
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
import logging
import time
import tempfile
from typing import Optional

from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.enums import ActionType, Phase
from v2.core.state import GameState
from v2.controller.dto import ActionInput


def setup_file_logging():
    """设置文件日志记录器."""
    if not hasattr(st.session_state, 'log_file_path'):
        # 创建临时日志文件
        temp_dir = tempfile.gettempdir()
        log_file_path = os.path.join(temp_dir, 'texas_holdem_debug.log')
        st.session_state.log_file_path = log_file_path
        
        # 配置文件日志处理器
        file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # 添加到根logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        
        # 同时添加到控制器logger
        if hasattr(st.session_state, 'controller') and hasattr(st.session_state.controller, '_logger'):
            st.session_state.controller._logger.addHandler(file_handler)


def read_log_file_tail(file_path: str, max_lines: int = 50) -> list:
    """读取日志文件的最后几行."""
    try:
        if not os.path.exists(file_path):
            return ["日志文件不存在"]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # 返回最后max_lines行，去除空行
        recent_lines = [line.strip() for line in lines[-max_lines:] if line.strip()]
        return recent_lines if recent_lines else ["暂无日志内容"]
        
    except Exception as e:
        return [f"读取日志文件失败: {str(e)}"]


def initialize_session_state():
    """初始化Streamlit session state，使用幂等方式避免重复创建."""
    # 使用setdefault确保键存在且仅在首次创建时初始化
    if 'controller' not in st.session_state:
        # 创建游戏控制器
        game_state = GameState()
        ai_strategy = SimpleAI()
        logger = logging.getLogger(__name__)
        
        st.session_state.controller = PokerController(
            game_state=game_state,
            ai_strategy=ai_strategy,
            logger=logger
        )
    
    # 使用setdefault确保其他键存在
    st.session_state.setdefault('game_started', False)
    st.session_state.setdefault('events', [])
    st.session_state.setdefault('debug_mode', False)
    st.session_state.setdefault('show_raise_input', False)
    st.session_state.setdefault('show_logs', False)
    
    # 设置文件日志记录
    setup_file_logging()


def render_header():
    """渲染页面头部."""
    st.title("🃏 德州扑克 Texas Hold'em")
    st.markdown("---")


def render_game_state(snapshot):
    """渲染游戏状态，使用 Streamlit columns 和 expander 优化布局."""
    if not snapshot:
        st.info("点击 '开始新手牌' 开始游戏")
        return
        
    # 使用 columns 布局优化显示
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        # 显示当前阶段
        phase_names = {
            Phase.PRE_FLOP: "翻牌前",
            Phase.FLOP: "翻牌",
            Phase.TURN: "转牌", 
            Phase.RIVER: "河牌",
            Phase.SHOWDOWN: "摊牌"
        }
        st.subheader(f"🎯 当前阶段: {phase_names.get(snapshot.phase, snapshot.phase.value)}")
    
    with col2:
        # 显示底池
        st.metric("💰 底池", f"${snapshot.pot}")
    
    with col3:
        # 显示当前下注
        st.metric("📊 当前下注", f"${snapshot.current_bet}")
    
    # 显示公共牌 - 使用更好的视觉元素
    if snapshot.community_cards:
        st.subheader("🃏 公共牌")
        cards_display = []
        for card in snapshot.community_cards:
            suit_symbol = {"HEARTS": "♥️", "DIAMONDS": "♦️", "CLUBS": "♣️", "SPADES": "♠️"}
            rank_display = card.rank.value
            suit_display = suit_symbol[card.suit.value]
            # 使用不同颜色显示红色和黑色花色
            if card.suit.value in ["HEARTS", "DIAMONDS"]:
                cards_display.append(f"<span style='color: red; font-size: 1.5em;'>{rank_display}{suit_display}</span>")
            else:
                cards_display.append(f"<span style='color: black; font-size: 1.5em;'>{rank_display}{suit_display}</span>")
        
        st.markdown(" ".join(cards_display), unsafe_allow_html=True)
    
    # 显示玩家信息 - 使用 expander 优化
    with st.expander("👥 玩家信息", expanded=True):
        for i, player in enumerate(snapshot.players):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                # 高亮当前玩家
                if i == snapshot.current_player:
                    st.markdown(f"**🎯 {player.name}** (当前)")
                else:
                    st.write(f"**{player.name}**")
            with col2:
                st.write(f"💰 筹码: ${player.chips}")
            with col3:
                st.write(f"📊 当前下注: ${player.current_bet}")
            with col4:
                status_emoji = {
                    "ACTIVE": "🟢",
                    "FOLDED": "🔴", 
                    "ALL_IN": "🟡",
                    "OUT": "⚫"
                }
                emoji = status_emoji.get(player.status.value, "❓")
                st.write(f"{emoji} {player.status.value}")
                
            # 显示人类玩家的手牌
            if i == 0 and player.hole_cards:  # 假设玩家0是人类
                cards_display = []
                for card in player.hole_cards:
                    suit_symbol = {"HEARTS": "♥️", "DIAMONDS": "♦️", "CLUBS": "♣️", "SPADES": "♠️"}
                    rank_display = card.rank.value
                    suit_display = suit_symbol[card.suit.value]
                    if card.suit.value in ["HEARTS", "DIAMONDS"]:
                        cards_display.append(f"<span style='color: red; font-size: 1.2em;'>{rank_display}{suit_display}</span>")
                    else:
                        cards_display.append(f"<span style='color: black; font-size: 1.2em;'>{rank_display}{suit_display}</span>")
                
                st.markdown(f"🎴 你的手牌: {' '.join(cards_display)}", unsafe_allow_html=True)


def process_ai_actions_continuously(controller):
    """连续处理AI行动直到轮到人类玩家或游戏结束."""
    max_iterations = 10  # 防止无限循环
    iterations = 0
    
    while iterations < max_iterations:
        current_player_id = controller.get_current_player_id()
        
        if current_player_id is None or current_player_id == 0:
            break  # 游戏结束或轮到人类玩家
            
        if controller.is_hand_over():
            break  # 手牌结束
            
        # 处理AI行动
        success = controller.process_ai_action()
        if not success:
            break
            
        iterations += 1
        time.sleep(0.1)  # 短暂延迟，避免过快处理
    
    return iterations > 0


def render_action_buttons(controller):
    """渲染行动按钮，优化AI连续行动处理."""
    current_player_id = controller.get_current_player_id()
    
    if current_player_id is None:
        st.info("⏳ 等待游戏状态更新...")
        return
        
    if current_player_id != 0:  # 不是人类玩家
        st.info("🤖 等待AI玩家行动...")
        
        # 自动处理AI行动
        if st.button("🚀 处理AI行动", key="process_ai"):
            with st.spinner("AI正在思考..."):
                ai_processed = process_ai_actions_continuously(controller)
                if ai_processed:
                    st.rerun()
        
        # 自动触发AI行动（可选）
        if st.checkbox("🔄 自动处理AI行动"):
            time.sleep(1)  # 给用户时间看到状态
            ai_processed = process_ai_actions_continuously(controller)
            if ai_processed:
                st.rerun()
        return
    
    # 人类玩家行动
    st.subheader("🎯 选择你的行动")
    
    # 获取当前游戏状态以确定可用行动
    snapshot = controller.get_snapshot()
    player = snapshot.players[0] if snapshot and snapshot.players else None
    
    if not player:
        st.error("无法获取玩家信息")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🚫 弃牌 (Fold)", key="fold"):
            action = ActionInput(
                player_id=0,
                action_type=ActionType.FOLD,
                amount=0
            )
            controller.execute_action(action)
            st.rerun()
    
    with col2:
        # 根据当前下注情况显示跟注或过牌
        if snapshot.current_bet > player.current_bet:
            call_amount = snapshot.current_bet - player.current_bet
            if st.button(f"✅ 跟注 ${call_amount}", key="call"):
                action = ActionInput(
                    player_id=0,
                    action_type=ActionType.CALL,
                    amount=0
                )
                controller.execute_action(action)
                st.rerun()
        else:
            if st.button("✅ 过牌 (Check)", key="check"):
                action = ActionInput(
                    player_id=0,
                    action_type=ActionType.CHECK,
                    amount=0
                )
                controller.execute_action(action)
                st.rerun()
    
    with col3:
        # 加注按钮
        min_raise = max(snapshot.current_bet * 2 - player.current_bet, 10)
        max_raise = player.chips
        
        if max_raise >= min_raise:
            if st.button("📈 加注 (Raise)", key="raise_btn"):
                st.session_state.show_raise_input = True
                st.rerun()
    
    with col4:
        if st.button("🎯 全押 (All-in)", key="all_in"):
            action = ActionInput(
                player_id=0,
                action_type=ActionType.ALL_IN,
                amount=0
            )
            controller.execute_action(action)
            st.rerun()
    
    # 加注金额输入
    if hasattr(st.session_state, 'show_raise_input') and st.session_state.show_raise_input:
        st.subheader("📈 加注金额")
        min_raise = max(snapshot.current_bet * 2 - player.current_bet, 10)
        max_raise = player.chips
        
        if max_raise >= min_raise:
            bet_amount = st.number_input(
                f"加注金额 (${min_raise} - ${max_raise})",
                min_value=min_raise,
                max_value=max_raise,
                value=min(min_raise, max_raise),
                step=10,
                key="raise_amount"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"✅ 确认加注 ${bet_amount}", key="confirm_raise"):
                    action = ActionInput(
                        player_id=0,
                        action_type=ActionType.RAISE,
                        amount=bet_amount
                    )
                    controller.execute_action(action)
                    st.session_state.show_raise_input = False
                    st.rerun()
            
            with col2:
                if st.button("❌ 取消", key="cancel_raise"):
                    st.session_state.show_raise_input = False
                    st.rerun()


def render_sidebar():
    """渲染侧边栏，包含调试功能和事件日志."""
    st.sidebar.title("🎮 游戏控制")
    
    # 调试模式开关
    debug_mode = st.sidebar.checkbox("🐛 调试模式", value=st.session_state.debug_mode)
    if debug_mode != st.session_state.debug_mode:
        st.session_state.debug_mode = debug_mode
        # 动态调整日志级别
        if hasattr(st.session_state, 'controller') and hasattr(st.session_state.controller, '_logger'):
            if debug_mode:
                st.session_state.controller._logger.setLevel(logging.DEBUG)
                logging.getLogger().setLevel(logging.DEBUG)
        else:
                st.session_state.controller._logger.setLevel(logging.INFO)
                logging.getLogger().setLevel(logging.INFO)
    
    # 日志级别选择
    if debug_mode:
        log_levels = ["ERROR", "WARNING", "INFO", "DEBUG"]
        selected_level = st.sidebar.selectbox(
            "📊 日志级别",
            log_levels, 
            index=log_levels.index("DEBUG") if debug_mode else log_levels.index("INFO")
        )
        
        # 应用日志级别
        numeric_level = getattr(logging, selected_level)
        if hasattr(st.session_state, 'controller') and hasattr(st.session_state.controller, '_logger'):
            st.session_state.controller._logger.setLevel(numeric_level)
        logging.getLogger().setLevel(numeric_level)
    
    # 调试功能区域
    if debug_mode:
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔧 调试工具")
        
        # 10手牌自动测试
        if st.sidebar.button("🎯 自动玩 10 手"):
            with st.spinner("正在进行10手牌测试..."):
                test_results = run_auto_play_test(10)
                st.sidebar.json(test_results)
            
        # 性能测试
        if st.sidebar.button("⚡ 性能测试"):
            with st.spinner("正在进行性能测试..."):
                perf_results = run_log_level_performance_test()
                st.sidebar.json(perf_results)
        
        # 导出调试日志
        if st.sidebar.button("📋 导出调试日志"):
            if hasattr(st.session_state, 'log_file_path'):
                try:
                    with open(st.session_state.log_file_path, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                    
                    # 创建下载按钮
                    st.sidebar.download_button(
                        label="💾 下载日志文件",
                        data=log_content,
                        file_name=f"texas_holdem_debug_{time.strftime('%Y%m%d_%H%M%S')}.log",
                        mime="text/plain"
                    )
                    st.sidebar.success("✅ 日志已准备下载")
                except Exception as e:
                    st.sidebar.error(f"❌ 导出日志失败: {str(e)}")
            else:
                st.sidebar.warning("⚠️ 日志文件不存在")
        
        # 导出游戏状态快照
        if st.sidebar.button("📸 导出游戏快照"):
            try:
                if hasattr(st.session_state, 'controller'):
                    snapshot_data = st.session_state.controller.export_snapshot()
                    import json
                    snapshot_json = json.dumps(snapshot_data, indent=2, ensure_ascii=False)
                    
                    st.sidebar.download_button(
                        label="💾 下载快照文件",
                        data=snapshot_json,
                        file_name=f"game_snapshot_{time.strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                    st.sidebar.success("✅ 快照已准备下载")
                else:
                    st.sidebar.warning("⚠️ 游戏控制器不存在")
            except Exception as e:
                st.sidebar.error(f"❌ 导出快照失败: {str(e)}")
                
    # 显示实时日志
    if debug_mode and hasattr(st.session_state, 'log_file_path'):
        st.sidebar.markdown("---")
        st.sidebar.subheader("📜 实时日志")
        
        # 显示日志开关
        show_logs = st.sidebar.checkbox("显示实时日志", value=st.session_state.get('show_logs', False))
        st.session_state.show_logs = show_logs
        
        if show_logs:
            log_lines = read_log_file_tail(st.session_state.log_file_path, max_lines=20)
            if log_lines:
                # 使用代码块显示日志，支持滚动
                log_text = "\n".join(log_lines[-10:])  # 只显示最后10行
                st.sidebar.code(log_text, language="text")
    
    # 事件日志
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 游戏事件")
    
    if st.session_state.events:
        # 显示最近的事件（倒序）
        recent_events = st.session_state.events[-10:]  # 最近10个事件
        for i, event in enumerate(reversed(recent_events)):
            event_text = f"{len(recent_events)-i}. {event}"
            st.sidebar.text(event_text)
    else:
        st.sidebar.text("暂无游戏事件")
    
    # 清除事件日志按钮
    if st.sidebar.button("🗑️ 清除事件日志"):
        st.session_state.events = []
        st.rerun()


def run_auto_play_test(num_hands: int) -> dict:
    """运行自动游戏测试，用于调试和验证."""
    controller = st.session_state.controller
    results = {
        "hands_played": 0,
        "total_chips_start": 0,
        "total_chips_end": 0,
        "chip_conservation": True,
        "errors": []
    }
    
    try:
        # 记录初始筹码
        initial_snapshot = controller.get_snapshot()
        if initial_snapshot:
            results["total_chips_start"] = sum(p.chips for p in initial_snapshot.players)
        
        for hand_num in range(num_hands):
            # 开始新手牌
            if not controller.start_new_hand():
                results["errors"].append(f"Hand {hand_num + 1}: Failed to start")
                break
            
            # 自动处理整手牌
            max_actions = 100  # 防止无限循环
            actions_taken = 0
            
            while not controller.is_hand_over() and actions_taken < max_actions:
                current_player_id = controller.get_current_player_id()
                if current_player_id is not None:
                    # 对于人类玩家，使用简单的AI策略
                    if current_player_id == 0:
                        # 简单策略：随机选择行动
                        import random
                        actions = [ActionType.FOLD, ActionType.CALL, ActionType.CHECK]
                        action_type = random.choice(actions)
                        action = ActionInput(
                            player_id=0,
                            action_type=action_type,
                            amount=0
                        )
                        controller.execute_action(action)
                    else:
                        controller.process_ai_action()
                    
                    actions_taken += 1
                else:
                    break
            
            # 结束手牌
            if controller.is_hand_over():
                controller.end_hand()
                results["hands_played"] += 1
            else:
                results["errors"].append(f"Hand {hand_num + 1}: Did not finish properly")
        
        # 检查筹码守恒
        final_snapshot = controller.get_snapshot()
        if final_snapshot:
            results["total_chips_end"] = sum(p.chips for p in final_snapshot.players)
            results["chip_conservation"] = (results["total_chips_start"] == results["total_chips_end"])
    
    except Exception as e:
        results["errors"].append(f"Exception: {str(e)}")
    
    return results


def run_log_level_performance_test() -> dict:
    """运行不同日志级别的性能对比测试."""
    import time
    
    results = {}
    log_levels = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    level_names = ["ERROR", "WARNING", "INFO", "DEBUG"]
    
    original_level = logging.getLogger().level
    
    try:
        for level, name in zip(log_levels, level_names):
            # 设置日志级别
            logging.getLogger().setLevel(level)
            if hasattr(st.session_state.controller, '_logger'):
                st.session_state.controller._logger.setLevel(level)
            
            # 运行性能测试
            start_time = time.time()
            test_results = run_auto_play_test(3)  # 使用较少手数进行快速测试
            end_time = time.time()
            
            results[name] = end_time - start_time
            
            # 短暂延迟避免过快切换
            time.sleep(0.1)
    
    finally:
        # 恢复原始日志级别
        logging.getLogger().setLevel(original_level)
        if hasattr(st.session_state.controller, '_logger'):
            st.session_state.controller._logger.setLevel(original_level)
    
    return results


def main():
    """主函数."""
    st.set_page_config(
        page_title="德州扑克",
        page_icon="🃏",
        layout="wide"
    )
    
    # 初始化session state
    initialize_session_state()
    
    # 渲染页面
    render_header()
    render_sidebar()
    
    # 获取游戏状态
    controller = st.session_state.controller
    snapshot = controller.get_snapshot() if st.session_state.game_started else None
    
    # 如果游戏未开始，显示开始按钮
    if not st.session_state.game_started:
        st.info("🎮 欢迎来到德州扑克！点击下方按钮开始游戏。")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🆕 开始新手牌", type="primary", use_container_width=True):
                success = controller.start_new_hand()
                if success:
                    st.session_state.game_started = True
                    st.session_state.events = []
                    if hasattr(st.session_state, 'show_raise_input'):
                        st.session_state.show_raise_input = False
                    st.rerun()
                else:
                    st.error("❌ 无法开始新手牌，请检查游戏状态")
        return
    
    # 渲染游戏状态
    render_game_state(snapshot)
    
    # 渲染行动按钮
    if st.session_state.game_started and not controller.is_hand_over():
        render_action_buttons(controller)
    elif st.session_state.game_started and controller.is_hand_over():
        st.success("🎉 手牌结束！")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 查看结果"):
                result = controller.end_hand()
                if result:
                    st.write(f"🏆 获胜者: {result.winner_ids}")
                    st.write(f"💰 底池金额: ${result.pot_amount}")
                    if result.winning_hand_description:
                        st.write(f"🃏 获胜牌型: {result.winning_hand_description}")
        
        with col2:
            if st.button("🔄 下一手牌"):
                success = controller.start_new_hand()
                if success:
                    st.session_state.events = []
                    if hasattr(st.session_state, 'show_raise_input'):
                        st.session_state.show_raise_input = False
                    st.rerun()
                else:
                    st.error("❌ 无法开始新手牌")


if __name__ == "__main__":
    main() 