# C04: aportes de Ciudadano 360 en React (C2, contrato ejecutable)

Fecha: 2026-11-10. Estado: **contrato ejecutable; sin implementación ni prueba
runtime**. Cierra el contrato pendiente de
[aportes Ciudadano 360](2026-10-27-2807-aportes-ciudadano360.md) (C2 elegida por el
responsable, ver ese plan y su registro de decisión) sobre el
[protocolo G1 v1](../../registro/decisiones/2026-11-06-2808-protocolo-g1-v1.md).
Fuente: HEAD `4ea95bcbe`. Entregas: C04.01 (proyección JSON por aporte, perfil L)
y C04.02 (renderers y disponibilidad C2, perfil L). Depende de C05.01 (ficha
Ciudadano 360 en React, dueño kernel), que aporta la página; C04 aporta los ocho
bloques de verticales dentro de ella.

## Recorrido nativo (se conserva intacto)

| Elemento | Fuente HEAD |
|---|---|
| Ficha `ciudadanos/ver/<pk>` (`ciudadanos_ver`) | `src/backends/kernel/ciudadanos/urls.py:78-80`; `views.py:206-255` `CiudadanosDetailView` (login, `ciudadanos.view_ciudadano`, `raise_exception=True`, ocho nombres en `CONTRIBUCIONES_RENDERIZADAS`, `views.py:212-221`) |
| Fragmento por aporte `ciudadanos/<pk>/contribucion/<nombre>/` | core `ciudadanos/urls.py:33-35`; en cada runtime `src/backends/config/backend_urls.py:27-31`; vista `ciudadanos/views.py:692-705` (login, mismo permiso, 404 si el nombre no es local o el ciudadano no existe) |
| Resolución local/remota | `src/backends/kernel/ciudadanos/detail_contributions.py:26-31` (mapa app), `:33` timeout 4 s, `:77-84` backend por `ciudadano_contributions`, `:87-107` GET sin redirects; red o status ≠ 200 → `""` |
| Registro por dueño | `src/backends/config/backends.json:110-112` (vat), `:139-141` (celiaquia), `:199-202` (cdf), `:317-322` (comedores) |
| Inserción en la ficha | `ciudadanos/templates/ciudadanos/ciudadano_detail.html:406` (`pwa_badges` en el `h1`), `:638` (`pwa`, tab datos), `:733` (`centrodefamilia_monto` con `default:'$0.00'`), `:1183` (tab `comedor`), `:1282` (tab `cdf`), `:1381` (tab `celiaquia`), `:1785` (tab `vat`), `:1790` (`comedores_colaboraciones`, fuera de los tabs) |

El fragmento HTML y su ruta quedan como están mientras exista la ficha Django.
La migración agrega rutas JSON; no cambia ni retira las existentes.

## Decisiones técnicas tomadas (con fundamento)

1. **Composición en el navegador, no fan-out en el kernel.** La ficha React pide
   cada aporte a `/api/web/<backend>/...` a través del proxy del core. Así cada
   llamada recibe la constancia G1 del proxy principal (no hace falta emitirla
   desde otra vía), cada tarjeta degrada sola y no hay llamada circular
   core→runtime→core. Alternativa descartada: que el kernel junte los ocho JSON
   en el servidor; exige firmar G1 fuera del proxy y suma la latencia de todos.
2. **Un endpoint por proveedor, no por bloque.** Los bloques que comparten
   contexto en la fuente salen en una sola respuesta: `comedores` +
   `comedores_colaboraciones`, `pwa` + `pwa_badges`, `centrodefamilia` +
   `centrodefamilia_monto`. Quedan cinco aportes web: `comedores`, `pwa`,
   `celiaquia`, `vat`, `centrodefamilia`. Evita consultar dos veces lo mismo y
   que el monto CDF y la tabla CDF se contradigan.
3. **La lista de aportes la da el kernel, nunca el cliente.** El JSON de la
   ficha (C05.01) incluye `aportes` con rutas relativas armadas en el servidor
   desde el registro existente. React solo llama a esas rutas.
4. **Vista genérica en el kernel, proyección en el dueño.** El kernel provee la
   vista y el registro (los runtimes ya importan kernel, como hoy con
   `contribucion_detalle_ciudadano`); cada dueño registra su proyector en su
   `ciudadano_detail.py`. Ningún backend importa a otro.
