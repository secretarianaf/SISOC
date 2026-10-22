# #2641 C2: consumidores y recursos de Comedores

Estado: **C2 implementado y validado localmente**. Las decisiones
pendientes del importador y Montos fueron aprobadas por el responsable. C3 requiere
su propia señal de inicio. Rama `juanikitro/Migracion`, base
`1cede84d2b3490f2ddb6bf933852408d9fd68bc7`. Se preservan los 95 cambios C0+C1
sin commit; el manifiesto del handoff coincidió en las 95 entradas al iniciar.
No hay commit, push, merge, cierre de issue, deploy ni acciones sobre entornos.

## Implementación y aceptación demostrada

- Ciudadano 360 consume cuatro fragmentos HTML: `comedores`,
  `comedores_colaboraciones`, `pwa` y `pwa_badges`. Consulta y templates están
  en `comedores/ciudadano_detail.py`, `pwa/ciudadano_detail.py` y sus carpetas
  `templates/`. El template kernel conserva el layout y las inserciones HTML;
  no recibe objetos ORM de esos dominios. Se conserva el escape de datos.
- `ciudadanos.detail_contributions.APPS_CONTRIBUCIONES` declara dueño por app,
  usando `backend_de_app` y el transporte existente. Las apps registran sus
  templates en `ready()` como antes. La composición local tiene el mismo
  endpoint de fragmentos que los runtimes backend, sin nombre público nuevo.
  Lectura exige sesión y `ciudadanos.view_ciudadano` también en el dueño.
  Timeout/403/503 omiten sólo el fragmento: no convierten datos ausentes en
  indicadores negativos ni exponen el cuerpo de error al usuario.
- `core.backend_proxy.APPS_SECCIONES_FAVORITAS` declara Comedores, ambos
  listados de Admisiones, Acompañamientos, Duplas y Rendiciones. La configuración
  local conserva prioridad; cuando no está instalada se reenvía con el proxy
  existente. No hay una sección independiente de favoritos PWA en el código
  actual. Se conservan validación, propietario, CSRF y sesión. Caída del dueño
  devuelve 503 y no elimina favoritos. El frontend existente envía JSON.
- El visor `audittrail.views.AuditLogResolveMixin.resolve_entry_changes` usa
  `changes_dict` persistido cuando el ContentType no tiene modelo instalado.
  La versión instalada de auditlog accede a `model._meta` sin comprobar None;
  su AttributeError quedaba absorbido por `getattr` y borraba visualmente el
  diff. Se reprodujo con objetos reales, sin modificar datos ni librerías.

No se registra todavía un backend Comedores en `backends.json`. El registro,
runtime, imágenes, Compose, rutas de proxy y selector reales corresponden a C3.
Los probes HTTP inyectan el destino y retiran únicamente los registros locales
del consumidor; ambos procesos todavía tienen el checkout completo.

## Recursos, pantallas y admin

Se conservan junto al dueño, sin mover binarios ni cambiar nombres de tareas:

| Recurso | Resolución existente y verificación |
| --- | --- |
| Prestaciones y planillas | `pwa/files/`; certificación usa `apps.get_app_config("pwa").path`; cuatro variantes PDF renderizadas con LibreOffice y BASE_DIR ajeno |
| Nómina de destinatarios | `pwa/files/varios/NOMINA.DE.DESTINATARIOS.docx`, por `__file__` en su servicio; existencia comprobada, no se ejecutó su flujo PDF completo |
| DOCX de informes | `admisiones/templates/admisiones/docx/`, por app en DocumentTemplateService; no se repitió el circuito completo de informes |
| Manifiesto de #2272 | `admisiones/data/issue_2272_expedientes.csv`, por `__file__`; 470 correcciones válidas, sin ejecutar la corrección contra una DB |
| Formularios PNUD | `relevamientos/data/pnud_formularios.json`, por `__file__`; carga real comprobada |
| Estáticos y fixtures | Permanecen en las apps; no se ejecutó collectstatic ni load_fixtures como operación en un entorno |

Se inspeccionaron las cinco páginas PNG de las cuatro variantes PDF. Son
legibles; `PRESTACIONES.54.docx` genera además una página final vacía. Es una
limitación de la plantilla existente: el binario y el servicio no tienen diff.
No se corrige el diseño documental dentro de este corte de boundaries.

El admin actual registra modelos reales de Comedores y PWA. C3 debe montar su
admin en el dueño y preservar las URLs con sesión, permisos y CSRF; un stub de
reverse no hace disponible el ModelAdmin. La auditoría de sesión sigue en kernel
según C1. No se eliminan ContentTypes ni se ejecuta remove_stale_contenttypes.

## Decisiones C2 aprobadas e implementación

El responsable respondió «1. apruebo» al adaptador local y «2. comedores» a la
propiedad de las pantallas de Montos. Contexto, recomendación técnica aceptada,
alternativas y consecuencias en
`docs/registro/decisiones/2026-10-15-c2-importador-y-montos-comedores.md`.

- `users.pwa_import_access` contiene los DTOs/registro compartidos y el adaptador
  local. `usuarios.pwa_import_access` conserva exports de compatibilidad.
  `comedores.pwa_user_import` no importa Usuarios: registra expansión de espacios,
  precedencia de asociación por organización, permisos y sincronización existentes.
- `usuarios.services_user_import` no importa PWA/Comedores. Conserva validaciones
  transversales, Inspecciones, identidad, credenciales y la operación completa de
  fila. `services_user_import_jobs`, su lease, cola, checkpoint y comando conservan
  nombre y semántica; no se trasladó el importador entero por su nombre.
