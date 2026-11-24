"""Edit, delete and review APIs of seguimientos, PNUD and actas (R03.02, R02.02).

These endpoints change persisted data, so every write test asserts the exact
rows that result and every rejected request asserts that nothing changed. The
native view (or form) receives the same input in a differential test.
"""

from datetime import datetime, timezone as dt_timezone

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client
from django.utils import timezone

from comedores.models import Comedor
from relevamientos.models import (
    ActaComplementaria,
    CierreSeguimiento,
    FuncionamientoSeguimiento,
    PrestacionActaComplementaria,
    PrestacionSeguimiento,
    PrimerSeguimiento,
    Relevamiento,
    SeguimientoPnud,
)

API = "/api/web/comedores/relevamientos/"
FECHA = datetime(2026, 3, 4, 15, 7, tzinfo=dt_timezone.utc)
REVIEW = "relevamientos.review_relevamiento"
FORM_ERROR = "Revise los campos marcados en rojo."

pytestmark = pytest.mark.django_db


def _usuario(nombre, *codes, territorial=False, **extra):
    usuario = get_user_model().objects.create_user(nombre, **extra)
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.es_territorial_comedor = territorial
    profile.save()
    for code in codes:
        app, codename = code.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return usuario


def _client(usuario, **extra):
    client = Client(**extra)
    client.force_login(usuario)
    return client


@pytest.fixture(name="gestionar_mock")
def gestionar_fixture(mocker):
    return mocker.patch(
        "relevamientos.signals.AsyncRemovePrimerSeguimientoToGestionar.start"
    )


def _ciclo():
    comedor = Comedor.objects.create(nombre="Comedor <Form>")
    relevamiento = Relevamiento.objects.create(comedor=comedor, estado="Finalizado")
    primero = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        estado=PrimerSeguimiento.ESTADO_COMPLETO,
        fecha_hora=FECHA,
        tecnico="Téc",
        gestionar_id="G-1",
        funcionamiento=FuncionamientoSeguimiento.objects.create(
            funcionamiento="Cerrado"
        ),
        cierre=CierreSeguimiento.objects.create(comentarios_finales="listo"),
    )
    PrestacionSeguimiento.objects.create(
        seguimiento=primero, id_prestacion_seg="p1", dias_prestacion="Lunes", ap_total=5
    )
    posterior = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        tipo=PrimerSeguimiento.TIPO_POSTERIOR,
        numero_orden=2,
    )
    return comedor, relevamiento, primero, posterior


def _seg(comedor, relevamiento, seguimiento, accion):
    return (
        f"{API}{comedor.pk}/relevamiento/{relevamiento.pk}/seguimientos/"
        f"{seguimiento.pk}/{accion}/"
    )


def _estado(seguimiento):
    """Every persisted column of a seguimiento, the blocks it points to and its rows."""
    seguimiento.refresh_from_db()
    campos = {
        f.name: getattr(seguimiento, f.attname)
        for f in PrimerSeguimiento._meta.concrete_fields
    }
    return campos, list(
        seguimiento.prestaciones.order_by("pk").values_list(
            "dias_prestacion",
            "tipo_prestacion",
            "ap_presencial",
            "ap_vianda",
            "ap_total",
        )
    )


def _valores(campos):
    """What a browser would submit for the descriptor's fields (defaults of their widgets)."""
    datos = {}

    def recorrer(nodos):
        for nodo in nodos:
            if isinstance(nodo, str):
                continue
            atributos = nodo["a"]
            if nodo["t"] == "input" and "name" in atributos:
                tipo = atributos.get("type", "text")
                if tipo in ("checkbox", "radio"):
                    if "checked" in atributos:
                        datos[atributos["name"]] = atributos.get("value", "on")
                else:
                    datos[atributos["name"]] = atributos.get("value", "")
            elif nodo["t"] == "select":
                opciones = [o for o in nodo["c"] if not isinstance(o, str)]
                elegida = next((o for o in opciones if "selected" in o["a"]), None)
                elegida = elegida or (opciones[0] if opciones else None)
                datos[atributos["name"]] = (
                    elegida["a"].get("value", "") if elegida else ""
                )
            elif nodo["t"] == "textarea":
                datos[atributos["name"]] = "".join(
                    c for c in nodo["c"] if isinstance(c, str)
                )
            recorrer(nodo["c"])

    for c in campos:
        recorrer(c["nodes"])
    return datos


