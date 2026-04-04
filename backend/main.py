from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import RegisterRequest, LoginRequest, AuthResponse
from security import hash_password, verify_password

app = FastAPI(title="Crio Café")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
PAGES_DIR = FRONTEND_DIR / "html"

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


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

@app.get("/admin", include_in_schema=False)
def admin_page():
    return FileResponse(PAGES_DIR / "admin-home.html")  

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="As senhas não coincidem.")

    email = data.email.lower().strip()
    phone = data.phone.strip()

    existing_email = db.scalar(select(User).where(User.email == email))
    if existing_email:
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")

    existing_phone = db.scalar(select(User).where(User.phone == phone))
    if existing_phone:
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

    return AuthResponse(
        message="Cadastro realizado com sucesso.",
        name=user.name,
        is_admin=user.is_admin,
    )


@app.post("/auth/login", response_model=AuthResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    email = data.email.lower().strip()

    user = db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuário inativo.")

    return AuthResponse(
        message="Login realizado com sucesso.",
        name=user.name,
        is_admin=user.is_admin,
    )