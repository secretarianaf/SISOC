"""Run the production and QA Nginx references against isolated synthetic files."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
PROBE = r"""
set -eu
mkdir -p /etc/nginx/snippets /etc/apache2/certs /sisoc/SISOC/media/centrodefamilia/cargas_masivas /sisoc/SISOC/media/inspecciones /sisoc/SISOC/static_root /sisoc/logs/nginx /home/admin-ssies/sisoc-comedores-test/BACKOFFICE/media/centrodefamilia/cargas_masivas /home/admin-ssies/sisoc-comedores-test/BACKOFFICE/media/inspecciones /home/admin-ssies/sisoc-comedores-test/BACKOFFICE/static_root
cp /certs/* /etc/apache2/certs/
if [ "$ENVIRONMENT" = homologacion ]; then
    cp /repo/docs/operacion/nginx/sisoc-homologacion-pwas.conf /etc/nginx/snippets/sisoc-pwas.conf
elif [ "$ENVIRONMENT" = qa ]; then
    cp /repo/docs/operacion/nginx/sisoc-qa-pwas.conf /etc/nginx/snippets/sisoc-pwas.conf
else
    cp /repo/docs/operacion/nginx/sisoc-pwas.conf /etc/nginx/snippets/
fi
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
if [ "$ENVIRONMENT" = homologacion ]; then
    sed -i '/limit_req_zone .*sisoc_admin/d' /etc/nginx/nginx.conf
fi
nginx -t
nginx
if [ "$ENVIRONMENT" = produccion ]; then
    test "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' -H 'Host: com.sisoc.secretarianaf.gob.ar' 'http://127.0.0.1/some?q=1')" = '301 https://sisoc.secretarianaf.gob.ar/some?q=1'
    test "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' -H 'Host: sisoc.secretarianaf.gob.ar' 'http://127.0.0.1/some?q=1')" = '301 https://sisoc.secretarianaf.gob.ar/some?q=1'
    test "$(curl -sk -o /dev/null -w '%{http_code} %{redirect_url}' --resolve com.sisoc.secretarianaf.gob.ar:443:127.0.0.1 --noproxy '*' 'https://com.sisoc.secretarianaf.gob.ar/some?q=1')" = '301 https://sisoc.secretarianaf.gob.ar/some?q=1'
    base=https://127.0.0.1
    host=sisoc.secretarianaf.gob.ar
    for path in cdi pas/ddjj adjuntos; do
        test "$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $host" "$base/media/$path/private.txt")" = 404
    done
elif [ "$ENVIRONMENT" = homologacion ]; then
    test "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' -H 'Host: hml-sisoc.secretarianaf.gob.ar' 'http://127.0.0.1/some?q=1')" = '301 https://hml-sisoc.secretarianaf.gob.ar/some?q=1'
    test "$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' -H 'Host: com.hml-sisoc.secretarianaf.gob.ar' 'http://127.0.0.1/some?q=1')" = '301 https://hml-sisoc.secretarianaf.gob.ar/some?q=1'
    test "$(curl -sk -o /dev/null -w '%{http_code} %{redirect_url}' --resolve com.hml-sisoc.secretarianaf.gob.ar:443:127.0.0.1 --noproxy '*' 'https://com.hml-sisoc.secretarianaf.gob.ar/some?q=1')" = '301 https://hml-sisoc.secretarianaf.gob.ar/some?q=1'
    base=https://127.0.0.1
    host=hml-sisoc.secretarianaf.gob.ar
    test "$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $host" "$base/MID")" = 301
    { printf 'HTTP/1.1 200 OK\r\nContent-Length: 3\r\nConnection: close\r\n\r\nMID'; } | nc -l -p 8100 &
    mid_pid=$!
    sleep 0.2
    test "$(curl -sk --max-time 3 -H "Host: $host" "$base/MID/")" = MID
    wait "$mid_pid"
    test "$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $host" "$base/pwa/inspecciones")" = 302
    { printf 'HTTP/1.1 200 OK\r\nContent-Length: 3\r\nConnection: close\r\n\r\nPWA'; } | nc -l -p 8083 &
    pwa_pid=$!
    sleep 0.2
    test "$(curl -sk --max-time 3 -H "Host: $host" "$base/pwa/inspecciones/")" = PWA
    wait "$pwa_pid"
    for path in cdi pas/ddjj adjuntos; do
        test "$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $host" "$base/media/$path/private.txt")" = 404
    done
else
    base=http://127.0.0.1
    host=localhost
fi
test "$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $host" "$base/media/centrodefamilia/cargas_masivas/private.xlsx")" = 404
if [ "$ENVIRONMENT" != qa ]; then
    curl -sk -D /tmp/cdf-headers -o /dev/null -H "Host: $host" "$base/media/centrodefamilia/cargas_masivas/private.xlsx"
    tr -d '\r' < /tmp/cdf-headers | grep -Fxi 'Strict-Transport-Security: max-age=31536000; includeSubDomains' >/dev/null
fi
test "$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $host" "$base/media/inspecciones/private.txt")" = 404
test "$(curl -sk -w ' %{http_code}' -H "Host: $host" "$base/media/public.txt")" = 'public 200'
test "$(curl -sk -o /dev/null -w '%{http_code}' -H "Host: $host" "$base/mobile")" = 302
nginx -s quit
"""


@unittest.skipUnless(
    os.getenv("SISOC_NGINX_DOCKER_TESTS") == "1", "requires explicit Docker opt-in"
)
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
                    "subjectAltName=DNS:sisoc.secretarianaf.gob.ar,DNS:hml-sisoc.secretarianaf.gob.ar",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for env in ("produccion", "qa", "homologacion"):
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
