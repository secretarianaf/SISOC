import pytest
from django.core.exceptions import ValidationError

from dashboard.models import Tablero
from dashboard.services.catalogo import sincronizar_catalogo


def entrada(pk, slug, **campos):
    return {
        "model": "dashboard.tablero",
        "pk": pk,
        "fields": {
            "nombre": slug,
            "slug": slug,
            "url": "https://example.org/nuevo",
            **campos,
        },
    }


@pytest.mark.django_db
def test_catalogo_crea_y_preserva_campos_operativos_y_permisos():
    actual = Tablero.objects.create(
        pk=1,
        slug="uno",
        nombre="Elegido por Datos",
        activo=False,
        visible_menu=False,
        permisos=["auth.role_existente"],
        url="https://example.org/viejo",
    )
    datos = [
        entrada(
            1,
            "uno",
            nombre="Nombre de codigo",
            visible_menu=True,
            permisos=["auth.role_nuevo"],
        ),
        entrada(2, "dos"),
    ]
    sincronizar_catalogo(datos)
    sincronizar_catalogo(datos)
    actual.refresh_from_db()
    assert actual.nombre == "Elegido por Datos"
    assert actual.activo is False
    assert actual.visible_menu is False
    assert actual.permisos == ["auth.role_existente"]
    assert actual.url == "https://example.org/nuevo"
    assert Tablero.objects.get(pk=2).activo is True
    assert Tablero.objects.get(pk=2).visible_menu is True
    assert Tablero.objects.count() == 2


@pytest.mark.django_db
def test_catalogo_rechaza_colisiones_sin_escritura_parcial():
    Tablero.objects.create(pk=2, slug="otro", nombre="Existente")
    with pytest.raises(ValidationError):
        sincronizar_catalogo([entrada(1, "uno"), entrada(2, "dos")])
    assert not Tablero.objects.filter(pk=1).exists()
    assert Tablero.objects.get(pk=2).slug == "otro"


@pytest.mark.django_db
def test_catalogo_no_toca_tableros_fuera_del_archivo():
    Tablero.objects.create(pk=9, slug="interfaz", nombre="Interfaz", activo=False)
    sincronizar_catalogo([entrada(1, "uno")])
    assert Tablero.objects.get(pk=9).activo is False


@pytest.mark.django_db
@pytest.mark.parametrize("forzar", [False, True])
def test_carga_de_fixtures_no_sobrescribe_campos_de_datos(
    monkeypatch, tmp_path, forzar
):
    import json

    from django.core.management import call_command
    from core.services import fixture_post_load
    from dashboard.apps import DashboardConfig
    from dashboard.models import Dashboard
    from dashboard.services import catalogo
    import dashboard

    tablero = Tablero.objects.create(
        pk=1,
        slug="uno",
        nombre="Datos",
        activo=False,
        permisos=["auth.role_conservado"],
    )
    carpeta = tmp_path / "dashboard" / "catalogo"
    carpeta.mkdir(parents=True)
    archivo = carpeta / "tableros.json"
    archivo.write_text(
        json.dumps([entrada(1, "uno", nombre="Codigo")]), encoding="utf-8"
    )
    fixtures = tmp_path / "otro" / "fixtures"
    fixtures.mkdir(parents=True)
    (fixtures / "otro.json").write_text(
        json.dumps(
            [{"model": "dashboard.dashboard", "pk": "otra", "fields": {"cantidad": 1}}]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(catalogo, "CATALOGO", archivo)
    monkeypatch.setattr(fixture_post_load, "_HANDLERS", {})
    DashboardConfig("dashboard", dashboard).ready()
    monkeypatch.setattr(
        "core.management.commands.load_fixtures.sync_territorio_desde_fixture",
        lambda: {
            "provincias_creadas": 0,
            "municipios_creadas": 0,
            "localidades_creadas": 0,
            "saltadas_por_integridad": 0,
        },
    )
    call_command("load_fixtures", force=forzar)
    tablero.refresh_from_db()
    assert Dashboard.objects.filter(pk="otra").exists()
    assert (tablero.nombre, tablero.activo, tablero.permisos) == (
        "Datos",
        False,
        ["auth.role_conservado"],
    )


def test_catalogo_no_es_fixture_descubierto_por_el_loader():
    from dashboard.services.catalogo import CATALOGO

    assert CATALOGO.exists()
    assert CATALOGO.parent.name != "fixtures"


@pytest.mark.django_db
def test_catalogo_del_repositorio_se_puede_cargar_dos_veces():
    from dashboard.services.catalogo import leer_catalogo

    entradas = leer_catalogo()
    sincronizar_catalogo(entradas)
    sincronizar_catalogo(entradas)
    assert Tablero.objects.count() == len(entradas)


@pytest.mark.django_db
def test_conflicto_no_detiene_carga_ni_aplica_cambios(monkeypatch):
    from dashboard.services import catalogo

    Tablero.objects.create(pk=2, slug="otro", nombre="Existente")
    monkeypatch.setattr(
        catalogo, "leer_catalogo", lambda: [entrada(1, "uno"), entrada(2, "dos")]
    )
    resultado = catalogo.sincronizar_catalogo_post_fixture()
    assert "sin sincronizar" in resultado
    assert not Tablero.objects.filter(pk=1).exists()
    assert Tablero.objects.get(pk=2).slug == "otro"
