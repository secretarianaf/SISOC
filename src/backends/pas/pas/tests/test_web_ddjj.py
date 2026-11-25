"""Public DDJJ JSON transport and canonical React entry (P1 session policy)."""

import hashlib
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from runpy import run_path
from types import ModuleType

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Municipio, Provincia
from encuestas.models import Pregunta, TipoPregunta, TipoSegmentacion
from encuestas.services import actualizar_segmentacion, crear_encuesta
from encuestas.tests.helpers import publicar_para_test
from pas.models import PasDeclaracionJurada, PasEstado, PasInvitacionDDJJ, PasPersona
from pas.services.ddjj_service import crear_invitacion

TEXTO_NO_DISPONIBLE = "Este enlace ya fue utilizado o se encuentra vencido."


@pytest.fixture
def persona():
    provincia = Provincia.objects.create(nombre="Provincia inicial")
    municipio = Municipio.objects.create(
        nombre="Municipio inicial", provincia=provincia
    )
    Municipio.objects.create(nombre="Aaa primero", provincia=provincia)
    return PasPersona.objects.create(
        id_persona=9181,
        apellidos="Sintetica",
        nombres="Persona",
        dni=30999777,
        provincia=provincia,
        municipio=municipio,
        calle="Calle sintetica",
        altura="742",
        domicilio="Calle sintetica 742",
        correo_electronico="persona@example.test",
        telefono_celular="1100000000",
        estado=PasEstado.objects.create(nombre="Activo DDJJ web"),
    )


def _rutas(invitacion):
    token = invitacion.token
    return {
        "canonica": f"/pas/ddjj/formulario/{token}",
        "datos": f"/pas/ddjj/formulario/{token}/datos",
        "envio": f"/pas/ddjj/formulario/{token}/enviar",
        "municipios": f"/pas/ddjj/formulario/{token}/municipios",
    }


def _envio(provincia, municipio, **cambios):
    datos = {
        "datos_mi_argentina_confirmados": "no",
        "calle": "Calle nueva",
        "altura": "15",
        "provincia": str(provincia.pk),
        "municipio": str(municipio.pk),
        "correo_electronico": "nuevo@example.test",
        "telefono_celular": "1122223333",
        "embarazada": "no",
        "hijos_menores_a_cargo": "no",
        "gastos_bajo_limite_smvm": "si",
        "no_accedio_mercado_cambios": "si",
        "acepto_declaracion": "on",
    }
    datos.update(cambios)
    return {clave: valor for clave, valor in datos.items() if valor is not None}


def _huella(persona):
    persona.refresh_from_db()
    return (
        PasDeclaracionJurada.objects.count(),
        tuple(
            PasInvitacionDDJJ.objects.order_by("pk").values_list(
                "pk", "utilizada", "revocada"
            )
        ),
        (
            persona.provincia_id,
            persona.municipio_id,
            persona.calle,
            persona.altura,
            persona.domicilio,
            persona.correo_electronico,
            persona.telefono_celular,
        ),
    )


def _csrf_client():
    client = Client(enforce_csrf_checks=True)
    return client


def _post_con_csrf(client, invitacion, datos):
    respuesta = client.get(_rutas(invitacion)["datos"])
    assert respuesta.status_code == 200
    token = respuesta.cookies["csrftoken"].value
    return client.post(_rutas(invitacion)["envio"], datos, HTTP_X_CSRFTOKEN=token)