def _form_seguimiento(data):
    campos = list(data["root"]["fields"])
    for bloque in data["bloques"]:
        campos += bloque["form"]["fields"]
    prest = data["prestaciones"]
    campos += prest["management"]
    for fila in prest["forms"]:
        campos += fila["hidden"] + fila["fields"]
    return _valores(campos)


# --- Seguimiento: edit ---------------------------------------------------------


def test_seguimiento_form_projects_the_native_widgets(client_seg=None):
    comedor, relevamiento, primero, _ = _ciclo()
    editor = _client(_usuario("ed_seg_get", "relevamientos.change_primerseguimiento"))

    respuesta = editor.get(_seg(comedor, relevamiento, primero, "editar"))

    assert respuesta.status_code == 200
    data = respuesta.json()
    assert data["seguimiento"]["tipo_display"] == "Primer seguimiento"
    assert data["comedor"] == {"id": comedor.pk, "nombre": "Comedor <Form>"}
    assert [f["name"] for f in data["root"]["fields"]] == [
        "seg-fecha_hora",
        "seg-estado",
        "seg-tecnico",
        "seg-motivo_diferencia_aprobado_declarado",
    ]
    assert len(data["bloques"]) == 17
    existentes = {b["key"] for b in data["bloques"] if b["existe"]}
    assert existentes == {"funcionamiento", "cierre"}
    estado = data["root"]["fields"][1]["nodes"][0]
    assert estado["t"] == "select" and estado["a"]["name"] == "seg-estado"
    assert any(
        "selected" in o["a"] and o["a"]["value"] == "Completo" for o in estado["c"]
    )
    fecha = data["root"]["fields"][0]["nodes"][0]
    assert fecha["a"]["type"] == "datetime-local"
    assert fecha["a"]["value"] == "2026-03-04T12:07"
    assert [f["name"] for f in data["prestaciones"]["management"]] == [
        "prestaciones-TOTAL_FORMS",
        "prestaciones-INITIAL_FORMS",
        "prestaciones-MIN_NUM_FORMS",
        "prestaciones-MAX_NUM_FORMS",
    ]
    assert len(data["prestaciones"]["forms"]) == 2  # the saved row and the extra one
    nativa = editor.get(
        f"/comedores/{comedor.pk}/relevamiento/{relevamiento.pk}/seguimiento/{primero.pk}/editar"
    ).content.decode()
    nombres = {
        n
        for n in _valores(
            data["root"]["fields"]
            + [c for b in data["bloques"] for c in b["form"]["fields"]]
        )
    }
    assert nombres and all(f'name="{n}"' in nativa for n in nombres)


