"""Control de calidad de PR (src/scripts/ci/quality_gate.py)."""

import json

from scripts.ci import quality_gate

DIFF = """\
diff --git a/src/backends/pas/pas/services/x.py b/src/backends/pas/pas/services/x.py
--- a/src/backends/pas/pas/services/x.py
+++ b/src/backends/pas/pas/services/x.py
@@ -10,0 +11,3 @@ def algo():
+    a = 1
+    b = 2
+    return a + b
@@ -40 +43 @@ def otro():
-    return 0
+    return 1
diff --git a/src/backends/pas/pas/viejo.py b/src/backends/pas/pas/viejo.py
--- a/src/backends/pas/pas/viejo.py
+++ /dev/null
@@ -1,2 +0,0 @@
-x = 1
-y = 2
"""

COVERAGE = """\
<?xml version="1.0" ?>
<coverage><packages><package><classes>
  <class filename="src/backends/pas/pas/services/x.py">
    <lines>
      <line number="11" hits="1"/>
      <line number="12" hits="1"/>
      <line number="13" hits="0"/>
      <line number="43" hits="4"/>
    </lines>
  </class>
</classes></package></packages></coverage>
"""


def test_lineas_cambiadas_lee_hunks_y_omite_borrados():
    assert quality_gate.lineas_cambiadas(DIFF) == {
        "src/backends/pas/pas/services/x.py": {11, 12, 13, 43},
    }


def test_cobertura_y_evaluacion_de_lineas_cambiadas(tmp_path):
    xml = tmp_path / "coverage.xml"
    xml.write_text(COVERAGE, encoding="utf-8")

    medidas = quality_gate.cobertura(xml)

    assert quality_gate.evaluar(quality_gate.lineas_cambiadas(DIFF), medidas) == (
        3,
        4,
        {"src/backends/pas/pas/services/x.py": [13]},
    )


def test_evaluar_ignora_lineas_no_ejecutables_y_codigo_que_no_es_de_app():
    medidas = {"src/backends/pas/pas/a.py": {5: 1}}
    cambios = {
        "src/backends/pas/pas/a.py": {4, 5},  # 4: comentario o línea en blanco
        "src/backends/pas/tests/test_a.py": {1},
        "src/backends/pas/pas/migrations/0001_initial.py": {1},
        "docs/x.md": {1},
    }

    assert quality_gate.evaluar(cambios, medidas) == (1, 1, {})


def test_archivo_sin_datos_de_cobertura_cuenta_como_no_cubierto():
    cambios = {"src/backends/pas/pas/nuevo.py": {1, 2}}

    assert quality_gate.evaluar(cambios, {}) == (
        0,
        2,
        {"src/backends/pas/pas/nuevo.py": [1, 2]},
    )


def test_revisar_falla_si_hay_codigo_de_app_sin_tests():
    archivos = ["src/backends/pas/pas/services/x.py", "docs/registro/x.md"]
    cambios = {"src/backends/pas/pas/services/x.py": {1}}
    medidas = {"src/backends/pas/pas/services/x.py": {1: 1}}

    problemas = quality_gate.revisar(archivos, cambios, medidas)

    assert len(problemas) == 1
    assert problemas[0].startswith("Se modifica código de una app sin tocar")


def test_revisar_falla_por_cobertura_bajo_el_umbral():
    archivos = ["src/backends/pas/pas/a.py", "src/backends/pas/tests/test_a.py"]
    cambios = {"src/backends/pas/pas/a.py": {1, 2, 3, 4, 5}}
    medidas = {"src/backends/pas/pas/a.py": {1: 1, 2: 1, 3: 1, 4: 0, 5: 1}}

    assert quality_gate.revisar(archivos, cambios, medidas) == []
    assert quality_gate.revisar(archivos, cambios, medidas, umbral=90)[0].startswith(
        "Cobertura de líneas cambiadas 80.0% (4/5), mínimo 90%."
    )


def test_revisar_acepta_cambios_sin_codigo_de_app():
    archivos = ["docs/ia/TESTING.md", "src/backends/pas/pas/migrations/0002_x.py"]

    assert quality_gate.revisar(archivos, {}, {}) == []


def test_clasificacion_de_tests_y_zonas_sensibles():
    assert quality_gate.es_test("src/backends/pas/tests/test_a.py")
    assert quality_gate.es_test("src/backends/comedores/tests/js/x.test.js")
    assert not quality_gate.es_test("src/backends/pas/pas/services/x.py")

    sensibles = [
        ".github/workflows/tests.yml",
        "src/backends/kernel/users/models.py",
        "src/backends/pas/pas/migrations/0002_x.py",
        "src/backends/comedores/pwa/api_permissions.py",
        "src/backends/config/settings.py",
        "requirements/base.txt",
    ]
    assert all(quality_gate.es_sensible(ruta) for ruta in sensibles)
    assert not quality_gate.es_sensible("src/backends/pas/pas/views.py")
    assert not quality_gate.es_sensible("docs/ia/TESTING.md")
    assert not quality_gate.es_sensible("src/backends/kernel/tests/test_x.py")


def test_gate_respeta_el_label_de_excepcion(monkeypatch, tmp_path):
    xml = tmp_path / "coverage.xml"
    xml.write_text(COVERAGE, encoding="utf-8")
    monkeypatch.setattr(quality_gate, "git", lambda *args: "")
    monkeypatch.setattr(
        quality_gate, "archivos_cambiados", lambda: ["src/backends/pas/pas/a.py"]
    )
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))

    monkeypatch.setattr(quality_gate, "labels_del_pr", set)
    assert quality_gate.gate(xml) == 1

    monkeypatch.setattr(quality_gate, "labels_del_pr", lambda: {quality_gate.EXCEPCION})
    assert quality_gate.gate(xml) == 0
    assert "excepción aprobada" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def test_labels_del_pr_sin_evento_no_consulta_la_api(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    assert quality_gate.labels_del_pr() == set()

    evento = tmp_path / "event.json"
    evento.write_text(json.dumps({"push": {}}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(evento))
    assert quality_gate.labels_del_pr() == set()
