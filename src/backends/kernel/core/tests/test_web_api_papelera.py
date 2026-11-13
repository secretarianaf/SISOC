"""Papelera en JSON (T06): consulta, vista previa y restauración en cascada, solo superusuario."""

from urllib.parse import urlencode

import pytest
from django.contrib.auth.models import User
from django.test import Client

from ciudadanos.models import Ciudadano, GrupoFamiliar

pytestmark = pytest.mark.django_db

FORM = "application/x-www-form-urlencoded"
LISTA = "/api/web/core/papelera/"


def _cliente(username="papelera_admin", superuser=True, csrf=False):
    user = User.objects.create_user(username=username, password="x")
    if superuser:
        user.is_superuser = True
        user.save()
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user)
    client.user = user
    return client


def _post(client, url, datos=None):
    return client.post(url, urlencode(datos or {}), content_type=FORM)


@pytest.fixture(name="eliminado")
def eliminado_fixture():
    admin = User.objects.create_user(
        username="quien_borra", password="x", first_name="Quien", last_name="Borra"
    )
    ana = Ciudadano.objects.create(
        nombre="Ana", apellido="Papelera", documento=30111222
    )
    zoe = Ciudadano.objects.create(nombre="Zoe", apellido="Zeta", documento=2)
    GrupoFamiliar.objects.create(ciudadano_1=ana, ciudadano_2=zoe, vinculo="HIJO/A")
    ana.delete(user=admin, cascade=True)
    return Ciudadano.all_objects.get(pk=ana.pk)


def _vivos():
    return {
        "ciudadanos": list(
            Ciudadano.objects.order_by("pk").values_list("pk", flat=True)
        ),
        "borrados": list(
            Ciudadano.all_objects.filter(deleted_at__isnull=False).values_list(
                "pk", flat=True
            )
        ),
        "familia": list(
            GrupoFamiliar.all_objects.order_by("pk").values_list("pk", "deleted_at")
        ),
    }


def _restaurar(eliminado):
    return f"/api/web/core/papelera/restaurar/ciudadanos/ciudadano/{eliminado.pk}/"


def test_anonimo_401_y_no_superusuario_403_en_todas_las_rutas(eliminado):
    rutas = (LISTA, _restaurar(eliminado))
    for url in rutas:
        assert Client().get(url).status_code == 401
    normal = _cliente("normal", superuser=False)
    for url in rutas:
        assert normal.get(url).status_code == 403
    antes = _vivos()
    assert _post(normal, _restaurar(eliminado), {"confirmed": "1"}).status_code == 403
    assert _vivos() == antes


def test_listado_proyecta_filas_y_filtros_nativos(eliminado):
    datos = _cliente().get(LISTA, {"model": "ciudadanos.Ciudadano"}).json()
    assert datos["selected_model_label"] == "Ciudadanos"
    assert datos["show_all_models"] is False
    assert datos["deleted_count"] >= 1
    fila = next(f for f in datos["rows"] if f["id"] == eliminado.pk)
    assert fila["label"] == str(eliminado)
    assert fila["deleted_by"] == "Quien Borra"
    assert fila["restore_url"].startswith(
        f"/papelera/preview-restore/ciudadanos/ciudadano/{eliminado.pk}/?next="
    )
    assert datos["filters"]["model"]["choices"][0] == {
        "value": "",
        "label": "Todos los modelos",
    }
    assert {"label": "Modelo", "value": "Ciudadanos"} in datos["active_filters"]
    assert datos["filter_errors"] == []
    assert datos["urls"]["list"] == "/papelera/"


def test_listado_sin_filtros_es_combinado():
    datos = _cliente().get(LISTA).json()
    assert datos["show_all_models"] is True
    assert datos["selected_model_label"] == "Todos los modelos"
    assert datos["active_filters"] == []
    assert datos["pagination"]["num_pages"] >= 1


def test_busqueda_y_filtro_por_quien_elimino(eliminado):
    cliente = _cliente()
    por_texto = cliente.get(
        LISTA, {"model": "ciudadanos.Ciudadano", "q": "Papelera"}
    ).json()
    assert [f["id"] for f in por_texto["rows"]] == [eliminado.pk]
    sin_resultados = cliente.get(
        LISTA, {"model": "ciudadanos.Ciudadano", "q": "Inexistente"}
    ).json()
    assert sin_resultados["rows"] == []
    por_usuario = cliente.get(
        LISTA, {"model": "ciudadanos.Ciudadano", "deleted_by": "quien_borra"}
    ).json()
    assert [f["id"] for f in por_usuario["rows"]] == [eliminado.pk]
    otro = cliente.get(
        LISTA, {"model": "ciudadanos.Ciudadano", "deleted_by": "nadie"}
    ).json()
    assert otro["rows"] == []


