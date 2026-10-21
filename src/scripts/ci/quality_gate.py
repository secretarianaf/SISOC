#!/usr/bin/env python3
"""Control de calidad de PR: tests y cobertura de las líneas cambiadas.

Solo stdlib. Compara el commit de prueba (merge del PR) con su primer padre,
que es la rama base que se probó en CI.

- ``gate --coverage coverage.xml``: falla si el PR modifica Python de una app
  sin tocar ningún test, o si las líneas nuevas/modificadas medibles quedan por
  debajo de ``UMBRAL`` % de cobertura. El label ``excepcion-calidad`` lo
  destraba (lo pone el revisor; ver ``docs/ia/TESTING.md``).
- ``zonas``: imprime en JSON las rutas delicadas que toca el PR; no falla.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
UMBRAL = 80.0
EXCEPCION = "excepcion-calidad"
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
# Prefijos y nombres que requieren revisión técnica aunque el cambio sea chico.
PREFIJOS_SENSIBLES = (
    ".github/",
    "docker/",
    "requirements/",
    "src/backends/config/",
    "src/backends/kernel/",
    "src/scripts/operacion/",
)
NOMBRES_SENSIBLES = {
    "docker-compose.yml",
    "pyproject.toml",
    "pytest.ini",
    ".pylintrc",
    ".importlinter",
    "package.json",
    "package-lock.json",
    "permissions.py",
    "api_permissions.py",
}


def es_test(ruta):
    """Archivo de test Python o JS, según las convenciones del repo."""
    path = PurePosixPath(ruta)
    return (
        "tests" in path.parts
        or path.name == "tests.py"
        or path.name.startswith("test_")
        or path.name.endswith(("_tests.py", ".test.js", ".test.ts", ".test.tsx"))
    )


def es_codigo_de_app(ruta):
    """Python de un dueño en src/backends, sin tests ni migraciones."""
    path = PurePosixPath(ruta)
    return (
        ruta.startswith("src/backends/")
        and path.suffix == ".py"
        and "migrations" not in path.parts
        and path.name != "conftest.py"
        and not es_test(ruta)
    )


def es_sensible(ruta):
    """Ruta delicada para la armonía del sistema (ver AGENTS.md); no los tests."""
    path = PurePosixPath(ruta)
    return not es_test(ruta) and (
        ruta.startswith(PREFIJOS_SENSIBLES)
        or path.name in NOMBRES_SENSIBLES
        or "migrations" in path.parts
        or path.name.startswith("settings")
    )


def lineas_cambiadas(diff):
    """Mapea archivo -> líneas agregadas o modificadas, desde un diff -U0."""
    cambios = {}
    actual = None
    for linea in diff.splitlines():
        if linea.startswith("+++ "):
            destino = linea[4:]
            actual = destino[2:] if destino.startswith("b/") else None
            if actual is not None:
                cambios.setdefault(actual, set())
        elif actual is not None and (coincidencia := HUNK.match(linea)):
            inicio = int(coincidencia.group(1))
            cantidad = int(coincidencia.group(2) or 1)
            cambios[actual].update(range(inicio, inicio + cantidad))
    return cambios


def cobertura(xml_path):
    """Mapea archivo -> {línea: hits} desde un coverage.xml (Cobertura)."""
    lineas = {}
    for clase in ET.parse(xml_path).getroot().iter("class"):
        archivo = lineas.setdefault(clase.get("filename"), {})
        for linea in clase.iter("line"):
            archivo[int(linea.get("number"))] = int(linea.get("hits"))
    return lineas


def evaluar(cambios, medidas):
    """Devuelve (cubiertas, medibles, faltantes por archivo) del código de app.

    Una línea es medible si coverage la reporta como ejecutable. Un archivo sin
    datos de cobertura cuenta todas sus líneas cambiadas como no cubiertas.
    """
    cubiertas = medibles = 0
    faltantes = {}
    for archivo, numeros in sorted(cambios.items()):
        if not es_codigo_de_app(archivo) or not numeros:
            continue
        medida = medidas.get(archivo)
        candidatas = sorted(numeros if medida is None else numeros & medida.keys())
        sin_cubrir = [n for n in candidatas if not medida or medida.get(n, 0) == 0]
        medibles += len(candidatas)
        cubiertas += len(candidatas) - len(sin_cubrir)
        if sin_cubrir:
            faltantes[archivo] = sin_cubrir
    return cubiertas, medibles, faltantes


def git(*args):
    """Salida de git en la raíz del repo."""
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def archivos_cambiados():
    """Archivos agregados/modificados/renombrados del PR."""
    salida = git("diff", "--name-only", "--diff-filter=ACMR", "HEAD^1", "HEAD")
    return [linea for linea in salida.splitlines() if linea]


def labels_del_pr():
    """Labels actuales del PR (por API, para que un re-run vea los nuevos)."""
    evento_path = os.environ.get("GITHUB_EVENT_PATH")
    if not evento_path:
        return set()
    evento = json.loads(Path(evento_path).read_text(encoding="utf-8"))
    numero = (evento.get("pull_request") or {}).get("number")
    if not numero:
        return set()
    url = (
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}"
        f"/issues/{numero}/labels?per_page=100"
    )
    headers = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return {label["name"] for label in json.load(response)}


def revisar(archivos, cambios, medidas, umbral=UMBRAL):
    """Devuelve la lista de problemas que bloquean el PR."""
    problemas = []
    codigo = [ruta for ruta in archivos if es_codigo_de_app(ruta)]
    if codigo and not any(es_test(ruta) for ruta in archivos):
        problemas.append(
            "Se modifica código de una app sin tocar ningún test: " + ", ".join(codigo)
        )
    cubiertas, medibles, faltantes = evaluar(cambios, medidas)
    if medibles and 100 * cubiertas / medibles < umbral:
        detalle = "; ".join(
            f"{archivo}: {', '.join(map(str, lineas))}"
            for archivo, lineas in faltantes.items()
        )
        problemas.append(
            f"Cobertura de líneas cambiadas {100 * cubiertas / medibles:.1f}% "
            f"({cubiertas}/{medibles}), mínimo {umbral:.0f}%. Sin cubrir: {detalle}"
        )
    return problemas


def resumen(texto):
    """Escribe en la consola y en el Summary del job, si existe."""
    print(texto)
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if destino:
        with open(destino, "a", encoding="utf-8") as archivo:
            archivo.write(texto + "\n")


def gate(coverage_xml):
    """Aplica el control y devuelve el código de salida."""
    diff = git("diff", "--unified=0", "--no-color", "HEAD^1", "HEAD", "--", "*.py")
    problemas = revisar(
        archivos_cambiados(), lineas_cambiadas(diff), cobertura(coverage_xml)
    )
    if not problemas:
        resumen("quality_gate: OK (tests y cobertura de líneas cambiadas).")
        return 0
    for problema in problemas:
        resumen(f"- {problema}")
    if EXCEPCION in labels_del_pr():
        resumen(f"quality_gate: excepción aprobada con el label `{EXCEPCION}`.")
        return 0
    resumen(
        "quality_gate: falla. Agregar tests que ejerciten las líneas cambiadas, o "
        f"pedir al revisor el label `{EXCEPCION}` y volver a correr este job."
    )
    return 1


def main(argv=None):
    """Punto de entrada CLI."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    gate_parser = sub.add_parser("gate")
    gate_parser.add_argument("--coverage", required=True, type=Path)
    sub.add_parser("zonas")
    args = parser.parse_args(argv)
    if args.comando == "gate":
        return gate(args.coverage)
    print(json.dumps([ruta for ruta in archivos_cambiados() if es_sensible(ruta)]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
