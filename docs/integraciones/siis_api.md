# Integración SIIS con SISOC

## Responsabilidades

- SISOC guarda las cuentas, valida credenciales, habilitación SIIS y permiso para crear usuarios.
- SIIS realiza las solicitudes desde su servidor y administra sus roles y sesiones.
- Una cuenta puede usar varias aplicaciones. El acceso a SIIS no concede acceso web a SISOC ni acceso a otra app.
- Las habilitaciones y las altas de administradores se solicitan al equipo de SISOC. No se administran mediante esta API.
- La recuperación de contraseña SIIS se solicita al soporte de SISOC; no se agregan endpoints de recuperación en esta versión.

## Credenciales y conexión

SISOC debe proporcionar la URL base del entorno y una API key válida mediante el procedimiento de entrega acordado. Los ejemplos usan `API_KEY_DEL_ENTORNO` y `TOKEN_ADMINISTRATIVO` como placeholders; no son credenciales utilizables.

- Todas las operaciones SIIS requieren `Authorization: Api-Key API_KEY_DEL_ENTORNO`.
- La API key debe permanecer en el servidor de SIIS. No incluirla en el navegador, repositorio, documentación, URLs ni logs.
- El alta requiere además `X-SIIS-Admin-Token: TOKEN_ADMINISTRATIVO`.
- El token administrativo acredita al administrador. La API key acredita al sistema que llama y, por sí sola, no permite crear usuarios.
- El token administrativo vence una hora después de su emisión y no se renueva automáticamente. No se puede revocar individualmente.
- Para cada alta, SISOC consulta que el administrador siga activo, habilitado para SIIS y con `auth.add_user`, y que la API key siga vigente.
- Los tokens de las apps PWA/DataCalle no sustituyen este token administrativo.
- En entornos expuestos, usar HTTPS. Las contraseñas y las dos credenciales no deben registrarse en logs ni incluirse en mensajes de error.

## Login del usuario

`POST /api/users/login/`

Headers:

```http
Authorization: Api-Key API_KEY_DEL_ENTORNO
Content-Type: application/json
```

Body:

```json
{
  "app": "siis",
  "username": "usuario.ejemplo",
  "password": "CONTRASENA_DEL_USUARIO"
}
```

`app: "siis"` es obligatorio para seleccionar este contrato. No se debe omitir para intentar usar el flujo de las apps anteriores. La respuesta SIIS no depende de qué otras apps tenga habilitadas la cuenta.

Respuesta `200 OK`:

```json
{
  "id": 123,
  "username": "usuario.ejemplo",
  "first_name": "Nombre",
  "last_name": "Apellido",
  "email": "usuario@example.com",
  "dni": "12345678",
  "acceso_siis": true
}
```

La respuesta contiene únicamente esos siete campos. No emite un token de sesión SISOC. SIIS puede establecer su propia sesión después de recibir el resultado exitoso.

- `401`: credenciales inválidas o usuario inactivo, sin datos personales.
- `403`: API key ausente/inválida/revocada, o credenciales válidas de una cuenta sin habilitación SIIS. No se devuelven datos personales ni se vuelve al flujo legacy.
- `400`: request inválido o campos faltantes.
- `429`: límite de intentos alcanzado; no insistir en bucle ni volver a enviar automáticamente credenciales.

Retirar la habilitación SIIS impide nuevos logins. No cierra automáticamente una sesión ordinaria que SIIS ya mantenga abierta: su vencimiento y cierre son responsabilidad de SIIS.

## Contraseñas y cambio obligatorio

Regla acordada: el login SIIS y la emisión de su token administrativo no se rechazan por tener cambio obligatorio pendiente o una contraseña temporal vencida. La contraseña presentada debe seguir siendo la vigente y la cuenta debe estar activa y habilitada; para obtener el token administrativo también se exige `auth.add_user`. SISOC conserva los flags de contraseña de los otros flujos, sin limpiarlos al ingresar desde SIIS. Una contraseña temporal puede seguir sirviendo para SIIS mientras no cambie la contraseña vigente o los demás requisitos de acceso.

## Obtener token administrativo

Ruta acordada: `POST /api/users/siis/admin-token/`.

Usar los mismos headers de API key y JSON del login. Body:

```json
{
  "username": "administrador.ejemplo",
  "password": "CONTRASENA_DEL_ADMINISTRADOR"
}
```

La cuenta debe estar activa, habilitada para SIIS y tener `auth.add_user` en SISOC. Ser administrador según los roles internos de SIIS no basta.

Respuesta acordada `200 OK`:

```json
{
  "admin_token": "TOKEN_ADMINISTRATIVO",
  "expires_in": 3600
}
```

Guardar el token en el servidor para realizar las altas. Cuando expire, el administrador debe volver a autenticarse; no conservar su contraseña para renovar automáticamente el token. La expiración del token no modifica por sí sola la sesión ordinaria que SIIS mantiene.

- `401`: credenciales inválidas o cuenta inactiva.
- `403`: API key inválida, cuenta sin habilitación SIIS o sin permiso de alta.
- `400`: request inválido.
- `429`: límite de intentos.

## Crear usuario

Ruta acordada: `POST /api/users/siis/`.

Headers:

```http
Authorization: Api-Key API_KEY_DEL_ENTORNO
X-SIIS-Admin-Token: TOKEN_ADMINISTRATIVO
Content-Type: application/json
```

Body:

```json
{
  "username": "nuevo.usuario",
  "password": "CONTRASENA_DEFINIDA_POR_EL_ADMINISTRADOR",
  "first_name": "Nombre",
  "last_name": "Apellido",
  "email": "nuevo.usuario@example.com",
  "dni": "12.345.678"
}
```

