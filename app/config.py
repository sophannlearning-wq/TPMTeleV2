import os
from dataclasses import dataclass

def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url

@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    timezone: str = "Asia/Phnom_Penh"
    data_dir: str = "data"
    bootstrap_admin_staff_id: str = "90024252"
    bootstrap_admin_name: str = "Sophann EN"

def load_settings() -> Settings:
    token=os.getenv("BOT_TOKEN","").strip()
    database=os.getenv("DATABASE_URL","").strip()
    if not token: raise RuntimeError("BOT_TOKEN is missing")
    if not database: raise RuntimeError("DATABASE_URL is missing")
    return Settings(token,normalize_database_url(database),os.getenv("TIMEZONE","Asia/Phnom_Penh"),os.getenv("DATA_DIR","data"),os.getenv("BOOTSTRAP_ADMIN_STAFF_ID","90024252"),os.getenv("BOOTSTRAP_ADMIN_NAME","Sophann EN"))
