# 2026-10-26 - Admin con Django Unfold como autoservicio de desarrollo y soporte (#2789)

## Estado

- aceptada. El alcance y las decisiones las aprobó el responsable del issue el
  2026-10-26, antes de implementar. Implementado y validado localmente; sin
  incorporación ni deploy.

## Contexto

- Soporte pedía queries a mano para cambiar estados o corregir datos, porque el
  admin no alcanzaba: pocos filtros y búsquedas, FKs como selects gigantes, sin
  acciones de transición y un menú plano por app técnica.
- El admin no se migra al front React (los fronts sí): tiene que quedar
  autocontenido en Django.
- Cada backend por vertical corre su propio proceso y registra solo sus apps; el
  core reenvía `/admin/<app>/` al runtime dueño (`config/backends.json`).

## Decision

- **Unfold pineado en `django-unfold==0.91.0`**, la última versión compatible con
  el Python 3.11 de la imagen (desde 0.92 exige Python 3.12). Licencia MIT. Se
  instala en `SHARED_APPS`, así lo heredan el core, `settings_all` y cada
  `*_runtime`.
- **Solo superusuarios.** `core.admin_site.SisocAdminSite` (Unfold) se instala como
  sitio por defecto con `core.admin_apps.SisocAdminConfig`. Exige usuario activo,
  staff y superusuario: la regla es más estricta que la anterior (solo staff),
  nunca más amplia. Vale igual para `admin/doc/` y los accesos a otros backends.
- **Operaciones vía services.** `core.admin_operaciones.Operacion` envuelve un
  service existente y se publica como acción por fila, en el detalle y en lote
  (máximo 100 registros), con confirmación, motivo y un `auditlog.LogEntry`
  explícito (operación, motivo, estado antes/después). El origen y el lote
  (`audittrail_source` y `audittrail_batch_key` en `additional_data`) los toma el
  signal de `audittrail`, así `core` no importa `audittrail` (contrato
  `core-no-domains` de `.importlinter`). El campo de estado queda de solo lectura.
  Si no hay service, la operación no se implementa: se lista como pendiente.
- **Auditoría explícita.** Se registra un `LogEntry` por operación con
  `force_log` en vez de sumar modelos a `audittrail/constants.py`, para no
  cambiar el volumen de auditoría del resto del sistema.
- **Dashboard por runtime.** `core.admin_dashboard` descubre los módulos
  `<app>/admin_metricas.py` entre las apps instaladas. `/admin/` muestra las del
  proceso y cada `/admin/<app>/` las suyas, que calcula su propio runtime. No se
  agrega un contrato JSON entre servicios. Las consultas son agregadas y se
  cachean por app (`DASHBOARD_CACHE_TIMEOUT`).
- **CSP.** El middleware suma `'unsafe-eval'` a `script-src` solo para rutas
  `/admin/`, porque Alpine.js de Unfold evalúa expresiones con `AsyncFunction`.
  El resto del sitio conserva la política global.
- Los campos de estado **sin service** siguen editables como hoy, para no quitarle
  a soporte lo que ya puede hacer. Se listan como pendientes en el PR.
- **Sin autocomplete en los admins de los verticales.** En deploy
  `/admin/autocomplete/` lo sirve el core, que no instala esos modelos y responde
  403. Se usan `raw_id_fields`: su popup abre el admin del dueño, que sí está
  ruteado. Los filtros por relación pasan a texto (`FieldTextFilter`). Lo
  controla un test en `test_admin_unfold.py`. El autocomplete queda en los
  admins del kernel y del núcleo. Propuesta del agente: si se necesita
  autocomplete en los verticales, se puede rutear el autocomplete por
  `app_label` en `core.backend_proxy` (en otro issue).
- El admin de Datacalle se rutea a su backend (`admin/datacalle/` en
  `config/backends.json`), igual que el de Dispositivos.

## Consecuencias

- Soporte puede buscar por identificador de negocio, filtrar por estado y fecha,
  operar transiciones respaldadas por services y ver la auditoría de cada
  registro sin SQL.
- Hay una dependencia de producción nueva, atada a la línea 0.91 hasta subir la
  imagen a Python 3.12. Para subirla hay que revisar los templates sobreescritos
  en `src/backends/kernel/templates/admin/` y los forms de
  `unfold.contrib.import_export`.
- El staff que no es superusuario pierde el acceso al admin. Antes de
  incorporar hay que revisar en PRD quién tiene `is_staff` sin `is_superuser`.
- En `/admin/` el riesgo de XSS es un poco mayor por `'unsafe-eval'`. Se acota
  porque solo entran superusuarios y los templates de Unfold no usan scripts
  inline.
- No hay una página global con las métricas de todos los runtimes. Si hiciera
  falta, se puede revisitar con `core.backend_proxy.pedir_json_a_backend`.
- Revisitar si el admin se abre a usuarios funcionales (fuera de alcance), si
  Unfold deja de soportar Django 5.2 o si soporte necesita operaciones que hoy
  no tienen service.

## Referencias

- Issue #2789.
- Código: `src/backends/kernel/core/admin_site.py`, `admin_apps.py`,
  `admin_base.py`, `admin_operaciones.py`, `admin_navigation.py`,
  `admin_dashboard.py`; `src/backends/config/middlewares/csp.py`; bloque `UNFOLD`
  en `src/backends/config/settings.py`.
- Tests: `src/backends/kernel/tests/test_admin_unfold.py`,
  `src/backends/kernel/tests/test_admin_operaciones.py`,
  `src/backends/kernel/tests/test_admin_dashboard.py`.
- Import/export previo: `docs/registro/cambios/2026-T3/2026-07-27-import-export-admin.md`.
