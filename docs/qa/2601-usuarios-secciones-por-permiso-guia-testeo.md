# Guía de testeo — Secciones del alta de usuarios por rol (PR #2601)

> Para QA. Se prueba en el entorno donde esté desplegado el PR #2601.
> Tiempo estimado: 20 minutos de preparación + 5 minutos por rol (≈ 1 hora en total).

## Qué cambió

Antes, quien podía dar de alta usuarios veía **todas** las tarjetas de la pantalla
**Administración → Usuarios → Agregar**, fuera o no de su programa.

Ahora cada tarjeta de un programa se ve **solo si el rol tiene el permiso de esa
sección**. Las tarjetas generales las ve siempre cualquiera que pueda dar de alta
usuarios.

| Tarjeta | Tipo | Permiso que la habilita |
|---|---|---|
| Datos Personales | General | — (siempre) |
| Datos de Acceso | General | — (siempre) |
| Permisos y Roles | General | — (siempre) |
| Alcance territorial | General | — (siempre) |
| Acceso SISOC - Mobile (y "Usuarios mobile creados por este usuario") | Comedores | Usuarios - Sección Acceso SISOC Mobile (Comedores) |
| Acceso SISOC - Mobile Territorial comedor | Comedores | Usuarios - Sección Mobile Territorial comedor |
| Equipos técnicos (Comedores) | Comedores | Usuarios - Sección Equipos técnicos (Comedores) |
| Acceso SISOC - Mobile DataCalle | DataCalle | Usuarios - Sección Acceso SISOC Mobile DataCalle |
| Administración de accesos | Administración | Usuarios - Sección Administración de accesos |

> "Configuración Adicional" ya no existe: se dividió en **Alcance territorial**,
> **Equipos técnicos (Comedores)** y **Administración de accesos**.

---

## Parte 1 — Preparación (con un usuario Admin)

### 1.1 Crear el grupo de destino

1. Ir a **Administración → Grupos → Agregar**.
2. Nombre: `QA - Destino`. Sin permisos.
3. Guardar.

### 1.2 Crear un rol (grupo) por sección

Crear estos 6 grupos. **Todos** llevan estos 3 permisos base:
`Can view user`, `Can add user`, `Can change user`.

Además, cada uno lleva **un solo** permiso de sección:

| Grupo a crear | Permiso de sección que se le agrega |
|---|---|
| `QA - Sección Mobile Comedores` | Usuarios - Sección Acceso SISOC Mobile (Comedores) |
| `QA - Sección Territorial` | Usuarios - Sección Mobile Territorial comedor |
| `QA - Sección Equipos técnicos` | Usuarios - Sección Equipos técnicos (Comedores) |
| `QA - Sección DataCalle` | Usuarios - Sección Acceso SISOC Mobile DataCalle |
| `QA - Sección Administración` | Usuarios - Sección Administración de accesos |
| `QA - Sin secciones` | ninguno (grupo de control) |

> Tip: en el buscador de permisos, escribir "Usuarios - Sección" filtra los 5.

### 1.3 Crear un usuario QA por rol

Crear 6 usuarios desde **Usuarios → Agregar**, uno en cada grupo:

| Usuario | Grupo |
|---|---|
| `qa_mobile` | QA - Sección Mobile Comedores |
| `qa_territorial` | QA - Sección Territorial |
| `qa_equipos` | QA - Sección Equipos técnicos |
| `qa_datacalle` | QA - Sección DataCalle |
| `qa_admin` | QA - Sección Administración |
| `qa_sin_seccion` | QA - Sin secciones |

Para **cada** uno:

1. Tipo de usuario: Interno. Contraseña conocida.
2. **No** marcar "Es usuario provincial".
3. En **Administración de accesos → Grupos que puede asignar**: elegir `QA - Destino`.
   (Sin esto el usuario QA solo se ve a sí mismo y no puede editar a nadie.)

### 1.4 Crear los usuarios destino (los que se van a editar)

Crear 4 usuarios, todos con el grupo `QA - Destino` en **Permisos y Roles → Grupos**:

| Usuario | Configuración que se le carga |
|---|---|
| `destino_mobile` | Acceso SISOC - Mobile: marcar "Habilitar acceso a SISOC - Mobile" y asociarle 1 espacio |
| `destino_territorial` | Territorial comedor: marcar "Habilitar acceso a SISOC - Mobile" y provincia Córdoba |
| `destino_datacalle` | DataCalle: marcar "Habilitar acceso a SISOC - Mobile DataCalle", rol Relevador, provincia Córdoba |
| `destino_backoffice` | Equipos técnicos: "Es Coordinador de Equipo Técnico" + 1 dupla. Administración de accesos: permiso directo `Can view user` |

Anotar la configuración de cada uno: al final se verifica que siga igual.

---

## Parte 2 — Prueba por rol

Para cada rol:

1. Cerrar sesión y entrar con el usuario QA.
2. Ir a **Usuarios → Agregar** y anotar qué tarjetas aparecen.
3. Crear un usuario de prueba (`alta_<rol>`, por ejemplo `alta_mobile`) usando solo lo que se ve.
4. Ir a **Usuarios**, editar cada `destino_*`, cambiar solo el **Nombre** y guardar.