5. **Sin timeout propio de 4 s en el cliente.** El de 4 s nativo existe para no
   bloquear el render de toda la ficha. En React cada tarjeta carga sola, así
   que rige el read timeout G1 de 60 s (decisión del responsable para equipos
   lentos). Mientras tanto la tarjeta muestra su estado de carga; el resto de
   la ficha ya está visible.
6. **El proveedor que falla no responde 200.** Hoy CDF, Comedores, Celiaquía y
   VAT capturan la excepción y devuelven vacío o cero (`centrodefamilia/ciudadano_detail.py:12-28`,
   `comedores/ciudadano_detail.py:10-34`, `celiaquia/ciudadano_detail.py:14-20`,
   `VAT/ciudadano_detail.py:13-38`); PWA no captura (`pwa/ciudadano_detail.py:9-22`).
   Cada dueño separa una función de consulta que propaga la excepción y
   evalúa los querysets dentro de ella (`list()`); `obtener_contexto` la
   envuelve con el `try` actual para el HTML, sin cambiar su resultado.
7. **Textos formateados en el servidor.** Fechas, montos y etiquetas
   (`get_*_display`) los arma el dueño con los mismos filtros que su template,
   en el mismo request (locale `es-ar`, zona `America/Argentina/Buenos_Aires`,
   `src/backends/config/settings.py:47-48`). React no formatea montos ni fechas.

## Endpoints

### Kernel (core): lista de aportes en el JSON de la ficha

Lo agrega C05.01 en `GET /api/web/ciudadanos/<pk>/` (montado en el core antes de
`api/web/` de usuarios, `src/backends/config/urls.py:76-77`; `ciudadanos` no es
un backend registrado, por lo que el proxy no lo reenvía). C04 define solo el
campo:

```json
"aportes": [
  {"aporte": "pwa", "secciones": ["pwa", "pwa_badges"], "url": "/api/web/comedores/ciudadanos/12/aportes/pwa/"},
  {"aporte": "centrodefamilia", "secciones": ["centrodefamilia", "centrodefamilia_monto"], "url": "/api/web/cdf/ciudadanos/12/aportes/centrodefamilia/"},
  {"aporte": "comedores", "secciones": ["comedores", "comedores_colaboraciones"], "url": "/api/web/comedores/ciudadanos/12/aportes/comedores/"},
  {"aporte": "celiaquia", "secciones": ["celiaquia"], "url": "/api/web/celiaquia/ciudadanos/12/aportes/celiaquia/"},
  {"aporte": "vat", "secciones": ["vat"], "url": "/api/web/vat/ciudadanos/12/aportes/vat/"}
]
```

- Mapa fijo en `ciudadanos/detail_contributions.py`:
  `APORTES_WEB = {"comedores": ("comedores", "comedores_colaboraciones"), "pwa": ("pwa", "pwa_badges"), "celiaquia": ("celiaquia",), "vat": ("vat",), "centrodefamilia": ("centrodefamilia", "centrodefamilia_monto")}`.
  El backend sale de `_backend_de_contribucion(secciones[0])` (`:77-84`), el mismo
  que hoy. En el monolito (`config.settings_all`) el nombre de backend sale de
  la clave de `backends.json` del dueño (comedores, celiaquia, vat, cdf).
- Un aporte cuyo backend no se resuelve no se lista (equivale al `""` de `:117-119`).
- Mismo permiso que la ficha: sin `ciudadanos.view_ciudadano`, 403 de la ficha y
  ningún aporte.

### Dueño: `GET /api/web/<backend>/ciudadanos/<pk>/aportes/<aporte>/`

| Backend (`url_prefixes`) | Aporte | Proyector registrado en |
|---|---|---|
| `api/web/comedores/` | `comedores` | `src/backends/comedores/comedores/ciudadano_detail.py` |
| `api/web/comedores/` | `pwa` | `src/backends/comedores/pwa/ciudadano_detail.py` |
| `api/web/celiaquia/` | `celiaquia` | `src/backends/celiaquia/celiaquia/ciudadano_detail.py` |
| `api/web/vat/` | `vat` | `src/backends/vat/VAT/ciudadano_detail.py` |
| `api/web/cdf/` | `centrodefamilia` | `src/backends/cdf/centrodefamilia/ciudadano_detail.py` |

