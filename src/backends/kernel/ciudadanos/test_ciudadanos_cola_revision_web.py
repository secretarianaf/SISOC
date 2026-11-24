"""Cola de revisión de identidad en JSON (C02.01, C02.02): lista, filtro, resolución y rechazos."""

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client

from ciudadanos.models import Ciudadano

pytestmark = pytest.mark.django_db

PERM = "ciudadanos.revision_identidad"
URL = "/api/web/ciudadanos/revision/"


def _cliente(username, permisos=(PERM,), csrf=False):
    user = User.objects.create_user(username=username, password="x")
    for codigo in permisos:
        app, codename = codigo.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


def _pendiente(apellido, **extra):
    datos = {
        "nombre": "Nora",
        "apellido": apellido,
        "tipo_registro_identidad": Ciudadano.TIPO_REGISTRO_SIN_DNI,
        "motivo_sin_dni": Ciudadano.MOTIVO_SIN_DNI_OTRO,
        "requiere_revision_manual": True,
        "estado_revision_manual": Ciudadano.REVISION_IDENTIDAD_PENDIENTE,
        **extra,
    }
    return Ciudadano.objects.create(**datos)


def _resuelto(apellido, estado):
    """Un legajo ya resuelto; ``save`` recalcula la revisión, así que se fija con ``update``."""
    ciudadano = _pendiente(apellido)
    Ciudadano.objects.filter(pk=ciudadano.pk).update(
        requiere_revision_manual=False, estado_revision_manual=estado
    )
    return ciudadano


def _revision(ciudadano):
    ciudadano.refresh_from_db()
    return ciudadano.requiere_revision_manual, ciudadano.estado_revision_manual


def test_cola_proyecta_filas_motivos_y_totales():
    sin_dni = _pendiente(
        "Alfa",
        motivo_sin_dni_descripcion="x" * 80,
        identificador_interno="INT-1",
    )
    no_validado = _pendiente(
        "Beta",
        documento=30111222,
        tipo_registro_identidad=Ciudadano.TIPO_REGISTRO_DNI_NO_VALIDADO,
        motivo_no_validacion_renaper=Ciudadano.MOTIVO_NO_VALIDADO_TRANSCRIPCION,
    )
    # Un legajo estándar y otro ya resuelto no entran en «pendiente».
    Ciudadano.objects.create(nombre="Est", apellido="Andar", documento=3)
    _resuelto("Gama", Ciudadano.REVISION_IDENTIDAD_APROBADA)
    respuesta = _cliente("cola_get").get(URL)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["estado"] == "pendiente"
    assert datos["estados"] == [
        {"value": "pendiente", "label": "Revisión Pendiente"},
        {"value": "descartada", "label": "Solicitudes descartadas"},
        {"value": "aprobada", "label": "Solicitudes aprobadas"},
    ]
    assert (datos["total_pendientes"], datos["total_filtrado"]) == (2, 2)
    alfa, beta = datos["filas"]
    assert alfa["id"] == sin_dni.pk
    assert alfa["nombre_texto"] == "Alfa, Nora"
    assert alfa["identificador"] == "INT-1"
    assert alfa["documento"] == "-"
    assert alfa["tipo_registro"] == "SIN_DNI"
    assert alfa["motivo"]["texto"] == "Otro"
    assert alfa["motivo"]["descripcion"] == "x" * 59 + "…"
    assert alfa["provincia"] == "-"
    assert alfa["estado_revision"] == "PENDIENTE"
    assert alfa["editar_url"] == f"/ciudadanos/editar/{sin_dni.pk}"
    assert beta["id"] == no_validado.pk
    assert beta["documento"] == "30111222"
    assert beta["motivo"]["texto"] == "Errores en la transcripción de datos manuales"
    assert beta["motivo"]["descripcion"] is None
    assert datos["paginacion"]["paginated"] is False
    assert datos["cola_url"] == "/ciudadanos/revision/"
    assert datos["messages"] == []
    assert "no-store" in respuesta["Cache-Control"]


