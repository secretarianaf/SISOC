"""Web API (G1 v1) of the CDI nomina attendance screen.

``/api/web/cdi/centros/<pk>/nomina/asistencia/`` runs ``AsistenciaNominaCentroView`` itself:
the rows, counters, date handling, POST and messages are compared with the native page.
"""

from datetime import date
from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from centrodeinfancia.models import (
    AccesoCDI,
    AsistenciaNominaCentroInfancia,
    CentroDeInfancia,
    NominaCentroInfancia,
)
from ciudadanos.models import Ciudadano
from core import web_gate

CAMBIO = "centrodeinfancia.change_centrodeinfancia"
FECHA = date(2026, 7, 1)
GUARDADA = "Asistencia registrada correctamente."

pytestmark = pytest.mark.django_db


def _api(pk):
    return f"/api/web/cdi/centros/{pk}/nomina/asistencia/"


def _calendario(pk):
    """The month calendar stays the native JSON endpoint the page script calls."""
    return reverse("centrodeinfancia_nomina_asistencia_calendario", args=[pk])


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return User.objects.get(pk=user.pk)


def _permiso(codigo):
    app, codename = codigo.split(".")
    permiso = Permission.objects.filter(
        content_type__app_label=app, codename=codename
    ).first()
    return permiso or Permission.objects.create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codename,
        name=codename,
    )


def _usuario(username, *, perms=(CAMBIO,), superuser=False):
    user = User.objects.create_user(username=username, is_superuser=superuser)
    for codigo in perms:
        user.user_permissions.add(_permiso(codigo))
    return _ready(user)


def _cliente(user, **extra):
    client = Client(**extra)
    client.force_login(user)
    return client


def _post(client, url, data):
    """The native form posts URL-encoded; the Django test client defaults to multipart."""
    return client.post(
        url, urlencode(data), content_type="application/x-www-form-urlencoded"
    )


def _nomina(centro, apellido, nombre, documento, **extra):
    ciudadano = Ciudadano.objects.create(
        apellido=apellido, nombre=nombre, documento=documento
    )
    return NominaCentroInfancia.objects.create(
        centro=centro,
        ciudadano=ciudadano,
        apellido=apellido,
        nombre=nombre,
        dni=documento,
        estado=extra.pop("estado", NominaCentroInfancia.ESTADO_ACTIVO),
        **extra,
    )


@pytest.fixture(name="datos")
def datos_fixture():
    centro = CentroDeInfancia.objects.create(nombre="CDI Girasoles")
    otro = CentroDeInfancia.objects.create(nombre="CDI Ajeno")
    ana = _nomina(centro, "Activa", "Ana", 40111222, sala="Sala verde")
    beto = _nomina(centro, "Beta", "Beto", 40111223)
    _nomina(
        centro,
        "Pendiente",
        "Paz",
        40111224,
        estado=NominaCentroInfancia.ESTADO_PENDIENTE,
    )
    return {"centro": centro, "otro": otro, "ana": ana, "beto": beto}


def _marcar(nomina, presente, usuario, observaciones=None, fecha=FECHA):
    return AsistenciaNominaCentroInfancia.objects.create(
        nomina=nomina,
        fecha=fecha,
        presente=presente,
        observaciones=observaciones,
        registrado_por=usuario,
    )


def test_get_projects_the_native_rows_and_counters(datos):
    user = _usuario("asis-lector", superuser=True)
    _marcar(datos["ana"], True, user, "Llegó tarde")
    client = _cliente(user)

    respuesta = client.get(_api(datos["centro"].pk), {"fecha": FECHA.isoformat()})
    nativo = client.get(
        reverse("centrodeinfancia_nomina_asistencia", args=[datos["centro"].pk]),
        {"fecha": FECHA.isoformat()},
    )

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/json"
    assert respuesta["Cache-Control"] == "private, no-store"
    data = respuesta.json()
    assert set(data) == {
        "centro",
        "fecha",
        "fecha_label",
        "rows",
        "totals",
        "messages",
    }
    assert data["centro"] == {"id": datos["centro"].pk, "nombre": "CDI Girasoles"}
    assert data["fecha"] == "2026-07-01"
    assert data["fecha_label"] == "01/07/2026"
    assert data["rows"] == [
        {
            "id": datos["ana"].pk,
            "nombre": "Activa, Ana",
            "dni": "40111222",
            "sala": "Sala verde",
            "presente": True,
            "observaciones": "Llegó tarde",
        },
        {
            "id": datos["beto"].pk,
            "nombre": "Beta, Beto",
            "dni": "40111223",
            "sala": "-",
            "presente": None,
            "observaciones": "",
        },
    ]
    assert data["totals"] == {"presentes": 1, "ausentes": 0, "sin_marcar": 1}
    assert data["messages"] == []
    context = nativo.context
    assert [fila["nombre_completo"] for fila in context["filas"]] == [
        fila["nombre"] for fila in data["rows"]
    ]
    assert [fila["presente"] for fila in context["filas"]] == [
        fila["presente"] for fila in data["rows"]
    ]
    assert (
        context["total_presentes"],
        context["total_ausentes"],
        context["total_sin_marcar"],
    ) == (1, 0, 1)


