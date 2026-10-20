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
