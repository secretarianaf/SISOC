"""Activación por flag de las entradas React (``core.react_activation``).

Pasa por las URLconf reales (``config.urls_all`` y los ``*_runtime.urls``),
recargadas con el flag, como las arma el servidor.
"""

import re
import uuid
from contextlib import contextmanager
from importlib import import_module, reload

import pytest
from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.urls import Resolver404, clear_url_caches, resolve, set_urlconf

from config.backends import load_backends_registry
from config.settings import parse_react_verticales
from core.react_activation import REGISTRO, claves_activas, react_preview_patterns

pytestmark = pytest.mark.django_db

MARCA = '<div id="react-root-activacion"></div>'
INDEX = (
    '<!doctype html><html><head><script type="module" '
    'src="/v2/sisoc/assets/app-1.js"></script></head>'
    f"<body>{MARCA}</body></html>"
)
MODULOS = [f"{v}_runtime.urls" for v in load_backends_registry()] + [
    "config.urls",
    "config.urls_all",
]


def _recargar():
    for nombre in MODULOS:
        reload(import_module(nombre))
    clear_url_caches()
    set_urlconf(None)


@contextmanager
def _flag(activas, build, pas_build=None):
    with override_settings(
        REACT_VERTICALES_ACTIVAS=frozenset(activas),
        SISOC_REACT_BUILD_DIR=str(build),
        SISOC_REACT_PAS_BUILD_DIR=str(pas_build or build),
        ROOT_URLCONF="config.urls_all",
    ):
        _recargar()
        try:
            yield
        finally:
            pass
    _recargar()


