# Cambio: los selects de ciudadano e inscripción de VAT buscan por documento (#2889)

## Alcance

El issue #2889 reporta respuestas 504 en las vistas de VAT y CDI en PRD. Este cambio cubre la parte de VAT cuya causa se confirmó en el código: cuatro formularios renderizaban una tabla entera en un `<select>`.

| Formulario | Campo | Tabla que cargaba |
|---|---|---|
| `InscripcionForm` | `ciudadano` | `Ciudadano` completa |
| `InscripcionOfertaForm` | `ciudadano` | `Ciudadano` completa |
| `VoucherForm` | `ciudadano` | `Ciudadano` completa |
| `ResultadoEvaluacionForm` | `inscripcion` | `Inscripcion` completa, con una consulta extra por fila en `__str__` |

`InetEstadoView` también cargaba todo el padrón: serializa `InscripcionForm` entero aunque solo use `estado` y `observaciones`.

Rutas principales:

- `src/backends/vat/VAT/forms.py`: `BusquedaRemotaFormMixin`.
- `src/backends/vat/VAT/services/buscador_ciudadano_service.py`: `opciones_ciudadano` y `opciones_inscripcion`.
- `src/backends/vat/VAT/views/buscador_ciudadano.py`: `OpcionesCiudadanoView` y `OpcionesInscripcionView`.
- `src/backends/vat/VAT/urls.py` y `src/backends/config/url_registry.json`: rutas `vat_ajax_buscar_ciudadanos` y `vat_ajax_buscar_inscripciones`.

Quedan fuera de este cambio, y siguen abiertos en #2889: `/api/inet/comisiones/`, los 504 de CDI y el dimensionamiento de workers.

## Comportamiento

- Los campos ya no muestran una lista: se escribe el DNI o el pasaporte y se elige entre hasta 20 resultados. Ciudadano pide al menos 6 caracteres e inscripción, al menos 7 dígitos del DNI.
- La búsqueda de ciudadano no acepta nombres ni apellidos, porque un `icontains` recorrería todo el padrón. Por eso no se reutilizó `api_buscar_ciudadanos`, que además exige `ciudadanos.view_ciudadano`.
- La búsqueda de inscripciones respeta el alcance territorial del usuario (`base_inscripciones_queryset_for_user`). Antes, el `<select>` mostraba todas. La validación del POST no cambia: acepta cualquier inscripción existente.
- Las rutas nuevas exigen los permisos de VAT de los formularios que las usan.
- Al editar, o al llegar con `?ciudadano=<id>`, la opción elegida se sigue mostrando.
- Los mensajes propios de Select2, como el de caracteres mínimos, se ven en inglés, igual que en el resto de los selects del sitio.

No hay migraciones ni cambios de datos.

## Verificación

Validado en local, en un contenedor efímero con SQLite y sin datos de PRD:

- `pytest src/backends/vat src/backends/kernel/tests/test_health_urls.py -n auto`: 606 pasan, 4 se saltean y 2 fallan.
- Los 2 fallos son `test_listado_de_vouchers_sin_n_mas_1` y `test_listado_de_inscripciones_sin_n_mas_1`, de `src/backends/vat/tests/test_admin_operaciones_vat.py`. Son preexistentes: con el código de `HEAD` dan el mismo resultado (24 y 23 consultas, con un tope de 20).
- `src/backends/vat/tests/test_vat_busqueda_remota.py`: 30 tests pasan. Con el `forms.py` original fallan 8, los que describen el bug.
- `pylint` da 10/10 en el servicio, las vistas y los tests nuevos. `black --check` pasa en los archivos tocados.
- `url_registry.json` se regeneró con `generar_registro_urls`, quitando `media/` y `static/`, que aparecen solo con DEBUG local.

Sin verificar:

- El widget en un navegador real.
- La mejora en un entorno con datos de PRD.
- Que `/health/urls/` deje de mostrar 504.
