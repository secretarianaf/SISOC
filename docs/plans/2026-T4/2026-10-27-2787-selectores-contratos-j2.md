# J2: contratos de selectores CDF e Inspecciones

Estado **E2**. J2 elegida; especificación futura sin componentes, dependencias,
peticiones HTTP, DB, tests de aplicación ni capturas. No ampliar permisos ni
modificar contratos PWA/API key. No equivale a migrar los formularios completos.

## Fuente y responsabilidad

Fuente `59a8f797688c9e762d5a4e9eaa187698ffade8aa`. Se compararon con checkout los
Forms/vistas de CDF y views_ajax/forms/services/panel.js de Inspecciones revisados,
sin diferencias en los archivos contrastados. El registro fija paths; no prueba
exposición actual, autenticación efectiva o loader. Form y service siguen en su
backend; no importar un backend desde otro o desde kernel para renderizar opciones.

J2 reutiliza patrones de estado React, no apariencia MUI ni el FormSchema privado
de otra app como contrato universal. Opciones de búsqueda no son autorización.
IDs se normalizan para comparar selección sin convertir códigos con ceros
iniciales en números; un ID ORM y un Cueanexo/DNI no son la misma clase de dato.

## CDF: selección múltiple y dependencia categoría/actividad

| Control | Fuente y transporte actuales | Regla que conserva React |
|---|---|---|
| sexoact | ActividadCentroForm, ModelMultipleChoiceField Sexo.objects.all(), opcional | Lista de IDs, campo repetido en POST. No reducir a string único ni filtrar opciones por un estado inventado |
| dias | ModelMultipleChoiceField Dia.objects.all(), opcional; iniciales de instancia | Retener todos los IDs en edición y vaciar como lista vacía opcional; no inferir orden semanal diferente del catálogo |
| categoria | ModelChoiceField opcional sobre Categoria.objects.all() | Opción vacía y selección de instancia conforme Form. No copiar filtro solo activo de Insumos |
| actividad | Form filtra queryset por categoría enviada o de instancia; sin categoría inicial, none | Cambio de padre limpia selección antigua; no conservar actividad de otra categoría. Backend vuelve a validar IDs/queryset al submit |

GET de opciones vigente: nombre `ajax_cargar_actividades`, path registrado
`/centrodefamilia/ajax/actividades/`, query `categoria_id`; devuelve array
`[{id,nombre}]`, no `{results}`. El JS actual pide alias `/ajax/actividades/`.
Resolver URL por nombre desde dueño para React y conservar alias operativo;
no copiar hardcode ni afirmar que el alias falla por usar otro prefijo. Registro
también contiene forwarding de ese alias; recepción real se verifica después.

No hay paginación/límite declarado en ese helper: no imponer veinte opciones por
reutilizar el componente de Inspecciones. Reutilizar dato backend, proyectar a
`{value,label}` localmente sin HTML remoto. Leer iniciales del Form, no deducir
selección de la primera página/primer resultado o del texto visible.

Acceso fuente de formulario y endpoint pasa por `view_centro` y los controles
de vistas existentes; no añadir Add/Change por interpretar el nombre de acción.
No extrapolar R1 de centros VAT a CDF. Cada nueva API aplica gate y regla real de
su dueño; la UI no convierte permiso de lectura en permiso genérico de otros datos.

El alta/edición de actividad retorna a `centro_detail`, no a actividadcentro_detail:
M2 requiere la presentación React de esa ficha destino además del formulario.
Es dependencia de parte de CDF01 desde CDF02, sin obligar por intuición a migrar
todo CDF ni borrar W1. La asistencia y la promoción mantienen sus permisos/services.
Horas usan otro widget en fuente; J2 de selectores no autoriza reemplazarlo por
input nativo distinto ni añadir una librería de fechas.

### Estados y recuperación de opciones

Categoría cambia → actividad vacía y «Cargando...» → array válido con placeholder
«Seleccione una actividad». Respuestas de una categoría anterior no deben
sobrescribir la actual en React. Mantener el resto del formulario y no enviar
mutaciones desde la carga de opciones.

El script fuente no tiene catch ni comprobación response.ok. Rechazo de fetch o
de response.json impide el segundo then y puede dejar «Cargando...»; JSON con
forma incorrecta puede llegar a otra presentación antes de fallar en forEach.
No se afirma que todos los HTTP no-200 produzcan el mismo estado ni que exista
un incidente desplegado. El nuevo estado de error/reintento tiene
[L2 elegida](2026-10-27-2787-error-carga-actividades-l1-l2.md): error visible y
reintento manual del GET de opciones de la categoría actual, conservando otros
campos sin retener una actividad inválida. No repite guardado ni se hereda de C2.

