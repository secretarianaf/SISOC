"""Seguimientos PNUD (N22): alta desde la app, corrección, listado y revisión."""

import io

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.models import Comedor, ComedorDatosConvenioPnud, Programas
from core.models import Provincia
from relevamientos.models import Relevamiento, SeguimientoPnud
from users.models import TerritorialComedorProvincia

pytestmark = pytest.mark.django_db

PENDIENTE = SeguimientoPnud.ESTADO_VALIDACION_PENDIENTE
A_SUBSANAR = SeguimientoPnud.ESTADO_VALIDACION_A_SUBSANAR
VALIDADO = SeguimientoPnud.ESTADO_VALIDACION_VALIDADO


def _make_territorial(username, provincias):
    user = get_user_model().objects.create_user(
        username=username, email=f"{username}@example.com", password="testpass123"
    )
    user.profile.es_territorial_comedor = True
    user.profile.save(update_fields=["es_territorial_comedor"])
    for provincia in provincias:
        TerritorialComedorProvincia.objects.create(
            profile=user.profile, provincia=provincia
        )
    return user


def _client(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


def _url(comedor, pnud_id=None):
    base = f"/api/territorial/comedores/{comedor.id}/seguimientos-pnud/"
    return f"{base}{pnud_id}/" if pnud_id else base


def _payload(**overrides):
    payload = {
        "client_uuid": "pnud-uuid-1",
        "formulario": "iia",
        "fecha_hora": "27/09/2026 10:30",
        "datos": {
            "funcionamiento": "Abierto, en funcionamiento alimentario",
            "ent_nombre_apellido": "Rosa Díaz",
            "recibe_donaciones": True,
            "prestaciones": [
                {
                    "dia": "Lunes",
                    "comida": "Almuerzo",
                    "ap_total": 40,
                    "de_presencial": 35,
                }
            ],
        },
    }
    payload.update(overrides)
    return payload


def _programa(nombre):
    return Programas.objects.create(nombre=nombre)


@pytest.fixture
def zona():
    provincia = Provincia.objects.create(nombre="Prov PNUD")
    comedor = Comedor.objects.create(
        nombre="Espacio PNUD",
        provincia=provincia,
        calle="Original",
        numero=10,
        programa=_programa("Abordaje comunitario - Línea Tradicional"),
        codigo_de_proyecto="PNUD-77",
        id_externo=4321,
    )
    tecnico = _make_territorial("terr_pnud", [provincia])
    return provincia, comedor, tecnico


# ------------------------------------------------------------------- alta


def test_alta_sin_asignacion_previa_queda_pendiente_de_validacion(zona):
    _, comedor, tecnico = zona

    response = _client(tecnico).post(_url(comedor), _payload(), format="json")

    assert response.status_code == 201, response.content
    data = response.json()
    assert data["formulario"] == "iia"
    assert data["estado_validacion"] == PENDIENTE
    assert data["origen"] == "app"
    assert data["tecnico"] == tecnico.id
    assert data["datos"]["prestaciones"][0]["ap_total"] == 40
    seguimiento = SeguimientoPnud.objects.get(pk=data["id"])
    assert seguimiento.comedor_id == comedor.id
    assert seguimiento.asignado_desde_sisoc is False
    assert seguimiento.fecha_hora is not None


def test_alta_es_idempotente_por_client_uuid(zona):
    _, comedor, tecnico = zona
    client = _client(tecnico)

    primero = client.post(_url(comedor), _payload(), format="json")
    reintento = client.post(_url(comedor), _payload(), format="json")

    assert primero.status_code == 201
    assert reintento.status_code == 200
    assert reintento.json()["id"] == primero.json()["id"]
    assert SeguimientoPnud.objects.count() == 1


def test_client_uuid_de_otro_comedor_da_409(zona):
    provincia, comedor, tecnico = zona
    otro = Comedor.objects.create(nombre="Otro espacio", provincia=provincia)
    client = _client(tecnico)
    client.post(_url(comedor), _payload(), format="json")

    response = client.post(_url(otro), _payload(), format="json")

    assert response.status_code == 409
    assert SeguimientoPnud.objects.count() == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"client_uuid": ""},
        {"formulario": "pac"},
        {"datos": "no-es-objeto"},
        {"fecha_hora": "2026-09-27T10:30"},
    ],
)
def test_alta_valida_el_payload(zona, overrides):
    _, comedor, tecnico = zona

    response = _client(tecnico).post(
        _url(comedor), _payload(**overrides), format="json"
    )

    assert response.status_code == 400
    assert "detail" in response.json()
    assert SeguimientoPnud.objects.count() == 0


