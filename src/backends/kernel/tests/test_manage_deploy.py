"""Administración del deploy: selección de imagen y prevención del grafo parcial."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "src/scripts/operacion/manage_deploy.py"
SHA = "a" * 40


def cargar_script():
    spec = importlib.util.spec_from_file_location("manage_deploy", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def preparar_docker(
    monkeypatch, module, *, image=None, available=True, exitcode=0, **changes
):
    calls = []
    files = [ROOT / "docker/compose/docker-compose.deploy.yml"]
    metadata = {
        "image": image or f"sisoc/core:{SHA}",
        "directory": str(ROOT),
        "files": ",".join(map(str, files)),
        "project": "sisoc",
    }
    metadata.update(changes)

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if command[1] == "inspect":
            return subprocess.CompletedProcess(command, 0, json.dumps(metadata), "")
        if command[1:3] == ["image", "inspect"]:
            return subprocess.CompletedProcess(command, 0 if available else 1, "", "")
        if command[-3:] == ["ps", "-q", "django"]:
            return subprocess.CompletedProcess(command, 0, "core-container\n", "")
        return subprocess.CompletedProcess(command, exitcode)

    monkeypatch.setattr(module.subprocess, "run", run)
    return calls


def test_comando_usa_migrador_inmutable_sin_arranque_y_conserva_argumentos(monkeypatch):
    module = cargar_script()
    calls = preparar_docker(monkeypatch, module, exitcode=7)
    arguments = ["makemigrations", "--check", "--dry-run", "--name", "con espacios"]
    assert module.main(arguments) == 7
    command, options = calls[-1]
    assert command[-len(arguments) :] == arguments
    assert command[command.index("migrator") + 1] == "manage.py"
    assert command[command.index("--entrypoint") + 1] == "python"
    assert command[command.index("--pull") + 1] == "never"
    assert "--no-deps" in command and "--rm" in command
    assert "DJANGO_SETTINGS_MODULE=config.settings_all" in command
    assert options["env"]["SISOC_RELEASE_SHA"] == SHA
    assert options["cwd"] == ROOT


@pytest.mark.parametrize("image,available", [("sisoc/core:local", True), (None, False)])
def test_rechaza_imagen_no_versionada_o_migrador_ausente(
    monkeypatch, capsys, image, available
):
    module = cargar_script()
    calls = preparar_docker(monkeypatch, module, image=image, available=available)
    assert module.main(["migrate", "--plan"]) == 2
    assert not any("run" in command for command, _ in calls)
    assert capsys.readouterr().err


def test_ayuda_no_toca_docker(monkeypatch, capsys):
    module = cargar_script()
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: pytest.fail("Docker"))
    assert module.main(["--help"]) == 0
    assert "makemigrations --check --dry-run" in capsys.readouterr().out


@pytest.mark.parametrize("changes", [{"directory": "/otro-checkout"}, {"files": ""}])
def test_rechaza_otro_checkout_o_configuracion_ausente(monkeypatch, changes):
    module = cargar_script()
    calls = preparar_docker(monkeypatch, module, **changes)
    assert module.main(["migrate", "--plan"]) == 2
    assert not any("run" in command for command, _ in calls)


@pytest.mark.parametrize("command", ["makemigrations", "createsuperuser"])
def test_grafo_parcial_rechaza_antes_de_django_sin_traceback(command):
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings"}
    result = subprocess.run(
        [sys.executable, str(ROOT / "manage.py"), command, "--noinput"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "manage_deploy.py" in result.stderr
    assert "Traceback" not in result.stderr
    assert "NodeNotFoundError" not in result.stderr


def test_otros_comandos_y_ayuda_conservan_ejecucion(tmp_path):
    """Django simulado evita DB: verifica los argumentos en el límite público."""
    django = tmp_path / "django"
    (django / "core").mkdir(parents=True)
    (django / "__init__.py").write_text("", encoding="utf-8")
    (django / "core/__init__.py").write_text("", encoding="utf-8")
    (django / "conf.py").write_text(
        "class Settings: DEBUG = False\nsettings = Settings()\n", encoding="utf-8"
    )
    (django / "core/management.py").write_text(
        "import json\ndef execute_from_command_line(args): print(json.dumps(args[1:]))\n",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "PYTHONPATH": str(tmp_path),
        "DJANGO_SETTINGS_MODULE": "config.settings",
    }
    for arguments in (
        ["check", "--deploy"],
        ["makemigrations", "--help"],
        ["migrate", "--plan", "--settings=config.settings_all"],
    ):
        result = subprocess.run(
            [sys.executable, str(ROOT / "manage.py"), *arguments],
            env=env,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == arguments
