"""
Minervini Screener v1.0 - In-memory Scan Result Cache
Caches screen_all() results to avoid re-running the full scan on every API request.
"""
from datetime import datetime, timedelta
from typing import Optional
from core.logging_setup import get_logger

logger = get_logger(__name__)

_scan_cache: list[dict] = []
_scan_cache_time: Optional[datetime] = None
_scan_cache_ttl = timedelta(minutes=5)  # Cache TTL


async def get_scan_results(force_refresh: bool = False) -> list[dict]:
    """Get scan results, refreshing from DB if cache is stale."""
    global _scan_cache, _scan_cache_time

    now = datetime.now()
    if not force_refresh and _scan_cache_time and (now - _scan_cache_time) < _scan_cache_ttl:
        logger.debug(f"Returning {len(_scan_cache)} cached scan results")
        return _scan_cache

    # Cache miss or expired — run scan
    from data.downloader import DataDownloader
    downloader = DataDownloader()
    results = await downloader.screen_all()

    _scan_cache = results
    _scan_cache_time = now
    logger.info(f"Scan cache refreshed: {len(results)} results")
    return results


def invalidate_cache():
    """Force cache refresh on next request."""
    global _scan_cache_time
    _scan_cache_time = None
    logger.debug("Scan cache invalidated")
