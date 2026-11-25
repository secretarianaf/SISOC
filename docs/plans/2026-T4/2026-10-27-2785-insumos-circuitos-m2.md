# Insumos: circuitos completos de activación M2

Estado: **E2, especificación propuesta para futura implementación**. No hay
endpoints, formularios React, entorno ni evidencia visual ejecutados. M2 y la
exclusión admin/Unfold están confirmadas; el detalle de API de este documento es
propuesta del agente. No equivale a aprobación técnica de código.

## Fuente y límites

Fuente `59a8f797688c9e762d5a4e9eaa187698ffade8aa`:
`src/backends/sisoc_core/insumos/{urls,views,forms,models,services,validators}.py`,
templates de esa app y `static/custom/js/insumoForm.js`. Los cuatro archivos
forms/views/models/services del checkout no difieren de esa fuente. Se leyeron
tests existentes de permisos como especificación, sin ejecutarlos.

El patrón de feedback por operación existe en
`src/backends/vpsl/ver_para_ser_libre/api_workflow.py`. Reutilizar el enfoque,
sin importar ese backend ni llamar una vista HTML como API genérica: los services
locales ya guardan/eliminan. No basarse en consumir toda la cola de mensajes.

## Grupos M2 y rutas públicas

| Grupo | UI pública completa | Acciones y retorno | Dependencias para activación |
|---|---|---|---|
| INS-A | `/insumos/`, `/insumos/crear`, `/insumos/<pk>/editar`, `/insumos/<pk>/eliminar` | Guardar/eliminar/cancelar vuelve a `/insumos/` sin conservar filtros; descarga `/insumos/<pk>/descargar` sigue backend | Contexto #2798, shell #2800, checks #2801 y diff #2799; lectura #2802 más formularios de I03, no solo lectura |
| INS-B | `/insumos/categorias/`, `/insumos/categorias/crear`, `/insumos/categorias/<pk>/editar`, `/insumos/categorias/<pk>/eliminar` | Guardar/eliminar/cancelar vuelve a `/insumos/categorias/` | Contexto/shell/checks/diff y todas las operaciones I02 |

Son dos grupos de activación propuestos y relacionados, no dos aplicaciones ni
servicios nuevos. Los templates actuales no contienen `next`/referrer en estos
formularios: sus retornos son fijos. No agregar conservación de filtros como
mejora implícita. No cambiar slashes de las URLs públicas por uniformidad.

El botón Categorías del listado INS-A abre INS-B. Durante migración puede enlazar
otro circuito aún no migrado, pero no declarar toda Insumos completa ni la
migración terminada hasta que INS-B también sea React. No hay POST de INS-B que
retorne al listado INS-A en las vistas inspeccionadas. No inferir independencia
de datos: borrar categoría hace SET_NULL en insumos; al volver al listado o abrir
otro formulario, leer opciones/datos actuales, sin cache persistente nueva.

Los enlaces externos localizados son sidebar y los propios templates/vistas.
No prueba ausencia de bookmarks o consumidores dinámicos. Verificar navegación
y URL directa en implementación; no cortar enlaces para acotar un grupo.

## Namespace de API propuesto, unificado

Usar `/api/web/insumos/` y descendants, coherente con `/api/web/session/` ya
propuesto. Las menciones anteriores `/api/insumos/` quedan reemplazadas como
propuesta documental: no existe aquí un endpoint implementado que renombrar.
No registrar ambos namespaces ni generar tipos antes del backend real.

| Path bajo `/api/web/insumos/` | Métodos explícitos nuevos | Permiso IAM por petición | Resultado GET |
|---|---|---|---|
| raíz | GET/HEAD | `insumos.view_insumo` | Página de lectura, filtro y orden de I01 |
| `options/` | GET/HEAD | `insumos.view_insumo` | Categorías activas del filtro; no permiso de gestión de categorías |
| `crear/` | GET/HEAD/POST | `insumos.add_insumo` | Iniciales y opciones de InsumoForm de alta |
| `<pk>/editar/` | GET/HEAD/POST | `insumos.change_insumo` | Iniciales/opciones y archivo actual protegido |
| `<pk>/eliminar/` | GET/HEAD/POST | `insumos.delete_insumo` | ID/título para confirmación, sin borrar en GET |
| `categorias/` | GET/HEAD | `insumos.view_insumocategoria` | Lista 20/página, orden/nombre y programa visible |
| `categorias/crear/` | GET/HEAD/POST | `insumos.add_insumocategoria` | Iniciales/opciones de InsumoCategoriaForm |
| `categorias/<pk>/editar/` | GET/HEAD/POST | `insumos.change_insumocategoria` | Iniciales/opciones de instancia |
| `categorias/<pk>/eliminar/` | GET/HEAD/POST | `insumos.delete_insumocategoria` | ID/nombre y aviso de efecto SET_NULL |

