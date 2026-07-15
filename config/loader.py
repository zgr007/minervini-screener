"""
Minervini Screener v1.0 - Configuration Loader
Pydantic-based settings with YAML + .env override support.
"""
import os
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class AppConfig(BaseSettings):
    name: str = "Minervini Screener"
    version: str = "1.0.0"
    debug: bool = True
    log_level: str = "INFO"
    log_format: str = "console"  # json or console


class DatabaseConfig(BaseSettings):
    pool_size: int = 10
    max_overflow: int = 20
    echo_sql: bool = False
    sqlite_path: str = "data/minervini.db"


class RedisConfig(BaseSettings):
    socket_timeout: int = 5
    max_connections: int = 20


class MarketDef(BaseSettings):
    name: str = ""
    timezone: str = ""
    currency: str = ""
    trading_days: str = "Mon-Fri"
    data_source: str = ""
    default_tickers: List[str] = []


class MarketConfig(BaseSettings):
    default: str = "US"
    markets: Dict[str, MarketDef] = {}


class DataConfig(BaseSettings):
    max_retries: int = 3
    retry_delay_seconds: int = 5
    request_timeout: int = 30
    min_days_required: int = 252
    quality_checks: Dict[str, Any] = {
        "max_missing_pct": 0.1,
        "max_zero_volume_days": 5,
        "max_price_gap_pct": 50.0,
    }


class MAConfig(BaseSettings):
    periods: List[int] = [10, 50, 150, 200]


class RSConfig(BaseSettings):
    periods_months: List[int] = [3, 6, 12]
    weights: List[float] = [0.4, 0.35, 0.25]


class VolumeConfig(BaseSettings):
    sma_periods: List[int] = [20, 50]


class BollingerConfig(BaseSettings):
    period: int = 20
    std_multiplier: float = 2.0


class ATRConfig(BaseSettings):
    period: int = 14


class IndicatorConfig(BaseSettings):
    ma: MAConfig = MAConfig()
    rs: RSConfig = RSConfig()
    volume: VolumeConfig = VolumeConfig()
    bollinger: BollingerConfig = BollingerConfig()
    atr: ATRConfig = ATRConfig()


class Stage2Config(BaseSettings):
    ma_fast_period: int = 10
    ma_mid_period: int = 50
    ma_long_period: int = 150
    ma_ultra_long_period: int = 200
    min_price_above_ma200_pct: float = 0.0
    min_rise_from_52w_low_pct: float = 30.0


class EPSGrowthConfig(BaseSettings):
    threshold_25: float = 25.0
    threshold_50: float = 50.0
    threshold_100: float = 100.0
    score_0: int = 0
    score_25: int = 2
    score_50: int = 3
    score_100: int = 4


class RevenueGrowthConfig(BaseSettings):
    threshold: float = 10.0
    max_score: int = 3


class ROEConfig(BaseSettings):
    threshold: float = 17.0
    max_score: int = 2


class CatalystConfig(BaseSettings):
    max_score: int = 1


class ScoringConfig(BaseSettings):
    eps_growth_yoy: EPSGrowthConfig = EPSGrowthConfig()
    revenue_growth: RevenueGrowthConfig = RevenueGrowthConfig()
    roe: ROEConfig = ROEConfig()
    catalyst: CatalystConfig = CatalystConfig()


class FundamentalConfig(BaseSettings):
    enabled: bool = True
    min_total_score: int = 6
    scoring: ScoringConfig = ScoringConfig()


class InstitutionalConfig(BaseSettings):
    enabled: bool = True
    is_mandatory: bool = False
    scoring: Dict[str, Any] = {
        "holder_decrease_threshold": -0.05,
        "position_increase_threshold": 0.05,
        "volume_accumulation_threshold": 1.5,
    }


class ScreeningConfig(BaseSettings):
    stage2: Stage2Config = Stage2Config()
    rs: Dict[str, Any] = {"min_percentile": 80, "near_high_52w_threshold_pct": 15.0}
    fundamental: FundamentalConfig = FundamentalConfig()
    institutional: InstitutionalConfig = InstitutionalConfig()


