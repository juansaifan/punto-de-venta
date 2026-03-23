Módulo 6 — Personas (v3)
1. Objetivo
El módulo Personas gestiona todas las entidades humanas o institucionales que interactúan con el negocio o con el sistema, centrándose en la **identidad** y los **roles**.
Estas entidades incluyen:
clientes
proveedores
empleados
usuarios del sistema
Centralizar esta información permite:
evitar duplicación de datos
mantener trazabilidad de operaciones
controlar accesos al sistema
asociar operaciones comerciales a personas específicas
Este módulo se integra con:

2. Estructura del módulo
Personas
│
├─ Personas
├─ Contactos
├─ Clientes
├─ Proveedores
├─ Empleados
├─ Usuarios del sistema
└─ Roles y permisos
El diseño separa la entidad base (persona) de los distintos roles que puede cumplir dentro del sistema.

3. Submódulo — Personas
Objetivo
Representa la entidad base del módulo.
Todas las demás entidades derivan de esta estructura.
Una persona puede representar:
persona física
empresa
organización

Datos principales
nombre
apellido / razón social
tipo de persona
tipo de documento
número de documento
CUIT / CUIL
estado
fecha de alta
observaciones

Tipos de persona
persona física
persona jurídica

Modelo de roles
Una misma persona puede cumplir múltiples roles.
Ejemplo:
Persona
  ├ Cliente
  ├ Proveedor
  └ Usuario del sistema
Esto evita duplicación de registros.

4. Submódulo — Contactos
Objetivo
Permitir registrar múltiples contactos asociados a una persona.
Esto es especialmente útil para empresas o proveedores.

Ejemplo
Proveedor: Distribuidora Norte

Contactos
  ├ Administración
  ├ Ventas
  └ Logística

Datos registrados
persona asociada
nombre del contacto
cargo
teléfono
email
observaciones

5. Submódulo — Clientes
Objetivo
Gestionar los clientes del negocio desde el punto de vista de **identidad y configuración comercial**.
Los clientes pueden asociarse a operaciones comerciales dentro del módulo Punto de Venta / Ventas, pero la **gestión financiera de deuda, cuentas corrientes y morosidad** se realiza en el submódulo de Tesorería / Cuentas Corrientes (no en Personas).

Funciones
Permite:
registrar clientes
editar clientes
consultar clientes
asociar clientes a ventas

Segmentación de clientes
Los clientes pueden clasificarse en distintos segmentos.
Ejemplo:
cliente ocasional
cliente frecuente
cliente mayorista
cliente corporativo
Esto permite:
aplicar promociones
aplicar listas de precios
analizar ventas

Datos registrados
persona asociada
segmento de cliente
condición de pago
límite de crédito (capacidad de crédito conceptual del cliente; la aplicación del límite y la deuda viva se maneja en Tesorería / Cuentas Corrientes)
estado
fecha de alta
observaciones

6. Submódulo — Proveedores
Objetivo
Gestionar los proveedores del negocio.
Este submódulo se integra principalmente con Inventario.

Funciones
Permite:
registrar proveedores
editar proveedores
consultar proveedores
asociar proveedores a productos

Datos registrados
persona asociada
CUIT
condiciones comerciales
condiciones de pago
lista de precios
estado

Información logística opcional
frecuencia de entrega
mínimo de compra
tiempo estimado de entrega
Esto puede utilizarse para optimizar reposiciones.

7. Submódulo — Empleados
Objetivo
Registrar el personal que trabaja en el negocio.
Esto permite asociar operaciones con el empleado que las realizó.

Funciones
Permite:
registrar empleados
editar empleados
consultar empleados
asociar empleados a usuarios del sistema

Datos registrados
persona asociada
documento
cargo
fecha de ingreso
estado

Jerarquía organizacional
El sistema permite definir jerarquías internas.
Ejemplo:
Supervisor
  ├ Cajero
  └ Vendedor
Esto puede utilizarse para:
control de permisos
organización del personal
auditoría de operaciones

8. Submódulo — Usuarios del sistema
Objetivo
Gestionar las cuentas de acceso al sistema.
Un usuario representa una identidad digital dentro del sistema POS.

Funciones
Permite:
crear usuario
editar usuario
desactivar usuario
asignar roles

Datos registrados
usuario
contraseña
persona asociada
rol asignado
estado
último acceso

9. Submódulo — Roles y permisos
Objetivo
Controlar el acceso a las funcionalidades del sistema.

Roles del sistema
Ejemplos de roles:
administrador
supervisor
cajero
vendedor
operador de inventario

Permisos
Los permisos determinan qué acciones puede realizar cada rol.
Ejemplo:
crear venta
anular venta
editar inventario
modificar precios
generar reportes
gestionar usuarios

10. Integración con otros módulos

- Punto de Venta / Ventas:
  - Usa `Persona` + rol `Cliente` para asociar ventas a personas concretas.
- Inventario:
  - Usa rol `Proveedor` para asociar productos y compras.
- Tesorería / Cuentas Corrientes:
  - Usa rol `Cliente` y su `límite de crédito` para construir la cartera de clientes, registrar deuda (VENTA a crédito, PAGO, AJUSTE) y calcular morosidad.  
  - La lógica de saldo de cuenta corriente, aging y tramos de morosidad **no** pertenece al módulo Personas, sino a Tesorería.

Evaluación del módulo Personas (v3)
La arquitectura final del módulo cubre correctamente:
identidad de personas
gestión de clientes (como rol y configuración, incluyendo límite de crédito)
gestión de proveedores
gestión de empleados
usuarios del sistema
control de accesos
El diseño mantiene un modelo limpio basado en persona → roles, lo que permite escalar el sistema sin duplicar información. La gestión de deuda y cuentas corrientes se delega explícitamente a Tesorería / Cuentas Corrientes.
