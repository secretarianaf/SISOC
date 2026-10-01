"""Boton "Volver" unificado en todas las pantallas (issue #2460)."""

import pathlib
import re

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

RAIZ = pathlib.Path(__file__).resolve().parent.parent

EXTIENDE_MAIN = 'extends "includes/main.html"'

# Pantallas de error: su "volver al inicio" es un link dentro de un parrafo.
EXCLUIDOS = {
    "templates/403.html",
    "templates/404.html",
    "templates/500.html",
}


def _templates_de_pantalla():
    for ruta in RAIZ.rglob("*.html"):
        partes = ruta.parts
        if "node_modules" in partes or "static_root" in partes:
            continue
        relativa = ruta.relative_to(RAIZ).as_posix()
        if relativa in EXCLUIDOS:
            continue
        contenido = ruta.read_text(encoding="utf-8", errors="ignore")
        if EXTIENDE_MAIN in contenido:
            yield relativa, contenido


# Se miran <a> y <button>: los "Volver" que quedaban usaban `vat-back`,
# `sisoc-back-link` y `sisoc-wizard-back`, ninguna con la clase `btn`.
TAG_RE = re.compile(r"<(a|button)\b[^>]*>(.*?)</\1>", re.I | re.S)

# Allowlist explicita: pantallas donde el "Volver" se conserva a proposito.
#
# Son los que funcionan como *cancelar* de un formulario (conviven con un
# submit dentro del mismo <form>): no son navegacion sino descartar la edicion,
# y sacarlos dejaria el formulario sin salida al lado de "Guardar". Si UX
# prefiere, se renombran a "Cancelar" y esta lista se vacia.
#
# Antes esto era una heuristica por distancia (cualquier type="submit" a menos
# de 400 caracteres eximia al boton), y dejaba pasar los de navegacion pura.
CANCELAR_DE_FORMULARIO = {
    "admisiones/templates/admisiones/informe_tecnico_complementario_detalle.html",
    "admisiones/templates/admisiones/informe_tecnico_form.html",
    "centrodeinfancia/templates/centrodeinfancia/intervencion_form.html",
    "centrodeinfancia/templates/centrodeinfancia/nomina_form.html",
    "kernel/ciudadanos/templates/ciudadanos/ciudadano_form.html",
    "kernel/ciudadanos/templates/ciudadanos/grupofamiliar_form.html",
    "comedores/templates/comedor/actividad_espacio_pwa_form.html",
    "comedores/templates/comedor/actividades_pnud_form.html",
    "comedores/templates/comedor/cursos_app_mobile_form.html",
    "comunicados/templates/comunicados/mailing_form.html",
    "dispositivos/templates/dispositivos_form.html",
    "ocr/templates/ocr/ocr_upload.html",
    "pas/templates/pas/informe_form.html",
    "pas/templates/pas/persona_form.html",
    "templates/core/trash_restore_confirm.html",
    "usuarios/templates/user/bulk_credentials_form.html",
    "usuarios/templates/user/user_import_form.html",
    "ver_para_ser_libre/templates/ver_para_ser_libre/checklist_form.html",
    "ver_para_ser_libre/templates/ver_para_ser_libre/registro_form.html",
    "ver_para_ser_libre/templates/ver_para_ser_libre/sede_form.html",
    "ver_para_ser_libre/templates/ver_para_ser_libre/simple_form.html",
    # Paso atras de un wizard dentro de un modal (btnVolverResyncConvenio), no
    # navegacion entre pantallas.
    "admisiones/templates/admisiones/admisiones_tecnicos_form.html",
}


def _es_boton_volver(html_interno):
    """El texto visible arranca con "Volver" y no depende del contexto."""

    texto = " ".join(re.sub(r"<[^>]+>", " ", html_interno).split())
    if "{%" in texto or "{{" in texto:
        return False
    return bool(re.match(r"^Volver\b", texto, re.I))


