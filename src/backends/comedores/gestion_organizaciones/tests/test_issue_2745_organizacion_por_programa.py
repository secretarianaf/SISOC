"""Etapas 2 y 3 del #2745: servicios y carga de datos por programa.

Plan: docs/plans/2026-T4/2026-10-20-2745-legajo-organizacion-por-programa.md.
"""

import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.messages import get_messages
from django.urls import reverse

from comedores.models import Comedor, Programas
from comedores.utils import es_programa_alimentar_comunidad
from core.models import Provincia
from gestion_organizaciones.forms import FirmanteForm, OrganizacionForm
from gestion_organizaciones.models import (
    ConvenioProyecto,
    DatosRegionOrganizacion,
    Firmante,
    LineaProyecto,
    ProgramaOrganizacion,
    RegionAbordaje,
    SubzonaAbordaje,
)
from gestion_organizaciones.services import programas as servicio
from gestion_organizaciones.templatetags.organizaciones_tags import monto
from organizaciones.models import Organizacion, ProyectoOrganizacion
from rendicioncuentasmensual.models import RendicionCuentaMensual
from rendicioncuentasmensual.services import RendicionesOrganizacionService

SECOS = RendicionCuentaMensual.LINEA_SECOS
TRADICIONAL = RendicionCuentaMensual.LINEA_TRADICIONAL


@pytest.fixture
def programas(db):
    return SimpleNamespace(
        alco=Programas.objects.create(nombre="Alimentar comunidad"),
        secos=Programas.objects.create(nombre="Abordaje comunitario - Línea Secos"),
        tradicional=Programas.objects.create(
            nombre="Abordaje comunitario - Línea Tradicional"
        ),
        pnud=Programas.objects.create(nombre="PNUD Prog1"),
    )


@pytest.fixture
def region(db):
    norte = RegionAbordaje.objects.create(nombre="NORTE")
    sur = RegionAbordaje.objects.create(nombre="SUR")
    return SimpleNamespace(
        norte=norte,
        sur=sur,
        salta=SubzonaAbordaje.objects.create(region=norte, nombre="SALTA"),
        chubut=SubzonaAbordaje.objects.create(region=sur, nombre="CHUBUT"),
    )


def _organizacion(nombre="Org #2745", *programas_org):
    organizacion = Organizacion.objects.create(nombre=nombre)
    for programa in programas_org:
        ProgramaOrganizacion.objects.create(
            organizacion=organizacion, programa=programa
        )
    return organizacion


def _proyecto(organizacion, codigo, linea=None, activo=True):
    proyecto = ProyectoOrganizacion.objects.create(
        organizacion=organizacion, codigo=codigo, activo=activo
    )
    if linea is not None:
        LineaProyecto.objects.create(proyecto=proyecto, programa=linea)
    return proyecto


def _convenio(proyecto, **extra):
    datos = {
        "proyecto": proyecto,
        "numero": "0123/2026",
        "fecha": date(2026, 3, 1),
        "meses": 12,
        "monto_total": Decimal("1000"),
        "componente_alimentario": Decimal("700"),
        "componente_gastos_generales": Decimal("200"),
        "componente_siph": Decimal("50"),
        "componente_gasto_bancario": Decimal("50"),
    }
    datos.update(extra)
    return ConvenioProyecto.objects.create(**datos)


def _rendicion(numero, linea, **extra):
    return RendicionCuentaMensual.objects.create(
        mes=1,
        anio=2026,
        convenio=f"C-{numero}",
        numero_rendicion=numero,
        linea_programatica=linea,
        **extra,
    )


# --- Etapa 2: servicios -------------------------------------------------------


def test_alimentar_comunidad_se_reconoce_por_nombre(programas):
    assert es_programa_alimentar_comunidad(programas.alco)
    assert es_programa_alimentar_comunidad(
        SimpleNamespace(nombre="ALIMENTAR  Comunidad")
    )
    assert not es_programa_alimentar_comunidad(programas.secos)
    assert not es_programa_alimentar_comunidad(None)


