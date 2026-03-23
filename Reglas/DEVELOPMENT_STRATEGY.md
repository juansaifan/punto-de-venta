# DEVELOPMENT_STRATEGY.md — Estrategia General de Desarrollo Autónomo

## Propósito
Documento reutilizable que define cómo debe avanzar un sistema de software durante desarrollo autónomo.

Objetivos:
- maximizar progreso por iteración
- evitar micro‑tareas innecesarias
- mantener coherencia arquitectónica
- permitir reutilización en distintos proyectos

---

# Principios

## 1. Progreso tangible
Cada iteración debe producir resultados observables:
- nuevas funcionalidades
- endpoints funcionales
- servicios de dominio
- tests ejecutables
- mejoras estructurales

Evitar iteraciones que solo generen análisis.

---

## 2. Bloques funcionales
Preferir implementar bloques completos:

servicio → endpoint → tests

en lugar de dividir en micro‑cambios.

---

## 3. Completar módulos
Estrategia recomendada:

1. iniciar módulo
2. completar funcionalidades principales
3. estabilizar
4. auditar
5. pasar al siguiente módulo

---

## 4. Prioridad de desarrollo

Orden típico de sistemas:

1. núcleo operativo
2. control financiero o transaccional
3. analítica y reportes
4. configuración
5. integraciones externas

---

## 5. Integración temprana
Los módulos deben integrarse tan pronto como sea posible.

Evitar desarrollar subsistemas completamente aislados.

---

## 6. Tests tempranos
Toda funcionalidad relevante debe incluir pruebas que validen:

- comportamiento esperado
- casos de error
- integraciones básicas

---

# Flujo de trabajo recomendado

analizar módulo
↓
identificar funcionalidades faltantes
↓
implementar servicios
↓
exponer APIs
↓
crear tests
↓
ejecutar tests
↓
actualizar estado del módulo

---

# Uso con agentes autónomos

Un agente puede ejecutar varios pasos consecutivos dentro de la misma iteración
si pertenecen al mismo módulo o funcionalidad.