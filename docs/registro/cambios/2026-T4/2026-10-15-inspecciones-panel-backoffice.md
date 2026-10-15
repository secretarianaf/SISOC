# Inspecciones escolares: panel del backoffice (escuelas, asignaciones y actas)

Fecha: 2026-10-15. Rama: `feat/inspecciones-panel-backoffice`. Antecedente:
`docs/registro/cambios/2026-T4/2026-10-14-inspecciones-escolares-backend.md`.

El panel `/inspecciones/` pasa de dos formularios CSV a tres pestañas
(Escuelas, Asignaciones y Actas) con los totales arriba. El acceso no cambia:
`users.services_inspecciones.puede_gestionar_inspecciones` (coordinación,
permiso `inspecciones.gestionar_inspecciones` o superusuario). Todas las
vistas nuevas, incluidas las de imágenes, PDF y búsquedas AJAX, responden 403
sin ese permiso.

## Modelo `Escuela` (migración `inspecciones.0002`)

- Campos nuevos: `provincia` (FK `core.Provincia`, `PROTECT`),
  `localidad_vinculada` (FK `core.Localidad`, `SET_NULL`, nula si no se pudo
  resolver), `cp`, `telefono`, `mail` (texto: la importación guarda el mail
  inválido tal cual), `jurisdiccion_original`, `localidad_original`,
  `a_revisar` (indexado) y `motivos_revision` (lista JSON con
  `localidad_repetida`, `localidad_inexistente` y `mail_invalido`). Índice por
  `nombre` para el listado paginado.
- **Cueanexo**: no hay columna nueva. Las escuelas nuevas guardan el Cueanexo
  (9 dígitos, texto, con ceros) en `codigo`, que ya era único y es el `id` de
  la API, y en `cue`, que la API expone como `cue`. `codigo` no cambia después
  del alta (la app lo guarda en sus borradores): si se corrige el Cueanexo de
  una escuela, cambia `cue`. La unicidad la dan `codigo` (constraint) y el
  control de alta e importación, que busca el Cueanexo en `codigo` y en `cue`.
  `Escuela.cueanexo` devuelve `cue` o, si está vacío, `codigo`.
- `localidad` (ahora de 255) y `distrito` siguen siendo texto: es lo que lee
  la PWA. Con localidad vinculada son el nombre de la localidad y el de su
  municipio; sin vínculo, el texto original y el distrito que ya tenía. La
  localidad genérica de CABA pertenece en la base a una comuna puntual: para
  ella el distrito es "Ciudad Autónoma de Buenos Aires", no esa comuna.
- **Datos existentes**: la migración copia `localidad` a `localidad_original`
  y deja `provincia` y `localidad_vinculada` vacías y `a_revisar` en falso. Ni
  `codigo` ni `cue` cambian. Al reimportar el padrón, cada escuela se encuentra
  por Cueanexo (en `codigo` o `cue`), se completa y conserva su `codigo`.

## Pestaña Escuelas

- Listado paginado del lado del servidor (25 por página) con buscador por
  nombre, Cueanexo (por prefijo) o domicilio, filtros Provincia → Localidad
  (Select2 AJAX dependiente de la provincia) y chip "A revisar" con contador.
- Alta y edición en el mismo modal: Provincia → Localidad (Select2 con
  "Localidad · Municipio"), Cueanexo (9 dígitos), Nombre, Domicilio, C. P.
  (admite CPA, `B1754ABC`), Teléfono y Mail (validado como email). Un Cueanexo
  existente se avisa en el campo con el link "Abrir para editar" (abre el modal
  de esa escuela con `?editar=<id>`). Botones "Guardar escuela" y "Guardar y
  cargar otra". Guardar con localidad de la lista y mail válido quita la marca
  "a revisar".

## Importación del padrón en tres pasos (archivo → revisión → resultado)

- `.xlsx` (sólo la primera hoja; las demás no se abren) o `.csv`, hasta 25 MB,
  con las columnas `Jurisdicción, Localidad, Cueanexo, Nombre, Domicilio,
  C. P., Teléfono, Mail`. El encabezado se busca entre las primeras 30 filas.
- Rechazos: sólo filas sin Cueanexo válido, sin Nombre o con jurisdicción
  desconocida. Un Cueanexo repetido dentro del mismo archivo se informa como
  rechazo de la segunda fila (no puede haber dos escuelas con la misma clave).
  Un Cueanexo de una celda numérica del Excel recupera sus ceros; en texto
  tiene que tener 9 dígitos.
