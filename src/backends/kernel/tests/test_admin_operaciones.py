"""Issue #2789: operaciones de soporte del admin (core.admin_operaciones)."""

from auditlog.models import LogEntry
from django import forms
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.test import RequestFactory
import pytest

from core import admin_operaciones
from core.admin_base import SisocModelAdmin
from core.admin_operaciones import (
    Operacion,
    OperacionesAdminMixin,
    ejecutar_operacion,
)
from django.contrib import admin
from core.models import Nacionalidad


def _renombrar(obj, _usuario, datos):
    obj.nacionalidad = datos.get("nuevo_nombre") or f"{obj.nacionalidad} (ok)"
    obj.save(update_fields=["nacionalidad"])


def _renombrar_y_fallar(obj, _usuario, _datos):
    obj.nacionalidad = "a medias"
    obj.save(update_fields=["nacionalidad"])
    raise ValidationError("Transición inválida.")


RENOMBRAR = Operacion(
    slug="renombrar",
    titulo="Renombrar",
    ejecutar=_renombrar,
    campo_estado="nacionalidad",
    motivo_obligatorio=True,
    motivo_min_largo=5,
    campos=lambda: {"nuevo_nombre": forms.CharField(required=False)},
)


class NacionalidadOperacionesAdmin(OperacionesAdminMixin, SisocModelAdmin):
    operaciones = (RENOMBRAR,)


@pytest.fixture(name="model_admin")
def model_admin_fixture():
    return NacionalidadOperacionesAdmin(Nacionalidad, admin.site)


def _request(rf_method, superuser, data=None, path="/admin/core/nacionalidad/"):
    request = getattr(RequestFactory(), rf_method)(path, data or {})
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    request._messages = FallbackStorage(request)  # pylint: disable=protected-access
    request.user = superuser
    return request


@pytest.mark.django_db
def test_ejecuta_el_service_y_registra_auditlog_con_motivo(superuser):
    obj = Nacionalidad.objects.create(nacionalidad="Uruguaya")

    ok, errores = ejecutar_operacion(
        operacion=RENOMBRAR,
        objetos=[obj],
        usuario=superuser,
        datos={"motivo": "Pedido de soporte 123", "nuevo_nombre": "Oriental"},
    )

    assert ok == [obj] and errores == []
    obj.refresh_from_db()
    assert obj.nacionalidad == "Oriental"
    entrada = LogEntry.objects.get_for_object(obj).get()
    assert entrada.actor == superuser
    assert entrada.changes_dict == {"nacionalidad": ["Uruguaya", "Oriental"]}
    assert entrada.additional_data["operacion"] == "renombrar"
    assert entrada.additional_data["motivo"] == "Pedido de soporte 123"
    assert entrada.additional_data["datos"] == {"nuevo_nombre": "Oriental"}
    assert entrada.audittrail_meta.source == "admin:renombrar"


@pytest.mark.django_db
def test_error_del_service_revierte_el_registro_y_no_frena_el_lote(superuser):
    malo = Nacionalidad.objects.create(nacionalidad="Mala")
    bueno = Nacionalidad.objects.create(nacionalidad="Buena")
    operacion = Operacion(
        slug="mixta",
        titulo="Mixta",
        ejecutar=lambda o, u, d: (
            _renombrar_y_fallar(o, u, d) if o.pk == malo.pk else _renombrar(o, u, d)
        ),
    )

    ok, errores = ejecutar_operacion(
        operacion=operacion, objetos=[malo, bueno], usuario=superuser, datos={}
    )

    assert ok == [bueno]
    assert errores == [(malo, "Transición inválida.")]
    malo.refresh_from_db()
    assert malo.nacionalidad == "Mala"
    assert not LogEntry.objects.get_for_object(malo).exists()


@pytest.mark.django_db
def test_service_que_devuelve_false_cuenta_como_error(superuser):
    obj = Nacionalidad.objects.create(nacionalidad="X")
    operacion = Operacion(slug="nada", titulo="Nada", ejecutar=lambda o, u, d: False)

    ok, errores = ejecutar_operacion(
        operacion=operacion, objetos=[obj], usuario=superuser, datos={}
    )

    assert not ok
    assert errores == [(obj, admin_operaciones.SERVICE_SIN_CAMBIOS)]


