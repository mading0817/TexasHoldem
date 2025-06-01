"""
Documentation configuration for Texas Hold'em Poker Game v2.

This configuration file sets up pdoc for generating API documentation
with Google-style docstrings.

Updated to use modular documentation generation:
- Command: pdoc -o docs -d google v2.core v2.controller v2.ui
- Output: docs/v2/ (single layer, no double v2/v2/ structure)
- GitHub Pages ready with .nojekyll file
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('..'))

# pdoc configuration
docformat = "google"

# Project information
project = "Texas Hold'em Poker Game v2"
author = "Texas Hold'em Development Team"
version = "0.2.0-alpha"

# Documentation settings
html_title = f"{project} v{version} Documentation"
html_show_source = True
html_show_inheritance = True

# Module discovery - 现在使用模块化生成方式
# 使用命令: pdoc -o docs -d google v2.core v2.controller v2.ui
modules = [
    "v2.core",
    "v2.controller", 
    "v2.ui"
] 

# GitHub Pages 配置
# - 输出目录: docs/
# - 禁用Jekyll: .nojekyll 文件
# - 访问路径: /v2/core.html, /v2/controller.html, /v2/ui.html 