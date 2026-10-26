"""Importación del padrón de escuelas (.xlsx/.csv) y el flujo de tres pasos."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from inspecciones.models import Escuela
from inspecciones.services.importacion_escuelas import (
    aplicar_escuelas,
    analizar_escuelas,
    mail_valido,
)
from inspecciones.services.subidas import DIRECTORIO
from inspecciones.storage import almacenamiento_privado

pytestmark = pytest.mark.django_db

ENCABEZADO = (
    "Jurisdicción",
    "Localidad",
    "Cueanexo",
    "Nombre",
    "Domicilio",
    "C. P.",
    "Teléfono",
    "Mail",
)


def _fila(
    jurisdiccion="Buenos Aires",
    localidad="SAN JUSTO",
    cueanexo="060123400",
    nombre="EP N° 12",
    mail="ep12@abc.gob.ar",
):
    return (
        jurisdiccion,
        localidad,
        cueanexo,
        nombre,
        "AV. PERON  3245 ",
        "B1754ABC",
        "011 4651-2233",
        mail,
    )


def _importar(planilla, filas, **kwargs):
    archivo = planilla([ENCABEZADO, *filas], **kwargs)
    analisis = analizar_escuelas(archivo)
    return analisis, aplicar_escuelas(analisis["datos"])


def test_localidad_unica_se_vincula_y_conserva_ceros(planilla, geografia):
    _analisis, (resumen, _obs) = _importar(planilla, [_fila()])

    escuela = Escuela.objects.get()
    assert resumen["nuevas_sin_observaciones"] == 1
    assert escuela.codigo == escuela.cue == "060123400"
    assert escuela.provincia == geografia["bsas"]
    assert escuela.localidad_vinculada == geografia["san_justo"]
    assert escuela.localidad == "San Justo"
    assert escuela.distrito == "La Matanza"
    assert escuela.localidad_original == "SAN JUSTO"
    assert escuela.domicilio == "AV. PERON 3245"
    assert escuela.cp == "B1754ABC"
    assert escuela.a_revisar is False


def test_celda_numerica_recupera_los_ceros_iniciales(planilla, geografia):
    _importar(planilla, [_fila(cueanexo=20000100, localidad="San Justo")])

    assert Escuela.objects.get().cueanexo == "020000100"


def test_localidad_repetida_e_inexistente_quedan_a_revisar(planilla, geografia):
    analisis, _ = _importar(
        planilla,
        [
            _fila(localidad="SAN JOSE", cueanexo="060000001"),
            _fila(localidad="VILLA INVENTADA", cueanexo="060000002"),
        ],
    )

    repetida = Escuela.objects.get(codigo="060000001")
    inexistente = Escuela.objects.get(codigo="060000002")
    assert repetida.localidad_vinculada is None
    assert repetida.motivos_revision == ["localidad_repetida"]
    assert repetida.localidad == "SAN JOSE"
    assert inexistente.motivos_revision == ["localidad_inexistente"]
    assert inexistente.a_revisar is True
    resumen = analisis["resumen"]
    assert resumen["a_revisar"] == 2
    assert {m["codigo"]: m["cantidad"] for m in resumen["motivos"]} == {
        "localidad_repetida": 1,
        "localidad_inexistente": 1,
    }
    detalles = [o["detalle"] for o in analisis["observaciones"]]
    assert "SAN JOSE: está en 2 municipios de Buenos Aires" in detalles


def test_equivalencias_de_provincia_y_caba(planilla, geografia):
    analisis, _ = _importar(
        planilla,
        [
            _fila("Ciudad de Buenos Aires", "CIUDAD DE BUENOS AIRES", "020000100"),
            _fila("Tierra del Fuego", "USHUAIA", "940000100"),
        ],
    )

    caba = Escuela.objects.get(codigo="020000100")
    assert caba.provincia == geografia["caba"]
    # La genérica de la ciudad, no la homónima del padrón.
    assert caba.localidad_vinculada == geografia["caba_generica"]
    assert caba.distrito == "Ciudad Autónoma de Buenos Aires"
    assert caba.jurisdiccion_original == "Ciudad de Buenos Aires"
    tdf = Escuela.objects.get(codigo="940000100")
    assert tdf.provincia == geografia["tdf"]
    assert tdf.localidad_vinculada == geografia["ushuaia"]
    assert {e["desde"] for e in analisis["resumen"]["equivalencias"]} == {
        "Ciudad de Buenos Aires",
        "Tierra del Fuego",
    }


def test_mail_invalido_se_guarda_y_marca(planilla, geografia):
    _importar(planilla, [_fila(mail="ep7castelar@")])

    escuela = Escuela.objects.get()
    assert escuela.mail == "ep7castelar@"
    assert escuela.motivos_revision == ["mail_invalido"]


def test_varios_mails_validos_no_marcan():
    assert mail_valido("A@X.COM / b@y.com.ar")
    assert mail_valido("")
    assert not mail_valido("a@x.com / roto@")


def test_filas_rechazadas(planilla, geografia):
    analisis, (resumen, _) = _importar(
        planilla,
        [
            _fila(cueanexo="06-0123"),
            _fila(cueanexo="0601234"),
            _fila(nombre=""),
            _fila(jurisdiccion="Atlántida"),
            _fila(),
            _fila(),
        ],
    )

    assert resumen["rechazadas"] == 5
    causas = [o["detalle"] for o in analisis["observaciones"]]
    assert any("lleva 9 dígitos" in c for c in causas)
    assert any("Falta el nombre" in c for c in causas)
    assert any("Jurisdicción desconocida" in c for c in causas)
    assert any("repetido en el archivo" in c for c in causas)
    assert Escuela.objects.count() == 1


def test_reimportar_actualiza_sin_duplicar(planilla, geografia):
    _importar(planilla, [_fila(), _fila(localidad="SAN JOSE", cueanexo="060000001")])
    cambiada = list(_fila())
    cambiada[4] = "AV. PERON 3300"

    analisis, (resumen, _) = _importar(
        planilla, [cambiada, _fila(localidad="SAN JOSE", cueanexo="060000001")]
    )

    assert analisis["resumen"]["actualizadas_sin_observaciones"] == 1
    assert resumen["nuevas"] == 0
    assert Escuela.objects.count() == 2
    assert Escuela.objects.get(codigo="060123400").domicilio == "AV. PERON 3300"


def test_reimportar_conserva_localidad_corregida_a_mano(planilla, geografia):
    _importar(planilla, [_fila(localidad="SAN JOSE")])
    escuela = Escuela.objects.get()
    escuela.localidad_vinculada = geografia["san_jose_lomas"]
    escuela.localidad, escuela.distrito = "San José", "Lomas de Zamora"
    escuela.a_revisar, escuela.motivos_revision = False, []
    escuela.save()

    _importar(planilla, [_fila(localidad="SAN JOSE")])

    escuela.refresh_from_db()
    assert escuela.localidad_vinculada == geografia["san_jose_lomas"]
    assert escuela.a_revisar is False


def test_reimportar_no_cambia_el_codigo_de_una_escuela_vieja(planilla, geografia):
    vieja = Escuela.objects.create(codigo="E-12", cue="060123400", nombre="EP 12")

    _importar(planilla, [_fila()])

    vieja.refresh_from_db()
    assert Escuela.objects.count() == 1
    assert vieja.codigo == "E-12"
    assert vieja.provincia == geografia["bsas"]


def test_csv_y_encabezado_tras_filas_de_titulo(planilla, geografia):
    archivo = planilla(
        [("Padrón",), ENCABEZADO, _fila()], nombre="padron.csv", titulo=False
    )

    analisis = analizar_escuelas(archivo)

    assert analisis["resumen"]["fila_encabezado"] == 2
    assert analisis["resumen"]["nuevas"] == 1


def test_solo_lee_la_primera_hoja(planilla, geografia):
    analisis = analizar_escuelas(planilla([ENCABEZADO, _fila()]))

    assert analisis["resumen"]["total"] == 1
    assert "999999999" not in str(analisis)


def test_faltan_columnas_obligatorias(planilla, geografia):
    with pytest.raises(ValidationError, match="Cueanexo|cueanexo"):
        analizar_escuelas(planilla([("Jurisdicción", "Localidad", "Nombre")]))


def test_flujo_de_tres_pasos_con_archivo_privado(panel, planilla, geografia):
    archivo = planilla([ENCABEZADO, _fila(), _fila(mail="roto@")])

    respuesta = panel.post(
        reverse("inspecciones_importar_escuelas"), {"archivo": archivo}
    )

    assert respuesta.status_code == 302
    token = respuesta["Location"].rstrip("/").rsplit("/", 1)[-1]
    almacenamiento = almacenamiento_privado()
    assert almacenamiento.exists(f"{DIRECTORIO}/escuelas/{token}/archivo.xlsx")
    revision = panel.get(respuesta["Location"])
    assert revision.status_code == 200
    assert revision.context["resumen"]["a_importar"] == 1
    assert Escuela.objects.count() == 0
    csv = panel.get(
        reverse("inspecciones_importar_escuelas_observaciones", args=[token])
    )
    assert "repetido en el archivo" in csv.content.decode("utf-8")

    resultado = panel.post(
        reverse("inspecciones_importar_escuelas_confirmar", args=[token])
    )

    assert resultado.status_code == 200
    assert Escuela.objects.count() == 1
    assert not almacenamiento.exists(f"{DIRECTORIO}/escuelas/{token}/archivo.xlsx")
    vencida = panel.post(
        reverse("inspecciones_importar_escuelas_confirmar", args=[token])
    )
    assert vencida.status_code == 302


def test_el_token_es_del_usuario_que_subio(
    panel, planilla, geografia, coordinacion, client
):
    respuesta = panel.post(
        reverse("inspecciones_importar_escuelas"),
        {"archivo": planilla([ENCABEZADO, _fila()])},
    )
    token = respuesta["Location"].rstrip("/").rsplit("/", 1)[-1]
    client.force_login(coordinacion)

    ajena = client.post(
        reverse("inspecciones_importar_escuelas_confirmar", args=[token])
    )

    assert ajena.status_code == 302
    assert Escuela.objects.count() == 0


def test_archivo_ilegible_muestra_el_error(panel, geografia):
    from django.core.files.uploadedfile import SimpleUploadedFile

    respuesta = panel.post(
        reverse("inspecciones_importar_escuelas"),
        {"archivo": SimpleUploadedFile("padron.xlsx", b"no es un zip")},
    )

    assert respuesta.status_code == 200
    assert "no es un Excel" in respuesta.content.decode()
