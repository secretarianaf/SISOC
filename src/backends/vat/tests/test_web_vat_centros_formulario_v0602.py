"""V06.02: web API del formulario de alta y edición de un centro (``/api/web/vat/centros-formulario/``). Datos sintéticos."""

import itertools

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from rest_framework.test import APIClient

from core.models import Localidad, Municipio, Provincia
from VAT.models import Centro, InstitucionContacto
from VAT.web_preview_vat_centros_lista import centros_preview_patterns

pytestmark = pytest.mark.django_db

ROOT = "/api/web/vat/centros-formulario/"
_COUNTER = itertools.count()


def _client(*codes, sse=False, csrf=False):
    user = get_user_model().objects.create_user(f"cf{next(_COUNTER)}")
    user.user_permissions.add(
        *Permission.objects.filter(content_type__app_label="VAT", codename__in=codes)
    )
    if sse:
        permiso, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename="role_vat_sse",
            defaults={"name": "role_vat_sse"},
        )
        user.user_permissions.add(permiso)
    client = APIClient(enforce_csrf_checks=csrf)
    client.force_login(user)
    client.user = user
    return client


def _usuario_cfp(username, grupo="CFP", first="Ana", last="Gómez"):
    user = get_user_model().objects.create_user(
        username, first_name=first, last_name=last
    )
    user.groups.add(Group.objects.get_or_create(name=grupo)[0])
    return user


@pytest.fixture(name="geo")
def geo_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Tolosa", municipio=municipio)
    return provincia, municipio, localidad


def _datos(geo, referente, **cambios):
    provincia, municipio, localidad = geo
    datos = {
        "nombre": "CFP 401",
        "codigo": "060144900",
        "clase_institucion": "Formación Profesional",
        "tipo_gestion": "Estatal",
        "situacion": "Institución de ETP",
        "referentes": [str(referente.pk)],
        "referente": "",
        "domicilio_actividad": "Calle 7 N 1234",
        "provincia": str(provincia.pk),
        "municipio": str(municipio.pk),
        "localidad": str(localidad.pk),
        "correo": "cfp@example.com",
        "telefono": "221 555 0101",
        "contactos-TOTAL_FORMS": "1",
        "contactos-INITIAL_FORMS": "0",
        "contactos-MIN_NUM_FORMS": "0",
        "contactos-MAX_NUM_FORMS": "1000",
        "contactos-0-es_principal": "",
        "contactos-0-id": "",
        "contactos-0-centro": "",
        "contactos-0-nombre_contacto": "",
        "contactos-0-rol_area": "",
        "contactos-0-documento": "",
        "contactos-0-telefono_contacto": "",
        "contactos-0-email_contacto": "",
    }
    datos.update(cambios)
    return datos


@pytest.fixture(name="centro")
def centro_fixture(geo):
    provincia, municipio, localidad = geo
    referente = _usuario_cfp("ref.uno")
    centro = Centro.objects.create(
        nombre="CFP 401",
        codigo="060144900",
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
        domicilio_actividad="Calle 7 N 1234",
        telefono="221 555 0101",
        correo="cfp@example.com",
        tipo_gestion="Estatal",
        clase_institucion="Formación Profesional",
        situacion="Institución de ETP",
    )
    centro.referentes.add(referente)
    return centro


def test_access_follows_the_route_rule_and_the_native_guard(centro):
    for url in (f"{ROOT}nuevo/", f"{ROOT}{centro.pk}/editar/"):
        assert APIClient().get(url).status_code == 401
        sin_permiso = get_user_model().objects.create_user(f"cf-sin{next(_COUNTER)}")
        cliente = APIClient()
        cliente.force_login(sin_permiso)
        assert cliente.get(url).status_code == 403
        # the route permission alone is not the create/edit scope (native PermissionDenied of ``dispatch``)
        assert _client("view_centro").get(url).status_code == 403
        assert _client("view_centro", sse=True).get(url).status_code == 200
        assert _client("view_centro", sse=True).put(url).status_code == 405
    assert (
        _client("view_centro", sse=True).get(f"{ROOT}999999/editar/").status_code == 404
    )
    assert (
        _client("view_centro", csrf=True, sse=True)
        .post(f"{ROOT}nuevo/", {})
        .status_code
        == 403
    )


