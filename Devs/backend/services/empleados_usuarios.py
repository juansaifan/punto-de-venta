"""Servicios de integración Empleados ↔ Usuarios del sistema.

Regla: el vínculo real se define a través de `persona_id`.
Un Empleado pertenece a una Persona. Un Usuario (del sistema) se asocia opcionalmente a una Persona.
Por lo tanto, "vincular empleado a usuario" equivale a asegurar que:
- usuario.persona_id == empleado.persona_id

Con reglas de Personas:
- Una Persona no puede tener múltiples usuarios.
- Un Usuario ya vinculado no puede reasignarse sin desvincular explícitamente.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models.persona import Empleado
from backend.models.usuario import Usuario
from backend.services import personas_usuarios as svc_personas_usuarios


def vincular_empleado_a_usuario(
    sesion: Session,
    *,
    empleado_id: int,
    usuario_id: int,
) -> Usuario:
    empleado = sesion.get(Empleado, empleado_id)
    if empleado is None:
        raise ValueError("Empleado no encontrado")

    # Reutiliza las reglas de negocio del vínculo Persona ↔ Usuario
    return svc_personas_usuarios.asignar_persona_a_usuario(
        sesion, usuario_id=usuario_id, persona_id=empleado.persona_id
    )


def obtener_usuario_de_empleado(
    sesion: Session,
    *,
    empleado_id: int,
) -> Usuario | None:
    empleado = sesion.get(Empleado, empleado_id)
    if empleado is None:
        raise ValueError("Empleado no encontrado")

    return (
        sesion.query(Usuario)
        .where(Usuario.persona_id == empleado.persona_id)
        .order_by(Usuario.id.asc())
        .first()
    )


def desvincular_empleado_de_usuario(
    sesion: Session,
    *,
    empleado_id: int,
    usuario_id: int,
) -> Usuario:
    empleado = sesion.get(Empleado, empleado_id)
    if empleado is None:
        raise ValueError("Empleado no encontrado")

    usuario = sesion.get(Usuario, usuario_id)
    if usuario is None:
        raise ValueError("Usuario no encontrado")
    if usuario.persona_id != empleado.persona_id:
        raise ValueError("El usuario no está vinculado a este empleado")

    return svc_personas_usuarios.asignar_persona_a_usuario(
        sesion, usuario_id=usuario_id, persona_id=None
    )

