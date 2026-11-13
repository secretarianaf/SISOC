# Front v2 (React) — reglas para migrar módulos

Estado: **vigente como regla; base implementada**. `src/frontends/` existe, con
`packages/ui`, `packages/api`, `apps/vpsl`, `apps/celiaquia` y el shell local
`apps/sisoc`. El router `/v2/`
vive en `src/backends/kernel/core/v2_frontend.py`, con los destinos en
`settings.FRONTEND_V2_UPSTREAMS`.

Decisión y alternativas descartadas: `docs/registro/decisiones/2026-09-24-frontend-v2-react.md`.

Aplica a **todo módulo que migre su front a React** (primero Celiaquía, después
PAS; al final, todos). Si una tarea necesita romper una regla, se discute en la
épica antes de implementar, no dentro del PR.

## 1. Convivencia viejo / nuevo

- El front nuevo vive bajo **`/v2/<modulo>/`**. Ejemplo:
  `https://sisoc.secretarianaf.gob.ar/v2/celiaquia/expedientes/`.
- El front viejo sigue igual en su ruta actual (`/celiaquia/...`).
- **El menú viejo no enlaza a `/v2/`.** Al front nuevo se entra solo por URL.
  Pasar el menú a `/v2/` y borrar pantallas viejas queda fuera de alcance hasta
  que se decida explícitamente.
- Las dos versiones usan los **mismos services** del back. Nunca hay dos lógicas
  de negocio vivas.
- El rediseño solo se aplica en `/v2/`. No se tocan templates viejos para
  "parecerse" al diseño nuevo.

### Contexto del piloto INS-A

El core expone GET/HEAD `/api/web/session/` mediante sesión Django, no token PWA.
Devuelve identidad mínima, requisitos web, menú, capacidades y footer; mientras
haya un requisito pendiente, no devuelve navegación de negocio habilitada.
Cada API de negocio debe reevaluar sus propios controles: las capacidades no
autorizan acciones. Respuesta privada/no-store, sin guardar identidad en
localStorage. La lectura inicializa CSRF; el token no viaja en el JSON.

Fuentes: `src/backends/sisoc_core/usuarios/web_context.py` y `web_api_views.py`.
Schema de serializers reales en `web_api_serializers.py`. Pruebas:
`src/backends/sisoc_core/tests/test_web_session_api.py`. El piloto INS-A reproduce
el diseño Django, no adopta por defecto un rediseño. El shell React local
`apps/sisoc` implementa el circuito INS-A, pero no se agrega a
`FRONTEND_V2_UPSTREAMS`. La entrada de preview conserva los controles de acceso
antes del router V2 y no activa un destino público. Renderiza el
marco privado solo cuando `access.state` es `ready`; errores o payloads
desconocidos ocultan identidad, menú y contenido privado. Las capacidades del
contexto no sustituyen la autorización de cada API de negocio. Detalle y
compatibilidad HEAD:
`docs/registro/cambios/2026-T4/2026-10-30-2798-contexto-sesion-web.md`.

Vite sirve la app local bajo `/v2/sisoc/` y usa proxies a loopback para API,
static y rutas legacy fuera de ese namespace y de los recursos internos de
Vite. El proxy legacy preserva Host/origen para los controles normales de
sesión y CSRF; esta configuración no altera el backend ni sus rutas globales.
No persiste identidad en el navegador ni activa configuración global de
módulos. La evidencia visual y la aceptación del worktree original no certifican
automáticamente su integración en otro checkout: se verifican los seams y las
URLs afectadas antes de afirmar paridad o habilitar una ruta de usuario.

## 2. Estructura en el monorepo

```text
src/frontends/
  package.json          # npm workspaces + scripts comunes
  package-lock.json     # único lockfile de todo el front v2
  .nvmrc                # 22.14.0
  .npmrc                # save-exact=true
  tsconfig.base.json
  eslint.config.js
  Dockerfile            # ARG APP=<modulo>; targets dev y prod
  packages/
    ui/                 # @sisoc/ui: tema, layout v2, componentes compartidos
    api/                # @sisoc/api: cliente HTTP, manejo de sesión, tipos OpenAPI
  apps/
    celiaquia/          # base /v2/celiaquia/
    pas/                # base /v2/pas/
```

- **Una app por módulo** en `apps/<modulo>/`, con su propio servicio de compose
  e imagen.
- **Lo compartido va en paquetes internos** (`packages/*`). No se publican en
  npm; las apps los consumen como código fuente del workspace.
- Una app **no importa de otra app**. Lo que dos apps necesiten se mueve a un
  paquete.
- El front **no importa nada del back** ni lee archivos de apps Django.

## 3. Stack y versiones

Las versiones son **exactas** (sin `^` ni `~`) y viven en un único lockfile. El
stack base está alineado con las PWA existentes (SISOC-PWA-Espacios-Comunitarios).
La capa visual sigue la skill de UI/UX `tema-verde-institucional`.

### Runtime

| Componente | Versión | Nota |
| --- | --- | --- |
| Node | 22.14.0 | Igual que el Dockerfile de la PWA de Espacios Comunitarios |
| npm | el incluido en Node 22.14.0 | lockfile v3; instalar con `npm ci` |

### Dependencias

| Paquete | Versión | Uso |
| --- | --- | --- |
| react / react-dom | 19.2.4 | — |
| react-router-dom | 7.13.1 | ruteo dentro de cada app |
| @tanstack/react-query | 5.90.21 | estado de servidor, cache de requests |
| axios | 1.13.5 | cliente HTTP (dentro de `@sisoc/api`) |
| react-hook-form | 7.71.2 | formularios |
| @hookform/resolvers | 5.2.2 | — |
| zod | 4.3.6 | validación de formularios (solo UX) |
| @mui/material | 9.4.0 | componentes (tema de la skill) |
| @mui/icons-material | 9.4.0 | íconos |
| @emotion/react | 11.14.0 | requerido por MUI |
| @emotion/styled | 11.14.1 | requerido por MUI |
| @fontsource/roboto | 5.3.0 | Roboto autoalojada (300/400/500/700) |
| @sentry/react | 10.75.3 | errores del navegador |

### Herramientas de desarrollo

| Paquete | Versión |
| --- | --- |
| typescript | 5.9.3 |
| vite | 7.3.1 |
| @vitejs/plugin-react | 5.1.4 |
| eslint | 10.11.0 |
| @eslint/js | 10.0.1 |
| typescript-eslint | 8.70.1 |
| eslint-plugin-react-hooks | 7.1.1 |
| eslint-plugin-react-refresh | 0.5.7 |
| globals | 16.5.0 |
| openapi-typescript | 7.13.0 |
| vitest | 4.1.11 |
| jsdom | 29.1.1 |
| @testing-library/react | 16.3.3 |
| @testing-library/dom | 10.4.1 |
| @testing-library/jest-dom | 7.0.1 |
| @playwright/test | 1.63.0 |
| @types/react | 19.2.7 |
| @types/react-dom | 19.2.3 |
| @types/node | 24.10.1 |

Diferencias deliberadas con la PWA:

- **ESLint 10**, porque ESLint 9 figura sin soporte en npm.
- **MUI en lugar de Tailwind**, porque la skill de diseño está hecha sobre MUI.
  En `/v2/` no se mezclan Tailwind y MUI.
- **Íconos de `@mui/icons-material`**, en lugar de FontAwesome o lucide.

Qué se verificó:

- La combinación completa se instaló y pasó `tsc`, `vite build`, `vitest run` y
  `eslint`, con el `theme.ts` de la skill sin modificar, sobre Node 24 local
  (2026-09-24).
- Repetido sobre Node 22.14.0 en contenedor: pasa. El `package-lock.json` de
  `src/frontends/` es el que fija las versiones reales.

Política de actualización:

- No se suben versiones dentro de un PR de pantallas.
- Los parches y las correcciones de seguridad van en un PR dedicado.
- Las versiones mayores se deciden en la épica.
- Todas las apps de `src/frontends/` comparten las mismas versiones.

## 4. Diseño (skill `tema-verde-institucional`)

- El tema MUI (`buildTheme(mode)`) vive **una sola vez** en `@sisoc/ui`. Las
  apps no redefinen colores.
- Los componentes usan **roles del tema** (`primary`, `background`, `text`,
  `nav`, …), nunca hex sueltos.
- El modo por defecto es claro. La preferencia se guarda en `localStorage`
  (`app.theme`), siempre dentro de `try/catch`. Como todas las apps de `/v2/`
  comparten origen, la preferencia es común a todas.
- AppBar y Drawer usan la superficie `nav`. La sección activa se marca en ámbar.
- Contraste AA: texto ≥ 4,5:1; bordes de control y rellenos de botón ≥ 3:1.
- Los estados info/attention/pending son neutrales, **no un semáforo**. El verde
  es de marca, no significa "OK".
- Roboto se carga con `@fontsource/roboto`, no con CDN.
- El `main.tsx` de ejemplo de la skill se adapta con `import type { ReactNode }`.
  No se copia literal.

## 5. Layout y navegación de `/v2/`

- El layout (AppBar + Drawer) es **propio de `/v2/`**: vive en `@sisoc/ui` y no
  reutiliza ni modifica el sidebar viejo (`src/backends/kernel/templates/includes/sidebar/opciones.html`).
- El Drawer lista los módulos de `/v2/` que el usuario tiene permitidos, según
  el contexto de usuario que devuelve la API.
- Pasar de un módulo a otro (`/v2/celiaquia/` → `/v2/pas/`) es una navegación de
  página completa, porque son apps distintas.

## 6. Ruteo: todo entra por Django

El Nginx del host **no cambia**: ya envía todo el tráfico a Django. Django
recibe `/v2/<modulo>/...` y lo reenvía al servicio de front de ese módulo.

Reglas del router de Django:

- **Allowlist.** Los módulos y sus destinos salen de configuración
  (`settings`/env), nunca del request. Un módulo desconocido devuelve 404.
- **Solo lectura.** Solo acepta `GET`/`HEAD`. No reenvía `Cookie` ni
  `Authorization` al servicio de front, porque el front estático no los necesita.
- **Login obligatorio.** Todo `/v2/` exige sesión. Sin sesión, redirige a
  `/login/?next=<ruta pedida>`.
- **Mismo stack de middleware** que el resto del sitio (sesión, CSP, auditoría,
  confirmación de perfil, cambio de password obligatorio).
- **Timeout corto.** Si el servicio de front está caído o no responde, Django
  devuelve 503 para esa ruta y sigue funcionando para el resto.
- **Sin lógica.** No transforma contenido ni inyecta datos: solo reenvía.
- **Cache.**
  - Assets con hash (`/v2/<modulo>/assets/*`):
    `Cache-Control: public, max-age=31536000, immutable`.
  - `index.html`: `no-cache`.
  - Así, cada asset pasa por Django una sola vez por deploy y por navegador.
