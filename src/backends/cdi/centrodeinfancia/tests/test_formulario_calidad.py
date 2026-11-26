"""Formulario de Calidad de los CDI (200_CalidadCDI)."""

import pytest
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.urls import reverse

from centrodeinfancia.access import (
    puede_editar_formulario_calidad,
    puede_ver_formularios_calidad,
)
from centrodeinfancia.formulario_calidad_schema import (
    CHECKBOX,
    GRILLA,
    MATRIZ_NUMERICA,
    NUMERO,
    PREGUNTAS,
    PREGUNTAS_POR_NUMERO,
    campos_respuesta,
)
from centrodeinfancia.models import (
    AccesoCDI,
    CentroDeInfancia,
    FormularioCalidadCDI,
    Trabajador,
)
from centrodeinfancia.services_formulario_calidad import (
    MENSAJE_CHECKBOX,
    MENSAJE_ESPECIFICAR,
    MENSAJE_FILAS_INCOMPLETAS,
    FormularioIncompletoError,
    enviar_formulario,
    errores_de_completitud,
    guardar_borrador,
    limpiar_respuestas_ocultas,
)
from core.constants import UserGroups
from core.models import Provincia
from users.services_group_permissions import sync_permissions_for_group


def _respuestas_completas():
    """Valores de modelo que responden todo con la primera opción."""
    valores = {}
    for pregunta in PREGUNTAS:
        for nombre in pregunta.campos:
            if pregunta.tipo == CHECKBOX:
                valores[nombre] = nombre == pregunta.campos[0]
            elif pregunta.tipo == NUMERO:
                valores[nombre] = 4
            elif pregunta.tipo == MATRIZ_NUMERICA:
                valores[nombre] = "12.50"
            else:
                valores[nombre] = 1
        if pregunta.campo_especificar:
            valores[pregunta.campo_especificar] = "detalle"
    return valores


def _payload_completo():
    payload = {}
    for nombre, valor in _respuestas_completas().items():
        if valor is True:
            payload[nombre] = "on"
        elif valor is not False:
            payload[nombre] = str(valor)
    return payload


def _crear_usuario(username, *grupos):
    user = User.objects.create_user(username=username, password="test1234")
    for nombre in grupos:
        group, _ = Group.objects.get_or_create(name=nombre)
        sync_permissions_for_group(group)
        user.groups.add(group)
    return user


@pytest.fixture
def centro():
    provincia = Provincia.objects.create(nombre="Chaco")
    return CentroDeInfancia.objects.create(nombre="CDI Calidad", provincia=provincia)


@pytest.fixture
def referente(centro):
    user = _crear_usuario("referente-calidad", UserGroups.CDI_REFERENTE_CENTRO)
    AccesoCDI.objects.create(user=user, centro=centro)
    return user


# --- Schema -------------------------------------------------------------------


def test_schema_tiene_las_103_preguntas_en_orden():
    assert [pregunta.numero for pregunta in PREGUNTAS] == list(range(1, 104))


def test_schema_columnas_respetan_la_matriz_sql():
    columnas = {
        field.name: field.db_column for field in FormularioCalidadCDI._meta.fields
    }
    assert columnas["p1_inf_tenencia_tipo"] == "1_INF_TENENCIA_TIPO"
    assert columnas["p1_inf_tenencia_otro"] == "1_INF_TENENCIA_OTRO"
    assert columnas["p17_esp_sup_lact"] == "17_ESP_SUP_LACT"
    assert columnas["p97_art_i_a_planif"] == "97_ART_i_a_PLANIF"
    assert columnas["p101_acc_tipo_pers_lsa"] == "101_ACC_TIPO_PERS_LSA"
    assert columnas["p101_acc_tipo_otro_text"] == "101_ACC_TIPO_OTRO_TEXT"
    assert columnas["p103_incl_juegos_ext_adapt"] == "103_INCL_JUEGOS_EXT_ADAPT"
    assert columnas["centro"] == "0_CDI_ID"
    assert columnas["jurisdiccion"] == "0_Jurisdiccion_ID"
    assert columnas["departamento"] == "0_Departamento_ID"
    assert columnas["enviado_por"] == "0_User_ID"
    assert columnas["fecha_envio"] == "0_Timestamp"
    db_columns = [columnas[nombre] for nombre in campos_respuesta()]
    assert len(db_columns) == len(set(db_columns))


