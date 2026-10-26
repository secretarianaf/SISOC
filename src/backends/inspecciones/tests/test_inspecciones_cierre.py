"""Cierre transaccional, numeración, actas, PDF y notificación en papel."""

import re

import pytest
from django.utils import timezone

from inspecciones.models import Acta, Inspeccion, NotificacionPapel, SecuenciaActa
from inspecciones.services.cierre import siguiente_numero

pytestmark = pytest.mark.django_db

BASE = "/api/inspecciones"
NUMERO = re.compile(r"^ACTA-\d{4}-\d{6}$")


def _anio():
    return timezone.localdate().year


# ------------------------------------------------------------- cierre


def test_cierre_asigna_numero_hora_oficial_e_instantanea(api_a, escuela, cerrar):
    uuid, response = cerrar(api_a, escuela)

    assert response.status_code == 200, response.json()
    cuerpo = response.json()
    assert cuerpo["numero"] == f"ACTA-{_anio()}-000001"
    assert NUMERO.match(cuerpo["numero"])
    assert cuerpo["pdf_estado"] == "pendiente"
    assert cuerpo["cerrada_at"].endswith("-03:00")

    acta = Acta.objects.get(numero=cuerpo["numero"])
    assert acta.inspeccion.estado == Inspeccion.Estado.FINALIZADA
    assert acta.escuela == escuela
    assert acta.notificacion_estado == Acta.EstadoNotificacion.PENDIENTE
    assert acta.instantanea["formulario"]["preguntas"]["f05"] == "Abierta"
    assert acta.instantanea["payload"]["respuestas"]["f09"]["valor"] == 24
    assert len(acta.instantanea_sha256) == 64


def test_numeros_consecutivos_sin_reutilizar(api_a, api_b, cerrar):
    numeros = [cerrar(cliente)[1].json()["numero"] for cliente in (api_a, api_b, api_a)]

    anio = _anio()
    assert numeros == [f"ACTA-{anio}-{n:06d}" for n in (1, 2, 3)]
    assert SecuenciaActa.objects.get(anio=anio).ultimo == 3


def test_cierre_rechazado_no_consume_numero(api_a, payload, cerrar, nuevo_uuid):
    invalido = payload()
    invalido["respuestas"]["f05"] = None
    uuid = nuevo_uuid()
    rechazo = api_a.post(
        f"{BASE}/borradores/{uuid}/finalizar/", invalido, format="json"
    )
    assert rechazo.status_code == 400

    _, ok = cerrar(api_a)
    assert ok.json()["numero"] == f"ACTA-{_anio()}-000001"


def test_cierre_idempotente_por_uuid(api_a, cerrar):
    uuid, primera = cerrar(api_a)
    _, segunda = cerrar(api_a, inspeccion_uuid=uuid)

    assert segunda.status_code == 200
    assert segunda.json() == primera.json()
    assert Acta.objects.count() == 1


def test_cierre_invalido_es_400_y_el_borrador_queda_como_estaba(
    api_a, payload, nuevo_uuid
):
    uuid = nuevo_uuid()
    api_a.put(f"{BASE}/borradores/{uuid}/", payload(revision=3), format="json")
    invalido = payload(revision=4)
    invalido["respuestas"]["f09"] = {"valor": -2, "condicion": "dato", "motivo": ""}

    response = api_a.post(
        f"{BASE}/borradores/{uuid}/finalizar/", invalido, format="json"
    )

    assert response.status_code == 400
    assert "respuestas.f09" in response.json()["errores"]
    inspeccion = Inspeccion.objects.get(uuid=uuid)
    assert inspeccion.estado == Inspeccion.Estado.BORRADOR
    assert inspeccion.revision == 3
    assert not Acta.objects.exists()


def test_cierre_exige_imagenes_subidas(api_a, payload, imagen, nuevo_uuid):
    uuid, ingreso = nuevo_uuid(), nuevo_uuid()
    datos = payload(imagen_ingreso=ingreso)

    faltante = api_a.post(f"{BASE}/borradores/{uuid}/finalizar/", datos, format="json")
    assert faltante.status_code == 400
    assert faltante.json()["faltantes"] == [ingreso]

    api_a.put(
        f"{BASE}/borradores/{uuid}/imagenes/{ingreso}/",
        {"archivo": imagen(), "tipo": "ingreso"},
        format="multipart",
    )
    ok = api_a.post(f"{BASE}/borradores/{uuid}/finalizar/", datos, format="json")
    assert ok.status_code == 200, ok.json()
    # Cerrada, ya no se suben ni se borran imágenes.
    url = f"{BASE}/borradores/{uuid}/imagenes/{ingreso}/"
    assert api_a.delete(url).status_code == 409


