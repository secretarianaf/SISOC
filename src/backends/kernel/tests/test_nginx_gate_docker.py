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
ln -s /usr/local/bin/python3 /usr/bin/python3
cat > /usr/bin/git <<'EOF'
#!/bin/sh
set -eu
[ "$1" = -C ] && [ "$3" = show ]
cat "/repo/${4#*:}"
EOF
cat > /usr/bin/sudo <<'EOF'
#!/bin/sh
[ "$1" = -n ]
shift
exec "$@"
EOF
cat > /usr/local/sbin/sisoc-nginx-homologacion <<'EOF'
#!/bin/sh
cat > /tmp/hml-package.json
EOF
chmod 0755 /usr/bin/git /usr/bin/sudo /usr/local/sbin/sisoc-nginx-homologacion
bash /repo/src/scripts/operacion/deploy_nginx_gate.sh homologacion "$revision"
python - <<'EOF'
import base64, json
from pathlib import Path
package = json.loads(Path('/tmp/hml-package.json').read_text())
assert base64.b64decode(package['site']) == Path('/repo/docs/operacion/nginx/sisoc-homologacion.conf').read_bytes()
assert base64.b64decode(package['pwa']) == Path('/repo/docs/operacion/nginx/sisoc-homologacion-pwas.conf').read_bytes()
EOF
python -c "import os,socket,time; s=socket.socket(socket.AF_UNIX); s.bind('/var/run/docker.sock'); os.chmod('/var/run/docker.sock',0o666); time.sleep(15)" &
socket_pid=$!
for n in 1 2 3 4 5; do [ -S /var/run/docker.sock ] && break; sleep 0.2; done
[ -S /var/run/docker.sock ]
rm /tmp/hml-package.json
socket_output=$(bash /repo/src/scripts/operacion/deploy_nginx_gate.sh homologacion "$revision" 2>&1)
printf '%s' "$socket_output" | grep -q 'runner con acceso Docker'
test -s /tmp/hml-package.json
kill "$socket_pid"
wait "$socket_pid" 2>/dev/null || true
rm /var/run/docker.sock
mkdir -p /tmp/hostile
for binary in git sudo python3; do
    printf '#!/bin/sh\nexit 88\n' > "/tmp/hostile/$binary"
    chmod 0755 "/tmp/hostile/$binary"
done
for environment in qa production; do
    touch "/etc/sisoc-nginx/$environment.enabled" "/var/lib/sisoc-nginx/$environment.activated"
    cat > "/usr/local/sbin/sisoc-nginx-$environment" <<'EOF'
#!/bin/sh
cat > /tmp/selected-package.json
EOF
    chmod 0755 "/usr/local/sbin/sisoc-nginx-$environment"
    PATH="/tmp/hostile:$PATH" bash /repo/src/scripts/operacion/deploy_nginx_gate.sh "$environment" "$revision"
    SISOC_TEST_ENV="$environment" /usr/bin/python3 - <<'EOF'
import base64, hashlib, json, os
from pathlib import Path
package = json.loads(Path('/tmp/selected-package.json').read_text())
pwa = base64.b64decode(package['pwa'])
if os.environ['SISOC_TEST_ENV'] == 'qa':
    assert pwa == Path('/repo/docs/operacion/nginx/sisoc-qa-pwas.conf').read_bytes()
    assert hashlib.sha256(pwa).hexdigest() == '8382522d53ed11bd37e8b6cf5d5047b6d6304cf4ed5dd2bbadcbe0c655db1505'
else:
    assert pwa == Path('/repo/docs/operacion/nginx/sisoc-pwas.conf').read_bytes()
EOF
done
rm /etc/sisoc-nginx/production.enabled
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
