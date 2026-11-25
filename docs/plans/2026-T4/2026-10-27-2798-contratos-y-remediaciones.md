# Precisión de contratos compartidos: identidad, Insumos y remediaciones

Estado: **E2, propuesta de contrato basada en fuente; sin implementación**.
Avanza los puntos 1 y 2 del pedido de profundización. No cierra todos los
contratos de las 95 familias. Complementa el
[contexto web](2026-10-27-2798-contrato-contexto-web.md), el
[catálogo](2026-10-27-2785-entregas-por-flujo.md) y
[G1](2026-10-27-2808-protocolo-g1.md).

Fuente de planificación: `59a8f797688c9e762d5a4e9eaa187698ffade8aa`.
Se verificó que los archivos de Insumos, auth_views y encuestas leídos desde
el checkout no difieren de ese snapshot. Lectura de código, no prueba HTTP.

## Insumos: contratos locales que pueden revisarse sin inventar negocio

| Slice | Rutas vigentes y responsabilidad | Campos/semántica que se preservan |
|---|---|---|
| I01.01 | GET `/insumos/`; propuesta nueva GET `/api/web/insumos/` | Filtros `busqueda`, `categoria`, `page`; 20 por página; orden por categoría orden/nombre y fecha descendente; búsqueda en título o descripción |
| I01.02 | GET `/insumos/<pk>/descargar` | Archivo protegido, nombre de archivo existente, inactivo descargable y faltante 404; sin media público ni descarga nueva por comodidad |
| I02.01 | `/insumos/categorias/` | Lista ordenada por orden/nombre, 20 por página; no confundir con opciones activas del filtro de Insumos |
| I02.02 | `/insumos/categorias/crear`, `/<pk>/editar`, `/<pk>/eliminar` dentro de categorías | Form con programa, nombre, descripción, orden y activo; mantener validación de nombre por programa y comportamiento de baja |
| I03.01 | `/insumos/crear`, `/insumos/<pk>/editar` | Programa, categoría, título, descripción, archivo y activo; conservar autor inicial y registrar actualizador mediante service actual |
| I03.02 | `/insumos/<pk>/eliminar` | Confirmación y operación autorizada del backend; eliminación DB/archivo mediante service existente, sin prometer atomicidad conjunta |

Las rutas de formularios son GET/presentación y POST/operación según las vistas
genéricas actuales; no se afirma con esto toda la lista efectiva de métodos
heredados. La implementación nueva define sus métodos explícitos y prueba el
rechazo de los restantes, sin alterar el endpoint legacy por asociación.

Fuentes: `src/backends/sisoc_core/insumos/urls.py`, `views.py`, `forms.py`,
`models.py`, `services.py` y `validators.py`.

### Lectura y opciones

La respuesta propuesta conserva `count`, `next`, `previous`, `results` y metadata
de página para reproducir el pager. Resultado mínimo: id, título,
`categoria_display`, fecha ISO con offset, `creado_por_display`, activo y enlace
protegido. `categoria_display` es nombre o `Sin categoría`; creador es nombre
completo, username o `-`. No devolver descripción completa solo porque se busca
en ella, usuario completo o URL de storage.

Opciones del filtro: categorías activas en orden actual; el listado puede
filtrarse por categoría inactiva si llega por URL. `sin` significa categoría
nula; texto no numérico distinto de `sin` no aplica filtro. Conservar strip.
Página inválida/fuera de rango y `last` deben reproducir el comportamiento de
ListView; no adoptar el default DRF sin cotejo. Cero resultados es estado válido.

### Visibilidad y autorización no son la misma función

La vista usa `user.has_perm('insumos.add_insumo')` para mostrar gestión y
`user.has_perm('insumos.add_insumocategoria')` para el botón de categorías.
Las rutas usan `permissions_any_required` de `core.decorators`, que delega en
`iam.services.user_has_permission_code`. Son caminos distintos: no sustituir
visibilidad por el predicado IAM ni inferir permiso de editar/borrar desde Add.

La API nueva reevalúa permiso real por petición; la UI proyecta la visibilidad
actual. Pruebas: usuario con Add sin Change/Delete, usuario con consulta sin Add,
roles/permisos normalizados y superusuario. No vaciar permission_classes en la
prueba que pretende demostrar autorización.

