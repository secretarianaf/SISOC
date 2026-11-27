"""Web API (G1 v1) of the comedor activity screens (CO03.02).

``/api/web/comedores/actividades-espacio/`` runs the native views of
``comedores.views.actividad_espacio_pwa``: scoped PNUD comedor,
``ActividadEspacioPWAWebForm`` and the shared PWA service. One schedule is one stored
row; a rejected request must write nothing.
"""

from datetime import time

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client

from comedores.models import Comedor, Programas
from core.models import Dia
from duplas.models import Dupla
from pwa.models import ActividadEspacioPWA, AuditoriaOperacionPWA, CatalogoActividadPWA
from users.services import UserPermissionService

ROOT = "/api/web/comedores/actividades-espacio/"
PERMISO = "pwa.manage_colaboradores_pwa"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _tecnico_sin_coordinacion(monkeypatch):
    """The scope of a technician: only the comedores of its own dupla."""
    monkeypatch.setattr(
        UserPermissionService,
        "es_tecnico_o_abogado",
        staticmethod(lambda _user: True),
    )
    monkeypatch.setattr(
        UserPermissionService,
        "get_coordinador_duplas",
        staticmethod(lambda _user: (False, [])),
    )


def _usuario(nombre, *codes, **extra):
    usuario = get_user_model().objects.create_user(nombre, **extra)
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


@pytest.fixture(name="tecnico")
def tecnico_fixture():
    return _usuario("tecnico_k6a", PERMISO, first_name="Ana", last_name="Pérez")


@pytest.fixture(name="web")
def web_fixture(tecnico):
    return _cliente(tecnico)


@pytest.fixture(name="comedor")
def comedor_fixture(tecnico):
    dupla = Dupla.objects.create(
        nombre="Dupla K6a", estado="Activo", abogado=_usuario("abogado_k6a")
    )
    dupla.tecnico.add(tecnico)
    programa = Programas.objects.create(nombre="Programa PNUD K6a")
    return Comedor.objects.create(nombre="Comedor K6a", dupla=dupla, programa=programa)


@pytest.fixture(name="ajeno")
def ajeno_fixture():
    otra = Dupla.objects.create(
        nombre="Otra dupla", estado="Activo", abogado=_usuario("abogado_otra_k6a")
    )
    programa = Programas.objects.create(nombre="Otro PNUD K6a")
    return Comedor.objects.create(
        nombre="Fuera del alcance", dupla=otra, programa=programa
    )


@pytest.fixture(name="catalogo")
def catalogo_fixture():
    return {
        "taller": CatalogoActividadPWA.objects.create(
            categoria="Zz Categoria K6", actividad="Zz Taller K6", activo=True
        ),
        "otra": CatalogoActividadPWA.objects.create(
            categoria="Zz Categoria K6", actividad="Zz Otra K6", activo=True
        ),
        "inactiva": CatalogoActividadPWA.objects.create(
            categoria="Zz Categoria K6", actividad="Zz Vieja K6", activo=False
        ),
        "ajena": CatalogoActividadPWA.objects.create(
            categoria="Zz Segunda K6", actividad="Zz Ajena K6", activo=True
        ),
    }


@pytest.fixture(name="dias")
def dias_fixture():
    return [Dia.objects.create(nombre=nombre) for nombre in ("Lunes K6", "Martes K6")]


def _crear(comedor):
    return f"{ROOT}comedor/{comedor.pk}/crear/"


def _editar(comedor, actividad):
    return f"{ROOT}comedor/{comedor.pk}/{actividad.pk}/editar/"


def _datos(catalogo, dias, **extra):
    datos = {
        "categoria": "Zz Categoria K6",
        "catalogo_actividad": str(catalogo["taller"].pk),
        "vigencia_actividad_meses": "6",
        "schedule_dia_actividad": [str(dias[0].pk)],
        "schedule_hora_inicio": ["09:00"],
        "schedule_hora_fin": ["11:00"],
        "responsable_actividad": "Luis Gómez",
    }
    datos.update(extra)
    return datos


