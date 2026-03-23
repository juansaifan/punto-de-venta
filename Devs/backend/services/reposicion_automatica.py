"""Automatización de reposición de inventario.

Implementa la transferencia automática DEPOSITO → GONDOLA cuando:
- Configuración inventario `transferencias_automaticas` está habilitada.
- Un producto inventariable está por debajo del mínimo en GONDOLA.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from backend.models.producto import Producto, TipoProducto
from backend.services import alertas_inventario as svc_alertas
from backend.services import configuracion as svc_configuracion
from backend.services import inventario as svc_inventario
from backend.services import solicitudes_compra as svc_solicitudes


def ejecutar_reposicion_automatica(
    sesion: Session,
    *,
    dias_vencimiento: int = 7,
    solo_activos: bool = True,
    max_items: int = 100,
) -> dict[str, Any]:
    cfg = svc_configuracion.get_configuracion_inventario(sesion)
    if not bool(cfg.get("transferencias_automaticas", False)):
        return {"ejecutada": False, "motivo": "transferencias_automaticas deshabilitado", "transferencias": []}

    alertas = svc_alertas.detectar_alertas(
        sesion,
        ubicacion="GONDOLA",
        dias_vencimiento=dias_vencimiento,
        solo_activos=solo_activos,
        emitir_eventos=False,
    )

    transferencias: list[dict[str, Any]] = []
    pedidos: list[dict[str, Any]] = []
    for item in alertas["stock_bajo"][: max(0, int(max_items))]:
        producto_id = int(item["producto_id"])

        prod = sesion.get(Producto, producto_id)
        if prod is None or prod.tipo_producto != TipoProducto.INVENTARIABLE.value:
            continue

        minimo = Decimal(str(item["minimo"]))
        cantidad_gondola = Decimal(str(item["cantidad"]))
        deficit = minimo - cantidad_gondola
        if deficit <= 0:
            continue

        stock_deposito = svc_inventario.obtener_cantidad_stock(
            sesion, producto_id, ubicacion="DEPOSITO"
        )
        mover = min(deficit, stock_deposito)

        if mover > 0:
            movs = svc_inventario.transferir_stock(
                sesion,
                producto_id=producto_id,
                cantidad=mover,
                origen="DEPOSITO",
                destino="GONDOLA",
                referencia="AUTO_REPOSICION",
            )
            transferencias.append(
                {
                    "producto_id": producto_id,
                    "cantidad_transferida": float(mover),
                    "mov_salida_id": movs["salida"].id,
                    "mov_entrada_id": movs["entrada"].id,
                }
            )

        faltante = deficit - mover
        if faltante > 0 and bool(cfg.get("pedidos_automaticos", False)):
            sol = svc_solicitudes.crear_solicitud_compra(
                sesion,
                referencia="AUTO_PEDIDO_REPOSICION",
                items=[
                    {
                        "producto_id": producto_id,
                        "cantidad": faltante,
                        "motivo": "Reposición automática: faltante en depósito",
                    }
                ],
            )
            pedidos.append({"solicitud_id": sol.id, "producto_id": producto_id, "cantidad_solicitada": float(faltante)})

    return {"ejecutada": True, "transferencias": transferencias, "pedidos": pedidos}

