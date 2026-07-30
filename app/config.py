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
    # Alpaca no limita cantidad de simbolos por llamada, solo 10,000 filas
    # por pagina (confirmado en vivo). Para backfill profundo (7 anios de
    # D1 por simbolo) esas 10k filas se agotan con ~10-12 simbolos sin
    # importar cuantos se pidan, asi que un lote grande no ayuda -- se deja
    # moderado. Para refresco incremental (solo 3 dias) 1500 simbolos caben
    # completos en una sola pagina sin paginar, confirmado en vivo -- un
    # lote grande ahi reduce las llamadas necesarias en un orden de
    # magnitud.
    alpaca_symbols_per_call_backfill: int = 100
    alpaca_symbols_per_call_steady_state: int = 1000

    scheduler_tick_seconds: int = 30

    log_level: str = "INFO"

    class Config:
        env_prefix = "HD_"


settings = Settings()