def test_create_form_projects_what_the_native_page_prints(geo):
    _usuario_cfp("ref.cfp")
    _usuario_cfp("rev.uno", grupo="CFPRevisor", first="Rita", last="Vega")
    datos = _client("view_centro", sse=True).get(f"{ROOT}nuevo/").json()
    assert datos["editing"] is False
    assert datos["title"] == "Nuevo Centro de Formación Profesional"
    assert [f["name"] for f in datos["fields"]] == [
        "nombre",
        "codigo",
        "clase_institucion",
        "tipo_gestion",
        "situacion",
        "domicilio_actividad",
        "calle",
        "numero",
        "codigo_postal",
        "lote",
        "manzana",
        "entre_calles",
        "provincia",
        "municipio",
        "localidad",
        "correo",
        "telefono",
        "celular",
        "sitio_web",
    ]
    por_nombre = {f["name"]: f for f in datos["fields"]}
    assert por_nombre["nombre"]["label"] == "Denominación de la institución"
    assert por_nombre["nombre"]["required"] is True
    assert por_nombre["nombre"]["attrs"]["maxlength"] == "150"
    assert por_nombre["codigo"]["help_text"] == "Debe contener solo números."
    assert por_nombre["provincia"]["attrs"]["class"] == "form-control select2"
    assert por_nombre["provincia"]["attrs"]["data-placeholder"] == (
        "Seleccionar jurisdicción..."
    )
    assert [c["label"] for c in por_nombre["provincia"]["choices"]] == [
        "Seleccionar jurisdicción...",
        "Buenos Aires",
    ]
    assert por_nombre["numero"]["attrs"]["type"] == "number"
    assert por_nombre["correo"]["attrs"]["type"] == "email"
    assert datos["referentes"]["label"] == "Referente/s"
    assert datos["referentes"]["selected"] == []
    assert [o["label"] for o in datos["referentes"]["options"]] == [
        "ref.cfp - Ana Gómez"
    ]
    assert [o["label"] for o in datos["revisores"]["options"]] == [
        "rev.uno - Rita Vega"
    ]
    contactos = datos["contactos"]
    assert (contactos["initial_forms"], len(contactos["forms"])) == (0, 1)
    assert [h["name"] for h in contactos["forms"][0]["hidden"]] == [
        "es_principal",
        "id",
        "centro",
    ]
    assert [f["label"] for f in contactos["empty"]["fields"]] == [
        "Nombre y apellido del responsable",
        "Rol / Área",
        "Documento",
        "Teléfono",
        "Correo electrónico",
    ]
    assert datos["activo"] is None
    assert datos["actions"] == {
        "cancel": "/vat/centros/",
        "submit": "Guardar",
        "submit_continue": "Guardar y continuar",
        "save_continue": True,
    }
    assert datos["urls"] == {
        "municipios": "/ajax/load-municipios/",
        "localidades": "/ajax/load-localidades/",
    }


