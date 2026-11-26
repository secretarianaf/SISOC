"""Contract tests; run as root only inside a disposable Docker container."""

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "src/scripts/infra/sisoc_nginx_reconcile.py"
module = None
if (
    os.name == "posix"
    and os.getenv("SISOC_NGINX_TEST_CONTAINER") == "1"
    and Path("/.dockerenv").exists()
):
    spec = importlib.util.spec_from_file_location("sisoc_nginx_reconcile", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


class FakeOps:
    def __init__(self):
        self.reloads = 0
        self.fail = None
        self.loaded = None

    def validate(self):
        if self.fail == "validate":
            self.fail = None
            raise RuntimeError("validation failed")

    def reload(self):
        self.reloads += 1
        if self.fail == "reload":
            self.fail = None
            raise RuntimeError("reload failed")
        self.loaded = module.current_marker()

    def smoke(self, environment, marker):
        if self.fail == "smoke":
            self.fail = None
            return False
        return self.loaded == marker


@unittest.skipUnless(module is not None, "requires opt-in disposable Linux container")
class ReconcileContract(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="sisoc-nginx-", dir="/root"))
        self.addCleanup(shutil.rmtree, self.temp)
        self.manifest = self.temp / "manifest.json"
        self.site = self.temp / "site.conf"
        self.pwa = self.temp / "pwa.conf"
        self.marker = self.temp / "marker.conf"
        self.backup = self.temp / "backups"
        self.backup.mkdir(mode=0o700)
        self.lock = self.temp / "lock"
        self.ops = FakeOps()
        self.site_bytes = b"server { location /x { include /etc/nginx/snippets/sisoc-package-marker.conf; } include /etc/nginx/snippets/sisoc-pwas.conf; location /probe { include /etc/nginx/snippets/sisoc-package-marker.conf; } }\n"
        self.pwa_bytes = b"location /mobile/ { return 200; }\n"
        self.approve(self.site_bytes, self.pwa_bytes)
        self.site.write_bytes(self.site_bytes)
        self.pwa.write_bytes(self.pwa_bytes)
        self.old_marker = module.package_marker(self.site_bytes, self.pwa_bytes)
        self.marker.write_bytes(module.marker_content(self.old_marker))
        self.ops.loaded = self.old_marker
        self.context = patch.multiple(
            module,
            MANIFESTS={"qa": self.manifest},
            TARGETS={"qa": (self.site, self.pwa)},
            MARKER_PATH=self.marker,
            BACKUP_DIR=self.backup,
            LOCK_PATH=self.lock,
        )
        self.context.start()
        self.addCleanup(self.context.stop)

    def approve(self, site, pwa):
        self.manifest.write_text(
            json.dumps(
                {
                    "version": 1,
                    "environment": "qa",
                    "site_sha256": hashlib.sha256(site).hexdigest(),
                    "pwa_sha256": hashlib.sha256(pwa).hexdigest(),
                }
            ),
            encoding="utf-8",
        )
        self.manifest.chmod(0o600)

    def payload(self, site=None, pwa=None):
        return json.dumps(
            {
                "site": base64.b64encode(
                    site if site is not None else self.site_bytes
                ).decode(),
                "pwa": base64.b64encode(
                    pwa if pwa is not None else self.pwa_bytes
                ).decode(),
            }
        ).encode()

    def snapshot(self):
        return [p.read_bytes() for p in (self.site, self.pwa, self.marker)]

    def test_graph_rejects_approved_files_not_in_nginx_configuration(self):
        from types import SimpleNamespace

        ops = module.RealOps()
        with patch.object(
            ops,
            "_run",
            return_value=SimpleNamespace(
                stdout=b"# configuration file /etc/nginx/nginx.conf:\nhttp {}\n"
            ),
        ):
            self.assertFalse(ops.graph_contains_managed_files("qa"))

    def test_upstream_cannot_prove_inactive_vhost_with_public_marker(self):
        from types import SimpleNamespace

        fake = SimpleNamespace(
            stdout=(
                "HTTP/1.1 404 Not Found\r\n"
                + "X-SISOC-Nginx-Package: "
                + self.old_marker
                + "\r\n\r\n404"
            ).encode()
        )
        ops = module.RealOps()
        with patch.object(ops, "_run", return_value=fake):
            self.assertFalse(ops.smoke("qa", self.old_marker))

    def test_same_package_across_releases_does_not_reload(self):
        module.reconcile("qa", self.payload(), self.ops)
        module.reconcile("qa", self.payload(), self.ops)
        self.assertEqual(self.ops.reloads, 0)

    def test_approved_drift_installs_and_checks_loaded_marker(self):
        self.site.write_bytes(b"old site\n")
        module.reconcile("qa", self.payload(), self.ops)
        self.assertEqual(self.site.read_bytes(), self.site_bytes)
        self.assertEqual(self.ops.loaded, self.old_marker)
        self.assertEqual(self.ops.reloads, 1)

    def test_unapproved_or_tampered_manifest_cannot_write(self):
        before = self.snapshot()
        with self.assertRaises(Exception):
            module.reconcile("qa", self.payload(site=b"malicious"), self.ops)
        self.assertEqual(self.snapshot(), before)
        self.manifest.chmod(0o666)
        with self.assertRaises(Exception):
            module.reconcile("qa", self.payload(), self.ops)
        self.assertEqual(self.snapshot(), before)

    def test_failure_rolls_back_every_target(self):
        for failure in ("validate", "reload", "smoke"):
            with self.subTest(failure=failure):
                self.site.write_bytes(b"old site\n")
                before = self.snapshot()
                self.ops.fail = failure
                with self.assertRaises(Exception):
                    module.reconcile("qa", self.payload(), self.ops)
                self.assertEqual(self.snapshot(), before)

    def test_approved_package_cannot_add_arbitrary_include(self):
        payload = self.site_bytes.replace(
            b"server {", b'server { "include" /etc/passwd;'
        )
        self.approve(payload, self.pwa_bytes)
        before = self.snapshot()
        with self.assertRaises(Exception):
            module.reconcile("qa", self.payload(site=payload), self.ops)
        self.assertEqual(self.snapshot(), before)

    def test_unrelated_file_is_not_changed(self):
        unrelated = self.temp / "other-site.conf"
        unrelated.write_bytes(b"other site")
        self.site.write_bytes(b"old site")
        module.reconcile("qa", self.payload(), self.ops)
        self.assertEqual(unrelated.read_bytes(), b"other site")

    def test_unverifiable_effective_configuration_is_not_success(self):
        self.ops.loaded = "different-marker"
        self.ops.fail = "smoke"
        # A reload is required even when the files match.
        module.reconcile("qa", self.payload(), self.ops)
        self.assertEqual(self.ops.reloads, 1)
        self.assertEqual(self.ops.loaded, self.old_marker)

    def test_hml_accepts_independently_approved_package_and_probe(self):
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        manifest.update(
            environment="homologacion",
            probe_host="hml.example.invalid",
            probe_port=443,
            probe_scheme="https",
        )
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        with (
            patch.dict(module.MANIFESTS, {"homologacion": self.manifest}),
            patch.dict(module.TARGETS, {"homologacion": (self.site, self.pwa)}),
        ):
            self.assertEqual(
                module.reconcile("homologacion", self.payload(), self.ops), "unchanged"
            )
        self.assertEqual(self.ops.reloads, 0)

    def test_hml_probe_configuration_rejects_injection_and_invalid_ports(self):
        module._validate_probe("hml.example.invalid", 443, "https")
        for host, port, scheme in [
            ("host\n--insecure", 443, "https"),
            ("hml.example", 0, "https"),
            ("hml.example", 443, "file"),
        ]:
            with self.subTest(host=host, port=port, scheme=scheme):
                with self.assertRaises(ValueError):
                    module._validate_probe(host, port, scheme)

    def test_mid_install_failure_restores_all_files(self):
        updated_site = self.site_bytes + b"\n# approved new site\n"
        updated_pwa = self.pwa_bytes + b"\n# approved new PWA\n"
        self.approve(updated_site, updated_pwa)
        before = self.snapshot()
        original_write = module._atomic_write
        calls = []

        def failing_write(path, content, mode=0o644):
            calls.append(path)
            if path == self.pwa and calls.count(self.pwa) == 1:
                raise OSError("synthetic mid-install failure")
            return original_write(path, content, mode)

        with patch.object(module, "_atomic_write", side_effect=failing_write):
            with self.assertRaises(RuntimeError):
                module.reconcile(
                    "qa", self.payload(updated_site, updated_pwa), self.ops
                )
        self.assertEqual(before, self.snapshot())

    def test_manifest_for_another_environment_is_rejected(self):
        before = self.snapshot()
        manifest = json.loads(self.manifest.read_text())
        manifest["environment"] = "production"
        self.manifest.write_text(json.dumps(manifest))
        with self.assertRaises(PermissionError):
            module.reconcile("qa", self.payload(), self.ops)
        self.assertEqual(before, self.snapshot())

    def test_symlink_target_fails_closed(self):
        self.site.unlink()
        self.site.symlink_to(self.pwa)
        before = self.pwa.read_bytes()
        with self.assertRaises(Exception):
            module.reconcile("qa", self.payload(), self.ops)
        self.assertEqual(self.pwa.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
