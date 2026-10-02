"""Comentarios técnicos estructurados y su publicación a Provincia (issue #2318).

Cubre las reglas de `ComentariosTecnicosService`: validación de la combinación
de opciones, multi-alta sin sobrescritura, opciones del multiselect sin
duplicados, y motivo y publicación restringidos a lo elegido en cada instancia
(issue #2592).
"""

from datetime import date

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from ciudadanos.models import Ciudadano
from celiaquia.comentarios_tecnicos import (
    CODIGO_OTROS,
    MAX_LEN_CODIGO_OBSERVACION,
    TipoDocumentoComentario,
    catalogo_serializable,
    es_codigo_valido,
    observaciones_de,
    texto_observacion,
)
from celiaquia.models import (
    EstadoExpediente,
    EstadoLegajo,
    Expediente,
    ExpedienteCiudadano,
    HistorialComentarios,
    RevisionTecnico,
)
from celiaquia.services.comentarios_tecnicos_service import (
    ComentariosTecnicosService,
    normalizar_si_no,
)

pytestmark = pytest.mark.django_db

CODIGO_RENAPER = "RENAPER_FECHA_NACIMIENTO"
CODIGO_ANSES = "ANSES_REGISTRA_OBRA_SOCIAL"


@pytest.fixture(name="tecnico")
def fixture_tecnico():
    return User.objects.create_user(username="tec_comentarios", password="pass")


@pytest.fixture(name="legajo")
def fixture_legajo(tecnico):
    estado_exp = EstadoExpediente.objects.create(nombre="EST_EXP_CT")
    estado_legajo = EstadoLegajo.objects.create(nombre="EST_LEG_CT")
    expediente = Expediente.objects.create(usuario_provincia=tecnico, estado=estado_exp)
    ciudadano = Ciudadano.objects.create(
        apellido="Tecnico",
        nombre="Comentario",
        documento="40100200",
        fecha_nacimiento=date(1990, 1, 1),
    )
    return ExpedienteCiudadano.objects.create(
        expediente=expediente, ciudadano=ciudadano, estado=estado_legajo
    )


def _registrar(legajo, usuario, **kwargs):
    datos = {
        "tipo_documento": TipoDocumentoComentario.RENAPER,
        "tiene_observaciones": True,
        "observacion_codigo": CODIGO_RENAPER,
    }
    datos.update(kwargs)
    return ComentariosTecnicosService.registrar(legajo=legajo, usuario=usuario, **datos)


# --- Catálogo -------------------------------------------------------------


def test_catalogo_tiene_otros_en_los_tres_tipos():
    for tipo in TipoDocumentoComentario.values:
        codigos = [codigo for codigo, _ in observaciones_de(tipo)]
        assert codigos[-1] == CODIGO_OTROS
        assert len(codigos) == len(set(codigos))


def test_catalogo_anses_incluye_las_observaciones_de_codem():
    """Observaciones de CODEM incorporadas por el issue #2523.

    Se comparan los textos completos porque son normativos: los define el área y
    es lo que efectivamente se le comunica a la Provincia.
    """
    textos = dict(observaciones_de(TipoDocumentoComentario.ANSES))

    assert textos["ANSES_CODEM_VENCIDO"] == (
        "Enviar constancia de CODEM/ANSES, ya que la misma se encuentra vencida. "
        "Recordar que tiene una validez de 30 días."
    )
    assert textos["ANSES_CUIL_INEXISTENTE"] == (
        "El CODEM vinculado contiene un CUIL inexistente. Se solicita subir el que "
        "corresponde."
    )


def test_codigos_del_catalogo_entran_en_el_campo_que_los_persiste():
    """`HistorialComentarios.observacion_codigo` tiene largo acotado: un código
    nuevo más largo que el campo rompería recién al guardar."""
    for tipo in TipoDocumentoComentario.values:
        for codigo, _ in observaciones_de(tipo):
            assert len(codigo) <= MAX_LEN_CODIGO_OBSERVACION


