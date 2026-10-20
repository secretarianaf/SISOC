"""Verificación de rutas documentadas (src/scripts/ci/check_docs_paths.py)."""

import subprocess

from scripts.ci import check_docs_paths


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


def test_ignora_rutas_ignoradas_por_git(tmp_path):
    root = _repo(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / ".gitignore").write_text("src/cache/\n", encoding="utf-8")

    assert _faltantes(root, "Salida local: `src/cache/memoria/`.") == []


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
