"""Web API (G1 v1) of the signers and guarantors (O03).

``/api/web/comedores/organizaciones/`` runs the native ``Firmante*`` and
``Aval*`` views. The tests pin the persisted effects, the redirect targets, the
Django messages and error texts verbatim, the quirks of the native create (the
organization comes from the body) and today's access
(``organizaciones.view_organizacion`` on the route, no object scope).
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client

from comedores.models import Comedor, Programas
from core import web_gate
from duplas.models import Dupla
from gestion_organizaciones.models import Firmante, ProgramaOrganizacion
from organizaciones.models import Aval, Organizacion, RolFirmante, TipoEntidad

API = "/api/web/comedores/organizaciones/"
VIEW = "organizaciones.view_organizacion"
ROL_UNICO = "Ya existe un firmante con ese rol para esta organización."

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
    client.force_login(_usuario("firmantes_web", VIEW))
    return client


@pytest.fixture(name="roles")
def roles_fixture():
    nombres = [
        "Presidente",
        "Tesorero",
        "Secretario",
        "Obispo",
        "Apoderado 1",
        "Apoderado 2",
        "Firmante 1",
        "Firmante 2",
        "Firmante 3",
    ]
    return {n: RolFirmante.objects.create(nombre=n) for n in nombres}


def _organizacion(tipo=None, nombre="Org Firmantes"):
    entidad = TipoEntidad.objects.create(nombre=tipo) if tipo else None
    return Organizacion.objects.create(nombre=nombre, tipo_entidad=entidad)


def _campos(data):
    return {c["name"]: c for c in data["fields"]}


def _roles(data):
    return [o["label"] for o in _campos(data)["rol"]["options"] if o["value"]]


@pytest.mark.parametrize(
    "tipo,esperados",
    [
        ("Personería Jurídica", ["Presidente", "Tesorero", "Secretario"]),
        ("personería jurídica eclesiástica", ["Obispo", "Apoderado 1", "Apoderado 2"]),
        ("Asociación de hecho", ["Firmante 1", "Firmante 2", "Firmante 3"]),
        (None, []),
    ],
)
def test_create_form_offers_the_roles_of_the_entity_type(web, roles, tipo, esperados):
    organizacion = _organizacion(tipo)

    data = web.get(f"{API}{organizacion.pk}/firmantes/formulario/").json()

    assert _roles(data) == esperados
    assert data["title"] == "Datos de Firmantes"
    assert data["allow_another"] is True and data["organization_id"] == organizacion.pk
    assert list(_campos(data)) == ["nombre", "rol", "cuit", "programa"]
    assert _campos(data)["nombre"]["required"] is True
    assert data["urls"] == {"back": f"/organizaciones/detalle/{organizacion.pk}"}


def test_other_entity_type_offers_every_role_and_edit_always_does(web, roles):
    organizacion = _organizacion("Asociación civil")
    firmante = Firmante.objects.create(organizacion=organizacion, nombre="Ana")
    asociacion = _organizacion("Asociación de hecho", "Otra")

    alta = web.get(f"{API}{organizacion.pk}/firmantes/formulario/").json()
    edicion = web.get(f"{API}firmantes/{firmante.pk}/formulario/").json()
    restringida = web.get(f"{API}{asociacion.pk}/firmantes/formulario/").json()

    assert len(_roles(alta)) == 9 and len(_roles(edicion)) == 9
    assert len(_roles(restringida)) == 3
    assert edicion["allow_another"] is False
    assert edicion["urls"] == {"back": None} and edicion["organization_id"] is None
    assert _campos(edicion)["nombre"]["value"] == "Ana"


def test_programs_are_limited_to_the_organization_and_the_current_one(web):
    organizacion = _organizacion()
    propio = Programas.objects.create(nombre="Propio")
    actual = Programas.objects.create(nombre="Actual")
    Programas.objects.create(nombre="Ajeno")
    ProgramaOrganizacion.objects.create(organizacion=organizacion, programa=propio)
    firmante = Firmante.objects.create(
        organizacion=organizacion, nombre="Ana", programa=actual
    )

    alta = web.get(f"{API}{organizacion.pk}/firmantes/formulario/").json()
    edicion = web.get(f"{API}firmantes/{firmante.pk}/formulario/").json()
    sin_programas = web.get(
        f"{API}{_organizacion(nombre='Sin').pk}/firmantes/formulario/"
    ).json()

    etiquetas = lambda d: [
        o["label"] for o in _campos(d)["programa"]["options"]
    ]  # noqa: E731
    assert etiquetas(alta) == ["---------", "Propio"]
    assert sorted(etiquetas(edicion)) == ["---------", "Actual", "Propio"]
    assert len(etiquetas(sin_programas)) == 4


def test_create_saves_and_redirects_to_the_legajo_without_message(web, roles):
    organizacion = _organizacion("Personería Jurídica")

    respuesta = web.post(
        f"{API}{organizacion.pk}/firmantes/",
        {
            "organizacion_id": organizacion.pk,
            "nombre": "Ana",
            "rol": roles["Presidente"].pk,
            "cuit": "20111111112",
        },
    )

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "redirect": f"/organizaciones/detalle/{organizacion.pk}",
        "otro": False,
        "messages": [],
    }
    firmante = Firmante.objects.get()
    assert (firmante.organizacion, firmante.nombre, firmante.cuit) == (
        organizacion,
        "Ana",
        20111111112,
    )


def test_save_and_add_another_returns_to_the_create_form(web):
    organizacion = _organizacion()

    respuesta = web.post(
        f"{API}{organizacion.pk}/firmantes/",
        {"organizacion_id": organizacion.pk, "nombre": "Ana", "guardar_otro": "true"},
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["otro"] is True
    assert (
        respuesta.json()["redirect"]
        == f"/organizaciones/firmante/crear/{organizacion.pk}"
    )


def test_create_takes_the_organization_from_the_body_like_the_native_view(web):
    url_org, cuerpo_org = _organizacion(nombre="URL"), _organizacion(nombre="Cuerpo")

    web.post(
        f"{API}{url_org.pk}/firmantes/",
        {"organizacion_id": cuerpo_org.pk, "nombre": "Ana"},
    )

    assert Firmante.objects.get().organizacion == cuerpo_org


def test_create_without_organization_id_answers_400_with_the_native_message(web):
    organizacion = _organizacion()

    respuesta = web.post(f"{API}{organizacion.pk}/firmantes/", {"nombre": "Ana"})

    assert respuesta.status_code == 400
    assert respuesta.json()["messages"] == [
        {"message": "Falta el id de la organización.", "level": "error"}
    ]
    assert not Firmante.objects.exists()


def test_one_role_per_organization_on_create_and_edit(web, roles):
    organizacion = _organizacion("Personería Jurídica")
    rol = roles["Presidente"].pk
    base = {"organizacion_id": organizacion.pk, "rol": rol}
    web.post(f"{API}{organizacion.pk}/firmantes/", {**base, "nombre": "Ana"})

    repetido = web.post(
        f"{API}{organizacion.pk}/firmantes/", {**base, "nombre": "Beto"}
    )
    otro = Firmante.objects.create(
        organizacion=organizacion, nombre="Cris", rol=roles["Tesorero"]
    )
    edicion = web.post(f"{API}firmantes/{otro.pk}/", {"nombre": "Cris", "rol": rol})
    propio = web.post(
        f"{API}firmantes/{Firmante.objects.get(nombre='Ana').pk}/",
        {"nombre": "Ana B", "rol": rol},
    )

    assert repetido.status_code == 400
    assert repetido.json()["errors"] == {"rol": [ROL_UNICO]}
    assert _campos(repetido.json()["form"])["rol"]["errors"] == [ROL_UNICO]
    assert edicion.status_code == 400 and edicion.json()["errors"] == {
        "rol": [ROL_UNICO]
    }
    assert propio.status_code == 200
    assert Firmante.objects.count() == 2


def test_invalid_create_returns_the_bound_form_and_writes_nothing(web):
    organizacion = _organizacion()

    respuesta = web.post(
        f"{API}{organizacion.pk}/firmantes/",
        {"organizacion_id": organizacion.pk, "nombre": "", "cuit": "999999999999"},
    )

    assert respuesta.status_code == 400
    errores = respuesta.json()["errors"]
    assert errores["nombre"] == ["Este campo es requerido."]
    assert "cuit" in errores
    assert not Firmante.objects.exists()


def test_edit_updates_and_redirects_and_unknown_is_404(web):
    organizacion = _organizacion()
    firmante = Firmante.objects.create(organizacion=organizacion, nombre="Ana")

    respuesta = web.post(
        f"{API}firmantes/{firmante.pk}/", {"nombre": "Ana Z", "cuit": "5"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "redirect": f"/organizaciones/detalle/{organizacion.pk}",
        "otro": False,
        "messages": [],
    }
    firmante.refresh_from_db()
    assert (firmante.nombre, firmante.cuit) == ("Ana Z", 5)
    assert web.post(f"{API}firmantes/999999/", {"nombre": "X"}).status_code == 404
    assert web.get(f"{API}firmantes/999999/formulario/").status_code == 404


def test_baja_previews_the_cascade_and_soft_deletes_with_the_native_message(web, roles):
    organizacion = _organizacion()
    firmante = Firmante.objects.create(
        organizacion=organizacion, nombre="Ana", rol=roles["Presidente"]
    )

    vista = web.get(f"{API}firmantes/{firmante.pk}/baja/").json()

    assert vista["id"] == firmante.pk and vista["title"] == "Atención!"
    assert vista["message"] == "¿Está seguro que desea dar de baja al firmante Ana"
    assert vista["urls"] == {"cancel": f"/organizaciones/detalle/{organizacion.pk}"}
    assert vista["cascade_preview"]["total_afectados"] == 1
    assert vista["cascade_preview"]["desglose_por_modelo"][0]["modelo"] == "Firmantes"
    assert Firmante.objects.filter(pk=firmante.pk).exists()

    respuesta = web.post(f"{API}firmantes/{firmante.pk}/baja/")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "redirect": f"/organizaciones/detalle/{organizacion.pk}",
        "messages": [
            {"message": "Firmante dado de baja correctamente.", "level": "success"}
        ],
    }
    assert not Firmante.objects.filter(pk=firmante.pk).exists()
    assert Firmante.all_objects.get(pk=firmante.pk).deleted_at is not None
    assert web.get(f"{API}firmantes/{firmante.pk}/baja/").status_code == 404


def test_avales_have_the_same_flows_with_optional_fields(web):
    organizacion = _organizacion("Asociación de hecho")

    formulario = web.get(f"{API}{organizacion.pk}/avales/formulario/").json()
    creado = web.post(
        f"{API}{organizacion.pk}/avales/",
        {"organizacion_id": organizacion.pk, "guardar_otro": "true"},
    )
    aval = Aval.objects.get()
    edicion = web.get(f"{API}avales/{aval.pk}/formulario/").json()
    editado = web.post(
        f"{API}avales/{aval.pk}/", {"nombre": "Beto", "cuit": "20222222223"}
    )
    baja = web.get(f"{API}avales/{aval.pk}/baja/").json()
    borrado = web.post(f"{API}avales/{aval.pk}/baja/")

    assert formulario["title"] == "Datos de Avales"
    assert list(_campos(formulario)) == ["nombre", "cuit"]
    assert not _campos(formulario)["nombre"]["required"]
    assert creado.status_code == 201 and creado.json()["otro"] is True
    assert creado.json()["redirect"] == f"/organizaciones/aval/crear/{organizacion.pk}"
    assert edicion["allow_another"] is False
    assert editado.status_code == 200
    assert baja["message"] == "¿Está seguro que desea dar de baja el aval Beto"
    assert borrado.json()["messages"] == [
        {"message": "Aval dado de baja correctamente.", "level": "success"}
    ]
    assert not Aval.objects.exists()
    assert web.post(f"{API}avales/999999/", {}).status_code == 404


def test_access_is_todays_anonymous_401_no_permission_403_and_csrf_403(web):
    organizacion = _organizacion()
    url = f"{API}{organizacion.pk}/firmantes/"
    cuerpo = {"organizacion_id": organizacion.pk, "nombre": "Ana"}

    anonimo = Client().post(url, cuerpo)
    assert anonimo.status_code == 401
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    # The technician role does not open these routes: only ``view_organizacion``.
    tecnico = Client()
    tecnico.force_login(_usuario("firmantes_tec", "auth.role_tecnico_comedor"))
    assert tecnico.post(url, cuerpo).status_code == 403
    assert tecnico.get(f"{url}formulario/").status_code == 403
    con_csrf = Client(enforce_csrf_checks=True)
    con_csrf.force_login(get_user_model().objects.get(username="firmantes_web"))
    assert con_csrf.post(url, cuerpo).status_code == 403
    assert not Firmante.objects.exists()
    firmante = Firmante.objects.create(organizacion=organizacion, nombre="Ana")
    assert tecnico.post(f"{API}firmantes/{firmante.pk}/baja/").status_code == 403
    assert web.put(url).status_code == 405


def _todas(valor):
    """Every JSON object with a ``kind`` in the page, in document order."""
    if isinstance(valor, dict):
        if "kind" in valor:
            yield valor
        for hijo in valor.values():
            yield from _todas(hijo)
    elif isinstance(valor, list):
        for hijo in valor:
            yield from _todas(hijo)


def _secciones_de(data, kind):
    return [s for s in _todas(data["blocks"]) if s["kind"] == kind]


def test_legajo_delivers_the_signers_tables_as_sections(web, roles):
    organizacion = _organizacion("Asociación de hecho")
    programa = Programas.objects.create(nombre="Alimentar comunidad")
    ProgramaOrganizacion.objects.create(organizacion=organizacion, programa=programa)
    Firmante.objects.create(
        organizacion=organizacion,
        nombre="Ana",
        rol=roles["Firmante 1"],
        cuit=20111111112,
        programa=programa,
    )
    Firmante.objects.create(organizacion=organizacion, nombre="Sin programa")
    Aval.objects.create(organizacion=organizacion, nombre="Beto")

    data = web.get(f"{API}{organizacion.pk}/?programa={programa.pk}").json()

    secciones = _secciones_de(data, "firmantes")
    assert [s["title"] for s in secciones] == [
        "Firmantes · Alimentar comunidad",
        "Firmantes",
    ]
    programa_s, sin_programa = secciones
    assert programa_s["can_manage"] is True
    assert programa_s["add_url"] == f"/organizaciones/firmante/crear/{organizacion.pk}"
    assert programa_s["show_program"] is False
    fila = programa_s["rows"][0]
    assert (fila["name"], fila["role"], fila["cuit"]) == (
        "Ana",
        "Firmante 1",
        "20111111112",
    )
    assert fila["edit_url"] == f"/organizaciones/firmante/editar/{fila['id']}"
    assert fila["delete_url"] == f"/organizaciones/firmante/eliminar/{fila['id']}"
    assert sin_programa["add_url"] is None and sin_programa["show_program"] is True
    assert sin_programa["rows"][0]["program"] is None
    assert sin_programa["rows"][0]["cuit"] == "-"
    assert "html" not in data and "sections" not in data


def test_legajo_delivers_the_avales_table_as_a_section(web):
    organizacion = _organizacion("Asociación de hecho")
    sin_cuit = Aval.objects.create(organizacion=organizacion, nombre="Beto")
    con_cuit = Aval.objects.create(
        organizacion=organizacion, nombre="Carla", cuit=20111111112
    )

    data = web.get(f"{API}{organizacion.pk}/").json()

    (seccion,) = _secciones_de(data, "avales")
    assert seccion["can_manage"] is True
    assert seccion["add_url"] == f"/organizaciones/aval/crear/{organizacion.pk}"
    assert [(r["id"], r["name"], r["cuit"]) for r in seccion["rows"]] == [
        (sin_cuit.pk, "Beto", "-"),
        (con_cuit.pk, "Carla", "20111111112"),
    ]
    assert (
        seccion["rows"][0]["edit_url"] == f"/organizaciones/aval/editar/{sin_cuit.pk}"
    )
    assert seccion["rows"][0]["delete_url"] == (
        f"/organizaciones/aval/eliminar/{sin_cuit.pk}"
    )


def test_legajo_avales_empty_and_only_for_asociacion_de_hecho(web):
    vacia = _organizacion("Asociación de hecho", "Sin avales")
    otra = _organizacion("Personería Jurídica", "Con personería")
    Aval.objects.create(organizacion=otra, nombre="No se muestra")

    (seccion,) = _secciones_de(web.get(f"{API}{vacia.pk}/").json(), "avales")
    assert seccion["rows"] == []
    assert _secciones_de(web.get(f"{API}{otra.pk}/").json(), "avales") == []


def test_legajo_avales_of_a_dupla_technician_have_no_management_actions():
    organizacion = _organizacion("Asociación de hecho")
    Aval.objects.create(organizacion=organizacion, nombre="Beto")
    tecnico = _usuario("tecnico_avales", "auth.role_tecnico_comedor")
    dupla = Dupla.objects.create(
        nombre="D", estado="Activo", abogado=_usuario("abogado_avales")
    )
    dupla.tecnico.add(tecnico)
    Comedor.objects.create(nombre="C", organizacion=organizacion, dupla=dupla)
    cliente = Client()
    cliente.force_login(tecnico)

    (seccion,) = _secciones_de(cliente.get(f"{API}{organizacion.pk}/").json(), "avales")

    assert seccion["can_manage"] is False and seccion["add_url"] is None
    assert [r["name"] for r in seccion["rows"]] == ["Beto"]