def test_alta_rechaza_datos_demasiado_grandes(zona):
    _, comedor, tecnico = zona
    datos = {"comentarios_finales": "x" * (513 * 1024)}

    response = _client(tecnico).post(
        _url(comedor), _payload(datos=datos), format="json"
    )

    assert response.status_code == 400


def test_alta_fuera_de_zona_da_404(zona):
    _, comedor, _ = zona
    ajeno = _make_territorial("terr_otra_zona", [Provincia.objects.create(nombre="X")])

    response = _client(ajeno).post(_url(comedor), _payload(), format="json")

    assert response.status_code == 404
    assert SeguimientoPnud.objects.count() == 0


def test_alta_no_actualiza_el_legajo_del_comedor(zona):
    _, comedor, tecnico = zona
    datos = {"calle": "Nueva", "comedor": {"calle": "Pisada", "numero": 99}}

    response = _client(tecnico).post(
        _url(comedor), _payload(datos=datos), format="json"
    )

    assert response.status_code == 201
    comedor.refresh_from_db()
    assert comedor.calle == "Original"
    assert comedor.numero == 10
    assert "comedor" not in response.json()["datos"]


# ------------------------------------------------------------ corrección


def _crear(comedor, tecnico, **kwargs):
    return SeguimientoPnud.objects.create(
        comedor=comedor,
        tecnico=tecnico,
        formulario="iia",
        datos={"funcionamiento": "Cerrado"},
        origen=SeguimientoPnud.ORIGEN_APP,
        asignado_desde_sisoc=False,
        client_uuid=kwargs.pop("client_uuid", "pnud-existente"),
        **kwargs,
    )


def test_correccion_a_subsanar_vuelve_a_pendiente(zona):
    _, comedor, tecnico = zona
    seguimiento = _crear(comedor, tecnico, estado_validacion=A_SUBSANAR)

    response = _client(tecnico).patch(
        _url(comedor, seguimiento.id),
        {"datos": {"funcionamiento": "En funcionamiento con entrega"}},
        format="json",
    )

    assert response.status_code == 200, response.content
    seguimiento.refresh_from_db()
    assert seguimiento.estado_validacion == PENDIENTE
    assert seguimiento.datos == {"funcionamiento": "En funcionamiento con entrega"}


def test_correccion_de_validado_da_409(zona):
    _, comedor, tecnico = zona
    seguimiento = _crear(comedor, tecnico, estado_validacion=VALIDADO)

    response = _client(tecnico).patch(
        _url(comedor, seguimiento.id), {"datos": {"x": 1}}, format="json"
    )

    assert response.status_code == 409
    assert response.json()["estado_validacion"] == VALIDADO
    seguimiento.refresh_from_db()
    assert seguimiento.datos == {"funcionamiento": "Cerrado"}


def test_correccion_solo_del_tecnico_que_lo_cargo(zona):
    provincia, comedor, tecnico = zona
    seguimiento = _crear(comedor, tecnico, estado_validacion=A_SUBSANAR)
    otro = _make_territorial("terr_pnud_otro", [provincia])

    response = _client(otro).patch(
        _url(comedor, seguimiento.id), {"datos": {"x": 1}}, format="json"
    )

    assert response.status_code == 403


# --------------------------------------------------------------- lectura