def test_programas_de_organizacion_en_orden_del_legajo(programas):
    organizacion = _organizacion(
        "Org orden",
        programas.pnud,
        programas.tradicional,
        programas.alco,
        programas.secos,
    )

    assert servicio.programas_de_organizacion(organizacion) == [
        programas.alco,
        programas.secos,
        programas.tradicional,
        programas.pnud,
    ]
    assert servicio.programas_del_legajo() == [
        programas.alco,
        programas.secos,
        programas.tradicional,
    ]


def test_organizacion_sin_programas_no_aplica_reglas(programas):
    organizacion = _organizacion("Org sin programas")

    assert servicio.programas_de_organizacion(organizacion) == []
    assert not servicio.aplica_reglas_de_programa(organizacion)
    assert not servicio.tiene_programa_abordaje(organizacion)
    assert not servicio.aplica_reglas_de_programa(Organizacion())


def test_tiene_programa_abordaje(programas):
    assert not servicio.tiene_programa_abordaje(_organizacion("A", programas.alco))
    assert servicio.tiene_programa_abordaje(_organizacion("B", programas.secos))


def test_proyectos_firmantes_y_comedores_por_programa(programas):
    organizacion = _organizacion("Org datos", programas.secos, programas.tradicional)
    secos = _proyecto(organizacion, "S-1", programas.secos)
    _proyecto(organizacion, "S-INACTIVO", programas.secos, activo=False)
    tradicional = _proyecto(organizacion, "T-1", programas.tradicional)
    sin_linea = _proyecto(organizacion, "X-1")
    firmante = Firmante.objects.create(
        organizacion=organizacion, nombre="Ana", programa=programas.secos
    )
    Firmante.objects.create(organizacion=organizacion, nombre="Sin programa")
    comedor = Comedor.objects.create(
        nombre="Comedor secos", organizacion=organizacion, programa=programas.secos
    )

    assert list(servicio.proyectos_por_linea(organizacion, programas.secos)) == [secos]
    assert list(servicio.proyectos_por_linea(organizacion, programas.tradicional)) == [
        tradicional
    ]
    assert list(servicio.proyectos_sin_linea(organizacion)) == [sin_linea]
    assert list(servicio.firmantes_por_programa(organizacion, programas.secos)) == [
        firmante
    ]
    assert list(servicio.comedores_por_programa(organizacion, programas.secos)) == [
        comedor
    ]


def test_rendiciones_sin_linea_conservan_el_comportamiento_actual(programas):
    organizacion = _organizacion("Org rendiciones")
    comedor = Comedor.objects.create(nombre="C", organizacion=organizacion)
    r_secos = _rendicion(1, SECOS, comedor=comedor)
    r_trad = _rendicion(2, TRADICIONAL, comedor=comedor)

    resultado = set(RendicionesOrganizacionService.obtener_rendiciones(organizacion))

    assert resultado == {r_secos, r_trad}


def test_rendiciones_por_linea_usan_la_linea_de_la_rendicion(programas):
    organizacion = _organizacion("Org líneas", programas.secos, programas.tradicional)
    proyecto_trad = _proyecto(organizacion, "T-1", programas.tradicional)
    comedor = Comedor.objects.create(nombre="C", organizacion=organizacion)
    # Sin proyecto: aparece en su línea (definición 23).
    sin_proyecto = _rendicion(1, SECOS, comedor=comedor)
    # Línea Secos con proyecto de Línea Tradicional: va a Secos.
    cruzada = _rendicion(2, SECOS, proyecto=proyecto_trad)
    tradicional = _rendicion(3, TRADICIONAL, proyecto=proyecto_trad)

    assert set(servicio.rendiciones_por_programa(organizacion, programas.secos)) == {
        sin_proyecto,
        cruzada,
    }
    assert set(
        servicio.rendiciones_por_programa(organizacion, programas.tradicional)
    ) == {tradicional}
    assert not servicio.rendiciones_por_programa(organizacion, programas.alco).exists()


