"""Retorno SINTyS: lectura, alertas propuestas y gestión (Confirmar / Modificar)."""

import io
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from openpyxl import Workbook, load_workbook

from core.models import Municipio, Provincia
from pas.forms import PasCambioEstadoForm
from pas.models import (
    PasAviso,
    PasCircuitoMensual,
    PasEstado,
    PasHistorialEstado,
    PasIncompatibilidad,
    PasPersona,
)
from pas.services.cruces_service import (
    COLUMNAS_ENVIO_SINTYS,
    confirmar_incompatibilidad,
    generar_nomina_sintys_pas,
    incompatibilidades_pendientes,
    leer_retorno_sintys,
    mensaje_importacion,
    modificar_incompatibilidad,
    obtener_circuito_actual,
    procesar_retorno_sintys,
    registrar_importacion_sintys,
)
from pas.services.supervivencia_service import aplicar_bajas_fallecimiento_pendientes

pytestmark = pytest.mark.django_db

# Retorno SINTyS con datos sinteticos para los cinco casos de prueba.
RETORNO_EJEMPLO = (
    "ID|APELLIDO|NOMBRE|NDOC|CUIT_TXT|EVALUACION|MOTIVO\n"
    "900001|PRUEBA UNO|TITULAR|99000001|20990000010|COMPATIBLE|\n"
    "900002|PRUEBA DOS|TITULAR DE PRUEBA|99000002|20990000020|INCOMPATIBLE|PENSION NO CONTRIBUTIVA\n"
    "900003|PRUEBA TRES|TITULAR DE PRUEBA|99000003|27990000030|INCOMPATIBLE|JUBILACION / PENSION\n"
    "900004|PRUEBA CUATRO|Titular|99000004|20990000040|RENUNCIA|\n"
    "900005|PRUEBA CINCO|TITULAR DE PRUEBA|99000005|23990000050|FALLECIDO|\n"
)


@pytest.fixture(name="catalogo")
def catalogo_fixture():
    estados = {
        nombre: PasEstado.objects.get_or_create(nombre=nombre)[0]
        for nombre in ("Activo", "Suspendido", "Baja")
    }
    avisos = {}
    for codigo, descripcion, nombres in (
        (1, "100%", ["Activo"]),
        (10, "INCOMPATIBLE", ["Suspendido", "Baja"]),
        (39, "RENUNCIA", ["Baja"]),
        (40, "FALLECIDO", ["Baja"]),
    ):
        aviso = PasAviso.objects.get_or_create(
            codigo=codigo, defaults={"descripcion": descripcion}
        )[0]
        aviso.estados.add(*(estados[nombre] for nombre in nombres))
        avisos[codigo] = aviso
    return estados, avisos


@pytest.fixture(name="ubicacion")
def ubicacion_fixture():
    provincia = Provincia.objects.create(nombre="Provincia SINTyS")
    return provincia, Municipio.objects.create(
        nombre="Municipio SINTyS", provincia=provincia
    )


@pytest.fixture(name="usuario")
def usuario_fixture():
    return get_user_model().objects.create_user("operador-sintys")


def _persona(ubicacion, catalogo, id_persona, dni, estado="Activo", avisos=(1,)):
    estados, catalogo_avisos = catalogo
    persona = PasPersona.objects.create(
        id_persona=id_persona,
        apellidos=f"Apellido {id_persona}",
        nombres="Nombre",
        dni=dni,
        cuit=f"20{dni}9",
        provincia=ubicacion[0],
        municipio=ubicacion[1],
        estado=estados[estado],
    )
    persona.avisos.set([catalogo_avisos[codigo] for codigo in avisos])
    return persona


@pytest.fixture(name="padron")
def padron_fixture(ubicacion, catalogo):
    return {
        "compatible": _persona(ubicacion, catalogo, 900001, 99000001),
        "pension": _persona(ubicacion, catalogo, 900002, 99000002),
        "jubilacion": _persona(ubicacion, catalogo, 900003, 99000003),
        "renuncia": _persona(ubicacion, catalogo, 900004, 99000004),
        "fallecido": _persona(ubicacion, catalogo, 900005, 99000005),
    }


def _archivo(texto, nombre="retorno.txt", encoding="utf-8"):
    return SimpleUploadedFile(nombre, texto.encode(encoding))


def _circuito():
    return obtener_circuito_actual(crear=True)


