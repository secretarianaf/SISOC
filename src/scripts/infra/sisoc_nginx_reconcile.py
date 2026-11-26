#!/usr/bin/python3 -I
"""Privileged Nginx reconciler; install root-owned outside the checkout.

Input is bounded JSON on stdin containing base64 `site` and `pwa` bytes. The
root-owned per-environment manifest, never the runner, approves both hashes.
"""

import base64
import binascii
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import time

MANIFESTS = {
    "qa": Path("/etc/sisoc-nginx/qa.json"),
    "production": Path("/etc/sisoc-nginx/production.json"),
    "homologacion": Path("/etc/sisoc-nginx/homologacion.json"),
}
TARGETS = {
    "qa": (
        Path("/etc/nginx/sites-available/staging.conf"),
        Path("/etc/nginx/snippets/sisoc-pwas.conf"),
    ),
    "production": (
        Path("/etc/nginx/sites-available/sisoc"),
        Path("/etc/nginx/snippets/sisoc-pwas.conf"),
    ),
    "homologacion": (
        Path("/etc/nginx/sites-available/sisoc"),
        Path("/etc/nginx/snippets/sisoc-pwas.conf"),
    ),
}
MARKER_PATH = Path("/etc/nginx/snippets/sisoc-package-marker.conf")
BACKUP_DIR = Path("/var/backups/sisoc/nginx")
LOCK_PATH = Path("/run/sisoc-nginx/reconcile.lock")
LIMIT = 1024 * 1024


def package_marker(site, pwa):
    return hashlib.sha256(
        b"sisoc-nginx-package-v1\0"
        + hashlib.sha256(site).digest()
        + hashlib.sha256(pwa).digest()
    ).hexdigest()


def marker_content(marker):
    if not re.fullmatch(r"[0-9a-f]{64}", marker):
        raise ValueError("invalid marker")
    return ('add_header X-SISOC-Nginx-Package "' + marker + '" always;\n').encode(
        "ascii"
    )


