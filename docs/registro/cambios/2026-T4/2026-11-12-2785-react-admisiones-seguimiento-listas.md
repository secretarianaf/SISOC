# Cambio: listados técnico y legal de admisiones en React sobre G1 v1 (#2785, AD03.01, primera parte)

## Alcance

Páginas `comedores/admisiones/tecnicos/listar` y `comedores/admisiones/legales/listar`, según el
[contrato AD03](../../../plans/2026-T4/2026-11-10-2785-admisiones-circuito-tecnico-legal-ad03-m2.md).
No cambia vistas, servicios ni modelos nativos, ni activa React en producción. El editor técnico, el
detalle de admisión y el detalle legal quedan para las siguientes partes de AD03.01. Las brechas de
acceso se conservan tal cual, según la
[decisión](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md).

Archivos:

- `src/backends/comedores/admisiones/web_api_listas.py` y `web_api_seguimiento_urls.py`;
  `comedores_runtime/web_api_urls.py` monta `admisiones/`.
- `src/backends/comedores/admisiones/web_preview_seguimiento.py`: entrada local del GET nativo.
- `src/backends/config/url_registry.json` (regenerado) y `middlewares/admindocs.py`.
- `src/frontends/apps/sisoc/src/routes/admisionesSeguimiento.tsx`, `admisionesListas.tsx`
  (+ prueba) y su registro en `routes/index.ts`.
- Prueba: `test_web_api_listas_ad03.py`.

## Comportamiento

- `GET /api/web/comedores/admisiones/tecnicos/` y `.../legales/` ejecutan la vista nativa
  (`setup`, queryset con su alcance por actor, filtros, orden, preferencias de columnas, paginación
  de 10) y devuelven título, migas, configuración de filtros, favoritos, columnas, filas y mensajes.
  Una página inexistente es 404.
- Acceso igual al nativo: sesión web (G1) y alguno de `comedores.view_comedor`,
  `admisiones.view_admision` o `acompanamientos.view_informacionrelevante`; el listado legal acepta
  además `expedientespagos.view_expedientepago` (superusuario incluido).
- La insignia «Rectificar» o «Archivado» del botón «Ver» viaja como dato (`badge`) y no como marcado.
- Las migas conservan la particularidad nativa: `breadcrumb.html` lee `item.text`, que estos
  elementos no definen, por lo que el texto sale vacío y el primer enlace apunta al nombre de la URL.

## Verificación

Entorno sintético, sin red. Backend: pruebas de la API y del preview, `web_gate`, `backend_proxy` y
`servicios_backends`, `black`, `pylint` y `makemigrations --check`. Frontend: Vitest de `sisoc`
completo, `tsc`, ESLint y build. Visual (S13) y G1 de punta a punta sobre el árbol final.

## Limitaciones

- Diferencia de DOM nativa conservada como defecto del original: el atributo `title` del botón «Ver»
  con insignia queda roto por el marcado de la insignia; React dibuja la insignia como elemento y
  `title="Ver"`. El píxel no cambia (0,002 %).
- El resto de AD03 (editor, detalle, acciones técnicas y legales) queda para próximas entregas.
