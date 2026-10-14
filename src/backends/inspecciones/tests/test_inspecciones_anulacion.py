"""Anulación de actas y marca de acta de prueba (servicio, backoffice y API)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.urls import NoReverseMatch, reverse

from inspecciones.models import Acta, EventoInspeccion
from inspecciones.services.anulacion import anular_acta, marcar_prueba

pytestmark = pytest.mark.django_db

BASE = "/api/inspecciones"
MOTIVO = "Acta cargada sobre la escuela equivocada"


def _acta(client, cerrar, escuela_obj=None):
    _, response = cerrar(client, escuela_obj)
    assert response.status_code == 200, response.json()
    return Acta.objects.get(numero=response.json()["numero"])


def _destino_por_defecto(numero):
    try:
        return reverse("inspecciones_acta_detalle", args=[numero])
    except NoReverseMatch:
        return reverse("inspecciones_panel")


def _mensajes(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


# ------------------------------------------------------------- servicio


def test_anular_conserva_numero_instantanea_y_pdf(api_a, coordinacion, cerrar, pdf):
    acta = _acta(api_a, cerrar)
    api_a.put(
        f"{BASE}/actas/{acta.numero}/pdf/", {"archivo": pdf()}, format="multipart"
    )
    acta.refresh_from_db()
    antes = {
        "numero": acta.numero,
        "instantanea": acta.instantanea,
        "instantanea_sha256": acta.instantanea_sha256,
        "pdf": acta.pdf.name,
        "pdf_sha256": acta.pdf_sha256,
        "cerrada_at": acta.cerrada_at,
    }

    resultado = anular_acta(acta, f"  {MOTIVO}  ", coordinacion)

    acta.refresh_from_db()
    assert resultado.pk == acta.pk
    assert acta.estado == Acta.Estado.ANULADA
    assert acta.anulada_por == coordinacion
    assert acta.anulada_at is not None
    assert acta.motivo_anulacion == MOTIVO
    assert {
        "numero": acta.numero,
        "instantanea": acta.instantanea,
        "instantanea_sha256": acta.instantanea_sha256,
        "pdf": acta.pdf.name,
        "pdf_sha256": acta.pdf_sha256,
        "cerrada_at": acta.cerrada_at,
    } == antes
    evento = acta.eventos.get(accion=EventoInspeccion.Accion.ANULADA)
    assert evento.actor == coordinacion
    assert evento.actor_nombre == "Coordinacion"
    assert evento.at == acta.anulada_at
    assert evento.detalle["motivo"] == MOTIVO


@pytest.mark.parametrize("motivo", ["", "corto", "   a  b   c    ", None])
def test_anular_rechaza_motivo_corto(api_a, coordinacion, cerrar, motivo):
    acta = _acta(api_a, cerrar)

    with pytest.raises(ValidationError, match="motivo"):
        anular_acta(acta, motivo, coordinacion)

    acta.refresh_from_db()
    assert acta.estado == Acta.Estado.FINALIZADA
    assert not acta.eventos.filter(accion=EventoInspeccion.Accion.ANULADA).exists()


def test_anular_dos_veces_se_rechaza(api_a, coordinacion, cerrar):
    acta = _acta(api_a, cerrar)
    anular_acta(acta, MOTIVO, coordinacion)

    with pytest.raises(ValidationError, match="ya está anulada"):
        anular_acta(acta, "Otro motivo cualquiera", coordinacion)

    acta.refresh_from_db()
    assert acta.motivo_anulacion == MOTIVO
    assert acta.eventos.filter(accion=EventoInspeccion.Accion.ANULADA).count() == 1


def test_marcar_y_desmarcar_prueba(api_a, coordinacion, cerrar):
    acta = _acta(api_a, cerrar)

    marcar_prueba(acta, True, coordinacion)
    acta.refresh_from_db()
    assert acta.es_prueba is True
    marcar_prueba(acta, True, coordinacion)  # sin cambio: no registra otro evento
    marcar_prueba(acta, False, coordinacion)
    acta.refresh_from_db()
    assert acta.es_prueba is False

    eventos = acta.eventos.filter(detalle__campo="es_prueba").order_by("id")
    assert [e.detalle["es_prueba"] for e in eventos] == [True, False]
    assert {e.accion for e in eventos} == {EventoInspeccion.Accion.EDITADA}
    assert {e.actor for e in eventos} == {coordinacion}


def test_marca_de_prueba_bloqueada_en_anulada(api_a, coordinacion, cerrar):
    acta = _acta(api_a, cerrar)
    anular_acta(acta, MOTIVO, coordinacion)

    for valor in (True, False):
        with pytest.raises(ValidationError, match="anulada"):
            marcar_prueba(acta, valor, coordinacion)
    acta.refresh_from_db()
    assert acta.es_prueba is False


# ------------------------------------------------------------- backoffice


def test_vista_anular_con_coordinacion(client, api_a, coordinacion, cerrar):
    acta = _acta(api_a, cerrar)
    client.force_login(coordinacion)

    response = client.post(
        reverse("inspecciones_anular_acta", args=[acta.numero]), {"motivo": MOTIVO}
    )

    assert response.status_code == 302
    assert response["Location"] == _destino_por_defecto(acta.numero)
    assert _mensajes(response) == [f"Acta {acta.numero} anulada."]
    acta.refresh_from_db()
    assert acta.estado == Acta.Estado.ANULADA
    assert acta.anulada_por == coordinacion


def test_vista_anular_motivo_corto_muestra_error(client, api_a, coordinacion, cerrar):
    acta = _acta(api_a, cerrar)
    client.force_login(coordinacion)

    response = client.post(
        reverse("inspecciones_anular_acta", args=[acta.numero]), {"motivo": "corto"}
    )

    assert response.status_code == 302
    assert "motivo" in _mensajes(response)[0]
    acta.refresh_from_db()
    assert acta.estado == Acta.Estado.FINALIZADA


def test_vistas_sin_permiso_responden_403(client, api_a, inspector_a, cerrar):
    acta = _acta(api_a, cerrar)
    sin_programa = get_user_model().objects.create_user(username="otro", password="x")
    anular = reverse("inspecciones_anular_acta", args=[acta.numero])
    prueba = reverse("inspecciones_marcar_prueba_acta", args=[acta.numero])

    for usuario in (inspector_a, sin_programa):
        client.force_login(usuario)
        assert client.post(anular, {"motivo": MOTIVO}).status_code == 403
        assert client.post(prueba, {"es_prueba": "1"}).status_code == 403

    acta.refresh_from_db()
    assert acta.estado == Acta.Estado.FINALIZADA
    assert acta.es_prueba is False


def test_vistas_exigen_sesion_post_y_acta_existente(
    client, api_a, coordinacion, cerrar
):
    acta = _acta(api_a, cerrar)
    anular = reverse("inspecciones_anular_acta", args=[acta.numero])

    sin_sesion = client.post(anular, {"motivo": MOTIVO})
    assert sin_sesion.status_code == 302
    assert "login" in sin_sesion["Location"]

    client.force_login(coordinacion)
    assert client.get(anular).status_code == 405
    inexistente = reverse("inspecciones_anular_acta", args=["ACTA-1999-000001"])
    assert client.post(inexistente, {"motivo": MOTIVO}).status_code == 404
    inexistente = reverse("inspecciones_marcar_prueba_acta", args=["ACTA-1999-0001"])
    assert client.post(inexistente, {"es_prueba": "1"}).status_code == 404
    acta.refresh_from_db()
    assert acta.estado == Acta.Estado.FINALIZADA


@pytest.mark.parametrize(
    "siguiente",
    ["https://ejemplo.com/robo/", "//ejemplo.com/robo/", "javascript:alert(1)"],
)
def test_next_externo_redirige_a_la_ruta_por_defecto(
    client, api_a, coordinacion, cerrar, siguiente
):
    acta = _acta(api_a, cerrar)
    client.force_login(coordinacion)

    response = client.post(
        reverse("inspecciones_marcar_prueba_acta", args=[acta.numero]),
        {"es_prueba": "1", "next": siguiente},
    )

    assert response.status_code == 302
    assert response["Location"] == _destino_por_defecto(acta.numero)


def test_next_interno_se_respeta(client, api_a, coordinacion, cerrar):
    acta = _acta(api_a, cerrar)
    client.force_login(coordinacion)
    siguiente = reverse("inspecciones_panel") + "?pagina=2"

    response = client.post(
        reverse("inspecciones_anular_acta", args=[acta.numero]),
        {"motivo": MOTIVO, "next": siguiente},
    )

    assert response["Location"] == siguiente


def test_vista_marcar_prueba(client, api_a, coordinacion, cerrar):
    acta = _acta(api_a, cerrar)
    client.force_login(coordinacion)
    url = reverse("inspecciones_marcar_prueba_acta", args=[acta.numero])

    marcar = client.post(url, {"es_prueba": "1"})
    acta.refresh_from_db()
    assert acta.es_prueba is True
    assert _mensajes(marcar)[-1] == f"Acta {acta.numero} marcada como de prueba."

    invalido = client.post(url, {"es_prueba": "si"})
    assert _mensajes(invalido)[-1] == "Valor de prueba inválido."
    acta.refresh_from_db()
    assert acta.es_prueba is True

    client.post(url, {"es_prueba": "0"})
    acta.refresh_from_db()
    assert acta.es_prueba is False

    anular_acta(acta, MOTIVO, coordinacion)
    bloqueada = client.post(url, {"es_prueba": "1"})
    assert "anulada" in _mensajes(bloqueada)[-1]
    acta.refresh_from_db()
    assert acta.es_prueba is False


def test_permiso_de_gestion_alcanza_para_anular(client, api_a, cerrar):
    acta = _acta(api_a, cerrar)
    admin = get_user_model().objects.create_superuser(
        username="admin", password="x", email="admin@example.com"
    )
    client.force_login(admin)

    client.post(
        reverse("inspecciones_anular_acta", args=[acta.numero]), {"motivo": MOTIVO}
    )

    acta.refresh_from_db()
    assert acta.estado == Acta.Estado.ANULADA


# ------------------------------------------------------------- efecto en la PWA


def test_anular_el_acta_del_dia_libera_la_escuela(
    api_a, coordinacion, asignada_a, escuela, cerrar
):
    acta = _acta(api_a, cerrar, escuela)
    asignadas = f"{BASE}/escuelas/asignadas/"
    ficha = f"{BASE}/escuelas/{escuela.codigo}/"
    assert api_a.get(asignadas).json()[0]["estado"] == "finalizada"
    assert len(api_a.get(ficha).json()["visitas_hoy"]) == 1

    anular_acta(acta, MOTIVO, coordinacion)

    assert api_a.get(asignadas).json()[0]["estado"] == "pendiente"
    assert api_a.get(ficha).json()["visitas_hoy"] == []

    # Nueva visita al mismo turno, sin motivo de nueva visita y sin pisar la anterior.
    nueva = _acta(api_a, cerrar, escuela)
    assert nueva.numero != acta.numero
    assert api_a.get(asignadas).json()[0]["estado"] == "finalizada"
    assert [v["numero"] for v in api_a.get(ficha).json()["visitas_hoy"]] == [
        nueva.numero
    ]
    acta.refresh_from_db()
    assert acta.estado == Acta.Estado.ANULADA


def test_notificacion_sobre_acta_anulada_sigue_dando_409(
    api_a, coordinacion, cerrar, imagen, nuevo_uuid
):
    acta = _acta(api_a, cerrar)
    anular_acta(acta, MOTIVO, coordinacion)

    response = api_a.post(
        f"{BASE}/actas/{acta.numero}/notificaciones/",
        {
            "uuid": nuevo_uuid(),
            "archivos": [imagen()],
            "notificada_at": "2026-10-14T16:00:00-03:00",
            "receptor_nombre": "María Fernández",
            "receptor_cargo": "Vicedirectora",
            "condicion_firma": "firmada",
            "numero_confirmado": acta.numero,
        },
        format="multipart",
    )

    assert response.status_code == 409


def test_api_de_actas_expone_la_anulacion(
    api_a, api_b, api_coord, coordinacion, cerrar
):
    acta = _acta(api_a, cerrar)
    vigente = api_a.get(f"{BASE}/actas/").json()[0]
    assert vigente["estado"] == "finalizada"
    assert vigente["anulada_at"] is None
    assert vigente["motivo_anulacion"] is None

    anular_acta(acta, MOTIVO, coordinacion)
    acta.refresh_from_db()

    listado = api_a.get(f"{BASE}/actas/").json()
    assert [a["numero"] for a in listado] == [acta.numero]
    assert listado[0]["estado"] == "anulada"
    assert listado[0]["anulada_at"].endswith("-03:00")
    assert listado[0]["motivo_anulacion"] == MOTIVO

    for cliente in (api_a, api_coord):
        detalle = cliente.get(f"{BASE}/actas/{acta.numero}/").json()
        assert detalle["estado"] == "anulada"
        assert detalle["motivo_anulacion"] == MOTIVO
        assert detalle["anulada_at"] == listado[0]["anulada_at"]
        assert detalle["respuestas"]["f09"]["valor"] == 24
        assert "anulada" in [e["codigo"] for e in detalle["eventos"]]
    todas = api_coord.get(f"{BASE}/actas/", {"alcance": "todas"}).json()
    assert todas[0]["estado"] == "anulada"
    assert api_b.get(f"{BASE}/actas/{acta.numero}/").status_code == 404
