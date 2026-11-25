"""Programas en JSON (T05): consulta, alta, edición y baja con el acceso actual (solo sesión)."""

from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import User
from django.test import Client

from core.models import Programa

pytestmark = pytest.mark.django_db

FORM = "application/x-www-form-urlencoded"
BASE = "/api/web/core/programas/"


def _cliente(username="prog_user", csrf=False):
    user = User.objects.create_user(username=username, password="x")
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


def _post(client, url, datos):
    return client.post(url, urlencode(datos), content_type=FORM)


def _estado():
    return list(
        Programa.objects.order_by("pk").values_list(
            "pk", "nombre", "estado", "observaciones", "descripcion"
        )
    )


def test_anonimo_recibe_401_en_todas_las_rutas():
    programa = Programa.objects.create(nombre="Anonimo")
    cliente = Client()
    for url in (
        BASE,
        f"{BASE}crear/",
        f"{BASE}{programa.pk}/",
        f"{BASE}{programa.pk}/editar/",
        f"{BASE}{programa.pk}/eliminar/",
    ):
        assert cliente.get(url).status_code == 401


def test_listado_ordena_por_nombre_y_pagina_de_a_25():
    for i in range(26):
        Programa.objects.create(nombre=f"Prog {i:02d}", estado=i % 2 == 0)
    cliente = _cliente()
    datos = cliente.get(BASE).json()
    assert [item["nombre"] for item in datos["items"]] == [
        f"Prog {i:02d}" for i in range(25)
    ]
    assert datos["items"][0]["estado"] is True
    assert datos["items"][1]["estado"] is False
    assert datos["items"][0]["organismo"] is None
    pagina = datos["pagination"]
    assert pagina["paginated"] is True
    assert (pagina["number"], pagina["previous"], pagina["next"]) == (1, None, 2)
    assert pagina["count"] == 26
    assert datos["urls"]["create"] == "/programas/crear/"
    primero = Programa.objects.get(nombre="Prog 00")
    assert datos["items"][0]["urls"] == {
        "detail": f"/programas/{primero.pk}/",
        "edit": f"/programas/{primero.pk}/editar/",
        "delete": f"/programas/{primero.pk}/eliminar/",
    }
    segunda = cliente.get(f"{BASE}?page=2").json()
    assert [item["nombre"] for item in segunda["items"]] == ["Prog 25"]
    assert segunda["pagination"]["previous"] == 1
    assert cliente.get(f"{BASE}?page=9").status_code == 404


def test_listado_vacio_no_pagina():
    datos = _cliente().get(BASE).json()
    assert datos["items"] == []
    assert datos["pagination"]["paginated"] is False
    assert datos["pagination"]["count"] == 0


def test_detalle_y_404():
    programa = Programa.objects.create(
        nombre="Detalle", estado=False, observaciones="obs", descripcion="desc"
    )
    cliente = _cliente()
    respuesta = cliente.get(f"{BASE}{programa.pk}/")
    datos = respuesta.json()
    assert datos["nombre"] == "Detalle"
    assert datos["estado"] is False
    assert (datos["observaciones"], datos["descripcion"]) == ("obs", "desc")
    assert datos["organismo"] is None
    assert datos["urls"]["edit"] == f"/programas/{programa.pk}/editar/"
    assert "no-store" in respuesta["Cache-Control"]
    assert cliente.get(f"{BASE}0/").status_code == 404


def test_formulario_de_alta_proyecta_los_campos_nativos():
    datos = _cliente().get(f"{BASE}crear/").json()
    assert datos["mode"] == "create"
    assert [f["name"] for f in datos["fields"]] == [
        "nombre",
        "estado",
        "observaciones",
        "organismo",
        "descripcion",
    ]
    nombre, estado, observaciones, organismo, descripcion = datos["fields"]
    assert (nombre["widget"], nombre["required"], nombre["attrs"]["maxlength"]) == (
        "text",
        True,
        "255",
    )
    assert (estado["widget"], estado["value"]) == ("checkbox", True)
    assert observaciones["attrs"]["maxlength"] == "500"
    assert organismo["widget"] == "select"
    assert organismo["attrs"]["class"] == "form-control"
    assert descripcion["widget"] == "textarea"
    assert [f["label"] for f in datos["fields"]] == [
        "Nombre",
        "Estado",
        "Observaciones",
        "Organismo",
        "Descripción",
    ]


def test_alta_persiste_deja_el_mensaje_y_capitaliza():
    cliente = _cliente()
    respuesta = _post(
        cliente,
        f"{BASE}crear/",
        {
            "nombre": "programa nuevo",
            "estado": "on",
            "observaciones": "o",
            "descripcion": "d",
        },
    )
    assert respuesta.status_code == 200
    programa = Programa.objects.get()
    assert respuesta.json() == {"ok": True, "redirect": f"/programas/{programa.pk}/"}
    assert (programa.nombre, programa.estado, programa.observaciones) == (
        "Programa nuevo",
        True,
        "o",
    )
    assert programa.organismo_id is None
    primera = cliente.get(f"{BASE}{programa.pk}/").json()
    assert primera["messages"] == [
        {"message": "Programa creado correctamente.", "level": "success"}
    ]
    assert cliente.get(f"{BASE}{programa.pk}/").json()["messages"] == []


