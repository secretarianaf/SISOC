"""Eliminación lógica en cascada de actividades de Abordaje Comunitario.

Inactivar es la baja operativa; eliminar es para cargas erróneas: la actividad
y sus inscriptos quedan con borrado lógico, dejan de verse y se pueden
restaurar tal como estaban.
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from admisiones.models.admisiones import Admision
from comedores.models import Comedor, Nomina, Programas
from core.models import Dia
from pwa.models import (
    ActividadEspacioPWA,
    AuditoriaOperacionPWA,
    CatalogoActividadPWA,
    InscriptoActividadEspacioPWA,
)


@pytest.fixture
def comedor(db):
    programa = Programas.objects.create(nombre="PNUD Abordaje eliminar")
    return Comedor.objects.create(nombre="Espacio eliminar", programa=programa)


@pytest.fixture
def actividad(comedor):
    catalogo = CatalogoActividadPWA.objects.create(
        categoria="Deporte", actividad="Fútbol eliminar"
    )
    dia, _ = Dia.objects.get_or_create(nombre="Lunes")
    return ActividadEspacioPWA.objects.create(
        comedor=comedor,
        catalogo_actividad=catalogo,
        dia_actividad=dia,
        hora_inicio=datetime.time(10, 0),
        hora_fin=datetime.time(11, 0),
        horario_actividad="10:00 a 11:00",
    )


@pytest.fixture
def inscriptos(comedor, actividad):
    """Una persona con inscripción vieja inactiva y otra activa, y una segunda."""
    admision = Admision.objects.create(comedor=comedor, activa=True)
    nomina_1 = Nomina.objects.create(admision=admision, estado=Nomina.ESTADO_ACTIVO)
    nomina_2 = Nomina.objects.create(admision=admision, estado=Nomina.ESTADO_ACTIVO)
    return [
        InscriptoActividadEspacioPWA.objects.create(
            actividad_espacio=actividad, nomina=nomina_1, activo=False
        ),
        InscriptoActividadEspacioPWA.objects.create(
            actividad_espacio=actividad, nomina=nomina_1, activo=True
        ),
        InscriptoActividadEspacioPWA.objects.create(
            actividad_espacio=actividad, nomina=nomina_2, activo=True
        ),
    ]


@pytest.fixture
def admin_client(client):
    admin = get_user_model().objects.create_superuser("admin_elim", "e@e.com", "x")
    client.force_login(admin)
    return client, admin


def _url(actividad):
    return reverse(
        "actividad_espacio_pwa_eliminar",
        kwargs={"pk": actividad.comedor_id, "pk2": actividad.pk},
    )


@pytest.mark.django_db
def test_confirmacion_muestra_la_cascada(admin_client, actividad, inscriptos):
    client, _ = admin_client

    response = client.get(_url(actividad))

    assert response.status_code == 200
    preview = response.context["cascade_preview"]
    assert preview["total_afectados"] == 1 + len(inscriptos)
    assert "Eliminar actividad" in response.content.decode()


@pytest.mark.django_db
def test_eliminar_hace_borrado_logico_en_cascada(admin_client, actividad, inscriptos):
    client, admin = admin_client

    response = client.post(_url(actividad))

    assert response.status_code == 302
    assert response.url.endswith("#legajo-actividades-pnud")
    assert not ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()
    assert not InscriptoActividadEspacioPWA.objects.filter(
        actividad_espacio_id=actividad.pk
    ).exists()

    actividad_db = ActividadEspacioPWA.all_objects.get(pk=actividad.pk)
    assert actividad_db.deleted_by == admin
    inscriptos_db = InscriptoActividadEspacioPWA.all_objects.filter(
        actividad_espacio_id=actividad.pk
    )
    assert all(inscripto.is_deleted for inscripto in inscriptos_db)
    # El estado operativo no cambia: se restaura tal como estaba.
    assert actividad_db.activo is True
    assert sorted(i.activo for i in inscriptos_db) == [False, True, True]

    evento = AuditoriaOperacionPWA.objects.get(
        entidad="actividad", entidad_id=actividad.pk, accion="delete"
    )
    assert sorted(evento.metadata["inscriptos_eliminados"]) == sorted(
        i.pk for i in inscriptos
    )


@pytest.mark.django_db
def test_eliminar_no_altera_la_nomina_ni_otras_actividades(
    admin_client, comedor, actividad, inscriptos
):
    client, _ = admin_client
    nomina = inscriptos[1].nomina
    otra_actividad = ActividadEspacioPWA.objects.create(
        comedor=comedor,
        catalogo_actividad=actividad.catalogo_actividad,
        dia_actividad=actividad.dia_actividad,
        hora_inicio=datetime.time(15, 0),
        hora_fin=datetime.time(16, 0),
        horario_actividad="15:00 a 16:00",
    )
    otra_inscripcion = InscriptoActividadEspacioPWA.objects.create(
        actividad_espacio=otra_actividad, nomina=nomina, activo=True
    )
    nomina_antes = Nomina.objects.filter(pk=nomina.pk).values().get()

    client.post(_url(actividad))

    assert Nomina.objects.filter(pk=nomina.pk).values().get() == nomina_antes
    otra_inscripcion.refresh_from_db()
    assert otra_inscripcion.activo is True
    assert not otra_inscripcion.is_deleted
    assert ActividadEspacioPWA.objects.filter(pk=otra_actividad.pk).exists()
    assert list(
        nomina.inscripciones_actividad_pwa.values_list("actividad_espacio_id", flat=True)
    ) == [otra_actividad.pk]


@pytest.mark.django_db
def test_pestania_actividades_de_nomina_ignora_inscripciones_eliminadas(
    admin_client, actividad, inscriptos
):
    # pylint: disable=import-outside-toplevel,protected-access
    from comedores.services.comedor_service import impl

    client, _ = admin_client
    nominas = Nomina.objects.filter(pk__in={i.nomina_id for i in inscriptos})
    assert impl._apply_nomina_tab_filter(nominas, "actividades").count() == 2

    client.post(_url(actividad))

    assert impl._apply_nomina_tab_filter(nominas, "actividades").count() == 0
    assert nominas.count() == 2


@pytest.mark.django_db
def test_se_puede_recargar_la_actividad_correcta_tras_eliminar(
    admin_client, actividad
):
    """El horario de la eliminada no bloquea cargar la actividad bien."""
    client, _ = admin_client
    client.post(_url(actividad))
    url = reverse("actividad_espacio_pwa_crear", kwargs={"pk": actividad.comedor_id})

    response = client.post(
        url,
        {
            "categoria": actividad.catalogo_actividad.categoria,
            "catalogo_actividad": actividad.catalogo_actividad_id,
            "schedule_grupo": ["0"],
            "schedule_dias_0": [actividad.dia_actividad_id],
            "schedule_hora_inicio": ["10:00"],
            "schedule_hora_fin": ["11:00"],
        },
    )

    assert response.status_code == 302
    assert ActividadEspacioPWA.objects.filter(comedor=actividad.comedor).count() == 1


@pytest.mark.django_db
def test_actividad_eliminada_no_aparece_en_el_legajo(admin_client, actividad):
    client, _ = admin_client
    detalle = reverse("comedor_detalle", kwargs={"pk": actividad.comedor_id})
    assert "Fútbol eliminar" in client.get(detalle).content.decode()

    client.post(_url(actividad))

    assert "Fútbol eliminar" not in client.get(detalle).content.decode()


@pytest.mark.django_db
def test_restaurar_devuelve_actividad_e_inscriptos(admin_client, actividad, inscriptos):
    client, admin = admin_client
    client.post(_url(actividad))

    ActividadEspacioPWA.all_objects.get(pk=actividad.pk).restore(user=admin)

    assert ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()
    assert InscriptoActividadEspacioPWA.objects.filter(
        actividad_espacio=actividad
    ).count() == len(inscriptos)


@pytest.mark.django_db
def test_eliminar_requiere_permiso(client, actividad):
    usuario = get_user_model().objects.create_user("sin_permiso", password="x")
    client.force_login(usuario)

    assert client.post(_url(actividad)).status_code == 403
    assert ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()


@pytest.mark.django_db
def test_no_elimina_actividades_de_otro_comedor(admin_client, actividad):
    client, _ = admin_client
    otro = Comedor.objects.create(
        nombre="Otro espacio", programa=actividad.comedor.programa
    )
    url = reverse(
        "actividad_espacio_pwa_eliminar", kwargs={"pk": otro.pk, "pk2": actividad.pk}
    )

    assert client.post(url).status_code == 404
    assert ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()
