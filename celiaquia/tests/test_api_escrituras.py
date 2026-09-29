"""Escrituras de la API REST de Celiaquia.

El foco esta en lo que la maqueta de React va a ejercitar y en lo que puede
romperse en silencio: que cada accion delegue en su service, que los permisos
por rol se respeten y que las reglas de transicion sean las mismas que aplica
la pantalla.
"""

from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse

from celiaquia.models import (
    EstadoExpediente,
    EstadoLegajo,
    Expediente,
    ExpedienteCiudadano,
    ProvinciaCupo,
    RevisionTecnico,
)
from ciudadanos.models import Ciudadano
from core.models import Localidad, Municipio, Provincia
from users.models import Profile, ProfileTerritorialScope

pytestmark = pytest.mark.django_db


def _grant(user, codename, model, name=None):
    content_type = ContentType.objects.get_for_model(model)
    perm, _ = Permission.objects.get_or_create(
        codename=codename,
        content_type=content_type,
        defaults={"name": name or codename},
    )
    user.user_permissions.add(perm)


def _coordinador(username="coord_w"):
    user = User.objects.create_user(username=username, password="pass")
    _grant(user, "view_expediente", Expediente)
    _grant(user, "role_coordinadorceliaquia", User, name="Coordinador Celiaquia")
    return user


def _tecnico(username="tecnico_w"):
    user = User.objects.create_user(username=username, password="pass")
    _grant(user, "view_expediente", Expediente)
    _grant(user, "role_tecnicoceliaquia", User, name="Tecnico Celiaquia")
    return user


def _provincial(username, provincia):
    user = User.objects.create_user(username=username, password="pass")
    _grant(user, "view_expediente", Expediente)
    _grant(user, "role_provinciaceliaquia", User, name="Provincia Celiaquia")
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.es_usuario_provincial = True
    profile.save()
    ProfileTerritorialScope.objects.create(profile=profile, provincia=provincia)
    return user


@pytest.fixture
def territorio():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Tolosa", municipio=municipio)
    return provincia, municipio, localidad


def _expediente_con_legajo(owner, territorio, doc, sufijo, estado="EN_CARGA"):
    provincia, municipio, localidad = territorio
    estado_exp, _ = EstadoExpediente.objects.get_or_create(nombre=estado)
    estado_legajo, _ = EstadoLegajo.objects.get_or_create(nombre="CARGADO")
    expediente = Expediente.objects.create(
        usuario_provincia=owner, estado=estado_exp, numero_expediente=f"EX-{sufijo}"
    )
    ciudadano = Ciudadano.objects.create(
        apellido="Perez",
        nombre="Ana",
        documento=doc,
        fecha_nacimiento=date(1990, 1, 1),
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
    )
    legajo = ExpedienteCiudadano.objects.create(
        expediente=expediente, ciudadano=ciudadano, estado=estado_legajo
    )
    return expediente, legajo


# --- Alta y edicion de expedientes -----------------------------------------


def test_provincial_crea_expediente_por_la_api(client, territorio):
    owner = _provincial("prov_crea", territorio[0])
    EstadoExpediente.objects.get_or_create(nombre="CREADO")
    client.force_login(owner)

    response = client.post(
        reverse("celiaquia-expediente-list"),
        {"numero_expediente": "EX-NUEVO", "observaciones": "carga inicial"},
    )

    assert response.status_code == 201
    creado = Expediente.objects.get(pk=response.json()["id"])
    # El expediente queda a nombre de quien lo crea: eso define su alcance.
    assert creado.usuario_provincia == owner
    assert creado.estado.nombre == "CREADO"


def test_el_alta_delega_en_el_service(client, territorio):
    owner = _provincial("prov_delega", territorio[0])
    EstadoExpediente.objects.get_or_create(nombre="CREADO")
    client.force_login(owner)

    with patch(
        "celiaquia.api_views.ExpedienteService.create_expediente"
    ) as create_mock:
        create_mock.return_value = _expediente_con_legajo(
            owner, territorio, "30999111", "SRV"
        )[0]
        client.post(reverse("celiaquia-expediente-list"), {"observaciones": "x"})

    assert create_mock.called


