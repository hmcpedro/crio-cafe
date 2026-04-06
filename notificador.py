#!/usr/bin/env python3
"""
notificador.py — Roda FORA do Docker, na máquina do desenvolvedor.

Pré-requisitos:
  pip install requests sqlalchemy psycopg[binary] python-dotenv

Requer que estejam rodando:
  - docker compose up -d   (postgres + evolution)

Uso:
  python notificador.py

Fluxo:
  1. Verifica a cada POLL_INTERVAL segundos se há notificações com
     status='aguardando_disparo' no banco.
  2. Para cada uma, busca os clientes ativos e envia via Evolution API.
  3. Atualiza o status para 'enviada' ou volta para 'aguardando_disparo' em falha.
"""

import os
import re
import sys
import time
import signal
import logging
from datetime import date as date_type
from pathlib import Path
from types import SimpleNamespace

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ── Configuração ──────────────────────────────────────────────────────────────

load_dotenv(Path(__file__).parent / ".env")

DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "admin")
DB_NAME = os.getenv("POSTGRES_DB", "aromap")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

EVOLUTION_URL      = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY  = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "aromap")

DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
UPLOADS_DIR  = Path(__file__).parent / "backend" / "uploads"

POLL_INTERVAL = 10   # segundos entre verificações
PAUSA_MSGS    = 3    # segundos entre mensagens consecutivas

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent / "notificador.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("notificador")

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

# ── Engine / Session ──────────────────────────────────────────────────────────

engine       = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# ── Evolution API helpers ─────────────────────────────────────────────────────

EVO_HEADERS = {
    "apikey": EVOLUTION_API_KEY,
    "Content-Type": "application/json",
}


