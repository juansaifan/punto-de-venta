"""Motor de base de datos y sesión SQLAlchemy."""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config.settings import settings
from backend.database.base import Base


def _registrar_modelos():
    """Importa todos los modelos para que Base.metadata los conozca."""
    import backend.models  # noqa: F401


def obtener_motor():
    """Crea el motor de SQLAlchemy."""
    url = settings.database_url
    if url.startswith("sqlite"):
        ruta = url.replace("sqlite:///", "")
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    motor = create_engine(
        url,
        connect_args={"check_same_thread": False} if "sqlite" in url else {},
        echo=settings.debug,
    )
    if "sqlite" in url:
        from sqlalchemy import event

        @event.listens_for(motor, "connect")
        def configurar_sqlite(conn, record):
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
    return motor


def obtener_sesion(motor=None):
    """Devuelve una factoría de sesiones."""
    if motor is None:
        motor = obtener_motor()
    return sessionmaker(autocommit=False, autoflush=False, bind=motor)


def inicializar_bd(motor=None):
    """Crea todas las tablas en la base de datos."""
    _registrar_modelos()
    if motor is None:
        motor = obtener_motor()
    Base.metadata.create_all(bind=motor)