def test_get_lista_con_respuestas_y_aprobados_sin_asignacion(zona):
    _, comedor, tecnico = zona
    programa = Programas.objects.create(
        nombre="Abordaje comunitario - Línea Tradicional"
    )
    comedor.programa = programa
    comedor.save(update_fields=["programa"])
    ComedorDatosConvenioPnud.objects.create(
        comedor=comedor,
        aprobadas_almuerzo_lunes=40,
        aprobadas_almuerzo_martes=45,
        aprobadas_merienda_reforzada_lunes=12,
    )
    _crear(comedor, tecnico, estado_validacion=PENDIENTE)

    response = _client(tecnico).get(_url(comedor))

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["datos"] == {"funcionamiento": "Cerrado"}
    aprobados = data["prestaciones_aprobadas"]
    assert aprobados["fuente"] == "convenio_pnud"
    assert aprobados["por_dia"]["lunes"]["almuerzo"] == 40
    assert aprobados["por_dia"]["lunes"]["merienda_reforzada"] == 12
    assert aprobados["por_comida"]["almuerzo"] == 45


def test_aprobados_sin_fuente_quedan_en_null(zona):
    _, comedor, tecnico = zona

    response = _client(tecnico).get(_url(comedor))

    aprobados = response.json()["prestaciones_aprobadas"]
    assert aprobados["fuente"] is None
    assert aprobados["por_comida"]["almuerzo"] is None


def test_listado_y_detalle_territorial_exponen_seguimientos_pnud(zona):
    _, comedor, tecnico = zona
    Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente", territorial_user=tecnico
    )
    _crear(
        comedor,
        tecnico,
        estado_validacion=A_SUBSANAR,
        observaciones_coordinador="Corregir",
    )
    client = _client(tecnico)

    listado = client.get("/api/territorial/comedores/")
    detalle = client.get(f"/api/territorial/comedores/{comedor.id}/")

    item = listado.json()["results"][0]["seguimientos_pnud"]["items"][0]
    assert item["formulario"] == "iia"
    assert item["estado_validacion"] == A_SUBSANAR
    assert item["observaciones_coordinador"] == "Corregir"
    assert "datos" not in item
    item_detalle = detalle.json()["seguimientos_pnud"]["items"][0]
    assert item_detalle["datos"] == {"funcionamiento": "Cerrado"}
    assert "prestaciones_aprobadas" in detalle.json()


def test_firma_se_sube_sin_asignacion_previa(zona, settings, tmp_path):
    _, comedor, tecnico = zona
    settings.MEDIA_ROOT = tmp_path
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color="black").save(buffer, format="PNG")
    firma = SimpleUploadedFile("firma.png", buffer.getvalue(), content_type="image/png")

    response = _client(tecnico).post(
        f"/api/territorial/comedores/{comedor.id}/firma/", {"firma": firma}
    )

    assert response.status_code == 201
    assert response.json()["url"]


# ------------------------------------------------------ revisión (N16)


def _coordinador(client):
    user = get_user_model().objects.create_user(
        username="coord_pnud", password="testpass123"
    )
    for codename in ("review_relevamiento", "view_relevamiento"):
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="relevamientos", codename=codename
            )
        )
    client.force_login(user)
    return user


def test_coordinador_valida_y_ve_el_detalle(client, zona):
    _, comedor, tecnico = zona
    seguimiento = _crear(comedor, tecnico, estado_validacion=PENDIENTE)
    coordinador = _coordinador(client)

    detalle = client.get(
        reverse(
            "seguimiento_pnud_detalle",
            kwargs={"comedor_pk": comedor.id, "pk": seguimiento.id},
        )
    )
    response = client.post(
        reverse(
            "seguimiento_pnud_revision_coordinador",
            kwargs={"comedor_pk": comedor.id, "pk": seguimiento.id},
        ),
        {"estado_validacion": VALIDADO},
    )

    assert detalle.status_code == 200
    assert "Funcionamiento" in detalle.content.decode()
    assert response.status_code == 302
    seguimiento.refresh_from_db()
    assert seguimiento.estado_validacion == VALIDADO
    assert seguimiento.coordinador_id == coordinador.id


