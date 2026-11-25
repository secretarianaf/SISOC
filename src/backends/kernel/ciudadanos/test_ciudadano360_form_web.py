"""Alta y edición de ciudadano en JSON (C05.02): formulario, escritura nativa y rechazos."""

import io
from datetime import date

import pytest
from PIL import Image
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from ciudadanos import views
from ciudadanos.models import Ciudadano
from core.models import Localidad, Municipio, Nacionalidad, Provincia, Sexo

pytestmark = pytest.mark.django_db

ADD, CHANGE, VIEW = (
    "ciudadanos.add_ciudadano",
    "ciudadanos.change_ciudadano",
    "ciudadanos.view_ciudadano",
)


def _png():
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def renaper_simulado(monkeypatch, settings, tmp_path):
    """Nunca se llama a RENAPER: la búsqueda nativa recibe una respuesta simulada."""
    settings.MEDIA_ROOT = str(tmp_path)
    llamadas = []

    def falso(dni, sexo=None):
        llamadas.append((dni, sexo))
        if dni == "30999000":
            return {"success": False, "message": "No se encontraron datos en RENAPER."}
        return {
            "success": True,
            "data": {
                "nombre": "Rita",
                "apellido": "Renaper",
                "documento": int(dni),
                "fecha_nacimiento": date(1985, 3, 9),
            },
        }

    monkeypatch.setattr(views, "obtener_datos_ciudadano_desde_renaper", falso)
    return llamadas


def _cliente(username, permisos=(ADD, CHANGE, VIEW), csrf=False):
    user = User.objects.create_user(username=username, password="x")
    for codigo in permisos:
        app, codename = codigo.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client


def _estado():
    return list(Ciudadano.all_objects.order_by("pk").values())


def _valor(datos, nombre):
    return next(f["value"] for f in datos["fields"] if f["name"] == nombre)


def _campo(datos, nombre):
    return next(f for f in datos["fields"] if f["name"] == nombre)


@pytest.fixture(name="geo")
def geo_fixture():
    prov = Provincia.objects.create(nombre="Buenos Aires")
    otra = Provincia.objects.create(nombre="Córdoba")
    muni = Municipio.objects.create(nombre="La Plata", provincia=prov)
    Municipio.objects.create(nombre="Capital", provincia=otra)
    loc = Localidad.objects.create(nombre="Centro", municipio=muni)
    return prov, muni, loc


def _datos_validos(**extra):
    return {
        "tipo_registro_identidad": "ESTANDAR",
        "apellido": "Nuevo",
        "nombre": "Nora",
        "fecha_nacimiento": "1990-05-17",
        "tipo_documento": "DNI",
        "documento": "30111222",
        "activo": "on",
        **extra,
    }


# --- Alta ---------------------------------------------------------------------


def test_alta_get_proyecta_el_formulario_nativo(geo):
    respuesta = _cliente("crear_get").get("/api/web/ciudadanos/crear/")
    assert respuesta.status_code == 200, respuesta.content
    datos = respuesta.json()
    assert datos["modo"] == "crear" and datos["revision"] is None
    assert [f["name"] for f in datos["fields"]][:6] == [
        "tipo_registro_identidad",
        "apellido",
        "nombre",
        "fecha_nacimiento",
        "tipo_documento",
        "documento",
    ]
    tipos = _campo(datos, "tipo_registro_identidad")
    assert [c["value"] for c in tipos["choices"]] == [
        "ESTANDAR",
        "SIN_DNI",
        "DNI_NO_VALIDADO_RENAPER",
    ]
    assert _campo(datos, "foto")["widget"] == "file"
    assert _campo(datos, "foto")["current"] is None
    assert _campo(datos, "observaciones")["widget"] == "textarea"
    assert _campo(datos, "latitud")["attrs"]["step"] == "0.000001"
    assert _campo(datos, "activo")["value"] is True
    assert _campo(datos, "apellido")["help_text"] == ""
    # Sin provincia elegida, municipio y localidad solo ofrecen la opción vacía.
    assert [c["value"] for c in _campo(datos, "municipio")["choices"]] == [""]
    assert [c["label"] for c in _campo(datos, "provincia")["choices"][1:]] == [
        "Buenos Aires",
        "Córdoba",
    ]
    assert datos["busqueda"]["sexo"] == "M" and len(datos["busqueda"]["sexos"]) == 4
    assert datos["urls"]["volver"] == "/ciudadanos/listar"
    assert "no-store" in respuesta["Cache-Control"]
    assert _estado() == []


