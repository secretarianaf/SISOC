# Merge de `development` en `Celiaquia-react`

Fecha: 2026-10-02

## Contexto

Las dos ramas trabajaron en paralelo sobre el mismo terreno:

- `development` reestructuró el repo a `backends/<producto>/` + `kernel/`, y
  construyó `frontends/` con una app para **VPSL**.
- `Celiaquia-react` construyó la API de Celiaquía y una app de **Celiaquía**
  sobre ese mismo monorepo.

La consigna fue conservar los dos trabajos, no elegir uno. Esto deja constancia
de las decisiones que no se leen del diff.

## Decisiones

### El monorepo hospeda las dos apps

- `frontends/package.json`: unión de los dos sets de scripts; el toolchain de
  test y build (`vite`, `vitest`, testing-library, `jsdom`) queda hoisteado en la
  raíz. `apps/celiaquia` lo declaraba otra vez con versiones distintas, lo que
  instalaba una segunda copia de vite y vitest.
- `apps/celiaquia` se alinea a `axios@1.20.0` (la de `@sisoc/api`) y a
  `react-router-dom@7.18.4` (la de `apps/vpsl`). Dos routers en un mismo bundle
  no comparten contexto.
- `vitest.config.ts` pasa a declarar un proyecto por workspace. Hace falta
  porque cada app declara el entorno distinto y ninguna está mal: vpsl lo pone
  por archivo (`// @vitest-environment jsdom`) y celiaquía en su
  `vite.config.ts`, que además trae `setupFiles`. Bajo una sola config la de
  celiaquía se ignoraba y sus 44 tests caían con `document is not defined`.
- `Dockerfile`: queda la versión de `development`. La mía copiaba el `dist` a la
  raíz de nginx, incompatible con el `base: "/v2/<app>/"` con el que Vite genera
  las rutas de los assets con hash. La de development ya está parametrizada por
  `ARG APP` y sirve a las dos apps.

### Duplicaciones que quedan, a propósito

- `packages/api/openapi.yaml` (VPSL, 14 rutas) y `openapi.celiaquia.yaml`
  (Celiaquía, 70). Son contratos de dos backends distintos; unificarlos obligaría
  a un solo urlconf de schema.
- `packages/ui/src/theme.ts` (VPSL) y `theme.celiaquia.ts`. **Es deuda
  conocida**: son dos sistemas de diseño que deberían converger, pero
  fusionarlos a ciegas cambiaría el aspecto de las dos apps en el mismo commit
  en que se las junta.
- `packages/api/src/index.ts` exporta los dos clientes: el de axios
  (`get`/`postForm`, VPSL) y el tipado contra OpenAPI (`crearCliente`,
  Celiaquía). No hay nombres en común entre `./types` y `./tipos`.

### Routing de `/v2/` y de la API

- Queda el router de `development` (`kernel/core/v2_frontend.py`,
  `FRONTEND_V2_UPSTREAMS`), que es el que corresponde al layout de nginx que se
  conservó, y suma los headers de cache. Se registra ahí el upstream de
  celiaquía.
- `/api/celiaquia/` se mueve de `config/urls.py` a
  `backends/celiaquia/celiaquia_runtime/urls.py`, donde development ya había
  puesto `/api/ticketera/` y `/api/datacalle/`.
- `docker-compose.yml`: queda el healthcheck de development (manda
  `X-Forwarded-Proto` y tolera el arranque largo de CI) y la allowlist `/v2/`.

### Revisión técnica: extracción + funcionalidad nueva

Es el conflicto de fondo. En `Celiaquia-react` extraje `_rechazar`/`_subsanar`
de `RevisarLegajoView` a `RevisionService`, para que la API y la pantalla
ejecuten el mismo flujo. En paralelo, `development` agregó dentro de la vista:

- **issue #2592**: las observaciones que se publican son solo las elegidas en
  esa instancia (`observaciones_ids`), no todo el historial publicable. Antes
  cada subsanación arrastraba los motivos de las anteriores.
- **issue #2523**: documentación complementaria que Nación adjunta a la
  solicitud.

Se conservan las dos cosas: la lógica nueva se porta **al service**, y la vista
vuelve a delegar. En concreto:

- `RevisionService.observaciones_desde_comentarios_tecnicos` pasa a recibir los
  comentarios elegidos en lugar de consultar los publicables. El método
  `ComentariosTecnicosService.observaciones_publicables` que usaba ya no existe:
  development lo reemplazó por la selección explícita.
- `RevisionService.componer_motivo` recibe los comentarios elegidos, no el
  legajo.
- `rechazar` y `subsanar` reciben `comentarios` y se lo pasan a
  `ComentariosTecnicosService.publicar`, que en development dejó de tener valor
  por defecto.
- `subsanar` recibe `documentacion_complementaria` y la valida **antes** de
  tocar el estado del legajo, para que un archivo inválido no deje la
  subsanación a medias.
- `RevisarLegajoSerializer` suma `observaciones_ids` y
  `documentacion_complementaria`, así la API no se queda con la semántica vieja.

## Verificación

- `frontends`: typecheck, lint (0 errores; 2 warnings preexistentes en
  `apps/vpsl/src/App.tsx`), 83/83 tests, build de las dos apps y los dos chequeos
  de contrato, todo en verde.
- Backend: formato (`black`) y chequeos estáticos de nombres sobre los archivos
  tocados. **La suite de pytest no se corrió**: ver abajo.

## Pendiente

- El árbol de trabajo tiene los directorios de apps previos a la
  reestructuración (`admisiones/`, `celiaquia/`, `core/`, …) con solo
  `__pycache__` adentro. Git no los borra al mover los archivos, y Django no
  arranca porque cada app queda con dos ubicaciones en el filesystem. Hay que
  eliminarlos para poder correr `pytest`.
- El schema versionado `openapi.celiaquia.yaml` no se regeneró después de tocar
  `RevisarLegajoSerializer`. Hay que correr el comando de `npm run api:schema` y
  después `npm run api:types`, o CI lo va a marcar.
