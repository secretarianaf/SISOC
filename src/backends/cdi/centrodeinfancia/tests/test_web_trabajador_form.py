"""Web API (G1 v1) of the CDI worker create and edit screens (CDI05).

``/api/web/cdi/centros/<pk>/trabajadores/crear/`` and ``.../<id>/editar/`` run
the native create and update views, so every write goes through
``TrabajadorCDIForm`` and the native save. RENAPER and the user provisioning
are simulated: no real service is ever called.
"""

from datetime import date
from unittest import mock
from urllib.parse import urlencode

import pytest
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from centrodeinfancia.forms import NominaCentroInfanciaDestinatariosForm
from centrodeinfancia.models import (
    AccesoCDI,
    CentroDeInfancia,
    DepartamentoIpi,
    NominaNacionalidad,
    NominaPais,
    Trabajador,
)
from ciudadanos.models import Ciudadano
from core import web_gate
from core.constants import UserGroups
from core.models import Localidad, Municipio, Provincia

ALTA = "centrodeinfancia.add_trabajador"
EDICION = "centrodeinfancia.change_trabajador"
VER_CENTRO = "centrodeinfancia.view_centrodeinfancia"
VETO = "El rol Auditoría tiene acceso de solo lectura."
RENAPER = "centrodeinfancia.views.obtener_datos_ciudadano_desde_renaper"
PROVISION = "centrodeinfancia.views.crear_usuario_trabajador_automaticamente"
SINCRONIZAR = "centrodeinfancia.views.sincronizar_email_trabajador"
WRITES = ("INSERT", "UPDATE", "DELETE")

pytestmark = pytest.mark.django_db


def _crear(centro_pk):
    return f"/api/web/cdi/centros/{centro_pk}/trabajadores/crear/"


def _editar(centro_pk, trabajador_pk):
    return f"/api/web/cdi/centros/{centro_pk}/trabajadores/{trabajador_pk}/editar/"


def _ready(user):
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    return User.objects.get(pk=user.pk)


def _permiso(codigo):
    app, codename = codigo.split(".")
    permiso = Permission.objects.filter(
        content_type__app_label=app, codename=codename
    ).first()
    return permiso or Permission.objects.create(
        content_type=ContentType.objects.get_for_model(Group),
        codename=codename,
        name=codename,
    )


# Un actor con permisos de trabajador necesita además la regla de la Fuerza de
# Trabajo (#2943): por defecto, SIMEPI Equipo Nacional (alcance nacional y solo
# view_trabajador, así no tapa los 403 de alta y edición que se prueban).
def _usuario(
    username,
    *,
    perms=(ALTA, EDICION, VER_CENTRO),
    superuser=False,
    grupos=(UserGroups.SIMEPI_EQUIPO_NACIONAL,),
):
    user = User.objects.create_user(username=username, is_superuser=superuser)
    for codigo in perms:
        user.user_permissions.add(_permiso(codigo))
    for nombre in grupos:
        user.groups.add(Group.objects.get_or_create(name=nombre)[0])
    return _ready(user)


def _cliente(user, **kwargs):
    client = Client(**kwargs)
    client.force_login(user)
    return client


