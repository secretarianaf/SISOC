# Ver para ser libre en Front v2

La norma vigente es [`frontend_v2.md`](../implementaciones/frontend_v2.md). Las pantallas Django de VPSL siguen en sus rutas originales y en el menú de SISOC. El React nuevo se abre directamente en `/v2/vpsl/`; el menú viejo no lo enlaza hasta que se decida el cambio de navegación.

## Flujo

1. El navegador pide `/v2/vpsl/` a SISOC. Django exige sesión y reenvía el HTML y los assets a `front_vpsl:8080` por la red de Compose. El servicio de front no recibe cookies ni cabeceras de autorización.
2. React consulta `/api/vpsl/session/` en el mismo origen y arma la navegación con los permisos del usuario. Las demás lecturas y escrituras usan `/api/vpsl/`, con la sesión de Django y CSRF en las escrituras.
3. La API DRF corre en el Django principal. Valida permisos y alcance provincial, usa los modelos de VPSL y reutiliza las reglas existentes. Los formularios y acciones todavía pasan por `api_workflow.py`, que adapta vistas y ModelForms previos.
4. Django sigue aplicando migraciones y sirviendo el resto de SISOC. El contenedor `front_vpsl` solo sirve archivos estáticos y puede reiniciarse de forma independiente.

## Arranque local

Configurar `.env` como para SISOC y ejecutar `docker compose up --build`. Abrir `http://localhost:8001/v2/vpsl/` con un usuario que tenga permisos VPSL. Para hot reload, usar `docker compose -f docker-compose.yml -f docker-compose.frontends.dev.yml up --build front_vpsl` y entrar por la misma URL; Vite usa el puerto 5173 para HMR. El override apunta el router Django a `front_vpsl:5173`; `FRONTEND_V2_HMR_ORIGINS` habilita solo en DEBUG el websocket directo `ws://localhost:5173`. Si el host no es localhost, configurar el origen público apropiado. El preámbulo de React Refresh se sirve como archivo externo para respetar `script-src` estricto.

La build de producción usa `frontends/Dockerfile` con Node 22.14.0 y `nginx-unprivileged`. Las dependencias se fijan en un único `frontends/package-lock.json`. La API acepta JSON para datos y multipart para archivos; preserva sesión y CSRF. Los listados de registros y laboratorio se consultan por `/api/vpsl/jornadas/<id>/registros/` y `/api/vpsl/jornadas/<id>/laboratorio/`, con `page` y `page_size` hasta 200. El esquema API se genera con `FRONTEND_V2_SCHEMA_ONLY=1 python manage.py spectacular --file frontends/packages/api/openapi.yaml --format openapi`; desde `frontends/`, `npm run types:generate` actualiza los tipos TypeScript.

El tema ejecutable vive en `frontends/packages/ui/src/theme.ts` y lo comparte `@sisoc/ui`; la preferencia claro/oscuro sigue en `app.theme`.

La guía general de `development` se mantiene sin cambios en este PR. Su sección de estado todavía describe `frontends/` como pendiente y propone Celiaquía como primera app; esta entrega implementa VPSL primero. La guía también conserva la matriz inicial de versiones y el nombre `buildTheme(mode)`; la implementación usa las versiones exactas de `frontends/package-lock.json` y exporta `getTheme(mode)`. Los parches de seguridad se registran en `docs/registro/cambios/2026-09-29-vpsl-react-dependencias-seguras.md`. Estos datos de la guía general deberán actualizarse por separado antes de usarla para evaluar futuras migraciones.

## Funciones del MVP

React cubre itinerarios, evaluación y subsanación, jornadas con ubicación y vehículos, checklist, registros nominales con graduación, laboratorio, cierre, sedes históricas y exportación. Incluye los cambios de VPSL posteriores del PR #2566. El backend conserva permisos por acción, alcance provincial y validación de formularios.

El backend reutiliza las reglas oficiales del PR #2566. La API transmite la excepción de graduación de registros históricos, conserva la localidad heredada de la sede y permite editar jornadas previas sin exigir retroactivamente ubicación. La previsualización de Maps actualiza la dirección automática y conserva una dirección editada manualmente.

## Validación y límites

- La equivalencia exacta de medidas y jerarquía con las pantallas VPSL del Figma *Nuevo DS SISOC* requiere acceso a esa fuente. Los controles remanentes usan el tema compartido y el contraste de bordes y texto se verifica por pruebas.
- La API, modelos, base, sesión y migraciones viven en SISOC. Las escrituras React reutilizan las vistas Django y sus ModelForms oficiales a través del adaptador `api_workflow.py`; la lectura y el alcance provincial comparten `services/access.py`. Para extraer el backend como dominio autónomo, trasladar antes la orquestación de escrituras a servicios comunes.
- Las lecturas de jornada separan checklist/cierre de registros y laboratorio paginados. OpenAPI tipa salidas y variantes de entrada de formularios; los campos obligatorios específicos del registro existente se entregan además en el esquema GET del formulario y se validan definitivamente en ModelForms.
- Maps, RENAPER y el almacenamiento de archivos requieren pruebas en homologación con las integraciones reales. El flujo de migración y despliegue debe verificarse con datos representativos antes de activar la URL para usuarios. La comparación exacta con Figma y la aceptación de cada rol requieren revisión humana. La corrida local de cierre registró 165 pruebas Python, 14 Vitest, 3 Playwright sobre Vite preview y Nginx, cero vulnerabilidades npm y build de imagen `prod` con smoke HTTP; ver `docs/registro/cambios/2026-09-29-vpsl-react-cierre-revision.md`.

El despliegue actual construye `front_vpsl` antes de detener el stack, etiqueta su imagen con el SHA y falla si no compila. No requiere cambios en el NGINX del host.
