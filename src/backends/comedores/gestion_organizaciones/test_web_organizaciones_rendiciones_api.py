"""Web API (G1 v1) of the organization rendiciones (O04).

``/api/web/comedores/organizaciones/<id>/rendiciones/<pk>/`` runs the native
``OrganizacionRendicionDetailView``: the tests pin its queryset (dupla scope,
non-deleted, project or comedor of the organization), today's access (any of
``ORGANIZACION_DOCUMENTACION_PERMS``) and the capabilities of the PDF button.
The legajo table and its filter travel as sections.
"""

from datetime import date, datetime, timezone

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from comedores.models import Comedor, Programas
from core import web_gate
from duplas.models import Dupla
from gestion_organizaciones.models import LineaProyecto, ProgramaOrganizacion
from organizaciones.models import Organizacion, ProyectoOrganizacion
from rendicioncuentasmensual.models import RendicionCuentaMensual

API = "/api/web/comedores/organizaciones/"
VER = "rendicioncuentasmensual.view_rendicioncuentamensual"
SECOS = RendicionCuentaMensual.LINEA_SECOS
TRADICIONAL = RendicionCuentaMensual.LINEA_TRADICIONAL

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


def _rendicion(numero, linea="", **extra):
    return RendicionCuentaMensual.objects.create(
        mes=3,
        anio=2026,
        convenio=f"C-{numero}",
        numero_rendicion=numero,
        linea_programatica=linea,
        **extra,
    )


@pytest.fixture(name="org")
def org_fixture():
    organizacion = Organizacion.objects.create(nombre="Org Rendiciones")
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="P-1"
    )
    return organizacion, proyecto


def test_detail_projects_every_native_field(org):
    organizacion, proyecto = org
    rendicion = _rendicion(
        7,
        SECOS,
        proyecto=proyecto,
        periodo_inicio=date(2026, 1, 1),
        periodo_fin=date(2026, 3, 31),
        fecha_validacion_territorial=datetime(2026, 4, 1, 15, 30, tzinfo=timezone.utc),
        fecha_validacion_auditoria=datetime(2026, 4, 2, 3, 5, tzinfo=timezone.utc),
        acta_auditoria=SimpleUploadedFile("acta.pdf", b"%PDF"),
    )

    data = (
        _client(_usuario("rend_admin", superuser=True))
        .get(f"{API}{organizacion.pk}/rendiciones/{rendicion.pk}/")
        .json()
    )

    assert data["number"] == 7 and data["number_text"] == "7"
    assert data["organization"] == {"id": organizacion.pk, "name": "Org Rendiciones"}
    assert (data["project_code"], data["convenio"]) == ("P-1", "C-7")
    assert data["period"] == "01/01/2026 al 31/03/2026"
    assert data["process"] == (
        f"{rendicion.get_etapa_proceso_display()} — "
        f"{rendicion.get_subestado_proceso_display()}"
    )
    assert data["territorial"] == "Sí" and data["territorial_date"].startswith(
        "01/04/2026"
    )
    assert data["audit"] == "Sí" and data["audit_date"].startswith("0")
    assert data["validated"] == "No" and data["validated_date"] == "-"
    assert data["audited"] == "No" and data["audited_date"] == "-"
    assert data["regularized"] == "No" and data["regularized_date"] == "-"
    assert data["audit_record_url"] == rendicion.acta_auditoria.url
    assert data["complementary_record_url"] is None
    assert data["can_view_rendicion"] is True and data["can_download_pdf"] is True
    assert data["urls"] == {
        "rendicion": reverse("rendicioncuentasmensual_detail", args=[rendicion.pk]),
        "pdf_request": reverse(
            "rendicioncuentasmensual_download_pdf_solicitar", args=[rendicion.pk]
        ),
        "pdf_status": reverse(
            "rendicioncuentasmensual_download_pdf_estado", args=[rendicion.pk]
        ),
    }
    assert data["urls"]["pdf_request"].endswith("/descargar-pdf/solicitar/")