@pytest.mark.django_db
def test_accion_de_detalle_pide_confirmacion_y_motivo(model_admin, superuser):
    obj = Nacionalidad.objects.create(nacionalidad="Chilena")

    pantalla = model_admin.operacion_renombrar(_request("get", superuser), str(obj.pk))
    sin_motivo = model_admin.operacion_renombrar(
        _request("post", superuser, {"confirmar_operacion": "1", "motivo": "no"}),
        str(obj.pk),
    )
    obj.refresh_from_db()
    nombre_tras_rechazo = obj.nacionalidad
    confirmada = model_admin.operacion_renombrar(
        _request(
            "post", superuser, {"confirmar_operacion": "1", "motivo": "Ticket 42"}
        ),
        str(obj.pk),
    )

    assert pantalla.status_code == 200
    assert pantalla.template_name == "admin/sisoc/confirmar_operacion.html"
    assert sin_motivo.status_code == 200
    assert sin_motivo.context_data["form"].errors["motivo"]
    assert nombre_tras_rechazo == "Chilena"
    assert confirmada.status_code == 302
    obj.refresh_from_db()
    assert obj.nacionalidad == "Chilena (ok)"


@pytest.mark.django_db
def test_accion_en_lote_respeta_el_tope(model_admin, superuser, monkeypatch):
    monkeypatch.setattr(admin_operaciones, "MAX_REGISTROS_POR_LOTE", 2)
    for nombre in ("A", "B", "C"):
        Nacionalidad.objects.create(nacionalidad=nombre)
    accion = model_admin.get_actions(_request("get", superuser))[
        "operacion_renombrar_lote"
    ][0]
    request = _request("post", superuser)

    respuesta = accion(model_admin, request, Nacionalidad.objects.all())

    assert respuesta is None
    assert "hasta 2 registros" in str(list(get_messages(request))[0])
    assert not Nacionalidad.objects.filter(nacionalidad__endswith="(ok)").exists()


@pytest.mark.django_db
def test_accion_en_lote_confirmada_procesa_la_seleccion(model_admin, superuser):
    objetos = [Nacionalidad.objects.create(nacionalidad=n) for n in ("A", "B")]
    accion = model_admin.get_actions(_request("get", superuser))[
        "operacion_renombrar_lote"
    ][0]
    request = _request(
        "post", superuser, {"confirmar_operacion": "1", "motivo": "Lote de prueba"}
    )

    respuesta = accion(
        model_admin,
        request,
        Nacionalidad.objects.filter(pk__in=[o.pk for o in objetos]),
    )

    assert respuesta.status_code == 302
    assert Nacionalidad.objects.filter(nacionalidad__endswith="(ok)").count() == 2
    assert LogEntry.objects.filter(additional_data__operacion="renombrar").count() == 2


@pytest.mark.django_db
def test_operaciones_se_publican_en_fila_detalle_y_lote(model_admin, superuser):
    request = _request("get", superuser)

    assert "operacion_renombrar" in model_admin.actions_row
    assert "operacion_renombrar" in model_admin.actions_detail
    assert "operacion_renombrar_lote" in model_admin.get_actions(request)
    # El campo de estado solo cambia por la operación.
    assert "nacionalidad" in model_admin.get_readonly_fields(request)


@pytest.mark.django_db
def test_historial_muestra_eventos_de_auditlog(auth_client, superuser):
    obj = Nacionalidad.objects.create(nacionalidad="Peruana")
    ejecutar_operacion(
        operacion=RENOMBRAR,
        objetos=[obj],
        usuario=superuser,
        datos={"motivo": "Corrección de soporte"},
    )

    response = auth_client.get(f"/admin/core/nacionalidad/{obj.pk}/history/")

    assert response.status_code == 200
    html = response.content.decode()
    assert "historial-auditlog" in html
    assert "Corrección de soporte" in html
