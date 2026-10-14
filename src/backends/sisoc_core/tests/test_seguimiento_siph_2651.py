"""#2651: Seguimiento SIPH (Servicios Integrales de Promoción Humana).

Formulario nuevo de Abordaje Comunitario (Línea Secos y Línea Tradicional),
repetible n veces por comedor, con o sin relevamiento inicial, desde SISOC y
desde la app. Entra como un ``formulario`` más de ``SeguimientoPnud``, que ya
tiene la asignación desde SISOC, el alta y la corrección desde la app, la
revisión del coordinador y el detalle genérico. Lo propio del SIPH: las
actividades del comedor para precargar (``ActividadEspacioPWA``) y la
exportación al docx del área.
"""

import datetime
import io
import json
import zipfile

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.forms import ValidationError
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from comedores.api_views_territorial_pnud import formulario_permitido
from comedores.models import Comedor, Programas
from core.models import Dia, Provincia
from pwa.models import ActividadEspacioPWA, CatalogoActividadPWA
from relevamientos.alta_backoffice import crear_seguimiento_pnud_asignado, opciones_alta
from relevamientos.models import SeguimientoPnud
from users.models import TerritorialComedorProvincia

pytestmark = pytest.mark.django_db

SECOS = "Abordaje comunitario - Línea Secos"
TRADICIONAL = "Abordaje comunitario - Línea Tradicional"
ALIMENTAR = "Alimentar comunidad"
PENDIENTE = SeguimientoPnud.ESTADO_VALIDACION_PENDIENTE
VALIDADO = SeguimientoPnud.ESTADO_VALIDACION_VALIDADO
ETIQUETA_POPUP = "Seguimiento SIPH (Línea Tradicional y Módulos Secos)"

# Respuestas con las claves del formulario (pnudForm.ts de la app, siph).
DATOS_SIPH = {
    "codigo_proyecto": "SIPH-77",
    "codigo_externo": "4321",
    "funcionamiento": "Abierto, con actividad",
    "ent_nombre_apellido": "Rosa Díaz",
    "ent_dni": "30111222",
    "actividad_en_espacio": True,
    "calle": "Mitre",
    "numero": "123",
    "barrio": "Centro",
    "localidad": "Lanús",
    "municipio": "Lanús",
    "provincia": "Buenos Aires",
    "actividad_visitada": "Culturales y/o artísticas — Taller de murga",
    "actividades": [
        {
            "tipo_actividad": "Culturales y/o artísticas",
            "subtipo_actividad": "Taller de murga",
            "dias_funcionamiento": "Lunes, Miércoles",
            "horario_funcionamiento": "14:00 a 16:00",
            "personas_observadas": 18,
        }
    ],
    "financiamiento_planificado": True,
    "financiamiento_componentes": [
        "Retribución talleristas",
        "Materiales/insumos/equipamiento",
    ],
    "financiamiento_talleristas_cantidad": "2",
    "financiamiento_materiales_detalle": "Instrumentos",
    "otros_recursos": True,
    "otros_recursos_origen": ["Estado Municipal", "Donaciones"],
    "otros_recursos_destino": "Vestuario de la murga",
    "mejoras": ["Incorporación de nuevos talleristas"],
    "dificultades": ["Problemas con las rendiciones de cuentas"],
    "demandas_otras_actividades": True,
    "demandas_cuales": "Apoyo escolar",
    "comentarios_finales": "Sin novedades.",
    "modalidad_entrevista": "Presencial",
}


def _comedor(programa_nombre):
    provincia = Provincia.objects.create(nombre=f"Prov {programa_nombre}")
    programa = Programas.objects.create(nombre=programa_nombre)
    return Comedor.objects.create(
        nombre="Espacio SIPH",
        provincia=provincia,
        programa=programa,
        codigo_de_proyecto="SIPH-77",
        id_externo=4321,
    )


def _territorial(nombre, provincia):
    user = get_user_model().objects.create_user(
        username=f"terr_{nombre}", password="testpass123"
    )
    user.profile.es_territorial_comedor = True
    user.profile.save(update_fields=["es_territorial_comedor"])
    TerritorialComedorProvincia.objects.create(
        profile=user.profile, provincia=provincia
    )
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return user, client


def _coordinador(client):
    user = get_user_model().objects.create_user(
        username="coord_siph", password="testpass123"
    )
    for codename in ("review_relevamiento", "view_relevamiento"):
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="relevamientos", codename=codename
            )
        )
    client.force_login(user)
    return user