def test_seguimiento_edit_persists_exactly_what_the_native_editor_does():
    comedor, relevamiento, primero, posterior = _ciclo()
    editor = _client(_usuario("ed_seg_ok", "relevamientos.change_primerseguimiento"))
    datos = _form_seguimiento(
        editor.get(_seg(comedor, relevamiento, primero, "editar")).json()
    )
    datos.update(
        {
            "seg-estado": "En Proceso",
            "seg-tecnico": "Nueva técnica",
            "seg-motivo_diferencia_aprobado_declarado": "Motivo\nnuevo",
            "funcionamiento-funcionamiento": "Abierto en funcionamiento",
            "recursos-recursos_comedor_estado_nacional": "true",
            "prestaciones-1-dias_prestacion": "Martes",
            "prestaciones-1-ap_total": "7",
        }
    )
    datos["prestaciones-TOTAL_FORMS"] = "2"

    respuesta = editor.post(_seg(comedor, relevamiento, primero, "editar"), datos)

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "message": "Seguimiento actualizado correctamente.",
        "redirect": f"/comedores/{comedor.pk}/relevamiento/{relevamiento.pk}/seguimiento/{primero.pk}/",
    }
    campos, prestaciones = _estado(primero)
    assert (campos["estado"], campos["tecnico"]) == ("En Proceso", "Nueva técnica")
    assert campos["motivo_diferencia_aprobado_declarado"] == "Motivo\nnuevo"
    assert prestaciones == [
        ("Lunes", None, None, None, 5),
        ("Martes", None, None, None, 7),
    ]
    primero.refresh_from_db()
    assert primero.funcionamiento.funcionamiento == "Abierto en funcionamiento"
    assert primero.recursos.recursos_comedor_estado_nacional is True
    # Blocks nobody filled in stay absent, and the other instance is untouched.
    assert primero.servicios_basicos is None and primero.menu is None
    assert _estado(posterior)[1] == []
    # The same input through the native view leaves the same columns, blocks and rows on a twin.
    entrada = {
        k: v
        for k, v in datos.items()
        if not k.startswith("prestaciones-") and not k.startswith("cierre-")
    }
    entrada.update(
        {
            "prestaciones-TOTAL_FORMS": "1",
            "prestaciones-INITIAL_FORMS": "0",
            "prestaciones-MIN_NUM_FORMS": "0",
            "prestaciones-MAX_NUM_FORMS": "1000",
            "prestaciones-0-dias_prestacion": "Martes",
            "prestaciones-0-ap_total": "7",
        }
    )
    api_gemelo = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        tipo=PrimerSeguimiento.TIPO_VIRTUAL,
        numero_orden=3,
    )
    nativo_gemelo = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        tipo=PrimerSeguimiento.TIPO_VIRTUAL,
        numero_orden=4,
    )
    api = _client(_usuario("ed_seg_twin", "relevamientos.change_primerseguimiento"))
    nativo = _client(_usuario("ed_seg_nat", "relevamientos.change_primerseguimiento"))
    assert (
        api.post(_seg(comedor, relevamiento, api_gemelo, "editar"), entrada).status_code
        == 200
    )
    nativa = nativo.post(
        f"/comedores/{comedor.pk}/relevamiento/{relevamiento.pk}/seguimiento/{nativo_gemelo.pk}/editar",
        entrada,
    )
    assert nativa.status_code == 302

    def resumen(objeto):
        objeto.refresh_from_db()
        return (
            objeto.estado,
            objeto.tecnico,
            objeto.motivo_diferencia_aprobado_declarado,
            objeto.funcionamiento.funcionamiento,
            objeto.recursos.recursos_comedor_estado_nacional,
            objeto.servicios_basicos_id,
            _estado(objeto)[1],
        )

    assert resumen(api_gemelo) == resumen(nativo_gemelo)
    assert resumen(api_gemelo)[:5] == (
        "En Proceso",
        "Nueva técnica",
        "Motivo\nnuevo",
        "Abierto en funcionamiento",
        True,
    )
    assert resumen(api_gemelo)[6] == [("Martes", None, None, None, 7)]


def test_seguimiento_edit_deletes_a_prestacion_and_creates_no_empty_block():
    comedor, relevamiento, primero, _ = _ciclo()
    editor = _client(_usuario("ed_seg_del", "relevamientos.change_primerseguimiento"))
    datos = _form_seguimiento(
        editor.get(_seg(comedor, relevamiento, primero, "editar")).json()
    )
    datos["prestaciones-0-DELETE"] = "on"
    antes = PrimerSeguimiento.objects.filter(pk=primero.pk).values().get()

    respuesta = editor.post(_seg(comedor, relevamiento, primero, "editar"), datos)

    assert respuesta.status_code == 200
    assert _estado(primero)[1] == []
    primero.refresh_from_db()
    assert primero.servicios_basicos_id is None and primero.menu_id is None
    despues = PrimerSeguimiento.objects.filter(pk=primero.pk).values().get()
    # The native editor saves an untouched empty text as "" instead of NULL (same on both paths).
    assert despues == {**antes, "motivo_diferencia_aprobado_declarado": ""}


def test_seguimiento_edit_invalid_is_400_and_leaves_every_row_unchanged():
    comedor, relevamiento, primero, _ = _ciclo()
    editor = _client(_usuario("ed_seg_bad", "relevamientos.change_primerseguimiento"))
    datos = _form_seguimiento(
        editor.get(_seg(comedor, relevamiento, primero, "editar")).json()
    )
    datos.update(
        {
            "seg-estado": "No existe",
            "funcionamiento-funcionamiento": "Cerrado por reformas",
            "prestaciones-0-ap_total": "-3",
            "prestaciones-1-dias_prestacion": "Nueva",
            "prestaciones-TOTAL_FORMS": "2",
        }
    )
    antes = _estado(primero)
    total = PrestacionSeguimiento.objects.count()

    respuesta = editor.post(_seg(comedor, relevamiento, primero, "editar"), datos)

    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert cuerpo["detail"] == FORM_ERROR
    estado = next(f for f in cuerpo["root"]["fields"] if f["name"] == "seg-estado")
    assert estado["errors"] and "No existe" not in str(estado["nodes"][0]["c"])
    fila = cuerpo["prestaciones"]["forms"][0]["fields"]
    assert any(f["errors"] for f in fila)
    assert _estado(primero) == antes
    assert PrestacionSeguimiento.objects.count() == total
    primero.refresh_from_db()
    assert primero.funcionamiento.funcionamiento == "Cerrado"


