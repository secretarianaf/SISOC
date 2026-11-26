"""Contract checks for the versioned production Nginx configuration."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]


class NginxProductionContract(unittest.TestCase):
    def test_production_keeps_original_and_private_locations(self):
        config = (ROOT / "docs/operacion/nginx/sisoc-produccion.conf").read_text(
            encoding="utf-8"
        )
        for expected in (
            "alias /sisoc/SISOC/static_root/;",
            "alias /sisoc/SISOC/media/;",
            "location ^~ /admin/ {",
            "limit_req zone=sisoc_admin burst=40 nodelay;",
            "location ^~ /media/inspecciones/ {",
            "location ^~ /media/centrodefamilia/cargas_masivas/ {",
            "include /etc/nginx/snippets/sisoc-pwas.conf;",
            "access_log  /sisoc/logs/nginx/SISOC-ssl-access.log;",
        ):
            self.assertIn(expected, config)

    def test_hml_uses_production_contract_without_production_domain(self):
        config = (ROOT / "docs/operacion/nginx/sisoc-homologacion.conf").read_text(
            encoding="utf-8"
        )
        self.assertIn("server_name hml-sisoc.secretarianaf.gob.ar;", config)
        self.assertIn(
            "return 301 https://hml-sisoc.secretarianaf.gob.ar$request_uri;", config
        )
        self.assertNotIn("server_name sisoc.secretarianaf.gob.ar;", config)
        self.assertNotIn("https://sisoc.secretarianaf.gob.ar", config)
        for expected in (
            "location ^~ /admin/ {",
            "limit_req zone=sisoc_admin burst=40 nodelay;",
            "location ^~ /media/inspecciones/ {",
            "location ^~ /media/centrodefamilia/cargas_masivas/ {",
            "include /etc/nginx/snippets/sisoc-pwas.conf;",
            "listen unix:/run/sisoc-nginx/probe.sock;",
        ):
            self.assertIn(expected, config)


if __name__ == "__main__":
    unittest.main()