- **Riesgo aceptado.** En los entornos de deploy, Django corre con Gunicorn
  síncrono (4 workers × 1 thread por defecto), así que servir assets ocupa
  workers.
  - Condición para revisar la decisión: saturación de workers o latencia de
    `/v2/` peor que la de las pantallas viejas en HML.
  - En ese caso, se evalúa servir los assets de `/v2/` desde Nginx.

## 7. Comunicación con el back

- **Canal único:** API HTTP JSON bajo `/api/<modulo>/` (por ejemplo
  `/api/celiaquia/`, `/api/pas/`).
  - El front no accede a la base.
  - El front no depende de templates ni del contexto de Django.
  - El back no conoce al front.
- **Archivos en el back:** `api_urls.py`, `api_views.py` y `api_serializers.py`
  de la app, como el resto del repo.
  - `<app>/api.py` **no se usa para esto**: es el contrato Python público entre
    módulos (`docs/ia/MODULAR_BOUNDARIES.md`).
- **La lógica sigue en `<app>/services/`.** Las API views son delgadas y
  reutilizan los mismos services que usan las vistas Django actuales.
  - React no replica reglas de negocio; solo hace validaciones de UX (zod).

### Convenciones de API

Son las mismas que ya usa el repo:

- **Nombres de campos:** `snake_case`, sin conversión a camelCase. El front usa
  los nombres tal como vienen en los tipos generados.
- **Paginación:** `PageNumberPagination` de DRF, con la respuesta
  `{count, next, previous, results}`.
  - Parámetros `page` y `page_size` (máximo 200), como `src/backends/vat/VAT/pagination.py`.
  - Paginar es obligatorio en listados.
- **Filtros y orden:** query params en `snake_case`.
- **Errores:** los estándar de DRF.
  - `{"detail": "..."}` para errores generales.
  - `{"campo": ["mensaje"]}` para validaciones.
  - No se inventan otros formatos.
- **Fechas:**
  - Fechas en ISO 8601 (`YYYY-MM-DD`).
  - Fecha y hora en ISO 8601 con offset. El back usa `USE_TZ` con
    `America/Argentina/Buenos_Aires`.
  - El front formatea para mostrar en `es-AR`.
- **Status:**
  - `401`: sin sesión.
  - `403`: sin permiso.
  - `404`: no existe o está fuera del alcance del usuario.
  - `400`: error de validación.
  - Las API de `/v2/` mantienen las clases de autenticación por defecto de DRF,
    para que un request sin sesión devuelva 401 y no 403.

### Contrato (OpenAPI)

- El schema de drf-spectacular es la fuente de verdad.
  - Se genera con `python manage.py spectacular`, porque `/api/schema/` solo se
    expone con `ENABLE_API_DOCS`.
  - Se versiona en `src/frontends/packages/api/openapi.yaml`.
- Los tipos TS se generan desde ese archivo con `openapi-typescript`. No se
  escriben a mano.
- **CI** falla si:
  - el schema versionado no coincide con el que genera el back;
  - los tipos no coinciden con el schema.
- Un cambio que rompe el contrato va en el **mismo PR** que el ajuste del front.

## 8. Sesión, seguridad y permisos

- **Autenticación:** sesión de Django en el mismo dominio. No hay tokens en el
  navegador.
- **CSRF:** `@sisoc/api` envía `X-CSRFToken`, leído de la cookie `csrftoken`,
  en todo método no seguro.
- **Respuestas de la API:**
  - `401`: `@sisoc/api` redirige con navegación completa a
    `/login/?next=<ruta actual>`.
  - `403` con sesión activa: pantalla "sin permiso". No redirige al login, para
    evitar loops.
- **Permisos:** cada endpoint valida los permisos del módulo y el alcance del
  usuario (por ejemplo, la provincia en Celiaquía).
  - Ocultar un botón no es control de acceso.
  - Entrar por URL a `/v2/` no saltea nada.
- **CSP:** el front respeta el CSP vigente (`src/backends/config/middlewares/csp.py`).
  - Sin scripts inline en `index.html` (el build de Vite no los genera).
  - Sin CDNs fuera de los permitidos; fuentes autoalojadas.
- **Secretos:** el build no lleva secretos. Toda variable `VITE_*` es pública
  por definición.

## 9. Docker Compose y desarrollo local

- **Servicio:** cada app es un servicio propio, llamado `front_<modulo>` (por
 ejemplo `front_celiaquia`), con imagen construida desde `docker/frontends/Dockerfile`
  (`ARG APP`).
- **Dependencia del back:** declara
  `depends_on: { django: { condition: service_healthy } }`.
  - El servicio `django` tiene un healthcheck contra el `/health/` existente.
  - Reiniciar un servicio de front no reinicia `django`, y viceversa.
- **Desarrollo:** target `dev` con Vite y hot reload, código montado como
  volumen y `node_modules` en volumen propio (patrón `compose.dev.yaml` de la
  PWA).
  - El navegador entra por Django (`/v2/<modulo>/`).
  - El websocket de HMR conecta directo al puerto de Vite (`server.hmr`),
    porque Django no reenvía websockets.
- **Producción:** target `prod` con el build estático servido por
  `nginx-unprivileged` (patrón de la PWA).
  - Puerto interno, sin exponer al host: solo lo alcanza Django por la red de
    compose.

## 10. Calidad y CI

Cuando cambia `src/frontends/**` o una API consumida por `/v2/`, CI corre:
`npm ci`, `lint`, `typecheck`, `test` (Vitest + Testing Library), `build` y el
chequeo de contrato.

- **Tests unitarios y de componentes:** junto al código de cada app o paquete.
- **E2E con Playwright:** solo para los flujos críticos que defina la tarea de
  cada módulo.
- **Revisión de PRs:** igual que el resto del repo (`.github/CODEOWNERS`).

## 11. Observabilidad

Sentry usa el **mismo proyecto que el back**, configurado con `@sisoc/api` /
`@sisoc/ui`:

- `environment` igual que el back del entorno.
- `release` = SHA del commit.
- Tag `frontend=v2-<modulo>`.
- `sendDefaultPii: false`, porque son datos de salud y sociales.
- Replays solo si el entorno del back los tiene activos, y siempre con
  `maskAllText` y `blockAllMedia` activos.

## 12. Deploy (HML / PRD)

- Los servicios `front_<modulo>` se agregan al compose de deploy y al flujo
  existente (`src/scripts/operacion/deploy_refresh.sh`, `.github/workflows/deploy.yml`).
  No se crea otra plataforma de deploy.
- La imagen se construye por entorno (variables `VITE_*` del entorno) y se
  etiqueta con el SHA.
- Si falla el build del front, falla el deploy antes de reemplazar el servicio
  anterior.
- No hay cambios en el Nginx del host.

## Componentes de paridad compartidos (#2785)

Los módulos de `src/frontends/apps/sisoc/src/routes/` repetían la misma mecánica para
parecerse a la pantalla nativa. Ahora viven en dos módulos; usarlos en lugar de copiar:

- `select2.tsx`: un único `Select2` sobre opciones locales (simple o múltiple) con el
  marcado de Select2 4.1. Cada diferencia entre las pantallas es una opción explícita
  (`termHandling`, `enterOnSelected`, `removeOpensResults`, `clearTrigger`, `focusMarker`,
  `outsideClick`, `dropdownParent`, `hideEmptyChoice`, `singleFocus`). Los archivos
  `cdfSelect2.tsx`, `duplasSelect2.tsx`, `pasSelect2.tsx` y `datacalleSelect2.tsx` son
  envolturas finas que fijan las opciones de su pantalla. `singleFocus="selection"` es la
  regla de foco del select simple nativo (la caja conserva el foco; Enter, Espacio y
  Alt+Abajo abren; Escape, Tab y Alt+Arriba cierran). `InspSelect2.tsx` sigue aparte: su
  fuente es remota (búsqueda asíncrona, demora de 250 ms, opción de dos líneas).
- `nativeParity.tsx`: `NativeToasts` (toasts al final de `<body>`, como toastr),
  `useModalTabTrap` y `NativeModal` (modal Bootstrap en su lugar del DOM, con trampa de
  Tab, Escape y foco devuelto) y `resetAfterRejectedPost` (arriba del documento y teclado
  desde el inicio, como la recarga nativa tras un POST rechazado).

Cuándo usarlos: un select con búsqueda local, un modal propio de la pantalla, los toasts
de una pantalla o el reinicio tras un 400. No agregar una variante nueva: sumar una
opción al componente compartido y una prueba en `select2.test.tsx`.

## Pendientes

Resueltos:

- ~~Ubicación del router `/v2/` en el back~~: está en `src/backends/kernel/core/v2_frontend.py`,
  sin imports de dominio y con los destinos en `settings.FRONTEND_V2_UPSTREAMS`.
- ~~Validar la matriz de versiones sobre Node 22.14.0 dentro del contenedor~~:
  hecho, con el cambio de vitest documentado arriba.

Abiertos:

- Contexto de usuario con sesión: `/api/users/me/` hoy acepta solo
  `TokenAuthentication`. Hay que habilitarlo con sesión o definir un endpoint
  equivalente. Es un cambio de autenticación: requiere revisión. **Mientras
  tanto el Drawer de `/v2/` no filtra por permisos del usuario**: muestra el
  árbol fijo del módulo.
- ~~Contrato versionado y chequeo en CI~~: cada módulo tiene su schema en
  `packages/api/` (`openapi.yaml` para VPSL, `openapi.celiaquia.yaml` para
  Celiaquía, este último generado con `--urlconf config.urls_frontend_v2`) y
  `.github/workflows/frontend-v2.yml` falla si el schema o los tipos quedaron
  viejos.
- ~~`front_celiaquia` en el compose de deploy~~: está en
  `docker/compose/docker-compose.deploy.yml`, con el mismo esquema que `front_vpsl`.


### Continuación local INS-A: formularios en validación

El piloto sisoc monta alta, edición y confirmación de eliminación en React bajo
/v2/sisoc/insumos/, usando los metadatos y POST multipart de la API web existente.
La sesión, CSRF y los permisos por operación siguen siendo responsabilidad de
Django. El proxy local de /api/web preserva Host mediante changeOrigin=false;
no se deben ampliar orígenes confiables para ocultar una reescritura del proxy.

El listado carga su CSS específica solo mientras está montado. Las mutaciones
de resultado incierto no se reintentan automáticamente; los avisos son locales
a la operación, en memoria y con apariencia Toastr. El archivo actual muestra su
nombre base y conserva la descarga protegida. Estado histórico del piloto:
[registro INS-A](../registro/cambios/2026-T4/2026-10-30-2785-listado-react-insumos.md).
La reconciliación local en Migracion-2 se sigue en
`odd/tasks/react-global-2785.md`; sus verificaciones y aceptación se distinguen
de las del origen. No se activaron rutas globales ni despliegues.

### Continuación local INS-B: categorías en validación

