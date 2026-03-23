"""Dependencias comunes de la API."""
from collections.abc import Generator

from sqlalchemy.orm import Session

from backend.database.sesion import obtener_motor, obtener_sesion


def get_db() -> Generator[Session, None, None]:
    """Provee una sesión de BD por request; cierra al finalizar."""
    motor = obtener_motor()
    SesionLocal = obtener_sesion(motor)
    sesion = SesionLocal()
    try:
        yield sesion
        sesion.commit()
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()