def test_detail_falls_back_to_the_month_and_the_dash_defaults(org):
    organizacion, _ = org
    comedor = Comedor.objects.create(nombre="C", organizacion=organizacion)
    Comedor.objects.filter(pk=comedor.pk).update(codigo_de_proyecto="VIEJO-1")
    rendicion = RendicionCuentaMensual.objects.create(mes=3, anio=2026, comedor=comedor)

    data = (
        _client(_usuario("rend_admin2", superuser=True))
        .get(f"{API}{organizacion.pk}/rendiciones/{rendicion.pk}/")
        .json()
    )

    assert data["number"] == rendicion.pk and data["number_text"] == "-"
    assert data["convenio"] == "-" and data["project_code"] == "VIEJO-1"
    assert data["period"] == "Marzo 2026"
    assert data["can_download_pdf"] is False


def test_validated_date_prefers_the_audit_management_date(org):
    organizacion, proyecto = org
    rendicion = _rendicion(
        1,
        proyecto=proyecto,
        validada=True,
        fecha_carga_auditoria=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
    )

    data = (
        _client(_usuario("rend_admin3", superuser=True))
        .get(f"{API}{organizacion.pk}/rendiciones/{rendicion.pk}/")
        .json()
    )

    assert data["validated"] == "Sí"
    assert data["validated_date"].startswith("01/05/2026")


def test_pdf_button_needs_the_view_permission_and_the_audit_validation(org):
    organizacion, proyecto = org
    abierta = _rendicion(1, proyecto=proyecto)
    validada = _rendicion(
        2,
        proyecto=proyecto,
        fecha_validacion_auditoria=datetime(2026, 4, 2, 12, 0, tzinfo=timezone.utc),
    )
    con_permiso = _client(_usuario("rend_ver", "organizaciones.view_organizacion", VER))
    sin_permiso = _client(_usuario("rend_solo_org", "organizaciones.view_organizacion"))

    pedir = lambda c, r: c.get(
        f"{API}{organizacion.pk}/rendiciones/{r.pk}/"
    ).json()  # noqa: E731

    assert pedir(con_permiso, abierta)["can_download_pdf"] is False
    assert pedir(con_permiso, validada)["can_download_pdf"] is True
    assert pedir(sin_permiso, validada)["can_view_rendicion"] is False
    assert pedir(sin_permiso, validada)["can_download_pdf"] is False


def test_the_native_queryset_decides_404(org):
    organizacion, proyecto = org
    ajena = Organizacion.objects.create(nombre="Ajena")
    otra_proyecto = ProyectoOrganizacion.objects.create(organizacion=ajena, codigo="X")
    borrada = _rendicion(1, proyecto=proyecto)
    borrada.delete()
    de_otra = _rendicion(2, proyecto=otra_proyecto)
    propia = _rendicion(3, proyecto=proyecto)
    web = _client(_usuario("rend_lector", "organizaciones.view_organizacion"))

    assert (
        web.get(f"{API}{organizacion.pk}/rendiciones/{propia.pk}/").status_code == 200
    )
    assert (
        web.get(f"{API}{organizacion.pk}/rendiciones/{borrada.pk}/").status_code == 404
    )
    assert (
        web.get(f"{API}{organizacion.pk}/rendiciones/{de_otra.pk}/").status_code == 404
    )
    assert web.get(f"{API}{ajena.pk}/rendiciones/{propia.pk}/").status_code == 404
    assert web.get(f"{API}{organizacion.pk}/rendiciones/999999/").status_code == 404


