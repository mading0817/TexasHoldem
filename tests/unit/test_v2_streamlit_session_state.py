"""
Unit tests for Streamlit session state initialization.

Tests for PLAN #38: Session State 幂等初始化问题
"""

import pytest
from unittest.mock import Mock, patch
import streamlit as st

from v2.ui.streamlit.app import initialize_session_state
from v2.controller.poker_controller import PokerController


class TestSessionStateInitialization:
    """测试Streamlit session state初始化的幂等性."""
    
    def setup_method(self):
        """每个测试前重置session state."""
        # 清空session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
    
    def test_initialize_session_state_first_time(self):
        """测试首次初始化session state."""
        # 确保session state为空
        assert len(st.session_state) == 0
        
        # 初始化
        initialize_session_state()
        
        # 验证所有必需的键都存在
        assert 'controller' in st.session_state
        assert 'game_started' in st.session_state
        assert 'events' in st.session_state
        assert 'debug_mode' in st.session_state
        assert 'show_raise_input' in st.session_state
        
        # 验证默认值
        assert st.session_state.game_started is False
        assert st.session_state.events == []
        assert st.session_state.debug_mode is False
        assert st.session_state.show_raise_input is False
        
        # 验证控制器类型
        assert isinstance(st.session_state.controller, PokerController)
    
    def test_initialize_session_state_idempotent(self):
        """测试重复调用initialize_session_state的幂等性."""
        # 首次初始化
        initialize_session_state()
        
        # 保存初始状态
        original_controller = st.session_state.controller
        original_game_started = st.session_state.game_started
        original_events = st.session_state.events
        original_debug_mode = st.session_state.debug_mode
        original_show_raise_input = st.session_state.show_raise_input
        
        # 修改一些值
        st.session_state.game_started = True
        st.session_state.events = ['test_event']
        st.session_state.debug_mode = True
        st.session_state.show_raise_input = True
        
        # 再次初始化
        initialize_session_state()
        
        # 验证控制器没有被重新创建
        assert st.session_state.controller is original_controller
        
        # 验证修改的值保持不变（幂等性）
        assert st.session_state.game_started is True
        assert st.session_state.events == ['test_event']
        assert st.session_state.debug_mode is True
        assert st.session_state.show_raise_input is True
    
    def test_initialize_session_state_partial_state(self):
        """测试部分session state存在时的初始化."""
        # 预设部分状态
        st.session_state.game_started = True
        st.session_state.events = ['existing_event']
        
        # 初始化
        initialize_session_state()
        
        # 验证预设的值保持不变
        assert st.session_state.game_started is True
        assert st.session_state.events == ['existing_event']
        
        # 验证缺失的键被添加
        assert 'controller' in st.session_state
        assert 'debug_mode' in st.session_state
        assert 'show_raise_input' in st.session_state
        
        # 验证新添加键的默认值
        assert st.session_state.debug_mode is False
        assert st.session_state.show_raise_input is False
    
    def test_initialize_session_state_no_keyerror(self):
        """测试在空session state下调用两次初始化不会产生KeyError."""
        # 确保session state为空
        assert len(st.session_state) == 0
        
        # 连续调用两次，不应该抛出KeyError
        try:
            initialize_session_state()
            initialize_session_state()
        except KeyError as e:
            pytest.fail(f"initialize_session_state raised KeyError: {e}")
        
        # 验证状态正确
        assert len(st.session_state) == 5  # 应该有5个键
        assert isinstance(st.session_state.controller, PokerController)
    
    def test_initialize_session_state_controller_creation(self):
        """测试控制器创建的正确性."""
        initialize_session_state()
        
        controller = st.session_state.controller
        
        # 验证控制器具有必要的方法
        assert hasattr(controller, 'start_new_hand')
        assert hasattr(controller, 'execute_action')
        assert hasattr(controller, 'get_snapshot')
        assert hasattr(controller, 'is_hand_over')
        assert hasattr(controller, 'get_current_player_id')
        
        # 验证控制器可以正常工作
        assert controller.get_snapshot() is not None
        assert controller.is_hand_over() is True  # 初始状态应该没有手牌在进行
    
    def test_initialize_session_state_multiple_calls_same_controller(self):
        """测试多次调用不会创建新的控制器实例."""
        initialize_session_state()
        controller1 = st.session_state.controller
        
        initialize_session_state()
        controller2 = st.session_state.controller
        
        initialize_session_state()
        controller3 = st.session_state.controller
        
        # 验证是同一个实例
        assert controller1 is controller2
        assert controller2 is controller3
        assert controller1 is controller3
    
    def test_initialize_session_state_all_required_keys(self):
        """测试所有必需的键都被正确初始化."""
        initialize_session_state()
        
        required_keys = {
            'controller': PokerController,
            'game_started': bool,
            'events': list,
            'debug_mode': bool,
            'show_raise_input': bool
        }
        
        for key, expected_type in required_keys.items():
            assert key in st.session_state, f"Missing required key: {key}"
            assert isinstance(st.session_state[key], expected_type), \
                f"Key {key} has wrong type: {type(st.session_state[key])}, expected {expected_type}" 