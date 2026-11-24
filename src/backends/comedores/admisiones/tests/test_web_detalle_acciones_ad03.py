"""Detail-page actions the React screen posts to the native views (AD03.02).

The inline edit of the agreement number, the PWA switch, the additional-file
upload and the forced closure keep their native endpoints; these tests pin the
persisted effect of each one and that a rejection leaves the data unchanged.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from admisiones.models.admisiones import Admision, ArchivoAdmision
from comedores.models import Comedor

pytestmark = pytest.mark.django_db


def _usuario(nombre, permiso=None, superuser=False, grupo=None):
    usuario = get_user_model().objects.create_user(nombre)
    perfil = usuario.profile
    perfil.acceso_web = True
    perfil.must_change_password = False
    perfil.needs_profile_confirmation = False
    perfil.save()
    if permiso:
        app, codigo = permiso.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codigo)
        )
    if grupo:
        usuario.groups.add(Group.objects.get_or_create(name=grupo)[0])
    if superuser:
        usuario.is_superuser = True
        usuario.save()
    return usuario


def _cliente(usuario):
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="admision")
def admision_fixture():
    comedor = Comedor.objects.create(nombre="Comedor Acciones AD03")
    return Admision.objects.create(comedor=comedor, convenio_numero=3)


def _estado(admision):
    admision.refresh_from_db()
    return admision.convenio_numero, admision.vigente_pwa


def test_agreement_number_is_saved_and_cleared(admision):
    root = _cliente(_usuario("root_conv", superuser=True))

    respuesta = root.post(
        "/ajax/actualizar-convenio-numero/",
        {"admision_id": admision.pk, "convenio_numero": "7"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["success"] is True
    assert respuesta.json()["convenio_numero"] == 7
    assert _estado(admision)[0] == 7
    root.post(
        "/ajax/actualizar-convenio-numero/",
        {"admision_id": admision.pk, "convenio_numero": ""},
    )
    assert _estado(admision)[0] is None


@pytest.mark.parametrize(
    ("valor", "error"),
    [
        ("-1", "El numero de convenio no puede ser negativo."),
        ("abc", "Debe ingresar un numero valido."),
    ],
)
def test_agreement_number_rejections_leave_it_unchanged(admision, valor, error):
    root = _cliente(_usuario("root_conv_rej", superuser=True))

    respuesta = root.post(
        "/ajax/actualizar-convenio-numero/",
        {"admision_id": admision.pk, "convenio_numero": valor},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["error"] == error
    assert _estado(admision)[0] == 3


def test_agreement_number_without_dupla_role_is_rejected_unchanged(admision):
    lector = _cliente(_usuario("lector_conv", "comedores.view_comedor"))

    respuesta = lector.post(
        "/ajax/actualizar-convenio-numero/",
        {"admision_id": admision.pk, "convenio_numero": "9"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["error"] == "No tiene permisos para editar esta admision."
    assert _estado(admision)[0] == 3


def test_vigente_pwa_switch_moves_the_flag_within_the_comedor(admision):
    otra = Admision.objects.create(comedor=admision.comedor, vigente_pwa=True)
    root = _cliente(_usuario("root_pwa", superuser=True))

    respuesta = root.post(
        "/ajax/actualizar-vigente-pwa/",
        {"admision_id": admision.pk, "vigente_pwa": "1"},
    )

    assert respuesta.status_code == 200
    assert _estado(admision)[1] is True
    assert _estado(otra)[1] is False
    root.post(
        "/ajax/actualizar-vigente-pwa/",
        {"admision_id": admision.pk, "vigente_pwa": "0"},
    )
    assert _estado(admision)[1] is False


def test_vigente_pwa_without_role_is_rejected_unchanged(admision):
    lector = _cliente(_usuario("lector_pwa", "comedores.view_comedor"))

    respuesta = lector.post(
        "/ajax/actualizar-vigente-pwa/",
        {"admision_id": admision.pk, "vigente_pwa": "1"},
    )

    assert respuesta.status_code == 400
    assert _estado(admision)[1] is False


def _url(admision):
    return f"/comedores/{admision.comedor_id}/admision/{admision.pk}/detalle/"


def test_additional_file_upload_creates_one_custom_document(admision):
    root = _cliente(_usuario("root_up", superuser=True))
    antes = ArchivoAdmision.objects.filter(admision=admision).count()

    respuesta = root.post(
        _url(admision),
        {"nombre": "Nota extra", "archivo": SimpleUploadedFile("n.pdf", b"%PDF-1")},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"success": True}
    assert ArchivoAdmision.objects.filter(admision=admision).count() == antes + 1


def test_additional_file_upload_rejections_create_nothing(admision):
    root = _cliente(_usuario("root_up_rej", superuser=True))

    sin_nombre = root.post(
        _url(admision),
        {"nombre": "", "archivo": SimpleUploadedFile("n.pdf", b"%PDF-1")},
    )

    assert sin_nombre.status_code == 400
    assert sin_nombre.json()["error"] == "El archivo y el nombre son obligatorios."
    assert ArchivoAdmision.objects.filter(admision=admision).count() == 0


def test_forced_closure_persists_and_empty_reason_changes_nothing(admision):
    root = _cliente(_usuario("root_cierre", superuser=True))

    vacio = root.post(
        _url(admision), {"forzar_cierre": "1", "motivo_forzar_cierre": " "}
    )

    assert vacio.status_code == 302
    admision.refresh_from_db()
    assert admision.activa is True
    assert not admision.motivo_forzar_cierre
    root.post(
        _url(admision), {"forzar_cierre": "1", "motivo_forzar_cierre": "Duplicada"}
    )
    admision.refresh_from_db()
    assert admision.activa is False
    assert admision.motivo_forzar_cierre == "Duplicada"
    assert admision.estado_mostrar == "Inactivada"
    assert admision.estado_admision == "inactivada"


def test_forced_closure_rejects_a_user_without_read_permission(admision):
    sin = _cliente(_usuario("sin_cierre"))

    respuesta = sin.post(
        _url(admision), {"forzar_cierre": "1", "motivo_forzar_cierre": "x"}
    )

    assert respuesta.status_code in (302, 403)
    admision.refresh_from_db()
    assert admision.activa is True
