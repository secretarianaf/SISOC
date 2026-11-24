"""Aportes de Ciudadano 360 en JSON (C04.01): vista generica, lista de la ficha y G1."""

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client, override_settings

from ciudadanos import detail_contributions as dc
from ciudadanos.models import Ciudadano
from ciudadanos.views import CiudadanosDetailView
from core.web_gate import META_KEY

pytestmark = pytest.mark.django_db

PERM = "ciudadanos.view_ciudadano"


def _usuario(username, permisos=(PERM,)):
    user = User.objects.create_user(username=username, password="x")
    for codigo in permisos:
        app, codename = codigo.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return user


def _cliente(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="ciudadano")
def ciudadano_fixture():
    return Ciudadano.objects.create(nombre="Ana", apellido="Aporte", documento=30111222)


def _url(ciudadano, aporte="cdf", backend="cdf"):
    return f"/api/web/{backend}/ciudadanos/{ciudadano.pk}/aportes/{aporte}/"


def test_aportes_web_cubre_exactamente_las_contribuciones_renderizadas():
    secciones = {s for valores in dc.APORTES_WEB.values() for s in valores}
    assert secciones == set(CiudadanosDetailView.CONTRIBUCIONES_RENDERIZADAS)
    assert set(dc.APORTES_WEB) == {
        "comedores",
        "pwa",
        "celiaquia",
        "vat",
        "centrodefamilia",
    }


def test_lista_de_aportes_arma_las_rutas_desde_el_registro(ciudadano):
    aportes = dc.aportes_web_de_ciudadano(ciudadano.pk)
    assert {a["aporte"]: a["url"] for a in aportes} == {
        "comedores": f"/api/web/comedores/ciudadanos/{ciudadano.pk}/aportes/comedores/",
        "pwa": f"/api/web/comedores/ciudadanos/{ciudadano.pk}/aportes/pwa/",
        "celiaquia": f"/api/web/celiaquia/ciudadanos/{ciudadano.pk}/aportes/celiaquia/",
        "vat": f"/api/web/vat/ciudadanos/{ciudadano.pk}/aportes/vat/",
        "centrodefamilia": f"/api/web/cdf/ciudadanos/{ciudadano.pk}/aportes/centrodefamilia/",
    }
    por_aporte = {a["aporte"]: a["secciones"] for a in aportes}
    assert por_aporte["pwa"] == ["pwa", "pwa_badges"]
    assert por_aporte["centrodefamilia"] == ["centrodefamilia", "centrodefamilia_monto"]


def test_backend_no_resuelto_no_se_lista(ciudadano):
    # Con backends separados, un backend que el core no tiene configurado no aparece.
    with override_settings(SISOC_BACKENDS={"cdf": {"origin": "http://cdf"}}):
        aportes = dc.aportes_web_de_ciudadano(ciudadano.pk)
    assert [a["aporte"] for a in aportes] == ["centrodefamilia"]


def test_registro_rechaza_aportes_desconocidos_y_duplicados(monkeypatch):
    monkeypatch.setattr(dc, "_PROYECTORES", {})
    with pytest.raises(ValueError):
        dc.registrar_proyector_aporte("otro", lambda ciudadano: {})

    def uno(ciudadano):
        return {}

    dc.registrar_proyector_aporte("vat", uno)
    dc.registrar_proyector_aporte("vat", uno)
    with pytest.raises(ValueError):
        dc.registrar_proyector_aporte("vat", lambda ciudadano: {})


def test_fecha_texto_aplica_hora_local_y_valor_por_defecto():
    from datetime import datetime, timezone as tz

    assert dc.fecha_texto(None) == ""
    assert dc.fecha_texto(None, por_defecto="-") == "-"
    # 01:30 UTC del 2 de enero es 22:30 del 1 de enero en Buenos Aires.
    valor = datetime(2026, 1, 2, 1, 30, tzinfo=tz.utc)
    assert dc.fecha_texto(valor) == "01/01/2026"
    assert dc.fecha_texto(valor, "d/m/Y H:i") == "01/01/2026 22:30"


def test_anonimo_recibe_401(ciudadano):
    respuesta = Client().get(_url(ciudadano))
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "Inicie sesión para continuar."}


