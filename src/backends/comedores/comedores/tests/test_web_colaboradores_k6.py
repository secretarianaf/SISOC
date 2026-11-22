"""Web API (G1 v1) of the comedor collaborator screens (CO03.01).

``/api/web/comedores/colaboradores/`` runs the native views of
``comedores.views.colaborador``: scoped comedor, creation veto, citizen search,
``ColaboradorEspacioForm`` and ``ColaboradorEspacioService``. A rejected request
must write nothing and a collaborator must never become an access user.
"""

from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.utils import timezone

from ciudadanos.models import Ciudadano, Sexo
from comedores.models import (
    ActividadColaboradorEspacio,
    AuditColaboradorEspacio,
    ColaboradorEspacio,
    Comedor,
    Programas,
)
from comedores.services.comedor_service import ComedorService
from duplas.models import Dupla
from users.services import UserPermissionService

ROOT = "/api/web/comedores/colaboradores/"
CODIGOS = [
    "comedores.add_colaboradorespacio",
    "comedores.change_colaboradorespacio",
    "comedores.delete_colaboradorespacio",
]

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
    return _usuario("tecnico_k6c", *CODIGOS, first_name="Ana", last_name="Pérez")


@pytest.fixture(name="web")
def web_fixture(tecnico):
    return _cliente(tecnico)


@pytest.fixture(name="comedor")
def comedor_fixture(tecnico):
    dupla = Dupla.objects.create(
        nombre="Dupla K6c", estado="Activo", abogado=_usuario("abogado_k6c")
    )
    dupla.tecnico.add(tecnico)
    return Comedor.objects.create(nombre="Comedor K6c", dupla=dupla)


@pytest.fixture(name="ajeno")
def ajeno_fixture():
    otra = Dupla.objects.create(
        nombre="Otra dupla", estado="Activo", abogado=_usuario("abogado_otra_k6c")
    )
    return Comedor.objects.create(nombre="Fuera del alcance", dupla=otra)


@pytest.fixture(name="actividades")
def actividades_fixture():
    return [
        ActividadColaboradorEspacio.objects.create(
            nombre="Cocina", activo=True, orden=1
        ),
        ActividadColaboradorEspacio.objects.create(
            nombre="Limpieza", activo=True, orden=2
        ),
        ActividadColaboradorEspacio.objects.create(
            nombre="Inactiva", activo=False, orden=3
        ),
    ]


@pytest.fixture(name="persona")
def persona_fixture():
    sexo, _ = Sexo.objects.get_or_create(sexo="Femenino")
    return Ciudadano.objects.create(
        nombre="Ana",
        apellido="Gómez",
        documento="30999111",
        sexo=sexo,
        fecha_nacimiento=date(2000, 1, 1),
        cuil_cuit="27309991114",
    )


def _crear(comedor):
    return f"{ROOT}comedor/{comedor.pk}/crear/"


def _editar(comedor, colaborador):
    return f"{ROOT}comedor/{comedor.pk}/{colaborador.pk}/editar/"


def _eliminar(comedor, colaborador):
    return f"{ROOT}comedor/{comedor.pk}/{colaborador.pk}/eliminar/"


def _datos(catalogo, **extra):
    datos = {
        "genero": "M",
        "codigo_telefono": " 11 ",
        "numero_telefono": "5551234",
        "fecha_alta": "2026-10-01",
        "fecha_baja": "",
        "actividades": [str(catalogo[0].pk), str(catalogo[1].pk)],
    }
    datos.update(extra)
    return datos


def _colaborador(comedor, persona, actividades, **extra):
    colaborador = ColaboradorEspacio.objects.create(
        comedor=comedor,
        ciudadano=persona,
        genero="V",
        fecha_alta=date(2026, 9, 1),
        **extra,
    )
    colaborador.actividades.set([actividades[0]])
    return colaborador


def _estado():
    return (
        list(
            ColaboradorEspacio.objects.order_by("pk").values_list(
                "pk", "ciudadano_id", "genero", "fecha_alta", "fecha_baja"
            )
        ),
        list(
            ColaboradorEspacio.actividades.through.objects.order_by("pk").values_list(
                "colaboradorespacio_id", "actividadcolaboradorespacio_id"
            )
        ),
        AuditColaboradorEspacio.objects.count(),
        Ciudadano.objects.count(),
        get_user_model().objects.count(),
    )