def test_rendiciones_combinan_proyecto_y_linea(programas):
    organizacion = _organizacion("Org filtros", programas.secos)
    p1 = _proyecto(organizacion, "S-1", programas.secos)
    p2 = _proyecto(organizacion, "S-2", programas.secos)
    en_p1 = _rendicion(1, SECOS, proyecto=p1)
    _rendicion(2, SECOS, proyecto=p2)
    _rendicion(3, TRADICIONAL, proyecto=p1)

    resultado = RendicionesOrganizacionService.obtener_rendiciones(
        organizacion, "S-1", linea_programatica=SECOS
    )

    assert list(resultado) == [en_p1]


def test_resumen_convenio(programas):
    organizacion = _organizacion("Org convenio", programas.tradicional)
    proyecto = _proyecto(organizacion, "T-1", programas.tradicional)
    convenio = _convenio(proyecto)

    assert servicio.resumen_convenio(convenio) == {
        "suma": Decimal("1000"),
        "total": Decimal("1000"),
        "diferencia": Decimal("0"),
        "coincide": True,
    }

    convenio.imprevistos = Decimal("25.50")
    resumen = servicio.resumen_convenio(convenio)
    assert resumen["suma"] == Decimal("1025.50")
    assert resumen["diferencia"] == Decimal("-25.50")
    assert not resumen["coincide"]


@pytest.mark.parametrize(
    "valor, esperado",
    [
        (Decimal("100000000"), "$100.000.000"),
        (Decimal("1234.5"), "$1.234,50"),
        (0, "$0"),
        (Decimal("-2500"), "-$2.500"),
        (None, ""),
        ("abc", "abc"),
    ],
)
def test_filtro_monto(valor, esperado):
    assert monto(valor) == esperado


def test_asociaciones_de_programa_incluye_datos_dados_de_baja(programas):
    organizacion = _organizacion("Org asociaciones", programas.secos)
    comedor = Comedor.objects.create(
        nombre="Comedor de baja", organizacion=organizacion, programa=programas.secos
    )
    comedor.delete()

    assert servicio.asociaciones_de_programa(organizacion, programas.secos) == {
        "comedores": 1
    }
    assert servicio.asociaciones_de_programa(organizacion, programas.alco) == {}


# --- Etapa 3: formulario de la organización ----------------------------------


@pytest.fixture
def provincia(db):
    return Provincia.objects.create(nombre="Buenos Aires")


def _datos_form(provincia, programas_ids=(), proyectos=(), **extra):
    datos = {
        "nombre": "Org formulario",
        "fecha_vencimiento": "2030-01-01",
        "provincia": str(provincia.pk),
        "programas": [str(pk) for pk in programas_ids],
        "proyectos_lineas": json.dumps(list(proyectos)),
    }
    datos.update(extra)
    return datos


def test_alta_con_programas_proyectos_y_region(programas, region, provincia):
    form = OrganizacionForm(
        data=_datos_form(
            provincia,
            [programas.alco.pk, programas.secos.pk],
            [{"codigo": "S-1", "linea": programas.secos.pk}],
            region=str(region.norte.pk),
            subzona=str(region.salta.pk),
        )
    )

    assert form.is_valid(), form.errors
    organizacion = form.save()

    assert servicio.programas_de_organizacion(organizacion) == [
        programas.alco,
        programas.secos,
    ]
    proyecto = organizacion.proyectos.get()
    assert proyecto.codigo == "S-1"
    assert proyecto.linea.programa == programas.secos
    datos = DatosRegionOrganizacion.objects.get(organizacion=organizacion)
    assert (datos.region, datos.subzona) == (region.norte, region.salta)


