"""Live helper + Nginx integration, inside the disposable proof image only."""

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import unittest

ROOT = Path("/repo")
SITE = Path("/etc/nginx/sites-available/staging.conf")
PWA = Path("/etc/nginx/snippets/sisoc-pwas.conf")
MARKER = Path("/etc/nginx/snippets/sisoc-package-marker.conf")
MANIFEST = Path("/etc/sisoc-nginx/qa.json")
HELPER = "/usr/local/libexec/sisoc-nginx-reconcile.py"


@unittest.skipUnless(
    os.name == "posix"
    and os.getenv("SISOC_NGINX_TEST_CONTAINER") == "1"
    and Path("/.dockerenv").exists(),
    "requires opt-in disposable Linux container",
)
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
        cls.pwa = (ROOT / "docs/operacion/nginx/sisoc-qa-pwas.conf").read_bytes()
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

    def test_05_first_onboarding_and_rollback(self):
        unmanaged = (
            b"server { listen 80 default_server; "
            b"location / { return 204; } "
            b"location ^~ /media/centrodefamilia/cargas_masivas/ { return 404; } "
            b"location ^~ /media/inspecciones/ { return 404; } "
            b"include /etc/nginx/snippets/sisoc-pwas.conf; }\n"
        )
        for kind in ("validation", "reload", "smoke", "success"):
            with self.subTest(kind=kind):
                unrelated = Path("/etc/nginx/conf.d/unrelated.conf")
                unrelated.write_text("# untouched\n")
                SITE.write_bytes(unmanaged)
                PWA.write_bytes(self.pwa)
                site_metadata = SITE.stat()
                MARKER.unlink(missing_ok=True)
                backups = set(Path("/var/backups/sisoc/nginx").glob("qa-bootstrap-*"))
                subprocess.run(["/usr/sbin/nginx", "-s", "reload"], check=True)
                stable = 0
                for _ in range(60):
                    probe = subprocess.run(
                        [
                            "/usr/bin/curl",
                            "-s",
                            "-o",
                            "/dev/null",
                            "-w",
                            "%{http_code}",
                            "http://127.0.0.1/",
                        ],
                        capture_output=True,
                        check=True,
                    )
                    stable = stable + 1 if probe.stdout == b"204" else 0
                    if stable == 10:
                        break
                    time.sleep(0.2)
                else:
                    self.fail("unmanaged baseline unavailable")
                candidate = self.site
                if kind == "validation":
                    candidate += b"\ninvalid_nginx_directive on;\n"
                elif kind == "reload":
                    Path("/run/sisoc-nginx/fail-reload").touch()
                elif kind == "smoke":
                    candidate = candidate.replace(
                        b"location = /__sisoc_nginx_package {\n        include /etc/nginx/snippets/sisoc-package-marker.conf;\n        return 404;",
                        b"location = /__sisoc_nginx_package {\n        include /etc/nginx/snippets/sisoc-package-marker.conf;\n        return 200;",
                    )
                self.approve(candidate, self.pwa)
                payload = json.dumps(
                    {
                        "site": base64.b64encode(candidate).decode(),
                        "pwa": base64.b64encode(self.pwa).decode(),
                    }
                ).encode()
                result = subprocess.run(
                    ["/usr/local/bin/python3", "-I", HELPER, "qa", "--bootstrap"],
                    input=payload,
                    capture_output=True,
                )
                created = (
                    set(Path("/var/backups/sisoc/nginx").glob("qa-bootstrap-*"))
                    - backups
                )
                self.assertEqual(len(created), 1)
                backup = created.pop()
                self.assertEqual((backup / "0").read_bytes(), unmanaged)
                self.assertEqual((backup / "1").read_bytes(), self.pwa)
                self.assertEqual(
                    json.loads((backup / "metadata.json").read_text())["marker"],
                    "absent",
                )
                self.assertEqual(unrelated.read_text(), "# untouched\n")
                if kind == "success":
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(SITE.read_bytes(), candidate)
                    self.assertTrue(MARKER.exists())
                else:
                    self.assertNotEqual(result.returncode, 0, kind)
                    self.assertEqual(SITE.read_bytes(), unmanaged)
                    self.assertEqual(PWA.read_bytes(), self.pwa)
                    self.assertFalse(MARKER.exists())
                    self.assertEqual(SITE.stat().st_mode, site_metadata.st_mode)
                    self.assertEqual(SITE.stat().st_uid, site_metadata.st_uid)
                    self.assertEqual(SITE.stat().st_gid, site_metadata.st_gid)
                    self.assertEqual(SITE.stat().st_mtime_ns, site_metadata.st_mtime_ns)
                    self.assertIn(b"previous configuration restored", result.stderr)
                    probe = subprocess.run(
                        [
                            "/usr/bin/curl",
                            "-s",
                            "-o",
                            "/dev/null",
                            "-w",
                            "%{http_code}",
                            "http://127.0.0.1/",
                        ],
                        capture_output=True,
                        check=True,
                    )
                    self.assertEqual(probe.stdout, b"204")
                    for path in (
                        "/media/inspecciones/example",
                        "/media/centrodefamilia/cargas_masivas/example",
                    ):
                        probe = subprocess.run(
                            [
                                "/usr/bin/curl",
                                "-s",
                                "-o",
                                "/dev/null",
                                "-w",
                                "%{http_code}",
                                "http://127.0.0.1" + path,
                            ],
                            capture_output=True,
                            check=True,
                        )
                        self.assertEqual(probe.stdout, b"404")

    def test_06_bootstrap_refuses_existing_marker(self):
        old = SITE.read_bytes(), PWA.read_bytes(), MARKER.read_bytes()
        payload = json.dumps(
            {
                "site": base64.b64encode(self.site).decode(),
                "pwa": base64.b64encode(self.pwa).decode(),
            }
        ).encode()
        result = subprocess.run(
            ["/usr/local/bin/python3", "-I", HELPER, "qa", "--bootstrap"],
            input=payload,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"bootstrap requires unmanaged state", result.stderr)
        self.assertEqual(
            old, (SITE.read_bytes(), PWA.read_bytes(), MARKER.read_bytes())
        )

    def test_07_restore_interrupted_from_backup(self):
        backup = max(
            Path("/var/backups/sisoc/nginx").glob("qa-bootstrap-*"),
            key=lambda p: p.stat().st_mtime_ns,
        )
        previous = (backup / "0").read_bytes(), (backup / "1").read_bytes()
        SITE.write_bytes(b"interrupted write")
        result = subprocess.run(
            [
                "/usr/local/bin/python3",
                "-I",
                HELPER,
                "qa",
                "--restore-bootstrap",
                str(backup),
            ],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((SITE.read_bytes(), PWA.read_bytes()), previous)
        self.assertFalse(MARKER.exists())
        probe = subprocess.run(
            [
                "/usr/bin/curl",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                "http://127.0.0.1/",
            ],
            capture_output=True,
            check=True,
        )
        self.assertEqual(probe.stdout, b"204")

    def test_08_reject_unsafe_bootstrap_inputs(self):
        payload = json.dumps(
            {
                "site": base64.b64encode(self.site).decode(),
                "pwa": base64.b64encode(self.pwa).decode(),
            }
        ).encode()

        def call():
            return subprocess.run(
                ["/usr/local/bin/python3", "-I", HELPER, "qa", "--bootstrap"],
                input=payload,
                capture_output=True,
            )

        old = SITE.read_bytes()
        hardlink = SITE.with_name("test-hardlink")
        os.link(SITE, hardlink)
        try:
            self.assertNotEqual(call().returncode, 0)
            self.assertEqual(SITE.read_bytes(), old)
        finally:
            hardlink.unlink()
        temporary = PWA.with_name("pwa-original")
        PWA.rename(temporary)
        PWA.symlink_to(temporary)
        try:
            self.assertNotEqual(call().returncode, 0)
            self.assertEqual(SITE.read_bytes(), old)
        finally:
            PWA.unlink()
            temporary.rename(PWA)
        os.setxattr(SITE, "user.sisoc-test", b"fixture")
        try:
            self.assertNotEqual(call().returncode, 0)
            self.assertEqual(SITE.read_bytes(), old)
        finally:
            os.removexattr(SITE, "user.sisoc-test")
        drifted = self.pwa.replace(b"\r\n", b"\n")
        self.assertNotEqual(drifted, self.pwa)
        PWA.write_bytes(drifted)
        try:
            result = call()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"shared PWA differs", result.stderr)
            self.assertEqual(PWA.read_bytes(), drifted)
            self.assertEqual(SITE.read_bytes(), old)
        finally:
            PWA.write_bytes(self.pwa)

    def test_09_failed_recovery_is_reported(self):
        backup = max(
            Path("/var/backups/sisoc/nginx").glob("qa-bootstrap-*"),
            key=lambda p: p.stat().st_mtime_ns,
        )
        Path("/run/sisoc-nginx/fail-reload").touch()
        result = subprocess.run(
            [
                "/usr/local/bin/python3",
                "-I",
                HELPER,
                "qa",
                "--restore-bootstrap",
                str(backup),
            ],
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b"backup restored", result.stdout)

    def test_10_recovery_rejects_corrupt_or_linked_backup(self):
        backup = max(
            Path("/var/backups/sisoc/nginx").glob("qa-bootstrap-*"),
            key=lambda p: p.stat().st_mtime_ns,
        )
        artifact = backup / "0"
        original = artifact.read_bytes()
        current = SITE.read_bytes()
        command = [
            "/usr/local/bin/python3",
            "-I",
            HELPER,
            "qa",
            "--restore-bootstrap",
            str(backup),
        ]
        artifact.write_bytes(b"corrupted backup")
        try:
            result = subprocess.run(command, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"backup integrity check failed", result.stderr)
            self.assertEqual(SITE.read_bytes(), current)
        finally:
            artifact.write_bytes(original)
        linked = backup / "linked"
        os.link(artifact, linked)
        try:
            result = subprocess.run(command, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(SITE.read_bytes(), current)
        finally:
            linked.unlink()
        artifact.rename(linked)
        artifact.symlink_to(linked)
        try:
            result = subprocess.run(command, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(SITE.read_bytes(), current)
        finally:
            artifact.unlink()
            linked.rename(artifact)


if __name__ == "__main__":
    unittest.main()
