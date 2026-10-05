"""El kernel arranca sin ninguna app de dominio.

Cada backend por vertical (#2309) instala solo el kernel más sus apps. Si el
kernel vuelve a declarar FKs, señales o imports de arranque hacia dominios
(comedores, organizaciones, duplas...), este test falla.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

SCRIPT = """
import config, django
django.setup()
from django.core.management import call_command
call_command("check")
import users.models, users.services, users.territorial_scope
import users.services_generate_user, users.services_datacalle
import users.services_delegation, users.services_group_permissions, users.admin
import core.admin, core.context_processors, core.views, core.resources
from core.models import Programa
assert Programa().organismo is None
print("KERNEL_OK")
"""


def test_kernel_arranca_sin_apps_de_dominio():
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "tests.settings_solo_kernel",
        "WAIT_FOR_DB": "false",
    }
    resultado = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    assert "KERNEL_OK" in resultado.stdout, resultado.stdout + resultado.stderr
