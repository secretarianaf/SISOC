"""Deployment does not reconcile Nginx; versioned vhosts stay standalone."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]


class DeployNginxContract(unittest.TestCase):
    def test_deploy_does_not_invoke_nginx_reconciliation(self):
        for relative in (
            ".github/workflows/deploy.yml",
            "src/scripts/operacion/deploy_verified.sh",
        ):
            with self.subTest(path=relative):
                self.assertNotIn(
                    "deploy_nginx_gate", (ROOT / relative).read_text(encoding="utf-8")
                )

    def test_vhosts_do_not_require_reconciliation_marker(self):
        for environment in ("qa", "homologacion", "produccion"):
            with self.subTest(environment=environment):
                config = (
                    ROOT / f"docs/operacion/nginx/sisoc-{environment}.conf"
                ).read_text(encoding="utf-8")
                self.assertNotIn("sisoc-package-marker", config)
                self.assertNotIn("/run/sisoc-nginx/probe.sock", config)
                self.assertIn(
                    "location ^~ /media/centrodefamilia/cargas_masivas/", config
                )
                self.assertIn("location ^~ /media/inspecciones/", config)


if __name__ == "__main__":
    unittest.main()