def test_coordinador_no_devuelve_sin_observaciones(client, zona):
    _, comedor, tecnico = zona
    seguimiento = _crear(comedor, tecnico, estado_validacion=PENDIENTE)
    _coordinador(client)
    url = reverse(
        "seguimiento_pnud_revision_coordinador",
        kwargs={"comedor_pk": comedor.id, "pk": seguimiento.id},
    )

    sin_obs = client.post(url, {"estado_validacion": A_SUBSANAR})
    seguimiento.refresh_from_db()
    assert seguimiento.estado_validacion == PENDIENTE

    con_obs = client.post(
        url, {"estado_validacion": A_SUBSANAR, "observaciones_coordinador": "Falta DNI"}
    )

    assert sin_obs.status_code == 302
    assert con_obs.status_code == 302
    seguimiento.refresh_from_db()
    assert seguimiento.estado_validacion == A_SUBSANAR
    assert seguimiento.observaciones_coordinador == "Falta DNI"


# ------------------------------------------------- programa (§3 / §4.2)


@pytest.mark.parametrize(
    "programa, formulario, esperado",
    [
        ("Abordaje comunitario - Línea Secos", "secos", 201),
        ("Abordaje comunitario - Línea Secos", "iia", 400),
        ("Abordaje comunitario - Línea Tradicional", "secos", 400),
        ("Abordaje comunitario - Línea Tradicional", "iib1", 201),
        ("Alimentar comunidad", "secos", 400),
        (None, "iia", 400),
    ],
)
def test_formulario_debe_corresponder_al_programa(zona, programa, formulario, esperado):
    _, comedor, tecnico = zona
    comedor.programa = _programa(programa) if programa else None
    comedor.save(update_fields=["programa"])

    response = _client(tecnico).post(
        _url(comedor), _payload(formulario=formulario), format="json"
    )

    assert response.status_code == esperado, response.content
    if esperado == 400:
        assert "detail" in response.json()


@pytest.mark.parametrize("campo", ["formulario", "fecha_hora", "client_uuid"])
def test_valores_no_texto_dan_400(zona, campo):
    _, comedor, tecnico = zona

    response = _client(tecnico).post(
        _url(comedor), _payload(**{campo: 123}), format="json"
    )

    assert response.status_code == 400
    assert "detail" in response.json()


def test_fecha_hora_mismo_formato_en_alta_y_lectura(zona):
    _, comedor, tecnico = zona
    client = _client(tecnico)

    alta = client.post(_url(comedor), _payload(), format="json").json()
    lectura = client.get(_url(comedor)).json()["items"][0]

    assert alta["fecha_hora"] == lectura["fecha_hora"]
    assert alta["fecha_hora"].startswith("2026-09-27T10:30:00")
    assert alta["fecha_hora"].endswith("-03:00")


def test_get_expone_programa_y_encabezado(zona):
    _, comedor, tecnico = zona

    data = _client(tecnico).get(_url(comedor)).json()

    assert data["linea_pnud"] == "tradicional"
    assert data["programa_id"] == comedor.programa_id
    assert data["codigo_proyecto"] == "PNUD-77"
    assert data["id_externo"] == 4321


# -------------------------------------------------------- seguridad (A8)


def test_get_no_expone_respuestas_de_otros_tecnicos(zona):
    provincia, comedor, tecnico = zona
    otro = _make_territorial("terr_pnud_vecino", [provincia])
    _crear(comedor, tecnico, estado_validacion=PENDIENTE)
    _crear(comedor, otro, estado_validacion=PENDIENTE, client_uuid="uuid-del-otro")

    items = _client(tecnico).get(_url(comedor)).json()["items"]

    propios = [i for i in items if i["tecnico"] == tecnico.id]
    ajenos = [i for i in items if i["tecnico"] == otro.id]
    assert "datos" in propios[0]
    assert "datos" not in ajenos[0]
    assert ajenos[0]["tecnico_nombre"] == "terr_pnud_vecino"


