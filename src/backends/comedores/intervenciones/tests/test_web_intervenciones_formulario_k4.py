"""Web API (G1 v1) of the comedor intervention form: create, edit and subtypes (CO02).

The endpoints run ``IntervencionCreateView`` / ``IntervencionUpdateView`` and keep
the permission codes of their URLs. A rejected POST must write nothing.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
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


def _usuario(nombre, *codes, superusuario=False):
    usuario = get_user_model().objects.create_user(nombre, is_superuser=superusuario)
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
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


@pytest.fixture(name="web")
def web_fixture():
    return _cliente(
        _usuario(
            "editor_k4",
            "intervenciones.add_intervencion",
            "intervenciones.change_intervencion",
        )
    )


@pytest.fixture(name="comedor")
def comedor_fixture():
    return Comedor.objects.create(nombre="Comedor K4", codigo_de_proyecto="")


@pytest.fixture(name="cat")
def catalogos_fixture():
    tipo = TipoIntervencion.objects.create(nombre="Visita", programa="comedores")
    return {
        "tipo": tipo,
        "sub": SubIntervencion.objects.create(nombre="Inicial", tipo_intervencion=tipo),
        "sin_subs": TipoIntervencion.objects.create(nombre="Llamada", programa=""),
        "ajeno": TipoIntervencion.objects.create(nombre="Solo CDI", programa="cdi"),
        "destinatario": TipoDestinatario.objects.create(nombre="Titular"),
        "contacto": TipoContacto.objects.create(nombre="Presencial"),
    }


def _datos(cat, **extra):
    datos = {
        "tipo_intervencion": str(cat["sin_subs"].pk),
        "subintervencion": "",
        "destinatario": str(cat["destinatario"].pk),
        "fecha": "2026-10-01",
        "forma_contacto": str(cat["contacto"].pk),
        "observaciones": "Texto",
    }
    datos.update(extra)
    return datos


def _admision(comedor):
    admision = Admision.objects.create(
        comedor=comedor, activa=True, enviado_acompaniamiento=True
    )
    Acompanamiento.objects.create(admision=admision, nro_convenio="")
    return admision


def _intervencion(comedor, cat, **extra):
    datos = {
        "comedor": comedor,
        "tipo_intervencion": cat["tipo"],
        "subintervencion": cat["sub"],
        "destinatario": cat["destinatario"],
        "forma_contacto": cat["contacto"],
        "fecha": timezone.make_aware(timezone.datetime(2026, 10, 1, 9, 30)),
        "observaciones": "Original",
    }
    datos.update(extra)
    return Intervencion.objects.create(**datos)


# --- Access --------------------------------------------------------------------


def test_each_endpoint_keeps_the_native_permission_and_requires_a_session(comedor, cat):
    intervencion = _intervencion(comedor, cat)
    crear = f"{ROOT}comedor/{comedor.pk}/crear/"
    editar = f"{ROOT}{intervencion.pk}/editar/{comedor.pk}/"
    solo_alta = _cliente(_usuario("alta_k4", "intervenciones.add_intervencion"))
    solo_edicion = _cliente(
        _usuario("edicion_k4", "intervenciones.change_intervencion")
    )

    for url in (crear, editar, f"{ROOT}subestados/"):
        assert Client().get(url).status_code in (401, 403)
    assert solo_alta.get(crear).status_code == 200
    assert solo_alta.get(editar).status_code == 403
    assert solo_edicion.get(crear).status_code == 403
    assert solo_edicion.get(editar).status_code == 200
    assert solo_alta.post(editar, _datos(cat)).status_code == 403
    # The subtype lookup only asks for a signed-in user, like the native route.
    sin_permisos = _cliente(_usuario("nadie_k4"))
    assert sin_permisos.get(f"{ROOT}subestados/").status_code == 200
    assert Intervencion.objects.count() == 1


# --- Create --------------------------------------------------------------------


def test_create_form_projects_the_native_page(web, comedor, cat):
    admision = _admision(comedor)

    data = web.get(
        f"{ROOT}comedor/{comedor.pk}/crear/", {"admision_id": admision.pk}
    ).json()

    assert data["comedor"]["id"] == comedor.pk
    assert data["admision_id"] == admision.pk
    campos = data["fields"]
    assert campos["tipo_intervencion"]["label"] == "Tipo de Intervención"
    assert campos["tipo_intervencion"]["required"] is True
    # Only the types of the comedor program (or without program), blank first.
    assert [o["label"] for o in campos["tipo_intervencion"]["options"]] == [
        "---------",
        "Visita",
        "Llamada",
    ]
    assert campos["subintervencion"]["required"] is False
    assert campos["subintervencion"]["options"] == [{"value": "", "label": "---------"}]
    assert campos["destinatario"]["required"] and campos["forma_contacto"]["required"]
    assert campos["fecha"]["label"] == "Fecha"
    assert campos["fecha"]["hidden_initial"]
    assert campos["observaciones"] == {
        "id": "id_observaciones",
        "label": "Descripción",
        "required": False,
        "invalid": False,
        "value": "",
    }
    assert campos["tiene_documentacion"]["label"] == "Documentación Adjunta"
    assert data["fields"]["documentacion"]["label"] == "Cargar Documentación"
    assert (
        web.get(f"{ROOT}comedor/{comedor.pk}/crear/", {"admision_id": "x"}).json()[
            "admision_id"
        ]
        is None
    )
    assert web.get(f"{ROOT}comedor/999999/crear/").status_code == 404


def test_create_saves_through_the_native_view_and_redirects(
    web, comedor, cat, settings, tmp_path
):
    settings.MEDIA_ROOT = str(tmp_path)
    admision = _admision(comedor)
    archivo = SimpleUploadedFile("acta.txt", b"contenido")

    respuesta = web.post(
        f"{ROOT}comedor/{comedor.pk}/crear/",
        _datos(
            cat,
            admision_id=str(admision.pk),
            tiene_documentacion="on",
            documentacion=archivo,
        ),
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/comedores/intervencion/ver/{comedor.pk}?admision_id={admision.pk}",
    }
    creada = Intervencion.objects.get()
    assert creada.comedor_id == comedor.pk
    assert creada.admision_id == admision.pk
    assert creada.tipo_intervencion == cat["sin_subs"]
    assert creada.subintervencion is None
    assert creada.destinatario == cat["destinatario"]
    assert creada.forma_contacto == cat["contacto"]
    assert timezone.localtime(creada.fecha).date().isoformat() == "2026-10-01"
    assert creada.observaciones == "Texto"
    assert creada.tiene_documentacion is True
    assert creada.documentacion.read() == b"contenido"


def test_create_follows_a_local_next_and_ignores_an_external_one(web, comedor, cat):
    url = f"{ROOT}comedor/{comedor.pk}/crear/"

    local = web.post(f"{url}?next=/comedores/{comedor.pk}", _datos(cat))
    externo = web.post(f"{url}?next=https://externo.example/x", _datos(cat))

    assert local.json()["redirect"] == f"/comedores/{comedor.pk}"
    assert externo.json()["redirect"] == f"/comedores/intervencion/ver/{comedor.pk}"
    assert Intervencion.objects.count() == 2


@pytest.mark.parametrize(
    "cambios",
    [
        {"tipo_intervencion": ""},
        {"destinatario": ""},
        {"forma_contacto": ""},
        {"fecha": ""},
        {"fecha": "1999-12-31"},
        {"fecha": "2101-01-01"},
        {"tipo_intervencion": "TIPO_CON_SUBS", "subintervencion": ""},
    ],
)
def test_create_rejects_an_invalid_form_and_writes_nothing(web, comedor, cat, cambios):
    cambios = {
        clave: (str(cat["tipo"].pk) if valor == "TIPO_CON_SUBS" else valor)
        for clave, valor in cambios.items()
    }

    respuesta = web.post(f"{ROOT}comedor/{comedor.pk}/crear/", _datos(cat, **cambios))

    assert respuesta.status_code == 400
    campos = respuesta.json()["fields"]
    assert any(campo.get("invalid") for campo in campos.values())
    assert Intervencion.objects.count() == 0


def test_create_keeps_the_native_rule_that_a_posted_type_is_always_allowed(
    web, comedor, cat
):
    """``include_ids`` of the native form adds the posted type to its queryset."""
    respuesta = web.post(
        f"{ROOT}comedor/{comedor.pk}/crear/",
        _datos(cat, tipo_intervencion=str(cat["ajeno"].pk)),
    )

    assert respuesta.status_code == 200
    assert Intervencion.objects.get().tipo_intervencion == cat["ajeno"]


def test_create_returns_the_bound_values_of_a_rejected_post(web, comedor, cat):
    respuesta = web.post(
        f"{ROOT}comedor/{comedor.pk}/crear/",
        _datos(cat, destinatario="", observaciones="No se pierde"),
    )

    campos = respuesta.json()["fields"]
    assert respuesta.status_code == 400
    assert campos["destinatario"]["invalid"] is True
    assert campos["tipo_intervencion"]["invalid"] is False
    assert campos["tipo_intervencion"]["value"] == str(cat["sin_subs"].pk)
    assert campos["observaciones"]["value"] == "No se pierde"
    assert campos["fecha"]["value"] == "2026-10-01"


def test_create_rejects_an_admission_of_another_comedor(web, comedor, cat):
    ajena = _admision(Comedor.objects.create(nombre="Ajeno"))

    respuesta = web.post(
        f"{ROOT}comedor/{comedor.pk}/crear/", _datos(cat, admision_id=str(ajena.pk))
    )

    assert respuesta.status_code == 400
    assert Intervencion.objects.count() == 0


def test_create_refuses_json_and_missing_csrf_without_writing(comedor, cat):
    usuario = _usuario("alta2_k4", "intervenciones.add_intervencion")
    url = f"{ROOT}comedor/{comedor.pk}/crear/"

    json_body = _cliente(usuario).post(
        url, json.dumps(_datos(cat)), content_type="application/json"
    )
    sin_csrf = _cliente(usuario, enforce_csrf_checks=True).post(url, _datos(cat))

    assert json_body.status_code == 415
    assert sin_csrf.status_code == 403
    assert Intervencion.objects.count() == 0


# --- Edit ----------------------------------------------------------------------


def test_edit_form_projects_the_instance(web, comedor, cat):
    intervencion = _intervencion(comedor, cat)

    data = web.get(f"{ROOT}{intervencion.pk}/editar/{comedor.pk}/").json()

    campos = data["fields"]
    assert campos["tipo_intervencion"]["value"] == str(cat["tipo"].pk)
    assert campos["subintervencion"]["value"] == str(cat["sub"].pk)
    assert [o["label"] for o in campos["subintervencion"]["options"]] == [
        "---------",
        "Inicial",
    ]
    assert campos["destinatario"]["value"] == str(cat["destinatario"].pk)
    # Native quirk: the localized text a type=date input cannot show.
    assert campos["fecha"]["value"] == "01/10/2026"
    assert campos["observaciones"]["value"] == "Original"
    assert data["admision_id"] is None
    assert web.get(f"{ROOT}999999/editar/{comedor.pk}/").status_code == 404
    assert web.get(f"{ROOT}{intervencion.pk}/editar/999999/").status_code == 404


def test_edit_saves_and_returns_to_the_comedor_list(web, comedor, cat):
    intervencion = _intervencion(comedor, cat)

    respuesta = web.post(
        f"{ROOT}{intervencion.pk}/editar/{comedor.pk}/",
        _datos(
            cat,
            observaciones="Cambiada",
            tipo_intervencion=str(cat["tipo"].pk),
            subintervencion=str(cat["sub"].pk),
            fecha="2026-11-02",
        ),
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/comedores/intervencion/ver/{comedor.pk}",
    }
    intervencion.refresh_from_db()
    assert intervencion.observaciones == "Cambiada"
    assert timezone.localtime(intervencion.fecha).date().isoformat() == "2026-11-02"
    assert Intervencion.objects.count() == 1


def test_edit_rejects_an_invalid_form_and_keeps_the_row(web, comedor, cat):
    intervencion = _intervencion(comedor, cat)

    respuesta = web.post(
        f"{ROOT}{intervencion.pk}/editar/{comedor.pk}/",
        _datos(
            cat,
            tipo_intervencion=str(cat["tipo"].pk),
            subintervencion="",
            observaciones="No se guarda",
        ),
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["fields"]["subintervencion"]["invalid"] is True
    intervencion.refresh_from_db()
    assert intervencion.observaciones == "Original"
    assert intervencion.subintervencion == cat["sub"]


# --- Subtypes ------------------------------------------------------------------


def test_subtypes_are_the_native_select2_list(web, cat):
    SubIntervencion.objects.create(nombre="Anterior", tipo_intervencion=cat["tipo"])

    data = web.get(f"{ROOT}subestados/", {"id": cat["tipo"].pk}).json()

    assert [d["text"] for d in data] == ["Anterior", "Inicial"]
    assert set(data[0]) == {"id", "text"}
    assert web.get(f"{ROOT}subestados/").json() == []
    assert web.get(f"{ROOT}subestados/", {"id": cat["sin_subs"].pk}).json() == []