def test_sin_programas_el_proyecto_no_exige_linea(programas, provincia):
    form = OrganizacionForm(
        data=_datos_form(provincia, proyectos=[{"codigo": "P-1", "linea": None}])
    )

    assert form.is_valid(), form.errors
    organizacion = form.save()
    assert organizacion.proyectos.get().codigo == "P-1"
    assert not LineaProyecto.objects.exists()


def test_con_abordaje_el_proyecto_exige_linea(programas, provincia):
    form = OrganizacionForm(
        data=_datos_form(
            provincia, [programas.secos.pk], [{"codigo": "P-1", "linea": None}]
        )
    )

    assert not form.is_valid()
    assert "Elegí la línea del proyecto P-1." in form.errors["proyectos_lineas"]


def test_linea_fuera_de_los_programas_elegidos(programas, provincia):
    form = OrganizacionForm(
        data=_datos_form(
            provincia,
            [programas.secos.pk],
            [{"codigo": "P-1", "linea": programas.tradicional.pk}],
        )
    )

    assert not form.is_valid()
    assert "no está entre los programas elegidos" in form.errors["proyectos_lineas"][0]


def test_proyecto_sin_programa_de_abordaje(programas, provincia):
    form = OrganizacionForm(
        data=_datos_form(
            provincia, [programas.alco.pk], [{"codigo": "P-1", "linea": None}]
        )
    )

    assert not form.is_valid()
    assert "necesita una línea" in form.errors["proyectos_lineas"][0]


def test_linea_que_no_es_de_abordaje(programas, provincia):
    form = OrganizacionForm(
        data=_datos_form(
            provincia, proyectos=[{"codigo": "P-1", "linea": programas.alco.pk}]
        )
    )

    assert not form.is_valid()
    assert "Línea Secos o Línea Tradicional" in form.errors["proyectos_lineas"][0]


def test_proyectos_ilegibles(programas, provincia):
    form = OrganizacionForm(data=_datos_form(provincia, proyectos_lineas="{no-json"))

    assert not form.is_valid()
    assert "proyectos_lineas" in form.errors


def test_edicion_muestra_lineas_y_conserva_programas_de_otros_programas(
    programas, provincia
):
    organizacion = _organizacion("Org PNUD", programas.pnud, programas.secos)
    organizacion.provincia = provincia
    organizacion.save()
    _proyecto(organizacion, "S-1", programas.secos)

    form = OrganizacionForm(instance=organizacion)

    assert set(form.fields["programas"].queryset) == {
        programas.alco,
        programas.secos,
        programas.tradicional,
        programas.pnud,
    }
    assert set(form.initial["programas"]) == {programas.pnud.pk, programas.secos.pk}
    assert json.loads(form.initial["proyectos_lineas"]) == [
        {"codigo": "S-1", "linea": programas.secos.pk}
    ]


def test_no_se_quita_un_programa_con_datos_asociados(programas, provincia):
    organizacion = _organizacion("Org quitar", programas.secos, programas.alco)
    _proyecto(organizacion, "S-1", programas.secos)
    Firmante.objects.create(
        organizacion=organizacion, nombre="Ana", programa=programas.alco
    )

    form = OrganizacionForm(
        data=_datos_form(
            provincia, [], [{"codigo": "S-1", "linea": programas.secos.pk}]
        ),
        instance=organizacion,
    )

    assert not form.is_valid()
    errores = " ".join(form.errors["programas"])
    assert "1 proyectos" in errores
    assert "1 firmantes" in errores
    assert ProgramaOrganizacion.objects.filter(organizacion=organizacion).count() == 2


def test_se_quita_un_programa_sin_datos(programas, provincia):
    organizacion = _organizacion("Org quitar libre", programas.secos, programas.alco)

    form = OrganizacionForm(
        data=_datos_form(provincia, [programas.secos.pk]), instance=organizacion
    )

    assert form.is_valid(), form.errors
    form.save()
    assert servicio.programas_de_organizacion(organizacion) == [programas.secos]


