"""Caracterización del generador del mapa de arquitectura.

El generador lee `src/backends/config/settings.py`, `src/backends/config/urls.py` y el template del menú
lateral con regex y AST. Si alguien reformatea esos archivos, el parser no
explota: devuelve datos incompletos en silencio y el mapa pasa a mentir. Estos
tests existen para que eso falle ruidosamente en CI.

No tocan la base ni escriben archivos: sólo ejercitan las funciones de lectura.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke

RAIZ = Path(__file__).resolve().parents[4]
GENERADOR = RAIZ / "src" / "scripts" / "arquitectura" / "generar_mapa.py"


@pytest.fixture(scope="module")
def generador():
    spec = importlib.util.spec_from_file_location("generar_mapa", GENERADOR)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def apps(generador):
    return generador.apps_instaladas()


@pytest.fixture(scope="module")
def menu(generador, apps):
    return generador.menu_lateral(generador.nombres_de_url(apps))


def test_lee_las_apps_propias_de_installed_apps(apps):
    assert {"core", "users", "comedores", "celiaquia", "VAT", "pas"} <= set(apps)
    assert "django" not in apps
    assert "rest_framework" not in apps


def test_toda_app_instalada_tiene_zona_en_el_mapa(generador, apps):
    """Una app nueva sin ubicar cae en 'sin_clasificar' y hay que ubicarla."""
    sin_zona = [app for app in apps if generador.zona_de(app) == "sin_clasificar"]
    assert not sin_zona, (
        "Estas apps no están en ninguna zona del mapa: "
        f"{sin_zona}. Agregalas a ZONAS en {GENERADOR.name}."
    )


def test_mapea_los_prefijos_de_api_a_su_app(generador):
    rutas = generador.rutas_montadas()
    assert "/api/comedores/" in rutas["comedores"]["api"]
    assert "/api/territorial/" in rutas["comedores"]["api"]
    assert "/api/pwa/" in rutas["pwa"]["api"]


def test_distingue_los_planos_de_autenticacion(generador, apps):
    """Token DRF es el plano móvil; API key el server-to-server.

    Una API puede combinarlos: `relevamientos` usa `HasAPIKeyOrToken`, así que
    debe aparecer en los dos. Detectar una sola señal por app ocultaba eso.
    """
    planos = generador.auth_de_apis(apps)
    assert "token" in planos["comedores"]
    assert "token" in planos["pwa"]
    assert planos["ticketera"] == ["api_key"]
    assert planos["VAT"] == ["api_key"]
    assert {"api_key", "token"} <= set(planos["relevamientos"])


def test_separa_fachada_publica_de_import_de_internals(generador, apps):
    aristas, peso = generador.aristas_de_imports(apps)
    por_clave = {(a["src"], a["dst"]): a for a in aristas}

    # dashboard consume comedores sólo por su fachada (contrato declarado).
    assert por_clave[("dashboard", "comedores")]["kind"] == "api"
    assert peso["comedores"]["lineas"] > 0


def test_ve_dependencias_que_import_linter_no_puede_ver(generador, apps):
    """El AST alcanza namespace packages; grimp no.

    `.importlinter` lo documenta como limitación conocida: sólo analiza paquetes
    con `__init__.py`, así que `historial.services` queda fuera de su grafo. Por
    eso el contrato `core-no-domains` no detecta `core/views.py -> historial`,
    que sí viola lo declarado y no está en el baseline de `ignore_imports`.

    Si algún día se corta ese import (o `historial/services/__init__.py` aparece
    y el linter empieza a verlo), este test falla y hay que actualizarlo.
    """
    aristas, _ = generador.aristas_de_imports(apps)
    desde_core = {a["dst"] for a in aristas if a["src"] == "core"}

    assert "historial" in desde_core
    # El resto de lo que importa core es núcleo compartido, no dominio.
    assert desde_core - {"historial"} <= {"users", "iam"}


def test_un_enlace_suelto_no_queda_dentro_del_grupo_anterior(menu):
    """ "Mi cuenta" es hermano de los grupos, no un item de Legajos."""
    grupos_de_mi_cuenta = [
        g["label"] for g in menu for i in g["items"] if i["url_name"] == "mi_cuenta"
    ]
    assert grupos_de_mi_cuenta == ["Mi cuenta"]


def test_el_menu_lateral_se_parsea_completo(menu):
    grupos_con_items = [g for g in menu if g["items"]]
    assert len(grupos_con_items) >= 5

    items = [item for grupo in menu for item in grupo["items"]]
    assert len(items) >= 50

    sin_etiqueta = [i["url_name"] for i in items if not i["label"]]
    assert not sin_etiqueta, f"Items de menú sin etiqueta legible: {sin_etiqueta}"

    sin_app = [i["url_name"] for i in items if not i["app"]]
    assert not sin_app, f"Items de menú sin app resuelta: {sin_app}"


def test_el_menu_conserva_la_jerarquia_de_desplegables(menu):
    """La ruta de un item la dan los <a href="#"> que lo contienen."""
    por_url = {i["url_name"]: i for g in menu for i in g["items"]}

    assert por_url["comedores"]["ruta"] == ["Comedores"]
    assert por_url["admisiones_tecnicos_listar"]["ruta"] == [
        "Comedores",
        "Admisión - Comedores",
    ]
    assert por_url["vat_comision_list"]["ruta"] == ["INET", "Oferta Educativa"]
    assert por_url["pas_panel_control"]["ruta"] == ["PAS"]


def test_el_menu_hereda_los_permisos_de_los_if_que_lo_envuelven(menu):
    por_url = {i["url_name"]: i for g in menu for i in g["items"]}

    assert "comedores.view_comedor" in por_url["comedores"]["permisos"]
    # Hereda el gate del desplegable que lo contiene, no sólo el propio.
    tecnicos = por_url["admisiones_tecnicos_listar"]["permisos"]
    assert "admisiones.view_admision" in tecnicos
    assert "comedores.view_comedor" in tecnicos
    # Fuera de todo {% if %} no debe arrastrar permisos de un bloque anterior.
    assert por_url["mi_cuenta"]["permisos"] == []
    # Un gate por is_superuser no es un permiso de Django, pero es el requisito.
    assert "is_superuser" in por_url["papelera_list"]["permisos"]


def test_el_grafo_no_se_publica_como_estatico(generador):
    """El grafo describe permisos y rutas: Nginx sirve /static/ sin auth.

    Tampoco puede escribirse dentro del checkout: `deploy_refresh.sh` aborta el
    despliegue si encuentra cambios locales en archivos versionados, y el
    generador corre en cada arranque.
    """
    assert not (
        RAIZ / "src" / "backends" / "kernel" / "static" / "arquitectura" / "grafo.json"
    ).exists()
    assert (
        RAIZ / "src" / "backends" / "kernel" / "static" / "arquitectura" / "mapa.js"
    ).exists()
    assert generador.SALIDA_RUNTIME == RAIZ / "var" / "arquitectura"
    assert "/var/" in (RAIZ / ".gitignore").read_text(encoding="utf-8")


def test_el_grafo_no_arrastra_metadata_de_despliegue(generador):
    """El registro de PWA trae ssh_identity y puertos internos; no van al grafo."""
    grafo = generador.construir()
    campos = {clave for pwa in grafo["pwas"] for clave in pwa}

    assert "ssh_identity" not in campos
    assert "port" not in campos
    assert "project" not in campos
    assert {"id", "repository", "canonical_path", "consume"} <= campos


def test_servicios_conservan_duenos_y_prefijos_del_registro(generador, apps):
    lista = generador.servicios(apps + generador.PAQUETES_EXTRA)
    por_id = {s["id"]: s for s in lista}
    registro = generador._registro_backends()
    assert set(por_id) == {"kernel", "sisoc_core", *registro}
    assert "core" in por_id["kernel"]["apps"]
    assert "historial" in por_id["sisoc_core"]["apps"]
    for identificador, spec in registro.items():
        assert por_id[identificador]["service"] == spec["service"]
        assert por_id[identificador]["apps"] == spec["apps"]
        assert por_id[identificador]["rutas"] == [
            "/" + ruta for ruta in spec["url_prefixes"]
        ]
    assert not {"origin_env", "default_origin", "ssh_identity", "port"} & {
        k for s in lista for k in s
    }


def test_frontends_descubre_workspaces_y_proxy_sin_ejecutar_settings(
    generador, monkeypatch, tmp_path
):
    backends = tmp_path / "src" / "backends"
    config = backends / "config"
    config.mkdir(parents=True)
    (config / "settings.py").write_text(
        'raise RuntimeError("No ejecutar settings")\n'
        'FRONTEND_V2_UPSTREAMS = {"nuevo": os.getenv("SECRETO"), "ausente": "x"}\n',
        encoding="utf-8",
    )
    (config / "backends.json").write_text('{"nuevo": {}}', encoding="utf-8")
    for app in ("nuevo", "sin_proxy"):
        carpeta = tmp_path / "src" / "frontends" / "apps" / app
        carpeta.mkdir(parents=True)
        (carpeta / "package.json").write_text(
            json.dumps({"name": "@sisoc/" + app}), encoding="utf-8"
        )
    monkeypatch.setattr(generador, "RAIZ", tmp_path)
    monkeypatch.setattr(generador, "BACKENDS", backends)
    fronts = {f["id"]: f for f in generador.frontends()}
    assert set(fronts) == {"nuevo", "sin_proxy", "ausente"}
    assert fronts["nuevo"]["ruta_web"] == "/v2/nuevo/"
    assert fronts["nuevo"]["backend_asociado"] == "nuevo"
    assert fronts["nuevo"]["certeza_backend"] == "inferido"
    assert fronts["sin_proxy"]["registrado"] is False
    assert fronts["sin_proxy"]["ruta_web"] == ""
    assert fronts["ausente"]["codigo_presente"] is False
    assert fronts["ausente"]["backend_asociado"] == ""
    assert "SECRETO" not in json.dumps(fronts)


def test_registro_roto_no_se_oculta(generador, monkeypatch, tmp_path):
    config = tmp_path / "config"
    config.mkdir()
    (config / "backends.json").write_text("{roto", encoding="utf-8")
    monkeypatch.setattr(generador, "BACKENDS", tmp_path)
    with pytest.raises(json.JSONDecodeError):
        generador._registro_backends()


def test_grafo_completo_tiene_dueno_y_frontends_actuales(generador):
    grafo = generador.construir()
    assert all(m["dueno"] for m in grafo["modulos"])
    assert all(m["ruta_codigo"].startswith("src/backends/") for m in grafo["modulos"])
    fronts = {f["id"]: f for f in grafo["frontends"]}
    assert {"celiaquia", "vpsl"} <= fronts.keys()
    for identificador in ("celiaquia", "vpsl"):
        assert fronts[identificador]["registrado"]
        assert fronts[identificador]["codigo_presente"]
        assert fronts[identificador]["backend_asociado"] == identificador
    assert grafo["totales"]["backends"] == len(generador._registro_backends())
    assert "backend_vpsl" in grafo["asincronia"]["servicios_compose"]
    assert "front_celiaquia" in grafo["asincronia"]["servicios_compose"]


def test_arranque_conserva_captura_completa_de_imagen(generador, monkeypatch, tmp_path):
    """No escanear la imagen recortada ni reemplazar su fecha por la del arranque."""
    salida = tmp_path / "var" / "arquitectura"
    monkeypatch.setattr(generador, "RAIZ", tmp_path)
    monkeypatch.setattr(generador, "SALIDA_RUNTIME", salida)
    captura = {
        "generado": "2026-10-06T10:00:00-03:00",
        "servicios": [{"id": "vpsl"}],
        "frontends": [{"id": "vpsl"}],
        "totales": {
            "apps": 1,
            "aristas": 0,
            "aristas_api": 0,
            "aristas_internals": 0,
            "items_menu": 0,
            "lineas": 0,
        },
    }
    monkeypatch.setattr(generador, "construir", lambda: captura.copy())
    monkeypatch.setattr(sys, "argv", ["generar_mapa.py", "--imagen"])
    generador.main()
    esperado = json.loads((salida / "grafo.json").read_text("utf-8"))
    assert esperado["fuente"] == "imagen"

    def no_escanear():
        raise AssertionError("El core no tiene el código completo")

    monkeypatch.setattr(generador, "construir", no_escanear)
    monkeypatch.setattr(sys, "argv", ["generar_mapa.py"])
    (salida / "grafo.json").write_text("{}", encoding="utf-8")
    generador.main()
    assert json.loads((salida / "grafo.json").read_text("utf-8")) == esperado

    # Un --imagen ejecutado a mano en desarrollo no debe congelar el mapa:
    # si hay código completo, el siguiente arranque vuelve a leer el checkout.
    (tmp_path / "src" / "frontends" / "apps").mkdir(parents=True)
    backends = tmp_path / "src" / "backends"
    (backends / "nuevo").mkdir(parents=True)
    monkeypatch.setattr(generador, "BACKENDS", backends)
    monkeypatch.setattr(generador, "_registro_backends", lambda: {"nuevo": {}})
    captura_nueva = {**captura, "generado": "2026-10-07T10:00:00-03:00"}
    monkeypatch.setattr(generador, "construir", lambda: captura_nueva)
    generador.main()
    assert json.loads((salida / "grafo.json").read_text("utf-8"))["generado"] == (
        captura_nueva["generado"]
    )


def test_imagen_genera_mapa_antes_de_recortar_codigo():
    dockerfile = (RAIZ / "docker" / "django" / "Dockerfile").read_text("utf-8")
    assert dockerfile.index("generar_mapa.py --imagen") < dockerfile.index(
        "RUN rm -rf /repo/src/frontends"
    )
    assert dockerfile.index("generar_mapa.py --imagen") < dockerfile.index(
        "FROM source AS core_source"
    )
    assert "var" in (RAIZ / ".dockerignore").read_text("utf-8").splitlines()
