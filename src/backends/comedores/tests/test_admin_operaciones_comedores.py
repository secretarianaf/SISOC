"""Issue #2789 (Fase 2): operaciones de soporte del admin en comedores.

Cada operación delega en el service existente y deja un ``auditlog.LogEntry``
con la operación. Los listados principales no hacen N+1.
"""

from datetime import date

import pytest
from auditlog.models import LogEntry
from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from ciudadanos.models import Ciudadano
from comedores.models import (
    ColaboradorEspacio,
    Comedor,
    EstadoActividad,
    EstadoDetalle,
    EstadoProceso,
    HistorialValidacion,
    Nomina,
    Programas,
)
from comunicados.models import Comunicado, EstadoComunicado, MailingJob
from core.admin_operaciones import ejecutar_operacion
from core.models import Dia, Municipio, Provincia
from pwa.models import (
    ActividadEspacioPWA,
    CatalogoActividadPWA,
    CoordinadorEquipoTecnicoPWA,
)

MOTIVO = "Pedido de soporte 2789"


def _operacion(model, slug):
    model_admin = django_admin.site.get_model_admin(model)
    return next(op for op in model_admin.operaciones if op.slug == slug)


def _ejecutar(model, slug, obj, usuario, **datos):
    return ejecutar_operacion(
        operacion=_operacion(model, slug),
        objetos=[obj],
        usuario=usuario,
        datos={"motivo": MOTIVO, **datos},
    )


def _log_de(obj, slug):
    return LogEntry.objects.get_for_object(obj).filter(additional_data__operacion=slug)


@pytest.fixture(name="provincia")
def provincia_fixture(db):
    return Provincia.objects.create(nombre="Provincia Admin 2789")


@pytest.fixture(name="programa")
def programa_fixture(db):
    return Programas.objects.create(nombre="Programa Admin 2789")


@pytest.fixture(name="comedor")
def comedor_fixture(provincia, programa):
    return Comedor.objects.create(
        nombre="Comedor Admin 2789", provincia=provincia, programa=programa
    )


def _ciudadano(documento):
    return Ciudadano.objects.create(
        tipo_documento=Ciudadano.DOCUMENTO_DNI,
        documento=documento,
        apellido=f"Apellido {documento}",
        nombre="Ana",
        fecha_nacimiento="1990-01-15",
    )


@pytest.fixture(name="ciudadano")
def ciudadano_fixture(db):
    return _ciudadano(30111222)


@pytest.fixture(name="estado_en_ejecucion")
def estado_en_ejecucion_fixture(db):
    actividad = EstadoActividad.objects.create(estado="Activo")
    return EstadoProceso.objects.create(
        estado="En ejecución", estado_actividad=actividad
    )


# --- Comedor ----------------------------------------------------------------


@pytest.mark.django_db
def test_cambiar_estado_llama_al_estado_manager(
    mocker, comedor, superuser, estado_en_ejecucion
):
    registrar = mocker.patch("comedores.admin.registrar_cambio_estado")

    ok, errores = _ejecutar(
        Comedor, "cambiar_estado", comedor, superuser, subestado=estado_en_ejecucion
    )

    assert ok == [comedor] and errores == []
    registrar.assert_called_once_with(
        comedor=comedor,
        actividad=estado_en_ejecucion.estado_actividad,
        proceso=estado_en_ejecucion,
        detalle=None,
        usuario=superuser,
    )
    assert _log_de(comedor, "cambiar_estado").exists()


@pytest.mark.django_db
def test_cambiar_estado_rechaza_motivo_de_otro_subestado(
    comedor, superuser, estado_en_ejecucion
):
    otro = EstadoProceso.objects.create(
        estado="Otro", estado_actividad=estado_en_ejecucion.estado_actividad
    )
    detalle_ajeno = EstadoDetalle.objects.create(estado="Ajeno", estado_proceso=otro)

    ok, errores = _ejecutar(
        Comedor,
        "cambiar_estado",
        comedor,
        superuser,
        subestado=estado_en_ejecucion,
        motivo_estado=detalle_ajeno,
    )

    assert not ok and len(errores) == 1
    comedor.refresh_from_db()
    assert comedor.ultimo_estado is None


