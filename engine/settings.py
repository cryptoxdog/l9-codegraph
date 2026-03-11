"""
CRM AI Platform — Central Configuration
All environment-driven. No secrets in code.
"""
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class DatabaseConfig:
    host: str = os.getenv("CRM_DB_HOST", "localhost")
    port: int = int(os.getenv("CRM_DB_PORT", "5432"))
    name: str = os.getenv("CRM_DB_NAME", "crm_ai")
    user: str = os.getenv("CRM_DB_USER", "crm_service")
    password: str = os.getenv("CRM_DB_PASSWORD", "")
    pool_min: int = int(os.getenv("CRM_DB_POOL_MIN", "2"))
    pool_max: int = int(os.getenv("CRM_DB_POOL_MAX", "10"))
    statement_timeout_ms: int = int(os.getenv("CRM_DB_TIMEOUT_MS", "30000"))

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass(frozen=True)
class GoogleAdsConfig:
    developer_token: str = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
    client_id: str = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
    client_secret: str = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
    refresh_token: str = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
    login_customer_id: str = os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")
    customer_id: str = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
    conversion_action_id: str = os.getenv("GOOGLE_ADS_CONVERSION_ACTION_ID", "")
    api_version: str = os.getenv("GOOGLE_ADS_API_VERSION", "v17")


@dataclass(frozen=True)
class SalesforceConfig:
    instance_url: str = os.getenv("SF_INSTANCE_URL", "")
    client_id: str = os.getenv("SF_CLIENT_ID", "")
    client_secret: str = os.getenv("SF_CLIENT_SECRET", "")
    username: str = os.getenv("SF_USERNAME", "")
    password: str = os.getenv("SF_PASSWORD", "")
    security_token: str = os.getenv("SF_SECURITY_TOKEN", "")
    api_version: str = os.getenv("SF_API_VERSION", "v60.0")
    data_cloud_endpoint: str = os.getenv("SF_DATA_CLOUD_ENDPOINT", "")


@dataclass(frozen=True)
class QualityConfig:
    min_export_score: float = float(os.getenv("CRM_MIN_EXPORT_SCORE", "60"))
    min_match_score: float = float(os.getenv("CRM_MIN_MATCH_SCORE", "70"))
    stale_days_threshold: int = int(os.getenv("CRM_STALE_DAYS", "365"))
    duplicate_similarity_threshold: float = float(os.getenv("CRM_DUPE_THRESHOLD", "0.85"))
    max_duplicate_batch: int = int(os.getenv("CRM_MAX_DUPE_BATCH", "5000"))
    email_verification_enabled: bool = os.getenv("CRM_EMAIL_VERIFY", "true").lower() == "true"
    phone_verification_enabled: bool = os.getenv("CRM_PHONE_VERIFY", "true").lower() == "true"
    address_verification_enabled: bool = os.getenv("CRM_ADDR_VERIFY", "true").lower() == "true"


@dataclass(frozen=True)
class ExportConfig:
    enhanced_conversions_batch_size: int = int(os.getenv("CRM_EC_BATCH_SIZE", "2000"))
    enhanced_conversions_max_retries: int = int(os.getenv("CRM_EC_MAX_RETRIES", "5"))
    enhanced_conversions_retry_delay_s: int = int(os.getenv("CRM_EC_RETRY_DELAY", "300"))
    customer_match_batch_size: int = int(os.getenv("CRM_CM_BATCH_SIZE", "500000"))
    conversion_lookback_days: int = int(os.getenv("CRM_CONV_LOOKBACK_DAYS", "90"))
    export_lock_timeout_s: int = int(os.getenv("CRM_EXPORT_LOCK_TIMEOUT", "600"))


@dataclass(frozen=True)
class ObservabilityConfig:
    log_level: str = os.getenv("CRM_LOG_LEVEL", "INFO")
    metrics_enabled: bool = os.getenv("CRM_METRICS_ENABLED", "true").lower() == "true"
    metrics_prefix: str = os.getenv("CRM_METRICS_PREFIX", "crm_ai")
    alert_webhook_url: str = os.getenv("CRM_ALERT_WEBHOOK", "")
    alert_on_quality_drop: float = float(os.getenv("CRM_ALERT_QUALITY_THRESHOLD", "70"))
    alert_on_match_rate_drop: float = float(os.getenv("CRM_ALERT_MATCH_THRESHOLD", "40"))


@dataclass(frozen=True)
class PlatformConfig:
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    google_ads: GoogleAdsConfig = field(default_factory=GoogleAdsConfig)
    salesforce: SalesforceConfig = field(default_factory=SalesforceConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    default_country: str = os.getenv("CRM_DEFAULT_COUNTRY", "US")
    default_currency: str = os.getenv("CRM_DEFAULT_CURRENCY", "USD")
    default_timezone: str = os.getenv("CRM_DEFAULT_TIMEZONE", "America/New_York")


def load_config() -> PlatformConfig:
    return PlatformConfig()
