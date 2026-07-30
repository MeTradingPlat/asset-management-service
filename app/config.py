from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    http_port: int = 8086
    http_host: str = "0.0.0.0"

    db_host: str = "postgres-historical"
    db_port: int = 5432
    db_name: str = "bd_historical"
    db_user: str = "user_historical"
    db_password: str = ""

    marketdata_url: str = "http://marketdata-service:8082"

    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""
    alpaca_base_url: str = "https://data.alpaca.markets"
    alpaca_calls_per_minute: int = 200
    alpaca_symbols_per_call: int = 100

    scheduler_tick_seconds: int = 30

    log_level: str = "INFO"

    class Config:
        env_prefix = "HD_"


settings = Settings()
