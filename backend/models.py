import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Numeric, ForeignKey, Text, Date, Time, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    cliente: Mapped[Optional["Cliente"]] = relationship("Cliente", back_populates="user", uselist=False)


class Cliente(Base):
    __tablename__ = "clientes"

    id_cliente: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    email_verificado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consentimento_data: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    permissao_localizacao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship("User", back_populates="cliente")
    preferencias: Mapped[Optional["PreferenciaCliente"]] = relationship(
        "PreferenciaCliente", back_populates="cliente", uselist=False
    )
    localizacoes: Mapped[list["Localizacao"]] = relationship(
        "Localizacao", back_populates="cliente"
    )


class PreferenciaCliente(Base):
    __tablename__ = "preferencias_cliente"

    id_cliente: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id_cliente", ondelete="CASCADE"), primary_key=True
    )
    cafes_quentes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cafes_gelados: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    paes_salgados: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    doces_sobremesas: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notif_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    cliente: Mapped["Cliente"] = relationship("Cliente", back_populates="preferencias")


class Localizacao(Base):
    __tablename__ = "localizacao"

    id_localizacao: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    id_cliente: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id_cliente", ondelete="CASCADE"), nullable=False
    )
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(11, 8), nullable=False)
    registrado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    cliente: Mapped["Cliente"] = relationship("Cliente", back_populates="localizacoes")


class Campanha(Base):
    __tablename__ = "campanhas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    produto_alvo: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo_desconto: Mapped[str] = mapped_column(String(20), nullable=False)
    valor_desconto: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    imagem_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date] = mapped_column(Date, nullable=False)
    hora_inicio: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    hora_fim: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    # 7 chars Seg→Dom: '1'=ativo '0'=inativo  ex: '1111100' = seg a sex
    dias_semana: Mapped[str] = mapped_column(String(7), nullable=False, default="1111111")
    unidades: Mapped[list] = mapped_column(ARRAY(String), nullable=False, default=list)
    tipo_notificacao: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    notificacao_agendada_em: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="agendada")
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    criado_por: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    notificacoes: Mapped[list["NotificacaoCampanha"]] = relationship(
        "NotificacaoCampanha", back_populates="campanha", cascade="all, delete-orphan"
    )


class Resgate(Base):
    __tablename__ = "resgates"
    __table_args__ = (UniqueConstraint("id_usuario", "id_campanha", name="uq_resgate_usuario_campanha"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    id_campanha: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False
    )
    resgatado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    campanha: Mapped["Campanha"] = relationship("Campanha")


class NotificacaoCampanha(Base):
    __tablename__ = "notificacoes_campanha"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_campanha: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    agendado_para: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    enviado_em: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pendente")
    criado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    campanha: Mapped["Campanha"] = relationship("Campanha", back_populates="notificacoes")
