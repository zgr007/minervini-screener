"""
Stock name resolution for CN and US stocks.
CN names from pre-generated cn_stocks.json; US names via yfinance lookup.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CN_STOCKS_FILE = Path("data/cn_stocks.json")
_cn_name_map: dict[str, str] = {}  # code -> name


def _load_cn_map():
    """Load CN stock names from JSON into memory."""
    if _cn_name_map:
        return
    try:
        if _CN_STOCKS_FILE.exists():
            records = json.loads(_CN_STOCKS_FILE.read_text(encoding="utf-8"))
            for r in records:
                _cn_name_map[r["code"]] = r["name"]
            logger.info(f"Loaded {len(_cn_name_map)} CN stock names")
    except Exception as e:
        logger.error(f"Failed to load CN stock names: {e}")


def resolve_name(symbol: str, market: str) -> str:
    """Get the display name for a stock symbol."""
    if market == "CN":
        _load_cn_map()
        return _cn_name_map.get(symbol, symbol)
    # For US, try yfinance (non-blocking callers handle this)
    return symbol  # fallback — caller can override with yfinance result


def resolve_name_yf(symbol: str) -> str:
    """Look up US stock name via yfinance. May block briefly."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info
        name = info.get("shortName") or info.get("longName") or ""
        if name and "N/A" not in str(name):
            return name.strip()
    except Exception:
        pass
    return symbol