def test_alta_busqueda_precarga_desde_renaper_simulado(renaper_simulado):
    client = _cliente("crear_dni")
    datos = client.get("/api/web/ciudadanos/crear/?dni=30111222&sexo=F").json()
    assert renaper_simulado == [("30111222", "F")]
    assert _valor(datos, "apellido") == "Renaper"
    assert _valor(datos, "documento") == "30111222"
    assert datos["busqueda"] == {
        "dni": "30111222",
        "sexo": "F",
        "sexos": datos["busqueda"]["sexos"],
    }
    assert [m["message"] for m in datos["messages"]] == [
        "Datos cargados desde RENAPER. Complete el formulario del ciudadano."
    ]
    assert _estado() == []


def test_alta_busqueda_invalida_o_sin_resultado_avisa(renaper_simulado):
    client = _cliente("crear_dni2")
    corto = client.get("/api/web/ciudadanos/crear/?dni=12").json()
    assert corto["messages"] == [
        {"message": "Ingrese un DNI numérico válido para buscar.", "level": "warning"}
    ]
    sin = client.get("/api/web/ciudadanos/crear/?dni=30999000").json()
    assert sin["messages"] == [
        {"message": "No se encontraron datos en RENAPER.", "level": "warning"}
    ]
    assert renaper_simulado == [("30999000", "M")]


def test_alta_post_valido_escribe_lo_nativo_con_la_foto(geo):
    prov, muni, loc = geo
    sexo = Sexo.objects.create(sexo="F")
    nacionalidad = Nacionalidad.objects.create(nacionalidad="Argentina")
    client = _cliente("crear_post")
    respuesta = client.post(
        "/api/web/ciudadanos/crear/",
        _datos_validos(
            provincia=str(prov.pk),
            municipio=str(muni.pk),
            localidad=str(loc.pk),
            sexo=str(sexo.pk),
            nacionalidad=str(nacionalidad.pk),
            calle="Mitre",
            email="nora@example.org",
            observaciones="Nota",
            foto=SimpleUploadedFile("legajo.png", _png(), content_type="image/png"),
        ),
    )
    assert respuesta.status_code == 200
    (fila,) = _estado()
    assert respuesta.json() == {"ok": True, "redirect": f"/ciudadanos/ver/{fila['id']}"}
    assert (fila["apellido"], fila["nombre"], fila["documento"]) == (
        "Nuevo",
        "Nora",
        30111222,
    )
    assert fila["fecha_nacimiento"] == date(1990, 5, 17)
    assert (fila["provincia_id"], fila["municipio_id"], fila["localidad_id"]) == (
        prov.pk,
        muni.pk,
        loc.pk,
    )
    assert fila["identificador_interno"] == f"CIU-{fila['id']}"
    assert fila["creado_por_id"] == fila["modificado_por_id"]
    assert fila["foto"].startswith("ciudadanos/") and fila["foto"].endswith(".png")
    assert fila["activo"] is True and fila["deleted_at"] is None
    ficha = client.get(f"/api/web/ciudadanos/{fila['id']}/").json()
    assert ficha["messages"] == [
        {"message": "Ciudadano creado correctamente.", "level": "success"}
    ]