Las rutas locales `/v2/sisoc/insumos/categorias/`, `crear`, `<id>/editar` y
`<id>/eliminar` consumen `/api/web/insumos/categorias/`. `routes/categorias.tsx` las reconoce
con los mismos slashes de las URLs públicas originales y monta
`InsumosCategoriasList.tsx` o `InsumosCategoriaForm.tsx` dentro del mismo marco
INS-A. Los permisos de cada operación se verifican tanto en la entrada HTML como
en la API de sesión. Los POST son formularios URL-encoded; se reutilizan el Form
y los servicios de Django. Guardar, eliminar y cancelar vuelven al listado de
categorías con el aviso existente. No se agrega caché persistente: después de
eliminar una categoría, volver al circuito de insumos consulta nuevamente datos
y opciones. La paginación compartida vive en `insumosPagination.ts`. No se
sustituyen las rutas públicas originales ni se habilita React globalmente.

Estado de validación y límites:
[registro INS-B](../registro/cambios/2026-T4/2026-11-03-2785-react-categorias-insumos.md).

### Identidad local: entradas React sin montar

`identity_preview_patterns` (`src/backends/sisoc_core/usuarios/identity_preview.py`)
sirve el build de `apps/sisoc` en las rutas públicas de identidad solo dentro de
un URLconf sintético local; producción sigue usando los templates. El registro
`routes/index.ts` elige la pantalla por ruta: `/` y `/login/` montan `Login.tsx`, que consume
`/api/web/login/` y conserva el logout nativo por POST. Las demás rutas usan el
marco de Insumos, que acepta contenido y títulos opcionales para pantallas de
identidad sin cambiar su salida actual. Registro:
`../registro/cambios/2026-T4/2026-11-03-2785-react-login-logout.md`.

`/password/first-change/` monta `RequiredPasswordChange.tsx` dentro de ese marco,
alimentado solo por el DTO de presentación de `/api/web/password/first-change/`
(usuario, menú heredado y pie). No consulta `/api/web/session/`, no recibe
capacidades de negocio y conserva los enlaces originales del menú. Registro:
`../registro/cambios/2026-T4/2026-11-03-2785-react-cambio-obligatorio.md`.

`/mi-cuenta/` y `/mi-cuenta/confirmar/` montan `Account.tsx` en el mismo marco
(la confirmación como modal obligatorio sin cierre), con `/api/web/account/` y
`/api/web/account/confirm/`. Los mensajes de Django se muestran con
`InsumosToastList`, que respeta su nivel en un único contenedor Toastr. Registro:
`../registro/cambios/2026-T4/2026-11-04-2785-react-cuenta-confirmacion.md`.

El marco escribe los ítems principales del sidebar en el orden del template
original y les aplica el mismo `order` en línea, para que Tab recorra el menú
igual que la página nativa sin mover su posición visual. No define estilos de
foco propios: botones y enlaces usan los contornos de las hojas originales. El
logo móvil sigue siendo enfocable como en el template, «Volver» apunta a `/`
(destino por defecto del botón original) y el enlace de versión, también en el
login, apunta a `/novedades/`. Registro:
`../registro/cambios/2026-T4/2026-11-06-2785-paridad-teclado-shell.md`.

`/password_change/` y `/password_change/done/` montan `PasswordChange.tsx`,
alimentado por `/api/web/password/change/`. Conserva el template instalado de
Unfold, sin el marco SISOC, y el `PasswordChangeForm` estándar con contraseña
anterior; el éxito navega solo a `/password_change/done/`. Registro:
`../registro/cambios/2026-T4/2026-11-04-2785-react-cambio-voluntario.md`.

`/password_reset/`, `/password_reset/done/`, `/reset/done/` y las rutas de
confirmación `/reset/<uidb64>/<token>/` y su alias
`/password/reset/confirm/<uidb64>/<token>/` montan `PasswordReset.tsx` con el
marco de `user/password_reset_base.html`, sin el shell SISOC. La solicitud usa
`/api/web/password/reset/` y siempre navega a `/password_reset/done/`, coincida
o no la cuenta. El canje del token por la sesión sigue en la vista Django
original, que redirige a `set-password` antes de servir la UI: React nunca envía
el token y consulta `/api/web/password/reset/<uidb64>/`, que valida solo el
token de sesión en cada GET y POST. Registro:
`../registro/cambios/2026-T4/2026-11-06-2785-react-recuperacion-contrasena.md`.

`/grupos/`, `/grupos/crear/` y `/grupos/editar/<id>/` montan `Groups.tsx` en el
mismo marco, con las migas de pan originales, alimentado por `/api/web/groups/`
y sus rutas de alta y edición. El selector de permisos es propio de React y
reproduce el comportamiento del widget original, incluido el orden de catálogo
y el refresco de íconos; funciona para quienes ya pueden crear o editar grupos
sin depender de `/admin/jsi18n/`. Preferencias de columnas y CSV siguen en sus
rutas nativas. Registro:
`../registro/cambios/2026-T4/2026-11-04-2785-react-grupos.md`.

`/inicio/` monta `PendingSurvey.tsx` en el mismo marco, sin botón «Volver»,
con la portada original y el modal de la primera encuesta pendiente según
`/api/web/surveys/pending/`. Responder, posponer y descartar usan las acciones
URL-encoded de `/api/web/surveys/<id>/` y navegan al destino que devuelve el
servidor; Bootstrap y el script condicional originales operan sobre los nodos
React. Registro:
`../registro/cambios/2026-T4/2026-11-04-2785-react-respuesta-encuestas.md`.

`/usuarios/importar/` y `/usuarios/importar/lotes/<id>/` montan
`routes/userImport.tsx` en el mismo marco, alimentado por
`/api/web/users/import/` y sus rutas de lote. Importar solo encola el lote con
el Form y el servicio existentes; leer el estado nunca inicia ni reintenta el
lote y la reanudación es un único POST. Plantilla y CSV siguen en sus rutas
nativas y ningún DTO incluye contraseñas. Registro:
`../registro/cambios/2026-T4/2026-11-06-2785-react-importacion-usuarios.md`.

`/usuarios/credenciales-masivas/` y `/usuarios/credenciales-masivas/lotes/<id>/`
montan `routes/bulkCredentials.tsx`, que reutiliza el transporte y los controles
de la importación, alimentado por `/api/web/users/bulk-credentials/`. Las vistas
API heredan de las nativas, que siguen siendo las únicas que escriben; la
plantilla se descarga con el envío GET nativo del formulario. Registro:
`../registro/cambios/2026-T4/2026-11-06-2785-react-credenciales-masivas.md`.

`/usuarios/` y los pasos `/usuarios/borrar/<id>/` y `/usuarios/activar/<id>/`
montan `routes/usuarios.tsx` (listado en `usuariosList.tsx`, confirmación en
`usuariosState.tsx`), alimentado por `/api/web/users/list/` y
`/api/web/users/<id>/(deactivate|activate)/`. Las vistas API heredan de las
nativas: el alcance del actor, los filtros, las columnas y el cambio de estado
(`is_active`) siguen siendo suyos; React solo proyecta. Registro:
`../registro/cambios/2026-T4/2026-11-13-2785-react-usuarios-listado.md`.

El alta y la edición de usuarios (`/usuarios/crear/` y `/usuarios/editar/<id>/`)
tienen su transporte de sesión en `/api/web/users/create/` y
`/api/web/users/<id>/edit/` (`usuarios/web_user_form.py`, sobre las vistas y el
formulario nativos); la pantalla React se registra al completar el formulario.
Detalle en
`../registro/cambios/2026-T4/2026-11-13-2785-react-usuarios-formulario.md`.

### Agregar una pantalla React en `apps/sisoc`

`App.tsx` no conoce pantallas: recorre `ROUTES` de
`src/frontends/apps/sisoc/src/routes/index.ts` y monta la primera ruta cuyo
`match(pathname)` devuelve parámetros (`null` significa «no es mía»). Cada
unidad vive en su propio módulo de `src/frontends/apps/sisoc/src/routes/`
(`login.tsx`, `account.tsx`, `groups.tsx`, `passwordReset.tsx`, etc.) con su
prueba al lado. El último registro es `businessRoute`: atiende cualquier otra
ruta, carga `/api/web/session/` y monta el marco de negocio, que a su vez elige
entre `SHELL_ROUTES` (`categorias.tsx` antes que `insumos.tsx`, que acepta toda
ruta y muestra el listado). El marco (`routes/SisocShell.tsx`) y los marcos de
identidad (`identityFrames.tsx`) se reutilizan; no se copian.

Para agregar una pantalla:

1. Crear `routes/<unidad>.tsx` que exporte un `RouteDefinition` con `name`,
   `match` (rutas exactas, con los mismos slashes que la URL pública) y
   `render`. Si usa el marco SISOC, pasar uno de los marcos de
   `identityFrames.tsx` o agregar ahí uno nuevo.
2. Crear `routes/<unidad>.test.tsx`: renderiza `App` en la ruta, con
   `routes/testFixtures.ts`, y verifica transporte, título y contenido.
3. Registrarla en `ROUTES` de `routes/index.ts`, antes de `businessRoute`, y
   agregar sus rutas a la tabla de `routes/index.test.ts`.

No hace falta editar `App.tsx` ni `App.test.tsx`; este último cubre solo el
marco y el arranque de sesión. Registro:
`../registro/cambios/2026-T4/2026-11-06-2785-rutas-por-modulo.md`.

### Vertical remoto sobre G1: listado de actas de Inspecciones

Primera pantalla de un vertical servido por su propio runtime. El patrón para
las siguientes:

1. API web en el vertical, bajo `/api/web/<vertical>/` (prefijo en
   `url_prefixes` de `src/backends/config/backends.json`), con
   `WebGatePermission` antes de la regla de permiso del dueño. Conviene armar el
   contexto con la vista HTML existente para no duplicar filtros. Agregar las
   rutas al patrón de `src/backends/config/middlewares/admindocs.py` y regenerar
   `url_registry.json`.
2. Entrada sin montar en el vertical: hereda la vista nativa (guardas, 403, 404)
   y sirve el `index.html` con assets bajo el prefijo propio. Ejemplo:
   `actas_preview_patterns` en
   `src/backends/inspecciones/inspecciones/web_preview.py`.
3. Ruta en `apps/sisoc/src/routes/` con la URL nativa: el menú, el usuario y el
   pie vienen de `/api/web/session/` (core) y los datos de la API del vertical.
   Inspecciones usa el layout claro (`routes/ClaroFrame.tsx`), no el marco
   oscuro, y su selector remoto J2 (`routes/InspSelect2.tsx`).

Registro:
`../registro/cambios/2026-T4/2026-11-10-2785-react-inspecciones-actas.md`.