def _actividad(comedor, catalogo, dia, inicio=time(9), fin=time(11), **extra):
    datos = {
        "comedor": comedor,
        "catalogo_actividad": catalogo,
        "dia_actividad": dia,
        "hora_inicio": inicio,
        "hora_fin": fin,
        "horario_actividad": f"{inicio:%H:%M} a {fin:%H:%M}",
        "responsable_actividad": "Original",
        "vigencia_actividad_meses": 3,
    }
    datos.update(extra)
    return ActividadEspacioPWA.objects.create(**datos)


def _estado():
    return (
        list(
            ActividadEspacioPWA.objects.order_by("pk").values_list(
                "pk",
                "catalogo_actividad_id",
                "dia_actividad_id",
                "hora_inicio",
                "hora_fin",
                "horario_actividad",
                "responsable_actividad",
                "vigencia_actividad_meses",
                "activo",
            )
        ),
        AuditoriaOperacionPWA.objects.count(),
    )


# --- Access --------------------------------------------------------------------


def test_each_endpoint_keeps_the_native_permission_scope_and_pnud_rule(
    web, comedor, ajeno, catalogo, dias
):
    actividad = _actividad(comedor, catalogo["taller"], dias[0])
    urls = [_crear(comedor), _editar(comedor, actividad)]

    for url in urls:
        assert Client().get(url).status_code in (401, 403), url
        assert _cliente(_usuario(f"sin_{abs(hash(url))}")).get(url).status_code == 403
        assert Client().post(url, {}).status_code in (401, 403), url
        assert web.get(url).status_code == 200, url
    # The native order: scope and PNUD rule answer 404 once the permission passed.
    assert web.get(_crear(ajeno)).status_code == 404
    comedor.programa = None  # no programa: not PNUD (ids 3 and 4 are PNUD by id)
    comedor.save()
    assert web.get(_crear(comedor)).status_code == 404
    assert web.get(_editar(comedor, actividad)).status_code == 404
    assert web.post(_crear(comedor), _datos(catalogo, dias)).status_code == 404
    assert ActividadEspacioPWA.objects.count() == 1


def test_write_requires_csrf_and_a_form_content_type(tecnico, comedor, catalogo, dias):
    antes = _estado()

    assert (
        _cliente(tecnico, enforce_csrf_checks=True)
        .post(_crear(comedor), _datos(catalogo, dias))
        .status_code
        == 403
    )
    assert (
        _cliente(tecnico)
        .post(_crear(comedor), data="{}", content_type="application/json")
        .status_code
        == 415
    )
    assert _estado() == antes


# --- Read ----------------------------------------------------------------------


def test_create_form_projects_the_native_page(web, comedor, catalogo, dias):
    data = web.get(_crear(comedor)).json()

    assert data["comedor"] == {
        "id": comedor.pk,
        "nombre": "Comedor K6a",
        "url": f"/comedores/{comedor.pk}",
    }
    assert data["edit_mode"] is False
    assert data["urls"]["volver"] == f"/comedores/{comedor.pk}#legajo-actividades-pnud"
    campos = data["fields"]
    assert campos["categoria"]["options"][0] == {"value": "", "label": "Seleccionar"}
    assert "Zz Categoria K6" in [o["value"] for o in campos["categoria"]["options"]]
    assert campos["categoria"]["value"] == ""
    assert campos["catalogo_actividad"]["required"] is True
    assert campos["vigencia_actividad_meses"]["label"] == "Vigencia en meses"
    # The widget's ``min`` is serialized as the text the markup carries.
    assert campos["vigencia_actividad_meses"]["min"] == "0"
    assert campos["responsable_actividad"]["max_length"] == 255
    # The catalog the page script filters by category: active entries only.
    opciones = {o["id"]: o for o in data["activity_options"]}
    assert catalogo["taller"].pk in opciones
    assert catalogo["inactiva"].pk not in opciones
    assert [d["nombre"] for d in data["days"]] == ["Lunes K6", "Martes K6"]
    assert data["rows"] == [
        {
            "values": {"dia_actividad": "", "hora_inicio": "", "hora_fin": ""},
            "errors": {},
        }
    ]
    assert data["non_field_errors"] == []


