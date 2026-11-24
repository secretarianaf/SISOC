# INS-A: preparación ejecutable y checklist B0–B2 (#2785)

Estado vigente 2026-10-28: **preparación estática coherente, E2**. No hay API/app
implementadas, entorno autorizado, baseline aceptado o prueba visual ejecutada.
El responsable autorizó preservar el plan mediante commits documentales locales;
no autorizó código, entorno, push, PR, merge, activación o deploy.

## Resultado de esta preparación

Una entrega INS-A completa: listado, crear, editar, confirmar/borrar, cancelar,
feedback y retornos. La descarga sigue en Django con autorización existente.
La lectura puede desarrollarse primero en ruta de validación; **activar la URL
pública requiere formularios/acciones/retornos React**, no lectura con Django final.
INS-B categorías conserva su circuito propio y puede seguir enlazado temporalmente.
No declarar toda Insumos ni la migración terminadas por entregar INS-A.

## B0 — Fuente, impacto y referencia

| Comprobación | Estado / evidencia |
|---|---|
| Fuente del contrato | 59a8f797688c9e762d5a4e9eaa187698ffade8aa; ref origin/development local comprobado, sin fetch ni garantía de frescura remota |
| Evidencia histórica | source_sha afa6fc conserva extracción inicial; source_definition_sha59a8f es definición reconciliada. Ninguno es baseline visual aceptado |
| Rutas públicas INS-A | /insumos/; /insumos/crear; /insumos/<pk>/editar; /insumos/<pk>/eliminar; /insumos/<pk>/descargar. Slashes conservados |
| Consumidores conocidos | Sidebar kernel, listados/Forms/confirmaciones, descarga y enlace a categorías. Ampliar por diff real de shell/paquetes; no afirmar ausencia de bookmarks o referencias dinámicas |
| Retornos | Guardar, cancelar y borrar retornan /insumos/ sin filtros. Return_with_query solo comprueba navegación/descarga, no agrega conservación de filtros a mutaciones |
| Referencia/candidato | SHA aceptado, URLs, candidato y aceptación siguen null/pending. Se fijan con entorno sintético autorizado antes de comparar |

Al implementar, partir de development actualizado y reconciliar diferencia frente
al snapshot congelado sin sobrescribir INET/Unfold ni otros cambios. La rama de
preservación documental puede partir del ref local congelado; no confundirla con
un checkout de implementación actualizado o con autorización de acceso remoto.

## B1 — Contrato y acceso

