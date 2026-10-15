"""Tablero en vivo de coordinación: indicadores, mapa, tabla, CSV y permisos."""

import csv
import io
import itertools
import os
import time
import uuid
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.db import connection
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.test.utils import CaptureQueriesContext
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from core.models import Localidad, Municipio, Provincia
from inspecciones.models import Acta, Escuela, Inspeccion, NotificacionPapel
from inspecciones.services import tablero
from inspecciones.services.formato import hoy

pytestmark = pytest.mark.django_db

URL_PAGINA = "/inspecciones/tablero/"
URL_DATOS = "/inspecciones/tablero/datos/"
URL_CSV = "/inspecciones/tablero/exportar.csv"

_numeros = itertools.count(1)


@pytest.fixture(autouse=True)
def _cache_limpio():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def geo(db):
    """Dos provincias con una localidad cada una."""
    resultado = {}
    for clave in ("a", "b"):
        provincia = Provincia.objects.create(nombre=f"Provincia tablero {clave}")
        municipio = Municipio.objects.create(
            nombre=f"Municipio {clave}", provincia=provincia
        )
        localidad = Localidad.objects.create(
            nombre=f"Localidad {clave}", municipio=municipio
        )
        resultado[clave] = (provincia, localidad)
    return resultado


def nueva_escuela(cue, geo_clave=None, geo=None):
    provincia, localidad = geo[geo_clave] if geo_clave else (None, None)
    return Escuela.objects.create(
        codigo=cue,
        cue=cue,
        nombre=f"Escuela {cue}",
        provincia=provincia,
        localidad_vinculada=localidad,
        localidad="Texto",
        distrito="Distrito",
    )


def cantidad(valor, condicion="dato"):
    if valor is None and condicion == "dato":
        condicion = "no_informado"
    return {"valor": valor, "condicion": condicion, "motivo": ""}


def crear_acta(  # pylint: disable=too-many-arguments,too-many-locals
    inspector,
    escuela=None,
    *,
    fecha=None,
    turno="tarde",
    resultado="constatado",
    f07="si",
    f08="si",
    f09=24,
    f10=20,
    f11=10,
    f12=8,
    ubicacion="gps",
    firma_tipo="excepcion",
    motivo_firma="negativa",
    estado=Acta.Estado.FINALIZADA,
    es_prueba=False,
    notificacion=Acta.EstadoNotificacion.PENDIENTE,
    cue_manual="0601",
    cerrada_at=None,
):
    numero = next(_numeros)
    fecha = fecha or hoy()
    inspeccion = Inspeccion.objects.create(
        uuid=uuid.uuid4(),
        inspector=inspector,
        estado=Inspeccion.Estado.FINALIZADA,
        revision=1,
        escuela=escuela,
        fecha_visita=fecha,
        turno=turno,
        resultado=resultado,
    )
    if ubicacion == "gps":
        datos_ubicacion = {
            "fuente": "gps",
            "lat": -34.6 - numero / 1000,
            "lng": -58.5,
            "precision_m": 10,
        }
    elif ubicacion == "manual":
        datos_ubicacion = {
            "fuente": "manual",
            "lat": None,
            "lng": None,
            "motivo_sin_gps": "Sin señal",
        }
    else:
        datos_ubicacion = None
    firma_uuid = str(uuid.uuid4())
    firma = (
        {
            "tipo": "firma",
            "nombre": "Ana",
            "cargo": "Directora",
            "imagen_uuid": firma_uuid,
        }
        if firma_tipo == "firma"
        else {"tipo": "excepcion", "motivo_tipo": motivo_firma, "motivo": "x"}
    )
    payload = {
        "escuela": {
            "nombre": escuela.nombre if escuela else "Escuela manual",
            "cue": escuela.cue if escuela else cue_manual,
            "localidad": "San Justo",
            "distrito": "La Matanza",
        },
        "fecha_visita": fecha.isoformat(),
        "turno": turno,
        "ubicacion": datos_ubicacion,
        "respuestas": {
            "f05": "no" if resultado == "cerrada" else "si",
            "resultado": resultado,
            "f06": {"nadie": False, "nombre": "María", "funcion": "Directora"},
            "f07": f07,
            "f08": f08,
            "f09": f09 if isinstance(f09, dict) else cantidad(f09),
            "f10": f10 if isinstance(f10, dict) else cantidad(f10),
            "f11": f11 if isinstance(f11, dict) else cantidad(f11),
            "f12": f12 if isinstance(f12, dict) else cantidad(f12),
            "f16": "=HIPERVINCULO(1)",
        },
        "f15": [str(uuid.uuid4())],
        "firma": firma,
    }
    return Acta.objects.create(
        inspeccion=inspeccion,
        inspector=inspector,
        escuela=escuela,
        numero=f"ACTA-2026-{numero:06d}",
        anio=2026,
        secuencia=numero,
        cerrada_at=cerrada_at or timezone.now() - timedelta(minutes=numero),
        fecha_visita=fecha,
        turno=turno,
        resultado=resultado,
        firma_tipo=firma_tipo,
        formulario_version="v1",
        instantanea={"numero": f"ACTA-2026-{numero:06d}", "payload": payload},
        instantanea_sha256="0" * 64,
        estado=estado,
        es_prueba=es_prueba,
        notificacion_estado=notificacion,
    )


