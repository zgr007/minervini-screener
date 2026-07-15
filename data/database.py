"""
Minervini Screener v1.0 - Database Models & Session Management
SQLAlchemy 2.x async models for all 13 tables.
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import AsyncGenerator, Optional

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Date, Text,
    ForeignKey, Numeric, Enum as SAEnum, UniqueConstraint, Index,
    create_engine, event,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from config.loader import settings


class Base(DeclarativeBase):
    pass


# ---------- Stocks ----------
class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(200))
    exchange: Mapped[Optional[str]] = mapped_column(String(50))
    market: Mapped[str] = mapped_column(String(10), default="US")  # US, CN, HK
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    market_cap: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[Optional[str]] = mapped_column(String(10))
    asset_type: Mapped[Optional[str]] = mapped_column(String(20), default="stock")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("symbol", "market", name="uq_stock_symbol_market"),
        Index("idx_stock_market_active", "market", "is_active"),
    )


# ---------- Daily Bars ----------
class DailyBar(Base):
    __tablename__ = "daily_bars"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    market: Mapped[str] = mapped_column(String(10), default="US")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    adjusted_close: Mapped[Optional[float]] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_bar_symbol_date"),
        Index("idx_bar_date", "trade_date"),
        Index("idx_bar_symbol_date", "symbol", "trade_date"),
    )


# ---------- Indicators ----------
class Indicator(Base):
    __tablename__ = "indicators"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    # MAs
    ma_10: Mapped[Optional[float]] = mapped_column(Float)
    ma_50: Mapped[Optional[float]] = mapped_column(Float)
    ma_150: Mapped[Optional[float]] = mapped_column(Float)
    ma_200: Mapped[Optional[float]] = mapped_column(Float)
    # 52-week high/low
    high_52w: Mapped[Optional[float]] = mapped_column(Float)
    low_52w: Mapped[Optional[float]] = mapped_column(Float)
    pct_from_high: Mapped[Optional[float]] = mapped_column(Float)
    pct_from_low: Mapped[Optional[float]] = mapped_column(Float)
    # RS
    rs_percentile: Mapped[Optional[float]] = mapped_column(Float)
    # Volume MAs
    avg_volume_20: Mapped[Optional[float]] = mapped_column(Float)
    avg_volume_50: Mapped[Optional[float]] = mapped_column(Float)
    # Bollinger
    boll_mid: Mapped[Optional[float]] = mapped_column(Float)
    boll_upper: Mapped[Optional[float]] = mapped_column(Float)
    boll_lower: Mapped[Optional[float]] = mapped_column(Float)
    boll_width: Mapped[Optional[float]] = mapped_column(Float)
    # ATR
    atr_14: Mapped[Optional[float]] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_indicator_symbol_date"),
        Index("idx_indicator_date", "trade_date"),
    )


# ---------- Fundamentals ----------
class Fundamental(Base):
    __tablename__ = "fundamentals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    eps_growth_yoy: Mapped[Optional[float]] = mapped_column(Float)
    revenue_growth_yoy: Mapped[Optional[float]] = mapped_column(Float)
    revenue_growth_acceleration: Mapped[Optional[bool]] = mapped_column(Boolean)
    roe: Mapped[Optional[float]] = mapped_column(Float)
    catalyst_note: Mapped[Optional[str]] = mapped_column(Text)
    score: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("symbol", "report_date", name="uq_fund_symbol_date"),
    )


# ---------- Institutional Data ----------
class InstitutionalData(Base):
    __tablename__ = "institutional_data"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    holder_count_change: Mapped[Optional[float]] = mapped_column(Float)
    institution_position_change: Mapped[Optional[float]] = mapped_column(Float)
    abnormal_volume_note: Mapped[Optional[str]] = mapped_column(Text)
    score: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("symbol", "report_date", name="uq_inst_symbol_date"),
    )


# ---------- Screen Results ----------
class ScreenResult(Base):
    __tablename__ = "screen_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    market: Mapped[str] = mapped_column(String(10), default="US")
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(200))
    price: Mapped[Optional[float]] = mapped_column(Float)
    trend_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    rs_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    rs_percentile: Mapped[Optional[float]] = mapped_column(Float)
    pct_from_high: Mapped[Optional[float]] = mapped_column(Float)
    fundamental_score: Mapped[Optional[float]] = mapped_column(Float)
    institutional_score: Mapped[Optional[float]] = mapped_column(Float)
    total_score: Mapped[Optional[float]] = mapped_column(Float)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    risk_warning: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_screen_run", "run_date", "market"),
        Index("idx_screen_selected", "selected"),
    )


# ---------- Patterns ----------
class Pattern(Base):
    __tablename__ = "patterns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    detected_date: Mapped[date] = mapped_column(Date, nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(30))  # vcp, cup_handle, flat_base, double_bottom, bollinger
    pivot_price: Mapped[Optional[float]] = mapped_column(Float)
    pattern_low: Mapped[Optional[float]] = mapped_column(Float)
    stop_price: Mapped[Optional[float]] = mapped_column(Float)
    target_price: Mapped[Optional[float]] = mapped_column(Float)
    confidence: Mapped[Optional[str]] = mapped_column(String(20))  # high, medium, low
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, triggered, expired
    reason: Mapped[Optional[str]] = mapped_column(Text)
    detail_json: Mapped[Optional[str]] = mapped_column(Text)  # JSON blob with full pattern data
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_pattern_symbol_type", "symbol", "pattern_type"),
    )


# ---------- Watchlist ----------
class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(200))
    added_date: Mapped[date] = mapped_column(Date, default=date.today)
    source: Mapped[Optional[str]] = mapped_column(String(50))  # screen, manual, rs
    pattern_id: Mapped[Optional[str]] = mapped_column(String(36))
    pivot_price: Mapped[Optional[float]] = mapped_column(Float)
    stop_price: Mapped[Optional[float]] = mapped_column(Float)
    pct_from_pivot: Mapped[Optional[float]] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="observing")  # observing, near_pivot, triggered, expired, bought
    note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("symbol", name="uq_watchlist_symbol"),
    )


# ---------- Signals ----------
class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    signal_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    signal_type: Mapped[str] = mapped_column(String(30))  # buy, sell, stop_loss, trailing_stop, top_signal
    direction: Mapped[str] = mapped_column(String(10))  # buy, sell
    price: Mapped[Optional[float]] = mapped_column(Float)
    volume_confirmed: Mapped[Optional[bool]] = mapped_column(Boolean)
    market_confirmed: Mapped[Optional[bool]] = mapped_column(Boolean)
    risk_confirmed: Mapped[Optional[bool]] = mapped_column(Boolean)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, executed, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------- Positions ----------
class Position(Base):
    __tablename__ = "positions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    average_cost: Mapped[float] = mapped_column(Float)
    current_stop: Mapped[Optional[float]] = mapped_column(Float)
    initial_stop: Mapped[Optional[float]] = mapped_column(Float)
    highest_price: Mapped[Optional[float]] = mapped_column(Float)
    pattern_type: Mapped[Optional[str]] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="open")  # open, closed
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ---------- Orders ----------
class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10))  # buy, sell
    order_type: Mapped[str] = mapped_column(String(20))  # market, limit, stop, stop_limit
    quantity: Mapped[int] = mapped_column(Integer)
    limit_price: Mapped[Optional[float]] = mapped_column(Float)
    stop_price: Mapped[Optional[float]] = mapped_column(Float)
    filled_price: Mapped[Optional[float]] = mapped_column(Float)
    filled_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, filled, partial, cancelled, rejected
    signal_id: Mapped[Optional[str]] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ---------- Trades ----------
class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(String(10))  # buy, sell
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    pnl: Mapped[Optional[float]] = mapped_column(Float)
    trade_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    order_id: Mapped[Optional[str]] = mapped_column(String(36))
    note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_trade_symbol_time", "symbol", "trade_time"),
    )


# ---------- Review Logs ----------
class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_date: Mapped[date] = mapped_column(Date, default=date.today)
    symbol: Mapped[Optional[str]] = mapped_column(String(20))
    trade_id: Mapped[Optional[str]] = mapped_column(String(36))
    rule_followed: Mapped[bool] = mapped_column(Boolean, default=True)
    mistake_type: Mapped[Optional[str]] = mapped_column(String(50))
    lesson: Mapped[Optional[str]] = mapped_column(Text)
    screenshot_path: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_review_date", "review_date"),
    )


# ---------- Async Engine & Session ----------
def get_db_url() -> str:
    """Get database URL, defaulting to SQLite for local dev."""
    from os import getenv
    env_url = getenv("DATABASE_URL")
    if env_url:
        # Convert postgresql:// to postgresql+asyncpg:// for async
        if env_url.startswith("postgresql://") and "+asyncpg" not in env_url:
            return env_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return env_url
    return f"sqlite+aiosqlite:///{settings.database.sqlite_path}"


engine = create_async_engine(get_db_url(), echo=settings.database.echo_sql, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables (for local dev with SQLite)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
