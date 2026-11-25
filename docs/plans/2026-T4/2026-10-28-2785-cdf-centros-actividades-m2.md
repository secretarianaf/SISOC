# CDF-A/CDF-B: centros y actividades en React

E2: definición fuente, sin implementación ni prueba runtime. D1 conserva política
existente por acción, CR1 limita credenciales a proyecciones privadas separadas,
M2 exige retorno/feedback React. Quirks se documentan, no se corrigen incidentalmente.

## Centros: rutas y políticas distintas

| Acción | Contrato fuente |
|---|---|
| centro_list / centros_ajax | Login/view_centro; SSE/superusuario global, AccesoCDF histórico→solo activos (puede vacío), sin historial referente legacy por FK, demás vacío |
| centro_detail | Referente FK, AccesoCDF activo, SSE, superusuario o gestor territorial; no derivar del listado |
| centro_create | Form GET/POST y view_centro; can_add limita UI SSE/superusuario pero clase no agrega ese predicado al endpoint |
| centro_update | Referente FK/SSE/superusuario, inválido vuelve Form, éxito ficha |
| centro_delete | Confirmación y baja lógica activo=False, predicado de edición, retorno listado |

No declarar métodos exclusivos sin resolver CBV/mixins/HEAD/OPTIONS; no inventar
mutación GET. D1 no agrega gates ausentes ni quita los existentes. Negativos se
comparan con política efectiva, no se inventa nuevo403 para endurecer por interfaz.

## CentroForm y estados

Orden: tipo,nombre,codigo,organizacion_asociada,provincia,municipio,localidad,
calle,numero,latitud,longitud,domicilio_actividad,telefono,celular,correo,sitio_web,
link_redes,nombre_referente,apellido_referente,telefono_referente,correo_referente,
referente,faro_asociado,foto,activo.

Requeridos fuente: tipo, nombre200, codigo20 único, provincia,
domicilio_actividad255, telefono/celular50, correo100, nombre/apellido referente100,
telefono_referente50, correo_referente100 y referente. Null=True en columna referente
no implica opcional con blank=False. Opcionales: organización, municipio/localidad,
calle255, numero positivo, coordenadas decimal9/6, URLs200, FARO y foto; activo
checkbox/defaultTrue. Mantener validación Django de email/URL/imagen/choices/FK.

Opciones: referentes de grupos CDF_REFERENTE_CENTRO o legacy ReferenteCentro,
distinct; FARO activos; organización con «Seleccionar organización...».
?faro= inicializa adherido y FARO, controles disabled en servidor: no confiar solo
en bloqueo cliente. Ambas coordenadas o ninguna; límites latitud±90/longitud±180.

Errores fuente: «Complete latitud y longitud, o deje ambas vacías.»;
«Debe asociar un Centro FARO activo si el centro es ADHERIDO.»;
«Un Centro FARO no puede tener un FARO asociado.»

Alta→listado «Centro creado exitosamente.»; edición→ficha «Centro actualizado
correctamente.»; baja→listado «Centro dado de baja correctamente.». Foto multipart,
reemplazo/limpieza e inválidos conservan recorrido y widget actuales.

Crispy + editor map_pin_editor después de longitud. Provincia limpia municipio/
localidad; localidad depende atributo data-municipio-id agregado por carga de
municipios. Edición inicial y cambio posterior requieren pruebas separadas.

Sin tipo solo tipo; FARO/adherido muestran grupos. JS usa div_id_sitioweb/linkredes,
pero Form sitio_web/link_redes: registrar divergencia, no corregir visibilidad
incidentalmente. JS compartido centro_form.js también sirve VAT; no cambiarlo
para migrar CDF. Mapa ficha usa Google iframe; editor usa address_preview existente,
no contratar proveedor/geocodificador nuevo ni probar integración real bajo E2.

## Listado y ficha: datos y dependencias

busqueda numérica→codigo prefijo o ID exacto; texto→nombre icontains. Backend -id,
NoCount10/página; AJAX actual devuelve HTML/pagination_html, count/num_pages null
más flags. React necesita proyección, no HTML de formulario inyectado. Config22
campos; codigo aparece FIELD_MAP/UI pero no FIELD_TYPES: no inventar tipo o filtro
numérico sin contrastar engine. Orden interactivo listSort local no se convierte
en orden global API por comodidad.

Ficha «Actividades en curso» consulta todos los estados. search_actividades_curso
busca nombre/categoría/estado según vista; página page_actividades_curso,5 por
página, orden nombre/id. Count(participanteactividad) no filtra estado; ganancia
precio×ese conteo. Total actividades/recaudado siguen filtro; otras métricas usan
otro queryset. No recomputar todas las métricas desde inscritos en React.

Otras actividades excluyen centro actual; search_actividades, page_act,5/página.
Conservar queries/hash/tabs y comportamiento real de enlaces; no corregir parámetros
que paginaciones actuales pierden. CABAL y credenciales CR1 dependen de sus circuitos.

centros_adheridos_paginados y observaciones no tienen productor identificado en
vista, configuración de contexto o fuente inspeccionada. Sus ramas template muestran
vacíos: «No hay centros adheridos.» y «No hay observaciones registradas para este
centro.». No conectar helpers huérfanos ni crear API/funcionalidad para rellenarlos.
Confirmar esos vacíos en runtime futuro, sin afirmar ausencia absoluta de cambios
desplegados fuera del checkout. center_map_query sí se calcula dentro del template
con google_maps_query: coordenadas válidas o vacío; fallback de dirección existente.
No necesita endpoint adicional. No declarar toda la ficha lista con solo resumen.

