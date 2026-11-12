"""Web API (G1 v1) of the organization documents (O02).

``/api/web/comedores/organizaciones/`` runs the native document views: the
tests pin the persisted effects (same-record replacement, new version over an
accepted one, GDE replication), the Django error texts verbatim, the capacity
rules of the dupla and today's access (any of ``ORGANIZACION_DOCUMENTACION_PERMS``).
"""

from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from comedores.models import Comedor
from core import web_gate
from duplas.models import Dupla
from organizaciones.models import (
    ArchivoOrganizacion,
    DocumentacionOrganizacion,
    Organizacion,
    TipoEntidad,
)

API = "/api/web/comedores/organizaciones/"
PERSONERIA = DocumentacionOrganizacion.CATEGORIA_PERSONERIA
ACEPTADO = ArchivoOrganizacion.ESTADO_ACEPTADO
A_VALIDAR = ArchivoOrganizacion.ESTADO_A_VALIDAR

pytestmark = pytest.mark.django_db


def _usuario(nombre, *codes, superuser=False):
    usuario = get_user_model().objects.create_user(nombre)
    usuario.is_superuser = superuser
    usuario.save()
    profile = usuario.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for code in codes:
        app, codename = code.split(".")
        if app == "auth":
            permiso = Permission.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(Group),
                codename=codename,
                defaults={"name": codename},
            )[0]
        else:
            permiso = Permission.objects.get(
                content_type__app_label=app, codename=codename
            )
        usuario.user_permissions.add(permiso)
    return usuario


def _client(usuario):
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="mundo")
def mundo_fixture():
    """An organization of a dupla, its technician, its lawyer and a catalog document."""
    tecnico = _usuario("doc_tecnico", "auth.role_tecnico_comedor")
    abogado = _usuario("doc_abogado", "auth.role_abogado_dupla")
    dupla = Dupla.objects.create(nombre="D", estado="Activo", abogado=abogado)
    dupla.tecnico.add(tecnico)
    tipo = TipoEntidad.objects.create(nombre="Personería jurídica")
    organizacion = Organizacion.objects.create(nombre="Org Docs", tipo_entidad=tipo)
    Comedor.objects.create(nombre="C", organizacion=organizacion, dupla=dupla)
    documento = DocumentacionOrganizacion.objects.create(
        nombre="Estatuto", categoria=PERSONERIA, obligatorio=True, orden=1
    )
    return type(
        "Mundo",
        (),
        {
            "org": organizacion,
            "doc": documento,
            "tec": _client(tecnico),
            "abo": _client(abogado),
            "lector": _client(
                _usuario("doc_lector", "organizaciones.view_organizacion")
            ),
            "admin": _client(_usuario("doc_admin", superuser=True)),
        },
    )


def _pdf(nombre="a.pdf", contenido=b"%PDF-1.4 ok", tipo="application/pdf"):
    return SimpleUploadedFile(nombre, contenido, content_type=tipo)


def _subir(cliente, mundo, **extra):
    datos = {"archivo": _pdf()}
    datos.update(extra)
    return cliente.post(f"{API}{mundo.org.pk}/documentacion/{mundo.doc.pk}/subir/", datos)


def _archivo(mundo, estado=A_VALIDAR, **extra):
    return ArchivoOrganizacion.objects.create(
        organizacion=mundo.org,
        documentacion=mundo.doc,
        archivo=_pdf(),
        estado=estado,
        **extra,
    )


def _estado(cliente, archivo, estado, **extra):
    return cliente.post(
        f"{API}documentacion/{archivo.pk}/estado/", {"estado": estado, **extra}
    )


# --- subir -----------------------------------------------------------------------------


def test_technician_uploads_and_gets_the_row_as_data(mundo):
    respuesta = _subir(mundo.tec, mundo)

    assert respuesta.status_code == 200
    archivo = ArchivoOrganizacion.objects.get(organizacion=mundo.org)
    assert archivo.estado == "Documento adjunto"
    fila = respuesta.json()["fila"]
    assert fila["row_id"] == mundo.doc.pk
    assert fila["name"] == "Estatuto" and fila["mandatory"] is True
    assert fila["custom"] is False and fila["document_id"] == mundo.doc.pk
    assert fila["file"]["id"] == archivo.pk
    assert fila["file"]["state"] == "Documento adjunto"
    assert fila["file"]["url"] == archivo.archivo.url
    assert fila["file"]["expiry"] is None and fila["file"]["gde"] == ""
    assert fila["can_send"] is True and fila["can_validate"] is False
    assert fila["history_url"] == (
        f"/organizaciones/{mundo.org.pk}/documentacion/{mundo.doc.pk}/historial/"
    )


