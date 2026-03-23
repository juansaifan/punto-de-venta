"""
Aplicación FastAPI del Sistema Punto de Venta.
Ejecutar desde Devs: uvicorn backend.api.app:app --reload --port 8000
"""
import sys
from pathlib import Path

# Asegurar que Devs esté en el path
devs_root = Path(__file__).resolve().parent.parent.parent
if str(devs_root) not in sys.path:
    sys.path.insert(0, str(devs_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import inicializar_bd, obtener_motor
from backend.api.routers import productos as router_productos
from backend.api.routers import personas as router_personas
from backend.api.routers import ventas as router_ventas
from backend.api.routers import inventario as router_inventario
from backend.api.routers import caja as router_caja
from backend.api.routers import reportes as router_reportes
from backend.api.routers import dashboard as router_dashboard
from backend.api.routers import finanzas as router_finanzas
from backend.api.routers import compras as router_compras
from backend.api.routers import configuracion as router_configuracion
from backend.api.routers import integraciones as router_integraciones
from backend.api.routers import cuentas_corrientes as router_cuentas_corrientes
from backend.api.routers import solicitudes_compra as router_solicitudes_compra
from backend.api.routers import auditoria_eventos as router_auditoria_eventos
from backend.consumers import cuentas_corrientes_auditoria as consumer_cc_auditoria
from backend.consumers import inventario_auditoria as consumer_inventario_auditoria
from backend.api.routers import operaciones_comerciales as router_operaciones_comerciales
from backend.consumers import operaciones_comerciales_auditoria as consumer_ops_auditoria
from backend.consumers import finanzas_auditoria as consumer_finanzas_auditoria
from backend.api.routers import pesables as router_pesables


def _crear_app() -> FastAPI:
    app = FastAPI(
        title="Sistema Punto de Venta – API",
        version="0.1.0",
    )

    @app.on_event("startup")
    def startup():
        motor = obtener_motor()
        inicializar_bd(motor)
        consumer_cc_auditoria.registrar_consumidores()
        consumer_inventario_auditoria.registrar_consumidores()
        consumer_ops_auditoria.registrar_consumidores()
        consumer_finanzas_auditoria.registrar_consumidores()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def raiz():
        return {"mensaje": "Sistema Punto de Venta API", "docs": "/docs"}

    @app.get("/health")
    def health():
        return {"estado": "ok"}

    app.include_router(router_productos.router, prefix="/api")
    app.include_router(router_personas.router, prefix="/api")
    app.include_router(router_ventas.router, prefix="/api")
    app.include_router(router_inventario.router, prefix="/api")
    app.include_router(router_caja.router, prefix="/api")
    app.include_router(router_reportes.router, prefix="/api")
    app.include_router(router_dashboard.router, prefix="/api")
    app.include_router(router_finanzas.router, prefix="/api")
    app.include_router(router_compras.router, prefix="/api")
    app.include_router(router_configuracion.router, prefix="/api")
    app.include_router(router_integraciones.router, prefix="/api")
    app.include_router(router_cuentas_corrientes.router, prefix="/api")
    app.include_router(router_auditoria_eventos.router, prefix="/api")
    app.include_router(router_solicitudes_compra.router, prefix="/api")
    app.include_router(router_operaciones_comerciales.router, prefix="/api")
    app.include_router(router_pesables.router, prefix="/api")

    return app


app = _crear_app()