@pytest.fixture(name="datos")
def datos_fixture():
    provincia = Provincia.objects.create(nombre="Mendoza")
    municipio = Municipio.objects.create(nombre="Godoy Cruz", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Villa Hipódromo", municipio=municipio)
    DepartamentoIpi.objects.create(
        codigo_departamento="50001", nombre="Godoy Cruz", provincia=provincia
    )
    NominaPais.objects.create(nombre="Argentina")
    NominaNacionalidad.objects.create(nombre="Argentina")
    centro = CentroDeInfancia.objects.create(
        nombre="CDI Girasoles", provincia=provincia, codigo_cdi="CDI-7"
    )
    otro = CentroDeInfancia.objects.create(nombre="CDI Ajeno", provincia=provincia)
    nacionalidad = next(
        valor
        for valor, _ in NominaCentroInfanciaDestinatariosForm.opciones_nacionalidad()
        if valor
    )
    return {
        "provincia": provincia,
        "municipio": municipio,
        "localidad": localidad,
        "centro": centro,
        "otro": otro,
        "nacionalidad": nacionalidad,
    }


def _payload(datos, **cambios):
    """Every required field of ``TrabajadorCDIForm`` with a valid value."""
    base = {
        "fecha_carga": "2026-09-01",
        "subcomponente": "cdi",
        "funcion_cdi": "educador_docente_sala",
        "sala_cdi": "3_anios",
        "registro_tipo": "alta",
        "nombre": "Lucía",
        "apellido": "Gómez",
        "fecha_nacimiento": "1990-05-06",
        "tipo_documentacion": "dni_permanente",
        "dni": "30111222",
        "sexo_registral": "mujer",
        "cuit": "20-44535030-4",
        "pais_nacimiento": "Argentina",
        "nacionalidad_trabajador": datos["nacionalidad"],
        "nivel_educativo": "primario_completo",
        "anos_trabajo_primera_infancia": "5",
        "tipo_contratacion": "relacion_dependencia",
        "carga_horaria_semanal": "30",
        "email": "lucia@example.test",
        "telefono": "2615551234",
        "calle_contacto": "Calle 1 123",
        "tipo_barrio": "urbano",
        "provincia_contacto": str(datos["provincia"].pk),
        "departamento_contacto": "Godoy Cruz",
        "municipio_contacto": str(datos["municipio"].pk),
        "localidad_contacto": str(datos["localidad"].pk),
        "grupo_pertenencia": ["ninguno"],
        "lenguajes": ["espanol_castellano"],
        "es_interprete": "no",
        "tiene_discapacidad": "no",
    }
    base.update(cambios)
    return base


def _enviar(client, url, datos):
    return client.post(
        url,
        urlencode(datos, doseq=True),
        content_type="application/x-www-form-urlencoded",
    )


def _estado():
    return list(Trabajador.all_objects.order_by("pk").values())


# --- Create: the native page, as JSON ------------------------------------------


def test_create_form_projects_the_native_markup_field_by_field(datos):
    client = _cliente(_usuario("tf-paridad", superuser=True))
    centro = datos["centro"]

    api = client.get(_crear(centro.pk), {"query": "zzzz"})
    nativo = client.get(
        reverse("centrodeinfancia_trabajador_crear", args=[centro.pk]),
        {"query": "zzzz"},
    )

    assert api.status_code == 200
    assert api["Content-Type"] == "application/json"
    assert api["Cache-Control"] == "private, no-store"
    assert "Cookie" in api["Vary"]
    assert "csrftoken" in api.cookies
    data = api.json()
    html = nativo.content.decode()
    assert len(data["fields"]) > 35
    for nombre, campo in data["fields"].items():
        assert campo in html, nombre
    assert set(data["multiples"]) == {
        "capacitaciones_certificadas",
        "grupo_pertenencia",
        "lenguajes",
        "tipo_discapacidad",
    }
    for nombre, grupo in data["multiples"].items():
        for opcion in grupo["options"]:
            assert f'id="{opcion["id"]}"' in html, nombre
            assert f'value="{opcion["value"]}"' in html, nombre
    assert data["is_edit"] is False
    assert data["mostrar_formulario"] is True
    assert data["search"]["query"] == "zzzz"
    assert data["search"]["no_resultados"] is True
    assert data["centro"] == {
        "id": centro.pk,
        "nombre": "CDI Girasoles",
        "url": f"/centrodeinfancia/detalle/{centro.pk}",
        "provincia": "Mendoza",
        "departamento": "-",
        "municipio": "-",
        "localidad": "-",
        "codigo_cdi": "CDI-7",
    }
    assert data["urls"]["cancelar"] == f"/centrodeinfancia/detalle/{centro.pk}"
    assert data["messages"] == []


def test_without_a_search_the_form_stays_hidden_and_a_short_query_opens_the_manual_form(
    datos,
):
    client = _cliente(_usuario("tf-oculto", superuser=True))

    data = client.get(_crear(datos["centro"].pk)).json()
    corto = client.get(_crear(datos["centro"].pk), {"query": "12"}).json()

    assert data["mostrar_formulario"] is False
    assert data["search"]["ciudadanos"] == []
    # Native quirk kept: any query without matches opens the manual form.
    assert corto["mostrar_formulario"] is True


def test_local_citizen_search_lists_results_and_a_selection_prefills(datos):
    Ciudadano.objects.create(apellido="Ramírez", nombre="Sofía", documento=1234567)
    client = _cliente(_usuario("tf-busqueda", superuser=True))
    centro = datos["centro"]

    with mock.patch(RENAPER) as renaper:
        lista = client.get(_crear(centro.pk), {"query": "1234567"}).json()
        ciudadano = Ciudadano.objects.get(documento=1234567)
        elegido = client.get(
            _crear(centro.pk), {"query": "1234567", "ciudadano_id": ciudadano.pk}
        ).json()

    renaper.assert_not_called()
    assert lista["search"]["ciudadanos"] == [
        {
            "id": ciudadano.pk,
            "apellido": "Ramírez",
            "nombre": "Sofía",
            "documento": "1234567",
        }
    ]
    assert lista["mostrar_formulario"] is False
    assert elegido["search"]["selected"]["apellido"] == "Ramírez"
    assert elegido["ciudadano_id"] == ciudadano.pk
    assert elegido["mostrar_formulario"] is True
    assert 'value="Sofía"' in elegido["fields"]["nombre"]
    assert 'value="1234567"' in elegido["fields"]["dni"]


def test_renaper_lookup_is_the_native_one_and_locks_the_verified_fields(datos):
    client = _cliente(_usuario("tf-renaper", superuser=True))
    respuesta = {
        "success": True,
        "message": "Datos obtenidos de RENAPER (simulado).",
        "data": {
            "nombre": "Mara",
            "apellido": "Suárez",
            "dni": 30999888,
            "fecha_nacimiento": "1991-02-03",
            "sexo": "Femenino",
        },
    }

    with mock.patch(RENAPER, return_value=respuesta) as renaper:
        data = client.get(_crear(datos["centro"].pk), {"query": "30999888"}).json()

    renaper.assert_called_once_with("30999888")
    assert data["search"]["renaper_precarga"] is True
    assert data["search"]["renaper_prefill_token"]
    assert 'value="Mara"' in data["fields"]["nombre"]
    assert "disabled" in data["fields"]["nombre"]
    assert "Dato verificado por RENAPER." in data["fields"]["nombre"]
    assert data["messages"] == [
        {"message": "Datos obtenidos de RENAPER (simulado).", "level": "info"}
    ]


def test_the_prefill_token_locks_values_on_post_and_marks_them_verified(datos):
    client = _cliente(_usuario("tf-token", superuser=True))
    centro = datos["centro"]
    respuesta = {
        "success": True,
        "data": {"nombre": "Mara", "apellido": "Suárez", "dni": 30999888},
    }
    with mock.patch(RENAPER, return_value=respuesta):
        token = client.get(_crear(centro.pk), {"query": "30999888"}).json()["search"][
            "renaper_prefill_token"
        ]

    with mock.patch(PROVISION), mock.patch(SINCRONIZAR):
        # The locked fields come from the signed token, never from the POST.
        enviado = _payload(
            datos,
            nombre="Otro",
            apellido="Cambiado",
            dni="30111222",
            renaper_prefill_token=token,
        )
        resultado = _enviar(client, _crear(centro.pk), enviado)

    assert resultado.status_code == 200
    trabajador = Trabajador.objects.get()
    assert (trabajador.nombre, trabajador.apellido, trabajador.dni) == (
        "Mara",
        "Suárez",
        30999888,
    )
    assert set(trabajador.campos_verificados_renaper) == {"nombre", "apellido", "dni"}


# --- Create: writes ---------------------------------------------------------------


def test_valid_create_persists_for_the_scoped_centre_and_follows_the_native_redirect(
    datos,
):
    client = _cliente(_usuario("tf-alta"))
    centro = datos["centro"]

    with mock.patch(PROVISION) as provision, mock.patch(SINCRONIZAR) as sincronizar:
        respuesta = _enviar(client, _crear(centro.pk), _payload(datos))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "ok": True,
        "redirect": f"/centrodeinfancia/detalle/{centro.pk}",
    }
    trabajador = Trabajador.objects.get()
    assert trabajador.centro_id == centro.pk
    assert (trabajador.nombre, trabajador.apellido) == ("Lucía", "Gómez")
    assert trabajador.dni == 30111222
    assert trabajador.cuit == "20445350304"
    assert trabajador.fecha_carga == date(2026, 9, 1)
    assert trabajador.funcion_cdi == "educador_docente_sala"
    assert trabajador.grupo_pertenencia == ["ninguno"]
    assert trabajador.lenguajes == ["espanol_castellano"]
    assert trabajador.campos_verificados_renaper == []
    provision.assert_called_once()
    assert provision.call_args.args[1].pk == trabajador.pk
    sincronizar.assert_called_once()
    siguiente = client.get(f"/api/web/cdi/centros/{centro.pk}/").json()
    assert {"message": "Trabajador agregado correctamente.", "level": "success"} in (
        siguiente["messages"]
    )