def test_client_uuid_de_otro_tecnico_da_409(zona):
    provincia, comedor, tecnico = zona
    otro = _make_territorial("terr_pnud_copia", [provincia])
    _client(tecnico).post(_url(comedor), _payload(), format="json")

    response = _client(otro).post(_url(comedor), _payload(), format="json")

    assert response.status_code == 409
    assert "datos" not in response.json()


def _subir_firma(client, comedor):
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color="black").save(buffer, format="PNG")
    archivo = SimpleUploadedFile("f.png", buffer.getvalue(), content_type="image/png")
    return client.post(
        f"/api/territorial/comedores/{comedor.id}/firma/", {"firma": archivo}
    )


def test_firma_debe_ser_una_url_del_storage_propio(zona, settings, tmp_path):
    _, comedor, tecnico = zona
    settings.MEDIA_ROOT = tmp_path
    client = _client(tecnico)
    url = _subir_firma(client, comedor).json()["url"]

    ajena = client.post(
        _url(comedor),
        _payload(datos={"firma_entrevistado": "https://evil.example/x.png"}),
        format="json",
    )
    propia = client.post(
        _url(comedor),
        _payload(client_uuid="uuid-firma", datos={"firma_entrevistado": url}),
        format="json",
    )

    assert ajena.status_code == 400
    assert propia.status_code == 201, propia.content


def test_firma_sigue_funcionando_en_comedor_asignado_fuera_de_zona(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    otra_provincia = Provincia.objects.create(nombre="Prov Asignada")
    comedor = Comedor.objects.create(nombre="Asignado", provincia=otra_provincia)
    tecnico = _make_territorial("terr_asignado", [])
    Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente", territorial_user=tecnico
    )

    response = _subir_firma(_client(tecnico), comedor)

    assert response.status_code == 201


# ------------------------------------------------ revisión (A4 / A5)


def test_detalle_del_coordinador_usa_etiquetas_y_secciones(client, zona):
    _, comedor, tecnico = zona
    seguimiento = _crear(comedor, tecnico, estado_validacion=PENDIENTE)
    seguimiento.formulario = "iia"
    seguimiento.datos = {
        "ent_nombre_apellido": "Rosa Díaz",
        "recibe_donaciones": True,
        "prestaciones": [
            {
                "id": "fila-tecnica-987",
                "dia": "Lunes",
                "comida": "Almuerzo",
                "ap_total": 40,
            }
        ],
    }
    seguimiento.save()
    _coordinador(client)

    html = client.get(
        reverse(
            "seguimiento_pnud_detalle",
            kwargs={"comedor_pk": comedor.id, "pk": seguimiento.id},
        )
    ).content.decode()

    assert "Datos del entrevistado del espacio comunitario" in html
    assert "Nombre y apellido" in html
    assert "Ent nombre apellido" not in html
    assert "fila-tecnica-987" not in html  # columnas técnicas de las filas hijas
    assert "Acompañamiento Territorial" in html


def test_validado_no_admite_otra_revision(client, zona):
    _, comedor, tecnico = zona
    seguimiento = _crear(comedor, tecnico, estado_validacion=VALIDADO)
    _coordinador(client)

    client.post(
        reverse(
            "seguimiento_pnud_revision_coordinador",
            kwargs={"comedor_pk": comedor.id, "pk": seguimiento.id},
        ),
        {"estado_validacion": A_SUBSANAR, "observaciones_coordinador": "Volver"},
    )

    seguimiento.refresh_from_db()
    assert seguimiento.estado_validacion == VALIDADO


# ------------------------------------------------------------ ronda 2


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/media/firmas/{id}/x.png",
        "javascript:/media/firmas/{id}/x",
        "/media/firmas/{id}/../../otro/x.png",
        "//evil.example/media/firmas/{id}/x.png",
    ],
)
def test_firma_rechaza_esquema_host_y_path_ajenos(zona, url):
    _, comedor, tecnico = zona

    response = _client(tecnico).post(
        _url(comedor),
        _payload(datos={"firma_entrevistado": url.format(id=comedor.id)}),
        format="json",
    )

    assert response.status_code == 400, response.content