def test_edit_form_has_the_stored_values_the_activo_switch_and_no_continue(centro):
    InstitucionContacto.objects.create(
        centro=centro,
        nombre_contacto="Ana Gómez",
        documento="30111222",
        es_principal=True,
        email_contacto="ana@example.com",
        tipo="email",
        valor="ana@example.com",
    )
    datos = _client("view_centro", sse=True).get(f"{ROOT}{centro.pk}/editar/").json()
    assert datos["editing"] is True
    assert datos["title"] == "Editar Centro de Formación Profesional"
    por_nombre = {f["name"]: f for f in datos["fields"]}
    assert por_nombre["nombre"]["value"] == "CFP 401"
    # the jurisdiction travels hidden and the localidades are those of the municipio
    assert por_nombre["provincia"]["attrs"]["type"] == "hidden"
    assert por_nombre["provincia"]["value"] == str(centro.provincia_id)
    assert [c["label"] for c in por_nombre["localidad"]["choices"]] == [
        "Seleccionar localidad...",
        "Tolosa",
    ]
    assert datos["referentes"]["selected"] == [str(centro.referentes.get().pk)]
    assert datos["activo"] == {
        "id": "id_activo",
        "label": "Activo",
        "checked": True,
        "errors": [],
    }
    assert datos["actions"]["save_continue"] is False
    assert datos["actions"]["cancel"] == f"/vat/centros/{centro.pk}/"
    contactos = datos["contactos"]
    assert contactos["initial_forms"] == 1
    existente = contactos["forms"][0]
    assert {h["name"]: h["value"] for h in existente["hidden"]}[
        "es_principal"
    ] == "True"
    assert existente["fields"][0]["value"] == "Ana Gómez"
    assert existente["errors"] == []