def test_upload_over_a_not_accepted_document_replaces_the_same_record(mundo):
    previo = _archivo(mundo, "Rectificar", observaciones="Falta firma", numero_gde="GDE-1")

    respuesta = _subir(mundo.tec, mundo, fecha_vencimiento="2030-05-06")

    assert respuesta.status_code == 200
    assert ArchivoOrganizacion.objects.filter(organizacion=mundo.org).count() == 1
    previo.refresh_from_db()
    assert previo.estado == "Documento adjunto" and previo.observaciones == ""
    assert previo.numero_gde is None and str(previo.fecha_vencimiento) == "2030-05-06"
    assert respuesta.json()["fila"]["file"]["id"] == previo.pk
    assert respuesta.json()["fila"]["file"]["expiry"]["date"] == "06/05/2030"


def test_upload_over_an_accepted_document_adds_a_new_version(mundo):
    previo = _archivo(mundo, ACEPTADO)

    respuesta = _subir(mundo.tec, mundo)

    assert respuesta.status_code == 200
    assert ArchivoOrganizacion.objects.filter(organizacion=mundo.org).count() == 2
    nuevo = ArchivoOrganizacion.objects.exclude(pk=previo.pk).get()
    assert respuesta.json()["fila"]["file"]["id"] == nuevo.pk
    previo.refresh_from_db()
    assert previo.estado == ACEPTADO


@pytest.mark.parametrize(
    "archivo,fecha,texto",
    [
        (None, None, "Debe adjuntar un archivo."),
        (
            _pdf(contenido=b"x" * (20 * 1024 * 1024 + 1)),
            None,
            "El archivo excede el tamaño máximo permitido de 20 MB.",
        ),
        (
            _pdf("a.exe", tipo="application/pdf"),
            None,
            "Formato inválido. Solo se permiten archivos PDF, JPG, PNG, Excel o Word.",
        ),
        (
            _pdf(tipo="text/html"),
            None,
            "Tipo de archivo no permitido. Formatos válidos: PDF, JPG, PNG, Excel o Word.",
        ),
        (_pdf(), "no-es-fecha", "Fecha de vencimiento invalida."),
    ],
)
def test_upload_validations_answer_400_with_the_django_text(mundo, archivo, fecha, texto):
    datos = {}
    if archivo is not None:
        datos["archivo"] = archivo
    if fecha:
        datos["fecha_vencimiento"] = fecha

    respuesta = mundo.tec.post(
        f"{API}{mundo.org.pk}/documentacion/{mundo.doc.pk}/subir/", datos
    )

    assert respuesta.status_code == 400
    assert respuesta.json() == {"error": texto}
    assert not ArchivoOrganizacion.objects.exists()


def test_only_the_technician_of_the_dupla_uploads(mundo):
    for cliente in (mundo.abo, mundo.lector):
        respuesta = _subir(cliente, mundo)
        assert respuesta.status_code == 403
        assert respuesta.json() == {"error": "Sin permisos para cargar este documento."}
    assert not ArchivoOrganizacion.objects.exists()
    assert _subir(mundo.admin, mundo).status_code == 200


# --- documentación adicional ---------------------------------------------------------


def test_additional_document_is_created_without_catalog(mundo):
    respuesta = mundo.tec.post(
        f"{API}{mundo.org.pk}/documentacion/personalizada/",
        {"nombre": "  " + "N" * 300 + "  ", "archivo": _pdf(), "fecha_vencimiento": "2030-01-02"},
    )

    assert respuesta.status_code == 200
    archivo = ArchivoOrganizacion.objects.get()
    assert archivo.documentacion is None and archivo.nombre_personalizado == "N" * 255
    fila = respuesta.json()["fila"]
    assert fila["row_id"] == f"custom-{archivo.pk}" and fila["custom"] is True
    assert fila["name"] == "N" * 255 and fila["document_id"] is None
    assert fila["history_url"] is None


def test_additional_document_needs_a_name_and_the_send_capacity(mundo):
    url = f"{API}{mundo.org.pk}/documentacion/personalizada/"

    sin_nombre = mundo.tec.post(url, {"nombre": " ", "archivo": _pdf()})
    sin_permiso = mundo.abo.post(url, {"nombre": "X", "archivo": _pdf()})
    ajena = mundo.tec.post(
        f"{API}{Organizacion.objects.create(nombre='Ajena').pk}/documentacion/personalizada/",
        {"nombre": "X", "archivo": _pdf()},
    )

    assert sin_nombre.status_code == 400
    assert sin_nombre.json() == {"error": "Debe indicar un nombre para el documento."}
    assert sin_permiso.status_code == 403
    assert ajena.status_code == 404
    assert not ArchivoOrganizacion.objects.exists()


