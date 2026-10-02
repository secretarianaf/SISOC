"""Plan de deploy por archivos cambiados (scripts/operacion/deploy_targets.py)."""

import importlib.util
from pathlib import Path

import pytest

_RUTA = (
    Path(__file__).resolve().parents[4] / "scripts" / "operacion" / "deploy_targets.py"
)
_spec = importlib.util.spec_from_file_location("deploy_targets", _RUTA)
deploy_targets = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(deploy_targets)


@pytest.mark.parametrize(
    ("archivos", "esperado"),
    [
        # Un cambio solo en un vertical despliega solo ese vertical.
        (
            ["src/backends/dispositivos/dispositivos/views.py"],
            ("selectivo", ["backend_dispositivos"], True),
        ),
        (["src/frontends/apps/vpsl/src/App.tsx"], ("selectivo", ["front_vpsl"], False)),
        (
            ["src/backends/pas/pas/tasks.py"],
            ("selectivo", ["backend_pas", "celery_beat", "celery_pas_worker"], True),
        ),
        (
            [
                "src/backends/dispositivos/datacalle/models.py",
                "src/frontends/apps/vpsl/a.ts",
            ],
            ("selectivo", ["backend_dispositivos", "front_vpsl"], True),
        ),
        # Lo compartido despliega todo.
        (["src/backends/kernel/core/views.py"], ("completo", [], True)),
        (["src/backends/config/settings.py"], ("completo", [], True)),
        (["src/backends/kernel/templates/includes/main.html"], ("completo", [], True)),
        (["src/backends/kernel/static/custom/js/base.js"], ("completo", [], True)),
        (["requirements/base.txt"], ("completo", [], True)),
        (["docker/compose/docker-compose.deploy.yml"], ("completo", [], True)),
        (["CHANGELOG.md"], ("completo", [], True)),
        # El core se despliega solo: el marcador lo resuelve deploy_refresh.sh.
        (
            ["src/backends/sisoc_core/comedores/views.py"],
            ("selectivo", ["@core"], True),
        ),
        (
            [
                "src/backends/sisoc_core/comedores/views.py",
                "src/backends/pas/pas/views.py",
            ],
            (
                "selectivo",
                ["@core", "backend_pas", "celery_beat", "celery_pas_worker"],
                True,
            ),
        ),
        (
            [
                "src/backends/sisoc_core/comedores/views.py",
                "src/backends/kernel/core/views.py",
            ],
            ("completo", [], True),
        ),
        # Documentación, tests y CI no reinician nada.
        (["docs/registro/prs/PR-1.md", "README.md"], ("ninguno", [], False)),
        (
            [
                "src/backends/kernel/tests/test_x.py",
                "src/backends/dispositivos/tests/test_y.py",
                "src/backends/sisoc_core/tests/test_z.py",
            ],
            ("ninguno", [], False),
        ),
        # El estático de un vertical despliega ese vertical y corre el migrador,
        # que es quien hace collectstatic.
        (
            ["src/backends/vat/VAT/static/custom/js/vat.js"],
            ("selectivo", ["backend_vat"], True),
        ),
        ([".github/workflows/tests.yml"], ("ninguno", [], False)),
    ],
)
def test_planificar(archivos, esperado):
    assert deploy_targets.planificar(archivos) == esperado


def test_sha_desconocido_es_despliegue_completo(capsys):
    deploy_targets.main(["0" * 40, "f" * 40])

    assert capsys.readouterr().out.startswith("MODO=completo")


def test_servicios_core_son_los_que_corren_la_imagen_del_core():
    config = {
        "services": {
            "django": {"image": "sisoc/core:abc"},
            "mailing_worker": {"image": "sisoc/core:abc"},
            "backend_vat": {"image": "sisoc/backend-vat:abc"},
            "redis": {"image": "redis:7"},
            "sin_imagen": {},
        }
    }

    assert deploy_targets.servicios_core(config) == ["django", "mailing_worker"]