def test_a_failed_provisioning_keeps_the_saved_worker_and_reports_the_partial_success(
    datos,
):
    client = _cliente(_usuario("tf-parcial"))
    centro = datos["centro"]

    def falla(request, _trabajador):
        messages.warning(
            request,
            "El trabajador se guardó, pero no se pudo crear su usuario automáticamente.",
        )

    with mock.patch(PROVISION, side_effect=falla) as provision, mock.patch(SINCRONIZAR):
        respuesta = _enviar(client, _crear(centro.pk), _payload(datos))

    assert respuesta.status_code == 200
    assert provision.call_count == 1
    assert Trabajador.objects.count() == 1
    mensajes = client.get(f"/api/web/cdi/centros/{centro.pk}/").json()["messages"]
    assert [m["level"] for m in mensajes] == ["warning", "success"]
    assert mensajes[0]["message"].startswith("El trabajador se guardó, pero")
    assert mensajes[1]["message"] == "Trabajador agregado correctamente."


@pytest.mark.parametrize(
    ("cambios", "campo", "mensaje"),
    [
        ({"nombre": ""}, "nombre", "Este campo es obligatorio."),
        ({"nombre": "A1"}, "nombre", "Ingrese solo letras"),
        ({"subcomponente": "pfpi"}, "funcion_pfpi", "Este campo es obligatorio."),
        ({"sala_cdi": ""}, "sala_cdi", "Este campo es obligatorio."),
        ({"email": ""}, "email", "Este campo es obligatorio para generar el usuario."),
        (
            {"dni": "123"},
            "dni",
            "Ingrese un número de documento válido de 7 u 8 dígitos.",
        ),
        (
            {"fecha_nacimiento": "2999-01-01"},
            "fecha_nacimiento",
            "La fecha de nacimiento no puede ser futura.",
        ),
        (
            {"carga_horaria_semanal": "61"},
            "carga_horaria_semanal",
            "La carga horaria no puede superar las 60 horas semanales.",
        ),
        ({"cuit": "20-11111111-1"}, "cuit", "dígito verificador"),
        (
            {"grupo_pertenencia": ["ninguno", "indigena"]},
            "grupo_pertenencia",
            'No combine "Ninguno de los anteriores"',
        ),
        (
            {"lenguajes": ["no_sabe", "guarani"]},
            "lenguajes",
            'No combine "No sabe" con otros lenguajes.',
        ),
    ],
)
def test_a_rejected_create_is_a_400_with_the_native_errors_and_no_effects(
    datos, cambios, campo, mensaje
):
    client = _cliente(_usuario("tf-rechazo"))
    antes = _estado()

    with mock.patch(PROVISION) as provision, mock.patch(SINCRONIZAR):
        respuesta = _enviar(
            client, _crear(datos["centro"].pk), _payload(datos, **cambios)
        )

    assert respuesta.status_code == 400
    data = respuesta.json()
    assert data["mostrar_formulario"] is True
    if campo in data["multiples"]:
        assert any(mensaje in e for e in data["multiples"][campo]["errors"])
    else:
        assert "is-invalid" in data["fields"][campo]
        assert mensaje in data["fields"][campo]
    assert _estado() == antes
    provision.assert_not_called()


