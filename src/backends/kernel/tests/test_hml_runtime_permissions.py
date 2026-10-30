"""Linux filesystem regression tests; no Django or database required."""

import errno
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import yaml

SCRIPT = (
    Path(__file__).resolve().parents[4]
    / "src/scripts/operacion/provision_hml_runtime_permissions.py"
)
UID = 10001
KEY = "system.posix_acl_access"


@unittest.skipUnless(
    sys.platform == "linux" and os.geteuid() == 0,
    "Needs isolated Linux root for UID/ACL tests",
)
class HmlPermissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.base.chmod(0o755)
        self.root = self.base / "media"
        self.root.mkdir(mode=0o755)
        self.file = self.root / "synthetic.txt"
        self.file.write_bytes(b"unchanged synthetic document")
        self.file.chmod(0o640)
        self.backup = self.base / "backup.json"

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def child_write(self, directory):
        pid = os.fork()
        if pid == 0:
            try:
                os.setgroups([])
                os.setgid(1016)
                os.setuid(UID)
                fd, name = tempfile.mkstemp(dir=directory)
                with os.fdopen(fd, "wb") as handle:
                    handle.write(b"synthetic")
                os.unlink(name)
                os._exit(0)
            except PermissionError:
                os._exit(errno.EACCES)
            except Exception:
                os._exit(99)
        return os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1])

    def apply(self):
        result = self.run_cli("--apply", "--backup", str(self.backup))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_existing_and_future_directories_without_changing_documents(self):
        self.assertEqual(self.child_write(self.root), errno.EACCES)
        before = (
            self.file.read_bytes(),
            self.file.stat().st_uid,
            self.file.stat().st_gid,
        )
        self.apply()
        self.assertEqual(self.child_write(self.root), 0)
        future = self.root / "future"
        future.mkdir()
        self.assertEqual(self.child_write(future), 0)
        self.assertEqual(
            before,
            (self.file.read_bytes(), self.file.stat().st_uid, self.file.stat().st_gid),
        )
        self.assertEqual(self.file.stat().st_mode & 7, 0)
        self.assertTrue(self.backup.exists())
        self.assertEqual(self.backup.stat().st_mode & 0o777, 0o600)
        check = self.run_cli()
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertEqual(json.loads(check.stdout)["pending"], 0)

    def test_read_only_check_and_idempotence(self):
        check = self.run_cli()
        self.assertEqual(check.returncode, 1, check.stderr)
        self.assertFalse(self.backup.exists())
        self.assertNotIn(KEY, os.listxattr(self.file))
        self.apply()
        before = os.getxattr(self.file, KEY)
        result = self.run_cli("--apply", "--backup", str(self.base / "second.json"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, os.getxattr(self.file, KEY))

    def test_existing_masked_permissions_are_not_expanded(self):
        entries = [
            (1, 6, 0xFFFFFFFF),
            (2, 7, 20001),
            (4, 4, 0xFFFFFFFF),
            (16, 4, 0xFFFFFFFF),
            (32, 0, 0xFFFFFFFF),
        ]
        os.setxattr(
            self.file,
            KEY,
            struct.pack("<I", 2) + b"".join(struct.pack("<HHI", *e) for e in entries),
        )
        self.apply()
        raw = os.getxattr(self.file, KEY)
        entries = [struct.unpack("<HHI", raw[i : i + 8]) for i in range(4, len(raw), 8)]
        self.assertIn((2, 4, 20001), entries)
        self.assertIn((2, 6, UID), entries)

    def test_root_symlinks_and_root_identity_are_rejected(self):
        link = self.base / "link"
        link.symlink_to(self.root, target_is_directory=True)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(link),
                "--apply",
                "--backup",
                str(self.backup),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(KEY, os.listxattr(self.root))
        self.assertNotEqual(self.run_cli("--uid", "0").returncode, 0)

    def test_inheritance_keeps_restrictive_creation_private(self):
        self.apply()
        previous = os.umask(0o077)
        private = self.root / "private-new.txt"
        try:
            fd = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
            os.close(fd)
        finally:
            os.umask(previous)
        self.assertEqual(private.stat().st_mode & 7, 0)
        raw = os.getxattr(private, KEY)
        acl = [struct.unpack("<HHI", raw[i : i + 8]) for i in range(4, len(raw), 8)]
        self.assertIn((4, 0, 0xFFFFFFFF), acl)
        self.assertEqual(self.child_write(self.root), 0)

    def test_application_owner_gains_effective_write_access(self):
        os.chown(self.root, UID, 1016)
        self.root.chmod(0o500)
        os.chown(self.file, UID, 1016)
        self.file.chmod(0o400)
        self.assertEqual(self.child_write(self.root), errno.EACCES)
        self.apply()
        self.assertEqual(self.child_write(self.root), 0)
        self.assertEqual((self.file.stat().st_mode >> 6) & 7, 6)
        self.assertEqual(self.run_cli().returncode, 0)

    def test_concurrent_mode_change_is_rejected(self):
        code = (
            "import os\nimport runpy\nimport sys\n"
            "script, root, backup, document = sys.argv[1:]\n"
            "real_fsync = os.fsync\n"
            "def change_mode_after_planning(fd):\n"
            "    real_fsync(fd)\n"
            "    os.chmod(document, 0o600)\n"
            "os.fsync = change_mode_after_planning\n"
            "sys.argv = [script, '--root', root, '--apply', '--backup', backup]\n"
            "runpy.run_path(script, run_name='__main__')\n"
        )
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                code,
                str(SCRIPT),
                str(self.root),
                str(self.backup),
                str(self.file),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["error"], "RuntimeError")
        self.assertEqual(
            output["detail"], "Filesystem identity changed; backup retained"
        )
        self.assertNotIn(str(self.root), result.stdout)
        self.assertEqual(self.file.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(KEY, os.listxattr(self.file))
        self.assertEqual(self.file.read_bytes(), b"unchanged synthetic document")
        self.assertTrue(self.backup.exists())


class HmlComposePolicyTests(unittest.TestCase):
    def test_every_persistent_writer_has_explicit_hml_identity(self):
        root = SCRIPT.parents[3]
        services = {}
        for name in ("deploy", "produccion", "celery"):
            path = root / f"docker/compose/docker-compose.{name}.yml"
            for service, body in yaml.safe_load(path.read_text())["services"].items():
                services[service] = {**services.get(service, {}), **body}
        overlay = yaml.safe_load(
            (root / "docker/compose/docker-compose.hml-runtime.yml").read_text()
        )["services"]
        writers = []
        for service, body in services.items():
            if service == "migrator":
                continue
            for volume in body.get("volumes", []):
                if isinstance(volume, str):
                    parts = volume.split(":")
                    target = parts[1] if len(parts) > 1 else parts[0]
                    read_only = len(parts) > 2 and "ro" in parts[2].split(",")
                else:
                    target = volume["target"]
                    read_only = volume.get("read_only", False)
                if target in ("/sisoc/media", "/sisoc/logs", "/beat") and not read_only:
                    writers.append(service)
                    break
        self.assertTrue(writers)
        for service in writers:
            with self.subTest(service=service):
                self.assertEqual(overlay.get(service, {}).get("user"), "10001:1016")


if __name__ == "__main__":
    unittest.main()
