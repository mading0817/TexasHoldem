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
from v2.core.enums import ActionType, Phase, Action
from v2.core.state import GameState
from v2.controller.dto import ActionInput
from v2.core.events import EventBus


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
        
        # 检查是否已经添加了handler，避免重复添加
        root_logger = logging.getLogger()
        
        # 移除现有的FileHandler以避免重复
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                root_logger.removeHandler(handler)
        
        # 添加新的handler
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.DEBUG)
        
        # 标记已设置
        st.session_state.log_handler_setup = True


def read_log_file_tail(file_path: str, max_lines: int = 50) -> list:
    """读取日志文件的最后几行."""
    try:
        if not os.path.exists(file_path):
            return ["日志文件不存在"]
        
        # 尝试多种编码方式读取文件
        encodings = ['utf-8', 'gbk', 'cp1252', 'latin1']
        lines = []
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                    lines = f.readlines()
                break
            except UnicodeDecodeError:
                continue
        
        if not lines:
            # 如果所有编码都失败，使用二进制模式读取并尝试解码
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                    # 尝试解码为UTF-8，失败时替换无效字符
                    text = content.decode('utf-8', errors='replace')
                    lines = text.splitlines(keepends=True)
            except Exception:
                return ["日志文件读取失败：编码问题"]
            
        # 返回最后max_lines行，去除空行
        recent_lines = [line.strip() for line in lines[-max_lines:] if line.strip()]
        return recent_lines if recent_lines else ["暂无日志内容"]
        
    except Exception as e:
        return [f"读取日志文件失败: {str(e)}"]


def initialize_session_state():
    """初始化session state."""
    if 'controller' not in st.session_state:
        # 创建游戏状态和控制器
        game_state = GameState()
        ai_strategy = SimpleAI()
        logger = setup_file_logging()
        event_bus = EventBus()

        controller = PokerController(game_state, ai_strategy, logger, event_bus)

        # 设置玩家
        _setup_players(controller)

        st.session_state.controller = controller
    
    # 设置默认值，只有当键不存在时才设置
    if 'game_started' not in st.session_state:
        st.session_state.game_started = False
    if 'events' not in st.session_state:
        st.session_state.events = []
    if 'log_file_path' not in st.session_state:
        st.session_state.log_file_path = None
    # 添加摊牌处理标记，防止重复处理
    if 'showdown_processed' not in st.session_state:
        st.session_state.showdown_processed = False
    if 'hand_result_displayed' not in st.session_state:
        st.session_state.hand_result_displayed = False

    # 添加调试模式相关的session state变量
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = False
    if 'show_logs' not in st.session_state:
        st.session_state.show_logs = False
    if 'show_raise_input' not in st.session_state:
        st.session_state.show_raise_input = False
    if 'show_bet_input' not in st.session_state:
        st.session_state.show_bet_input = False