- Vista: `AporteCiudadanoWebView` (kernel, `ciudadanos/web_aportes.py`), DRF
  `APIView`, `SessionAuthentication` + `core.web_gate.WebGatePermission`, solo
  `GET`/`HEAD`/`OPTIONS`, `Cache-Control: private, no-store`, `Vary: Cookie`.
  Se monta con `backend="<clave>"` dentro del `web_api_urls` de cada dueño,
  incluido desde su `<x>_runtime/urls.py` bajo `api/web/<clave>/` (como
  `cdf_runtime/urls.py` monta hoy `api/centrodefamilia/`).
- Orden de chequeos y respuestas:

| Caso | Status | Cuerpo |
|---|---|---|
| Sin sesión | 401 | `{"detail": "Inicie sesión para continuar."}` (core) |
| Requisito web pendiente | 403 | `{"detail", "state", "required_action_url"}` (core, sin reenviar) |
| Constancia G1 inválida | 403 | `{"detail": "Solicitud no autorizada."}` |
| Sin `ciudadanos.view_ciudadano` | 403 | `{"detail": "..."}` estándar DRF |
| `aporte` no registrado localmente **o** su backend no es `<backend>` de la URL | 404 | `{"detail": "Aporte no disponible en este servicio."}` |
| Ciudadano inexistente | 404 | estándar |
| La consulta del proveedor lanza excepción | 503 | `{"detail": "Servicio no disponible.", "codigo": "aporte_no_disponible"}`; se registra con `logger.exception` como hoy |
| Éxito (con o sin registros) | 200 | `{"aporte": "<aporte>", "secciones": {...}}` |

  El chequeo de backend en la URL impide pedir en el monolito
  `/api/web/cdf/.../aportes/vat/`. No existe parámetro de origen, URL ni nombre
  de sección libre: el `aporte` solo elige entre los registrados.

## Proyecciones por aporte (campo a campo)

Fechas `*_texto` con `date_format(localtime(v) si es datetime, "d/m/Y")`; `null`
se proyecta como `null` y el texto como lo resuelve el template (`-` donde el
template usa `default:"-"`). URLs con `reverse` del nombre nativo en el dueño.

### `comedores` (template `comedores/comedores/templates/comedor/ciudadano_seccion.html`, `ciudadano_colaboraciones.html`)

```text
secciones.comedores = {
  nomina_actual: null | {estado, comedor: null | {id, nombre, url, tipo_texto, provincia_texto, municipio_texto}, fecha_texto},
  historial: [{estado, comedor: null | {id, nombre, url}, fecha_texto}]   # todas las nóminas, orden -fecha
}
secciones.comedores_colaboraciones = [
  {comedor: null | {id, nombre, url}, fecha_alta_texto, fecha_baja_texto, actividades: [nombre]}  # orden -fecha_alta, -id
]
```

- `nomina_actual` = primera de `-fecha` (`ciudadano_detail.py:40-41`); `url` =
  `comedor_detalle`; `comedor: null` si no hay comedor o id (template `:25-31`, `-`).
- Tipo/Provincia/Municipio: nombre o `-` (`:38`, `:44`, `:50`).
- Estado: `activo` → «Activo», `espera` → «En espera», otro → «Baja» (`:57-63`);
  badge «Activo» en el título solo si la actual es `activo` (`:5-12`).
- Historial «Historial de Comedores» solo si hay más de una nómina (`:74`).
- Vacío: «No hay registros de comedores.» (`:117`).
- Colaboraciones: bloque «Colaboraciones en comedores» solo si hay alguna
  (`ciudadano_colaboraciones.html:2`); actividades separadas por coma o `-`
  (`:31-36`); fechas o `-` (`:28-29`).

### `pwa` (`comedores/pwa/templates/pwa/ciudadano_flags.html`, `ciudadano_badges.html`)

```text
secciones.pwa = {pertenece_comunidad_indigena: bool, situacion_calle: bool, persona_con_celiaquia: bool}
```

