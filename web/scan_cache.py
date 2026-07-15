"""
Minervini Screener v1.0 - Scan Result Cache (DB-backed)
Reads from screen_results DB table. Falls back to empty list if no data yet.
Never blocks waiting for a full scan — the scan runs as a background task.
"""
from datetime import datetime, timedelta
from typing import Optional
from core.logging_setup import get_logger

logger = get_logger(__name__)

_scan_cache: list[dict] = []
_scan_cache_time: Optional[datetime] = None
_scan_cache_ttl = timedelta(minutes=5)


async def get_scan_results(force_refresh: bool = False) -> list[dict]:
    """Get scan results: from cache → DB screen_results table → empty list.

    NEVER calls screen_all() directly — that would block the HTTP request
    for 30+ minutes. The scan must be triggered separately via scheduler
    or /screen/run endpoint.

    Special case: when cache is empty, skip TTL and always re-read DB.
    This ensures dashboard picks up data as soon as the background scan
    finishes writing to screen_results table.
    """
    global _scan_cache, _scan_cache_time

    now = datetime.now()
    use_cache = (
        not force_refresh
        and _scan_cache_time
        and (now - _scan_cache_time) < _scan_cache_ttl
        and len(_scan_cache) > 0  # Don't cache empty results
    )
    if use_cache:
        logger.debug(f"Returning {len(_scan_cache)} cached scan results")
        return _scan_cache

    # Cache miss or empty — read from DB screen_results table
    results = await _load_from_db()

    _scan_cache = results
    _scan_cache_time = now
    logger.info(f"Scan cache loaded from DB: {len(results)} results")
    return results


async def _load_from_db() -> list[dict]:
    """Load scan results from the screen_results DB table."""
    try:
        from data.database import async_session_factory, ScreenResult
        from sqlalchemy import select

        async with async_session_factory() as session:
            stmt = (
                select(ScreenResult)
                .order_by(ScreenResult.total_score.desc().nullslast())
                .limit(5000)
            )
            rows = (await session.execute(stmt)).scalars().all()

        if not rows:
            logger.debug("screen_results table is empty — returning []")
            return []

        results = []
        for r in rows:
            results.append({
                "code": r.symbol,
                "name": r.name or "",
                "signal": "buy" if r.selected else "watch" if r.trend_passed else "no_entry",
                "score": r.total_score or 0,
                "stage2": r.trend_passed or False,
                "rs_rating": r.rs_percentile or (80 if r.rs_passed else 0),
                "rs_rank": int(r.rs_percentile) if r.rs_percentile else 0,
                "pattern": {"detected": False},
                "breakout": {},
                "stop_loss": {},
                "reason": r.reason or "",
                "current_price": r.price or 0,
            })
        return results
    except Exception as e:
        logger.error(f"Failed to load scan results from DB: {e}", exc_info=True)
        return []


def invalidate_cache():
    """Force cache refresh from DB on next request."""
    global _scan_cache_time
    _scan_cache_time = None
    logger.debug("Scan cache invalidated")
