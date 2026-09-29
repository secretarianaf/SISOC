"""Buscadores homogeneos: filtros combinables en todos los listados.

Cubre las pantallas que se migraron al componente de filtros combinables,
verificando que ademas de renderizar la UI el filtro efectivamente filtra y que
la busqueda que cada listado ya tenia sigue funcionando.
"""

import json

import pytest
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone

pytestmark = pytest.mark.django_db


def _filtros(items):
    return json.dumps({"logic": "AND", "items": items})


@pytest.fixture
def admin(client):
    usuario = User.objects.create_superuser("admin_busc", "b@b.com", "test")
    client.force_login(usuario)
    return usuario


LISTADOS_MIGRADOS = [
    "importarexpedientes_list",
    "centrodeinfancia",
    "vpsl_itinerario_list",
    "vpsl_sede_list",
    "vat_modalidadcursada_list",
    "vat_planversioncurricular_list",
]


@pytest.mark.parametrize("nombre_url", LISTADOS_MIGRADOS)
def test_el_listado_expone_el_buscador_de_filtros_combinables(
    client, admin, nombre_url
):
    response = client.get(reverse(nombre_url))
    contenido = response.content.decode()

    assert response.status_code == 200
    assert response.context["filters_mode"] is True
    assert response.context["filters_config"]["fields"]
    assert "poncho-filter-row-template" in contenido
    assert "filters-config-json" in contenido


@pytest.mark.parametrize("nombre_url", LISTADOS_MIGRADOS)
def test_la_config_declara_campos_con_tipo_y_operadores(client, admin, nombre_url):
    config = client.get(reverse(nombre_url)).context["filters_config"]

    assert config["defaultField"]
    for field in config["fields"]:
        assert field["name"] and field["label"] and field["type"]
        assert config["operators"].get(field["type"]), field


def test_modalidad_cursada_filtra_por_nombre(client, admin):
    from VAT.models import ModalidadCursada

    buscada = ModalidadCursada.objects.create(nombre="Presencial intensiva")
    ModalidadCursada.objects.create(nombre="Virtual")

    response = client.get(
        reverse("vat_modalidadcursada_list"),
        {
            "filters": _filtros(
                [{"field": "nombre", "op": "contains", "value": "inten"}]
            )
        },
    )

    assert [m.pk for m in response.context["modalidades"]] == [buscada.pk]


def test_modalidad_cursada_ya_no_arrastra_la_busqueda_vieja(client, admin):
    """El buscador simple era decorativo: la vista nunca aplicaba `busqueda`.

    Al migrar a filtros combinables se removio, porque ya no hay input que lo
    dispare: el parametro no tiene que alterar el listado.
    """

    from VAT.models import ModalidadCursada

    ModalidadCursada.objects.create(nombre="Semipresencial")
    ModalidadCursada.objects.create(nombre="Virtual")

    response = client.get(reverse("vat_modalidadcursada_list"), {"busqueda": "Semi"})

    assert response.context["modalidades"].count() == 2


def test_sede_vpsl_combina_dos_filtros(client, admin):
    from ver_para_ser_libre.models import SedeVPSL

    objetivo = SedeVPSL.objects.create(
        nombre="Escuela Norte", jurisdiccion="Chaco", localidad="Resistencia"
    )
    SedeVPSL.objects.create(
        nombre="Escuela Norte", jurisdiccion="Salta", localidad="Salta"
    )
    SedeVPSL.objects.create(
        nombre="Otra", jurisdiccion="Chaco", localidad="Resistencia"
    )

    response = client.get(
        reverse("vpsl_sede_list"),
        {
            "filters": _filtros(
                [
                    {"field": "nombre", "op": "contains", "value": "Norte"},
                    {"field": "jurisdiccion", "op": "eq", "value": "Chaco"},
                ]
            )
        },
    )

    assert [s.pk for s in response.context["sedes"]] == [objetivo.pk]


def test_sede_vpsl_busca_por_domicilio_con_el_filtro_combinable(client, admin):
    """El texto libre se reemplazo por el filtro combinable sobre el mismo campo."""

    from ver_para_ser_libre.models import SedeVPSL

    objetivo = SedeVPSL.objects.create(nombre="Sede Uno", domicilio="Calle Falsa 123")
    SedeVPSL.objects.create(nombre="Sede Dos", domicilio="Otra")

    response = client.get(
        reverse("vpsl_sede_list"),
        {
            "filters": _filtros(
                [{"field": "domicilio", "op": "contains", "value": "Falsa"}]
            )
        },
    )

    assert [s.pk for s in response.context["sedes"]] == [objetivo.pk]


def test_sede_vpsl_conserva_busqueda_enlace_anterior(client, admin):
    from ver_para_ser_libre.models import SedeVPSL

    objetivo = SedeVPSL.objects.create(nombre="Escuela Norte", domicilio="Calle Falsa")
    SedeVPSL.objects.create(nombre="Escuela Sur", domicilio="Otra")

    response = client.get(reverse("vpsl_sede_list"), {"busqueda": "Falsa"})

    assert [s.pk for s in response.context["sedes"]] == [objetivo.pk]