class VCPConfig(BaseSettings):
    min_contractions: int = 2
    max_contractions: int = 5
    contraction_decrease_required: bool = True
    volume_decline_required: bool = True
    stop_loss_pct_below_low: float = 0.08


class CupHandleConfig(BaseSettings):
    min_weeks: int = 6
    handle_weeks: List[int] = [1, 2]
    stop_loss_pct: float = 0.04


class FlatBaseConfig(BaseSettings):
    min_weeks: int = 3
    range_pct: List[float] = [5, 15]
    stop_loss_pct: float = 0.04


class DoubleBottomConfig(BaseSettings):
    min_gap_days: int = 10
    stop_loss_pct_below_second: float = 0.02


class BollingerSignalConfig(BaseSettings):
    band_width_contract_pct: float = 0.15
    volume_confirmation_multiplier: float = 1.5


class PatternConfig(BaseSettings):
    vcp: VCPConfig = VCPConfig()
    cup_handle: CupHandleConfig = CupHandleConfig()
    flat_base: FlatBaseConfig = FlatBaseConfig()
    double_bottom: DoubleBottomConfig = DoubleBottomConfig()
    bollinger: BollingerSignalConfig = BollingerSignalConfig()


class BuyConfig(BaseSettings):
    volume_multiplier: float = 1.5
    max_risk_per_trade_pct: float = 0.02
    initial_position_pct: float = 0.50
    add_position_days: List[int] = [2, 5]
    add_position_gain_pct: List[float] = [0.02, 0.05]


class StopLossConfig(BaseSettings):
    vcp_pct: float = 0.08
    cup_handle_pct: float = 0.04
    flat_base_pct: float = 0.04
    double_bottom_pct: float = 0.02
    hard_stop_pct: float = 0.02


class TrailingStopConfig(BaseSettings):
    profit_0_10: str = "initial_stop"
    profit_10_20: str = "breakeven"
    profit_20_30: str = "trail_15pct"
    profit_30_50: str = "trail_10pct"
    profit_50_plus: str = "trail_8pct"


class TopSignalConfig(BaseSettings):
    volume_stagnation_multiplier: float = 2.0
    volume_stagnation_gain_pct: float = 0.01
    below_50ma_pct: float = 0.02
    consecutive_down_days: int = 2
    target_profit_pct_1: float = 0.20
    target_profit_pct_2: float = 0.25
    target_profit_pct_exit: float = 0.30


class SellConfig(BaseSettings):
    stop_loss: StopLossConfig = StopLossConfig()
    trailing_stop: TrailingStopConfig = TrailingStopConfig()
    top_signals: TopSignalConfig = TopSignalConfig()


class BullConfig(BaseSettings):
    max_total_position_pct: float = 1.0
    max_single_position_pct: float = 0.25
    max_holdings: int = 6
    min_holdings: int = 3


class NeutralConfig(BaseSettings):
    max_total_position_pct: float = 0.60
    max_single_position_pct: float = 0.15
    max_holdings: int = 4
    min_holdings: int = 2


class BearConfig(BaseSettings):
    max_total_position_pct: float = 0.20
    max_single_position_pct: float = 0.05
    max_holdings: int = 2
    min_holdings: int = 0


class PortfolioConfig(BaseSettings):
    max_drawdown_pct: float = 0.15
    max_daily_loss_pct: float = 0.03
    min_cash_reserve_pct: float = 0.05
    max_correlation: float = 0.70


class RiskConfig(BaseSettings):
    market_phase: Dict[str, Any] = {}
    portfolio: PortfolioConfig = PortfolioConfig()
    forbidden: List[str] = [
        "averaging_down", "full_position_single_stock",
        "buying_weakness", "chasing_extended_breakouts",
        "no_stop_loss", "trading_missing_data",
        "trading_incomplete_signals",
    ]


