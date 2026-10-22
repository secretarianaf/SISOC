"""Adaptador local: identidad, accesos y checkpoint permanecen atómicos."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import User, Group, Permission
from django.core.exceptions import ValidationError

from comedores.models import Comedor
from organizaciones.models import Organizacion
from pwa.models import AccesoComedorPWA
from users import pwa_import_access as port
from users.models import UserImportJob, UserImportJobRow
from usuarios.services_user_import import process_single_user_import_row
from usuarios import services_user_import_jobs as worker

pytestmark = pytest.mark.django_db


def _fila(**kwargs):
    return {
        "username": "importado_c2",
        "nombre": "Persona",
        "apellido": "C2",
        "rol": "operadora",
        **kwargs,
    }


@pytest.fixture
def admin():
    return User.objects.create_superuser(username="actor_importacion")


@pytest.mark.parametrize("inspecciones", (False, True))
def test_sin_adaptador_importa_filas_independientes(monkeypatch, admin, inspecciones):
    monkeypatch.setattr(port, "_adaptador", None)
    monkeypatch.setattr(port, "_resolver", None)
    row = _fila()
    if inspecciones:
        row.update(
            inspecciones="inspector", dni="30111222", correo="inspector@example.com"
        )
    job = SimpleNamespace(requested_by=admin, is_pwa_import=inspecciones)
    result = process_single_user_import_row(row_data=row, job=job)
    assert result["status"] == UserImportJobRow.Status.CREATED
    user = User.objects.get(username=row["username"])
    assert user.profile.es_inspector_escolar is inspecciones
    assert user.is_staff is not inspecciones
    assert user.profile.acceso_web is not inspecciones


@pytest.mark.parametrize(
    "fields",
    (
        {"comedores": "1"},
        {"organizaciones": "1"},
        {"permisos": "manage_nomina_pwa"},
        {},
    ),
)
def test_sin_adaptador_rechaza_dependencia_antes_de_escribir(
    monkeypatch, admin, fields
):
    monkeypatch.setattr(port, "_adaptador", None)
    job = SimpleNamespace(requested_by=admin, is_pwa_import=True)
    with pytest.raises(ValidationError, match="no está disponible"):
        process_single_user_import_row(row_data=_fila(**fields), job=job)
    assert not User.objects.filter(username="importado_c2").exists()


@pytest.mark.parametrize("tipo", ("grupo", "permiso"))
def test_sin_adaptador_no_omite_revocacion_dependiente(monkeypatch, admin, tipo):
    user = User.objects.create_user(username="antes_c2")
    permiso = Permission.objects.get(
        content_type__app_label="pwa", codename="manage_nomina_pwa"
    )
    if tipo == "grupo":
        group = Group.objects.create(name="Acceso dependiente C2")
        group.permissions.add(permiso)
        user.groups.add(group)
    else:
        user.user_permissions.add(permiso)
    monkeypatch.setattr(port, "_adaptador", None)
    with pytest.raises(ValidationError, match="no está disponible"):
        process_single_user_import_row(
            row_data=_fila(
                username=user.username,
                correo="nuevo@example.com",
                accion_grupos="reemplazar",
            ),
            job=SimpleNamespace(requested_by=admin, is_pwa_import=False),
        )
    user.refresh_from_db()
    assert user.email == ""
    assert user.has_perm("pwa.manage_nomina_pwa")


def test_adaptador_expande_organizacion_y_prioriza_su_asociacion(admin):
    org = Organizacion.objects.create(nombre="Organización C2")
    comedor = Comedor.objects.create(nombre="Espacio C2", organizacion=org)
    result = process_single_user_import_row(
        row_data=_fila(organizaciones=str(org.pk), comedores=str(comedor.pk)),
        job=SimpleNamespace(requested_by=admin, is_pwa_import=True),
    )
    access = AccesoComedorPWA.objects.get(
        user_id=result["created_user_id"], comedor=comedor
    )
    assert access.activo
    assert access.tipo_asociacion == AccesoComedorPWA.TIPO_ASOCIACION_ORGANIZACION
    assert access.organizacion_id == org.pk


@pytest.mark.parametrize("existente", (False, True))
def test_fallo_del_adaptador_revierte_usuario_y_accesos(monkeypatch, admin, existente):
    comedor = Comedor.objects.create(nombre="Espacio rollback")
    user = User.objects.create_user(username="importado_c2") if existente else None
    original = port._adaptador

    def sincronizar_y_fallar(**kwargs):
        original.sincronizar(**kwargs)
        raise ValidationError("falló después del acceso")

    monkeypatch.setattr(
        port, "_adaptador", replace(original, sincronizar=sincronizar_y_fallar)
    )
    with pytest.raises(ValidationError, match="falló después"):
        process_single_user_import_row(
            row_data=_fila(comedores=str(comedor.pk), correo="nuevo@example.com"),
            job=SimpleNamespace(requested_by=admin, is_pwa_import=True),
        )
    assert not AccesoComedorPWA.objects.filter(comedor=comedor).exists()
    if existente:
        user.refresh_from_db()
        assert user.email == ""
    else:
        assert not User.objects.filter(username="importado_c2").exists()


@pytest.mark.django_db(transaction=True)
def test_checkpoint_y_accesos_revierten_en_la_misma_transaccion(mocker, admin):
    comedor = Comedor.objects.create(nombre="Espacio checkpoint C2")
    job = UserImportJob.objects.create(
        requested_by=admin,
        is_pwa_import=True,
        archivo="users/import_jobs/test/c2.xlsx",
        original_filename="c2.xlsx",
    )
    mocker.patch.object(
        worker,
        "_load_job_rows",
        return_value=[_fila(comedores=str(comedor.pk), fila=2)],
    )
    mocker.patch.object(
        worker, "_record_row_created", side_effect=RuntimeError("checkpoint falló")
    )
    with pytest.raises(RuntimeError, match="checkpoint falló"):
        worker.process_user_import_job(job)
    assert not User.objects.filter(username="importado_c2").exists()
    assert not AccesoComedorPWA.objects.filter(comedor=comedor).exists()
    job.refresh_from_db()
    assert job.next_row_index == 0


def test_sin_adaptador_no_autoriza_permiso_pwa_en_lote_general(monkeypatch, admin):
    monkeypatch.setattr(port, "_adaptador", None)
    with pytest.raises(ValidationError, match="no está disponible"):
        process_single_user_import_row(
            row_data=_fila(permisos="manage_nomina_pwa"),
            job=SimpleNamespace(requested_by=admin, is_pwa_import=False),
        )
    assert not User.objects.filter(username="importado_c2").exists()


def test_adaptador_conserva_rechazo_de_permiso_no_delegable():
    actor = User.objects.create_user(username="actor_sin_permiso_c2")
    with pytest.raises(ValidationError, match="autorizado para asignar"):
        process_single_user_import_row(
            row_data=_fila(permisos="manage_nomina_pwa"),
            job=SimpleNamespace(requested_by=actor, is_pwa_import=False),
        )
    assert not User.objects.filter(username="importado_c2").exists()


def test_sin_adaptador_agrega_grupo_independiente_sin_revocar_accesos(
    monkeypatch, admin
):
    user = User.objects.create_user(username="mixto_c2")
    permiso = Permission.objects.get(
        content_type__app_label="pwa", codename="manage_nomina_pwa"
    )
    user.user_permissions.add(permiso)
    group, _ = Group.objects.get_or_create(name="Usuario Ver")
    monkeypatch.setattr(port, "_adaptador", None)
    process_single_user_import_row(
        row_data=_fila(
            username=user.username, permisos=group.name, accion_grupos="agregar"
        ),
        job=SimpleNamespace(requested_by=admin, is_pwa_import=False),
    )
    assert user.groups.filter(pk=group.pk).exists()
    assert user.user_permissions.filter(pk=permiso.pk).exists()


def test_revalida_efectos_de_grupo_antes_de_escribir_sin_adaptador(monkeypatch, admin):
    from usuarios import services_user_import as importer

    group, _ = Group.objects.get_or_create(name="Usuario Ver")
    original = importer._validar_y_preparar_fila

    def validar_y_cambiar_grupo(row_data, job):
        datos = original(row_data, job)
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label="pwa", codename="manage_nomina_pwa"
            )
        )
        return datos

    monkeypatch.setattr(port, "_adaptador", None)
    monkeypatch.setattr(importer, "_validar_y_preparar_fila", validar_y_cambiar_grupo)
    with pytest.raises(ValidationError, match="no está disponible"):
        process_single_user_import_row(
            row_data=_fila(permisos=group.name),
            job=SimpleNamespace(requested_by=admin, is_pwa_import=False),
        )
    assert not User.objects.filter(username="importado_c2").exists()
