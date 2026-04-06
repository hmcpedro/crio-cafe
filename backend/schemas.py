from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=6)
    confirm_password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    message: str
    name: str
    is_admin: bool
    token: str


# ── Perfil ────────────────────────────────────────────────────────────────────

class UserProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    member_since: str           # ex: "maio de 2025"
    email_verificado: bool
    permissao_localizacao: bool


class UpdateProfileRequest(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    phone: str = Field(min_length=10, max_length=20)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)
    confirm_password: str = Field(min_length=6)


# ── Preferências ──────────────────────────────────────────────────────────────

class PreferenciasResponse(BaseModel):
    cafes_quentes: bool
    cafes_gelados: bool
    paes_salgados: bool
    doces_sobremesas: bool
    notif_email: bool


class PreferenciasRequest(BaseModel):
    cafes_quentes: bool
    cafes_gelados: bool
    paes_salgados: bool
    doces_sobremesas: bool
    notif_email: bool


# ── Localização ───────────────────────────────────────────────────────────────

class LocalizacaoRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


# ── Campanhas ─────────────────────────────────────────────────────────────────

class NotificacaoResponse(BaseModel):
    id: str
    tipo: str
    agendado_para: Optional[str]    # ISO datetime string ou None
    enviado_em: Optional[str]       # ISO datetime string ou None
    status: str                     # pendente | enviada | cancelada
    criado_em: str


class ResgateResponse(BaseModel):
    id: str
    campanha_id: str
    campanha_nome: str
    campanha_status: str   # ativa | agendada | encerrada
    resgatado_em: str      # ISO datetime


class CampanhaResponse(BaseModel):
    id: str
    nome: str
    descricao: str
    produto_alvo: str
    tipo_desconto: str              # percentual | fixo | combo
    valor_desconto: Optional[float]
    imagem_path: Optional[str]      # URL relativa ex: /uploads/campanhas/uuid.jpg
    data_inicio: str                # YYYY-MM-DD
    data_fim: str                   # YYYY-MM-DD
    hora_inicio: Optional[str]      # HH:MM
    hora_fim: Optional[str]         # HH:MM
    dias_semana: str                # 7 chars Seg→Dom '1'/'0'
    unidades: List[str]
    tipo_notificacao: str           # imediata | agendada | manual
    notificacao_agendada_em: Optional[str]  # ISO datetime
    status: str                     # ativa | agendada | encerrada
    criado_em: str
    notificacoes: List[NotificacaoResponse]
