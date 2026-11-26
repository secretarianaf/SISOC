# Contrato propuesto de contexto y navegación web (#2798)

## Estado y decisiones concretadas para revisión

Fecha: 2026-10-27. Definición estática derivada del
[plan aprobado](2026-10-27-2785-migracion-integral-react.md). La orientación
general está aprobada; este detalle de contrato todavía no está implementado ni
se presenta como aceptado funcionalmente. No se cambian permisos, middleware,
endpoints existentes, settings ni archivos de #2789/#2793 o #2794.

Propuesta concreta del agente:

| Elemento | Definición propuesta |
|---|---|
| App transversal | `src/frontends/apps/sisoc`, workspace `@sisoc/sisoc`; solo un cliente estático del monorepo. No existe todavía ni representa un backend nuevo |
| Ruta de prueba de Insumos | `/v2/sisoc/insumos/`; ruta pública histórica `/insumos/` conservada durante validación y como objetivo final |
| Dueño backend del contexto | `usuarios`, en `src/backends/sisoc_core/usuarios`, porque ya es dueño de login/cuenta web. No mover esa responsabilidad al kernel ni a PWA |
| Endpoint nuevo | `GET /api/web/session/` y HEAD equivalente sin cuerpo; OPTIONS/métodos permitidos según DRF. Sin operaciones de autenticación, escritura de negocio ni emisión de tokens |
| Archivos candidatos futuros | `usuarios/web_api_urls.py`, `web_api_views.py`, `web_api_serializers.py`, service local de composición, tests junto a su dueño; nombres relativos a la app, aún no creados |
| Routing | Include explícito bajo `/api/web/` en el core, coordinado con #2793. No cambia `/api/users/`, router protegido global de v2 ni URLconf de otros servicios |
| Identidad | Sesión Django del mismo origen. Header Token/Bearer sin sesión no autentica este contrato; con cookie válida se evalúa solo esa identidad de sesión |
| CSRF | Inicializar cookie CSRF mediante mecanismo Django existente en esta lectura; no devolver valor de cookie/token en JSON. Las mutaciones futuras necesitan sesión y validación CSRF real |
| Cache | `Cache-Control: private, no-store`, `Vary: Cookie`; sin cache compartido de identidad/capacidades. No guardar respuesta en localStorage |
| Esquema | [OpenAPI propuesto](2026-10-27-2798-web-session.openapi.json), separado de schemas de producción y sin generar tipos de una API inexistente |

El nombre `sisoc` concreta el placeholder del plan sin añadir otra plataforma.
No implica que INET, Celiaquía, VPSL u otra app importe esta app: comparten
paquetes y navegan por página completa entre apps.

## Fuentes y reutilización

| Fuente inspeccionada | Qué determina |
|---|---|
| `src/backends/sisoc_core/usuarios/auth_views.py` | Dueño de login, cuenta, primer cambio y confirmación; el éxito de flujos forzados hoy va a inicio |
| `src/backends/kernel/users/middleware.py` | Acceso web antes de contraseña y perfil; `/api/` está exento. No suponer que un endpoint nuevo hereda el control de HTML |
| `src/backends/kernel/users/profile_utils.py` | Lectura segura de perfil y necesidad de confirmación; no reparar ni crear perfiles desde un GET |
| `src/backends/sisoc_core/encuestas/services.py`, `context_processors.py`, `middleware.py` | Usar `get_rondas_pendientes_para_request` y el criterio existente de obligatoriedad; evitar copiar segmentación, vencimientos o reglas de recordatorio |
| `src/backends/kernel/iam/services.py`, `core/permissions/registry.py` y `core/templatetags/custom_filters.py` | Permisos efectivos/normalización existentes. No sustituirlos por comparación de strings de rol ni enviar todos los permisos al cliente |
| `src/backends/kernel/core/services/sidebar_access.py` | Predicados registrados por dominio; ausencia de proveedor conserva el resultado actual, sin importar otro backend |
| `src/backends/kernel/core/services/sidebar_items.py`, `src/backends/sisoc_core/dashboard/apps.py` y `templatetags/dashboard_tags.py` | Proveedor existente de tableros y agrupación; no crear otro registro de contribuciones |
| `src/backends/kernel/core/context_processors.py` | Reutilizar `footer_version` para la etiqueta de versión. No copiar lectura/parseo de changelog en React |
| `src/backends/sisoc_core/usuarios/api_views.py` y `api_urls.py` | Login/logout/me/password de token/PWA no equivalen al contrato web nuevo y deben conservar consumidores y autenticación |

No se encontró un endpoint existente que cubra ese contexto de sesión y menú
transversal. El contexto VPSL es específico y el de users usa token/PWA. La
propuesta separada reduce ese impacto a cambio de mantener un contrato web nuevo.

## Respuesta y recorrido de acceso

