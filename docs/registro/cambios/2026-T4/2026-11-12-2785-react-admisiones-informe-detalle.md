# Cambio: detalle del informe técnico de admisión en React sobre G1 v1 (#2785, AD02.01, primera entrega)

## Alcance

Página de detalle `comedores/admision/informe_tecnico/<tipo>/<pk>/ver/`, según el
[contrato AD02](../../../plans/2026-T4/2026-10-28-2785-admisiones-informes-documentos-m2.md).
No cambia vistas, formularios, servicios ni modelos nativos, ni activa React en producción.
El alta/edición del informe, las acciones documentales y la generación de DOCX/PDF siguen
nativas; el detalle solo las enlaza. Las brechas de acceso se conservan tal cual, según la
[decisión](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md).

Archivos:

- `src/backends/comedores/admisiones/web_api_informes.py` y `web_api_informes_urls.py`;
  `comedores_runtime/web_api_urls.py` monta `admisiones/informes/`.
- `src/backends/comedores/admisiones/web_preview_informes.py`: entrada local del GET nativo.
- `src/backends/config/url_registry.json` (regenerado) y `middlewares/admindocs.py`.
- `src/frontends/apps/sisoc/src/routes/admisionesInformeDetalle.tsx` (+ prueba) y su
  registro en `routes/index.ts`.
- Prueba: `test_web_api_informe_detalle_ad02.py`.

## Comportamiento

- `GET /api/web/comedores/admisiones/informes/<tipo>/<pk>/` ejecuta `InformeTecnicoDetailView`
  (`setup`, `get_object`, `get_context_data`) y devuelve campos visibles, estado, observaciones
  de subsanación, enlaces de archivos y mensajes pendientes. Un informe inexistente o de otro
  tipo es 404.
- Acceso igual al nativo: sesión web (G1) y alguno de `comedores.view_comedor`,
  `admisiones.view_admision` o `acompanamientos.view_informacionrelevante` (superusuario
  incluido); sin alcance por objeto.
- Subir el DOCX editado y revisar el informe (estado y campos a subsanar) siguen siendo POST
  a la URL nativa, con sus reglas y mensajes; los modales y las validaciones del script de la
  plantilla se replican en React.

## Verificación

Entorno sintético, sin red. Backend: pruebas de `admisiones`, `web_gate`, `backend_proxy` y
`servicios_backends`, `black`, `pylint` y `makemigrations --check`. Frontend: Vitest de `sisoc`
completo, `tsc`, ESLint y build. La prueba de la API cubre acceso (anónimo, sin permiso, cada permiso
de lectura, superusuario), 404, mensajes y el POST nativo; la del preview cubre las guardas nativas.

## Limitaciones

- El resto de AD02 (editor de informes, documentos, complementario) queda para próximas entregas.
- Esta entrega no incluye verificación visual (S13) ni G1 de punta a punta; quedan para el cierre del lote.