def test_codigo_no_es_valido_para_otro_tipo_de_documento():
    assert es_codigo_valido(TipoDocumentoComentario.RENAPER, CODIGO_RENAPER)
    assert not es_codigo_valido(TipoDocumentoComentario.ANSES, CODIGO_RENAPER)


def test_catalogo_serializable_marca_la_opcion_libre():
    catalogo = catalogo_serializable()
    assert set(catalogo) == set(TipoDocumentoComentario.values)
    libres = [o for o in catalogo[TipoDocumentoComentario.ANSES.value] if o["libre"]]
    assert [o["codigo"] for o in libres] == [CODIGO_OTROS]


@pytest.mark.parametrize(
    "valor,esperado",
    [
        ("SI", True),
        ("sí", True),
        ("1", True),
        (True, True),
        ("No", False),
        ("0", False),
        (False, False),
        ("", None),
        ("cualquiera", None),
        (None, None),
    ],
)
def test_normalizar_si_no(valor, esperado):
    assert normalizar_si_no(valor) is esperado


# --- Alta -----------------------------------------------------------------


def test_registrar_guarda_texto_de_catalogo_como_interno(legajo, tecnico):
    comentario = _registrar(legajo, tecnico)

    assert comentario.tipo_comentario == HistorialComentarios.TIPO_COMENTARIO_TECNICO
    assert comentario.es_interno is True
    assert comentario.publicado_en is None
    assert comentario.tiene_observaciones is True
    assert comentario.observacion_codigo == CODIGO_RENAPER
    assert comentario.comentario == texto_observacion(
        TipoDocumentoComentario.RENAPER, CODIGO_RENAPER
    )
    assert comentario.usuario == tecnico
    # Estado del legajo al momento de la creación (requerimiento §4).
    assert comentario.estado_relacionado == RevisionTecnico.PENDIENTE


def test_registrar_sin_observaciones_deja_la_observacion_vacia(legajo, tecnico):
    comentario = _registrar(
        legajo,
        tecnico,
        tiene_observaciones=False,
        observacion_codigo=CODIGO_RENAPER,
        observacion_libre="se ignora",
    )

    assert comentario.tiene_observaciones is False
    assert comentario.observacion_codigo is None
    assert comentario.comentario == "Sin observaciones."


def test_registrar_otros_usa_el_texto_libre(legajo, tecnico):
    comentario = _registrar(
        legajo,
        tecnico,
        observacion_codigo=CODIGO_OTROS,
        observacion_libre="  Falta la firma del profesional.  ",
    )

    assert comentario.observacion_codigo == CODIGO_OTROS
    assert comentario.comentario == "Falta la firma del profesional."


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tipo_documento": ""},
        {"tipo_documento": "INEXISTENTE"},
        {"tiene_observaciones": ""},
        {"observacion_codigo": ""},
        {"observacion_codigo": "INEXISTENTE"},
        {"tipo_documento": TipoDocumentoComentario.ANSES},  # código de otro tipo
        {"observacion_codigo": CODIGO_OTROS, "observacion_libre": "   "},
    ],
)
def test_registrar_rechaza_combinaciones_invalidas(legajo, tecnico, kwargs):
    with pytest.raises(ValidationError):
        _registrar(legajo, tecnico, **kwargs)
    assert not ComentariosTecnicosService.historial(legajo).exists()


def test_altas_sucesivas_no_se_sobrescriben(legajo, tecnico):
    _registrar(legajo, tecnico)
    _registrar(legajo, tecnico, tiene_observaciones=False)
    _registrar(
        legajo,
        tecnico,
        tipo_documento=TipoDocumentoComentario.ANSES,
        observacion_codigo=CODIGO_ANSES,
    )

    assert ComentariosTecnicosService.historial(legajo).count() == 3


# --- Opciones del multiselect (issue #2592) --------------------------------


def _anses(legajo, tecnico, **kwargs):
    return _registrar(
        legajo,
        tecnico,
        tipo_documento=TipoDocumentoComentario.ANSES,
        observacion_codigo=CODIGO_ANSES,
        **kwargs,
    )


