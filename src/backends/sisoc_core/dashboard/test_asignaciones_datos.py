"""Interfaz de asignaciones individuales del equipo de Datos."""

import pytest
from auditlog.models import LogEntry
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import connection
from django.test import Client
from django.urls import reverse

from core.models import Provincia
from dashboard.models import (
    AudienciaTableros,
    ConcesionTablero,
    ConfiguracionTableroInterno,
    Tablero,
)

pytestmark = pytest.mark.django_db


def test_consulta_y_asignacion_exigen_rol():
    usuario = User.objects.create_user(username="receptor")
    actor = User.objects.create_user(username="sinrol")
    client = Client()
    client.force_login(actor)
    url = reverse("dashboard_asignaciones_usuario", args=[usuario.pk])
    assert client.get(url).status_code == 403
    assert client.post(url, {}).status_code == 403


def test_busqueda_de_usuarios_y_recientes_paginados():
    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    for numero in range(27):
        User.objects.create_user(username=f"destino{numero:02d}")
    usuario_fuera_de_pagina = User.objects.get(username="destino26")
    fuera_de_pagina = Tablero.objects.create(nombre="Fuera de página")
    ConcesionTablero.objects.create(
        usuario=usuario_fuera_de_pagina,
        tablero=fuera_de_pagina,
        tipo="nacional",
    )
    client = Client()
    client.force_login(actor)
    url = reverse("dashboard_buscar_usuarios_datos")
    recientes = client.get(url).content.decode()
    assert recientes.index("destino26") < recientes.index("destino25")
    assert "destino00" not in recientes
    assert "destino00" in client.get(url, {"page": 2}).content.decode()
    consultas_concesiones = []

    def capturar_concesiones(ejecutar, sql, parametros, muchos, contexto):
        if ConcesionTablero._meta.db_table in sql:
            consultas_concesiones.append(parametros)
        return ejecutar(sql, parametros, muchos, contexto)

    with connection.execute_wrapper(capturar_concesiones):
        primera = client.get(url, {"q": "destino"}).content.decode()
    segunda = client.get(url, {"q": "destino", "page": 2}).content.decode()
    assert "destino00" in primera and "destino26" not in primera
    assert "destino26" in segunda and "destino00" not in segunda
    assert "Fuera de página" not in primera
    assert "Fuera de página" in segunda
    assert len(consultas_concesiones) == 1
    assert len(consultas_concesiones[0]) == 25
    assert usuario_fuera_de_pagina.pk not in consultas_concesiones[0]


def test_busqueda_muestra_asignaciones_y_estado_por_usuario():
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.create(name="Equipo de Datos"))
    usuario = User.objects.create_user(username="destino-a")
    otro_miembro = User.objects.create_user(username="destino-b")
    User.objects.create_user(username="destino-c")
    audiencia = AudienciaTableros.objects.create(nombre="Equipo provincial")
    audiencia.agregar_miembro(usuario)
    audiencia.agregar_miembro(otro_miembro)
    progresar = Tablero.objects.create(
        nombre="Resumen Progresar",
        slug="resumen-progresar",
        ruta_interna="/dashboard/progresar-curso-obligatorio/",
    )
    ConfiguracionTableroInterno.objects.create(
        codigo="progresar_curso", tablero=progresar, activa=True
    )
    provincia = Provincia.objects.create(nombre="Salta")
    ConcesionTablero.objects.create(usuario=usuario, tablero=progresar, tipo="nacional")
    ConcesionTablero.objects.create(
        audiencia=audiencia, tablero=progresar, tipo="provincia", provincia=provincia
    )
    ConcesionTablero.objects.create(
        usuario=usuario, tablero=progresar, tipo="cdi", cdi_id=123
    )
    client = Client()
    client.force_login(actor)
    url = reverse("dashboard_buscar_usuarios_datos")
    respuesta = client.get(url, {"q": "destino"})
    assert respuesta.status_code == 200
    assert [
        (resultado.username, len(resultado.asignaciones_tableros))
        for resultado in respuesta.context["pagina"]
    ] == [("destino-a", 3), ("destino-b", 1), ("destino-c", 0)]
    contenido = respuesta.content.decode()
    assert contenido.count("Resumen Progresar") == 4
    assert contenido.count("Individual") == 2
    assert contenido.count("Audiencia: Equipo provincial") == 2
    assert contenido.count("Provincia: Salta") == 2
    assert "Nacional" in contenido
    assert "CDI: ID 123" in contenido
    assert contenido.count("Política de alcance activa") == 3
    assert (
        contenido.count("Asignación registrada. Política de alcance no aplicada.") == 1
    )
    assert contenido.count("Sin asignaciones de tablero registradas.") == 1


