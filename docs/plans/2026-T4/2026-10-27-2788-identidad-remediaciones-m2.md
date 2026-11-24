# Identidad, cuenta y respuesta de encuestas: circuitos M2

Estado **E2, contratos propuestos desde fuente**, sin código, entorno, correo,
sesiones, contraseñas reales o pruebas de aplicación. No se sustituyen G1/P1/C2,
I1/W1/M2/R1 ni la exclusión admin/Unfold #2789.

## Fuentes y alcance de evidencia

En `59a8f797688c9e762d5a4e9eaa187698ffade8aa`: usuarios/auth_views.py,
usuarios/urls.py, users/account_forms.py, users/middleware.py, config/urls.py y
encuestas/{views,services,middleware,context_processors}.py. Los archivos
auth_views/account_forms/middleware de users y views/services/middleware de
encuestas leídos del checkout no difieren de esa fuente. Se leyeron templates
de usuarios y modal/campo_pregunta de encuestas; no se renderizaron.

Nombres anteriores relativos a apps corresponden a `src/backends/sisoc_core/`
para usuarios/encuestas y `src/backends/kernel/` para users. La ampliación de
rutas estándar auth usa registro versionado y fuente de Django local 5.2.15,
sin importar Django ni resolver URLs. Objetivo del repo 5.2.17: repetir contraste
en versión objetivo antes de implementar; no afirmar identidad de versiones.

## Circuitos y rutas públicas

| Circuito | Paths y estados que deben ser React al activarlo | Efectos backend y dependencias |
|---|---|---|
| ID-A login/logout | `/`, `/login/`; logout `/logout` y `/logout/` con su destino | Sesión Django, CSRF, rotación y login seguro; logout POST y limpieza de estado privado. No usar login token PWA para fabricar cookie |
| ID-B recuperación | `/password_reset/`, `/password_reset/done/`, `/reset/<uidb64>/<token>/`, `/reset/done/` y alias `/password/reset/confirm/<uidb64>/<token>/` | Form username/email, envío de correo existente, validación de token/session por Django y formulario nuevo; no rediseñar mail backend ni enviar uno en E2 |
| ID-C cambio obligatorio | `/password/first-change/` | SetPasswordForm, limpiar flags/temporales y actualizar hash de sesión, retorno inicio; permite resolver requisito antes de perfil/encuesta |
| ID-D cuenta/confirmación | `/mi-cuenta/`, `/mi-cuenta/confirmar/` | MiCuentaForm propio, guardado atómico de User/Profile y confirmación; modal obligatorio sin cierre mantiene estética actual |
| ID-E cambio voluntario heredado | `/password_change/`, `/password_change/done/` | Form estándar con old_password + new_password1/2, sesión conservada según Django; no confundir con SetPasswordForm sin contraseña previa |
| EQ-A inicio y respuesta | `/inicio/` con modal pendiente y acciones `/encuestas/responder/<pk>/`, `.../mas-tarde/`, `.../descartar/` | Cola/service de rondas, segmentación, condiciones/preguntas y cumplimiento. Grupo transversal T01/E01, no todo ABM de encuestas |

Los nombres ID-* y EQ-A identifican grupos de activación propuestos, no apps,
servicios o tickets nuevos. Desarrollo/validación por slice sigue separado de
activación del circuito completo con formularios React. Enlaces a otros grupos
conservan paths; todos deben migrar antes del cierre integral.

La inclusión de django.contrib.auth.urls añade ocho rutas en su fuente local.
Login y cuatro rutas de reset están declaradas antes en config, con esos mismos
paths, por lo que no son cinco pantallas adicionales. Logout con slash y cambio
voluntario/done requieren cobertura propia. El suplemento estructurado conserva
esa distinción, sin sumar declaraciones al inventario original de 614/770.

## Entrada pública y frontera estática

El router v2 actual exige login y reenvía asset_path/query al upstream estático.
No basta quitarle login_required globalmente: preparar entrada pública acotada
para estos paths y assets permitidos; conservar el resto protegido y middleware
vigente. La propuesta requiere revisión técnica por tratar auth/settings/routing.

