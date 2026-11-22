"""Local synthetic INS-A runtime. Never use against a deployment or real data."""

import argparse
from datetime import datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile


def scratch_root(value, *, preparing=False):
    """Require a dedicated system-temp directory, never a repository or symlink."""
    original = Path(value)
    root = original.resolve(strict=True)
    temporary = Path(tempfile.gettempdir()).resolve()
    if root.is_relative_to(Path(__file__).resolve().parents[3]):
        raise ValueError("Scratch directory must be outside the repository")
    if (
        original.is_symlink()
        or not root.is_dir()
        or root.parent != temporary
        or not root.name.startswith("sisoc-insumos-visual-")
    ):
        raise ValueError("Use a dedicated empty scratch directory under system temp")
    if preparing and any(root.iterdir()):
        raise ValueError("Use a dedicated empty scratch directory under system temp")
    return root


MARKER = "synthetic-insumos-visual-v1"
PDF = b"%PDF-1.4\n% Synthetic INS-A visual fixture only\n%%EOF\n"


class NoMigrations(dict):
    """Build disposable test schema, never apply deployment migrations."""

    def __contains__(self, key):
        return True

    def __getitem__(self, key):
        return None


def _deny_connect(*_args, **_kwargs):
    raise PermissionError("Synthetic visual runtime forbids outgoing connections")