def test_sin_permiso_recibe_403_sin_datos(ciudadano):
    respuesta = _cliente(_usuario("sin_permiso_c04", permisos=())).get(_url(ciudadano))
    assert respuesta.status_code == 403
    assert "secciones" not in respuesta.json()


def test_aporte_inexistente_o_de_otro_backend_es_404(ciudadano):
    cliente = _cliente(_usuario("lector_c04"))
    inexistente = cliente.get(_url(ciudadano, "no_existe", "cdf"))
    otro_backend = cliente.get(_url(ciudadano, "vat", "cdf"))
    for respuesta in (inexistente, otro_backend):
        assert respuesta.status_code == 404
        assert respuesta.json() == {"detail": "Aporte no disponible en este servicio."}


def test_ciudadano_inexistente_es_404():
    cliente = _cliente(_usuario("lector2_c04"))
    respuesta = cliente.get("/api/web/cdf/ciudadanos/999999/aportes/centrodefamilia/")
    assert respuesta.status_code == 404


def test_exito_responde_200_con_cache_privado(ciudadano):
    cliente = _cliente(_usuario("lector3_c04"))
    respuesta = cliente.get(_url(ciudadano, "centrodefamilia"))
    assert respuesta.status_code == 200
    assert respuesta.json()["aporte"] == "centrodefamilia"
    assert set(respuesta.json()["secciones"]) == {
        "centrodefamilia",
        "centrodefamilia_monto",
    }
    assert "no-store" in respuesta["Cache-Control"]
    assert "private" in respuesta["Cache-Control"]
    assert "Cookie" in respuesta["Vary"]


def test_proveedor_que_falla_responde_503_y_se_registra(ciudadano, monkeypatch, caplog):
    def roto(_ciudadano):
        raise RuntimeError("proveedor caido")

    monkeypatch.setitem(dc._PROYECTORES, "centrodefamilia", roto)
    cliente = _cliente(_usuario("lector4_c04"))
    with caplog.at_level("ERROR", logger="django"):
        respuesta = cliente.get(_url(ciudadano, "centrodefamilia"))
    assert respuesta.status_code == 503
    assert respuesta.json() == {
        "detail": "Servicio no disponible.",
        "codigo": "aporte_no_disponible",
    }
    assert "aporte centrodefamilia" in caplog.text
    assert "no-store" in respuesta["Cache-Control"]


def test_solo_lectura(ciudadano):
    cliente = _cliente(_usuario("lector5_c04"))
    assert cliente.post(_url(ciudadano, "centrodefamilia")).status_code in (403, 405)
    assert cliente.head(_url(ciudadano, "centrodefamilia")).status_code == 200


def test_constancia_g1_alterada_no_ejecuta_la_consulta(ciudadano, monkeypatch):
    llamadas = []
    monkeypatch.setitem(
        dc._PROYECTORES, "centrodefamilia", lambda c: llamadas.append(c) or {}
    )
    cliente = _cliente(_usuario("lector6_c04"))
    # En el monolito el header G1 no se confia: la politica se evalua localmente.
    respuesta = cliente.get(_url(ciudadano, "centrodefamilia"), **{META_KEY: "falsa"})
    assert respuesta.status_code == 200
    assert len(llamadas) == 1


def test_ficha_json_lista_los_aportes_y_exige_permiso(ciudadano):
    url = f"/api/web/ciudadanos/{ciudadano.pk}/"
    assert Client().get(url).status_code == 401
    sin_permiso = _cliente(_usuario("sin_permiso2_c04", permisos=()))
    assert sin_permiso.get(url).status_code == 403
    cliente = _cliente(_usuario("lector7_c04"))
    respuesta = cliente.get(url)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert (datos["id"], datos["nombre"], datos["apellido"]) == (
        ciudadano.pk,
        "Ana",
        "Aporte",
    )
    assert datos["numero_documento"] == "30111222"
    assert [a["aporte"] for a in datos["aportes"]] == list(dc.APORTES_WEB)
    assert cliente.get("/api/web/ciudadanos/999999/").status_code == 404
    assert "no-store" in respuesta["Cache-Control"]
