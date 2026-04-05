-- Campanhas promocionais
CREATE TABLE campanhas (
    id                      UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    nome                    VARCHAR(200) NOT NULL,
    descricao               TEXT         NOT NULL,
    produto_alvo            VARCHAR(200) NOT NULL,
    tipo_desconto           VARCHAR(20)  NOT NULL
                               CHECK (tipo_desconto IN ('percentual', 'fixo', 'combo')),
    valor_desconto          NUMERIC(10, 2),
    imagem_path             TEXT,
    data_inicio             DATE         NOT NULL,
    data_fim                DATE         NOT NULL,
    hora_inicio             TIME,
    hora_fim                TIME,
    -- 7 chars Seg→Dom: '1'=ativo '0'=inativo  ex: '1111100' = seg a sex
    dias_semana             CHAR(7)      NOT NULL DEFAULT '1111111',
    unidades                TEXT[]       NOT NULL DEFAULT '{}',
    tipo_notificacao        VARCHAR(20)  NOT NULL DEFAULT 'manual'
                               CHECK (tipo_notificacao IN ('imediata', 'agendada', 'manual')),
    notificacao_agendada_em TIMESTAMP,
    -- status calculado pelo backend; 'encerrada' pode ser forçado manualmente
    status                  VARCHAR(20)  NOT NULL DEFAULT 'agendada'
                               CHECK (status IN ('ativa', 'agendada', 'encerrada')),
    criado_em               TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por              UUID         REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_campanhas_status    ON campanhas (status);
CREATE INDEX idx_campanhas_criado_em ON campanhas (criado_em DESC);

-- Registro de notificações por campanha
-- Preparado para integração futura com scripts de envio de WhatsApp
CREATE TABLE notificacoes_campanha (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    id_campanha   UUID        NOT NULL REFERENCES campanhas(id) ON DELETE CASCADE,
    tipo          VARCHAR(20) NOT NULL
                     CHECK (tipo IN ('imediata', 'agendada', 'manual')),
    agendado_para TIMESTAMP,
    enviado_em    TIMESTAMP,
    -- pendente = aguardando envio | aguardando_disparo = na fila do notificador.py | enviando = em progresso | enviada = confirmado | cancelada = abortado
    status        VARCHAR(20) NOT NULL DEFAULT 'pendente'
                     CHECK (status IN ('pendente', 'aguardando_disparo', 'enviando', 'enviada', 'cancelada')),
    criado_em     TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notif_campanha ON notificacoes_campanha (id_campanha);
CREATE INDEX idx_notif_status   ON notificacoes_campanha (status);
