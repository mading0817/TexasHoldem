#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
游戏配置(GameConfig)和玩家配置(PlayerConfig)类单元测试
测试配置创建、验证、默认配置等功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core_game_logic.core.config import GameConfig, PlayerConfig
from core_game_logic.core.exceptions import GameConfigError


class TestPlayerConfig:
    """玩家配置测试"""
    
    def test_player_config_creation(self):
        """测试玩家配置创建"""
        print("测试玩家配置创建...")
        
        # 测试人类玩家配置
        human_config = PlayerConfig(seat=0, type="human", name="玩家1")
        assert human_config.seat == 0, "座位号应该正确"
        assert human_config.type == "human", "类型应该是human"
        assert human_config.name == "玩家1", "名称应该正确"
        assert human_config.is_human, "应该是人类玩家"
        assert not human_config.is_ai, "不应该是AI玩家"
        
        # 测试AI玩家配置
        ai_config = PlayerConfig(seat=1, type="ai", model="random", name="AI-1")
        assert ai_config.seat == 1, "座位号应该正确"
        assert ai_config.type == "ai", "类型应该是ai"
        assert ai_config.model == "random", "模型应该正确"
        assert ai_config.name == "AI-1", "名称应该正确"
        assert not ai_config.is_human, "不应该是人类玩家"
        assert ai_config.is_ai, "应该是AI玩家"
        
        print("[OK] 玩家配置创建测试通过")
    
    def test_player_config_default_names(self):
        """测试玩家配置默认名称"""
        print("测试玩家配置默认名称...")
        
        # 测试人类玩家默认名称
        human_config = PlayerConfig(seat=0, type="human")
        assert human_config.name == "玩家1", "人类玩家默认名称应该正确"
        
        # 测试AI玩家默认名称
        ai_config = PlayerConfig(seat=2, type="ai", model="gemini")
        assert ai_config.name == "AI-GEMINI-3", "AI玩家默认名称应该正确"
        
        print("[OK] 玩家配置默认名称测试通过")
    
    def test_player_config_validation(self):
        """测试玩家配置验证"""
        print("测试玩家配置验证...")
        
        # 测试无效座位号
        try:
            PlayerConfig(seat=-1, type="human")
            assert False, "负数座位号应该抛出异常"
        except ValueError:
            pass
        
        # 测试无效玩家类型
        try:
            PlayerConfig(seat=0, type="invalid")
            assert False, "无效玩家类型应该抛出异常"
        except ValueError:
            pass
        
        # 测试无效AI模型
        try:
            PlayerConfig(seat=0, type="ai", model="invalid")
            assert False, "无效AI模型应该抛出异常"
        except ValueError:
            pass
        
        print("[OK] 玩家配置验证测试通过")