def test_edit_form_shows_the_stored_row_and_keeps_an_inactive_catalog_choice(
    web, comedor, catalogo, dias
):
    actividad = _actividad(
        comedor, catalogo["inactiva"], dias[1], time(8, 30), time(10)
    )

    data = web.get(_editar(comedor, actividad)).json()

    assert data["edit_mode"] is True
    assert data["fields"]["categoria"]["value"] == "Zz Categoria K6"
    assert data["fields"]["catalogo_actividad"]["value"] == str(catalogo["inactiva"].pk)
    assert data["fields"]["vigencia_actividad_meses"]["value"] == "3"
    assert data["fields"]["responsable_actividad"]["value"] == "Original"
    # A historical selection stays selectable although the catalog retired it.
    assert catalogo["inactiva"].pk in [o["id"] for o in data["activity_options"]]
    assert data["rows"] == [
        {
            "values": {
                "dia_actividad": str(dias[1].pk),
                "hora_inicio": "08:30",
                "hora_fin": "10:00",
            },
            "errors": {},
        }
    ]


# --- Create --------------------------------------------------------------------


def test_create_one_schedule_persists_one_row_audit_actor_and_message(
    web, tecnico, comedor, catalogo, dias
):
    respuesta = web.post(_crear(comedor), _datos(catalogo, dias))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/comedores/{comedor.pk}#legajo-actividades-pnud",
    }
    actividad = ActividadEspacioPWA.objects.get()
    assert actividad.comedor == comedor
    assert actividad.catalogo_actividad == catalogo["taller"]
    assert actividad.dia_actividad == dias[0]
    assert (actividad.hora_inicio, actividad.hora_fin) == (time(9), time(11))
    assert actividad.horario_actividad == "09:00 a 11:00"
    assert actividad.responsable_actividad == "Luis Gómez"
    assert actividad.vigencia_actividad_meses == 6
    assert actividad.activo is True
    assert actividad.creado_por == tecnico
    assert actividad.actualizado_por == tecnico
    evento = AuditoriaOperacionPWA.objects.get()
    assert (evento.entidad, evento.accion, evento.user) == (
        "actividad",
        "create",
        tecnico,
    )
    # The success message waits for the next page, the comedor card.
    siguiente = web.get(_crear(comedor)).json()
    assert [m["message"] for m in siguiente["messages"]] == [
        "Actividad creada correctamente."
    ]


def test_create_several_schedules_persists_one_row_each_and_dedupes_identical_ones(
    web, comedor, catalogo, dias
):
    datos = _datos(
        catalogo,
        dias,
        schedule_dia_actividad=[str(dias[0].pk), str(dias[1].pk), str(dias[0].pk)],
        schedule_hora_inicio=["09:00", "14:00", "09:00"],
        schedule_hora_fin=["11:00", "16:30", "11:00"],
    )

    respuesta = web.post(_crear(comedor), datos)

    assert respuesta.json()["ok"] is True
    filas = ActividadEspacioPWA.objects.order_by("pk")
    assert [(f.dia_actividad_id, f.horario_actividad) for f in filas] == [
        (dias[0].pk, "09:00 a 11:00"),
        (dias[1].pk, "14:00 a 16:30"),
    ]
    assert AuditoriaOperacionPWA.objects.count() == 2
    mensajes = web.get(_crear(comedor)).json()["messages"]
    assert [m["message"] for m in mensajes] == [
        "Se crearon 2 horarios de actividad correctamente."
    ]