HEAD conserva headers/status de GET y no cuerpo; OPTIONS solo descubrimiento
si lo proporciona el framework, sin negocio. PUT/PATCH/DELETE no son métodos de
mutación de esta propuesta: 405. Se elige POST por compatibilidad con Form y
multipart actuales, sin introducir PATCH parcial, versionado o idempotencia.
Es una API nueva, no la lista efectiva de métodos de las vistas HTML heredadas.

Todos los endpoints aplican sesión, prioridad de requisitos web y permiso de
su acción; IDs fuera de queryset/inexistentes son 404 después de los controles
correspondientes. No añadir alcance provincial inexistente ni exigir view a
quien actualmente puede crear/cambiar/borrar por su permiso independiente.

La visibilidad sigue el template: Add controla gestión del listado Insumos;
en categorías, Add/Change/Delete controlan sus botones por separado mediante
`has_perm`. El permiso IAM de ruta no se reemplaza por esa visibilidad.

## Datos editables y opciones

| Formulario | Campos en orden | Tipos y validación backend existentes |
|---|---|---|
| Insumo | programa, categoria, titulo, descripcion, archivo, activo | Programa requerido; categoría nullable del programa; título requerido máx. 200; descripción opcional; archivo requerido en alta y conservado en edición sin reemplazo; activo checkbox |
| Categoría | programa, nombre, descripcion, orden, activo | Programa requerido; nombre requerido máx. 150; descripción opcional; orden entero no negativo con default 0; activo checkbox |

GET de formulario propone `{initial, options, current_file}`. `initial` contiene
solo esos campos editables (IDs como strings de controles, `""` para opción
vacía; booleanos para checkbox); nunca usuario, auditoría o ruta storage.
`archivo` no se serializa en initial: `current_file` es null o `{name, download_url}`
con descarga autorizada existente. `options.programa` y `options.categoria`
contienen `{value,label}` en orden real del Form; categorías además `programa_id`.
La lista efectiva se calcula desde el Form de esa operación e instancia, no del
endpoint de filtro: debe incluir programa/categoría actuales inactivos al editar.

Diseño y layout son componentes React específicos, con mismos labels, ayudas,
errores y posición; no motor de formularios universal ni HTML remoto. Backend
mantiene ModelForm/clean/validadores y los services existentes como autoridad.
No convertir una lista parcial de constraints aquí en reemplazo de full_clean.

POST Insumo usa multipart/form-data, con nombres actuales y archivo binario;
POST Categoría usa application/x-www-form-urlencoded. En checkbox falso omitir
clave; verdadero enviar valor de control. Categoría vacía se envía como `""`.
No usar JSON/base64 ni depender del límite de `accept` del navegador.
El archivo requerido no ofrece borrar sin reemplazo por comodidad; conservar la
semántica real de ClearableFileInput/Form, verificándola en entorno autorizado.

El selector de programa elimina categorías de otro programa y limpia selección
no válida, como insumoForm.js; backend vuelve a validar categoría/programa.
Mantener extensiones y content types actuales, máximo 10 MiB; no afirmar análisis
de malware ni validación exhaustiva de contenido. No introducir nuevos formatos.

## Respuestas y feedback por operación

| Resultado | Contrato propuesto | Evidencia futura requerida |
|---|---|---|
| GET válido | 200, JSON mínimo del recurso/formulario | No incluir HTML, tokens, storage público ni campos privados no usados |
| POST válido | 200 `{ok:true,message,redirect}`; textos exactos actuales y destino fijo generado por reverse del servidor | Servicio ejecutado y estado real verificado, no inferido del aviso |
| Datos inválidos | 400 `{errors:{campo:[{message,code}]}}`; `__all__` para error general, formato Django get_json_data sin HTML escapado como markup | Misma ubicación/texto/orden visual que el formulario inválido actual; ningún guardado |
| Sin sesión | 401 JSON para API nueva | No cambiar 403 HTML anónimo de entry Insumos ni el login global |
| Requisito pendiente o sin permiso | 403; estado/remediación según contexto web y causa de acceso diferenciada | Nada de negocio ejecutado; no interpretar cualquier 403 como sesión expirada |
| CSRF inválido | 403 antes de mutación | Capturar fallo efectivo de middleware/autenticación, aunque la respuesta sea HTML; cliente no asume siempre JSON |
| Objeto no encontrado | 404 | No filtrar datos por el texto del error |
| Método no soportado | 405 | GET/HEAD no mutan; POST directo exige permiso/CSRF |
| Red/servidor/storage incierto | Conservar fallo e incertidumbre, sin mensaje de éxito inventado | No retry automático de mutación ni promesa de rollback storage |