def test_seguimiento_edit_access_lookup_and_csrf():
    comedor, relevamiento, primero, _ = _ciclo()
    otro_rel = Relevamiento.objects.create(comedor=comedor)
    otro_comedor = Comedor.objects.create(nombre="Otro")
    url = _seg(comedor, relevamiento, primero, "editar")
    sin = _client(_usuario("ed_seg_sin", "relevamientos.view_relevamiento"))
    editor = _client(_usuario("ed_seg_ok2", "relevamientos.change_primerseguimiento"))
    estricto = _client(
        _usuario("ed_seg_csrf", "relevamientos.change_primerseguimiento"),
        enforce_csrf_checks=True,
    )
    antes = _estado(primero)

    assert sin.get(url).status_code == 403 and sin.post(url, {}).status_code == 403
    assert Client().get(url).status_code == 401
    assert estricto.post(url, {"seg-estado": "Completo"}).status_code == 403
    assert editor.get(_seg(comedor, otro_rel, primero, "editar")).status_code == 404
    assert (
        editor.post(
            f"{API}{otro_comedor.pk}/relevamiento/{relevamiento.pk}/seguimientos/{primero.pk}/editar/",
            {"seg-estado": "Asignado"},
        ).status_code
        == 404
    )
    assert _estado(primero) == antes


# --- Seguimiento: delete -------------------------------------------------------


def test_seguimiento_delete_removes_the_instance_blocks_and_rows(gestionar_mock):
    comedor, relevamiento, primero, posterior = _ciclo()
    funcionamiento_id = primero.funcionamiento_id
    cierre_id = primero.cierre_id
    editor = _client(_usuario("del_seg_ok", "relevamientos.delete_primerseguimiento"))

    respuesta = editor.post(_seg(comedor, relevamiento, primero, "eliminar"), {})

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "message": "Seguimiento eliminado correctamente.",
        "redirect": f"/comedores/{comedor.pk}/relevamiento/{relevamiento.pk}",
    }
    assert not PrimerSeguimiento.objects.filter(pk=primero.pk).exists()
    assert not PrestacionSeguimiento.objects.filter(seguimiento_id=primero.pk).exists()
    assert not FuncionamientoSeguimiento.objects.filter(pk=funcionamiento_id).exists()
    assert not CierreSeguimiento.objects.filter(pk=cierre_id).exists()
    assert PrimerSeguimiento.objects.filter(pk=posterior.pk).exists()
    assert Relevamiento.objects.filter(pk=relevamiento.pk).exists()
    assert gestionar_mock.call_count == 1
    assert (
        editor.post(_seg(comedor, relevamiento, primero, "eliminar"), {}).status_code
        == 404
    )
    assert gestionar_mock.call_count == 1


def test_seguimiento_delete_without_gestionar_id_sends_no_baja(gestionar_mock):
    comedor, relevamiento, _, posterior = _ciclo()
    editor = _client(_usuario("del_seg_nog", "relevamientos.delete_primerseguimiento"))

    assert (
        editor.post(_seg(comedor, relevamiento, posterior, "eliminar"), {}).status_code
        == 200
    )

    assert not PrimerSeguimiento.objects.filter(pk=posterior.pk).exists()
    assert gestionar_mock.call_count == 0


def test_seguimiento_delete_alias_removes_the_first_instance(gestionar_mock):
    comedor, relevamiento, primero, posterior = _ciclo()
    editor = _client(
        _usuario("del_seg_alias", "relevamientos.delete_primerseguimiento")
    )

    respuesta = editor.post(
        f"{API}{comedor.pk}/relevamiento/{relevamiento.pk}/seguimientos/primero/eliminar/",
        {},
    )

    assert respuesta.status_code == 200
    assert not PrimerSeguimiento.objects.filter(pk=primero.pk).exists()
    assert PrimerSeguimiento.objects.filter(pk=posterior.pk).exists()
    sin = Relevamiento.objects.create(comedor=comedor)
    assert (
        editor.post(
            f"{API}{comedor.pk}/relevamiento/{sin.pk}/seguimientos/primero/eliminar/",
            {},
        ).status_code
        == 404
    )