def test_filtro_de_estado_y_valor_invalido():
    _pendiente("Pend")
    aprobada = _resuelto("Apro", Ciudadano.REVISION_IDENTIDAD_APROBADA)
    cliente = _cliente("cola_filtro")
    datos = cliente.get(f"{URL}?estado=aprobada").json()
    assert datos["estado"] == "aprobada"
    assert [f["id"] for f in datos["filas"]] == [aprobada.pk]
    assert datos["filas"][0]["estado_revision"] == "APROBADA"
    assert (datos["total_pendientes"], datos["total_filtrado"]) == (1, 1)
    assert cliente.get(f"{URL}?estado=descartada").json()["filas"] == []
    # Un estado desconocido cae en «pendiente», como la vista nativa.
    assert cliente.get(f"{URL}?estado=otro").json()["estado"] == "pendiente"


def test_paginacion_de_25_y_pagina_inexistente():
    for numero in range(30):
        _pendiente(f"Pag{numero:02d}")
    cliente = _cliente("cola_pag")
    primera = cliente.get(URL).json()
    assert len(primera["filas"]) == 25
    assert primera["paginacion"] == {
        "paginated": True,
        "number": 1,
        "previous": None,
        "next": 2,
        "range": [1, 2],
        "count": 30,
    }
    segunda = cliente.get(f"{URL}?page=2").json()
    assert len(segunda["filas"]) == 5
    assert segunda["paginacion"]["previous"] == 1
    assert cliente.get(f"{URL}?page=9").status_code == 404


@pytest.mark.parametrize(
    "accion, estado",
    [
        ("marcar-revisado", "APROBADA"),
        ("descartar-revision", "DESCARTADA"),
    ],
)
def test_resolver_escribe_lo_nativo_y_vuelve_a_la_cola(accion, estado):
    cliente = _cliente(f"cola_{accion[:4]}")
    ciudadano = _pendiente("Resu")
    respuesta = cliente.post(
        f"/api/web/ciudadanos/{ciudadano.pk}/{accion}/",
        {"next": "/ciudadanos/revision/?estado=pendiente"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": "/ciudadanos/revision/?estado=pendiente",
    }
    assert _revision(ciudadano) == (False, estado)
    verbo = "revisado" if accion == "marcar-revisado" else "descartado"
    assert cliente.get(URL).json()["messages"] == [
        {
            "message": f"Ciudadano {ciudadano} marcado como {verbo}.",
            "level": "success",
        }
    ]
    assert cliente.get(URL).json()["filas"] == []


def test_resolver_ignora_un_next_externo():
    cliente = _cliente("cola_next")
    ciudadano = _pendiente("Next")
    respuesta = cliente.post(
        f"/api/web/ciudadanos/{ciudadano.pk}/descartar-revision/",
        {"next": "https://evil.example/"},
    )
    assert respuesta.json()["redirect"] == f"/ciudadanos/ver/{ciudadano.pk}"
    assert _revision(ciudadano) == (False, "DESCARTADA")


def test_rechazos_no_resuelven_ni_listan():
    ciudadano = _pendiente("Rech")
    acciones = (
        f"/api/web/ciudadanos/{ciudadano.pk}/marcar-revisado/",
        f"/api/web/ciudadanos/{ciudadano.pk}/descartar-revision/",
    )
    sin_permiso = _cliente("cola_sin", ("ciudadanos.view_ciudadano",))
    assert Client().get(URL).status_code == 401
    assert sin_permiso.get(URL).status_code == 403
    for accion in acciones:
        assert Client().post(accion).status_code == 401
        assert sin_permiso.post(accion).status_code == 403
    # Sin permiso un id inexistente tampoco filtra: 403 antes que 404.
    assert (
        sin_permiso.post("/api/web/ciudadanos/999999/descartar-revision/").status_code
        == 403
    )
    con_permiso = _cliente("cola_ok")
    assert (
        con_permiso.post("/api/web/ciudadanos/999999/descartar-revision/").status_code
        == 404
    )
    assert con_permiso.get(acciones[1]).status_code == 405
    assert con_permiso.post(URL).status_code == 405
    assert _revision(ciudadano) == (True, "PENDIENTE")


def test_resolver_exige_csrf():
    ciudadano = _pendiente("Csrf")
    cliente = _cliente("cola_csrf", csrf=True)
    for accion in ("marcar-revisado", "descartar-revision"):
        respuesta = cliente.post(f"/api/web/ciudadanos/{ciudadano.pk}/{accion}/")
        assert respuesta.status_code == 403
    assert _revision(ciudadano) == (True, "PENDIENTE")