- Perfiles `NominaEspacioPWA` activos del ciudadano (`pwa/ciudadano_detail.py:10-21`).
- Filas «Pueblo originario:», «Situación de calle:», «Persona con Celiaquía:»
  con «Sí»/«No» (`ciudadano_flags.html:2-31`).
- Badges del `h1`: «Situación de calle» y «Persona con Celiaquía», solo cuando
  el valor es `true` (`ciudadano_badges.html:2-8`). Pueblo originario no tiene badge.

### `celiaquia` (`celiaquia/celiaquia/templates/celiaquia/ciudadano_detalle_seccion.html`)

```text
secciones.celiaquia = {
  legajo_actual: null | {estado_expediente, estado_legajo, resultado_cruce, estado_cupo, es_titular_activo: bool, revision_tecnica},
  historial: [{estado_legajo, estado_cupo, creado_en_texto}]   # "d/m/Y H:i", orden -creado_en
}
```

- Fuente: `celiaquia.api.obtener_resumen_ciudadano` (contrato público del
  dueño, `celiaquia/api.py:18-21`; impl. `services/ciudadano_resumen_service/impl.py:30-52`).
- Etiquetas tal cual: «Estado Expediente», «Estado Legajo», «Resultado Cruce»,
  «Estado Cupo», «Titular Activo» con «Si»/«No» sin tilde (`:47`), «Revision
  Tecnico» sin tildes (`:51`).
- Badge «Activo» del título se muestra siempre, aun sin legajo (`:6-11`):
  peculiaridad de la fuente que se conserva.
- «Historial de Expedientes» solo si `historial` tiene más de uno (`:57`);
  incluye el actual.
- Vacío: «No hay expedientes de celiaquía registrados.» (`:82`).

### `vat` (`vat/VAT/templates/vat/ciudadano_detalle_seccion.html`)

```text
secciones.vat = {
  programas: [{                                   # orden str(programa).lower()
    nombre,                                       # str(programa)
    voucher_badge: {tipo: "activo"|"referencia"|"sin_voucher", estado_display},
    voucher: null | {id, url, estado_display},    # activo o, si no hay, referencia
    creditos_totales: int, creditos_actuales: int, cursos_asignados: int,
    asistencias_presentes: int, asistencias_registradas: int,
    inscripciones: [{curso_texto, comision: {id, codigo, url}, estado_display, asistencias_presentes, asistencias_registradas, asistencia_porcentaje, url}],
    inscripciones_oferta: [{curso_texto, comision: {id, codigo, url}, estado_display, url}]
  }]
}
```

- Cálculos en el dueño con el código actual (`VAT/ciudadano_detail.py:40-133`):
  créditos, voucher activo/referencia, cursos asignados, asistencia y porcentaje
  redondeado. React no recalcula.
- Título «Programa VAT» con badge «N programa»/«N programas» si hay programas (`:6-14`).
- Badge de voucher: «Voucher activo», «Voucher <estado en minúscula>» o «Sin
  voucher» (`:34-40`); «Voucher asignado» `#<id>` con enlace `vat_voucher_detail`
  y «(<estado>)», o `-` (`:53-62`).
- «Créditos totales», «Créditos actuales», «Cursos asignados», «Asistencia»
  `P/R sesiones` (`:66-89`).
- Tabla «Cursos asignados» (Curso, Comisión, Estado, Asistencia, Detalle): curso
  `titulo_referencia.nombre` o `-`; comisión `vat_comision_detail`; porcentaje
  `(N%)` solo si hay registradas; «Ver inscripción» → `vat_inscripcion_detail` (`:93-134`).
- Tabla «Inscripciones de oferta»: el enlace de comisión usa
  `vat_comision_detail` con `inscripcion_oferta.oferta.pk` (`:154`); se conserva
  como está. «Ver inscripción» → `vat_inscripcion_oferta_detail` (`:162`).
- Vacío: «No hay registros VAT para este ciudadano.» (`:175`).
- Coordinación: el trabajo VAT/INET en curso crea `api/web/vat/`; C04 solo
  agrega esta ruta a ese mismo prefijo.

### `centrodefamilia` (`cdf/centrodefamilia/templates/centrodefamilia/ciudadano_detalle_seccion.html`, `ciudadano_detalle_monto.html`)

