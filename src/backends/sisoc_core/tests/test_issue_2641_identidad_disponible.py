"""Disponibilidad y límites del contrato de identidad de #2641."""

import re
from urllib.parse import urlsplit

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.core import mail
from django.http import HttpResponse, QueryDict
from django.test import Client, RequestFactory
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from audittrail.models import AuditoriaSesionPWA
from comedores.models import Comedor
from core.internal_services import RespuestaInterna
from pwa.models import AccesoComedorPWA
from users.admin_operations import operacion_requiere_espacios

pytestmark = pytest.mark.django_db
PASSWORD = "ClaveSegura123!"


@pytest.fixture
def entrevistador():
    user = User.objects.create_user(
        username="disponible", password=PASSWORD, email="disponible@example.com"
    )
    profile = user.profile
    profile.es_relevador_calle = True
    profile.datacalle_rol = "entrevistador"
    profile.save()
    return user


def test_login_otro_programa_no_consulta_comedores(entrevistador, mocker):
    remote = mocker.patch(
        "usuarios.api_views.pedir_json_interno", side_effect=AssertionError
    )
    response = APIClient().post(
        "/api/users/login/", {"username": entrevistador.username, "password": PASSWORD}
    )
    assert response.status_code == 200
    assert Token.objects.filter(key=response.data["token"], user=entrevistador).exists()
    remote.assert_not_called()
    assert AuditoriaSesionPWA.objects.filter(
        user=entrevistador, evento="login_ok"
    ).exists()