La ficha del acta (`/inspecciones/actas/<numero>/`) suma acciones: la API
(`src/backends/inspecciones/inspecciones/web_api_acta.py`) devuelve los textos
ya impresos como la plantilla y corre el `post()` nativo de anular y marcar
prueba, que responde `{"ok": true, "redirect": ...}`. La página siguiente
consume los mensajes y los muestra como toastr (`routes/inspeccionesToasts.tsx`);
los archivos siguen siendo las URLs nativas. Registro:
`../registro/cambios/2026-T4/2026-11-10-2785-react-inspecciones-acta-detalle.md`.

La pestaña Escuelas (`/inspecciones/` y el formulario de escuela) agrega
formularios en modal y en página: la API
(`src/backends/inspecciones/inspecciones/web_api_escuelas.py`) corre el `post()`
nativo y distingue el modal por `X-Requested-With`, como `panel.js`; un
formulario inválido vuelve como datos con errores (400), no como HTML. El
selector J2 (`routes/InspSelect2.tsx`) admite deshabilitado, vaciado dependiente y
`dropdownParent` del modal. Registro:
`../registro/cambios/2026-T4/2026-11-10-2785-react-inspecciones-escuelas.md`.

La pestaña Asignaciones (`/inspecciones/asignaciones/` y el alta de asignación)
sigue el mismo patrón: la API
(`src/backends/inspecciones/inspecciones/web_api_asignaciones.py`) corre
`AsignacionesView` y devuelve los totales de la jornada del servicio nativo, que
ignoran los filtros de estado, por lo que la pantalla no los deriva de la página;
el alta corre el `post()` nativo y «Quitar» es un POST propio con `confirm`, sin
reintento. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-inspecciones-asignaciones.md`.

El Tablero (`/inspecciones/tablero/`) consulta cada 5 s el mismo JSON que la
página nativa: la API
(`src/backends/inspecciones/inspecciones/web_api_tablero.py`) devuelve sin tocarla
la respuesta de las vistas nativas de datos, CSV y descarga de actas (PDF o ZIP), de
modo que cifras, filas, mapa, CSV y ZIP salen del mismo servicio y la pantalla no
recalcula nada. El mapa carga Leaflet del mismo CDN y con los mismos hashes que la
nativa. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-inspecciones-tablero.md`.

Seguimientos compartidos de la migración: el selector J2 deja el foco en la
caja al abrir y responde al teclado como Select2 4.1 nativo (Enter/Espacio/Alt+↓
abren; Escape/Tab/Alt+↑ cierran sin mover el foco), y `SisocShell` recibe
`{% block app-header %}` como prop `appHeader` (botones de PAS, nombre del
comedor en AC01) en lugar de portales. Los listados de Duplas, AC01 y CDF
comparten la barra de filtros de `advanced_filters.js`, el modal de columnas,
el encabezado con orden del servidor y la paginación en
`routes/listControls.tsx`. Registros:
`../registro/cambios/2026-T4/2026-11-11-2785-inspselect2-foco-nativo.md`,
`../registro/cambios/2026-T4/2026-11-11-2785-shell-app-header.md` y
`../registro/cambios/2026-T4/2026-11-11-2785-listados-compartidos.md`.

### Vertical remoto CDI: reportes

Pantallas del backend CDI sobre G1, con el mismo patrón que Inspecciones pero
en el marco oscuro (`includes/main.html`). `src/backends/cdi/cdi_runtime/web_api_urls.py`
agrupa las rutas `/api/web/cdi/` del backend y `cdi_preview_patterns`
(`src/backends/cdi/centrodeinfancia/web_preview.py`) monta las entradas en un
URLconf local con el mismo `permissions_any_required` de `src/backends/cdi/centrodeinfancia/urls.py`.
En el front, `routes/cdiFrame.tsx` carga `/api/web/session/` y la API del
vertical, dibuja `SisocShell` y agrega el botón «Consultas» de la cabecera.

- `/centrodeinfancia/reportes/` (`routes/cdiReportes.tsx`): resumen y selectores;
  el XLSX es la descarga nativa.
- Observaciones (`routes/cdiObservaciones.tsx`): alta, ficha, edición y baja
  sobre las vistas nativas, con el veto de auditoría CDI-A3 también en el HTML.
- `/centrodeinfancia/listar` (`routes/cdiCentros.tsx`, CDI09.01): listado de
  centros con filtros, columnas, orden local y páginas de 10; el CSV y el PDF de
  nómina de niños siguen siendo descargas nativas.
- `/centrodeinfancia/<centro>/nomina/<nómina>/ver/` (`routes/cdiNomina.tsx`,
  CDI04.01): ficha de un destinatario de la nómina; los valores salen del
  backend con las mismas expresiones del template nativo.
- `/centrodeinfancia/<centro>/nomina/` (`routes/cdiNominaLista.tsx`,
  CDI04.02/CDI04.03): lista de la nómina con métricas, filtros locales, páginas de 100
  y el modal «Derivar»; la derivación es el único POST y ejecuta la función nativa
  `nomina_centrodeinfancia_derivar`. Alta, edición y baja siguen siendo enlaces nativos.
- `/centrodeinfancia/detalle/<centro>` (`routes/cdiCentroDetalle.tsx`, CDI09.01): ficha
  del centro con héroe, carpeta de solapas laterales, resumen de nómina, trabajadores,
  formularios, calidad y observaciones. Los tres POST (estado de un usuario, baja de un
  trabajador, alta de observación) ejecutan las vistas nativas y recargan la ficha; la
  contraseña temporal sigue la regla nativa por fila y la respuesta es `no-store`. Con
  `CDI_INTERVENCIONES_VISIBLE` activa la API responde 409 y la vista previa sirve el HTML.
- `/centrodeinfancia/intervencion/detalle/<id>/` (`routes/cdiDocumentacion.tsx`, CDI06/CDI-F2):
  detalle de una intervención; «Descargar» usa la descarga autenticada por objeto
  `/api/web/cdi/intervenciones/<id>/documentacion/` (bytes del storage del objeto, `private, no-store`)
  y no cierra el alias `/media/documentacion/`, que depende del preflight de ownership del contrato.
- `/centrodeinfancia/<centro>/trabajadores/<trabajador>/` (`routes/cdiTrabajadores.tsx`, CDI05):
  ficha de un trabajador con las siete tarjetas plegables del template nativo; los valores
  salen de `web_api_trabajador_detalle.py` con las mismas expresiones y la baja usa el
  endpoint existente `trabajadores/<id>/eliminar/`. Las entradas de vista previa de los
  trabajadores están en `centrodeinfancia/web_preview_trabajadores.py`.
- `/centrodeinfancia/<centro>/trabajadores/crear/` y `.../<trabajador>/editar/`
  (`routes/cdiTrabajadoresForm.tsx` y `cdiTrabajadoresForm.behavior.ts`, CDI05): búsqueda por DNI,
  progreso y siete tarjetas; cada campo es el marcado `as_crispy_field` del formulario nativo
  (`web_api_trabajador_form.py` ejecuta las vistas nativas, con aprovisionamiento y veto CDI-A3)
  y los scripts de la plantilla corren como comportamiento del formulario. El POST es
  urlencoded, único y sin reintento.
- `/centrodeinfancia/<centro>/generar-usuario/` (`routes/cdiUsuariosGenerar.tsx`, CDI01.01):
  generar usuario referente sobre `GenerarUsuarioCDIView`. La contraseña temporal solo viaja en la
  respuesta (`no-store`) del POST que crea el usuario y vive en el estado del componente, nunca en
  almacenamiento, URL ni historial. El bloque RENAPER compartido (`routes/cdiRenaperBloque.tsx`:
  agregar, DNI, verificado y manual, token firmado) consulta `/api/web/cdi/renaper/<bloque>/`, siempre
  simulado en las pruebas.

El menú lateral de `SisocShell` y `ClaroFrame` dibuja los grupos anidados con el
marcado de cada nivel del template y los abre y resalta con las mismas
condiciones `'<fragmento>' in pagina_actual`, de modo que las subpáginas mantienen
la rama abierta; `headerItems` recibe el botón «Consultas» y `activePath` permite
evaluar las reglas sobre otra ruta. Registro:
`../registro/cambios/2026-T4/2026-11-10-2785-shell-menu-tercer-nivel.md`.
Registros:
`../registro/cambios/2026-T4/2026-11-10-2785-react-cdi-reportes.md` y
`../registro/cambios/2026-T4/2026-11-10-2785-react-cdi-observaciones.md`,
`../registro/cambios/2026-T4/2026-11-12-2785-react-cdi-centros-listado.md` y
`../registro/cambios/2026-T4/2026-11-12-2785-react-cdi-nomina-ficha.md` y
`../registro/cambios/2026-T4/2026-11-12-2785-react-cdi-nomina-lista.md` y
`../registro/cambios/2026-T4/2026-11-12-2785-react-cdi-centro-detalle.md` y
`../registro/cambios/2026-T4/2026-11-13-2785-react-cdi-documentacion.md`.
`../registro/cambios/2026-T4/2026-11-13-2785-react-cdi-trabajador-ficha.md` y
`../registro/cambios/2026-T4/2026-11-13-2785-react-cdi-trabajador-form.md`.
`../registro/cambios/2026-T4/2026-11-13-2785-react-cdi-renaper-generar-usuario.md`.
### Vertical remoto sobre G1: Duplas (equipo técnico) de Comedores

Segunda aplicación del patrón, ahora con el marco nativo `includes/main.html`
(`legacyIdentityFrame` sobre `routes/SisocShell.tsx`):

- Comedores publica `/api/web/comedores/` en `backends.json`. Cada app del
  backend suma su `include` en
  `src/backends/comedores/comedores_runtime/web_api_urls.py`, montado en
  `src/backends/comedores/comedores_runtime/urls.py`.
- `src/backends/comedores/duplas/web_api.py` corre la vista nativa
  (`DuplaListView`, `DuplaDetailView`) y proyecta su contexto: filtros
  combinables, preferencias de columnas (`duplas_list`), paginación y mensajes.
  La regla nativa (`auth.role_admin`, con el bypass de superusuario) va
  después de `WebGatePermission`. El CSV sigue siendo el GET nativo
  `/equipo-tecnico/exportar/`.
- `duplas_preview_patterns` (`src/backends/comedores/duplas/web_preview.py`)
  aplica la misma guarda de URL y sirve los assets bajo `/equipo-tecnico/react/`.
- Ruta `routes/duplas.tsx` (listado y ficha). El menú marca «Equipos Técnicos»
  en todas las páginas del prefijo, como la plantilla nativa: para eso el marco
  legado acepta `activePath` (opcional; sin él no cambia nada).

- Alta, edición y baja (`routes/duplasFormRoute.tsx`, `routes/duplasForm.tsx`):
  el POST va a la API, que corre el `post()` de la vista nativa (ModelForm,
  señales del coordinador, baja lógica en cascada y mensajes) y responde
  `{"ok": true, "redirect": ...}` o el formulario con errores (400). El
  selector de técnicos reproduce Select2 4.1 múltiple
  (`routes/duplasSelect2.tsx`).