def test_create_rejections_are_the_native_ones_and_write_nothing(
    web, comedor, catalogo, dias
):
    _actividad(comedor, catalogo["taller"], dias[0], time(9), time(11))
    antes = _estado()
    casos = [
        ({"vigencia_actividad_meses": "0"}, "vigencia_actividad_meses", None),
        ({"catalogo_actividad": ""}, "catalogo_actividad", None),
        (
            {"catalogo_actividad": str(catalogo["ajena"].pk)},
            "catalogo_actividad",
            "Selecciona una actividad de la categoría elegida.",
        ),
        ({"schedule_dia_actividad": [""]}, None, "Completa todos los dias y horarios"),
        ({"schedule_hora_inicio": ["9"]}, None, "Completa todos los dias y horarios"),
        (
            {"schedule_hora_inicio": ["12:00"], "schedule_hora_fin": ["11:00"]},
            None,
            "Completa todos los dias y horarios",
        ),
        (
            {
                "schedule_dia_actividad": [str(dias[0].pk)],
                "schedule_hora_inicio": ["10:00"],
                "schedule_hora_fin": ["12:00"],
            },
            None,
            "Ya existe la misma actividad con un horario que se pisa ese dia.",
        ),
        (
            {
                "schedule_dia_actividad": [str(dias[1].pk), str(dias[1].pk)],
                "schedule_hora_inicio": ["09:00", "10:00"],
                "schedule_hora_fin": ["11:00", "12:00"],
            },
            None,
            "La misma actividad no puede tener horarios cruzados en el mismo dia.",
        ),
    ]
    for cambios, campo, mensaje in casos:
        respuesta = web.post(_crear(comedor), _datos(catalogo, dias, **cambios))
        assert respuesta.status_code == 400, cambios
        cuerpo = respuesta.json()
        if campo:
            assert cuerpo["fields"][campo]["errors"], cambios
        if mensaje and campo:
            assert cuerpo["fields"][campo]["errors"] == [mensaje]
        if mensaje and not campo:
            assert mensaje in " ".join(cuerpo["non_field_errors"]), cambios
        # The bound values and the rows come back so nothing typed is lost.
        assert cuerpo["fields"]["responsable_actividad"]["value"] == "Luis Gómez"
        assert len(cuerpo["rows"]) == len(cambios.get("schedule_dia_actividad", [1]))
        assert _estado() == antes, cambios


def test_row_errors_come_back_per_schedule_row(web, comedor, catalogo, dias):
    respuesta = web.post(
        _crear(comedor),
        _datos(
            catalogo,
            dias,
            schedule_dia_actividad=[str(dias[0].pk), "9999999"],
            schedule_hora_inicio=["09:00", "xx"],
            schedule_hora_fin=["11:00", "11:00"],
        ),
    )

    assert respuesta.status_code == 400
    filas = respuesta.json()["rows"]
    assert filas[0]["errors"] == {}
    assert filas[1]["errors"] == {
        "dia_actividad": "Selecciona un dia valido.",
        "hora_inicio": "Hora inicio debe tener formato HH:MM.",
    }
    assert filas[1]["values"]["hora_inicio"] == "xx"
    assert ActividadEspacioPWA.objects.count() == 0


# --- Edit ----------------------------------------------------------------------


def test_edit_updates_the_first_schedule_and_creates_the_extra_ones(
    web, tecnico, comedor, catalogo, dias
):
    actividad = _actividad(comedor, catalogo["taller"], dias[0])

    respuesta = web.post(
        _editar(comedor, actividad),
        _datos(
            catalogo,
            dias,
            catalogo_actividad=str(catalogo["otra"].pk),
            responsable_actividad="Nueva",
            schedule_dia_actividad=[str(dias[1].pk), str(dias[0].pk)],
            schedule_hora_inicio=["13:00", "18:00"],
            schedule_hora_fin=["14:00", "19:00"],
        ),
    )

    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/comedores/{comedor.pk}#legajo-actividades-pnud",
    }
    actividad.refresh_from_db()
    assert actividad.catalogo_actividad == catalogo["otra"]
    assert actividad.dia_actividad == dias[1]
    assert actividad.horario_actividad == "13:00 a 14:00"
    assert actividad.responsable_actividad == "Nueva"
    assert actividad.actualizado_por == tecnico
    extra = ActividadEspacioPWA.objects.exclude(pk=actividad.pk).get()
    assert (extra.dia_actividad, extra.horario_actividad) == (dias[0], "18:00 a 19:00")
    assert extra.catalogo_actividad == catalogo["otra"]
    assert extra.creado_por == tecnico
    assert sorted(AuditoriaOperacionPWA.objects.values_list("accion", flat=True)) == [
        "create",
        "update",
    ]
    mensajes = web.get(_crear(comedor)).json()["messages"]
    assert [m["message"] for m in mensajes] == [
        "Actividad actualizada y horarios adicionales creados correctamente."
    ]