def test_a_rejected_create_keeps_the_typed_values_in_the_markup(datos):
    client = _cliente(_usuario("tf-valores"))

    respuesta = _enviar(
        client, _crear(datos["centro"].pk), _payload(datos, nombre="Ana", dni="1")
    )

    assert respuesta.status_code == 400
    data = respuesta.json()
    assert 'value="Ana"' in data["fields"]["nombre"]
    assert 'value="1"' in data["fields"]["dni"]
    opciones = {
        o["value"]: o["checked"] for o in data["multiples"]["lenguajes"]["options"]
    }
    assert opciones["espanol_castellano"] is True
    assert opciones["guarani"] is False


def test_the_actor_cannot_choose_the_centre_or_unlisted_fields(datos):
    client = _cliente(_usuario("tf-campos"))

    with mock.patch(PROVISION), mock.patch(SINCRONIZAR):
        _enviar(
            client,
            _crear(datos["centro"].pk),
            _payload(datos, centro=str(datos["otro"].pk), usuario="1"),
        )

    trabajador = Trabajador.objects.get()
    # The centre comes from the URL and the form has no user field.
    assert trabajador.centro_id == datos["centro"].pk
    assert trabajador.usuario_id is None


# --- Edit ---------------------------------------------------------------------------


@pytest.fixture(name="trabajador")
def trabajador_fixture(datos):
    return Trabajador.objects.create(
        centro=datos["centro"],
        nombre="Lucía",
        apellido="Gómez",
        fecha_carga=date(2026, 9, 1),
        subcomponente="cdi",
        funcion_cdi="educador_docente_sala",
        sala_cdi="3_anios",
        email="lucia@example.test",
        campos_verificados_renaper=["nombre", "apellido"],
        grupo_pertenencia=["indigena"],
        pueblo_originario="chane",
        lenguajes=["guarani"],
    )


