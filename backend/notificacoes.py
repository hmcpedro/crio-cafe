"""
notificacoes.py — Disparo de mensagens WhatsApp via pywhatkit.

REQUISITO: WhatsApp Web deve estar aberto e logado no Chrome da máquina
onde este backend está rodando. pywhatkit automatiza o WhatsApp Web
via browser — não é uma API oficial do WhatsApp.
"""

import re
import time
import logging
from pathlib import Path
from datetime import date as date_type

try:
    import pywhatkit
    PYWHATKIT_OK = True
except Exception as _e:
    PYWHATKIT_OK = False
    logging.warning(f"[NOTIF] pywhatkit indisponível ({_e}) — notificações WhatsApp desativadas.")

logger = logging.getLogger("notificacoes")

# Caminho base dos uploads (dentro do container)
UPLOADS_BASE = Path("/app/backend/uploads")

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _formatar_phone(phone: str) -> str:
    """Converte '11999999999' → '+5511999999999'."""
    digits = re.sub(r"\D", "", phone)
    if not digits.startswith("55"):
        digits = "55" + digits
    return "+" + digits


def _periodo_str(data_inicio: str, data_fim: str) -> str:
    ini = date_type.fromisoformat(data_inicio)
    fim = date_type.fromisoformat(data_fim)
    return (
        f"{ini.day} de {MESES[ini.month - 1]}"
        f" a {fim.day} de {MESES[fim.month - 1]}"
    )


def _montar_mensagem(
    nome_cliente: str,
    campanha_nome: str,
    descricao: str,
    periodo: str,
    horario: str | None,
) -> str:
    msg = f"Olá, {nome_cliente}! 👋\n\n"
    msg += f"*{campanha_nome}*\n\n"
    msg += f"{descricao}\n\n"
    msg += f"📅 {periodo}"
    if horario:
        msg += f"\n🕒 {horario}"
    msg += "\n\n_Aromap - Ofertas perto de você_ ☕"
    return msg


def _caminho_imagem_local(imagem_path: str | None) -> str | None:
    """
    imagem_path vem como '/uploads/campanhas/uuid.png' (URL do servidor).
    Converte para o caminho absoluto no filesystem do container.
    """
    if not imagem_path:
        return None
    local = UPLOADS_BASE / Path(imagem_path).relative_to("/uploads")
    return str(local) if local.exists() else None


# ── Função principal ──────────────────────────────────────────────────────────

def disparar_campanha_whatsapp(
    campanha_nome: str,
    descricao: str,
    data_inicio: str,
    data_fim: str,
    hora_inicio: str | None,
    hora_fim: str | None,
    imagem_path: str | None,
    clientes: list[dict],        # [{"phone": "...", "name": "..."}]
    wait_time: int = 15,         # segundos de espera para o WhatsApp Web abrir
) -> tuple[int, int]:
    """
    Envia mensagem WhatsApp para todos os clientes da lista.

    Retorna (enviados, falhas).

    Exige pywhatkit instalado e WhatsApp Web aberto no Chrome.
    """
    if not PYWHATKIT_OK:
        logger.error("[NOTIF] pywhatkit não disponível. Nenhuma mensagem enviada.")
        return 0, len(clientes)

    if not clientes:
        logger.info("[NOTIF] Nenhum cliente na lista — nada a enviar.")
        return 0, 0

    periodo  = _periodo_str(data_inicio, data_fim)
    horario  = f"{hora_inicio} às {hora_fim}" if hora_inicio and hora_fim else None
    img_path = _caminho_imagem_local(imagem_path)

    enviados = 0
    falhas   = 0

    for i, cliente in enumerate(clientes):
        phone      = _formatar_phone(cliente["phone"])
        primeiro   = cliente["name"].strip().split()[0]
        mensagem   = _montar_mensagem(primeiro, campanha_nome, descricao, periodo, horario)

        try:
            if img_path:
                pywhatkit.sendwhats_image(
                    phone,
                    img_path,
                    caption=mensagem,
                    wait_time=wait_time,
                    tab_close=True,
                    close_time=3,
                )
            else:
                pywhatkit.sendwhatmsg_instantly(
                    phone,
                    mensagem,
                    wait_time=wait_time,
                    tab_close=True,
                    close_time=3,
                )
            enviados += 1
            logger.info(f"[NOTIF] Enviado para {phone} ({primeiro})")

        except Exception as exc:
            falhas += 1
            logger.error(f"[NOTIF] Falha ao enviar para {phone}: {exc}")

        # Intervalo entre mensagens para não sobrecarregar o WhatsApp Web
        if i < len(clientes) - 1:
            time.sleep(5)

    logger.info(f"[NOTIF] Concluído: {enviados} enviados, {falhas} falhas.")
    return enviados, falhas