Registros:
`../registro/cambios/2026-T4/2026-11-10-2785-react-duplas-listado.md` y
`../registro/cambios/2026-T4/2026-11-10-2785-react-duplas-abm.md`.
### Vertical remoto CDF: centros

Centro de Familia publica `/api/web/cdf/` (`src/backends/cdf/cdf_runtime/web_api_urls.py`,
montado en `src/backends/cdf/cdf_runtime/urls.py`). `src/backends/cdf/centrodefamilia/web_api.py`
corre `CentroListView` y `CentroDetailView` y proyecta su contexto (NoCount con
`count: null`); el panel de credenciales CR1 es un pedido aparte. `cdf_preview_patterns`
(`src/backends/cdf/centrodefamilia/web_preview.py`) monta las entradas con la misma
guarda `view_centro` y assets en `/centrodefamilia/react/assets/`. En el front,
`routes/cdfCentros.tsx` usa `routes/cdfFrame.tsx` y `routes/listControls.tsx`. Alta,
edición y baja (`routes/cdfCentroForm.tsx`) envían a `src/backends/cdf/centrodefamilia/web_api_gestion.py`,
que corre el `post()` nativo (mensajes y baja lógica en cascada incluidos). Registros:
`../registro/cambios/2026-T4/2026-11-10-2805-react-cdf-centros-consulta.md` y
`../registro/cambios/2026-T4/2026-11-10-2805-react-cdf-centros-gestion.md`.

### Vertical remoto Dispositivos: listado, legajo y mapa

El backend `dispositivos` publica `/api/web/dispositivos/`
(`src/backends/dispositivos/dispositivos_runtime/web_api_urls.py`, montado en
`src/backends/dispositivos/dispositivos_runtime/urls.py`). La raíz del prefijo queda libre
(el core la reserva para el nombre del vertical), así que el listado vive en `listado/`.
`src/backends/dispositivos/dispositivos/web_api.py` corre `DispositivoListView`,
`DispositivoDetailView` y `DispositivoMapView` y proyecta su contexto; las secciones del
legajo salen de `build_detalle_secciones` (`src/backends/dispositivos/dispositivos/views.py`),
la misma función que usa el HTML. `dispositivos_preview_patterns`
(`src/backends/dispositivos/dispositivos/web_preview.py`) monta las entradas con las guardas
nativas y assets en `/dispositivos/react/assets/`. En el front, `routes/dispositivos.tsx`
(listado y legajo) y `routes/dispositivosMapa.tsx` (Leaflet por CDN con el mismo SRI y la
consulta de ubicación en serie). Registro:
`../registro/cambios/2026-T4/2026-11-11-2785-react-dispositivos-consulta.md`.
Generar usuario referente (`routes/cdfCentroUsuario.tsx`) usa
`src/backends/cdf/centrodefamilia/web_api_usuario.py`, que corre
`GenerarUsuarioCDFView` (404 antes de la regla de delegación, territorio y cupo)
y devuelve solo la proyección CR1; la contraseña temporal vive en la memoria del
componente. Preinscripción, beneficiarios y responsables (`routes/cdfBeneficiarios.tsx`,
con `routes/cdfDataTable.tsx`) usan `src/backends/cdf/centrodefamilia/web_api_beneficiarios.py`:
las búsquedas RENAPER y el alta corren el servicio nativo sin encolar mensajes, y
`exportar/disponible/` reemplaza el aviso del CSV vacío. Registros:
`../registro/cambios/2026-T4/2026-11-11-2805-react-cdf-centros-usuario.md` y
`../registro/cambios/2026-T4/2026-11-11-2805-react-cdf-beneficiarios.md`.
La ficha de la actividad y sus participantes (`routes/cdfActividades.tsx`,
`routes/cdfParticipantes.tsx`, con `routes/cdfCrispy.tsx`) usan
`src/backends/cdf/centrodefamilia/web_api_actividades.py`: cada endpoint corre la vista
nativa (alta por búsqueda o formulario, baja con promoción automática y promoción
manual) y responde su redirección como JSON; el mensaje queda encolado para la página
de destino. `cdf_actividades_preview_patterns`
(`src/backends/cdf/centrodefamilia/web_preview_actividades.py`) monta las entradas.
La planilla de asistencia (`routes/cdfAsistencia.tsx`) usa
`src/backends/cdf/centrodefamilia/web_api_asistencia.py`, que corre
`AsistenciaActividadView` (404, después `puede_tomar_asistencia_cdf`); lo no marcado se
guarda como ausente. Registros: `../registro/cambios/2026-T4/2026-11-13-2785-react-cdf-actividades-participantes.md`
y `../registro/cambios/2026-T4/2026-11-13-2785-react-cdf-asistencia.md`.
El listado de actividades y el catálogo (`routes/cdfActividadList.tsx`) usan
`src/backends/cdf/centrodefamilia/web_api_actividades_gestion.py`, que corre
`ActividadCentroListView` y `ActividadCreateView`; el orden por columna es local, como
`listSort.js`. Registro: `../registro/cambios/2026-T4/2026-11-13-2785-react-cdf-actividades-lista-catalogo.md`.
El formulario de la actividad de un centro (`routes/cdfActividadForm.tsx`) usa
`src/backends/cdf/centrodefamilia/web_api_actividad_form.py`, que corre
`ActividadCentroCreateView` y `ActividadCentroUpdateView`; la hora usa flatpickr desde el
CDN, como la página nativa. Registro: `../registro/cambios/2026-T4/2026-11-13-2785-react-cdf-actividad-formulario.md`.

DataCalle (operativos del backoffice) comparte el runtime y el prefijo: sus rutas viven
bajo `/api/web/dispositivos/datacalle/` (`src/backends/dispositivos/datacalle/web_api_urls.py`,
incluido desde `src/backends/dispositivos/dispositivos_runtime/web_api_urls.py`). `src/backends/dispositivos/datacalle/web_api.py`
corre las vistas nativas de listado, ficha, formulario, cierre y baja (alcance provincial
de `apply_relevamientos_scope`, `RelevamientoForm` con `actor`, `cerrar_relevamiento`
idempotente y `delete_relevamiento` con su cascada) y `datacalle_preview_patterns`
(`src/backends/dispositivos/datacalle/web_preview.py`) monta las entradas con assets en
`/datacalle/react/assets/`. En el front, `routes/datacalleRelevamientos.tsx`,
`routes/datacalleRelevamientoForm.tsx` y `routes/datacalleSelect2.tsx`. Registro:
`../registro/cambios/2026-T4/2026-11-11-2785-react-datacalle-operativos.md`.

La ficha del caso (`/datacalle/casos/<uuid>/`) sale de `GET /api/web/dispositivos/datacalle/casos/<uuid>/` (`CasoDetailWebView`, permiso `view_encuesta`, solo lo que muestra la ficha nativa) y de `routes/datacalleCasos.tsx`. La API por token `api/datacalle/` no cambia. Registro: `../registro/cambios/2026-T4/2026-11-12-2785-react-datacalle-casos.md`.

### Comedores sobre G1: catálogos con el marco oscuro

ABM de montos por programa (`/montoprestacion/`, CO05) y catálogo PNUD, con
escritura a través de G1. Sigue el patrón del listado de actas, con dos diferencias:

1. La API (`src/backends/comedores/comedores/web_api_montos.py`) ejecuta la
   vista nativa también para escribir: `form_valid` guarda, registra el
   historial y deja el mensaje; la API devuelve `{"ok": true, "redirect": ...}`
   o el formulario ligado con 400. Los valores se pasan por el motor de
   plantillas, así el texto es el mismo que en el HTML.
2. Las pantallas que extienden `includes/main.html` usan
   `routes/MainFrame.tsx`: carga `/api/web/session/` y el endpoint del
   vertical, agrega `hitos.css` y la clase `app-loaded` del `body`, y le pasa a
   `SisocShell` el `activePath` cuando el menú nativo marca la entrada por un
   fragmento de la ruta (`'montoprestacion' in pagina_actual`).

Las rutas de `src/backends/comedores/comedores_runtime/web_api_urls.py` se suman como una inclusión
por pantalla. La entrada sin montar es
`src/backends/comedores/comedores/web_preview_catalogos.py`, con assets en
`/comedores/react/assets/`.

El catálogo global de actividades PNUD (CO04.02,
`src/backends/comedores/comedores/web_api_pnud.py`) usa el mismo marco y la
regla del mixin nativo (`ActividadPnudPermissionMixin`).

Registros:
`../registro/cambios/2026-T4/2026-11-10-2785-react-montos.md` y
`../registro/cambios/2026-T4/2026-11-10-2785-react-actividades-pnud.md`.

Gestor de templates (AD01) y acompañamiento (AC01) siguen el mismo marco:
`src/backends/comedores/admisiones/web_api_templates.py` proyecta las vistas de
consulta del gestor y sus acciones siguen siendo formularios POST a las URLs
nativas (alta y editor de versión quedan en Django);
`src/backends/comedores/acompanamientos/web_api.py` proyecta listado y ficha y
restaura hitos con `admision_id` explícito y lista blanca de los 23 hitos.
Registros: `../registro/cambios/2026-T4/2026-11-10-2785-react-ad01-gestor-templates.md` y
`../registro/cambios/2026-T4/2026-11-10-2785-react-ac01-acompanamientos.md`.

