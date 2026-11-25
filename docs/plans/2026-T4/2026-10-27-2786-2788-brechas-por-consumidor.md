# Brechas por consumidor y dependencias de transición (#2786–#2788)

Fecha: 2026-10-27. Snapshot: `ae0b0da01c546d801f18237c3c6dab29a5496790`.
Relevamiento estático; no solicitudes a servicios ni acceso a datos reales.
Complementa la [matriz de 95 familias](2026-10-27-2786-matriz-flujos.md).

## API existente frente a contrato web necesario

| Dueño / consumidor | Evidencia de autenticación/permiso | Consecuencia para React con sesión |
|---|---|---|
| CDF / integración | `src/backends/cdf/centrodefamilia/api_views.py`: viewsets con `HasAPIKey`; defaults DRF incluyen token/sesión, pero ese permiso sigue requiriendo API key | No poner una key en el build, navegador ni un proxy sin autorización. Reutilizar consultas/services/serializers compatibles y definir contrato web de lectura con el alcance de las vistas HTML |
| VAT / API de integración | `src/backends/vat/VAT/api_views.py`: numerosos viewsets con `HasAPIKey` | No quitar esa restricción para habilitar React. Comparar contrato por operación y consumidor; conservar integraciones |
| VAT / API web existente | `src/backends/vat/VAT/api_web_views.py` y `api_urls.py`: `web/centros`, `web/ciudadanos`, `web/titulos`, `web/cursos`, `web/inscripciones`, `web/pav`, con `HasAPIKeyOrToken` | Candidata a reutilización. Ese permiso de `src/backends/kernel/core/api_auth.py` acepta primero `request.user.is_authenticated`, por lo que el nombre no significa «solo token». Comparar campos, filtros, reglas y alcance con cada pantalla; por ejemplo, centros filtra por parámetros del request, lo cual no acredita el mismo alcance del backoffice |
| Comedores / PWA | `src/backends/comedores/comedores/api_views.py`: token, `IsAuthenticated` y, en escritura, `IsPWAWriteAllowed` | No asumir sesión web ni ampliar mutaciones por cambiar autenticación. Reutilizar service después de confirmar permiso/objeto y conservar PWA |
| Comedores / territorial | `src/backends/comedores/comedores/api_views_territorial.py`: token y `IsTerritorialComedorUser` | La zona y función territorial no son permisos del backoffice por equivalencia de modelo. Mantener su contrato |
| Comunicados / PWA | `src/backends/comedores/comunicados/api_views.py`: permiso HasAPIKey o IsAuthenticated, queryset de contenido publicado y destinatarios según endpoint | Puede aceptar autenticación existente, pero lectura publicada no equivale a gestión de borradores, destinatarios, publicación ni mailing |
| DataCalle / app de campo | `src/backends/dispositivos/datacalle/api_views.py`: `TokenAuthentication`, `TieneAccesoDataCalle`; services y roles de equipo/coordinador | No sustituir por sesión genérica ni copiar cola offline al frontend web. Conservar alcance por equipo/provincia y distinción de errores 409 cerrado/no iniciado y reintentabilidad |
| Inspecciones / PWA | `src/backends/inspecciones/inspecciones/api_views.py`: token y `TieneAccesoInspecciones`; `api_urls.py` declara consumidor PWA | Backoffice usa `puede_gestionar` y rutas de importación/gestión propias; API de campo no certifica esos flujos |
| Ticketera / integración CDI | `src/backends/cdi/ticketera/api_views.py`: `HasAPIKey` para usuario/credenciales/verificación/reset | No reconstruir Ticketera ni usar sus operaciones como login web SISOC. Gestionar las pantallas CDI que las disparan, con permisos y datos sintéticos |
| RENAPER / core API | `src/backends/kernel/core/api_views.py` y `api_urls.py`, registro de consulta y permiso de API key | Usar flujos de lookup autorizados existentes o contrato web mínimo; no publicar credencial de integración. La búsqueda web de ciudadanos tiene otro contrato |
| Identidad PWA/SIIS | `src/backends/sisoc_core/usuarios/api_views.py`: token/PWA en me/logout; login/reset y SIIS tienen consumidores propios | La propuesta de sesión web #2798 queda separada; no modifica esos contratos por asociación |

«Acepta sesión» no significa «apto para la pantalla». Hay que comprobar también
campos, paginación, filtros, efectos, rol y alcance por objeto/provincia/centro,
archivos y estados. El inventario conserva referencias a declaraciones de
autenticación/permisos y métodos para esa comparación. Tests unitarios que
reemplazan `permission_classes` por `[]` no demuestran autorización: se observó
ese patrón en pruebas de VAT web y no se las toma como validación de permisos.

## PAS: recorrido público propio que también se migra

