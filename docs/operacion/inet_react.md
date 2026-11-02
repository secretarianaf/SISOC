# INET React v2

## Acceso y arquitectura

Acceso por URL `/v2/inet/` con la sesión SISOC existente. El menú legacy sigue
apuntando a VAT. La app vive en `src/frontends/apps/inet`; reutiliza `@sisoc/ui`
y `@sisoc/api`, siguiendo el patrón de VPSL. No hay nuevas tablas ni migraciones.

El diseño usa el tema compartido SISOC: colores y estilos comunes,
Roboto local, temas claro/oscuro (`app.theme`), header de 82 px, navegación de
230 px y footer institucional. Las pantallas de INET se componen
con buscadores, legajos, pestañas, formularios y confirmaciones React.

## Funciones

- CFP: búsqueda por nombre/CUE, estado y territorio; alta, edición y eliminación
  con preview de cascada; información, ubicaciones y contactos.
- Oferta: cursos del CFP, plan curricular de su provincia y modalidad; alta,
  edición, eliminación y creación de comisión desde cada curso.
- Comisiones: creación con horarios y validación semanal del wizard existente;
  fechas, ubicación, cupo, edición de horarios conservando clases realizadas.
- Inscripciones: búsqueda exacta de documento en SISOC; alta rápida; protocolo
  del kernel para personas sin DNI; cupos, cambios de estado y baja con historial.
- Asistencia: nómina activa completa, presentes/ausentes y observaciones por clase.
- Planes curriculares: listado, detalle, alta, edición y eliminación; catálogos
  del formulario existente, normativa y alcance provincial.

Los datos manuales no se presentan como identidad validada por RENAPER. La
resolución de identidad y la edición global del ciudadano continúan en el kernel.
No se agrega una dependencia de red para inscribir o tomar asistencia.

## API interna

`/api/inet/` usa SessionAuthentication + CSRF y permisos IAM de VAT. La API externa
`/api/vat/` conserva HasAPIKey. Los catálogos de territorio, referentes, planes,
sectores y modalidades se consultan desde opciones del formulario, paginadas,
con el mismo alcance que el recurso. No se expone una búsqueda global de padrón.

Recursos: `centros`, `cursos`, `comisiones`, `horarios`, `contactos`, `ubicaciones`,
`planes`, `inscripciones` y `sesiones`. Cada recurso soporta lectura paginada y
detalle. Los siete recursos editables tienen `form/`, `<id>/form/`, `options/<campo>/`,
`<id>/options/<campo>/` y `<id>/delete-preview/`. Se agregan `session/`,
`horario-form/`, `ciudadano-form/`, `comisiones/<id>/ciudadanos/`,
`comisiones/<id>/inscribir/`, `inscripciones/<id>/estado/` y
`sesiones/<id>/asistencia/`.

Las escrituras pasan por ModelForms y services compartidos con legacy. El
backend delimita CFP y provincia, bloquea padres ajenos y guarda operaciones
compuestas en transacciones. La baja usa soft delete; las inscripciones cambian
de estado. No se borra un horario con clases realizadas/canceladas.

Contrato: `src/frontends/packages/api/openapi.inet.yaml`, generado con `config.urls_inet_v2`.
Tipos: `src/frontends/packages/api/src/inet.generated.ts`; `npm run inet:types` los regenera.
CI verifica schema y tipos junto con los contratos existentes.

## Configuración de builds y rutas

El servicio `front_inet` construye desde la raíz usando
`docker/frontends/Dockerfile`, igual que VPSL. En desarrollo, el directorio de
trabajo es `/app/src/frontends` y el verificador compartido se monta desde
`src/scripts/frontends/`. La app extiende
`src/frontends/config/tsconfig.base.json`.

Al cambiar URLs, regenerar `src/backends/config/url_registry.json` mediante
`docker compose exec django python manage.py generar_registro_urls`; no alcanza
con editar el prefijo en `src/backends/config/backends.json`.

Los controles conservan contraste AA. Los contratos de INET y Celiaquía se verifican con
`src/scripts/frontends/verificar-contrato.mjs`.

## Arranque

Desde la raíz:

```powershell
docker compose up --build -d front_inet
```

Abrir el puerto Django local configurado, por ejemplo
`http://localhost:8001/v2/inet/`. `FRONT_INET_ORIGIN` usa por defecto
`http://front_inet:8080` y el router Django aplica sesión y CSP.

Desarrollo con HMR:

```powershell
docker compose -f docker-compose.yml -f docker/compose/docker-compose.frontends.dev.yml up --build -d front_inet django
```

El override usa `FRONT_INET_ORIGIN=http://front_inet:5173`, HMR en localhost:5175
y el volumen Linux compartido de dependencias. El servicio opcional
`frontend_tools` permite ejecutar npm sin instalar dependencias en Windows.

## Validación

```powershell
docker compose exec django pytest src/backends/vat/tests/test_inet_api.py -q
docker compose exec django python manage.py check
docker compose exec django python manage.py spectacular --urlconf config.urls_inet_v2 --file src/frontends/packages/api/openapi.inet.yaml --validate --fail-on-warn
```

En `src/frontends`: `npm run lint`, `npm run typecheck`, `npm run test`,
`npm run api:check`, `npm run build`, `npm run test:e2e`.
`src/frontends/e2e/inet.e2e.ts` usa fixtures aisladas y comprueba CSP, CSRF, navegación,
validación y temas. Capturas de claro, oscuro y móvil quedan en `test-results/`.
Deploy usa imagen `sisoc/front-inet:<SHA>` y verifica nginx en QA/HML/PRD.

Pantallas y reglas vigentes: `docs/implementaciones/inet_react.md`.
Resumen de cambios y verificación:
`docs/registro/cambios/2026-T4/2026-10-26-inet-react.md`.