def test_alta_post_invalido_responde_400_sin_escribir():
    client = _cliente("crear_inv")
    respuesta = client.post(
        "/api/web/ciudadanos/crear/",
        {"tipo_registro_identidad": "ESTANDAR", "latitud": "1", "observaciones": "x"},
    )
    assert respuesta.status_code == 400
    datos = respuesta.json()
    assert datos["errors"]["apellido"] == ["Este campo es obligatorio."]
    assert set(datos["errors"]) >= {
        "apellido",
        "nombre",
        "fecha_nacimiento",
        "documento",
    }
    assert datos["non_field_errors"] == [
        "Complete latitud y longitud, o deje ambas vacías."
    ]
    assert _valor(datos, "observaciones") == "x" and _valor(datos, "latitud") == "1"
    assert _estado() == []


def test_alta_sin_dni_exige_motivo_y_documento_duplicado_se_rechaza():
    client = _cliente("crear_sin")
    sin = client.post(
        "/api/web/ciudadanos/crear/",
        {
            "tipo_registro_identidad": "SIN_DNI",
            "tipo_documento": "DNI",
            "apellido": "S",
            "nombre": "N",
        },
    )
    assert sin.status_code == 400
    assert sin.json()["errors"] == {
        "motivo_sin_dni": ["Debe indicar el motivo por el que no posee DNI."]
    }
    assert (
        client.post("/api/web/ciudadanos/crear/", _datos_validos()).status_code == 200
    )
    antes = _estado()
    repetido = client.post("/api/web/ciudadanos/crear/", _datos_validos())
    assert repetido.status_code == 400
    assert repetido.json()["errors"] or repetido.json()["non_field_errors"]
    assert _estado() == antes


# --- Edición ------------------------------------------------------------------


@pytest.fixture(name="existente")
def existente_fixture(geo):
    prov, muni, loc = geo
    return Ciudadano.objects.create(
        nombre="Ana",
        apellido="Uno",
        documento=30111222,
        fecha_nacimiento=date(1990, 5, 17),
        provincia=prov,
        municipio=muni,
        localidad=loc,
        calle="Mitre",
        altura="1",
        email="ana@example.org",
    )


def test_edicion_get_trae_valores_y_restringe_la_geografia(existente):
    datos = (
        _cliente("edit_get").get(f"/api/web/ciudadanos/{existente.pk}/editar/").json()
    )
    assert datos["modo"] == "editar" and datos["busqueda"] is None
    assert _valor(datos, "apellido") == "Uno"
    assert _valor(datos, "documento") == "30111222"
    assert _campo(datos, "tipo_documento")["disabled"] is True
    assert datos["fecha_nacimiento_inicial"] == "1990-05-17"
    assert [c["label"] for c in _campo(datos, "municipio")["choices"]] == [
        "---------",
        "La Plata",
    ]
    assert datos["urls"]["volver"] == f"/ciudadanos/ver/{existente.pk}"
    assert datos["revision"] is None


def test_edicion_trae_el_aviso_de_revision(existente):
    Ciudadano.objects.filter(pk=existente.pk).update(
        tipo_registro_identidad="SIN_DNI",
        motivo_sin_dni=Ciudadano.MOTIVO_SIN_DNI_EXTRAVIADO,
        motivo_sin_dni_descripcion="Perdió el DNI",
        requiere_revision_manual=True,
    )
    revision = (
        _cliente("edit_rev")
        .get(f"/api/web/ciudadanos/{existente.pk}/editar/")
        .json()["revision"]
    )
    assert revision == {
        "sin_dni": True,
        "no_validado": False,
        "motivo_texto": "Documento extraviado o en trámite",
        "descripcion_texto": "Perdió el DNI",
    }