La especificación normativa está en
[INS-A/INS-B M2](2026-10-27-2785-insumos-circuitos-m2.md) y el
[contexto web #2798](2026-10-27-2798-contrato-contexto-web.md).
Las APIs siguientes son **propuestas nuevas**, no endpoints existentes.

| Operación bajo /api/web/insumos/ | Métodos | Autoridad / datos |
|---|---|---|
| raíz y options/ | GET/HEAD | ViewInsumo; filtros/página y opciones del filtro |
| crear/ | GET/HEAD/POST | AddInsumo; iniciales/opciones reales del Form y multipart de alta |
| <pk>/editar/ | GET/HEAD/POST | ChangeInsumo; instancia/opciones históricas/archivo actual y guardado |
| <pk>/eliminar/ | GET/HEAD/POST | DeleteInsumo; confirmación sin mutar en GET, ejecución en POST |

- Dueño backend: sisoc_core/insumos; conservar Forms, validadores y services. No
  CRUD genérico ni importar otro backend. #2802 sigue lectura; I03/F7 aporta las
  operaciones para cerrar INS-A, sin ampliar el ticket de lectura por omisión.
- Sesión Django y precedencia por petición: acceso web→contraseña→perfil→encuesta
  →ready; sin ready por defecto. Permiso propio de cada acción y CSRF, no botones
  como autorización. Token PWA/SIIS no cambia, G1 remoto no bloquea el circuito local.
- Alta/edición mantienen programa/categoría/título/descripción/archivo/activo, Form
  y límite10MiB existente. Opciones de edición incluyen programa/categoría actuales
  inactivos; no reutilizar opciones de filtro como si fueran todas las del Form.
- Éxito propuesto200 con resultado/message/redirect propio de la operación;
  inválido400 con errores de campo y __all__. GET/HEAD no mutan; PUT/PATCH/DELETE405.
  CSRF403 puede ser HTML del middleware: tratarlo como rechazo, nunca éxito ni JSON
  supuesto. Contrastar estado persistido, no solo toast.
- current_file solo nombre/download_url; descargar mantiene view_insumo aunque el
  actor tenga Change. Add/Change/Delete sin View pueden operar y retornar a lista
  denegada: no conceder View ni repetir la mutación por ese resultado de navegación.
- Entrada HTML anónima Insumos conserva403; API nueva propone401. Guard local no
  retira login global ni exige ViewInsumo a toda app transversal.
- Sin reintentos automáticos de mutaciones. DB y storage no son transacción conjunta;
  eliminación de DB puede preceder fallo de fichero. No inventar rollback o éxito.

## B2 — Datos, comparación visual y herramientas

[Manifiesto #2799](2026-10-27-2799-insumos-manifiesto-visual.json):

| Alcance | Casos visuales | Combinaciones caso×viewport | Casos contractuales |
|---|---:|---:|---:|
| INS-A | 38 | 78 | 12 |
| INS-B | 14 | 28 | 1 |
| Total declarado | 52 | 106 | 13 |

Nueve roles sintéticos,25 insumos de lectura. Datos de operación se incorporan
solo al caso que los requiere, mediante unión explícita por ref: programas y
categorías propios/ajenos/inactivos, archivo actual, eliminación y contextos
históricos. Dataset categorías21 para paginación separado. No seed ni archivo real
creado; referencia/candidato usan DB/storage independientes y reinicio por caso.

Cada caso declara INS-A o INS-B; comprobar afectados indirectos de SET_NULL y
paquetes compartidos. Un caso con varios capture_points necesita evidencia de cada
punto;106 combinaciones no equivalen automáticamente a106 imágenes suficientes.

- Misma fixture comparable, reloj, viewport, Chromium/OS/fuentes/tema oscuro forzado
  de Insumos; header/sidebar/footer, labels, errores y foco actuales. No tema claro
  INET o apariencia MUI por conveniencia.
- Before/after/diff por URL, estado, rol y viewport; revisión de breakpoints y
  consumidores compartidos según diff. Sin autoaceptar baseline, máscaras amplias
  ni tolerancia para ocultar regresiones. Aceptación humana explícita futura.
- Positivos/negativos: filtros/20 por página, inactivos/archivos ausentes, Form y
  programas/categorías, permisos independientes, Add/Change/Delete sin View,
  denegación/CSRF/estado pendiente, error de red/storage y retornos reales.
- Vitest/Playwright/typecheck/checks/schema existentes se reutilizan al implementar.
  Nueva app propuesta src/frontends/apps/sisoc y ruta /v2/sisoc/insumos/. Integrar
  en configs reales; no instalar otro sistema de tests o generar tipos antes del API.

## Qué queda para la fase autorizada de ejecución

1. Actualizar/reconciliar fuente sin perder evidencia; rama de código limpia y
   aislada, sin tocar trabajo #2789. No reutilizar entornos o credenciales ajenos.
2. Autorizar y materializar entorno, fixtures/roles/archivos sintéticos y loader.
3. Implementar contexto/shell/checks/API/UI completos con tests y snapshots reales.
4. Fijar y aceptar referencia/candidato; ejecutar contratos y pruebas visuales,
   permisos, persistencia y efectos; registrar fallos, omisiones y diferencias.
5. Activar/publicar solo mediante autorización posterior; baseline o CI verdes no
   autorizan merge/deploy ni declaran toda la épica terminada.

La implementación sigue fuera de E2. Esta preparación no exige detallar los215
contratos antes del piloto ni vuelve a presentar E1/E2 como decisión pendiente.
Parar únicamente por cambio importante de negocio/alcance/seguridad/costo,
autorización externa/irreversible necesaria o imposibilidad real de aislamiento.

## Verificación de esta preparación

Auditoría estática contra ref local y registro de nueve rutas; relaciones de
fixtures, partición de casos, permisos, conteos y enlaces comprobados documentalmente.
Ningún API, workspace, Form React, dato, DB, fichero sintético, servidor, build,
test de aplicación, Chromium, screenshot, CI o despliegue ejecutado.

- [Fichas F1–F8](2026-10-27-2785-fichas-prioritarias.md).
- [Preparación de lectura](2026-10-27-2799-2802-paridad-insumos.md).
- [Índice vigente](2026-10-27-2785-cierre-progresivo-de-contratos.md).
