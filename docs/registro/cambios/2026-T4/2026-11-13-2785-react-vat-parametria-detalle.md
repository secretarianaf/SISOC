# Cambio: detalle de parametría de voucher y asignaciones de VAT en React sobre G1 v1 (#2785, V01.01 y V01.03)

## Alcance

Cierre de V01 del [contrato V01/V08](../../../plans/2026-T4/2026-11-12-2785-vat-v01-v08-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): `/vat/vouchers/parametrias/<pk>/` (estadísticas,
vouchers asignados con búsqueda y paginación, métricas) y las asignaciones individual y masiva de la parametría. Lee y
escribe por `VoucherParametriaDetailView`, `VoucherParametriaAsignarView` y `VoucherParametriaAsignarMasivoView`, sin
tocar vistas, servicios, plantillas ni URLs nativas. No activa React en producción.

Archivos:

- `src/backends/vat/VAT/web_api_parametria_detail.py` (rutas en `web_api_urls.py`), `url_registry.json` regenerado y
  `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat.py`: entrada de vista previa del detalle.
- `src/frontends/apps/sisoc/src/routes/vatParametriaDetalle.tsx` y `vatParametriaDetailStyles.ts` (el `<style>` nativo,
  literal), registrado en `routes/index.ts`.
- Pruebas: `test_web_vat_parametria_detalle_v01.py`, `test_web_preview_vat_v01_v08.py` (ampliado) y
  `vatParametriaDetalle.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1 y `VAT.view_voucher` para el detalle (403, 404 si no existe); el panel de
  asignación aparece solo con `VAT.add_voucher`, que además exige el POST (403) junto con CSRF.
- El detalle conserva el cálculo nativo: totales por estado, créditos emitidos, usados y disponibles, porcentajes
  (`widthratio`), últimas cinco asignaciones y vouchers de a 20 por `vouchers_page`, con `busqueda` por nombre,
  apellido o DNI. Los enlaces de página repiten los demás parámetros y ponen `busqueda` primero, como
  `components/pagination.html`.
- Asignar corre la vista nativa: crea el voucher, reactiva uno agotado o vencido (recarga automática) o avisa si ya hay
  uno activo; la asignación masiva admite hasta 500 DNIs y resume «N creados, N reactivados, …». El POST responde con la
  redirección al detalle y el mensaje nativo aparece al recargarlo. Datos faltantes («Ingresá un DNI.», «No ingresaste
  ningún DNI.», «Máximo 500 DNIs por operación.») no guardan nada.
- Las pestañas Individual y Masiva cambian en el cliente, como el script de la plantilla.
- Quirk nativo conservado: el nombre de ciudadano de los mensajes usa `nombre_completo` (`Nombre Apellido`) y la lista de
  vouchers muestra el estado traducido con su insignia de color.

## Verificación

- Backend (imagen fijada, sin red): pruebas nuevas (incluida la comparación del escritor nativo con la API), `vat` web,
  `test_web_gate`, `test_backend_proxy` y `test_servicios_backends`; `black`, `pylint` y `makemigrations --check` sin
  cambios.
- Frontend: `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo: 401, 403, CSRF, 404, lectura y asignación persistida.
- Comparación visual nativo contra React (detalle, pestaña masiva, con búsqueda, vacío y solo lectura; escritorio y móvil)
  y guardas: sin diferencias.
