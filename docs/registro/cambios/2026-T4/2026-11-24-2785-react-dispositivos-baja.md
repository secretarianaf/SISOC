# Cambio: confirmación de baja de Dispositivos en React (#2785, T5d)

## Qué cambia

- **URL canónica.** `/dispositivos/<pk>/eliminar` (sin barra final, como
  `dispositivos/urls.py`) sirve la pantalla React cuando la vertical
  `dispositivos` está activa en `REACT_VERTICALES_ACTIVAS` (por defecto `todas`).
  La entrada `DispositivoEliminarEntry` (`dispositivos/web_preview.py`) conserva el
  decorador nativo (`delete_dispositivo`) y la regla de objeto de
  `DispositivoDeleteView` (alcance territorial: 404 fuera de alcance o
  inexistente); recién después devuelve el `index.html` congelado.
- **Datos de pantalla.** `GET /api/web/dispositivos/<pk>/eliminar/`
  (`DispositivoEliminarWebView`, nombre `web_dispositivos_eliminar`) corre la misma
  guarda y el mismo `get_object` nativo y proyecta lo que muestra
  `dispositivos_confirm_delete.html`: id, nombre de la institución, destino de
  «Cancelar» (legajo del dispositivo) y mensajes pendientes. Solo lectura.
- **React.** `routes/dispositivoEliminar.tsx` dibuja la misma tarjeta
  («Confirmar eliminación», «¿Seguro que desea eliminar el dispositivo …?»,
  «Eliminar» y «Cancelar»). La confirmación es el formulario nativo: `POST` con
  `csrfmiddlewaretoken` a la misma URL canónica, enviado una sola vez por el
  navegador. La vista nativa borra, deja su mensaje («Dispositivo eliminado
  correctamente.» o el de registros asociados) y redirige como siempre.
- Se sumó la ruta al registro de URLs (`url_registry.json`, regenerado con
  `generar_registro_urls`) y al patrón de rutas web de `admindocs.py`.

## Por qué

Cierre de la migración a React con el mismo patrón de URLs (S2–S4): la baja de un
dispositivo era la única pantalla visible de Dispositivos que seguía en plantilla.

## Cómo funciona con React apagado

Sin `dispositivos` ni `todas` en `REACT_VERTICALES_ACTIVAS` la entrada no se monta
y la URL devuelve la plantilla nativa sin cambios. Con React activo, cualquier
método distinto de `GET`/`HEAD` llega a la vista nativa.

## Cómo se verificó

- Pytest (`test_web_dispositivos_eliminar.py`): índice servido solo a un usuario
  autorizado; denegaciones idénticas a las nativas (anónimo, sin permiso, solo
  ver/editar, fuera de alcance, inexistente) sin datos; `POST` nativo que borra y
  redirige al listado; `POST` denegado sin efecto; datos de pantalla con la misma
  guarda y alcance, solo lectura; flag activo sirve React y flag apagado conserva
  la plantilla; `HEAD` de admindocs no saltea la API.
- Vitest (`dispositivoEliminar.test.tsx`): ruta canónica exacta, datos
  proyectados, `POST` único con CSRF a la URL canónica, «Cancelar» al legajo,
  denegación y 404 sin datos ni reintentos. `tsc` y `eslint` sin errores.

## Límites

- No se probó en navegador real (pedido explícito de avanzar sin esa prueba).
- La pantalla no agrega permisos ni acciones: replica la plantilla nativa.