def _setup_players(controller: PokerController, num_players: int = 4, initial_chips: int = 1000) -> None:
    """设置玩家.
    
    Args:
        controller: 游戏控制器
        num_players: 玩家数量
        initial_chips: 初始筹码
    """
    from v2.core.player import Player
    
    # 检查是否已经有玩家
    snapshot = controller.get_snapshot()
    if len(snapshot.players) >= num_players:
        return  # 已经初始化过了
    
    # 添加玩家到游戏状态
    for i in range(num_players):
        if i == 0:
            name = "You"  # 人类玩家
        else:
            name = f"AI_{i}"
        
        # 通过控制器的游戏状态添加玩家
        player = Player(
            seat_id=i,
            name=name,
            chips=initial_chips
        )
        controller._game_state.add_player(player)


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
        # 计算实时底池：当前底池 + 所有玩家的当前下注
        current_round_bets = sum(player.current_bet for player in snapshot.players)
        total_pot = snapshot.pot + current_round_bets
        
        # 显示实时底池和详细信息
        st.metric("💰 底池", f"${total_pot}")
        if current_round_bets > 0:
            st.caption(f"已收集: ${snapshot.pot} + 当前轮: ${current_round_bets}")
        else:
            st.caption(f"已收集: ${snapshot.pot}")
    
    with col3:
        # 显示当前下注
        st.metric("📊 当前下注", f"${snapshot.current_bet}")
    
    # 显示公共牌 - 使用更好的视觉元素
    if snapshot.community_cards:
        st.subheader("🃏 公共牌")
        cards_display = []
        for card in snapshot.community_cards:
            # 修复牌面显示 - 使用正确的rank名称映射
            rank_display_map = {
                "TWO": "2", "THREE": "3", "FOUR": "4", "FIVE": "5",
                "SIX": "6", "SEVEN": "7", "EIGHT": "8", "NINE": "9",
                "TEN": "10", "JACK": "J", "QUEEN": "Q", 
                "KING": "K", "ACE": "A"
            }
            suit_symbol = {"♥": "♥️", "♦": "♦️", "♣": "♣️", "♠": "♠️"}
            rank_display = rank_display_map.get(card.rank.name, card.rank.name)
            suit_display = suit_symbol[card.suit.value]
            # 使用不同颜色显示红色和黑色花色
            if card.suit.value in ["♥", "♦"]:
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
                    st.markdown(f"**🎯 {player.name}** (当前行动)")
                elif i == snapshot.dealer_position:
                    st.markdown(f"**🎲 {player.name}** (庄家)")
                else:
                    st.write(f"**{player.name}**")
            with col2:
                st.write(f"💰 筹码: ${player.chips}")
            with col3:
                st.write(f"📊 当前下注: ${player.current_bet}")
            with col4:
                # 优化状态显示，使其更清晰
                status_display = {
                    "ACTIVE": "🟢 活跃",
                    "FOLDED": "🔴 已弃牌", 
                    "ALL_IN": "🟡 全押",
                    "OUT": "⚫ 出局",
                    "WAITING": "⏳ 等待"
                }
                status_text = status_display.get(player.status.value, f"❓ {player.status.value}")
                st.write(status_text)
                
            # 显示盲注信息
            if hasattr(player, 'is_small_blind') and player.is_small_blind:
                st.caption("🔸 小盲")
            elif hasattr(player, 'is_big_blind') and player.is_big_blind:
                st.caption("🔹 大盲")
                
            # 显示人类玩家的手牌
            if i == 0 and player.hole_cards:  # 假设玩家0是人类
                cards_display = []
                for card in player.hole_cards:
                    # 修复牌面显示 - 使用正确的rank名称映射
                    rank_display_map = {
                        "TWO": "2", "THREE": "3", "FOUR": "4", "FIVE": "5",
                        "SIX": "6", "SEVEN": "7", "EIGHT": "8", "NINE": "9",
                        "TEN": "10", "JACK": "J", "QUEEN": "Q", 
                        "KING": "K", "ACE": "A"
                    }
                    suit_symbol = {"♥": "♥️", "♦": "♦️", "♣": "♣️", "♠": "♠️"}
                    rank_display = rank_display_map.get(card.rank.name, card.rank.name)
                    suit_display = suit_symbol[card.suit.value]
                    if card.suit.value in ["♥", "♦"]:
                        cards_display.append(f"<span style='color: red; font-size: 1.2em;'>{rank_display}{suit_display}</span>")
                    else:
                        cards_display.append(f"<span style='color: black; font-size: 1.2em;'>{rank_display}{suit_display}</span>")
                
                st.markdown(f"🎴 你的手牌: {' '.join(cards_display)}", unsafe_allow_html=True)