Mensajes de éxito: «Insumo creado/actualizado/eliminado correctamente.» y
«Categoría creada/actualizada/eliminada correctamente.», expandiendo cada acción
con su texto de views.py. Renderizar como texto, misma severidad/posición inferior
derecha y apariencia actual. Consumir solo resultado de esa operación en memoria;
sin puente M1, cola global, localStorage, logs de payload ni notificación externa.

Un usuario con Add pero sin View puede guardar y llegar a un listado denegado
según reglas existentes. No sumar View para ocultar esa combinación ni concederlo
automáticamente. Añadir caso específico de persistencia y retorno denegado.

## Efectos, concurrencia y reversión

- Insumo: preservar creador inicial, registrar actualizador. No permitir esos
  campos en payload. Reemplazo de archivo conserva el ciclo de vida existente;
  no introducir limpieza de archivos antiguos por deducción.
- Borrar insumo elimina DB y luego storage: no son una transacción conjunta.
  Fallo de storage puede dejar DB eliminada. No devolver éxito por capturar todo
  error ni reintentar ciegamente; investigación/limpieza fuera de esta migración.
- Borrar categoría hace SET_NULL en insumos; conservar texto de confirmación y
  probar antes/después. No cascada de documentos ni borrado de archivos.
- Duplicado de categoría case-insensitive por programa usa el Form actual;
  constraint DB es adicional. No prometer exclusión mutua o equivalencia de
  collation entre entornos. Dos altas simultáneas y edición concurrente son
  escenarios a observar; no agregar locks/versiones/reglas nuevas sin decisión.
- Reversión de activación no revierte escrituras ni recupera archivo borrado.
  Preparar versión UI anterior compatible y conservar backend hasta aceptación;
  retiro de templates solo tras evidencia, con admin/PDF/correo fuera del retiro.

## Evidencia y trabajos derivados

El [manifiesto ampliado](2026-10-27-2799-insumos-manifiesto-visual.json) agrega
casos de formulario/confirmación/éxito/error y datos sintéticos. Cada caso se
instancia por separado en referencia/candidato; no compartir DB mutable entre
ambos ni reutilizar un insumo eliminado por un caso previo. Archivos sintéticos
idénticos, reloj comparable y roles autorizados; ningún dato real.

#2802 sigue siendo lectura; no ampliarlo silenciosamente a ABM. Derivar después
una ficha acotada para formularios Insumo y otra para categorías, con este contrato
revisado, y agrupar su activación M2. No crear aquí tickets masivos o declararlos
implementados. Quedan por verificar en runtime errores nativos de Form/CSRF,
archivo requerido/edición, métodos efectivos y opciones precisas; los escenarios
ya quedan definidos, sin falsificar resultados.

Pruebas fuente útiles: tests de permisos/relación programa-categoría existentes
en `src/backends/sisoc_core/insumos/tests/`; sumar errores/efectos y UI por operación
durante implementación. No se ejecutaron bajo E2.

## Auditoría estática B0–B2 del paquete INS-A

Se comprobó el ref local origin/development59a8f797688c9e762d5a4e9eaa187698ffade8aa,
no su actualización remota. Las nueve rutas y slashes coinciden con fuente/registro;
sidebar conocido e indirectos por futuro diff deben incluirse. E2 sigue vigente.

current_file.download_url conserva permiso view_insumo de la descarga backend.
Change sin View puede editar/ver nombre actual pero recibir denegación al descargar;
no convertir el descriptor en permiso de bytes. Add/Change/Delete sin View se
prueban independientemente: mutación válida puede persistir y retornar a listado403.
No conceder View ni reintentar automáticamente por esa denegación posterior.

Manifiesto vigente:52 casos/106 combinaciones caso-viewport,13 casos de contrato,
9 roles, dataset lectura25. INS-A38/78 e INS-B14/28. Capture_points múltiples no se
cuentan como una sola imagen aprobada; todas las pruebas/capturas están sin ejecutar.
Fixture sets se unen por ref solo para el caso que los necesita; sus datos de
operación no alteran el dataset lectura por defecto. Return_with_query no promete
conservar filtros tras guardar/eliminar: esos retornos siguen fijos de fuente.