def test_elegibilidad_no_disponible_no_emite_token_ni_afirma_rechazo(mocker):
    user = User.objects.create_user(username="solo_espacios", password=PASSWORD)
    mocker.patch(
        "usuarios.api_views.pedir_json_interno",
        return_value=RespuestaInterna(503, None),
    )
    response = APIClient().post(
        "/api/users/login/", {"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 503
    assert not Token.objects.filter(user=user).exists()


def test_me_conserva_permisos_y_territorio_con_espacios_caido(entrevistador, mocker):
    permission = Permission.objects.get(
        content_type__app_label="auth", codename="view_user"
    )
    entrevistador.user_permissions.add(permission)
    token = Token.objects.create(user=entrevistador)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    mocker.patch(
        "usuarios.api_views.pedir_json_interno",
        return_value=RespuestaInterna(503, None),
    )
    response = client.get("/api/users/me/")
    assert response.status_code == 200
    assert response.data["id"] == entrevistador.pk
    assert response.data["espacios_comunitarios_disponible"] is False
    assert "auth.view_user" in response.data["permissions"]
    assert response.data["profile"]["datacalle_rol"] == "entrevistador"
    assert response.data["pwa"]["read_only"] is True
    assert "territorial_scopes" in response.data["scope"]


def test_cambio_logout_y_recupero_son_independientes(entrevistador, mocker):
    remote = mocker.patch(
        "usuarios.api_views.pedir_json_interno", side_effect=AssertionError
    )
    reset_remote = mocker.patch(
        "usuarios.services_password_reset_pwa.pedir_json_interno",
        side_effect=AssertionError,
    )
    entrevistador.profile.must_change_password = True
    entrevistador.profile.save()
    token = Token.objects.create(user=entrevistador)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    assert (
        client.post(
            "/api/users/password-change-required/",
            {"new_password": "OtraClaveSegura321!"},
        ).status_code
        == 200
    )
    assert client.post("/api/users/logout/", {}).status_code == 200
    assert not Token.objects.filter(user=entrevistador).exists()
    client.credentials()
    assert (
        client.post(
            "/api/users/password-reset/request/",
            {"username": entrevistador.username, "email": entrevistador.email},
        ).status_code
        == 200
    )
    assert len(mail.outbox) == 1
    assert "/reset/" in mail.outbox[0].body
    remote.assert_not_called()
    reset_remote.assert_not_called()


@pytest.mark.parametrize("mixed", [False, True])
def test_recupero_preserva_destino_exclusivo_y_usa_web_para_mixtos(mixed, mocker):
    user = User.objects.create_user(
        username=f"recupero_{mixed}", password=PASSWORD, email="recupero@example.com"
    )
    user.profile.acceso_web = mixed
    user.profile.save(update_fields=["acceso_web"])
    comedor = Comedor.objects.create(nombre="Espacio recupero")
    AccesoComedorPWA.objects.create(user=user, comedor=comedor, rol="representante")
    response = APIClient().post(
        "/api/users/password-reset/request/",
        {"username": user.username, "email": user.email},
    )
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    assert ("password-reset-confirm?" in mail.outbox[0].body) is (not mixed)
    assert ("/reset/" in mail.outbox[0].body) is mixed


@pytest.mark.parametrize("mixed", [False, True])
def test_recupero_central_completo_revoca_token_anterior(
    client, entrevistador, mocker, mixed
):
    if mixed:
        comedor = Comedor.objects.create(nombre="Espacio de cuenta mixta")
        AccesoComedorPWA.objects.create(
            user=entrevistador, comedor=comedor, rol="representante"
        )
    remote = mocker.patch(
        "usuarios.services_password_reset_pwa.pedir_json_interno",
        side_effect=AssertionError,
    )
    token = Token.objects.create(user=entrevistador)
    token_key = token.key
    response = APIClient().post(
        "/api/users/password-reset/request/",
        {
            "username": entrevistador.username,
            "email": entrevistador.email,
        },
    )
    assert response.status_code == 200
    link = re.search(r"https?://\S+/reset/\S+", mail.outbox[0].body).group()
    response = client.post(
        urlsplit(link).path,
        {
            "new_password1": "RecuperadaSegura321!",
            "new_password2": "RecuperadaSegura321!",
        },
    )
    assert response.status_code == 302
    entrevistador.refresh_from_db()
    assert entrevistador.check_password("RecuperadaSegura321!")
    assert not Token.objects.filter(user=entrevistador).exists()
    stale_client = APIClient()
    stale_client.credentials(HTTP_AUTHORIZATION=f"Token {token_key}")
    assert stale_client.get("/api/users/me/").status_code == 401
    remote.assert_not_called()


def test_edicion_generica_no_revoca_accesos_omitidos(client, mocker):
    admin = User.objects.create_superuser(
        username="admin_disponible", password=PASSWORD
    )
    user = User.objects.create_user(username="identidad_mixta", password=PASSWORD)
    comedor = Comedor.objects.create(nombre="Espacio conservado")
    access = AccesoComedorPWA.objects.create(
        user=user, comedor=comedor, rol="representante"
    )
    permission = Permission.objects.get(
        content_type__app_label="pwa", codename="manage_nomina_pwa"
    )
    user.user_permissions.add(permission)
    client.force_login(admin)
    remote = mocker.patch(
        "usuarios.views.reenviar_operacion_usuario", side_effect=AssertionError
    )
    response = client.post(
        f"/usuarios/editar/{user.pk}/", {"first_name": "Actualizado"}
    )
    assert response.status_code == 302
    user.refresh_from_db()
    access.refresh_from_db()
    assert user.first_name == "Actualizado"
    assert access.activo
    assert user.user_permissions.filter(pk=permission.pk).exists()
    remote.assert_not_called()


@pytest.mark.parametrize(
    "field", ["acceso_web", "acceso_siis", "groups", "user_permissions"]
)
def test_edicion_generica_permite_vaciar_control_presentado(field):
    from users.admin_forms import CustomUserChangeForm

    admin = User.objects.create_superuser(username="admin_vaciado", password=PASSWORD)
    user = User.objects.create_user(username="vaciado_explicito", password=PASSWORD)
    user.profile.acceso_web = True
    user.profile.acceso_siis = True
    user.profile.save(update_fields=["acceso_web", "acceso_siis"])
    group, _ = Group.objects.get_or_create(name="Usuario Ver")
    permission = Permission.objects.get(
        content_type__app_label="auth", codename="view_user"
    )
    user.groups.add(group)
    user.user_permissions.add(permission)
    data = QueryDict(mutable=True)
    data.setlist("_identity_present", [field])
    form = CustomUserChangeForm(instance=user, actor=admin, data=data)
    assert form.is_valid(), form.errors
    form.save()
    user.refresh_from_db()
    if field in {"acceso_web", "acceso_siis"}:
        assert not getattr(user.profile, field)
    else:
        assert not getattr(user, field).exists()


def test_vaciado_presentado_revalida_dependencia_del_permiso():
    user = User.objects.create_user(username="vaciado_dependiente")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="pwa", codename="manage_nomina_pwa"
        )
    )
    data = QueryDict(mutable=True)
    data.setlist("_identity_present", ["user_permissions"])
    assert operacion_requiere_espacios(data, user)