def test_get_without_date_uses_today_and_an_invalid_date_reports_the_native_message(
    datos,
):
    client = _cliente(_usuario("asis-fecha", superuser=True))

    hoy = client.get(_api(datos["centro"].pk)).json()
    invalida = client.get(_api(datos["centro"].pk), {"fecha": "2026-13-40"})

    assert hoy["fecha"] == timezone.localdate().isoformat()
    assert invalida.status_code == 200
    assert invalida.json()["messages"] == [
        {
            "message": "La fecha debe tener formato AAAA-MM-DD y ser válida.",
            "level": "error",
        }
    ]
    assert invalida.json()["fecha"] == hoy["fecha"]


def test_get_without_active_nomina_returns_no_rows(datos):
    vacio = CentroDeInfancia.objects.create(nombre="CDI Vacío")

    data = _cliente(_usuario("asis-vacio", superuser=True)).get(_api(vacio.pk)).json()

    assert data["rows"] == []
    assert data["totals"] == {"presentes": 0, "ausentes": 0, "sin_marcar": 0}


def test_post_saves_the_marks_and_redirects_with_the_native_message(datos):
    user = _usuario("asis-guarda")
    client = _cliente(user)

    respuesta = _post(
        client,
        _api(datos["centro"].pk),
        {
            "fecha": FECHA.isoformat(),
            f"presente_{datos['ana'].pk}": "1",
            f"obs_{datos['ana'].pk}": "  Con fiebre  ",
            f"presente_{datos['beto'].pk}": "0",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": (
            reverse("centrodeinfancia_nomina_asistencia", args=[datos["centro"].pk])
            + "?fecha=2026-07-01"
        ),
    }
    marcas = {
        a.nomina_id: (a.presente, a.observaciones, a.registrado_por_id)
        for a in AsistenciaNominaCentroInfancia.objects.filter(fecha=FECHA)
    }
    assert marcas == {
        datos["ana"].pk: (True, "Con fiebre", user.pk),
        datos["beto"].pk: (False, None, user.pk),
    }
    siguiente = client.get(_api(datos["centro"].pk), {"fecha": FECHA.isoformat()})
    assert siguiente.json()["messages"] == [{"message": GUARDADA, "level": "success"}]
    assert siguiente.json()["totals"] == {
        "presentes": 1,
        "ausentes": 1,
        "sin_marcar": 0,
    }


def test_post_without_a_mark_clears_the_previous_one(datos):
    user = _usuario("asis-borra")
    _marcar(datos["ana"], True, user)

    respuesta = _post(
        _cliente(user), _api(datos["centro"].pk), {"fecha": FECHA.isoformat()}
    )

    assert respuesta.status_code == 200
    assert not AsistenciaNominaCentroInfancia.objects.exists()


def test_post_rejected_by_the_native_service_redirects_with_its_message_and_writes_nothing(
    datos,
):
    client = _cliente(_usuario("asis-rechaza"))

    malo = _post(
        client,
        _api(datos["centro"].pk),
        {"fecha": FECHA.isoformat(), f"presente_{datos['ana'].pk}": "9"},
    )
    fecha_mala = _post(client, _api(datos["centro"].pk), {"fecha": "ayer"})

    assert malo.status_code == 200
    assert malo.json() == {
        "ok": True,
        "redirect": reverse(
            "centrodeinfancia_nomina_asistencia", args=[datos["centro"].pk]
        ),
    }
    assert fecha_mala.status_code == 200
    assert not AsistenciaNominaCentroInfancia.objects.exists()
    mensajes = client.get(_api(datos["centro"].pk)).json()["messages"]
    assert [m["level"] for m in mensajes] == ["error", "error"]
    assert mensajes[0]["message"] == "El estado de asistencia recibido no es válido."


