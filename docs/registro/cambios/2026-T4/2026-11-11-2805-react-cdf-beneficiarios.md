# Cambio: preinscripción, beneficiarios y responsables CDF en React sobre G1 v1 (#2805, CDF03)

## Alcance

Cuarta unidad CDF, apilada sobre la
[generación de usuario](2026-11-11-2805-react-cdf-centros-usuario.md), con dos
entregas del contrato
[CDF03/CDF04](../../../plans/2026-T4/2026-11-10-2785-cdf03-cdf04-contratos.md):

- CDF03.02, preinscripción (`/centrodefamilia/beneficiarios/nuevo/`): búsqueda
  por CUIL y de responsable por DNI (RENAPER) y alta combinada.
- CDF03.01, consulta: listados de beneficiarios
  (`/centrodefamilia/beneficiarios/beneficiarios/`) y de responsables
  (`/centrodefamilia/beneficiarios/responsables/`) y sus fichas.

No cambian las vistas, formularios, plantillas, el JavaScript nativo ni el CSV.
El único cambio nativo es una extracción sin cambio de comportamiento en
`src/backends/cdf/centrodefamilia/services/beneficiarios_service/impl.py`:
`procesar_preinscripcion` (separa el POST, procesa los dos formularios y limpia
la caché RENAPER) y `errores_preinscripcion`; la vista nativa sigue llamando a
`generar_respuesta`. No activa React en producción.

Archivos:

- `src/backends/cdf/centrodefamilia/web_api_beneficiarios.py` y
  `src/backends/cdf/centrodefamilia/web_api_beneficiarios_urls.py`, incluido en
  `src/backends/cdf/cdf_runtime/web_api_urls.py`.
- `src/backends/cdf/centrodefamilia/web_preview.py`: cinco entradas nuevas.
- `src/backends/config/middlewares/admindocs.py` y
  `src/backends/config/url_registry.json` (regenerado).
- `src/frontends/apps/sisoc/src/routes/`: `cdfBeneficiarios.tsx` (ruta única de
  CDF03, listado y ficha de beneficiarios), `cdfResponsables.tsx`,
  `cdfPreinscripcion.tsx`, `cdfDataTable.tsx` (buscador, tabla con columnas,
  paginación y tarjetas de ficha) y `cdfSelect2.tsx` (selector múltiple).
- Pruebas: `src/backends/cdf/tests/test_web_cdf_preinscripcion.py`,
  `src/backends/cdf/tests/test_preinscripcion_nativa.py`,
  `src/backends/cdf/tests/test_web_cdf_beneficiarios.py`,
  `src/frontends/apps/sisoc/src/routes/cdfPreinscripcion.test.tsx` y
  `src/frontends/apps/sisoc/src/routes/cdfBeneficiarios.test.tsx`.

## Comportamiento

| Ruta (`/api/web/cdf/`) | Comportamiento |
|---|---|
| `GET beneficiarios/preinscripcion/options/` | Los campos que dibuja `beneficiarios_form.html`, con los atributos que genera crispy y sus opciones (sin `creado_por`) |
| `GET beneficiarios/buscar-cuil/?cuil=` y `GET beneficiarios/buscar-responsable/?dni=&sexo=` | Corren las funciones nativas: mismo JSON, mismos textos y la misma caché `renaper_cache` en la sesión |
| `POST beneficiarios/preinscripcion/` | `procesar_preinscripcion`: 200 `{status, message, toast}`, 400 `{status, errors}` (vacío sin vínculo) o 500 «Error al guardar: …». No encola mensajes de Django |
| `GET beneficiarios/` | `BeneficiariosListView`: filtros, páginas exactas de 10 (página inválida o fuera de rango 404), columnas y `can_export` |
| `GET beneficiarios/exportar/disponible/` | `{exists, message}` con los filtros actuales; 403 sin rol de exportación ni SSE |
| `GET responsables/` | `ResponsableListView`: páginas NoCount de 10 (`count: null`), conteo de beneficiarios por ventana |
| `GET beneficiarios/<pk>/` y `GET responsables/<pk>/` | Fichas de las plantillas nativas; 404 si no existe o está dado de baja |

Acceso igual que hoy: sesión y requisitos web (G1), después `view_centro`. El
padrón de beneficiarios y responsables no tiene alcance por centro ni territorio
(D1, ver [brechas conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)).
Las respuestas son `private, no-store`.

Pantallas React: mismas piezas de `search_bar.html`, `data_table.html` (con
«Configurar columnas»), `pagination.html` y las tarjetas de `cdf.css`. El botón
«Exportar búsqueda» consulta `exportar/disponible/`: si no hay filas muestra
«No hay beneficiarios para exportar con el filtro aplicado.» sin navegar; si hay,
navega al CSV nativo con el orden local activo. La preinscripción reproduce
`centro_familia_beneficiarios.js` (máscara de CUIL, búsquedas, carga de
municipios y localidades, validaciones y textos); al confirmar muestra «Datos
cargados con éxito» y deja el formulario limpio, como la recarga nativa. Un 400
conserva la alerta nativa «Error al enviar los datos: Error en el servidor» y
además marca los errores de campo. Un 504 sin confirmar muestra «No se pudo
confirmar el resultado. Verificá el estado antes de reintentar.» y no reintenta.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada; RENAPER y la tabla
del padrón (no administrada) simulados.

- Backend: 20 pruebas nuevas en rojo sobre la unidad anterior y luego en verde;
  5 pruebas de la vista nativa que pasan igual antes y después de la extracción.
  Suite CDF, pruebas de G1 y del proxy, registro de URLs al día, colección
  completa sin errores, `black`, `pylint` 10/10 en los archivos nuevos (el
  servicio no suma avisos respecto de la base) y `makemigrations --check`.
- Frontend: pruebas de ruta en rojo (módulos inexistentes) y luego en verde
  (18); Vitest del proyecto sisoc (tres corridas), `tsc`, ESLint y build de Vite.
- Visual (regla S13), 13 estados (listados con y sin filtro y vacío, fichas,
  preinscripción inicial, CUIL existente, CUIL posible, actividad elegida y
  responsable encontrado) en 1440x900 y 390x844: diferencia perceptual 0 % y
  desvío 0 px; orden de Tab igual dentro del contenido.
- G1 de punta a punta (core y runtime CDF): listados, fichas, aviso de CSV vacío,
  preinscripción completa con la caché RENAPER a través del proxy (filas de
  beneficiario, responsable, vínculo y datos RENAPER creados) y sin mensajes
  pendientes después. Anónimo 401, sin CSRF 403, sin permiso 403, requisito
  pendiente 403 con `state`, página inválida e inexistente 404.

## Limitaciones

- Comportamientos nativos conservados por paridad y anotados como riesgo: si el
  beneficiario es inválido, el responsable nuevo ya quedó guardado; y un
  responsable dado de baja con el mismo DNI hace fallar el alta con 500 (la
  restricción única cuenta las bajas lógicas).
- Los 500 devuelven el texto de la excepción, como hoy.
- `cdfSelect2.tsx` repite la interacción de `duplasSelect2.tsx` con otras clases;
  unificarlos queda para un cambio aparte.
- Mismas diferencias del marco compartido que las unidades anteriores.