def test_lee_el_formato_txt_del_ejemplo():
    filas = leer_retorno_sintys(_archivo(RETORNO_EJEMPLO))

    assert len(filas) == 5
    assert filas[1]["ID"] == "900002"
    assert filas[1]["EVALUACION"] == "INCOMPATIBLE"
    assert filas[1]["MOTIVO"] == "PENSION NO CONTRIBUTIVA"
    assert filas[1]["linea"] == 3


def test_lee_xlsx_y_texto_latin1():
    workbook = Workbook()
    workbook.active.append(
        ["ID", "APELLIDO", "NOMBRE", "NDOC", "CUIT_TXT", "EVALUACION", "MOTIVO"]
    )
    workbook.active.append(
        [900001.0, "PRUEBA UNO", "TITULAR", 99000001, "x", "FALLECIDO", None]
    )
    contenido = io.BytesIO()
    workbook.save(contenido)

    filas_xlsx = leer_retorno_sintys(
        SimpleUploadedFile("retorno.xlsx", contenido.getvalue())
    )
    filas_latin = leer_retorno_sintys(
        _archivo(
            "ID;APELLIDO;NOMBRE;NDOC;CUIT_TXT;EVALUACION;MOTIVO\n"
            "1;PEÑA;ANA;2;3;INCOMPATIBLE;MAYOR DE 65 AÑOS\n",
            nombre="retorno.csv",
            encoding="cp1252",
        )
    )

    assert filas_xlsx[0]["ID"] == "900001"
    assert filas_xlsx[0]["MOTIVO"] == ""
    assert filas_latin[0]["APELLIDO"] == "PEÑA"
    assert filas_latin[0]["MOTIVO"] == "MAYOR DE 65 AÑOS"


@pytest.mark.parametrize(
    ("contenido", "nombre", "mensaje"),
    [
        ("", "retorno.txt", "vacío"),
        ("numero_cuil,resultado\n1,OK\n", "retorno.csv", "Faltan las columnas"),
        ("no es un xlsx", "retorno.xlsx", "No se pudo leer"),
    ],
)
def test_rechaza_formatos_invalidos(contenido, nombre, mensaje):
    with pytest.raises(ValidationError, match=mensaje):
        leer_retorno_sintys(_archivo(contenido, nombre=nombre))


def test_genera_alertas_solo_para_los_que_cambian(padron, catalogo):
    estados, avisos = catalogo
    circuito = _circuito()

    resumen = procesar_retorno_sintys(
        circuito, leer_retorno_sintys(_archivo(RETORNO_EJEMPLO))
    )

    assert resumen == {
        "total": 5,
        "compatibles": 1,
        "alertas": 4,
        "sin_cambios": 0,
        "ya_gestionadas": 0,
        "errores": [],
    }
    alertas = {
        alerta.persona_id: alerta
        for alerta in PasIncompatibilidad.objects.filter(origen="sintys")
    }
    assert padron["compatible"].pk not in alertas
    pension = alertas[padron["pension"].pk]
    assert pension.categoria == PasIncompatibilidad.Categoria.INGRESOS
    assert pension.detalle == "PENSION NO CONTRIBUTIVA"
    assert pension.estado_propuesto == estados["Suspendido"]
    assert pension.aviso_propuesto == avisos[10]
    assert pension.periodo_impacto == circuito.periodo
    assert alertas[padron["renuncia"].pk].estado_propuesto == estados["Baja"]
    assert alertas[padron["renuncia"].pk].aviso_propuesto == avisos[39]
    assert alertas[padron["renuncia"].pk].detalle == "Renuncia"
    fallecido = alertas[padron["fallecido"].pk]
    assert fallecido.categoria == PasIncompatibilidad.Categoria.SUPERVIVENCIA
    assert fallecido.aviso_propuesto == avisos[40]
    # Ningún titular cambia de estado hasta que el operador gestiona la alerta.
    assert set(PasPersona.objects.values_list("estado__nombre", flat=True)) == {
        "Activo"
    }


