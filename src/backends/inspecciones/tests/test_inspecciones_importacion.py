"""Backoffice: importación CSV de escuelas y asignaciones, y acceso al panel."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from inspecciones.models import AsignacionEscuela, Escuela
from inspecciones.services.importacion import (
    importar_asignaciones,
    importar_escuelas,
)

pytestmark = pytest.mark.django_db


def _csv(texto, encoding="utf-8"):
    return SimpleUploadedFile(
        "datos.csv", texto.encode(encoding), content_type="text/csv"
    )


ESCUELAS = (
    "CUE;Nombre;Distrito;Localidad;Domicilio;Nivel\n"
    "060123400;EP N° 12;La Matanza;San Justo;Perón 3245;Primario\n"
    "060456700;ES N° 45;La Matanza;Ramos Mejía;Belgrano 210;Secundario\n"
    "06-04;Mal CUE;;;;\n"
    ";Sin CUE;;;;\n"
)


def test_importar_escuelas_conserva_ceros_y_reporta_rechazos():
    resultado = importar_escuelas(_csv(ESCUELAS))

    assert resultado.total == 4
    assert resultado.creadas == 2
    assert [r["fila"] for r in resultado.rechazadas] == [4, 5]
    escuela = Escuela.objects.get(codigo="060123400")
    assert escuela.cue == "060123400"
    assert escuela.localidad == "San Justo"


def test_reimportar_actualiza_sin_duplicar():
    importar_escuelas(_csv(ESCUELAS))
    cambiado = ESCUELAS.replace("Perón 3245", "Perón 3300")

    resultado = importar_escuelas(_csv(cambiado, encoding="cp1252"))

    assert resultado.creadas == 0
    assert resultado.actualizadas == 1
    assert resultado.sin_cambios == 1
    assert Escuela.objects.count() == 2
    assert Escuela.objects.get(codigo="060123400").domicilio == "Perón 3300"


def test_importar_escuelas_exige_columnas():
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError, match="cue"):
        importar_escuelas(_csv("nombre\nEscuela\n"))


def test_importar_asignaciones(inspector_a, coordinacion, escuela):
    ajeno = get_user_model().objects.create_user(username="sin_programa")
    inspector_a.profile.dni = "30111222"
    inspector_a.profile.save(update_fields=["dni"])
    texto = (
        "fecha,escuela,inspector\n"
        f"2026-10-15,{escuela.cue},inspector_a\n"
        "15/10/2026,060123400,30111222\n"
        "2026-10-15,999,inspector_a\n"
        "2026-10-15,060123400,sin_programa\n"
        "ayer,060123400,inspector_a\n"
    )

    resultado = importar_asignaciones(_csv(texto), actor=coordinacion)

    assert resultado.creadas == 1
    assert resultado.sin_cambios == 1
    assert [r["fila"] for r in resultado.rechazadas] == [4, 5, 6]
    asignacion = AsignacionEscuela.objects.get()
    assert asignacion.inspector == inspector_a
    assert asignacion.creada_por == coordinacion
    assert ajeno.asignaciones_inspeccion.count() == 0


def test_panel_solo_para_coordinacion_o_permiso(client, inspector_a, coordinacion):
    url = reverse("inspecciones_panel")

    client.force_login(inspector_a)
    assert client.get(url).status_code == 403

    client.force_login(coordinacion)
    assert client.get(url).status_code == 200

    gestor = get_user_model().objects.create_user(username="gestor", password="x")
    gestor.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="inspecciones", codename="gestionar_inspecciones"
        )
    )
    client.force_login(gestor)
    assert client.get(url).status_code == 200


def test_panel_importa_escuelas(client, coordinacion):
    client.force_login(coordinacion)

    response = client.post(
        reverse("inspecciones_importar_escuelas"),
        {"escuelas-archivo": _csv(ESCUELAS)},
    )

    assert response.status_code == 200
    assert response.context["resultado"].creadas == 2
    assert "Fila 4" in response.content.decode()