def test_centro_de_infancia_filtra_por_organizacion(client, admin):
    from centrodeinfancia.models import CentroDeInfancia

    objetivo = CentroDeInfancia.objects.create(
        nombre="CDI Uno", organizacion="Fundación Alfa"
    )
    CentroDeInfancia.objects.create(nombre="CDI Dos", organizacion="Fundación Beta")

    response = client.get(
        reverse("centrodeinfancia"),
        {
            "filters": _filtros(
                [{"field": "organizacion", "op": "contains", "value": "Alfa"}]
            )
        },
    )

    assert [c.pk for c in response.context["centros"]] == [objetivo.pk]


def test_centro_de_infancia_conserva_busqueda_enlace_anterior(client, admin):
    from centrodeinfancia.models import CentroDeInfancia

    objetivo = CentroDeInfancia.objects.create(nombre="CDI Uno", organizacion="Alfa")
    CentroDeInfancia.objects.create(nombre="CDI Dos", organizacion="Beta")

    response = client.get(reverse("centrodeinfancia"), {"busqueda": "Alfa"})

    assert [c.pk for c in response.context["centros"]] == [objetivo.pk]


def test_importar_expedientes_filtra_por_usuario(client, admin):
    from importarexpediente.models import ArchivosImportados

    otro = User.objects.create_user("carga_masiva", password="x")
    objetivo = ArchivosImportados.objects.create(archivo="uno.csv", usuario=otro)
    ArchivosImportados.objects.create(archivo="dos.csv", usuario=admin)

    response = client.get(
        reverse("importarexpedientes_list"),
        {
            "filters": _filtros(
                [{"field": "usuario", "op": "contains", "value": "carga_masiva"}]
            )
        },
    )

    assert [a.pk for a in response.context["archivos_importados"]] == [objetivo.pk]


def test_importar_expedientes_conserva_busqueda_enlace_anterior(client, admin):
    from importarexpediente.models import ArchivosImportados

    objetivo = ArchivosImportados.objects.create(archivo="uno.csv", usuario=admin)
    ArchivosImportados.objects.create(archivo="dos.csv", usuario=admin)

    response = client.get(reverse("importarexpedientes_list"), {"busqueda": "uno"})

    assert [a.pk for a in response.context["archivos_importados"]] == [objetivo.pk]


def test_plan_curricular_conserva_sus_filtros_propios(client, admin):
    """Los filtros de titulo/activo del listado siguen conviviendo con los combinables."""

    from VAT.models import ModalidadCursada, PlanVersionCurricular, Sector

    sector = Sector.objects.create(nombre="Industria")
    modalidad = ModalidadCursada.objects.create(nombre="Presencial")
    activo = PlanVersionCurricular.objects.create(
        nombre="Plan activo", sector=sector, modalidad_cursada=modalidad, activo=True
    )
    PlanVersionCurricular.objects.create(
        nombre="Plan inactivo",
        sector=sector,
        modalidad_cursada=modalidad,
        activo=False,
    )

    response = client.get(reverse("vat_planversioncurricular_list"), {"activo": "true"})

    assert [p.pk for p in response.context["planes"]] == [activo.pk]


def test_plan_curricular_filtra_por_campo_combinable(client, admin):
    from VAT.models import ModalidadCursada, PlanVersionCurricular, Sector

    sector = Sector.objects.create(nombre="Industria")
    modalidad = ModalidadCursada.objects.create(nombre="Presencial")
    objetivo = PlanVersionCurricular.objects.create(
        nombre="Electricidad", sector=sector, modalidad_cursada=modalidad
    )
    PlanVersionCurricular.objects.create(
        nombre="Gastronomía", sector=sector, modalidad_cursada=modalidad
    )

    response = client.get(
        reverse("vat_planversioncurricular_list"),
        {
            "filters": _filtros(
                [{"field": "nombre", "op": "contains", "value": "Electri"}]
            )
        },
    )

    assert [p.pk for p in response.context["planes"]] == [objetivo.pk]


def test_itinerarios_conserva_su_busqueda_libre_y_su_panel(client, admin):
    """Unica pantalla donde el buscador propio del modulo sigue vivo.

    Su logica no es expresable con el engine (OR entre siete campos, mapeo de
    estado por texto, provincia segun permisos), asi que se mantiene y viaja en
    el mismo submit que los filtros combinables.
    """

    contenido = client.get(reverse("vpsl_itinerario_list")).content.decode()

    assert 'name="busqueda"' in contenido
    assert 'form="filters-form"' in contenido
    assert "poncho-filter-row-template" in contenido


# --- Caminos criticos ------------------------------------------------------
# Los casos de arriba corren con superusuario, que no tiene scope. Estos cubren
# lo que el superusuario no puede mostrar: que filtrar no amplie el alcance, que
# el export respete los filtros y que las fechas funcionen sobre un DateTimeField.