def test_post_accepts_urlencoded_only_and_requires_csrf(datos):
    user = _usuario("asis-formato")
    client = _cliente(user)
    estricto = _cliente(user, enforce_csrf_checks=True)

    json_post = client.post(
        _api(datos["centro"].pk), "{}", content_type="application/json"
    )
    multipart = client.post(_api(datos["centro"].pk), {"fecha": "2026-07-01"})
    sin_csrf = _post(estricto, _api(datos["centro"].pk), {"fecha": "2026-07-01"})

    assert json_post.status_code == 415
    assert multipart.status_code == 415
    assert sin_csrf.status_code == 403
    assert not AsistenciaNominaCentroInfancia.objects.exists()


def test_scope_is_enforced_for_the_page_the_post_and_the_native_calendar(datos):
    user = _usuario("asis-referente")
    AccesoCDI.objects.create(user=user, centro=datos["centro"])
    client = _cliente(user)

    assert client.get(_api(datos["centro"].pk)).status_code == 200
    assert client.get(_api(datos["otro"].pk)).status_code == 404
    assert (
        _post(client, _api(datos["otro"].pk), {"fecha": "2026-07-01"}).status_code
        == 404
    )
    assert (
        client.get(_calendario(datos["otro"].pk), {"mes": "2026-07"}).status_code == 404
    )
    assert client.get(_api(999999)).status_code == 404
    native = client.get(
        reverse("centrodeinfancia_nomina_asistencia", args=[datos["otro"].pk])
    )
    assert native.status_code == 404


def test_calendar_stays_the_native_endpoint_the_screen_script_calls(datos):
    user = _usuario("asis-calendario")
    _marcar(datos["ana"], True, user, fecha=date(2026, 7, 1))
    _marcar(datos["beto"], False, user, fecha=date(2026, 7, 1))
    _marcar(datos["ana"], True, user, fecha=date(2026, 7, 15))
    _marcar(datos["ana"], True, user, fecha=date(2026, 8, 1))
    client = _cliente(user)

    respuesta = client.get(_calendario(datos["centro"].pk), {"mes": "2026-07"})
    malo = client.get(_calendario(datos["centro"].pk), {"mes": "2026-13"})

    assert _calendario(datos["centro"].pk) == (
        f"/centrodeinfancia/{datos['centro'].pk}/nomina/asistencia/calendario/"
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"dias": ["2026-07-01", "2026-07-15"]}
    assert client.get(_calendario(datos["centro"].pk), {"mes": "2026-09"}).json() == {
        "dias": []
    }
    assert malo.status_code == 400
    assert malo.json() == {"detail": "El mes debe tener formato AAAA-MM."}
    api = client.get(
        f"/api/web/cdi/centros/{datos['centro'].pk}/nomina/asistencia/calendario/",
        {"mes": "2026-07"},
    )
    assert api.status_code == 404


def test_anonymous_gets_401_and_a_view_only_user_gets_403(datos):
    solo_ver = _usuario(
        "asis-solo-ver", perms=("centrodeinfancia.view_centrodeinfancia",)
    )

    url = _api(datos["centro"].pk)
    anonimo = Client().get(url)
    assert anonimo.status_code == 401
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    prohibido = _cliente(solo_ver).get(url)
    assert prohibido.status_code == 403
    assert prohibido.json() != {"detail": web_gate.DETAIL_REQUIREMENT}
    escritura = _post(
        _cliente(solo_ver), _api(datos["centro"].pk), {"fecha": "2026-07-01"}
    )
    assert escritura.status_code == 403


def test_the_native_urls_keep_working(datos):
    client = _cliente(_usuario("asis-nativo", superuser=True))
    base = reverse("centrodeinfancia_nomina_asistencia", args=[datos["centro"].pk])

    assert client.get(base).status_code == 200
    assert client.get(
        reverse(
            "centrodeinfancia_nomina_asistencia_calendario",
            args=[datos["centro"].pk],
        ),
        {"mes": "2026-07"},
    ).json() == {"dias": []}
    redireccion = client.get(
        reverse("centrodeinfancia_trabajadores_asistencia", args=[datos["centro"].pk]),
        {"fecha": "2026-07-01"},
    )
    assert redireccion.status_code == 302
    assert redireccion["Location"] == base + "?fecha=2026-07-01"
