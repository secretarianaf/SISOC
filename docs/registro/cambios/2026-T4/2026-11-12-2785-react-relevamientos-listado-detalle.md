# Cambio: listado y detalle de relevamientos en React sobre G1 v1 (#2785, R01.01)

## Alcance

Primera entrega del
[contrato R01-R03](../../../plans/2026-T4/2026-11-10-2785-relevamientos-seguimientos-actas-m2.md):
el listado `/comedores/<comedor_pk>/relevamiento/listar` (relevamientos con sus
seguimientos, actas complementarias y seguimientos PNUD) y el detalle
`/comedores/<comedor_pk>/relevamiento/<pk>`. Las altas, ediciones, revisiones y
bajas siguen siendo los POST nativos; la sincronización asincrónica con GESTIONAR
sigue en el código nativo. No cambia vistas, plantillas, modelos ni la API de la
app territorial. No activa React en producción.

Archivos (todos dentro de `src/backends/comedores/relevamientos/` salvo aviso):

- `web_api_views.py`, `web_api_serializers.py`, `web_api_urls.py`: dos endpoints
  `GET` nuevos bajo `/api/web/comedores/relevamientos/`, incluidos desde
  `comedores_runtime/web_api_urls.py`; `config/url_registry.json` regenerado con
  `generar_registro_urls` y `config/middlewares/admindocs.py` con la ruta nueva.
- `web_preview.py`: entrada React sin montar (`relevamientos_preview_patterns`).
- `src/frontends/apps/sisoc/src/routes/relevamientos.tsx`, registrado en
  `routes/index.ts`.
- Pruebas: `tests/test_web_relevamientos_api.py`,
  `tests/test_web_preview_relevamientos.py` y `routes/relevamientos.test.tsx`.

## Comportamiento

Cada endpoint instancia la vista nativa (`setup()` y `get_context_data()`) y
proyecta su contexto: mismo orden `-estado, -id`, seguimientos por `numero_orden`,
mismo 404 (comedor inexistente; relevamiento inexistente o dado de baja) y
fechas impresas por el motor de plantillas. Las secciones de datos del detalle
se obtienen renderizando `relevamiento_detail_secciones.html` con el contexto
nativo y leyendo sus títulos, etiquetas y valores, de modo que no puedan
desalinearse de la plantilla que sigue alimentando el PDF.

Acceso (sin cambios, ver
[brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)):
G1 primero (401 sin sesión, 403 con `state` si hay un requisito pendiente);
después superusuario o `relevamientos.view_relevamiento`, sin alcance por
usuario. El detalle busca solo por `pk` e ignora `comedor_pk`, como la vista
nativa. Los botones salen de los permisos Django, como `perms.*` en la
plantilla. Solo GET y HEAD; la lectura no escribe.

Los modales («Nuevo acompañamiento territorial», «Agregar seguimiento»,
«Asignar territorial», «Revisión del coordinador» y la baja de seguimiento)
envían un formulario nativo con `csrfmiddlewaretoken` a las mismas URL de hoy;
la lista de territoriales se lee de `/comedores/<id>/territoriales/`.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: pruebas nuevas (19 de API y 3 de vista previa) en rojo y luego en
  verde; app `relevamientos`, `test_web_gate`, `test_backend_proxy` y
  `test_servicios_backends` (con el registro regenerado), `black` y `pylint`
  10/10.
- Frontend: Vitest del proyecto completo, `tsc`, ESLint y build de Vite.
- G1 de punta a punta (core y runtime con gunicorn): lista y detalle desde el
  navegador sin errores; anónimo 401, sin permiso 403, requisito pendiente 403
  con `state`, header falsificado ignorado, POST sin CSRF 403, comedor
  inexistente 404.

- Visual (S13), 6 estados (lista, lista como lector, detalle finalizado, detalle
  pendiente, modal de alta, modal con error de validación) en 1440x900 y 390x844:
  contenido, estilos y orden de elementos iguales, desvío máximo 0,03 px y
  0,000 % de píxeles distintos; orden de Tab igual salvo el nombre accesible del
  logo del marco compartido (exento). Anónimo (403), comedor y relevamiento
  inexistentes (404) responden igual.

## Limitaciones

- Seguimiento: `SisocShell` tipa `heading` como texto; el cabezal del detalle y
  del listado pasa nodos con un cast de tipo (decisión aceptada, a resolver al
  tipar `heading` como nodo en el marco compartido).
- El carrusel de fotos replica `data-bs-ride` (avance cada 5 s, pausa al pasar
  el mouse o enfocar, controles e indicadores) sin la animación de deslizamiento
  (la comparación visual usa `reducedMotion`).
- La autocompletación de territoriales replica el script nativo: lista, filtro,
  selección exacta, línea de estado, botón «Sincronizar con GESTIONAR», recarga
  tras 10 minutos, estados de carga y avisos.
- Las secciones del detalle viajan como árbol de elementos permitidos (etiquetas
  y atributos de una lista blanca, sin scripts), tomado del parcial nativo; el
  colapso de tarjetas (`data-card-widget`) se reimplementa en React.
