"""Fixtures de Inspecciones escolares: usuarios por rol, escuela y payloads."""

import copy
import io
import uuid

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.models import Localidad, Municipio, Provincia
from inspecciones.models import AsignacionEscuela, Escuela
from inspecciones.services.formato import hoy

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 256
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 256
PDF = b"%PDF-1.4\n%prueba\n"


def _usuario(username, rol):
    user = get_user_model().objects.create_user(
        username=username, password="x", first_name=username.title()
    )
    if rol:
        user.profile.es_inspector_escolar = True
        user.profile.inspecciones_rol = rol
        user.profile.save(update_fields=["es_inspector_escolar", "inspecciones_rol"])
    return user


def _cliente(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def inspector_a(db):
    return _usuario("inspector_a", "inspector")


@pytest.fixture
def inspector_b(db):
    return _usuario("inspector_b", "inspector")


@pytest.fixture
def coordinacion(db):
    return _usuario("coordinacion", "coordinacion")


@pytest.fixture
def api_a(inspector_a):
    return _cliente(inspector_a)


@pytest.fixture
def api_b(inspector_b):
    return _cliente(inspector_b)


@pytest.fixture
def api_coord(coordinacion):
    return _cliente(coordinacion)


@pytest.fixture
def cliente_de():
    return _cliente


@pytest.fixture
def geografia(db):
    """Provincias, municipios y localidades mínimos para el padrón.

    - Buenos Aires: San Justo (única) y San José (en dos municipios).
    - CABA: la localidad genérica de la ciudad y una homónima del padrón.
    - Tierra del Fuego con su nombre oficial completo.
    """
    caba = Provincia.objects.create(nombre="Ciudad Autónoma de Buenos Aires")
    bsas = Provincia.objects.create(nombre="Buenos Aires")
    tdf = Provincia.objects.create(
        nombre="Tierra del Fuego, Antártida e Islas del Atlántico Sur"
    )
    comuna = Municipio.objects.create(nombre="Comuna 1", provincia=caba)
    matanza = Municipio.objects.create(nombre="La Matanza", provincia=bsas)
    brown = Municipio.objects.create(nombre="Almirante Brown", provincia=bsas)
    lomas = Municipio.objects.create(nombre="Lomas de Zamora", provincia=bsas)
    ushuaia = Municipio.objects.create(nombre="Ushuaia", provincia=tdf)
    return {
        "caba": caba,
        "bsas": bsas,
        "tdf": tdf,
        "caba_generica": Localidad.objects.create(
            nombre="Ciudad Autónoma de Buenos Aires", municipio=comuna
        ),
        "caba_homonima": Localidad.objects.create(
            nombre="Ciudad de Buenos Aires", municipio=comuna
        ),
        "san_justo": Localidad.objects.create(nombre="San Justo", municipio=matanza),
        "san_jose_brown": Localidad.objects.create(nombre="San José", municipio=brown),
        "san_jose_lomas": Localidad.objects.create(nombre="San José", municipio=lomas),
        "ushuaia": Localidad.objects.create(nombre="Ushuaia", municipio=ushuaia),
    }


@pytest.fixture
def gestor(db):
    """Usuario del backoffice con el permiso de gestión (sin rol en la app)."""
    user = get_user_model().objects.create_user(username="gestor", password="x")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="inspecciones", codename="gestionar_inspecciones"
        )
    )
    return user


@pytest.fixture
def panel(client, gestor):
    client.force_login(gestor)
    return client


@pytest.fixture
def planilla():
    """Arma un ``.xlsx`` (o ``.csv``) subido, con filas de título opcionales."""

    def construir(filas, *, nombre="padron.xlsx", titulo=True, segunda_hoja=True):
        if nombre.endswith(".csv"):
            texto = "\n".join(";".join(str(v) for v in fila) for fila in filas)
            return SimpleUploadedFile(nombre, texto.encode("utf-8"))
        libro = openpyxl.Workbook()
        hoja = libro.active
        hoja.title = "padron"
        if titulo:
            hoja.append(["Establecimiento - Localización"])
        for fila in filas:
            hoja.append(list(fila))
        if segunda_hoja:
            # Nunca se lee: puede tener datos personales.
            otra = libro.create_sheet("- Usuarios")
            otra.append(["Jurisdicción", "Localidad", "Cueanexo", "Nombre"])
            otra.append(["Buenos Aires", "San Justo", "999999999", "NO LEER"])
        contenido = io.BytesIO()
        libro.save(contenido)
        return SimpleUploadedFile(nombre, contenido.getvalue())

    return construir