def _evo_get(path: str) -> dict:
    url = f"{EVOLUTION_URL}{path}"
    logger.debug(f"[EVO] GET {url}")
    r = requests.get(url, headers=EVO_HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def _evo_post(path: str, payload: dict) -> dict:
    url = f"{EVOLUTION_URL}{path}"
    logger.debug(f"[EVO] POST {url} payload={payload}")
    r = requests.post(url, json=payload, headers=EVO_HEADERS, timeout=30)
    if not r.ok:
        logger.error(f"[EVO] HTTP {r.status_code} em POST {path} → {r.text}")
    r.raise_for_status()
    return r.json()


def verificar_instancia() -> bool:
    """
    Verifica se a instância Evolution está conectada (WhatsApp autenticado).
    Retorna True se ok, False caso contrário.
    """
    logger.info(f"[EVO] Verificando instância '{EVOLUTION_INSTANCE}'...")
    try:
        data = _evo_get(f"/instance/connectionState/{EVOLUTION_INSTANCE}")
        state = data.get("instance", {}).get("state") or data.get("state", "")
        logger.info(f"[EVO] Estado da instância: {state!r}")
        if state == "open":
            logger.info("[EVO] Instância conectada e pronta.")
            return True
        else:
            logger.warning(
                f"[EVO] Instância não está conectada (state={state!r}). "
                f"Execute: python notificador.py --qr   para gerar o QR Code."
            )
            return False
    except requests.exceptions.ConnectionError:
        logger.error(
            f"[EVO] Não foi possível conectar ao Evolution API em {EVOLUTION_URL}. "
            f"Verifique se o Docker está rodando: docker compose up -d"
        )
        return False
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            logger.warning(
                f"[EVO] Instância '{EVOLUTION_INSTANCE}' não existe. "
                f"Execute: python notificador.py --criar-instancia"
            )
        else:
            logger.error(f"[EVO] Erro HTTP ao verificar instância: {e}")
        return False
    except Exception as e:
        logger.exception(f"[EVO] Erro inesperado ao verificar instância: {e}")
        return False


def criar_instancia() -> bool:
    """Cria a instância no Evolution API se ela não existir."""
    logger.info(f"[EVO] Criando instância '{EVOLUTION_INSTANCE}'...")
    try:
        data = _evo_post("/instance/create", {
            "instanceName": EVOLUTION_INSTANCE,
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS",
        })
        logger.info(f"[EVO] Instância criada: {data}")
        return True
    except Exception as e:
        logger.error(f"[EVO] Falha ao criar instância: {e}")
        return False


def obter_qr_code() -> None:
    """Busca e exibe o QR Code para conectar o WhatsApp."""
    logger.info(f"[EVO] Buscando QR Code para instância '{EVOLUTION_INSTANCE}'...")
    try:
        # Garante que instância existe
        try:
            _evo_get(f"/instance/connectionState/{EVOLUTION_INSTANCE}")
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                logger.info("[EVO] Instância não existe, criando...")
                if not criar_instancia():
                    return
            else:
                raise

        data = _evo_get(f"/instance/connect/{EVOLUTION_INSTANCE}")
        qr_base64 = data.get("base64") or data.get("qrcode", {}).get("base64", "")
        qr_code   = data.get("code")   or data.get("qrcode", {}).get("code", "")

        if qr_code:
            logger.info(f"[EVO] QR Code gerado. Escaneie com o WhatsApp:")
            logger.info(f"[EVO] Acesse: {EVOLUTION_URL}/manager  (usuário: admin  senha: {EVOLUTION_API_KEY})")
            print("\n" + "=" * 60)
            print("  Acesse o Manager para escanear o QR Code:")
            print(f"  {EVOLUTION_URL}/manager")
            print("=" * 60 + "\n")
        elif qr_base64:
            logger.info("[EVO] QR Code em base64 disponível. Acesse o manager para visualizar.")
        else:
            logger.warning(f"[EVO] Resposta inesperada do connect: {data}")
    except Exception as e:
        logger.exception(f"[EVO] Erro ao obter QR Code: {e}")


def enviar_texto(phone: str, mensagem: str) -> bool:
    """
    Envia mensagem de texto via Evolution API.
    phone: formato E.164 sem '+', ex: '5511999999999'
    Retorna True se enviado com sucesso.
    """
    numero = re.sub(r"\D", "", phone)
    if not numero.startswith("55"):
        numero = "55" + numero

    logger.debug(f"[EVO] Enviando texto para {numero} — {len(mensagem)} chars")
    try:
        resp = _evo_post(
            f"/message/sendText/{EVOLUTION_INSTANCE}",
            {
                "number": numero,
                "textMessage": {"text": mensagem},
            },
        )
        msg_id = resp.get("key", {}).get("id") or resp.get("messageId", "?")
        logger.info(f"[EVO] Mensagem enviada para {numero} — messageId={msg_id}")
        return True
    except requests.exceptions.HTTPError as e:
        body = e.response.text if e.response else ""
        logger.error(f"[EVO] HTTP {e.response.status_code if e.response else '?'} ao enviar para {numero}: {body}")
        return False
    except Exception as e:
        logger.exception(f"[EVO] Erro inesperado ao enviar para {numero}: {e}")
        return False


def enviar_imagem(phone: str, imagem_url: str, caption: str) -> bool:
    """
    Envia imagem com legenda via Evolution API.
    imagem_url: URL pública ou caminho local convertido para base64.
    """
    numero = re.sub(r"\D", "", phone)
    if not numero.startswith("55"):
        numero = "55" + numero

    logger.debug(f"[EVO] Enviando imagem para {numero}")
    try:
        resp = _evo_post(
            f"/message/sendMedia/{EVOLUTION_INSTANCE}",
            {
                "number": numero,
                "mediaMessage": {
                    "mediatype": "image",
                    "mimetype": "image/jpeg",
                    "media": imagem_url,
                    "caption": caption,
                },
            },
        )
        msg_id = resp.get("key", {}).get("id") or resp.get("messageId", "?")
        logger.info(f"[EVO] Imagem enviada para {numero} — messageId={msg_id}")
        return True
    except requests.exceptions.HTTPError as e:
        body = e.response.text if e.response else ""
        logger.warning(
            f"[EVO] Falha ao enviar imagem para {numero} (HTTP {e.response.status_code if e.response else '?'}): {body}. "
            f"Tentando enviar só texto..."
        )
        return False
    except Exception as e:
        logger.exception(f"[EVO] Erro inesperado ao enviar imagem para {numero}: {e}")
        return False


# ── Mensagem ──────────────────────────────────────────────────────────────────

def periodo_str(data_inicio, data_fim) -> str:
    return (
        f"{data_inicio.day} de {MESES[data_inicio.month - 1]}"
        f" a {data_fim.day} de {MESES[data_fim.month - 1]}"
    )


def montar_mensagem(nome_cliente: str, campanha_nome: str, descricao: str,
                    periodo: str, horario: str | None) -> str:
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
    try:
        relativo = Path(imagem_path).relative_to("/uploads")
        local    = UPLOADS_DIR / relativo
        return str(local) if local.exists() else None
    except Exception:
        return None


def imagem_para_base64(caminho: str) -> str | None:
    """Converte arquivo local para data URI base64 para envio via Evolution API."""
    import base64
    import mimetypes
    try:
        mime = mimetypes.guess_type(caminho)[0] or "image/jpeg"
        with open(caminho, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:{mime};base64,{data}"
    except Exception as e:
        logger.warning(f"[NOTIF] Falha ao converter imagem para base64 ({caminho}): {e}")
        return None


# ── Lógica de envio ───────────────────────────────────────────────────────────

def enviar_campanha(db, campanha: SimpleNamespace, notif_id) -> None:
    logger.info(f"[CAMPANHA] Iniciando envio da campanha '{campanha.nome}' (notif_id={notif_id})")

    clientes = db.execute(
        text("SELECT name, phone FROM users WHERE is_active = TRUE AND is_admin = FALSE")
    ).fetchall()

    if not clientes:
        logger.warning("[CAMPANHA] Nenhum cliente ativo encontrado. Marcando como enviada.")
        _atualizar_status(db, notif_id, "enviada")
        return

    logger.info(f"[CAMPANHA] {len(clientes)} cliente(s) elegível(is) para receber a notificação.")

    periodo = periodo_str(campanha.data_inicio, campanha.data_fim)
    horario = None
    if campanha.hora_inicio and campanha.hora_fim:
        horario = f"{campanha.hora_inicio.strftime('%H:%M')} às {campanha.hora_fim.strftime('%H:%M')}"

    # Prepara imagem se disponível
    img_b64 = None
    if campanha.imagem_path:
        local = caminho_imagem_local(campanha.imagem_path)
        if local:
            img_b64 = imagem_para_base64(local)
            logger.info(f"[CAMPANHA] Imagem encontrada e convertida: {local}")
        else:
            logger.warning(f"[CAMPANHA] Imagem referenciada não existe localmente: {campanha.imagem_path}")

    enviados = 0
    falhas   = 0

    for i, cliente in enumerate(clientes):
        primeiro = cliente.name.strip().split()[0]
        mensagem = montar_mensagem(primeiro, campanha.nome, campanha.descricao, periodo, horario)

        logger.info(f"[ENVIO] [{i+1}/{len(clientes)}] Enviando para {cliente.name} ({cliente.phone})...")

        sucesso = False
        if img_b64:
            sucesso = enviar_imagem(cliente.phone, img_b64, mensagem)
            if not sucesso:
                logger.info(f"[ENVIO] Fallback para texto para {cliente.phone}")
                sucesso = enviar_texto(cliente.phone, mensagem)
        else:
            sucesso = enviar_texto(cliente.phone, mensagem)

        if sucesso:
            enviados += 1
        else:
            falhas += 1

        if i < len(clientes) - 1:
            time.sleep(PAUSA_MSGS)

    logger.info(f"[CAMPANHA] '{campanha.nome}' concluída — {enviados} enviadas, {falhas} falhas.")
    _atualizar_status(db, notif_id, "enviada")


def _atualizar_status(db, notif_id, novo_status: str) -> None:
    db.execute(
        text(
            "UPDATE notificacoes_campanha "
            "SET status = :s, enviado_em = NOW() "
            "WHERE id = :id"
        ),
        {"s": novo_status, "id": str(notif_id)},
    )
    db.commit()
    logger.debug(f"[DB] Notificação {notif_id} → status='{novo_status}'")


# ── Verificações de startup ───────────────────────────────────────────────────

def verificar_db() -> bool:
    logger.info(f"[DB] Testando conexão com {DB_HOST}:{DB_PORT}/{DB_NAME}...")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("[DB] Conexão OK.")
        return True
    except Exception as e:
        logger.error(
            f"[DB] Falha na conexão: {e}\n"
            f"     Verifique se o Docker está rodando: docker compose up -d"
        )
        return False


# ── Loop principal ────────────────────────────────────────────────────────────

def verificar_e_enviar() -> None:
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

        if pendentes:
            logger.info(f"[LOOP] {len(pendentes)} notificação(ões) aguardando disparo.")
        else:
            logger.debug("[LOOP] Nenhuma notificação pendente.")

        for row in pendentes:
            logger.info(f"[LOOP] Processando: '{row.nome}' (notif_id={row.id})")
            _atualizar_status(db, row.id, "enviando")

            campanha = SimpleNamespace(
                nome        = row.nome,
                descricao   = row.descricao,
                imagem_path = row.imagem_path,
                data_inicio = row.data_inicio,
                data_fim    = row.data_fim,
                hora_inicio = row.hora_inicio,
                hora_fim    = row.hora_fim,
            )

            try:
                enviar_campanha(db, campanha, row.id)
            except Exception as e:
                logger.exception(f"[LOOP] Erro ao enviar campanha '{row.nome}': {e}")
                logger.warning(f"[LOOP] Voltando status para 'aguardando_disparo' para nova tentativa.")
                _atualizar_status(db, row.id, "aguardando_disparo")
    finally:
        db.close()


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Notificador Aromap via Evolution API")
    parser.add_argument("--qr",               action="store_true", help="Exibe QR Code para conectar WhatsApp")
    parser.add_argument("--criar-instancia",  action="store_true", help="Cria a instância no Evolution API")
    parser.add_argument("--status",           action="store_true", help="Verifica status da instância e sai")
    args = parser.parse_args()

    print("=" * 60)
    print("  Notificador Aromap — Evolution API")
    print(f"  Evolution: {EVOLUTION_URL}  instância: {EVOLUTION_INSTANCE}")
    print(f"  Banco:     {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print("=" * 60)

    if args.criar_instancia:
        criar_instancia()
        sys.exit(0)

    if args.qr:
        obter_qr_code()
        sys.exit(0)

    if args.status:
        verificar_instancia()
        sys.exit(0)

    # Startup checks
    if not verificar_db():
        logger.error("Banco indisponível. Encerrando.")
        sys.exit(1)

    if not verificar_instancia():
        logger.error(
            "WhatsApp não conectado. Execute:\n"
            "  python notificador.py --qr\n"
            "e escaneie o QR Code no manager."
        )
        sys.exit(1)

    logger.info(f"[LOOP] Iniciando polling a cada {POLL_INTERVAL}s. Ctrl+C para encerrar.")

    running = True
    def _stop(sig, frame):
        nonlocal running
        logger.info("[LOOP] Sinal de encerramento recebido. Parando...")
        running = False
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    while running:
        try:
            verificar_e_enviar()
        except Exception as e:
            logger.exception(f"[LOOP] Erro inesperado no ciclo: {e}")
        time.sleep(POLL_INTERVAL)

    logger.info("[LOOP] Notificador encerrado.")


if __name__ == "__main__":
    main()