@pytest.mark.django_db
def test_cambiar_estado_end_to_end_por_url(
    auth_client, comedor, superuser, estado_en_ejecucion
):
    url = reverse("admin:comedores_comedor_operacion_cambiar_estado", args=[comedor.pk])

    response = auth_client.post(
        url,
        {
            "confirmar_operacion": "1",
            "motivo": MOTIVO,
            "subestado": estado_en_ejecucion.pk,
        },
    )

    assert response.status_code == 302
    comedor.refresh_from_db()
    assert comedor.ultimo_estado.estado_general.estado_proceso == estado_en_ejecucion
    assert comedor.ultimo_estado.usuario == superuser
    log = _log_de(comedor, "cambiar_estado").get()
    assert log.changes_dict == {"ultimo_estado": [None, str(comedor.ultimo_estado_id)]}


@pytest.mark.django_db
def test_validar_y_no_validar_llaman_al_service(mocker, comedor, superuser):
    validar = mocker.patch(
        "comedores.admin.ValidacionService.validar_comedor",
        return_value=(True, "ok"),
    )

    _ejecutar(Comedor, "validar", comedor, superuser)
    _ejecutar(
        Comedor, "no_validar", comedor, superuser, opciones=["sin_movimiento", "otro"]
    )

    assert validar.call_args_list == [
        mocker.call(
            comedor_id=comedor.pk, user=superuser, accion="validar", comentario=MOTIVO
        ),
        mocker.call(
            comedor_id=comedor.pk,
            user=superuser,
            accion="no_validar",
            opciones=["sin_movimiento", "otro"],
            comentario=MOTIVO,
        ),
    ]
    assert _log_de(comedor, "validar").exists()
    assert _log_de(comedor, "no_validar").exists()


@pytest.mark.django_db
def test_no_validar_real_deja_historial(comedor, superuser):
    ok, _ = _ejecutar(
        Comedor,
        "no_validar",
        comedor,
        superuser,
        opciones=["no_corresponde_a_la_dupla", "otro"],
    )

    assert ok == [comedor]
    comedor.refresh_from_db()
    assert comedor.estado_validacion == "No Validado"
    historial = HistorialValidacion.objects.get(comedor=comedor)
    assert historial.opciones_no_validar == ["no_corresponde_a_la_dupla", "otro"]
    assert historial.comentario == MOTIVO
    assert _log_de(comedor, "no_validar").get().changes_dict == {
        "estado_validacion": ["Pendiente", "No Validado"]
    }


@pytest.mark.django_db
def test_validar_con_error_del_service_no_registra(mocker, comedor, superuser):
    mocker.patch(
        "comedores.admin.ValidacionService.validar_comedor",
        return_value=(False, "Acción no válida."),
    )

    ok, errores = _ejecutar(Comedor, "validar", comedor, superuser)

    assert not ok and errores == [(comedor, "Acción no válida.")]
    assert not _log_de(comedor, "validar").exists()


@pytest.mark.django_db
def test_reenviar_a_gestionar_al_confirmar(
    mocker, comedor, superuser, settings, django_capture_on_commit_callbacks
):
    settings.GESTIONAR_INTEGRATION_ENABLED = True
    tarea = mocker.patch("comedores.admin.AsyncSendComedorToGestionar")
    payload = mocker.patch(
        "comedores.admin.build_comedor_payload", return_value={"Rows": []}
    )

    with django_capture_on_commit_callbacks(execute=True):
        ok, _ = _ejecutar(Comedor, "reenviar_gestionar", comedor, superuser)

    assert ok == [comedor]
    payload.assert_called_once_with(comedor)
    tarea.assert_called_once_with({"Rows": []})
    tarea.return_value.start.assert_called_once_with()
    assert _log_de(comedor, "reenviar_gestionar").exists()


