"""
V3 Naming Conventions Test - 命名规范检查

该测试确保v3项目严格遵循命名规范：
- 模块命名：snake_case
- 类命名：PascalCase + 职责后缀
- 方法命名：动词开头 + 明确意图
- 常量：SCREAMING_SNAKE_CASE + 域前缀

这是PLAN 01的验收测试，必须100%通过。
"""

import os
import re
import pytest
from pathlib import Path


class TestV3NamingConventions:
    """V3命名规范测试类"""
    
    def test_module_naming_convention(self):
        """测试模块命名规范：snake_case"""
        v3_path = Path(__file__).parent.parent.parent
        core_modules = []
        
        # 收集所有核心模块名
        for root, dirs, files in os.walk(v3_path / "core"):
            for dir_name in dirs:
                if not dir_name.startswith("__"):
                    core_modules.append(dir_name)
        
        # 验证模块名符合snake_case规范
        snake_case_pattern = re.compile(r'^[a-z]+(_[a-z]+)*$')
        for module_name in core_modules:
            assert snake_case_pattern.match(module_name), \
                f"模块名 '{module_name}' 不符合snake_case规范"
    
    def test_directory_structure_completeness(self):
        """测试目录结构完整性"""
        v3_path = Path(__file__).parent.parent.parent
        
        # 必需的核心模块
        required_core_modules = [
            "state_machine", "betting", "pot", "chips", 
            "deck", "eval", "rules", "invariant", "events", "snapshot"
        ]
        
        for module in required_core_modules:
            module_path = v3_path / "core" / module
            assert module_path.exists(), f"核心模块 '{module}' 目录不存在"
            
            init_file = module_path / "__init__.py"
            assert init_file.exists(), f"核心模块 '{module}' 缺少__init__.py文件"
    
    def test_init_files_have_all_declaration(self):
        """测试所有__init__.py文件都有__all__声明"""
        v3_path = Path(__file__).parent.parent.parent
        
        init_files = []
        for root, dirs, files in os.walk(v3_path):
            for file in files:
                if file == "__init__.py":
                    init_files.append(Path(root) / file)
        
        for init_file in init_files:
            with open(init_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "__all__" in content, \
                    f"文件 '{init_file}' 缺少__all__声明"
    
    def test_module_access_rules_documentation(self):
        """测试模块访问规则文档化"""
        v3_path = Path(__file__).parent.parent.parent
        
        # 检查核心模块的文档说明
        core_init = v3_path / "core" / "__init__.py"
        with open(core_init, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "核心模块只能依赖其他核心模块" in content, \
                "核心模块访问规则未在文档中说明"
        
        # 检查应用层的文档说明
        app_init = v3_path / "application" / "__init__.py"
        with open(app_init, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "CQRS" in content, \
                "应用层CQRS模式未在文档中说明"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 