def test_edit_form_shows_the_instance_with_the_locked_fields(datos, trabajador):
    client = _cliente(_usuario("tf-editar-ver"))
    centro = datos["centro"]

    data = client.get(_editar(centro.pk, trabajador.pk)).json()
    nativo = client.get(
        reverse("centrodeinfancia_trabajador_editar", args=[centro.pk, trabajador.pk])
    ).content.decode()

    assert data["is_edit"] is True
    assert data["search"] is None
    assert data["mostrar_formulario"] is True
    assert 'value="Lucía"' in data["fields"]["nombre"]
    assert "disabled" in data["fields"]["nombre"]
    for nombre, campo in data["fields"].items():
        assert campo in nativo, nombre
    opciones = {
        o["value"]: o["checked"]
        for o in data["multiples"]["grupo_pertenencia"]["options"]
    }
    assert opciones["indigena"] is True


def test_valid_edit_updates_the_worker_and_syncs_the_email_only_when_it_changed(
    datos, trabajador
):
    client = _cliente(_usuario("tf-editar"))
    centro = datos["centro"]
    cambios = _payload(
        datos,
        nombre="Lucía",
        apellido="Gómez",
        email="nuevo@example.test",
        carga_horaria_semanal="40",
    )

    with mock.patch(PROVISION) as provision, mock.patch(SINCRONIZAR) as sincronizar:
        respuesta = _enviar(client, _editar(centro.pk, trabajador.pk), cambios)
        otra = _enviar(
            client,
            _editar(centro.pk, trabajador.pk),
            {**cambios, "carga_horaria_semanal": "35"},
        )

    assert respuesta.status_code == 200
    assert respuesta.json()["redirect"] == f"/centrodeinfancia/detalle/{centro.pk}"
    trabajador.refresh_from_db()
    assert trabajador.carga_horaria_semanal == 35
    assert trabajador.email == "nuevo@example.test"
    assert trabajador.centro_id == centro.pk
    assert otra.status_code == 200
    assert provision.call_count == 2
    sincronizar.assert_called_once()
    mensajes = client.get(f"/api/web/cdi/centros/{centro.pk}/").json()["messages"]
    assert (
        mensajes.count(
            {"message": "Trabajador actualizado correctamente.", "level": "success"}
        )
        == 2
    )


def test_a_rejected_edit_changes_nothing(datos, trabajador):
    client = _cliente(_usuario("tf-editar-rechazo"))
    antes = _estado()

    with mock.patch(PROVISION) as provision, mock.patch(SINCRONIZAR):
        respuesta = _enviar(
            client,
            _editar(datos["centro"].pk, trabajador.pk),
            _payload(datos, carga_horaria_semanal="99"),
        )

    assert respuesta.status_code == 400
    assert "is-invalid" in respuesta.json()["fields"]["carga_horaria_semanal"]
    assert _estado() == antes
    provision.assert_not_called()


# --- Scope, permissions and the auditor veto -------------------------------------------