def test_grillas_de_articulacion_tienen_15_entidades():
    for numero in (97, 98, 99):
        pregunta = PREGUNTAS_POR_NUMERO[numero]
        assert pregunta.tipo == GRILLA
        assert len(pregunta.filas) == 15


# --- Servicio -----------------------------------------------------------------


def test_limpiar_respuestas_ocultas_vacia_las_preguntas_salteadas():
    formulario = FormularioCalidadCDI(
        p20_esp_descanso_disp=5,
        p21_esp_descanso_reg=2,
        p51_prot_salud_existe=2,
        p52_prot_salud_aspectos_emerg=True,
        p1_inf_tenencia_tipo=1,
        p1_inf_tenencia_otro="no aplica",
    )

    limpiar_respuestas_ocultas(formulario)

    assert formulario.p21_esp_descanso_reg is None
    assert formulario.p52_prot_salud_aspectos_emerg is False
    assert formulario.p1_inf_tenencia_otro is None


def test_completitud_no_exige_preguntas_salteadas():
    valores = _respuestas_completas()
    valores.update(
        p34_eqp_juegos_ext=2,
        p35_eqp_juegos_estado=None,
        p36_eqp_juegos_disp=None,
    )
    formulario = FormularioCalidadCDI(**valores)

    assert errores_de_completitud(formulario) == {}


def test_completitud_detecta_faltantes_por_tipo():
    valores = _respuestas_completas()
    valores.update(
        p1_inf_tenencia_tipo=7,
        p1_inf_tenencia_otro="",
        p22_mat_suf_iii=None,
        p90_fam_com_cuaderno=False,
    )
    valores["p16_esp_cant_amb"] = None
    formulario = FormularioCalidadCDI(**valores)

    errores = errores_de_completitud(formulario)

    assert errores[1] == MENSAJE_ESPECIFICAR
    assert errores[22] == MENSAJE_FILAS_INCOMPLETAS
    assert errores[90] == MENSAJE_CHECKBOX
    assert 16 in errores


def test_p101_otros_exige_especificar():
    valores = _respuestas_completas()
    valores.update(
        p100_acc_elementos_existe=1,
        p101_acc_tipo_otros=True,
        p101_acc_tipo_otro_text="",
    )
    formulario = FormularioCalidadCDI(**valores)

    assert errores_de_completitud(formulario)[101] == MENSAJE_ESPECIFICAR

    formulario.p101_acc_tipo_otros = False
    limpiar_respuestas_ocultas(formulario)

    assert 101 not in errores_de_completitud(formulario)
    assert formulario.p101_acc_tipo_otro_text is None


@pytest.mark.django_db
def test_enviar_completo_registra_metadatos_y_queda_inmutable(centro, referente):
    formulario = FormularioCalidadCDI(**_respuestas_completas())

    enviar_formulario(formulario, centro, referente)
    formulario.refresh_from_db()

    assert formulario.estado == FormularioCalidadCDI.Estado.ENVIADO
    assert formulario.fecha_envio is not None
    assert formulario.enviado_por == referente
    assert formulario.jurisdiccion_id == centro.provincia_id
    formulario.p2_inf_elec_tipo = 3
    with pytest.raises(ValidationError):
        formulario.save()
    with pytest.raises(ValidationError):
        formulario.delete()


@pytest.mark.django_db
def test_enviar_incompleto_guarda_el_avance_como_borrador(centro, referente):
    formulario = FormularioCalidadCDI(p1_inf_tenencia_tipo=1)

    with pytest.raises(FormularioIncompletoError) as exc:
        enviar_formulario(formulario, centro, referente)

    guardado = FormularioCalidadCDI.objects.get(pk=formulario.pk)
    assert guardado.estado == FormularioCalidadCDI.Estado.BORRADOR
    assert guardado.p1_inf_tenencia_tipo == 1
    assert 1 not in exc.value.errores
    assert 2 in exc.value.errores


