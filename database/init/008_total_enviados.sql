-- Adiciona contador de mensagens efetivamente enviadas por disparo
-- Para bancos já existentes, executar: psql -U admin -d aromap -f 008_total_enviados.sql
ALTER TABLE notificacoes_campanha
    ADD COLUMN IF NOT EXISTS total_enviados INTEGER NOT NULL DEFAULT 0;
