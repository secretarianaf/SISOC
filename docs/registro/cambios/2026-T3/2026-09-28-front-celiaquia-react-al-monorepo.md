# 2026-09-28 - Front de Celiaquía en React incorporado al monorepo

## Contexto

- La maqueta visual del front v2 de Celiaquía se venía desarrollando en un repo
  aparte (`github.com/nehuen871/celiaquia`), fuera de SISOC-BACK.
- Trabajar el front y el back en repos separados obliga a coordinar dos
  historias para un mismo cambio y deja el front fuera de CI.
- `docs/registro/decisiones/2026-09-24-frontend-v2-react.md` y
  `docs/implementaciones/frontend_v2.md` ya definen que el front v2 vive en el
  monorepo, bajo `frontends/apps/<modulo>/`.

## Cambios aplicados

- Se copió el proyecto completo a `frontends/apps/celiaquia/`, sin su `.git`:
  el historial anterior queda en el repo de origen, que estaba sincronizado con
  `origin/main`.
- Se eliminó el repo local de origen (`~/celiaquiaReact`).
- Se quitaron Tailwind y `postcss.config.mjs`, que ya no se usaban: la maqueta
  es toda MUI, y `frontend_v2.md` prohíbe mezclar Tailwind con MUI en `/v2/`.

Qué trae la app, resumido:

- Tema del DS SISOC con `getTheme('light' | 'dark')`, grupo `nav`,
  `{severidad}.text`, escalas de radio/borde/ícono y las seis variantes
  tipográficas propias.
- Marco de navegación (Header, Sidebar de tres niveles, Footer) y los átomos y
  paneles del sistema.
- Las ocho pantallas equivalentes a los templates de `celiaquia/templates/`:
  listado, alta, detalle de expediente, cupos, detalle de provincia y las dos
  de pagos.

## Impacto esperado

- **El back no cambia.** No se tocó ninguna app Django, ni urls, ni settings.
- La app todavía **no está conectada**: lee de `frontends/apps/celiaquia/app/lib/mock.ts`
  y no hace ningún request. No hay ruteo `/v2/celiaquia/` en Django todavía.
- Nada de lo que hoy funciona en `/celiaquia/` se ve afectado.

## Desvíos respecto de `docs/implementaciones/frontend_v2.md`

Se registran para resolverlos en la épica, no en este movimiento:

- **Next.js 16 en lugar de Vite 7 + React Router 7.** La maqueta se construyó
  sobre Next (App Router). Convertirla a Vite es una tarea propia.
- **Lockfile y Dockerfile propios de la app**, en vez del único lockfile de
  `frontends/` y el `frontends/Dockerfile` con `ARG APP`.
- **Faltan `frontends/packages/ui` y `frontends/packages/api`.** El tema vive
  hoy dentro de la app (`app/theme/theme.ts`) y no en `@sisoc/ui`.
- **El servicio de compose se llama `web`** en el compose propio de la app, no
  `front_celiaquia` en el compose del repo.
- El `theme.ts` original de la skill de UI/UX no estaba en la carpeta entregada:
  el tema se reconstruyó desde `especificacion-theme.md`. Los valores de `nav`,
  `info.main`, radios, bordes y tamaños de ícono son los documentados; el resto
  de las familias de color se derivó siguiendo las reglas de esa spec.

## Validación

- `npx next build` en la ruta nueva: compila y prerenderiza las 7 rutas
  estáticas, sin errores de TypeScript.
- `npx eslint app`: sin errores ni warnings.
- `docker compose up -d --build` desde `frontends/apps/celiaquia/`: las rutas
  `/`, `/expedientes`, `/cupos/1` y `/pagos/expediente/77` responden 200.
- `git status` ve `frontends/` como directorio nuevo; `node_modules/` queda
  fuera por el `.gitignore` de la raíz.

## Riesgos y rollback

- Riesgo principal: que el desvío de stack (Next vs Vite) se consolide por
  inercia y después cueste más alinearlo con el resto de `frontends/`.
- Rollback: borrar `frontends/`. El proyecto sigue publicado en
  `github.com/nehuen871/celiaquia` en el commit `bbd096a`.
