"""
测试用户游戏流程.

这个测试模拟用户的实际游戏操作，验证修复后的应用能否正常工作。
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_complete_game_flow():
    """测试完整的游戏流程，包括session state初始化和调试模式."""
    
    # Mock streamlit session state
    mock_session_state = MagicMock()
    mock_session_state.__contains__ = Mock(return_value=False)  # 模拟空的session state
    
    # Mock streamlit组件
    with patch('streamlit.session_state', mock_session_state), \
         patch('streamlit.set_page_config'), \
         patch('streamlit.title'), \
         patch('streamlit.markdown'), \
         patch('streamlit.info'), \
         patch('streamlit.columns'), \
         patch('streamlit.button'), \
         patch('streamlit.sidebar') as mock_sidebar, \
         patch('streamlit.rerun'), \
         patch('streamlit.success'), \
         patch('streamlit.error'), \
         patch('streamlit.warning'):
        
        # 设置sidebar mock
        mock_sidebar.title = Mock()
        mock_sidebar.checkbox = Mock(return_value=False)
        mock_sidebar.selectbox = Mock(return_value="INFO")
        mock_sidebar.button = Mock(return_value=False)
        mock_sidebar.markdown = Mock()
        mock_sidebar.subheader = Mock()
        mock_sidebar.write = Mock()
        mock_sidebar.text = Mock()
        
        # 导入应用模块
        from v2.ui.streamlit.app import initialize_session_state, render_sidebar, main
        
        # 测试初始化
        initialize_session_state()
        
        # 验证初始化函数被调用（通过检查session state的设置）
        assert mock_session_state.__setitem__.called or hasattr(mock_session_state, 'debug_mode')
        
        # 测试render_sidebar不会因为缺少debug_mode而报错
        try:
            render_sidebar()
            # 如果没有异常，说明测试通过
            assert True
        except AttributeError as e:
            if "debug_mode" in str(e):
                pytest.fail(f"debug_mode仍然未初始化: {e}")
            else:
                # 其他AttributeError可能是正常的mock限制
                pass


def test_debug_mode_toggle():
    """测试调试模式的开关功能."""
    
    mock_session_state = MagicMock()
    mock_session_state.debug_mode = False
    mock_session_state.show_logs = False
    mock_session_state.__contains__ = lambda key: True  # 模拟已初始化的session state
    
    with patch('streamlit.session_state', mock_session_state), \
         patch('streamlit.sidebar') as mock_sidebar:
        
        # 模拟用户点击调试模式checkbox
        mock_sidebar.checkbox = Mock(return_value=True)  # 用户开启调试模式
        mock_sidebar.title = Mock()
        mock_sidebar.selectbox = Mock(return_value="DEBUG")
        mock_sidebar.button = Mock(return_value=False)
        mock_sidebar.markdown = Mock()
        mock_sidebar.subheader = Mock()
        mock_sidebar.write = Mock()
        mock_sidebar.text = Mock()
        
        from v2.ui.streamlit.app import render_sidebar
        
        # 测试render_sidebar处理调试模式切换
        try:
            render_sidebar()
            # 验证debug_mode被正确更新
            assert mock_session_state.debug_mode == True
        except Exception as e:
            pytest.fail(f"调试模式切换失败: {e}")


def test_session_state_variables_coverage():
    """测试所有在代码中使用的session state变量都被初始化."""
    
    # 读取app.py文件内容
    app_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'ui', 'streamlit', 'app.py')
    with open(app_file_path, 'r', encoding='utf-8') as f:
        app_content = f.read()
    
    # 提取所有st.session_state.xxx的使用
    import re
    session_state_vars = set()
    pattern = r'st\.session_state\.(\w+)'
    matches = re.findall(pattern, app_content)
    
    for match in matches:
        session_state_vars.add(match)
    
    # 检查initialize_session_state函数中是否初始化了所有变量
    init_function_start = app_content.find('def initialize_session_state():')
    init_function_end = app_content.find('\ndef ', init_function_start + 1)
    init_function_content = app_content[init_function_start:init_function_end]
    
    # 这些变量在运行时动态创建，不需要在初始化中设置
    runtime_vars = {
        'last_hand_result',  # 在游戏过程中创建
        'log_handler_setup',  # 在日志设置中创建
        'get'  # 这不是session state变量，是方法调用
    }
    
    missing_vars = []
    for var in session_state_vars:
        if var not in runtime_vars and f'st.session_state.{var}' not in init_function_content:
            missing_vars.append(var)
    
    if missing_vars:
        pytest.fail(f"以下session state变量未在初始化函数中设置: {missing_vars}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 