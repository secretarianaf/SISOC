# Autenticación de SIIS mediante SISOC

Estado: alineación cerrada y diseño aprobado por el usuario el 2026-10-06 mediante grill-with-docs. Implementación local escrita, pendiente de pruebas Django y revisión; entrega operativa pendiente. No se emitieron credenciales ni se desplegó. Ver [registro de implementación](../../registro/cambios/2026-T4/2026-10-06-auth-siis.md).

## Modelo de accesos confirmado

- Una misma cuenta puede tener acceso a varias aplicaciones y a SISOC web mediante habilitaciones independientes.
- Se añadirá un indicador explícito de acceso a SISOC web.
- Una cuenta nueva creada desde SIIS tendrá inicialmente solo acceso a SIIS.
- Tener acceso a SIIS no bloquea por sí mismo el acceso web; ingresar a SISOC web depende de su propia habilitación y de las demás condiciones aplicables.
- El indicador de acceso web controlará tanto el backoffice de SISOC como el administrador de Django (`/admin/`). Los permisos existentes siguen siendo necesarios para operar en cada interfaz.
- Para las cuentas existentes, se inicializará el acceso web habilitado, salvo para cuentas exclusivas de otras aplicaciones. Se preservará el acceso web de quienes hoy pueden usar ambos, incluidos los coordinadores y administradores de DataCalle.
- Después de inicializar el indicador, la habilitación de ingreso web dependerá de ese indicador explícito, no de ser coordinador ni de los roles o accesos de otra aplicación. Las condiciones generales de autenticación y los permisos de cada interfaz siguen aplicando.
- La clasificación de cuentas actuales solo sirve para inicializar el indicador; no será una regla dinámica que vuelva a calcularlo a partir de los roles.
- Se retirarán las exclusiones entre aplicaciones que impiden combinar DataCalle con representante PWA o Territorial comedor en el formulario de usuarios. Se conservarán las reglas internas de roles, asociaciones y alcances de cada aplicación.
- Si se deshabilita el acceso web de una cuenta con sesión abierta, la siguiente solicitud web debe quedar bloqueada. La regla aplica tanto al backoffice como a `/admin/` y no depende de que el usuario cierre sesión.
- En el formulario de creación del backoffice de SISOC, el indicador de acceso web aparecerá marcado por defecto y podrá desmarcarse. Esto no cambia el alta desde SIIS, que crea la cuenta con acceso web deshabilitado.

Este acuerdo reemplaza la regla anterior de bloqueo web para toda cuenta SIIS. La creación y la habilitación de una cuenta existente son acciones distintas. Las habilitaciones se administran exclusivamente desde SISOC; SIIS no puede modificarlas.

El alta con username o DNI existente sigue rechazándose. No se modifica una cuenta existente como efecto de un intento de alta.

## Alcance confirmado por el usuario