def test_scope_and_nested_ids_are_enforced(datos, trabajador):
    user = _usuario("tf-referente", grupos=[UserGroups.CDI_REFERENTE_CENTRO])
    AccesoCDI.objects.create(user=user, centro=datos["centro"])
    cliente = _cliente(user)
    ajeno = Trabajador.objects.create(
        centro=datos["otro"], nombre="Eva", apellido="Sol"
    )
    antes = _estado()

    assert cliente.get(_crear(datos["centro"].pk)).status_code == 200
    assert cliente.get(_editar(datos["centro"].pk, trabajador.pk)).status_code == 200
    # Centre outside the scope, worker of another centre and a mixed pair: 404, no write.
    assert cliente.get(_crear(datos["otro"].pk)).status_code == 404
    assert (
        _enviar(cliente, _crear(datos["otro"].pk), _payload(datos)).status_code == 404
    )
    assert cliente.get(_editar(datos["otro"].pk, ajeno.pk)).status_code == 404
    assert cliente.get(_editar(datos["centro"].pk, ajeno.pk)).status_code == 404
    assert (
        _enviar(
            cliente, _editar(datos["centro"].pk, ajeno.pk), _payload(datos)
        ).status_code
        == 404
    )
    assert cliente.get(_editar(datos["centro"].pk, 999999)).status_code == 404
    assert _estado() == antes


def test_the_url_permission_is_required_for_each_screen(datos, trabajador):
    solo_alta = _cliente(_usuario("tf-solo-alta", perms=(ALTA,)))
    solo_edicion = _cliente(_usuario("tf-solo-edicion", perms=(EDICION,)))
    otro = _cliente(_usuario("tf-otro-permiso", perms=(VER_CENTRO,)))
    centro = datos["centro"]
    antes = _estado()

    assert solo_alta.get(_crear(centro.pk)).status_code == 200
    assert solo_alta.get(_editar(centro.pk, trabajador.pk)).status_code == 403
    assert solo_edicion.get(_crear(centro.pk)).status_code == 403
    assert _enviar(solo_edicion, _crear(centro.pk), _payload(datos)).status_code == 403
    assert solo_edicion.get(_editar(centro.pk, trabajador.pk)).status_code == 200
    assert otro.get(_crear(centro.pk)).status_code == 403
    assert (
        _enviar(otro, _editar(centro.pk, trabajador.pk), _payload(datos)).status_code
        == 403
    )
    assert _estado() == antes


@pytest.mark.parametrize(
    "grupos",
    [
        [UserGroups.SIMEPI_AUDITORIA],
        [UserGroups.SIMEPI_AUDITORIA, UserGroups.SIMEPI_EGP],
    ],
    ids=["auditoria", "auditoria_egp"],
)
def test_auditor_mutations_are_rejected_without_effects(datos, trabajador, grupos):
    client = _cliente(_usuario("tf-veto-" + str(len(grupos)), grupos=grupos))
    centro = datos["centro"]
    antes = _estado()

    with mock.patch(PROVISION) as provision, mock.patch(SINCRONIZAR):
        alta = _enviar(client, _crear(centro.pk), _payload(datos))
        edicion = _enviar(client, _editar(centro.pk, trabajador.pk), _payload(datos))
        lectura = client.get(_crear(centro.pk))

    assert alta.status_code == 403
    assert alta.json() == {"detail": VETO}
    assert edicion.status_code == 403
    assert edicion.json() == {"detail": VETO}
    assert lectura.status_code == 200
    assert _estado() == antes
    provision.assert_not_called()


def test_reads_never_write(datos, trabajador):
    client = _cliente(_usuario("tf-lectura", superuser=True))
    client.get(_editar(datos["centro"].pk, trabajador.pk))

    with CaptureQueriesContext(connection) as queries:
        assert client.get(_editar(datos["centro"].pk, trabajador.pk)).status_code == 200
        assert (
            client.get(_crear(datos["centro"].pk), {"query": "zzzz"}).status_code == 200
        )

    assert not [
        q["sql"] for q in queries.captured_queries if q["sql"].startswith(WRITES)
    ]


def test_csrf_format_and_methods_are_enforced(datos, trabajador):
    user = _usuario("tf-transporte")
    estricto = _cliente(user, enforce_csrf_checks=True)
    client = _cliente(user)
    centro = datos["centro"]
    antes = _estado()

    assert estricto.post(_crear(centro.pk), _payload(datos)).status_code == 403
    assert (
        client.post(
            _crear(centro.pk), "{}", content_type="application/json"
        ).status_code
        == 415
    )
    assert client.put(_crear(centro.pk)).status_code == 405
    assert client.delete(_editar(centro.pk, trabajador.pk)).status_code == 405
    assert _estado() == antes