def test_quitar_proyecto_lo_desactiva_y_conserva_linea_y_convenio(programas, provincia):
    organizacion = _organizacion("Org desactivar", programas.tradicional)
    proyecto = _proyecto(organizacion, "T-1", programas.tradicional)
    _convenio(proyecto)

    form = OrganizacionForm(
        data=_datos_form(provincia, [programas.tradicional.pk], []),
        instance=organizacion,
    )
    assert form.is_valid(), form.errors
    form.save()

    proyecto.refresh_from_db()
    assert not proyecto.activo
    assert LineaProyecto.objects.filter(proyecto=proyecto).exists()
    assert ConvenioProyecto.objects.filter(proyecto=proyecto).exists()


def test_cambiar_linea_de_proyecto(programas, provincia):
    organizacion = _organizacion("Org cambio", programas.secos, programas.tradicional)
    proyecto = _proyecto(organizacion, "P-1", programas.secos)

    form = OrganizacionForm(
        data=_datos_form(
            provincia,
            [programas.secos.pk, programas.tradicional.pk],
            [{"codigo": "P-1", "linea": programas.tradicional.pk}],
        ),
        instance=organizacion,
    )
    assert form.is_valid(), form.errors
    form.save()

    assert (
        LineaProyecto.objects.get(proyecto=proyecto).programa == programas.tradicional
    )


def test_no_pasa_a_secos_un_proyecto_con_imprevistos(programas, provincia):
    organizacion = _organizacion(
        "Org imprevistos", programas.secos, programas.tradicional
    )
    proyecto = _proyecto(organizacion, "T-1", programas.tradicional)
    _convenio(proyecto, imprevistos=Decimal("10"))

    form = OrganizacionForm(
        data=_datos_form(
            provincia,
            [programas.secos.pk, programas.tradicional.pk],
            [{"codigo": "T-1", "linea": programas.secos.pk}],
        ),
        instance=organizacion,
    )

    assert not form.is_valid()
    assert "Imprevistos" in form.errors["proyectos_lineas"][0]


def test_subzona_de_otra_region(programas, region, provincia):
    form = OrganizacionForm(
        data=_datos_form(
            provincia,
            [programas.secos.pk],
            region=str(region.norte.pk),
            subzona=str(region.chubut.pk),
        )
    )

    assert not form.is_valid()
    assert "no pertenece a la región" in form.errors["subzona"][0]


def test_region_sin_subzona(programas, region, provincia):
    form = OrganizacionForm(
        data=_datos_form(provincia, [programas.secos.pk], region=str(region.norte.pk))
    )

    assert not form.is_valid()
    assert "subzona" in form.errors


def test_region_cargada_no_se_puede_vaciar(programas, region, provincia):
    organizacion = _organizacion("Org región", programas.secos)
    DatosRegionOrganizacion.objects.create(
        organizacion=organizacion, region=region.norte, subzona=region.salta
    )

    form = OrganizacionForm(
        data=_datos_form(provincia, [programas.secos.pk]), instance=organizacion
    )

    assert not form.is_valid()
    assert "region" in form.errors


def test_cambiar_region_y_subzona(programas, region, provincia):
    organizacion = _organizacion("Org región cambio", programas.secos)
    DatosRegionOrganizacion.objects.create(
        organizacion=organizacion, region=region.norte, subzona=region.salta
    )

    form = OrganizacionForm(
        data=_datos_form(
            provincia,
            [programas.secos.pk],
            region=str(region.sur.pk),
            subzona=str(region.chubut.pk),
        ),
        instance=organizacion,
    )
    assert form.is_valid(), form.errors
    form.save()

    datos = DatosRegionOrganizacion.objects.get(organizacion=organizacion)
    assert (datos.region, datos.subzona) == (region.sur, region.chubut)
    assert DatosRegionOrganizacion.objects.count() == 1