# --- estado ------------------------------------------------------------------------------


def test_lawyer_accepts_and_the_row_carries_the_new_state(mundo):
    archivo = _archivo(mundo)

    respuesta = _estado(mundo.abo, archivo, ACEPTADO)

    assert respuesta.status_code == 200
    archivo.refresh_from_db()
    assert archivo.estado == ACEPTADO and archivo.modificado_por.username == "doc_abogado"
    fila = respuesta.json()["fila"]
    assert fila["file"]["state"] == ACEPTADO and fila["can_validate"] is True


def test_rectify_needs_observations_from_the_lawyer_and_stores_them(mundo):
    archivo = _archivo(mundo)

    sin = _estado(mundo.abo, archivo, "Rectificar")
    con = _estado(mundo.abo, archivo, "Rectificar", observaciones=" Falta el sello ")

    assert sin.status_code == 400
    assert sin.json() == {"error": "Debe indicar observaciones."}
    assert con.status_code == 200
    archivo.refresh_from_db()
    assert archivo.estado == "Rectificar" and archivo.observaciones == "Falta el sello"
    assert con.json()["fila"]["file"]["observations"] == "Falta el sello"


def test_state_rules_keep_the_native_403_texts(mundo):
    archivo = _archivo(mundo, "Documento adjunto")

    tecnico_acepta = _estado(mundo.tec, archivo, ACEPTADO)
    abogado_envia = _estado(mundo.abo, archivo, A_VALIDAR)
    lector = _estado(mundo.lector, archivo, A_VALIDAR)
    invalido = _estado(mundo.abo, archivo, "Inventado")

    assert tecnico_acepta.status_code == 403
    assert tecnico_acepta.json() == {
        "error": "El abogado solo puede validar documentos en estado A Validar Abogado."
    }
    assert abogado_envia.status_code == 403
    assert abogado_envia.json() == {
        "error": "El abogado solo puede validar documentos en estado A Validar Abogado."
    }
    assert lector.status_code == 403
    assert lector.json() == {"error": "Sin permisos para modificar este documento."}
    assert invalido.status_code == 400 and invalido.json() == {"error": "Estado invalido."}
    archivo.refresh_from_db()
    assert archivo.estado == "Documento adjunto"


def test_technician_sends_to_validate_and_accepted_is_not_resent(mundo):
    adjunto = _archivo(mundo, "Documento adjunto")
    otro = _archivo(mundo, ACEPTADO)

    enviado = _estado(mundo.tec, adjunto, A_VALIDAR)
    reenvio = _estado(mundo.tec, otro, A_VALIDAR)

    assert enviado.status_code == 200
    assert reenvio.status_code == 403
    assert reenvio.json() == {"error": "El documento no esta disponible para envio tecnico."}


# --- vencimiento y GDE -----------------------------------------------------------------


def test_expiry_is_set_cleared_and_validated(mundo):
    archivo = _archivo(mundo)
    url = f"{API}documentacion/{archivo.pk}/vencimiento/"

    puesto = mundo.tec.post(url, {"fecha_vencimiento": "2000-01-01"})
    invalido = mundo.tec.post(url, {"fecha_vencimiento": "31/12/2030"})
    lector = mundo.lector.post(url, {"fecha_vencimiento": "2030-01-01"})
    borrado = mundo.abo.post(url, {"fecha_vencimiento": ""})

    assert puesto.json()["fila"]["file"]["expiry"] == {
        "date": "01/01/2000",
        "iso": "2000-01-01",
        "status": "vencido",
    }
    assert invalido.status_code == 400
    assert invalido.json() == {"error": "Fecha de vencimiento invalida."}
    assert lector.status_code == 403
    assert lector.json() == {"error": "Sin permisos para modificar este documento."}
    assert borrado.json()["fila"]["file"]["expiry"] is None
    archivo.refresh_from_db()
    assert archivo.fecha_vencimiento is None


