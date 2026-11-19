"""Permisos docentes, aislamiento por centro y contacto en alta manual."""

from datetime import time
import re

import pytest
from django.contrib.auth.models import Group, User
from django.urls import reverse
from django.utils import timezone

from core.models import Dia
from VAT.forms import CentroForm, CiudadanoInscripcionRapidaForm
from VAT.models import (
    AsistenciaSesion,
    Centro,
    ComisionHorario,
    Inscripcion,
    ProfesorCentro,
    SesionComision,
)
from VAT.services.access_scope import (
    can_user_access_centro,
    can_user_edit_centro,
    filter_centros_queryset_for_user,
    filter_centros_queryset_for_management,
    puede_ver_usuarios_centro_vat,
)
from VAT.test_comision_detail_template_compartido import escenario  # noqa: F401


@pytest.fixture
def docente(escenario):
    _, comision, _ = escenario
    user = User.objects.create_user(username="docente-prueba", password="prueba-local")
    group, _ = Group.objects.get_or_create(name="INET Asistencia")
    user.groups.add(group)
    comision.curso.centro.referentes.add(user)
    return user


def sesion_para(comision):
    dia, _ = Dia.objects.get_or_create(nombre="Lunes")
    horario = ComisionHorario.objects.create(
        comision_curso=comision,
        dia_semana=dia,
        hora_desde=time(10),
        hora_hasta=time(12),
    )
    return SesionComision.objects.create(
        comision_curso=comision,
        horario=horario,
        numero_sesion=1,
        fecha=timezone.localdate(),
    )


@pytest.mark.django_db
def test_estilos_del_recorrido_docente_tienen_nonce_csp(docente, escenario, client):
    _, comision, _ = escenario
    sesion = sesion_para(comision)
    client.force_login(docente)
    for route, pk in (
        ("vat_centro_detail", comision.curso.centro_id),
        ("vat_curso_detail", comision.curso_id),
        ("vat_comision_curso_detail", comision.pk),
        ("vat_asistencia_sesion_curso", sesion.pk),
    ):
        response = client.get(reverse(route, args=[pk]))
        assert response.status_code == 200
        nonce = response.wsgi_request.csp_nonce
        styles = re.findall(r"<style\b[^>]*>", response.content.decode())
        assert styles
        assert all(f'nonce="{nonce}"' in style for style in styles), route


@pytest.mark.django_db
def test_docente_solo_ve_centro_asignado_y_no_gestiona(docente, escenario, client):
    _, comision, _ = escenario
    centro = comision.curso.centro
    otro = Centro.objects.create(nombre="Otro centro", codigo="OTRO")
    assert list(filter_centros_queryset_for_user(Centro.objects.all(), docente)) == [
        centro
    ]
    assert can_user_access_centro(docente, centro)
    assert not can_user_access_centro(docente, otro)
    assert not can_user_edit_centro(docente, centro)
    assert not filter_centros_queryset_for_management(
        Centro.objects.all(), docente
    ).exists()
    assert not puede_ver_usuarios_centro_vat(docente, centro)
    assert docente in CentroForm().fields["referentes"].queryset
    client.force_login(docente)
    response = client.get(reverse("vat_comision_curso_detail", args=[comision.pk]))
    assert response.status_code == 200
    html = response.content.decode()
    for tab in ("general", "sesiones", "resultados"):
        assert f'data-sisoc-tab-target="{tab}"' in html
    for tab in ("inscriptos", "espera", "horarios"):
        assert f'data-sisoc-tab-target="{tab}"' not in html
        assert f'data-sisoc-panel="{tab}"' not in html
    assert response.context["puede_gestionar_asistencia"]
    assert not response.context["puede_editar_comision"]
    assert client.get(reverse("vat_centro_detail", args=[otro.pk])).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("asignacion", ["ninguna", "otro", "legada"])