@pytest.mark.django_db
def test_datos_publicos_reflejan_el_formulario_sin_login_ni_escrituras(persona):
    invitacion = crear_invitacion(persona)
    otra = Provincia.objects.create(nombre="Otra provincia")
    Municipio.objects.create(nombre="Fuera de la provincia", provincia=otra)
    antes = _huella(persona)
    client = Client()

    respuesta = client.get(_rutas(invitacion)["datos"], {"extra": "ignorado"})

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/json"
    assert "no-store" in respuesta["Cache-Control"]
    assert "private" in respuesta["Cache-Control"]
    assert "csrftoken" in respuesta.cookies
    assert "sessionid" not in respuesta.cookies
    cuerpo = respuesta.json()
    assert cuerpo["values"] == {
        "calle": "Calle sintetica",
        "altura": "742",
        "provincia": str(persona.provincia_id),
        "municipio": str(persona.municipio_id),
        "correo_electronico": "persona@example.test",
        "telefono_celular": "1100000000",
        "embarazada": "",
        "controles_embarazo_cumplidos": "",
        "hijos_menores_a_cargo": "",
        "vacunacion_cumplida": "",
        "regularidad_escolar_acreditada": "",
        "gastos_bajo_limite_smvm": "",
        "no_accedio_mercado_cambios": "",
        "acepto_declaracion": False,
    }
    assert cuerpo["existing"] == {
        "calle": True,
        "altura": True,
        "provincia": True,
        "municipio": True,
        "correo_electronico": True,
        "telefono_celular": True,
    }
    assert cuerpo["labels"]["calle"] == "Calle"
    assert cuerpo["labels"]["embarazada"] == "¿Estás embarazada?"
    assert cuerpo["labels"]["acepto_declaracion"].startswith("Confirmo que estos")
    assert cuerpo["empty_label"] == "---------"
    assert cuerpo["provinces"] == [
        {"id": str(otra.pk), "label": "Otra provincia"},
        {"id": str(persona.provincia_id), "label": "Provincia inicial"},
    ]
    assert [item["label"] for item in cuerpo["municipalities"]] == [
        "Aaa primero",
        "Municipio inicial",
    ]
    assert cuerpo["urls"] == {
        "municipalities": _rutas(invitacion)["municipios"],
        "submit": _rutas(invitacion)["envio"],
        "confirmation": reverse("pas_ddjj_confirmacion"),
    }
    assert "errors" not in cuerpo
    assert b"ignorado" not in respuesta.content
    assert _huella(persona) == antes
    assert not Session.objects.exists()


@pytest.mark.django_db
def test_datos_y_envio_conservan_404_y_410_sin_datos_personales(persona):
    client = Client()
    desconocida = "/pas/ddjj/formulario/00000000-0000-4000-8000-000000000000"
    assert client.get(desconocida + "/datos").status_code == 404
    assert client.post(desconocida + "/enviar", {}).status_code == 404

    ahora = timezone.now()
    estados = [
        {"utilizada": ahora},
        {"revocada": ahora},
        {"vence": ahora - timedelta(minutes=1)},
    ]
    for campos in estados:
        invitacion = crear_invitacion(persona)
        PasInvitacionDDJJ.objects.filter(pk=invitacion.pk).update(**campos)
        antes = _huella(persona)
        for metodo, ruta in (("get", "datos"), ("post", "envio")):
            argumentos = (
                (_envio(persona.provincia, persona.municipio),)
                if metodo == "post"
                else ()
            )
            respuesta = getattr(client, metodo)(_rutas(invitacion)[ruta], *argumentos)
            assert respuesta.status_code == 410
            assert respuesta.json() == {"detail": TEXTO_NO_DISPONIBLE}
            assert b"persona@example.test" not in respuesta.content
        assert _huella(persona) == antes


@pytest.mark.django_db
def test_envio_valido_con_csrf_persiste_por_presentar_ddjj(persona, tmp_path):
    nueva = Provincia.objects.create(nombre="Provincia nueva")
    municipio = Municipio.objects.create(nombre="Municipio nuevo", provincia=nueva)
    invitacion = crear_invitacion(persona)
    client = _csrf_client()

    with override_settings(MEDIA_ROOT=tmp_path):
        respuesta = _post_con_csrf(
            client,
            invitacion,
            _envio(
                nueva,
                municipio,
                embarazada="si",
                controles_embarazo_cumplidos="si",
                hijos_menores_a_cargo="si",
                vacunacion_cumplida="no",
                regularidad_escolar_acreditada="si",
                gastos_bajo_limite_smvm="no",
                no_accedio_mercado_cambios="si",
            ),
        )
        declaracion = PasDeclaracionJurada.objects.get()
        assert declaracion.archivo_pdf.read().startswith(b"%PDF")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"redirect": reverse("pas_ddjj_confirmacion")}
    assert "no-store" in respuesta["Cache-Control"]
    invitacion.refresh_from_db()
    persona.refresh_from_db()
    assert invitacion.utilizada is not None
    assert declaracion.invitacion_id == invitacion.pk
    assert declaracion.version == 1
    assert declaracion.provincia_id == nueva.pk
    assert declaracion.municipio_id == municipio.pk
    assert declaracion.domicilio == "Calle nueva 15"
    assert declaracion.correo_electronico == "nuevo@example.test"
    assert declaracion.telefono_celular == "1122223333"
    assert declaracion.datos_mi_argentina_confirmados is False
    assert declaracion.embarazada is True
    assert declaracion.controles_embarazo_cumplidos is True
    assert declaracion.hijos_menores_a_cargo is True
    assert declaracion.vacunacion_cumplida is False
    assert declaracion.regularidad_escolar_acreditada is True
    assert declaracion.gastos_bajo_limite_smvm is False
    assert declaracion.no_accedio_mercado_cambios is True
    assert declaracion.acepto_declaracion is True
    assert declaracion.finalizada is not None
    assert (persona.provincia_id, persona.municipio_id) == (nueva.pk, municipio.pk)
    assert (persona.calle, persona.altura, persona.domicilio) == (
        "Calle nueva",
        "15",
        "Calle nueva 15",
    )
    second = client.post(
        _rutas(invitacion)["envio"],
        _envio(nueva, municipio),
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )
    assert second.status_code == 410
    assert PasDeclaracionJurada.objects.count() == 1