class TestGameConfig:
    """游戏配置测试"""
    
    def test_game_config_creation(self):
        """测试游戏配置创建"""
        print("测试游戏配置创建...")
        
        # 创建基本配置
        config = GameConfig(
            starting_chips=1000,
            small_blind=1,
            big_blind=2,
            max_players=6,
            min_players=2
        )
        
        assert config.starting_chips == 1000, "初始筹码应该正确"
        assert config.small_blind == 1, "小盲注应该正确"
        assert config.big_blind == 2, "大盲注应该正确"
        assert config.max_players == 6, "最大玩家数应该正确"
        assert config.min_players == 2, "最小玩家数应该正确"
        
        print("[OK] 游戏配置创建测试通过")
    
    def test_default_4_player_config(self):
        """测试默认4人游戏配置"""
        print("测试默认4人游戏配置...")
        
        config = GameConfig.default_4_player()
        
        # 验证基本设置
        assert len(config.players) == 4, "应该有4个玩家"
        assert config.starting_chips == 1000, "初始筹码应该是1000"
        assert config.small_blind == 1, "小盲注应该是1"
        assert config.big_blind == 2, "大盲注应该是2"
        assert config.max_players == 4, "最大玩家数应该是4"
        
        # 验证玩家配置
        human_player = config.get_human_player()
        assert human_player is not None, "应该有人类玩家"
        assert human_player.seat == 0, "人类玩家应该在座位0"
        assert human_player.is_human, "应该是人类玩家"
        
        ai_players = config.get_ai_players()
        assert len(ai_players) == 3, "应该有3个AI玩家"
        for ai_player in ai_players:
            assert ai_player.is_ai, "应该是AI玩家"
            assert ai_player.model == "random", "默认应该是random模型"
        
        print("[OK] 默认4人游戏配置测试通过")
    
    def test_default_heads_up_config(self):
        """测试默认单挑游戏配置"""
        print("测试默认单挑游戏配置...")
        
        config = GameConfig.default_heads_up()
        
        # 验证基本设置
        assert len(config.players) == 2, "应该有2个玩家"
        assert config.max_players == 2, "最大玩家数应该是2"
        assert config.min_players == 2, "最小玩家数应该是2"
        
        # 验证玩家配置
        human_player = config.get_human_player()
        assert human_player is not None, "应该有人类玩家"
        assert human_player.seat == 0, "人类玩家应该在座位0"
        
        ai_players = config.get_ai_players()
        assert len(ai_players) == 1, "应该有1个AI玩家"
        assert ai_players[0].seat == 1, "AI玩家应该在座位1"
        
        print("[OK] 默认单挑游戏配置测试通过")
    
    def test_game_config_validation(self):
        """测试游戏配置验证"""
        print("测试游戏配置验证...")
        
        # 测试无效初始筹码
        try:
            GameConfig(starting_chips=0)
            assert False, "初始筹码为0应该抛出异常"
        except ValueError:
            pass
        
        # 测试无效小盲注
        try:
            GameConfig(small_blind=0)
            assert False, "小盲注为0应该抛出异常"
        except ValueError:
            pass
        
        # 测试大盲注小于小盲注
        try:
            GameConfig(small_blind=10, big_blind=5)
            assert False, "大盲注小于小盲注应该抛出异常"
        except ValueError:
            pass
        
        # 测试最大玩家数小于最小玩家数
        try:
            GameConfig(max_players=2, min_players=4)
            assert False, "最大玩家数小于最小玩家数应该抛出异常"
        except ValueError:
            pass
        
        print("[OK] 游戏配置验证测试通过")
    
    def test_add_player(self):
        """测试添加玩家"""
        print("测试添加玩家...")
        
        config = GameConfig()
        
        # 添加人类玩家
        human_config = PlayerConfig(seat=0, type="human")
        config.add_player(human_config)
        assert len(config.players) == 1, "应该有1个玩家"
        
        # 添加AI玩家
        ai_config = PlayerConfig(seat=1, type="ai", model="random")
        config.add_player(ai_config)
        assert len(config.players) == 2, "应该有2个玩家"
        
        # 测试重复座位
        try:
            duplicate_config = PlayerConfig(seat=0, type="ai", model="random")
            config.add_player(duplicate_config)
            assert False, "重复座位应该抛出异常"
        except ValueError:
            pass
        
        print("[OK] 添加玩家测试通过")
    
    def test_player_validation(self):
        """测试玩家验证"""
        print("测试玩家验证...")
        
        # 测试超过最大玩家数
        config = GameConfig(max_players=2)
        config.add_player(PlayerConfig(seat=0, type="human"))
        config.add_player(PlayerConfig(seat=1, type="ai", model="random"))
        
        try:
            config.add_player(PlayerConfig(seat=2, type="ai", model="random"))
            assert False, "超过最大玩家数应该抛出异常"
        except ValueError:
            pass
        
        # 测试没有人类玩家 - 使用validate_for_game_start方法
        try:
            config = GameConfig(players=[
                PlayerConfig(seat=0, type="ai", model="random"),
                PlayerConfig(seat=1, type="ai", model="random")
            ])
            config.validate_for_game_start()  # 这里应该抛出异常
            assert False, "没有人类玩家应该抛出异常"
        except ValueError:
            pass
        
        # 测试多个人类玩家 - 使用validate_for_game_start方法
        try:
            config = GameConfig(players=[
                PlayerConfig(seat=0, type="human"),
                PlayerConfig(seat=1, type="human")
            ])
            config.validate_for_game_start()  # 这里应该抛出异常
            assert False, "多个人类玩家应该抛出异常"
        except ValueError:
            pass
        
        print("[OK] 玩家验证测试通过")
    
    def test_ai_settings(self):
        """测试AI设置"""
        print("测试AI设置...")
        
        config = GameConfig()
        
        # 验证默认AI设置
        assert "gemini" in config.ai_settings, "应该有gemini设置"
        assert "chatgpt" in config.ai_settings, "应该有chatgpt设置"
        
        gemini_settings = config.ai_settings["gemini"]
        assert gemini_settings["model"] == "gemini-pro", "gemini模型应该正确"
        assert gemini_settings["temperature"] == 0.7, "temperature应该正确"
        
        chatgpt_settings = config.ai_settings["chatgpt"]
        assert chatgpt_settings["model"] == "gpt-4", "chatgpt模型应该正确"
        assert chatgpt_settings["temperature"] == 0.7, "temperature应该正确"
        
        print("[OK] AI设置测试通过")


def run_tests():
    """运行所有测试"""
    print("=== 游戏配置单元测试 ===\n")
    
    player_config_test = TestPlayerConfig()
    game_config_test = TestGameConfig()
    
    test_methods = [
        ("玩家配置创建", player_config_test.test_player_config_creation),
        ("玩家配置默认名称", player_config_test.test_player_config_default_names),
        ("玩家配置验证", player_config_test.test_player_config_validation),
        ("游戏配置创建", game_config_test.test_game_config_creation),
        ("默认4人游戏配置", game_config_test.test_default_4_player_config),
        ("默认单挑游戏配置", game_config_test.test_default_heads_up_config),
        ("游戏配置验证", game_config_test.test_game_config_validation),
        ("添加玩家", game_config_test.test_add_player),
        ("玩家验证", game_config_test.test_player_validation),
        ("AI设置", game_config_test.test_ai_settings),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in test_methods:
        try:
            test_func()
            print(f"[OK] {test_name}测试通过\n")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test_name}测试失败: {e}\n")
            failed += 1
    
    print(f"测试结果: {passed}通过, {failed}失败")
    
    if failed == 0:
        print("[SUCCESS] 所有游戏配置测试通过！")
        return True
    else:
        print("[ERROR] 部分测试失败，需要修复")
        return False


if __name__ == "__main__":
    run_tests() 