def test_alcance_en_operaciones_docentes(docente, escenario, client, asignacion):
    _, comision, _ = escenario
    centro = comision.curso.centro
    centro.referentes.remove(docente)
    if asignacion == "otro":
        Centro.objects.create(nombre="Otro", codigo="OTRO").referentes.add(docente)
    elif asignacion == "legada":
        centro.referente = docente
        centro.save()
    client.force_login(docente)
    sesion = sesion_para(comision)
    expected = 200 if asignacion == "legada" else 404
    for name, pk in (
        ("vat_comision_curso_detail", comision.pk),
        ("vat_asistencia_sesion_curso", sesion.pk),
        ("vat_profesor_centro_buscar", comision.pk),
    ):
        assert client.get(reverse(name, args=[pk])).status_code == expected
    if asignacion != "legada":
        assert (
            client.post(
                reverse("vat_asistencia_sesion_curso", args=[sesion.pk])
            ).status_code
            == 404
        )
        assert (
            client.post(
                reverse("vat_comision_curso_resultados", args=[comision.pk])
            ).status_code
            == 404
        )
        assert not AsistenciaSesion.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "route",
    [
        "vat_curso_update",
        "vat_curso_delete",
        "vat_comision_curso_update",
        "vat_comision_curso_delete",
        "vat_comision_curso_resultados",
    ],
)
def test_sin_permiso_no_habilita_acciones(escenario, client, route):
    _, comision, _ = escenario
    user = User.objects.create_user(username="sin-permisos")
    comision.curso.centro.referentes.add(user)
    client.force_login(user)
    assert client.post(reverse(route, args=[comision.pk])).status_code == 403


@pytest.mark.django_db
def test_docente_guarda_asistencia_y_resultados(docente, escenario, client):
    _, comision, _ = escenario
    sesion = sesion_para(comision)
    inscripcion = Inscripcion.objects.get(comision_curso=comision)
    client.force_login(docente)
    response = client.post(
        reverse("vat_asistencia_sesion_curso", args=[sesion.pk]),
        {f"presente_{inscripcion.pk}": "1"},
    )
    assert response.status_code == 302
    assert AsistenciaSesion.objects.get(sesion=sesion, inscripcion=inscripcion).presente
    profesor = ProfesorCentro.objects.create(
        centro=comision.curso.centro,
        nombre="Docente",
        apellido="Prueba",
        documento="30123456",
        email="docente@example.com",
    )
    response = client.post(
        reverse("vat_comision_curso_resultados", args=[comision.pk]),
        {
            "profesor": profesor.pk,
            "fecha_fin": comision.fecha_fin.isoformat(),
            "numero_acta": "PRUEBA-1",
            f"resultado_{inscripcion.pk}": "aprobado",
        },
    )
    assert response.status_code == 302
    inscripcion.refresh_from_db()
    assert inscripcion.resultado_final == "aprobado"
    assert inscripcion.resultado_registrado_por == docente


@pytest.mark.django_db
@pytest.mark.parametrize(
    "route",
    [
        "vat_curso_update",
        "vat_curso_delete",
        "vat_comision_curso_update",
        "vat_comision_curso_delete",
        "vat_comision_curso_export_inscriptos",
        "vat_comision_curso_export_preinscriptos",
        "vat_profesor_centro_crear",
        "vat_inscripcion_curso_cambiar_estado",
        "vat_inscripcion_curso_cambiar_estado_lote",
        "vat_comision_curso_horario_update",
        "vat_comision_curso_horario_delete",
    ],
)
def test_docente_no_accede_gestion_por_url(docente, escenario, client, route):
    _, comision, _ = escenario
    client.force_login(docente)
    url = reverse(route, args=[comision.pk])
    assert client.get(url).status_code == 403
    assert client.post(url).status_code in (403, 405)


@pytest.mark.django_db
def test_docente_con_cfp_conserva_gestion(docente, escenario, client):
    _, comision, _ = escenario
    docente.groups.add(Group.objects.get(name="CFP"))
    client.force_login(docente)
    response = client.get(reverse("vat_comision_curso_detail", args=[comision.pk]))
    assert response.status_code == 200
    assert 'data-sisoc-tab-target="inscriptos"' in response.content.decode()
    assert response.context["puede_editar_comision"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "contacto",
    [
        {},
        {"telefono": "+54 11 1234-5678"},
        {"email": "alumno@example.com"},
        {"telefono": "123", "email": "alumno@example.com"},
    ],
)
def test_alta_manual_persiste_contacto_opcional(contacto):
    form = CiudadanoInscripcionRapidaForm(
        {
            "apellido": "Prueba",
            "nombre": "Contacto",
            "fecha_nacimiento": "2000-01-01",
            "tipo_documento": "DNI",
            "documento": "30111223",
            **contacto,
        }
    )
    assert form.is_valid(), form.errors
    ciudadano = form.save()
    ciudadano.refresh_from_db()
    assert (ciudadano.telefono or "") == contacto.get("telefono", "")
    assert (ciudadano.email or "") == contacto.get("email", "")


@pytest.mark.django_db
def test_mail_invalido_conserva_valores():
    form = CiudadanoInscripcionRapidaForm({"email": "invalido", "telefono": "123"})
    assert not form.is_valid()
    assert "email" in form.errors
    assert form["email"].value() == "invalido"
    assert form["telefono"].value() == "123"
