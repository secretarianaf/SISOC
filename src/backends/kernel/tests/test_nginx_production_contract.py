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


if __name__ == "__main__":
    unittest.main()