def test_firma_relativa_del_storage_propio_se_acepta(zona):
    _, comedor, tecnico = zona

    response = _client(tecnico).post(
        _url(comedor),
        _payload(datos={"firma_entrevistado": f"/media/firmas/{comedor.id}/f.png"}),
        format="json",
    )

    assert response.status_code == 201, response.content


def test_tabla_malformada_da_400(zona):
    _, comedor, tecnico = zona

    response = _client(tecnico).post(
        _url(comedor), _payload(datos={"prestaciones": 5}), format="json"
    )

    assert response.status_code == 400
    assert "prestaciones" in response.json()["detail"]


def test_detalle_no_se_rompe_con_datos_malformados(client, zona):
    _, comedor, tecnico = zona
    seguimiento = _crear(comedor, tecnico, estado_validacion=PENDIENTE)
    seguimiento.formulario = "iia"
    seguimiento.datos = {
        "prestaciones": 5,
        "firma_entrevistado": "javascript:alert(1)",
        "extra": {"a": 1, "b": [{"c": 2}]},
    }
    seguimiento.save()
    _coordinador(client)

    response = client.get(
        reverse(
            "seguimiento_pnud_detalle",
            kwargs={"comedor_pk": comedor.id, "pk": seguimiento.id},
        )
    )

    html = response.content.decode()
    assert response.status_code == 200
    assert 'src="javascript' not in html
    assert "{&#x27;" not in html and "{'" not in html
    assert "A: 1" in html


def test_patch_rechaza_si_el_comedor_dejo_de_ser_pnud(zona):
    _, comedor, tecnico = zona
    seguimiento = _crear(comedor, tecnico, estado_validacion=A_SUBSANAR)
    seguimiento.formulario = "iia"
    seguimiento.save()
    comedor.programa = _programa("Alimentar comunidad")
    comedor.save(update_fields=["programa"])

    response = _client(tecnico).patch(
        _url(comedor, seguimiento.id), {"datos": {"x": 1}}, format="json"
    )

    assert response.status_code == 400
    seguimiento.refresh_from_db()
    assert seguimiento.estado_validacion == A_SUBSANAR


def test_programa_con_nombre_no_usa_el_id_de_respaldo(zona):
    _, comedor, tecnico = zona
    programa, _ = Programas.objects.get_or_create(id=3)
    programa.nombre = "Alimentar comunidad"
    programa.save()
    comedor.programa = programa
    comedor.save(update_fields=["programa"])

    response = _client(tecnico).post(
        _url(comedor), _payload(formulario="secos"), format="json"
    )

    assert response.status_code == 400


def test_alta_concurrente_de_otro_tecnico_da_409(zona, mocker):
    provincia, comedor, tecnico = zona
    otro = _make_territorial("terr_pnud_carrera", [provincia])
    _crear(comedor, otro, client_uuid="pnud-uuid-1")
    filtro_real = SeguimientoPnud.objects.filter
    llamadas = []

    def filtro(*args, **kwargs):
        # La primera búsqueda por uuid no lo ve (carrera): el INSERT choca.
        llamadas.append(kwargs)
        if len(llamadas) == 1:
            return SeguimientoPnud.objects.none()
        return filtro_real(*args, **kwargs)

    mocker.patch.object(SeguimientoPnud.objects, "filter", side_effect=filtro)

    response = _client(tecnico).post(_url(comedor), _payload(), format="json")

    assert response.status_code == 409
    assert "datos" not in response.json()


def test_client_uuid_demasiado_largo_da_400(zona):
    _, comedor, tecnico = zona
    client = _client(tecnico)

    pnud = client.post(_url(comedor), _payload(client_uuid="x" * 65), format="json")
    acta = client.post(
        f"/api/territorial/comedores/{comedor.id}/actas-complementarias/",
        {"client_uuid": "x" * 65},
        format="json",
    )

    assert pnud.status_code == 400
    assert "detail" in pnud.json()
    assert acta.status_code == 400


