# Sistema Punto de Venta – Código (Devs)

Código fuente del proyecto. La documentación y reglas están en `../Reglas/`.

## Estructura

```
Devs/
├── backend/
│   ├── api/          # Rutas FastAPI
│   ├── config/       # Configuración
│   ├── database/     # Base de datos, sesión, modelos
│   ├── models/       # Entidades de dominio
│   └── services/     # Lógica de negocio
├── frontend/         # (pendiente)
├── scripts/
├── docs/
├── logs/
├── requirements.txt
└── README.md
```

## Backend

- **Lenguaje:** Python 3.11+
- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.x
- **Base de datos:** SQLite por defecto (`data/pos.db`)

### Ejecutar API

Desde la carpeta `Devs`:

```bash
pip install -r requirements.txt
uvicorn backend.api.app:app --reload --port 8000
```

Documentación interactiva: http://localhost:8000/docs

### Variables de entorno

- `POS_DATABASE_URL`: URL de conexión (por defecto SQLite en `data/pos.db`)
- `POS_STORE_NAME`: Nombre del negocio
- `POS_DEBUG`: 1/0 para logs SQL