def test_cierre_con_firma_en_pantalla(api_a, payload, png, nuevo_uuid):
    uuid, firma = nuevo_uuid(), nuevo_uuid()
    api_a.put(
        f"{BASE}/borradores/{uuid}/imagenes/{firma}/",
        {"archivo": png(), "tipo": "firma"},
        format="multipart",
    )
    datos = payload()
    datos["imagenes"] = [{"uuid": firma, "tipo": "firma", "descripcion": ""}]
    datos["firma"] = {
        "tipo": "firma",
        "nombre": "María Fernández",
        "cargo": "Vicedirectora",
        "dni": "",
        "texto_mostrado": "Texto de conformidad",
        "conformidad": True,
        "imagen_uuid": firma,
        "firmada_at": "2026-10-14T14:51:00-03:00",
        "hash_contenido": "b" * 64,
    }

    response = api_a.post(f"{BASE}/borradores/{uuid}/finalizar/", datos, format="json")

    assert response.status_code == 200, response.json()
    detalle = api_a.get(f"{BASE}/actas/{response.json()['numero']}/").json()
    assert detalle["firma_tipo"] == "firma"
    eventos = {e["codigo"]: e for e in detalle["eventos"]}
    assert {"creada", "firmada", "finalizada"} <= set(eventos)
    assert eventos["firmada"]["actor"] == "María Fernández"
    assert eventos["firmada"]["at"] == "2026-10-14T14:51:00-03:00"
    assert detalle["firma"]["hash_contenido"] == "b" * 64
    assert detalle["imagenes"][0]["uuid"] == firma


def test_segunda_visita_en_el_mismo_turno_exige_motivo(
    api_a, api_b, escuela, payload, cerrar
):
    cerrar(api_a, escuela)
    _, sin_motivo = cerrar(api_b, escuela)
    assert sin_motivo.status_code == 400
    assert "motivo_nueva_visita" in sin_motivo.json()["errores"]

    datos = payload(escuela)
    datos["motivo_nueva_visita"] = "Verificación pedida por coordinación"
    response = api_b.post(
        f"{BASE}/borradores/3f1d7c0e-8e0b-4b3f-9a8e-1c2d3e4f5a6b/finalizar/",
        datos,
        format="json",
    )
    assert response.status_code == 200, response.json()


def test_el_acta_es_inmutable(api_a, cerrar):
    _, response = cerrar(api_a)
    acta = Acta.objects.get(numero=response.json()["numero"])

    acta.instantanea = {"payload": {}}
    with pytest.raises(ValueError, match="inmutable"):
        acta.save()


def test_secuencia_por_anio():
    SecuenciaActa.objects.create(anio=2031, ultimo=41)

    assert siguiente_numero(2031) == 42
    assert siguiente_numero(2032) == 1


# ------------------------------------------------------------- actas


def test_listado_y_detalle_de_actas_con_permisos(
    api_a, api_b, api_coord, escuela, cerrar
):
    uuid, cierre = cerrar(api_a, escuela)
    numero = cierre.json()["numero"]

    listado = api_a.get(f"{BASE}/actas/").json()
    assert [a["numero"] for a in listado] == [numero]
    resumen = listado[0]
    assert resumen["uuid"] == uuid
    assert resumen["estado"] == "finalizada"
    assert resumen["escuela"] == {
        "nombre": escuela.nombre,
        "cue": "060123400",
        "distrito": "La Matanza",
        "localidad": "San Justo",
    }
    assert resumen["resultado"] == "constatado"
    assert resumen["firma_tipo"] == "excepcion"
    assert resumen["notificacion"] == {
        "estado": "pendiente",
        "cargada_at": None,
        "condicion_firma": None,
    }

    # Inspector B: lo ajeno no existe para él.
    assert api_b.get(f"{BASE}/actas/").json() == []
    assert api_b.get(f"{BASE}/actas/{numero}/").status_code == 404
    assert api_b.get(f"{BASE}/actas/{numero}/pdf/").status_code == 404

    # Coordinación ve todo; "Mis actas" sin parámetro sigue siendo lo propio.
    assert api_coord.get(f"{BASE}/actas/").json() == []
    todas = api_coord.get(f"{BASE}/actas/", {"alcance": "todas"}).json()
    assert [a["numero"] for a in todas] == [numero]
    detalle = api_coord.get(f"{BASE}/actas/{numero}/").json()
    assert detalle["numero"] == numero
    assert detalle["respuestas"]["f09"]["valor"] == 24
    assert detalle["escuela"]["catalogo_id"] == escuela.codigo
    assert detalle["formulario"]["version"] == "v1"
    assert detalle["notificaciones"] == []
    assert "finalizada" in [e["codigo"] for e in detalle["eventos"]]