def datos(**params):
    return tablero.calcular_tablero(tablero.leer_filtros(params))


def numeros_csv(**params):
    salida = io.StringIO()
    tablero.escribir_csv(salida, tablero.leer_filtros(params))
    filas = list(csv.reader(io.StringIO(salida.getvalue().lstrip("﻿")), delimiter=";"))
    return filas[0], filas[1:]


# ------------------------------------------------------------ validez


def test_anuladas_y_de_prueba_no_cuentan(inspector_a, geo):
    escuela = nueva_escuela("060000001", "a", geo)
    valida = crear_acta(inspector_a, escuela)
    crear_acta(inspector_a, escuela, estado=Acta.Estado.ANULADA)
    crear_acta(inspector_a, nueva_escuela("060000002", "a", geo), es_prueba=True)

    resultado = datos()

    indicadores = resultado["indicadores"]
    assert indicadores["actas_validas"] == 1
    assert indicadores["escuelas_unicas"] == 1
    assert indicadores["escuelas_con_mas_de_una_visita"] == 0
    assert indicadores["notificacion_pendiente"] == 1
    assert [p["numero"] for p in resultado["mapa"]["puntos"]] == [valida.numero]
    assert [a["numero"] for a in resultado["ultimas"]] == [valida.numero]
    assert sum(t["cantidad"] for t in resultado["turnos"]) == 1
    assert resultado["ausentismo"]["computables"] == 1
    _, filas = numeros_csv()
    assert [fila[0] for fila in filas] == [valida.numero]


def test_borradores_van_aparte(inspector_a, inspector_b, escuela):
    crear_acta(inspector_a, escuela)
    Inspeccion.objects.create(
        uuid=uuid.uuid4(),
        inspector=inspector_b,
        revision=3,
        escuela=escuela,
        fecha_visita=hoy(),
        turno="tarde",
    )
    # Sin datos todavía (revisión 0) o de otro día: no es avance de hoy.
    Inspeccion.objects.create(uuid=uuid.uuid4(), inspector=inspector_b, revision=0)
    Inspeccion.objects.create(
        uuid=uuid.uuid4(),
        inspector=inspector_b,
        revision=2,
        fecha_visita=hoy() - timedelta(days=1),
    )

    indicadores = datos()["indicadores"]

    assert indicadores["actas_validas"] == 1
    assert indicadores["borradores_en_curso"] == 1
    assert indicadores["inspectores"] == {
        "con_actividad": 2,
        "habilitados": 2,
        "sin_actividad": 0,
    }


