# Cambio: importación de expedientes de pago en React sobre G1 v1 (#2785, EX02)

## Alcance

Entregas EX02.02 (listado y detalle de lotes) y EX02.01 (subida y validación,
importación, borrado de datos importados y fechas de acreditación) del
[contrato EX01/EX02](../../../plans/2026-T4/2026-11-10-2785-expedientes-pagos-importacion-m2.md),
sobre el [protocolo G1 v1](../../decisiones/2026-11-06-2808-protocolo-g1-v1.md).
Los expedientes de un comedor (EX01) ya están en React y no se tocan.

No cambia vistas, formularios, servicios, modelos, plantillas ni URLs nativas
(a diferencia de lo propuesto en el contrato, no se extrae lógica de las vistas:
la API llama a las vistas nativas y lee sus mensajes, así que no hay riesgo de
regresión en las rutas nativas). No activa React en producción.

Archivos:

- `src/backends/comedores/importarexpediente/web_api_importarexpedientes.py` y
  `web_api_importarexpedientes_urls.py`, incluidos desde
  `src/backends/comedores/comedores_runtime/web_api_urls.py`;
  `src/backends/config/url_registry.json` regenerado con `generar_registro_urls`.
- `src/backends/config/middlewares/admindocs.py`: las rutas nuevas quedan fuera
  del atajo HEAD de admindocs.
- `src/backends/comedores/importarexpediente/web_preview_importarexpedientes.py`:
  entradas React sin montar, assets en `/importarexpedientes/react/assets/`.
- `src/frontends/apps/sisoc/src/routes/importarExpedientes.tsx`, registrado en
  `routes/index.ts`.
- Pruebas: `test_web_importarexpedientes_api.py`,
  `test_web_preview_importarexpedientes.py` (en `importarexpediente/`) y
  `routes/importarExpedientes.test.tsx`.

## Comportamiento

| Ruta | Comportamiento |
|---|---|
| `GET /api/web/comedores/importarexpedientes/` | `ImportarExpedienteListView`: filtros combinables, `busqueda`, 10 por página, página inválida 404 y completado de períodos guardado en el GET |
| `GET .../<pk>/` | `ImportarExpedienteDetalleListView`: contadores, errores por fila (20 por página), búsqueda por fila o texto, `can_update_acreditacion` |
| `GET/POST .../subir/` | `ImportExpedientesView`: validación sin escribir expedientes; rechazo 400 (409 si el expediente ya está cargado) con los mensajes en el cuerpo |
| `POST .../<pk>/importar/` | `ImportDatosView`: 200; 409 si ya fue importado (sin efectos); 400 archivo ilegible; 500 si falla el bloque |
| `POST .../<pk>/borrar-datos/` | `BorrarDatosImportadosView`: borrado físico, bandera en falso, estados sin revertir; repetirlo borra cero |
| `GET/POST .../<pk>/fechas-acreditacion/` | `ImportarFechasAcreditacionView`: errores 400 con los mensajes; éxito con redirect |

Acceso (sin cambios, ver
[brechas de acceso conservadas](../../decisiones/2026-11-10-2785-brechas-acceso-conservadas.md)):
G1 primero; después listado y detalle con `importarexpediente.view_archivosimportados`
(sin scope por usuario), subir, importar y borrar solo con sesión, y fechas con
uno de `importarexpediente.change_archivosimportados` o
`expedientespagos.change_expedientepago`.

Los mensajes de un redirect nativo al listado quedan en la sesión y los consume
el GET del listado (como la página nativa); los de un rechazo que se queda en el
formulario vuelven en el cuerpo. Cada acción pide la confirmación nativa, se
envía una sola vez, exige CSRF y ante un resultado incierto no reenvía.

## Verificación

Entorno sintético, sin red ni datos reales, imagen fijada.

- Backend: 30 pruebas de API y 4 de preview en verde; kernel (`test_web_gate`,
  `test_backend_proxy`, `test_servicios_backends`) 82 en verde;
  `makemigrations --check` sin cambios; black y pylint sin hallazgos nuevos.
- Frontend: 14 pruebas de ruta; Vitest completo (1487 en verde), `tsc`,
  ESLint y build de Vite.
- Visual (S13), 8 estados (listado, detalle con errores, detalle completado con
  y sin permiso de fechas, subida, subida rechazada, fechas, fechas rechazadas)
  en 1440x900 y 390x844: estructura, texto, orden de Tab y geometría iguales
  (desvío máximo 0,02 px). Única diferencia: «fechas rechazadas» en móvil, 1,39 %
  de píxeles, porque el aviso toastr nativo aún no es visible en la captura
  mientras el de React ya lo es (el elemento existe en ambos). Anónimo, sin
  permiso, sin permiso de fechas y lote inexistente responden igual.
- G1 de punta a punta (core y runtime de Comedores con gunicorn): anónimo 401,
  sin permiso 403, requisito pendiente 403, header falsificado ignorado, POST
  sin CSRF 403, listado y detalle 200, subida con solo sesión 200 y fechas con
  solo lectura 403.

## Limitaciones

- Subir, importar y borrar siguen abiertos a cualquier sesión y el listado sin
  scope por usuario: paridad con el nativo (decisión de brechas de acceso).
- `importar` ejecuta `aplicar_estados_por_lote` en la misma request, como hoy;
  su duración con volumen productivo no se midió.
- El AJAX nativo y la descarga del archivo siguen siendo rutas nativas.
- Diferencias del marco compartido (`SisocShell`): nombre accesible del logo y
  menú móvil.
