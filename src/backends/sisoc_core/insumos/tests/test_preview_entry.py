from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import Permission, User
from django.test import override_settings
from django.urls import resolve

PREVIEW_PATHS = (
    "/v2/sisoc/insumos/categorias/",
    "/v2/sisoc/insumos/categorias/crear",
    "/v2/sisoc/insumos/categorias/17/editar",
    "/v2/sisoc/insumos/categorias/17/eliminar",
    "/v2/sisoc/insumos",
    "/v2/sisoc/insumos/",
    "/v2/sisoc/insumos/crear",
    "/v2/sisoc/insumos/crear/",
    "/v2/sisoc/insumos/17/editar",
    "/v2/sisoc/insumos/17/editar/",
    "/v2/sisoc/insumos/17/eliminar",
    "/v2/sisoc/insumos/17/eliminar/",
)


@pytest.fixture
def no_permissions_user(db):
    return User.objects.create_user(username="preview-without-permissions")


@pytest.fixture
def upstream_response():
    response = MagicMock()
    response.status = 200
    response.headers = {"Content-Type": "text/html"}
    response.read.return_value = b"preview"
    response.__enter__.return_value = response
    response.__exit__.return_value = None
    return response


@pytest.mark.django_db
@pytest.mark.parametrize("path", PREVIEW_PATHS)
def test_insumos_preview_preserves_anonymous_403(client, path):
    with patch("core.v2_frontend.urlopen") as fetch:
        assert client.get(path).status_code == 403
    fetch.assert_not_called()


@pytest.mark.django_db
def test_insumos_preview_preserves_anonymous_head_403(client):
    with patch("core.v2_frontend.urlopen") as fetch:
        response = client.head("/v2/sisoc/insumos/", REMOTE_ADDR="198.51.100.10")

    assert response.status_code == 403
    fetch.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize("path", PREVIEW_PATHS)
def test_insumos_preview_preserves_authenticated_no_permission_403(
    client, no_permissions_user, path
):
    client.force_login(no_permissions_user)
    with patch("core.v2_frontend.urlopen") as fetch:
        assert client.get(path).status_code == 403
    fetch.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path,codename,asset_path",
    [
        (
            "/v2/sisoc/insumos/categorias/",
            "view_insumocategoria",
            "insumos/categorias/",
        ),
        (
            "/v2/sisoc/insumos/categorias/crear",
            "add_insumocategoria",
            "insumos/categorias/crear",
        ),
        (
            "/v2/sisoc/insumos/categorias/17/editar",
            "change_insumocategoria",
            "insumos/categorias/17/editar",
        ),
        (
            "/v2/sisoc/insumos/categorias/17/eliminar",
            "delete_insumocategoria",
            "insumos/categorias/17/eliminar",
        ),
        ("/v2/sisoc/insumos", "view_insumo", "insumos"),
        ("/v2/sisoc/insumos/crear/", "add_insumo", "insumos/crear/"),
        ("/v2/sisoc/insumos/17/editar", "change_insumo", "insumos/17/editar"),
        ("/v2/sisoc/insumos/17/eliminar/", "delete_insumo", "insumos/17/eliminar/"),
    ],
)
def test_insumos_preview_uses_the_matching_action_permission_without_view(
    client, db, path, codename, asset_path, upstream_response
):
    user = User.objects.create_user(username=f"preview-{codename}")
    permission = Permission.objects.get(
        content_type__app_label="insumos", codename=codename
    )
    user.user_permissions.add(permission)
    client.force_login(user)

    with (
        override_settings(FRONTEND_V2_UPSTREAMS={"sisoc": "http://front-sisoc:8080"}),
        patch("core.v2_frontend.urlopen", return_value=upstream_response) as fetch,
    ):
        response = client.get(path)

    assert response.status_code == 200
    assert response.content == b"preview"
    fetch.assert_called_once()
    outbound = fetch.call_args.args[0]
    assert outbound.full_url == f"http://front-sisoc:8080/v2/sisoc/{asset_path}"
    assert outbound.get_method() == "GET"


