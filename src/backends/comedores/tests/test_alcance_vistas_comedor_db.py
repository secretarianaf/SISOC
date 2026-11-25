"""Regresiones de alcance: vistas que resolvían un comedor (o un hijo) por pk."""

from datetime import date

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import RequestFactory

from comedores.models import Comedor, PrestacionAlimentariaConformidad
from comedores.views.comedor import descargar_certificacion_prestaciones_web
from core.models import Provincia
from expedientespagos import views as exp_views
from expedientespagos.models import ExpedientePago
from intervenciones import views as int_views
from intervenciones.models.intervenciones import Intervencion
from rendicioncuentasmensual import views as rend_views
from rendicioncuentasmensual.models import (
    DocumentacionAdjunta,
    RendicionCuentaMensual,
)
from users.models import Profile, ProfileTerritorialScope

pytestmark = pytest.mark.django_db


def _usuario_provincial(username, provincia):
    user = User.objects.create_user(username=username, password="x")
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.provincia = provincia
    profile.es_usuario_provincial = True
    profile.save()
    ProfileTerritorialScope.objects.create(profile=profile, provincia=provincia)
    return user


@pytest.fixture(name="escenario")
def escenario_fixture():
    prov_a = Provincia.objects.create(nombre="Alcance A")
    prov_b = Provincia.objects.create(nombre="Alcance B")
    comedor = Comedor.objects.create(nombre="Comedor A", provincia=prov_a)
    return {
        "comedor": comedor,
        "en_alcance": _usuario_provincial("prov_a", prov_a),
        "fuera": _usuario_provincial("prov_b", prov_b),
        "super": User.objects.create_superuser("root", "r@x.com", "x"),
    }


def _req(user, method="get", data=None):
    factory = RequestFactory()
    request = getattr(factory, method)("/", data or {})
    request.user = user
    return request


def _setup(view_cls, request, **kwargs):
    view = view_cls()
    view.setup(request, **kwargs)
    return view


# --- comedores: certificación de prestaciones -------------------------------


def _certificacion(comedor):
    return PrestacionAlimentariaConformidad.objects.create(
        comedor=comedor,
        periodo=date(2026, 5, 1),
        conforme=True,
        certificacion_pdf=SimpleUploadedFile("c.pdf", b"%PDF-1.4"),
    )


