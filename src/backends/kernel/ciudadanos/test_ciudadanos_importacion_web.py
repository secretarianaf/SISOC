"""Importación masiva de ciudadanos en JSON (C01.01, C01.02): carga, lote, reanudar y rechazos."""

from io import BytesIO

import pytest
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone
from openpyxl import Workbook

from ciudadanos.models import Ciudadano, CiudadanosImportJob, CiudadanosImportJobRow

pytestmark = pytest.mark.django_db

PERM = "ciudadanos.add_ciudadano"
BASE = "/api/web/ciudadanos/importacion-masiva/"


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _cliente(username, permisos=(PERM,), csrf=False):
    user = User.objects.create_user(username=username, password="x")
    for codigo in permisos:
        app, codename = codigo.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    client = Client(enforce_csrf_checks=csrf)
    client.force_login(user)
    return client, user


def _excel(nombre="ciudadanos.xlsx", filas=(("20301112223", "M"),)):
    libro = Workbook()
    hoja = libro.active
    hoja.append(["cuil_o_dni", "sexo"])
    for fila in filas:
        hoja.append(list(fila))
    salida = BytesIO()
    libro.save(salida)
    return SimpleUploadedFile(nombre, salida.getvalue())


def _lote(user, **campos):
    job = CiudadanosImportJob(requested_by=user, original_filename="lote.xlsx")
    job.archivo.save("lote.xlsx", _excel(), save=False)
    for nombre, valor in campos.items():
        setattr(job, nombre, valor)
    job.save()
    return job


def _estado():
    return {
        "lotes": list(
            CiudadanosImportJob.objects.order_by("pk").values_list(
                "pk", "status", "resume_count", "last_error_message"
            )
        ),
        "filas": CiudadanosImportJobRow.objects.count(),
        "ciudadanos": Ciudadano.objects.count(),
    }


def test_formulario_proyecta_el_template_y_los_lotes_recientes():
    client, user = _cliente("imp_get")
    job = _lote(
        user,
        status=CiudadanosImportJob.Status.COMPLETED_WITH_ERRORS,
        created_rows=2,
        existing_rows=3,
        failed_rows=1,
        pending_rows=4,
    )
    respuesta = client.get(BASE)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["campo"] == {"label": "Archivo Excel", "accept": ".xlsx"}
    assert datos["errors"] == {}
    assert datos["plantilla_url"] == "/ciudadanos/importacion-masiva/plantilla/"
    assert datos["volver_url"] == "/ciudadanos/listar"
    assert datos["messages"] == []
    (fila,) = datos["lotes"]
    assert fila["id"] == job.pk
    assert fila["usuario_texto"] == "imp_get"
    assert fila["estado"] == "completed_with_errors"
    assert [fila[k] for k in ("creados", "existentes", "fallidos", "pendientes")] == [
        2,
        3,
        1,
        4,
    ]
    assert fila["detalle_url"] == f"/ciudadanos/importacion-masiva/lotes/{job.pk}/"
    # Local time (America/Argentina/Buenos_Aires), as the native ``|date`` filter prints it.
    job.refresh_from_db()
    assert fila["fecha_texto"] == timezone.localtime(job.requested_at).strftime(
        "%d/%m/%Y %H:%M"
    )
    assert "no-store" in respuesta["Cache-Control"]
    assert _estado()["lotes"] == [(job.pk, "completed_with_errors", 0, "")]


def test_carga_valida_crea_el_lote_y_deja_el_mensaje():
    client, user = _cliente("imp_post")
    respuesta = client.post(BASE, {"archivo": _excel("padron.xlsx")})
    assert respuesta.status_code == 200
    job = CiudadanosImportJob.objects.get()
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/ciudadanos/importacion-masiva/lotes/{job.pk}/",
    }
    assert job.requested_by == user
    assert job.original_filename == "padron.xlsx"
    assert job.status == CiudadanosImportJob.Status.PENDING
    assert job.archivo.name.endswith(".xlsx")
    # La carga no procesa filas ni toca ciudadanos: eso es del worker.
    assert _estado()["filas"] == 0
    assert _estado()["ciudadanos"] == 0
    # El mensaje queda en cola para la próxima página.
    mensajes = client.get(BASE).json()["messages"]
    assert mensajes == [
        {
            "message": "Lote creado. El worker lo procesara de forma asincronica.",
            "level": "success",
        }
    ]
    assert client.get(BASE).json()["messages"] == []


def test_carga_invalida_responde_400_y_no_crea_lote():
    client, _ = _cliente("imp_mal")
    antes = _estado()
    sin_archivo = client.post(BASE, {})
    assert sin_archivo.status_code == 400
    assert sin_archivo.json()["errors"]["archivo"] == ["Este campo es requerido."]
    otra_extension = client.post(
        BASE, {"archivo": SimpleUploadedFile("datos.csv", b"cuil_o_dni\n1")}
    )
    assert otra_extension.status_code == 400
    assert "archivo" in otra_extension.json()["errors"]
    assert otra_extension.json()["campo"]["accept"] == ".xlsx"
    assert _estado() == antes


