"""Standalone synthetic-runtime contract; run with the pinned Django image."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("insumos_visual_runtime.py")


class VisualRuntimeTests(unittest.TestCase):
    def test_prepare_refuses_nonempty_output_without_changing_it(self):
        root = Path(tempfile.mkdtemp(prefix="sisoc-insumos-visual-test-"))
        sentinel = root / "unrelated.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "prepare",
                "--root",
                str(root),
                "--manifest",
                str(root / "missing.json"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("empty scratch directory", result.stderr)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")
        self.assertEqual(sorted(p.name for p in root.iterdir()), ["unrelated.txt"])

    def test_prepare_materializes_independent_synthetic_fixture_and_real_http(self):
        root = Path(tempfile.mkdtemp(prefix="sisoc-insumos-visual-test-"))
        manifest_dir = Path(tempfile.mkdtemp(prefix="sisoc-insumos-manifest-"))
        manifest = manifest_dir / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "fixtures": {
                        "profile_default": {
                            "acceso_web": True,
                            "must_change_password": False,
                            "needs_profile_confirmation": False,
                        },
                        "roles": {
                            "consulta": {
                                "permissions": ["insumos.view_insumo"],
                                "display": "Consulta",
                            },
                            "gestion_categorias": {
                                "permissions": [
                                    "insumos.view_insumocategoria",
                                    "insumos.add_insumocategoria",
                                    "insumos.change_insumocategoria",
                                    "insumos.delete_insumocategoria",
                                ],
                                "display": "Category management",
                            },
                            "sin_permiso": {
                                "permissions": [],
                                "display": "Sin permiso",
                            },
                        },
                        "program": {
                            "ref": "programa_prueba",
                            "name": "Programa Prueba Visual",
                            "active": True,
                        },
                        "categories": [
                            {
                                "ref": "cat_a",
                                "name": "Manuales A",
                                "active": True,
                                "order": 1,
                                "program_ref": "programa_prueba",
                            }
                        ],
                        "items": [
                            {
                                "ref": "insumo_001",
                                "title": "Manual de prueba 01",
                                "description": "Contenido sintetico",
                                "category_ref": "cat_a",
                                "program_ref": "programa_prueba",
                                "active": True,
                                "created_at": "2026-10-27T00:01:00-03:00",
                                "creator_role": "consulta",
                                "file": {
                                    "name": "manual-prueba-01.pdf",
                                    "content_ref": "pdf_sintetico_minimo",
                                    "present_in_storage": True,
                                },
                            }
                        ],
                    }
                }
            ),
            encoding="utf-8",
        )
        approved = json.loads(manifest.read_text(encoding="utf-8"))
        approved["fixtures"]["items"].append(
            {
                **approved["fixtures"]["items"][0],
                "ref": "insumo_024",
                "title": "Insumo sin creador",
                "creator_role": None,
                "file": {
                    "name": "sin-creador.pdf",
                    "content_ref": "pdf_sintetico_minimo",
                    "present_in_storage": True,
                },
            }
        )
        manifest.write_text(json.dumps(approved), encoding="utf-8")
        command = [
            sys.executable,
            str(SCRIPT),
            "prepare",
            "--root",
            str(root),
            "--manifest",
            str(manifest),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr[-3000:])
        refs = json.loads((root / "fixture-refs.json").read_text(encoding="utf-8"))
        self.assertIn("gestion_categorias", refs["users"])
        self.assertEqual(set(refs["items"]), {"insumo_001", "insumo_024"})
        self.assertEqual(len(list((root / "media").rglob("*.pdf"))), 2)
        before = (root / "visual.sqlite3").read_bytes()
        rejected = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(rejected.returncode, 2)
        self.assertEqual((root / "visual.sqlite3").read_bytes(), before)
        probe = r"""
import json, socket, sys
sys.path.insert(0, sys.argv[1])
from insumos_visual_runtime import application
application(sys.argv[2])
from django.conf import settings
from django.test import Client
from insumos.models import Insumo
assert Insumo.objects.get(titulo="Insumo sin creador").usuario_creacion_id is None
c = Client(HTTP_HOST="localhost")
assert c.get("/insumos/").status_code == 403
assert c.login(username="visual_consulta", password="synthetic-visual-only")
r = c.get("/insumos/")
assert r.status_code == 200 and b"Manual de prueba 01" in r.content
assert c.get("/insumos/crear").status_code == 403
assert c.get("/api/web/session/").json()["access"]["state"] == "ready"
c.logout()
assert c.login(username="visual_gestion_categorias", password="synthetic-visual-only")
assert c.get("/insumos/categorias/").status_code == 200
assert c.get("/api/web/insumos/categorias/").status_code == 200
assert c.get("/insumos/").status_code == 403
assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"
assert str(settings.MEDIA_ROOT).startswith(sys.argv[2])
try:
    socket.socket().connect(("127.0.0.1", 9))
except PermissionError:
    pass
else:
    raise AssertionError("outgoing sockets must be blocked")
print("synthetic-http-ok")
"""
        checked = subprocess.run(
            [sys.executable, "-c", probe, str(SCRIPT.parent), str(root)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr[-3000:])
        self.assertIn("synthetic-http-ok", checked.stdout)


if __name__ == "__main__":
    unittest.main()