def test_edicion_post_actualiza_lo_nativo_y_no_toca_el_tipo_de_documento(existente):
    client = _cliente("edit_post", (CHANGE, VIEW))
    antes = Ciudadano.objects.values().get(pk=existente.pk)
    respuesta = client.post(
        f"/api/web/ciudadanos/{existente.pk}/editar/",
        _datos_validos(
            apellido="Dos",
            nombre="Ana",
            documento="30111222",
            tipo_documento="PASAPORTE",
            provincia=str(existente.provincia_id),
            municipio=str(existente.municipio_id),
            localidad=str(existente.localidad_id),
            calle="Mitre",
            altura="1",
            email="ana@example.org",
            telefono="1155550000",
        ),
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/ciudadanos/ver/{existente.pk}",
    }
    despues = Ciudadano.objects.values().get(pk=existente.pk)
    cambios = {k for k in antes if antes[k] != despues[k]}
    assert {"apellido", "telefono", "modificado_por_id"} <= cambios
    assert cambios <= {
        "apellido",
        "telefono",
        "modificado_por_id",
        "modificado",
        "identificador_interno",
        "observaciones",  # None pasa a "" como en el formulario nativo
    }
    assert despues["apellido"] == "Dos" and despues["telefono"] == "1155550000"
    assert despues["tipo_documento"] == antes["tipo_documento"]
    ficha = client.get(f"/api/web/ciudadanos/{existente.pk}/").json()
    assert ficha["messages"] == [
        {"message": "Ciudadano actualizado.", "level": "success"}
    ]


def test_edicion_post_invalido_responde_400_sin_escribir(existente):
    antes = _estado()
    respuesta = _cliente("edit_inv").post(
        f"/api/web/ciudadanos/{existente.pk}/editar/",
        {"tipo_registro_identidad": "ESTANDAR", "apellido": ""},
    )
    assert respuesta.status_code == 400
    assert "apellido" in respuesta.json()["errors"]
    assert _estado() == antes


# --- Acceso ---------------------------------------------------------------------


def test_rechazos_de_acceso_no_escriben(existente):
    antes = _estado()
    editar = f"/api/web/ciudadanos/{existente.pk}/editar/"
    assert Client().get("/api/web/ciudadanos/crear/").status_code == 401
    assert Client().post(editar, _datos_validos()).status_code == 401
    sin_permiso = _cliente("form_sin", (VIEW,))
    for url in ("/api/web/ciudadanos/crear/", editar):
        assert sin_permiso.get(url).status_code == 403
        assert sin_permiso.post(url, _datos_validos(documento="1")).status_code == 403
    # Como la vista nativa: el permiso se evalúa antes de buscar el objeto.
    assert sin_permiso.get("/api/web/ciudadanos/999999/editar/").status_code == 403
    con_permiso = _cliente("form_ok")
    assert con_permiso.get("/api/web/ciudadanos/999999/editar/").status_code == 404
    assert (
        con_permiso.post(
            "/api/web/ciudadanos/999999/editar/", _datos_validos()
        ).status_code
        == 404
    )
    assert con_permiso.put(editar).status_code == 405
    # Alta sin ``add`` pero con ``change``: no puede crear.
    solo_cambio = _cliente("form_cambio", (CHANGE,))
    assert (
        solo_cambio.post(
            "/api/web/ciudadanos/crear/", _datos_validos(documento="2")
        ).status_code
        == 403
    )
    assert _estado() == antes


def test_post_exige_csrf(existente):
    client = _cliente("form_csrf", csrf=True)
    antes = _estado()
    assert (
        client.post(
            "/api/web/ciudadanos/crear/", _datos_validos(documento="3")
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/web/ciudadanos/{existente.pk}/editar/", _datos_validos()
        ).status_code
        == 403
    )
    assert _estado() == antes


def test_edicion_con_foto_trae_los_textos_del_widget(existente):
    Ciudadano.objects.filter(pk=existente.pk).update(foto="ciudadanos/legajo.png")
    actual = _campo(
        _cliente("edit_foto").get(f"/api/web/ciudadanos/{existente.pk}/editar/").json(),
        "foto",
    )["current"]
    assert actual["name"] == "ciudadanos/legajo.png"
    assert actual["url"].endswith("/ciudadanos/legajo.png")
    assert actual["initial_text"] and actual["clear_label"] and actual["input_text"]