```text
secciones.centrodefamilia = [{centro_nombre, actividad_nombre, estado, fecha_registro_texto}]   # orden -fecha_registro, todos los estados
secciones.centrodefamilia_monto = {total: "<decimal como string>", total_texto: "$<floatformat:2>"}
```

- Monto: suma de `actividad_centro__precio` solo de `estado="inscrito"`, `or 0`
  (`ciudadano_detail.py:18-23`); `total_texto` con el mismo filtro del template
  (`ciudadano_detalle_monto.html:2`). Un cero exitoso es un dato válido y se
  muestra como tal.
- Estado: `inscrito` → «Inscrito», `lista_espera` → «Lista Espera», otro → «Dado
  de Baja» (`seccion.html:22-28`).
- Título «Centro de Familia»; columnas Centro, Actividad, Estado, Fecha Registro.
- Vacío: «No hay participaciones registradas.» (`:36`).
- Observación sin verificar en runtime: con `es-ar`, `floatformat:2` produce
  coma decimal (`$0,00`), mientras el fallback de la ficha es `$0.00`
  (`ciudadano_detail.html:733`). Por eso `total_texto` sale del servidor y la
  prueba lo compara con el fragmento nativo.
- No tocar el código CDF del worktree con cambios sin commitear: el cambio en
  `ciudadano_detail.py` se hace en la rama de implementación partiendo de su
  estado vigente.

## Renderers React y disponibilidad C2 (C04.02)

- Módulo: `src/frontends/apps/sisoc/src/routes/ciudadano360Aportes.tsx`, que
  exporta un renderer por sección. Lo usa la ruta de la ficha
  (`ciudadano360.tsx`, C05.01); C04 no crea una ruta navegable propia.
- Cada aporte se pide en paralelo al montar la ficha; una tarjeta no espera a
  otra. Sin reintento automático (es GET, pero se sigue la regla común).
- Estados por sección:

| Respuesta del aporte | Presentación |
|---|---|
| Cargando | Bloque en su posición con el indicador de carga del shell; sin valores |
| 200 con registros | Igual al template nativo (textos, orden, enlaces, condiciones) |
| 200 vacío | Texto vacío nativo de la sección; el monto muestra su `total_texto` |
| 401 / 403 con `state` | Flujo estándar del shell (login o requisito pendiente) |
| 403 sin `state`, 404, 5xx, 503, 504, red, redirect, JSON inválido o sin las claves esperadas | **C2:** «No disponible» donde el template muestra un valor o el texto vacío |

- Alcance exacto de «No disponible» (excepción C2 aprobada, nada más):
  - Comedores, Centro de Familia, Celiaquía, VAT: el bloque con su título nativo
    y «No disponible» en lugar del contenido o del texto vacío; sin badges del título.
  - Monto Centro de Familia: «No disponible» en lugar de `$0.00`.
  - PWA filas: las tres filas con «No disponible» como valor; nunca «No».
  - PWA badges: ninguno.
  - Colaboraciones: no se muestra el bloque (la fuente no tiene texto vacío ni
    valor que pueda fingir ausencia; se conserva el comportamiento nativo).
- Un fallo no muestra datos parciales de esa sección ni afecta a las demás.
- Enlaces: rutas Django nativas (`comedor_detalle`, `vat_*`), navegación
  completa, hasta que cada flujo migre. Sin `dangerouslySetInnerHTML` ni
  parseo del HTML del fragmento.
- Visual: regla S13 por caso (paridad estructural, cada elemento a 2 CSS px
  como máximo, diff perceptual ≤ 1 % sin antialiasing, 8 min de diagnóstico).
  La diferencia aceptada se limita a los estados «No disponible» del manifiesto
  [C2](2026-10-27-2807-manifiesto-visual.json).

## Permisos y alcance (sin cambios)

- Ficha y cada aporte: `ciudadanos.view_ciudadano`. Los proveedores no reciben
  usuario: no hay filtro por provincia, centro ni equipo, y la migración no lo
  agrega (ver 2807). G1 solo prueba que el core evaluó los requisitos web.
