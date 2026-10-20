"""Verificación de rutas documentadas (src/scripts/ci/check_docs_paths.py)."""

import shutil
import subprocess

import pytest

from scripts.ci import check_docs_paths


def _git_disponible(cwd):
    """La imagen de tests no trae git; el job docs_paths cubre ese caso en CI."""
    if shutil.which("git") is None:
        return False
    resultado = subprocess.run(
        ["git", "rev-parse", "--git-dir"], cwd=cwd, capture_output=True, check=False
    )
    return resultado.returncode == 0


def _repo(tmp_path):
    (tmp_path / "src" / "app").mkdir(parents=True)
    (tmp_path / "src" / "app" / "views.py").write_text("", encoding="utf-8")
    (tmp_path / "docs" / "guias").mkdir(parents=True)
    (tmp_path / "docs" / "otra.md").write_text("", encoding="utf-8")
    return tmp_path


def _faltantes(root, texto):
    doc = root / "docs" / "guias" / "guia.md"
    doc.write_text(texto, encoding="utf-8")
    return check_docs_paths.faltantes(doc, root)


def test_informa_rutas_desde_la_raiz_y_enlaces_inexistentes(tmp_path):
    root = _repo(tmp_path)
    texto = "\n".join(
        [
            "Ver `src/app/views.py` y `src/app/borrado.py`.",
            "Enlaces: [ok](../otra.md) y [roto](../no-existe.md#seccion).",
        ]
    )

    assert _faltantes(root, texto) == [
        (1, "src/app/borrado.py"),
        (2, "../no-existe.md#seccion"),
    ]


def test_ignora_lo_que_no_es_una_ruta_verificable(tmp_path):
    root = _repo(tmp_path)
    texto = "\n".join(
        [
            "`src/app/views.py:12` y `src/app/views.py::Vista` existen.",
            "Placeholders: `src/<vertical>/tests/`, `src/app/*.py`, `docs/AAAA-TN/`.",
            "Relativas a una app o comandos: `services/x.py`, `python src/no.py`.",
            "URL: [sitio](http://localhost:8001) y `https://ejemplo.org/a/b`.",
            "`src/app/viejo.py` <!-- docs-paths: referencia histórica -->",
            "`src/app/otro.py` <!-- docs-paths: relativo a la app -->",
        ]
    )

    assert _faltantes(root, texto) == []


@pytest.mark.skipif(shutil.which("git") is None, reason="git no disponible")
def test_ignora_rutas_ignoradas_por_git(tmp_path):
    root = _repo(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / ".gitignore").write_text("src/cache/\n", encoding="utf-8")

    assert _faltantes(root, "Salida local: `src/cache/memoria/`.") == []


@pytest.mark.skipif(
    not _git_disponible(check_docs_paths.ROOT),
    reason="sin git no se distinguen las salidas locales ignoradas",
)
def test_los_docs_de_agentes_citan_rutas_existentes():
    """Si falla: corregir la ruta citada o marcarla como relativa a la app."""

    root = check_docs_paths.ROOT
    docs = [
        root / "AGENTS.md",
        root / "CLAUDE.md",
        *(root / "docs" / "ia").glob("*.md"),
    ]

    assert {doc.name: check_docs_paths.faltantes(doc, root) for doc in docs} == {
        doc.name: [] for doc in docs
    }