def test_formulario_renderizado_declara_controles_vaciables(client, mocker):
    admin = User.objects.create_superuser(username="admin_presentes", password=PASSWORD)
    user = User.objects.create_user(username="formulario_presentes")
    client.force_login(admin)
    mocker.patch(
        "usuarios.views.reenviar_operacion_usuario",
        return_value=HttpResponse(status=503),
    )
    response = client.get(f"/usuarios/editar/{user.pk}/")
    assert response.status_code == 200
    presentes = set(
        re.findall(
            r'name="_identity_present"\s+value="([^"]+)"', response.content.decode()
        )
    )
    assert {"acceso_web", "acceso_siis", "groups", "user_permissions"} <= presentes


def test_marcador_no_habilita_campo_fuera_de_seccion_del_actor():
    from users.admin_forms import CustomUserChangeForm

    actor = User.objects.create_user(username="actor_sin_administracion")
    user = User.objects.create_user(username="acceso_protegido")
    user.profile.acceso_web = True
    user.profile.save(update_fields=["acceso_web"])
    data = QueryDict(mutable=True)
    data.setlist("_identity_present", ["acceso_web"])
    form = CustomUserChangeForm(instance=user, actor=actor, data=data)
    assert form.fields["acceso_web"].disabled
    assert form.is_valid(), form.errors
    form.save()
    user.refresh_from_db()
    assert user.profile.acceso_web


def test_autoedicion_provincial_no_declara_vaciado_de_control_deshabilitado(
    client, mocker
):
    from core.models import Provincia

    actor = User.objects.create_superuser(
        username="provincial_propio", password=PASSWORD
    )
    actor.profile.es_usuario_provincial = True
    actor.profile.provincia = Provincia.objects.create(nombre="Provincia propia")
    actor.profile.save(update_fields=["es_usuario_provincial", "provincia"])
    client.force_login(actor)
    remote = mocker.patch(
        "usuarios.views.reenviar_operacion_usuario",
        return_value=HttpResponse(status=503),
    )
    response = client.get(f"/usuarios/editar/{actor.pk}/")
    assert response.status_code == 200
    presentes = re.findall(
        r'name="_identity_present"\s+value="([^"]+)"', response.content.decode()
    )
    assert "es_usuario_provincial" not in presentes
    remote.reset_mock()
    response = client.post(
        f"/usuarios/editar/{actor.pk}/",
        {
            "first_name": "Independiente",
            "acceso_web": "on",
            "_identity_present": presentes,
        },
    )
    assert response.status_code == 302
    actor.refresh_from_db()
    assert actor.first_name == "Independiente"
    assert actor.profile.es_usuario_provincial
    remote.assert_not_called()