La entrada de página obtiene un index fijo/versionado sin cookies, Authorization,
token de reset, uid, next ni query privada en la URL al upstream. Distinguir
assets de navegación; no entregar cualquier URL de backend como fallback SPA.
Prueba futura registra URL sintética saliente para demostrar esa frontera, sin
registrar secretos reales. Error del frontend conserva emergencia 503 independiente.

Antes del POST de login inicializar CSRF con mecanismo Django para anónimos y
proteger login explícitamente. SessionAuthentication por sí sola no demuestra
CSRF anónimo. No relajar SameSite/CORS/CSP ni almacenar contraseña/token en
localStorage, sessionStorage, analytics, artefactos o estado global del frontend.
Reutilizar cliente y primitivas existentes; diseño exacto de bootstrap/endpoint
se revisa antes de código, sin inventar un nuevo sistema de autenticación.

Reset GET válido conserva canje de token a sesión y redirect a `set-password`
antes de servir UI cuando lo hace Django; admitir también POST directo válido
del contrato propio. No enviar token al servidor estático ni devolverlo desde
contexto web. Enlace inválido/expirado muestra el estado actual con React, no
un formulario utilizable. Revalidar al submit y tras cambio concurrente de clave.

## Contratos de formularios y resultados

| Operación | Datos exactos y reglas a preservar | Resultado/navegación |
|---|---|---|
| Login | username y password; usuario strip, contraseña sin trim para autenticar; vacío/espacios solo son inválidos; BackofficeAuthenticationForm valida activo, acceso_web y expiración inicial | Mismos errores de campo/general; contraseña vacía después de error, username conservado. Destino permitido por LoginView y controles posteriores, default inicio |
| Request reset | username requerido máx.150 y email validado; usuario activo exacto y correo casefold conforme get_users | Mismo done para combinación válida sintácticamente, coincida o no. No agregar enumeración de cuenta, respuesta con email real ni promesa de tiempo constante |
| Confirm reset | new_password1/2, validadores Django/token/usuario | Efectos de PasswordResetConfirmCustomView: guardar contraseña, eliminar DRF Token y limpiar flags/temporales. Retorno password_reset_complete; no auto-login inventado |
| Cambio obligatorio | new_password1/2 y mismo SetPasswordForm | Limpiar must_change_password y campos temporales, update_session_auth_hash; aviso «Contraseña actualizada correctamente.», inicio. Si ya no requerido, mismo redirect sin mutar |
| Cambio voluntario | old_password + new_password1/2 mediante PasswordChangeForm | Guardar y conservar sesión según framework, destino password_change_done. No sustituir por cambio obligatorio ni quitar old_password |
| Mi cuenta/confirmación | first_name, last_name, email, dni, cuil, correo_institucional | Todos requeridos salvo correo institucional; DNI normalizado/mínimo 6, CUIL por validador actual; email no se vuelve único; guardado User/Profile atómico, marca confirmada. Cuenta vuelve a sí misma; confirmación a inicio |
| Logout | POST de sesión y CSRF, sin user_id arbitrario | Invalidar sesión, limpiar datos en memoria y volver login; no replay de mutación al autenticar otra vez |

Las APIs nuevas se proponen bajo `/api/web/` con formas/errores y resultados
por operación, nunca HTML de formulario remoto ni model dump. Mantener IDs de
usuario implícitos por sesión en cuenta: no aceptar pk de otro usuario, grupos,
permisos, rol, territorio, delegación o flags privados desde payload.

No equiparar efectos explícitos de reset y cambio obligatorio/voluntario:
solo reset propio contiene eliminación explícita de DRF Token. Comprobar señales,
otros efectos y comportamiento del framework en tests futuros antes de afirmar
qué sesiones/tokens sobreviven. No ampliar revocación por intuición.

