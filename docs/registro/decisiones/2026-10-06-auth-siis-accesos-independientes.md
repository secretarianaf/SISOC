# SIIS: identidad compartida y habilitaciones independientes

Estado: diseño y límites aprobados; alineación cerrada por el usuario el 2026-10-06. Implementación pendiente.

SISOC será la fuente de identidad y habilitación de SIIS, mientras SIIS administra sus roles y sesiones. Una misma cuenta puede tener accesos independientes a varias aplicaciones y a SISOC web. El indicador web explícito reemplazará el acceso inferido por rol o aplicación, preservando los accesos existentes aprobados, incluidos coordinadores y administradores de DataCalle. Las habilitaciones se administran exclusivamente desde SISOC; SIIS ofrece login y alta de cuentas nuevas, inicialmente habilitadas solo para SIIS.

El usuario aprobó identificar el login SIIS mediante `app: "siis"` y conservar el payload y la respuesta de los clientes actuales sin ese campo. La alternativa de exigir identificación de aplicación a todos los consumidores se descartó porque el usuario no quiere obligarlos a cambiar ahora. Queda una diferencia deliberada entre el contrato legacy y SIIS, que deberá contemplarse si se versiona el contrato en el futuro.

Para las altas se eligió la recomendación del agente de validar, además de la API key, un token firmado del administrador obtenido mediante autenticación administrativa separada. SISOC comprueba cuenta activa, habilitación y `auth.add_user` en cada alta. El usuario aceptó un vencimiento de una hora, sin renovación automática ni revocación individual, a cambio de evitar una tabla de tokens. Se presentaron como alternativas un token almacenado con revocación individual, credenciales del administrador en cada alta y confiar en la identidad declarada por SIIS.

El usuario decidió reutilizar la herramienta existente de API keys y aceptar cualquier clave válida, descartando el aislamiento por integración mediante un modelo nuevo. Las claves se pueden revocar desde SISOC sin despliegue. Esta decisión no sustituye la autorización personal del administrador.

El usuario excluyó expresamente proteger la unicidad de DNI/email frente a altas concurrentes; se comprobarán duplicados, conservando la unicidad existente de username, pero se acepta esa posibilidad de duplicación simultánea. Retirar el acceso SIIS bloquea nuevos logins y altas administrativas, sin cerrar las sesiones ordinarias que SIIS ya mantenga abiertas.

El usuario también decidió que el canal SIIS no rechace login ni emisión administrativa por cambio obligatorio pendiente o vencimiento de una contraseña temporal. Se conservan esos flags para los demás flujos y se comprueban contraseña vigente, cuenta activa, habilitación SIIS y permiso administrativo cuando corresponde. Se acepta que una contraseña temporal aún vigente pueda servir para SIIS aunque haya vencido en otros canales; no se modifica la política de esos otros canales.

El [plan de alineación](../../plans/2026-T4/2026-10-06-autenticacion-siis.md) contiene los criterios, límites y detalles técnicos del diseño aprobado. No se decidió adoptar LDAP, Active Directory, SSO ni federación de identidad.