# --- Etapa 3: firmante ----------------------------------------------------------


def test_firmante_solo_ofrece_programas_de_la_organizacion(programas):
    organizacion = _organizacion("Org firmante", programas.alco)

    form = FirmanteForm(instance=Firmante(organizacion=organizacion))

    assert list(form.fields["programa"].queryset) == [programas.alco]
    invalido = FirmanteForm(
        data={"nombre": "Ana", "programa": str(programas.secos.pk)},
        instance=Firmante(organizacion=organizacion),
    )
    assert not invalido.is_valid()
    assert "programa" in invalido.errors


def test_firmante_en_organizacion_sin_programas_ofrece_todos(programas):
    organizacion = _organizacion("Org firmante libre")

    form = FirmanteForm(instance=Firmante(organizacion=organizacion))

    assert set(form.fields["programa"].queryset) == set(Programas.objects.all())


def test_firmante_conserva_su_programa_actual(programas):
    organizacion = _organizacion("Org firmante actual", programas.alco)
    firmante = Firmante.objects.create(
        organizacion=organizacion, nombre="Ana", programa=programas.pnud
    )

    form = FirmanteForm(instance=firmante)

    assert set(form.fields["programa"].queryset) == {programas.alco, programas.pnud}


# --- Etapa 3: vistas --------------------------------------------------------------


@pytest.fixture
def usuario(db):
    user = User.objects.create_user(username="gestor-2745", password="secret")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="organizaciones", codename="view_organizacion"
        )
    )
    return user


def _datos_convenio(**extra):
    datos = {
        "numero": "0001/2026",
        "fecha": "2026-03-01",
        "meses": "12",
        "monto_total": "1000",
        "componente_alimentario": "700",
        "componente_gastos_generales": "200",
        "componente_siph": "50",
        "componente_gasto_bancario": "50",
    }
    datos.update(extra)
    return datos


def test_convenio_secos_sin_imprevistos(client, usuario, programas):
    organizacion = _organizacion("Org conv secos", programas.secos)
    proyecto = _proyecto(organizacion, "S-1", programas.secos)
    client.force_login(usuario)
    url = reverse("organizacion_proyecto_convenio", kwargs={"proyecto_id": proyecto.pk})

    respuesta = client.get(url)
    assert respuesta.status_code == 200
    assert "imprevistos" not in respuesta.context["form"].fields

    respuesta = client.post(url, _datos_convenio(imprevistos="99"))
    assert respuesta.status_code == 302
    convenio = ConvenioProyecto.objects.get(proyecto=proyecto)
    assert convenio.imprevistos is None
    assert convenio.numero == "0001/2026"


def test_convenio_tradicional_con_imprevistos_y_aviso_de_suma(
    client, usuario, programas
):
    organizacion = _organizacion("Org conv trad", programas.tradicional)
    proyecto = _proyecto(organizacion, "T-1", programas.tradicional)
    client.force_login(usuario)
    url = reverse("organizacion_proyecto_convenio", kwargs={"proyecto_id": proyecto.pk})

    respuesta = client.post(url, _datos_convenio(imprevistos="10"))

    assert respuesta.status_code == 302
    assert ConvenioProyecto.objects.get(proyecto=proyecto).imprevistos == Decimal("10")
    textos = [str(m) for m in get_messages(respuesta.wsgi_request)]
    assert any("no coincide" in texto and "$1.010" in texto for texto in textos)


def test_convenio_edicion_no_duplica(client, usuario, programas):
    organizacion = _organizacion("Org conv edición", programas.secos)
    proyecto = _proyecto(organizacion, "S-1", programas.secos)
    _convenio(proyecto)
    client.force_login(usuario)
    url = reverse("organizacion_proyecto_convenio", kwargs={"proyecto_id": proyecto.pk})

    client.post(url, _datos_convenio(numero="0002/2026"))

    assert ConvenioProyecto.objects.get(proyecto=proyecto).numero == "0002/2026"
    assert ConvenioProyecto.objects.count() == 1


