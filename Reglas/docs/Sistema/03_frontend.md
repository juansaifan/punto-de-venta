# 03 — Frontend

## Dos Frontends en el Proyecto

El proyecto contiene dos frontends en estados muy distintos:

| Frontend | Carpeta | Estado |
|---|---|---|
| **Flutter (principal)** | `Devs/frontend_flutter/` | En desarrollo activo |
| **Web HTML/JS (legacy)** | `Devs/frontend/` | Incompleto / experimental |

---

## Frontend Flutter (Principal)

### Tecnologías
- Flutter SDK ≥ 3.3.0 / Dart
- Dependencias: `http`, `shared_preferences`, `cupertino_icons`
- Target: **Windows desktop** (build en `windows/`)

### Estructura de Carpetas

```
frontend_flutter/lib/
├── main.dart              # Entry point, ShellPrincipal (navegación)
├── core/
│   ├── api/               # Clientes HTTP hacia el backend
│   ├── config/            # Configuración (URL base del backend, etc.)
│   └── theme/
│       └── app_theme.dart # Tema visual del POS
├── modules/               # Pantallas por dominio
│   ├── dashboard/
│   │   └── dashboard_screen.dart
│   ├── caja/
│   │   └── caja_screen.dart
│   ├── inventario/
│   │   └── inventario_screen.dart
│   ├── ventas/
│   │   └── ventas_screen.dart
│   └── pesables/
│       └── pesables_screen.dart
└── widgets/
    ├── primary_button.dart
    ├── responsive_scaffold.dart
    └── selector_cliente_como_ventas.dart
```

### Pantallas Implementadas

| Índice | Módulo | Componente |
|---|---|---|
| 0 | Dashboard | `PantallaDashboard` |
| 1 | Ventas (POS) | `PantallaVentas` (pantalla principal al iniciar) |
| 2 | Pesables | `PantallaPesables` |
| 3 | Caja | `PantallaCaja` |
| 4 | Operaciones Comerciales | `_PantallaPlaceholder` |
| 5 | Tesorería | `_PantallaPlaceholder` |
| 6 | Finanzas | `_PantallaPlaceholder` |
| 7 | Inventario | `PantallaInventario` |
| 8 | Personas | `_PantallaPlaceholder` |
| 9 | Reportes | `_PantallaPlaceholder` |
| 10 | Integraciones | `_PantallaPlaceholder` |
| 11 | Configuraciones | `_PantallaPlaceholder` |

Los módulos con `_PantallaPlaceholder` muestran el mensaje _"Submódulo en preparación frontend"_.

### Navegación

La navegación principal se controla en `ShellPrincipal` (StatefulWidget en `main.dart`):
- Mantiene un `int _indice` que representa la pantalla activa.
- `DisenoResponsivoPos` (de `responsive_scaffold.dart`) provee el scaffold con panel lateral y área de contenido.
- El cambio de pantalla no usa router declarativo (Navigator 2.0) — es un `setState` simple.

### Manejo de Estado

- No hay gestor de estado global identificado (no hay Provider, Riverpod, Bloc, etc.)
- Cada pantalla maneja su propio estado con `StatefulWidget`
- `shared_preferences` disponible en dependencias pero su uso específico no es evidente en los archivos analizados

### Integración con Backend

- Los clientes HTTP están en `lib/core/api/`
- Se usa el paquete `http` de Dart para llamadas REST
- La URL base del backend está en `lib/core/config/`
- El detalle interno de estos archivos no fue leído (no expuestos en el análisis)

### Widget Destacado: `selector_cliente_como_ventas.dart`
Componente de selección de cliente reutilizable (probablemente usado en pantalla de ventas para asociar cliente a la venta).

---

## Frontend Web HTML/JS (Legacy / Experimental)

### Archivos
```
Devs/frontend/
├── index.html
├── app.js
├── mock_dashboard_api.js   # Mock local del API de dashboard
├── style.css
├── components/             # (vacío — solo .gitkeep)
└── ui/                     # (vacío — solo .gitkeep)
```

### Estado
- Las carpetas `components/` y `ui/` están vacías (solo placeholder `.gitkeep`)
- `mock_dashboard_api.js` sugiere que hubo trabajo experimental con datos mockeados
- **No está integrado con el backend real**
- El README del proyecto lista este frontend como "(pendiente)"

---

## Consideraciones para Desarrollo

1. La pantalla de inicio al lanzar la app es **Ventas** (índice 1), no Dashboard.
2. Los módulos con placeholder son candidatos directos para implementación futura.
3. La arquitectura no establece contratos formales (interfaces/abstracciones) entre pantallas y clientes API — todo es directo.
4. No hay tests de widget implementados más allá del `widget_test.dart` generado por Flutter por defecto.