- SIIS tendrá un formulario que envía username y password a SISOC.
- SISOC debe responder si el usuario tiene acceso a SIIS y devolver datos del usuario.
- Los roles de SIIS se administran en SIIS.
- Se solicita un indicador de acceso a SIIS en el modelo, siguiendo los patrones existentes.
- SIIS inicia el alta de usuarios y las cuentas deben guardarse en SISOC. Se reutilizará un endpoint apropiado si existe; en caso contrario se creará uno.
- El alta desde SIIS la solicita un administrador que ingresa con su propia cuenta de SISOC. SISOC debe comprobar su permiso para crear usuarios en cada solicitud de alta; una validación solo en SIIS no alcanza.
- Los permisos administrativos para esta integración se controlan en SISOC, independientemente de los roles operativos de SIIS. El permiso requerido para las altas será `auth.add_user`, igual que en el backoffice actual. La identidad se acredita mediante el token firmado acordado.
- Una cuenta creada desde SIIS queda habilitada para ingresar a SIIS inmediatamente, sin aprobación posterior en SISOC.
- Si el username solicitado ya existe en SISOC, se rechaza el alta. Este flujo no habilita ni modifica cuentas existentes, cualquiera sea su origen.
- El administrador define la contraseña al crear la cuenta desde SIIS. No se eligió un flujo de alta mediante enlace para que el usuario establezca su contraseña.
- El usuario puede seguir usando esa contraseña: no se exige cambio obligatorio inicial para el alta desde SIIS. Consecuencia de la decisión: el administrador conoce la contraseña inicial y puede seguir conociendo la vigente hasta que el usuario la cambie.
- La respuesta de login exitoso para SIIS debe contener únicamente: id, username, nombre, apellido, email, DNI y habilitación para SIIS. Los nombres JSON exactos, salvo id y username, están pendientes. No se acordó incluir un token en esa respuesta.
- Las solicitudes de login y de alta llegan a SISOC desde el servidor de SIIS, no directamente desde el navegador del usuario.
- SIIS enviará `app: "siis"` en el payload de `POST /api/users/login/`, junto con username y password. Ese campo selecciona el contrato SIIS y requiere una API key válida; una clave ausente o inválida no debe causar fallback al login legacy.
- Las apps existentes podrán seguir enviando su payload actual, sin `app`, y conservarán su contrato de login. Se acepta temporalmente esa diferencia para evitar exigir cambios a los clientes externos. No se hará obligatoria la identificación de aplicación en los clientes actuales como parte de esta feature.
- SIIS exigirá una API key válida en login y altas, administrada mediante la herramienta existente de SISOC y revocable sin despliegue. Por decisión explícita del usuario, se acepta cualquier API key válida de esa herramienta; no se añade un modelo de claves ni aislamiento entre integraciones. Esta regla reemplaza el requisito anterior de aceptar una clave exclusiva de SIIS. La API key no sustituye las credenciales del usuario ni la validación del permiso del administrador para crear cuentas.
- Los administradores de SIIS pueden administrar usuarios desde SIIS según sus permisos de SISOC. Su acceso a la web de SISOC depende de la habilitación web independiente, no de estar habilitados para SIIS.
- Si se necesita una cuenta administradora, debe solicitarse al equipo responsable de SISOC. El alta desde SIIS no debe conceder permisos administrativos.
- Para las altas, SIIS enviará su API key y un token del administrador emitido por SISOC mediante una operación separada de autenticación administrativa. El login ordinario conserva únicamente los datos acordados.
- En cada alta, SISOC debe validar la identidad del administrador y comprobar que siga activo, habilitado para SIIS y con `auth.add_user`. Retirar ese permiso debe impedir la siguiente alta aunque el administrador conserve un token.
- El token administrativo vence una hora después de su emisión, sin renovación automática. Para continuar creando usuarios después de ese plazo, el administrador debe volver a autenticarse. La habilitación y los permisos se comprueban en cada alta dentro de ese plazo.
- En el login de SIIS, credenciales válidas sin habilitación para SIIS producen `403 Forbidden`, con un mensaje de acceso no habilitado y sin datos personales.
- El alta desde SIIS exige username, contraseña, nombre, apellido, email y DNI. Ninguno de esos seis campos es opcional.
- El alta desde SIIS se rechaza si el DNI ya está asociado a otra cuenta de SISOC, aunque el username sea nuevo. No se modifica la cuenta existente. La regla acordada corresponde al alta desde SIIS; no se acordó modificar los demás flujos de alta ni imponer una restricción global de base de datos.
- Si el alta se rechaza por una cuenta existente, la respuesta debe aclarar esa situación e indicar que se solicite al soporte de SISOC la habilitación para SIIS. No debe modificar la cuenta ni devolver sus datos personales.
- El alta desde SIIS también se rechaza cuando el email ya está asociado a otra cuenta de SISOC, con el mismo mensaje de contacto con soporte y sin modificar la cuenta existente.
- Para detectar duplicados de username y email, la comparación ignora mayúsculas/minúsculas y espacios al principio y al final. Esto no cambia por sí mismo el comportamiento de autenticación de los otros clientes.
- Por decisión explícita del usuario, no se añadirá protección específica contra altas concurrentes con el mismo DNI o email, ni en SIIS ni en otros flujos. Se comprobarán duplicados antes de crear y se conservará la unicidad existente de username. Riesgo aceptado: dos solicitudes simultáneas podrían crear cuentas con DNI o email repetidos.
- La primera versión ofrece login y alta desde SIIS, incluyendo la autenticación administrativa separada ya acordada. La edición, desactivación y gestión de habilitaciones quedan en SISOC; no se añaden esas operaciones a la API de SIIS.
- El DNI del alta admite entre 7 y 8 dígitos, permitiendo puntos y espacios que SISOC quitará antes de guardar y comparar. Se conservará como texto. La comparación debe contemplar esos separadores en los DNI existentes sin modificarlos como efecto del alta.
- Se acepta que retirar la habilitación SIIS impida nuevos logins, sin cerrar automáticamente sesiones ordinarias ya abiertas en SIIS. SIIS administra el vencimiento y cierre de esas sesiones. Las altas administrativas sí comprueban la habilitación vigente en cada solicitud.
- En esta primera versión, la recuperación de contraseña de usuarios SIIS la resuelve el soporte de SISOC. No se añadirán endpoints de recuperación SIIS ni se ampliará automáticamente el flujo API exclusivo de PWA.
- La entrega a SIIS debe incluir documentación del contrato y una API key válida. La documentación puede contener ejemplos con placeholders, nunca la clave real. La emisión y entrega de la clave requieren definir el entorno y usar un canal privado; no se realizaron durante esta alineación.
- Por decisión explícita del usuario, el login SIIS y la emisión de su token administrativo no se rechazan por `must_change_password` ni por el vencimiento de una contraseña temporal. Se siguen validando contraseña correcta, cuenta activa, acceso SIIS y, para el token administrativo, `auth.add_user`. No se limpian esos flags ni se modifican las políticas de los demás flujos. Consecuencia aceptada: una contraseña temporal puede seguir sirviendo para SIIS mientras sea la vigente, aunque haya vencido para otros flujos.

