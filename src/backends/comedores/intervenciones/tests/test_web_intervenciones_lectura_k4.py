"""Web API (G1 v1) of the comedor intervention list, detail and file removal (CO02).

``/api/web/comedores/intervenciones/`` runs the native views of
``intervenciones.views`` and keeps the permission codes of their URLs.
"""

from datetime import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from acompanamientos.models.acompanamiento import Acompanamiento
from admisiones.models.admisiones import Admision
from catalogo_intervenciones.models import (
    SubIntervencion,
    TipoContacto,
    TipoDestinatario,
    TipoIntervencion,
)
from comedores.models import Comedor
from intervenciones.models.intervenciones import Intervencion

ROOT = "/api/web/comedores/intervenciones/"

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _usuario(nombre, *codes, superusuario=False):
    usuario = _ready(
        get_user_model().objects.create_user(nombre, is_superuser=superusuario)
    )
    for code in codes:
        app, codename = code.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return usuario


def _cliente(usuario, **kwargs):
    client = Client(**kwargs)
    client.force_login(usuario)
    return client


@pytest.fixture(name="lector")
def lector_fixture():
    return _usuario("lector_k4", "intervenciones.view_intervencion")


@pytest.fixture(name="web")
def web_fixture(lector):
    return _cliente(lector)


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor K4", codigo_de_proyecto="")


@pytest.fixture(name="catalogos")
def catalogos_fixture():
    tipo = TipoIntervencion.objects.create(nombre="Visita", programa="comedores")
    sub = SubIntervencion.objects.create(nombre="Inicial", tipo_intervencion=tipo)
    return {
        "tipo": tipo,
        "sub": sub,
        "destinatario": TipoDestinatario.objects.create(nombre="Titular"),
        "contacto": TipoContacto.objects.create(nombre="Presencial"),
    }


def _local(*partes):
    return timezone.make_aware(datetime(*partes))


def _intervencion(comedor, catalogos, **extra):
    datos = {
        "comedor": comedor,
        "tipo_intervencion": catalogos["tipo"],
        "subintervencion": catalogos["sub"],
        "destinatario": catalogos["destinatario"],
        "forma_contacto": catalogos["contacto"],
        "fecha": _local(2026, 10, 1, 23, 30),
        "observaciones": "Texto libre",
    }
    datos.update(extra)
    return Intervencion.objects.create(**datos)


def _admision(comedor, nro="", activa=True):
    admision = Admision.objects.create(
        comedor=comedor,
        activa=activa,
        enviado_acompaniamiento=True,
        estado_admision="iniciada",
    )
    Acompanamiento.objects.create(admision=admision, nro_convenio=nro)
    return admision


# --- Access --------------------------------------------------------------------


@pytest.mark.parametrize("sufijo", ["comedor/{c}/", "{i}/"])
def test_reads_require_the_session_and_the_native_permission(
    comedor, catalogos, sufijo
):
    intervencion = _intervencion(comedor, catalogos)
    url = ROOT + sufijo.format(c=comedor.pk, i=intervencion.pk)

    assert Client().get(url).status_code in (401, 403)
    sin_permiso = _cliente(_usuario("sin_permiso_k4", "comedores.view_comedor"))
    assert sin_permiso.get(url).status_code == 403
    assert (
        _cliente(_usuario("lector2_k4", "intervenciones.view_intervencion"))
        .get(url)
        .status_code
        == 200
    )
    assert _cliente(_usuario("root_k4", superusuario=True)).get(url).status_code == 200


# --- List ----------------------------------------------------------------------


