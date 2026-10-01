#!/usr/bin/env python3
"""Decide qué servicios desplegar según los archivos cambiados entre dos SHAs.

Solo stdlib: corre en el host del runner, antes de construir imágenes.

Uso:
    deploy_targets.py <sha_desplegado> <sha_nuevo>
    deploy_targets.py --files <archivo>...   (para pruebas)

Salida (una línea, para ``eval`` en bash):
    MODO=<completo|selectivo|ninguno> SERVICIOS="<svc> <svc>" MIGRAR=<0|1>

Reglas (ver docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md):
- ``backends/<x>/**`` despliega solo el backend ``x`` (config/backends.json) y
  corre el migrador. Sus tests no despliegan nada.
- ``frontends/apps/<x>/**`` despliega solo ``front_<x>``. ``frontends/`` fuera
  de ``apps/`` (paquetes compartidos, Dockerfile, lockfile) despliega todos los
  fronts.
- Documentación, tests y CI no despliegan nada.
- Cualquier otra cosa (kernel, core, config, templates, static, requirements,
  docker, compose, CHANGELOG.md que muestra el footer) es despliegue completo.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SIN_DEPLOY_PREFIJOS = ("docs/", "tests/", ".github/", "postman/", "benchmarks/")


def _sin_deploy(ruta: str) -> bool:
    if ruta.startswith(SIN_DEPLOY_PREFIJOS):
        return True
    return ruta.endswith(".md") and ruta != "CHANGELOG.md"


def _backends() -> dict:
    with open(ROOT / "config" / "backends.json", encoding="utf-8") as registro:
        return json.load(registro)


def _fronts() -> list[str]:
    apps = ROOT / "frontends" / "apps"
    if not apps.is_dir():
        return []
    return sorted(f"front_{p.name}" for p in apps.iterdir() if p.is_dir())


def planificar(archivos: list[str]) -> tuple[str, list[str], bool]:
    backends = _backends()
    servicios: set[str] = set()
    migrar = False
    for ruta in archivos:
        ruta = ruta.replace("\\", "/")
        if _sin_deploy(ruta):
            continue
        partes = ruta.split("/")
        if partes[0] == "backends" and len(partes) > 2 and partes[1] in backends:
            if partes[2] == "tests":
                continue
            servicios.add(backends[partes[1]]["service"])
            migrar = True
            continue
        if partes[0] == "frontends":
            if len(partes) > 3 and partes[1] == "apps":
                servicios.add(f"front_{partes[2]}")
            elif len(partes) > 1 and partes[1] in ("e2e",):
                continue
            else:
                servicios.update(_fronts())
            continue
        return "completo", [], True
    if not servicios:
        return "ninguno", [], False
    return "selectivo", sorted(servicios), migrar


def archivos_entre(base: str, destino: str) -> list[str]:
    salida = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only", f"{base}..{destino}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [linea for linea in salida.splitlines() if linea.strip()]


def main(argv: list[str]) -> int:
    if argv[:1] == ["--files"]:
        archivos = argv[1:]
    elif len(argv) == 2:
        try:
            archivos = archivos_entre(argv[0], argv[1])
        except (OSError, subprocess.CalledProcessError):
            # Sin git, sin historia común o SHA desconocido: no se arriesga nada.
            archivos = ["<desconocido>"]
    else:
        print(__doc__, file=sys.stderr)
        return 2
    modo, servicios, migrar = planificar(archivos)
    print(f'MODO={modo} SERVICIOS="{" ".join(servicios)}" MIGRAR={int(migrar)}')
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
