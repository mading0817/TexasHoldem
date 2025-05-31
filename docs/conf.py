"""
Documentation configuration for Texas Hold'em Poker Game v2.

This configuration file sets up pdoc for generating API documentation
with Google-style docstrings.
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

# Module discovery
modules = [
    "v2.core",
    "v2.controller", 
    "v2.ui"
] 