Detalle del informe técnico de admisión (AD02.01):
`src/backends/comedores/admisiones/web_api_informes.py` ejecuta
`InformeTecnicoDetailView` con el acceso actual y las acciones (subir DOCX editado,
revisar) siguen siendo POST a la URL nativa. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-admisiones-informe-detalle.md`.
El editor del informe (alta y edición) usa el mismo marco: `web_api_informe_formulario.py` proyecta el
formulario efectivo y `web_api_informe_guardar.py` guarda borrador y finalización con el circuito nativo.
Registros: `../registro/cambios/2026-T4/2026-11-12-2785-react-admisiones-informe-formulario.md`,
`../registro/cambios/2026-T4/2026-11-12-2785-react-admisiones-informe-guardar.md` y
`../registro/cambios/2026-T4/2026-11-12-2785-react-admisiones-informe-editor.md`.

Circuito técnico/legal de admisiones (AD03.01, entrega de listados):
`src/backends/comedores/admisiones/web_api_listas.py` ejecuta `AdmisionesTecnicosListView` y
`AdmisionesLegalesListView` (alcance por actor, filtros, orden, columnas y paginación nativos) bajo
`/api/web/comedores/admisiones/{tecnicos,legales}/`; el módulo React es `admisionesSeguimiento.tsx`
y las filas siguen enlazando a las páginas nativas. El detalle de admisión (`web_api_detalle.py`, `admisionesDetalle.tsx`) corre `AdmisionDetailView` con
el acceso actual; «Forzar Cierre» sigue siendo el POST nativo. Registros:
`../registro/cambios/2026-T4/2026-11-12-2785-react-admisiones-seguimiento-listas.md` y
`../registro/cambios/2026-T4/2026-11-12-2785-react-admisiones-seguimiento-detalle.md`.

Editor técnico de admisión (AD03.02, `/comedores/admisiones/tecnicos/editar/<pk>`):
`web_api_editor.py` proyecta el contexto de `AdmisionesTecnicosUpdateView` en
`/api/web/comedores/admisiones/<pk>/` y ejecuta el despacho nativo del `post()` (sin la rama
genérica de `UpdateView`) en `<pk>/acciones/<accion>/`; el módulo React es `admisionesEditor.tsx`
dentro de la ruta `admisionesSeguimiento.tsx`. Cuando la página nativa dibuja el formulario
embebido de informe y carátula, `informe_embebido` lo proyecta y `acciones/informe-caratula/` lo guarda
(informe y carátula juntos); el modo embebido es el editor de informe de AD02.
Registro: `../registro/cambios/2026-T4/2026-11-12-2785-react-admisiones-editor-tecnico.md`.

Detalle legal de admisión (AD03.03, `/comedores/admisiones/legales/ver/<pk>` y
`.../legales/revisar-complementario/<pk>`): `web_api_legales.py` proyecta el contexto de
`AdmisionesLegalesDetailView` en `/api/web/comedores/admisiones/legales/<pk>/` y cada acción
(`<pk>/acciones/<accion>/`) alimenta al handler nativo de `LegalesService` con solo los campos del
botón; los mensajes del servicio se devuelven en `messages` y los formularios inválidos responden 400.
El módulo React es `admisionesLegales.tsx`; los PDF y DOCX siguen siendo enlaces nativos. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-admisiones-legales-detalle.md`.

Expedientes de pago de un comedor (EX01) usan el mismo marco:
`src/backends/comedores/expedientespagos/web_api.py` ejecuta las vistas nativas
de listado, ficha, alta, edición y baja lógica con el acceso actual (lectura con
sesión, escritura con uno de los cuatro permisos de lectura) y nunca recalcula
montos. Registro:
`../registro/cambios/2026-T4/2026-11-11-2785-react-expedientes-pagos.md`.

El listado global de rendiciones mensuales (RM01.01, primera entrega) usa el
mismo marco: `src/backends/comedores/rendicioncuentasmensual/web_api.py`
ejecuta `RendicionCuentaMensualGlobalListView` (filtros por tipo, territorial y
estado, columnas, paginación de 25) con los cinco permisos de hoy y arma cada
celda con el include nativo; el CSV sigue siendo `listado/?export=csv`. Las URL
nativas conservan el prefijo duplicado `/rendicioncuentasmensual/rendicioncuentasmensual/`.
Registro:
`../registro/cambios/2026-T4/2026-11-11-2785-react-rendicion-mensual-listado.md`.

La rendición de cuentas final (RF01.01 a RF01.03) usa el
mismo marco: `src/backends/comedores/rendicioncuentasfinal/web_api.py` ejecuta
`RendicionCuentasFinalDetailView` (conserva el `get_or_create` del GET) y
`DocumentosRendicionCuentasFinalListView` con el alcance por área de
`filter_documentos_por_area`, y las seis acciones (validar, subsanar, switch,
adjuntar, crear y eliminar) repiten los efectos y mensajes nativos; exige
`view_rendicioncuentasfinal`, el permiso de las pantallas nativas. Las rutas Django y `/media/rendicion_cuentas_final/` no
cambian. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-rendicion-final-consulta.md`.

Los comunicados publicados (CM03.01) usan el mismo marco:
`src/backends/comedores/comunicados/web_api_views.py` ejecuta
`ComunicadoListView` y `ComunicadoDetailView` (solo internos publicados y
vigentes, detalle sin filtro para gestores) y no reutiliza la API PWA. Registro:
`../registro/cambios/2026-T4/2026-11-11-2785-react-comunicados-publicados.md`.

La gestión de comunicados (CM02.01) suma `GET .../comunicados/gestion/`, que ejecuta
`ComunicadoGestionListView` con su guarda de permisos (403 «No tiene permisos para
gestionar comunicados.»), y el pie del detalle para gestores. Publicar, archivar y
destacar siguen siendo formularios POST nativos con CSRF; React solo los dibuja y
pregunta antes de publicar o archivar. La vista previa sirve ambas pantallas en React
a todos los perfiles. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-comunicados-gestion.md`.

Los relevamientos (R01.01) suman `GET .../relevamientos/<comedor_pk>/` y
`GET .../relevamientos/<comedor_pk>/relevamiento/<pk>/`, que ejecutan
`RelevamientoListView` y `RelevamientoDetailView` y proyectan su contexto; las
secciones de datos del detalle salen del propio parcial nativo, convertido a un árbol de elementos permitidos
(la misma que alimenta el PDF). Los modales de alta, seguimiento, asignación,
revisión y baja son formularios POST nativos con CSRF; el acceso, incluido el
detalle sin alcance por comedor, es el de hoy. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-relevamientos-listado-detalle.md`.

El detalle de seguimientos (R03.01), de seguimientos PNUD y de actas complementarias
(R02.01) suma `GET .../relevamientos/<comedor_pk>/relevamiento/<r>/seguimientos/<pk>/`
(y `.../primero/`), `.../pnud/<pk>/` y `.../actas/<pk>/`, que ejecutan sus vistas
nativas con los mismos 404 y proyectan su contexto. Los PDF, las ediciones, las
revisiones y las bajas siguen siendo enlaces y POST nativos con CSRF. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-relevamientos-seguimientos-actas.md`.

Las mutaciones de relevamientos (R01.02) suman `POST .../relevamiento/numero-if/`,
`GET/POST .../relevamiento/<pk>/eliminar/` y `POST .../relevamiento/<pk>/revision/`: cada
una repite el permiso y las reglas de su vista nativa y reutiliza su código (baja lógica
en cascada, `aplicar_revision_coordinador`), responde `{ok, message, redirect}` o el
error con 400, 403 o 409 y exige CSRF. React muestra la confirmación de baja con su vista
previa y nunca reenvía un resultado incierto. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-relevamientos-mutaciones.md`.

La edición, baja y revisión de seguimientos, seguimientos PNUD y actas (R03.02, R02.02)
suman endpoints bajo `/api/web/comedores/relevamientos/<comedor>/` que ejecutan el código
nativo (`SeguimientoEditor`, `ActaComplementariaEditor`, las vistas de baja y
`aplicar_revision_coordinador`). Los formularios viajan como el marcado real de cada campo
(`{{ field }}`) con sus errores y React los pinta sin controlar, así que los nombres y valores
del POST son los nativos; un formulario inválido responde 400 sin escribir nada. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-relevamientos-formularios.md`.

### Ciudadano 360: aportes de verticales (C04)

La ficha React (`routes/ciudadano360.tsx`, solo vista previa local hasta que C05.01
migre el resto) pide `GET /api/web/ciudadanos/<pk>/` y, con la lista `aportes` que
arma el servidor, cada aporte a `/api/web/<backend>/ciudadanos/<pk>/aportes/<aporte>/`
(vista genérica `ciudadanos.web_aportes`, proyector registrado por cada dueño). Las
tarjetas viven en `routes/ciudadano360Aportes.tsx` y degradan solas a «No disponible»
(C2). Ver `docs/registro/cambios/2026-T4/2026-11-12-2785-react-ciudadano360-aportes.md`.

La ficha completa (C05.01) suma la proyección `ciudadanos.web_ficha` (datos, familia,
historial, interacciones, acciones y mensajes ya formateados con las reglas del template)
y `routes/ciudadano360Ficha.tsx` (pestañas, Datos Personales, Grupo Familiar, gráfico
Chart.js, programas, interacciones y observaciones). Ver
`docs/registro/cambios/2026-T4/2026-11-12-2785-react-ciudadano360-ficha.md`.

La baja de un ciudadano (C05.03) es `routes/ciudadanoBaja.tsx` sobre
`/api/web/ciudadanos/<pk>/baja/` (`ciudadanos.web_baja`, que corre la vista nativa de baja
y proyecta su confirmación). Ver
`docs/registro/cambios/2026-T4/2026-11-12-2785-react-ciudadano-baja.md`.

Agregar familiar (C05.02) es `routes/ciudadanoFamiliar.tsx` sobre
`/api/web/ciudadanos/<pk>/familiares/nuevo/` (`ciudadanos.web_familiar`, que corre la vista
nativa con su formulario). Ver
`docs/registro/cambios/2026-T4/2026-11-12-2785-react-ciudadano-familiar.md`.

El alta y la edición de un ciudadano (C05.02) son `routes/ciudadanoForm.tsx` sobre
`/api/web/ciudadanos/crear/` y `/api/web/ciudadanos/<pk>/editar/` (`ciudadanos.web_form`, que
corre las vistas nativas; RENAPER solo se simula en las pruebas). Ver
`docs/registro/cambios/2026-T4/2026-11-12-2785-react-ciudadano-form.md`.

El historial de auditoría de una instancia es `routes/ciudadanoHistorial.tsx` sobre
`/api/web/auditoria/<app>/<modelo>/<pk>/` (`audittrail.web_historial`, que corre la vista
nativa; la exportación sigue siendo el `GET` nativo). Ver
`docs/registro/cambios/2026-T4/2026-11-13-2785-react-ciudadano-historial.md`.

El listado global de auditoría (`/auditoria/`, `GET /api/web/auditoria/listado/`) y el detalle de un
evento (`/auditoria/evento/<id>/`, `GET /api/web/auditoria/evento/<id>/`) son
`routes/ciudadanoHistorial.tsx` (modo global) y `routes/auditoriaEvento.tsx`, sobre
`audittrail.web_auditoria`: corren `AuditLogListView` y `AuditLogDetailView` con su `dispatch`. La
exportación sigue siendo el `GET` nativo. Ver
`docs/registro/cambios/2026-T4/2026-11-13-2785-react-auditoria-listado-evento.md`.
El listado de comedores (CO07.01) es `routes/comedores.tsx` sobre
`/api/web/comedores/comedores/` (`comedores.web_api_comedores`, que corre `ComedorListView`; la
exportación y los formularios siguen nativos) y la baja es `routes/comedorBaja.tsx` sobre
`/api/web/comedores/comedores/<pk>/baja/` (`ComedorDeleteView`). El alta y la edición son `routes/comedorForm.tsx` sobre
`/api/web/comedores/comedores/formulario/` y `crear/`/`<pk>/editar/` (`ComedorCreateView` y
`ComedorUpdateView`). Ver
`docs/registro/cambios/2026-T4/2026-11-13-2785-react-comedor-listado.md`.