def test_escuelas_unicas_se_deduplican(inspector_a, inspector_b, geo):
    a = nueva_escuela("060000011", "a", geo)
    b = nueva_escuela("060000012", "b", geo)
    crear_acta(inspector_a, a, turno="manana")
    crear_acta(inspector_b, a, turno="tarde")
    crear_acta(inspector_a, b)
    # Carga manual: misma escuela (mismo CUE) en dos visitas.
    crear_acta(inspector_a, None, cue_manual="0601 99")
    crear_acta(inspector_b, None, cue_manual="060199")

    indicadores = datos()["indicadores"]

    assert indicadores["actas_validas"] == 5
    assert indicadores["escuelas_unicas"] == 3
    assert indicadores["escuelas_con_mas_de_una_visita"] == 2


def test_firma_y_notificacion_desglosadas(inspector_a, escuela):
    crear_acta(inspector_a, escuela, firma_tipo="firma")
    crear_acta(inspector_a, escuela, motivo_firma="negativa")
    crear_acta(inspector_a, escuela, motivo_firma="ausente")
    crear_acta(
        inspector_a,
        escuela,
        motivo_firma="ausente",
        notificacion=Acta.EstadoNotificacion.CARGADA,
    )

    indicadores = datos()["indicadores"]

    assert indicadores["con_firma"] == 1
    assert indicadores["sin_firma"] == 3
    motivos = {m["valor"]: m["cantidad"] for m in indicadores["sin_firma_por_motivo"]}
    assert motivos == {"negativa": 1, "ausente": 2, "otra": 0}
    assert indicadores["notificacion_pendiente"] == 3
    assert indicadores["notificacion_cargada"] == 1


# ------------------------------------------------------------ índices


def test_ausentismo_y_aulas_solo_computables(inspector_a, escuela):
    crear_acta(inspector_a, escuela, f09=10, f10=5, f11=4, f12=4)
    # Cero presentes y cero aulas funcionando: son datos, no faltantes.
    crear_acta(inspector_a, escuela, f09=20, f10=0, f11=6, f12=0)
    # Denominador cero: se excluye.
    crear_acta(inspector_a, escuela, f09=0, f10=0, f11=0, f12=0)
    # Sin dato (no informado / no constatado).
    crear_acta(
        inspector_a,
        escuela,
        f09=None,
        f10=cantidad(None, "no_constatado"),
        f11=cantidad(None, "no_informado"),
        f12=3,
    )
    # Sin constatación: aunque tenga números no entra.
    crear_acta(inspector_a, escuela, resultado="cerrada", f09=30, f10=1)
    # Constatación parcial con los dos datos: entra.
    crear_acta(inspector_a, escuela, resultado="parcial", f09=10, f10=10, f11=2, f12=1)

    resultado = datos()
    ausentismo, aulas = resultado["ausentismo"], resultado["aulas"]

    assert ausentismo["previsto"] == 40
    assert ausentismo["presente"] == 15
    assert ausentismo["porcentaje"] == 62.5
    assert ausentismo["computables"] == 3
    assert ausentismo["excluidas"] == 3
    assert ausentismo["colegios"] == 1
    assert ausentismo["motivos_exclusion"] == {
        "sin_constatacion": 1,
        "sin_dato": 1,
        "denominador_cero": 1,
    }
    assert aulas["previsto"] == 12
    assert aulas["presente"] == 5
    assert aulas["porcentaje"] == 41.7
    assert aulas["computables"] == 3
    assert aulas["excluidas"] == 3
    assert aulas["colegios"] == 1


def test_indices_sin_computables_no_inventan_cero(inspector_a, escuela):
    crear_acta(inspector_a, escuela, resultado="no_ingreso", f09=None, f10=None)

    resultado = datos()

    assert resultado["ausentismo"]["porcentaje"] is None
    assert resultado["ausentismo"]["computables"] == 0
    assert resultado["ausentismo"]["excluidas"] == 1
    assert resultado["ausentismo"]["colegios"] == 0


