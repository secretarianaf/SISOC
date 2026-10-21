# Cambio: el admin vuelve a mostrar VAT y los demás verticales (#2741)

## Alcance

Al separar cada vertical en su propio servicio, el portal dejó de instalar sus
apps y su admin dejó de listarlas. Sólo Comedores (C3) y OCR (C4) montaron el
admin en su runtime y lo enlazaron desde el índice del portal. El issue pide
VAT (cursos y priorización); se extiende a todos los verticales con `admin.py`
para que ningún módulo quede afuera.

Se repite el patrón de OCR en `cdf`, `cdi`, `celiaquia`, `dispositivos`,
`inspecciones`, `pas`, `vat` y `vpsl`:

- `src/backends/<backend>/<backend>_runtime/urls.py` monta `admin.site.urls`
  fuera de `backend_urlpatterns`, así `settings_all` no lo duplica.
- `src/backends/config/backends.json` suma el prefijo `admin/<app_label>/` y un
  `admin_links` por vertical.

`datacalle` y `ticketera` no tienen `admin.py` y no se enlazan.

## Comportamiento

- En `/admin/` aparece "Administración de dominios" con un enlace por vertical
  (VAT en `/admin/VAT/`). Sólo se ve con `is_staff` y permisos del módulo
  (`has_module_perms`); el servicio dueño vuelve a validar los permisos.
- El portal reenvía sólo `/admin/<app_label>/` al dueño; el resto del admin
  (usuarios, grupos, auth) sigue en el portal.
- En la composición local (`settings_all`) el admin ya lista todas las apps y
  los enlaces no se muestran.

## Verificación

`src/backends/kernel/tests/test_admin_verticales.py`: prefijo y enlace en el
registro, reenvío del portal sólo al admin del dueño, enlace filtrado por
permisos, arranque de cada runtime con su admin registrado, y un chequeo de que
todo backend con `admin.py` tenga enlace.
