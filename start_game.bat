@echo off
echo 🃏 启动德州扑克游戏...
echo.
echo 正在启动Streamlit应用...
echo 请稍等，浏览器将自动打开 http://localhost:8501
echo.
echo 如果浏览器没有自动打开，请手动访问: http://localhost:8501
echo.
echo 按 Ctrl+C 停止游戏服务器
echo.

REM 确保在项目根目录运行
cd /d "%~dp0"

REM 设置PYTHONPATH环境变量
set PYTHONPATH=%CD%;%PYTHONPATH%

.venv\Scripts\streamlit.exe run v2\ui\streamlit\app.py

echo.
echo 游戏服务器已停止
pause 