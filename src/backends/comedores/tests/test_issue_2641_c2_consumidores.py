"""Contratos C2: fragmentos, favoritos y recursos conservan su dueño."""

import json
from types import SimpleNamespace

import pytest
import requests
from django.contrib.auth.models import Permission, User
from django.test import RequestFactory
from django.urls import resolve, reverse

from ciudadanos import detail_contributions
from ciudadanos.models import Ciudadano
from core import backend_proxy
from core.models import FiltroFavorito
from core.services.favorite_filters import registry


CONTRIBUCIONES = ("comedores", "comedores_colaboraciones", "pwa", "pwa_badges")


@pytest.mark.django_db
@pytest.mark.parametrize("nombre", CONTRIBUCIONES)
def test_fragmento_local_conserva_permiso_y_ruta(client, nombre):
    ciudadano = Ciudadano.objects.create(nombre="Persona", apellido="C2")
    user = User.objects.create_user(username="lector_c2")
    client.force_login(user)
    path = f"/ciudadanos/{ciudadano.pk}/contribucion/{nombre}/"
    assert resolve(path).func.__name__ == "contribucion_detalle_ciudadano"
    assert client.get(path).status_code == 403
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="ciudadanos", codename="view_ciudadano"
        )
    )
    assert client.get(path).status_code == 200
    client.logout()
    assert client.get(path).status_code == 302


@pytest.mark.parametrize("nombre", CONTRIBUCIONES)
@pytest.mark.parametrize("fallo", (403, 503, "timeout"))
def test_fragmento_remoto_degrada_sin_datos_ni_imports(
    mocker, monkeypatch, nombre, fallo
):
    monkeypatch.setattr(detail_contributions, "_CONTRIBUCIONES", {})
    backend = {"origin": "http://owner.invalid"}
    owner = mocker.patch.object(
        detail_contributions, "backend_de_app", return_value=backend
    )
    get = mocker.patch.object(detail_contributions.requests, "get")
    if fallo == "timeout":
        get.side_effect = requests.Timeout()
    else:
        get.return_value = SimpleNamespace(status_code=fallo, text="DATO NO AUTORIZADO")
    request = RequestFactory().get("/ciudadanos/1/", HTTP_COOKIE="sessionid=original")
    assert (
        detail_contributions.renderizar_contribucion(
            nombre, request, SimpleNamespace(pk=1), mocker.Mock()
        )
        == ""
    )
    owner.assert_called_once_with(detail_contributions.APPS_CONTRIBUCIONES[nombre])
    assert get.call_args.kwargs["headers"]["cookie"] == "sessionid=original"
    assert get.call_args.kwargs["allow_redirects"] is False


@pytest.mark.django_db
@pytest.mark.parametrize("seccion", tuple(backend_proxy.APPS_SECCIONES_FAVORITAS))
def test_favoritos_se_reenvian_al_dueno_sin_configuracion_local(
    client, monkeypatch, mocker, seccion
):
    user = User.objects.create_user(username="favoritos_c2")
    client.force_login(user)
    favorito = FiltroFavorito.objects.create(
        usuario=user, seccion=seccion, nombre="Mi filtro", filtros={"items": []}
    )
    monkeypatch.setattr(registry, "_CONFIGURACIONES_POR_SECCION", {})
    backend = {"origin": "http://owner.invalid"}
    owner = mocker.patch.object(backend_proxy, "backend_de_app", return_value=backend)
    forward = mocker.patch("core.views.reenviar_a_backend")
    from django.http import JsonResponse

    forward.side_effect = lambda *_a, **_kw: JsonResponse(
        {"error": "No disponible"}, status=503
    )
    url = reverse("filtros_favoritos")
    assert client.get(url, {"seccion": seccion}).status_code == 503
    assert client.post(url, {"seccion": seccion, "nombre": "Otro"}).status_code == 503
    detalle = reverse("detalle_filtro_favorito", args=[favorito.pk])
    assert client.get(detalle).status_code == 503
    assert client.delete(detalle).status_code == 503
    assert FiltroFavorito.objects.filter(pk=favorito.pk).exists()
    assert forward.call_count == 4
    assert owner.call_args.args == (backend_proxy.APPS_SECCIONES_FAVORITAS[seccion],)
    # La sección enviada por el cliente no permite resolver un favorito ajeno.
    otro = User.objects.create_user(username="otro_c2")
    client.force_login(otro)
    assert client.get(detalle, {"seccion": seccion}).status_code == 404
    assert forward.call_count == 4