def _url(comedor, pnud_id=None):
    base = f"/api/territorial/comedores/{comedor.id}/seguimientos-pnud/"
    return f"{base}{pnud_id}/" if pnud_id else base


def _siph(comedor, tecnico, **extra):
    datos = {"formulario": SeguimientoPnud.FORMULARIO_SIPH, "datos": dict(DATOS_SIPH)}
    datos.update(extra)
    return SeguimientoPnud.objects.create(
        comedor=comedor,
        tecnico=tecnico,
        fecha_hora=datetime.datetime(
            2026, 10, 14, 15, 30, tzinfo=datetime.timezone.utc
        ),
        origen=SeguimientoPnud.ORIGEN_APP,
        asignado_desde_sisoc=False,
        client_uuid=f"siph-{SeguimientoPnud.objects.count() + 1}",
        estado_validacion=PENDIENTE,
        **datos,
    )


# ----------------------------------------------------------- formulario


def test_siph_es_un_formulario_pnud_de_las_dos_lineas_de_abordaje_comunitario():
    assert SeguimientoPnud.FORMULARIO_SIPH == "siph"
    assert "SIPH" in dict(SeguimientoPnud.FORMULARIO_CHOICES)["siph"]
    for programa in (SECOS, TRADICIONAL):
        comedor = _comedor(programa)
        assert formulario_permitido(comedor, "siph"), programa
        assert ("pnud_siph", ETIQUETA_POPUP) in opciones_alta(comedor), programa
    alimentar = _comedor(ALIMENTAR)
    assert not formulario_permitido(alimentar, "siph")
    assert "pnud_siph" not in dict(opciones_alta(alimentar))


@pytest.mark.parametrize("programa", [SECOS, TRADICIONAL])
def test_la_app_da_de_alta_un_siph_sin_relevamiento_inicial(programa):
    comedor = _comedor(programa)
    _, client = _territorial("alta", comedor.provincia)

    response = client.post(
        _url(comedor),
        {
            "client_uuid": "siph-app-1",
            "formulario": "siph",
            "fecha_hora": "14/10/2026 15:30",
            "datos": DATOS_SIPH,
        },
        format="json",
    )

    assert response.status_code == 201, response.data
    seguimiento = SeguimientoPnud.objects.get(client_uuid="siph-app-1")
    assert seguimiento.formulario == "siph"
    assert seguimiento.estado_validacion == PENDIENTE
    assert seguimiento.datos["actividades"][0]["personas_observadas"] == 18


def test_un_comedor_de_alimentar_comunidad_no_admite_el_siph():
    comedor = _comedor(ALIMENTAR)
    _, client = _territorial("alimentar", comedor.provincia)

    response = client.post(
        _url(comedor),
        {"client_uuid": "siph-pac", "formulario": "siph", "datos": DATOS_SIPH},
        format="json",
    )

    assert response.status_code == 400


def test_se_puede_asignar_otro_siph_cuando_el_anterior_termino():
    """ "n veces": solo bloquea una segunda asignación mientras hay una sin terminar."""
    comedor = _comedor(TRADICIONAL)
    tecnico, _ = _territorial("asignado", comedor.provincia)
    territorial = json.dumps({"gestionar_uid": str(tecnico.id), "nombre": "T"})

    primero = crear_seguimiento_pnud_asignado(comedor, territorial, "siph")
    with pytest.raises(ValidationError):
        crear_seguimiento_pnud_asignado(comedor, territorial, "siph")
    primero.estado_validacion = VALIDADO
    primero.save(update_fields=["estado_validacion"])
    segundo = crear_seguimiento_pnud_asignado(comedor, territorial, "siph")

    assert segundo.pk != primero.pk
    assert comedor.seguimientos_pnud.filter(formulario="siph").count() == 2


# ------------------------------------------------------------ actividades