def test_a_technician_only_sees_the_organizations_of_the_dupla(org):
    organizacion, proyecto = org
    rendicion = _rendicion(1, proyecto=proyecto)
    tecnico = _usuario("rend_tec", "auth.role_tecnico_comedor")
    dupla = Dupla.objects.create(
        nombre="D", estado="Activo", abogado=_usuario("rend_abogado")
    )
    dupla.tecnico.add(tecnico)
    web = _client(tecnico)
    url = f"{API}{organizacion.pk}/rendiciones/{rendicion.pk}/"

    assert web.get(url).status_code == 404
    Comedor.objects.create(nombre="C", organizacion=organizacion, dupla=dupla)
    assert web.get(url).status_code == 200


def test_access_is_todays_anonymous_401_no_permission_403_and_read_only(org):
    organizacion, proyecto = org
    url = f"{API}{organizacion.pk}/rendiciones/{_rendicion(1, proyecto=proyecto).pk}/"

    anonimo = Client().get(url)
    assert anonimo.status_code == 401
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert _client(_usuario("rend_sin")).get(url).status_code == 403
    web = _client(_usuario("rend_ro", "organizaciones.view_organizacion"))
    for metodo in ("post", "put", "patch", "delete"):
        assert getattr(web, metodo)(url).status_code == 405, metodo


def _todas(valor):
    """Every JSON object with a ``kind`` in the page, in document order."""
    if isinstance(valor, dict):
        if "kind" in valor:
            yield valor
        for hijo in valor.values():
            yield from _todas(hijo)
    elif isinstance(valor, list):
        for hijo in valor:
            yield from _todas(hijo)


def test_legajo_delivers_the_table_filter_and_other_lines_as_sections():
    secos = Programas.objects.create(nombre="Abordaje comunitario - Línea Secos")
    tradicional = Programas.objects.create(
        nombre="Abordaje comunitario - Línea Tradicional"
    )
    organizacion = Organizacion.objects.create(nombre="Org Legajo Rend")
    ProgramaOrganizacion.objects.create(organizacion=organizacion, programa=secos)
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo="S-1"
    )
    ProyectoOrganizacion.objects.create(organizacion=organizacion, codigo="S-2")
    LineaProyecto.objects.create(proyecto=proyecto, programa=secos)
    _rendicion(
        1,
        SECOS,
        proyecto=proyecto,
        fecha_validacion_territorial=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    _rendicion(2, TRADICIONAL, proyecto=proyecto)
    web = _client(_usuario("rend_leg", "organizaciones.view_organizacion"))

    data = web.get(
        f"{API}{organizacion.pk}/?programa={secos.pk}&seccion=rendiciones"
    ).json()

    tablas = [s for s in _todas(data["blocks"]) if s["kind"] == "rendiciones"]
    filtros = [s for s in _todas(data["blocks"]) if s["kind"] == "rendiciones_filtro"]
    assert [t["show_line"] for t in tablas] == [False, True]
    principal, otras = tablas
    assert [r["convenio"] for r in principal["rows"]] == ["C-1"]
    fila = principal["rows"][0]
    assert (fila["number"], fila["project"], fila["period"]) == (
        "1",
        "S-1",
        "Marzo 2026",
    )
    assert (fila["territorial"], fila["audit"], fila["validated"], fila["audited"]) == (
        True,
        False,
        False,
        False,
    )
    assert (
        fila["url"]
        == f"/organizaciones/{organizacion.pk}/rendiciones/{fila['id']}/detalle/"
    )
    assert fila["line"] == SECOS
    assert (
        fila["line_label"]
        == RendicionCuentaMensual(
            linea_programatica=SECOS
        ).get_linea_programatica_display()
    )
    assert [r["convenio"] for r in otras["rows"]] == ["C-2"]
    assert otras["rows"][0]["line"] == TRADICIONAL
    assert len(filtros) == 1 and filtros[0] == {
        "kind": "rendiciones_filtro",
        "codes": ["S-1", "S-2"],
        "selected": "",
        "program_id": secos.pk,
    }
    assert [b["kind"] for b in data["blocks"]][2:4] == [
        "rendiciones_programa",
        "rendiciones_otras",
    ]