def test_ninguna_pantalla_declara_su_propio_boton_volver_de_navegacion():
    """El "Volver" lo pone includes/main.html: nadie lo vuelve a declarar.

    La unica excepcion es la allowlist de arriba, que son "cancelar" de un
    formulario. Cualquier otro anchor o button que empiece con "Volver" es un
    boton duplicado, sin importar que clase use.
    """

    sobrantes = []
    for relativa, contenido in _templates_de_pantalla():
        if relativa in CANCELAR_DE_FORMULARIO:
            continue
        for match in TAG_RE.finditer(contenido):
            if not _es_boton_volver(match.group(2)):
                continue
            linea = contenido[: match.start()].count("\n") + 1
            sobrantes.append(f"{relativa}:{linea}")

    assert not sobrantes, (
        "Estas pantallas declaran su propio boton 'Volver'; el unificado ya lo "
        "renderiza includes/main.html. Si alguno es el 'cancelar' de un "
        "formulario, sumalo a CANCELAR_DE_FORMULARIO:\n  " + "\n  ".join(sobrantes)
    )


def test_la_allowlist_no_acumula_entradas_muertas():
    """Una entrada que ya no tiene su "Volver" tiene que salir de la lista."""

    vivas = {
        relativa
        for relativa, contenido in _templates_de_pantalla()
        if any(_es_boton_volver(m.group(2)) for m in TAG_RE.finditer(contenido))
    }
    muertas = sorted(CANCELAR_DE_FORMULARIO - vivas)

    assert not muertas, (
        "Estas entradas de CANCELAR_DE_FORMULARIO ya no tienen un 'Volver' "
        "propio; sacalas de la lista:\n  " + "\n  ".join(muertas)
    )


def test_el_componente_no_vive_mas_en_el_search_bar():
    search_bar = (RAIZ / "templates/components/search_bar.html").read_text(
        encoding="utf-8"
    )

    assert "poncho-volver" not in search_bar
    assert "back_url" not in search_bar


@pytest.mark.django_db
def test_una_pantalla_cualquiera_renderiza_el_boton(client):
    admin = User.objects.create_superuser("admin_volver", "volver@test.com", "test")
    client.force_login(admin)

    contenido = client.get(reverse("comedores")).content.decode()

    assert "data-sisoc-volver" in contenido
    assert "sisoc-volver-barra" in contenido
    assert "btn btn-secondary btn-sm sisoc-volver" in contenido


@pytest.mark.django_db
def test_la_pantalla_de_inicio_lo_oculta(client):
    admin = User.objects.create_superuser("admin_inicio", "inicio@test.com", "test")
    client.force_login(admin)

    response = client.get(reverse("inicio"))

    assert response.status_code == 200
    assert response.context["ocultar_volver"] is True
    assert "data-sisoc-volver" not in response.content.decode()


@pytest.mark.django_db
def test_la_vista_puede_fijar_un_destino_por_defecto(client):
    from django.template.loader import render_to_string

    html = render_to_string(
        "components/back_button.html", {"volver_url": "/comedores/"}
    )

    assert 'href="/comedores/"' in html
    assert 'data-volver-fallback="/comedores/"' in html


def test_el_context_processor_define_los_defaults():
    from core.context_processors import boton_volver

    defaults = boton_volver(None)

    assert defaults == {
        "ocultar_volver": False,
        "volver_url": "",
        "volver_texto": "Volver",
        "volver_transitoria": False,
    }


def test_las_pantallas_de_formulario_se_marcan_como_transitorias():
    """Altas, ediciones y borrados no se apilan en el historial del boton.

    Si se apilaran, despues de un POST-redirect-GET "Volver" llevaria al
    formulario vacio o al confirm_delete de un objeto ya borrado (404).
    """

    from types import SimpleNamespace

    from django.views.generic import CreateView, DeleteView, ListView, UpdateView

    from core.context_processors import _es_pantalla_transitoria

    def _request(vista):
        func = SimpleNamespace(view_class=vista) if vista else object()
        return SimpleNamespace(resolver_match=SimpleNamespace(func=func))

    assert _es_pantalla_transitoria(_request(CreateView)) is True
    assert _es_pantalla_transitoria(_request(UpdateView)) is True
    assert _es_pantalla_transitoria(_request(DeleteView)) is True
    assert _es_pantalla_transitoria(_request(ListView)) is False
    # Vista basada en funcion o doble de test: no se puede deducir, es destino.
    assert _es_pantalla_transitoria(_request(None)) is False
    assert _es_pantalla_transitoria(SimpleNamespace(resolver_match=None)) is False


@pytest.mark.django_db
def test_un_listado_no_se_marca_como_transitorio(client):
    admin = User.objects.create_superuser("admin_trans", "trans@test.com", "test")
    client.force_login(admin)

    contenido = client.get(reverse("comedores")).content.decode()

    assert 'data-volver-transitoria="0"' in contenido
