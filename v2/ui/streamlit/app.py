"""
Streamlit web interface for Texas Hold'em poker game.

This module provides a web-based user interface using Streamlit for playing
Texas Hold'em poker against AI opponents.
"""

import streamlit as st
import logging
import time
from typing import Optional

from v2.controller.poker_controller import PokerController
from v2.ai.simple_ai import SimpleAI
from v2.core.enums import ActionType, Phase
from v2.core.state import GameState
from v2.controller.dto import ActionInput


def initialize_session_state():
    """初始化Streamlit session state."""
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
        
    if 'game_started' not in st.session_state:
        st.session_state.game_started = False
        
    if 'events' not in st.session_state:
        st.session_state.events = []
        
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = False


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
    """渲染侧边栏，包含游戏控制和事件日志."""
    st.sidebar.title("🎮 游戏控制")
    
    # 开始新手牌按钮
    if st.sidebar.button("🆕 开始新手牌"):
        success = st.session_state.controller.start_new_hand()
        if success:
            st.session_state.game_started = True
            st.session_state.events = []
            if hasattr(st.session_state, 'show_raise_input'):
                st.session_state.show_raise_input = False
            st.rerun()
        else:
            st.sidebar.error("❌ 无法开始新手牌")
    
    # 调试模式切换
    st.session_state.debug_mode = st.sidebar.checkbox("🔧 调试模式", value=st.session_state.debug_mode)
    
    # 调试功能
    if st.session_state.debug_mode:
        st.sidebar.subheader("🔧 调试功能")
        
        # 10手牌自动测试
        if st.sidebar.button("🎲 自动玩10手牌"):
            with st.sidebar.spinner("正在自动游戏..."):
                results = run_auto_play_test(10)
                st.sidebar.success(f"✅ 完成10手牌测试")
                st.sidebar.json(results)
    
    # 事件日志
    st.sidebar.subheader("📋 事件日志")
    snapshot = st.session_state.controller.get_snapshot()
    if snapshot and snapshot.events:
        # 显示最近10个事件，使用滚动容器
        events_to_show = snapshot.events[-10:]
        for i, event in enumerate(reversed(events_to_show)):
            st.sidebar.text(f"{len(events_to_show)-i}: {event}")
    else:
        st.sidebar.text("暂无事件")


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


if __name__ == "__main__":
    main() 