def test_gde_only_on_accepted_documents_and_it_is_replicated(mundo):
    pendiente = _archivo(mundo, A_VALIDAR)
    aceptado = _archivo(mundo, ACEPTADO)

    rechazo = mundo.abo.post(
        f"{API}documentacion/{pendiente.pk}/numero-gde/", {"numero_gde": "G"}
    )
    with mock.patch(
        "admisiones.services.admisiones_service.impl.AdmisionService."
        "replicar_numero_gde_desde_organizacion"
    ) as replicar:
        ok = mundo.abo.post(
            f"{API}documentacion/{aceptado.pk}/numero-gde/",
            {"numero_gde": " " + "G" * 60},
        )

    assert rechazo.status_code == 400
    assert rechazo.json() == {
        "error": "El número de GDE solo puede cargarse en documentos aceptados."
    }
    assert ok.status_code == 200
    aceptado.refresh_from_db()
    assert aceptado.numero_gde == "G" * 50
    assert ok.json()["fila"]["file"]["gde"] == "G" * 50
    replicar.assert_called_once()
    assert replicar.call_args.args[0].pk == aceptado.pk
    mundo.abo.post(f"{API}documentacion/{aceptado.pk}/numero-gde/", {"numero_gde": ""})
    aceptado.refresh_from_db()
    assert aceptado.numero_gde is None


# --- historial -----------------------------------------------------------------------------


def test_history_lists_every_version_newest_first_inside_the_dupla(mundo):
    viejo = _archivo(mundo, ACEPTADO, observaciones="")
    nuevo = _archivo(mundo, "Rectificar", observaciones="Revisar")
    url = f"{API}{mundo.org.pk}/documentacion/{mundo.doc.pk}/historial/"

    data = mundo.tec.get(url).json()

    assert data["organization"] == {"id": mundo.org.pk, "name": "Org Docs"}
    assert data["document"] == {"id": mundo.doc.pk, "name": "Estatuto"}
    assert [f["id"] for f in data["files"]] == [nuevo.pk, viejo.pk]
    assert data["files"][0]["state"] == "Rectificar"
    assert data["files"][0]["observations"] == "Revisar"
    assert data["files"][0]["expiry"] == "-" and data["files"][1]["observations"] == "-"
    assert data["files"][0]["url"] == nuevo.archivo.url
    assert data["urls"] == {
        "list": "/organizaciones/listar",
        "legajo": f"/organizaciones/detalle/{mundo.org.pk}",
    }
    ajena = Organizacion.objects.create(nombre="Ajena")
    assert mundo.tec.get(f"{API}{ajena.pk}/documentacion/{mundo.doc.pk}/historial/").status_code == 404
    assert mundo.lector.get(url).status_code == 200
    assert mundo.tec.get(f"{API}{mundo.org.pk}/documentacion/999999/historial/").status_code == 404


# --- acceso y sección del legajo ---------------------------------------------------------


def test_access_is_todays_anonymous_401_no_permission_403_and_csrf_403(mundo):
    archivo = _archivo(mundo)
    url = f"{API}documentacion/{archivo.pk}/estado/"

    anonimo = Client().post(url, {"estado": ACEPTADO})
    assert anonimo.status_code == 401
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert _client(_usuario("doc_sin")).post(url, {"estado": ACEPTADO}).status_code == 403
    con_csrf = Client(enforce_csrf_checks=True)
    con_csrf.force_login(get_user_model().objects.get(username="doc_abogado"))
    assert con_csrf.post(url, {"estado": ACEPTADO}).status_code == 403
    archivo.refresh_from_db()
    assert archivo.estado == A_VALIDAR
    for metodo in ("get", "put", "delete"):
        assert getattr(mundo.abo, metodo)(url).status_code == 405


def test_legajo_delivers_the_documentation_table_as_a_section(mundo):
    _archivo(mundo, ACEPTADO, numero_gde="GDE-9", fecha_vencimiento="2030-01-02")
    mundo.tec.post(
        f"{API}{mundo.org.pk}/documentacion/personalizada/",
        {"nombre": "Extra", "archivo": _pdf()},
    )

    data = mundo.tec.get(f"{API}{mundo.org.pk}/").json()

    secciones = [s for s in data["sections"] if s["kind"] == "documentos"]
    assert len(secciones) == 1
    seccion = secciones[0]
    assert seccion["organization_id"] == mundo.org.pk
    assert seccion["category"] == "Organizacion con personeria juridica"
    assert (seccion["can_validate"], seccion["can_send"]) == (False, True)
    assert [f["name"] for f in seccion["rows"]] == ["Estatuto", "Extra"]
    assert seccion["rows"][0]["file"]["gde"] == "GDE-9"
    assert seccion["rows"][1]["custom"] is True
    assert f'<div data-legajo-seccion="{data["sections"].index(seccion)}"></div>' in data["html"]
    assert "Documentación de la Organización" not in data["html"]
    assert data["scripts"] == []