def application(value):
    """Load the real WSGI app using only scratch state and a synthetic env."""
    root = scratch_root(value)
    if (root / ".synthetic-runtime").read_text(encoding="utf-8") != MARKER:
        raise ValueError("Not a prepared synthetic visual runtime")
    for name in ("visual.sqlite3", "media", "logs", "tmp"):
        if (root / name).is_symlink():
            raise ValueError("Synthetic runtime paths must not be symlinks")
    # Clear, rather than inspect or reuse, inherited credentials and destinations.
    os.environ.clear()
    os.environ.update(
        {
            "PYTHON_DOTENV_DISABLED": "1",
            "ENVIRONMENT": "dev",
            "DJANGO_SECRET_KEY": "synthetic-visual-only-not-for-deployment",
            "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1",
            "GESTIONAR_INTEGRATION_ENABLED": "False",
            "PAS_MONTHLY_ENABLED": "False",
            "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
            "LOG_DIR": str(root / "logs"),
            "TMPDIR": str(root / "tmp"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    socket.socket.connect = _deny_connect
    socket.socket.connect_ex = _deny_connect
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backends"))
    from django.conf import settings

    if settings.configured:
        raise ValueError("Run visual tooling in a fresh standalone Python process")
    base = importlib.import_module("config.settings_all")
    config = {key: getattr(base, key) for key in dir(base) if key.isupper()}
    config.update(
        {
            "DATABASES": {
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": root / "visual.sqlite3",
                }
            },
            "MEDIA_ROOT": root / "media",
            "STATIC_ROOT": root / "static",
            "MIGRATION_MODULES": NoMigrations(),
            "SENTRY_DSN": "",
            "SENTRY_REPLAY_ENABLED": False,
            "SENTRY_ERROR_SAMPLE_RATE": 0.0,
            "SISOC_BACKENDS": {},
            "CELERY_BROKER_URL": "memory://",
            "CELERY_TASK_ALWAYS_EAGER": False,
            "CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP": False,
            "CACHES": {
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": str(root),
                }
            },
        }
    )
    settings.configure(**config)
    from django.core.wsgi import get_wsgi_application
    from django.contrib.staticfiles.handlers import StaticFilesHandler

    return StaticFilesHandler(get_wsgi_application())


def prepare(value, manifest_path):
    """Create one fresh per-case dataset; existing state is never reset/deleted."""
    root = scratch_root(value, preparing=True)
    manifest_bytes = Path(manifest_path).read_bytes()
    fixtures = json.loads(manifest_bytes)["fixtures"]
    (root / ".synthetic-runtime").write_text(MARKER, encoding="utf-8")
    for name in ("media", "logs", "tmp"):
        (root / name).mkdir()
    application(root)
    from django.core.management import call_command
    from django.db import transaction

    call_command("migrate", run_syncdb=True, interactive=False, verbosity=0)
    refs = {"users": {}, "programs": {}, "categories": {}, "items": {}}
    with transaction.atomic():
        _seed_users(fixtures, refs)
        _seed_read_items(fixtures, refs)
    refs["manifest_sha256"] = hashlib.sha256(manifest_bytes).hexdigest()
    refs["file_sha256"] = hashlib.sha256(PDF).hexdigest()
    (root / "fixture-refs.json").write_text(
        json.dumps(refs, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print("Synthetic INS-A read fixture prepared; no visual baseline accepted")


def _seed_users(fixtures, refs):
    from django.contrib.auth.models import Permission, User

    for role, spec in fixtures["roles"].items():
        user = User.objects.create_user(
            username=f"visual_{role}",
            password="synthetic-visual-only",
            first_name=spec["display"],
        )
        profile = user.profile
        profile.acceso_web = True
        profile.must_change_password = False
        profile.needs_profile_confirmation = False
        profile.rol = spec["display"]
        profile.save()
        for permission in spec["permissions"]:
            app, code = permission.split(".", 1)
            user.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label=app,
                    codename=code,
                )
            )
        refs["users"][role] = user.pk


def _seed_read_items(fixtures, refs):
    from django.core.files.base import ContentFile
    from core.models import Programa
    from insumos.models import Insumo, InsumoCategoria

    spec = fixtures["program"]
    program = Programa.objects.create(nombre=spec["name"], estado=spec["active"])
    refs["programs"][spec["ref"]] = program.pk
    for spec in fixtures["categories"]:
        category = InsumoCategoria.objects.create(
            programa_id=refs["programs"][spec["program_ref"]],
            nombre=spec["name"],
            activo=spec["active"],
            orden=spec["order"],
        )
        refs["categories"][spec["ref"]] = category.pk
    for spec in fixtures["items"]:
        file_spec = spec["file"]
        if file_spec["content_ref"] != "pdf_sintetico_minimo":
            raise ValueError("Unknown synthetic file reference")
        filename = file_spec["name"]
        if Path(filename).name != filename or "/" in filename or "\\" in filename:
            raise ValueError("Synthetic file name must be a basename")
        item = Insumo(
            programa_id=refs["programs"][spec["program_ref"]],
            categoria_id=(
                refs["categories"][spec["category_ref"]]
                if spec["category_ref"] is not None
                else None
            ),
            titulo=spec["title"],
            descripcion=spec["description"],
            activo=spec["active"],
            usuario_creacion_id=(
                refs["users"][spec["creator_role"]]
                if spec["creator_role"] is not None
                else None
            ),
        )
        item.archivo.save(filename, ContentFile(PDF), save=False)
        item.save()
        if not file_spec["present_in_storage"]:
            item.archivo.storage.delete(item.archivo.name)
        timestamp = datetime.fromisoformat(spec["created_at"])
        Insumo.objects.filter(pk=item.pk).update(
            fecha_creacion=timestamp,
            fecha_actualizacion=timestamp,
        )
        refs["items"][spec["ref"]] = item.pk


def serve(value, port, container_listen=False):
    """Serve loopback, or a container port explicitly published on host loopback."""
    from wsgiref.simple_server import make_server

    if not 1024 <= port <= 65535:
        raise ValueError("Use a nonprivileged local port")
    if container_listen and not Path("/.dockerenv").is_file():
        raise ValueError("--container-listen is only available inside Docker")
    app = application(value)
    with make_server(
        "0.0.0.0" if container_listen else "127.0.0.1", port, app
    ) as server:
        print(f"Synthetic visual runtime: http://127.0.0.1:{port}/insumos/", flush=True)
        server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "serve"])
    parser.add_argument("--root", required=True, help="Dedicated system-temp directory")
    parser.add_argument(
        "--manifest", help="Approved synthetic INS-A manifest (prepare)"
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--container-listen",
        action="store_true",
        help="Docker only: require docker -p 127.0.0.1:HOST:PORT, never a public bind",
    )
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            scratch_root(args.root, preparing=True)
            if not args.manifest:
                raise ValueError("prepare requires --manifest")
            prepare(args.root, args.manifest)
        else:
            serve(args.root, args.port, args.container_listen)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