La nómina de un comedor (CO01, `/comedores/<id>/admision/<admision>/nomina/` y `/comedores/<id>/nomina/`) es
`routes/comedorNomina.tsx` sobre `/api/web/comedores/comedores/<id>/[admision/<admision>/]nomina/`
(`comedores.web_api_nomina`, que corre `NominaDetailView` y `NominaDirectaDetailView`). El cambio de estado y la
derivación son `POST` de `comedores.web_api_nomina_acciones` sobre las funciones nativas; la baja y el alta siguen
siendo las rutas nativas hasta sus entregas. Ver
`docs/registro/cambios/2026-T4/2026-11-13-2785-react-comedor-nomina-lectura.md`.

El historial de asistencia de la nómina (CO01, `/comedores/<id>/admision/<admision>/nomina/asistencia/`) es
`routes/comedorAsistenciaHistorial.tsx` sobre
`/api/web/comedores/comedores/<id>/admision/<admision>/nomina/asistencia/`
(`comedores.web_api_asistencia_historial`, que corre `NominaAsistenciaHistorialView`). Solo lee: la asistencia la
registra la PWA y el PDF mensual sigue siendo un enlace nativo al archivo. Ver
`docs/registro/cambios/2026-T4/2026-11-13-2785-react-comedor-asistencia-historial.md`.

El historial de certificaciones mensuales de prestaciones (CO05.01, `/comedores/<id>/certificaciones-prestaciones/`)
es `routes/comedorCertificaciones.tsx` sobre `/api/web/comedores/comedores/<id>/certificaciones-prestaciones/`
(`comedores.web_api_certificaciones`, que corre `CertificacionesPrestacionesHistorialView`). Solo lee: el PDF sigue
siendo la descarga binaria nativa. Ver
`docs/registro/cambios/2026-T4/2026-11-13-2785-react-comedor-certificaciones.md`.

El histórico de transacciones DW (CO07.01, `/comedores/<id>/transacciones`) es `routes/comedorTransacciones.tsx` sobre
`/api/web/comedores/comedores/<id>/transacciones/` (`comedores.web_api_transacciones`, que corre
`ComedorTransaccionesDetailView` y su servicio DW existente). Solo lee: Transferido es `debito_total` y Gastado
`credito_total`, y un fallo del DW se ve como falta de datos. Ver
`docs/registro/cambios/2026-T4/2026-11-13-2785-react-comedor-transacciones.md`.

Los colaboradores de un comedor (CO03.01, `/comedores/<id>/colaboradores/crear/` y
`/comedores/<id>/colaboradores/<colaborador>/editar/`) son `routes/comedorColaboradores.tsx` sobre
`/api/web/comedores/colaboradores/comedor/<id>/` (`comedores.web_api_colaboradores`, que corre el `dispatch` de
`ColaboradorEspacioCreateView` y `ColaboradorEspacioUpdateView`; la baja es el `POST` `.../<colaborador>/eliminar/`
sobre `ColaboradorEspacioDeleteView`, sin pantalla propia). La búsqueda por DNI es el formulario GET nativo. Ver
`docs/registro/cambios/2026-T4/2026-11-13-2785-react-comedor-colaboradores.md`.

Las actividades de un espacio PNUD (CO03.02, `/comedores/<id>/actividades/crear/` y
`/comedores/<id>/actividades/<actividad>/editar/`) son `routes/comedorActividades.tsx` sobre
`/api/web/comedores/actividades-espacio/comedor/<id>/` (`comedores.web_api_actividades_espacio`, que corre el
`dispatch` de `ActividadEspacioPWACreateView` y `ActividadEspacioPWAUpdateView`). Cada horario es un registro:
la pantalla manda los campos repetidos `schedule_*` y reproduce el filtro por categoría y las filas del script de la
plantilla. Ver `docs/registro/cambios/2026-T4/2026-11-13-2785-react-comedor-actividades.md`.

El catálogo global de cursos de la app mobile (CO04.01, `/comedores/configuracion/cursos-app-mobile/`) es
`routes/comedorCursos.tsx` sobre `/api/web/comedores/cursos-app-mobile/` (`comedores.web_api_cursos`, que corre el
`dispatch` de las cuatro vistas de `views/cursos_app_mobile.py`). El alta y la edición envían multipart con la imagen y la
baja es la baja lógica nativa. Ver `docs/registro/cambios/2026-T4/2026-11-13-2785-react-comedor-cursos.md`.

### DDJJ pública PAS: entrada React sin montar

`apps/pas` es una app propia (base `/v2/pas/`) que reemplaza solo la
presentación del formulario público de declaración jurada y su confirmación.
Usa la hoja `custom/css/pas_ddjj.css` y la marca de PAS, no el marco SISOC ni
un tema MUI. `ddjj_preview_patterns`
(`src/backends/pas/pas/ddjj_preview.py`) la sirve en la URL canónica
`/pas/ddjj/formulario/<token>` y en `/pas/ddjj/confirmacion` solo dentro de un
URLconf local; las invitaciones inexistentes o no disponibles y los POST siguen
con la vista nativa. Los datos y el envío usan
`/pas/ddjj/formulario/<token>/datos` y `/enviar`, fuera de `/api/` para que la
sesión web restringida se bloquee igual que en el HTML (política P1), con CSRF
también para visitantes anónimos. El envío no se reintenta: ante un resultado
distinto de éxito o error de validación se vuelve por GET a la URL canónica.
Registro:
`../registro/cambios/2026-T4/2026-11-06-2806-react-ddjj-publica.md`.

### PAS back office sobre G1: buscador, panel y áreas

Las pantallas autenticadas de PAS van en `apps/sisoc` (marco oscuro con
`routes/MainFrame.tsx`), no en `apps/pas`. `routes/pas.tsx` toma las URLs
nativas `/pas/listar`, `/pas/panel-control[/<pk>]`, `/pas/<pk>`, `/pas/formacion`,
`/pas/mesa-ayuda` y `/pas/liquidacion`; los datos salen de `/api/web/pas/`
(`src/backends/pas/pas/web_api_views.py`, agregado en
`src/backends/pas/pas_runtime/web_api_urls.py`), que corre la vista nativa y
proyecta su contexto. `routes/pasFrame.tsx` reproduce el bloque `app-header`
de PAS con un portal y espera a que `pas.css` aplique antes del scroll
incremental y del salto a `#ddjj-panel`. La entrada sin montar es
`src/backends/pas/pas/web_preview_backoffice.py`, con assets en
`/pas/react/assets/`. «Cambiar estado» (`routes/pasCambioEstado.tsx`) reproduce el
modal de Bootstrap 5.3 y los Select2 de `pas.js` (`routes/pasSelect2.tsx`) y, como la
vista nativa, termina siempre en `/pas/panel-control/<pk>` con el mensaje como
toast. Registros:
`../registro/cambios/2026-T4/2026-11-10-2806-react-pas-backoffice.md` y
`../registro/cambios/2026-T4/2026-11-10-2806-react-pas-cambio-estado.md`.

La consulta de informes PAS (`routes/pasInformes.tsx`) toma `/pas/informes` y
`/pas/informes/<pk>`; los datos salen de `/api/web/pas/informes/`
(`src/backends/pas/pas/web_api_informes.py`), que corre las vistas nativas con
la regla de todos los permisos. La descarga CSV sigue nativa. La solicitud de un informe
(`routes/pasInformesGenerar.tsx`) toma `/pas/informes/generar` y usa
`opciones/`, `previsualizar/` y `generar/` bajo la misma API: reusan el
formulario y los servicios nativos, y `generar/` devuelve el CSV en el mismo
POST. Entrada local: `src/backends/pas/pas/web_preview_informes.py`. Registros:
`../registro/cambios/2026-T4/2026-11-11-2785-react-pas-informes.md` y
`../registro/cambios/2026-T4/2026-11-12-2785-react-pas-informes-generar.md`.

La carga y el seguimiento de lotes OCR (`routes/ocr.tsx`) toman `/ocr/` y
`/ocr/<pk>/`; los datos salen de `/api/web/ocr/`
(`src/backends/ocr/ocr/web_api_views.py`), que reusa el formulario nativo y
`create_ocr_job`; el procesamiento sigue en el worker OCR y la descarga del .txt
sigue en la ruta nativa. Entrada local: `src/backends/ocr/ocr/web_preview.py`.
Registro: `../registro/cambios/2026-T4/2026-11-12-2785-react-ocr.md`.
Organizaciones (O05.01): `/organizaciones/listar` en React lee
`/api/web/comedores/organizaciones/listado/`, que ejecuta `OrganizacionListView`
y el include nativo de filas; el CSV sigue en `/organizaciones/exportar`.
`/organizaciones/detalle/<pk>` monta el fragmento nativo del legajo que sirve
`/api/web/comedores/organizaciones/<pk>/`. Ver
[registro](../registro/cambios/2026-T4/2026-11-11-2785-react-organizaciones-listado.md).
Organizaciones (O01 a O04): las secciones del legajo (convenio, documentación,
firmantes, rendiciones) llegan en `sections` y React las monta en los marcadores
`data-legajo-seccion` del fragmento; el convenio, el historial de documentos,
los firmantes/avales y el detalle de rendición tienen página propia
(`routes/organizacion{Convenio,Documentos,Firmantes,Rendiciones}.tsx`) sobre las
vistas nativas. Ver
[registro](../registro/cambios/2026-T4/2026-11-12-2785-react-organizaciones-secciones.md).
Organizaciones (legajo, avales): la tabla «Avales» del legajo, que es marcado en línea
y no un include, llega como sección `avales` y React la monta en su marcador; los
marcadores usan `display: contents` para no alterar el diseño del contenedor. Ver
[registro](../registro/cambios/2026-T4/2026-11-13-2785-react-organizaciones-legajo-avales.md).
Organizaciones (legajo, avales y datos): la tabla «Avales» del legajo, que es marcado en línea
y no un include, y los bloques de datos (región, proyectos, comedores) llegan como
secciones y React las monta en su marcador; los marcadores usan `display: contents`
para no alterar el diseño del contenedor. Ver
[registro](../registro/cambios/2026-T4/2026-11-13-2785-react-organizaciones-legajo-avales.md) y
[registro de datos](../registro/cambios/2026-T4/2026-11-13-2785-react-organizaciones-legajo-datos.md).

Cruces y novedades PAS (PAS03, `routes/pasCruces.tsx`) toma `/pas/cruces`; la
proyección sale de `/api/web/pas/cruces/`
(`src/backends/pas/pas/web_api_cruces.py`), que corre `PasCrucesView`. Las tres
acciones (`exportar-sintys/`, `importar-sintys/`, `actualizar-renaper/`) usan los
servicios nativos con `pas.change_paspersona`; `exportar-sintys/` devuelve el XLSX
en el mismo POST y tras cada acción React vuelve a pedir la proyección. La web
nunca llama a SINTyS ni a RENAPER. Entrada local:
`src/backends/pas/pas/web_preview_cruces.py`. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-pas-cruces.md`.
Publicar, archivar y destacar comunicados (CM02.03) usan `POST .../comunicados/<pk>/publicar/`,
`.../archivar/` y `.../destacado/`: cada uno ejecuta el `post()` de la vista nativa y devuelve
`{"ok": true, "redirect": "/comunicados/gestion/"}` con el mensaje nativo en cola. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-comunicados-publicacion-estados.md`.

