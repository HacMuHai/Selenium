"""
Settings - nguồn cấu hình DUY NHẤT của toàn bộ ứng dụng.

Đọc từ biến môi trường / file `.env` ở repo root. Mọi module khác lấy config qua
`get_settings()`, KHÔNG dùng `os.getenv` rải rác.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình ứng dụng, nạp từ `.env` hoặc biến môi trường."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # MongoDB
    mongo_uri: str
    mongo_db: str = "selenium_scraper"
    # GIỮ tên collection cũ ("comments" nhưng thực chất chứa product) - không migrate
    mongo_collection: str = "comments"

    # Logging
    log_level: str = "INFO"

    # Selenium
    headless: bool = True
    max_workers: int = 3
    wait_timeout: float = 15.0

    # Export
    export_dir: str = "data"
    max_rows_per_file: int = 2000

    # Phân tích cảm xúc
    models_dir: str = "models_store"
    tag_dir: str = "data_tagged"       # nguồn nhãn ĐÃ LÀM SẠCH (gốc: excel_tag_v2, xem outdated/)
    default_model: str = "svm"
    test_size: float = 0.2
    random_seed: int = 42


@lru_cache
def get_settings() -> Settings:
    """Trả về Settings singleton (cache theo process)."""
    return Settings()  # type: ignore[call-arg]  # giá trị đến từ .env
