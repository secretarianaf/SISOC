# Acompañamiento Territorial / PNUD (N22): diagramas

Diagramas interactivos del flujo PNUD, generados con [Archify](https://github.com/tt-a1i/archify). Todos pasan la validación `showcase` (9/9 checks, sin errores ni warnings) y el `visual-check`. El detalle y las decisiones pendientes están en el issue #2583.

- Cada `.html` es autocontenido: tiene tema claro/oscuro, zoom, búsqueda, foco y trazado de rutas. La interfaz del visor está en inglés; el contenido, en español.
- Cada `.json` es la fuente del diagrama. Para regenerarlo: `node bin/archify.mjs deliver <tipo> <x>.json <x>.html --quality showcase`.
- Los `.light.png` / `.dark.png` son capturas a 1440×900.

## SISOC (backend, PR #2582 · 151bf3272)

| Diagrama | Tipo | Qué muestra |
|---|---|---|
| [sisoc-arquitectura-n22](sisoc/sisoc-arquitectura-n22.html) | architecture | Componentes de N22. La app territorial llama a la API territorial (Token DRF, alcance por zona), que pasa por las validaciones y guarda en `SeguimientoPnud`; aparecen también el storage de firmas y el backoffice del coordinador. El legajo del Comedor no se modifica. |
| [sisoc-secuencia-api-n22](sisoc/sisoc-secuencia-api-n22.html) | sequence | El contrato de la API: firma, alta idempotente por `client_uuid`, validaciones que responden 400, GET que solo devuelve los datos del técnico propio y PATCH con bloqueo que responde 409 si ya está Validado. |
| [sisoc-estados-seguimiento-pnud](sisoc/sisoc-estados-seguimiento-pnud.html) | lifecycle | `estado_validacion`: Pendiente validación coordinador → A subsanar → Validado (terminal). |
| [sisoc-revision-coordinador](sisoc/sisoc-revision-coordinador.html) | workflow | La revisión en el backoffice: listado → detalle → Revisar → correcciones o Validado. |
| [sisoc-ruteo-programa](sisoc/sisoc-ruteo-programa.html) | workflow | Cómo `linea_pnud` decide qué formularios se permiten y en qué casos responde 400. |

## App territorial (Gestionar#11 · ffb5fd7 · v1.1.41)

| Diagrama | Tipo | Qué muestra |
|---|---|---|
| [pwa-flujo-acompanamiento](pwa/pwa-flujo-acompanamiento.html) | workflow | Entrada, Inicial o Seguimiento, programa en SISOC, y según corresponda Virtual/Presencial y Vianda/Módulo, hasta el formulario. |
| [pwa-flujo-revision](pwa/pwa-flujo-revision.html) | workflow | Guardar, envío, revisión, corrección y, una vez Validado, el PDF. |
| [pwa-arquitectura](pwa/pwa-arquitectura.html) | architecture | Pantallas, formularios, caché y outbox, sync, cliente N22 y PDF. |
| [pwa-secuencia-sync](pwa/pwa-secuencia-sync.html) | sequence | Guardado offline y envío: firma y después POST o PATCH. |
| [pwa-secuencia-error](pwa/pwa-secuencia-error.html) | sequence | Refresco del detalle sin pisar correcciones y error de envío (409). |
| [pwa-estados-visibles](pwa/pwa-estados-visibles.html) | lifecycle | Los estados que ve el técnico, incluidos Error de envío y el seguimiento de otro técnico (ajeno). |
| [pwa-datos-formulario](pwa/pwa-datos-formulario.html) | dataflow | De dónde sale cada dato: lo precargado de SISOC, la ficha del espacio y lo que carga el técnico. |