- Provincias: "Ciudad de Buenos Aires" → "Ciudad Autónoma de Buenos Aires" y
  "Tierra del Fuego" → "Tierra del Fuego, Antártida e Islas del Atlántico Sur";
  las demás por nombre normalizado.
- Localidad: dentro de la provincia, sin tildes, sin mayúsculas y con espacios
  colapsados. Una coincidencia se vincula; varias o ninguna dejan la FK nula y
  la escuela "a revisar" con el texto original. En CABA, "CIUDAD DE BUENOS
  AIRES" se vincula a la localidad genérica "Ciudad Autónoma de Buenos Aires".
  Si una escuela ya tenía una localidad vinculada (por ejemplo, corregida a
  mano) y el archivo trae el mismo texto original, se conserva.
- Mail: uno o varios (separados por `/`, `;`, `,` o espacios); si alguno es
  inválido se guarda igual y la escuela queda "a revisar".
- La revisión muestra columnas reconocidas, nuevas, actualizadas, a revisar
  (con desglose por motivo), sin cambios, rechazadas, equivalencias de
  provincia aplicadas y las primeras 50 observaciones, y permite descargar
  todas en CSV. Nada se escribe hasta confirmar.
- Entre la revisión y la confirmación, el archivo, el análisis y las filas
  normalizadas quedan en `MEDIA_ROOT/inspecciones/importaciones/<tipo>/<token>/`
  (almacenamiento privado sin URL; el Nginx ya bloquea `/media/inspecciones/`).
  El token es del usuario que subió el archivo. Se borra al confirmar o
  cancelar; lo abandonado se limpia a las 24 horas, en la siguiente subida.
- La confirmación vuelve a clasificar las filas normalizadas contra la base
  actual (no relee el `.xlsx`) y guarda con un `INSERT` múltiple que actualiza
  por `codigo` (`ON DUPLICATE KEY UPDATE` en MySQL), en lotes de 1.000.

### Medición con el padrón real (64.495 filas, 6 MB)

Local: Docker Desktop en Windows, MySQL 8.4 en contenedor (buffer pool por
defecto de 128 MB), con el fixture `core/fixtures/localidad_municipio_provincia.json`
y por las vistas del panel (cliente de pruebas de Django, proceso ya iniciado):

| Paso | Catálogo vacío | Reimportación del mismo archivo |
| --- | --- | --- |
| Revisión (subida + lectura + análisis + guardado) | 6,6 s | 7,5 s |
| Confirmación | 5,9 s | 2,4 s |

Resultado: 64.495 nuevas (52.556 sin observaciones y 11.939 a revisar), 0
rechazadas. Motivos: 6.196 localidades en 2 o más municipios, 5.094
localidades que no están en la base y 771 mails inválidos (122 escuelas
tienen dos motivos). 53.205 escuelas (82,5 %) quedaron con localidad
vinculada. Con la base de producción, la referencia previa era 82 % / 10,5 %
/ 7,2 %. La reimportación del mismo archivo da 0 nuevas y 0 actualizadas.

Los tiempos entran en el `timeout` por defecto de Gunicorn (30 s), con margen.
La primera versión, con `bulk_create`/`bulk_update` y releyendo el `.xlsx` al
confirmar, tardaba más de un minuto en confirmar.

## Pestaña Asignaciones

- Listado por jornada (anterior / siguiente / hoy) con filtros por inspector,
  provincia, estado de la visita y estado del acta; totales de la jornada.
- Estado: pendiente, en curso (hay borrador con datos de esa jornada) o
  finalizada (hay acta no anulada, con link al detalle). Las actas anuladas y
  de prueba se muestran con su chip. "Finalizadas" en los totales excluye las
  anuladas y las de prueba.
- Quitar (borrado lógico) sólo si la visita no tiene acta, ni siquiera anulada.
- Alta en un modal: Jornada (hoy por defecto), Inspector (Select2 AJAX desde 3
  letras: usuario, nombre, apellido o DNI; sólo `es_inspector_escolar` con rol
  inspector) y Escuela (Select2 AJAX desde 3 letras: nombre, Cueanexo o
  domicilio, hasta 20, con Cueanexo y localidad). Si la escuela ya está
  asignada ese día a otro inspector se avisa y se permite (otra visita). Al
  mismo inspector, no: la restricción única `escuela + inspector + fecha` no
  cambia. Botones "Asignar" y "Asignar y cargar otra".
