# Cambio: confirmaciones de baja de CDI en React sobre sus URLs canónicas (#2785)

## Qué cambia

Las confirmaciones de baja lógica de Centro de Desarrollo Infantil se muestran en React en sus URLs de siempre:

| Pantalla | URL canónica | Cancelar | Redirección tras confirmar |
| --- | --- | --- | --- |
| Baja de centro | `/centrodeinfancia/eliminar/<pk>` | listado de centros | listado de centros con el mensaje nativo |
| Baja de registro de nómina | `/centrodeinfancia/<pk>/nomina/<pk2>/eliminar/` | nómina del centro | nómina del centro con el mensaje nativo |

La pantalla muestra lo mismo que `components/delete_confirm.html`: título, nombre del registro en mayúsculas, vista previa
de la cascada (totales y desglose por modelo), "Dar de baja" y "Cancelar". No hay campos para completar.

## Cómo funciona

- Entradas `centrodeinfancia.web_preview_bajas` (registradas en `REGISTRO["cdi"]`): heredan las vistas nativas de baja y usan
  el mismo decorador de permisos que `urls.py`. El GET resuelve el objeto con el alcance nativo y recién entonces sirve el
  `index.html` congelado; el POST sigue llegando a la vista nativa.
- API de sesión `centrodeinfancia.web_api_bajas` (`/api/web/cdi/centros/<pk>/eliminar/` y
  `/api/web/cdi/centros/<pk>/nomina/<pk2>/eliminar/`): mismo transporte que las observaciones (gate web, permiso de la URL,
  despacho nativo). El GET proyecta el contexto de confirmación; el POST hace la baja lógica nativa y devuelve la redirección.
- React (`routes/cdiBajas.tsx`) reutiliza el componente de confirmación de observaciones, envía un único POST con CSRF y, si
  el resultado no se confirma, avisa sin reintentar.
- Con `REACT_VERTICALES_ACTIVAS` sin `cdi` (o `ninguna`), las páginas nativas quedan exactamente como antes.

## Cómo se verificó

- `tests/test_web_bajas.py`: proyección, baja lógica con mensaje y redirección, permiso, alcance, nómina de otro centro,
  veto de Auditoría, gate (anónimo y requisito pendiente), formato del POST y HEAD de admindocs; los rechazos no cambian datos.
- `tests/test_web_preview_bajas.py`: índice React solo con permiso y alcance, guardas nativas, POST nativo y URLconf sin
  React con los templates nativos.
- `cdiBajas.test.tsx`: rutas propias, render, POST único con CSRF, rechazo nativo, resultado incierto sin reintento y 404.
- `url_registry.json` regenerado con `generar_registro_urls`: suma solo `centrodeinfancia_web_centro_eliminar` y
  `centrodeinfancia_web_nomina_eliminar`.

## Limitaciones

- No se probó en navegador real (pedido del usuario: avanzar sin esa prueba).