### Edición y archivos

El formulario filtra programas activos y categorías activas; al editar incluye
los actuales aunque estén inactivos. Categoría es opcional y debe pertenecer al
programa. La UI puede ayudar con `data-programa`, pero el form valida la relación.
Nombre de categoría duplicado por programa se controla desde el form existente.

El archivo usa validadores actuales: PDF/JPG/JPEG/PNG/DOC/DOCX/XLS/XLSX/CSV,
máximo 10 MiB y content type cuando está disponible. El atributo accept no los
reemplaza ni equivale a inspección exhaustiva del contenido. Conservar multipart,
edición sin reemplazo y errores actuales; no añadir base64 o subida pública.

`delete_insumo` elimina registro y luego archivo. No envolver solo DB en atomic
y afirmar que storage se revierte. Si se pierde respuesta o falla storage,
no repetir automáticamente ni afirmar que no hubo operación. Corregir ese ciclo
de vida requeriría un cambio separado, no una deducción de la migración visual.

## Identidad: campos y efectos que la presentación debe conservar

La declaración de login de `src/backends/config/urls_preview.py` apunta a
`admin.site.login`: es soporte de preview/admin, no otro login web a portar.
Conservar su referencia en el inventario como evidencia, sin incluirla como
pantalla nueva de U01 ni saltar la exclusión de admin/#2789.

| Recorrido | Entrada y fuente | Semántica crítica |
|---|---|---|
| Login | `UsuariosLoginView`, `BackofficeAuthenticationForm` | Usuario/contraseña mediante Django, habilitación web y retorno interno seguro; authed redirect y middleware actuales, no login token para fabricar cookie |
| Recuperación inicial | `UsernameEmailPasswordResetForm` | Username y email: busca usuario activo y coincidencia de correo casefold; no informar por API si la combinación existe; conserva backend/correo existente |
| Confirmación de recuperación | `PasswordResetConfirmCustomView` | Mantener token/uid y mecanismo Django de token en sesión; también compatibilidad de POST directo con token válido; no devolver ese token en contexto JSON |
| Cambio obligatorio | `FirstLoginPasswordChangeView`, `SetPasswordForm` | Guardar contraseña, limpiar flags/campos temporales y `update_session_auth_hash`; retorno actual a inicio |
| Mi cuenta/confirmación | `MiCuentaForm` y sus vistas | first_name, last_name, email, dni, cuil y correo_institucional; este último opcional; no grupos/permisos/rol/territorio/delegación |

Fuentes: `src/backends/sisoc_core/usuarios/auth_views.py`, `auth_forms.py`,
`src/backends/kernel/users/account_forms.py` y rutas de usuarios/config ya
identificadas en U01–U03. El formulario propio mantiene validaciones y guardado
transaccional cuando existen; no recrearlas con checks del navegador solamente.

**Diferencia de efectos confirmada en fuente:** confirmar recuperación web
elimina `rest_framework.authtoken.models.Token` del usuario y limpia campos
temporales del perfil. El cambio obligatorio, en cambio, actualiza hash de la
sesión actual y no contiene esa misma eliminación de Token en su `form_valid`.
No «unificar» ambos flujos ni omitir la revocación por interpretar que PWA está
fuera de la migración. Se preservan efectos existentes; no se amplía revocación.
La diferencia acreditada es la implementación explícita de ambas vistas; no se
infiere ausencia de efectos indirectos por señales u otras capas. Revisarlos y
fijar el resultado efectivo antes de cerrar los tests de revocación del contrato.

La nueva presentación necesita errores de campos/no campo y estado de enlace
inválido sin filtrar usuario/token. No reutilizar el endpoint PWA de reset sin
comparar esos efectos, CSRF y sesión. El contrato operativo nuevo de auth se
revisa aparte antes de código; este texto no implementa autenticación nueva.

## Matriz de requisitos por clase de operación

Una única regla «todas las APIs requieren ready» bloquearía las remediaciones.
La política debe reutilizar la prioridad fuente y permitir la acción que resuelve
el siguiente requisito, con excepciones exactas por método/ruta, no por prefijo.

