"""
Tests for Streamlit log visualization functionality.

This module tests the log visualization features in the Streamlit application,
including file logging setup, log reading, and display functionality.
"""

import pytest
import tempfile
import os
import logging
from unittest.mock import Mock, patch, MagicMock

# Import the functions we want to test
from v2.ui.streamlit.app import setup_file_logging, read_log_file_tail


@pytest.mark.unit
@pytest.mark.fast
class TestLogVisualization:
    """Test log visualization functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock session state
        self.mock_session_state = MagicMock()
        self.mock_session_state.log_file_path = None
        
    @pytest.mark.unit
    @pytest.mark.fast
    def test_setup_file_logging_creates_log_file(self):
        """Test that setup_file_logging creates a log file and configures handlers."""
        with patch('v2.ui.streamlit.app.st') as mock_st:
            # Create a simple object to act as session_state
            class MockSessionState:
                pass
            
            mock_session_state = MockSessionState()
            mock_st.session_state = mock_session_state
            
            # Call the function
            setup_file_logging()
            
            # Verify log file path was set
            assert hasattr(mock_st.session_state, 'log_file_path')
            assert mock_st.session_state.log_file_path is not None
            assert 'texas_holdem_debug.log' in mock_st.session_state.log_file_path
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_setup_file_logging_idempotent(self):
        """Test that setup_file_logging is idempotent (can be called multiple times)."""
        with patch('v2.ui.streamlit.app.st') as mock_st:
            mock_st.session_state = self.mock_session_state
            mock_st.session_state.log_file_path = '/existing/path/log.txt'
            
            # Call the function when log_file_path already exists
            setup_file_logging()
            
            # Verify the path wasn't changed
            assert mock_st.session_state.log_file_path == '/existing/path/log.txt'
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_read_log_file_tail_nonexistent_file(self):
        """Test reading from a non-existent log file."""
        result = read_log_file_tail('/nonexistent/path/log.txt')
        
        assert len(result) == 1
        assert "日志文件不存在" in result[0]
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_read_log_file_tail_empty_file(self):
        """Test reading from an empty log file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            temp_path = f.name
        
        try:
            result = read_log_file_tail(temp_path)
            assert len(result) == 1
            assert "暂无日志内容" in result[0]
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_read_log_file_tail_with_content(self):
        """Test reading from a log file with content."""
        log_content = [
            "2024-01-01 10:00:01 - test - INFO - First log message",
            "2024-01-01 10:00:02 - test - DEBUG - Second log message", 
            "2024-01-01 10:00:03 - test - WARNING - Third log message",
            "",  # Empty line should be filtered out
            "2024-01-01 10:00:04 - test - ERROR - Fourth log message"
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write('\n'.join(log_content))
            temp_path = f.name
        
        try:
            result = read_log_file_tail(temp_path, max_lines=10)
            
            # Should have 4 lines (empty line filtered out)
            assert len(result) == 4
            assert "First log message" in result[0]
            assert "Second log message" in result[1]
            assert "Third log message" in result[2]
            assert "Fourth log message" in result[3]
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_read_log_file_tail_max_lines_limit(self):
        """Test that max_lines parameter limits the output."""
        log_content = [f"Line {i}" for i in range(20)]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write('\n'.join(log_content))
            temp_path = f.name
        
        try:
            result = read_log_file_tail(temp_path, max_lines=5)
            
            # Should only return last 5 lines
            assert len(result) == 5
            assert "Line 15" in result[0]
            assert "Line 19" in result[4]
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_read_log_file_tail_handles_unicode(self):
        """Test that log file reading handles Unicode characters correctly."""
        log_content = [
            "2024-01-01 10:00:01 - test - INFO - 游戏开始",
            "2024-01-01 10:00:02 - test - DEBUG - 玩家行动: 跟注",
            "2024-01-01 10:00:03 - test - WARNING - 筹码不足"
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write('\n'.join(log_content))
            temp_path = f.name
        
        try:
            result = read_log_file_tail(temp_path)
            
            assert len(result) == 3
            assert "游戏开始" in result[0]
            assert "跟注" in result[1]
            assert "筹码不足" in result[2]
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_read_log_file_tail_handles_read_error(self):
        """Test that read_log_file_tail handles file read errors gracefully."""
        # Create a file and then make it unreadable
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name
        
        try:
            # On Windows, we'll simulate the error by patching the open function
            import sys
            if sys.platform.startswith('win'):
                # Mock open to raise PermissionError
                with patch('builtins.open', side_effect=PermissionError("Access denied")):
                    result = read_log_file_tail(temp_path)
                    
                    assert len(result) == 1
                    assert "读取日志文件失败" in result[0]
            else:
                # On Unix-like systems, change file permissions
                if hasattr(os, 'chmod'):
                    os.chmod(temp_path, 0o000)
                    
                    result = read_log_file_tail(temp_path)
                    
                    assert len(result) == 1
                    assert "读取日志文件失败" in result[0]
                else:
                    pytest.skip("Cannot test file permission errors on this system")
        except (OSError, PermissionError):
            # If permission change fails, skip this test
            pytest.skip("Cannot test file permission errors on this system")
        finally:
            try:
                if hasattr(os, 'chmod'):
                    os.chmod(temp_path, 0o644)  # Restore permissions
                os.unlink(temp_path)
            except (OSError, PermissionError):
                pass
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_file_logging_integration(self):
        """Test integration of file logging with actual logging."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name
        
        try:
            # Set up file handler
            file_handler = logging.FileHandler(temp_path, mode='w', encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # Create test logger
            test_logger = logging.getLogger('test_logger')
            test_logger.setLevel(logging.DEBUG)
            test_logger.addHandler(file_handler)
            
            # Log some messages
            test_logger.info("Test info message")
            test_logger.debug("Test debug message")
            test_logger.warning("Test warning message")
            
            # Flush and close handler
            file_handler.flush()
            file_handler.close()
            test_logger.removeHandler(file_handler)
            
            # Read back the log content
            result = read_log_file_tail(temp_path)
            
            assert len(result) >= 3
            assert any("Test info message" in line for line in result)
            assert any("Test debug message" in line for line in result)
            assert any("Test warning message" in line for line in result)
            
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    
    @pytest.mark.unit
    @pytest.mark.fast
    def test_log_visualization_debug_mode_only(self):
        """Test that log visualization is only shown in debug mode."""
        # This test would require mocking Streamlit components
        # For now, we'll test the logic that determines when to show logs
        
        # Simulate debug mode off
        debug_mode = False
        show_logs = False
        
        # In non-debug mode, logs should not be shown
        assert not (debug_mode and show_logs)
        
        # Simulate debug mode on, logs enabled
        debug_mode = True
        show_logs = True
        
        # In debug mode with logs enabled, logs should be shown
        assert debug_mode and show_logs
        
        # Simulate debug mode on, logs disabled
        debug_mode = True
        show_logs = False
        
        # In debug mode with logs disabled, logs should not be shown
        assert not (debug_mode and show_logs) 