# --- Access --------------------------------------------------------------------


def test_each_endpoint_keeps_the_native_permission_and_requires_a_session(
    comedor, persona, actividades
):
    colaborador = _colaborador(comedor, persona, actividades)
    permiso = {
        _crear(comedor): "comedores.add_colaboradorespacio",
        _editar(comedor, colaborador): "comedores.change_colaboradorespacio",
    }
    for url, codigo in permiso.items():
        assert Client().get(url).status_code in (401, 403), url
        resto = _usuario(
            f"sin_{codigo.split('.')[1]}", *(c for c in CODIGOS if c != codigo)
        )
        assert _cliente(resto).get(url).status_code == 403, url
        asignado = _usuario(f"con_{codigo.split('.')[1]}", codigo)
        # The user is not in the dupla: the native scope answers 404, after the permission.
        assert _cliente(asignado).get(url).status_code == 404, url
    sin_baja = _usuario("sin_baja", *CODIGOS[:2])
    assert _cliente(sin_baja).post(_eliminar(comedor, colaborador)).status_code == 403
    assert _cliente(_usuario("con_baja", CODIGOS[2])).post(
        _eliminar(comedor, colaborador)
    ).status_code in (404,)
    assert ColaboradorEspacio.objects.get().fecha_baja is None


def test_write_requires_csrf_and_a_form_content_type(tecnico, comedor, actividades):
    estricto = _cliente(tecnico, enforce_csrf_checks=True)
    antes = _estado()
    assert estricto.post(_crear(comedor), {"dni": "30111222"}).status_code == 403
    web = _cliente(tecnico)
    respuesta = web.post(_crear(comedor), data="{}", content_type="application/json")
    assert respuesta.status_code == 415
    assert _estado() == antes


def test_linea_secos_creation_is_the_native_404_but_edit_is_not_vetoed(
    web, comedor, persona, actividades
):
    colaborador = _colaborador(comedor, persona, actividades)
    comedor.programa = Programas.objects.create(
        nombre="Abordaje Comunitario - Línea Secos"
    )
    comedor.save()

    assert web.get(_crear(comedor)).status_code == 404
    assert (
        web.post(
            _crear(comedor), {"ciudadano_id": persona.pk, **_datos(actividades)}
        ).status_code
        == 404
    )
    assert web.get(_editar(comedor, colaborador)).status_code == 200
    assert ColaboradorEspacio.objects.count() == 1


# --- Create: search ------------------------------------------------------------


def test_create_page_without_search_only_offers_the_search(web, comedor):
    data = web.get(_crear(comedor)).json()

    assert data["comedor"] == {
        "id": comedor.pk,
        "nombre": "Comedor K6c",
        "url": f"/comedores/{comedor.pk}",
    }
    assert data["edit_mode"] is False
    assert data["preview"] is None
    assert data["form"] is None
    assert data["not_found"] is False
    assert data["messages"] == []


def test_search_finds_the_local_citizen_and_projects_the_native_form(
    web, comedor, persona, actividades
):
    data = web.get(f"{_crear(comedor)}?query=30999111").json()

    assert data["source"] == "sisoc"
    assert data["existing"] is False
    assert data["hidden"] == {"name": "ciudadano_id", "value": str(persona.pk)}
    assert data["preview"] == {
        "apellido": "Gómez",
        "nombre": "Ana",
        "dni": "30999111",
        "prefijo_cuil": "27",
        "cuil_cuit": "27309991114",
        "sufijo_cuil": "4",
        "sexo": "Femenino",
        "fecha_nacimiento": "01/01/2000",
        "edad": data["preview"]["edad"],
    }
    campos = data["form"]["fields"]
    assert campos["fecha_alta"]["value"] == timezone.now().date().isoformat()
    assert campos["genero"]["value"] == "ND"
    assert [c["value"] for c in campos["genero"]["choices"]][0] == "V"
    # Active catalog only, ordered by ``orden, id``; the label is the model's ``str``.
    assert [(c["label"], c["checked"]) for c in campos["actividades"]["choices"]] == [
        (str(actividades[0]), False),
        (str(actividades[1]), False),
    ]
    assert campos["codigo_telefono"]["max_length"] == 10
    # The native widget markup: the date is ``required``, the blank-less Select is not.
    assert campos["fecha_alta"]["html_required"] is True
    assert campos["genero"]["html_required"] is False
    assert campos["fecha_baja"]["html_required"] is False