## Decisión acordada: identidad del administrador

Se eligió la recomendación del agente de usar un token del administrador y una operación separada para obtenerlo. Esto permite comprobar la identidad en SISOC sin conservar la contraseña para cada alta y mantiene la respuesta de login ordinario acordada.

Alternativas presentadas y no elegidas:

- Credenciales del administrador en cada alta: evita tokens adicionales, pero exige volver a pedir la contraseña o conservarla en SIIS.
- API key más ID del administrador: delega en SIIS la prueba de identidad; quien tenga la API key puede declarar la identidad de cualquier administrador.

Se confirmó un token firmado con herramientas de Django, exclusivo para las altas administrativas SIIS y separado del Token DRF compartido por las apps actuales. Vence una hora después de su emisión, sin renovación automática. No requiere una tabla adicional y no admite revocación individual; SISOC seguirá bloqueando las altas si el administrador pierde su habilitación, su permiso o su estado activo, o si se revoca la API key de SIIS.

La decisión acepta la limitación de revocación individual a cambio de menor complejidad de almacenamiento y gestión. La alternativa presentada fue un token almacenado independiente con revocación individual. Quedan por definir el contrato exacto de emisión y la vinculación del token a la integración.

### Comparación con las integraciones actuales

- PWA, Territorial comedor y DataCalle usan el login compartido de `/api/users/login/`, que crea o reutiliza el Token DRF almacenado del usuario. El backend revisado no configura vencimiento automático de ese token. El logout compartido lo elimina, por lo que afecta a las apps que estén usando ese mismo token.
- Las API de PWA y DataCalle usan `TokenAuthentication` y comprueban permisos de aplicación en las solicitudes. Evidencia: `src/backends/sisoc_core/pwa/api_views.py` y `src/backends/dispositivos/datacalle/api_views.py`.
- Ticketera usa una API key para sus operaciones server-to-server y verifica username/password en su endpoint de autenticación sin emitir Token DRF. Ticketera administra sus sesiones. Su alta se autoriza mediante la API key, sin acreditar un administrador con `auth.add_user` como se requiere para SIIS.
- Reutilizar el Token DRF compartido para las altas administrativas SIIS acoplaría su revocación al logout de las otras apps y no cumple por sí solo el vencimiento independiente de una hora acordado.
- Se eligió el token firmado exclusivo para las altas SIIS, sin tabla adicional y sin revocación individual. La comparación anterior describe código del checkout, no una validación de comportamiento en producción.
- Se confirmó reutilizar las API keys existentes y aceptar cualquiera que sea válida. Se descartó un tipo/modelo de claves exclusivo de SIIS. Consecuencia aceptada: una clave válida de otra integración también puede autorizar una llamada al canal SIIS, y una clave utilizada por SIIS sigue siendo aceptable en endpoints que admiten API keys genéricas. Las altas siguen exigiendo además el token y el permiso del administrador.

