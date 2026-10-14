"""Sección "Inspecciones escolares" del ABM de usuarios y acceso a la PWA.

Mismo patrón que DataCalle: flag ``Profile.es_inspector_escolar`` + rol en
``Profile.inspecciones_rol``. El inspector es usuario sólo de la app.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from users.models import Profile, UserImportJob
from users.secciones_usuario import (
    SECCION_INSPECCIONES_ESCOLARES,
    TODAS_LAS_SECCIONES,
    permiso_de_seccion,
)
from core.services.sidebar_access import resolver_predicado_sidebar
from users.services_inspecciones import (
    es_coordinacion_inspecciones,
    tiene_acceso_inspecciones,
)
from usuarios.forms import CustomUserChangeForm, UserCreationForm
from usuarios.services_user_import import process_single_user_import_row

pytestmark = pytest.mark.django_db

User = get_user_model()
TARJETA = b'id="inspecciones-escolares-card"'


def _datos_alta(**extra):
    return {
        "username": "inspector_alta",
        "email": "inspector_alta@example.com",
        "password": "Sisoc12345!",
        "tipo_usuario": "interno",
        "acceso_web": True,
        "es_inspector_escolar": True,
        "inspecciones_rol": "inspector",
        **extra,
    }


def _usuario(username, *, rol="inspector", flag=True, password="testpass123"):
    user = User.objects.create_user(username=username, password=password)
    user.profile.es_inspector_escolar = flag
    user.profile.inspecciones_rol = rol
    user.profile.save(update_fields=["es_inspector_escolar", "inspecciones_rol"])
    return user


def _cliente_con_token(user):
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


# ------------------------------------------------------------- formulario


def test_alta_de_inspector_guarda_flag_y_rol_y_es_solo_app():
    form = UserCreationForm(data=_datos_alta())

    assert form.is_valid(), form.errors
    user = form.save()
    user.refresh_from_db()

    assert user.profile.es_inspector_escolar is True
    assert user.profile.inspecciones_rol == Profile.InspeccionesRol.INSPECTOR
    # Usuario de la app: sin SISOC web ni backoffice aunque la casilla venga tildada.
    assert user.profile.acceso_web is False
    assert user.is_staff is False
    assert user.profile.must_change_password is True
    assert tiene_acceso_inspecciones(user) is True


def test_alta_de_coordinacion_conserva_el_acceso_web():
    form = UserCreationForm(
        data=_datos_alta(username="coord_alta", inspecciones_rol="coordinacion")
    )

    assert form.is_valid(), form.errors
    user = form.save()

    assert user.profile.inspecciones_rol == Profile.InspeccionesRol.COORDINACION
    assert user.profile.acceso_web is True
    assert es_coordinacion_inspecciones(user) is True


def test_el_flag_sin_rol_no_valida():
    form = UserCreationForm(data=_datos_alta(inspecciones_rol=""))

    assert form.is_valid() is False
    assert "inspecciones_rol" in form.errors


def test_sin_flag_el_rol_se_descarta():
    form = UserCreationForm(
        data=_datos_alta(username="sin_flag", es_inspector_escolar=False)
    )

    assert form.is_valid(), form.errors
    user = form.save()

    assert user.profile.es_inspector_escolar is False
    assert user.profile.inspecciones_rol == ""
    assert tiene_acceso_inspecciones(user) is False


def test_edicion_cambia_el_rol_y_destildar_lo_limpia():
    user = UserCreationForm(data=_datos_alta(username="edit_insp")).save()
    datos = {
        "username": "edit_insp",
        "email": "edit_insp@example.com",
        "tipo_usuario": "interno",
        "es_inspector_escolar": True,
        "inspecciones_rol": "coordinacion",
    }

    form = CustomUserChangeForm(data=datos, instance=user)
    assert form.is_valid(), form.errors
    form.save()
    user.refresh_from_db()
    assert user.profile.inspecciones_rol == "coordinacion"

    datos["es_inspector_escolar"] = False
    form = CustomUserChangeForm(data=datos, instance=user)
    assert form.is_valid(), form.errors
    form.save()
    user.refresh_from_db()
    assert user.profile.es_inspector_escolar is False
    assert user.profile.inspecciones_rol == ""


def test_actor_sin_la_seccion_no_puede_marcar_el_flag():
    actor = User.objects.create_user(username="actor_sin_secc", password="x")
    actor.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="auth", codename__in=["add_user", "change_user"]
        )
    )
    actor = User.objects.get(pk=actor.pk)
    form = UserCreationForm(data=_datos_alta(username="colado"), actor=actor)

    assert form.fields["es_inspector_escolar"].disabled is True
    assert form.is_valid(), form.errors
    user = form.save()
    assert user.profile.es_inspector_escolar is False


def test_la_seccion_tiene_permiso_propio_y_tarjeta_en_el_alta(client):
    assert SECCION_INSPECCIONES_ESCOLARES in TODAS_LAS_SECCIONES
    codigo = permiso_de_seccion(SECCION_INSPECCIONES_ESCOLARES)
    assert codigo == "auth.role_usuarios_seccion_inspecciones_escolares"

    superusuario = User.objects.create_superuser(username="super_insp", password="x")
    client.force_login(superusuario)
    contenido = client.get(reverse("usuario_crear")).content

    assert TARJETA in contenido
    assert b'name="es_inspector_escolar"' in contenido
    assert b'name="inspecciones_rol"' in contenido


# ------------------------------------------------------------- API de usuarios


def test_users_me_expone_flag_y_rol_de_inspecciones():
    user = _usuario("me_inspector")
    user.profile.must_change_password = True
    user.profile.save(update_fields=["must_change_password"])

    response = _cliente_con_token(user).get("/api/users/me/")

    assert response.status_code == 200
    assert response.data["profile"]["es_inspector_escolar"] is True
    assert response.data["profile"]["inspecciones_rol"] == "inspector"
    assert response.data["pwa"]["must_change_password"] is True


def test_users_me_sin_programa_expone_valores_vacios():
    user = User.objects.create_user(username="me_sin_programa", password="x")

    response = _cliente_con_token(user).get("/api/users/me/")

    assert response.data["profile"]["es_inspector_escolar"] is False
    assert response.data["profile"]["inspecciones_rol"] == ""


@pytest.mark.parametrize("rol", ["inspector", "coordinacion"])
def test_login_pwa_acepta_usuarios_de_inspecciones(rol):
    _usuario(f"login_{rol}", rol=rol)

    response = APIClient().post(
        "/api/users/login/",
        {"username": f"login_{rol}", "password": "testpass123"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["token_type"] == "Token"


def test_login_pwa_rechaza_flag_sin_rol():
    _usuario("login_sin_rol", rol="")

    response = APIClient().post(
        "/api/users/login/",
        {"username": "login_sin_rol", "password": "testpass123"},
        format="json",
    )

    assert response.status_code == 401


# ------------------------------------------------------------- importador


def _job():
    actor = User.objects.create_superuser(username="importador", password="x")
    return UserImportJob.objects.create(
        requested_by=actor, original_filename="usuarios.xlsx", total_rows=1
    )


def _fila(**valores):
    return {
        "nombre": "Ana",
        "apellido": "Gómez",
        "correo": "ana.gomez@example.com",
        "dni": "30.111.222",
        "inspecciones": "Inspector",
        "permisos": "",
        "provincias": "",
        "rol": "",
        "fila": 2,
        **valores,
    }


def test_importador_da_de_alta_inspectores_con_dni_y_rol():
    resultado = process_single_user_import_row(row_data=_fila(), job=_job())

    user = User.objects.get(pk=resultado["created_user_id"])
    assert user.profile.es_inspector_escolar is True
    assert user.profile.inspecciones_rol == "inspector"
    assert user.profile.dni == "30111222"
    assert user.profile.acceso_web is False
    assert user.is_staff is False
    assert user.profile.must_change_password is True


def test_importador_rechaza_dni_o_correo_duplicados():
    job = _job()
    process_single_user_import_row(row_data=_fila(), job=job)

    with pytest.raises(ValidationError, match="DNI"):
        process_single_user_import_row(
            row_data=_fila(correo="otra@example.com"), job=job
        )
    with pytest.raises(ValidationError, match="correo"):
        process_single_user_import_row(row_data=_fila(dni="40111222"), job=job)


def test_importador_exige_dni_y_rol_valido():
    job = _job()
    with pytest.raises(ValidationError, match="DNI"):
        process_single_user_import_row(row_data=_fila(dni=""), job=job)
    with pytest.raises(ValidationError, match="Inspecciones"):
        process_single_user_import_row(row_data=_fila(inspecciones="director"), job=job)


def _job_de(actor):
    return UserImportJob.objects.create(
        requested_by=actor, original_filename="usuarios.xlsx", total_rows=1
    )


def _actor_importador(username, *, con_seccion):
    """Actor con ``auth.add_user`` (lo que exige el importador)."""
    actor = User.objects.create_user(username=username, password="x")
    actor.user_permissions.add(
        Permission.objects.get(content_type__app_label="auth", codename="add_user")
    )
    if con_seccion:
        # El permiso de la sección lo crea una data migration: no se asume en
        # la base de tests (mismo criterio que test_users_secciones_por_permiso).
        codename = permiso_de_seccion(SECCION_INSPECCIONES_ESCOLARES).split(".")[1]
        permiso, _ = Permission.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(Group),
            codename=codename,
            defaults={"name": codename},
        )
        actor.user_permissions.add(permiso)
    return User.objects.get(pk=actor.pk)


def test_importador_sin_la_seccion_no_da_de_alta_roles_de_inspecciones():
    job = _job_de(_actor_importador("importa_sin_secc", con_seccion=False))

    with pytest.raises(ValidationError, match="Inspecciones escolares"):
        process_single_user_import_row(
            row_data=_fila(inspecciones="coordinacion"), job=job
        )
    assert not User.objects.filter(email="ana.gomez@example.com").exists()


def test_importador_sin_la_seccion_no_se_autoasigna_coordinacion():
    actor = _actor_importador("importa_propio", con_seccion=False)
    fila = _fila(
        username=actor.username,
        correo="",
        nombre="",
        apellido="",
        inspecciones="coordinacion",
    )

    with pytest.raises(ValidationError, match="Inspecciones escolares"):
        process_single_user_import_row(row_data=fila, job=_job_de(actor))
    actor.profile.refresh_from_db()
    assert actor.profile.es_inspector_escolar is False
    assert es_coordinacion_inspecciones(actor) is False


def test_importador_con_la_seccion_asigna_el_rol_a_un_usuario_existente():
    existente = User.objects.create_user(
        username="ya_existe", email="ya.existe@example.com", password="x"
    )
    job = _job_de(_actor_importador("importa_con_secc", con_seccion=True))
    fila = _fila(
        username="ya_existe",
        correo="ya.existe@example.com",
        inspecciones="coordinacion",
    )

    process_single_user_import_row(row_data=fila, job=job)

    existente.profile.refresh_from_db()
    assert existente.profile.inspecciones_rol == "coordinacion"
    assert existente.profile.dni == "30111222"
    assert es_coordinacion_inspecciones(User.objects.get(pk=existente.pk)) is True


# ------------------------------------------------------------- menú lateral


@pytest.mark.parametrize(
    ("rol", "esperado"), [("coordinacion", True), ("inspector", False)]
)
def test_link_del_panel_en_el_menu_sigue_a_quien_puede_gestionar(rol, esperado):
    usuario = _usuario(f"menu_{rol}", rol=rol)

    assert resolver_predicado_sidebar("inspecciones_gestion", usuario) is esperado


def test_link_del_panel_en_el_menu_con_el_permiso_explicito():
    usuario = User.objects.create_user(username="menu_permiso", password="x")
    usuario.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="inspecciones", codename="gestionar_inspecciones"
        )
    )
    usuario = User.objects.get(pk=usuario.pk)

    assert resolver_predicado_sidebar("inspecciones_gestion", usuario) is True