def test_list_projects_the_native_page(web, comedor, catalogos):
    intervencion = _intervencion(comedor, catalogos)
    _intervencion(comedor, catalogos, subintervencion=None)
    otro = Comedor.objects.create(nombre="Otro")
    _intervencion(otro, catalogos)

    respuesta = web.get(f"{ROOT}comedor/{comedor.pk}/")

    assert respuesta.status_code == 200
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert data["comedor"] == {
        "id": comedor.pk,
        "nombre": "Comedor K4",
        "url": reverse("comedor_detalle", args=[comedor.pk]),
    }
    assert len(data["results"]) == 2
    fila = next(r for r in data["results"] if r["id"] == intervencion.pk)
    # 23:30 local on Oct 1st: the localized day, not the UTC one.
    assert fila == {
        "id": intervencion.pk,
        "fecha": "01/10/2026",
        "tipo_intervencion": "Visita",
        "subintervencion": "Inicial",
        "destinatario": "Titular",
        "forma_contacto": "Presencial",
        "tiene_documentacion": False,
        "url": f"/intervencion/detalle/{intervencion.pk}/",
        "url_eliminar": None,
    }
    # Native quirk: a missing subtype prints "None".
    assert {r["subintervencion"] for r in data["results"]} == {"Inicial", "None"}
    assert data["tipos_intervencion"] == [
        {"id": catalogos["tipo"].pk, "nombre": "Visita"}
    ]
    assert data["destinatarios"] == [
        {"id": catalogos["destinatario"].pk, "nombre": "Titular"}
    ]
    assert data["filtros"] == {"fecha": "", "tipo_intervencion": "", "destinatario": ""}
    assert data["urls"]["agregar"] == f"/comedores/intervencion/crear/{comedor.pk}"
    assert data["messages"] == []


def test_list_filters_like_the_native_view(web, comedor, catalogos):
    visita = _intervencion(comedor, catalogos)
    otro_tipo = TipoIntervencion.objects.create(nombre="Llamada", programa="comedores")
    otro_dest = TipoDestinatario.objects.create(nombre="Referente")
    llamada = _intervencion(
        comedor,
        catalogos,
        tipo_intervencion=otro_tipo,
        subintervencion=None,
        destinatario=otro_dest,
        fecha=_local(2026, 10, 2, 8, 0),
    )
    url = f"{ROOT}comedor/{comedor.pk}/"

    def ids(**consulta):
        data = web.get(url, consulta).json()
        return {r["id"] for r in data["results"]}, data

    assert ids(fecha="2026-10-01")[0] == {visita.pk}
    assert ids(fecha="2026-10-02")[0] == {llamada.pk}
    # An invalid date is ignored, like the native filter.
    assert ids(fecha="no-es-fecha")[0] == {visita.pk, llamada.pk}
    assert ids(tipo_intervencion=otro_tipo.pk)[0] == {llamada.pk}
    solo, data = ids(destinatario=catalogos["destinatario"].pk)
    assert solo == {visita.pk}
    assert data["filtros"]["destinatario"] == str(catalogos["destinatario"].pk)


def test_list_scopes_to_the_admission_of_the_comedor_only(web, comedor, catalogos):
    actual = _admision(comedor, nro="CONV-7")
    cerrada = _admision(comedor, activa=False)
    ajena = _admision(Comedor.objects.create(nombre="Ajeno"))
    en_actual = _intervencion(comedor, catalogos, admision=actual)
    en_cerrada = _intervencion(comedor, catalogos, admision=cerrada)
    url = f"{ROOT}comedor/{comedor.pk}/"

    data = web.get(url, {"admision_id": actual.pk}).json()

    assert data["admision_id"] == actual.pk
    assert [r["id"] for r in data["results"]] == [en_actual.pk]
    assert data["admisiones"] == [
        {"id": cerrada.pk, "convenio": None, "activa": False},
        {"id": actual.pk, "convenio": "CONV-7", "activa": True},
    ]
    for invalida in (str(ajena.pk), "x", "0"):
        data = web.get(url, {"admision_id": invalida}).json()
        assert data["admision_id"] is None
        assert {r["id"] for r in data["results"]} == {en_actual.pk, en_cerrada.pk}