def test_lote_proyecta_contadores_filas_y_pagina():
    client, user = _cliente("imp_lote")
    ana = Ciudadano.objects.create(nombre="Ana", apellido="Lote", documento=30111222)
    job = _lote(
        user,
        status=CiudadanosImportJob.Status.FAILED,
        total_rows=60,
        processed_rows=10,
        resume_count=2,
        last_successful_documento="30111222",
        last_successful_row=3,
        last_error_message="Se cayó el servicio",
        last_error_type="TimeoutError",
    )
    for numero in range(1, 61):
        CiudadanosImportJobRow.objects.create(
            job=job,
            fila=numero,
            documento_raw=f"2030000{numero:04d}",
            status=CiudadanosImportJobRow.Status.PENDING,
            ciudadano=ana if numero == 1 else None,
            mensaje="Creado" if numero == 1 else "",
        )
    primera = client.get(f"{BASE}lotes/{job.pk}/")
    assert primera.status_code == 200
    datos = primera.json()
    assert datos["id"] == job.pk
    assert datos["archivo"] == "lote.xlsx"
    assert datos["estado"] == "failed"
    assert datos["reanudaciones"] == 2
    assert (datos["totales"], datos["procesadas"]) == (60, 10)
    assert datos["ultimo_correcto"] == {"documento": "30111222", "fila_texto": "3"}
    assert datos["ultimo_intentado"] == {"documento": "", "fila_texto": "-"}
    assert datos["error_mensaje"] == "Se cayó el servicio"
    assert datos["error_tipo"] == "TimeoutError"
    assert datos["puede_reanudar"] is True
    assert datos["paginacion"] == {
        "number": 1,
        "num_pages": 2,
        "previous": False,
        "next": True,
    }
    assert len(datos["filas"]) == 50
    assert datos["filas"][0]["ciudadano_url"] == f"/ciudadanos/ver/{ana.pk}"
    assert datos["filas"][0]["mensaje"] == "Creado"
    assert datos["filas"][1]["mensaje"] == "-"
    assert datos["filas"][1]["ciudadano_url"] is None
    assert datos["lista_url"] == "/ciudadanos/listar"
    assert datos["volver_url"] == "/ciudadanos/importacion-masiva/"
    assert datos["exportar_url"] == (
        f"/ciudadanos/importacion-masiva/lotes/{job.pk}/exportar/"
    )
    segunda = client.get(f"{BASE}lotes/{job.pk}/?page=2").json()
    assert [f["fila"] for f in segunda["filas"]] == list(range(51, 61))
    assert segunda["paginacion"]["previous"] is True
    # Como el Paginator nativo: una página fuera de rango cae en la última.
    assert (
        client.get(f"{BASE}lotes/{job.pk}/?page=99").json()["paginacion"]["number"] == 2
    )


def test_lote_no_reanudable_y_lote_inexistente():
    client, user = _cliente("imp_404")
    job = _lote(user, status=CiudadanosImportJob.Status.COMPLETED)
    assert client.get(f"{BASE}lotes/{job.pk}/").json()["puede_reanudar"] is False
    assert client.get(f"{BASE}lotes/999999/").status_code == 404
    assert client.post(f"{BASE}lotes/999999/reanudar/").status_code == 404


def test_reanudar_un_lote_fallido_escribe_lo_nativo():
    client, user = _cliente("imp_res")
    job = _lote(
        user,
        status=CiudadanosImportJob.Status.FAILED,
        last_error_message="Se cayó",
        last_error_type="X",
    )
    respuesta = client.post(f"{BASE}lotes/{job.pk}/reanudar/")
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/ciudadanos/importacion-masiva/lotes/{job.pk}/",
    }
    job.refresh_from_db()
    assert job.status == CiudadanosImportJob.Status.PENDING
    assert job.resume_count == 1
    assert job.last_error_message == ""
    mensajes = client.get(f"{BASE}lotes/{job.pk}/").json()["messages"]
    assert mensajes == [
        {"message": "Lote marcado para reanudacion.", "level": "success"}
    ]


def test_reanudar_un_lote_no_fallido_se_rechaza_sin_escribir():
    client, user = _cliente("imp_noresume")
    job = _lote(user, status=CiudadanosImportJob.Status.COMPLETED)
    antes = _estado()
    respuesta = client.post(f"{BASE}lotes/{job.pk}/reanudar/")
    assert respuesta.status_code == 200
    assert _estado() == antes
    mensajes = client.get(f"{BASE}lotes/{job.pk}/").json()["messages"]
    assert mensajes == [
        {"message": "Solo se pueden reanudar lotes fallidos.", "level": "error"}
    ]


def test_rechazos_no_crean_ni_reanudan():
    _, dueno = _cliente("imp_dueno")
    job = _lote(dueno, status=CiudadanosImportJob.Status.FAILED)
    antes = _estado()
    rutas = (BASE, f"{BASE}lotes/{job.pk}/", f"{BASE}lotes/{job.pk}/reanudar/")
    anonimo = Client()
    sin_permiso, _ = _cliente("imp_sin", ("ciudadanos.view_ciudadano",))
    for ruta in rutas:
        assert anonimo.get(ruta).status_code == 401
        assert sin_permiso.get(ruta).status_code in (403, 405)
    assert anonimo.post(BASE, {"archivo": _excel()}).status_code == 401
    assert sin_permiso.post(BASE, {"archivo": _excel()}).status_code == 403
    assert sin_permiso.post(f"{BASE}lotes/{job.pk}/reanudar/").status_code == 403
    # Sin permiso un lote inexistente tampoco filtra: 403 antes que 404.
    assert sin_permiso.get(f"{BASE}lotes/999999/").status_code == 403
    con_permiso, _ = _cliente("imp_ok")
    assert con_permiso.put(BASE).status_code == 405
    assert con_permiso.post(f"{BASE}lotes/{job.pk}/").status_code == 405
    assert _estado() == antes


def test_carga_y_reanudar_exigen_csrf():
    cliente, dueno = _cliente("imp_csrf", csrf=True)
    job = _lote(dueno, status=CiudadanosImportJob.Status.FAILED)
    antes = _estado()
    assert cliente.post(BASE, {"archivo": _excel()}).status_code == 403
    assert cliente.post(f"{BASE}lotes/{job.pk}/reanudar/").status_code == 403
    assert _estado() == antes