@pytest.mark.django_db
def test_envio_sin_csrf_se_rechaza_sin_escrituras(persona):
    invitacion = crear_invitacion(persona)
    client = _csrf_client()
    client.get(_rutas(invitacion)["datos"])
    antes = _huella(persona)

    respuesta = client.post(
        _rutas(invitacion)["envio"], _envio(persona.provincia, persona.municipio)
    )

    assert respuesta.status_code == 403
    assert _huella(persona) == antes


@pytest.mark.django_db
def test_envio_invalido_devuelve_400_con_valores_y_errores_sin_escrituras(persona):
    otra = Provincia.objects.create(nombre="Otra provincia")
    ajeno = Municipio.objects.create(nombre="Ajeno", provincia=otra)
    invitacion = crear_invitacion(persona)
    client = _csrf_client()
    antes = _huella(persona)

    respuesta = _post_con_csrf(
        client,
        invitacion,
        _envio(
            otra,
            persona.municipio,
            calle="",
            correo_electronico="no-es-correo",
            embarazada="si",
            hijos_menores_a_cargo="si",
            vacunacion_cumplida="si",
            gastos_bajo_limite_smvm="no",
            acepto_declaracion=None,
        ),
    )

    assert respuesta.status_code == 400
    cuerpo = respuesta.json()
    assert cuerpo["errors"] == {
        "calle": ["Este dato es obligatorio."],
        "municipio": [
            "Seleccione una opción válida. La opción seleccionada no es una de "
            "las disponibles.",
            "Este dato es obligatorio.",
        ],
        "correo_electronico": [
            "Introduzca una dirección de correo electrónico válida.",
            "Este dato es obligatorio.",
        ],
        "controles_embarazo_cumplidos": ["Esta respuesta es obligatoria."],
        "regularidad_escolar_acreditada": ["Esta respuesta es obligatoria."],
        "acepto_declaracion": ["Este campo es requerido."],
    }
    assert cuerpo["values"]["calle"] == ""
    assert cuerpo["values"]["provincia"] == str(otra.pk)
    assert cuerpo["values"]["municipio"] == str(persona.municipio_id)
    assert cuerpo["values"]["correo_electronico"] == "no-es-correo"
    assert cuerpo["values"]["gastos_bajo_limite_smvm"] == "no"
    assert cuerpo["values"]["vacunacion_cumplida"] == "si"
    assert cuerpo["values"]["acepto_declaracion"] is False
    assert cuerpo["municipalities"] == [{"id": str(ajeno.pk), "label": "Ajeno"}]
    assert _huella(persona) == antes


