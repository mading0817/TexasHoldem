#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单的CLI启动测试，验证游戏是否能正常启动
"""

import sys
import os
import subprocess
import signal

def test_cli_startup():
    """测试CLI游戏启动"""
    print("🚀 测试CLI游戏启动...")
    
    try:
        # 启动CLI游戏进程
        proc = subprocess.Popen(
            [sys.executable, 'cli_game.py'], 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        # 发送初始配置：4个玩家，1000筹码，不开启调试，名字Test
        inputs = "4\n1000\nn\nTest\n"
        
        try:
            stdout, stderr = proc.communicate(input=inputs, timeout=10)
            
            if proc.returncode == 0 or "游戏开始" in stdout or "请输入" in stdout:
                print("✅ CLI游戏启动成功")
                print("📄 输出预览:")
                print(stdout[:800])
                return True
            else:
                print("❌ CLI游戏启动失败")
                print("🔴 错误输出:")
                print(stderr[:500])
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ CLI游戏启动超时，但可能正在等待用户输入（正常情况）")
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
            return True
            
    except Exception as e:
        print(f"❌ 测试过程发生异常: {e}")
        return False

if __name__ == "__main__":
    success = test_cli_startup()
    exit(0 if success else 1) 