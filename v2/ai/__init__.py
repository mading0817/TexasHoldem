"""
AI strategies for Texas Hold'em poker game v2.

This package provides AI strategy implementations that work with the v2 controller.
"""

from .base import AIStrategy
from .simple_ai import SimpleAI, SimpleAIConfig

__all__ = ['AIStrategy', 'SimpleAI', 'SimpleAIConfig'] 