@pytest.mark.django_db
def test_municipio_fuera_de_la_provincia_es_error_de_formulario(persona):
    otra = Provincia.objects.create(nombre="Otra provincia")
    invitacion = crear_invitacion(persona)
    antes = _huella(persona)

    respuesta = Client().post(
        _rutas(invitacion)["envio"],
        _envio(otra, persona.municipio),
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["errors"] == {
        "municipio": [
            "Seleccione una opción válida. La opción seleccionada no es una de "
            "las disponibles.",
            "Este dato es obligatorio.",
        ]
    }
    assert _huella(persona) == antes


@pytest.mark.django_db
def test_envio_que_pierde_disponibilidad_durante_la_presentacion_da_410(
    persona, monkeypatch, tmp_path
):
    from pas import web_ddjj

    invitacion = crear_invitacion(persona)
    original = web_ddjj.presentar_ddjj

    def revocar_y_presentar(inv, form):
        PasInvitacionDDJJ.objects.filter(pk=inv.pk).update(revocada=timezone.now())
        return original(inv, form)

    monkeypatch.setattr(web_ddjj, "presentar_ddjj", revocar_y_presentar)
    with override_settings(MEDIA_ROOT=tmp_path):
        respuesta = Client().post(
            _rutas(invitacion)["envio"], _envio(persona.provincia, persona.municipio)
        )

    assert respuesta.status_code == 410
    assert respuesta.json() == {"detail": TEXTO_NO_DISPONIBLE}
    assert PasDeclaracionJurada.objects.count() == 0
    invitacion.refresh_from_db()
    assert invitacion.utilizada is None


@pytest.mark.django_db
def test_metodos_no_admitidos(persona):
    invitacion = crear_invitacion(persona)
    client = Client()
    antes = _huella(persona)
    assert client.post(_rutas(invitacion)["datos"]).status_code == 405
    assert client.get(_rutas(invitacion)["envio"]).status_code == 405
    assert client.put(_rutas(invitacion)["envio"]).status_code == 405
    assert _huella(persona) == antes


def _usuario(nombre, **flags):
    usuario = get_user_model().objects.create_user(username=nombre, password="x")
    perfil = usuario.profile
    perfil.acceso_web = flags.get("acceso_web", True)
    perfil.must_change_password = flags.get("must_change_password", False)
    perfil.needs_profile_confirmation = flags.get("needs_confirmation", False)
    perfil.save()
    return usuario


def _encuesta_obligatoria():
    creador = _usuario("creador_encuesta")
    encuesta = crear_encuesta(
        usuario=creador,
        titulo="Obligatoria sintetica",
        es_obligatoria=True,
        intervalo_recordatorio_dias=None,
        duracion_ronda_dias=7,
    )
    Pregunta.objects.create(encuesta=encuesta, texto="¿Ok?", tipo=TipoPregunta.SI_NO)
    actualizar_segmentacion(encuesta, tipo=TipoSegmentacion.TODOS_LOS_USUARIOS)
    publicar_para_test(encuesta, usuario=creador)


@pytest.fixture
def build_ddjj(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    script = b"export const ddjj = true;"
    nombre = f"index-{hashlib.sha256(script).hexdigest()[:12]}.js"
    (assets / nombre).write_bytes(script)
    (assets / "secreto.env").write_text("no-es-un-asset")
    (tmp_path / "index.html").write_text(
        f'<html><script type="module" src="/v2/pas/assets/{nombre}"></script></html>'
    )
    return tmp_path, f"/pas/ddjj/react/assets/{nombre}", script


@contextmanager
def _urlconf_pas(build, activas):
    # Evaluar las rutas de producción con estos settings sin recargar el URLconf
    # compartido del resto de la suite.
    ruta = Path(__file__).resolve().parents[2] / "pas_runtime" / "urls.py"
    with override_settings(
        REACT_VERTICALES_ACTIVAS=activas,
        SISOC_REACT_BUILD_DIR="",
        SISOC_REACT_PAS_BUILD_DIR=str(build),
    ):
        modulo = ModuleType("pas_ddjj_runtime_test_urls")
        modulo.urlpatterns = run_path(str(ruta))["urlpatterns"]
        with override_settings(ROOT_URLCONF=modulo):
            yield


@pytest.fixture
def entrada_react(build_ddjj):
    build, asset, script = build_ddjj
    with _urlconf_pas(build, frozenset({"todas"})):
        yield asset, script


@pytest.mark.django_db
@pytest.mark.parametrize("build_disponible", [True, False])
def test_ddjj_fallback_nativo_sin_activacion_o_sin_build(
    persona, build_ddjj, build_disponible
):
    build, asset, _ = build_ddjj
    activas = frozenset() if build_disponible else frozenset({"todas"})
    build = build if build_disponible else build / "faltante"
    invitacion = crear_invitacion(persona)
    client = Client()

    with _urlconf_pas(build, activas):
        formulario = client.get(_rutas(invitacion)["canonica"])
        assert formulario.status_code == 200
        assert b"pas-ddjj-form" in formulario.content
        confirmacion = client.get(reverse("pas_ddjj_confirmacion"))
        assert confirmacion.status_code == 200
        assert asset.encode() not in confirmacion.content
        assert client.get(asset).status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("flags", "esperado"),
    [
        ({"acceso_web": False}, (403, None)),
        ({"must_change_password": True}, (302, "/password/first-change/")),
        ({"needs_confirmation": True}, (302, "/mi-cuenta/confirmar/")),
        ({"encuesta": True}, (302, "/inicio/")),
    ],
)
def test_politica_p1_es_igual_en_entrada_datos_municipios_y_envio(
    persona, entrada_react, flags, esperado
):
    del entrada_react
    invitacion = crear_invitacion(persona)
    if flags.pop("encuesta", False):
        _encuesta_obligatoria()
    client = Client()
    client.force_login(_usuario("restringido", **flags))
    antes = _huella(persona)
    rutas = _rutas(invitacion)

    respuestas = [
        client.get(rutas["canonica"]),
        client.get(rutas["datos"]),
        client.get(rutas["municipios"], {"provincia_id": persona.provincia_id}),
        client.post(rutas["envio"], _envio(persona.provincia, persona.municipio)),
        client.get(reverse("pas_ddjj_confirmacion")),
    ]

    for respuesta in respuestas:
        assert respuesta.status_code == esperado[0]
        if esperado[1]:
            assert respuesta["Location"] == esperado[1]
    assert _huella(persona) == antes


@pytest.mark.django_db
def test_sesion_sin_restricciones_continua_a_la_invitacion(persona):
    invitacion = crear_invitacion(persona)
    client = Client()
    client.force_login(_usuario("habilitado"))
    assert client.get(_rutas(invitacion)["datos"]).status_code == 200


@pytest.mark.django_db
def test_entrada_react_sirve_index_solo_con_invitacion_disponible(
    persona, entrada_react
):
    asset, script = entrada_react
    invitacion = crear_invitacion(persona)
    client = Client()
    antes = _huella(persona)

    respuesta = client.get(_rutas(invitacion)["canonica"], {"x": "no-se-reenvia"})

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "text/html; charset=utf-8"
    assert "no-store" in respuesta["Cache-Control"]
    assert asset.encode() in respuesta.content
    assert b"/v2/pas/assets/" not in respuesta.content
    assert b"no-se-reenvia" not in respuesta.content
    assert b"persona@example.test" not in respuesta.content
    assert "csrftoken" in respuesta.cookies
    head = client.head(_rutas(invitacion)["canonica"])
    assert head.status_code == 200
    assert head.content == b""
    assert client.get(reverse("pas_ddjj_confirmacion")).content == respuesta.content

    recurso = client.get(asset)
    assert recurso.status_code == 200
    assert recurso.content == script
    assert "immutable" in recurso["Cache-Control"]
    assert recurso["X-Content-Type-Options"] == "nosniff"
    assert client.get(asset + "?token=x").status_code == 404
    assert client.get("/pas/ddjj/react/assets/secreto.env").status_code == 404
    assert client.get("/pas/ddjj/react/index.html").status_code == 404
    assert client.post(asset).status_code == 405
    assert _huella(persona) == antes


@pytest.mark.django_db
def test_entrada_react_delega_404_410_y_post_en_la_vista_nativa(
    persona, entrada_react, tmp_path
):
    del entrada_react
    client = Client()
    desconocida = client.get(
        "/pas/ddjj/formulario/00000000-0000-4000-8000-000000000000"
    )
    assert desconocida.status_code == 404
    assert b"/pas/ddjj/react/assets/" not in desconocida.content

    usada = crear_invitacion(persona)
    PasInvitacionDDJJ.objects.filter(pk=usada.pk).update(utilizada=timezone.now())
    no_disponible = client.get(_rutas(usada)["canonica"])
    assert no_disponible.status_code == 410
    assert no_disponible.content.decode() == TEXTO_NO_DISPONIBLE

    invitacion = crear_invitacion(persona)
    invalido = client.post(_rutas(invitacion)["canonica"], {"calle": ""})
    assert invalido.status_code == 400
    assert b"pas-ddjj-form" in invalido.content
    with override_settings(MEDIA_ROOT=tmp_path):
        valido = client.post(
            _rutas(invitacion)["canonica"],
            _envio(persona.provincia, persona.municipio),
        )
    assert valido.status_code == 302
    assert valido["Location"] == reverse("pas_ddjj_confirmacion")
    assert PasDeclaracionJurada.objects.count() == 1


def test_entrada_react_rechaza_builds_sin_index_regular(tmp_path):
    from pas.ddjj_preview import ddjj_preview_patterns

    with pytest.raises(ValueError):
        ddjj_preview_patterns(tmp_path)