def test_presencia_separa_no_constatado_y_sin_dato(inspector_a, escuela):
    crear_acta(inspector_a, escuela, f07="si", f08="no")
    crear_acta(inspector_a, escuela, f07="no_constatado", f08="si")
    crear_acta(inspector_a, escuela, resultado="cerrada", f07=None, f08=None)

    presencia = datos()["presencia"]

    personal = {c["valor"]: c["cantidad"] for c in presencia["personal"]["categorias"]}
    assert personal == {"si": 1, "no": 0, "no_constatado": 1, "sin_dato": 1}
    assert presencia["personal"]["denominador"] == 2
    assert presencia["personal"]["total"] == 3
    estudiantes = {
        c["valor"]: c["cantidad"] for c in presencia["estudiantes"]["categorias"]
    }
    assert estudiantes == {"si": 1, "no": 1, "no_constatado": 0, "sin_dato": 1}


def test_resultados_y_turnos_con_categorias_explicitas(inspector_a, escuela):
    crear_acta(inspector_a, escuela, turno="manana", resultado="constatado")
    crear_acta(inspector_a, escuela, turno="manana", resultado="cerrada")
    crear_acta(inspector_a, escuela, turno="", resultado="")

    resultado = datos()

    turnos = {t["valor"]: t["cantidad"] for t in resultado["turnos"]}
    assert turnos == {
        "manana": 2,
        "tarde": 0,
        "vespertino": 0,
        "noche": 0,
        "sin_dato": 1,
    }
    resultados = {r["valor"]: r["cantidad"] for r in resultado["resultados"]}
    assert resultados == {
        "constatado": 1,
        "parcial": 0,
        "cerrada": 1,
        "no_ingreso": 0,
        "sin_dato": 1,
    }


# ------------------------------------------------------------ mapa


def test_actas_sin_gps_no_van_al_mapa_y_se_cuentan(inspector_a, escuela):
    con_gps = crear_acta(inspector_a, escuela, resultado="no_ingreso")
    crear_acta(inspector_a, escuela, ubicacion="manual")
    crear_acta(inspector_a, escuela, ubicacion=None)

    mapa = datos()["mapa"]

    assert [p["numero"] for p in mapa["puntos"]] == [con_gps.numero]
    punto = mapa["puntos"][0]
    assert punto["constatada"] is False
    assert punto["cueanexo"] == escuela.cue
    assert punto["turno"] == "Tarde"
    assert punto["resultado"] == "No dejó ingresar"
    assert mapa["con_gps"] == 1
    assert mapa["manual"] == 1
    assert mapa["sin_ubicacion"] == 1
    assert mapa["sin_coordenadas"] == 2


def test_url_del_detalle_del_acta(inspector_a, escuela):
    acta = crear_acta(inspector_a, escuela)

    punto = datos()["mapa"]["puntos"][0]

    try:
        esperada = reverse("inspecciones_acta_detalle", args=[acta.numero])
    except NoReverseMatch:
        esperada = None  # La pantalla de detalle llega con el panel.
    assert punto["url"] == esperada


# ------------------------------------------------------------ filtros


