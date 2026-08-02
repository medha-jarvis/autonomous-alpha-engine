"""
Alpha Engine Configuration
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH: Path = Path("/opt/data/alpha-engine/.env")
load_dotenv(dotenv_path=ENV_PATH, override=True)


@dataclass(frozen=True)
class Config:
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek/deepseek-v4-flash")
    r2_account_id: str = os.getenv("R2_ACCOUNT_ID", "")
    r2_access_key_id: str = os.getenv("R2_ACCESS_KEY_ID", "")
    r2_secret_access_key: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    r2_token_value: str = os.getenv("R2_TOKEN_VALUE", "")
    r2_bucket_name: str = os.getenv("R2_BUCKET_NAME", "concall-alpha-engine")
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "7117734948")
    typesense_host: str = os.getenv("TYPESENSE_HOST", "localhost")
    typesense_port: int = int(os.getenv("TYPESENSE_PORT", "8108"))
    typesense_api_key: str = os.getenv("TYPESENSE_API_KEY", "HermesInvestSearchKey2026")
    typesense_protocol: str = os.getenv("TYPESENSE_PROTOCOL", "http")
    bse_poll_interval_minutes: int = int(os.getenv("BSE_POLL_INTERVAL_MINUTES", "15"))
    data_dir: str = os.getenv("ALPHA_ENGINE_DATA_DIR", "/opt/data/alpha-engine")

    @property
    def r2_endpoint(self) -> str:
        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"

    @property
    def portfolio_stocks(self) -> dict[str, str]:
        return {
            "INTERARCH": "544195", "SAGILITY": "543672", "KAYNES": "543788",
            "REDINGTON": "532805", "KALYANKJIL": "543918", "AAVAS": "541771",
            "ANGELONE": "543235", "ASTRAL": "532830", "BAJAJELEC": "543768",
            "BHARATFORG": "500493", "BLUESTARCO": "532659", "BSE": "543232",
            "CESC": "500084", "COFORGE": "543276", "DIXON": "540499",
            "DREAMFOLK": "543591", "GODREJCP": "532424", "HAL": "541154",
            "HCLTECH": "532281", "HDFCBANK": "500180", "ICICIBANK": "532174",
            "INFY": "500209", "IRFC": "543257", "LT": "500510",
            "MCDOWELL-N": "532320", "MOTHERSON": "532574", "PCBL": "506590",
            "RADICO": "532497", "RELAXO": "530517", "TATACONSUM": "504800",
            "ZOMATO": "543320",
        }


config: Config = Config()


def lookup_scrip_code(ticker: str) -> str | None:
    return config.portfolio_stocks.get(ticker.upper())