def test_opciones_son_cronologicas_e_ignoran_los_no(legajo, tecnico):
    _registrar(legajo, tecnico)
    _registrar(legajo, tecnico, tiene_observaciones=False)
    _anses(legajo, tecnico)

    opciones = ComentariosTecnicosService.opciones_seleccionables(legajo)

    assert [o["etiqueta"].split(":")[0] for o in opciones] == ["RENAPER", "ANSES"]
    assert all(o["pendiente"] for o in opciones)
    assert not any("Sin observaciones." in o["etiqueta"] for o in opciones)


def test_opciones_deduplican_el_mismo_codigo(legajo, tecnico):
    _registrar(legajo, tecnico)
    segundo = _registrar(legajo, tecnico)

    opciones = ComentariosTecnicosService.opciones_seleccionables(legajo)

    # Una sola opción, que apunta al registro más reciente.
    assert [o["id"] for o in opciones] == [segundo.pk]


def test_opciones_deduplican_otros_con_el_mismo_texto(legajo, tecnico):
    _registrar(
        legajo, tecnico, observacion_codigo=CODIGO_OTROS, observacion_libre="Falta DNI"
    )
    _registrar(
        legajo,
        tecnico,
        observacion_codigo=CODIGO_OTROS,
        observacion_libre="  falta   dni ",
    )
    _registrar(
        legajo,
        tecnico,
        observacion_codigo=CODIGO_OTROS,
        observacion_libre="Falta la partida",
    )

    assert len(ComentariosTecnicosService.opciones_seleccionables(legajo)) == 2


def test_opciones_ya_publicadas_no_vienen_pendientes(legajo, tecnico):
    renaper = _registrar(legajo, tecnico)
    ComentariosTecnicosService.publicar(legajo, comentarios=[renaper])
    _anses(legajo, tecnico)

    pendientes = {
        o["etiqueta"].split(":")[0]: o["pendiente"]
        for o in ComentariosTecnicosService.opciones_seleccionables(legajo)
    }

    assert pendientes == {"RENAPER": False, "ANSES": True}


def test_opcion_publicada_vuelve_a_pendiente_si_se_registra_de_nuevo(legajo, tecnico):
    """El caso del tk: ANSES se pidió en la 1° instancia y Nación lo vuelve a
    registrar para la 2°. Tiene que ofrecerse tildado otra vez."""
    primero = _anses(legajo, tecnico)
    ComentariosTecnicosService.publicar(legajo, comentarios=[primero])
    segundo = _anses(legajo, tecnico)

    (opcion,) = ComentariosTecnicosService.opciones_seleccionables(legajo)

    assert opcion["id"] == segundo.pk
    assert opcion["pendiente"] is True


# --- Selección -------------------------------------------------------------


def test_resolver_seleccion_devuelve_solo_lo_elegido_en_orden(legajo, tecnico):
    renaper = _registrar(legajo, tecnico)
    anses = _anses(legajo, tecnico)
    _registrar(
        legajo,
        tecnico,
        tipo_documento=TipoDocumentoComentario.CONDICION_DIAGNOSTICA,
        observacion_codigo="DIAG_DOC_ILEGIBLE",
    )

    elegidos = ComentariosTecnicosService.resolver_seleccion(
        legajo, [str(anses.pk), str(renaper.pk)]
    )

    assert elegidos == [renaper, anses]


def test_resolver_seleccion_vacia(legajo, tecnico):
    _registrar(legajo, tecnico)

    assert ComentariosTecnicosService.resolver_seleccion(legajo, []) == []
    assert ComentariosTecnicosService.resolver_seleccion(legajo, ["", " "]) == []