@pytest.mark.django_db
def test_insumos_preview_head_forwards_without_body(client, db, upstream_response):
    user = User.objects.create_user(username="preview-head")
    permission = Permission.objects.get(
        content_type__app_label="insumos", codename="view_insumo"
    )
    user.user_permissions.add(permission)
    client.force_login(user)

    with (
        override_settings(FRONTEND_V2_UPSTREAMS={"sisoc": "http://front-sisoc:8080"}),
        patch("core.v2_frontend.urlopen", return_value=upstream_response) as fetch,
    ):
        response = client.head("/v2/sisoc/insumos/", REMOTE_ADDR="198.51.100.10")

    assert response.status_code == 200
    assert response.content == b""
    assert fetch.call_args.args[0].get_method() == "HEAD"
    upstream_response.read.assert_not_called()


@pytest.mark.django_db
def test_insumos_preview_rejects_unsafe_methods_before_proxy(client, db):
    user = User.objects.create_user(username="preview-unsafe")
    permission = Permission.objects.get(
        content_type__app_label="insumos", codename="add_insumo"
    )
    user.user_permissions.add(permission)
    client.force_login(user)

    with patch("core.v2_frontend.urlopen") as fetch:
        response = client.post("/v2/sisoc/insumos/crear/", {"titulo": "No guardar"})

    assert response.status_code == 405
    fetch.assert_not_called()


@pytest.mark.parametrize(
    "path",
    [
        "/v2/sisoc/insumos/17/descargar",
        "/v2/sisoc/otro/",
    ],
)
def test_non_preview_routes_remain_on_the_generic_v2_catchall(path):
    assert resolve(path).url_name == "frontend_v2"


@override_settings(FRONTEND_V2_UPSTREAMS={"vpsl": "http://front-vpsl:8080"})
def test_existing_generic_v2_anonymous_entry_keeps_login_redirect(client):
    response = client.get("/v2/vpsl/")

    assert response.status_code == 302
    assert response["Location"].startswith("/login/?next=/v2/vpsl/")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "request_case",
    [
        (
            "/v2/sisoc/insumos/categorias/",
            "view_insumocategoria",
            "insumos/categorias/",
        ),
        (
            "/v2/sisoc/insumos/categorias/crear",
            "add_insumocategoria",
            "insumos/categorias/crear",
        ),
        (
            "/v2/sisoc/insumos/categorias/17/editar",
            "change_insumocategoria",
            "insumos/categorias/17/editar",
        ),
        (
            "/v2/sisoc/insumos/categorias/17/eliminar",
            "delete_insumocategoria",
            "insumos/categorias/17/eliminar",
        ),
    ],
)
@pytest.mark.parametrize("actor_kind", ["anonymous", "denied", "allowed"])
@override_settings(FRONTEND_V2_UPSTREAMS={"sisoc": "http://front-sisoc:8080"})
def test_category_preview_head_permission_before_proxy(
    client, no_permissions_user, upstream_response, request_case, actor_kind
):
    path, codename, asset_path = request_case
    if actor_kind != "anonymous":
        if actor_kind == "allowed":
            permission = Permission.objects.get(
                content_type__app_label="insumos", codename=codename
            )
            no_permissions_user.user_permissions.add(permission)
        client.force_login(no_permissions_user)
    with patch("core.v2_frontend.urlopen", return_value=upstream_response) as fetch:
        response = client.head(path, REMOTE_ADDR="198.51.100.10")
    assert response.status_code == (200 if actor_kind == "allowed" else 403)
    assert response.content == b""
    if actor_kind == "allowed":
        fetch.assert_called_once()
        assert fetch.call_args.args[0].full_url.endswith("/" + asset_path)
        assert fetch.call_args.args[0].get_method() == "HEAD"
        upstream_response.read.assert_not_called()
    else:
        fetch.assert_not_called()
