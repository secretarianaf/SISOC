# Overview

## 1) Qué es el sistema
- Backoffice Django para SISOC que centraliza módulos de comedores, centro de familia, relevamientos y ciudadanía. Evidencia: README.md:1-4; src/backends/config/settings.py:42-83; src/backends/config/urls.py:12-44.
- API documentada con drf-spectacular (Swagger/Redoc) y front servidor de plantillas; expone `/api/docs` y `/api/redoc`. Evidencia: src/backends/config/settings.py:195-234; src/backends/config/urls.py:35-43.
- Desplegable vía Docker Compose (servicios mysql y django) con setup automatizado de migraciones/fixtures en el entrypoint. Evidencia: docker-compose.yml:1-34; docker/django/entrypoint.py:55-95.
- Variables de entorno parametrizan DB y claves externas (GESTIONAR/RENAPER), más puertos y dominio. Evidencia: .env.example:1-51; src/backends/config/settings.py:153-241.

## 2) Qué NO es / fuera de alcance
- Gestión con usuarios externos a organismos gubernamentales.
- No se declara procesamiento de pagos ni portal público ciudadano.

## 3) Actores y permisos (alto nivel)
- Grupos de usuario predefinidos incluyen Admin, Comedores (listar/crear/ver/editar/eliminar), roles de técnico/comedor/coordinador, algunos data entry, áreas legales/contable, dashboards de datos, roles celiaquía y API CentroFamilia. Evidencia: users/management/commands/create_groups.py:1-61.
- Usuarios de prueba en DEBUG asignan combinaciones de permisos (abogadoqa, tecnicoqa, legalesqa, contableqa, etc.). Evidencia: users/management/commands/create_test_users.py:1-80.
- Otros roles mencionados (técnicos, abogados, representantes provinciales, auditores, datos) sin mapeo directo en código. Evidencia: DESCONOCIDO.

## 4) Casos de uso top 5
- Gestionar comedores (altas, estados, sincronización con GESTIONAR, territoriales). Evidencia: comedores/management/commands/*.py; comedores/tasks.py:1-249; src/backends/config/urls.py:19-20.
- Registrar y sincronizar relevamientos de comedores con GESTIONAR. Evidencia: relevamientos/management/commands/*.py; relevamientos/tasks.py:1-144; src/backends/config/urls.py:31-32.
- Administrar ciudadanos, admisiones, centro de familia y celiaquía (formularios/beneficiarios). Evidencia: src/backends/config/urls.py:21-27,33.
- Operar dashboards y auditoría (dashboard app, audittrail, healthcheck). Evidencia: src/backends/config/settings.py:64-83; src/backends/config/urls.py:18,23,27.
- Gestionar usuarios y grupos internos de acceso. Evidencia: users/management/commands/create_groups.py:1-61; src/backends/config/urls.py:15-16.

## 5) Mapa de apps
| App | Responsabilidad |
| --- | --- |
| users | Autenticación y gestión de usuarios/perfiles. Evidencia: src/backends/config/settings.py:64; src/backends/config/urls.py:15-16. |
| core | Utilidades comunes, fixtures, logging. Evidencia: src/backends/config/settings.py:65; core/management/commands/load_fixtures.py:8-77. |
| dashboard | Tableros internos. Evidencia: src/backends/config/settings.py:66; src/backends/config/urls.py:18. |
| comedores | Gestión de comedores, estados, sincronización GESTIONAR. Evidencia: src/backends/config/settings.py:67; src/backends/config/urls.py:19-20; comedores/tasks.py:1-249. |
| organizaciones | Módulo de organizaciones vinculadas. Evidencia: src/backends/config/settings.py:68; src/backends/config/urls.py:20. |
| centrodeinfancia | Centros de infancia. Evidencia: src/backends/config/settings.py:69; src/backends/config/urls.py:21. |
| ciudadanos | Gestión de ciudadanos/beneficiarios. Evidencia: src/backends/config/settings.py:70; src/backends/config/urls.py:24. |
| duplas | Gestión de duplas técnicas. Evidencia: src/backends/config/settings.py:71; src/backends/config/urls.py:22. |
| admisiones | Procesos de admisión. Evidencia: src/backends/config/settings.py:72; src/backends/config/urls.py:25. |
| intervenciones | Intervenciones sobre casos. Evidencia: src/backends/config/settings.py:73. |
| historial | Historial de cambios. Evidencia: src/backends/config/settings.py:74. |
| acompanamientos | Seguimiento y acompañamientos. Evidencia: src/backends/config/settings.py:75; src/backends/config/urls.py:28. |
| expedientespagos | Expedientes de pagos. Evidencia: src/backends/config/settings.py:76; src/backends/config/urls.py:29. |
| relevamientos | Relevamientos de comedores. Evidencia: src/backends/config/settings.py:77; src/backends/config/urls.py:31-32. |
| rendicioncuentasfinal | Rendición final de cuentas. Evidencia: src/backends/config/settings.py:78; src/backends/config/urls.py:30. |
| rendicioncuentasmensual | Rendición mensual. Evidencia: src/backends/config/settings.py:79; src/backends/config/urls.py:32. |
| centrodefamilia | Gestión de centros de familia y beneficiarios. Evidencia: src/backends/config/settings.py:80; src/backends/config/urls.py:26,35. |
| celiaquia | Módulo celiaquía. Evidencia: src/backends/config/settings.py:81; src/backends/config/urls.py:33. |
| audittrail | Auditoría y purga de logs. Evidencia: src/backends/config/settings.py:82; src/backends/config/urls.py:23. |
| healthcheck | Endpoint de salud. Evidencia: src/backends/config/urls.py:27; healthcheck/urls.py:1-5. |

## 6) Integraciones externas
- MySQL como base de datos principal. Evidencia: src/backends/config/settings.py:153-168; docker-compose.yml:1-19.
- GESTIONAR (API) para sincronizar comedores, referentes, observaciones y relevamientos (con threads y `requests`). Evidencia: comedores/tasks.py:11-249; relevamientos/tasks.py:13-144; src/backends/config/settings.py:236-241.
- RENAPER para consulta de datos de ciudadanos mediante la integración compartida. Evidencia: core/integrations/renaper.py; core/services/renaper.py.
- Google Maps API key opcional. Evidencia: src/backends/config/settings.py:241.

## 7) Riesgos y supuestos
- Dependencia fuerte de variables de entorno (DB, GESTIONAR, RENAPER, DOMINIO); ausencia puede romper arranque. Evidencia: .env.example:1-51; src/backends/config/settings.py:153-241.
- Sin colas dedicadas: sincronizaciones externas usan hilos; riesgo de timeouts/bloqueos en procesos web si no se gestionan errores. Evidencia: comedores/tasks.py:1-249; relevamientos/tasks.py:1-144.
- Entrypoint ejecuta `makemigrations` en arranque de contenedor, con posible modificación de esquema en runtime si hay modelos nuevos. Evidencia: docker/django/entrypoint.py:55-65.
- Cache in-memory (LocMem) no es compartida entre instancias; suposiciones de cache podrían no escalar en múltiples réplicas. Evidencia: src/backends/config/settings.py:175-189.

## TODOs
- Confirmar actores reales y su mapeo a grupos/permissions más allá de los grupos predefinidos.
- Validar y documentar explícitamente qué queda fuera de alcance (portal ciudadano, pagos, etc.).
