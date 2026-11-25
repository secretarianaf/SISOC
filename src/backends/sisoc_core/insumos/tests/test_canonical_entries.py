"""Verify canonical Insumos entries through the real composed URLconf."""

from contextlib import contextmanager
from importlib import import_module, reload

import pytest
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import clear_url_caches, reverse, set_urlconf

from core.models import Programa
from insumos.models import Insumo, InsumoCategoria

pytestmark = pytest.mark.django_db
MARKER = b'<div id="react-insumos"></div>'
ASSET_PATH = "/insumos/react/assets/app.js"


def _reload_urls():
    for module in ("config.urls", "config.urls_all"):
        reload(import_module(module))
    clear_url_caches()
    set_urlconf(None)


@contextmanager
def _insumos_flag(build, *, enabled=True, core_enabled=False):
    enabled_keys = {"insumos"} if enabled else set()
    if core_enabled:
        enabled_keys.add("core")
    try:
        with override_settings(
            ROOT_URLCONF="config.urls_all",
            REACT_VERTICALES_ACTIVAS=frozenset(enabled_keys),
            SISOC_REACT_BUILD_DIR=str(build),
        ):
            _reload_urls()
            yield
    finally:
        _reload_urls()


@pytest.fixture
def build(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_bytes(b"console.log('insumos');")
    (tmp_path / "index.html").write_bytes(
        b'<script type="module" src="/v2/sisoc/assets/app.js"></script>' + MARKER
    )
    return tmp_path


@pytest.fixture
def items(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    programa = Programa.objects.create(nombre="Comedores")
    categoria = InsumoCategoria.objects.create(programa=programa, nombre="Manuales")
    insumo = Insumo.objects.create(
        programa=programa,
        categoria=categoria,
        titulo="Manual de prueba",
        archivo=SimpleUploadedFile("manual.pdf", b"contenido"),
    )
    return {"insumo": insumo, "insumocategoria": categoria}


def _login(client, codename):
    user = User.objects.create_user(username=codename)
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label="insumos", codename=codename)
    )
    client.force_login(user)


@pytest.mark.parametrize(
    ("name", "path", "permission", "object_type"),
    [
        ("insumos_listar", "/insumos/", "view_insumo", None),
        ("insumos_crear", "/insumos/crear", "add_insumo", None),
        ("insumos_editar", "/insumos/{pk}/editar", "change_insumo", "insumo"),
        ("insumos_eliminar", "/insumos/{pk}/eliminar", "delete_insumo", "insumo"),
        (
            "insumos_categorias_listar",
            "/insumos/categorias/",
            "view_insumocategoria",
            None,
        ),
        (
            "insumos_categorias_crear",
            "/insumos/categorias/crear",
            "add_insumocategoria",
            None,
        ),
        (
            "insumos_categorias_editar",
            "/insumos/categorias/{pk}/editar",
            "change_insumocategoria",
            "insumocategoria",
        ),
        (
            "insumos_categorias_eliminar",
            "/insumos/categorias/{pk}/eliminar",
            "delete_insumocategoria",
            "insumocategoria",
        ),
    ],
)
def test_entradas_canonicas_conservan_ruta_y_permiso(
    client, build, items, name, path, permission, object_type
):
    pk = items[object_type].pk if object_type else None
    canonical = path.format(pk=pk)
    baseline = reverse(name, args=(pk,) if object_type else None)
    with _insumos_flag(build):
        assert (
            reverse(name, args=(pk,) if object_type else None) == baseline == canonical
        )
        assert client.get(canonical).status_code == 403
        _login(client, permission)
        response = client.get(canonical)
        assert response.status_code == 200
        assert MARKER in response.content
        assert ASSET_PATH.encode() in response.content
        assert "private" in response["Cache-Control"]
        assert "no-store" in response["Cache-Control"]
        assert "csrftoken" in response.cookies
        assert client.head(canonical).content == b""
        if object_type:
            assert client.get(path.format(pk=999999)).status_code == 404
        if name.endswith("listar"):
            assert client.get(f"{canonical}?page=no-valida").status_code == 404


def test_solo_insumos_activo_entrega_sus_assets_y_mantiene_descarga_nativa(
    client, build, items
):
    with _insumos_flag(build):
        asset = client.get(ASSET_PATH)
        assert asset.status_code == 200
        assert b"console.log('insumos');" == asset.content
        assert "immutable" in asset["Cache-Control"]
        assert client.get("/insumos/react/assets/missing.js").status_code == 404

        url = reverse("insumos_descargar", args=(items["insumo"].pk,))
        assert client.get(url).status_code == 403
        _login(client, "view_insumo")
        download = client.get(url)
        assert download.status_code == 200
        assert download["Content-Disposition"] == 'attachment; filename="manual.pdf"'
        assert b"".join(download.streaming_content) == b"contenido"


def test_formulario_post_y_rollback_conservan_html_nativo(client, build):
    _login(client, "add_insumo")
    for enabled in (True, False):
        with _insumos_flag(build, enabled=enabled):
            url = reverse("insumos_crear")
            page = client.get(url)
            assert page.status_code == 200
            assert (MARKER in page.content) == enabled
            response = client.post(url, {})
            assert response.status_code == 200
            assert MARKER not in response.content
            assert response.context["form"].errors
            assert not Insumo.objects.exists()


@pytest.mark.parametrize("core_enabled", [False, True])
def test_assets_canonicos_no_exponen_otras_rutas_o_metodos(client, build, core_enabled):
    with _insumos_flag(build, core_enabled=core_enabled):
        assert client.get("/core/react/assets/app.js").status_code == (
            200 if core_enabled else 404
        )
        for suffix in (
            "index.html",
            "assets/../index.html",
            "assets/%2e%2e/index.html",
            "assets/app.js?nocache=1",
            "assets/fixture.env",
        ):
            assert client.get(f"/insumos/react/{suffix}").status_code == 404
        assert client.post(ASSET_PATH, {}).status_code == 405


@pytest.mark.parametrize("enabled", [False, True])
def test_permiso_de_consulta_no_habilita_gestion_ni_escrituras(
    client, build, items, enabled
):
    _login(client, "view_insumo")
    insumo_pk = items["insumo"].pk
    category_pk = items["insumocategoria"].pk
    inputs_before = list(Insumo.objects.order_by("pk").values())
    categories_before = list(InsumoCategoria.objects.order_by("pk").values())
    paths = (
        reverse("insumos_crear"),
        reverse("insumos_editar", args=(insumo_pk,)),
        reverse("insumos_eliminar", args=(insumo_pk,)),
        reverse("insumos_categorias_listar"),
        reverse("insumos_categorias_crear"),
        reverse("insumos_categorias_editar", args=(category_pk,)),
        reverse("insumos_categorias_eliminar", args=(category_pk,)),
    )

    with _insumos_flag(build, enabled=enabled):
        for url in paths:
            assert client.get(url).status_code == 403
            assert client.post(url, {"titulo": "No autorizado"}).status_code == 403

    assert list(Insumo.objects.order_by("pk").values()) == inputs_before
    assert list(InsumoCategoria.objects.order_by("pk").values()) == categories_before