def test_certificacion_prestaciones_fuera_de_alcance_404(escenario, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    cert = _certificacion(escenario["comedor"])
    with pytest.raises(Http404):
        descargar_certificacion_prestaciones_web(
            _req(escenario["fuera"]), escenario["comedor"].pk, cert.pk
        )


def test_certificacion_prestaciones_en_alcance_200(escenario, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    cert = _certificacion(escenario["comedor"])
    response = descargar_certificacion_prestaciones_web(
        _req(escenario["en_alcance"]), escenario["comedor"].pk, cert.pk
    )
    assert response.status_code == 200
    response.close()


# --- intervenciones -----------------------------------------------------------


def _intervencion(comedor):
    return Intervencion.objects.create(comedor=comedor)


def test_intervencion_detalle_fuera_de_alcance_404(escenario):
    view = _setup(
        int_views.IntervencionDetailView,
        _req(escenario["fuera"]),
        pk=escenario["comedor"].pk,
    )
    with pytest.raises(Http404):
        view.get_context_data()


def test_intervencion_detalle_en_alcance_ok(escenario):
    view = _setup(
        int_views.IntervencionDetailView,
        _req(escenario["en_alcance"]),
        pk=escenario["comedor"].pk,
    )
    assert view.get_context_data()["object"] == escenario["comedor"]


def test_intervencion_crear_fuera_de_alcance_404(escenario):
    view = _setup(
        int_views.IntervencionCreateView,
        _req(escenario["fuera"], "post"),
        pk=escenario["comedor"].pk,
    )
    with pytest.raises(Http404):
        view.get_form_kwargs()


def test_intervencion_editar_fuera_de_alcance_404(escenario):
    inter = _intervencion(escenario["comedor"])
    view = _setup(
        int_views.IntervencionUpdateView,
        _req(escenario["fuera"]),
        pk=inter.pk,
        pk2=escenario["comedor"].pk,
    )
    with pytest.raises(Http404):
        view.get_object()


def test_intervencion_editar_en_alcance_y_cruza_comedor(escenario):
    inter = _intervencion(escenario["comedor"])
    otro = Comedor.objects.create(
        nombre="Otro A", provincia=escenario["comedor"].provincia
    )
    ok = _setup(
        int_views.IntervencionUpdateView,
        _req(escenario["en_alcance"]),
        pk=inter.pk,
        pk2=escenario["comedor"].pk,
    )
    assert ok.get_object() == inter
    # IDOR: intervención de un comedor presentada bajo otro comedor en alcance.
    cruzado = _setup(
        int_views.IntervencionUpdateView,
        _req(escenario["en_alcance"]),
        pk=inter.pk,
        pk2=otro.pk,
    )
    with pytest.raises(Http404):
        cruzado.get_object()


def test_intervencion_borrar_fuera_de_alcance_404_y_en_alcance_ok(escenario):
    inter = _intervencion(escenario["comedor"])
    kwargs = {"comedor_id": escenario["comedor"].pk, "intervencion_id": inter.pk}
    fuera = _setup(int_views.IntervencionDeleteView, _req(escenario["fuera"]), **kwargs)
    with pytest.raises(Http404):
        fuera.get_object()
    dentro = _setup(
        int_views.IntervencionDeleteView, _req(escenario["en_alcance"]), **kwargs
    )
    assert dentro.get_object() == inter


def test_intervencion_borrar_no_cruza_comedor(escenario):
    inter = _intervencion(escenario["comedor"])
    otro = Comedor.objects.create(
        nombre="Otro A2", provincia=escenario["comedor"].provincia
    )
    view = _setup(
        int_views.IntervencionDeleteView,
        _req(escenario["en_alcance"]),
        comedor_id=otro.pk,
        intervencion_id=inter.pk,
    )
    with pytest.raises(Http404):
        view.get_object()


def test_intervencion_archivos_y_detalle_individual_fuera_de_alcance_404(escenario):
    inter = _intervencion(escenario["comedor"])
    with pytest.raises(Http404):
        int_views.subir_archivo_intervencion(_req(escenario["fuera"], "post"), inter.pk)
    with pytest.raises(Http404):
        int_views.eliminar_archivo_intervencion(
            _req(escenario["fuera"], "post"), inter.pk
        )
    view = _setup(
        int_views.IntervencionDetailIndividualView,
        _req(escenario["fuera"]),
        pk=inter.pk,
    )
    with pytest.raises(Http404):
        view.get_context_data()
    ok = _setup(
        int_views.IntervencionDetailIndividualView,
        _req(escenario["en_alcance"]),
        pk=inter.pk,
    )
    assert ok.get_context_data()["intervencion"] == inter


# --- expedientes de pago --------------------------------------------------------


def _expediente(comedor):
    return ExpedientePago.objects.create(
        comedor=comedor,
        expediente_convenio="CONV-1",
        mes_pago="Marzo",
        ano=2026,
        prestaciones_mensuales_desayuno=0,
        prestaciones_mensuales_almuerzo=0,
        prestaciones_mensuales_merienda=0,
        prestaciones_mensuales_cena=0,
        monto_mensual_desayuno=0,
        monto_mensual_almuerzo=0,
        monto_mensual_merienda=0,
        monto_mensual_cena=0,
    )


def test_expedientes_lista_y_alta_fuera_de_alcance_404(escenario):
    lista = _setup(
        exp_views.ExpedientesPagosListView,
        _req(escenario["fuera"]),
        pk=escenario["comedor"].pk,
    )
    with pytest.raises(Http404):
        lista.get_queryset()
    alta = _setup(
        exp_views.ExpedientesPagosCreateView,
        _req(escenario["fuera"], "post"),
        pk=escenario["comedor"].pk,
    )
    with pytest.raises(Http404):
        alta.post(alta.request)
    assert not ExpedientePago.objects.exists()


def test_expedientes_lista_en_alcance_ok(escenario):
    lista = _setup(
        exp_views.ExpedientesPagosListView,
        _req(escenario["en_alcance"]),
        pk=escenario["comedor"].pk,
    )
    assert list(lista.get_queryset()) == []


@pytest.mark.parametrize(
    "view_cls",
    [
        exp_views.ExpedientesPagosDetailView,
        exp_views.ExpedientesPagosUpdateView,
        exp_views.ExpedientesPagosDeleteView,
    ],
)
def test_expedientes_hijo_por_pk_respeta_alcance(escenario, view_cls):
    exp = _expediente(escenario["comedor"])
    fuera = _setup(view_cls, _req(escenario["fuera"]), pk=exp.pk)
    with pytest.raises(Http404):
        fuera.get_object()
    dentro = _setup(view_cls, _req(escenario["en_alcance"]), pk=exp.pk)
    assert dentro.get_object() == exp
    root = _setup(view_cls, _req(escenario["super"]), pk=exp.pk)
    assert root.get_object() == exp


# --- rendición mensual ------------------------------------------------------------


def _rendicion(comedor):
    return RendicionCuentaMensual.objects.create(
        comedor=comedor, mes=6, anio=2026, estado=RendicionCuentaMensual.ESTADO_REVISION
    )


def test_rendicion_lista_y_alta_fuera_de_alcance_404(escenario):
    lista = _setup(
        rend_views.RendicionCuentaMensualListView,
        _req(escenario["fuera"]),
        comedor_id=escenario["comedor"].pk,
    )
    with pytest.raises(Http404):
        lista.get_context_data(object_list=[])
    alta = _setup(
        rend_views.RendicionCuentaMensualCreateView,
        _req(escenario["fuera"], "post"),
        comedor_id=escenario["comedor"].pk,
    )
    with pytest.raises(Http404):
        alta.form_valid(None)
    assert not RendicionCuentaMensual.objects.exists()


@pytest.mark.parametrize(
    "view_cls",
    [
        rend_views.RendicionCuentaMensualDetailView,
        rend_views.RendicionCuentaMensualUpdateView,
        rend_views.RendicionCuentaMensualDeleteView,
    ],
)
def test_rendicion_hijo_por_pk_respeta_alcance(escenario, view_cls):
    rendicion = _rendicion(escenario["comedor"])
    fuera = _setup(view_cls, _req(escenario["fuera"]), pk=rendicion.pk)
    with pytest.raises(Http404):
        fuera.get_object()
    dentro = _setup(view_cls, _req(escenario["en_alcance"]), pk=rendicion.pk)
    assert dentro.get_object() == rendicion


@pytest.mark.parametrize(
    "view_cls,metodo",
    [
        (rend_views.RendicionCuentaMensualDownloadPdfView, "get"),
        (rend_views.RendicionPdfDescargaSolicitarView, "post"),
        (rend_views.RendicionPdfDescargaEstadoView, "get"),
    ],
)
def test_rendicion_pdf_fuera_de_alcance_404(escenario, view_cls, metodo):
    rendicion = _rendicion(escenario["comedor"])
    request = _req(escenario["fuera"], metodo)
    view = _setup(view_cls, request, pk=rendicion.pk)
    with pytest.raises(Http404):
        getattr(view, metodo)(request, pk=rendicion.pk)


def test_rendicion_pdf_estado_en_alcance_ok(escenario):
    rendicion = _rendicion(escenario["comedor"])
    request = _req(escenario["en_alcance"])
    view = _setup(rend_views.RendicionPdfDescargaEstadoView, request, pk=rendicion.pk)
    response = view.get(request, pk=rendicion.pk)
    assert response.status_code == 200


def test_rendicion_documento_y_eliminar_archivo_respetan_alcance(
    escenario, settings, tmp_path
):
    settings.MEDIA_ROOT = str(tmp_path)
    rendicion = _rendicion(escenario["comedor"])
    doc = DocumentacionAdjunta.objects.create(
        nombre="a.pdf",
        rendicion_cuenta_mensual=rendicion,
        archivo=SimpleUploadedFile("a.pdf", b"%PDF-1.4"),
    )
    request = _req(escenario["fuera"])
    view = _setup(rend_views.RendicionDocumentoVerView, request, pk=doc.pk)
    with pytest.raises(Http404):
        view.get(request, pk=doc.pk)

    with pytest.raises(Http404):
        rend_views.eliminar_archivo(_req(escenario["fuera"], "post"), doc.pk)
    doc.refresh_from_db()
    assert doc.deleted_at is None

    ok = rend_views.eliminar_archivo(_req(escenario["en_alcance"], "post"), doc.pk)
    assert ok.status_code == 200
