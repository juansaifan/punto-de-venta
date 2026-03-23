Módulo 1 — Dashboard
1. Objetivo
El Dashboard es el panel de control principal del sistema POS.
 Su función es ofrecer una visión operativa y gerencial inmediata del negocio, permitiendo identificar rápidamente:
desempeño de ventas
comportamiento horario
estado del negocio
alertas críticas de inventario
El dashboard es exclusivamente informativo.
 No permite operaciones de modificación ni transacciones.

2. Estructura del módulo
El Dashboard está dividido en dos columnas principales.
Dashboard
 ├─ Zona central (80%)
 │   ├─ KPIs principales
 │   ├─ Gráfico de ventas por hora
 │   └─ Alertas operativas
 │
 └─ Panel lateral (20%)
     └─ Tarjetas de estado del negocio


3. Zona central (80%)
Contiene la información principal de operación diaria.
3.1 KPIs principales
Tarjetas de indicadores clave de desempeño.
Objetivo: ofrecer una lectura rápida del estado comercial del día y del período actual.
Indicadores incluidos:


Cada KPI incluye:

valor principal
comparación vs periodo anterior
variación porcentual


3.2 Gráfico principal — Ventas del día por hora
Gráfico combinado que permite analizar el comportamiento de ventas durante la jornada.
Tipo de gráfico:
Barras → cantidad de ventas
Línea → importe vendido

Configuración:



Objetivo del gráfico:
identificar picos de ventas
detectar horas valle
evaluar comportamiento del flujo de clientes
Este gráfico se alimenta de datos provenientes del módulo Facturación / Ventas.

3.3 Alertas operativas
Sección destinada a advertencias críticas relacionadas con inventario.
Está compuesta por dos tablas independientes.

3.3.1 Productos próximos a vencer
Lista de productos con fecha de vencimiento cercana.
Campos mostrados:
Objetivo:
evitar pérdidas por vencimiento
priorizar rotación de productos
Origen de datos:
Inventario
Gestión de lotes


3.3.2 Alertas de reposición de stock
Lista de productos cuyo stock se encuentra por debajo del mínimo definido.
Campos mostrados:
Objetivo:
prevenir quiebres de stock
facilitar planificación de compras
Origen de datos:
Inventario
Control de stock mínimo


4. Panel lateral (20%)
Panel informativo de estado del negocio.
Contiene tarjetas analíticas y proyecciones.

4.1 Salud del negocio
Indicador general del estado financiero diario.
Incluye:
estado del negocio (verde / amarillo / rojo)
ingresos actuales
punto de equilibrio
objetivo diario

Este indicador evalúa si los ingresos actuales superan el punto de equilibrio.

4.2 Promedio de ventas por día
Promedio histórico calculado a partir de datos recientes.
Indicadores:
tickets promedio por día
ingresos promedio por día


4.3 Promedio para este día de la semana
Análisis histórico basado en comportamiento semanal.
Ejemplo:
promedio de tickets los martes
promedio de ingresos los martes
Permite comparar el desempeño actual contra el histórico del mismo día.

4.4 Pronóstico de ventas (hoy)
Estimación del resultado final del día basada en el ritmo actual de ventas.
Incluye:
ingresos pronosticados
porcentaje de cumplimiento

4.5 Punto de equilibrio
Indicador que muestra el progreso hacia cubrir los costos diarios.
Incluye:
valor del punto de equilibrio
porcentaje de cumplimiento

4.6 Ganancia actual
Resultado operativo calculado como:
ganancia = ingresos actuales − punto de equilibrio

4.7 Objetivos de ganancia
Metas financieras configuradas.
Incluye:
objetivo diario
objetivo semanal
objetivo mensual

4.8 Margen promedio del día
Estimación del margen de ganancia obtenido en la jornada.
Incluye:
margen promedio
tendencia vs día anterior

5. Frecuencia de actualización
Los datos del dashboard deben actualizarse mediante:
refresh automático cada 60–120 segundos
o mediante evento generado al registrar una venta.

6. Origen de datos
El Dashboard consume información de múltiples módulos:

7. Permisos
El acceso al Dashboard depende del rol del usuario.

8. Consideraciones de diseño
El dashboard está optimizado para:
lectura rápida
monitoreo en tiempo real
pantallas POS de mostrador
supervisión gerencial
Se prioriza:
claridad visual
información crítica
baja interacción

