# 2026-09-29 - Front v2 de Celiaquia: base del monorepo, conexion y router /v2/

## Contexto

- La maqueta de Celiaquia en React estaba en `frontends/apps/celiaquia/` pero
  era Next.js, leia de un `mock.ts` y no entraba por Django.
- `docs/implementaciones/frontend_v2.md` fija otra cosa: Vite + React Router,
  paquetes compartidos, sesion de Django y ruteo por `/v2/<modulo>/`.
- El objetivo es que el front nuevo haga lo mismo que las pantallas Django.

## Cambios aplicados

### Base de `frontends/`

Se creo lo que la guia describia y no existia:

- `frontends/package.json` con npm workspaces, `.nvmrc` (22.14.0), `.npmrc`
  (`save-exact=true`), `tsconfig.base.json`, `eslint.config.js`.
- `frontends/Dockerfile` con `ARG APP` y targets `dev` (Vite con HMR) y `prod`
  (estatico servido por `nginx-unprivileged`).
- `packages/ui` (`@sisoc/ui`): `buildTheme(mode)`, `ThemeProvider` con la
  preferencia en `localStorage` dentro de try/catch, el AppShell de `/v2/`
  (AppBar + Drawer de tres niveles + Footer) y los componentes del DS.
- `packages/api` (`@sisoc/api`): cliente axios con `withCredentials`, header
  `X-CSRFToken` leido de la cookie en todo metodo no seguro, 401 → login con
  `next`, 403 → error tipado `SinPermiso` (no redirige, para no hacer loop), y
  las funciones por endpoint de Celiaquia.

### La app: de Next.js a Vite

- `apps/celiaquia` es ahora Vite 7 + React Router 7 + TanStack Query, con
  `base: "/v2/celiaquia/"`.
- Las ocho pantallas quedaron conectadas a `api/celiaquia/`: listado con filtros
  y paginacion server-side, alta con previsualizacion real del Excel, detalle con
  legajos y revision tecnica, historial, cupos, movimientos y pagos.
- Estados de carga, error y "sin permiso" en cada pantalla. **No queda ningun
  dato de maqueta**: el `mock.ts` se conservo solo como referencia en
  `apps/celiaquia/docs/mock-inicial.ts.txt`.

### Router `/v2/` en Django

`core/frontend_v2.py` (nuevo) mas `FRONTEND_V2_SERVICIOS` en settings y las dos
rutas en `config/urls.py`. Django recibe `/v2/<modulo>/...` y lo reenvia:

- **Allowlist por configuracion**, nunca desde el request. Un modulo que no este
  en `settings` da 404. Esto es lo que evita que la URL se convierta en un SSRF.
- Solo `GET`/`HEAD`; no reenvia `Cookie` ni `Authorization`.
- `login_required`, con el mismo stack de middleware que el resto del sitio.
- Timeout corto: si el front no responde, esa ruta da 503 y el resto del sitio
  sigue andando.
- Assets con hash (`assets/*`) con `max-age` de un año; `index.html` con
  `no-cache`.
- Un 404 del servidor en una ruta que no es asset devuelve el `index.html`,
  porque el router del cliente maneja sus propias rutas.

Y el servicio `front_celiaquia` en el `docker-compose.yml` de desarrollo, con
puerto interno: solo lo alcanza Django por la red de compose.

## Un hallazgo contra la guia: vitest 4.1.11 no es instalable

`frontend_v2.md` fijaba `vitest@4.1.11`. **No se puede instalar** con el npm que
trae Node 22.14.0 (npm 10.9.2), que es el runtime que la misma guia manda:

```
npm error Cannot read properties of null (reading 'edgesOut')
```

Es un bug de arborist resolviendo el grafo de peers de vitest 4.1.x. Falla igual
con npm 11.5.1 sobre Node 24, asi que no es del runtime. Probado en contenedor:
`4.1.11` falla, `4.0.6` y `3.2.4` instalan bien.

Se dejo en **4.0.6** y se corrigio la tabla de la guia. Esto valida, de paso, el
pendiente que la guia tenia anotado ("falta repetir la corrida sobre Node
22.14.0 dentro del contenedor").

## Decisiones

- **El 403 no redirige al login.** Con sesion activa, un 403 es falta de
  permiso, no de sesion: redirigir haria un loop. Se muestra como aviso.
- **Los tipos de `@sisoc/api` estan escritos a mano**, siguiendo los serializers.
  La guia manda generarlos con `openapi-typescript`; queda pendiente junto con el
  chequeo de contrato en CI.
- **El Drawer muestra el arbol fijo del modulo**, no los permisos del usuario,
  porque `/api/users/me/` todavia no acepta sesion. Es un pendiente ya abierto en
  la guia, no algo nuevo.
- El filtro de pagos por provincia se hace en la pantalla: el endpoint de pagos
  todavia no expone ese filtro.

## Impacto esperado

- **Las pantallas viejas no cambian.** `/celiaquia/...` sigue igual; el menu
  viejo no enlaza a `/v2/`.
- `/v2/celiaquia/` solo funciona con `FRONTEND_V2_SERVICIOS` configurado. Sin esa
  variable, la ruta da 404 y nada mas cambia.

## Validación

- `pytest celiaquia/tests tests/test_frontend_v2_router.py`: **366 passed**
  (356 del modulo + 10 del router nuevo).
- Front: `tsc --noEmit` sin errores, `vite build` OK, `eslint` sin errores,
  `vitest run` 6 tests en verde.
- `docker build --target prod` con Node 22.14.0: la imagen se construye, o sea
  que `npm ci` del workspace completo funciona en el runtime que manda la guia.
- **De punta a punta, con el contenedor levantado**: `/v2/celiaquia/` sin sesion
  redirige a `/login/?next=/v2/celiaquia/`; con sesion devuelve el `index.html`
  con `Cache-Control: no-cache`; `/v2/celiaquia/expedientes` cae en el index; y
  `/v2/inexistente/` da 404.

## Lo que falta para la paridad completa

Del lado del back, endpoints que siguen solo en las pantallas Django porque su
logica todavia vive dentro de las views (detallado en
`2026-09-29-api-celiaquia-escrituras.md`): editar y reprocesar registros
erroneos, validacion RENAPER, respuesta a subsanacion con archivos, comentarios
tecnicos, correccion de evaluacion final, plantilla de Excel y lookup de
localidades.

Del lado del front, lo que depende de esos endpoints: los registros erroneos se
muestran pero **no se editan**, y no estan las pantallas de RENAPER ni de
respuesta a subsanacion.

Ademas: `openapi.yaml` + tipos generados + chequeo de contrato en CI, y sumar
`front_celiaquia` al compose de deploy y al workflow.

## Riesgos y rollback

- Riesgo principal: el router `/v2/` es una superficie nueva que hace requests
  salientes desde Django. Se acota con la allowlist, el timeout y los tests que
  cubren esos casos.
- Riesgo operativo: en deploy, Django con Gunicorn sincrono sirve tambien los
  assets de `/v2/`. Ya estaba aceptado en el ADR, con la condicion de revisarlo
  si se satura.
- Rollback: sacar las dos rutas de `config/urls.py`. Sin ellas, `frontends/` es
  codigo que no se ejecuta.
