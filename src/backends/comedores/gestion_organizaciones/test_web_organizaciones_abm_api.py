"""Web API (G1 v1) of the Organizaciones ABM (O05.02).

``/api/web/comedores/organizaciones/`` runs the native create, update and
delete views. The tests pin the persisted effects, the redirect targets, the
Django messages and error texts verbatim, and today's access:
``organizaciones.view_organizacion`` on the route with no object scope.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from comedores.models import Programas
from core import web_gate
from core.models import Provincia
from gestion_organizaciones.models import ProgramaOrganizacion
from organizaciones.models import (
    Organizacion,
    ProyectoOrganizacion,
    SubtipoEntidad,
    TipoEntidad,
)

API = "/api/web/comedores/organizaciones/"
VIEW = "organizaciones.view_organizacion"

pytestmark = pytest.mark.django_db


def _usuario(nombre, *codes):
    usuario = get_user_model().objects.create_user(nombre)
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for code in codes:
        app, codename = code.split(".")
        if app == "auth":
            permiso = Permission.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(Group),
                codename=codename,
                defaults={"name": codename},
            )[0]
        else:
            permiso = Permission.objects.get(
                content_type__app_label=app, codename=codename
            )
        usuario.user_permissions.add(permiso)
    return usuario


@pytest.fixture(name="web")
def web_fixture():
    client = Client()
    client.force_login(_usuario("abm_org", VIEW))
    return client


def _datos(**extra):
    provincia = Provincia.objects.get_or_create(nombre="Provincia sintética")[0]
    datos = {
        "nombre": "Organización Nueva",
        "provincia": str(provincia.pk),
        "sin_vencimiento": "on",
        "proyectos_lineas": "[]",
    }
    datos.update(extra)
    return datos


def _campos(data):
    return {c["name"]: c for c in data["form"]["fields"]}


def test_form_projects_the_real_fields_options_and_values(web):
    tipo = TipoEntidad.objects.create(nombre="Asociación civil")
    SubtipoEntidad.objects.create(nombre="Mutual", tipo_entidad=tipo)
    Programas.objects.create(nombre="Alimentar Comunidad")
    organizacion = Organizacion.objects.create(
        nombre="Existente", cuit=20111111112, tipo_entidad=tipo
    )

    nueva = web.get(f"{API}formulario/").json()["form"]
    editar = web.get(f"{API}{organizacion.pk}/formulario/").json()["form"]

    campos = {c["name"]: c for c in nueva["fields"]}
    assert campos["nombre"]["required"] is True
    assert campos["cuit"]["errors"] == [] and campos["cuit"]["value"] is None
    assert {"value": str(tipo.pk), "label": "Asociación civil"} in campos[
        "tipo_entidad"
    ]["options"]
    assert campos["programas"]["type"] == "multiple"
    assert [o["label"] for o in campos["programas"]["options"]] == [
        "Alimentar Comunidad"
    ]
    assert nueva["organizacion_id"] is None
    assert nueva["urls"]["cancel"] == "/organizaciones/listar"
    assert editar["organizacion_id"] == organizacion.pk
    assert editar["urls"]["cancel"] == f"/organizaciones/detalle/{organizacion.pk}"
    assert editar["tipo_entidad_actual"] == tipo.pk
    valores = {c["name"]: c["value"] for c in editar["fields"]}
    assert (valores["nombre"], valores["cuit"]) == ("Existente", 20111111112)
    assert web.get(f"{API}999999/formulario/").status_code == 404


def test_create_runs_the_native_view_and_persists_every_part(web):
    programa = Programas.objects.create(nombre="Alimentar Comunidad")

    respuesta = web.post(
        f"{API}crear/",
        _datos(cuit="20111111112", programas=[str(programa.pk)]),
    )

    organizacion = Organizacion.objects.get(nombre="Organización Nueva")
    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "redirect": f"/organizaciones/detalle/{organizacion.pk}",
        "messages": [],
    }
    assert organizacion.cuit == 20111111112
    assert list(
        ProgramaOrganizacion.objects.filter(organizacion=organizacion).values_list(
            "programa_id", flat=True
        )
    ) == [programa.pk]


def test_invalid_create_answers_400_with_the_django_texts_and_saves_nothing(web):
    Organizacion.objects.create(nombre="Otra", cuit=20111111112)

    cuit = web.post(f"{API}crear/", _datos(cuit="123"))
    duplicado = web.post(f"{API}crear/", _datos(cuit="20111111112"))
    vacio = web.post(f"{API}crear/", _datos(nombre=""))

    assert cuit.status_code == duplicado.status_code == vacio.status_code == 400
    assert cuit.json()["errors"]["cuit"] == [
        "Ingresá un CUIT de 11 dígitos, solo con números y sin espacios."
    ]
    assert duplicado.json()["errors"]["cuit"] == [
        "El CUIL ingresado ya está registrado en otra organización. "
        "Revisá la advertencia y confirmá para continuar."
    ]
    assert vacio.json()["errors"]["nombre"] == ["Este campo es requerido."]
    # The bound form comes back so React shows the user's values and errors.
    campos = _campos(cuit.json())
    assert campos["cuit"]["value"] == "123"
    assert campos["cuit"]["errors"] == cuit.json()["errors"]["cuit"]
    assert Organizacion.objects.count() == 1


def test_duplicate_cuit_can_be_confirmed_like_the_native_form(web):
    Organizacion.objects.create(nombre="Otra", cuit=20111111112)

    respuesta = web.post(
        f"{API}crear/",
        _datos(
            cuit="20111111112",
            cuil_duplicado_confirmado="on",
            cuil_duplicado_confirmado_valor="20111111112",
        ),
    )

    assert respuesta.status_code == 201
    assert Organizacion.objects.filter(cuit=20111111112).count() == 2


def test_update_keeps_projects_and_a_type_change_resets_the_legajo(web):
    tipo = TipoEntidad.objects.create(nombre="Asociación civil")
    otro = TipoEntidad.objects.create(nombre="Cooperativa")
    organizacion = Organizacion.objects.create(nombre="Vieja", tipo_entidad=tipo)
    ProyectoOrganizacion.objects.create(organizacion=organizacion, codigo="PRY-1")
    url = f"{API}{organizacion.pk}/editar/"

    simple = web.post(
        url,
        _datos(
            nombre="Vieja editada",
            tipo_entidad=str(tipo.pk),
            proyectos_lineas=json.dumps([{"codigo": "PRY-1", "linea": ""}]),
        ),
    )
    cambio = web.post(
        url,
        _datos(
            nombre="Vieja editada",
            tipo_entidad=str(otro.pk),
            proyectos_lineas=json.dumps([{"codigo": "PRY-1", "linea": ""}]),
        ),
    )

    assert simple.status_code == 200
    assert simple.json() == {
        "redirect": f"/organizaciones/detalle/{organizacion.pk}",
        "messages": [],
    }
    assert cambio.json()["messages"] == [
        {
            "message": "Se reinicio la documentacion del legajo porque cambio el Tipo de Entidad.",
            "level": "warning",
        }
    ]
    organizacion.refresh_from_db()
    assert (organizacion.nombre, organizacion.tipo_entidad_id) == (
        "Vieja editada",
        otro.pk,
    )
    assert organizacion.proyectos.get().activo is True
    assert web.post(f"{API}999999/editar/", _datos()).status_code == 404


def test_baja_previews_then_deletes_with_the_native_message(web):
    organizacion = Organizacion.objects.create(nombre="Para baja")

    previa = web.get(f"{API}{organizacion.pk}/baja/").json()
    baja = web.post(f"{API}{organizacion.pk}/baja/")

    assert previa["nombre"] == "Para baja"
    assert previa["motivo"] is None
    assert "total_afectados" in previa["cascade_preview"]
    assert previa["urls"] == {
        "cancel": f"/organizaciones/detalle/{organizacion.pk}",
        "list": "/organizaciones/listar",
    }
    assert baja.status_code == 200
    assert baja.json() == {
        "redirect": "/organizaciones/listar",
        "messages": [
            {
                "message": "La organización Para baja fue dada de baja correctamente.",
                "level": "success",
            }
        ],
    }
    assert not Organizacion.objects.filter(pk=organizacion.pk).exists()
    assert web.get(f"{API}{organizacion.pk}/baja/").status_code == 404


def test_baja_with_projects_is_blocked_with_the_native_reason(web):
    organizacion = Organizacion.objects.create(nombre="Con proyecto")
    ProyectoOrganizacion.objects.create(organizacion=organizacion, codigo="PRY-9")

    previa = web.get(f"{API}{organizacion.pk}/baja/").json()
    baja = web.post(f"{API}{organizacion.pk}/baja/")

    assert previa["motivo"].startswith("No se puede dar de baja la organización: ")
    assert baja.status_code == 409
    assert baja.json()["error"] == previa["motivo"]
    assert Organizacion.objects.filter(pk=organizacion.pk).exists()


def test_subtipos_and_cuil_serve_the_native_json(web):
    tipo = TipoEntidad.objects.create(nombre="Asociación civil")
    SubtipoEntidad.objects.create(nombre="Mutual", tipo_entidad=tipo)
    SubtipoEntidad.objects.create(nombre="Inactiva", tipo_entidad=tipo, activo=False)
    existente = Organizacion.objects.create(nombre="Dueña", cuit=20111111112)

    for api, nativa in (
        (
            f"{API}subtipos/?tipo_entidad={tipo.pk}",
            f"/organizaciones/subtipos-entidad/ajax/?tipo_entidad={tipo.pk}",
        ),
        (
            f"{API}cuil/?cuil=20111111112",
            "/organizaciones/cuil-check/ajax/?cuil=20111111112",
        ),
        (
            f"{API}cuil/?cuil=20111111112&exclude={existente.pk}",
            f"/organizaciones/cuil-check/ajax/?cuil=20111111112&exclude={existente.pk}",
        ),
        (f"{API}cuil/?cuil=abc", "/organizaciones/cuil-check/ajax/?cuil=abc"),
    ):
        assert web.get(api).json() == web.get(nativa).json(), api
    assert web.get(f"{API}subtipos/?tipo_entidad={tipo.pk}").json() == [
        {"id": SubtipoEntidad.objects.get(nombre="Mutual").pk, "text": "Mutual"}
    ]


def test_access_is_the_route_permission_and_csrf_is_enforced():
    organizacion = Organizacion.objects.create(nombre="Acceso")
    sin_permiso = Client()
    sin_permiso.force_login(_usuario("sin_abm"))
    tecnico = Client()
    tecnico.force_login(_usuario("tecnico_abm", "auth.role_tecnico_comedor"))
    anonimo = Client()
    estricto = Client(enforce_csrf_checks=True)
    estricto.force_login(_usuario("csrf_abm", VIEW))

    for client in (sin_permiso, tecnico):
        assert client.get(f"{API}formulario/").status_code == 403
        assert client.post(f"{API}crear/", _datos()).status_code == 403
        assert client.post(f"{API}{organizacion.pk}/baja/").status_code == 403
    respuesta = anonimo.post(f"{API}crear/", _datos())
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert estricto.post(f"{API}crear/", _datos()).status_code == 403
    assert estricto.post(f"{API}{organizacion.pk}/baja/").status_code == 403
    assert Organizacion.objects.count() == 1


def test_methods_are_limited_to_what_each_route_does(web):
    organizacion = Organizacion.objects.create(nombre="Métodos")
    assert web.post(f"{API}formulario/").status_code == 405
    assert web.get(f"{API}crear/").status_code == 405
    assert web.get(f"{API}{organizacion.pk}/editar/").status_code == 405
    assert web.put(f"{API}{organizacion.pk}/baja/").status_code == 405
    assert web.post(f"{API}subtipos/").status_code == 405
