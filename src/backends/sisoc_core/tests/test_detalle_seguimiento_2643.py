"""#2643: el detalle del seguimiento no muestra datos internos.

El detalle vuelca los campos de cada bloque. Mostraba los identificadores
que genera la app (``app-i47-actividades``…), el vínculo interno a los bloques
del relevamiento ("Recursos #N") y la firma como una URL en texto.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from comedores.models import Comedor
from core.models import Provincia
from relevamientos.models import (
    AsistenciaTecnicaSeguimiento,
    CierreSeguimiento,
    PrestacionSeguimiento,
    PrimerSeguimiento,
    RecursosSeguimiento,
    Relevamiento,
)
from relevamientos.views.web_views import _bloque_campos

FIRMA = "https://sisoc.example/media/firmas/205578/entrevistado.png"


def _labels(instance):
    return [campo["label"] for campo in _bloque_campos(instance)]


def test_no_muestra_el_identificador_que_genera_la_app():
    asistencia = AsistenciaTecnicaSeguimiento(
        id_asistencia="app-i47-asistencia", socio_organizativo=1
    )

    campos = _bloque_campos(asistencia)

    assert [c["value"] for c in campos] == [1]
    assert "Id asistencia" not in _labels(asistencia)


def test_no_muestra_el_vinculo_interno_a_los_recursos_del_relevamiento():
    recursos = RecursosSeguimiento(recursos_comedor_estado_nacional=True)
    recursos.fuente_recursos_id = 99

    assert _labels(recursos) == ["Recursos comedor estado nacional"]


def test_la_firma_se_marca_como_imagen():
    cierre = CierreSeguimiento(comentarios_finales="test", firma_entrevistado=FIRMA)

    campos = {c["label"]: c for c in _bloque_campos(cierre)}

    assert campos["Firma entrevistado"]["es_imagen"] is True
    assert campos["Comentarios finales"]["es_imagen"] is False


@pytest.mark.django_db
def test_detalle_muestra_la_firma_como_imagen_y_sin_ids_en_tablas(client):
    user = get_user_model().objects.create_user(
        username="ver_seg_2643", password="testpass123"
    )
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="relevamientos", codename="view_relevamiento"
        )
    )
    client.force_login(user)
    provincia = Provincia.objects.create(nombre="Prov seg 2643")
    comedor = Comedor.objects.create(nombre="Comedor seg 2643", provincia=provincia)
    relevamiento = Relevamiento.objects.create(comedor=comedor, estado="Finalizado")
    seguimiento = PrimerSeguimiento.objects.create(
        id_relevamiento=relevamiento,
        estado=PrimerSeguimiento.ESTADO_COMPLETO,
        cierre=CierreSeguimiento.objects.create(
            comentarios_finales="test test", firma_entrevistado=FIRMA
        ),
    )
    PrestacionSeguimiento.objects.create(
        seguimiento=seguimiento,
        id_prestacion_seg="app-i47-prestacion-1",
        dias_prestacion="Lunes",
        tipo_prestacion="Almuerzo",
    )

    response = client.get(
        reverse(
            "seguimiento_detalle",
            kwargs={
                "comedor_pk": comedor.id,
                "relevamiento_pk": relevamiento.id,
                "pk": seguimiento.id,
            },
        )
    )

    html = response.content.decode()
    assert response.status_code == 200
    assert f'src="{FIRMA}"' in html
    assert f">{FIRMA}<" not in html
    assert "app-i47-prestacion-1" not in html
    assert "ID prestación" not in html
    assert "Lunes" in html
