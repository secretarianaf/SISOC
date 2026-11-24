# Cambio: vouchers, parametrías y evaluaciones de VAT en React sobre G1 v1 (#2785, V01.01 y V08.01)

## Alcance

Primera entrega de V01 y V08 del
[contrato V01/V08](../../../plans/2026-T4/2026-11-12-2785-vat-v01-v08-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): la lista y el detalle de
vouchers (`/vat/vouchers/`, `/vat/vouchers/<pk>/`), la lista de parametrías
(`/vat/vouchers/parametrias/`) y la lista y el detalle de evaluaciones (`/vat/evaluaciones/`,
`/vat/evaluaciones/<pk>/`). La recarga y la cancelación del detalle de voucher siguen siendo los
POST nativos (`vat_voucher_recargar`, `vat_voucher_cancelar`); React solo dibuja sus formularios.
No cambia vistas, servicios, modelos, plantillas ni URLs nativas, ni la API INET. No activa React en
producción. Quedan sin migrar (ver «Pendiente» del contrato): altas y asignaciones, detalle de
parametría, resultados de evaluación, reporte de inscripciones/asistencias y exportaciones.

Archivos:

- `src/backends/vat/VAT/web_api_common.py`, `web_api_vouchers.py` y `web_api_evaluaciones.py`, con las
  rutas sumadas a `web_api_urls.py`; `src/backends/config/url_registry.json` regenerado y
  `src/backends/config/middlewares/admindocs.py` (rutas nuevas fuera del atajo HEAD).
- `src/backends/vat/VAT/web_preview_vat.py`: entradas React sin montar, assets en `/vat/react/assets/`.
- `src/frontends/apps/sisoc/src/routes/vatShared.tsx`, `vatVouchers.tsx` y `vatEvaluaciones.tsx`,
  registrados en `routes/index.ts`.
- Pruebas: `test_web_vat_vouchers_v01.py`, `test_web_vat_evaluaciones_v08.py`,
  `test_web_preview_vat_v01_v08.py`, `vatVouchers.test.tsx` y `vatEvaluaciones.test.tsx`.

## Comportamiento

- `GET /api/web/vat/vouchers/`, `.../vouchers/<pk>/`, `.../vouchers/parametrias/`,
  `.../evaluaciones/` y `.../evaluaciones/<pk>/` ejecutan la vista nativa (`setup`,
  `get_queryset`, `get_context_data`) y proyectan su contexto: filtros `estado`, `programa` y
  `busqueda`/`q`, 20 por página, 404 con página inválida o id inexistente. Fechas `d/m/Y`, hora
  local y coma decimal salen del motor de plantillas.
- Acceso: sesión (401), compuerta G1, `IsAuthenticated` y después el decorador de la ruta nativa
  (`VAT.view_voucher` para vouchers y parametrías, `VAT.view_evaluacion` para evaluaciones; 403).
  No hay alcance por CFP, igual que hoy (ver
  [brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)).
  Las vistas quedan fuera del contrato OpenAPI de INET (`schema = None`).
- El detalle de voucher ofrece «Recarga manual» y «Cancelar voucher» solo con `change_voucher` y
  según el estado, como el template; la cancelación pregunta `¿Cancelar este voucher?` antes de
  enviar. Los mensajes nativos en cola se muestran como toast.
- Quirks nativos conservados y fijados por pruebas: la paginación descarta `busqueda` de los
  enlaces de página; la lista de parametrías no filtra por `busqueda`; el historial no muestra
  descripción (el template lee un campo que no existe); el detalle de evaluación muestra Editar y
  Eliminar sin mirar permisos; el motivo de una recarga se imprime como la clave (`manual`).
- Hallazgo: `pylint` marca `config/middlewares/admindocs.py:50` por línea larga (273 de 150),
  preexistente en `HEAD`; no se toca.

## Verificación

- Backend (imagen fijada, sin red): `vat/tests` completo más `kernel/tests/test_web_gate.py`,
  `test_backend_proxy.py` y `test_servicios_backends.py`: 327 pruebas, todas en verde (en la base, las 14 pruebas
  nuevas de API fallan); `black` y `pylint` 10/10 en los archivos tocados salvo la línea preexistente de
  `admindocs.py`; `makemigrations --check` sin cambios.
- Frontend: `vitest --project sisoc` completo (82 archivos, 862 pruebas), `tsc`, `eslint` y build de Vite en verde.
- G1 de extremo a extremo (core más runtime de VAT): anónimo 401, sin permiso 403, requisito pendiente 403,
  constancia falsificada ignorada, POST sin CSRF 403 y camino feliz de lista, detalle (404 inexistente),
  parametrías y evaluaciones, todo en verde.
- Comparación visual contra el HTML nativo (11 casos, escritorio y móvil, más 5 guardas): estructura, orden de
  Tab y geometría iguales (máximo 0,02 px) y diferencia de píxeles de 0,000 %; solo las exenciones del arnés
  (nombre accesible del logo, menú móvil).
- No cubierto: el POST nativo de recarga y cancelación no se ejercitó en navegador desde la pantalla React (los
  formularios envían a la vista nativa sin cambios; la prueba de backend cubre el mensaje en el detalle), y la
  tabla de usos del detalle no tiene filas en la comparación visual (cubierta por pruebas unitarias).
