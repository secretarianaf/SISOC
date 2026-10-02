# Celiaquía — front v2

App React del módulo de Celiaquía. Se sirve bajo `/v2/celiaquia/`: Django recibe
esa ruta y la reenvía a este servicio (`core/frontend_v2.py`).

Las reglas del front v2 están en `docs/implementaciones/frontend_v2.md`, en la
raíz del repo. Esta app las sigue; lo que hace falta saber para trabajar acá:

## Correr

Desde `frontends/`:

```bash
npm ci
npm run dev:celiaquia     # Vite en :5173
```

Para verla como la ve el usuario hay que entrar por Django, con el servicio
levantado y la variable configurada:

```bash
FRONTEND_V2_SERVICIOS=celiaquia=http://front_celiaquia:8080/ docker compose up -d django front_celiaquia
```

Y abrir `http://localhost:8000/v2/celiaquia/`. Sin sesión redirige al login.

## Estructura

- `src/api.ts` — la instancia del cliente. La API vive en `/api/celiaquia/`.
- `src/pages/` — una por pantalla, conectada con TanStack Query.
- `src/componentes/` — lo que es de esta app y no del sistema de diseño.
- `src/navegacion.ts` — el árbol del Drawer.
- El tema y los componentes del DS vienen de `@sisoc/ui`; el cliente HTTP y los
  tipos, de `@sisoc/api`. No se redefinen colores acá.

## Dos cosas que conviene saber

**La sesión es de Django.** No hay tokens: `@sisoc/api` manda las cookies y el
`X-CSRFToken` en cada escritura. Un 401 redirige al login; un 403 se muestra
como "sin permiso" y no redirige, para no entrar en un loop.

**No toda la funcionalidad del módulo está acá todavía.** Los registros erróneos
se ven pero no se editan, y faltan las pantallas de validación RENAPER y de
respuesta a subsanación: sus endpoints aún no existen porque esa lógica sigue
dentro de las views de Django. El detalle está en
`docs/registro/cambios/2026-09-29-front-celiaquia-conectado.md`.