def test_search_by_ciudadano_id_flags_an_existing_collaboration(
    web, comedor, persona, actividades
):
    _colaborador(comedor, persona, actividades)

    data = web.get(f"{_crear(comedor)}?ciudadano_id={persona.pk}").json()

    assert data["existing"] is True
    assert data["form"] is None
    assert data["preview"]["dni"] == "30999111"


def test_invalid_dni_warns_and_unknown_dni_falls_back_to_renaper(
    web, comedor, monkeypatch
):
    corto = web.get(f"{_crear(comedor)}?query=123").json()
    assert corto["preview"] is None
    assert corto["messages"] == [
        {
            "message": "Ingrese un DNI numérico válido para realizar la búsqueda.",
            "tags": "warning",
        }
    ]

    monkeypatch.setattr(
        ComedorService,
        "obtener_datos_ciudadano_desde_renaper",
        staticmethod(
            lambda dni: {
                "success": True,
                "message": "Datos obtenidos de RENAPER.",
                "data": {
                    "apellido": "Ruiz",
                    "nombre": "Beto",
                    "documento": dni,
                    "genero": "M",
                    "fecha_nacimiento": date(1990, 5, 4),
                    "cuil_cuit": "20301112228",
                },
            }
        ),
    )
    renaper = web.get(f"{_crear(comedor)}?query=30111222").json()
    assert renaper["source"] == "renaper"
    assert renaper["hidden"] == {"name": "dni", "value": "30111222"}
    assert renaper["preview"]["apellido"] == "Ruiz"
    assert renaper["preview"]["sexo"] == "Masculino"
    assert renaper["preview"]["fecha_nacimiento"] == "04/05/1990"
    assert renaper["messages"][0]["tags"] == "info"
    assert Ciudadano.objects.filter(documento="30111222").count() == 0

    monkeypatch.setattr(
        ComedorService,
        "obtener_datos_ciudadano_desde_renaper",
        staticmethod(lambda dni: {"success": False, "message": "RENAPER caído."}),
    )
    caido = web.get(f"{_crear(comedor)}?query=30111223").json()
    assert caido["preview"] is None
    assert caido["not_found"] is True
    assert caido["messages"] == [{"message": "RENAPER caído.", "tags": "warning"}]


# --- Create: write -------------------------------------------------------------