@pytest.mark.parametrize("caso", ["no", "otro_legajo", "inexistente", "basura"])
def test_resolver_seleccion_rechaza_ids_invalidos(legajo, tecnico, caso):
    if caso == "no":
        ids = [_registrar(legajo, tecnico, tiene_observaciones=False).pk]
    elif caso == "otro_legajo":
        otro = ExpedienteCiudadano.objects.create(
            expediente=legajo.expediente,
            ciudadano=Ciudadano.objects.create(
                apellido="Otro",
                nombre="Legajo",
                documento="40100201",
                fecha_nacimiento=date(1990, 1, 1),
            ),
            estado=legajo.estado,
        )
        ids = [_registrar(otro, tecnico).pk]
    elif caso == "inexistente":
        ids = [999999]
    else:
        ids = ["abc"]

    with pytest.raises(ValidationError):
        ComentariosTecnicosService.resolver_seleccion(legajo, ids)


# --- Motivo ----------------------------------------------------------------


def test_componer_motivo_usa_solo_lo_elegido(legajo, tecnico):
    renaper = _registrar(legajo, tecnico)
    _anses(legajo, tecnico)

    motivo = ComentariosTecnicosService.componer_motivo([renaper])

    assert motivo.startswith("RENAPER: ")
    assert "ANSES" not in motivo


def test_componer_motivo_agrega_el_texto_libre(legajo, tecnico):
    renaper = _registrar(legajo, tecnico)

    motivo = ComentariosTecnicosService.componer_motivo([renaper], "  Urgente.  ")

    assert motivo.startswith("RENAPER: ")
    assert motivo.endswith("Urgente.")


def test_componer_motivo_acepta_solo_texto_libre():
    assert ComentariosTecnicosService.componer_motivo([], "Motivo puntual.") == (
        "Motivo puntual."
    )


def test_componer_motivo_sin_seleccion_ni_texto_libre_falla():
    with pytest.raises(ValidationError):
        ComentariosTecnicosService.componer_motivo([], "   ")


# --- Publicación ----------------------------------------------------------


def test_publicar_solo_alcanza_a_lo_elegido(legajo, tecnico):
    elegido = _registrar(legajo, tecnico)
    no_elegido = _anses(legajo, tecnico)
    sin_obs = _registrar(legajo, tecnico, tiene_observaciones=False)

    assert (
        ComentariosTecnicosService.publicar(
            legajo, comentarios=[elegido], usuario=tecnico
        )
        == 1
    )

    for comentario in (elegido, no_elegido, sin_obs):
        comentario.refresh_from_db()
    assert elegido.es_interno is False
    assert elegido.publicado_en is not None
    assert elegido.publicado_por == tecnico
    assert no_elegido.es_interno is True
    assert no_elegido.publicado_en is None
    assert sin_obs.es_interno is True


def test_publicar_alcanza_a_los_registros_repetidos_de_lo_elegido(legajo, tecnico):
    primero = _registrar(legajo, tecnico)
    segundo = _registrar(legajo, tecnico)

    assert ComentariosTecnicosService.publicar(legajo, comentarios=[segundo]) == 2

    primero.refresh_from_db()
    assert primero.es_interno is False


def test_publicar_sin_seleccion_no_publica_nada(legajo, tecnico):
    _registrar(legajo, tecnico)

    assert ComentariosTecnicosService.publicar(legajo, comentarios=[]) == 0
    assert ComentariosTecnicosService.historial(legajo).get().es_interno is True


def test_publicar_no_repisa_la_auditoria_de_los_ya_publicados(legajo, tecnico):
    primero = _registrar(legajo, tecnico)
    ComentariosTecnicosService.publicar(legajo, comentarios=[primero], usuario=tecnico)
    primero.refresh_from_db()
    publicado_en_original = primero.publicado_en

    otro_tecnico = User.objects.create_user(username="tec_2", password="pass")
    anses = _anses(legajo, tecnico)
    assert (
        ComentariosTecnicosService.publicar(
            legajo, comentarios=[primero, anses], usuario=otro_tecnico
        )
        == 1
    )

    primero.refresh_from_db()
    assert primero.publicado_en == publicado_en_original
    assert primero.publicado_por == tecnico