def test_filtros_coinciden_en_indicadores_mapa_tabla_y_csv(
    inspector_a, inspector_b, geo
):
    _, localidad_a = geo["a"]
    provincia_b, _ = geo["b"]
    escuela_a = nueva_escuela("060000021", "a", geo)
    escuela_b = nueva_escuela("060000022", "b", geo)
    crear_acta(inspector_a, escuela_a, turno="manana")
    crear_acta(inspector_b, escuela_a, turno="tarde")
    crear_acta(
        inspector_a,
        escuela_b,
        turno="tarde",
        notificacion=Acta.EstadoNotificacion.CARGADA,
    )
    crear_acta(inspector_b, escuela_b, turno="noche")
    crear_acta(inspector_a, escuela_b, fecha=hoy() - timedelta(days=1))
    crear_acta(inspector_a, escuela_a, es_prueba=True)

    casos = [
        ({}, 4),
        ({"provincia": str(provincia_b.pk)}, 2),
        ({"localidad": str(localidad_a.pk)}, 2),
        ({"inspector": str(inspector_a.pk)}, 2),
        ({"turno": "tarde"}, 2),
        ({"notificacion": "cargada"}, 1),
        ({"provincia": str(provincia_b.pk), "turno": "tarde"}, 1),
        ({"fecha": (hoy() - timedelta(days=1)).isoformat()}, 1),
    ]
    for params, esperadas in casos:
        resultado = datos(**params)
        indicadores = set(a["numero"] for a in resultado["ultimas"])
        mapa = set(p["numero"] for p in resultado["mapa"]["puntos"])
        _, filas = numeros_csv(**params)
        en_csv = set(fila[0] for fila in filas)
        assert resultado["indicadores"]["actas_validas"] == esperadas, params
        assert indicadores == mapa == en_csv, params
        assert len(en_csv) == esperadas, params


def test_filtros_invalidos_se_ignoran():
    filtros = tablero.leer_filtros(
        {
            "fecha": "no-es-fecha",
            "provincia": "x",
            "turno": "siesta",
            "notificacion": "otra",
            "inspector": "-1",
        }
    )

    assert filtros == tablero.Filtros(fecha=hoy())


def test_localidades_de_la_provincia_con_actas(inspector_a, geo):
    provincia_a, localidad_a = geo["a"]
    crear_acta(inspector_a, nueva_escuela("060000031", "a", geo))
    crear_acta(inspector_a, nueva_escuela("060000032", "b", geo))

    assert datos()["opciones"]["localidades"] == []
    localidades = datos(provincia=str(provincia_a.pk))["opciones"]["localidades"]
    assert localidades == [
        {"id": localidad_a.pk, "nombre": "Localidad a · Municipio a"}
    ]


# ------------------------------------------------------------ cache


def test_cache_no_mezcla_combinaciones_de_filtros(inspector_a, geo):
    provincia_a, _ = geo["a"]
    crear_acta(inspector_a, nueva_escuela("060000041", "a", geo))
    crear_acta(inspector_a, nueva_escuela("060000042", "b", geo))
    todas = tablero.leer_filtros({})
    solo_a = tablero.leer_filtros({"provincia": str(provincia_a.pk)})

    assert tablero.datos_tablero(todas)["indicadores"]["actas_validas"] == 2
    assert tablero.datos_tablero(solo_a)["indicadores"]["actas_validas"] == 1
    assert tablero.datos_tablero(todas)["indicadores"]["actas_validas"] == 2

    # Dentro de los 5 segundos se sirve lo cacheado; vencido, se recalcula.
    crear_acta(inspector_a, nueva_escuela("060000043", "a", geo))
    assert tablero.datos_tablero(solo_a)["indicadores"]["actas_validas"] == 1
    cache.delete(f"{tablero.CACHE_PREFIJO}:{solo_a.clave()}")
    assert tablero.datos_tablero(solo_a)["indicadores"]["actas_validas"] == 2
    assert tablero.datos_tablero(todas)["indicadores"]["actas_validas"] == 2


def test_cache_dura_dos_segundos(monkeypatch, inspector_a, escuela):
    llamadas = []
    original = tablero.cache.set
    monkeypatch.setattr(
        tablero.cache,
        "set",
        lambda clave, valor, segundos: llamadas.append(segundos)
        or original(clave, valor, segundos),
    )

    tablero.datos_tablero(tablero.leer_filtros({}))

    assert llamadas == [tablero.CACHE_SEGUNDOS] == [2]


# ------------------------------------------------------------ eficiencia


