# Cambio: gestión de comunicados en React sobre G1 v1 (#2785, CM02.01)

## Alcance

Segunda entrega del
[contrato CM01-CM03](../../../plans/2026-T4/2026-11-10-2785-comunicados-mailing-m2.md):
el listado de gestión `/comunicados/gestion/` y la variante de gestores del
detalle `/comunicados/ver/<pk>/` con su pie de acciones. Crear, editar, eliminar
y mailing masivo siguen en las pantallas nativas (los enlaces apuntan a ellas) y
el envío masivo sigue en el worker nativo; no se envía correo. No cambia vistas,
plantillas, modelos ni la API PWA (`/api/comunicados/`). No activa React en
producción.

Archivos:

- `src/backends/comedores/comunicados/web_api_views.py`,
  `web_api_serializers.py` y `web_api_urls.py`: endpoint nuevo
  `GET /api/web/comedores/comunicados/gestion/`; el detalle suma
  `fecha_creacion` y `modificado_por`. `src/backends/config/middlewares/admindocs.py`
  con la ruta nueva.
- `src/backends/comedores/comunicados/web_preview.py`: la entrada sirve React en
  la gestión y en el detalle para todos los perfiles.
- `src/frontends/apps/sisoc/src/routes/comunicados.tsx` (ruta ya registrada en
  `routes/index.ts`).
- Pruebas: `test_web_comunicados_gestion_api.py`, `test_web_preview_comunicados.py`,
  `test_web_comunicados_publicados_api.py` y `routes/comunicados.test.tsx`.

## Comportamiento

El endpoint ejecuta `ComunicadoGestionListView`: mismo `dispatch` (403 sin permiso
de gestión, también para anónimos en la vista previa), mismo queryset (el técnico
solo ve externos de su alcance), filtros `titulo`, `estado` y `tipo` exactos y sin
validar, 20 por página y 404 «Página no válida.». Cada fila trae las acciones ya
resueltas con las mismas condiciones de la plantilla. Acceso: G1 primero (401 sin
sesión) y después la guarda nativa. Solo GET y HEAD, sin escrituras.

Publicar, archivar y destacar son formularios POST nativos con token CSRF; los
botones piden la misma confirmación («¿Publicar este comunicado?», «¿Archivar este
comunicado?»). Los selects de estado y tipo reenvían el formulario al cambiar.

## Verificación

Entorno sintético, sin red, imagen fijada. Pruebas nuevas en verde por
interfaz pública (estado, JSON, permisos, mensajes, sin escrituras); Vitest del
proyecto, `tsc`, ESLint y build de Vite; `black` y `pylint`.

## Limitaciones

- Diferencia del marco compartido (`SisocShell`): el logo tiene nombre accesible
  en React y cambia el primer elemento del orden de Tab.
- Asimetría conservada: el detalle para gestores no aplica el alcance del técnico,
  igual que la página nativa.