def test_patrimonio_y_casos_sin_cambio_o_con_errores(ubicacion, catalogo):
    _persona(ubicacion, catalogo, 1, 1001)
    _persona(ubicacion, catalogo, 2, 1002, estado="Suspendido", avisos=(10,))
    _persona(ubicacion, catalogo, 3, 1003, estado="Baja", avisos=(39,))
    texto = (
        "ID|APELLIDO|NOMBRE|NDOC|CUIT_TXT|EVALUACION|MOTIVO\n"
        "2|X|X|1001|x|INCOMPATIBLE|AUTOMOTORES\n"
        "2|X|X|1002|x|INCOMPATIBLE|JUBILACION\n"
        "3|X|X|1003|x|RENUNCIA|\n"
        "4|X|X|1004|x|FALLECIDO|\n"
        "1|X|X|1001|x|OBSERVADO|\n"
    )

    resumen = procesar_retorno_sintys(_circuito(), leer_retorno_sintys(_archivo(texto)))

    assert resumen["alertas"] == 1
    assert resumen["sin_cambios"] == 2
    assert resumen["errores"] == [
        "Línea 5: titular no encontrado (ID 4, DNI 1004).",
        "Línea 6: evaluación desconocida «OBSERVADO».",
    ]
    alerta = PasIncompatibilidad.objects.get()
    assert alerta.persona.dni == 1001
    assert alerta.categoria == PasIncompatibilidad.Categoria.PATRIMONIO


def test_reimportar_reemplaza_pendientes_y_no_reabre_confirmadas(padron, usuario):
    circuito = _circuito()
    procesar_retorno_sintys(circuito, leer_retorno_sintys(_archivo(RETORNO_EJEMPLO)))
    confirmar_incompatibilidad(
        PasIncompatibilidad.objects.get(persona=padron["pension"]), usuario
    )

    resumen = procesar_retorno_sintys(
        circuito, leer_retorno_sintys(_archivo(RETORNO_EJEMPLO))
    )

    assert resumen["alertas"] == 3
    assert resumen["sin_cambios"] == 1  # la pensión ya quedó suspendida
    assert PasIncompatibilidad.objects.filter(origen="sintys").count() == 4
    assert (
        PasIncompatibilidad.objects.filter(estado="pendiente", origen="sintys").count()
        == 3
    )


def test_registrar_importacion_guarda_resumen_y_no_guarda_si_falla(
    padron, usuario, tmp_path
):
    circuito = _circuito()
    with override_settings(MEDIA_ROOT=tmp_path):
        with pytest.raises(ValidationError):
            registrar_importacion_sintys(circuito, _archivo("A|B\n1|2\n"), usuario)
        circuito.refresh_from_db()
        assert circuito.fecha_importacion_sintys is None

        resumen = registrar_importacion_sintys(
            circuito, _archivo(RETORNO_EJEMPLO), usuario
        )

    circuito.refresh_from_db()
    assert circuito.resultado_importacion_sintys == resumen
    assert circuito.importado_por == usuario
    assert circuito.fecha_procesamiento_alertas is None
    assert mensaje_importacion(resumen) == (
        "Retorno SINTyS procesado: 5 registros, 4 alertas nuevas, "
        "1 compatibles, 0 sin cambios."
    )
    assert mensaje_importacion(
        {**resumen, "ya_gestionadas": 2, "errores": ["x"]}
    ).endswith("2 ya estaban confirmadas. 1 filas con observaciones.")


def test_confirmar_aplica_el_cambio_y_completa_el_procesamiento(
    padron, usuario, catalogo, tmp_path
):
    estados, avisos = catalogo
    circuito = _circuito()
    with override_settings(MEDIA_ROOT=tmp_path):
        registrar_importacion_sintys(circuito, _archivo(RETORNO_EJEMPLO), usuario)

    for alerta in list(incompatibilidades_pendientes()):
        confirmar_incompatibilidad(alerta, usuario)

    pension = PasPersona.objects.get(pk=padron["pension"].pk)
    assert pension.estado == estados["Suspendido"]
    assert list(pension.avisos.all()) == [avisos[10]]
    historial = PasHistorialEstado.objects.get(persona=pension)
    assert historial.estado_anterior == estados["Activo"]
    assert historial.usuario == usuario
    alerta = PasIncompatibilidad.objects.get(persona=pension)
    assert alerta.estado == PasIncompatibilidad.Estado.CONFIRMADA
    assert alerta.gestionada_por == usuario
    assert alerta.fecha_gestion is not None
    assert PasPersona.objects.get(pk=padron["fallecido"].pk).estado == estados["Baja"]
    circuito.refresh_from_db()
    assert circuito.fecha_procesamiento_alertas is not None
    with pytest.raises(ValueError):
        confirmar_incompatibilidad(alerta, usuario)


def test_confirmar_sin_cambio_pendiente_solo_marca_la_alerta(padron, usuario):
    procesar_retorno_sintys(_circuito(), leer_retorno_sintys(_archivo(RETORNO_EJEMPLO)))
    alerta = PasIncompatibilidad.objects.get(persona=padron["pension"])
    alerta.estado_propuesto = None
    alerta.save(update_fields=["estado_propuesto"])

    confirmar_incompatibilidad(alerta, usuario)

    assert not PasHistorialEstado.objects.exists()
    alerta.refresh_from_db()
    assert alerta.estado == PasIncompatibilidad.Estado.CONFIRMADA


