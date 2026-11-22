"""Web API (G1 v1) and local preview of the report detail page (AD02.01)."""

import types
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.base import ContentFile
from django.db import models
from django.template import Context, Template
from django.test import Client, override_settings
from django.utils import timezone

from admisiones.models.admisiones import Admision, InformeTecnico, InformeTecnicoPDF
from admisiones.web_preview_informes import informes_preview_patterns
from comedores.models import Comedor
from config.urls_all import urlpatterns as monolith_patterns

API = "/api/web/comedores/admisiones/informes/"
NATIVO = "/comedores/admision/informe_tecnico/"
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    '<body><div id="root"></div></body></html>'
)

pytestmark = pytest.mark.django_db


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return user


def _valor(field):
    if field.choices:
        return field.choices[0][0]
    kinds = (
        (models.EmailField, "test@example.com"),
        (models.BooleanField, False),
        (models.DecimalField, Decimal("1.0")),
        (models.FloatField, 1.0),
        (models.DateTimeField, timezone.now()),
        (models.DateField, timezone.now().date()),
        (models.IntegerField, 1),
    )
    return next((v for k, v in kinds if isinstance(field, k)), "test")


def _informe(admision, **extra):
    datos = {}
    for field in InformeTecnico._meta.fields:
        autogen = field.primary_key or field.auto_created
        if autogen or getattr(field, "auto_now", False) or field.has_default():
            continue
        if getattr(field, "auto_now_add", False) or field.null:
            continue
        if not isinstance(field, models.ForeignKey):
            datos[field.name] = _valor(field)
    datos.update(
        admision=admision, tipo="base", estado="Iniciado", estado_formulario="borrador"
    )
    datos.update(extra)
    return InformeTecnico.objects.create(**datos)


def _usuario(nombre, permiso=None):
    usuario = _ready(get_user_model().objects.create_user(nombre))
    if permiso:
        app, codigo = permiso.split(".")
        usuario.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codigo)
        )
    return usuario


def _cliente(usuario):
    client = Client()
    client.force_login(usuario)
    return client


@pytest.fixture(name="informe")
def informe_fixture():
    comedor = Comedor.objects.create(nombre="Comedor AD02")
    admision = Admision.objects.create(comedor=comedor)
    return _informe(admision, observaciones_subsanacion="Revisar fechas")


def test_detail_projects_the_native_context(informe):
    web = _cliente(_usuario("lector_informe", "comedores.view_comedor"))

    respuesta = web.get(f"{API}base/{informe.pk}/")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["id"] == informe.pk
    assert (datos["tipo"], datos["estado"]) == ("base", "Iniciado")
    assert datos["comedor"] == "Comedor AD02"
    assert datos["observaciones_subsanacion"] == "Revisar fechas"
    nombres = [campo["nombre"] for campo in datos["campos"]]
    assert nombres and "Estado" not in nombres
    assert datos["puede_cambiar_estado"] is True
    assert datos["puede_subsanar"] is True
    assert datos["archivos"] == {
        "docx_descargar": None,
        "docx_editado_ver": None,
        "pdf_final": None,
        "borrador": None,
    }
    assert datos["urls"]["accion"] == f"{NATIVO}base/{informe.pk}/ver/"
    assert str(informe.admision_id) in datos["urls"]["admision"]
    assert datos["messages"] == []


def test_numbers_are_localized_like_the_native_template(informe):
    campo = next(
        f for f in InformeTecnico._meta.fields if isinstance(f, models.DecimalField)
    )
    InformeTecnico.objects.filter(pk=informe.pk).update(
        **{campo.name: Decimal("1234.5")}
    )
    esperado = Template("{{ v }}").render(Context({"v": Decimal("1234.50")}))
    web = _cliente(_usuario("lector_decimal", "comedores.view_comedor"))

    datos = web.get(f"{API}base/{informe.pk}/").json()

    valores = {c["nombre"]: c["valor"] for c in datos["campos"]}
    assert valores[str(campo.verbose_name)] == esperado
    assert "." not in esperado.split(",")[-1]


