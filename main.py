#!/usr/bin/env python3
"""
五子棋 (Gomoku) — 启动入口

Requires: Python 3.8+, pygame
Run:  python main.py
"""

import sys
import os

# Ensure the game module can be found
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Check for pygame
try:
    import pygame
except ImportError:
    print("=" * 60)
    print("  错误：需要 pygame 库")
    print("  请运行:  pip install pygame")
    print("=" * 60)
    sys.exit(1)

from gomoku_game import Game

if __name__ == "__main__":
    Game().run()
