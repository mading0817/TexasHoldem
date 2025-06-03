"""
测试Streamlit应用启动和session state初始化.

这个测试验证应用能否正常启动，所有session state变量是否正确初始化。
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_session_state_initialization():
    """测试session state初始化是否包含所有必要的变量."""
    # Mock streamlit
    with patch('streamlit.session_state') as mock_session_state:
        # 模拟session state为空字典
        mock_session_state.__contains__ = lambda key: False
        mock_session_state.__setattr__ = Mock()
        
        # Mock其他streamlit组件
        with patch('streamlit.set_page_config'), \
             patch('streamlit.title'), \
             patch('streamlit.markdown'), \
             patch('streamlit.info'), \
             patch('streamlit.columns'), \
             patch('streamlit.button'), \
             patch('streamlit.sidebar'):
            
            # 导入并调用初始化函数
            from v2.ui.streamlit.app import initialize_session_state
            
            # 调用初始化函数
            initialize_session_state()
            
            # 验证所有必要的session state变量都被设置
            expected_vars = [
                'controller',
                'game_started', 
                'events',
                'log_file_path',
                'showdown_processed',
                'hand_result_displayed',
                'debug_mode',
                'show_logs',
                'show_raise_input',
                'show_bet_input'
            ]
            
            # 检查所有变量都被设置
            for var in expected_vars:
                mock_session_state.__setattr__.assert_any_call(var, pytest.approx(True, abs=1e-9) if var in ['debug_mode', 'show_logs', 'show_raise_input', 'show_bet_input', 'game_started', 'showdown_processed', 'hand_result_displayed'] and var not in ['game_started', 'showdown_processed', 'hand_result_displayed'] else pytest.approx(False, abs=1e-9) if var in ['debug_mode', 'show_logs', 'show_raise_input', 'show_bet_input'] else pytest.approx([], abs=1e-9) if var == 'events' else None if var == 'log_file_path' else pytest.approx(False, abs=1e-9))


def test_app_imports():
    """测试应用的所有导入是否正常."""
    try:
        from v2.ui.streamlit.app import (
            initialize_session_state,
            render_header,
            render_game_state,
            render_action_buttons,
            render_sidebar,
            main
        )
        assert True, "所有函数导入成功"
    except ImportError as e:
        pytest.fail(f"导入失败: {e}")


def test_debug_mode_variables_exist():
    """测试调试模式相关的变量是否都存在于代码中."""
    import inspect
    from v2.ui.streamlit.app import initialize_session_state
    
    # 获取函数源码
    source = inspect.getsource(initialize_session_state)
    
    # 检查关键的session state变量是否在初始化函数中
    required_vars = [
        'debug_mode',
        'show_logs', 
        'show_raise_input',
        'show_bet_input'
    ]
    
    for var in required_vars:
        assert f'st.session_state.{var}' in source, f"变量 {var} 未在初始化函数中设置"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 