| Operación | Regla propuesta que conserva el recorrido fuente |
|---|---|
| GET contexto web | Sesión válida, aunque haya requisitos pendientes; 200 con estado prioritario y sin capacidades/menú de negocio si no ready; anónimo 401 |
| API nueva de negocio | Acceso web, contraseña, perfil y encuesta resueltos, más permiso/alcance del dominio por request |
| Cambio obligatorio | Sesión y acceso web; permite resolver contraseña sin exigir antes perfil/encuesta. No ignora acceso web denegado |
| Confirmación de perfil | Sesión, acceso web y contraseña resuelta; permite resolver perfil antes de encuesta |
| Responder encuesta | Sesión, acceso web, contraseña y perfil resueltos; permite responder la encuesta pendiente sin exigir que ya esté completada |
| Logout | Mantener excepción actual ante requisitos pendientes y CSRF del método vigente; limpiar cache privado del frontend |
| Login/reset públicos | Reproducir excepciones y prioridad específicas de las rutas actuales. No deducir que un prefijo API exento autoriza cambiar el efecto de una cookie web restringida |
| Invitación PAS | P1: anónimo por token; con sesión restringida conserva bloqueos actuales en entry/datos/POST; además CSRF/validez/consumo de invitación |

La matriz es definición para revisar con la fuente, no un middleware instalado.
Antes de ejecutar, enumerar cada endpoint nuevo de remediación y sus métodos en
la allowlist mínima, con caso negativo de prioridad combinada. No confiar en el
estado cacheado por React o en una constancia creada para otra operación.

## Encuesta obligatoria: contrato de servicio que no debe perderse

`ResponderRondaView` recibe POST de un usuario segmentado; no exige permisos de
administrar encuestas para responder. `registrar_respuesta` comprueba estado y
cierre de ronda, respuesta previa y segmentación. Campos `respuesta-<pk>`; opción
múltiple requiere `getlist`, no un dict que pierda valores repetidos. Mantener
tipos, validaciones de preguntas y transacción: no guardar respuestas parciales.

Las vistas responden con mensajes y retorno seguro actuales. El adaptador JSON
futuro debe expresar el mismo éxito/error sin inventar progreso parcial o cambiar
reglas de posponer/descartar. Esas acciones siguen sus services, no un booleano
cliente. Fuentes: `src/backends/sisoc_core/encuestas/views.py`, `services.py` y
`templates/encuestas/partials/responder_modal.html`.

## Negativos que habilitan futuras tareas concretas

1. Entry anónimo Insumos 403 frente a API JSON 401, sin retirar guard global.
2. Permiso IAM/visibilidad, Add sin Change/Delete y llamada directa a mutación.
3. Filtros/orden/página, categorías inactivas y nombres/fechas idénticos.
4. Archivo existente/faltante/inactivo, tipo/tamaño inválidos y pérdida de respuesta.
5. Recuperación con combinación inválida, token vencido/usado, POST directo válido,
   revocación Token y cambio obligatorio con sesión conservada según fuente.
6. Perfil sin edición de permisos; requisitos combinados y remediaciones sin bucle.
7. Encuesta no segmentada, cerrada, vencida, duplicada, incompleta y múltiple;
   permiso de administración no requerido para la respuesta habilitada.
8. Invitación pública POST con CSRF real: SessionAuthentication/AllowAny no se
   aceptan como prueba suficiente de CSRF anónimo; conservar protección efectiva.

Validación actual: referencias y coherencia con código leído. No se probaron HTTP,
mail, tokens reales, DB, sesiones, uploads, servicios, capturas ni CI. Las rutas
API propuestas requieren revisión del contrato antes de implementación futura.

## Precisión posterior de identidad y excepciones

[Circuitos y campos](2026-10-27-2788-identidad-remediaciones-m2.md) incluyen cambio
voluntario estándar y rutas duplicadas/shadowed, CSRF anónimo, entrada estática
sin tokens en URL saliente y efectos distintos de recuperación/cambio obligatorio.
La cola de encuestas se ordena por vencimiento: no imponer obligatorias primero.

La fila previa «API nueva de negocio requiere todo resuelto» no cierra la política
de gestión de encuestas: su middleware tiene una excepción Change específica.
[S1 elegida](2026-10-27-2788-excepcion-gestion-encuestas.md) conserva
la excepción actual por operación, sin exceptuar un prefijo API completo. No se modifica OpenAPI
de contexto para convertir pending en ready ni se concede un bypass por rol cliente.