## Actividades

actividadcentro_list: sin paginación fuente, filtro centro, orden centro/nombre.
ActividadCentroForm: categoria opcional, actividad requerida y queryset dependiente,
cantidad_personas positiva, sexoact/dias múltiples opcionales, horas desde/hasta
requeridas aunque modelo hasta permita blank, precio opcional, estado
planificada/en_curso/finalizada. FARO precio oculto/no requerido; precio truthy
rechaza «Un centro de tipo FARO no debe tener un precio asignado.»; cero pasa.

Horas: flatpickr24h H:i, solo hora. J2 decidió selectores, no reemplazo de todos
los plugins; conservar apariencia/interacción, sin imponer input nativo o nueva
librería. Definir adaptación local compatible antes de implementar.

Alta/edición retornan centro_detail con mensajes actuales; actividadcentro_detail
incluye inscritos, espera, precio, promo_error y navegación C/D. J2/L2 conservan
categoría/opciones, error y retry GET manual sin repetir guardado.

actividad_create_sola es catálogo con ActividadForm(categoria,nombre), retorno
centro_list. test_func existe pero clase no hereda UserPassesTestMixin: no afirmar
superusuario como gate efectivo. Mantener D1 y pruebas diferenciales por acción.
Componentes form_card/alerts/breadcrumbs compartidos no se modifican globalmente
para construir formularios React locales.

## Casos visuales y de contrato pendientes

- Actores por acción, alcance listado frente a ficha/edición, acceso directo y CSRF.
- NoCount vacío/límites/búsquedas/filtros/orden local; no totales ficticios.
- FARO/adherido/query, requeridos/duplicado/imagen/coordenadas, inválido y campos
  conservados, geografía inicial/cambio, mapa, editar/baja/cancelar/retornos.
- Ficha con tabs/bloques/ambas paginaciones/hash, conteos/ganancia distintos, CR1.
- Actividad listado/filtro/vacío/catálogo; FARO precio0/no0, horas, estado,
  múltiples/iniciales, J2/L2/stale, éxito a centro y navegación participantes/asistencia.

Cada URL/estado/rol requiere pareja referencia/candidato/diff desktop/móvil y foco/
teclado; fixtures sintéticas, baseline no aceptado. Fuente no sustituye capturas.

## Evidencia

Prefijo src/backends/cdf/centrodefamilia/: urls.py:69–115;
views/centro.py:93–111,194–322,327–391,443–504;
forms.py:34–212; models.py:14–16;
services/centro_filter_config/impl.py:5–129;
views/actividad.py:19–148;
templates/centros/centro_form.html:12–37;
templates/centros/actividadcentro_form.html:21–31;
templates/centros/centro_detail.html:187–196,311–405,513–735.
Compartido src/backends/kernel/static/custom/js/centro_form.js:23–139;
consumidor src/backends/vat/VAT/templates/vat/centros/centro_form.html:280.

Explorador contrastó vista centro/Form/modelos/tres templates/config filtros con
59a8f797688c9e762d5a4e9eaa187698ffade8aa; JS compartido observado solo checkout.
Padre contrastó queryset, filtro y métricas de ficha. Ninguna ejecución aplicación.

- [Circuitos CDF y D1](2026-10-28-2785-cdf-circuitos-y-alcance-autorizacion.md).
- [Participantes y asistencia](2026-10-28-2785-cdf-participantes-asistencia-m2.md).
- [Usuarios/CABAL y CR1](2026-10-28-2785-cdf-usuarios-cabal-y-credenciales.md).

## Integración React local de mapa y hora

Existe patrón MapPinEditor.tsx en apps/vpsl: lifecycle React sobre Leaflet1.9.4 y
motor compartido mapPinEditor.js, eventos pin:init/pin:destroy. Reutilizar patrón y
motor con JSX/clases/copy/dirección CDF, no copiar botones MUI o importar componente
privado VPSL. CDF usa calle/numero/provincia/municipio/localidad. No librería nueva.

address_preview POST autenticado /ajax/ubicacion/previsualizar/ requiere provincia
y domicilio o calle+numero/altura; municipio/localidad opcionales.400 invalid/errors,
503 unavailable, otros200; Cache-Control private,no-store. Geocodifica borrador, no
persiste ni autoriza centro; mantener descarte de resultados obsoletos/edición.
No probar proveedor real bajo E2. En implementación, simulación de respuesta y
capturas deterministas no acreditan interoperabilidad externa.

No se halló wrapper flatpickr/timepicker en frontends. Planificar adaptador React
local del plugin ya usado con init/destroy/estado controlado, sin nueva dependencia
ni input nativo distinto. Popup/24h/H:i, teclado/foco, inválido y edición requieren
diff visual futuro. J2 no decide otros plugins.

Evidencia adicional checkout: centro_detail.html:188–196;
src/backends/kernel/core/templatetags/custom_filters.py:224–230;
src/backends/config/settings.py:252–261; backend_settings.py:37–49;
src/frontends/apps/vpsl/src/MapPinEditor.tsx:23–78;
src/backends/kernel/templates/components/map_pin_editor.html:1–40;
src/backends/kernel/core/location_views.py:11–53;
src/backends/kernel/static/custom/js/mapPinEditor.js:75–100.
Corrección de incertidumbre anterior: el productor center_map_query es un tag,
no contexto ausente. Estos archivos adicionales no se atribuyen al snapshot congelado.
