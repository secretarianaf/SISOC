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


# --------------------------------------------------------- detalle y PDF


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
    assert "Descargar PDF" in html
    assert "Descargar docx" not in html


# Textos de trabajo del área (comentarios Gescom) que no son parte del formulario.
TEXTOS_DE_TRABAJO = ("Gescom", "GESCOM", "Comentario", "precargado en la app")


def _texto_pdf(contenido):
    from pypdf import PdfReader  # pylint: disable=import-outside-toplevel

    texto = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(contenido)).pages)
    return " ".join(texto.split())


def test_la_plantilla_no_tiene_los_comentarios_del_area():
    # QA (14/10): el formulario descargado traía los comentarios de Gescom.
    from django.apps import apps  # pylint: disable=import-outside-toplevel

    plantilla = zipfile.ZipFile(
        f"{apps.get_app_config('relevamientos').path}/templates/relevamientos/docx/"
        "seguimiento_siph.docx"
    )
    assert not [n for n in plantilla.namelist() if "comment" in n.lower()]
    xml = plantilla.read("word/document.xml").decode("utf-8")
    assert "comment" not in xml.lower()
    for texto in TEXTOS_DE_TRABAJO:
        assert texto not in xml, texto


def test_se_descarga_el_pdf_del_siph_con_las_respuestas(client):
    comedor = _comedor(TRADICIONAL)
    tecnico, _ = _territorial("pdf", comedor.provincia)
    seguimiento = _siph(comedor, tecnico)
    _coordinador(client)

    response = client.get(
        reverse(
            "seguimiento_pnud_pdf",
            kwargs={"comedor_pk": comedor.id, "pk": seguimiento.id},
        )
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"] == (
        f'attachment; filename="seguimiento-siph-{seguimiento.id}.pdf"'
    )
    texto = _texto_pdf(response.content)
    assert "{{" not in texto
    for esperado in (
        "SERVICIOS INTEGRALES DE PROMOCIÓN HUMANA",
        "Espacio SIPH",
        "SIPH-77",
        "Rosa Díaz",
        "30111222",
        "Taller de murga",
        "Lunes, Miércoles",
        "Mitre",
        "Vestuario de la murga",
        "Apoyo escolar",
        "Sin novedades.",
        "Abierto, con actividad",
    ):
        assert esperado in texto, esperado
    for texto_de_trabajo in TEXTOS_DE_TRABAJO:
        assert texto_de_trabajo not in texto, texto_de_trabajo


def test_el_pdf_solo_existe_para_el_siph(client):
    comedor = _comedor(TRADICIONAL)
    tecnico, _ = _territorial("pdf_iia", comedor.provincia)
    seguimiento = _siph(
        comedor, tecnico, formulario="iia", datos={"funcionamiento": "Cerrado"}
    )
    _coordinador(client)

    response = client.get(
        reverse(
            "seguimiento_pnud_pdf",
            kwargs={"comedor_pk": comedor.id, "pk": seguimiento.id},
        )
    )

    assert response.status_code == 404


def test_gestionar_baja_el_mismo_pdf_que_sisoc(client):
    # QA (14/10): la app mostraba su PDF genérico; tiene que ser el de SISOC.
    comedor = _comedor(SECOS)
    tecnico, api = _territorial("pdf_app", comedor.provincia)
    seguimiento = _siph(comedor, tecnico)
    otro = _siph(
        comedor, tecnico, formulario="secos", datos={"funcionamiento": "Cerrado"}
    )

    response = api.get(f"{_url(comedor, seguimiento.id)}pdf/")
    no_siph = api.get(f"{_url(comedor, otro.id)}pdf/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert "Rosa Díaz" in _texto_pdf(response.content)
    assert no_siph.status_code == 404


def test_un_territorial_de_otra_zona_no_baja_el_pdf():
    comedor = _comedor(SECOS)
    tecnico, _ = _territorial("pdf_duenio", comedor.provincia)
    seguimiento = _siph(comedor, tecnico)
    _, ajeno = _territorial("pdf_ajeno", Provincia.objects.create(nombre="Otra SIPH"))

    response = ajeno.get(f"{_url(comedor, seguimiento.id)}pdf/")

    assert response.status_code in (403, 404)


def test_la_firma_va_como_imagen_y_no_como_texto(settings, tmp_path):
    # Antes salía el texto "(firma registrada)", que no es parte del formulario.
    import base64  # pylint: disable=import-outside-toplevel

    from django.core.files.base import (
        ContentFile,
    )  # pylint: disable=import-outside-toplevel
    from django.core.files.storage import (
        default_storage,
    )  # pylint: disable=import-outside-toplevel

    from relevamientos.siph_docx import (
        docx_siph,
    )  # pylint: disable=import-outside-toplevel

    settings.MEDIA_ROOT = str(tmp_path)
    comedor = _comedor(SECOS)
    tecnico, _ = _territorial("firma", comedor.provincia)
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    )
    nombre = default_storage.save(
        f"firmas/{comedor.id}/entrevistado.png", ContentFile(png)
    )
    seguimiento = _siph(
        comedor,
        tecnico,
        datos={**DATOS_SIPH, "firma_entrevistado": default_storage.url(nombre)},
    )
    ajena = _siph(
        comedor,
        tecnico,
        datos={**DATOS_SIPH, "firma_entrevistado": "https://evil.test/firmas/x.png"},
    )

    docx = zipfile.ZipFile(docx_siph(seguimiento))
    sin_firma = zipfile.ZipFile(docx_siph(ajena))

    def medios(z):
        return [n for n in z.namelist() if n.startswith("word/media/")]

    # La plantilla trae sus logos: la firma suma una imagen; una URL ajena, ninguna.
    assert len(medios(docx)) == len(medios(sin_firma)) + 1
    assert "firma registrada" not in docx.read("word/document.xml").decode("utf-8")
