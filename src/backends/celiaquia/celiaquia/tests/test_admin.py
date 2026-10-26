from django.contrib import admin
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.test import RequestFactory

from celiaquia.models import ExpedienteCiudadano


class DummyAdminUser:
    is_active = True
    is_staff = True

    def has_perm(self, perm, obj=None):
        return True


def test_expedienteciudadano_admin_usa_raw_id_para_fks_de_alta_cardinalidad():
    # Issue #2789: sin selects gigantes, pero con raw_id_fields y no
    # autocomplete. En deploy /admin/autocomplete/ lo sirve el core, que no
    # instala celiaquia y responde 403 (test_admins_de_verticales_no_usan_autocomplete).
    model_admin = admin.site._registry[ExpedienteCiudadano]
    request = RequestFactory().get("/admin/celiaquia/expedienteciudadano/1/change/")
    request.user = DummyAdminUser()

    form = model_admin.get_form(request)

    for field_name in ("deleted_by", "expediente", "ciudadano", "subsanacion_usuario"):
        widget = form.base_fields[field_name].widget
        assert isinstance(widget, ForeignKeyRawIdWidget)
