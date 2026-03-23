"""Servicios de integración Personas ↔ Usuarios del sistema.

Este submódulo mantiene la frontera:
- Personas: identidad y roles.
- Configuración: gestión de usuarios/roles/permisos.

Aquí se implementa el vínculo `Usuario.persona_id` (asociación opcional).
"""

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.persona import Persona
from backend.models.usuario import Usuario


def asignar_persona_a_usuario(
    sesion: Session,
    *,
    usuario_id: int,
    persona_id: Optional[int],
) -> Usuario:
    """Asigna (o desasigna) una persona a un usuario."""
    usuario = sesion.get(Usuario, usuario_id)
    if usuario is None:
        raise ValueError("Usuario no encontrado")

    if persona_id is not None:
        persona = sesion.get(Persona, persona_id)
        if persona is None:
            raise ValueError("Persona no encontrada")

        # Regla de negocio (docs Módulo Personas: "persona asociada"):
        # una Persona no debe tener múltiples usuarios.
        existente = sesion.execute(
            select(Usuario.id).where(
                Usuario.persona_id == persona_id,
                Usuario.id != usuario_id,
            )
        ).first()
        if existente is not None:
            raise ValueError("La persona ya tiene un usuario asociado")

        # Evitar reasignaciones silenciosas: si el usuario ya está vinculado,
        # se debe desvincular explícitamente antes de re-vincular.
        if usuario.persona_id is not None and usuario.persona_id != persona_id:
            raise ValueError("El usuario ya está vinculado a otra persona")

    usuario.persona_id = persona_id
    sesion.add(usuario)
    sesion.flush()
    sesion.refresh(usuario)
    return usuario


def obtener_persona_de_usuario(
    sesion: Session,
    *,
    usuario_id: int,
) -> Persona:
    """Devuelve la persona asociada a un usuario."""
    usuario = sesion.get(Usuario, usuario_id)
    if usuario is None:
        raise ValueError("Usuario no encontrado")
    if usuario.persona_id is None:
        raise ValueError("Usuario sin persona asociada")
    persona = sesion.get(Persona, usuario.persona_id)
    if persona is None:
        raise ValueError("Persona no encontrada")
    return persona


def listar_usuarios_por_persona(
    sesion: Session,
    *,
    persona_id: int,
    limite: int = 100,
    offset: int = 0,
) -> Sequence[Usuario]:
    """Lista los usuarios asociados a una persona."""
    persona = sesion.get(Persona, persona_id)
    if persona is None:
        raise ValueError("Persona no encontrada")

    stmt = (
        select(Usuario)
        .where(Usuario.persona_id == persona_id)
        .order_by(Usuario.id.asc())
        .limit(limite)
        .offset(offset)
    )
    return sesion.scalars(stmt).all()