- Si falta el adaptador se permiten filas independientes, incluidas altas de
  Inspecciones. Se bloquean columnas de espacios, permisos/grupos dependientes
  y reemplazos que afectarían permisos o grupos de dominio antes de escribir.
  El clasificador C1 se reutiliza para evitar autorizar un efecto ambiguo.
  Usuario, accesos y checkpoint siguen dentro del atomic local del worker.
- Las cinco vistas de Montos y sus rutas están en
  `comedores/views/montos_prestacion.py` y `comedores/montos_urls.py`.
  Los cuatro templates y sus pruebas se trasladaron al dueño. `core.urls`/`views`
  ya no operan Montos ni importan Historial. URLs, nombres, permisos, formulario,
  modelo y tabla compartidos se conservan. No hay migraciones C2.
  El ModelAdmin se registra desde `comedores.admin`, conservando la URL
  `/admin/core/montoprestacionprograma/` y los permisos `core.*`.
- C3 debe resolver el proceso/imagen del worker con el adaptador instalado y
  registrar `/montoprestacion/` y `/admin/core/montoprestacionprograma/` junto al
  resto de Comedores. No se incorpora
  una nueva topología, worker, runtime o backend en este corte.

## Evidencia y límites

MySQL 8.4 sintético, red interna y sin puertos, sin .env ni datos existentes.
Fuentes montadas RO; EMAIL locmem, integraciones desactivadas. Scratch y logs:
`C:/Users/Juanito/AppData/Local/Temp/sisoc2641-c0-1nh_v_m2/`.

- `c2-final-tests.log`: **280 passed**, ocho warnings de deprecaciones existentes,
  120.70 s, MySQL 8.4. Comando reproducible en `c2-final-tests-command.json`.
  Incluye fragmentos y favoritos locales/remotos, sesión/CSRF/propiedad, HTTP
  entre procesos y caída, escape HTML, cuatro PDFs reales, admin del dueño,
  Montos con Historial, permisos, importador y rollback conjunto de usuario,
  accesos y checkpoint. También cubre identidad C1/HTTP, credenciales,
  Inspecciones, reanudación/cesión de lote, sidebar y exportación admin.
- `c2-completion-tests3.log`: 33/33 del bloque nuevo. La suite final incluye
  estos casos: no sumar corridas como si fueran tests únicos. El guard de
  importación también revalida efectos de grupo antes de escribir.
- `c2-final-cluster-probe.log`: probe de arranque ampliado a las catorce apps
  del cluster completo de Comedores, incluidos callers del importador y
  ausencia del ModelAdmin de Montos en kernel. No prueba imágenes C3.
- `c2-final-imports.log`: **26 contratos**, sin excepciones nuevas;
  `c2-final-imports-celiaquia.log`: contrato adicional conservado.
- `c2-final-black.log`: treinta Python C2; `c2-final-pylint.log`: dieciocho de
  runtime, 10/10. `c2-completion-django.log`: system check sin issues.
  `c2-final-migration-drift.log`: No changes detected.
- `c2-final-docs.log`: siguen sólo las dos referencias obsoletas
  preexistentes documentadas en C1 (test SIMEPI y script de deploy de fronts);
  no está aprobado ese control. La guía TESTING usa la ruta nueva de Montos.
  El selector devuelve completo + MIGRAR=1 por incluir kernel; no se ejecutó.
- Corridas anteriores: la primera parte pasó 99/99 y 129/129; hubo expectativas
  de prueba corregidas y dos tests de worker ajustados a transaction=True por
  close_old_connections en MySQL, sin cambiar el importador para ocultarlo.
  Al terminar C2, el cold probe detectó un import base retirado por error al
  mover el admin (restaurado), y un fixture de grupo arbitrario incorrectamente
  considerado independiente (corregido para usar Usuario Ver, manteniendo el
  clasificador C1). Las corridas fallidas no se presentan como aprobadas.
- No se ejecutaron suite completa, imágenes aisladas C3, CI, smoke en entornos,
  deploy ni aceptación humana. #2641 y #2725 permanecen OPEN; #2725 postergado.

Rollback C2: coordinar consumidor, adaptador, rutas, admin y templates con la
versión anterior. No hay migraciones C2 ni cambios de esquema/ContentTypes ni
transformación automática de filas existentes. No hubo acciones sobre datos
reales. El rollback de C1 conserva sus requisitos propios.
La comprensión humana no se declara validada: revisión y ejercicios fueron
delegados/declinados en la sesión anterior. Skills usadas: brainstorming para
contrastar el alcance ya aprobado, systematic-debugging para reproducir el diff
de auditoría ausente, y pdf para renderizar e inspeccionar las certificaciones.

La comparación final contra el snapshot C0+C1 sólo toca cuatro rutas compartidas
intencionalmente: `.importlinter`, guía, mapa y `core/backend_proxy.py`.
Las otras 91 entradas conservan exactamente su hash/ausencia original. Las
funciones C1 del proxy se conservan; C2 sólo agrega la propiedad de secciones.
Registro de backends, imágenes y Compose permanecen sin cambios de C3.
Se conserva el backup inicial y se agrega snapshot C2 final en el scratch.

Al terminar se retiraron MySQL tmpfs y la red del proyecto sintético; se verificaron
cero contenedores y redes remanentes del proyecto. No se tocó ningún entorno.
