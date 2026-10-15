"""Validación del formulario v1 en el servidor (mismas reglas que la app)."""

import copy

import pytest

from inspecciones.services.validacion import advertencias, validar_inspeccion


@pytest.fixture
def valido(payload):
    return payload(None)


def _validar(p, **kwargs):
    return validar_inspeccion(p, **kwargs)


def test_el_payload_de_referencia_es_valido(valido):
    assert _validar(valido) == {}


def test_escuela_cerrada_no_exige_los_campos_interiores_ni_los_vuelve_cero(valido):
    r = valido["respuestas"]
    r.update(f05="no", resultado="cerrada", f07=None, f08=None)
    for clave in ("f09", "f10", "f11", "f12"):
        r[clave] = {"valor": None, "condicion": "dato", "motivo": ""}
    original = copy.deepcopy(valido)

    assert _validar(valido) == {}
    # La validación no completa los faltantes con cero.
    assert valido == original


def test_ingreso_denegado_no_exige_interiores_pero_si_que_ocurrio(valido):
    r = valido["respuestas"]
    r.update(resultado="no_ingreso", f07=None, f08=None)
    r["f09"] = {"valor": None, "condicion": "dato", "motivo": ""}

    errores = _validar(valido)
    assert errores == {"respuestas.que_ocurrio": "Contá qué ocurrió."}

    r["que_ocurrio"] = "La directora no permitió el ingreso."
    assert _validar(valido) == {}


def test_no_ingreso_exige_abierta_si(valido):
    valido["respuestas"].update(resultado="no_ingreso", f05="no", que_ocurrio="x")

    assert "respuestas.resultado" in _validar(valido)


def test_cerrada_exige_abierta_no_y_abierta_no_implica_cerrada(valido):
    valido["respuestas"].update(resultado="cerrada", f05="si")
    assert "respuestas.resultado" in _validar(valido)

    valido["respuestas"].update(resultado="constatado", f05="no")
    assert "respuestas.resultado" in _validar(valido)


def test_cero_es_una_respuesta_valida(valido):
    r = valido["respuestas"]
    for clave in ("f09", "f10", "f11", "f12"):
        r[clave] = {"valor": 0, "condicion": "dato", "motivo": ""}

    assert _validar(valido) == {}


def test_constatado_exige_cantidades_o_su_condicion_con_motivo(valido):
    r = valido["respuestas"]
    r["f09"] = {"valor": None, "condicion": "dato", "motivo": ""}
    r["f10"] = {"valor": None, "condicion": "no_constatado", "motivo": ""}

    errores = _validar(valido)
    assert "respuestas.f09" in errores
    assert "respuestas.f10.motivo" in errores

    r["f09"] = {"valor": None, "condicion": "no_informado", "motivo": "No lo saben"}
    r["f10"] = {"valor": None, "condicion": "no_constatado", "motivo": "No se pudo"}
    assert _validar(valido) == {}


@pytest.mark.parametrize("valor", [-1, 2.5, "3", True])
def test_cantidades_enteras_no_negativas(valido, valor):
    valido["respuestas"]["f11"] = {"valor": valor, "condicion": "dato", "motivo": ""}

    assert "respuestas.f11" in _validar(valido)


def test_constatado_exige_f07_y_f08_pero_parcial_no(valido):
    r = valido["respuestas"]
    r.update(f07=None, f08=None)
    errores = _validar(valido)
    assert {"respuestas.f07", "respuestas.f08"} <= set(errores)

    r.update(resultado="parcial", motivo_parcial="Sólo planta baja")
    r["f09"] = {"valor": None, "condicion": "dato", "motivo": ""}
    assert _validar(valido) == {}


def test_parcial_exige_motivo(valido):
    valido["respuestas"]["resultado"] = "parcial"

    assert "respuestas.motivo_parcial" in _validar(valido)


@pytest.mark.parametrize(
    ("cambios", "clave"),
    [
        (
            {"f10": {"valor": 30, "condicion": "dato", "motivo": ""}},
            "presentes_superan",
        ),
        ({"f12": {"valor": 12, "condicion": "dato", "motivo": ""}}, "aulas_superan"),
        ({"f07": "no"}, "sin_personal_con_presentes"),
        ({"f08": "no"}, "sin_estudiantes_con_aulas"),
    ],
)
def test_advertencias_se_aceptan_con_justificacion(valido, cambios, clave):
    r = valido["respuestas"]
    r.update(cambios)

    assert advertencias(r) == [clave]
    assert _validar(valido) == {
        f"respuestas.justificaciones.{clave}": "Escribí la justificación."
    }

    r["justificaciones"][clave] = "Hay suplencias."
    assert _validar(valido) == {}


def test_escuela_cue_solo_digitos_o_motivo_si_se_desconoce(valido):
    valido["escuela"]["cue"] = "06-01"
    assert "escuela.cue" in _validar(valido)

    valido["escuela"].update(cue="", cue_desconocido=True, motivo_sin_cue="")
    assert "escuela.motivo_sin_cue" in _validar(valido)

    valido["escuela"]["motivo_sin_cue"] = "Cartel ilegible"
    assert _validar(valido) == {}


def test_nueva_visita_en_el_mismo_turno_exige_motivo(valido):
    assert "motivo_nueva_visita" in _validar(valido, turnos_visitados_hoy={"tarde"})

    valido["motivo_nueva_visita"] = "Cambio de turno de la mañana"
    assert _validar(valido, turnos_visitados_hoy={"tarde"}) == {}


def test_ubicacion_gps_o_manual_con_motivo(valido):
    valido["ubicacion"] = None
    assert "ubicacion" in _validar(valido)

    valido["ubicacion"] = {"fuente": "manual", "lat": None, "lng": None}
    assert "ubicacion.motivo_sin_gps" in _validar(valido)

    valido["ubicacion"]["motivo_sin_gps"] = "Permiso de ubicación denegado"
    assert _validar(valido) == {}


def test_foto_del_ingreso_o_motivo(valido):
    valido["respuestas"]["f04"] = {"imagen_uuid": None, "motivo_sin_foto": ""}

    assert "respuestas.f04" in _validar(valido)


def test_quien_atiende_o_nadie(valido):
    valido["respuestas"]["f06"] = {"nadie": False, "nombre": "", "funcion": ""}
    errores = _validar(valido)
    assert {"respuestas.f06.nombre", "respuestas.f06.funcion"} <= set(errores)

    valido["respuestas"]["f06"] = {"nadie": True, "nombre": "", "funcion": ""}
    assert _validar(valido) == {}


def test_observaciones_hasta_5000_y_hasta_10_adicionales(valido):
    valido["respuestas"]["f16"] = "x" * 5001
    valido["imagenes"] = [{"uuid": str(i), "tipo": "adicional"} for i in range(11)]

    errores = _validar(valido)
    assert {"respuestas.f16", "respuestas.f15"} <= set(errores)


def test_firma_completa_o_excepcion_con_motivo(valido):
    valido["firma"] = None
    assert "firma" in _validar(valido)

    valido["firma"] = {"tipo": "excepcion", "motivo_tipo": "otra", "motivo": ""}
    assert "firma.motivo" in _validar(valido)

    valido["firma"] = {
        "tipo": "firma",
        "nombre": "María",
        "cargo": "Directora",
        "conformidad": False,
        "imagen_uuid": "",
        "texto_mostrado": "Texto",
    }
    errores = _validar(valido)
    assert {"firma.conformidad", "firma.imagen_uuid"} <= set(errores)