# --- Permisos -----------------------------------------------------------------


@pytest.mark.django_db
def test_director_trabajador_edita_y_trabajador_comun_no_ve(centro):
    director = _crear_usuario("director-calidad", UserGroups.CDI_TRABAJADOR)
    Trabajador.objects.create(
        centro=centro,
        usuario=director,
        nombre="Dora",
        apellido="Directora",
        rol=Trabajador.Rol.DIRECTOR,
    )
    trabajador = _crear_usuario("trabajador-calidad", UserGroups.CDI_TRABAJADOR)
    Trabajador.objects.create(
        centro=centro,
        usuario=trabajador,
        nombre="Pablo",
        apellido="Profesor",
        rol=Trabajador.Rol.PROFESOR,
    )

    assert puede_editar_formulario_calidad(director, centro)
    assert not puede_editar_formulario_calidad(trabajador, centro)
    assert not puede_ver_formularios_calidad(trabajador, centro)


@pytest.mark.django_db
def test_simepi_ve_pero_no_edita(centro, referente):
    egp = _crear_usuario("egp-calidad", UserGroups.SIMEPI_EGP)
    auditor = _crear_usuario("auditor-calidad", UserGroups.SIMEPI_AUDITORIA)

    assert puede_editar_formulario_calidad(referente, centro)
    for user in (egp, auditor):
        assert puede_ver_formularios_calidad(user, centro)
        assert not puede_editar_formulario_calidad(user, centro)


# --- Vistas -------------------------------------------------------------------


@pytest.mark.django_db
def test_guardar_crea_borrador_y_luego_se_continua(client, centro, referente):
    client.force_login(referente)
    url = reverse("centrodeinfancia_calidad_cargar", kwargs={"pk": centro.pk})

    response = client.get(url)
    assert response.status_code == 200
    assert "Seleccione la o las opciones" in response.content.decode()

    response = client.post(url, {"accion": "guardar", "p2_inf_elec_tipo": "3"})
    assert response.status_code == 302
    borrador = FormularioCalidadCDI.objects.get(centro=centro)
    assert borrador.estado == FormularioCalidadCDI.Estado.BORRADOR

    client.post(url, {"accion": "guardar", "p3_inf_elec_estado": "1"})
    borrador.refresh_from_db()
    assert FormularioCalidadCDI.objects.filter(centro=centro).count() == 1
    assert borrador.p3_inf_elec_estado == 1


@pytest.mark.django_db
def test_enviar_incompleto_marca_pendientes(client, centro, referente):
    client.force_login(referente)
    url = reverse("centrodeinfancia_calidad_cargar", kwargs={"pk": centro.pk})

    response = client.post(url, {"accion": "enviar", "p2_inf_elec_tipo": "1"})

    assert response.status_code == 200
    assert 'id="seccion-infraestructura"' in response.content.decode()
    assert response.context["errores"][1]
    assert 2 not in response.context["errores"]


@pytest.mark.django_db
def test_enviar_completo_redirige_al_detalle_y_aparece_en_legajo(
    client, centro, referente
):
    client.force_login(referente)
    url = reverse("centrodeinfancia_calidad_cargar", kwargs={"pk": centro.pk})

    response = client.post(url, {"accion": "enviar", **_payload_completo()})

    formulario = FormularioCalidadCDI.objects.get(centro=centro)
    assert formulario.estado == FormularioCalidadCDI.Estado.ENVIADO
    assert response.url == reverse(
        "centrodeinfancia_calidad_detalle",
        kwargs={"pk": centro.pk, "form_pk": formulario.pk},
    )
    detalle = client.get(response.url)
    assert detalle.status_code == 200
    legajo = client.get(reverse("centrodeinfancia_detalle", kwargs={"pk": centro.pk}))
    assert "Formulario de Calidad" in legajo.content.decode()


