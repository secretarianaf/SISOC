#!/usr/bin/env python3
"""Ejecuta administración Django en el migrador de la versión que sirve tráfico."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
USAGE = """Uso: python3 src/scripts/operacion/manage_deploy.py <comando Django> [argumentos]
Ejemplo de lectura: makemigrations --check --dry-run
Ejemplo de lectura: migrate --plan
Selecciona el migrador del core activo; no construye imágenes ni prepara la DB.
Los argumentos se pasan a Django: migrate sin --plan y createsuperuser escriben
datos y requieren autorización. Para ayuda Django: <comando> --help.
"""


def consultar(command):
    """Las consultas de Docker nunca consumen el stdin del comando del usuario."""
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode:
        raise ValueError(
            "Falló la consulta de Docker; no se ejecutó el comando Django."
        )
    return result.stdout.strip()


def main(arguments=None):
    """Conserva argumentos, stdin interactivo y código de salida de Django."""
    arguments = sys.argv[1:] if arguments is None else arguments
    if not arguments or arguments[0] in {"-h", "--help"}:
        print(USAGE)
        return 0 if arguments else 2
    compose = ["docker", "compose", "--project-directory", str(ROOT)]
    try:
        container = consultar(
            compose
            + [
                "-f",
                str(ROOT / "docker/compose/docker-compose.deploy.yml"),
                "ps",
                "-q",
                "django",
            ]
        )
        if not container or len(container.splitlines()) != 1:
            raise ValueError("Se requiere exactamente un contenedor django activo.")
        template = (
            '{"image":{{json .Config.Image}},'
            '"directory":{{json (index .Config.Labels "com.docker.compose.project.working_dir")}},'
            '"files":{{json (index .Config.Labels "com.docker.compose.project.config_files")}},'
            '"project":{{json (index .Config.Labels "com.docker.compose.project")}}}'
        )
        metadata = json.loads(
            consultar(["docker", "inspect", "--format", template, container])
        )
        match = re.fullmatch(r"sisoc/core:([0-9a-f]{40})", metadata["image"])
        if not match or Path(metadata["directory"]).resolve() != ROOT:
            raise ValueError(
                "El core debe pertenecer a este checkout y usar un SHA inmutable."
            )
        files = [Path(path).resolve() for path in metadata["files"].split(",")]
        if not files or any(
            not path.is_relative_to(ROOT) or not path.is_file() for path in files
        ):
            raise ValueError(
                "Los archivos Compose del core no pertenecen a este checkout."
            )
        release = match.group(1)
        consultar(
            [
                "docker",
                "image",
                "inspect",
                "--format",
                "{{.Id}}",
                f"sisoc/migrator:{release}",
            ]
        )
        compose += ["--project-name", metadata["project"]]
        for path in files:
            compose += ["-f", str(path)]
        command = compose + [
            "--profile",
            "migrate",
            "run",
            "--rm",
            "--no-deps",
            "--pull",
            "never",
        ]
        if not sys.stdin.isatty():
            command.append("-T")
        command += [
            "--entrypoint",
            "python",
            "-e",
            "DJANGO_SETTINGS_MODULE=config.settings_all",
            "migrator",
            "manage.py",
            *arguments,
        ]
        return subprocess.run(
            command,
            cwd=ROOT,
            env={**os.environ, "SISOC_RELEASE_SHA": release},
            check=False,
        ).returncode
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"[manage-deploy] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
