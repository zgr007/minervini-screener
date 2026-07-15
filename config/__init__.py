"""
Configuration package for Minervini Screener.

Usage:
    from config import settings
    from config.loader import Settings
"""

from config.loader import Settings, settings

__all__ = ["Settings", "settings"]