def test_modificar_aplica_el_estado_elegido_y_confirma(padron, usuario, catalogo):
    estados, avisos = catalogo
    procesar_retorno_sintys(_circuito(), leer_retorno_sintys(_archivo(RETORNO_EJEMPLO)))
    alerta = PasIncompatibilidad.objects.get(persona=padron["renuncia"])
    form = PasCambioEstadoForm(
        {"estado": estados["Suspendido"].pk, "avisos": [avisos[10].pk]}
    )
    assert form.is_valid()

    modificar_incompatibilidad(alerta, form, usuario)

    persona = PasPersona.objects.get(pk=padron["renuncia"].pk)
    assert persona.estado == estados["Suspendido"]
    alerta.refresh_from_db()
    assert alerta.estado == PasIncompatibilidad.Estado.CONFIRMADA
    with pytest.raises(ValueError):
        modificar_incompatibilidad(alerta, form, usuario)


def test_la_baja_automatica_renaper_no_toma_alertas_sintys(padron, catalogo):
    estados, _ = catalogo
    procesar_retorno_sintys(_circuito(), leer_retorno_sintys(_archivo(RETORNO_EJEMPLO)))

    resultado = aplicar_bajas_fallecimiento_pendientes(date(2100, 1, 1))

    assert resultado == {"actualizadas": 0, "ya_aplicadas": 0}
    assert PasPersona.objects.get(pk=padron["fallecido"].pk).estado == estados["Activo"]
    assert (
        PasIncompatibilidad.objects.get(persona=padron["fallecido"]).estado
        == PasIncompatibilidad.Estado.PENDIENTE
    )


def test_exportacion_sintys_usa_el_formato_de_envio_sin_bajas(ubicacion, catalogo):
    activo = _persona(ubicacion, catalogo, 1, 1001)
    activo.genero = "F"
    activo.calle = "=Av. Siempreviva"
    activo.altura = "742"
    activo.telefono_celular = "1155550000"
    activo.correo_electronico = "ana@example.com"
    activo.save()
    _persona(ubicacion, catalogo, 2, 1002, estado="Suspendido", avisos=(10,))
    _persona(ubicacion, catalogo, 3, 1003, estado="Baja", avisos=(39,))

    filas = list(
        load_workbook(io.BytesIO(generar_nomina_sintys_pas()), read_only=True)[
            "nomina"
        ].iter_rows(values_only=True)
    )

    assert filas[0] == COLUMNAS_ENVIO_SINTYS
    assert len(filas[0]) == 41
    datos = [dict(zip(COLUMNAS_ENVIO_SINTYS, fila)) for fila in filas[1:]]
    assert [fila["ID_ORIG"] for fila in datos] == ["1", "2"]
    activo = datos[0]
    assert activo["PROG"] == "PAS"
    assert activo["NDOC_ORIG"] == 1001
    assert activo["CUIT_ORIG"] == 2010019
    assert activo["SEXO_ORIG"] == "F"
    assert activo["ESTADO"] == "Activo"
    assert activo["MONTO_ORIG"] == "78000.00"
    assert activo["CALLE"] == "'=Av. Siempreviva"
    assert activo["NUMERO"] == "742"
    assert activo["LOCALIDAD"] == "Municipio SINTyS"
    assert activo["PROV_ORIG"] == "Provincia SINTyS"
    assert activo["TELCELULAR"] == "1155550000"
    assert activo["EMAIL"] == "ana@example.com"
    llenas = {
        "PROG",
        "ID_ORIG",
        "NOMBRE_ORIG",
        "APELLIDO_ORIG",
        "NDOC_ORIG",
        "CUIT_ORIG",
        "SEXO_ORIG",
        "ESTADO",
        "MONTO_ORIG",
        "CALLE",
        "NUMERO",
        "LOCALIDAD",
        "PROV_ORIG",
        "TELCELULAR",
        "EMAIL",
    }
    assert all(valor is None for clave, valor in activo.items() if clave not in llenas)
    assert datos[1]["ESTADO"] == "Suspendido"
    assert datos[1]["MONTO_ORIG"] is None
    assert datos[1]["SEXO_ORIG"] is None
    assert not PasCircuitoMensual.objects.exists()