def test_edit_one_schedule_only_updates_and_never_creates(web, comedor, catalogo, dias):
    actividad = _actividad(comedor, catalogo["taller"], dias[0])

    web.post(
        _editar(comedor, actividad),
        _datos(catalogo, dias, responsable_actividad="Solo"),
    )

    assert ActividadEspacioPWA.objects.count() == 1
    actividad.refresh_from_db()
    assert actividad.responsable_actividad == "Solo"
    mensajes = web.get(_crear(comedor)).json()["messages"]
    assert [m["message"] for m in mensajes] == ["Actividad actualizada correctamente."]


def test_edit_rejection_keeps_the_stored_rows(web, comedor, catalogo, dias):
    actividad = _actividad(comedor, catalogo["taller"], dias[0])
    antes = _estado()

    respuesta = web.post(
        _editar(comedor, actividad),
        _datos(
            catalogo,
            dias,
            responsable_actividad="No debe guardarse",
            schedule_dia_actividad=[str(dias[1].pk), str(dias[1].pk)],
            schedule_hora_inicio=["13:00", "12:00"],
            schedule_hora_fin=["14:00", "13:30"],
        ),
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["fields"]["responsable_actividad"]["value"] == (
        "No debe guardarse"
    )
    assert _estado() == antes


def test_edit_of_an_activity_of_another_comedor_is_a_404(
    web, tecnico, comedor, ajeno, catalogo, dias
):
    ajena = _actividad(ajeno, catalogo["taller"], dias[0])
    antes = _estado()

    assert web.get(_editar(comedor, ajena)).status_code == 404
    assert web.post(_editar(comedor, ajena), _datos(catalogo, dias)).status_code == 404
    assert _estado() == antes


def test_legacy_edit_preserves_activity_fields_absent_from_payload(
    web, comedor, catalogo, dias
):
    actividad = _actividad(comedor, catalogo["taller"], dias[0])
    actividad.nombre_fantasia = "Taller de prueba"
    actividad.cantidad_personas = 13
    actividad.save(update_fields=["nombre_fantasia", "cantidad_personas"])

    respuesta = web.post(
        _editar(comedor, actividad),
        _datos(catalogo, dias, responsable_actividad="Nueva"),
    )
    assert respuesta.status_code == 200
    actividad.refresh_from_db()
    assert actividad.responsable_actividad == "Nueva"
    assert actividad.nombre_fantasia == "Taller de prueba"
    assert actividad.cantidad_personas == 13


def test_legacy_edit_can_explicitly_clear_optional_metadata(
    web, comedor, catalogo, dias
):
    actividad = _actividad(comedor, catalogo["taller"], dias[0])
    actividad.nombre_fantasia = "Taller de prueba"
    actividad.cantidad_personas = 13
    actividad.save(update_fields=["nombre_fantasia", "cantidad_personas"])

    respuesta = web.post(
        _editar(comedor, actividad),
        _datos(catalogo, dias, nombre_fantasia="", cantidad_personas=""),
    )
    assert respuesta.status_code == 200
    actividad.refresh_from_db()
    assert (actividad.nombre_fantasia, actividad.cantidad_personas) == ("", None)


def test_grouped_schedule_error_projects_each_day_in_web_v1(
    web, comedor, catalogo, dias
):
    antes = _estado()
    datos = _datos(catalogo, dias)
    datos.pop("schedule_dia_actividad")
    datos.update(
        {
            "schedule_grupo": ["a"],
            "schedule_dias_a": [str(dia.pk) for dia in dias],
            "schedule_hora_inicio": ["xx"],
            "schedule_hora_fin": ["10:30"],
        }
    )
    respuesta = web.post(_crear(comedor), datos)
    assert respuesta.status_code == 400
    filas = respuesta.json()["rows"]
    assert [fila["values"]["dia_actividad"] for fila in filas] == [
        str(dia.pk) for dia in dias
    ]
    assert all(
        fila["values"]["hora_inicio"] == "xx" and "hora_inicio" in fila["errors"]
        for fila in filas
    )
    assert _estado() == antes