def test_revision_actualiza_fecha_actualizacion(client, zona):
    _, comedor, tecnico = zona
    seguimiento = _crear(comedor, tecnico, estado_validacion=PENDIENTE)
    SeguimientoPnud.objects.filter(pk=seguimiento.pk).update(
        fecha_actualizacion="2020-01-01T00:00:00Z"
    )
    _coordinador(client)

    client.post(
        reverse(
            "seguimiento_pnud_revision_coordinador",
            kwargs={"comedor_pk": comedor.id, "pk": seguimiento.id},
        ),
        {"estado_validacion": VALIDADO},
    )

    seguimiento.refresh_from_db()
    assert seguimiento.fecha_actualizacion.year > 2020


def test_observaciones_ajenas_no_se_exponen(zona):
    provincia, comedor, tecnico = zona
    otro = _make_territorial("terr_pnud_obs", [provincia])
    _crear(
        comedor,
        otro,
        client_uuid="uuid-obs-ajena",
        estado_validacion=A_SUBSANAR,
        observaciones_coordinador="El DNI 30111222 no coincide",
    )
    Relevamiento.objects.create(
        comedor=comedor, estado="Visita pendiente", territorial_user=tecnico
    )
    client = _client(tecnico)

    get_pnud = client.get(_url(comedor)).json()["items"][0]
    listado = client.get("/api/territorial/comedores/").json()["results"][0]

    assert get_pnud["observaciones_coordinador"] is None
    assert get_pnud["estado_validacion"] == A_SUBSANAR
    item = listado["seguimientos_pnud"]["items"][0]
    assert item["observaciones_coordinador"] is None


# ------------------------------------------------------------ ronda 3


@pytest.mark.parametrize(
    "url",
    [
        r"/media/firmas/{id}/..\..\x.png",
        "/media/firmas/{id}/%5C..%5Cx.png",
        "http://user@testserver/media/firmas/{id}/f.png",
    ],
)
def test_firma_rechaza_barra_invertida_y_credenciales(zona, url):
    _, comedor, tecnico = zona

    response = _client(tecnico).post(
        _url(comedor),
        _payload(datos={"firma_entrevistado": url.format(id=comedor.id)}),
        format="json",
    )

    assert response.status_code == 400, response.content


def test_firma_de_otro_alias_de_allowed_hosts_se_acepta(zona, settings):
    _, comedor, tecnico = zona
    settings.ALLOWED_HOSTS = ["testserver", "sisoc.example.gob.ar"]
    client = _client(tecnico)

    alias = client.post(
        _url(comedor),
        _payload(
            datos={
                "firma_entrevistado": f"https://sisoc.example.gob.ar/media/firmas/{comedor.id}/f.png"
            }
        ),
        format="json",
    )
    puerto = client.post(
        _url(comedor),
        _payload(
            client_uuid="uuid-puerto",
            datos={
                "firma_entrevistado": f"https://testserver:443/media/firmas/{comedor.id}/f.png"
            },
        ),
        format="json",
    )

    assert alias.status_code == 201, alias.content
    assert puerto.status_code == 201, puerto.content


def test_allowed_hosts_con_comodin_no_amplia_los_hosts(zona, settings):
    _, comedor, tecnico = zona
    settings.ALLOWED_HOSTS = ["*", ".example.gob.ar"]

    response = _client(tecnico).post(
        _url(comedor),
        _payload(
            datos={
                "firma_entrevistado": f"https://otro.example.gob.ar/media/firmas/{comedor.id}/f.png"
            }
        ),
        format="json",
    )

    assert response.status_code == 400


def test_mensajes_de_revision_dicen_acompanamiento_territorial(client, zona):
    _, comedor, tecnico = zona
    relevamiento = Relevamiento.objects.create(
        comedor=comedor, estado="Finalizado", territorial_user=tecnico
    )
    _coordinador(client)

    response = client.post(
        reverse(
            "relevamiento_revision_coordinador",
            kwargs={"comedor_pk": comedor.id, "pk": relevamiento.id},
        ),
        {"estado_validacion": VALIDADO},
        follow=True,
    )

    mensajes = [str(m) for m in response.context["messages"]]
    assert "Acompañamiento Territorial validado correctamente." in mensajes
