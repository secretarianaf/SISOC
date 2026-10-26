"""Issue #2789: operaciones de soporte del admin de CDI (accesos de referentes)."""

from auditlog.models import LogEntry
from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import pytest

from centrodeinfancia import admin as cdi_admin
from centrodeinfancia.models import AccesoCDI, CentroDeInfancia, NominaCentroInfancia
from ciudadanos.models import Ciudadano
from core.admin_operaciones import ejecutar_operacion
from core.constants import UserGroups
from core.models import Provincia

pytestmark = pytest.mark.django_db

Estado = AccesoCDI.Estado


@pytest.fixture(autouse=True)
def _grupo_referente():
    # Las data migrations no corren en tests: el grupo que se delega no existe.
    Group.objects.get_or_create(name=UserGroups.CDI_REFERENTE_CENTRO)


@pytest.fixture(name="centro")
def centro_fixture():
    return CentroDeInfancia.objects.create(
        nombre="CDI Admin", provincia=Provincia.objects.create(nombre="Chaco")
    )


def _acceso(centro, username, **campos):
    user = User.objects.create_user(username=username, password="x")
    return AccesoCDI.objects.create(user=user, centro=centro, **campos)


def _ejecutar(slug, acceso, usuario, motivo=""):
    model_admin = admin.site._registry[AccesoCDI]  # pylint: disable=protected-access
    operacion = next(op for op in model_admin.operaciones if op.slug == slug)
    return ejecutar_operacion(
        operacion=operacion,
        objetos=[acceso],
        usuario=usuario,
        datos={"motivo": motivo},
    )


def _auditado(obj, slug):
    return LogEntry.objects.filter(
        object_pk=str(obj.pk), additional_data__operacion=slug
    ).exists()


@pytest.mark.parametrize(
    ("slug", "accion"),
    [("suspender", "suspender"), ("reactivar", "reactivar"), ("dar_de_baja", "baja")],
)
def test_operacion_llama_al_service(mocker, centro, superuser, slug, accion):
    acceso = _acceso(centro, f"ref-{slug}")
    servicio = mocker.patch.object(
        cdi_admin, "cambiar_estado_acceso", return_value=acceso
    )

    ok, _ = _ejecutar(slug, acceso, superuser, motivo="Pedido de la provincia")

    assert ok == [acceso]
    servicio.assert_called_once_with(
        actor=superuser,
        acceso=acceso,
        accion=accion,
        motivo="Pedido de la provincia",
    )
    assert _auditado(acceso, slug)


def test_suspender_reactivar_y_baja_reales(centro, superuser):
    acceso = _acceso(centro, "ref-real")

    _ejecutar("suspender", acceso, superuser, motivo="Licencia")
    acceso.refresh_from_db()
    suspendido = (acceso.estado, acceso.activo, acceso.motivo_estado)
    _ejecutar("reactivar", acceso, superuser)
    acceso.refresh_from_db()
    reactivado = acceso.estado
    _ejecutar("dar_de_baja", acceso, superuser, motivo="Dejó el centro")
    acceso.refresh_from_db()

    assert suspendido == (Estado.SUSPENDIDO, False, "Licencia")
    assert reactivado == Estado.ACTIVO
    assert acceso.estado == Estado.BAJA
    assert acceso.fecha_baja is not None
    entrada = LogEntry.objects.get(
        object_pk=str(acceso.pk), additional_data__operacion="dar_de_baja"
    )
    assert entrada.changes_dict == {"estado": [Estado.ACTIVO, Estado.BAJA]}


def test_reglas_del_service_se_informan_como_error(centro, superuser):
    responsable = _acceso(centro, "ref-responsable", es_responsable=True)
    dado_de_baja = _acceso(centro, "ref-baja", estado=Estado.BAJA)

    _, error_responsable = _ejecutar("suspender", responsable, superuser, "Prueba")
    _, error_baja = _ejecutar("reactivar", dado_de_baja, superuser)

    assert "responsable" in error_responsable[0][1]
    assert "No se puede reactivar" in error_baja[0][1]
    responsable.refresh_from_db()
    assert responsable.estado == Estado.ACTIVO
    assert not _auditado(responsable, "suspender")


def test_baja_es_destructiva_y_exige_motivo():
    model_admin = admin.site._registry[AccesoCDI]  # pylint: disable=protected-access
    baja = next(op for op in model_admin.operaciones if op.slug == "dar_de_baja")

    assert baja.destructiva and baja.motivo_obligatorio


def test_suspender_por_url_del_admin(auth_client, centro):
    acceso = _acceso(centro, "ref-url")
    url = reverse(
        "admin:centrodeinfancia_accesocdi_operacion_suspender", args=[acceso.pk]
    )

    sin_motivo = auth_client.post(url, {"confirmar_operacion": "1", "motivo": ""})
    acceso.refresh_from_db()
    estado_sin_motivo = acceso.estado
    respuesta = auth_client.post(
        url, {"confirmar_operacion": "1", "motivo": "Ticket de soporte 99"}
    )

    assert sin_motivo.status_code == 200
    assert estado_sin_motivo == Estado.ACTIVO
    assert respuesta.status_code == 302
    acceso.refresh_from_db()
    assert acceso.estado == Estado.SUSPENDIDO
    assert acceso.motivo_estado == "Ticket de soporte 99"
    assert _auditado(acceso, "suspender")


def _consultas(client, url):
    with CaptureQueriesContext(connection) as contexto:
        respuesta = client.get(url)
    assert respuesta.status_code == 200
    return len(contexto.captured_queries)


def _cargar(centro, desde, cantidad):
    for numero in range(desde, desde + cantidad):
        _acceso(centro, f"ref-n1-{numero}")
        ciudadano = Ciudadano.objects.create(
            apellido="Ape", nombre=f"N{numero}", documento=numero
        )
        NominaCentroInfancia.objects.create(
            centro=centro, ciudadano=ciudadano, dni=numero
        )


@pytest.mark.parametrize("modelo", [AccesoCDI, NominaCentroInfancia])
def test_listados_sin_n_mas_1(
    auth_client, centro, modelo, django_assert_max_num_queries
):
    url = reverse(
        f"admin:centrodeinfancia_{modelo._meta.model_name}_changelist"  # pylint: disable=protected-access
    )

    _cargar(centro, 50000000, 5)
    with django_assert_max_num_queries(10):
        consultas_con_5 = _consultas(auth_client, url)
    _cargar(centro, 50000100, 5)

    assert _consultas(auth_client, url) == consultas_con_5


def test_nomina_se_busca_por_documento(auth_client, centro):
    _cargar(centro, 50000200, 2)
    url = reverse("admin:centrodeinfancia_nominacentroinfancia_changelist")

    respuesta = auth_client.get(url, {"q": "50000201"})

    assert respuesta.status_code == 200
    assert respuesta.context["cl"].result_count == 1
