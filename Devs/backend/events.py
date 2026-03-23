"""
Bus de eventos in-process (EVENTOS.md).
Permite emitir eventos y suscribir callbacks sin acoplar módulos.
"""
from collections import defaultdict
from typing import Any, Callable
import logging

logger = logging.getLogger(__name__)

_handlers: dict[str, list[Callable[..., None]]] = defaultdict(list)


def subscribe(event_name: str, callback: Callable[..., None]) -> None:
    """Registra un callback para el evento dado."""
    _handlers[event_name].append(callback)


def emit(event_name: str, payload: dict[str, Any]) -> None:
    """
    Dispara el evento con el payload. Ejecuta todos los handlers registrados.
    Si un handler lanza, se registra el error y se continúa con el resto.
    """
    for fn in _handlers[event_name]:
        try:
            fn(payload)
        except Exception as e:
            logger.exception("Error en handler de %s: %s", event_name, e)


def clear_handlers(event_name: str | None = None) -> None:
    """Quita todos los handlers (solo para tests). Si event_name es None, limpia todos los eventos."""
    if event_name is None:
        _handlers.clear()
    else:
        _handlers[event_name].clear()