- Importación con el mismo flujo de tres pasos: columnas `fecha`
  (AAAA-MM-DD, DD/MM/AAAA o fecha de Excel), `cueanexo` e `inspector`
  (usuario, DNI o mail). **Cambio**: el inspector tiene que tener rol
  inspector (antes alcanzaba cualquier rol del programa), igual que en el alta.

## Pestaña Actas

- Listado paginado con filtros por fecha de visita, inspector, provincia y
  estado (todas, válidas, anuladas, de prueba). Columnas: número, escuela,
  provincia/localidad, turno, inspector, fecha y hora, firma
  (firmada/excepción), notificación (pendiente/cargada), chips "Anulada" y
  "Prueba".
- Detalle: encabezado con número, estados y "Descargar PDF"; resumen (abierta,
  resultado, personal presente/previsto, aulas funcionando/previstas); las
  respuestas F00–F16 con etiquetas y justificaciones, desde la instantánea del
  acta y su versión de formulario; evidencia con miniaturas, descripción y
  horarios; notificación en papel con sus fotos (y versiones anteriores);
  visita, escuela, ubicación (coordenadas, precisión, link a OpenStreetMap),
  recepción (firma en pantalla o excepción con motivo) e historial.
- Imágenes, firma, fotos de la notificación y PDF se sirven por vistas del
  panel (`/inspecciones/actas/<numero>/…`) con sesión y permiso,
  `Cache-Control: private, no-store`, sólo si pertenecen a esa acta.
- Anulación y marca de prueba: el detalle muestra los botones si existen las
  rutas `inspecciones_anular_acta` e `inspecciones_marcar_prueba_acta` (rama
  `feat/inspecciones-anulacion`); un acta anulada muestra el aviso con fecha,
  quién y motivo, y oculta los dos botones.

## Totales del panel

Escuelas en el catálogo, escuelas a revisar, asignaciones de hoy y actas
cerradas hoy. Las actas anuladas y las de prueba no cuentan.

## Rutas nuevas (`/inspecciones/`)

| Ruta | Nombre |
| --- | --- |
| `` (Escuelas) | `inspecciones_panel` |
| `escuelas/nueva/`, `escuelas/<id>/editar/` | `inspecciones_escuela_nueva`, `inspecciones_escuela_editar` |
| `escuelas/importar/` y `escuelas/importar/<token>/[confirmar/ · cancelar/ · observaciones.csv]` | `inspecciones_importar_escuelas[_revision · _confirmar · _cancelar · _observaciones]` |
| `asignaciones/`, `asignaciones/nueva/`, `asignaciones/<id>/quitar/` | `inspecciones_asignaciones`, `inspecciones_asignacion_nueva`, `inspecciones_asignacion_quitar` |
| `asignaciones/importar/…` | `inspecciones_importar_asignaciones[…]` |
| `actas/`, `actas/<numero>/`, `actas/<numero>/pdf/` | `inspecciones_actas`, `inspecciones_acta_detalle`, `inspecciones_acta_pdf` |
| `actas/<numero>/imagenes/<uuid>/`, `actas/<numero>/notificaciones/<uuid>/` | `inspecciones_acta_imagen`, `inspecciones_acta_notificacion_archivo` |
| `ajax/localidades/`, `ajax/inspectores/`, `ajax/escuelas/`, `ajax/asignaciones/verificar/` | `inspecciones_ajax_*` |

## PWA

`/api/inspecciones/escuelas/…` devuelve los mismos campos (`id`, `nombre`,
`cue`, `distrito`, `localidad`, `domicilio`, `nivel`) con el mismo formato;
`services/escuelas.py` no cambia. No se agregó `provincia` a la API.

## Deploy

- Migración `inspecciones.0002` (aditiva; corre en el migrador).
- `collectstatic`: archivos nuevos `inspecciones/css/panel.css` y
  `inspecciones/js/panel.js`.
- Antes de importar el padrón en un entorno, la geografía de SISOC
  (`core.Provincia/Municipio/Localidad`) tiene que estar cargada.