def test_cantidad_de_consultas_no_depende_del_volumen(inspector_a, geo):
    def consultas():
        with CaptureQueriesContext(connection) as capturadas:
            tablero.calcular_tablero(tablero.leer_filtros({}))
        return len(capturadas)

    crear_acta(inspector_a, nueva_escuela("060000051", "a", geo))
    pocas = consultas()
    for indice in range(25):
        crear_acta(
            inspector_a,
            nueva_escuela(f"0600001{indice:02d}", "ab"[indice % 2], geo),
            ubicacion=("gps", "manual", None)[indice % 3],
        )
    assert consultas() == pocas
    assert pocas <= 10


# ------------------------------------------------------------ CSV

COLUMNAS_ESPERADAS = [
    "Número de acta",
    "Fecha de visita",
    "Cierre (hora oficial)",
    "Escuela",
    "Cueanexo",
    "Provincia",
    "Localidad",
    "Distrito",
    "Turno",
    "Inspector",
    "Resultado de la constatación",
    "Motivo de la constatación parcial",
    "Qué ocurrió (no dejó ingresar)",
    "F05 Abierta",
    "F06 Quién atiende: nombre y función/rol - nombre",
    "F06 Quién atiende: nombre y función/rol - función/rol",
    "F07 Hay personal educativo",
    "F08 Hay estudiantes",
    "F09 Cantidad de personal total de la escuela (docente y no docente) que "
    "debiera estar prestando servicio en ese momento",
    "F09 Cantidad de personal total de la escuela (docente y no docente) que "
    "debiera estar prestando servicio en ese momento - condición",
    "F10 Cantidad de personal total de la escuela (docente y no docente) que "
    "efectivamente está prestando servicio en ese momento - presentes",
    "F10 Cantidad de personal total de la escuela (docente y no docente) que "
    "efectivamente está prestando servicio en ese momento - presentes - condición",
    "F11 Cuántas aulas en total deberían estar funcionando en ese momento",
    "F11 Cuántas aulas en total deberían estar funcionando en ese momento - condición",
    "F12 Cuántas aulas en total están efectivamente funcionando",
    "F12 Cuántas aulas en total están efectivamente funcionando - condición",
    "F13 No se pudo constatar porque la escuela estaba cerrada",
    "F14 No se pudo constatar porque la escuela no dejó ingresar",
    "F15 Imágenes adicionales (cantidad)",
    "F16 Observaciones",
    "Firma",
    "Motivo de la excepción de firma",
    "Notificación",
    "Condición de firma de la notificación",
]


