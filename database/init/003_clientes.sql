-- =============================================================
-- 003_clientes.sql
-- Tabela de perfil do cliente (extensão 1:1 de users)
-- =============================================================

CREATE TABLE IF NOT EXISTS clientes (
    id_cliente            UUID      PRIMARY KEY
                                    REFERENCES users(id) ON DELETE CASCADE,
    email_verificado      BOOLEAN   NOT NULL DEFAULT FALSE,
    consentimento_data    TIMESTAMP,
    permissao_localizacao BOOLEAN   NOT NULL DEFAULT FALSE
);

-- ── Trigger: cria registro em clientes ao cadastrar usuário não-admin ──
CREATE OR REPLACE FUNCTION fn_criar_cliente()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT NEW.is_admin THEN
        INSERT INTO clientes (id_cliente)
        VALUES (NEW.id)
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_criar_cliente ON users;
CREATE TRIGGER trg_criar_cliente
    AFTER INSERT ON users
    FOR EACH ROW EXECUTE FUNCTION fn_criar_cliente();