Los seis campos son obligatorios y no pueden estar vacíos. La contraseña debe cumplir la política de SISOC. El DNI debe tener entre 7 y 8 dígitos; se permiten puntos y espacios ASCII, que SISOC quita antes de guardar y comparar. El DNI se conserva como texto.

La cuenta nace activa, habilitada para SIIS y sin acceso web ni accesos o permisos administrativos adicionales. El administrador define la contraseña, que se puede seguir usando sin cambio inicial obligatorio. SISOC no devuelve ni guarda esa contraseña como texto plano. La entrega de la contraseña al usuario no es una operación de esta API.

Respuesta acordada `201 Created`: los mismos siete campos del login, correspondientes a la cuenta nueva.

- `400`: campos faltantes/inválidos, contraseña que no cumple la política o intento de enviar campos de privilegios adicionales.
- `401`: token administrativo ausente, inválido, alterado o vencido.
- `403`: API key inválida o administrador que ya no está activo, habilitado o autorizado para el alta.
- `409`: username, email o DNI ya asociados a una cuenta existente.
- `429`: demasiadas solicitudes para la misma identidad; esperar y reintentar. Login y autenticación administrativa limitan por IP del servidor SIIS y username; las altas, por IP y administrador. La ventana es de 10 solicitudes cada 5 minutos para cada operación.

Respuesta acordada para cuenta existente:

```json
{
  "error": "account_exists",
  "message": "La cuenta ya existe. Solicitá al soporte de SISOC su habilitación para SIIS."
}
```

No se modifica ni habilita la cuenta existente y no se informa a quién pertenece. La comparación de username y email ignora mayúsculas/minúsculas y espacios externos; la de DNI ignora puntos y espacios. No repetir el alta cambiando username para sortear el rechazo.

No enviar `is_staff`, `is_superuser`, grupos, permisos, roles administrativos, source, acceso web ni otras habilitaciones. El actor administrativo sale del token validado, no de un id enviado en el body.

Si se pierde la respuesta de un alta, no asumir que falló: un reintento de una cuenta ya creada devuelve `409`, no una reconciliación automática. La API no ofrece búsqueda ni modificación de cuentas existentes.

## Colección Postman

Importar [SIIS.postman_collection.json](../api/postman/SIIS.postman_collection.json) en Postman. Incluye las tres operaciones con requests preparados y ejemplos guardados de respuestas exitosas y rechazos. Son ejemplos ficticios del contrato; no resultados de llamadas ejecutadas.

1. Crear y seleccionar un entorno privado. Configurar `baseUrl` (sin barra final), `apiKey`, `username`, `password`, `adminUsername` y `adminPassword`. Las variables de credenciales incluidas están vacías: completar sus valores localmente y marcarlas como secretas en Postman. No sincronizar ni exportar credenciales reales.
2. Enviar **1. Login SIIS** para comprobar la cuenta de prueba.
3. Enviar **2. Obtener token administrativo** y copiar `admin_token` a la variable secreta de entorno `adminToken`. La colección no almacena automáticamente el token ni las contraseñas.
4. Ajustar las variables `newUsername`, `newPassword`, `newFirstName`, `newLastName`, `newEmail` y `newDni`; enviar **3. Crear usuario** solo en un entorno de prueba autorizado. Este request crea una cuenta; repetirlo devuelve `409` si la cuenta ya existe.
5. Abrir los ejemplos guardados de cada request para consultar su body, status y respuesta. Los ejemplos no se ejecutan automáticamente. Las comprobaciones incluidas verifican respuestas exitosas cuando se envía una solicitud; no ejecutan operaciones adicionales.

`newPassword` también está vacía y debe cumplir la política de SISOC. El token de los ejemplos es el placeholder `TOKEN_ADMINISTRATIVO`, sin validez criptográfica. Cuando el token real venza, repetir la autenticación administrativa; no persistir la contraseña para renovarlo automáticamente.

## Entrega y prueba de integración

Antes de entregar como servicio disponible:

1. Validar la implementación local y verificar el contrato; actualizar esta guía si cambia un nombre, ruta o respuesta propuesta.
2. Confirmar el entorno y su URL base, sin utilizar cuentas reales en ejemplos.
3. Crear una API key mediante la herramienta existente de SISOC y entregarla al responsable de SIIS por un canal privado. No pegar la clave en esta guía, un issue, un PR ni un log.
4. Disponer de una cuenta administradora de prueba habilitada para SIIS y con `auth.add_user`, provista por el equipo de SISOC.
5. Comprobar login, autenticación administrativa, alta, duplicados y rechazos por falta de habilitación/permiso, token vencido y clave revocada.
6. Comprobar que las apps existentes conservan su contrato y que los accesos combinados no se pisan al editar usuarios.

Límites acordados: sin edición/desactivación por API SIIS, sin modificación de habilitaciones, sin revocación individual del token, sin cierre remoto de sesiones SIIS y sin protección adicional contra altas concurrentes con igual DNI/email.

La API acepta cualquier API key válida de la herramienta actual; no existe aislamiento por integración. Emitir una clave para SIIS permite administrarla y revocarla separadamente, pero no limita automáticamente sus usos dentro de los endpoints que admiten claves genéricas.

Referencias: [plan y criterios de aceptación](../plans/2026-T4/2026-10-06-autenticacion-siis.md) y [decisiones acordadas](../registro/decisiones/2026-10-06-auth-siis-accesos-independientes.md).