@pytest.mark.django_db
def test_reenviar_a_gestionar_con_integracion_deshabilitada(
    mocker, comedor, superuser, settings
):
    settings.GESTIONAR_INTEGRATION_ENABLED = False
    tarea = mocker.patch("comedores.admin.AsyncSendComedorToGestionar")

    ok, errores = _ejecutar(Comedor, "reenviar_gestionar", comedor, superuser)

    assert not ok and len(errores) == 1
    tarea.assert_not_called()


# --- Nómina y colaboradores ---------------------------------------------------


@pytest.mark.django_db
def test_baja_de_nomina_llama_al_service(mocker, comedor, ciudadano, superuser):
    nomina = Nomina.objects.create(comedor=comedor, ciudadano=ciudadano)
    baja = mocker.patch("comedores.admin.soft_delete_nomina_persona")

    ok, _ = _ejecutar(Nomina, "baja", nomina, superuser)

    assert ok == [nomina]
    baja.assert_called_once_with(nomina=nomina, actor=superuser)
    assert _log_de(nomina, "baja").exists()


@pytest.mark.django_db
def test_baja_de_nomina_end_to_end_por_url(auth_client, comedor, ciudadano):
    nomina = Nomina.objects.create(comedor=comedor, ciudadano=ciudadano)
    url = reverse("admin:comedores_nomina_operacion_baja", args=[nomina.pk])

    response = auth_client.post(url, {"confirmar_operacion": "1", "motivo": MOTIVO})

    assert response.status_code == 302
    nomina.refresh_from_db()
    assert nomina.estado == Nomina.ESTADO_BAJA
    assert _log_de(nomina, "baja").get().changes_dict == {"estado": ["activo", "baja"]}


@pytest.mark.django_db
def test_baja_de_colaborador_llama_al_service(mocker, comedor, ciudadano, superuser):
    colaborador = ColaboradorEspacio.objects.create(
        comedor=comedor, ciudadano=ciudadano, fecha_alta=date(2026, 1, 1)
    )
    baja = mocker.patch(
        "comedores.admin.ColaboradorEspacioService.soft_delete",
        return_value={"success": True, "message": "ok"},
    )

    ok, _ = _ejecutar(ColaboradorEspacio, "baja", colaborador, superuser)

    assert ok == [colaborador]
    baja.assert_called_once_with(colaborador=colaborador, actor=superuser)
    assert _log_de(colaborador, "baja").exists()


@pytest.mark.django_db
def test_baja_de_colaborador_ya_dado_de_baja_es_error(comedor, ciudadano, superuser):
    colaborador = ColaboradorEspacio.objects.create(
        comedor=comedor,
        ciudadano=ciudadano,
        fecha_alta=date(2026, 1, 1),
        fecha_baja=date(2026, 2, 1),
    )

    ok, errores = _ejecutar(ColaboradorEspacio, "baja", colaborador, superuser)

    assert not ok and len(errores) == 1


# --- Comunicados ------------------------------------------------------------


@pytest.fixture(name="comunicado")
def comunicado_fixture(superuser):
    return Comunicado.objects.create(
        titulo="Aviso", cuerpo="Texto", usuario_creador=superuser
    )


@pytest.mark.django_db
def test_publicar_y_archivar_llaman_al_modelo(mocker, comunicado, superuser):
    publicar = mocker.patch.object(Comunicado, "publicar", autospec=True)
    archivar = mocker.patch.object(Comunicado, "archivar", autospec=True)

    _ejecutar(Comunicado, "publicar", comunicado, superuser)
    _ejecutar(Comunicado, "archivar", comunicado, superuser)

    publicar.assert_called_once_with(comunicado, superuser)
    archivar.assert_called_once_with(comunicado, superuser)
    assert _log_de(comunicado, "publicar").exists()
    assert _log_de(comunicado, "archivar").exists()


