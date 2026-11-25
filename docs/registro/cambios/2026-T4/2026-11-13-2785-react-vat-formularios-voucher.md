# Cambio: formularios de alta de voucher, alta masiva y parametría de VAT en React sobre G1 v1 (#2785, V01.02)

## Alcance

V01.02 del [contrato V01/V08](../../../plans/2026-T4/2026-11-12-2785-vat-v01-v08-m2.md), sobre el
[protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md): `/vat/vouchers/asignar/`,
`/vat/vouchers/asignar-masivo/` y `/vat/vouchers/parametrias/nueva/`. Escribe por las vistas nativas
`VoucherCreateView`, `VoucherAsignacionMasivaView` y `VoucherParametriaCreateView`, sin tocar vistas, formularios,
servicios, plantillas ni URLs nativas. No activa React en producción.

Archivos:

- `src/backends/vat/VAT/web_api_voucher_forms.py` (rutas en `web_api_urls.py`); `campo_formulario` de
  `web_api_common.py` suma `tag="radio"` (con el `id` de cada opción) y `help_text`; `url_registry.json` regenerado y
  `config/middlewares/admindocs.py`.
- `src/backends/vat/VAT/web_preview_vat.py`: entradas de la vista previa local.
- `src/frontends/apps/sisoc/src/routes/vatVouchersForm.tsx`, `vatParametriaFormStyles.ts` (el `<style>` nativo,
  literal) y `vatFormShared.tsx` (radio, ayuda y envío configurable), registrado en `routes/index.ts`.
- Pruebas: `test_web_vat_voucher_forms_v01.py`, `test_web_preview_vat_v01_v08.py` (ampliado) y
  `vatVouchersForm.test.tsx`.

## Comportamiento

- Acceso: sesión (401), compuerta G1, `VAT.add_voucher` (403) y CSRF en el POST, como las tres rutas nativas.
- Alta: `form_valid` nativo llama a `VoucherService.crear_voucher` y encola «Voucher asignado exitosamente a <nombre>.»;
  si el servicio falla, 400 con el formulario ligado y «Error al crear el voucher: …». `?ciudadano=<id>` precarga el
  ciudadano. La fecha de vencimiento debe ser posterior a hoy.
- Alta masiva: la API proyecta lo que la plantilla recibe (formulario y resultado); un DNI con voucher activo cuenta en
  «Ya tenían», uno inexistente en «No encontrados». Datos inválidos (sin DNIs o más de 500): 400 sin crear nada.
- Parametría: guarda `creado_por` con el usuario y encola «Parametría '<nombre>' creada correctamente.».
- Los formularios no llevan `novalidate` (como las plantillas): el navegador valida los campos requeridos antes de
  enviar. Los errores de un campo se unen con coma.
- Quirks nativos conservados: etiquetas sin `for` en los formularios genéricos, selector de ciudadano con todos los
  ciudadanos.

## Verificación

- Backend (imagen fijada, sin red): pruebas nuevas (incluida la comparación nativo contra API del mismo voucher y del
  resultado masivo), `vat` web, `test_web_gate`, `test_backend_proxy` y `test_servicios_backends`; `black`, `pylint`
  y `makemigrations --check` sin cambios.
- Frontend: `vitest --project sisoc`, `tsc`, `eslint` y build.
- G1 de extremo a extremo: 403 sin `add_voucher`, 400 inválido, CSRF y alta de parametría persistida.
- Comparación visual nativo contra React (alta, con ciudadano, con errores, masiva, masiva con resultado, parametría y
  parametría con errores; escritorio y móvil) y guardas: sin diferencias.