def test_seguimiento_delete_rejections_leave_the_data(gestionar_mock):
    comedor, relevamiento, primero, _ = _ciclo()
    otro = Comedor.objects.create(nombre="Otro")
    url = _seg(comedor, relevamiento, primero, "eliminar")
    sin = _client(_usuario("del_seg_sin", "relevamientos.change_primerseguimiento"))
    editor = _client(_usuario("del_seg_x", "relevamientos.delete_primerseguimiento"))
    estricto = _client(
        _usuario("del_seg_csrf", "relevamientos.delete_primerseguimiento"),
        enforce_csrf_checks=True,
    )

    assert sin.post(url, {}).status_code == 403
    assert Client().post(url, {}).status_code == 401
    assert estricto.post(url, {}).status_code == 403
    assert (
        editor.post(
            f"{API}{otro.pk}/relevamiento/{relevamiento.pk}/seguimientos/{primero.pk}/eliminar/",
            {},
        ).status_code
        == 404
    )
    assert editor.get(url).status_code == 405
    assert PrimerSeguimiento.objects.filter(pk=primero.pk).exists()
    assert PrestacionSeguimiento.objects.filter(seguimiento_id=primero.pk).count() == 1
    assert gestionar_mock.call_count == 0


# --- Reviews -------------------------------------------------------------------


def _revisar(client, url, estado, observaciones=""):
    return client.post(
        url, {"estado_validacion": estado, "observaciones_coordinador": observaciones}
    )


def test_seguimiento_review_stores_the_coordinator_and_rejections_change_nothing():
    comedor, relevamiento, primero, _ = _ciclo()
    revisor = _usuario("rev_seg", REVIEW)
    cliente = _client(revisor)
    url = _seg(comedor, relevamiento, primero, "revision")
    antes = _estado(primero)

    assert _revisar(cliente, url, "A subsanar", " ").status_code == 400
    assert _revisar(cliente, url, "Otro").status_code == 400
    assert _estado(primero) == antes

    respuesta = _revisar(cliente, url, "A subsanar", " Corregir ")
    assert respuesta.status_code == 200
    assert (
        respuesta.json()["message"]
        == "Seguimiento devuelto al territorial para subsanar."
    )
    primero.refresh_from_db()
    assert primero.estado_validacion == "A subsanar"
    assert primero.observaciones_coordinador == "Corregir"
    assert primero.coordinador == revisor and primero.fecha_revision_coordinador

    ok = _revisar(cliente, url, "Validado")
    assert ok.json()["message"] == "Seguimiento validado correctamente."
    primero.refresh_from_db()
    assert (
        primero.estado_validacion == "Validado"
        and primero.observaciones_coordinador is None
    )
    revisado = _estado(primero)
    ya = _revisar(cliente, url, "A subsanar", "x")
    assert ya.status_code == 409
    assert ya.json() == {
        "detail": "El seguimiento ya está validado: no admite otra revisión."
    }
    assert _estado(primero) == revisado


def test_seguimiento_review_access_lookup_and_unsent():
    comedor, relevamiento, primero, posterior = _ciclo()
    otro = Relevamiento.objects.create(comedor=comedor)
    cliente = _client(_usuario("rev_seg2", REVIEW))
    sin = _client(_usuario("rev_seg_sin", "relevamientos.view_relevamiento"))
    estricto = _client(_usuario("rev_seg_csrf", REVIEW), enforce_csrf_checks=True)
    url = _seg(comedor, relevamiento, primero, "revision")

    assert _revisar(sin, url, "Validado").status_code == 403
    assert Client().post(url, {}).status_code == 401
    assert _revisar(estricto, url, "Validado").status_code == 403
    assert (
        _revisar(
            cliente, _seg(comedor, otro, primero, "revision"), "Validado"
        ).status_code
        == 404
    )
    primero.refresh_from_db()
    assert primero.estado_validacion is None
    # An assigned instance nobody loaded yet is not reviewable.
    posterior.estado = PrimerSeguimiento.ESTADO_ASIGNADO
    posterior.origen = "sisoc"
    posterior.save()
    sin_cargar = _revisar(
        cliente, _seg(comedor, relevamiento, posterior, "revision"), "Validado"
    )
    assert sin_cargar.status_code == 409
    assert sin_cargar.json()["detail"].startswith("Todavía no hay nada que revisar")
    posterior.refresh_from_db()
    assert posterior.estado_validacion is None


