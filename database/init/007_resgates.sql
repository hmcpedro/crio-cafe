-- Tabela de resgates: um por usuário por campanha
CREATE TABLE IF NOT EXISTS resgates (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_usuario   UUID NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    id_campanha  UUID NOT NULL REFERENCES campanhas(id) ON DELETE CASCADE,
    resgatado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (id_usuario, id_campanha)
);
