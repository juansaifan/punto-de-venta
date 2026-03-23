"""Entidades del dominio Personas (persona base + roles)."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base


class Persona(Base):
    """
    Entidad base de Personas.

    Representa una persona física o jurídica. Los distintos roles
    (cliente, proveedor, empleado, contactos) se modelan como entidades
    vinculadas a esta tabla mediante FKs.
    """

    __tablename__ = "persona"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(128))
    apellido: Mapped[str] = mapped_column(String(128))
    documento: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relaciones a roles (no son estrictamente necesarias para la lógica
    # actual, pero facilitan navegación desde el ORM).
    clientes: Mapped[list["Cliente"]] = relationship(
        "Cliente", back_populates="persona", cascade="all, delete-orphan"
    )
    proveedores: Mapped[list["Proveedor"]] = relationship(
        "Proveedor", back_populates="persona", cascade="all, delete-orphan"
    )
    empleados: Mapped[list["Empleado"]] = relationship(
        "Empleado", back_populates="persona", cascade="all, delete-orphan"
    )
    contactos: Mapped[list["Contacto"]] = relationship(
        "Contacto", back_populates="persona", cascade="all, delete-orphan"
    )


class Cliente(Base):
    """
    Rol de cliente asociado a una persona.

    docs Módulo Personas §5 (Clientes).
    """

    __tablename__ = "cliente"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    persona_id: Mapped[int] = mapped_column(ForeignKey("persona.id"), nullable=False)
    segmento: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    condicion_pago: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    limite_credito: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    estado: Mapped[str] = mapped_column(String(32), default="ACTIVO")
    fecha_alta: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    persona: Mapped["Persona"] = relationship("Persona", back_populates="clientes")
    cuenta_corriente: Mapped[Optional["CuentaCorrienteCliente"]] = relationship(
        "CuentaCorrienteCliente",
        back_populates="cliente",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Proveedor(Base):
    """
    Rol de proveedor asociado a una persona.

    docs Módulo Personas §7 (Proveedores).
    """

    __tablename__ = "proveedor"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    persona_id: Mapped[int] = mapped_column(ForeignKey("persona.id"), nullable=False)
    cuit: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    condiciones_comerciales: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    condiciones_pago: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    lista_precios: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    estado: Mapped[str] = mapped_column(String(32), default="ACTIVO")
    frecuencia_entrega: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    minimo_compra: Mapped[Optional[float]] = mapped_column(Numeric(14, 2), nullable=True)
    tiempo_estimado_entrega: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    persona: Mapped["Persona"] = relationship("Persona", back_populates="proveedores")


class Empleado(Base):
    """
    Rol de empleado asociado a una persona.

    docs Módulo Personas §8 (Empleados).
    """

    __tablename__ = "empleado"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    persona_id: Mapped[int] = mapped_column(ForeignKey("persona.id"), nullable=False)
    documento: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    cargo: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    fecha_ingreso: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    estado: Mapped[str] = mapped_column(String(32), default="ACTIVO")

    persona: Mapped["Persona"] = relationship("Persona", back_populates="empleados")


class Contacto(Base):
    """
    Contacto asociado a una persona (empresa, proveedor, etc.).

    docs Módulo Personas §4 (Contactos).
    """

    __tablename__ = "contacto"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    persona_id: Mapped[int] = mapped_column(ForeignKey("persona.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(128))
    cargo: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    persona: Mapped["Persona"] = relationship("Persona", back_populates="contactos")


class CuentaCorrienteCliente(Base):
    """
    Cuenta corriente asociada a un cliente.

    Modela el saldo de deuda del cliente con el negocio (ventas a crédito,
    pagos y ajustes). El límite de crédito de referencia se toma de Cliente.limite_credito.
    """

    __tablename__ = "cuenta_corriente_cliente"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("cliente.id"), unique=True, nullable=False
    )
    saldo: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    cliente: Mapped["Cliente"] = relationship(
        "Cliente", back_populates="cuenta_corriente"
    )
    movimientos: Mapped[list["MovimientoCuentaCorriente"]] = relationship(
        "MovimientoCuentaCorriente",
        back_populates="cuenta",
        cascade="all, delete-orphan",
    )


class MovimientoCuentaCorriente(Base):
    """
    Movimiento de cuenta corriente de cliente.

    Tipos esperados:
    - VENTA: incrementa saldo (deuda)
    - PAGO: reduce saldo
    - AJUSTE: puede aumentar o disminuir según signo del monto
    """

    __tablename__ = "movimiento_cuenta_corriente"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cuenta_id: Mapped[int] = mapped_column(
        ForeignKey("cuenta_corriente_cliente.id"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(16))
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    cuenta: Mapped["CuentaCorrienteCliente"] = relationship(
        "CuentaCorrienteCliente", back_populates="movimientos"
    )