def _dar_rol(usuario, codename, nombre):
    """`auth.role_*` son permisos de rol colgados del ContentType de Group."""

    permiso, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codename,
        defaults={"name": nombre},
    )
    usuario.user_permissions.add(permiso)


def _usuario_provincial(client, username, provincia):
    from users.models import Profile, ProfileTerritorialScope

    usuario = User.objects.create_user(username=username, password="test1234")
    perfil, _ = Profile.objects.get_or_create(user=usuario)
    perfil.provincia = provincia
    perfil.es_usuario_provincial = True
    perfil.save()
    ProfileTerritorialScope.objects.create(profile=perfil, provincia=provincia)
    usuario.user_permissions.add(
        Permission.objects.get(
            codename="view_centrodeinfancia",
            content_type__app_label="centrodeinfancia",
        )
    )
    _dar_rol(usuario, "role_exportar_a_csv", "Exportar a csv")
    client.force_login(User.objects.get(pk=usuario.pk))
    return usuario


def test_centro_de_infancia_el_filtro_no_amplia_el_alcance_provincial(client):
    """Filtrar acota dentro del scope; nunca lo abre.

    El engine corre despues de `_aplicar_scope_centros_cdi`, asi que un centro de
    otra provincia no puede aparecer aunque matchee el filtro.
    """

    from centrodeinfancia.models import CentroDeInfancia
    from core.models import Provincia

    propia = Provincia.objects.create(nombre="Chaco")
    ajena = Provincia.objects.create(nombre="Salta")
    _usuario_provincial(client, "cdi_provincial", propia)

    dentro = CentroDeInfancia.objects.create(
        nombre="CDI Propio", organizacion="Fundación Alfa", provincia=propia
    )
    CentroDeInfancia.objects.create(
        nombre="CDI Ajeno", organizacion="Fundación Alfa", provincia=ajena
    )

    response = client.get(
        reverse("centrodeinfancia"),
        {
            "filters": _filtros(
                [{"field": "organizacion", "op": "contains", "value": "Alfa"}]
            )
        },
    )

    assert [c.pk for c in response.context["centros"]] == [dentro.pk]


def test_el_export_de_cdi_aplica_los_filtros_combinables(client, admin):
    """`export_helper.js` reenvia `?filters=`: el CSV tiene que respetarlos.

    Antes de migrar, el export leia `busqueda`. Al quedar ese parametro fuera de
    la UI, exportaba el universo completo del scope aunque el usuario filtrara.
    """

    from centrodeinfancia.models import CentroDeInfancia

    CentroDeInfancia.objects.create(nombre="CDI Alfa", organizacion="Fundación Alfa")
    CentroDeInfancia.objects.create(nombre="CDI Beta", organizacion="Fundación Beta")

    response = client.get(
        reverse("centrodeinfancia_exportar"),
        {
            "filters": _filtros(
                [{"field": "organizacion", "op": "contains", "value": "Alfa"}]
            )
        },
    )
    contenido = b"".join(response.streaming_content).decode("utf-8-sig")

    assert response.status_code == 200
    assert "CDI Alfa" in contenido
    assert "CDI Beta" not in contenido


def test_el_export_de_cdi_no_escapa_del_alcance_del_usuario(client):
    from centrodeinfancia.models import CentroDeInfancia
    from core.models import Provincia

    propia = Provincia.objects.create(nombre="Chaco")
    ajena = Provincia.objects.create(nombre="Salta")
    _usuario_provincial(client, "cdi_export_provincial", propia)

    CentroDeInfancia.objects.create(
        nombre="CDI Propio", organizacion="Fundación Alfa", provincia=propia
    )
    CentroDeInfancia.objects.create(
        nombre="CDI Ajeno", organizacion="Fundación Alfa", provincia=ajena
    )

    response = client.get(
        reverse("centrodeinfancia_exportar"),
        {
            "filters": _filtros(
                [{"field": "organizacion", "op": "contains", "value": "Alfa"}]
            )
        },
    )
    contenido = b"".join(response.streaming_content).decode("utf-8-sig")

    assert "CDI Propio" in contenido
    assert "CDI Ajeno" not in contenido


def test_importar_expedientes_filtra_por_fecha_de_subida(client, admin):
    """`fecha_subida` es DateTimeField y el filtro es de tipo `date`.

    Sin el mapeo a `__date`, el engine comparaba contra la medianoche y con
    `USE_TZ=True` el registro de hoy no aparecia nunca.
    """

    from importarexpediente.models import ArchivosImportados

    archivo = ArchivosImportados.objects.create(archivo="hoy.csv", usuario=admin)
    hoy = timezone.localtime(archivo.fecha_subida).date().isoformat()

    response = client.get(
        reverse("importarexpedientes_list"),
        {"filters": _filtros([{"field": "fecha_subida", "op": "eq", "value": hoy}])},
    )

    assert [a.pk for a in response.context["archivos_importados"]] == [archivo.pk]