Detalle posterior: [contrato y decisión de sesión PAS](2026-10-27-2806-ddjj-publica-pas.md)
y [manifiesto de casos](2026-10-27-2806-pas-manifiesto-visual.json). La revisión
de middleware identificó la decisión P1/P2. El responsable eligió P1:
conservar los bloqueos de una sesión restringida, incluso en la nueva API pública.

Familia PAS01 de la matriz. Es UI propia de SISOC, incluida en la épica;
no es una PWA externa ni un documento excluido. La generación de PDF sí permanece
en Django. Su acceso por invitación debe conservarse sin imponer login general.

| URL actual | Resultado visible / contrato actual |
|---|---|
| `/pas/ddjj/formulario/<uuid:token>` | GET de `PasDDJJFormularioView`: formulario de invitación disponible; token inexistente 404; usada/revocada/vencida 410 |
| Misma URL, POST | Form inválido se vuelve a renderizar con 400; presentación válida llama `presentar_ddjj` y redirige a confirmación; invitación consumida/vencida se rechaza con 410 |
| `/pas/ddjj/formulario/<uuid:token>/municipios` | Valida invitación antes del lookup; provincia ausente/no numérica devuelve lista vacía; no disponible da 410 con formato actual `detalle` |
| `/pas/ddjj/confirmacion` | Template de confirmación pública actual; no inventar autenticación nueva para mostrar resultado |
| `/pas/ddjj/<pk>/descargar` | Flujo administrativo con sesión y permiso `pas.view_paspersona`; diferente del formulario de invitación |
| `/media/pas/ddjj/<path>` | `PasDDJJPrivateMediaView` rechaza acceso directo con 404; no convertirlo en estático público |

Fuentes: `src/backends/pas/pas/urls.py`, `views.py`, `models.py`,
`forms.py`, `services/ddjj_service.py` y `tests/test_ddjj.py`.
`presentar_ddjj` usa transacción y bloquea la invitación con `select_for_update`
antes de revisar disponibilidad y guardar; la UI nueva no debe reemplazar esa
protección por un booleano cliente ni generar el PDF. El test existente de
presentación documenta PDF inmutable e impacto de datos; no se ejecutó aquí.

Decisión pendiente de implementación: entry público explícito para este flujo y
sus assets, conservando la URL canónica y su token, sin abrir todo `/v2/pas/` ni
el padrón. Alternativas a comparar: entregar shell React desde la ruta pública
actual o un entry público acotado que mantenga compatibilidad de enlaces. Usar
el servidor estático actual sin reenviarle cookies/tokens de negocio por headers
innecesarios. La validación de invitación y presentación siempre queda en PAS.

P1 confirma conservar el efecto de una cookie web con contraseña/perfil pendientes:
la URL puede ser pública para un visitante y aun así atravesar middleware
global con sesión. No introducir una exención nueva al portar entry/datos/POST.

Casos de aceptación: token disponible/inexistente/revocado/vencido/consumido,
form inválido y válido, dos intentos de presentación, datos de municipio,
confirmación, descarga autenticada y media directo. Comparación visual del
formulario y sus errores/confirmación en escritorio/móvil; los 410 actuales
también son un estado visible. Solo tokens, personas y contactos sintéticos en
capturas; la planificación no exporta ni registra tokens reales.

## Ciudadano 360: aportes remotos y fin del HTML heredado

Detalle posterior: [ocho bloques, contrato JSON y decisión de degradación](2026-10-27-2807-aportes-ciudadano360.md).
La ausencia de fragmento CDF puede convertirse en `$0.00`; no se considera
un cero confirmado. El responsable eligió C2 (`No disponible` ante falla),
excepción visual acotada a Ciudadano 360; implementación y verificación pendientes.

Familia C04. `src/backends/kernel/ciudadanos/detail_contributions.py` mantiene
proveedores y obtiene fragmentos remotos con `outbound_headers(request)`,
timeout de cuatro segundos y sin seguir redirects. Respuestas distintas de 200
o fallos de red omiten ese fragmento. `contribucion_detalle_ciudadano`, en
`src/backends/kernel/ciudadanos/views.py`, exige login y permiso de consulta.

El registro de backends identifica aportes de Comedores/PWA, VAT, CDF y
Celiaquía; cada consulta y autorización sigue en su dueño. Estos antecedentes
evitan imports entre procesos, pero un fragmento HTML no es un contrato JSON
para la UI React. Insertar ese HTML en React como resultado final incumple la
migración de presentación.

Trabajo por aporte, no una reescritura de Ciudadanos:

1. Mapear nombre de contribución, backend, consulta/service, permiso/objeto,
   template, campos/acciones y estado vacío/error.
2. Proponer JSON explícito mínimo en el dueño, compatible con el fragmento HTML
   mientras siga habiendo consumidores Django. Reutilizar helpers de sesión,
   identidad y proxy; no crear llamadas anónimas ni mover querysets al kernel.
3. Mantener la estructura visual del bloque en React con datos tipados;
   conservar enlaces a módulos legacy mientras no estén migrados.