Las tarjetas generales (Datos Personales, Datos de Acceso, Permisos y Roles,
Alcance territorial) tienen que aparecer **siempre**. Abajo va solo lo que cambia.

### Rol A — `qa_mobile` (Mobile Comedores)

- **Tiene que ver:** Acceso SISOC - Mobile.
- **No tiene que ver:** Territorial comedor, Equipos técnicos, DataCalle, Administración de accesos.
- **Probar:** crear `alta_mobile` con "Habilitar acceso a SISOC - Mobile" y 1 espacio → se guarda bien.
- **Probar:** marcar "Habilitar acceso a SISOC - Mobile" → se ocultan Permisos y Roles y Alcance territorial.
- **Al editar `destino_mobile`:** ve la tarjeta mobile con su espacio cargado.

### Rol B — `qa_territorial` (Territorial comedor)

- **Tiene que ver:** Acceso SISOC - Mobile Territorial comedor.
- **No tiene que ver:** Acceso SISOC - Mobile, Equipos técnicos, DataCalle, Administración de accesos.
- **Probar:** crear `alta_territorial` como territorial con 1 provincia → se guarda bien.
- **Al editar `destino_territorial`:** ve la provincia Córdoba cargada.

### Rol C — `qa_equipos` (Equipos técnicos)

- **Tiene que ver:** Equipos técnicos (Comedores).
- **No tiene que ver:** Acceso SISOC - Mobile, Territorial comedor, DataCalle, Administración de accesos.
- **Probar:** crear `alta_equipos` como Coordinador de Equipo Técnico **sin** dupla → error "Seleccione al menos una dupla".
- **Probar:** agregarle 1 dupla → se guarda bien.

### Rol D — `qa_datacalle` (DataCalle)

- **Tiene que ver:** Acceso SISOC - Mobile DataCalle.
- **No tiene que ver:** Acceso SISOC - Mobile, Territorial comedor, Equipos técnicos, Administración de accesos.
- **Probar:** crear `alta_datacalle` como Relevador con 1 provincia → se guarda bien.
- **Al editar `destino_datacalle`:** ve rol Relevador y provincia Córdoba.

### Rol E — `qa_admin` (Administración de accesos)

- **Tiene que ver:** Administración de accesos (Permisos directos, Grupos que puede asignar, Roles que puede asignar).
- **No tiene que ver:** Acceso SISOC - Mobile, Territorial comedor, Equipos técnicos, DataCalle.
- **Probar:** crear `alta_admin` con un permiso directo → se guarda bien.
- **Al editar `destino_backoffice`:** ve el permiso directo `Can view user`.

### Rol F — `qa_sin_seccion` (control)

- **Tiene que ver:** solo las 4 tarjetas generales.
- **No tiene que ver:** ninguna de las 5 secciones.
- **Probar:** crear `alta_sin_seccion` con nombre, usuario y contraseña → se guarda bien.

---

## Parte 3 — Lo oculto no se pierde (la prueba más importante)

En la Parte 2 cada rol editó los 4 `destino_*` cambiando solo el nombre, incluso
los que tienen configuración de secciones que ese rol **no ve**.

Entrar con **Admin** y abrir cada `destino_*`:

| Usuario | Tiene que seguir teniendo |
|---|---|
| `destino_mobile` | Acceso mobile activo y su espacio |
| `destino_territorial` | Territorial activo, provincia Córdoba |
| `destino_datacalle` | DataCalle activo, rol Relevador, provincia **Córdoba** |
| `destino_backoffice` | Coordinador de Equipo Técnico + su dupla + permiso directo `Can view user` |

Si algo se borró o cambió → **bug**. Anotar qué rol hizo la última edición.

---

## Parte 4 — Roles que ya existían (regresión)

Entrar con un usuario de cada rol real y abrir **Usuarios → Agregar**:

| Rol real | Tiene que ver (además de las generales) |
|---|---|
| Admin | Las 5 secciones |
| Usuarios - Gestor Comedores (nuevo) | Mobile, Territorial, Equipos técnicos |
| Coordinador DataCalle | Solo DataCalle |
| Administrador DataCalle | Solo DataCalle |
| CDI - Referente centro / SIMEPI | Ninguna sección |

> Cambio esperado: **Coordinador y Administrador DataCalle ya no ven** las secciones de
> Comedores ni Administración de accesos. **CDI/SIMEPI ya no ven** Territorial ni DataCalle.
> Si alguien pregunta "¿dónde quedó X?", es por esto y no es un bug.

---

## Planilla de resultados

| # | Prueba | OK / Falla | Nota |
|---|---|---|---|
| A | qa_mobile: tarjetas correctas + alta | | |
| B | qa_territorial: tarjetas correctas + alta | | |
| C | qa_equipos: tarjetas correctas + alta | | |
| D | qa_datacalle: tarjetas correctas + alta | | |
| E | qa_admin: tarjetas correctas + alta | | |
| F | qa_sin_seccion: solo generales + alta | | |
| 3 | Los 4 destino_* conservan su configuración | | |
| 4 | Roles existentes ven lo esperado | | |

Al reportar una falla: usuario QA, pantalla, qué esperabas ver y qué viste (con captura).