def test_csv_columnas_estables_y_sin_datos_de_firma(inspector_a, geo):
    escuela = nueva_escuela("060000061", "a", geo)
    firmada = crear_acta(inspector_a, escuela, firma_tipo="firma")
    excepcion = crear_acta(
        inspector_a,
        escuela,
        motivo_firma="ausente",
        f10=cantidad(None, "no_constatado"),
        notificacion=Acta.EstadoNotificacion.CARGADA,
    )
    NotificacionPapel.objects.create(
        uuid=uuid.uuid4(),
        acta=excepcion,
        version=1,
        cargada_por=inspector_a,
        notificada_at=timezone.now(),
        receptor_nombre="Ana",
        receptor_cargo="Directora",
        condicion_firma=NotificacionPapel.CondicionFirma.NEGATIVA,
        motivo="No quiso",
        numero_confirmado=excepcion.numero,
    )

    vacio, sin_filas = numeros_csv(fecha="2000-01-01")
    columnas, filas = numeros_csv()

    assert columnas == COLUMNAS_ESPERADAS
    assert vacio == COLUMNAS_ESPERADAS and sin_filas == []
    assert all(len(fila) == len(COLUMNAS_ESPERADAS) for fila in filas)
    por_numero = {fila[0]: dict(zip(columnas, fila)) for fila in filas}
    fila_firmada = por_numero[firmada.numero]
    assert fila_firmada["Firma"] == "Firmada"
    assert fila_firmada["Motivo de la excepción de firma"] == ""
    assert fila_firmada["Cueanexo"] == "060000061"
    assert fila_firmada["Provincia"] == "Provincia tablero a"
    assert fila_firmada["Localidad"] == "Localidad a"
    assert fila_firmada["Turno"] == "Tarde"
    assert fila_firmada["F05 Abierta"] == "Sí"
    assert fila_firmada["F15 Imágenes adicionales (cantidad)"] == "1"
    assert fila_firmada["Notificación"] == "Pendiente"
    # Neutraliza fórmulas.
    assert fila_firmada["F16 Observaciones"] == "'=HIPERVINCULO(1)"
    fila_excepcion = por_numero[excepcion.numero]
    assert fila_excepcion["Firma"] == "Excepción"
    assert fila_excepcion["Motivo de la excepción de firma"] == (
        "No había nadie para firmar"
    )
    assert fila_excepcion["Notificación"] == "Cargada"
    assert fila_excepcion["Condición de firma de la notificación"] == (
        "Negativa a firmar"
    )
    f10 = COLUMNAS_ESPERADAS[20]
    assert fila_excepcion[f10] == ""
    assert fila_excepcion[f10 + " - condición"] == "No constatado"

    salida = io.StringIO()
    tablero.escribir_csv(salida, tablero.leer_filtros({}))
    contenido = salida.getvalue()
    firma_uuid = firmada.instantanea["payload"]["firma"]["imagen_uuid"]
    assert firma_uuid not in contenido
    assert "imagen" not in contenido.split("\n", 1)[1].lower()
    assert "http" not in contenido.lower()
    assert "/inspecciones/" not in contenido


# ------------------------------------------------------------ vistas


@pytest.mark.parametrize("url", [URL_PAGINA, URL_DATOS, URL_CSV])
def test_rutas_exigen_permiso(client, inspector_a, url):
    assert client.get(url).status_code == 302  # sin sesión: al login

    client.force_login(inspector_a)

    assert client.get(url).status_code == 403


def test_rutas_con_nombre():
    assert reverse("inspecciones_tablero") == URL_PAGINA
    assert reverse("inspecciones_tablero_datos") == URL_DATOS
    assert reverse("inspecciones_tablero_exportar") == URL_CSV


def test_endpoint_json_para_coordinacion(client, coordinacion, inspector_a, escuela):
    acta = crear_acta(inspector_a, escuela)
    client.force_login(coordinacion)

    response = client.get(URL_DATOS, {"turno": "tarde"})

    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    cuerpo = response.json()
    assert cuerpo["generado_at"].endswith("-03:00")
    assert cuerpo["filtros"]["turno"] == "tarde"
    assert cuerpo["indicadores"]["actas_validas"] == 1
    assert cuerpo["ultimas"][0]["numero"] == acta.numero
    assert set(cuerpo) >= {
        "indicadores",
        "turnos",
        "resultados",
        "ausentismo",
        "aulas",
        "presencia",
        "mapa",
        "ultimas",
        "generado_at",
    }


def test_exportar_csv_para_coordinacion(client, coordinacion, inspector_a, escuela):
    crear_acta(inspector_a, escuela)
    client.force_login(coordinacion)

    response = client.get(URL_CSV)

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    assert f"inspecciones-actas-{hoy().isoformat()}.csv" in (
        response["Content-Disposition"]
    )
    texto = response.content.decode("utf-8")
    assert texto.startswith("﻿Número de acta;")


def _hay_pestanas():
    try:
        get_template("inspecciones/_pestanas.html")
    except TemplateDoesNotExist:
        return False
    return True


@pytest.mark.skipif(
    not _hay_pestanas(), reason="El parcial de pestañas llega con el panel."
)
def test_pagina_del_tablero(client, coordinacion, geo):
    provincia_a, _ = geo["a"]
    client.force_login(coordinacion)

    response = client.get(URL_PAGINA, {"provincia": provincia_a.pk})

    assert response.status_code == 200
    html = response.content.decode()
    assert 'data-url-datos="/inspecciones/tablero/datos/"' in html
    assert "leaflet@1.9.4/dist/leaflet.js" in html
    assert "leaflet.markercluster@1.5.3" in html
    assert "no equivale a adhesión al paro" in html
    assert response.context["filtros"].provincia == provincia_a.pk


