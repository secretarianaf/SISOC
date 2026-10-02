"""Regresiones de templates de ciudadanos."""

from pathlib import Path


def test_ciudadano_detail_template_incluye_accion_eliminar():
    repo_root = Path(__file__).resolve().parents[4]
    template_path = (
        repo_root
        / "src"
        / "backends"
        / "kernel"
        / "ciudadanos"
        / "templates"
        / "ciudadanos"
        / "ciudadano_detail.html"
    )

    content = template_path.read_text(encoding="utf-8")

    assert "ciudadanos_eliminar" in content


def test_ciudadano_detail_template_usa_admision_comedor_con_guardas():
    repo_root = Path(__file__).resolve().parents[4]
    template_path = (
        repo_root
        / "src"
        / "backends"
        / "kernel"
        / "ciudadanos"
        / "templates"
        / "ciudadanos"
        / "ciudadano_detail.html"
    )

    content = template_path.read_text(encoding="utf-8")

    assert "nomina_actual.admision.comedor" in content
    assert "nomina.admision.comedor" in content
    assert "nomina_actual.comedor.id" not in content
    assert "nomina.comedor.id" not in content


def test_ciudadano_detail_template_incluye_pestana_vat():
    repo_root = Path(__file__).resolve().parents[4]
    template_path = (
        repo_root
        / "src"
        / "backends"
        / "kernel"
        / "ciudadanos"
        / "templates"
        / "ciudadanos"
        / "ciudadano_detail.html"
    )

    content = template_path.read_text(encoding="utf-8")
    seccion = (
        repo_root
        / "src"
        / "backends"
        / "vat"
        / "VAT"
        / "templates"
        / "vat"
        / "ciudadano_detalle_seccion.html"
    ).read_text(encoding="utf-8")

    assert 'href="#vat"' in content
    assert 'id="vat"' in content
    assert "contribuciones_html.vat" in content
    assert "Cursos asignados" in seccion
    assert "Créditos actuales" in seccion


def test_ciudadano_detail_template_usa_el_resumen_publico_de_celiaquia():
    repo_root = Path(__file__).resolve().parents[4]
    template_path = (
        repo_root
        / "src"
        / "backends"
        / "kernel"
        / "ciudadanos"
        / "templates"
        / "ciudadanos"
        / "ciudadano_detail.html"
    )

    content = template_path.read_text(encoding="utf-8")
    seccion = (
        repo_root
        / "src"
        / "backends"
        / "celiaquia"
        / "celiaquia"
        / "templates"
        / "celiaquia"
        / "ciudadano_detalle_seccion.html"
    ).read_text(encoding="utf-8")

    assert "contribuciones_html.celiaquia" in content
    assert "celiaquia_resumen.legajo_actual" in seccion
    assert "celiaquia_resumen.historial" in seccion
    assert "expediente_actual" not in content
    assert "expedientes_celiaquia" not in content


def test_ciudadano_list_template_incluye_filtro_estado_revision_dinamico():
    repo_root = Path(__file__).resolve().parents[4]
    template_path = (
        repo_root
        / "src"
        / "backends"
        / "kernel"
        / "ciudadanos"
        / "templates"
        / "ciudadanos"
        / "ciudadano_list.html"
    )

    content = template_path.read_text(encoding="utf-8")

    assert "estado-revision-group" in content
    assert "id_estado_revision" in content
    assert '["", "SIN_DNI", "DNI_NO_VALIDADO_RENAPER"]' in content