def test_estado_del_embed_nacional_en_las_tres_pantallas():
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.create(name="Equipo de Datos"))
    usuario = User.objects.create_user(username="destino")
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    audiencia.agregar_miembro(usuario)
    tablero = Tablero.objects.create(
        nombre="Ejemplo", slug="embed", url="https://example.com/tablero"
    )
    provincia = Provincia.objects.create(nombre="Salta")
    for sujeto in ({"usuario": usuario}, {"audiencia": audiencia}):
        ConcesionTablero.objects.create(tablero=tablero, tipo="nacional", **sujeto)
        ConcesionTablero.objects.create(
            tablero=tablero, tipo="provincia", provincia=provincia, **sujeto
        )
        ConcesionTablero.objects.create(
            tablero=tablero, tipo="cdi", cdi_id=123, **sujeto
        )
    client = Client()
    client.force_login(actor)
    pantallas = (
        (reverse("dashboard_buscar_usuarios_datos"), {"q": "destino"}, 2),
        (reverse("dashboard_asignaciones_usuario", args=[usuario.pk]), {}, 2),
        (reverse("dashboard_audiencia_detalle", args=[audiencia.pk]), {}, 1),
    )

    for url, datos, cantidad in pantallas:
        respuesta = client.get(url, datos)
        assert respuesta.status_code == 200
        contenido = respuesta.content.decode()
        assert (
            contenido.count(
                "Habilita la entrada en SISOC. El filtrado depende del proveedor."
            )
            == cantidad
        )
        assert contenido.count("Política de alcance no aplicada") == cantidad * 2
        assert "Política de alcance activa" not in contenido

    tablero.activo = False
    tablero.save(update_fields=["activo"])
    for url, datos, cantidad in pantallas:
        contenido = client.get(url, datos).content.decode()
        assert "Habilita la entrada en SISOC" not in contenido
        assert contenido.count("Política de alcance no aplicada") == cantidad * 3


@pytest.mark.parametrize("es_staff", [True, False])
def test_head_tambien_exige_rol_en_ambas_rutas(es_staff):
    usuario = User.objects.create_user(username="receptor")
    client = Client(REMOTE_ADDR="203.0.113.42" if es_staff else "127.0.0.1")
    if es_staff:
        actor = User.objects.create_user(username="staff", is_staff=True)
        client.force_login(actor)
    for url in (
        reverse("dashboard_buscar_usuarios_datos"),
        reverse("dashboard_asignaciones_usuario", args=[usuario.pk]),
    ):
        response = client.head(url, HTTP_X_VIEW="1")
        assert response.status_code == 403
        assert "X-View" not in response


def test_asigna_y_revoca_sin_tocar_audiencias_o_roles():
    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    usuario = User.objects.create_user(username="receptor")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    provincia = Provincia.objects.create(nombre="Salta")
    audiencia = AudienciaTableros.objects.create(nombre="Audiencia")
    grant = ConcesionTablero.objects.create(
        audiencia=audiencia, tablero=tablero, tipo="nacional"
    )
    client = Client()
    client.force_login(actor)
    url = reverse("dashboard_asignaciones_usuario", args=[usuario.pk])
    assert client.get(url).status_code == 200
    response = client.post(
        url,
        {
            "accion": "agregar",
            "tablero": tablero.pk,
            "tipo": "provincia",
            "provincias": [provincia.pk],
        },
    )
    assert response.status_code == 302
    directa = ConcesionTablero.objects.get(usuario=usuario, tablero=tablero)
    assert directa.provincia_id == provincia.pk
    response = client.post(
        url, {"accion": "revocar", "tablero": tablero.pk, "concesion": directa.pk}
    )
    assert response.status_code == 302
    assert not ConcesionTablero.objects.filter(pk=directa.pk).exists()
    assert ConcesionTablero.objects.filter(pk=grant.pk).exists()
    assert not usuario.groups.exists()
    content_type = ContentType.objects.get_for_model(ConcesionTablero)
    for accion in (LogEntry.Action.CREATE, LogEntry.Action.DELETE):
        assert LogEntry.objects.filter(
            content_type=content_type,
            object_pk=str(directa.pk),
            actor=actor,
            action=accion,
        ).exists()