@pytest.mark.django_db
def test_no_se_publica_un_comunicado_archivado(comunicado, superuser):
    comunicado.estado = EstadoComunicado.ARCHIVADO
    comunicado.save()

    ok, errores = _ejecutar(Comunicado, "publicar", comunicado, superuser)

    assert not ok
    assert errores == [(comunicado, "No se puede publicar un comunicado archivado.")]


@pytest.mark.django_db
def test_publicar_end_to_end_por_url(auth_client, comunicado, superuser):
    url = reverse(
        "admin:comunicados_comunicado_operacion_publicar", args=[comunicado.pk]
    )

    response = auth_client.post(url, {"confirmar_operacion": "1", "motivo": MOTIVO})

    assert response.status_code == 302
    comunicado.refresh_from_db()
    assert comunicado.estado == EstadoComunicado.PUBLICADO
    assert comunicado.usuario_ultima_modificacion == superuser
    assert _log_de(comunicado, "publicar").exists()


@pytest.fixture(name="mailing_job")
def mailing_job_fixture(superuser):
    return MailingJob.objects.create(
        requested_by=superuser,
        archivo="comunicados/mailing/jobs/lote.xlsx",
        original_filename="lote.xlsx",
        asunto="Asunto",
        cuerpo="Cuerpo",
        status=MailingJob.Status.FAILED,
    )


@pytest.mark.django_db
def test_reanudar_mailing_llama_al_service(mocker, mailing_job, superuser):
    reanudar = mocker.patch("comunicados.admin.request_resume_mailing_job")

    ok, _ = _ejecutar(MailingJob, "reanudar", mailing_job, superuser)

    assert ok == [mailing_job]
    reanudar.assert_called_once_with(job=mailing_job)
    assert _log_de(mailing_job, "reanudar").exists()


@pytest.mark.django_db
def test_reanudar_mailing_real_solo_si_fallo(mailing_job, superuser):
    ok, _ = _ejecutar(MailingJob, "reanudar", mailing_job, superuser)
    mailing_job.refresh_from_db()
    ok_repetido, errores = _ejecutar(MailingJob, "reanudar", mailing_job, superuser)

    assert ok == [mailing_job]
    assert mailing_job.status == MailingJob.Status.PENDING
    assert mailing_job.resume_count == 1
    assert not ok_repetido and len(errores) == 1


# --- PWA --------------------------------------------------------------------


@pytest.mark.django_db
def test_baja_de_actividad_pwa_llama_al_service(mocker, comedor, superuser):
    actividad = ActividadEspacioPWA.objects.create(
        comedor=comedor,
        catalogo_actividad=CatalogoActividadPWA.objects.create(
            categoria="Deporte", actividad="Fútbol"
        ),
        dia_actividad=Dia.objects.create(nombre="Lunes"),
        horario_actividad="10 a 12",
    )
    baja = mocker.patch("pwa.admin.soft_delete_actividad_espacio")

    ok, _ = _ejecutar(ActividadEspacioPWA, "baja", actividad, superuser)

    assert ok == [actividad]
    baja.assert_called_once_with(actividad=actividad, actor=superuser)
    assert _log_de(actividad, "baja").exists()


@pytest.mark.django_db
def test_desactivar_coordinador_pwa(mocker, superuser):
    usuario = get_user_model().objects.create_user(username="coord_2789")
    coordinador = CoordinadorEquipoTecnicoPWA.objects.create(user=usuario)
    desactivar = mocker.patch(
        "pwa.admin.deactivate_coordinador_equipo_tecnico_pwa_access"
    )

    ok, _ = _ejecutar(CoordinadorEquipoTecnicoPWA, "desactivar", coordinador, superuser)

    assert ok == [coordinador]
    desactivar.assert_called_once_with(usuario)
    assert _log_de(coordinador, "desactivar").exists()