def test_no_se_editan_metadatos_fuera_de_creado(client, territorio):
    owner = _provincial("prov_edita", territorio[0])
    expediente, _ = _expediente_con_legajo(
        owner, territorio, "30111222", "ED", estado="EN_ESPERA"
    )
    client.force_login(owner)

    response = client.patch(
        reverse("celiaquia-expediente-detail", kwargs={"pk": expediente.pk}),
        {"observaciones": "tarde"},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_solo_coordinacion_elimina_expedientes(client, territorio):
    owner = _provincial("prov_borra", territorio[0])
    expediente, _ = _expediente_con_legajo(owner, territorio, "30111333", "DEL")
    client.force_login(owner)

    response = client.delete(
        reverse("celiaquia-expediente-detail", kwargs={"pk": expediente.pk})
    )

    assert response.status_code == 403


# --- Recepcion --------------------------------------------------------------


def test_coordinacion_recepciona_un_expediente_confirmado(client, territorio):
    owner = _provincial("prov_recep", territorio[0])
    coord = _coordinador("coord_recep")
    expediente, _ = _expediente_con_legajo(
        owner, territorio, "30111444", "REC", estado="CONFIRMACION_DE_ENVIO"
    )
    EstadoExpediente.objects.get_or_create(nombre="RECEPCIONADO")
    client.force_login(coord)

    response = client.post(
        reverse("celiaquia-expediente-recepcionar", kwargs={"pk": expediente.pk})
    )

    expediente.refresh_from_db()
    assert response.status_code == 200
    assert expediente.estado.nombre == "RECEPCIONADO"


def test_no_se_recepciona_un_expediente_en_otro_estado(client, territorio):
    owner = _provincial("prov_recep2", territorio[0])
    coord = _coordinador("coord_recep2")
    expediente, _ = _expediente_con_legajo(
        owner, territorio, "30111555", "REC2", estado="EN_CARGA"
    )
    client.force_login(coord)

    response = client.post(
        reverse("celiaquia-expediente-recepcionar", kwargs={"pk": expediente.pk})
    )

    assert response.status_code == 400


def test_la_provincia_no_recepciona(client, territorio):
    owner = _provincial("prov_recep3", territorio[0])
    expediente, _ = _expediente_con_legajo(
        owner, territorio, "30111666", "REC3", estado="CONFIRMACION_DE_ENVIO"
    )
    client.force_login(owner)

    response = client.post(
        reverse("celiaquia-expediente-recepcionar", kwargs={"pk": expediente.pk})
    )

    assert response.status_code == 403


# --- Revision tecnica -------------------------------------------------------


def test_coordinacion_aprueba_un_legajo(client, territorio):
    owner = _provincial("prov_rev", territorio[0])
    coord = _coordinador("coord_rev")
    _, legajo = _expediente_con_legajo(owner, territorio, "30111777", "REV")
    client.force_login(coord)

    response = client.post(
        reverse("celiaquia-legajo-revisar", kwargs={"pk": legajo.pk}),
        {"accion": "APROBAR"},
        content_type="application/json",
    )

    legajo.refresh_from_db()
    assert response.status_code == 200
    assert legajo.revision_tecnico == RevisionTecnico.APROBADO
    # Un legajo aprobado no puede quedar con RENAPER sin validar.
    assert legajo.estado_validacion_renaper == 1


def test_no_se_revisa_dos_veces_un_legajo_aprobado(client, territorio):
    owner = _provincial("prov_rev2", territorio[0])
    coord = _coordinador("coord_rev2")
    _, legajo = _expediente_con_legajo(owner, territorio, "30111888", "REV2")
    legajo.revision_tecnico = RevisionTecnico.APROBADO
    legajo.save(update_fields=["revision_tecnico"])
    client.force_login(coord)

    response = client.post(
        reverse("celiaquia-legajo-revisar", kwargs={"pk": legajo.pk}),
        {"accion": "RECHAZAR"},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_la_provincia_no_aprueba_legajos(client, territorio):
    owner = _provincial("prov_rev3", territorio[0])
    _, legajo = _expediente_con_legajo(owner, territorio, "30111999", "REV3")
    client.force_login(owner)

    response = client.post(
        reverse("celiaquia-legajo-revisar", kwargs={"pk": legajo.pk}),
        {"accion": "APROBAR"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_el_tecnico_no_asignado_no_revisa(client, territorio):
    """404 y no 403: el legajo no entra en el alcance del tecnico.

    El alcance se aplica en `get_queryset()`, asi que un expediente que no le
    fue asignado no existe para el. Responder 403 confirmaria que existe.
    """

    owner = _provincial("prov_rev4", territorio[0])
    tecnico = _tecnico("tecnico_suelto")
    _, legajo = _expediente_con_legajo(owner, territorio, "30112111", "REV4")
    client.force_login(tecnico)

    response = client.post(
        reverse("celiaquia-legajo-revisar", kwargs={"pk": legajo.pk}),
        {"accion": "APROBAR"},
        content_type="application/json",
    )

    assert response.status_code == 404
    legajo.refresh_from_db()
    assert legajo.revision_tecnico == RevisionTecnico.PENDIENTE


def test_una_accion_invalida_no_toca_el_legajo(client, territorio):
    owner = _provincial("prov_rev5", territorio[0])
    coord = _coordinador("coord_rev5")
    _, legajo = _expediente_con_legajo(owner, territorio, "30112222", "REV5")
    client.force_login(coord)

    response = client.post(
        reverse("celiaquia-legajo-revisar", kwargs={"pk": legajo.pk}),
        {"accion": "ARCHIVAR"},
        content_type="application/json",
    )

    legajo.refresh_from_db()
    assert response.status_code == 400
    assert legajo.revision_tecnico == RevisionTecnico.PENDIENTE


# --- Cupos ------------------------------------------------------------------


def test_coordinacion_configura_el_cupo_de_una_provincia(client, territorio):
    coord = _coordinador("coord_cupo")
    provincia = territorio[0]
    client.force_login(coord)

    response = client.post(
        reverse("celiaquia-cupo-configurar", kwargs={"provincia_id": provincia.pk}),
        {"total_asignado": 500},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert ProvinciaCupo.objects.get(provincia=provincia).total_asignado == 500


def test_configurar_cupo_crea_el_registro_si_no_existia(client, territorio):
    coord = _coordinador("coord_cupo2")
    provincia = territorio[0]
    assert not ProvinciaCupo.objects.filter(provincia=provincia).exists()
    client.force_login(coord)

    client.post(
        reverse("celiaquia-cupo-configurar", kwargs={"provincia_id": provincia.pk}),
        {"total_asignado": 10},
        content_type="application/json",
    )

    assert ProvinciaCupo.objects.filter(provincia=provincia).exists()


def test_la_provincia_no_configura_su_propio_cupo(client, territorio):
    owner = _provincial("prov_cupo", territorio[0])
    client.force_login(owner)

    response = client.post(
        reverse("celiaquia-cupo-configurar", kwargs={"provincia_id": territorio[0].pk}),
        {"total_asignado": 999},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_la_baja_de_cupo_delega_en_el_service(client, territorio):
    owner = _provincial("prov_baja", territorio[0])
    coord = _coordinador("coord_baja")
    _, legajo = _expediente_con_legajo(owner, territorio, "30112333", "BAJA")
    client.force_login(coord)

    with patch("celiaquia.api_views.CupoService.liberar_slot") as liberar:
        response = client.post(
            reverse("celiaquia-cupo-baja-legajo", kwargs={"legajo_id": legajo.pk}),
            {"motivo": "baja solicitada"},
            content_type="application/json",
        )

    assert response.status_code == 200
    assert liberar.called
    assert liberar.call_args.kwargs["motivo"] == "baja solicitada"


def test_el_error_del_service_de_cupo_se_traduce_a_400(client, territorio):
    owner = _provincial("prov_susp", territorio[0])
    coord = _coordinador("coord_susp")
    _, legajo = _expediente_con_legajo(owner, territorio, "30112444", "SUSP")
    client.force_login(coord)

    with patch(
        "celiaquia.api_views.CupoService.suspender_slot",
        side_effect=DjangoValidationError("El legajo no esta dentro del cupo."),
    ):
        response = client.post(
            reverse("celiaquia-cupo-suspender-legajo", kwargs={"legajo_id": legajo.pk}),
            {},
            content_type="application/json",
        )

    assert response.status_code == 400


def test_no_se_opera_el_cupo_de_un_legajo_fuera_de_alcance(client, territorio):
    otra_provincia = Provincia.objects.create(nombre="Salta")
    otro_municipio = Municipio.objects.create(
        nombre="Capital", provincia=otra_provincia
    )
    otra_localidad = Localidad.objects.create(nombre="Centro", municipio=otro_municipio)
    ajeno_owner = _provincial("prov_ajena", otra_provincia)
    _, legajo_ajeno = _expediente_con_legajo(
        ajeno_owner,
        (otra_provincia, otro_municipio, otra_localidad),
        "30112555",
        "AJENO",
    )
    propio = _provincial("prov_propia", territorio[0])
    client.force_login(propio)

    response = client.post(
        reverse("celiaquia-cupo-baja-legajo", kwargs={"legajo_id": legajo_ajeno.pk}),
        {},
        content_type="application/json",
    )

    # 403 por rol antes que 404: el provincial no gestiona cupo en ningun caso.
    assert response.status_code == 403


# --- Pagos ------------------------------------------------------------------


def test_la_creacion_de_pago_delega_en_el_service(client, territorio):
    coord = _coordinador("coord_pago")
    client.force_login(coord)

    with patch("celiaquia.api_views.PagoService.crear_expediente_pago") as crear:
        crear.return_value = None
        client.post(
            reverse("celiaquia-pago-list"),
            {"provincia_id": territorio[0].pk, "periodo": "2026-03"},
            content_type="application/json",
        )

    assert crear.called
    assert crear.call_args.kwargs["periodo"] == "2026-03"


def test_la_provincia_no_genera_expedientes_de_pago(client, territorio):
    owner = _provincial("prov_pago", territorio[0])
    client.force_login(owner)

    response = client.post(
        reverse("celiaquia-pago-list"),
        {"provincia_id": territorio[0].pk},
        content_type="application/json",
    )

    assert response.status_code == 403