4. Definir dato vacío, denegado, timeout, servicio caído y payload inválido.
   La omisión actual o un cero de dashboard no demuestra ausencia de actividad.
   Cualquier mensaje visual adicional requiere decisión; no introducir rediseño
   de estados de error por esta planificación.
5. Comprobar con runtimes separados, más la composición local, los accesos
   permitidos y negativos. Que settings_all funcione no prueba aislamiento.

### Checklist 3 de verticales independientes

| Ítem de la guía | Estado de planificación / evidencia |
|---|---|
| Elegir contrato existente sin importar modelos/api.py del vertical | Hecho para diagnóstico: HTML remoto, JSON de métricas y reenvío existentes identificados. Pendiente contrato JSON nuevo por aporte para React |
| Consulta/autorización/template en el dueño y registro AppConfig/backends | Regla preservada en el plan; registro actual identificado. Cambios JSON y su registro quedan pendientes por aporte |
| Helpers de proxy conservando sesión/headers | Helpers existentes identificados; no se creó HTTP alternativo. Pendiente ejecución de su uso para JSON |
| Fallback por timeout/caída/403/vacío/payload inválido | Conducta HTML actual identificada; contrato JSON/presentación final requiere decisión y pruebas |
| Composición completa y runtimes separados | Pendiente ejecución autorizada; no se arrancaron procesos ni se ejecutaron suites |

Fuente: `docs/desarrollo/verticales_independientes.md`, checklist 3. Se aplica
`verticales-checklist` para conservar dueño y frontera de ejecución; no se crea
otro checklist con reglas distintas ni se presenta planificación como validación.

## Control de sesión web en APIs de otros runtimes

El endpoint de contexto y el piloto viven en el core y pueden consultar perfil
y encuestas locales. Eso no resuelve por sí solo los requisitos forzados de
APIs nuevas de CDF, Comedores, PAS, etc. `/api/` está exento en middleware actual;
un navegador puede enviar requests aunque no muestre el botón.

Debe quedar una definición R4 acotada con:

- qué comprobación ocurre en gateway/core y cuál en el runtime dueño;
- cómo se conserva permiso/objeto/provincia además de sesión/CSRF;
- cómo se conoce la encuesta obligatoria del core sin importarla en kernel o
  vertical, y sin inventar protocolo de autenticación ni dependencia remota oculta;
- qué ocurre ante core/servicio no disponible, cambios de permisos o estado entre
  requests y acceso directo al runtime; costos de latencia/disponibilidad;
- exclusión explícita de APIs token/API key existentes y de invitaciones PAS,
  para no aplicar controles web a consumidores distintos por coincidencia de URL.

Alternativas para evaluar: gate público antes del proxy con controles propios
por runtime, composición de helpers locales más una consulta interna existente
para requisitos del core, o mecanismo de autorización delegado. No se elige una
por omisión. Una aserción nueva, cache o setting sería material y requiere decisión;
primero verificar si las prácticas actuales ya cubren el caso. El resultado
observable es que el request directo no pueda saltar una restricción y que PWA,
integraciones y DDJJ públicas mantengan sus contratos.

## Reconciliación con INET #2794

Se consultó la lista de archivos y el patch de
`docs/implementaciones/inet_react.md` del PR abierto. Declara buscador/ficha CFP,
ubicaciones/contactos, planes, cursos/comisiones, inscripción y asistencia.
Ese alcance se cruza con V02–V07 de la matriz. Vouchers/parametrías, otros
catálogos y evaluaciones no se presumen completos solo por esa descripción.

Antes de abrir implementación VAT: comparar rutas/campos/acciones reales de cada
familia contra el head y los contratos del PR; registrar cubierto/parcial/no
cubierto y aceptación visual. No rehacer INET, aceptar su diseño como baseline
automáticamente, ni certificar integración/QA/deploy por su descripción o tests
declarados. Sus cambios compartidos siguen coordinados con #2789/#2793.

## Siguiente trabajo acotado

Las familias de la matriz permanecen para descomposición; no se abren 95 issues
de implementación. Las definiciones prioritarias son: CDF lectura web frente a
API key, PAS DDJJ pública, aportes de Ciudadano 360 y controles web entre runtimes.
Cada una tiene una frontera/consumidor distinta y puede cerrarse con contrato,
negativos y dependencias sin tocar datos ni cambiar producción. Su publicación
no autoriza implementación ni cierra #2786 por sí sola.

Tareas de definición creadas y vinculadas: [#2805 CDF](https://github.com/secretarianaf/SISOC/issues/2805),
[#2806 PAS](https://github.com/secretarianaf/SISOC/issues/2806),
[#2807 Ciudadano 360](https://github.com/secretarianaf/SISOC/issues/2807) y
[#2808 controles web entre runtimes](https://github.com/secretarianaf/SISOC/issues/2808).
Su evidencia es autocontenida en los cuerpos; los documentos detallados siguen
locales sin commit/push ni enlaces a una rama remota inexistente.