def _trusted_directory(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("relative path rejected")
    for part in (path, *path.parents):
        info = part.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise PermissionError("untrusted directory")


def _read_regular(path, max_size=LIMIT):
    _trusted_directory(path.parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != 0
            or info.st_mode & 0o022
            or info.st_nlink != 1
            or info.st_size > max_size
        ):
            raise PermissionError("untrusted file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(max_size + 1)
        if len(data) > max_size:
            raise ValueError("file too large")
        return data, stat.S_IMODE(info.st_mode)
    finally:
        os.close(fd)


def _atomic_write(path, content, mode=0o644):
    _trusted_directory(path.parent)
    fd, name = tempfile.mkstemp(prefix=".sisoc-nginx-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def current_marker():
    content, _ = _read_regular(MARKER_PATH)
    match = re.fullmatch(
        rb'add_header X-SISOC-Nginx-Package "([0-9a-f]{64})" always;\n', content
    )
    if not match:
        raise ValueError("invalid installed marker")
    return match.group(1).decode("ascii")


def _includes(site, pwa):
    # Conservative grammar: reject escapes and inline comments instead of
    # attempting to interpret ambiguous Nginx configuration syntax.
    def tokens(data):
        if b"\\" in data or b"\x00" in data:
            raise ValueError("ambiguous Nginx syntax")
        lines = []
        for line in data.splitlines():
            if line.lstrip().startswith(b"#"):
                continue
            if b"#" in line:
                raise ValueError("inline comments unsupported")
            lines.append(line)
        source = b"\n".join(lines)
        tokens = re.findall(rb'"[^"\\]*"|\'[^\'\\]*\'|[{};]|[^\s{};"\']+', source)
        found = []
        for index, token in enumerate(tokens):
            if token.strip(b"\"'") == b"include":
                if index + 2 >= len(tokens) or tokens[index + 2] != b";":
                    raise ValueError("ambiguous include")
                found.append(tokens[index + 1].strip(b"\"'"))
        return found

    includes = [x.strip() for x in tokens(site)]
    if sorted(includes) != sorted(
        [
            b"/etc/nginx/snippets/sisoc-pwas.conf",
            b"/etc/nginx/snippets/sisoc-package-marker.conf",
            b"/etc/nginx/snippets/sisoc-package-marker.conf",
        ]
    ) or tokens(pwa):
        raise ValueError("unapproved include")


def _validate_probe(host, port, scheme):
    if not isinstance(host, str) or len(host) > 253:
        raise ValueError("invalid trusted HML probe host")
    if (
        not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", host)
        or ".." in host
    ):
        raise ValueError("invalid trusted HML probe host")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("invalid trusted HML probe port")
    if scheme not in ("http", "https"):
        raise ValueError("invalid trusted HML probe scheme")


class RealOps:
    def _run(self, command, timeout=30):
        return subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
        )

    def validate(self):
        self._run(["/usr/sbin/nginx", "-t"])

    def reload(self):
        self._run(["/usr/bin/systemctl", "reload", "nginx"])

    def graph_contains_managed_files(self, environment):
        try:
            output = self._run(["/usr/sbin/nginx", "-T"]).stdout
            filenames = re.findall(
                rb"^# configuration file ([^\r\n]+):\r?$", output, re.MULTILINE
            )
            loaded = {
                Path(os.fsdecode(path)).resolve(strict=True) for path in filenames
            }
            return all(
                path.resolve(strict=True) in loaded
                for path in (*TARGETS[environment], MARKER_PATH)
            )
        except (KeyError, OSError, ValueError, subprocess.SubprocessError):
            return False

    def smoke(self, environment, marker):
        socket = Path("/run/sisoc-nginx/probe.sock")
        private = [
            "/usr/bin/curl",
            "--noproxy",
            "*",
            "--silent",
            "--show-error",
            "--max-time",
            "3",
            "--unix-socket",
            str(socket),
            "--dump-header",
            "-",
            "--output",
            "/dev/null",
            "--write-out",
            "\n%{http_code}",
            "http://localhost/__sisoc_nginx_package",
        ]
        if environment == "qa":
            public = [
                "/usr/bin/curl",
                "--noproxy",
                "*",
                "--silent",
                "--show-error",
                "--max-time",
                "3",
                "-H",
                "Host: localhost",
                "--dump-header",
                "-",
                "--output",
                "/dev/null",
                "--write-out",
                "\n%{http_code}",
                "http://127.0.0.1/media/centrodefamilia/cargas_masivas/",
            ]
        else:
            if environment == "production":
                host, port, scheme = "sisoc.secretarianaf.gob.ar", 443, "https"
            else:
                manifest = json.loads(_read_regular(MANIFESTS[environment], 4096)[0])
                host, port, scheme = (
                    manifest["probe_host"],
                    manifest["probe_port"],
                    manifest["probe_scheme"],
                )
                _validate_probe(host, port, scheme)
            public = [
                "/usr/bin/curl",
                "--noproxy",
                "*",
                "--silent",
                "--show-error",
                "--max-time",
                "3",
                "--resolve",
                f"{host}:{port}:127.0.0.1",
                "--dump-header",
                "-",
                "--output",
                "/dev/null",
                "--write-out",
                "\n%{http_code}",
                f"{scheme}://{host}:{port}/media/centrodefamilia/cargas_masivas/",
            ]

        def matches(command):
            output = self._run(command, timeout=5).stdout.decode("latin1")
            headers, status = output.rsplit("\n", 1)
            found = [
                line.split(":", 1)[1].strip()
                for line in headers.splitlines()
                if line.lower().startswith("x-sisoc-nginx-package:")
            ]
            return status == "404" and found == [marker]

        for _ in range(10):
            try:
                _trusted_directory(socket.parent)
                parent = socket.parent.lstat()
                info = socket.lstat()
                trusted = (
                    not parent.st_mode & 0o077
                    and stat.S_ISSOCK(info.st_mode)
                    and info.st_uid == 0
                )
                if (
                    trusted
                    and self.graph_contains_managed_files(environment)
                    and matches(private)
                    and matches(public)
                ):
                    return True
            except (ValueError, OSError, subprocess.SubprocessError):
                pass
            time.sleep(0.2)
        return False


# The complete transaction stays together so rollback covers every mutation.
# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def reconcile(environment, raw, ops):
    if os.geteuid() != 0 or environment not in MANIFESTS or environment not in TARGETS:
        raise PermissionError("unsupported environment or caller")
    if len(raw) > 3 * LIMIT:
        raise ValueError("package too large")
    package = json.loads(raw)
    if not isinstance(package, dict) or set(package) != {"site", "pwa"}:
        raise ValueError("invalid package fields")
    try:
        site, pwa = (
            base64.b64decode(package[key], validate=True) for key in ("site", "pwa")
        )
    except (TypeError, binascii.Error) as exc:
        raise ValueError("invalid package encoding") from exc
    if len(site) > LIMIT or len(pwa) > LIMIT:
        raise ValueError("package too large")
    _includes(site, pwa)
    _trusted_directory(LOCK_PATH.parent)
    lockfd = os.open(
        LOCK_PATH, os.O_CREAT | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600
    )
    try:
        info = os.fstat(lockfd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != 0
            or info.st_mode & 0o077
            or info.st_nlink != 1
        ):
            raise PermissionError("untrusted lock")
        fcntl.flock(lockfd, fcntl.LOCK_EX)
        manifest = json.loads(_read_regular(MANIFESTS[environment], 4096)[0])
        expected = {
            "version": 1,
            "environment": environment,
            "site_sha256": hashlib.sha256(site).hexdigest(),
            "pwa_sha256": hashlib.sha256(pwa).hexdigest(),
        }
        if environment == "homologacion" and isinstance(manifest, dict):
            host, port, scheme = (
                manifest.get("probe_host"),
                manifest.get("probe_port"),
                manifest.get("probe_scheme"),
            )
            _validate_probe(host, port, scheme)
            expected.update(probe_host=host, probe_port=port, probe_scheme=scheme)
        if (
            not isinstance(manifest, dict)
            or (
                not isinstance(manifest.get("version"), int)
                or isinstance(manifest.get("version"), bool)
            )
            or manifest != expected
        ):
            raise PermissionError("package not approved")
        paths = (*TARGETS[environment], MARKER_PATH)
        previous = [_read_regular(path) for path in paths]
        desired_marker = package_marker(site, pwa)
        desired = (site, pwa, marker_content(desired_marker))
        previous_marker = current_marker()
        if all(
            before[0] == after for before, after in zip(previous, desired)
        ) and ops.smoke(environment, desired_marker):
            return "unchanged"
        _trusted_directory(BACKUP_DIR)
        backup = Path(tempfile.mkdtemp(prefix=environment + "-", dir=BACKUP_DIR))
        os.chmod(backup, 0o700)
        for index, (data, mode) in enumerate(previous):
            _atomic_write(backup / str(index), data, mode)
        try:
            for path, data, before in zip(paths, desired, previous):
                if data != before[0]:
                    _atomic_write(path, data, before[1])
            ops.validate()
            ops.reload()
            if not ops.smoke(environment, desired_marker):
                raise RuntimeError("effective configuration not verified")
        except BaseException as original:
            try:
                for path, (data, mode) in zip(paths, previous):
                    _atomic_write(path, data, mode)
                ops.validate()
                ops.reload()
                if not ops.smoke(environment, previous_marker):
                    raise RuntimeError(
                        "restored configuration not verified"
                    ) from original
            except BaseException as rollback:
                raise RuntimeError("reconciliation and rollback failed") from rollback
            raise RuntimeError(
                "reconciliation failed; previous configuration restored"
            ) from original
        return "updated"
    finally:
        os.close(lockfd)


def main():
    # Reject execution from runner-writable checkouts, even via an allowed wrapper.
    _read_regular(Path(__file__))
    if len(sys.argv) != 2:
        raise ValueError("expected exactly one fixed environment")
    data = sys.stdin.buffer.read(3 * LIMIT + 1)
    print("[sisoc-nginx] " + reconcile(sys.argv[1], data, RealOps()))


if __name__ == "__main__":
    try:
        main()
    except (
        ValueError,
        PermissionError,
        OSError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as exc:
        print("[sisoc-nginx] ERROR: " + str(exc), file=sys.stderr)
        sys.exit(1)