@pytest.mark.django_db
def test_trabajador_no_director_no_accede(client, centro):
    trabajador = _crear_usuario("trabajador-vista", UserGroups.CDI_TRABAJADOR)
    Trabajador.objects.create(
        centro=centro, usuario=trabajador, nombre="Ana", apellido="Aux"
    )
    client.force_login(trabajador)

    listado = client.get(
        reverse("centrodeinfancia_calidad_listado", kwargs={"pk": centro.pk})
    )
    cargar = client.get(
        reverse("centrodeinfancia_calidad_cargar", kwargs={"pk": centro.pk})
    )

    assert listado.status_code == 403
    assert cargar.status_code == 403


@pytest.mark.django_db
def test_borrador_no_se_ve_en_el_detalle(client, centro, referente):
    borrador = guardar_borrador(FormularioCalidadCDI(), centro, referente)
    client.force_login(referente)

    response = client.get(
        reverse(
            "centrodeinfancia_calidad_detalle",
            kwargs={"pk": centro.pk, "form_pk": borrador.pk},
        )
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_valor_invalido_marca_la_pregunta(client, centro, referente):
    client.force_login(referente)
    url = reverse("centrodeinfancia_calidad_cargar", kwargs={"pk": centro.pk})

    response = client.post(url, {"accion": "guardar", "p17_esp_sup_lact": "99999"})

    assert response.status_code == 200
    assert not FormularioCalidadCDI.objects.filter(centro=centro).exists()
    preguntas = {
        item["pregunta"].numero: item
        for seccion in response.context["secciones"]
        for item in seccion["preguntas"]
    }
    assert preguntas[17]["error"]
    assert not preguntas[16]["error"]


@pytest.mark.django_db
def test_web_calidad_history_and_detail_preserve_native_scope(
    client, centro, referente
):
    sent = FormularioCalidadCDI.objects.create(
        centro=centro, estado=FormularioCalidadCDI.Estado.ENVIADO, enviado_por=referente
    )
    draft = FormularioCalidadCDI.objects.create(centro=centro)
    client.force_login(referente)
    history = f"/api/web/cdi/centros/{centro.pk}/calidad/"

    response = client.get(history)
    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]
    assert response.json()["rows"] == [
        {
            "id": sent.pk,
            "fecha_envio": "",
            "enviado_por": referente.username,
            "url": reverse(
                "centrodeinfancia_calidad_detalle", args=[centro.pk, sent.pk]
            ),
        }
    ]
    assert response.json()["borrador_modificado"]
    assert client.get(f"{history}{sent.pk}/").status_code == 200
    assert client.get(f"{history}{draft.pk}/").status_code == 404
    assert client.get(history, {"page": 2}).status_code == 404


@pytest.mark.django_db
def test_web_calidad_form_saves_partial_and_returns_incomplete_send(
    client, centro, referente
):
    client.force_login(referente)
    entry = f"/api/web/cdi/centros/{centro.pk}/calidad/cargar/"

    response = client.get(entry)
    assert response.status_code == 200
    assert "csrftoken" in response.cookies
    assert response.json()["secciones"][0]["preguntas"][0]["numero"] == 1
    assert not response.json()["es_borrador_existente"]

    payload = "accion=enviar&p1_inf_tenencia_tipo=1"
    incomplete = client.post(
        entry, payload, content_type="application/x-www-form-urlencoded"
    )
    assert incomplete.status_code == 400
    assert incomplete.json()["es_borrador_existente"]
    assert incomplete.json()["errores"]
    assert not FormularioCalidadCDI.objects.filter(
        centro=centro, estado=FormularioCalidadCDI.Estado.ENVIADO, enviado_por=referente
    ).exists()

    saved = client.post(
        entry,
        "accion=guardar&p1_inf_tenencia_tipo=1",
        content_type="application/x-www-form-urlencoded",
    )
    assert saved.json() == {
        "ok": True,
        "redirect": reverse("centrodeinfancia_detalle", args=[centro.pk]),
    }