def test_anonymous_gets_401_json_and_the_pending_requirement_is_reported(datos):
    destino = _crear(datos["centro"].pk)

    anonimo = Client().get(destino)
    pendiente = _usuario("tf-pendiente", superuser=True)
    pendiente.profile.must_change_password = True
    pendiente.profile.save()
    cliente = _cliente(pendiente)
    falso = web_gate.sign(
        audience="cdi",
        user_pk=pendiente.pk,
        session_key=cliente.cookies[settings.SESSION_COOKIE_NAME].value,
        method="GET",
        target=destino,
    )
    rechazo = cliente.get(destino, HTTP_X_SISOC_WEB_GATE=falso, RAW_URI=destino)

    assert anonimo.status_code == 401
    assert anonimo.json() == {"detail": web_gate.DETAIL_UNAUTHENTICATED}
    assert rechazo.status_code == 403
    assert rechazo.json()["detail"] == web_gate.DETAIL_REQUIREMENT


def test_admindocs_head_does_not_bypass_the_web_api(datos):
    staff = User.objects.create_user("tf-staff", is_staff=True)

    respuesta = _cliente(_ready(staff)).head(_crear(datos["centro"].pk))

    assert "X-View" not in respuesta
    assert respuesta.status_code == 403


# --- Runtime: only the core's signed attestation reaches the view -----------------------


@pytest.fixture(name="runtime")
def runtime_fixture():
    with override_settings(
        SISOC_BACKEND="cdi",
        ROOT_URLCONF="cdi_runtime.urls",
        SISOC_BACKENDS={},
        INTERNAL_IPS=[],
    ):
        yield


def _signed(user, client, target, *, method="GET", now=None, audience="cdi"):
    return web_gate.sign(
        audience=audience,
        user_pk=user.pk,
        session_key=client.cookies[settings.SESSION_COOKIE_NAME].value,
        method=method,
        target=target,
        now=now,
    )


@pytest.mark.usefixtures("runtime")
def test_runtime_serves_a_signed_request_and_rejects_bad_ones(datos):
    user = _usuario("tf-runtime", superuser=True)
    client = _cliente(user)
    destino = _crear(datos["centro"].pk)
    valido = _signed(user, client, destino)

    ok = client.get(destino, RAW_URI=destino, HTTP_X_SISOC_WEB_GATE=valido)

    assert ok.status_code == 200
    assert ok.json()["is_edit"] is False
    alterados = {
        "missing": None,
        "other_target": _signed(user, client, destino + "?x=1"),
        "other_audience": _signed(user, client, destino, audience="inspecciones"),
        "other_method": _signed(user, client, destino, method="POST"),
        "expired": _signed(user, client, destino, now=timezone.now().timestamp() - 61),
    }
    for motivo, token in alterados.items():
        extra = {"RAW_URI": destino}
        if token is not None:
            extra["HTTP_X_SISOC_WEB_GATE"] = token
        rechazo = client.get(destino, **extra)
        assert rechazo.status_code == 403, motivo
        assert rechazo.json() == {"detail": web_gate.DETAIL_REJECTED}, motivo


@pytest.mark.usefixtures("runtime")
def test_runtime_keeps_the_permission_and_the_auditor_veto_after_a_valid_attestation(
    datos,
):
    destino = _crear(datos["centro"].pk)
    sin = _usuario("tf-runtime-sin", perms=())
    auditor = _usuario("tf-runtime-auditor", grupos=[UserGroups.SIMEPI_AUDITORIA])
    c_sin, c_aud = _cliente(sin), _cliente(auditor)

    denegado = c_sin.get(
        destino, RAW_URI=destino, HTTP_X_SISOC_WEB_GATE=_signed(sin, c_sin, destino)
    )
    veto = c_aud.post(
        destino,
        urlencode(_payload(datos)),
        content_type="application/x-www-form-urlencoded",
        RAW_URI=destino,
        HTTP_X_SISOC_WEB_GATE=_signed(auditor, c_aud, destino, method="POST"),
    )

    assert denegado.status_code == 403
    assert denegado.json() != {"detail": web_gate.DETAIL_REJECTED}
    assert veto.status_code == 403
    assert veto.json() == {"detail": VETO}
    assert not Trabajador.objects.exists()