def process_ai_actions_continuously(controller):
    """持续处理AI行动直到轮到人类玩家或手牌结束."""
    max_ai_actions = 20  # 防止无限循环
    ai_actions_count = 0
    
    # 记录处理前的状态
    initial_snapshot = controller.get_snapshot()
    initial_phase = initial_snapshot.phase
    initial_events_count = len(initial_snapshot.events)
    
    # 增强日志记录
    if 'events' not in st.session_state:
        st.session_state.events = []
    
    # 记录AI处理开始
    debug_msg = f"[DEBUG] 开始AI连续处理 - 阶段:{initial_phase.value}, 当前玩家:{controller.get_current_player_id()}, 事件数:{initial_events_count}"
    st.session_state.events.append(debug_msg)
    
    while ai_actions_count < max_ai_actions:
        if controller.is_hand_over():
            debug_msg = f"[DEBUG] 手牌结束，停止AI处理 (处理了{ai_actions_count}次AI行动)"
            st.session_state.events.append(debug_msg)
            break
            
        current_player_id = controller.get_current_player_id()
        if current_player_id is None:
            # 没有当前玩家，可能需要阶段转换
            debug_msg = f"[DEBUG] 当前玩家为None，尝试阶段转换"
            st.session_state.events.append(debug_msg)
            
            # 强制检查阶段转换
            try:
                controller._check_phase_transition()
                # 检查阶段转换后是否有新的当前玩家
                current_player_id = controller.get_current_player_id()
                new_snapshot = controller.get_snapshot()
                
                if new_snapshot.phase != initial_phase:
                    debug_msg = f"[DEBUG] 阶段转换成功: {initial_phase.value} -> {new_snapshot.phase.value}"
                    st.session_state.events.append(debug_msg)
                    initial_phase = new_snapshot.phase
                
                if current_player_id is None:
                    debug_msg = f"[DEBUG] 阶段转换后仍无当前玩家，可能需要等待或手牌结束"
                    st.session_state.events.append(debug_msg)
                    break
                else:
                    debug_msg = f"[DEBUG] 阶段转换后当前玩家: {current_player_id}"
                    st.session_state.events.append(debug_msg)
            except Exception as e:
                error_msg = f"[ERROR] 阶段转换失败: {e}"
                st.session_state.events.append(error_msg)
                st.error(error_msg)
                break
            
        # 如果轮到人类玩家（玩家0），停止AI处理
        if current_player_id == 0:
            debug_msg = f"[DEBUG] 轮到人类玩家，停止AI处理 (处理了{ai_actions_count}次AI行动)"
            st.session_state.events.append(debug_msg)
            break
            
        # 记录行动前的状态
        snapshot_before = controller.get_snapshot()
        phase_before = snapshot_before.phase
        events_before_count = len(snapshot_before.events)
        
        # 获取当前玩家信息
        current_player = None
        for p in snapshot_before.players:
            if p.seat_id == current_player_id:
                current_player = p
                break
        
        player_name = current_player.name if current_player else f"Player_{current_player_id}"
        debug_msg = f"[DEBUG] 准备处理 {player_name} 的行动 (筹码:{current_player.chips if current_player else 'N/A'}, 当前下注:{current_player.current_bet if current_player else 'N/A'})"
        st.session_state.events.append(debug_msg)
        
        # 处理AI行动
        success = controller.process_ai_action()
        
        if success:
            ai_actions_count += 1
            
            # 记录行动后的状态
            snapshot_after = controller.get_snapshot()
            phase_after = snapshot_after.phase
            events_after_count = len(snapshot_after.events)
            
            # 初始化UI事件列表
            if 'events' not in st.session_state:
                st.session_state.events = []
            
            # 记录新增的游戏事件
            if events_after_count > events_before_count:
                # 获取新增的事件
                new_events = snapshot_after.events[events_before_count:]
                for event in new_events:
                    # 直接添加事件，不再修改格式（因为controller已经添加了玩家名称和阶段信息）
                    st.session_state.events.append(event)
            
            # 记录AI行动成功
            debug_msg = f"[DEBUG] {player_name} 行动成功 (第{ai_actions_count}次AI行动)"
            st.session_state.events.append(debug_msg)
            
            # 检查阶段是否发生变化
            if phase_after != phase_before:
                # 阶段转换事件已经在controller中记录，这里不需要重复添加
                debug_msg = f"[DEBUG] 阶段转换: {phase_before.value} -> {phase_after.value}"
                st.session_state.events.append(debug_msg)
                
                # 阶段转换后，重新检查当前玩家
                # 如果阶段转换后轮到人类玩家，停止AI处理
                new_current_player_id = controller.get_current_player_id()
                if new_current_player_id == 0:
                    debug_msg = f"[DEBUG] 阶段转换后轮到人类玩家，停止AI处理"
                    st.session_state.events.append(debug_msg)
                    break
        else:
            # AI行动失败，停止处理
            error_msg = f"[ERROR] {player_name} AI行动失败，停止处理"
            st.session_state.events.append(error_msg)
            break
            
        # 短暂延迟，让用户看到AI行动
        time.sleep(0.1)
    
    # 处理完成后，检查是否有遗漏的事件
    final_snapshot = controller.get_snapshot()
    final_events_count = len(final_snapshot.events)
    
    # 记录处理完成
    debug_msg = f"[DEBUG] AI处理完成 - 总共处理{ai_actions_count}次行动, 当前玩家:{controller.get_current_player_id()}, 阶段:{final_snapshot.phase.value}"
    st.session_state.events.append(debug_msg)
    
    # 如果有新事件但没有被处理，添加它们
    if final_events_count > initial_events_count + ai_actions_count:
        missing_events = final_snapshot.events[initial_events_count + ai_actions_count:]
        for event in missing_events:
            st.session_state.events.append(event)
    
    return ai_actions_count > 0