## Glosario de la integración

**Habilitación para SIIS**: autorización de una cuenta para ingresar a SIIS, administrada en SISOC.

**Rol de SIIS**: función y permisos de una persona dentro de SIIS, administrados por SIIS.

**Alta desde SIIS**: creación de una cuenta en SISOC solicitada desde SIIS.

**Habilitación para SISOC web**: autorización independiente para ingresar a la interfaz web de SISOC; puede coexistir con accesos a aplicaciones externas.

**Administrador autorizado para altas desde SIIS**: usuario de SISOC con permiso para solicitar la creación de cuentas desde SIIS. SISOC es quien determina esa autorización.

## Evidencia del código actual

- `src/backends/sisoc_core/usuarios/api_views.py`: el login valida credenciales y acceso PWA, Territorial o DataCalle; devuelve un token de SISOC, su tipo, ID y username.
- `src/backends/kernel/users/models.py`: `Profile` contiene indicadores de acceso mobile; DataCalle también tiene un campo de rol.
- `src/backends/sisoc_core/tests/test_users_api_login.py`: cobertura existente de credenciales inválidas, rechazo sin acceso PWA y acceso territorial.
- `src/backends/sisoc_core/usuarios/api_urls.py`: no registra un endpoint de alta general en `/api/users/`.
- `src/backends/cdi/ticketera/api_views.py` y `docs/integraciones/ticketera_api.md`: existe un alta server-to-server específica de Ticketera, con API key y reglas de origen, colisión de username y contraseña temporal. Es un antecedente para evaluar reutilización de patrones; todavía no se decidió reutilizar ese endpoint para SIIS.
- `src/backends/sisoc_core/usuarios/forms.py`, `_clean_relevador_calle_fields`: el formulario actual impide combinar DataCalle con representante PWA o Territorial comedor. La independencia entre aplicaciones requiere decidir cómo adaptar estas exclusiones; no alcanza con añadir los indicadores SIIS y web.

## Diseño técnico aprobado

El usuario confirmó el cierre de la alineación con este diseño y sus límites documentados. Las rutas, campos y respuestas de esta sección describen el contrato acordado a implementar; no un comportamiento ya disponible.

### Contrato HTTP

- `POST /api/users/login/`: SIIS envía `app: "siis"`, `username` y `password`, con `Authorization: Api-Key <key>`. Se conserva el flujo legacy cuando no se envía `app`. El modo SIIS no emite ni crea un Token DRF.
- Respuesta SIIS exitosa: `id`, `username`, `first_name`, `last_name`, `email`, `dni`, `acceso_siis: true`. Las credenciales inválidas o una cuenta inactiva devuelven `401` sin datos personales; las credenciales válidas sin acceso SIIS devuelven el `403` acordado. La API key también debe ser válida.
- `POST /api/users/siis/admin-token/`: exige API key y credenciales de un usuario activo, habilitado para SIIS y con `auth.add_user`. Devuelve `admin_token` y `expires_in: 3600`.
- `POST /api/users/siis/`: alta con API key y `X-SIIS-Admin-Token`, y body con `username`, `password`, `first_name`, `last_name`, `email` y `dni`, todos obligatorios. La cuenta se crea activa, con acceso SIIS y sin acceso web, otros accesos, staff, superusuario, grupos o permisos administrativos concedidos por el payload.
- Alta exitosa: `201` y los mismos siete campos de usuario acordados para SIIS, sin devolver contraseña ni token de las apps existentes.
- Alta duplicada: `409` con un código estable y el mensaje de cuenta existente/contacto con soporte, sin indicar datos de la cuenta encontrada.
- Campos inválidos o faltantes: `400` con errores en español. Contraseña validada mediante la política existente de Django y almacenada con su hash; nunca en texto plano ni en el campo de contraseña temporal visible.
- Los campos de privilegios y habilitaciones adicionales en el alta se rechazan; no se aceptan cambios de rol, staff, superusuario, grupos, permisos, source ni acceso web enviados por SIIS.

