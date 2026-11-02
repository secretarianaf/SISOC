"""Plan de deploy por archivos cambiados (src/scripts/operacion/deploy_targets.py)."""

import importlib.util
from pathlib import Path

import pytest

_RUTA = (
    Path(__file__).resolve().parents[4]
    / "src"
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
            ["src/backends/dispositivos/dispositivos/views.py"],
            ("selectivo", ["backend_dispositivos", "user_import_worker"], True),
        ),
        (["src/frontends/apps/vpsl/src/App.tsx"], ("selectivo", ["front_vpsl"], False)),
        (
            ["src/backends/pas/pas/tasks.py"],
            (
                "selectivo",
                [
                    "backend_pas",
                    "celery_beat",
                    "celery_pas_worker",
                    "user_import_worker",
                ],
                True,
            ),
        ),
        (
            ["src/backends/comedores/comedores/views/comedor.py"],
            (
                "selectivo",
                ["backend_comedores", "mailing_worker", "user_import_worker"],
                True,
            ),
        ),
        (
            ["src/backends/comedores/pwa/files/varios/PRESTACIONES.2.docx"],
            (
                "selectivo",
                ["backend_comedores", "mailing_worker", "user_import_worker"],
                True,
            ),
        ),
        (
            [
                "src/backends/dispositivos/datacalle/models.py",
                "src/frontends/apps/vpsl/a.ts",
            ],
            (
                "selectivo",
                ["backend_dispositivos", "front_vpsl", "user_import_worker"],
                True,
            ),
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
            ["src/backends/sisoc_core/usuarios/views.py"],
            ("selectivo", ["@core"], True),
        ),
        (
            [
                "src/backends/sisoc_core/usuarios/views.py",
                "src/backends/pas/pas/views.py",
            ],
            (
                "selectivo",
                [
                    "@core",
                    "backend_pas",
                    "celery_beat",
                    "celery_pas_worker",
                    "user_import_worker",
                ],
                True,
            ),
        ),
        (
            [
                "src/backends/sisoc_core/usuarios/views.py",
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
                "src/backends/comedores/tests/test_z.py",
                "src/backends/kernel/core/benchmarks/baselines/default.json",
                "docs/api/postman/SISOC APIs.postman_collection.json",
            ],
            ("ninguno", [], False),
        ),
        # El estático de un vertical despliega ese vertical y corre el migrador,
        # que es quien hace collectstatic.
        (
            ["src/backends/vat/VAT/static/custom/js/vat.js"],
            ("selectivo", ["backend_vat", "user_import_worker"], True),
        ),
        ([".github/workflows/tests.yml"], ("ninguno", [], False)),
        (["src/scripts/github/release_orchestrator.js"], ("ninguno", [], False)),
        (
            ["docker/frontends/Dockerfile", "docker/frontends/nginx.conf.template"],
            ("selectivo", ["front_celiaquia", "front_inet", "front_vpsl"], False),
        ),
        (
            ["src/scripts/frontends/verificar-contrato.mjs"],
            ("selectivo", ["front_celiaquia", "front_inet", "front_vpsl"], False),
        ),
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


def test_importador_compuesto_se_actualiza_tambien_por_cambios_de_usuarios():
    config = {
        "services": {
            "django": {"image": "sisoc/core:abc"},
            "importador": {
                "image": "sisoc/migrator:abc",
                "environment": {"DJANGO_SERVICE_ROLE": "user_import_worker"},
            },
            "mailing_worker": {"image": "sisoc/backend-comedores:abc"},
            "migrator": {"image": "sisoc/migrator:abc"},
        }
    }
    assert deploy_targets.servicios_core(config) == ["django", "importador"]


@pytest.mark.parametrize("backend", sorted(deploy_targets._backends()))
def test_cualquier_backend_actualiza_worker_con_imagen_completa(backend):
    modo, servicios, migrar = deploy_targets.planificar(
        [f"src/backends/{backend}/app/services.py"]
    )
    assert modo == "selectivo"
    assert migrar
    assert "user_import_worker" in servicios


def test_workers_opcionales_ausentes_en_qa_no_exigen_servicios_de_prd():
    config = {"services": {"backend_comedores": {}, "django": {}}}
    assert deploy_targets.servicios_presentes(
        config, ["backend_comedores", "mailing_worker", "user_import_worker"]
    ) == ["backend_comedores"]


def test_servicios_presentes_deduplica_worker_compartido_sin_omitirlo():
    config = {
        "services": {
            "django": {},
            "backend_comedores": {},
            "user_import_worker": {},
            "mailing_worker": {},
        }
    }
    assert deploy_targets.servicios_presentes(
        config,
        ["django", "user_import_worker", "backend_comedores", "user_import_worker"],
    ) == ["backend_comedores", "django", "user_import_worker"]


def test_backend_obligatorio_ausente_no_se_omite_silenciosamente():
    with pytest.raises(ValueError, match="backend_comedores"):
        deploy_targets.servicios_presentes(
            {"services": {"django": {}}}, ["backend_comedores", "user_import_worker"]
        )


def test_celery_de_pas_ausente_tampoco_se_considera_opcional():
    with pytest.raises(ValueError, match="celery_pas_worker"):
        deploy_targets.servicios_presentes(
            {"services": {"backend_pas": {}}},
            ["backend_pas", "celery_pas_worker", "user_import_worker"],
        )


def test_ocr_actualiza_web_worker_y_adaptador_compuesto():
    assert deploy_targets.planificar(["src/backends/ocr/ocr/services_ocr.py"]) == (
        "selectivo",
        ["backend_ocr", "ocr_worker", "user_import_worker"],
        True,
    )
    assert deploy_targets.planificar(["src/backends/ocr/tests/test_views.py"]) == (
        "ninguno",
        [],
        False,
    )


def test_ocr_worker_es_obligatorio_tambien_en_qa():
    with pytest.raises(ValueError, match="ocr_worker"):
        deploy_targets.servicios_presentes(
            {"services": {"backend_ocr": {}}},
            ["backend_ocr", "ocr_worker", "user_import_worker"],
        )


def test_selectivo_portal_no_reinicia_ocr_extraido():
    assert deploy_targets.servicios_core(
        {
            "services": {
                "django": {"image": "sisoc/core:abc"},
                "ocr_worker": {"image": "sisoc/backend-ocr:abc"},
                "backend_ocr": {"image": "sisoc/backend-ocr:abc"},
            }
        }
    ) == ["django"]