def render_action_buttons(controller):
    """渲染行动按钮，优化AI连续行动处理."""
    current_player_id = controller.get_current_player_id()
    
    if current_player_id is None:
        st.info("⏳ 等待游戏状态更新...")
        return
        
    if current_player_id != 0:  # 不是人类玩家
        st.info("🤖 AI玩家正在思考...")
        
        # 自动处理AI行动 - 移除混乱的按钮，直接自动处理
        with st.spinner("AI正在行动..."):
            time.sleep(0.5)  # 短暂延迟让用户看到AI在思考
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
            action = Action(
                action_type=ActionType.FOLD,
                amount=0,
                player_id=0
            )
            controller.execute_action(action)
            # 记录用户行动事件
            st.session_state.events.append(f"你选择了弃牌")
            st.rerun()
    
    with col2:
        # 根据当前下注情况显示跟注或过牌
        if snapshot.current_bet > player.current_bet:
            call_amount = snapshot.current_bet - player.current_bet
            if st.button(f"✅ 跟注 ${call_amount}", key="call"):
                action = Action(
                    action_type=ActionType.CALL,
                    amount=0,
                    player_id=0
                )
                controller.execute_action(action)
                # 记录用户行动事件
                st.session_state.events.append(f"你跟注了 ${call_amount}")
                st.rerun()
        else:
            if st.button("✅ 过牌 (Check)", key="check"):
                action = Action(
                    action_type=ActionType.CHECK,
                    amount=0,
                    player_id=0
                )
                controller.execute_action(action)
                # 记录用户行动事件
                st.session_state.events.append(f"你选择了过牌")
                st.rerun()
    
    with col3:
        # 加注/下注按钮 - 修复BET vs RAISE逻辑和最小值计算
        if snapshot.current_bet == 0:
            # 无人下注时显示"下注"按钮
            min_bet = snapshot.big_blind  # 最小下注为大盲注
            max_bet = player.chips + player.current_bet  # 玩家可以下注的最大总额
            
            if max_bet >= min_bet:
                if st.button("💰 下注 (Bet)", key="bet_btn"):
                    st.session_state.show_bet_input = True
                    st.rerun()
        else:
            # 有人下注时显示"加注"按钮
            # 德州扑克规则：最小加注 = 当前下注 + 上次加注增量
            last_raise_increment = snapshot.last_raise_amount if snapshot.last_raise_amount > 0 else snapshot.big_blind
            min_raise = snapshot.current_bet + last_raise_increment
            max_raise = player.chips + player.current_bet  # 玩家可以下注的最大总额
            
            if max_raise >= min_raise:
                if st.button("📈 加注 (Raise)", key="raise_btn"):
                    st.session_state.show_raise_input = True
                    st.rerun()
    
    with col4:
        if st.button("🎯 全押 (All-in)", key="all_in"):
            action = Action(
                action_type=ActionType.ALL_IN,
                amount=0,
                player_id=0
            )
            controller.execute_action(action)
            # 记录用户行动事件
            st.session_state.events.append(f"你选择了全押 ${player.chips}")
            st.rerun()
    
    # 下注金额输入（无人下注时）
    if hasattr(st.session_state, 'show_bet_input') and st.session_state.show_bet_input:
        st.subheader("💰 下注金额")
        
        # 计算正确的最小和最大下注金额
        min_bet = snapshot.big_blind
        max_bet = player.chips + player.current_bet  # 玩家的总可用筹码
        
        if max_bet >= min_bet:
            # 显示当前下注信息
            st.info(f"当前下注: ${snapshot.current_bet} | 你已下注: ${player.current_bet}")
            
            bet_amount = st.number_input(
                f"下注金额 (${min_bet} - ${max_bet})",
                min_value=min_bet,
                max_value=max_bet,
                value=min_bet,
                step=snapshot.big_blind,
                key="bet_amount",
                help="输入你想要的下注金额"
            )
            
            # 显示实际需要投入的筹码
            actual_bet_needed = bet_amount - player.current_bet
            st.write(f"💰 需要投入筹码: ${actual_bet_needed}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"✅ 确认下注 ${bet_amount}", key="confirm_bet"):
                    action = Action(
                        action_type=ActionType.BET,
                        amount=bet_amount,  # 传递下注金额
                        player_id=0
                    )
                    controller.execute_action(action)
                    # 记录用户行动事件
                    st.session_state.events.append(f"你下注了 ${bet_amount} (投入 ${actual_bet_needed})")
                    st.session_state.show_bet_input = False
                    st.rerun()
            
            with col2:
                if st.button("❌ 取消", key="cancel_bet"):
                    st.session_state.show_bet_input = False
                    st.rerun()
        else:
            st.warning("筹码不足以进行下注")
            if st.button("❌ 取消", key="cancel_bet_insufficient"):
                st.session_state.show_bet_input = False
                st.rerun()

    # 加注金额输入（有人下注时）
    if hasattr(st.session_state, 'show_raise_input') and st.session_state.show_raise_input:
        st.subheader("📈 加注金额")
        
        # 计算正确的最小和最大加注金额
        last_raise_increment = snapshot.last_raise_amount if snapshot.last_raise_amount > 0 else snapshot.big_blind
        min_raise = snapshot.current_bet + last_raise_increment
        max_raise = player.chips + player.current_bet  # 玩家的总可用筹码
        
        if max_raise >= min_raise:
            # 显示当前下注信息
            st.info(f"当前下注: ${snapshot.current_bet} | 你已下注: ${player.current_bet}")
            st.info(f"上次加注增量: ${last_raise_increment} | 最小加注总额: ${min_raise}")
            
            bet_amount = st.number_input(
                f"总下注金额 (${min_raise} - ${max_raise})",
                min_value=min_raise,
                max_value=max_raise,
                value=min_raise,
                step=last_raise_increment,
                key="raise_amount",
                help="输入你想要的总下注金额（不是增量）"
            )
            
            # 显示实际需要投入的筹码
            actual_bet_needed = bet_amount - player.current_bet
            st.write(f"💰 需要投入筹码: ${actual_bet_needed}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"✅ 确认加注到 ${bet_amount}", key="confirm_raise"):
                    action = Action(
                        action_type=ActionType.RAISE,
                        amount=bet_amount,  # 传递总下注金额
                        player_id=0
                    )
                    controller.execute_action(action)
                    # 记录用户行动事件
                    st.session_state.events.append(f"你加注到 ${bet_amount} (投入 ${actual_bet_needed})")
                    st.session_state.show_raise_input = False
                    st.rerun()
            
            with col2:
                if st.button("❌ 取消", key="cancel_raise"):
                    st.session_state.show_raise_input = False
                    st.rerun()
        else:
            st.warning("筹码不足以进行加注")
            if st.button("❌ 取消", key="cancel_raise_insufficient"):
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
        
        # 显示当前session state状态
        st.sidebar.write("**Session State状态:**")
        if hasattr(st.session_state, 'controller'):
            controller = st.session_state.controller
            is_hand_over = controller.is_hand_over()
            snapshot = controller.get_snapshot()
            
            st.sidebar.text(f"game_started: {st.session_state.get('game_started', False)}")
            st.sidebar.text(f"showdown_processed: {st.session_state.get('showdown_processed', False)}")
            st.sidebar.text(f"hand_result_displayed: {st.session_state.get('hand_result_displayed', False)}")
            st.sidebar.text(f"is_hand_over: {is_hand_over}")
            st.sidebar.text(f"phase: {snapshot.phase if snapshot else 'None'}")
            st.sidebar.text(f"pot: ${snapshot.pot if snapshot else 0}")
            st.sidebar.text(f"hand_in_progress: {controller._hand_in_progress}")
            
            # 显示应该匹配的UI条件
            if is_hand_over and st.session_state.get('game_started', False):
                condition1 = (snapshot and snapshot.phase == Phase.SHOWDOWN and 
                             not st.session_state.get('showdown_processed', False))
                condition2 = (st.session_state.get('showdown_processed', False) and 
                             not st.session_state.get('hand_result_displayed', False))
                condition3 = (st.session_state.get('showdown_processed', False) and 
                             st.session_state.get('hand_result_displayed', False))
                condition4 = (not snapshot or snapshot.phase != Phase.SHOWDOWN)
                
                st.sidebar.text("**UI条件匹配:**")
                st.sidebar.text(f"需要处理摊牌: {condition1}")
                st.sidebar.text(f"显示结果: {condition2}")
                st.sidebar.text(f"摊牌完成: {condition3}")
                st.sidebar.text(f"非摊牌结束: {condition4}")
        
        # 强制重置session state按钮
        if st.sidebar.button("🔄 重置Session State"):
            st.session_state.showdown_processed = False
            st.session_state.hand_result_displayed = False
            if hasattr(st.session_state, 'last_hand_result'):
                del st.session_state.last_hand_result
            st.sidebar.success("✅ Session State已重置")
            st.rerun()
        
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
                
    # 显示实时日志和游戏事件
    st.sidebar.markdown("---")
    st.sidebar.subheader("📜 游戏日志")
    
    # 显示游戏事件日志（更详细的信息）
    if hasattr(st.session_state, 'controller'):
        snapshot = st.session_state.controller.get_snapshot()
        if snapshot and hasattr(snapshot, 'events') and snapshot.events:
            # 显示游戏状态中的事件
            st.sidebar.write("**游戏状态事件:**")
            recent_game_events = snapshot.events[-8:]  # 最近8个事件
            for i, event in enumerate(reversed(recent_game_events)):
                st.sidebar.text(f"{len(recent_game_events)-i}. {event}")
        
    # 显示实时系统日志（调试模式下）
    if debug_mode and hasattr(st.session_state, 'log_file_path'):
        # 显示日志开关
        show_logs = st.sidebar.checkbox("显示系统日志", value=st.session_state.get('show_logs', False))
        st.session_state.show_logs = show_logs
        
        if show_logs:
            log_lines = read_log_file_tail(st.session_state.log_file_path, max_lines=15)
            if log_lines:
                st.sidebar.write("**系统日志:**")
                # 过滤并格式化日志，只显示重要信息
                filtered_logs = []
                for line in log_lines[-8:]:  # 最后8行
                    if any(keyword in line.lower() for keyword in ['action', 'bet', 'fold', 'call', 'raise', 'phase', 'winner']):
                        # 简化日志显示，只保留关键信息
                        if ' - ' in line:
                            parts = line.split(' - ')
                            if len(parts) >= 3:
                                time_part = parts[0].split()[-1] if parts[0] else ""
                                message = parts[-1].strip()
                                filtered_logs.append(f"{time_part}: {message}")
                
                if filtered_logs:
                    for log in filtered_logs[-6:]:  # 最多显示6行
                        st.sidebar.text(log)
                else:
                    st.sidebar.text("暂无相关日志")
    
    # 事件日志（保留原有功能）
    if st.session_state.events:
        st.sidebar.write("**UI事件:**")
        # 显示最近的事件（倒序）
        recent_events = st.session_state.events[-5:]  # 最近5个事件
        for i, event in enumerate(reversed(recent_events)):
            event_text = f"{len(recent_events)-i}. {event}"
            st.sidebar.text(event_text)
    
    # 清除事件日志按钮
    if st.sidebar.button("🗑️ 清除日志"):
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
                        action = Action(
                            action_type=action_type,
                            amount=0,
                            player_id=0
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
                # 确保没有手牌在进行中
                if controller._hand_in_progress:
                    try:
                        controller.end_hand()
                    except Exception as e:
                        st.warning(f"结束上一手牌时出错: {e}")
                
                success = controller.start_new_hand()
                if success:
                    st.session_state.game_started = True
                    st.session_state.events = []
                    # 重置摊牌处理标记
                    st.session_state.showdown_processed = False
                    st.session_state.hand_result_displayed = False
                    if hasattr(st.session_state, 'show_raise_input'):
                        st.session_state.show_raise_input = False
                    st.rerun()
                else:
                    st.error("❌ 无法开始新手牌，请检查游戏状态")
        return
    
    # 渲染游戏状态
    render_game_state(snapshot)
    
    # 检查手牌是否结束
    is_hand_over = controller.is_hand_over()
    
    # 处理游戏逻辑
    if st.session_state.game_started and not is_hand_over:
        # 手牌进行中，处理AI行动
        current_player_id = controller.get_current_player_id()
        if current_player_id is not None and current_player_id != 0:
            # 当前是AI玩家，自动处理
            ai_processed = process_ai_actions_continuously(controller)
            if ai_processed:
                st.rerun()  # 刷新页面显示最新状态
        elif current_player_id is None:
            # 没有当前玩家，可能需要检查游戏状态
            st.info("⏳ 检查游戏状态...")
            st.rerun()  # 刷新页面重新检查状态
        
        # 渲染行动按钮（只有轮到人类玩家时）
        if current_player_id == 0:
            render_action_buttons(controller)
        else:
            st.info("🤖 等待AI玩家行动...")
            
    elif st.session_state.game_started and is_hand_over:
        # 手牌结束，处理摊牌逻辑
        snapshot = controller.get_snapshot()
        
        # 检查是否需要处理摊牌
        if (snapshot and snapshot.phase == Phase.SHOWDOWN and 
            not st.session_state.showdown_processed):
            
            st.info("🎯 摊牌阶段，正在计算结果...")
            try:
                result = controller.end_hand()
                if result:
                    # 标记摊牌已处理
                    st.session_state.showdown_processed = True
                    
                    # 记录手牌结束事件
                    if 'events' not in st.session_state:
                        st.session_state.events = []
                    st.session_state.events.append(f"手牌结束: {result.winning_hand_description}")
                    
                    # 存储结果用于显示
                    st.session_state.last_hand_result = result
                    st.session_state.hand_result_displayed = False
                    
                    st.rerun()  # 刷新页面显示结果
                else:
                    st.error("❌ 摊牌计算失败")
                    st.session_state.showdown_processed = True
                    st.rerun()
            except Exception as e:
                st.error(f"摊牌阶段处理失败: {e}")
                st.session_state.showdown_processed = True
                st.rerun()
        
        # 统一的手牌结束显示和下一手牌逻辑
        else:
            st.success("🎉 手牌结束！")
            
            # 显示结果
            if hasattr(st.session_state, 'last_hand_result') and st.session_state.last_hand_result:
                result = st.session_state.last_hand_result
                current_snapshot = controller.get_snapshot()
                if current_snapshot:
                    winner_names = [current_snapshot.players[i].name for i in result.winner_ids]
                    st.write(f"🏆 获胜者: {', '.join(winner_names)}")
                    st.write(f"💰 底池金额: ${result.pot_amount}")
                    if result.winning_hand_description:
                        st.write(f"🃏 获胜牌型: {result.winning_hand_description}")
            
            # 标记结果已显示（如果还没有标记的话）
            if not st.session_state.hand_result_displayed:
                st.session_state.hand_result_displayed = True
            
            # 统一的下一手牌按钮
            col1, col2 = st.columns(2)
            with col2:
                # 使用唯一的key避免重复
                button_key = f"next_hand_{hash(str(st.session_state.get('last_hand_result', '')))}"
                if st.button("🔄 下一手牌", type="primary", key=button_key):
                    try:
                        # 记录用户操作
                        if 'events' not in st.session_state:
                            st.session_state.events = []
                        st.session_state.events.append("[USER] 点击了'下一手牌'按钮")
                        
                        success = controller.start_new_hand()
                        if success:
                            # 清理状态
                            st.session_state.events = []
                            st.session_state.showdown_processed = False
                            st.session_state.hand_result_displayed = False
                            
                            # 清理可选状态
                            for attr in ['show_raise_input', 'show_bet_input', 'last_hand_result']:
                                if hasattr(st.session_state, attr):
                                    delattr(st.session_state, attr)
                            
                            st.session_state.events.append("[SYSTEM] 新手牌开始成功")
                            st.rerun()
                        else:
                            st.error("❌ 无法开始新手牌")
                            st.session_state.events.append("[ERROR] 无法开始新手牌")
                    except RuntimeError as e:
                        # 如果出现"当前已有手牌在进行中"的错误，强制重置状态
                        if "当前已有手牌在进行中" in str(e):
                            st.warning("检测到手牌状态异常，正在重置...")
                            st.session_state.events.append("[SYSTEM] 检测到手牌状态异常，正在重置")
                            try:
                                # 使用强制重置方法
                                controller.force_reset_hand_state()
                                success = controller.start_new_hand()
                                if success:
                                    # 清理状态
                                    st.session_state.events = []
                                    st.session_state.showdown_processed = False
                                    st.session_state.hand_result_displayed = False
                                    
                                    # 清理可选状态
                                    for attr in ['show_raise_input', 'show_bet_input', 'last_hand_result']:
                                        if hasattr(st.session_state, attr):
                                            delattr(st.session_state, attr)
                                    
                                    st.session_state.events.append("[SYSTEM] 重置成功，新手牌开始")
                                    st.rerun()
                                else:
                                    st.error("❌ 重置后仍无法开始新手牌")
                                    st.session_state.events.append("[ERROR] 重置后仍无法开始新手牌")
                            except Exception as reset_e:
                                st.error(f"❌ 重置失败: {reset_e}")
                                st.session_state.events.append(f"[ERROR] 重置失败: {reset_e}")
                        else:
                            st.error(f"❌ 开始新手牌失败: {e}")
                            st.session_state.events.append(f"[ERROR] 开始新手牌失败: {e}")


if __name__ == "__main__":
    main() 