- Datos sensibles (situación de calle, celiaquía, montos, programas): solo los
  campos que el template ya muestra. No se proyectan IDs internos salvo los que
  arman enlaces que la fuente ya tiene (comedor, voucher, comisión, inscripción).

## Criterios de aceptación

1. Por cada uno de los cinco aportes, con registros y vacío real, la tarjeta
   React reproduce el fragmento nativo: textos citados arriba, orden, enlaces
   (mismo `href`), condiciones de visualización y formato de fecha/monto.
2. `GET` del aporte con proveedor que lanza excepción responde 503 y la tarjeta
   muestra «No disponible»; el fragmento HTML de la misma condición conserva su
   salida actual (vacío o `$0,00`/`$0.00` según rama).
3. Monto CDF: cero exitoso muestra el `total_texto` del servidor; CDF caído
   muestra «No disponible». Son casos separados.
4. PWA caído: ningún badge y filas con «No disponible»; nunca «No».
5. `/api/web/cdf/ciudadanos/<pk>/aportes/vat/` → 404; aporte inexistente → 404;
   ciudadano inexistente → 404; sin permiso → 403 sin datos; anónimo → 401;
   requisito pendiente → 403 con `state` sin reenviar; header G1 alterado → 403
   sin ejecutar la consulta.
6. Con un runtime detenido, la ficha y los demás aportes cargan; solo ese
   bloque pasa a «No disponible».
7. Ningún módulo de un backend importa otro backend (chequeo existente de
   imports; `src/backends/kernel/tests/test_c2_consumidores_sin_comedores.py`).
8. Rutas existentes sin cambios: el fragmento y la ficha Django responden igual
   que en la base (diferencial de status, headers y cuerpo).

## Casos de prueba

| Capa | Caso |
|---|---|
| Kernel unit | `APORTES_WEB` cubre exactamente los ocho nombres de `CONTRIBUCIONES_RENDERIZADAS`; la lista `aportes` respeta el backend de `_backend_de_contribucion`; backend no resuelto → no listado |
| Kernel vista | 404 por aporte de otro backend en monolito; 403 sin permiso; 503 con proyector que lanza; `Cache-Control`/`Vary` |
| Cada dueño | proyección con datos sintéticos igual al contexto del template (un test por campo citado); consulta que propaga excepción; `obtener_contexto` HTML sin cambio de salida (test previo se mantiene) |
| CDF | `total_texto` igual a la salida del template nativo para 0, decimal y miles; queryset evaluado dentro de la consulta |
| G1 | runtime con `SISOC_BACKEND` sin constancia → 403; con constancia válida → 200 (helpers de `kernel/tests/test_web_gate.py`) |
| Vitest | cada renderer: con datos, vacío, cargando y C2; badges PWA solo con `true`; colaboraciones ausente en fallo; JSON sin claves → C2 |
| Navegador | ocho bloques × con datos/vacío/caído, escritorio y móvil, tabs `comedor`/`cdf`/`celiaquia`/`vat`, header y tarjeta de monto; Tab order igual al nativo |

Solo datos sintéticos; sin identidades reales.

## Dependencias y riesgos

- Dependencias: C05.01 (ficha React y `GET /api/web/ciudadanos/<pk>/`);
  prefijos `api/web/comedores/`, `api/web/celiaquia/`, `api/web/vat/` (trabajo
  VAT en curso), `api/web/cdf/` en `backends.json` y `url_registry.json`
  regenerado (preparación del padre); G1 v1 integrado.
- Riesgo: cinco requests extra por ficha a través del proxy; aceptable frente a
  los ocho requests secuenciales actuales del servidor.
- Riesgo: un runtime lento deja su tarjeta cargando hasta 60 s; el resto de la
  ficha no espera.
- Riesgo: separar consulta y `try` en cinco proveedores toca código compartido
  con el HTML (Risk item 3 si cambia su salida): la prueba diferencial del
  fragmento es obligatoria.
- Incertidumbre: el formato exacto de `floatformat:2` bajo `es-ar` y la
  presencia de separador de miles no se observaron en runtime; se resuelve
  comparando con el fragmento nativo, no con un valor fijo.
- Incertidumbre: no se verificó si algún consumidor externo usa la ruta de
  fragmento además del core; queda intacta, así que no cambia.