def _pnud(comedor, datos=None):
    return SeguimientoPnud.objects.create(
        comedor=comedor, formulario="siph", datos={"a": 1} if datos is None else datos
    )


def test_pnud_review_touches_fecha_actualizacion_and_rejections_do_not():
    comedor = Comedor.objects.create(nombre="PNUD")
    pnud = _pnud(comedor)
    vacio = _pnud(comedor, {})
    cliente = _client(_usuario("rev_pnud", REVIEW))
    url = f"{API}{comedor.pk}/pnud/{pnud.pk}/revision/"
    antes = pnud.fecha_actualizacion

    rechazo = _revisar(cliente, url, "A subsanar")
    assert rechazo.status_code == 400
    pnud.refresh_from_db()
    assert pnud.fecha_actualizacion == antes and pnud.estado_validacion is None

    ok = _revisar(cliente, url, "Validado")
    assert ok.status_code == 200
    assert ok.json() == {
        "ok": True,
        "message": "Seguimiento PNUD validado correctamente.",
        "redirect": f"/comedores/{comedor.pk}/seguimiento-pnud/{pnud.pk}",
    }
    pnud.refresh_from_db()
    assert pnud.estado_validacion == "Validado" and pnud.fecha_actualizacion > antes
    assert _revisar(cliente, url, "Validado").status_code == 409
    sin_cargar = _revisar(
        cliente, f"{API}{comedor.pk}/pnud/{vacio.pk}/revision/", "Validado"
    )
    assert sin_cargar.status_code == 409
    vacio.refresh_from_db()
    assert vacio.estado_validacion is None
    otro = Comedor.objects.create(nombre="Otro")
    assert (
        _revisar(
            cliente, f"{API}{otro.pk}/pnud/{pnud.pk}/revision/", "Validado"
        ).status_code
        == 404
    )
    assert (
        _revisar(_client(_usuario("rev_pnud_sin")), url, "Validado").status_code == 403
    )


# --- Acta ----------------------------------------------------------------------


def _acta_url(comedor, accion="crear", acta=None):
    if acta is not None:
        return f"{API}{comedor.pk}/actas/{acta.pk}/{accion}/"
    return f"{API}{comedor.pk}/actas/{accion}/"


def _form_acta(data):
    campos = list(data["form"]["fields"])
    prest = data["prestaciones"]
    campos += prest["management"]
    for fila in prest["forms"]:
        campos += fila["hidden"] + fila["fields"]
    return _valores(campos)


def test_acta_form_projects_the_native_fields():
    comedor = Comedor.objects.create(nombre="Comedor Acta")
    tecnica = _usuario("tec_acta", territorial=True)
    _usuario("no_tec_acta")
    editor = _client(_usuario("acta_get", "relevamientos.add_actacomplementaria"))

    respuesta = editor.get(_acta_url(comedor))

    assert respuesta.status_code == 200
    data = respuesta.json()
    assert data["acta_id"] is None
    assert [f["name"] for f in data["form"]["fields"]] == [
        "acta-fecha_hora",
        "acta-tecnico",
        "acta-observaciones",
    ]
    tecnico = data["form"]["fields"][1]
    assert tecnico["label"] == "Técnico territorial"
    assert (
        tecnico["help_text"]
        == "Si se deja vacío queda registrado el usuario que carga el acta."
    )
    opciones = [
        o["a"]["value"] for o in tecnico["nodes"][0]["c"] if not isinstance(o, str)
    ]
    assert opciones == ["", str(tecnica.pk)]
    assert len(data["prestaciones"]["forms"]) == 1


