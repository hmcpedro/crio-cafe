import json
import shutil
import uuid as uuid_module
from datetime import date as date_type, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Form, File, UploadFile, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import User, Cliente, PreferenciaCliente, Localizacao, Campanha, NotificacaoCampanha
from schemas import (
    RegisterRequest, LoginRequest, AuthResponse,
    UserProfileResponse, UpdateProfileRequest, ChangePasswordRequest,
    PreferenciasResponse, PreferenciasRequest, LocalizacaoRequest,
    CampanhaResponse, NotificacaoResponse,
)
from security import hash_password, verify_password
from auth import create_access_token, get_current_user

app = FastAPI(title="Crio Café")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
PAGES_DIR = FRONTEND_DIR / "html"
UPLOADS_DIR = BASE_DIR / "backend" / "uploads" / "campanhas"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=BASE_DIR / "backend" / "uploads"), name="uploads")


# ── Helpers ───────────────────────────────────────────────────────────────────

MONTHS_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

def format_member_since(dt) -> str:
    return f"{MONTHS_PT[dt.month - 1]} de {dt.year}"


def _compute_status(c: Campanha) -> str:
    """Recalcula status com base nas datas; respeita encerramento manual."""
    if c.status == "encerrada":
        return "encerrada"
    today = date_type.today()
    if c.data_fim < today:
        return "encerrada"
    if c.data_inicio > today:
        return "agendada"
    return "ativa"


def _notif_to_schema(n: NotificacaoCampanha) -> NotificacaoResponse:
    return NotificacaoResponse(
        id=str(n.id),
        tipo=n.tipo,
        agendado_para=n.agendado_para.isoformat() if n.agendado_para else None,
        enviado_em=n.enviado_em.isoformat() if n.enviado_em else None,
        status=n.status,
        criado_em=n.criado_em.isoformat(),
    )


def _campanha_to_schema(c: Campanha) -> CampanhaResponse:
    return CampanhaResponse(
        id=str(c.id),
        nome=c.nome,
        descricao=c.descricao,
        produto_alvo=c.produto_alvo,
        tipo_desconto=c.tipo_desconto,
        valor_desconto=float(c.valor_desconto) if c.valor_desconto is not None else None,
        imagem_path=c.imagem_path,
        data_inicio=c.data_inicio.isoformat(),
        data_fim=c.data_fim.isoformat(),
        hora_inicio=c.hora_inicio.strftime("%H:%M") if c.hora_inicio else None,
        hora_fim=c.hora_fim.strftime("%H:%M") if c.hora_fim else None,
        dias_semana=c.dias_semana,
        unidades=c.unidades or [],
        tipo_notificacao=c.tipo_notificacao,
        notificacao_agendada_em=c.notificacao_agendada_em.isoformat() if c.notificacao_agendada_em else None,
        status=_compute_status(c),
        criado_em=c.criado_em.isoformat(),
        notificacoes=[_notif_to_schema(n) for n in c.notificacoes],
    )


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/login")

@app.get("/login", include_in_schema=False)
def login_page():
    return FileResponse(PAGES_DIR / "login.html")

@app.get("/cadastro", include_in_schema=False)
def cadastro_page():
    return FileResponse(PAGES_DIR / "cadastro.html")

@app.get("/home", include_in_schema=False)
def home_page():
    return FileResponse(PAGES_DIR / "home.html")

@app.get("/ofertas", include_in_schema=False)
def ofertas_page():
    return FileResponse(PAGES_DIR / "ofertas.html")

@app.get("/perfil", include_in_schema=False)
def perfil_page():
    return FileResponse(PAGES_DIR / "perfil.html")

@app.get("/admin", include_in_schema=False)
def admin_page():
    return FileResponse(PAGES_DIR / "admin-home.html")

@app.get("/admin/campanhas", include_in_schema=False)
def admin_campanhas_page():
    return FileResponse(PAGES_DIR / "admin-campanhas.html")

@app.get("/admin/relatorios", include_in_schema=False)
def admin_relatorios_page():
    return FileResponse(PAGES_DIR / "admin-relatorios.html")