def test_create_with_a_local_citizen_persists_the_collaboration_audit_and_message(
    web, tecnico, comedor, persona, actividades
):
    usuarios = get_user_model().objects.count()
    respuesta = web.post(
        _crear(comedor), {"ciudadano_id": persona.pk, **_datos(actividades)}
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": f"/comedores/{comedor.pk}"}
    colaborador = ColaboradorEspacio.objects.get()
    assert colaborador.ciudadano == persona
    assert colaborador.comedor == comedor
    assert colaborador.genero == "M"
    # Phone fields are stripped by the native form.
    assert colaborador.codigo_telefono == "11"
    assert colaborador.numero_telefono == "5551234"
    assert colaborador.fecha_alta == date(2026, 10, 1)
    assert colaborador.fecha_baja is None
    assert set(colaborador.actividades.values_list("pk", flat=True)) == {
        actividades[0].pk,
        actividades[1].pk,
    }
    assert colaborador.creado_por == tecnico
    assert colaborador.modificado_por == tecnico
    auditoria = AuditColaboradorEspacio.objects.get()
    assert auditoria.accion == AuditColaboradorEspacio.ACCION_CREATE
    assert auditoria.changed_by == tecnico
    assert auditoria.metadata == {"source": "sisoc"}
    # No access user is created or granted by associating a person.
    assert get_user_model().objects.count() == usuarios
    # The success message waits for the next page, the comedor card.
    siguiente = web.get(f"/api/web/comedores/colaboradores/comedor/{comedor.pk}/crear/")
    assert "Colaborador agregado correctamente al espacio." in [
        m["message"] for m in siguiente.json()["messages"]
    ]


def test_create_from_renaper_creates_the_citizen_through_the_service(
    web, comedor, actividades, monkeypatch
):
    def crear(dni, user=None):
        sexo, _ = Sexo.objects.get_or_create(sexo="Masculino")
        return {
            "success": True,
            "ciudadano": Ciudadano.objects.create(
                nombre="Beto",
                apellido="Ruiz",
                documento=dni,
                sexo=sexo,
                fecha_nacimiento=date(1990, 5, 4),
            ),
        }

    monkeypatch.setattr(
        ComedorService, "crear_ciudadano_desde_renaper", staticmethod(crear)
    )
    respuesta = web.post(_crear(comedor), {"dni": "30111222", **_datos(actividades)})

    assert respuesta.json()["ok"] is True
    colaborador = ColaboradorEspacio.objects.get()
    assert colaborador.ciudadano.documento == 30111222
    assert AuditColaboradorEspacio.objects.get().metadata == {"source": "renaper"}


def test_create_without_citizen_or_with_a_duplicate_is_rejected_without_writing(
    web, comedor, persona, actividades
):
    antes = _estado()
    sin_persona = web.post(_crear(comedor), _datos(actividades))
    assert sin_persona.status_code == 400
    assert sin_persona.json()["messages"] == [
        {
            "message": "Debe buscar un ciudadano o consultar RENAPER antes de guardar el colaborador.",
            "tags": "warning",
        }
    ]
    assert _estado() == antes

    _colaborador(comedor, persona, actividades)
    antes = _estado()
    duplicado = web.post(
        _crear(comedor), {"ciudadano_id": persona.pk, **_datos(actividades)}
    )
    assert duplicado.status_code == 400
    assert duplicado.json()["existing"] is True
    assert _estado() == antes


def test_create_form_errors_are_the_native_ones_and_write_nothing(
    web, comedor, persona, actividades
):
    antes = _estado()
    for cambios, campo, mensaje in (
        ({"actividades": []}, "actividades", "Este campo es requerido."),
        ({"fecha_alta": ""}, "fecha_alta", "Este campo es requerido."),
        (
            {"fecha_baja": "2026-09-01"},
            "fecha_baja",
            "La fecha de baja no puede ser anterior a la fecha de alta.",
        ),
        (
            {"numero_telefono": "12ab"},
            "numero_telefono",
            "El número de teléfono debe contener solo números.",
        ),
        (
            {"codigo_telefono": "1x"},
            "codigo_telefono",
            "El código de teléfono debe contener solo números.",
        ),
        ({"actividades": [str(actividades[2].pk)]}, "actividades", None),
    ):
        respuesta = web.post(
            _crear(comedor),
            {"ciudadano_id": persona.pk, **_datos(actividades, **cambios)},
        )
        assert respuesta.status_code == 400, campo
        errores = respuesta.json()["form"]["errors"]
        assert campo in errores, campo
        if mensaje:
            assert errores[campo][0]["message"] == mensaje
        assert respuesta.json()["messages"] == [
            {"message": "Errores en el formulario del colaborador.", "tags": "warning"}
        ]
        # The bound values come back so the form is not lost.
        assert respuesta.json()["form"]["fields"]["genero"]["value"] == "M"
    assert _estado() == antes


# --- Edit ----------------------------------------------------------------------


def test_edit_page_shows_the_current_collaborator(web, comedor, persona, actividades):
    colaborador = _colaborador(
        comedor, persona, actividades, codigo_telefono="11", numero_telefono="555"
    )

    data = web.get(_editar(comedor, colaborador)).json()

    assert data["edit_mode"] is True
    assert data["source"] == "edicion"
    assert data["hidden"] == {"name": "ciudadano_id", "value": str(persona.pk)}
    assert data["preview"]["apellido"] == "Gómez"
    campos = data["form"]["fields"]
    assert campos["genero"]["value"] == "V"
    assert campos["codigo_telefono"]["value"] == "11"
    assert campos["fecha_alta"]["value"] == "2026-09-01"
    assert [c["checked"] for c in campos["actividades"]["choices"]] == [True, False]


def test_edit_updates_the_collaborator_and_audits_it_without_touching_the_citizen(
    web, tecnico, comedor, persona, actividades
):
    colaborador = _colaborador(comedor, persona, actividades)
    usuarios = get_user_model().objects.count()
    datos = _datos(
        actividades,
        genero="MT",
        actividades=[str(actividades[1].pk)],
        ciudadano_id=str(persona.pk),
    )

    respuesta = web.post(_editar(comedor, colaborador), datos)

    assert respuesta.json() == {"ok": True, "redirect": f"/comedores/{comedor.pk}"}
    colaborador.refresh_from_db()
    assert colaborador.genero == "MT"
    assert colaborador.fecha_baja is None
    assert list(colaborador.actividades.values_list("pk", flat=True)) == [
        actividades[1].pk
    ]
    assert colaborador.modificado_por == tecnico
    auditoria = AuditColaboradorEspacio.objects.get()
    assert auditoria.accion == AuditColaboradorEspacio.ACCION_UPDATE
    assert auditoria.snapshot_antes["genero"] == "V"
    assert auditoria.snapshot_despues["genero"] == "MT"
    assert Ciudadano.objects.count() == 1
    assert get_user_model().objects.count() == usuarios


def test_edit_rejection_keeps_the_stored_collaborator(
    web, comedor, persona, actividades
):
    colaborador = _colaborador(comedor, persona, actividades)
    antes = _estado()

    respuesta = web.post(
        _editar(comedor, colaborador),
        _datos(actividades, actividades=[], genero="MT"),
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["form"]["errors"]["actividades"]
    assert respuesta.json()["form"]["fields"]["genero"]["value"] == "MT"
    assert _estado() == antes


def test_edit_cannot_set_a_withdrawal_date(web, comedor, persona, actividades):
    colaborador = _colaborador(comedor, persona, actividades)
    antes = _estado()

    respuesta = web.post(
        _editar(comedor, colaborador), _datos(actividades, fecha_baja="2026-10-15")
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["messages"] == [
        {
            "message": "Solo se pueden editar colaboradores activos.",
            "tags": "warning",
        }
    ]
    assert _estado() == antes


def test_edit_of_a_withdrawn_or_foreign_collaborator_is_a_404(
    web, comedor, ajeno, persona, actividades
):
    baja = _colaborador(comedor, persona, actividades, fecha_baja=date(2026, 9, 30))
    ajeno_colab = _colaborador(ajeno, persona, actividades)
    antes = _estado()

    assert web.get(_editar(comedor, baja)).status_code == 404
    assert web.post(_editar(comedor, baja), _datos(actividades)).status_code == 404
    assert web.get(_editar(ajeno, ajeno_colab)).status_code == 404
    # A collaborator of another comedor cannot be edited through an own comedor.
    assert web.get(_editar(comedor, ajeno_colab)).status_code == 404
    assert _estado() == antes


# --- Withdrawal ----------------------------------------------------------------


def test_withdrawal_stamps_the_date_audits_and_is_idempotent(
    web, tecnico, comedor, persona, actividades
):
    colaborador = _colaborador(comedor, persona, actividades)

    respuesta = web.post(_eliminar(comedor, colaborador))

    assert respuesta.json() == {"ok": True, "redirect": f"/comedores/{comedor.pk}"}
    colaborador.refresh_from_db()
    assert colaborador.fecha_baja == timezone.now().date()
    assert colaborador.modificado_por == tecnico
    assert AuditColaboradorEspacio.objects.get().accion == (
        AuditColaboradorEspacio.ACCION_DELETE
    )
    assert Ciudadano.objects.count() == 1

    antes = _estado()
    repetida = web.post(_eliminar(comedor, colaborador))
    assert repetida.json()["ok"] is True
    assert _estado() == antes


def test_withdrawal_of_a_future_registration_never_inverts_the_dates(
    web, comedor, persona, actividades
):
    futura = timezone.now().date() + timedelta(days=10)
    colaborador = _colaborador(comedor, persona, actividades)
    colaborador.fecha_alta = futura
    colaborador.save()

    web.post(_eliminar(comedor, colaborador))

    colaborador.refresh_from_db()
    assert colaborador.fecha_baja == futura


def test_withdrawal_is_post_only_and_scoped(web, comedor, ajeno, persona, actividades):
    propio = _colaborador(comedor, persona, actividades)
    otro = _colaborador(ajeno, persona, actividades)
    antes = _estado()

    assert web.get(_eliminar(comedor, propio)).status_code == 405
    assert web.post(_eliminar(ajeno, otro)).status_code == 404
    assert web.post(_eliminar(comedor, otro)).status_code == 404
    assert _estado() == antes
