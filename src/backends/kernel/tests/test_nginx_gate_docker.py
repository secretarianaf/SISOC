"""Isolated tests of deployment onboarding states."""

from pathlib import Path
import os
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[4]
PROBE = r"""
set -eu
export SISOC_ROOT_DIR=/repo
revision=0123456789012345678901234567890123456789
output=$(bash /repo/src/scripts/operacion/deploy_nginx_gate.sh qa "$revision")
printf '%s' "$output" | grep -q 'NO GESTIONADO'
mkdir -p /etc/sisoc-nginx
chmod 0755 /etc/sisoc-nginx
touch /etc/sisoc-nginx/qa.enabled
mkdir -p /var/lib/sisoc-nginx
chmod 0755 /var/lib/sisoc-nginx
touch /var/lib/sisoc-nginx/qa.activated
if bash /repo/src/scripts/operacion/deploy_nginx_gate.sh qa "$revision"; then exit 1; fi
chmod 0700 /etc/sisoc-nginx
if runuser -u nobody -- bash /repo/src/scripts/operacion/deploy_nginx_gate.sh qa "$revision"; then exit 1; fi
chmod 0755 /etc/sisoc-nginx
touch /etc/sisoc-nginx/homologacion.enabled
touch /var/lib/sisoc-nginx/homologacion.activated
if bash /repo/src/scripts/operacion/deploy_nginx_gate.sh homologacion "$revision"; then exit 1; fi
mkdir -p /var/lib/sisoc-nginx
chmod 0755 /var/lib/sisoc-nginx
touch /var/lib/sisoc-nginx/production.activated
if bash /repo/src/scripts/operacion/deploy_nginx_gate.sh production "$revision"; then
    echo 'activated environment incorrectly treated as unmanaged' >&2; exit 1
fi
"""


@unittest.skipUnless(
    os.getenv("SISOC_NGINX_DOCKER_TESTS") == "1", "requires explicit Docker opt-in"
)
class GateDocker(unittest.TestCase):
    def test_unmanaged_and_fail_closed_states(self):
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "-v",
                f"{ROOT}:/repo:ro",
                "-w",
                "/repo",
                "python:3.12-slim",
                "bash",
                "-c",
                PROBE,
            ],
            check=True,
        )


if __name__ == "__main__":
    unittest.main()
