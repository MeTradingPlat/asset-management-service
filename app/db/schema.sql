CREATE TABLE IF NOT EXISTS tracked_symbols (
    symbol_id       SERIAL PRIMARY KEY,
    symbol          VARCHAR(20) NOT NULL UNIQUE,
    market          VARCHAR(10) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_checked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS watermarks (
    symbol_id          INT NOT NULL REFERENCES tracked_symbols(symbol_id),
    timeframe          VARCHAR(6) NOT NULL,
    last_ingested_at   TIMESTAMPTZ,
    oldest_ingested_at TIMESTAMPTZ,
    backfill_complete  BOOLEAN NOT NULL DEFAULT FALSE,
    last_checked_at    TIMESTAMPTZ,
    last_error         TEXT,
    consecutive_errors INT NOT NULL DEFAULT 0,
    PRIMARY KEY (symbol_id, timeframe)
);

CREATE TABLE IF NOT EXISTS candles (
    symbol_id   INT NOT NULL REFERENCES tracked_symbols(symbol_id),
    timeframe   VARCHAR(6) NOT NULL,
    ts          TIMESTAMPTZ NOT NULL,
    open        NUMERIC(18,6) NOT NULL,
    high        NUMERIC(18,6) NOT NULL,
    low         NUMERIC(18,6) NOT NULL,
    close       NUMERIC(18,6) NOT NULL,
    volume      BIGINT NOT NULL DEFAULT 0,
    trade_count INT,
    vwap        NUMERIC(18,6),
    source      VARCHAR(16) NOT NULL DEFAULT 'alpaca_native',
    PRIMARY KEY (symbol_id, timeframe, ts)
);

CREATE INDEX IF NOT EXISTS idx_candles_symbol_tf ON candles (symbol_id, timeframe);

-- candles recibe UPSERTs (ON CONFLICT DO UPDATE) constantes durante el
-- backfill -- cada UPDATE deja una tupla muerta. Con el default de Postgres
-- (vacuum recien al 20% de tuplas muertas) el vacuum se acumula sobre una
-- tabla de decenas de millones de filas y termina en una sola pasada
-- larguisima que compite por I/O con las escrituras en vivo (confirmado en
-- produccion: una pasada de mas de 30 minutos atascada). Bajar el umbral
-- dispara vacuums mas chicos y frecuentes en vez de uno gigante; subir el
-- cost_limit deja que cada pasada termine mas rapido una vez que arranca.
ALTER TABLE candles SET (
    autovacuum_vacuum_scale_factor = 0.02,
    autovacuum_analyze_scale_factor = 0.02,
    autovacuum_vacuum_cost_limit = 1000
);
