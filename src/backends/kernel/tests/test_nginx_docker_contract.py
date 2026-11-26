"""Run the production and QA Nginx references against isolated synthetic files."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
PROBE = r"""
set -eu
mkdir -p /run/sisoc-nginx /etc/nginx/snippets /etc/apache2/certs /sisoc/SISOC/media/centrodefamilia/cargas_masivas /sisoc/SISOC/media/inspecciones /sisoc/SISOC/static_root /sisoc/logs/nginx /home/admin-ssies/sisoc-comedores-test/BACKOFFICE/media/centrodefamilia/cargas_masivas /home/admin-ssies/sisoc-comedores-test/BACKOFFICE/media/inspecciones /home/admin-ssies/sisoc-comedores-test/BACKOFFICE/static_root
chmod 0700 /run/sisoc-nginx
cp /certs/* /etc/apache2/certs/
cp /repo/docs/operacion/nginx/sisoc-pwas.conf /etc/nginx/snippets/
printf 'add_header X-SISOC-Nginx-Package "package-old" always;\n' > /etc/nginx/snippets/sisoc-package-marker.conf
cp /repo/docs/operacion/nginx/sisoc-$ENVIRONMENT.conf /etc/nginx/conf.d/default.conf
printf public > /sisoc/SISOC/media/public.txt
printf private > /sisoc/SISOC/media/centrodefamilia/cargas_masivas/private.xlsx
printf private > /sisoc/SISOC/media/inspecciones/private.txt
mkdir -p /sisoc/SISOC/media/cdi /sisoc/SISOC/media/pas/ddjj /sisoc/SISOC/media/adjuntos
for path in cdi pas/ddjj adjuntos; do printf private > "/sisoc/SISOC/media/$path/private.txt"; done
cp -r /sisoc/SISOC/media/. /home/admin-ssies/sisoc-comedores-test/BACKOFFICE/media/
cat > /etc/nginx/nginx.conf <<'EOF'
events {}
http {
    limit_req_zone $binary_remote_addr zone=default:1m rate=100r/s;
    limit_req_zone $binary_remote_addr zone=sisoc_admin:1m rate=100r/s;
    include /etc/nginx/conf.d/*.conf;
}
EOF
rm /etc/nginx/snippets/sisoc-package-marker.conf
if nginx -t >/dev/null 2>&1; then
    echo 'ERROR: missing marker unexpectedly accepted' >&2
    exit 1
fi
printf 'add_header X-SISOC-Nginx-Package "package-old" always;\n' > /etc/nginx/snippets/sisoc-package-marker.conf
chmod 0644 /etc/nginx/snippets/sisoc-package-marker.conf
test "$(stat -c '%u:%g' /etc/nginx/snippets/sisoc-package-marker.conf)" = 0:0
nginx -t
nginx
if [ "$ENVIRONMENT" = produccion ]; then
    test "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' -H 'Host: com.sisoc.secretarianaf.gob.ar' 'http://127.0.0.1/some?q=1')" = '301 https://sisoc.secretarianaf.gob.ar/some?q=1'
    test "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' -H 'Host: sisoc.secretarianaf.gob.ar' 'http://127.0.0.1/some?q=1')" = '301 https://sisoc.secretarianaf.gob.ar/some?q=1'
    test "$(curl -sk -o /dev/null -w '%{http_code} %{redirect_url}' --resolve com.sisoc.secretarianaf.gob.ar:443:127.0.0.1 --noproxy '*' 'https://com.sisoc.secretarianaf.gob.ar/some?q=1')" = '301 https://sisoc.secretarianaf.gob.ar/some?q=1'
    base=https://127.0.0.1
    host=sisoc.secretarianaf.gob.ar
    probe_url=https://sisoc.secretarianaf.gob.ar/media/centrodefamilia/cargas_masivas/private.xlsx
    probe_curl() { curl -sS --noproxy '*' --cacert /certs/fullchain.crt --resolve sisoc.secretarianaf.gob.ar:443:127.0.0.1 -D /tmp/headers -o /dev/null -w '%{http_code}' "$probe_url"; }
    for path in cdi pas/ddjj adjuntos; do
        test "$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $host" "$base/media/$path/private.txt")" = 404
    done
else
    base=http://127.0.0.1
    host=localhost
    probe_url=http://127.0.0.1/media/centrodefamilia/cargas_masivas/private.xlsx
    probe_curl() { curl -sS --noproxy '*' -H 'Host: localhost' -D /tmp/headers -o /dev/null -w '%{http_code}' "$probe_url"; }
fi
check_marker() {
    expected="$1"
    test "$(curl -sS --noproxy '*' --unix-socket /run/sisoc-nginx/probe.sock -D /tmp/private-headers -o /dev/null -w '%{http_code}' http://localhost/__sisoc_nginx_package)" = 404 || return 1
    tr -d '\r' < /tmp/private-headers | grep -Fxi "X-SISOC-Nginx-Package: $expected" >/dev/null || return 1
    test "$(probe_curl)" = 404 || return 1
    tr -d '\r' < /tmp/headers | grep -Fxi "X-SISOC-Nginx-Package: $expected" >/dev/null || return 1
    if [ "$ENVIRONMENT" = produccion ]; then
        tr -d '\r' < /tmp/headers | grep -Fxi 'Strict-Transport-Security: max-age=31536000; includeSubDomains' >/dev/null || return 1
    fi
}
check_marker package-old
printf 'add_header X-SISOC-Nginx-Package "package-new" always;\n' > /etc/nginx/snippets/sisoc-package-marker.conf
nginx -T 2>&1 | grep -q 'X-SISOC-Nginx-Package "package-new"'
check_marker package-old
nginx -s reload
attempt=0
until check_marker package-new; do
    attempt=$((attempt + 1))
    [ "$attempt" -lt 20 ] || exit 1
    sleep 0.1
done
test "$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $host" "$base/media/centrodefamilia/cargas_masivas/private.xlsx")" = 404
test "$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $host" "$base/media/inspecciones/private.txt")" = 404
test "$(curl -sk -w ' %{http_code}' -H "Host: $host" "$base/media/public.txt")" = 'public 200'
test "$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $host" "$base/mobile")" = 302
nginx -s quit
"""


class NginxDockerContract(unittest.TestCase):
    def test_nginx_references(self):
        with tempfile.TemporaryDirectory(prefix="sisoc-nginx-") as temp:
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "-v",
                    f"{temp}:/certs",
                    "python:3.12-slim",
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-keyout",
                    "/certs/secretarianaf.gob.ar.key",
                    "-out",
                    "/certs/fullchain.crt",
                    "-days",
                    "1",
                    "-subj",
                    "/CN=sisoc.secretarianaf.gob.ar",
                    "-addext",
                    "subjectAltName=DNS:sisoc.secretarianaf.gob.ar",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for env in ("produccion", "qa"):
                with self.subTest(environment=env):
                    subprocess.run(
                        [
                            "docker",
                            "run",
                            "--rm",
                            "--network",
                            "none",
                            "-v",
                            f"{ROOT}:/repo:ro",
                            "-v",
                            f"{temp}:/certs:ro",
                            "-e",
                            f"ENVIRONMENT={env}",
                            "nginx:1.27-alpine",
                            "sh",
                            "-c",
                            PROBE,
                        ],
                        check=True,
                    )


if __name__ == "__main__":
    unittest.main()