### Implementación y transición

- Indicadores propuestos en `Profile`: `acceso_siis` y `acceso_web`. El alta SIIS fija explícitamente `true` y `false`, respectivamente. El formulario web muestra la habilitación web marcada inicialmente.
- Administrar ambos indicadores desde la edición existente de usuarios y el admin, conservando permisos y restricciones actuales del actor. La API SIIS no incluye una operación de edición de habilitaciones.
- Inicializar el indicador web de las cuentas existentes según las reglas acordadas, preservando cuentas hoy habilitadas para ambas interfaces/aplicaciones. No reescribir roles ni recalcular el flag en cada login.
- Reemplazar el bloqueo de login web basado en tipo de aplicación/rol por el indicador explícito, cubrir login del backoffice y de Django admin, y comprobarlo también en las solicitudes con sesión abierta. Conservar los requisitos existentes de cuenta activa, staff y permisos donde correspondan.
- Revisar los otros flujos de creación para que introducir el indicador no habilite ni bloquee accidentalmente cuentas nuevas. Retirar solo las exclusiones entre aplicaciones aprobadas; conservar roles y alcances propios de cada app.
- Token firmado con propósito exclusivo para altas SIIS y comprobación de edad máxima de 3600 segundos. Validar en servidor la identidad, cuenta activa, acceso SIIS, permiso y API key antes de cada alta. No aceptarlo como Token DRF general.
- La firma del token debe separar el propósito SIIS de cualquier otro token firmado del proyecto. La identidad del actor se obtiene del token validado, nunca de un id/username administrativo declarado en el body del alta. La habilitación y el permiso se consultan de nuevo por solicitud.
- Reutilizar la biblioteca y administración actual de API keys, sin tabla nueva ni filtrado por integración. No reutilizar los endpoints específicos de Ticketera para SIIS porque sus reglas de reconciliación y contraseña temporal difieren.
- Reutilizar rate limiting y auditoría existentes para las operaciones nuevas. No registrar contraseñas, tokens, claves ni payloads con datos personales.

### Validación propuesta, todavía no ejecutada

| Criterio | Evidencia necesaria |
| --- | --- |
| Login SIIS válido | Exactamente los siete campos; sin creación de Token DRF |
| Credenciales inválidas, cuenta inactiva, falta de habilitación o API key inválida | Rechazo apropiado, sin datos personales ni fallback legacy |
| Cuenta con cambio obligatorio o contraseña temporal vencida | Login SIIS y emisión administrativa no se rechazan por esos flags; se conservan los flags y los demás requisitos de autenticación/permiso |
| Compatibilidad con apps actuales | Tests del login legacy conservan respuesta y emisión/reutilización de token |
| Alta autorizada | Cuenta y perfil creados juntos, solo SIIS habilitado y sin privilegios |
| Token ausente, alterado o vencido | Alta rechazada y sin creación parcial |
| Administrador desactivado o sin acceso/permiso después de emitir token | Siguiente alta rechazada |
| API key revocada después de emitir token | Siguiente operación rechazada |
| Duplicados | Username/email normalizados y DNI con/sin separadores provocan `409`; cuenta original intacta |
| Campos obligatorios, DNI y contraseña | Validación de campos faltantes/vacíos, DNI inválido y política de contraseña |
| Payload con privilegios adicionales | Rechazo sin asignar permisos, staff ni otros accesos |
| Flag web | Control de ambos logins y siguiente solicitud de una sesión existente |
| Inicialización web | Casos de usuario web, PWA exclusivo, DataCalle entrevistador y DataCalle coordinador/administrador |
| Accesos combinados | Formulario permite combinaciones aprobadas y conserva validación de roles/alcances |
| Guardado de accesos combinados | Activar o guardar PWA no borra grupos/permisos de DataCalle u otras aplicaciones |
| Alcance territorial combinado | Se conservan los rechazos actuales de conflictos territoriales; habilitar otra app no ensancha ni borra silenciosamente el alcance |
| Concurrencia DNI/email | Sin cobertura ni garantía adicional, por exclusión explícita del usuario |

