# 2026-09-30 - INET/VAT: corrección visual de sedes y cascada de localidades

## Resumen

Se corrigen ajustes visuales y de interacción derivados de las mejoras INET de septiembre:

- Se elimina del modal de cursos un comentario de template que se renderizaba como texto visible.
- En el modal y formulario de ubicaciones, `Localidad` queda deshabilitada hasta elegir un `Departamento`.
- Al seleccionar un departamento, se cargan por AJAX las localidades asociadas.
- Si la provincia de referencia tiene un único departamento disponible, se selecciona automáticamente y se cargan sus localidades.
- Los departamentos/localidades disponibles se resuelven desde la provincia de la ubicación principal del centro, con fallback al legajo del centro cuando no existe ubicación principal.

## Archivos relevantes

- `VAT/forms.py`
- `VAT/views/institucion.py`
- `VAT/templates/vat/centros/centro_detail.html`
- `VAT/templates/vat/institucion/ubicacion_form.html`
- `VAT/templates/vat/centros/partials/centro_cursos_panel.html`
- `VAT/tests.py`

## Validación

- `docker compose exec django pytest VAT/tests.py -q -k "sede_toma_departamentos or centro_detail_modal_ubicacion or ajax_municipios_por_centro or sede_admite or sede_en_edicion"`
- `docker compose exec django python manage.py check`