# ------------------------------------------------------------ volumen


@pytest.mark.skipif(
    not os.environ.get("INSPECCIONES_TABLERO_VOLUMEN"),
    reason="Prueba de volumen: INSPECCIONES_TABLERO_VOLUMEN=1 para correrla.",
)
def test_volumen_64000_escuelas_y_1000_actas(client, coordinacion, inspector_a, geo):
    provincia_a, localidad_a = geo["a"]
    Escuela.objects.bulk_create(
        [
            Escuela(
                codigo=f"9{numero:08d}",
                cue=f"9{numero:08d}",
                nombre=f"Escuela {numero}",
                provincia=provincia_a,
                localidad_vinculada=localidad_a,
            )
            for numero in range(64_000)
        ],
        batch_size=2000,
    )
    escuelas = list(Escuela.objects.order_by("id").values_list("id", flat=True)[:900])
    Inspeccion.objects.bulk_create(
        [
            Inspeccion(
                uuid=uuid.uuid4(),
                inspector=inspector_a,
                estado=Inspeccion.Estado.FINALIZADA,
                revision=1,
                escuela_id=escuelas[i % len(escuelas)],
                fecha_visita=hoy(),
                turno="tarde",
                resultado="constatado",
            )
            for i in range(1000)
        ],
        batch_size=500,
    )
    # MySQL no devuelve los ids de bulk_create: se releen.
    inspecciones = list(Inspeccion.objects.filter(revision=1).order_by("id"))
    plantilla = crear_acta(inspector_a, None).instantanea
    Acta.objects.all().delete()
    ahora = timezone.now()
    Acta.objects.bulk_create(
        [
            Acta(
                inspeccion=inspeccion,
                inspector=inspector_a,
                escuela_id=inspeccion.escuela_id,
                numero=f"ACTA-2027-{i:06d}",
                anio=2027,
                secuencia=i,
                cerrada_at=ahora - timedelta(seconds=i),
                fecha_visita=hoy(),
                turno="tarde",
                resultado="constatado",
                firma_tipo="excepcion",
                instantanea=plantilla,
                instantanea_sha256="0" * 64,
            )
            for i, inspeccion in enumerate(inspecciones, start=1)
        ],
        batch_size=500,
    )
    client.force_login(coordinacion)

    inicio = time.perf_counter()
    response = client.get(URL_DATOS)
    segundos = time.perf_counter() - inicio
    inicio = time.perf_counter()
    client.get(URL_DATOS)
    cacheada = time.perf_counter() - inicio
    inicio = time.perf_counter()
    exportado = client.get(URL_CSV)
    csv_segundos = time.perf_counter() - inicio
    # El cliente de pruebas reinicia el registro de consultas en cada pedido:
    # se cuentan llamando al servicio directamente.
    with CaptureQueriesContext(connection) as capturadas:
        tablero.calcular_tablero(tablero.leer_filtros({}))

    assert response.status_code == 200
    assert exportado.status_code == 200
    cuerpo = response.json()
    assert cuerpo["indicadores"]["actas_validas"] == 1000
    assert cuerpo["indicadores"]["escuelas_unicas"] == 900
    assert len(cuerpo["mapa"]["puntos"]) == 1000
    assert len(capturadas) <= 10
    print(
        f"\n[volumen] {connection.vendor}: datos {segundos * 1000:.0f} ms "
        f"({len(response.content) // 1024} KiB), cacheada {cacheada * 1000:.0f} ms, "
        f"{len(capturadas)} consultas; CSV {csv_segundos * 1000:.0f} ms "
        f"({len(exportado.content) // 1024} KiB)"
    )