Antes de implementar, identificar los tests y comandos oficiales mínimos que cubren estos criterios. No se autorizan pruebas en QA/HML/PRD, ejecución de migraciones sobre datos reales, despliegues, commits ni pushes por esta alineación.

## Revisión técnica del diseño (2026-10-06)

Revisión hecha por el agente a pedido del usuario, que declinó realizar la primera revisión. Es revisión de diseño y código existente; no prueba funcional de la feature.

1. **La independencia entre aplicaciones requiere adaptar el guardado, no solo quitar exclusiones.** En `src/backends/sisoc_core/usuarios/forms.py`, las ramas de guardado de representantes y coordinadores PWA vacían grupos y permisos directos, y algunas ramas alteran staff por tipo de aplicación. La implementación debe preservar los permisos de otras apps y sus límites de delegación. El flag web no debe conceder staff ni permisos por sí mismo. Hay que cubrir creación y edición; un cambio global de limpieza de permisos podría introducir escaladas y requiere tests de combinaciones y actor sin autorización.
2. **El alcance territorial compartido ya tiene una protección que debe mantenerse.** `_validar_conflicto_alcance_datacalle` rechaza derivaciones del rol DataCalle que borrarían o ampliarían el alcance genérico compartido por otros módulos. Se conserva esa validación. Se eliminan las exclusiones por pertenecer a otra aplicación, no los conflictos reales de alcance. Esta feature no crea alcances independientes por aplicación ni garantiza combinar roles territoriales incompatibles.
3. **Django admin no utiliza el formulario de login del backoffice.** `src/backends/config/urls.py` registra `admin.site.urls`; cambiar solo `BackofficeAuthenticationForm` deja un punto de entrada sin cubrir. El diseño requiere cubrir el ingreso admin y las solicitudes con sesión existente, también en runtimes que usan el middleware compartido. Las rutas públicas necesarias para autenticación/logout y las API deben tener un tratamiento explícito para evitar bloqueos o redirecciones circulares.
4. **La inicialización del flag web necesita migración histórica y revisión de todos los productores de cuentas.** `src/backends/kernel/users/signals.py` crea el Profile al guardar User; formularios, Ticketera, imports y comandos también originan cuentas. Un default aislado puede habilitar cuentas de apps o bloquear altas legítimas. Separar el schema del kernel de la inicialización que conoce PWA/core; no importar aplicaciones del core desde el kernel ni usar helpers actuales dentro de una migración histórica. Antes de concretar la migración, identificar su dueño y dependencias en el grafo del migrador completo.
5. **La recuperación API actual es exclusiva de PWA.** `src/backends/sisoc_core/usuarios/services_password_reset_pwa.py` descarta usuarios sin acceso PWA. No sirve automáticamente para un usuario solo SIIS. El usuario confirmó que la recuperación SIIS se resuelve mediante soporte de SISOC, sin endpoints nuevos. El procedimiento operativo concreto de soporte deberá respetar los flags y políticas de contraseña; no se inventa ni se ejecuta un procedimiento sobre cuentas reales durante la alineación.
6. **La compatibilidad requiere selección explícita y sin fallback.** El modo SIIS debe seleccionarse por el request, no por el origen ni por los flags del usuario. Una cuenta con acceso a varias apps puede usar ambos contratos. No emitir el Token DRF compartido para el login SIIS ni cambiar el logout y vencimiento de las apps actuales. No cambiar silenciosamente la sensibilidad a mayúsculas del login existente: normalizar la detección de duplicados no es lo mismo que modificar la autenticación.
7. **El rollback del control web tiene riesgo de seguridad.** Volver a código anterior que no consulta el flag puede permitir login web a cuentas solo SIIS, aunque el nuevo flag siga deshabilitado. Antes de incorporar o desplegar se necesita un rollback que mantenga el control de acceso, o una mitigación explícita aprobada. No se ejecutó ni preparó un cambio sobre datos reales.