@pytest.mark.django_db
def test_calidad_preview_uses_react_for_three_exact_urls_and_native_without_build(
    client, centro, referente, tmp_path, settings
):
    from types import ModuleType

    from config.urls_all import urlpatterns
    from core.react_activation import react_preview_patterns

    (tmp_path / "index.html").write_text(
        '<html><script src="/v2/sisoc/assets/synthetic.js"></script></html>',
        encoding="utf-8",
    )
    settings.SISOC_REACT_BUILD_DIR = str(tmp_path)
    settings.REACT_VERTICALES_ACTIVAS = ("cdi",)
    urlconf = ModuleType("calidad_preview_urls")
    urlconf.urlpatterns = react_preview_patterns("cdi") + urlpatterns
    settings.ROOT_URLCONF = urlconf
    sent = FormularioCalidadCDI.objects.create(
        centro=centro, estado=FormularioCalidadCDI.Estado.ENVIADO, enviado_por=referente
    )
    client.force_login(referente)
    urls = [
        reverse("centrodeinfancia_calidad_listado", args=[centro.pk]),
        reverse("centrodeinfancia_calidad_cargar", args=[centro.pk]),
        reverse("centrodeinfancia_calidad_detalle", args=[centro.pk, sent.pk]),
    ]
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200
        assert b"/centrodeinfancia/react/assets/synthetic.js" in response.content

    settings.REACT_VERTICALES_ACTIVAS = ("ninguna",)
    native_urlconf = ModuleType("calidad_native_urls")
    native_urlconf.urlpatterns = react_preview_patterns("cdi") + urlpatterns
    settings.ROOT_URLCONF = native_urlconf
    assert (
        b"/centrodeinfancia/react/assets/synthetic.js"
        not in client.get(urls[0]).content
    )


@pytest.mark.django_db
def test_web_calidad_post_preserves_ownership_csrf_and_immutable_send(
    client, centro, referente
):
    from urllib.parse import urlencode

    from django.test import Client

    secured = Client(enforce_csrf_checks=True)
    history = f"/api/web/cdi/centros/{centro.pk}/calidad/"
    entry = f"{history}cargar/"
    payload = urlencode({"accion": "enviar", **_payload_completo()})
    assert secured.get(history).status_code == 401

    trabajador = _crear_usuario("trabajador-web-calidad", UserGroups.CDI_TRABAJADOR)
    Trabajador.objects.create(
        centro=centro, usuario=trabajador, nombre="Ana", apellido="Aux"
    )
    client.force_login(trabajador)
    assert client.get(entry).status_code == 403
    assert (
        client.post(
            entry, payload, content_type="application/x-www-form-urlencoded"
        ).status_code
        == 403
    )

    secured.force_login(referente)
    another = CentroDeInfancia.objects.create(nombre="CDI fuera de alcance")
    assert secured.get(f"/api/web/cdi/centros/{another.pk}/calidad/").status_code == 404
    assert (
        secured.post(
            entry, payload, content_type="application/x-www-form-urlencoded"
        ).status_code
        == 403
    )
    assert not FormularioCalidadCDI.objects.exists()

    token = secured.get(entry).cookies["csrftoken"].value
    result = secured.post(
        entry,
        payload,
        content_type="application/x-www-form-urlencoded",
        HTTP_X_CSRFTOKEN=token,
    )
    assert result.status_code == 200
    sent = FormularioCalidadCDI.objects.get()
    assert sent.estado == FormularioCalidadCDI.Estado.ENVIADO
    assert sent.enviado_por == referente
    assert result.json()["redirect"] == reverse(
        "centrodeinfancia_calidad_detalle",
        args=[centro.pk, sent.pk],
    )
    assert secured.get(f"{history}{sent.pk}/").json()["id"] == sent.pk
    assert (
        secured.post(
            f"{history}{sent.pk}/",
            payload,
            content_type="application/x-www-form-urlencoded",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 405
    )
    assert FormularioCalidadCDI.objects.count() == 1
