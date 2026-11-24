"""Editor actions the React screen posts to the native endpoints (AD03.02).

The document state and GDE number, the expediente number, the people of the roster, the
file upload and the deletion keep their native AJAX endpoints; these tests pin the persisted
effect of each one and that a rejection leaves the data unchanged.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from admisiones.models.admisiones import (
    Admision,
    ArchivoAdmision,
    Documentacion,
    EstadoAdmision,
    TipoConvenio,
)
from comedores.models import Comedor

pytestmark = pytest.mark.django_db

EXPEDIENTE = "EX-2026-000000002- -APN-DGD#MCH"


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


@pytest.fixture(name="root")
def root_fixture():
    return _cliente(_usuario("root_acciones_ed", superuser=True))


@pytest.fixture(name="admision")
def admision_fixture():
    convenio = TipoConvenio.objects.create(pk=3, nombre="Personería Jurídica")
    estado = EstadoAdmision.objects.create(pk=1, nombre="Pendiente")
    comedor = Comedor.objects.create(nombre="Comedor Acciones Editor")
    return Admision.objects.create(
        comedor=comedor,
        tipo="incorporacion",
        tipo_convenio=convenio,
        estado=estado,
        estado_admision="documentacion_en_proceso",
        num_expediente="EX-2026-000000001- -APN-DGD#MCH",
    )


@pytest.fixture(name="archivo")
def archivo_fixture(admision):
    documentacion = Documentacion.objects.create(nombre="Estatuto", obligatorio=True)
    documentacion.convenios.add(admision.tipo_convenio)
    return ArchivoAdmision.objects.create(
        admision=admision,
        documentacion=documentacion,
        archivo=SimpleUploadedFile("estatuto.pdf", b"%PDF"),
        estado="Documento adjunto",
    )


def _fresco(objeto):
    objeto.refresh_from_db()
    return objeto


def test_document_state_is_changed_and_a_rectify_needs_the_observation(
    admision, archivo
):
    abogado = _cliente(_usuario("abogado_ed", superuser=True, grupo="Abogado Dupla"))

    sin_observacion = abogado.post(
        "/ajax/actualizar-estado/",
        {
            "estado": "Rectificar",
            "documento_id": archivo.pk,
            "admision_id": admision.pk,
        },
    )

    assert sin_observacion.status_code == 400
    assert (
        sin_observacion.json()["error"]
        == "Debe ingresar observaciones para rectificar."
    )
    assert _fresco(archivo).estado == "Documento adjunto"

    rectificado = abogado.post(
        "/ajax/actualizar-estado/",
        {
            "estado": "Rectificar",
            "documento_id": archivo.pk,
            "admision_id": admision.pk,
            "observacion": "Falta la firma.",
        },
    )

    assert rectificado.status_code == 200
    assert rectificado.json()["success"] is True
    archivo = _fresco(archivo)
    assert archivo.estado == "Rectificar"
    assert archivo.observaciones == "Falta la firma."


def test_document_state_rejects_incomplete_data_and_unknown_files(
    admision, archivo, root
):
    incompleto = root.post("/ajax/actualizar-estado/", {"admision_id": admision.pk})

    assert incompleto.status_code == 400
    assert incompleto.json()["error"] == "Datos incompletos."
    inexistente = root.post(
        "/ajax/actualizar-estado/",
        {"estado": "Aceptado", "documento_id": 999999, "admision_id": admision.pk},
    )
    assert inexistente.status_code == 400
    assert _fresco(archivo).estado == "Documento adjunto"


def test_gde_number_is_saved_only_for_accepted_documents(admision, archivo, root):
    rechazado = root.post(
        "/ajax/actualizar-numero-gde/",
        {"documento_id": archivo.pk, "numero_gde": "IF-1"},
    )

    assert rechazado.status_code == 400
    assert rechazado.json()["error"] == (
        "Solo se puede actualizar el número GDE en documentos aceptados."
    )
    assert _fresco(archivo).numero_gde in (None, "")

    archivo.estado = "Aceptado"
    archivo.save()
    guardado = root.post(
        "/ajax/actualizar-numero-gde/",
        {"documento_id": archivo.pk, "numero_gde": " IF-2026-9 "},
    )

    assert guardado.status_code == 200
    assert guardado.json()["numero_gde"] == "IF-2026-9"
    assert _fresco(archivo).numero_gde == "IF-2026-9"


def test_expediente_number_is_saved_or_rejected_unchanged(admision, root):
    otra = Admision.objects.create(
        comedor=Comedor.objects.create(nombre="Otro"), num_expediente=EXPEDIENTE
    )
    anterior = admision.num_expediente

    for valor, error in (
        ("EX-2026", "Formato inválido. Use EX-AÑO-NÚMERO- -APN-REPARTICIÓN#ORGANISMO."),
        ("", "El número de expediente es obligatorio."),
    ):
        respuesta = root.post(
            "/ajax/actualizar-num-expediente/",
            {"admision_id": admision.pk, "num_expediente": valor},
        )
        assert respuesta.status_code == 400
        assert respuesta.json()["error"] == error
    duplicado = root.post(
        "/ajax/actualizar-num-expediente/",
        {"admision_id": admision.pk, "num_expediente": EXPEDIENTE.lower()},
    )
    assert duplicado.status_code == 400
    assert duplicado.json()["error"].startswith(
        f"El expediente ya pertenece a la admisión #{otra.pk};"
    )
    assert _fresco(admision).num_expediente == anterior

    guardado = root.post(
        "/ajax/actualizar-num-expediente/",
        {
            "admision_id": admision.pk,
            "num_expediente": "ex-2026-000000003- -apn-dgd#mch",
        },
    )

    assert guardado.status_code == 200
    assert _fresco(admision).num_expediente == "EX-2026-000000003- -APN-DGD#MCH"


def test_expediente_number_is_locked_once_sent_to_legal(admision, root):
    admision.enviado_legales = True
    admision.save()

    respuesta = root.post(
        "/ajax/actualizar-num-expediente/",
        {"admision_id": admision.pk, "num_expediente": EXPEDIENTE},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["error"] == (
        "No se puede editar el expediente una vez enviado a legales."
    )
    assert _fresco(admision).num_expediente == "EX-2026-000000001- -APN-DGD#MCH"


def test_roster_people_are_only_for_the_food_community_program(admision, root):
    respuesta = root.post(
        "/ajax/actualizar-personas-conveniadas-nomina/",
        {"admision_id": admision.pk, "personas_conveniadas_nomina": "12"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["error"] == "Disponible solo para Alimentar Comunidad."
    assert _fresco(admision).personas_conveniadas_nomina is None


def test_additional_document_is_uploaded_and_deleted_through_the_native_urls(
    admision, root
):
    crear = f"/admision/{admision.pk}/documentacion/personalizada/agregar/"

    sin_nombre = root.post(crear, {"archivo": SimpleUploadedFile("nota.pdf", b"%PDF")})

    assert sin_nombre.status_code == 400
    assert not ArchivoAdmision.objects.filter(admision=admision).exists()

    creado = root.post(
        crear,
        {
            "nombre": "Nota adicional",
            "archivo": SimpleUploadedFile("nota.pdf", b"%PDF"),
        },
    )

    assert creado.status_code == 201
    assert creado.json()["success"] is True
    archivo = ArchivoAdmision.objects.get(admision=admision)
    assert archivo.nombre_personalizado == "Nota adicional"

    eliminado = root.delete(
        f"/admision/{admision.pk}/documentacion/{archivo.pk}/eliminar/"
        f"?archivo_id={archivo.pk}"
    )

    assert eliminado.status_code == 200
    assert eliminado.json()["success"] is True
    assert not ArchivoAdmision.objects.filter(admision=admision).exists()


def test_required_document_is_uploaded_to_its_slot(admision, root):
    documentacion = Documentacion.objects.create(nombre="Acta", obligatorio=True)
    documentacion.convenios.add(admision.tipo_convenio)

    respuesta = root.post(
        f"/admision/{admision.pk}/documentacion/{documentacion.pk}/subir/",
        {"archivo": SimpleUploadedFile("acta.pdf", b"%PDF")},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["success"] is True
    archivo = ArchivoAdmision.objects.get(
        admision=admision, documentacion=documentacion
    )
    assert archivo.estado == "Documento adjunto"