`200` significa que se pudo determinar el contexto de una sesión activa; no
significa que pueda consultar cualquier dato de negocio. `access.state` marca
una sola situación prioritaria, reevaluada en backend en cada nueva consulta:

| Orden | Condición actual que se reutiliza | state | required_action_url |
|---|---|---|---|
| 0 | Sin sesión válida/usuario inactivo | Respuesta `401`, sin contexto privado | No redirección HTTP desde API; cliente usa login histórico y next seguro |
| 1 | Perfil ausente o `acceso_web` falso | `web_access_denied` | `null`; no abrir negocio ni crear un perfil para evitar el rechazo |
| 2 | `must_change_password` | `password_change_required` | `/password/first-change/` |
| 3 | `needs_profile_confirmation(user)` | `profile_confirmation_required` | `/mi-cuenta/confirmar/` |
| 4 | Alguna ronda pendiente es obligatoria según servicio existente | `mandatory_survey_required` | `/inicio/` con modal Django actual durante la transición |
| 5 | Ninguna condición anterior | `ready` | `null` |

Para una sesión con controles pendientes, el contexto no devuelve menú ni
capacidades de negocio habilitadas. Eso mejora coherencia de UI pero **no es un
control de autorización**: las APIs de negocio nuevas deben comprobar el mismo
requisito al recibir cada request, además de su permiso/objeto/provincia.

El piloto de Insumos y el contexto viven en el mismo servicio core; ahí es
posible componer los helpers existentes sin importar otro backend. Este contrato
no resuelve automáticamente cómo imponer controles forzados en todas las APIs
de verticales independientes. Esa decisión de R4 debe delimitar gateway y dueño
de cada comprobación, sin imports entre servicios ni llamadas remotas ocultas.
No cerrar la integración transversal porque este GET funcione.

No tratar los éxitos históricos de contraseña/perfil que vuelven a `/inicio/`
como si ya conservaran `next`: no lo hacen según las vistas inspeccionadas. El
retorno adicional después de controles forzados pertenece a la transición R4.
El login normal conserva el destino interno; fragmento hash se mantiene del lado
cliente y solo se incorpora a un destino interno validado. No permitir `//host`,
hosts externos ni variantes codificadas como escape. El endpoint de contexto no
recibe `next` ni navega al usuario por un destino aportado por otro servicio.

## Datos mínimos y navegación

- `user`: username, display_name (nombre completo o username), avatar_initial
  (primera letra del username en mayúsculas como sidebar actual) y role_label
  (valor mostrado actualmente o `-`). Sin DNI, email, grupos completos, lista
  de permisos, estado de tokens ni datos PWA.
- `access`: state y required_action_url. `user` puede ser null para acceso web
  denegado; no es necesario exponer un perfil para explicar la prohibición.
- `navigation`: árbol de elementos visibles con id estable, label, href interno
  o null para grupo y children. El orden devuelto reproduce orden visual actual,
  incluido CSS `order`; no ordenar por alfabeto ni por orden físico del HTML.
- `capabilities.insumos`: can_view, show_management y show_categories. Los dos
  últimos representan visibilidad actual, no autorización de cada mutación.
- `footer_version_label`: etiqueta existente del footer; el enlace a novedades
  sigue siendo el actual. No se inventa un número de versión en el frontend.

La [extracción estática del sidebar](2026-10-27-2798-sidebar-referencias.json)
enumera 61 referencias literales de URL y sus condiciones, incluidas nueve bajo
guardas constantes False, y una contribución dinámica de tableros. No certifica
jerarquía ni ejecuta precedencia de expresiones Django; labels cercanos son
candidatos. Cada condición debe contrastarse antes de implementar el árbol.
Las guardas False no se reactivan y las restricciones VAT/CDI/DataCalle se
conservan. Una ruta fuera del menú sigue dentro del inventario de migración.

El servidor filtra navegación usando IAM/predicados existentes. El renderer
React solo dibuja y determina activo/expandido para la ruta lógica actual del
flujo, por ejemplo Insumos; no usa el path `/api/web/session/` como página activa.
Los iconos/clases/assets son presentación versionada por id, no HTML o URLs
arbitrarias de usuario. Los tableros reutilizan el proveedor y su agrupación,
pero su `activo` calculado para la URL API no se toma como estado de pantalla.

No hay un árbol genérico completo en la base actual: la mayoría del menú vive
en templates. La implementación requiere una proyección backend de esas reglas
de presentación, usando helpers de permiso compartidos y tests contra el menú
legacy. No extraer todo el sidebar ni modificar todos los templates por adelantado.
La duplicación temporal de condiciones de visibilidad no se convierte en una
segunda política de autorización ni se traslada al frontend; registrar su retiro
con legacy. Un proveedor ausente devuelve lo mismo que hoy; una excepción real
de consulta no se convierte silenciosamente en menú vacío/sesión lista.

## Status y errores

