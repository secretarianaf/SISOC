"""Plan de deploy por archivos cambiados (scripts/operacion/deploy_targets.py)."""

import importlib.util
from pathlib import Path

import pytest

_RUTA = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "operacion"
    / "deploy_targets.py"
)
_spec = importlib.util.spec_from_file_location("deploy_targets", _RUTA)
deploy_targets = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(deploy_targets)


@pytest.mark.parametrize(
    ("archivos", "esperado"),
    [
        # Un cambio solo en un vertical despliega solo ese vertical.
        (
            ["backends/dispositivos/dispositivos/views.py"],
            ("selectivo", ["backend_dispositivos"], True),
        ),
        (["frontends/apps/vpsl/src/App.tsx"], ("selectivo", ["front_vpsl"], False)),
        (
            ["backends/pas/pas/tasks.py"],
            ("selectivo", ["backend_pas", "celery_beat", "celery_pas_worker"], True),
        ),
        (
            ["backends/dispositivos/datacalle/models.py", "frontends/apps/vpsl/a.ts"],
            ("selectivo", ["backend_dispositivos", "front_vpsl"], True),
        ),
        # Lo compartido despliega todo.
        (["kernel/core/views.py"], ("completo", [], True)),
        (["config/settings.py"], ("completo", [], True)),
        (["templates/includes/main.html"], ("completo", [], True)),
        (["requirements/base.txt"], ("completo", [], True)),
        (["docker-compose.deploy.yml"], ("completo", [], True)),
        (["CHANGELOG.md"], ("completo", [], True)),
        (["comedores/views.py"], ("completo", [], True)),
        # Documentación, tests y CI no reinician nada.
        (["docs/registro/prs/PR-1.md", "README.md"], ("ninguno", [], False)),
        (
            ["tests/test_x.py", "backends/dispositivos/tests/test_y.py"],
            ("ninguno", [], False),
        ),
        ([".github/workflows/tests.yml"], ("ninguno", [], False)),
    ],
)
def test_planificar(archivos, esperado):
    assert deploy_targets.planificar(archivos) == esperado


def test_sha_desconocido_es_despliegue_completo(capsys):
    deploy_targets.main(["0" * 40, "f" * 40])

    assert capsys.readouterr().out.startswith("MODO=completo")
