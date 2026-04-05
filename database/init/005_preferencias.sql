-- =============================================================
-- 005_preferencias.sql
-- Preferências de notificação do cliente
-- =============================================================

CREATE TABLE IF NOT EXISTS preferencias_cliente (
    id_cliente       UUID    PRIMARY KEY
                             REFERENCES clientes(id_cliente) ON DELETE CASCADE,
    cafes_quentes    BOOLEAN NOT NULL DEFAULT TRUE,
    cafes_gelados    BOOLEAN NOT NULL DEFAULT TRUE,
    paes_salgados    BOOLEAN NOT NULL DEFAULT TRUE,
    doces_sobremesas BOOLEAN NOT NULL DEFAULT FALSE,
    notif_email      BOOLEAN NOT NULL DEFAULT TRUE
);

-- ── Trigger: cria preferências padrão ao criar cliente ──
CREATE OR REPLACE FUNCTION fn_criar_preferencias()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO preferencias_cliente (id_cliente)
    VALUES (NEW.id_cliente)
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_criar_preferencias ON clientes;
CREATE TRIGGER trg_criar_preferencias
    AFTER INSERT ON clientes
    FOR EACH ROW EXECUTE FUNCTION fn_criar_preferencias();
