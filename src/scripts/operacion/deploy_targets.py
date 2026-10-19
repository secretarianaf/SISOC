#!/usr/bin/env python3
"""Decide qué servicios desplegar según los archivos cambiados entre dos SHAs.

Solo stdlib: corre en el host del runner, antes de construir imágenes.

Uso:
    deploy_targets.py <sha_desplegado> <sha_nuevo>
    deploy_targets.py --files <archivo>...   (para pruebas)
    deploy_targets.py --servicios-core < <docker compose config --format json>
    deploy_targets.py --servicios-presentes <servicio>... < compose.json

Salida (una línea, para ``eval`` en bash):
    MODO=<completo|selectivo|ninguno> SERVICIOS="<svc> <svc>" MIGRAR=<0|1>

Reglas (ver docs/registro/decisiones/2026-09-30-monorepo-kernel-backends.md y
2026-10-02-estructura-src-backends.md):
- ``src/backends/<x>/**`` despliega solo el backend ``x``
  (src/backends/config/backends.json) y corre el migrador.
- ``src/backends/sisoc_core/**`` despliega solo los servicios del core: el marcador
  ``@core``, que ``deploy_refresh.sh`` traduce a los servicios con imagen
  ``sisoc/core`` y al worker compuesto de importación (``--servicios-core``).
  Ninguna imagen web de vertical incluye ``sisoc_core``.
- ``src/backends/<x>/tests/**`` (kernel incluido) no despliega nada.
- ``src/backends/kernel/**`` y ``src/backends/config/**`` no son verticales:
  los usan todas las imágenes, así que son despliegue completo.
- ``src/frontends/apps/<x>/**`` despliega solo ``front_<x>``. ``src/frontends/``
  fuera de ``apps/`` (paquetes compartidos, configuración, lockfile),
  ``docker/frontends/`` y ``src/scripts/frontends/`` despliegan todos los fronts.
- Documentación y CI no despliegan nada.
- Cualquier otra cosa (kernel, config, requirements, docker, compose,
  CHANGELOG.md que muestra el footer) es despliegue completo.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

SIN_DEPLOY_PREFIJOS = (
    "docs/",
    ".github/",
    "src/scripts/github/",
    # Baseline versionado de benchmarks: no corre en runtime.
    "src/backends/kernel/core/benchmarks/baselines/",
)

# Carpetas de src/backends/ que no son verticales: un cambio ahí es completo.
NO_VERTICALES = ("config", "kernel")

# Carpeta del código propio del core y marcador de sus servicios en SERVICIOS.
CORE_DIR = "sisoc_core"
CORE_MARCADOR = "@core"
CORE_IMAGEN = "sisoc/core:"
# Declarados sólo en docker-compose.produccion.yml; pueden faltar en QA.
WORKERS_OPCIONALES = {"mailing_worker", "user_import_worker"}


def _sin_deploy(ruta: str) -> bool:
    if ruta.startswith(SIN_DEPLOY_PREFIJOS):
        return True
    return ruta.endswith(".md") and ruta != "CHANGELOG.md"


def _backends() -> dict:
    with open(
        ROOT / "src" / "backends" / "config" / "backends.json", encoding="utf-8"
    ) as registro:
        return json.load(registro)


def _fronts() -> list[str]:
    apps = ROOT / "src" / "frontends" / "apps"
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
        if partes[:2] == ["src", "backends"] and len(partes) > 3:
            carpeta = partes[2]
            if len(partes) > 4 and partes[3] == "tests":
                continue
            if carpeta in backends and carpeta not in NO_VERTICALES:
                servicios.add(backends[carpeta]["service"])
                # Procesos que corren el mismo código (p. ej. Celery de PAS).
                servicios.update(backends[carpeta].get("extra_services", []))
                migrar = True
                continue
            if carpeta == CORE_DIR:
                servicios.add(CORE_MARCADOR)
                migrar = True
                continue
        if ruta.startswith(("docker/frontends/", "src/scripts/frontends/")):
            servicios.update(_fronts())
            continue
        if partes[:2] == ["src", "frontends"]:
            if len(partes) > 4 and partes[2] == "apps":
                servicios.add(f"front_{partes[3]}")
            elif len(partes) > 2 and partes[2] in ("e2e",):
                continue
            else:
                servicios.update(_fronts())
            continue
        return "completo", [], True
    if not servicios:
        return "ninguno", [], False
    return "selectivo", sorted(servicios), migrar


def servicios_core(config: dict) -> list[str]:
    """Procesos con código del portal, incluido su importador compuesto.

    El rol existente identifica al importador aunque su imagen ya no sea la
    del web. Omitirlo dejaría Usuarios viejo después de un selectivo @core.
    """
    return sorted(
        nombre
        for nombre, servicio in (config.get("services") or {}).items()
        if str(servicio.get("image", "")).startswith(CORE_IMAGEN)
        or (servicio.get("environment") or {}).get("DJANGO_SERVICE_ROLE")
        == "user_import_worker"
    )


def servicios_presentes(config: dict, seleccionados: list[str]) -> list[str]:
    """Resuelve el plan en el entorno sin exigir sus workers opcionales.

    Mailing e importación viven en el override de producción (HML/PRD). Otros
    servicios ausentes, incluido Celery, obligan al fallback completo.
    """
    disponibles = config.get("services") or {}
    faltantes = set(seleccionados) - disponibles.keys() - WORKERS_OPCIONALES
    if faltantes:
        raise ValueError(
            "Servicios obligatorios ausentes: " + ", ".join(sorted(faltantes))
        )
    return sorted(set(seleccionados).intersection(disponibles))


def archivos_entre(base: str, destino: str) -> list[str]:
    salida = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only", f"{base}..{destino}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [linea for linea in salida.splitlines() if linea.strip()]


def main(argv: list[str]) -> int:
    if argv[:1] == ["--servicios-core"]:
        print(" ".join(servicios_core(json.load(sys.stdin))))
        return 0
    if argv[:1] == ["--servicios-presentes"]:
        try:
            print(" ".join(servicios_presentes(json.load(sys.stdin), argv[1:])))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0
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