def test_delegacion_actual_sin_cambios_no_bloquea_guardado_personal(client, mocker):
    admin = User.objects.create_superuser(
        username="admin_delegacion", password=PASSWORD
    )
    user = User.objects.create_user(username="delegacion_sin_cambios")
    group = Group.objects.create(name="Delegacion de dominio conservada")
    group.permissions.add(
        Permission.objects.get(
            content_type__app_label="pwa", codename="manage_nomina_pwa"
        )
    )
    role = group.permissions.get(
        content_type__app_label="auth", codename__startswith="role_"
    )
    user.profile.grupos_asignables.add(group)
    user.profile.roles_asignables.add(role)
    client.force_login(admin)
    remote = mocker.patch(
        "usuarios.views.reenviar_operacion_usuario", side_effect=AssertionError
    )
    response = client.post(
        f"/usuarios/editar/{user.pk}/",
        {
            "first_name": "Personal",
            "grupos_asignables": [group.pk],
            "roles_asignables": [role.pk],
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.first_name == "Personal"
    assert user.profile.grupos_asignables.filter(pk=group.pk).exists()
    assert user.profile.roles_asignables.filter(pk=role.pk).exists()
    remote.assert_not_called()


def test_post_compuesto_no_guarda_identidad_si_dueno_no_responde(client, mocker):
    admin = User.objects.create_superuser(username="admin_bloqueo", password=PASSWORD)
    user = User.objects.create_user(username="sin_cambio", password=PASSWORD)
    client.force_login(admin)
    remote = mocker.patch(
        "usuarios.views.reenviar_operacion_usuario",
        return_value=HttpResponse(status=503),
    )
    response = client.post(
        f"/usuarios/editar/{user.pk}/",
        {
            "first_name": "No guardar",
            "comedores_pwa": [1],
            "requiere_espacios": "false",
        },
    )
    assert response.status_code == 503
    assert remote.call_count == 1
    user.refresh_from_db()
    assert user.first_name == ""


def test_operacion_compuesta_revierte_usuario_y_perfil_si_falla_dominio(client, mocker):
    admin = User.objects.create_superuser(username="admin_atomic", password=PASSWORD)
    comedor = Comedor.objects.create(nombre="Espacio atomic")
    client.force_login(admin)
    mocker.patch(
        "pwa.user_forms.UserCreationForm._sync_pwa_access",
        side_effect=RuntimeError("fallo dominio"),
    )
    with pytest.raises(RuntimeError, match="fallo dominio"):
        client.post(
            "/usuarios/crear/",
            {
                "username": "no_parcial",
                "tipo_usuario": "interno",
                "es_representante_pwa": "on",
                "tipo_asociacion_pwa": "espacio",
                "comedores_pwa": [comedor.pk],
            },
        )
    assert not User.objects.filter(username="no_parcial").exists()


def test_grupo_con_efecto_indirecto_se_clasifica_en_servidor():
    group = Group.objects.create(name="Grupo compuesto 2641")
    group.permissions.add(
        Permission.objects.get(
            content_type__app_label="pwa", codename="manage_nomina_pwa"
        )
    )
    data = QueryDict(mutable=True)
    data.setlist("groups", [str(group.pk)])
    assert operacion_requiere_espacios(data)


@pytest.mark.parametrize("name", ["Administrador", "Grupo desconocido 2641"])
def test_roles_arbitrarios_o_globales_no_se_eximen_por_ser_automaticos(name):
    group, _ = Group.objects.get_or_create(name=name)
    assert operacion_requiere_espacios({"groups": [group.pk]})


@pytest.mark.parametrize(
    "data",
    [
        None,
        {},
        {
            "pwa": {"roles": [], "read_only": False},
            "duplas_ids": [],
            "duplas_asignadas": [],
        },
    ],
)
def test_contexto_parcial_no_se_declara_disponible(entrevistador, mocker, data):
    token = Token.objects.create(user=entrevistador)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    mocker.patch(
        "usuarios.api_views.pedir_json_interno",
        return_value=RespuestaInterna(200, data),
    )
    response = client.get("/api/users/me/")
    assert response.status_code == 200
    assert response.data["espacios_comunitarios_disponible"] is False
    assert response.data["profile"]["datacalle_rol"] == "entrevistador"


def test_contexto_interno_no_autentica_por_header_de_usuario():
    user = User.objects.create_user(username="header_no_es_credencial")
    response = APIClient().get(
        "/interno/espacios/contexto/", HTTP_X_USER_ID=str(user.pk)
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "field, expected",
    [
        ("acceso_web", 403),
        ("must_change_password", 302),
        ("needs_profile_confirmation", 302),
    ],
)
def test_operacion_web_interna_conserva_controles_obligatorios(client, field, expected):
    admin = User.objects.create_superuser(
        username=f"control_{field}", password=PASSWORD
    )
    setattr(admin.profile, field, field != "acceso_web")
    admin.profile.save(update_fields=[field])
    client.force_login(admin)
    response = client.get("/interno/usuarios/operacion/")
    assert response.status_code == expected
    if field == "must_change_password":
        assert response["Location"] == "/password/first-change/"
    if field == "needs_profile_confirmation":
        assert response["Location"] == "/mi-cuenta/confirmar/"


def test_ruta_interna_revalida_alcance_y_csrf(client):
    actor = User.objects.create_user(username="actor_limitado", password=PASSWORD)
    actor.user_permissions.add(
        Permission.objects.get(content_type__app_label="auth", codename="change_user")
    )
    other = User.objects.create_user(username="fuera_del_alcance", password=PASSWORD)
    client.force_login(actor)
    assert (
        client.get(f"/interno/usuarios/operacion/?user_id={other.pk}").status_code
        == 404
    )
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(actor)
    assert (
        csrf_client.post(
            f"/interno/usuarios/operacion/?user_id={actor.pk}",
            {"first_name": "manipulado"},
        ).status_code
        == 403
    )


def test_timeout_despues_de_commit_no_reintenta_ni_promete_rollback(mocker):
    import requests
    from core.internal_services import reenviar_operacion_usuario

    user = User.objects.create_user(username="respuesta_perdida")
    request = RequestFactory().post(
        "/usuarios/editar/1/?user_id=999", {"first_name": "Guardado"}
    )
    body = request.body
    mocker.patch(
        "core.internal_services.backend_de_app",
        return_value={"origin": "http://backend_comedores:8000"},
    )

    def committed_then_timeout(*_args, **_kwargs):
        User.objects.filter(pk=user.pk).update(first_name="Guardado")
        raise requests.Timeout()

    remote = mocker.patch(
        "core.backend_proxy.requests.request", side_effect=committed_then_timeout
    )
    response = reenviar_operacion_usuario(request, user_id=user.pk, body=body)
    assert response.status_code == 504
    assert "No se pudo confirmar el resultado" in response.content.decode()
    assert remote.call_count == 1
    assert remote.call_args.kwargs["data"] == body
    assert remote.call_args.args[1].endswith(
        f"/interno/usuarios/operacion/?user_id={user.pk}"
    )
    user.refresh_from_db()
    assert user.first_name == "Guardado"


def test_revalida_efecto_de_grupo_al_guardar_sin_pisar_cambio_concurrente():
    from django.core.exceptions import ValidationError
    from users.admin_forms import CustomUserChangeForm

    admin = User.objects.create_superuser(username="admin_carrera", password=PASSWORD)
    user = User.objects.create_user(username="asignacion_concurrente")
    group, _ = Group.objects.get_or_create(name="Usuario Ver")
    form = CustomUserChangeForm(instance=user, actor=admin, data={"groups": [group.pk]})
    assert form.is_valid(), form.errors
    # El efecto del grupo cambia después de validar el formulario.
    group.permissions.add(
        Permission.objects.get(
            content_type__app_label="pwa", codename="manage_nomina_pwa"
        )
    )
    with pytest.raises(ValidationError, match="asignaciones cambiaron"):
        form.save()
    assert not user.groups.filter(pk=group.pk).exists()


def test_guardado_personal_no_pisa_permisos_o_flags_actualizados_despues_de_validar():
    from users.admin_forms import CustomUserChangeForm

    admin = User.objects.create_superuser(username="admin_personal", password=PASSWORD)
    user = User.objects.create_user(username="carrera_personal")
    form = CustomUserChangeForm(
        instance=user, actor=admin, data={"first_name": "Actualizado"}
    )
    assert form.is_valid(), form.errors
    permission = Permission.objects.get(
        content_type__app_label="pwa", codename="manage_nomina_pwa"
    )
    user.user_permissions.add(permission)
    user.profile.es_coordinador = True
    user.profile.save(update_fields=["es_coordinador"])
    form.save()
    user.refresh_from_db()
    assert user.first_name == "Actualizado"
    assert user.profile.es_coordinador
    assert user.user_permissions.filter(pk=permission.pk).exists()