@pytest.mark.django_db
def test_favoritos_locales_validan_payload_y_propietario(client):
    user = User.objects.create_user(username="favorito_local")
    client.force_login(user)
    url = reverse("filtros_favoritos")
    invalid = client.post(
        url,
        json.dumps(
            {
                "seccion": "comedores",
                "nombre": "X",
                "filtros": {"items": [{"field": "secreto", "op": "eq", "value": 1}]},
            }
        ),
        content_type="application/json",
    )
    assert invalid.status_code == 409
    response = client.post(
        url,
        json.dumps({"seccion": "comedores", "nombre": "X", "filtros": {"items": []}}),
        content_type="application/json",
    )
    assert response.status_code == 201
    detalle = reverse("detalle_filtro_favorito", args=[response.json()["id"]])
    assert client.get(detalle).status_code == 200
    assert client.delete(detalle).status_code == 200


@pytest.mark.django_db
def test_auditoria_de_modelo_no_instalado_conserva_diff():
    from audittrail.views import AuditLogResolveMixin
    from auditlog.models import LogEntry
    from django.contrib.contenttypes.models import ContentType

    entry = LogEntry(
        changes={"nombre": ["Anterior", "Actual"]},
        content_type=ContentType(app_label="ausente_c2", model="comedor"),
    )
    assert AuditLogResolveMixin().resolve_entry_changes(entry) == {
        "nombre": {"old": "Anterior", "new": "Actual"}
    }


@pytest.mark.django_db
def test_fragmentos_renderizan_datos_y_escapan_html(client):
    from datetime import date
    from admisiones.models.admisiones import Admision
    from comedores.models import Comedor, Nomina, ColaboradorEspacio
    from pwa.models import NominaEspacioPWA

    user = User.objects.create_superuser(username="lector_completo")
    ciudadano = Ciudadano.objects.create(nombre="Persona", apellido="Prueba")
    comedor = Comedor.objects.create(nombre="<script>espacio</script>")
    admision = Admision.objects.create(comedor=comedor)
    nomina = Nomina.objects.create(ciudadano=ciudadano, admision=admision)
    NominaEspacioPWA.objects.create(
        nomina=nomina, situacion_calle=True, persona_con_celiaquia=True
    )
    ColaboradorEspacio.objects.create(
        comedor=comedor, ciudadano=ciudadano, fecha_alta=date.today()
    )
    client.force_login(user)
    response = client.get(reverse("ciudadanos_ver", args=[ciudadano.pk]))
    assert response.status_code == 200
    html = response.content.decode()
    assert "&lt;script&gt;espacio&lt;/script&gt;" in html
    assert "<script>espacio</script>" not in html
    assert "Colaboraciones en comedores" in html
    assert "Situación de calle</span>" in html
    assert reverse("comedor_detalle", args=[comedor.pk]) in html


@pytest.mark.django_db
@pytest.mark.parametrize(
    "nombre", ("comedores_comedor", "pwa_nominaespaciopwa", "pwa_auditoriaoperacionpwa")
)
def test_admin_del_dueno_es_real_y_conserva_permisos(client, nombre):
    path = reverse(f"admin:{nombre}_changelist")
    assert resolve(path).func.__module__.startswith("django.contrib.admin")
    # Ser staff no alcanza: el admin es solo para superusuarios (#2789).
    user = User.objects.create_user(username="staff_sin_permiso", is_staff=True)
    client.force_login(user)
    response = client.get(path)
    assert response.status_code == 302
    assert response.url.startswith(reverse("admin:login"))
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    assert client.get(path).status_code == 200