def test_acta_create_without_tecnico_assigns_the_user_and_origin_sisoc():
    comedor = Comedor.objects.create(nombre="Comedor Acta")
    usuario = _usuario("acta_new", "relevamientos.add_actacomplementaria")
    editor = _client(usuario)
    datos = _form_acta(editor.get(_acta_url(comedor)).json())
    datos.update(
        {
            "acta-fecha_hora": "2026-03-04T12:30",
            "acta-observaciones": "Cambio\nde prestación",
            "prestaciones-0-dias_prestacion": "Lunes",
            "prestaciones-0-tipo_prestacion": "Cena",
            "prestaciones-0-cantidad_actual": "20",
        }
    )

    respuesta = editor.post(_acta_url(comedor), datos)

    assert respuesta.status_code == 200
    acta = ActaComplementaria.objects.get()
    assert respuesta.json() == {
        "ok": True,
        "message": "Acta complementaria guardada correctamente.",
        "redirect": f"/comedores/{comedor.pk}/acta-complementaria/{acta.pk}",
    }
    assert (acta.comedor, acta.tecnico, acta.origen) == (comedor, usuario, "sisoc")
    assert acta.observaciones == "Cambio\nde prestación"
    assert (
        timezone.localtime(acta.fecha_hora).strftime("%Y-%m-%d %H:%M")
        == "2026-03-04 12:30"
    )
    assert list(
        acta.prestaciones.values_list(
            "dias_prestacion", "tipo_prestacion", "cantidad_actual", "cantidad_espera"
        )
    ) == [("Lunes", "Cena", 20, None)]
    # The native view with the same input creates the same acta shape.
    nativo = Client()
    nativo.force_login(_usuario("acta_nat", "relevamientos.add_actacomplementaria"))
    assert (
        nativo.post(
            f"/comedores/{comedor.pk}/acta-complementaria/crear", datos
        ).status_code
        == 302
    )
    gemela = ActaComplementaria.objects.exclude(pk=acta.pk).get()
    assert (gemela.observaciones, gemela.origen, gemela.fecha_hora) == (
        acta.observaciones,
        acta.origen,
        acta.fecha_hora,
    )
    assert list(
        gemela.prestaciones.values_list("dias_prestacion", "cantidad_actual")
    ) == [("Lunes", 20)]


def test_acta_create_with_a_non_territorial_tecnico_or_negative_quantity_creates_nothing():
    comedor = Comedor.objects.create(nombre="Comedor Acta")
    no_tec = _usuario("no_tec2")
    editor = _client(_usuario("acta_bad", "relevamientos.add_actacomplementaria"))
    base = _form_acta(editor.get(_acta_url(comedor)).json())

    malo = editor.post(_acta_url(comedor), {**base, "acta-tecnico": str(no_tec.pk)})
    negativo = editor.post(
        _acta_url(comedor),
        {
            **base,
            "prestaciones-0-dias_prestacion": "Lunes",
            "prestaciones-0-cantidad_actual": "-1",
        },
    )

    assert malo.status_code == 400 and negativo.status_code == 400
    assert malo.json()["detail"] == FORM_ERROR
    assert next(
        f for f in malo.json()["form"]["fields"] if f["name"] == "acta-tecnico"
    )["errors"]
    assert any(
        f["errors"] for f in negativo.json()["prestaciones"]["forms"][0]["fields"]
    )
    assert ActaComplementaria.objects.count() == 0
    assert PrestacionActaComplementaria.objects.count() == 0


def test_acta_edit_updates_and_deletes_rows_and_a_rejection_changes_nothing():
    comedor = Comedor.objects.create(nombre="Comedor Acta")
    acta = ActaComplementaria.objects.create(
        comedor=comedor, observaciones="Viejo", origen="app"
    )
    uno = PrestacionActaComplementaria.objects.create(
        acta=acta, dias_prestacion="Lunes", cantidad_actual=1
    )
    dos = PrestacionActaComplementaria.objects.create(
        acta=acta, dias_prestacion="Martes", cantidad_actual=2
    )
    editor = _client(_usuario("acta_ed", "relevamientos.change_actacomplementaria"))
    url = _acta_url(comedor, "editar", acta)
    datos = _form_acta(editor.get(url).json())
    assert datos["prestaciones-INITIAL_FORMS"] == "2"

    malo = editor.post(url, {**datos, "prestaciones-0-cantidad_actual": "x"})
    assert malo.status_code == 400
    acta.refresh_from_db()
    assert acta.observaciones == "Viejo"
    assert list(
        acta.prestaciones.order_by("pk").values_list("cantidad_actual", flat=True)
    ) == [1, 2]

    datos.update(
        {
            "acta-observaciones": "Nuevo",
            "prestaciones-0-cantidad_actual": "10",
            "prestaciones-1-DELETE": "on",
        }
    )
    ok = editor.post(url, datos)

    assert ok.status_code == 200
    acta.refresh_from_db()
    assert (acta.observaciones, acta.origen, acta.tecnico) == (
        "Nuevo",
        "app",
        acta.tecnico,
    )
    assert acta.tecnico is not None  # no tecnico on edit: the editing user is recorded
    assert list(acta.prestaciones.values_list("pk", "cantidad_actual")) == [
        (uno.pk, 10)
    ]
    assert not PrestacionActaComplementaria.objects.filter(pk=dos.pk).exists()