def test_el_get_trae_las_actividades_del_comedor_para_precargar():
    comedor = _comedor(TRADICIONAL)
    _, client = _territorial("actividades", comedor.provincia)
    lunes = Dia.objects.create(nombre="Lunes")
    miercoles = Dia.objects.create(nombre="Miércoles")
    viernes = Dia.objects.create(nombre="Viernes")
    # El catálogo viene sembrado por migración: no se duplica.
    murga, _ = CatalogoActividadPWA.objects.get_or_create(
        categoria="Culturales y/o artísticas", actividad="Taller de murga"
    )
    apoyo, _ = CatalogoActividadPWA.objects.get_or_create(
        categoria="Educativas", actividad="Apoyo escolar"
    )
    comun = {
        "horario_actividad": "14 a 16",
        "hora_inicio": datetime.time(14),
        "hora_fin": datetime.time(16),
    }
    # Una fila por día: la misma actividad y horario se presentan juntas.
    ActividadEspacioPWA.objects.create(
        comedor=comedor, catalogo_actividad=murga, dia_actividad=lunes, **comun
    )
    ActividadEspacioPWA.objects.create(
        comedor=comedor, catalogo_actividad=murga, dia_actividad=miercoles, **comun
    )
    ActividadEspacioPWA.objects.create(
        comedor=comedor,
        catalogo_actividad=apoyo,
        dia_actividad=viernes,
        horario_actividad="Tarde",
    )
    # Una dada de baja no se precarga.
    ActividadEspacioPWA.objects.create(
        comedor=comedor,
        catalogo_actividad=apoyo,
        dia_actividad=lunes,
        horario_actividad="Mañana",
        activo=False,
    )

    response = client.get(_url(comedor))

    assert response.status_code == 200
    assert response.data["actividades"] == [
        {
            "tipo": "Culturales y/o artísticas",
            "subtipo": "Taller de murga",
            "dias": "Lunes, Miércoles",
            "horario": "14:00 a 16:00",
            "etiqueta": "Culturales y/o artísticas — Taller de murga (Lunes, Miércoles, 14:00 a 16:00)",
        },
        {
            "tipo": "Educativas",
            "subtipo": "Apoyo escolar",
            "dias": "Viernes",
            "horario": "Tarde",
            "etiqueta": "Educativas — Apoyo escolar (Viernes, Tarde)",
        },
    ]


# -------------------------------------------------------- detalle y docx


def test_el_detalle_del_coordinador_muestra_las_etiquetas_del_siph(client):
    comedor = _comedor(SECOS)
    tecnico, _ = _territorial("detalle", comedor.provincia)
    seguimiento = _siph(comedor, tecnico)
    _coordinador(client)

    html = client.get(
        reverse(
            "seguimiento_pnud_detalle",
            kwargs={"comedor_pk": comedor.id, "pk": seguimiento.id},
        )
    ).content.decode()

    assert "SERVICIOS INTEGRALES DE PROMOCIÓN HUMANA" in html
    assert "1. DATOS DEL ENTREVISTADO" in html
    assert "Rosa Díaz" in html
    assert "¿La actividad visitada se realiza en el espacio comunitario?" in html
    assert "Taller de murga" in html
    assert "Retribución talleristas" in html
    assert "Ent nombre apellido" not in html
    assert "Descargar docx" in html


def test_se_descarga_el_docx_del_siph_con_las_respuestas(client):
    comedor = _comedor(TRADICIONAL)
    tecnico, _ = _territorial("docx", comedor.provincia)
    seguimiento = _siph(comedor, tecnico)
    _coordinador(client)

    response = client.get(
        reverse(
            "seguimiento_pnud_docx",
            kwargs={"comedor_pk": comedor.id, "pk": seguimiento.id},
        )
    )

    assert response.status_code == 200
    assert response["Content-Type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert response["Content-Disposition"] == (
        f'attachment; filename="seguimiento-siph-{seguimiento.id}.docx"'
    )
    contenido = (
        b"".join(response.streaming_content) if response.streaming else response.content
    )
    xml = (
        zipfile.ZipFile(io.BytesIO(contenido)).read("word/document.xml").decode("utf-8")
    )
    assert "{{" not in xml and "{%" not in xml
    for texto in (
        "Rosa Díaz",
        "30111222",
        "Taller de murga",
        "Lunes, Miércoles",
        "Mitre",
        "Vestuario de la murga",
        "Apoyo escolar",
        "Sin novedades.",
        "X Abierto, con actividad",
        "☒ Retribución talleristas",
        "☒ Presencial",
        "☐ Virtual",
    ):
        assert texto in xml, texto
    assert "Espacio SIPH" in xml
    assert "SIPH-77" in xml


def test_el_docx_solo_existe_para_el_siph(client):
    comedor = _comedor(TRADICIONAL)
    tecnico, _ = _territorial("docx_iia", comedor.provincia)
    seguimiento = _siph(
        comedor, tecnico, formulario="iia", datos={"funcionamiento": "Cerrado"}
    )
    _coordinador(client)

    response = client.get(
        reverse(
            "seguimiento_pnud_docx",
            kwargs={"comedor_pk": comedor.id, "pk": seguimiento.id},
        )
    )

    assert response.status_code == 404
