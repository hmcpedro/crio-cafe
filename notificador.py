#!/usr/bin/env python3
"""
notificador.py — Roda FORA do Docker, na máquina do desenvolvedor.

Requer:
  pip install pywhatkit sqlalchemy psycopg[binary] python-dotenv

Requer que esteja em execução:
  - Docker Compose (postgres + backend)
  - Chrome com WhatsApp Web aberto e logado

Uso:
  python notificador.py

O script observa o banco a cada 10 segundos.
Quando uma notificação está com status 'aguardando_disparo',
envia WhatsApp para todos os clientes ativos e atualiza o status.
"""

import os
import re
import time
import logging
import uuid
from datetime import date as date_type
from pathlib import Path

import pywhatkit
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

# ── Configuração ──────────────────────────────────────────────────────────────

load_dotenv(Path(__file__).parent / ".env")

DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "admin")
DB_NAME = os.getenv("POSTGRES_DB", "aromap")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")   # host local, não o container
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Caminho local das imagens (bind mount do docker-compose)
UPLOADS_DIR = Path(__file__).parent / "backend" / "uploads"

POLL_INTERVAL = 10   # segundos entre cada verificação
WAIT_TIME     = 15   # segundos que o pywhatkit espera o WhatsApp Web abrir
PAUSA_MSGS    = 6    # segundos entre mensagens consecutivas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("notificador")

# ── DB ────────────────────────────────────────────────────────────────────────

engine       = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def formatar_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if not digits.startswith("55"):
        digits = "55" + digits
    return "+" + digits


def periodo_str(data_inicio, data_fim) -> str:
    return (
        f"{data_inicio.day} de {MESES[data_inicio.month - 1]}"
        f" a {data_fim.day} de {MESES[data_fim.month - 1]}"
    )


def montar_mensagem(nome_cliente, campanha_nome, descricao, periodo, horario) -> str:
    msg  = f"Olá, {nome_cliente}! 👋\n\n"
    msg += f"*{campanha_nome}*\n\n"
    msg += f"{descricao}\n\n"
    msg += f"📅 {periodo}"
    if horario:
        msg += f"\n🕒 {horario}"
    msg += "\n\n_Aromap - Ofertas perto de você_ ☕"
    return msg


def caminho_imagem_local(imagem_path: str | None) -> str | None:
    """'/uploads/campanhas/uuid.png' → caminho absoluto local."""
    if not imagem_path:
        return None
    # imagem_path começa com /uploads/
    relativo = Path(imagem_path).relative_to("/uploads")
    local    = UPLOADS_DIR / relativo
    return str(local) if local.exists() else None


# ── Lógica de envio ───────────────────────────────────────────────────────────

def enviar_campanha(db, campanha_row, notif_row):
    """Envia WhatsApp para todos os clientes ativos e atualiza o status."""
    # Busca clientes ativos (não-admin)
    clientes = db.execute(
        text("SELECT name, phone FROM users WHERE is_active = TRUE AND is_admin = FALSE")
    ).fetchall()

    if not clientes:
        logger.warning("Nenhum cliente ativo encontrado.")
        _atualizar_status(db, notif_row.id, "enviada")
        return

    periodo = periodo_str(campanha_row.data_inicio, campanha_row.data_fim)
    horario = (
        f"{campanha_row.hora_inicio.strftime('%H:%M')} às {campanha_row.hora_fim.strftime('%H:%M')}"
        if campanha_row.hora_inicio and campanha_row.hora_fim
        else None
    )
    img_path = caminho_imagem_local(campanha_row.imagem_path)

    enviados = 0
    falhas   = 0

    for i, cliente in enumerate(clientes):
        phone    = formatar_phone(cliente.phone)
        primeiro = cliente.name.strip().split()[0]
        mensagem = montar_mensagem(
            primeiro,
            campanha_row.nome,
            campanha_row.descricao,
            periodo,
            horario,
        )

        try:
            if img_path:
                pywhatkit.sendwhats_image(
                    phone, img_path,
                    caption=mensagem,
                    wait_time=WAIT_TIME,
                    tab_close=True,
                    close_time=3,
                )
            else:
                pywhatkit.sendwhatmsg_instantly(
                    phone, mensagem,
                    wait_time=WAIT_TIME,
                    tab_close=True,
                    close_time=3,
                )
            enviados += 1
            logger.info(f"  ✓ Enviado para {phone} ({primeiro})")

        except Exception as exc:
            falhas += 1
            logger.error(f"  ✗ Falha para {phone}: {exc}")

        if i < len(clientes) - 1:
            time.sleep(PAUSA_MSGS)

    logger.info(f"Campanha '{campanha_row.nome}': {enviados} enviados, {falhas} falhas.")
    _atualizar_status(db, notif_row.id, "enviada")


def _atualizar_status(db, notif_id, novo_status: str):
    db.execute(
        text(
            "UPDATE notificacoes_campanha "
            "SET status = :s, enviado_em = NOW() "
            "WHERE id = :id"
        ),
        {"s": novo_status, "id": str(notif_id)},
    )
    db.commit()


# ── Loop principal ────────────────────────────────────────────────────────────

def verificar_e_enviar():
    db = SessionLocal()
    try:
        pendentes = db.execute(
            text("""
                SELECT nc.id, nc.id_campanha,
                       c.nome, c.descricao, c.imagem_path,
                       c.data_inicio, c.data_fim,
                       c.hora_inicio, c.hora_fim
                FROM notificacoes_campanha nc
                JOIN campanhas c ON c.id = nc.id_campanha
                WHERE nc.status = 'aguardando_disparo'
                ORDER BY nc.criado_em
            """)
        ).fetchall()

        for row in pendentes:
            logger.info(f"Disparando campanha: {row.nome}")

            # Cria objeto auxiliar para reutilizar enviar_campanha
            class NotifRow:
                id = row.id

            class CampanhaRow:
                nome         = row.nome
                descricao    = row.descricao
                imagem_path  = row.imagem_path
                data_inicio  = row.data_inicio
                data_fim     = row.data_fim
                hora_inicio  = row.hora_inicio
                hora_fim     = row.hora_fim

            # Marca como 'enviando' para evitar reprocessamento duplo
            _atualizar_status(db, row.id, "enviando")

            try:
                enviar_campanha(db, CampanhaRow(), NotifRow())
            except Exception as exc:
                logger.exception(f"Erro ao enviar campanha {row.nome}: {exc}")
                # Volta para aguardando_disparo para tentar novamente
                _atualizar_status(db, row.id, "aguardando_disparo")

    finally:
        db.close()


def main():
    logger.info("=" * 50)
    logger.info("  Notificador Aromap iniciado")
    logger.info(f"  Banco: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    logger.info(f"  Verificando a cada {POLL_INTERVAL}s")
    logger.info("  Certifique-se que o WhatsApp Web está aberto e logado no Chrome.")
    logger.info("=" * 50)

    while True:
        try:
            verificar_e_enviar()
        except Exception as exc:
            logger.error(f"Erro no ciclo de verificação: {exc}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
