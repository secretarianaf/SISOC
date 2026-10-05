#!/usr/bin/env python3
"""Detecta referencias literales a raíces movidas en documentación vigente.

Solo stdlib, sin Django ni DB. No interpreta imports Python, URLs públicas ni
árboles de directorios. Revisa código inline y destinos de enlaces Markdown.
Los registros, planes, análisis y snapshots de infraestructura son históricos;
no se reescriben. Una ruta relativa a una app debe aclararse con el comentario
``<!-- docs-paths: relativo a la app -->`` en esa misma línea.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HISTORICOS = {"registro", "plans", "analisis", "infra", "memoria"}
LITERALES = re.compile(r"`([^`\n]+)`|\]\(([^)\n]+)\)")
RELATIVO = "<!-- docs-paths: relativo a la app -->"


def raices_movidas(root):
    """Resuelve apps por dueño actual, sin mantener otro inventario de apps."""
    destinos = {
        "config": "src/backends/config",
        "kernel": "src/backends/kernel",
        "backends": "src/backends",
        "frontends": "src/frontends",
        "scripts": "src/scripts",
        "templates": "src/backends/kernel/templates",
        "static": "src/backends/kernel/static",
        "tests": "src/backends/<dueño>/tests",
    }
    for apps_dir in (root / "src/backends").iterdir():
        if not apps_dir.is_dir() or apps_dir.name == "config":
            continue
        for app in apps_dir.iterdir():
            if app.is_dir() and (
                (app / "apps.py").is_file() or (app / "__init__.py").is_file()
            ):
                destinos[app.name] = app.relative_to(root).as_posix()
    return destinos


def documentos(root):
    """Guías vigentes; las exclusiones se documentan también en la guía."""
    yield root / "AGENTS.md"
    yield root / "CLAUDE.md"
    yield root / "README.md"
    for path in sorted((root / "docs").rglob("*.md")):
        if (
            not HISTORICOS.intersection(path.relative_to(root / "docs").parts)
            and not path.read_text(encoding="utf-8").startswith(
                "<!-- docs-paths: documento histórico -->"
            )
        ):
            yield path


def detectar(texto, destinos):
    """Devuelve línea, ruta anterior y raíz actual para literales inequívocos."""
    for numero, linea in enumerate(texto.splitlines(), 1):
        if RELATIVO in linea or "<!-- docs-paths: referencia histórica -->" in linea:
            continue
        for literal in LITERALES.finditer(linea):
            valor = (literal.group(1) or literal.group(2)).strip()
            # Una ruta de repo empieza con su raíz, no con / (URL/host),
            # ni con el prefijo de un import Python. Admite ./ en enlaces.
            ruta = valor.removeprefix("./")
            cabeza, separador, resto = ruta.partition("/")
            if cabeza in {"tests", "templates", "static"} and not resto:
                continue  # Nombres de carpetas genéricos dentro de una app.
            if separador and cabeza in destinos and " " not in ruta:
                yield numero, valor, destinos[cabeza]
            elif ruta == "requirements.txt":
                yield numero, valor, "requirements/all.txt"
            elif ruta.startswith("docker-compose.") and ruta.endswith(".yml"):
                if ruta != "docker-compose.yml":
                    yield numero, valor, "docker/compose/" + ruta


def main():
    """Informa hallazgos y termina con 1 cuando hay referencias obsoletas."""
    destinos = raices_movidas(ROOT)
    hallazgos = 0
    cantidad = 0
    for path in documentos(ROOT):
        cantidad += 1
        for linea, ruta, destino in detectar(path.read_text(encoding="utf-8"), destinos):
            print(f"{path.relative_to(ROOT).as_posix()}:{linea}: {ruta} -> {destino}")
            hallazgos += 1
    print(f"{cantidad} documentos vigentes; {hallazgos} referencias obsoletas.")
    return int(bool(hallazgos))


if __name__ == "__main__":
    sys.exit(main())