@pytest.fixture(name="build")
def build_fixture(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    (tmp_path / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    return tmp_path


def _cliente(permisos=("view_paspersona", "add_paspersona")):
    from django.contrib.auth.models import Permission

    user = User.objects.create_user(f"u{uuid.uuid4().hex[:8]}")
    for codigo in permisos:
        user.user_permissions.add(Permission.objects.get(codename=codigo))
    cliente = Client()
    cliente.force_login(user)
    return cliente


def test_sin_flag_las_urls_son_las_nativas(build):
    with _flag((), build):
        assert react_preview_patterns("pas", "cdi", "core") == []
        respuesta = _cliente().get("/pas/listar")
        assert respuesta.status_code == 200
        assert MARCA not in respuesta.content.decode()
        assert "Entry" not in repr(resolve("/pas/listar").func)


def test_sin_flag_el_post_va_a_la_vista_nativa(build):
    with _flag((), build):
        respuesta = _cliente().post("/pas/crear", {})
        assert respuesta.status_code == 200
        assert MARCA not in respuesta.content.decode()


def test_flag_pas_sirve_react_con_las_guardas_nativas(build):
    with _flag({"pas"}, build):
        respuesta = _cliente().get("/pas/listar")
        assert respuesta.status_code == 200
        assert MARCA in respuesta.content.decode()
        assert "/pas/react/assets/app-1.js" in respuesta.content.decode()
        anonimo = Client().get("/pas/listar")
        assert anonimo.status_code in (302, 403)
        assert MARCA not in anonimo.content.decode()
        assert _cliente(()).get("/pas/listar").status_code == 403
        # Un titular inexistente sigue siendo el 404 nativo.
        assert _cliente().get("/pas/999999").status_code == 404


def test_flag_pas_no_tapa_post_ni_rutas_no_migradas(build):
    with _flag({"pas"}, build):
        cliente = _cliente()
        post = cliente.post("/pas/crear", {})
        assert post.status_code == 200
        assert MARCA not in post.content.decode()
        # Exportación sin migrar: el mismo resultado que sin flag.
        con_flag = cliente.get("/pas/ddjj/tokens/exportar").status_code
    with _flag((), build):
        assert _cliente().get("/pas/ddjj/tokens/exportar").status_code == con_flag


def test_flag_de_una_vertical_deja_nativas_a_las_demas(build):
    with _flag({"pas"}, build):
        for ruta in ("/centrodeinfancia/", "/vat/centros/", "/ciudadanos/listar"):
            try:
                vista = resolve(ruta).func
            except Resolver404:
                continue
            assert "index_bytes" not in getattr(vista, "view_initkwargs", {}), ruta


def test_clave_desconocida_o_build_ausente_no_monta_nada(tmp_path):
    with _flag({"pas", "no-existe"}, tmp_path):
        assert react_preview_patterns("pas") == []
    with _flag({"no-existe"}, tmp_path):
        assert react_preview_patterns("no-existe") == []


def _ruta_ejemplo(ruta):
    ruta = re.sub(r"<uuid:[^>]+>", str(uuid.uuid4()), ruta)
    ruta = re.sub(r"<int:[^>]+>", "1", ruta)
    ruta = re.sub(r"<path:[^>]+>", "assets/app-1.js", ruta)
    ruta = re.sub(r"<[a-z]+:[^>]+>", "x", ruta)
    return re.sub(r"<[^>]+>", "x", ruta)


def test_sin_duplicados_ni_tapados_con_todo_activo(build):
    """Cada ruta se monta una vez; las entradas no-assets tienen ruta nativa."""
    with _flag(set(REGISTRO), build):
        por_ruta = {}
        for clave in REGISTRO:
            for patron in react_preview_patterns(clave):
                por_ruta.setdefault(str(patron.pattern), []).append(clave)
        duplicadas = {r: c for r, c in por_ruta.items() if len(c) > 1}
        assert not duplicadas
        assert por_ruta
    with _flag((), build):
        sin_nativa = []
        for ruta in por_ruta:
            if "react/" in ruta:
                with pytest.raises(Resolver404):
                    resolve("/" + _ruta_ejemplo(ruta))
                continue
            try:
                resolve("/" + _ruta_ejemplo(ruta))
            except Resolver404:
                sin_nativa.append(ruta)
        assert not sin_nativa


def test_variable_sin_definir_activa_todas_las_claves():
    assert parse_react_verticales(None) == frozenset({"todas"})
    with override_settings(REACT_VERTICALES_ACTIVAS=parse_react_verticales(None)):
        assert claves_activas() == frozenset(REGISTRO)


@pytest.mark.parametrize("valor", ["ninguna", " ninguna ", ""])
def test_ninguna_o_vacia_apaga_todo(valor, build):
    assert parse_react_verticales(valor) == frozenset()
    with _flag(parse_react_verticales(valor), build):
        assert claves_activas() == frozenset()
        assert react_preview_patterns(*REGISTRO) == []
        respuesta = _cliente().get("/pas/listar")
        assert MARCA not in respuesta.content.decode()


def test_lista_explicita_se_respeta():
    assert parse_react_verticales("pas, cdi") == frozenset({"pas", "cdi"})
    with override_settings(REACT_VERTICALES_ACTIVAS=parse_react_verticales("pas,cdi")):
        assert claves_activas() == frozenset({"pas", "cdi"})


def test_por_defecto_monta_todo_con_build_y_nada_sin_build(build, tmp_path):
    activas = parse_react_verticales(None)
    with _flag(activas, build):
        assert react_preview_patterns("pas", "cdi", "core")
        assert MARCA in _cliente().get("/pas/listar").content.decode()
    vacio = tmp_path / "sin-build"
    vacio.mkdir()
    with _flag(activas, vacio):
        assert react_preview_patterns("pas", "cdi", "core") == []
        assert MARCA not in _cliente().get("/pas/listar").content.decode()


def _dueno_de_ruta(ruta, backends):
    """Backend al que el proxy del core reenvía ``ruta``; ``None`` es el core."""
    relativa = ruta.lstrip("/")
    for nombre, spec in backends.items():
        if any(relativa.startswith(prefijo) for prefijo in spec["url_prefixes"]):
            return nombre
    return None


def _urlconf(dueno, backends):
    return backends[dueno]["urlconf"] if dueno else "config.urls"


def _assets_de_entradas(patrones):
    """Rutas de assets reescritas en el ``index.html`` de cada entrada."""
    assets = set()
    for patron in patrones:
        index = getattr(patron.callback, "view_initkwargs", {}).get("index_bytes")
        if index:
            assets.update(re.findall(r'"(/[^"]*app-1\.js)"', index.decode()))
    return assets


def test_assets_de_cada_entrada_llegan_al_backend_que_la_sirve(build, tmp_path, rf):
    """Guarda del hotfix: nginx sirve ``/static/`` y ``/media/`` desde disco y el
    proxy del core reenvía por ``url_prefixes``; un asset fuera del backend que
    monta la entrada, o tapado por otra ruta, deja la pantalla en blanco."""
    backends = load_backends_registry()
    # El build de PAS (DDJJ) publica sus assets bajo /v2/pas/.
    pas_build = tmp_path / "pas-build"
    (pas_build / "assets").mkdir(parents=True)
    (pas_build / "index.html").write_text(
        INDEX.replace("/v2/sisoc/", "/v2/pas/"), encoding="utf-8"
    )
    (pas_build / "assets" / "app-1.js").write_text("console.log(1);", encoding="utf-8")
    errores = []
    with _flag(set(REGISTRO), build, pas_build):
        for clave in REGISTRO:
            dueno = clave if clave in backends else None
            assets = _assets_de_entradas(react_preview_patterns(clave))
            assert assets, clave
            for ruta in sorted(assets):
                if ruta.startswith(("/static/", "/media/")):
                    errores.append(f"{clave}: {ruta} lo intercepta nginx")
                    continue
                if _dueno_de_ruta(ruta, backends) != dueno:
                    errores.append(f"{clave}: {ruta} no se enruta a {dueno or 'core'}")
                    continue
                try:
                    match = resolve(ruta, urlconf=_urlconf(dueno, backends))
                except Resolver404:
                    errores.append(f"{clave}: {ruta} no resuelve")
                    continue
                respuesta = match.func(rf.get(ruta), *match.args, **match.kwargs)
                if respuesta.status_code != 200:
                    errores.append(f"{clave}: {ruta} da {respuesta.status_code}")
    assert not errores, errores