| Situación | Resultado propuesto |
|---|---|
| Contexto determinado, incluso remediación pendiente | `200` con access.state; menú vacío/capacidades falsas si no ready |
| Sin sesión válida | `401 {"detail":"Inicie sesión para continuar."}`, sin Location ni contexto privado |
| Método no admitido | `405`, Allow coherente; GET no produce escrituras de negocio ni borra tokens |
| Fallo al evaluar una dependencia local necesaria | Propagar el error al manejo existente y registrar sin PII. Nunca declarar ready por default; no introducir timeout/cache/fallback global nuevo |
| CSRF inválido en mutación web futura | `403` estándar; no interpretarlo como permiso de negocio ni reintentar a ciegas |
| Permiso insuficiente de negocio, luego de estado ready | `403` estándar; consultar contexto para distinguir remediación, no crear bucle de login |

Un detalle de implementación debe verificarse expresamente: autenticar solo
por sesión con DRF no garantiza por sí mismo `401` anónimo (puede producir
`403` según challenge/clases). Resolverlo localmente en la nueva vista antes de
leer contexto privado, siguiendo el patrón de respuesta explícita existente
cuando corresponda; no cambiar defaults de autenticación global ni añadir
TokenAuthentication para obtener el status esperado. Confirmarlo por test real.

Los clientes de VPSL/Celiaquía permanecen intactos. El consumidor nuevo usa el
cliente de sesión existente y el nuevo contrato tipado cuando exista su schema
real. Al expirar sesión/terminar logout, limpiar cache privado en memoria; no
guardar payload en localStorage ni reenviar una mutación después del login.

## Compatibilidad y negativos que bloquean implementación

| Prueba posterior | Criterio |
|---|---|
| Cookie válida, token sin cookie, cookie de otro usuario | Contexto de la sesión y solo de ella; sin cookie no hay datos privados |
| Sin perfil, sin acceso web, flags combinados y encuesta obligatoria | Orden de estados comprobado; APIs de negocio también rechazan el bypass |
| PWA/SIIS login/me/logout/reset y rutas internas de Espacios | Mismos contratos/token/cookies/errores; el contexto web no consulta PWA |
| Roles mixtos, superusuario, VAT/CDI/DataCalle, proveedor de tableros ausente | Misma visibilidad/orden que legacy; guardas False siguen deshabilitadas |
| CSRF cookie y logout | Bootstrap seguro; POST logout legacy con CSRF, no endpoint token. GET no invalida sesión |
| Contexto y datos de dos usuarios en el mismo navegador/servidor | No compartir cache ni persistir datos del usuario previo |
| Camino completo de Insumos | No confundir can_view ni show_management con permiso de editar/borrar |

Hallazgo de paridad pendiente: `/insumos/` sin sesión responde hoy `403` por el
decorador externo de permisos; el router genérico v2 redirige al login. Para
mantener comportamiento se recomienda un guard acotado al entry del flujo antes
de aplicar el router genérico; no retirar protección global ni limitar toda la
app transversal a `view_insumo`. Debe definirse/validarse en la implementación
del entry. El manifiesto marca ese caso bloqueado: no compara 403 con login como
si fueran la misma pantalla. El contrato nuevo JSON puede devolver 401 sin
cambiar silenciosamente la respuesta HTML histórica.

## Entrega y siguientes pasos

La [precisión de contratos/remediaciones](2026-10-27-2798-contratos-y-remediaciones.md)
complementa este documento: conservar `user.has_perm` de visibilidad Insumos,
IAM de autorización y los efectos diferentes de reset/cambio obligatorio.
La API no debe exigir ready a la propia acción que resuelve contraseña/perfil/
encuesta; definir excepciones exactas conservando prioridad fuente.

Contrato y OpenAPI son propuestas revisables listas; fuente de verdad runtime
seguirá siendo el schema generado desde la implementación. No se crearon tipos
TS, APIs ni app. Cerrar #2798 requiere revisar estos detalles, resolver el entry
y evaluar la comprensión de la decisión antes de derivar implementación material.
La orientación aprobada no sustituye esa revisión. No se crea un ticket de
endpoint operativo hasta que el contrato esté cerrado.

El [manifiesto de Insumos](2026-10-27-2799-insumos-manifiesto-visual.json) fija
casos/roles/datos propuestos, sin usuarios/bases/capturas existentes. Reconciliar
#2793 (head consultado `79a4c95492aa96bcb0211bad7ff4bc005e1af95a`) y #2794
(`ada5cf63328ed33304f358ca49e13801ca0f439a`) antes de cambiar código común.

Actualización posterior: ambos PRs están integrados; ver
[delta de base](2026-10-27-2786-delta-integraciones.md). INET agrega un contexto
de sesión de su dominio y el patrón de challenge Session/401; reutilizar lo
aplicable sin mezclarlo con menú/contexto transversal. El
[paquete de piloto](2026-10-27-2785-paquete-piloto-insumos.md) concreta el alcance
de ejecución a decidir. No se considera implementado este endpoint por existir INET.
