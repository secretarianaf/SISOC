# Inspecciones escolares: sección de usuarios y backend de la PWA

Fecha: 2026-10-14. Rama: `feat/inspecciones-escolares`. Decisión:
`docs/registro/decisiones/2026-10-14-inspecciones-escolares-backend.md`.

## Qué cambia

### Usuarios (kernel + core)

- `Profile.es_inspector_escolar` y `Profile.inspecciones_rol`
  (`inspector` | `coordinacion`), migración `users.0061`.
- ABM de usuarios: tarjeta "Inspecciones escolares" con el check y el rol, en
  alta y edición, habilitada por el permiso de sección
  `auth.role_usuarios_seccion_inspecciones_escolares`. La migración lo otorga
  a quien ya tenía la sección de administración de accesos; el grupo bootstrap
  de administración también lo recibe.
- El inspector se crea sin acceso SISOC web ni backoffice (usuario sólo de la
  app); coordinación conserva el acceso web.
- `GET /api/users/me/` expone `profile.es_inspector_escolar` (bool) y
  `profile.inspecciones_rol` (`"inspector"`, `"coordinacion"` o `""`).
  `pwa.must_change_password` funciona igual que para Gestionar.
  `pwa.is_pwa_user` sigue siendo `false` para estos usuarios, igual que para el
  territorial de Gestionar: la app debe decidir por el flag y el rol.
- `POST /api/users/login/` acepta a los usuarios del programa con rol válido.
- Importador de usuarios (XLSX existente): columnas opcionales `DNI` e
  `Inspecciones` (`inspector` / `coordinacion`). Con `Inspecciones`, DNI (sólo
  dígitos) y correo son obligatorios; un DNI o correo ya registrado se rechaza
  con su causa (nunca se pisa un usuario). Genera contraseña temporal con cambio
  obligatorio, como el resto de las altas.

### Backend `inspecciones` (vertical nuevo)

- Registro en `src/backends/config/backends.json`, servicio
  `backend_inspecciones` en `docker/compose/docker-compose.deploy.yml`
  (`BACKEND_INSPECCIONES_WORKERS`, por defecto 4), `pytest.ini`,
  `.importlinter` y `src/backends/config/url_registry.json`.
- Modelos: `Escuela`, `AsignacionEscuela`, `Inspeccion`, `ImagenInspeccion`,
  `SecuenciaActa`, `Acta`, `NotificacionPapel`, `ArchivoNotificacion`,
  `EventoInspeccion`.
- API `/api/inspecciones/` según el contrato de la PWA (ver abajo las
  diferencias). Token DRF; sólo usuarios del programa.
- Backoffice `/inspecciones/`: totales del día e importación CSV de escuelas y
  de asignaciones por jornada (filas nuevas, actualizadas, sin cambios y
  rechazadas con causa). Acceso: rol coordinación o permiso
  `inspecciones.gestionar_inspecciones`. Entrada en el menú lateral.
  El admin de Django registra los modelos (catálogo editable, actas de sólo
  lectura), disponible en la composición completa.
- CORS: `PWA_CORS_ALLOWED_ORIGINS` (lista separada por comas) suma orígenes de
  PWA servidas fuera del dominio de SISOC, sólo para CORS. Publicada bajo
  `/pwa/<app>/` del mismo dominio, como Gestionar, no hace falta.

## Diferencias con el contrato de la PWA

| Tema | Contrato | Implementado | Motivo |
| --- | --- | --- | --- |
| Flag y rol en `/me/` | pendiente | `profile.es_inspector_escolar` + `profile.inspecciones_rol` | Mismo patrón que DataCalle. La app hoy deduce el rol de `profile.rol`, que es texto libre descriptivo: debe usar `inspecciones_rol`. |
| `GET /actas/` | actas propias | propias; coordinación agrega `?alcance=todas` | "Mis actas" no se mezcla; coordinación ve todo a pedido. |
| Fotos de la notificación | sin endpoint | `GET /api/inspecciones/notificaciones/archivos/<uuid>/` y `archivos_ids` en el detalle | La especificación pide que coordinación las vea y descargue. |
| Detalle del acta | instantánea, eventos, notificaciones | además `formulario`, `instantanea_sha256`, `eventos[].codigo`, `notificaciones[].version`, `cargada_por`; `imagenes[]` con `sha256` y `subida_at`; resumen con `inspector` y `es_prueba` | Aditivo. |
| `f15` | clave de `respuestas` | se acepta en `respuestas.f15` o en la raíz (la app lo manda en la raíz) | Compatibilidad con `payload.ts`. |
| Errores de validación | 400 con detalle | 400 `{"detail", "errores": {"respuestas.f09": "..."}}`; imágenes faltantes con `faltantes: [uuid]` | Rutas del cable para marcar campos. |
| Archivo inválido | 422 sólo para >10 adicionales | 422 también para tipo no JPEG/PNG, >10 MB y PDF inválido | Igual que el backend simulado. |
| Cierre con revisión vieja | no definido | 409 si la `revision` del cuerpo es menor que la guardada | No cerrar con un estado anterior al del servidor. |
| `DELETE` repetido o inexistente | 204 | 204 (idempotente); sobre finalizada, 409 | |
| Escritura de coordinación sobre lo ajeno | no definido | 404 | Coordinación consulta, no modifica (especificación §2). |
| Búsqueda con menos de 3 caracteres | mínimo 3 | 200 con `[]`; también busca por localidad | Igual que el backend simulado. |
| `id` de escuela | `"esc-1001"` | `Escuela.codigo` (por defecto, el CUE) | El catálogo real no está definido. |
| `firma.hash_contenido` | se guarda y puede recalcularse | se guarda, no se recalcula | Se calcula sobre el modelo interno de la app. |
| Status de éxito | no siempre explícito | `PUT` borrador/imagen/PDF, `POST` finalizar y notificaciones: 200 | El reintento devuelve lo mismo que la primera vez. |

## Operación y despliegue

- **Antes de habilitar**: agregar en el Nginx de cada host
  `location ^~ /media/inspecciones/ { return 404; }` (ya documentado en
  `docs/operacion/nginx/sisoc-produccion.conf` y en los runbooks de QA y
  entornos). Sin eso las evidencias quedan servidas por `/media/`.
- El cambio toca kernel y config: el plan de deploy es **completo** y requiere
  construir la imagen `sisoc/backend-inspecciones` y correr el migrador
  (`users.0061`, `inspecciones.0001`).
- QA tiene `client_max_body_size 50m`: una notificación con 5 fotos de 10 MB
  queda en el límite. PRD tiene 500M.
- Cargar el catálogo y las asignaciones desde `/inspecciones/` y dar de alta a
  los inspectores con el ABM o el importador de usuarios.

## Validación

Tests en `src/backends/inspecciones/tests/` (API, validación, cierre,
importación y concurrencia `mysql_compat`) y
`src/backends/sisoc_core/tests/test_users_inspecciones_escolares.py`.