@pytest.fixture
def escuela(db):
    return Escuela.objects.create(
        codigo="060123400",
        nombre='EP N° 12 "Domingo F. Sarmiento"',
        cue="060123400",
        distrito="La Matanza",
        localidad="San Justo",
        domicilio="Av. Pres. Perón 3245",
        nivel="Primario",
    )


@pytest.fixture
def asignada_a(escuela, inspector_a):
    return AsignacionEscuela.objects.create(
        escuela=escuela, inspector=inspector_a, fecha=hoy()
    )


def _cantidad(valor, condicion="dato", motivo=""):
    return {"valor": valor, "condicion": condicion, "motivo": motivo}


def payload_base(escuela_obj=None, *, revision=1, imagen_ingreso=None):
    """Estado final válido: escuela constatada, sin advertencias, con excepción."""
    return {
        "revision": revision,
        "formulario_version": "v1",
        "escuela": {
            "catalogo_id": escuela_obj.codigo if escuela_obj else None,
            "carga_manual": escuela_obj is None,
            "nombre": escuela_obj.nombre if escuela_obj else "Escuela manual",
            "cue": escuela_obj.cue if escuela_obj else "0601",
            "cue_desconocido": False,
            "motivo_sin_cue": "",
            "domicilio": "Av. Pres. Perón 3245",
            "localidad": "San Justo",
            "distrito": "La Matanza",
        },
        "fecha_visita": hoy().isoformat(),
        "turno": "tarde",
        "motivo_nueva_visita": "",
        "ubicacion": {
            "fuente": "gps",
            "lat": -34.67021,
            "lng": -58.56344,
            "precision_m": 12,
            "capturada_at": "2026-10-14T14:32:05-03:00",
            "motivo_sin_gps": "",
        },
        "respuestas": {
            "f04": {
                "imagen_uuid": imagen_ingreso,
                "motivo_sin_foto": "" if imagen_ingreso else "Sin cámara",
            },
            "f05": "si",
            "resultado": "constatado",
            "motivo_parcial": "",
            "que_ocurrio": "",
            "f06": {"nadie": False, "nombre": "María", "funcion": "Directora"},
            "f07": "si",
            "f08": "si",
            "f09": _cantidad(24),
            "f10": _cantidad(20),
            "f11": _cantidad(10),
            "f12": _cantidad(8),
            "justificaciones": {
                "presentes_superan": "",
                "aulas_superan": "",
                "sin_personal_con_presentes": "",
                "sin_estudiantes_con_aulas": "",
            },
            "f16": "",
        },
        "imagenes": (
            [{"uuid": imagen_ingreso, "tipo": "ingreso", "descripcion": ""}]
            if imagen_ingreso
            else []
        ),
        "f15": [],
        "firma": {
            "tipo": "excepcion",
            "motivo_tipo": "negativa",
            "motivo": "Se negó a firmar",
            "nombre": "María",
            "cargo": "Directora",
            "registrada_at": "2026-10-14T14:50:00-03:00",
            "hash_contenido": "a" * 64,
        },
        "creada_at": "2026-10-14T14:28:00-03:00",
        "actualizada_at": "2026-10-14T14:41:10-03:00",
    }


@pytest.fixture
def payload():
    def construir(escuela_obj=None, **kwargs):
        return copy.deepcopy(payload_base(escuela_obj, **kwargs))

    return construir


@pytest.fixture
def imagen():
    def construir(contenido=JPEG, nombre="foto.jpg", tipo="image/jpeg"):
        return SimpleUploadedFile(nombre, contenido, content_type=tipo)

    return construir


@pytest.fixture
def pdf():
    return lambda: SimpleUploadedFile("acta.pdf", PDF, content_type="application/pdf")


@pytest.fixture
def png():
    return lambda: SimpleUploadedFile("firma.png", PNG, content_type="image/png")


@pytest.fixture
def nuevo_uuid():
    return lambda: str(uuid.uuid4())


@pytest.fixture
def cerrar(payload, nuevo_uuid):
    """Cierra una inspección válida del cliente y devuelve (uuid, respuesta)."""

    def _cerrar(client, escuela_obj=None, inspeccion_uuid=None, **kwargs):
        inspeccion_uuid = inspeccion_uuid or nuevo_uuid()
        respuesta = client.post(
            f"/api/inspecciones/borradores/{inspeccion_uuid}/finalizar/",
            payload(escuela_obj, **kwargs),
            format="json",
        )
        return inspeccion_uuid, respuesta

    return _cerrar