def test_list_offers_delete_only_to_superusers_and_unknown_comedor_is_404(
    comedor, catalogos
):
    intervencion = _intervencion(comedor, catalogos)
    root = _cliente(_usuario("root2_k4", superusuario=True))

    fila = root.get(f"{ROOT}comedor/{comedor.pk}/").json()["results"][0]

    assert fila["url_eliminar"] == (
        f"/comedores/intervencion/borrar/{comedor.pk}/{intervencion.pk}/"
    )
    assert root.get(f"{ROOT}comedor/999999/").status_code == 404


# --- Detail --------------------------------------------------------------------


def test_detail_projects_the_native_page(web, comedor, catalogos, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    intervencion = _intervencion(
        comedor, catalogos, subintervencion=None, observaciones=None
    )

    data = web.get(f"{ROOT}{intervencion.pk}/").json()

    assert data == {
        "id": intervencion.pk,
        "fecha": "01/10/2026 23:30",
        "tipo_intervencion": "Visita",
        "subintervencion": "None",
        "forma_contacto": "Presencial",
        "observaciones": "None",
        "documentacion": None,
        "puede_eliminar_archivo": False,
        "messages": [],
    }
    intervencion.documentacion.save("acta.txt", ContentFile(b"x"))
    con_archivo = web.get(f"{ROOT}{intervencion.pk}/").json()
    assert con_archivo["documentacion"]["name"].startswith("documentacion/acta")
    assert con_archivo["documentacion"]["url"].endswith(
        con_archivo["documentacion"]["name"]
    )
    assert web.get(f"{ROOT}999999/").status_code == 404


# --- File removal --------------------------------------------------------------


def _con_archivo(comedor, catalogos, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    intervencion = _intervencion(comedor, catalogos, tiene_documentacion=True)
    intervencion.documentacion.save("acta.txt", ContentFile(b"x"))
    return intervencion


def test_delete_file_runs_the_native_action_and_queues_its_message(
    comedor, catalogos, settings, tmp_path
):
    intervencion = _con_archivo(comedor, catalogos, settings, tmp_path)
    usuario = _usuario(
        "archivo_k4", "intervenciones.view_intervencion", "comedores.view_comedor"
    )
    web = _cliente(usuario)

    respuesta = web.post(f"{ROOT}{intervencion.pk}/documentacion/eliminar/")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/intervencion/detalle/{intervencion.pk}/",
    }
    intervencion.refresh_from_db()
    assert not intervencion.documentacion
    assert intervencion.tiene_documentacion is False
    assert list(tmp_path.rglob("acta*")) == []
    detalle = web.get(f"{ROOT}{intervencion.pk}/").json()
    assert detalle["messages"] == [
        {"message": "El archivo fue eliminado correctamente.", "level": "success"}
    ]
    # Repeated removal: the native error message, nothing else changes.
    web.post(f"{ROOT}{intervencion.pk}/documentacion/eliminar/")
    assert web.get(f"{ROOT}{intervencion.pk}/").json()["messages"] == [
        {"message": "No hay archivo para eliminar.", "level": "error"}
    ]


def test_delete_file_is_rejected_without_the_permission_or_csrf(
    comedor, catalogos, settings, tmp_path
):
    intervencion = _con_archivo(comedor, catalogos, settings, tmp_path)
    url = f"{ROOT}{intervencion.pk}/documentacion/eliminar/"
    sin_permiso = _cliente(
        _usuario("sin_archivo_k4", "intervenciones.view_intervencion")
    )
    sin_csrf = _cliente(
        _usuario("csrf_k4", "comedores.view_comedor"), enforce_csrf_checks=True
    )

    assert Client().post(url).status_code in (401, 403)
    assert sin_permiso.post(url).status_code == 403
    assert sin_csrf.post(url).status_code == 403
    assert sin_csrf.get(url).status_code == 405
    intervencion.refresh_from_db()
    assert intervencion.documentacion
    assert intervencion.tiene_documentacion is True
    assert len(list(tmp_path.rglob("acta*"))) == 1
    root = _cliente(_usuario("root3_k4", superusuario=True))
    assert root.post(f"{ROOT}999999/documentacion/eliminar/").status_code == 404
