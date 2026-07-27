"""应用配置 —— 从项目根 .env 读取，单用户 v0。"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/outfit_ai/config.py -> project root
_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MiniMax（识图 + 文本，复用 mmx CLI 同一把 key）
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimaxi.com/v1"
    minimax_model: str = "MiniMax-M3"

    # 存储
    database_url: str = "sqlite:///./data/outfit_ai.db"
    upload_dir: str = "./data/uploads"
    max_image_bytes: int = 10 * 1024 * 1024  # MiniMax 单图上限 10MB

    # 运行时
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    user_id: str = "local"  # v0 单用户占位

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
