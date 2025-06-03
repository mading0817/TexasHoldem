"""
测试Streamlit应用启动和session state初始化.

这个测试验证应用能否正常启动，所有session state变量是否正确初始化。
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_session_state_initialization():
    """测试session state初始化是否包含所有必要的变量."""
    # Mock streamlit 模块
    with patch('v2.ui.streamlit.app.st') as mock_st:
        # 创建一个简单的字典来模拟session state
        session_state_data = {}
        
        # 创建一个自定义的session state mock类
        class MockSessionState:
            def __init__(self):
                self._data = session_state_data
                
            def __contains__(self, key):
                return key in self._data
                
            def __setattr__(self, key, value):
                if key.startswith('_'):
                    super().__setattr__(key, value)
                else:
                    self._data[key] = value
                    
            def __getattr__(self, key):
                return self._data.get(key)
        
        # 将mock_session_state赋值给st.session_state
        mock_st.session_state = MockSessionState()
        
        # Mock其他必要的streamlit组件
        mock_st.title = Mock()
        mock_st.markdown = Mock()
        mock_st.info = Mock()
        
        # 导入并调用初始化函数
        from v2.ui.streamlit.app import initialize_session_state
        
        # 调用初始化函数
        initialize_session_state()
        
        # 验证变量被设置
        assert len(session_state_data) > 0, "session state变量应该被设置"
        
        # 验证关键变量被设置
        required_keys = ['controller', 'game_started', 'events', 'debug_mode']
        for key in required_keys:
            assert key in session_state_data, f"关键变量 {key} 应该被设置"


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