class BacktestConfig(BaseSettings):
    default_initial_capital: float = 100000
    default_commission_pct: float = 0.001
    default_slippage_pct: float = 0.001
    min_trades_for_analysis: int = 10
    risk_free_rate: float = 0.05


class FeishuConfig(BaseSettings):
    enabled: bool = False
    webhook_url: str = ""


class TelegramConfig(BaseSettings):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class EmailConfig(BaseSettings):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_addr: str = ""
    to_addr: str = ""


class BarkConfig(BaseSettings):
    enabled: bool = False
    key: str = ""
    server: str = "https://api.day.app"


class WebhookConfig(BaseSettings):
    enabled: bool = False
    url: str = ""


class ConsoleConfig(BaseSettings):
    enabled: bool = True


class NotificationChannels(BaseSettings):
    console: ConsoleConfig = ConsoleConfig()
    feishu: FeishuConfig = FeishuConfig()
    telegram: TelegramConfig = TelegramConfig()
    email: EmailConfig = EmailConfig()
    bark: BarkConfig = BarkConfig()
    webhook: WebhookConfig = WebhookConfig()


class NotificationConfig(BaseSettings):
    channels: NotificationChannels = NotificationChannels()
    notify_on: List[str] = [
        "weekly_screen", "daily_watchlist_update", "near_pivot",
        "breakout_buy", "stop_loss_triggered", "trailing_stop_update",
        "top_sell_signal", "market_downturn", "data_update_failure",
    ]
    notify_format: Dict[str, Any] = {
        "include_reason": True, "include_price": True,
        "include_volume": True, "include_risk": True,
    }


class OpenAIConfig(BaseSettings):
    model: str = "gpt-4-turbo-preview"
    temperature: float = 0.3
    max_tokens: int = 2000


class OllamaConfig(BaseSettings):
    base_url: str = "http://localhost:11434"
    model: str = "llama2"


class AIConfig(BaseSettings):
    provider: str = "openai"
    openai: OpenAIConfig = OpenAIConfig()
    ollama: OllamaConfig = OllamaConfig()
    prompts: Dict[str, str] = {
        "stock_analysis": "analyze_stock_v1",
        "daily_report": "daily_report_v1",
    }


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app: AppConfig = AppConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    market: MarketConfig = MarketConfig()
    data: DataConfig = DataConfig()
    indicators: IndicatorConfig = IndicatorConfig()
    screening: ScreeningConfig = ScreeningConfig()
    patterns: PatternConfig = PatternConfig()
    signals: Dict[str, Any] = {}
    risk: RiskConfig = RiskConfig()
    backtest: BacktestConfig = BacktestConfig()
    notifications: NotificationConfig = NotificationConfig()
    ai: AIConfig = AIConfig()

    def load_yaml(self, path: str = "config.yaml") -> None:
        """Load YAML config file and overlay onto settings."""
        p = Path(path)
        if not p.exists():
            return
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return
        self._apply_yaml(data, self, "")

    def _apply_yaml(self, data: dict, obj: Any, prefix: str) -> None:
        """Recursively apply YAML dict to pydantic settings."""
        for key, value in data.items():
            if isinstance(value, dict) and hasattr(obj, key):
                child = getattr(obj, key)
                if hasattr(child, "model_fields"):
                    self._apply_yaml(value, child, f"{prefix}.{key}")
                else:
                    setattr(obj, key, value)
            elif hasattr(obj, key):
                setattr(obj, key, value)

    @property
    def db_url(self) -> str:
        """Get database URL from env or fall back to SQLite."""
        env_url = os.getenv("DATABASE_URL")
        if env_url:
            return env_url
        return f"sqlite+aiosqlite:///{self.database.sqlite_path}"

    @property
    def redis_url(self) -> str:
        env_url = os.getenv("REDIS_URL")
        return env_url or "redis://localhost:6379/0"

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url


settings = Settings()
settings.load_yaml()