def test_generated_docx_state_offers_download_and_upload_not_review(informe):
    informe.estado = "Docx generado"
    informe.estado_formulario = "finalizado"
    informe.save()
    pdf = InformeTecnicoPDF(
        admision=informe.admision, tipo="base", informe_id=informe.pk
    )
    pdf.archivo.save("final.pdf", ContentFile(b"%PDF"), save=False)
    pdf.archivo_docx.save("borrador.docx", ContentFile(b"docx"), save=True)
    web = _cliente(_usuario("lector_docx", "admisiones.view_admision"))

    datos = web.get(f"{API}base/{informe.pk}/").json()

    assert datos["archivos"]["docx_descargar"].endswith("borrador.docx")
    assert datos["archivos"]["borrador"] == {
        "kind": "docx_final",
        "url": datos["archivos"]["docx_descargar"],
    }
    assert datos["puede_cambiar_estado"] is False


def test_validated_report_exposes_the_final_pdf_and_no_review(informe):
    informe.estado = "Validado"
    informe.estado_formulario = "finalizado"
    informe.save()
    pdf = InformeTecnicoPDF(
        admision=informe.admision, tipo="base", informe_id=informe.pk
    )
    pdf.archivo.save("final.pdf", ContentFile(b"%PDF"), save=True)
    web = _cliente(_usuario("lector_validado", "comedores.view_comedor"))

    datos = web.get(f"{API}base/{informe.pk}/").json()

    assert datos["archivos"]["pdf_final"].endswith("final.pdf")
    assert datos["archivos"]["borrador"] is None
    assert (datos["puede_cambiar_estado"], datos["puede_subsanar"]) == (False, False)


def test_access_is_the_native_guard_and_lookups(informe):
    url = f"{API}base/{informe.pk}/"
    assert Client().get(url).status_code in (401, 403)
    assert _cliente(_usuario("sin_permiso_informe")).get(url).status_code == 403
    for permiso in (
        "comedores.view_comedor",
        "admisiones.view_admision",
        "acompanamientos.view_informacionrelevante",
    ):
        web = _cliente(_usuario(f"u_{permiso.split('.')[1]}", permiso))
        assert web.get(url).status_code == 200, permiso
    root = _usuario("super_informe")
    root.is_superuser = True
    root.save()
    web = _cliente(root)
    assert web.get(url).status_code == 200
    assert web.get(f"{API}base/999999/").status_code == 404
    assert web.get(f"{API}juridico/{informe.pk}/").status_code == 404
    assert web.post(url, {}).status_code == 405


def test_native_post_stays_native_and_its_message_reaches_the_api(informe):
    web = _cliente(_usuario("revisor_informe", "comedores.view_comedor"))

    respuesta = web.post(f"{NATIVO}base/{informe.pk}/ver/", {"subir_docx": "1"})

    assert respuesta.status_code == 302
    datos = web.get(f"{API}base/{informe.pk}/").json()
    assert datos["messages"] == [
        {"message": "Debe seleccionar un archivo DOCX.", "level": "error"}
    ]
    assert web.get(f"{API}base/{informe.pk}/").json()["messages"] == []


@pytest.fixture(name="preview")
def preview_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    module = types.ModuleType("informe_preview_test_urls")
    module.urlpatterns = informes_preview_patterns(tmp_path) + list(monolith_patterns)
    with override_settings(ROOT_URLCONF=module):
        yield


@pytest.mark.usefixtures("preview")
def test_preview_serves_the_index_after_the_native_guards(informe):
    url = f"{NATIVO}base/{informe.pk}/ver/"
    web = _cliente(_usuario("lector_preview", "comedores.view_comedor"))

    respuesta = web.get(url)

    assert respuesta.status_code == 200
    assert '/comedores/react/assets/app-1.js"' in respuesta.content.decode()
    assert "csrftoken" in respuesta.cookies
    assert Client().get(url).status_code in (302, 403)
    assert _cliente(_usuario("sin_permiso_preview")).get(url).status_code == 403
    assert web.get(f"{NATIVO}base/999999/ver/").status_code == 404
    assert web.post(url, {"subir_docx": "1"}).status_code == 302


def test_preview_requires_an_index(tmp_path):
    with pytest.raises(ValueError):
        informes_preview_patterns(tmp_path)
