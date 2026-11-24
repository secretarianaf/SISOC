# Cambio: aportes de Ciudadano 360 en React (#2785, C04 con la parte de C05.01 que necesita)

## Qué cambia

- **C05.01 (parte mínima, dueño kernel).** `GET /api/web/ciudadanos/<pk>/`
  (`ciudadanos/web_api.py`, montado en el core antes de `api/web/`) entrega el
  encabezado de la ficha y la lista `aportes` con rutas armadas en el servidor
  (`aportes_web_de_ciudadano`). Mismo permiso (`ciudadanos.view_ciudadano`) y mismo
  404 que `CiudadanosDetailView`. La ruta React `ciudadano360.tsx` dibuja el
  encabezado y el lugar de cada tarjeta; el resto de la ficha (pestañas, familia,
  programas, interacciones y acciones) sigue en Django. La entrada
  `ciudadanos/web_preview.py` solo existe como vista previa local y no se monta en
  ningún URLconf de producción.
- **C04.01.** `GET /api/web/<backend>/ciudadanos/<pk>/aportes/<aporte>/`
  (`ciudadanos/web_aportes.py`, vista genérica del kernel) para `comedores`,
  `pwa`, `celiaquia`, `vat` y `centrodefamilia`. Cada dueño separa una función de
  consulta que propaga la excepción y registra su proyector
  (`registrar_proyector_aporte`); `obtener_contexto` del fragmento HTML la envuelve
  con el mismo `try` de antes y conserva su salida. Un proveedor que falla responde
  503 `aporte_no_disponible`; un aporte no registrado o de otro backend, 404.
  Se agregó el prefijo `api/web/celiaquia/` (`celiaquia_runtime/web_api_urls.py` y
  `backends.json`) y se regeneró `url_registry.json`.
- **C04.02.** `ciudadano360Aportes.tsx` con un renderer por sección y la
  disponibilidad C2: «No disponible» solo donde el template muestra el valor o el
  texto vacío; PWA nunca dice «No» si cayó el proveedor; colaboraciones no se
  dibujan en fallo. Cada aporte se pide en paralelo y una tarjeta no espera a otra.
  Enlaces a las rutas Django nativas.

## Cómo se verificó

- Pytest aislado (imagen fijada, sin red): 14 pruebas del kernel (lista, vista,
  G1, 401/403/404/503, caché), 1 de la vista previa y las de cada dueño
  (comedores y PWA, CDF, Celiaquía, VAT) con datos sintéticos, incluido el
  diferencial de `total_texto` contra el template nativo.
- Vitest: 22 pruebas nuevas; tsc y eslint sin avisos.
- G1 (core y runtime con gunicorn): 401 anónimo, 403 sin permiso y con requisito
  pendiente, cabecera G1 falsificada ignorada, POST sin CSRF 403 y camino feliz.
- Visual S13, escritorio y móvil, con datos y vacío: 0 % de diferencia perceptual y
  geometría dentro de 0,07 px. La referencia nativa es un anfitrión de laboratorio
  que arma los fragmentos reales en el mismo orden que dibuja React, porque la
  ficha completa todavía no se migró.

## Limitaciones y diferencias conocidas

- Los estados «No disponible» (C2) no se comparan visualmente con el nativo: es la
  excepción aprobada.
- Los fragmentos de Celiaquía, Centro de Familia y VAT usan un comentario
  `{# ... #}` de varias líneas que Django no interpreta: el HTML nativo muestra ese
  texto. React no lo reproduce; conviene corregir esas plantillas
  (`{% comment %}`) en un cambio aparte.
- La ficha React aún no reemplaza a la nativa: falta el resto de C05.01.