@pytest.mark.django_db
def test_desactivar_coordinador_pwa_end_to_end_por_url(auth_client):
    usuario = get_user_model().objects.create_user(username="coord_2789_e2e")
    coordinador = CoordinadorEquipoTecnicoPWA.objects.create(user=usuario)
    url = reverse(
        "admin:pwa_coordinadorequipotecnicopwa_operacion_desactivar",
        args=[coordinador.pk],
    )

    response = auth_client.post(url, {"confirmar_operacion": "1", "motivo": MOTIVO})

    assert response.status_code == 302
    coordinador.refresh_from_db()
    assert coordinador.activo is False
    assert _log_de(coordinador, "desactivar").get().changes_dict == {
        "activo": ["True", "False"]
    }


# --- N+1 en los listados principales ------------------------------------------


def _consultas_del_listado(client, model):
    url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")
    with CaptureQueriesContext(connection) as contexto:
        response = client.get(url)
    assert response.status_code == 200
    return len(contexto.captured_queries)


def _crear_comedores(provincia, desde, cantidad):
    for numero in range(desde, desde + cantidad):
        Comedor.objects.create(
            nombre=f"Comedor {numero}",
            provincia=provincia,
            programa=Programas.objects.create(nombre=f"Programa {numero}"),
            municipio=Municipio.objects.create(
                nombre=f"Municipio {numero}", provincia=provincia
            ),
        )


def _crear_nominas_y_colaboradores(desde, cantidad):
    for numero in range(desde, desde + cantidad):
        comedor = Comedor.objects.create(nombre=f"Espacio {numero}")
        ciudadano = _ciudadano(40000000 + numero)
        Nomina.objects.create(comedor=comedor, ciudadano=ciudadano)
        ColaboradorEspacio.objects.create(
            comedor=comedor, ciudadano=ciudadano, fecha_alta=date(2026, 1, 1)
        )


@pytest.mark.django_db
@pytest.mark.parametrize("model", [Comedor, Nomina, ColaboradorEspacio])
def test_listados_principales_sin_n_mas_1(
    auth_client, provincia, model, django_assert_max_num_queries
):
    _crear_comedores(provincia, 0, 5)
    _crear_nominas_y_colaboradores(0, 5)
    con_cinco = _consultas_del_listado(auth_client, model)
    _crear_comedores(provincia, 5, 5)
    _crear_nominas_y_colaboradores(5, 5)

    with django_assert_max_num_queries(12):
        con_diez = _consultas_del_listado(auth_client, model)

    assert con_diez == con_cinco


@pytest.mark.django_db
@pytest.mark.parametrize(
    "slug", ["cambiar_estado", "validar", "no_validar", "reenviar_gestionar"]
)
def test_pantallas_de_confirmacion_de_comedor(
    auth_client, comedor, estado_en_ejecucion, slug
):
    url = reverse(f"admin:comedores_comedor_operacion_{slug}", args=[comedor.pk])

    response = auth_client.get(url)

    assert response.status_code == 200
    assert response.template_name == "admin/sisoc/confirmar_operacion.html"
    if slug == "cambiar_estado":
        assert "Activo / En ejecución" in response.content.decode()


@pytest.mark.django_db
def test_no_validar_end_to_end_con_varias_opciones(auth_client, comedor):
    url = reverse("admin:comedores_comedor_operacion_no_validar", args=[comedor.pk])

    response = auth_client.post(
        url,
        {
            "confirmar_operacion": "1",
            "motivo": MOTIVO,
            "opciones": ["sin_movimiento", "pac_inexistente_o_no_coincide"],
        },
    )

    assert response.status_code == 302
    historial = HistorialValidacion.objects.get(comedor=comedor)
    assert historial.opciones_no_validar == [
        "sin_movimiento",
        "pac_inexistente_o_no_coincide",
    ]
    assert _log_de(comedor, "no_validar").exists()
