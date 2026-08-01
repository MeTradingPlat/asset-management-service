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
    # Cuantos lotes (llamadas a Alpaca) corren en paralelo POR hilo del
    # scheduler (backfill y steady-state cuentan por separado). El
    # TokenBucket compartido (rate_limiter.py) es thread-safe y se consulta
    # por pagina real, asi que subir esto nunca puede pasar las llamadas/min
    # configuradas -- solo evita que cada hilo quede bloqueado esperando UNA
    # respuesta de Alpaca (~10s) a la vez mientras el presupuesto real sigue
    # libre. En 1 (default) el comportamiento es igual al original: una
    # llamada en vuelo por hilo.
    scheduler_fetch_workers: int = 1
    # La escritura por simbolo dentro de un batch es espera de I/O (DB), no
    # CPU -- paralelizarla ayuda. db_pool_max_connections debe cubrir el
    # peor caso: 2 hilos del scheduler (backfill + steady-state) *
    # scheduler_fetch_workers lotes en vuelo cada uno *
    # scheduler_write_workers conexiones por lote, mas margen para la API
    # HTTP (routes_candles/routes_symbols) y symbol_poller, que comparten el
    # mismo pool.
    #
    # El host es de 4 cores compartido con otro proyecto entero (~15 JVMs
    # propias, sin ningun aislamiento de recursos) -- 6 workers x 2 hilos
    # del scheduler = hasta 12 conexiones Postgres activas a la vez
    # confirmado en produccion como demasiada concurrencia real para 4
    # cores (load average subiendo a 40+ sin bajar, ps mostrando varios
    # backends de Postgres compitiendo por CPU en COMMIT). Bajado a un
    # valor conservador: menos que el maximo posible, pero sigue siendo
    # mejor que el original 100% secuencial. Subir scheduler_fetch_workers
    # en vez de scheduler_write_workers cuando el host tenga mas margen --
    # el cuello de botella real es el fetch a Alpaca (~10s/llamada), no la
    # escritura.
    scheduler_write_workers: int = 2
    db_pool_max_connections: int = 8

    log_level: str = "INFO"

    class Config:
        env_prefix = "HD_"


settings = Settings()