def test_alta_sin_estado_guarda_inactivo():
    _post(_cliente(), f"{BASE}crear/", {"nombre": "Inactivo"})
    assert Programa.objects.get().estado is False


def test_alta_rechazada_no_escribe_y_devuelve_el_formulario_ligado():
    Programa.objects.create(nombre="Repetido")
    antes = _estado()
    cliente = _cliente()
    vacio = _post(cliente, f"{BASE}crear/", {"nombre": ""})
    assert vacio.status_code == 400
    campos = {f["name"]: f for f in vacio.json()["fields"]}
    assert campos["nombre"]["errors"] == ["Este campo es requerido."]
    repetido = _post(cliente, f"{BASE}crear/", {"nombre": "Repetido"})
    assert repetido.status_code == 400
    campos = {f["name"]: f for f in repetido.json()["fields"]}
    assert campos["nombre"]["value"] == "Repetido"
    assert campos["nombre"]["errors"]
    largo = _post(
        cliente, f"{BASE}crear/", {"nombre": "Largo", "observaciones": "x" * 501}
    )
    assert largo.status_code == 400
    assert _estado() == antes
    assert cliente.get(BASE).json()["messages"] == []


def test_edicion_persiste_deja_el_mensaje_y_respeta_el_404():
    programa = Programa.objects.create(nombre="Editable", estado=True)
    cliente = _cliente()
    formulario = cliente.get(f"{BASE}{programa.pk}/editar/").json()
    assert formulario["mode"] == "edit"
    valores = {f["name"]: f["value"] for f in formulario["fields"]}
    assert (valores["nombre"], valores["estado"]) == ("Editable", True)
    respuesta = _post(
        cliente,
        f"{BASE}{programa.pk}/editar/",
        {"nombre": "Editado", "observaciones": "nueva"},
    )
    assert respuesta.json() == {"ok": True, "redirect": f"/programas/{programa.pk}/"}
    programa.refresh_from_db()
    assert (programa.nombre, programa.estado, programa.observaciones) == (
        "Editado",
        False,
        "nueva",
    )
    assert cliente.get(f"{BASE}{programa.pk}/").json()["messages"] == [
        {"message": "Programa actualizado correctamente.", "level": "success"}
    ]
    assert cliente.get(f"{BASE}0/editar/").status_code == 404
    assert _post(cliente, f"{BASE}0/editar/", {"nombre": "X"}).status_code == 404


def test_edicion_rechazada_no_modifica():
    Programa.objects.create(nombre="Otro")
    programa = Programa.objects.create(nombre="Mio", observaciones="intacta")
    antes = _estado()
    respuesta = _post(_cliente(), f"{BASE}{programa.pk}/editar/", {"nombre": "Otro"})
    assert respuesta.status_code == 400
    assert _estado() == antes


def test_baja_confirma_borra_y_vuelve_al_listado():
    programa = Programa.objects.create(nombre="Baja")
    sobrevive = Programa.objects.create(nombre="Sobrevive")
    cliente = _cliente()
    confirmacion = cliente.get(f"{BASE}{programa.pk}/eliminar/").json()
    assert confirmacion["nombre"] == "Baja"
    assert confirmacion["urls"]["detail"] == f"/programas/{programa.pk}/"
    assert Programa.objects.count() == 2
    respuesta = _post(cliente, f"{BASE}{programa.pk}/eliminar/", {})
    assert respuesta.json() == {"ok": True, "redirect": "/programas/"}
    assert list(Programa.objects.values_list("pk", flat=True)) == [sobrevive.pk]
    assert cliente.get(BASE).json()["messages"] == []
    assert cliente.get(f"{BASE}{programa.pk}/eliminar/").status_code == 404
    assert _post(cliente, f"{BASE}{programa.pk}/eliminar/", {}).status_code == 404


def test_cualquier_usuario_autenticado_opera_acceso_actual():
    """Decisión 2026-11-10: sin permisos específicos; el arreglo posterior debe cambiar esta prueba."""
    cliente = _cliente("sin_permisos")
    assert _post(cliente, f"{BASE}crear/", {"nombre": "Libre"}).status_code == 200
    assert Programa.objects.filter(nombre="Libre").exists()


def test_post_sin_csrf_es_403_y_no_escribe():
    cliente = _cliente("csrf", csrf=True)
    antes = _estado()
    assert _post(cliente, f"{BASE}crear/", {"nombre": "Sin token"}).status_code == 403
    assert _estado() == antes
