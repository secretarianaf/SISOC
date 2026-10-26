#!/usr/bin/env python3
"""Detecta referencias literales a raíces movidas en documentación vigente.

Solo stdlib, sin Django ni DB. No interpreta imports Python, URLs públicas ni
árboles de directorios. Revisa código inline y destinos de enlaces Markdown.
Los registros, planes, análisis y snapshots de infraestructura son históricos;
no se reescriben. Una ruta relativa a una app debe aclararse con el comentario
``<!-- docs-paths: relativo a la app -->`` en esa misma línea.

Con ``--existencia DOC...`` también falla si esos documentos vigentes citan una
ruta que no existe: literales que empiezan con una entrada de la raíz del repo
(``src/``, ``docs/``...) y enlaces Markdown relativos al documento. Omite
comodines, placeholders (``<app>``) y rutas ignoradas por Git (salidas locales).
CI lo aplica solo a los Markdown modificados por el PR.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HISTORICOS = {"registro", "plans", "analisis", "infra", "memoria"}
LITERALES = re.compile(r"`([^`\n]+)`|\]\(([^)\n]+)\)")
RELATIVO = "<!-- docs-paths: relativo a la app -->"
HISTORICA = "<!-- docs-paths: referencia histórica -->"
NO_RUTA = re.compile(r"[*?<>{}\[\]$|…]|\.\.\.|://|^mailto:|AAAA|YYYY")


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
        if not HISTORICOS.intersection(
            path.relative_to(root / "docs").parts
        ) and not path.read_text(encoding="utf-8").startswith(
            "<!-- docs-paths: documento histórico -->"
        ):
            yield path


def detectar(texto, destinos):
    """Devuelve línea, ruta anterior y raíz actual para literales inequívocos."""
    for numero, linea in enumerate(texto.splitlines(), 1):
        if RELATIVO in linea or HISTORICA in linea:
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


def candidatas(texto, doc, root):
    """Devuelve línea, literal y ruta absoluta de cada referencia verificable."""
    raices = {p.name for p in root.iterdir() if p.name != ".git"}
    for numero, linea in enumerate(texto.splitlines(), 1):
        if RELATIVO in linea or HISTORICA in linea:
            continue
        for literal in LITERALES.finditer(linea):
            valor = (literal.group(1) or literal.group(2)).strip()
            # Sin ancla ni sufijo de línea/símbolo (`archivo.py:12`, `.py::Clase`).
            ruta = valor.split("#", 1)[0].split(":", 1)[0]
            if not ruta or " " in valor or NO_RUTA.search(valor):
                continue
            if literal.group(2) is not None and not ruta.startswith("/"):
                yield numero, valor, (doc.parent / ruta).resolve()
            elif "/" in ruta and ruta.removeprefix("./").split("/", 1)[0] in raices:
                yield numero, valor, root / ruta.removeprefix("./")


def ignorados(root, rutas):
    """Subconjunto de rutas ignoradas por Git; vacío si Git no está disponible."""
    relativas = [
        r.relative_to(root).as_posix() for r in rutas if r.is_relative_to(root)
    ]
    if not relativas:
        return set()
    # Con "/" final también aplican los patrones de directorio que aún no existe.
    relativas += [ruta + "/" for ruta in relativas]
    try:
        salida = subprocess.run(
            ["git", "check-ignore", "--stdin"],
            cwd=root,
            input="\n".join(relativas),
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    except OSError:
        return set()
    return {root / linea.rstrip("/") for linea in salida.splitlines() if linea}


def faltantes(doc, root):
    """Devuelve línea y literal de las rutas citadas en doc que no existen."""
    referencias = [
        ref
        for ref in candidatas(doc.read_text(encoding="utf-8"), doc, root)
        if not ref[2].exists()
    ]
    excluidas = ignorados(root, [ref[2] for ref in referencias])
    return [
        (numero, valor) for numero, valor, ruta in referencias if ruta not in excluidas
    ]


def main(argv=None):
    """Informa hallazgos y termina con 1 cuando hay referencias obsoletas o rotas."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--existencia",
        nargs="*",
        default=[],
        metavar="DOC",
        help="Markdown en los que además se verifica que las rutas citadas existan.",
    )
    args = parser.parse_args(argv)
    destinos = raices_movidas(ROOT)
    a_verificar = {(ROOT / doc).resolve() for doc in args.existencia}
    hallazgos = 0
    cantidad = 0
    for path in documentos(ROOT):
        cantidad += 1
        relativo = path.relative_to(ROOT).as_posix()
        for linea, ruta, destino in detectar(
            path.read_text(encoding="utf-8"), destinos
        ):
            print(f"{relativo}:{linea}: {ruta} -> {destino}")
            hallazgos += 1
        if path.resolve() in a_verificar:
            for linea, ruta in faltantes(path, ROOT):
                print(f"{relativo}:{linea}: {ruta} no existe")
                hallazgos += 1
    print(f"{cantidad} documentos vigentes; {hallazgos} referencias obsoletas o rotas.")
    return int(bool(hallazgos))


if __name__ == "__main__":
    sys.exit(main())
