"""Instrumento DataCalle 4.1.0: el formulario de menores (14 a 17 años), #2664.

La app vuelve a tener una variante acotada (`adolescente`) para las personas de
14 a 17 que aceptan responder: un subconjunto del papel general, sin claves
nuevas. SISOC toma la copia y, como la ficha solo muestra lo que llegó, lo que
le falta es decir **qué formulario** se usó: sin eso, un caso de menores con
ocho respuestas parece un caso incompleto.
"""

import datetime
import json
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model

from core.models import Provincia
from datacalle.models import Encuesta, Relevamiento
from datacalle.services import aplicar_columnas_indexadas
from datacalle.services.instrumento import get_catalogos, get_cuestionario, get_version

RUTA_INSTRUMENTO = Path(__file__).resolve().parents[1] / "datacalle" / "instrumento"
MENORES = "Formulario de menores (14 a 17 años)"


@pytest.mark.smoke
def test_la_copia_local_trae_el_formulario_de_menores_sin_claves_nuevas():
    # 4.1.1 (#2724) solo cambia una opción de la 25: test_datacalle_instrumento_4_1_1.py.
    assert get_version() == "4.1.1"
    diccionario = json.loads(
        (RUTA_INSTRUMENTO / "diccionario-respuestas.json").read_text(encoding="utf-8")
    )
    # Es un subconjunto del papel general: mismas 88 claves. Las retiradas pasan
    # de 27 a 28 por la ENMIENDA del área del 1/10 (PR #15 de la app), que la
    # copia 4.0.0 de SISOC no había tomado: `yaEntrevistadaDatos` deja de
    # preguntarse porque la opción "ya fue entrevistada" se retira. No es de #2664.
    assert len(diccionario) == 88
    assert sum(1 for campo in diccionario if campo["soloHistorico"]) == 28
    assert next(c for c in diccionario if c["campo"] == "yaEntrevistadaDatos")[
        "soloHistorico"
    ]
    variantes = get_cuestionario()["variantes"]
    assert set(variantes["adolescente"]["campos"]) >= {
        "tieneDocumento",
        "nivelEducativo",
        "dondeDuermeEstaNoche",
        "desdeCuandoCalle",
    }
    regla = variantes["reglas"][0]
    assert regla["variante"] == "adolescente"
    assert {"campo": "personaEntrevistada", "prefijoEn": ["r14a17"]} in regla["cuando"][
        "todas"
    ]
    opcion = next(
        o
        for o in get_catalogos()["varianteCuestionario"]["opciones"]
        if o["codigo"] == "adolescente"
    )
    assert opcion["etiqueta"] == MENORES
    assert not opcion.get("retirada")


@pytest.mark.smoke
@pytest.mark.parametrize(
    "variante,etiqueta,es_menores",
    [
        ("adolescente", MENORES, True),
        ("completo", "Cuestionario completo", False),
        ("", "", False),
    ],
)
def test_el_caso_sabe_que_formulario_se_uso(variante, etiqueta, es_menores):
    caso = Encuesta(variante=variante)

    assert caso.variante_etiqueta == etiqueta
    assert caso.es_formulario_menores is es_menores


def _coordinador(provincia):
    user = get_user_model().objects.create_user(
        username="coord_2664", email="coord_2664@example.com", password="Sisoc12345!"
    )
    user.profile.es_usuario_provincial = True
    user.profile.save()
    user.profile.territorial_scopes.create(provincia=provincia)
    from django.contrib.auth.models import Permission

    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="datacalle",
            codename__in=["view_relevamiento", "view_encuesta"],
        )
    )
    return user


def _caso_de_menores(relevamiento):
    caso = Encuesta(
        relevamiento=relevamiento,
        estado=Encuesta.Estado.COMPLETA,
        variante="adolescente",
        respuestas={
            "codigoEntrevistado": "ANPA04032011",
            "esCabeceraGrupo": "si",
            "personasObservadas": 1,
            "grupoObservado": {"r14a17_mujer": 1},
            "personaEntrevistada": "r14a17_mujer#1",
            "realizaEntrevista": "si",
            "lugarHallazgo": "espacioPublico",
            "tieneDocumento": "no",
            "nivelEducativo": "secundarioIncompleto",
            "dondeDuermeEstaNoche": "viaPublica",
            "desdeCuandoCalle": "semanaAMes",
        },
    )
    aplicar_columnas_indexadas(caso)
    caso.save()
    return caso


@pytest.mark.django_db
def test_la_ficha_y_el_listado_dicen_que_es_el_formulario_de_menores(client):
    provincia = Provincia.objects.create(nombre="Prov 2664")
    relevamiento = Relevamiento.objects.create(
        denominacion="Operativo 2664",
        provincia=provincia,
        fase=Relevamiento.Fase.ESPACIO_PUBLICO,
        area_operativa="Plaza",
        fecha_inicio=datetime.date(2026, 10, 13),
        fecha_fin=datetime.date(2026, 10, 17),
    )
    caso = _caso_de_menores(relevamiento)
    client.force_login(_coordinador(provincia))

    ficha = client.get(f"/datacalle/casos/{caso.pk}/")
    listado = client.get(f"/datacalle/relevamientos/{relevamiento.pk}/")

    assert ficha.status_code == 200
    html = ficha.content.decode()
    assert MENORES in html
    # El aviso explica por qué faltan las demás preguntas del papel general.
    assert "no se le preguntan" in html
    assert "Secundario incompleto" in html
    assert listado.status_code == 200
    assert "Menores (14 a 17)" in listado.content.decode()