def test_convenio_de_proyecto_sin_linea_redirige(client, usuario, programas):
    organizacion = _organizacion("Org conv sin línea")
    proyecto = _proyecto(organizacion, "X-1")
    client.force_login(usuario)
    url = reverse("organizacion_proyecto_convenio", kwargs={"proyecto_id": proyecto.pk})

    respuesta = client.post(url, _datos_convenio())

    assert respuesta.status_code == 302
    assert respuesta.url == reverse(
        "organizacion_editar", kwargs={"pk": organizacion.pk}
    )
    assert not ConvenioProyecto.objects.exists()


def test_convenio_sin_permiso(client, programas):
    organizacion = _organizacion("Org conv permiso", programas.secos)
    proyecto = _proyecto(organizacion, "S-1", programas.secos)
    client.force_login(User.objects.create_user(username="sin-permiso", password="x"))
    url = reverse("organizacion_proyecto_convenio", kwargs={"proyecto_id": proyecto.pk})

    respuesta = client.post(url, _datos_convenio())

    assert respuesta.status_code in (302, 403)
    assert not ConvenioProyecto.objects.exists()


def test_alta_de_firmante_limita_programas(client, usuario, programas):
    organizacion = _organizacion("Org alta firmante", programas.alco)
    client.force_login(usuario)

    respuesta = client.get(
        reverse("firmante_crear", kwargs={"organizacion_pk": organizacion.pk})
    )

    assert list(respuesta.context["form"].fields["programa"].queryset) == [
        programas.alco
    ]


# --- Etapa 3, paso 7: baja de organización sin perder datos ---------------------


def _dar_de_baja(client, usuario, organizacion):
    client.force_login(usuario)
    return client.post(reverse("organizacion_eliminar", kwargs={"pk": organizacion.pk}))


@pytest.mark.parametrize("caso", ["comedor", "linea", "convenio", "solo_proyecto"])
def test_baja_bloqueada_si_tiene_proyectos(client, usuario, programas, caso):
    organizacion = _organizacion(f"Org baja {caso}", programas.tradicional)
    proyecto = _proyecto(
        organizacion,
        "T-1",
        programas.tradicional if caso in ("linea", "convenio") else None,
    )
    if caso == "comedor":
        Comedor.objects.create(nombre="C", organizacion=organizacion, proyecto=proyecto)
    if caso == "convenio":
        _convenio(proyecto)

    respuesta = _dar_de_baja(client, usuario, organizacion)

    assert respuesta.status_code == 200
    textos = " ".join(str(m) for m in get_messages(respuesta.wsgi_request))
    assert "No se puede dar de baja la organización: tiene 1 proyecto" in textos
    assert Organizacion.objects.filter(pk=organizacion.pk).exists()
    assert ProyectoOrganizacion.objects.filter(pk=proyecto.pk).exists()
    assert LineaProyecto.objects.count() == (1 if caso in ("linea", "convenio") else 0)
    assert ConvenioProyecto.objects.count() == (1 if caso == "convenio" else 0)


def test_baja_sin_proyectos_sigue_funcionando(client, usuario, programas):
    organizacion = _organizacion("Org baja libre", programas.alco)
    firmante = Firmante.objects.create(organizacion=organizacion, nombre="Ana")

    respuesta = _dar_de_baja(client, usuario, organizacion)

    assert respuesta.status_code == 302
    assert not Organizacion.objects.filter(pk=organizacion.pk).exists()
    assert Organizacion.all_objects.filter(pk=organizacion.pk).exists()
    assert Firmante.all_objects.filter(pk=firmante.pk).exists()
    assert ProgramaOrganizacion.objects.filter(organizacion=organizacion).exists()