def test_pdf_subida_idempotente_y_descarga(api_a, api_b, api_coord, cerrar, pdf):
    _, cierre = cerrar(api_a)
    numero = cierre.json()["numero"]
    url = f"{BASE}/actas/{numero}/pdf/"

    assert api_a.get(url).status_code == 404
    assert api_b.put(url, {"archivo": pdf()}, format="multipart").status_code == 404
    no_pdf = api_a.put(
        url,
        {"archivo": pdf().__class__("x.pdf", b"no es pdf")},
        format="multipart",
    )
    assert no_pdf.status_code == 422

    primera = api_a.put(url, {"archivo": pdf()}, format="multipart")
    assert primera.status_code == 200
    assert primera.json()["pdf_estado"] == "disponible"
    segunda = api_a.put(url, {"archivo": pdf()}, format="multipart")
    assert segunda.json()["sha256"] == primera.json()["sha256"]

    descarga = api_a.get(url)
    assert descarga.status_code == 200
    assert descarga["Content-Type"] == "application/pdf"
    assert b"".join(descarga.streaming_content).startswith(b"%PDF-")
    assert api_coord.get(url).status_code == 200
    assert api_a.get(f"{BASE}/actas/").json()[0]["pdf_estado"] == "disponible"


# ------------------------------------------------------------- notificación


def _notificar(client, numero, carga_uuid, archivos, **extra):
    datos = {
        "uuid": carga_uuid,
        "archivos": archivos,
        "notificada_at": "2026-10-14T16:00:00-03:00",
        "receptor_nombre": "María Fernández",
        "receptor_cargo": "Vicedirectora",
        "condicion_firma": "firmada",
        "motivo": "",
        "observaciones": "",
        "numero_confirmado": numero,
        **extra,
    }
    return client.post(
        f"{BASE}/actas/{numero}/notificaciones/", datos, format="multipart"
    )


def test_notificacion_idempotente_y_versionada(
    api_a, api_b, api_coord, cerrar, imagen, nuevo_uuid
):
    _, cierre = cerrar(api_a)
    numero = cierre.json()["numero"]
    carga = nuevo_uuid()

    primera = _notificar(api_a, numero, carga, [imagen(), imagen()])
    assert primera.status_code == 200, primera.json()
    assert primera.json()["estado"] == "cargada"
    repetida = _notificar(api_a, numero, carga, [imagen()])
    assert repetida.json() == primera.json()
    assert NotificacionPapel.objects.count() == 1

    correccion = _notificar(
        api_a,
        numero,
        nuevo_uuid(),
        [imagen()],
        condicion_firma="negativa",
        motivo="Se negó a firmar el papel",
        reemplaza_uuid=carga,
        motivo_correccion="Foto ilegible",
    )
    assert correccion.status_code == 200, correccion.json()

    detalle = api_coord.get(f"{BASE}/actas/{numero}/").json()
    assert [n["version"] for n in detalle["notificaciones"]] == [1, 2]
    assert detalle["notificaciones"][0]["archivos"] == 2
    assert detalle["notificaciones"][1]["reemplaza_uuid"] == carga
    assert detalle["notificacion"]["estado"] == "cargada"
    assert detalle["notificacion"]["condicion_firma"] == "negativa"
    archivo_id = detalle["notificaciones"][0]["archivos_ids"][0]
    archivo_url = f"{BASE}/notificaciones/archivos/{archivo_id}/"
    assert api_coord.get(archivo_url).status_code == 200
    assert api_b.get(archivo_url).status_code == 404
    # La carga no toca el acta: número, instantánea y PDF siguen iguales.
    acta = Acta.objects.get(numero=numero)
    assert acta.estado == Acta.Estado.FINALIZADA
    assert not acta.pdf


def test_notificacion_valida_numero_cantidad_y_motivo(
    api_a, api_b, cerrar, imagen, nuevo_uuid
):
    _, cierre = cerrar(api_a)
    numero = cierre.json()["numero"]

    otro_numero = _notificar(
        api_a, numero, nuevo_uuid(), [imagen()], numero_confirmado="ACTA-2000-000001"
    )
    assert otro_numero.status_code == 400
    seis = _notificar(api_a, numero, nuevo_uuid(), [imagen() for _ in range(6)])
    assert seis.status_code == 400
    sin_motivo = _notificar(
        api_a, numero, nuevo_uuid(), [imagen()], condicion_firma="sin_receptor"
    )
    assert sin_motivo.status_code == 400
    assert "motivo" in sin_motivo.json()["errores"]
    ajena = _notificar(api_b, numero, nuevo_uuid(), [imagen()])
    assert ajena.status_code == 404
    assert not NotificacionPapel.objects.exists()


def test_notificacion_en_acta_anulada_es_409(api_a, cerrar, imagen, nuevo_uuid):
    _, cierre = cerrar(api_a)
    numero = cierre.json()["numero"]
    Acta.objects.filter(numero=numero).update(estado=Acta.Estado.ANULADA)

    response = _notificar(api_a, numero, nuevo_uuid(), [imagen()])

    assert response.status_code == 409