def test_create_persists_through_the_native_view_and_redirects(geo):
    referente = _usuario_cfp("ref.alta")
    cliente = _client("view_centro", sse=True)
    respuesta = cliente.post(
        f"{ROOT}nuevo/",
        _datos(
            geo,
            referente,
            **{
                "contactos-0-nombre_contacto": "Ana Gómez",
                "contactos-0-telefono_contacto": "221 555 0202",
                "contactos-0-es_principal": "True",
            },
        ),
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": "/vat/centros/"}
    centro = Centro.objects.get(codigo="060144900")
    assert list(centro.referentes.all()) == [referente]
    assert centro.contactos_adicionales.get().nombre_contacto == "Ana Gómez"
    assert centro.ubicaciones.get().rol_ubicacion == "sede_principal"
    # the native success message waits for the next page, as after the native redirect
    seguimiento = cliente.get("/api/web/vat/centros-lista/")
    assert seguimiento.status_code == 200
    assert {"message": "Centro creado exitosamente.", "level": "success"} in (
        seguimiento.json()["messages"]
    )


def test_create_with_save_continue_goes_to_the_detail(geo):
    referente = _usuario_cfp("ref.cont")
    respuesta = _client("view_centro", sse=True).post(
        f"{ROOT}nuevo/", _datos(geo, referente, save_continue="1")
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["redirect"] == (
        f"/vat/centros/{Centro.objects.get(codigo='060144900').pk}/"
    )


def test_rejected_create_returns_the_bound_form_and_stores_nothing(geo):
    referente = _usuario_cfp("ref.malo")
    respuesta = _client("view_centro", sse=True).post(
        f"{ROOT}nuevo/",
        _datos(
            geo,
            referente,
            nombre="",
            codigo="12",
            referentes=[],
            **{
                "contactos-0-nombre_contacto": "Ana",
                "contactos-0-telefono_contacto": "abc",
            },
        ),
    )
    assert respuesta.status_code == 400
    datos = respuesta.json()
    por_nombre = {f["name"]: f for f in datos["fields"]}
    assert por_nombre["nombre"]["errors"] == ["Este campo es requerido."]
    assert por_nombre["codigo"]["errors"] == ["El CUE debe tener al menos 9 dígitos."]
    assert por_nombre["codigo"]["value"] == "12"
    assert por_nombre["municipio"]["value"] == str(geo[1].pk)
    assert datos["referentes"]["errors"] == ["Debe seleccionar al menos un referente."]
    assert datos["referentes"]["selected"] == []
    assert datos["contactos"]["forms"][0]["errors"] == [
        {
            "field": "telefono_contacto",
            "messages": [
                "El teléfono del contacto solo puede incluir números, espacios, "
                "paréntesis o guiones."
            ],
        },
        {
            "field": "__all__",
            "messages": [
                "Debe informar al menos un teléfono o correo electrónico para el contacto."
            ],
        },
    ]
    assert Centro.objects.count() == 0


def test_two_principal_contacts_are_a_formset_error(geo):
    referente = _usuario_cfp("ref.dos")
    datos_post = _datos(
        geo,
        referente,
        **{
            "contactos-TOTAL_FORMS": "2",
            "contactos-0-nombre_contacto": "Ana",
            "contactos-0-telefono_contacto": "221 555 0202",
            "contactos-0-es_principal": "True",
            "contactos-1-es_principal": "True",
            "contactos-1-id": "",
            "contactos-1-centro": "",
            "contactos-1-nombre_contacto": "Beto",
            "contactos-1-telefono_contacto": "221 555 0303",
        },
    )
    respuesta = _client("view_centro", sse=True).post(f"{ROOT}nuevo/", datos_post)
    assert respuesta.status_code == 400
    assert respuesta.json()["contactos"]["non_form_errors"] == [
        "Solo puede existir un contacto principal."
    ]
    assert Centro.objects.count() == 0


def test_update_changes_the_centro_and_a_rejected_one_changes_nothing(centro, geo):
    cliente = _client("view_centro", sse=True)
    referente = centro.referentes.get()
    base = _datos(
        geo,
        referente,
        **{"activo_present": "1", "activo": "on"},
    )
    rechazado = cliente.post(
        f"{ROOT}{centro.pk}/editar/", {**base, "nombre": "", "telefono": "221 555 9999"}
    )
    assert rechazado.status_code == 400
    assert rechazado.json()["fields"][0]["errors"] == ["Este campo es requerido."]
    centro.refresh_from_db()
    assert (centro.nombre, centro.telefono) == ("CFP 401", "221 555 0101")
    valido = cliente.post(
        f"{ROOT}{centro.pk}/editar/",
        {**base, "nombre": "CFP 401 bis", "telefono": "221 555 9999"},
    )
    assert valido.status_code == 200
    assert valido.json() == {"ok": True, "redirect": f"/vat/centros/{centro.pk}/"}
    centro.refresh_from_db()
    assert (centro.nombre, centro.telefono) == ("CFP 401 bis", "221 555 9999")


def test_update_without_the_ids_of_existing_contacts_is_the_native_error(centro, geo):
    InstitucionContacto.objects.create(
        centro=centro,
        nombre_contacto="Ana",
        email_contacto="ana@example.com",
        tipo="email",
        valor="ana@example.com",
    )
    InstitucionContacto.objects.create(
        centro=centro,
        nombre_contacto="Beto",
        email_contacto="beto@example.com",
        tipo="email",
        valor="beto@example.com",
    )
    respuesta = _client("view_centro", sse=True).post(
        f"{ROOT}{centro.pk}/editar/",
        _datos(
            geo, centro.referentes.get(), **{"contactos-0-nombre_contacto": "Nuevo"}
        ),
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["non_field_errors"] == [
        "No se pudo guardar la edición de contactos porque faltan los "
        "identificadores de filas existentes. Recargá la página e intentá "
        "nuevamente."
    ]


def test_the_native_pages_keep_working_and_the_preview_owns_both_routes(geo, tmp_path):
    cliente = Client()
    cliente.force_login(_client("view_centro", sse=True).user)
    assert cliente.get("/vat/centros/nuevo/").status_code == 200
    (tmp_path / "index.html").write_text(
        '<!doctype html><html><head><script type="module" '
        'src="/v2/sisoc/assets/app-1.js"></script></head><body></body></html>',
        encoding="utf-8",
    )
    rutas = [str(p.pattern) for p in centros_preview_patterns(tmp_path)]
    assert "vat/centros/nuevo/" in rutas
    assert "vat/centros/<int:pk>/editar/" in rutas
