"""
Minervini Screener v1.0 - Strategy Package

This package re-exports the SEPA (Specific Entry Point Analysis) strategy
from core.sepa for backward compatibility. All strategy logic lives in
core/sepa.py, core/breakout.py, core/stoploss.py, and core/portfolio.py.

Usage:
    from strategy import run_sepa, StrategyResult
"""

from core.sepa import run_sepa, StrategyResult

__all__ = ["run_sepa", "StrategyResult"]
