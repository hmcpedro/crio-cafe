-- =============================================================
-- 004_localizacao.sql
-- Log de localização do cliente (lat/long por registro)
-- =============================================================

CREATE TABLE IF NOT EXISTS localizacao (
    id_localizacao UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    id_cliente     UUID         NOT NULL
                                REFERENCES clientes(id_cliente) ON DELETE CASCADE,
    latitude       NUMERIC(10, 8) NOT NULL,
    longitude      NUMERIC(11, 8) NOT NULL,
    registrado_em  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_localizacao_cliente
    ON localizacao (id_cliente);

CREATE INDEX IF NOT EXISTS idx_localizacao_registrado
    ON localizacao (registrado_em DESC);
