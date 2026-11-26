# U04/U05: lotes de credenciales e importación de usuarios

E2: preparación fuente, sin app/workers/DB/email/tests o capturas ejecutados.
U04.01/02 y U05.01/02 conservan IDs. U-CR1 resuelve temporal individual; no habilita
nueva exposición masiva. Descarga CSV sensible U05 ya existe con control propio.

## U04: envío de temporales existentes

usuarios/credenciales-masivas/: GET/POST carga, plantilla/?tipo_envio, lotes/<pk>/
GET, lotes/<pk>/reanudar/ POST. Guard ChangeUser Y permiso específico masivo,
bypasssuperusuario existente. Form tipo_envio/archivo XLSX, standard o inet.
Headers standard usuario/mail; INET añade Nombre del Centro. Columna mail existe,
celda vacía usa email usuario; INET centro porfila. Validar libro antes de crear job.

Resolver username__iexact es global, no scopeadministrable; temporal existente
se reutiliza, no genera/cambia password. Sin usuario/mailválido/temporal falla de
dominio. Historial reciente propio; detalle/reanudar porID no limitados a solicitante.
Conservar/documentar alcance, no copiar restricciónCSVU05 ni certificar seguridad.

Carga válida guarda archivo/job→detalle. Filas50/página ordenfila,id; estado,
contadores/última fila/intento/error/reanudaciones/destinatario. Actualizar manualGET,
no pollingJSON existente. Estados pending→processing→completed|failed; reanudar
solo failed→pending con checkpoint y contador; estancado→failed. No cancelación
inventada. React no inicia job al consultar estado ni reintenta carga automática.

Worker agrupa email y centro según tipo; omite filas sent, para al primerfallo.
Checkpoint no garantiza exactly-once si SMTP envió antes de persistir marca. No
contraseñas en DTO/avisos/almacenamiento cliente; U04 no expone descarga masiva en
estas vistas. Pruebas futuras simulan SMTP, sin envío real ni datos reales.

## U05: importar es encolar, no preview-confirmar

usuarios/importar/: GET/POST, plantillaGET, lotes/<pk>GET, reanudarPOST,
descargar-csvGET. Guard AddUser. Form archivo, enviar_credenciales opcionalinitialTrue,
es_pwa opcionalinitialFalse. Requeridos nombre/apellido/permisos/provincias/rol;
opcionales correo/username/accion_grupos/organizaciones/comedores/dni/inspecciones.
Accionesgrupos agregar/quitar/reemplazar. Errorlibro en archivo; válido guarda filas
pending/job y redirectdetalle, no etapa confirmación o autosave nueva.

Autoriza filas job.requested_by, no observador/reanudador. Delegación/PWA/Inspecciones
se resuelven por ese actor; existentes pueden recibir accionesgrupos, nuevos generan
username si falta y temporal. No dividir identidad/asociaciones en escriturascliente.

Historial propio; detalle/reanudar sin filtrosolicitante. CSV solo solicitante o
superusuario, otro404. Detalle50/página ordenfila,id con estado/page y queryestado
conservado. GETactualizar manual, no nuevo polling por defecto. Estadosjob pending,
processing,completed,completed_with_errors,failed; filas pending,created,skipped,
failed. Filafallida detiene; reanudarfailed conserva checkpoint; leaseUUID+locks,
estancado→pending y cesiónslice. Es diferente de U04, no serviciojob genérico nuevo.

No cancelación fuente, no dedup de archivo acreditada: repetirPOST crea otrojob.
Email opcional agrupado con temporalesvigentes, credentials_sent_at aléxito;
falloSMTP agrega mensaje, no revierte usuarios. No prometer atomicidadDB+correo ni
exactamente una vez por tener lease/checkpoint.

### CSV sensible existente: backend, no DTO secreto nuevo

Usuario,Nombre,Apellido,Correo,Rol,Contraseña temporal. Filas created con usuario
vivo; temporal se lee Profile al descargar y vacío si must_change_passwordFalse.
No snapshot inmutable de creación. Mantener endpoint autenticado y permiso propio,
no elevar a otroactor por ver detalle/reanudar. React no parsea CSV para poblar
estadoUI, no incluye secreto en JSONdetalles/avisos/contexto/cache/storage. No
retención/purga/caducidad inventada del archivo; verificar política/cabeceras reales
antes de afirmar cumplimiento. U-CR1 no amplía permiso a exportación nueva.

## Exportaciones U06.03/U07

Usuarios ViewUser Y rolCSV; get_filtered_usuarios_en_alcance y orden sort/direction
por whitelist. Grupos ViewGroup Y rolCSV, querysetglobal/conteopermisos: esta vista
no aplica busqueda del listado, divergencia fuente no corregida incidentalmente.
Columnasactivas por preferencia. Usuarios defaults first_name,last_name,username,
email,rol,password_reset_requested_indicator; opcionales is_active,is_staff,
is_superuser,last_login,date_joined,id. Grupos defaults name,permissions_count;
id opcional. Ninguna agrega contraseña por poder exportar usuarios.

## Dependencia Form Comedores

Campos representante/coordinadorPWA/duplas/comedoresadicionales/rendiciones/permisos
operativos/tipoasociación/organizaciones/comedores. CoordinadorPWA requiereduplas,
incompatible con coordinadorSISOC/territorial/operadoractivo. Representante requiere
organización/comedor e incompatible con coordinadorSISOC/operadoractivo. Desmarcar
representante limpia asociaciones según Form. No inferir esquema completo por
este resumen: identidad heredada y permisosoperativos requieren anexo dirigido.

## Casos futuros por URL/estado/rol

Carga vacía/error/standard-INET/plantilla, historial vacío/ajeno, detalle estados/
errorlargo, reanudarválido-inválido, filas50/filtroestado/actualizarmanual. GuardsAND,
actorobserva/reanuda segúnfuente frente CSV404ajeno y superpermitido; CSV después
cambiopassword, sinusuariosvivos, cabeceras/controlacceso. Checkpoint/fallointermedio/
leaseperdido/estancado/correoagrupado/falloSMTP sinrollback; resultadoincierto noPOSTretry.
Export columnas/filtros/orden/scope/gruposbusqueda. Sin envío real, sintéticos y
simulados, desktop/móvil/foco/mensajes/retornos, referencia/candidato/diff acumulado.

## Fuente

src/backends/sisoc_core/usuarios/views.py:232–358; urls.py:82–144;
views_user_import.py:29–153; views_export.py:16–80;
src/backends/kernel/users/services_bulk_credentials.py:178–208,563–705;
services_bulk_credentials_jobs.py:72–174,532–687; models.py:453–643;
form_sections.py:925–966; services_user_import.py:47–95,239–389,462–500,839–924;
services_user_import_jobs.py:92–219,498–595; usuarios_column_config.py:7–127;
src/backends/sisoc_core/usuarios/grupos_column_config.py:7–37;
src/backends/comedores/pwa/user_forms.py:140–207,338–410.
Explorer comparó ocho archivos principales servicios/jobs/modelos/exportación/Form
Comedores con59a8f797688c9e762d5a4e9eaa187698ffade8aa normalizandoCRLF; no atribuir
ese SHA a archivos adicionales sin comparación. Padre contrastó guardCSV de import.
CodeGraphsync; sin ejecución, configuración, CI, commit/push/deploy.

- [ABM usuarios y U-CR1](2026-10-28-2785-usuarios-grupos-y-credenciales.md).
- [Catálogo](2026-10-27-2785-entregas-por-flujo.json).
