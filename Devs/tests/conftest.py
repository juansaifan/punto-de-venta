"""Fixtures compartidos para tests."""
import sys
from pathlib import Path

# Raíz del proyecto (Devs)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.base import Base
from backend.database.sesion import inicializar_bd
from backend.api.app import app
from backend.api.deps import get_db


def _crear_engine_tests():
    """
    Crea un engine SQLite en memoria por test, compartido entre conexiones del mismo test
    (TestClient abre múltiples conexiones). StaticPool mantiene una única conexión viva.
    """
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Cliente HTTP con BD SQLite en memoria; BD limpia por test."""
    engine = _crear_engine_tests()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        sesion = TestingSessionLocal()
        try:
            yield sesion
            sesion.commit()
        except Exception:
            sesion.rollback()
            raise
        finally:
            sesion.close()

    inicializar_bd(engine)  # registra modelos y crea tablas
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


@pytest.fixture
def producto_datos() -> dict:
    """Datos mínimos para crear un producto."""
    return {
        "sku": "TEST-001",
        "nombre": "Producto de prueba",
        "precio_venta": "10.50",
        "stock_minimo": "2",
        "activo": True,
    }


@pytest.fixture
def persona_datos() -> dict:
    """Datos mínimos para crear una persona."""
    return {
        "nombre": "Juan",
        "apellido": "Pérez",
        "documento": "12345678",
        "telefono": "999888777",
        "activo": True,
    }