Tests existentes relevantes para ampliar durante la implementación:

- `src/backends/sisoc_core/tests/test_users_api_login.py`
- `src/backends/sisoc_core/tests/test_users_pwa_forms.py`
- `src/backends/sisoc_core/tests/test_users_auth_flows.py`
- `src/backends/sisoc_core/tests/test_users_secciones_por_permiso.py`
- `src/backends/dispositivos/tests/test_datacalle_qa_usuarios.py`
- `src/backends/kernel/tests/test_users_signals_unit.py`
- Agregar cobertura enfocada para SIIS, middleware/admin y la migración histórica del flag web.

Verificación realizada: lectura del código, de pruebas cercanas y de reglas de boundaries/testing; verificador documental sin referencias obsoletas. No se ejecutaron tests Django ni pruebas de autenticación real, y no se instalaron dependencias. `requirements/base.txt` fija Django 5.2.16, DRF 3.16.1 y djangorestframework-api-key 3.1.0; el Python local consultado no tiene instalada la biblioteca de API keys.

## Pendiente para implementación y entrega

- Implementar el diseño aprobado y contrastar la guía externa con las respuestas reales antes de entregarla como servicio operativo.
- Definir durante la implementación/documentación operativa el procedimiento concreto de recuperación por soporte, sin ampliar el contrato SIIS acordado.
- Comprobar todos los puntos de ingreso y creación de usuarios antes de concretar la migración y la implementación; el Python local consultado no tiene instalada `rest_framework_api_key`.

## Fallos planteados por el usuario y criterio de entrega

- **Que se pisen accesos entre aplicaciones.** Riesgo confirmado por las ramas actuales de limpieza de grupos/permisos y derivación territorial. La implementación debe probar alta y edición de cuentas combinadas, preservar permisos y habilitaciones ajenos a la app modificada y mantener los rechazos de conflictos territoriales. Ningún flag debe conceder permisos administrativos por sí solo.
- **Que la integración sea confusa para el equipo de SIIS.** La entrega debe incluir una guía con login normal, autenticación administrativa, alta, campos obligatorios, ejemplos, errores, vencimiento y responsabilidad de sesiones/soporte, además de la API key por un canal privado. La guía debe aclarar que la API key sola no autoriza altas, que `app: "siis"` selecciona el contrato y que la cuenta creada tiene acceso solo a SIIS.

La [guía para el equipo de SIIS](../../integraciones/siis_api.md) documenta la propuesta HTTP. Antes de enviarla como contrato disponible, contrastarla con la implementación y ejecutar los casos de aceptación. Su publicación como servicio operativo y la entrega de la clave real siguen pendientes.

El usuario identificó riesgos de conservación de accesos y claridad contractual, y confirmó el cierre de la alineación con el diseño y sus límites documentados. Esto demuestra acuerdo sobre intención, alcance y esos riesgos, no una validación de funcionamiento ni comprensión completa de los detalles criptográficos y de migración.

Las limitaciones aceptadas son: contraseña inicial conocida por el administrador sin cambio obligatorio, aceptación SIIS de una contraseña vigente aunque sea temporal vencida o tenga cambio obligatorio pendiente, ausencia de revocación individual del token firmado, aceptación de cualquier API key válida, sesiones SIIS ordinarias administradas por SIIS y ausencia de garantía adicional de unicidad concurrente para DNI/email.

No se decidió implementar LDAP, Active Directory, SSO ni un protocolo de federación.