def test_no_acepta_cdi_ni_revoca_concesiones_ajenas():
    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    usuario = User.objects.create_user(username="receptor")
    otro = User.objects.create_user(username="otro")
    tablero = Tablero.objects.create(nombre="Uno", slug="uno")
    ajena = ConcesionTablero.objects.create(
        usuario=otro, tablero=tablero, tipo="nacional"
    )
    client = Client()
    client.force_login(actor)
    url = reverse("dashboard_asignaciones_usuario", args=[usuario.pk])
    assert (
        client.post(
            url, {"accion": "agregar", "tablero": tablero.pk, "tipo": "cdi"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            url, {"accion": "revocar", "tablero": tablero.pk, "concesion": ajena.pk}
        ).status_code
        == 400
    )
    assert ConcesionTablero.objects.filter(pk=ajena.pk).exists()
    assert client.post(url, {"accion": "desconocida"}).status_code == 400


def test_indica_si_la_politica_esta_aplicada_por_tablero_y_alcance():
    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    usuario = User.objects.create_user(username="receptor")
    progresar = Tablero.objects.create(
        nombre="Progresar",
        slug="progresar",
        ruta_interna="/dashboard/progresar-curso-obligatorio/",
    )
    otro = Tablero.objects.create(nombre="Otro", slug="otro")
    ConfiguracionTableroInterno.objects.create(
        codigo="progresar_curso", tablero=progresar, activa=True
    )
    ConcesionTablero.objects.create(usuario=usuario, tablero=progresar, tipo="nacional")
    ConcesionTablero.objects.create(
        usuario=usuario, tablero=progresar, tipo="cdi", cdi_id=12
    )
    ConcesionTablero.objects.create(usuario=usuario, tablero=otro, tipo="nacional")
    client = Client()
    client.force_login(actor)
    response = client.get(reverse("dashboard_asignaciones_usuario", args=[usuario.pk]))
    contenido = response.content.decode()
    assert contenido.count("Política de alcance activa") == 1
    assert contenido.count("Política de alcance no aplicada") == 2
    progresar.ruta_interna = "/ruta-incompatible/"
    progresar.save(update_fields=["ruta_interna"])
    response = client.get(reverse("dashboard_asignaciones_usuario", args=[usuario.pk]))
    contenido = response.content.decode()
    assert "Política de alcance activa" not in contenido
    assert contenido.count("Política de alcance no aplicada") == 3


@pytest.mark.django_db
def test_estado_de_alcance_en_usuario_y_audiencia():
    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    usuario = User.objects.create_user(username="destino")
    audiencia = AudienciaTableros.objects.create(nombre="Ejemplo")
    tablero = Tablero.objects.create(
        nombre="Progresar",
        slug="progresar",
        ruta_interna="/dashboard/progresar-curso-obligatorio/",
    )
    configuracion = ConfiguracionTableroInterno.objects.create(
        codigo="progresar_curso", tablero=tablero, activa=True
    )
    provincia = Provincia.objects.create(nombre="Salta")
    for destino in ({"usuario": usuario}, {"audiencia": audiencia}):
        ConcesionTablero.objects.create(tablero=tablero, tipo="nacional", **destino)
        ConcesionTablero.objects.create(
            tablero=tablero, tipo="provincia", provincia=provincia, **destino
        )
        ConcesionTablero.objects.create(
            tablero=tablero, tipo="cdi", cdi_id=123, **destino
        )
    cliente = Client()
    cliente.force_login(actor)
    urls = (
        reverse("dashboard_asignaciones_usuario", args=[usuario.pk]),
        reverse("dashboard_audiencia_detalle", args=[audiencia.pk]),
    )

    def comprobar(activas, no_aplicadas):
        for url in urls:
            respuesta = cliente.get(url)
            assert respuesta.status_code == 200
            contenido = respuesta.content.decode()
            assert contenido.count("Política de alcance activa") == activas
            assert contenido.count("Política de alcance no aplicada") == no_aplicadas

    comprobar(2, 1)
    configuracion.activa = False
    configuracion.save(update_fields=["activa"])
    comprobar(0, 3)
    configuracion.activa = True
    configuracion.save(update_fields=["activa"])
    tablero.activo = False
    tablero.save(update_fields=["activo"])
    comprobar(0, 3)


@pytest.mark.django_db
def test_celiaquia_indica_politica_de_provincias_pero_no_de_cdi():
    call_command("create_groups", verbosity=0)
    actor = User.objects.create_user(username="datos")
    actor.groups.add(Group.objects.get(name="Equipo de Datos"))
    usuario = User.objects.create_user(username="destino")
    tablero = Tablero.objects.create(
        nombre="Celiaquía", slug="celiaquia", ruta_interna="/celiaquia/tablero/"
    )
    config = ConfiguracionTableroInterno.objects.create(
        codigo="celiaquia", tablero=tablero, activa=True
    )
    provincia = Provincia.objects.create(nombre="Salta")
    ConcesionTablero.objects.create(
        tablero=tablero, usuario=usuario, tipo="provincia", provincia=provincia
    )
    ConcesionTablero.objects.create(
        tablero=tablero, usuario=usuario, tipo="cdi", cdi_id=123
    )
    cliente = Client()
    cliente.force_login(actor)
    url = reverse("dashboard_asignaciones_usuario", args=[usuario.pk])
    respuesta = cliente.get(url)
    assert respuesta.content.decode().count("Política de alcance activa") == 1
    assert respuesta.content.decode().count("Política de alcance no aplicada") == 1
    config.activa = False
    config.save(update_fields=["activa"])
    assert cliente.get(url).content.decode().count("Política de alcance activa") == 0