La baja de comunicados (CM02.02, eliminar) usa `GET` y `POST .../comunicados/<pk>/eliminar/`: ejecutan
`ComunicadoDeleteView` con su orden nativo de chequeos (404, luego 403 salvo administrador y borrador) y el
POST devuelve `{"ok": true, "redirect": "/comunicados/gestion/"}`. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-comunicados-eliminacion.md`.

El alta y la edición de comunicados (CM02.02) usan `GET` y `POST .../comunicados/crear/` y
`.../comunicados/<pk>/editar/`, más `GET .../comunicados/destinatarios/<universo>/buscar/` y `.../todos/`: ejecutan
`ComunicadoCreateView`, `ComunicadoUpdateView` y las vistas nativas de destinatarios (POST multipart, 400 con el
formulario ligado, JSON 415) y el panel de destinatarios se reimplementa en React. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-comunicados-formulario.md`.

Los vouchers y las parametrías de VAT (V01.01) y las evaluaciones (V08.01) usan `GET /api/web/vat/vouchers/`,
`.../vouchers/<pk>/`, `.../vouchers/parametrias/`, `.../evaluaciones/` y `.../evaluaciones/<pk>/`
(`src/backends/vat/VAT/web_api_vouchers.py`, `web_api_evaluaciones.py` y la base `web_api_common.py`): cada una
ejecuta la vista nativa y proyecta su contexto, con el permiso de la ruta (`VAT.view_voucher`,
`VAT.view_evaluacion`) detrás de la compuerta G1. La recarga y la cancelación del detalle siguen siendo los POST
nativos con CSRF. Contrato: `../plans/2026-T4/2026-11-12-2785-vat-v01-v08-m2.md`. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-vat-vouchers-evaluaciones.md`.

El alta, la edición y la baja de evaluaciones (V08.02) usan `GET` y `POST .../evaluaciones/nueva/`,
`.../evaluaciones/<pk>/editar/` y `.../evaluaciones/<pk>/eliminar/`
(`src/backends/vat/VAT/web_api_evaluaciones_forms.py`): ejecutan `EvaluacionCreateView`, `EvaluacionUpdateView` y
`EvaluacionDeleteView` (formulario nativo, `form_valid`, mensajes y baja física) y el POST devuelve
`{"ok": true, "redirect": "/vat/evaluaciones/"}` o 400 con los campos y errores del formulario ligado. Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-vat-evaluaciones-formulario.md`.

Los resultados de evaluación (V08.01 y V08.02) usan `GET .../resultados-evaluacion/`, `.../<pk>/`, `.../nuevo/`,
`.../<pk>/editar/` y `.../<pk>/eliminar/` (`src/backends/vat/VAT/web_api_resultados.py`): ejecutan las vistas
nativas `ResultadoEvaluacion*View` (lista con filtros, detalle, formulario con `form_valid`, que fija
`registrado_por`, y baja lógica del `SoftDeleteDeleteViewMixin`). El POST devuelve
`{"ok": true, "redirect": "/vat/resultados-evaluacion/"}` o 400 con el formulario ligado. Rutas React:
`vatResultados.tsx` y `vatResultadosForm.tsx`, sobre `vatFormShared.tsx` (campo, POST y confirmación de baja
compartidos con las evaluaciones). Registro:
`../registro/cambios/2026-T4/2026-11-12-2785-react-vat-resultados-evaluacion.md`.

El reporte de inscriptos y asistencias (V08.01) usa `GET .../vat/reportes/inscripciones-asistencias/`
(`src/backends/vat/VAT/web_api_reportes.py`): ejecuta `ReporteInscriptosAsistenciasView` con su mismo alcance por
usuario (`build_reporte_inscripciones_asistencia`) y proyecta filtros, métricas, resumen por grupo y detalle nominal
paginado. Las cuatro exportaciones (`?export=csv|xlsx|detalle_csv|detalle_xlsx`) siguen siendo descargas nativas: la API
las ignora y la entrada de vista previa las deja pasar a la vista nativa. Ruta React: `vatReporte.tsx` con los
estilos nativos en `vatReporteStyles.ts`; el menú «Tour de ayuda» carga `driver.js` y `vat_tour.js` y no inicia solo.
Registro: `../registro/cambios/2026-T4/2026-11-12-2785-react-vat-reporte-inscripciones.md`.

Los formularios de alta de V01.02 (voucher, alta masiva y parametría) usan `GET` y `POST .../vouchers/asignar/`,
`.../vouchers/asignar-masivo/` y `.../vouchers/parametrias/nueva/` (`src/backends/vat/VAT/web_api_voucher_forms.py`):
ejecutan `VoucherCreateView`, `VoucherAsignacionMasivaView` y `VoucherParametriaCreateView` (formulario, servicio,
mensajes y guardado nativos). El alta devuelve `{"ok": true, "redirect": ...}` o 400 con el formulario ligado; la alta
masiva devuelve 200 con el resultado (asignados, ya tenían, no encontrados, errores) o 400. `campo_formulario` suma el
tag `radio` y el `help_text`. Ruta React: `vatVouchersForm.tsx` sobre `vatFormShared.tsx`. Registro:
`../registro/cambios/2026-T4/2026-11-13-2785-react-vat-formularios-voucher.md`.

El detalle de parametría (V01.01) y sus asignaciones (V01.03) usan `GET .../vouchers/parametrias/<pk>/` y
`POST .../parametrias/<pk>/asignar/` y `.../asignar-masivo/` (`src/backends/vat/VAT/web_api_parametria_detail.py`):
ejecutan `VoucherParametriaDetailView`, `VoucherParametriaAsignarView` y `VoucherParametriaAsignarMasivoView`
(`_asignar_desde_parametria`, servicio y mensajes nativos) y el POST devuelve `{"ok": true, "redirect": <detalle>}`;
el mensaje se muestra al recargar el detalle, como la redirección nativa. Ruta React: `vatParametriaDetalle.tsx`.
Registro: `../registro/cambios/2026-T4/2026-11-13-2785-react-vat-parametria-detalle.md`.

Las intervenciones y observaciones de comedor (CO02, CO06) usan `src/backends/comedores/intervenciones/web_api.py`,
`web_api_formulario.py` y `web_api_baja.py` bajo `/api/web/comedores/intervenciones/` (listado `comedor/<pk>/`, ficha `<pk>/`,
baja de archivo `<pk>/documentacion/eliminar/`, alta `comedor/<pk>/crear/`, edición `<pk>/editar/<pk2>/`, subtipos `subestados/`
y baja `comedor/<comedor_id>/baja/<intervencion_id>/`) y `src/backends/comedores/comedores/web_api_observaciones.py` bajo
`/api/web/comedores/observaciones/` (`comedor/<comedor_pk>/crear/`, `<pk>/`, `<pk>/editar/`, `<pk>/eliminar/`). Ejecutan las
vistas nativas con los permisos de sus URLs (las intervenciones sin alcance por comedor, como el nativo; las observaciones con el
alcance del usuario) y los POST devuelven `{"ok": true, "redirect": ...}` o 400 con el formulario ligado. Rutas React:
`comedorIntervenciones.tsx`, `comedorIntervencionesForm.tsx`, `comedorIntervencionesBaja.tsx` (componente de baja compartido) y
`comedorObservaciones.tsx`. Registros:
`../registro/cambios/2026-T4/2026-11-13-2785-react-comedor-intervenciones-lectura.md`,
`../registro/cambios/2026-T4/2026-11-13-2785-react-comedor-intervenciones-formulario.md`,
`../registro/cambios/2026-T4/2026-11-13-2785-react-comedor-intervenciones-baja.md` y
`../registro/cambios/2026-T4/2026-11-13-2785-react-comedor-observaciones.md`.

La validación, el convenio PNUD/Abordaje y el responsable de tarjeta de comedor (CO07.03, lane K5) usan
`src/backends/comedores/comedores/web_api_validacion.py`, `web_api_convenio.py` y `web_api_tarjeta.py` bajo
`/api/web/comedores/comedores/` (`<pk>/validacion/` entrega la capacidad calculada por `ValidacionService.puede_validar` y las
opciones de «No Validar»; `<pk>/validar/` ejecuta la vista nativa `validar_comedor` y devuelve `{"redirect": ...}`, con el mensaje
nativo en cola para la ficha; `<pk>/convenio-pnud/` ejecuta `ComedorDatosConvenioPnudUpdateView` con su formulario por variante,
los montos Decimal y la preservación de centavos históricos; `<pk>/responsable-tarjeta/` ejecuta
`ResponsableTarjetaComedorUpdateView` con el grupo exacto `Tecnico Comedor` y la cadena Provincia > Municipio > Localidad). El
componente `comedorValidacion.tsx` reproduce los dos modales y lo monta la ficha del comedor (no tiene ruta propia);
`comedorConvenio.tsx` y `comedorTarjeta.tsx` son las pantallas `/comedores/<id>/convenio-pnud/` y
`/comedores/<id>/responsable-tarjeta/editar`, con la vista previa local `web_preview_convenio_tarjeta.py`. Registros:
`../registro/cambios/2026-T4/2026-11-13-2785-react-comedor-validacion.md`,
`../registro/cambios/2026-T4/2026-11-13-2785-react-comedor-convenio.md` y
`../registro/cambios/2026-T4/2026-11-13-2785-react-comedor-tarjeta.md`.

### Comedores sobre G1: ficha del comedor (CO07.01)

`GET /api/web/comedores/comedores/<pk>/` (`web_api_comedor_ficha*.py`) corre `ComedorDetailView` y proyecta
un bloque de `comedor_detail.html` por clave (`header`, `titulo`, `acordeon`, `tablero`, `certificaciones`,
`colaboradores`, `interacciones`, `capacitaciones`, `nomina`, `intervenciones`, `observaciones`). La ruta
`routes/comedorFicha.tsx` (`/comedores/<pk>`, vista previa `DetailEntry`) monta la tarjeta de nómina, las tablas y
modales de intervenciones y observaciones (`comedorFichaRelaciones.tsx`), las tarjetas inferiores
(`comedorFichaBloques.tsx`, `comedorFichaCapacitaciones.tsx`) y la validación (`comedorValidacion.tsx`). Aceptar o
rechazar una capacitación publica a `POST .../<pk>/capacitaciones/<certificado_id>/estado/`.
Un alta rechazada (400) desde los modales de intervención y observación lleva a la pantalla de alta del
comedor con los valores y errores del servidor (`comedorFichaRechazo.ts`: el cuerpo del 400 espera en
`sessionStorage` hasta que la pantalla de alta lo toma con `tomarRechazo`). Registro:
`../registro/cambios/2026-T4/2026-11-13-2785-react-comedor-ficha.md`.