Un error de validación nueva API puede usar JSON 400 con errores de campo/general;
la UI conserva textos, ubicación y datos según cada formulario. Denegación,
sesión vencida y CSRF no se tratan como credenciales incorrectas por defecto.
No asumir JSON si el middleware responde HTML. Error de correo/infraestructura
no es confirmación de entrega; no probar mail real en esta etapa.

## Prioridades de requisitos y sus remediaciones

Acceso web → contraseña → perfil → encuesta → ready. Cada operación permite
resolver su propio requisito después de los superiores, sin requerir ready.
Logout sigue habilitado para salir de una sesión restringida. Cookie con acceso
web deshabilitado conserva denegación actual de rutas HTML, también en login/
reset; no tratar cualquier entrada pública como bypass de esa cookie existente.

Perfil histórico ausente: el Form puede crearlo, pero el control de acceso web
anterior puede bloquear antes; no conceder acceso_web para permitir confirmar.
No pedir a la UI que invente flags faltantes. Remediación que ya no es necesaria
conserva redirect/estado actual; recargar contexto después de cada éxito.

Excepción administrativa de encuestas conservada por [S1](2026-10-27-2788-excepcion-gestion-encuestas.md):
no traducir automáticamente `access.state != ready` en bloqueo sin excepciones
para todo endpoint. Tampoco crear bypass general por rol o prefijo `/api/`.

## Encuesta: cola, formulario, anonimato y acciones

get_rondas_pendientes ordena por cierre más cercano, no por obligatoriedad.
context_processor presenta la primera; middleware bloquea si existe cualquiera
obligatoria. Una opcional puede aparecer primero: mantener posibilidad de
responderla/descartarla según service antes de llegar a la obligatoria.
No ordenar obligatorias primero como supuesta optimización de React.

Mantener `respuesta-<pk>`, opciones múltiples con getlist, tipos y condiciones
de campo_pregunta/modal y JS actual del kernel. Backend vuelve a evaluar
visibilidad y valores; preguntas ocultas no exigen respuesta. La primera pregunta
inválida no puede dejar RespuestaRonda/RespuestaPregunta parciales.

Responder: sesión, requisitos superiores, segmentación y ronda abierta/no vencida/
no respondida, sin permiso de administración. Posponer solo postergables y
descartar solo opcionales; obligatorio no ofrece cerrar, ESC, posponer o descartar.
Las acciones revalidan ronda/segmentación/cumplimiento y evitan doble respuesta.

La respuesta anónima persiste usuario=None y cumplimiento separado. No devolver
un vínculo identificable ni contenido de respuestas en session context/logs.
POST actual retorna por `_redirect_next`: next solo host permitido/HTTPS según
request; fallback inicio. No reflejar Location arbitrario desde cliente.
Error actual también redirige con aviso y reconstruye modal: no introducir
guardado de borradores o persistencia de respuestas como mejora implícita.

## Referencia visual y aceptación

Login y recuperación tienen su layout propio, Montserrat/assets/CSS y responsive;
no adoptar shell oscuro Insumos para ellos. Cuenta/confirmación/obligatorio usan
main/base; confirmación tiene modal sin cierre. Cambio voluntario necesita fijar
template efectivo del framework y referencia en entorno: registro no prueba qué
loader/versión renderizó. No usar admin como baseline automático por reutilizar
un template de su paquete; esa URL pertenece a aplicación, fuera de `/admin/`.

El [manifiesto de identidad/encuestas](2026-10-27-2788-identidad-manifiesto-visual.json)
define estados, roles sintéticos y evidencia funcional/visual. No fija baseline
aceptada, entorno ni IDs reales. Comparar ambos lados por fixture aislada y reset
de casos mutantes; datos propios sintéticos y sin capturas de contraseñas/tokens.

Reversión de entrada UI no revierte cambio de contraseña, revocación o respuestas
ya guardadas. Conservar backend y versión compatible hasta aceptación; no abrir
auth para resolver fallback ni repetir POST tras perder la respuesta.
