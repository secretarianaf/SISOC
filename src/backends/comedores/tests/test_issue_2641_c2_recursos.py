"""Recursos de Comedores resueltos por su app con raíz operativa ajena."""

from datetime import date
from pathlib import Path
from types import SimpleNamespace
from io import BytesIO

import pytest
from django.apps import apps
from pypdf import PdfReader

from comedores.services.certificacion_prestaciones_service import (
    generar_certificacion_prestaciones_pdf,
)
from admisiones.management.commands.corregir_expedientes_issue_2272 import Command
from relevamientos.pnud_formularios import definiciones


@pytest.mark.parametrize(
    "conforme,subusuario", [(True, False), (True, True), (False, False), (False, True)]
)
def test_certificaciones_renderizan_pdf_con_base_dir_ajeno(
    settings, tmp_path, conforme, subusuario
):
    settings.BASE_DIR = tmp_path / "portal_sin_apps"
    comedor = SimpleNamespace(
        nombre="Espacio C2",
        calle="Calle de prueba",
        numero=123,
        localidad=None,
        provincia=None,
        programa=SimpleNamespace(nombre="Alimentar Comunidad"),
    )
    usuario = SimpleNamespace(
        username="actor",
        get_full_name=lambda: "Actor C2",
        profile=SimpleNamespace(dni="30111222"),
    )
    pdf = generar_certificacion_prestaciones_pdf(
        comedor=comedor,
        periodo=date(2035, 1, 1),
        usuario=usuario,
        source=SimpleNamespace(),
        conforme=conforme,
        usuario_principal=usuario if subusuario else None,
    )
    assert pdf.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(pdf))
    assert len(reader.pages) > 0
    assert "Espacio C2" in "\n".join(page.extract_text() for page in reader.pages)


def test_manifiesto_y_archivos_son_del_dueno(settings, tmp_path):
    settings.BASE_DIR = tmp_path
    command = Command()
    assert command.get_manifest_path().is_relative_to(
        Path(apps.get_app_config("admisiones").path)
    )
    resultado = command._cargar_y_validar_manifiesto()
    assert len(resultado.correcciones) == 470
    assert not resultado.errores
    pwa = Path(apps.get_app_config("pwa").path)
    assert (pwa / "files/varios/NOMINA.DE.DESTINATARIOS.docx").is_file()
    assert (
        pwa
        / "files/rendicion_de_cuentas/FORM.I.-Certificacion.de.CUENTA.BANCARIA.1.xlsx"
    ).is_file()

    assert definiciones()