def test_acta_form_access_lookup_and_csrf():
    comedor = Comedor.objects.create(nombre="Comedor Acta")
    otro = Comedor.objects.create(nombre="Otro")
    acta = ActaComplementaria.objects.create(comedor=comedor, observaciones="x")
    crear = _client(_usuario("acta_c", "relevamientos.add_actacomplementaria"))
    editar = _client(_usuario("acta_e", "relevamientos.change_actacomplementaria"))
    estricto = _client(
        _usuario("acta_csrf", "relevamientos.add_actacomplementaria"),
        enforce_csrf_checks=True,
    )

    assert (
        editar.get(_acta_url(comedor)).status_code == 403
    )  # create needs add, not change
    assert crear.get(_acta_url(comedor, "editar", acta)).status_code == 403
    assert Client().get(_acta_url(comedor)).status_code == 401
    assert estricto.post(_acta_url(comedor), {}).status_code == 403
    assert editar.get(_acta_url(otro, "editar", acta)).status_code == 404
    assert crear.get(f"{API}9999/actas/crear/").status_code == 404
    assert (
        editar.post(
            _acta_url(otro, "editar", acta), {"acta-observaciones": "y"}
        ).status_code
        == 404
    )
    acta.refresh_from_db()
    assert acta.observaciones == "x" and ActaComplementaria.objects.count() == 1


def test_acta_review_and_delete_effects_and_rejections():
    comedor = Comedor.objects.create(nombre="Comedor Acta")
    acta = ActaComplementaria.objects.create(
        comedor=comedor, observaciones="x", origen="app"
    )
    PrestacionActaComplementaria.objects.create(acta=acta, dias_prestacion="Lunes")
    revisor = _usuario("acta_rev", REVIEW)
    cliente = _client(revisor)
    url = _acta_url(comedor, "revision", acta)

    assert _revisar(cliente, url, "A subsanar").status_code == 400
    acta.refresh_from_db()
    assert acta.estado_validacion is None
    ok = _revisar(cliente, url, "Validado")
    assert ok.json()["message"] == "Acta complementaria validada correctamente."
    acta.refresh_from_db()
    assert acta.estado_validacion == "Validado" and acta.coordinador == revisor
    ya = _revisar(cliente, url, "A subsanar", "x")
    assert ya.status_code == 409
    assert ya.json() == {
        "detail": "El acta complementaria ya está validada: no admite otra revisión."
    }
    vacia = ActaComplementaria.objects.create(comedor=comedor)
    sin_cargar = _revisar(cliente, _acta_url(comedor, "revision", vacia), "Validado")
    assert sin_cargar.status_code == 409
    vacia.refresh_from_db()
    assert vacia.estado_validacion is None

    borrador = _client(_usuario("acta_del", "relevamientos.delete_actacomplementaria"))
    sin = _client(_usuario("acta_del_sin", "relevamientos.change_actacomplementaria"))
    assert sin.post(_acta_url(comedor, "eliminar", acta), {}).status_code == 403
    assert ActaComplementaria.objects.filter(pk=acta.pk).exists()
    respuesta = borrador.post(_acta_url(comedor, "eliminar", acta), {})
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "message": "Acta complementaria eliminada correctamente.",
        "redirect": f"/comedores/{comedor.pk}/relevamiento/listar",
    }
    assert not ActaComplementaria.objects.filter(pk=acta.pk).exists()
    assert PrestacionActaComplementaria.objects.count() == 0
    assert ActaComplementaria.objects.filter(pk=vacia.pk).exists()
    assert borrador.post(_acta_url(comedor, "eliminar", acta), {}).status_code == 404


def test_native_writes_still_work(gestionar_mock):
    comedor, relevamiento, primero, posterior = _ciclo()
    usuario = _usuario("nativos", "relevamientos.delete_primerseguimiento", REVIEW)
    cliente = _client(usuario)
    base = f"/comedores/{comedor.pk}/relevamiento/{relevamiento.pk}/seguimiento"

    assert (
        cliente.post(
            f"{base}/{primero.pk}/revision", {"estado_validacion": "Validado"}
        ).status_code
        == 302
    )
    primero.refresh_from_db()
    assert primero.estado_validacion == "Validado"
    assert cliente.post(f"{base}/{posterior.pk}/eliminar").status_code == 302
    assert not PrimerSeguimiento.objects.filter(pk=posterior.pk).exists()
