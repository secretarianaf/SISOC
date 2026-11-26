"""Live helper + Nginx integration, inside the disposable proof image only."""

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path("/repo")
SITE = Path("/etc/nginx/sites-available/staging.conf")
PWA = Path("/etc/nginx/snippets/sisoc-pwas.conf")
MARKER = Path("/etc/nginx/snippets/sisoc-package-marker.conf")
MANIFEST = Path("/etc/sisoc-nginx/qa.json")
HELPER = "/usr/local/libexec/sisoc-nginx-reconcile.py"


class LiveNginx(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for directory in (
            "/etc/nginx/sites-available",
            "/etc/nginx/snippets",
            "/etc/nginx/conf.d",
            "/etc/sisoc-nginx",
            "/run/sisoc-nginx",
            "/var/backups/sisoc/nginx",
            "/var/log/nginx",
            "/home/admin-ssies/sisoc-comedores-test/BACKOFFICE/media/centrodefamilia/cargas_masivas",
            "/home/admin-ssies/sisoc-comedores-test/BACKOFFICE/static_root",
            "/usr/local/libexec",
            "/var/cache/nginx",
        ):
            Path(directory).mkdir(parents=True, exist_ok=True)
        os.chmod("/run/sisoc-nginx", 0o700)
        Path(HELPER).write_bytes(
            (ROOT / "src/scripts/infra/sisoc_nginx_reconcile.py").read_bytes()
        )
        Path(HELPER).chmod(0o755)
        Path("/usr/bin/systemctl").write_text("""#!/bin/sh
set -eu
[ "$1 $2" = "reload nginx" ]
if [ -f /run/sisoc-nginx/fail-reload ]; then rm /run/sisoc-nginx/fail-reload; exit 1; fi
echo reload >> /run/sisoc-nginx/reloads
exec /usr/sbin/nginx -s reload
""")
        Path("/usr/bin/systemctl").chmod(0o755)
        Path("/etc/nginx/nginx.conf").write_text(
            "user nobody nogroup;\nevents {}\nhttp { include /etc/nginx/sites-available/staging.conf; }\n"
        )
        cls.site = (ROOT / "docs/operacion/nginx/sisoc-qa.conf").read_bytes()
        cls.pwa = (ROOT / "docs/operacion/nginx/sisoc-pwas.conf").read_bytes()
        SITE.write_bytes(cls.site)
        PWA.write_bytes(cls.pwa)
        MARKER.write_bytes(cls.marker(cls.site, cls.pwa))
        cls.approve(cls.site, cls.pwa)
        subprocess.run(["/usr/sbin/nginx", "-t"], check=True)
        subprocess.run(["/usr/sbin/nginx"], check=True)

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["/usr/sbin/nginx", "-s", "quit"], check=False)

    @staticmethod
    def marker(site, pwa):
        digest = hashlib.sha256(
            b"sisoc-nginx-package-v1\0"
            + hashlib.sha256(site).digest()
            + hashlib.sha256(pwa).digest()
        ).hexdigest()
        return f'add_header X-SISOC-Nginx-Package "{digest}" always;\n'.encode()

    @staticmethod
    def approve(site, pwa):
        MANIFEST.write_text(
            json.dumps(
                {
                    "version": 1,
                    "environment": "qa",
                    "site_sha256": hashlib.sha256(site).hexdigest(),
                    "pwa_sha256": hashlib.sha256(pwa).hexdigest(),
                }
            )
        )
        MANIFEST.chmod(0o600)

    @staticmethod
    def run_helper(site, pwa):
        payload = json.dumps(
            {
                "site": base64.b64encode(site).decode(),
                "pwa": base64.b64encode(pwa).decode(),
            }
        ).encode()
        return subprocess.run(
            ["/usr/local/bin/python3", "-I", HELPER, "qa"],
            input=payload,
            capture_output=True,
        )

    def reload_count(self):
        path = Path("/run/sisoc-nginx/reloads")
        return len(path.read_text().splitlines()) if path.exists() else 0

    def test_01_equal_across_two_releases(self):
        before = self.reload_count()
        for _ in range(2):
            result = self.run_helper(self.site, self.pwa)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b"unchanged", result.stdout)
        self.assertEqual(self.reload_count(), before)

    def test_02_approved_drift(self):
        changed = self.site + b"\n# approved fixture\n"
        self.approve(changed, self.pwa)
        before = self.reload_count()
        result = self.run_helper(changed, self.pwa)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(SITE.read_bytes(), changed)
        self.assertEqual(self.reload_count(), before + 1)

    def test_03_unapproved(self):
        before = (
            SITE.read_bytes(),
            PWA.read_bytes(),
            MARKER.read_bytes(),
            self.reload_count(),
        )
        result = self.run_helper(b"manipulated", self.pwa)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            before,
            (
                SITE.read_bytes(),
                PWA.read_bytes(),
                MARKER.read_bytes(),
                self.reload_count(),
            ),
        )

    def test_04_validation_reload_and_smoke_failures_rollback(self):
        for kind in ("validation", "reload", "smoke"):
            with self.subTest(kind=kind):
                old = SITE.read_bytes(), PWA.read_bytes(), MARKER.read_bytes()
                if kind == "validation":
                    candidate = self.site + b"\ninvalid_nginx_directive on;\n"
                elif kind == "smoke":
                    candidate = self.site.replace(
                        b"location = /__sisoc_nginx_package {\n        include /etc/nginx/snippets/sisoc-package-marker.conf;\n        return 404;",
                        b"location = /__sisoc_nginx_package {\n        include /etc/nginx/snippets/sisoc-package-marker.conf;\n        return 200;",
                    )
                    self.assertNotEqual(candidate, self.site)
                else:
                    candidate = self.site + b"\n# reload failure\n"
                    Path("/run/sisoc-nginx/fail-reload").touch()
                self.approve(candidate, self.pwa)
                result = self.run_helper(candidate, self.pwa)
                self.assertNotEqual(result.returncode, 0, kind)
                self.assertEqual(
                    old, (SITE.read_bytes(), PWA.read_bytes(), MARKER.read_bytes())
                )
                self.assertIn(b"previous configuration restored", result.stderr)


if __name__ == "__main__":
    unittest.main()