@app.get("/admin/campanha-detalhe", include_in_schema=False)
def admin_campanha_detalhe_page():
    return FileResponse(PAGES_DIR / "admin-campanha-detalhe.html")

@app.get("/admin/nova-campanha", include_in_schema=False)
def admin_nova_campanha_page():
    return FileResponse(PAGES_DIR / "admin-nova-campanha.html")

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="As senhas não coincidem.")

    email = data.email.lower().strip()
    phone = data.phone.strip()

    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")

    if db.scalar(select(User).where(User.phone == phone)):
        raise HTTPException(status_code=400, detail="Este telefone já está cadastrado.")

    user = User(
        name=data.name.strip(),
        email=email,
        phone=phone,
        password_hash=hash_password(data.password),
        is_admin=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # O trigger SQL cria clientes + preferencias_cliente automaticamente.
    # Confirmamos via ORM para garantir sessão atualizada.
    db.refresh(user)

    return AuthResponse(
        message="Cadastro realizado com sucesso.",
        name=user.name,
        is_admin=user.is_admin,
        token=create_access_token(str(user.id)),
    )


@app.post("/auth/login", response_model=AuthResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    email = data.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuário inativo.")

    return AuthResponse(
        message="Login realizado com sucesso.",
        name=user.name,
        is_admin=user.is_admin,
        token=create_access_token(str(user.id)),
    )


# ── Perfil do usuário logado (/api/me) ────────────────────────────────────────

@app.get("/api/me", response_model=UserProfileResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cliente = db.scalar(select(Cliente).where(Cliente.id_cliente == current_user.id))
    return UserProfileResponse(
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        phone=current_user.phone,
        member_since=format_member_since(current_user.created_at),
        email_verificado=cliente.email_verificado if cliente else False,
        permissao_localizacao=cliente.permissao_localizacao if cliente else False,
    )


@app.patch("/api/me", response_model=UserProfileResponse)
def update_me(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_phone = data.phone.strip()

    # Verifica conflito de telefone com outro usuário
    conflict = db.scalar(
        select(User).where(User.phone == new_phone, User.id != current_user.id)
    )
    if conflict:
        raise HTTPException(status_code=400, detail="Este telefone já está em uso.")

    current_user.name = data.name.strip()
    current_user.phone = new_phone
    db.commit()
    db.refresh(current_user)

    cliente = db.scalar(select(Cliente).where(Cliente.id_cliente == current_user.id))
    return UserProfileResponse(
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        phone=current_user.phone,
        member_since=format_member_since(current_user.created_at),
        email_verificado=cliente.email_verificado if cliente else False,
        permissao_localizacao=cliente.permissao_localizacao if cliente else False,
    )


@app.patch("/api/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")

    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="As senhas não coincidem.")

    current_user.password_hash = hash_password(data.new_password)
    db.commit()


# ── Preferências ──────────────────────────────────────────────────────────────

@app.get("/api/me/preferencias", response_model=PreferenciasResponse)
def get_preferencias(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = db.scalar(
        select(PreferenciaCliente).where(PreferenciaCliente.id_cliente == current_user.id)
    )
    if not prefs:
        # Cria com valores padrão se não existir (usuário legado)
        prefs = PreferenciaCliente(id_cliente=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)

    return PreferenciasResponse(
        cafes_quentes=prefs.cafes_quentes,
        cafes_gelados=prefs.cafes_gelados,
        paes_salgados=prefs.paes_salgados,
        doces_sobremesas=prefs.doces_sobremesas,
        notif_email=prefs.notif_email,
    )


@app.put("/api/me/preferencias", response_model=PreferenciasResponse)
def update_preferencias(
    data: PreferenciasRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = db.scalar(
        select(PreferenciaCliente).where(PreferenciaCliente.id_cliente == current_user.id)
    )
    if not prefs:
        prefs = PreferenciaCliente(id_cliente=current_user.id)
        db.add(prefs)

    prefs.cafes_quentes    = data.cafes_quentes
    prefs.cafes_gelados    = data.cafes_gelados
    prefs.paes_salgados    = data.paes_salgados
    prefs.doces_sobremesas = data.doces_sobremesas
    prefs.notif_email      = data.notif_email
    db.commit()
    db.refresh(prefs)

    return PreferenciasResponse(
        cafes_quentes=prefs.cafes_quentes,
        cafes_gelados=prefs.cafes_gelados,
        paes_salgados=prefs.paes_salgados,
        doces_sobremesas=prefs.doces_sobremesas,
        notif_email=prefs.notif_email,
    )


# ── Localização ───────────────────────────────────────────────────────────────

@app.post("/api/me/localizacao", status_code=status.HTTP_201_CREATED)
def post_localizacao(
    data: LocalizacaoRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    loc = Localizacao(
        id_cliente=current_user.id,
        latitude=data.latitude,
        longitude=data.longitude,
    )
    db.add(loc)
    db.commit()
    return {"message": "Localização registrada."}


# ── Campanhas ─────────────────────────────────────────────────────────────────

@app.post("/api/campanhas", response_model=CampanhaResponse, status_code=status.HTTP_201_CREATED)
async def create_campanha(
    nome: str = Form(...),
    descricao: str = Form(...),
    produto_alvo: str = Form(...),
    tipo_desconto: str = Form(...),
    valor_desconto: Optional[str] = Form(None),
    data_inicio: str = Form(...),
    data_fim: str = Form(...),
    hora_inicio: Optional[str] = Form(None),
    hora_fim: Optional[str] = Form(None),
    dias_semana: str = Form("1111111"),
    unidades: str = Form("[]"),         # JSON array string ex: '["vila-mariana"]'
    tipo_notificacao: str = Form("manual"),
    notificacao_agendada_em: Optional[str] = Form(None),
    imagem: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")

    # DEBUG — remover após diagnóstico
    import sys
    print(f"[DEBUG] tipo_desconto recebido: {repr(tipo_desconto)}", file=sys.stderr, flush=True)
    print(f"[DEBUG] valor_desconto recebido: {repr(valor_desconto)}", file=sys.stderr, flush=True)
    print(f"[DEBUG] tipo_notificacao recebido: {repr(tipo_notificacao)}", file=sys.stderr, flush=True)

    # Normalização e aliases para tipo_desconto
    _tipo_desconto_aliases = {
        "percent":    "percentual",
        "percentual": "percentual",
        "fixed":      "fixo",
        "fixo":       "fixo",
        "combo":      "combo",
    }
    tipo_desconto = _tipo_desconto_aliases.get(tipo_desconto.strip().lower(), tipo_desconto.strip().lower())
    if tipo_desconto not in ("percentual", "fixo", "combo"):
        raise HTTPException(status_code=400, detail=f"tipo_desconto inválido: '{tipo_desconto}'.")

    _tipo_notificacao_aliases = {
        "imediato":  "imediata",
        "imediata":  "imediata",
        "agendado":  "agendada",
        "agendada":  "agendada",
        "manual":    "manual",
    }
    tipo_notificacao = _tipo_notificacao_aliases.get(tipo_notificacao.strip().lower(), tipo_notificacao.strip().lower())
    if tipo_notificacao not in ("imediata", "agendada", "manual"):
        raise HTTPException(status_code=400, detail=f"tipo_notificacao inválido: '{tipo_notificacao}'.")

    # Parse de datas
    try:
        inicio = date_type.fromisoformat(data_inicio.strip())
        fim = date_type.fromisoformat(data_fim.strip())
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido (use YYYY-MM-DD).")

    if fim < inicio:
        raise HTTPException(status_code=400, detail="data_fim não pode ser anterior a data_inicio.")

    # Parse de valor — aceita "20", "20%", "R$ 20,50", "0,20", "0.20"
    val_desc = None
    if tipo_desconto != "combo":
        if not valor_desconto or not valor_desconto.strip():
            exemplo = "20 (para 20%)" if tipo_desconto == "percentual" else "5,50 (em R$)"
            raise HTTPException(
                status_code=400,
                detail=f"Informe o valor do desconto. Exemplo: {exemplo}."
            )
        raw = valor_desconto.strip().replace("R$", "").replace("%", "").replace(" ", "").replace(",", ".")
        try:
            val_desc = Decimal(raw)
            if val_desc <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            exemplo = "20 (para 20%)" if tipo_desconto == "percentual" else "5,50 (em R$)"
            raise HTTPException(
                status_code=400,
                detail=f"Valor inválido. Use apenas números. Exemplo: {exemplo}."
            )
        if tipo_desconto == "percentual" and val_desc > 100:
            raise HTTPException(status_code=400, detail="Desconto percentual não pode ser maior que 100.")
    elif valor_desconto and valor_desconto.strip():
        # Combo: aceita valor opcional mas valida se informado
        raw = valor_desconto.strip().replace("R$", "").replace("%", "").replace(" ", "").replace(",", ".")
        try:
            val_desc = Decimal(raw) if raw else None
        except InvalidOperation:
            val_desc = None

    # Parse de unidades
    try:
        unidades_list: list = json.loads(unidades) if unidades else []
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Campo unidades deve ser JSON array.")

    # Parse de agendamento de notificação
    notif_agendada = None
    if tipo_notificacao == "agendada" and notificacao_agendada_em and notificacao_agendada_em.strip():
        try:
            notif_agendada = datetime.fromisoformat(notificacao_agendada_em.strip())
        except ValueError:
            raise HTTPException(status_code=400, detail="notificacao_agendada_em inválido.")

    # Upload de imagem
    imagem_path = None
    if imagem and imagem.filename:
        ext = Path(imagem.filename).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            raise HTTPException(status_code=400, detail="Imagem deve ser JPG, PNG ou WEBP.")
        filename = f"{uuid_module.uuid4()}{ext}"
        dest = UPLOADS_DIR / filename
        with open(dest, "wb") as f:
            shutil.copyfileobj(imagem.file, f)
        imagem_path = f"/uploads/campanhas/{filename}"

    # Status inicial
    today = date_type.today()
    initial_status = "agendada" if inicio > today else "ativa"

    campanha = Campanha(
        nome=nome.strip(),
        descricao=descricao.strip(),
        produto_alvo=produto_alvo.strip(),
        tipo_desconto=tipo_desconto,
        valor_desconto=val_desc,
        imagem_path=imagem_path,
        data_inicio=inicio,
        data_fim=fim,
        hora_inicio=hora_inicio.strip() or None if hora_inicio else None,
        hora_fim=hora_fim.strip() or None if hora_fim else None,
        dias_semana=dias_semana[:7].ljust(7, "0"),
        unidades=unidades_list,
        tipo_notificacao=tipo_notificacao,
        notificacao_agendada_em=notif_agendada,
        status=initial_status,
        criado_por=current_user.id,
    )
    db.add(campanha)
    db.flush()

    # Cria registro de notificação vinculado à campanha
    notif = NotificacaoCampanha(
        id_campanha=campanha.id,
        tipo=tipo_notificacao,
        agendado_para=notif_agendada,
        status="pendente",
    )
    db.add(notif)
    db.commit()
    db.refresh(campanha)

    return _campanha_to_schema(campanha)


@app.get("/api/campanhas", response_model=list[CampanhaResponse])
def list_campanhas(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    q = select(Campanha).order_by(Campanha.criado_em.desc())
    campanhas = db.scalars(q).all()

    results = [_campanha_to_schema(c) for c in campanhas]

    if status_filter:
        results = [r for r in results if r.status == status_filter]

    return results


@app.get("/api/campanhas/{campanha_id}", response_model=CampanhaResponse)
def get_campanha(campanha_id: str, db: Session = Depends(get_db)):
    try:
        uid = uuid_module.UUID(campanha_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido.")

    campanha = db.scalar(select(Campanha).where(Campanha.id == uid))
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")

    return _campanha_to_schema(campanha)


@app.patch("/api/campanhas/{campanha_id}/encerrar", response_model=CampanhaResponse)
def encerrar_campanha(
    campanha_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")

    try:
        uid = uuid_module.UUID(campanha_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID inválido.")

    campanha = db.scalar(select(Campanha).where(Campanha.id == uid))
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")

    campanha.status = "encerrada"

    # Cancela notificações pendentes
    for notif in campanha.notificacoes:
        if notif.status == "pendente":
            notif.status = "cancelada"

    db.commit()
    db.refresh(campanha)
    return _campanha_to_schema(campanha)
