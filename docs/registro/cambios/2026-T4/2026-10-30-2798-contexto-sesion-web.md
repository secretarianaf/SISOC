# Cambio: contexto de sesión web del core (#2798, #2785)

## Alcance

Se implementa GET/HEAD `/api/web/session/`, propiedad de `usuarios` en el core.
Fuentes: `usuarios/web_context.py`, `web_api_views.py`, `web_api_serializers.py`
y `web_api_urls.py` bajo `src/backends/sisoc_core/`. Se reutilizan el resolver
de requisitos y la proyección de navegación ya registrados. Evidencia del piloto
original; guía: `docs/implementaciones/frontend_v2.md`.

## Comportamiento

- Sesión Django exclusivamente. Token/Bearer/API key sin cookie no autentican
  esta ruta; una cabecera de otro usuario no sustituye la identidad de la cookie.
- Anónimo o inactivo: 401 JSON sin redirect, con challenge `Session`. Una sesión
  activa recibe identidad mínima, requisito prioritario, navegación, capacidades
  de Insumos y etiqueta del footer existente. No se emiten/borran tokens.
- Identidad limitada a username, nombre visible, inicial de username y etiqueta
  de rol. No se serializan email, DNI, IDs, grupos ni listas de permisos.
- Acceso web denegado: identidad nula. Contraseña, perfil o encuesta obligatoria
  pendientes conservan su prioridad y rutas existentes. En cualquier estado no
  listo, menú vacío y las tres capacidades de negocio falsas.
- La capacidad de gestión usa AddInsumo y categorías usa AddInsumoCategoria,
  independientemente de ViewInsumo. No agregan permisos de edición/eliminación ni
  autorizan acciones. Cada futura API de negocio debe reevaluar sus controles.
- Respuestas privadas, no-store y Vary Cookie; inicialización de cookie CSRF sin
  incluir el token en JSON. Mutaciones no admitidas; con CSRF válido responden 405.
- Dependencias necesarias fallidas se propagan, nunca se responde ready por
  defecto. GET no crea perfiles ni escribe datos de negocio.

El schema se deriva de serializers reales, con navegación recursiva y salida
whitelist. Su ajuste local elimina la alternativa ApiKeyAuth añadida por la
configuración global, sin cambiar el esquema ni autenticación de otras APIs.
No es el contrato de login/PWA y no modifica sus consumidores.

## Compatibilidad HEAD autorizada

El middleware Django admindocs respondía HEAD interno/staff con 200/X-View antes
de ejecutar esta vista. El responsable autorizó una excepción sólo para HEAD
`/api/web/session/`. `config.middlewares.admindocs.WebSessionXViewMiddleware`
delega al padre para cualquier otro path/método, en el mismo lugar del stack.
Vive en config, disponible también en imágenes aisladas, no en una app del core
que falte en los verticales. No cambia pantallas ni permisos admin/Unfold #2789.

Se regenera `src/backends/config/url_registry.json` con el comando existente:
una entrada web_session, sin prefijo proxy ni backend nuevo.

## Verificación

- RED de HTTP: ruta ausente 404; después, HEAD interceptado con 200; contexto de
  sesión autenticada sin handler 405. Los casos quedan fijados en tests.
- RED del schema: anunciaba ApiKeyAuth; corregido localmente y comprobado contra
  la generación real de OpenAPI, no contra el documento propuesto.
- Focal final: 31 pruebas aprobadas, 97,96% combinado en los cuatro módulos
  medidos; middleware y serializers 100%.
- Suite serial ampliada: 190 aprobadas. Incluye API, requisitos, navegación,
  autenticación/PWA, encuestas, sidebar, tableros/footer, registro actualizado de
  URLs y arranque core sin apps de verticales.
- Black: ocho archivos conformes. Pylint: cinco módulos de aplicación, 10/10.
  DTOs de sólo salida siguen la convención INET para métodos create/update no
  soportados; no se inventan métodos de persistencia para satisfacer lint.
- Aislamiento local: imagen existente, sin red, `env -i`, dotenv deshabilitado,
  repositorio readonly y DB/storage/logs/cache de prueba sintéticos/temporales.
- Verificación independiente: 128 pruebas aprobadas (31 existentes y 97 probes).
  Incluye 96 comparaciones diferenciales de middleware contra Django para otros
  paths/métodos/actores y un recorrido HTTP OPTIONS, rechazo de mutaciones, Allow
  y sesión terminada. Hash del dump SQLite completo sin cambios en solicitudes
  rechazadas y OPTIONS. Sin bloqueantes. CI y revisión nativa separados.

## Límites y reversión

No hay frontend INS-A, servidor visual, baseline aceptado ni diff de píxeles.
T3–T7 permanecen pendientes. No se activó navegación pública, publicó, mergeó o
desplegó. La reversión retira la ruta, el adapter y su entrada de registro y
restaura el middleware padre; no revierte datos ni permisos de usuarios.

Riesgo: items 2/5, sesión y configuración compartida. Requiere revisión técnica.