def test_rango_de_fechas_invertido_informa_el_error_y_no_filtra(eliminado):
    datos = (
        _cliente()
        .get(
            LISTA,
            {
                "model": "ciudadanos.Ciudadano",
                "deleted_from": "2030-01-02",
                "deleted_to": "2030-01-01",
            },
        )
        .json()
    )
    assert datos["filter_errors"] == [
        "La fecha 'Desde' no puede ser posterior a la fecha 'Hasta'."
    ]
    assert datos["rows"]


def test_vista_previa_de_restauracion_no_escribe(eliminado):
    antes = _vivos()
    cliente = _cliente()
    datos = cliente.get(
        _restaurar(eliminado), {"next": "/papelera/?model=ciudadanos.Ciudadano"}
    ).json()
    assert datos["id"] == eliminado.pk
    assert datos["model_identifier"] == "ciudadanos.ciudadano"
    assert datos["total_afectados"] == sum(
        item["cantidad"] for item in datos["breakdown"]
    )
    assert datos["total_afectados"] >= 2
    assert (
        datos["restore_url"]
        == f"/papelera/restore/ciudadanos/ciudadano/{eliminado.pk}/"
    )
    assert datos["back_url"] == "/papelera/?model=ciudadanos.Ciudadano"
    assert datos["next_url"] == "/papelera/?model=ciudadanos.Ciudadano"
    assert any(
        item["label"] == "Id" and item["value"] == str(eliminado.pk)
        for item in datos["details"]
    )
    assert _vivos() == antes
    ajena = cliente.get(_restaurar(eliminado), {"next": "https://example.org/"}).json()
    assert ajena["next_url"] is None
    assert ajena["back_url"] == "/papelera/?model=ciudadanos.Ciudadano"


def test_vista_previa_404_si_no_esta_en_papelera_o_el_modelo_no_existe(eliminado):
    cliente = _cliente()
    viva = Ciudadano.objects.get(documento=2)
    assert (
        cliente.get(
            f"/api/web/core/papelera/restaurar/ciudadanos/ciudadano/{viva.pk}/"
        ).status_code
        == 404
    )
    assert (
        cliente.get(
            "/api/web/core/papelera/restaurar/ciudadanos/noexiste/1/"
        ).status_code
        == 404
    )


def test_restaurar_sin_confirmar_no_escribe_y_vuelve_a_la_vista_previa(eliminado):
    antes = _vivos()
    respuesta = _post(_cliente(), _restaurar(eliminado), {})
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/papelera/preview-restore/ciudadanos/ciudadano/{eliminado.pk}/",
    }
    assert _vivos() == antes


def test_restaurar_confirmado_restaura_en_cascada_y_deja_el_mensaje(eliminado):
    cliente = _cliente()
    respuesta = _post(
        cliente, _restaurar(eliminado), {"confirmed": "1", "next": "/papelera/?page=2"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "redirect": "/papelera/?page=2"}
    assert Ciudadano.objects.filter(pk=eliminado.pk).exists()
    assert all(deleted is None for _, deleted in _vivos()["familia"])
    mensajes = cliente.get(LISTA).json()["messages"]
    assert len(mensajes) == 1
    assert mensajes[0]["level"] == "success"
    assert mensajes[0]["message"].startswith(
        "Restauración completada. Registros restaurados: "
    )
    assert cliente.get(LISTA).json()["messages"] == []
    assert cliente.get(_restaurar(eliminado)).status_code == 404
    assert _post(cliente, _restaurar(eliminado), {"confirmed": "1"}).status_code == 404


def test_restaurar_ignora_un_next_externo(eliminado):
    respuesta = _post(
        _cliente(),
        _restaurar(eliminado),
        {"confirmed": "1", "next": "https://example.org/x"},
    )
    assert respuesta.json()["redirect"] == "/papelera/?model=ciudadanos.Ciudadano"


def test_restaurar_sin_csrf_es_403_y_no_escribe(eliminado):
    cliente = _cliente("csrf_admin", csrf=True)
    antes = _vivos()
    assert _post(cliente, _restaurar(eliminado), {"confirmed": "1"}).status_code == 403
    assert _vivos() == antes