## Inspecciones: búsquedas remotas diferentes

| Endpoint fuente bajo `/inspecciones/ajax/` | Request y respuesta | Alcance/orden/límite actuales |
|---|---|---|
| inspectores/ | GET `q`; `{results:[{id,text,detalle}]}` | strip, mínimo 3 caracteres, máximo 20; activos del programa. Alta solo inspectores; filtro `alcance=programa` incorpora coordinación. Orden apellido/nombre/username; DNI por prefijo si búsqueda numérica sin puntos |
| escuelas/ | GET `q`; `{results:[{id,text,detalle}]}` | strip, mínimo 3 caracteres, máximo 20; filtro de texto del catálogo, orden nombre/id. Detalle Cueanexo/localidad/provincia |
| localidades/ | GET `provincia`, `q`; `{results:[{id,text}]}` | Provincia numérica, inválida → []; hasta 30, orden nombre/municipio. No tiene el mismo mínimo tres del selector de inspectores |
| asignaciones/verificar/ | GET escuela/fecha/inspector; objeto con otras y, cuando válido, escuela | Aviso de otras visitas, no bloquea asignar a otro inspector. Form valida relación/datos; sin escuela/fecha válidas otras=[] |

Los AJAX heredan GestionInspeccionesMixin: sesión y puede_gestionar_inspecciones,
no cualquier usuario con acceso a la PWA. La regla vive en kernel y admite
permiso explícito gestionar_inspecciones o coordinación vigente; no reimplementar
roles enviados por cliente. Sus vistas declaran http_method_names=[get]: no
afirmar HEAD autorizado por copiar un cliente genérico. Probar rechazo de métodos.

panel.js aplica delay 250 ms, mínimo por atributo, allowClear, placeholder y popup
dentro de modal si corresponde. Mensajes actuales «Escribí al menos N letras»,
«Sin resultados», «Buscando…». El componente React debe conservarlos y los dos
renglones de opción sin inyectar HTML de response; React representa texto/detalle.

Provincia cambia → localidad vacía y deshabilitada si no hay provincia. Filtros
con auto-submit mantienen su efecto; no hacer autosave del formulario de alta.
Conservar selección inicial entregada por vista aunque no figure en la búsqueda
actual. Helpers de selección histórica por ID no equivalen al catálogo activo:
no sustituir uno por otro ni estrechar/ampliar su alcance sin revisión de fuente.

La búsqueda no concede validez al submit: AsignacionForm usa inspectores y valida
es_inspector; EscuelaForm valida provincia/localidad y Cueanexo, conservando ceros.
Una escuela asignada a otro inspector es aviso de otra visita, no prohibición;
la duplicación de misma combinación/fecha sigue la regla del service.

## Datos de formulario y resultado del modal

Los endpoints existentes de modal pueden retornar HTML en errores y JSON al
guardar. J2/M2 no autoriza incrustar ese fragmento como formulario React. Proponer
adaptador JSON acotado de Form/initial/options/errores y delegar los mismos
services; conservar endpoints existentes si tienen consumidores no migrados.

Respetar «Asignar» frente a «Asignar y cargar otra», fecha elegida, aviso tras éxito
y navegación actuales. No reemplazar una segunda asignación por retry automático.
Sin sesión, un endpoint legacy puede redirigir a login y devolver HTML tras fetch;
cliente verifica status/content-type/redirect antes de interpretar results=[]:
sesión vencida o denegación no significa catálogo sin coincidencias.

## Aceptación y alcance

El [manifiesto](2026-10-27-2787-selectores-manifiesto-visual.json) fija casos de
abierto/cerrado, múltiples/iniciales, padre/hijo, umbral/límites, orden, modal,
permiso, teclado, carga y errores. Referencia/candidato/fixtures/baseline deben
instanciarse después de autorización; no escribir valores reales en artefactos.

Inspecciones usa layout claro propio; CDF toma el layout de su template. Reutilizar
un control no uniforma tema ni shell. J2 tampoco cambia el contraste I1 de INET.
Regresión de MUI/paquetes comunes se amplía solo si el diff los toca; no modificar
VPSL/Celiaquía por tomar sus patrones como referencia de implementación.

Sin dependencias, generic form builder, cache persistente, autenticación nueva
o contratos de sincronización externos. El orden es control local, comparación
con su fuente y extracción compartida solo si se demuestra reutilización real.
