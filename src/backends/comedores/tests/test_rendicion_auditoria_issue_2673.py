import re
from datetime import date
from importlib import import_module
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.db import connection
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import Permission
from django.template import Context
from django.template.loader import get_template
from django.template.loader_tags import BlockNode

from comedores.models import Comedor
from organizaciones.models import Organizacion, ProyectoOrganizacion
from rendicioncuentasmensual.auditoria import (
    AuditoriaBusquedaForm,
    AuditoriaForm,
    AuditoriaService,
)
from rendicioncuentasmensual.forms import RendicionCuentaMensualForm
from rendicioncuentasmensual.models import RendicionCuentaMensual
from rendicioncuentasmensual.services import (
    RendicionCuentaMensualService,
    RendicionProcesoService,
)


@pytest.fixture
def proyecto(db):
    return ProyectoOrganizacion.objects.create(
        organizacion=Organizacion.objects.create(nombre="Organización Auditoría"),
        codigo="AUD-2673",
        nombre="Proyecto Auditoría",
    )


def crear_rendicion(proyecto, **kwargs):
    return RendicionCuentaMensual.objects.create(
        **{
            "mes": 9,
            "anio": 2026,
            "proyecto": proyecto,
            "convenio": "P01",
            "numero_rendicion": 1,
            "periodo_inicio": date(2026, 9, 1),
            "periodo_fin": date(2026, 9, 30),
            "etapa_proceso": "auditoria",
            "subestado_proceso": "pendiente",
            "validada": None,
            "genera_acta_auditoria": None,
            **kwargs,
        }
    )


@pytest.mark.django_db
def test_guarda_validacion_sin_acta_y_sin_montos(proyecto, superuser):
    rendicion = crear_rendicion(proyecto)
    form = AuditoriaForm(
        {"validada": "True", "genera_acta_auditoria": "False"}, rendicion=rendicion
    )
    assert form.is_valid(), form.errors
    AuditoriaService.guardar(
        rendicion=rendicion, datos=form.cleaned_data, actor=superuser
    )
    rendicion.refresh_from_db()
    assert rendicion.validada is True
    assert rendicion.genera_acta_auditoria is False
    assert rendicion.fecha_gestion_auditoria is not None
    assert rendicion.subestado_proceso == "en_curso"
    assert rendicion.fecha_auditada is None
    assert rendicion.monto_rendido is None
    assert not AuditoriaService.disponibles().filter(pk=rendicion.pk).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("decision", [None, "", "desconocido"])
def test_rechaza_validacion_sin_decision_de_acta(proyecto, superuser, decision):
    rendicion = crear_rendicion(proyecto)
    datos = {"validada": True}
    if decision is not None:
        datos["genera_acta_auditoria"] = decision
    with pytest.raises(ValidationError, match="genera_acta_auditoria"):
        AuditoriaService.guardar(rendicion=rendicion, datos=datos, actor=superuser)
    rendicion.refresh_from_db()
    assert rendicion.validada is None
    assert rendicion.fecha_gestion_auditoria is None


@pytest.mark.django_db
@pytest.mark.parametrize("decision", [None, False, True])
def test_decision_acta_solo_si_no_y_no_por_defecto(proyecto, decision):
    rendicion = crear_rendicion(proyecto, genera_acta_auditoria=decision)
    form = AuditoriaForm(
        rendicion=rendicion, initial={"genera_acta_auditoria": decision}
    )
    assert list(form.fields["genera_acta_auditoria"].choices) == [
        (False, "No"),
        (True, "Sí"),
    ]
    assert form["genera_acta_auditoria"].value() is (
        False if decision is None else decision
    )
    assert form.fields["genera_acta_auditoria"].required


@pytest.mark.parametrize("validada,acta", [(None, None), (True, False), (True, True)])
@pytest.mark.parametrize(
    "plantilla", ["organizacion_detail.html", "organizacion_rendicion_detail.html"]
)
def test_legajo_refleja_validacion_y_acta_sin_inferir_desde_etapa(
    plantilla, validada, acta
):
    rendicion = RendicionCuentaMensual(
        id=1,
        mes=9,
        anio=2026,
        validada=validada,
        genera_acta_auditoria=acta,
        etapa_proceso="regularizacion",
        fecha_carga_auditoria=timezone.now(),
    )
    template = get_template(plantilla).template
    contenido = next(
        bloque
        for bloque in template.nodelist.get_nodes_by_type(BlockNode)
        if bloque.name == "content"
    )
    contexto = Context(
        {
            "organizacion": Organizacion(id=1, nombre="Organización sintética"),
            "rendicion": rendicion,
            "rendiciones_presentadas": [rendicion],
        }
    )
    with contexto.bind_template(template):
        html = contenido.render(contexto)
    assert "Cargada para Auditoría" not in html
    if plantilla == "organizacion_detail.html":
        tabla_rendiciones = html.split("<th>Validación</th>", 1)[1]
        celdas = re.findall(r"<td[^>]*>\s*(.*?)\s*</td>", tabla_rendiciones, re.DOTALL)
        assert celdas[5] == ("✔" if validada else "-")
        assert celdas[6] == ("✔" if acta else "-")
    else:
        assert re.search(
            r"Validación</small><strong>\s*" + ("Sí" if validada else "No"), html
        )
        assert re.search(
            r"Auditada</small><strong>\s*" + ("Sí" if acta else "No"), html
        )
        fecha_validacion = re.search(
            r"Fecha de Validación</small><strong>\s*(.*?)\s*</strong>", html
        ).group(1)
        assert (fecha_validacion == "-") is (not validada)


@pytest.mark.parametrize("decision", [None, False, True])
@pytest.mark.parametrize("etapa", ["auditoria", "regularizacion"])
@pytest.mark.parametrize("con_fecha", [False, True])
def test_auditada_refleja_decision_de_acta_o_fecha_si_no_hay_decision(
    decision, etapa, con_fecha
):
    rendicion = RendicionCuentaMensual(
        genera_acta_auditoria=decision,
        etapa_proceso=etapa,
        subestado_proceso="finalizada",
        fecha_auditada=timezone.now() if con_fecha else None,
    )
    # Sin decision registrada (historicas o Linea Secos) vale la fecha de auditoria.
    esperado = con_fecha if decision is None else decision
    assert rendicion.auditada is esperado


def crear_sin_acta(proyecto, **kwargs):
    return crear_rendicion(
        proyecto,
        **{
            "validada": True,
            "genera_acta_auditoria": False,
            "fecha_gestion_auditoria": timezone.now(),
            "subestado_proceso": "en_curso",
            **kwargs,
        },
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "datos,campo",
    [
        ({"genera_acta_auditoria": "False"}, "validada"),
        (
            {
                "validada": "False",
                "genera_acta_auditoria": "True",
                "resultado": "finalizada",
            },
            "validada",
        ),
        ({"validada": "True", "genera_acta_auditoria": "True"}, "resultado"),
        (
            {
                "validada": "True",
                "genera_acta_auditoria": "False",
                "resultado": "finalizada",
            },
            "resultado",
        ),
        (
            {
                "validada": "True",
                "genera_acta_auditoria": "True",
                "resultado": "finalizada_con_observaciones",
            },
            "observaciones",
        ),
    ],
)
def test_formulario_aplica_campos_condicionales(proyecto, datos, campo):
    form = AuditoriaForm(datos, rendicion=crear_rendicion(proyecto))
    assert not form.is_valid()
    assert campo in form.errors


@pytest.mark.django_db
def test_elegibles_exige_codigo_organizacion_validada_y_sin_acta(proyecto):
    base = crear_rendicion(proyecto)
    elegible = crear_sin_acta(proyecto, numero_rendicion=2)
    crear_rendicion(proyecto, validada=False)
    crear_rendicion(proyecto, validada=None)
    crear_rendicion(proyecto, genera_acta_auditoria=True)
    crear_rendicion(proyecto, acta_auditoria="acta.pdf")
    crear_rendicion(proyecto, genera_acta_auditoria=None)
    otro = ProyectoOrganizacion.objects.create(
        organizacion=Organizacion.objects.create(nombre="Otra Organización"),
        codigo=proyecto.codigo,
        nombre="Otro proyecto",
    )
    crear_rendicion(otro)
    assert list(
        RendicionCuentaMensualService.rendiciones_elegibles_para_auditoria(base)
    ) == [elegible]


@pytest.mark.django_db
def test_replicacion_acta_resultado_selecciones_y_documentos(
    proyecto, superuser, settings
):
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    }
    base = crear_rendicion(proyecto)
    primera = crear_sin_acta(proyecto, numero_rendicion=2)
    segunda = crear_sin_acta(proyecto, numero_rendicion=3)
    AuditoriaService.guardar(
        rendicion=base,
        actor=superuser,
        datos={
            "validada": True,
            "genera_acta_auditoria": True,
            "resultado": "finalizada_con_observaciones",
            "observaciones": "Revisar comprobantes",
            "rendiciones_incluidas": [primera, segunda],
            "acta_auditoria": SimpleUploadedFile("acta.pdf", b"%PDF-1.4 acta"),
            "documento_regularizacion": SimpleUploadedFile(
                "complementaria.pdf", b"%PDF-1.4 complemento"
            ),
        },
    )
    base.refresh_from_db()
    for item in (base, primera, segunda):
        item.refresh_from_db()
        assert item.validada is True
        assert item.genera_acta_auditoria is True
        assert item.rendicion_origen_acta_id == base.pk
        assert item.subestado_proceso == "finalizada_con_observaciones"
        assert item.observaciones == "Revisar comprobantes"
        assert item.acta_auditoria.name == base.acta_auditoria.name
        assert item.documento_regularizacion.name == base.documento_regularizacion.name
        assert item.usuario_ultima_modificacion == superuser
        assert set(item.rendiciones_incluidas.values_list("pk", flat=True)) == {
            base.pk,
            primera.pk,
            segunda.pk,
        } - {item.pk}


@pytest.mark.django_db
def test_revalida_seleccion_que_cambio_despues_de_abrir_formulario(proyecto, superuser):
    base = crear_rendicion(proyecto)
    incluida = crear_sin_acta(proyecto)
    form = AuditoriaForm(
        {
            "validada": "True",
            "genera_acta_auditoria": "True",
            "resultado": "finalizada",
            "rendiciones_incluidas": [incluida.pk],
        },
        rendicion=base,
    )
    assert form.is_valid(), form.errors
    incluida.genera_acta_auditoria = True
    incluida.save()
    with pytest.raises(ValidationError):
        AuditoriaService.guardar(
            rendicion=base, datos=form.cleaned_data, actor=superuser
        )
    base.refresh_from_db()
    assert base.genera_acta_auditoria is None
    assert base.subestado_proceso == "pendiente"


@pytest.mark.django_db
def test_pantalla_con_precarga_y_post_guarda_sin_acta(auth_client, proyecto):
    base = crear_rendicion(proyecto)
    url = reverse("rendicioncuentasmensual_auditoria", kwargs={"pk": base.pk})
    respuesta = auth_client.get(url)
    assert respuesta.status_code == 200
    assert proyecto.codigo in respuesta.content.decode()
    assert b'name="monto_rendido"' not in respuesta.content
    respuesta = auth_client.post(
        url, {"validada": "True", "genera_acta_auditoria": "False"}
    )
    assert respuesta.status_code == 302
    base.refresh_from_db()
    assert base.validada is True


@pytest.mark.django_db
def test_pantalla_conserva_errores_y_valores(auth_client, proyecto):
    base = crear_rendicion(proyecto)
    respuesta = auth_client.post(
        reverse("rendicioncuentasmensual_auditoria", kwargs={"pk": base.pk}),
        {
            "validada": "True",
            "genera_acta_auditoria": "True",
            "resultado": "finalizada_con_observaciones",
        },
    )
    assert respuesta.status_code == 200
    assert "observaciones" in respuesta.context["form"].errors
    assert respuesta.context["form"].is_bound


@pytest.mark.django_db
def test_pantalla_rechaza_etapas_anteriores_y_actas_cerradas(auth_client, proyecto):
    for cambios in (
        {"etapa_proceso": "revision_auditoria"},
        {"subestado_proceso": "finalizada"},
    ):
        base = crear_rendicion(proyecto, **cambios)
        url = reverse("rendicioncuentasmensual_auditoria", kwargs={"pk": base.pk})
        assert auth_client.get(url).status_code == 404
        assert (
            auth_client.post(
                url, {"validada": "True", "genera_acta_auditoria": "False"}
            ).status_code
            == 404
        )


@pytest.mark.django_db
def test_usuario_sin_permiso_no_puede_gestionar(client, user, proyecto):
    client.force_login(user)
    base = crear_rendicion(proyecto)
    url = reverse("rendicioncuentasmensual_auditoria", kwargs={"pk": base.pk})
    assert client.get(url).status_code in (302, 403)
    assert client.post(
        url, {"validada": "True", "genera_acta_auditoria": "False"}
    ).status_code in (302, 403)
    base.refresh_from_db()
    assert base.subestado_proceso == "pendiente"


@pytest.mark.django_db
def test_acceso_desde_listado_solo_ofrece_rendiciones_disponibles(
    auth_client, proyecto
):
    base = crear_rendicion(proyecto)
    crear_rendicion(proyecto, etapa_proceso="revision_auditoria")
    url = reverse("rendicioncuentasmensual_auditoria_nueva")
    respuesta = auth_client.get(url)
    assert list(respuesta.context["disponibles"]) == []
    respuesta = auth_client.get(url, {"busqueda": "AUD-2673"})
    assert list(respuesta.context["disponibles"]) == [base]
    respuesta = auth_client.get(url, {"rendicion": base.pk})
    assert respuesta.status_code == 302
    assert respuesta.url == reverse(
        "rendicioncuentasmensual_auditoria", kwargs={"pk": base.pk}
    )


@pytest.mark.django_db
@pytest.mark.parametrize("validada", [True, None])
def test_regularizacion_se_replica_al_grupo(proyecto, superuser, settings, validada):
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    }
    base = crear_rendicion(proyecto)
    incluida = crear_sin_acta(proyecto)
    AuditoriaService.guardar(
        rendicion=base,
        actor=superuser,
        datos={
            "validada": True,
            "genera_acta_auditoria": True,
            "resultado": "finalizada_con_observaciones",
            "observaciones": "A regularizar",
            "rendiciones_incluidas": [incluida],
        },
    )
    RendicionCuentaMensual.objects.filter(pk__in=[base.pk, incluida.pk]).update(
        validada=validada
    )
    base.refresh_from_db()
    RendicionProcesoService.ejecutar(
        rendicion=base, actor=superuser, accion="iniciar_regularizacion", datos={}
    )
    incluida.refresh_from_db()
    assert incluida.etapa_proceso == "regularizacion"
    RendicionProcesoService.ejecutar(
        rendicion=base,
        actor=superuser,
        accion="finalizar_regularizacion",
        datos={
            "documento_regularizacion": SimpleUploadedFile(
                "complementaria.pdf", b"%PDF-1.4 complemento"
            ),
        },
    )
    base.refresh_from_db()
    incluida.refresh_from_db()
    assert base.subestado_proceso == incluida.subestado_proceso == "finalizada"
    assert base.documento_regularizacion.name == incluida.documento_regularizacion.name


@pytest.mark.django_db
def test_elegibilidad_incluye_rendicion_legada_por_comedor(proyecto):
    base = crear_sin_acta(proyecto)
    comedor = Comedor.objects.create(
        nombre="Comedor legado",
        organizacion=proyecto.organizacion,
        codigo_de_proyecto=proyecto.codigo,
    )
    legada = crear_sin_acta(None, comedor=comedor)
    assert list(
        RendicionCuentaMensualService.rendiciones_elegibles_para_auditoria(base)
    ) == [legada]
    assert list(
        RendicionCuentaMensualService.rendiciones_elegibles_para_auditoria(legada)
    ) == [base]


@pytest.mark.django_db
def test_permiso_de_auditoria_alcanza_para_gestionar_sin_permiso_general(
    client, user, proyecto
):
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="rendicioncuentasmensual",
            codename="manage_auditoria_stage",
        )
    )
    client.force_login(user)
    base = crear_rendicion(proyecto)
    url = reverse("rendicioncuentasmensual_auditoria", kwargs={"pk": base.pk})
    assert client.get(url).status_code == 200
    assert (
        client.post(
            url, {"validada": "True", "genera_acta_auditoria": "False"}
        ).status_code
        == 302
    )
    base.refresh_from_db()
    assert base.usuario_ultima_modificacion == user


@pytest.mark.django_db
def test_seleccion_manual_rechaza_identificador_invalido(auth_client):
    assert (
        auth_client.get(
            reverse("rendicioncuentasmensual_auditoria_nueva"),
            {"rendicion": "invalida"},
        ).status_code
        == 404
    )


@pytest.mark.django_db
@pytest.mark.parametrize("valor", [None, "False", False, ""])
def test_no_permite_guardar_sin_confirmar_validacion(proyecto, superuser, valor):
    base = crear_rendicion(proyecto)
    datos = {"genera_acta_auditoria": False}
    if valor is not None:
        datos["validada"] = valor
    with pytest.raises(ValidationError, match="validada"):
        AuditoriaService.guardar(rendicion=base, datos=datos, actor=superuser)
    base.refresh_from_db()
    assert base.validada is None
    assert base.fecha_gestion_auditoria is None


@pytest.mark.django_db
def test_reingreso_exige_decision_y_no_permite_desvalidar(auth_client, proyecto):
    base = crear_rendicion(proyecto, validada=True, subestado_proceso="en_curso")
    url = reverse("rendicioncuentasmensual_auditoria", kwargs={"pk": base.pk})
    detalle = reverse("rendicioncuentasmensual_detail", kwargs={"pk": base.pk})
    respuesta = auth_client.get(url)
    form = respuesta.context["form"]
    assert form.ya_validada
    assert form.fields["validada"].disabled
    assert form.fields["genera_acta_auditoria"].required
    assert b'name="validada"' not in respuesta.content
    respuesta = auth_client.post(url, {"validada": "False"})
    assert "genera_acta_auditoria" in respuesta.context["form"].errors
    respuesta = auth_client.post(
        url, {"validada": "False", "genera_acta_auditoria": "False"}
    )
    assert respuesta.status_code == 302
    assert respuesta.url == detalle
    base.refresh_from_db()
    assert base.validada is True
    assert base.genera_acta_auditoria is False
    assert base.estado_proceso_display == "Auditoría validada sin acta"
    assert base.fecha_gestion_auditoria is not None
    assert auth_client.get(url).status_code == 404
    assert auth_client.post(url, {"validada": "True"}).status_code == 404
    assert not AuditoriaService.disponibles().filter(pk=base.pk).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("decision", [False, True])
def test_puede_validar_y_cerrar_en_el_primer_ingreso(proyecto, superuser, decision):
    base = crear_rendicion(proyecto)
    datos = {"validada": True, "genera_acta_auditoria": decision}
    if decision:
        datos["resultado"] = "finalizada"
    AuditoriaService.guardar(rendicion=base, datos=datos, actor=superuser)
    base.refresh_from_db()
    assert base.fecha_gestion_auditoria is not None
    with pytest.raises(ValidationError):
        AuditoriaService.guardar(rendicion=base, datos=datos, actor=superuser)
    with pytest.raises(ValidationError):
        RendicionProcesoService.ejecutar(
            rendicion=base, actor=superuser, accion="iniciar_auditoria", datos={}
        )


@pytest.mark.django_db
@pytest.mark.parametrize("busqueda", ["", "   ", "\u0301"])
def test_busqueda_vacia_no_lista_rendiciones(auth_client, proyecto, busqueda):
    crear_rendicion(proyecto)
    respuesta = auth_client.get(
        reverse("rendicioncuentasmensual_auditoria_nueva"), {"busqueda": busqueda}
    )
    assert "busqueda" in respuesta.context["busqueda_form"].errors
    assert not respuesta.context["busqueda_valida"]
    assert list(respuesta.context["disponibles"]) == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "filtro,texto",
    [
        ("proyecto", "pRoyecto audit"),
        ("organizacion", "organiZACION audit"),
    ],
)
def test_busca_parcial_sin_tildes_y_solo_en_el_filtro(
    auth_client, proyecto, filtro, texto
):
    base = crear_rendicion(proyecto)
    crear_sin_acta(proyecto)
    crear_rendicion(proyecto, etapa_proceso="revision_auditoria")
    url = reverse("rendicioncuentasmensual_auditoria_nueva")
    respuesta = auth_client.get(url, {"filtro": filtro, "busqueda": texto})
    assert list(respuesta.context["disponibles"]) == [base]
    otro_filtro = "organizacion" if filtro == "proyecto" else "proyecto"
    respuesta = auth_client.get(url, {"filtro": otro_filtro, "busqueda": texto})
    assert list(respuesta.context["disponibles"]) == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "periodo,cantidad",
    [
        ("09/2026", 1),
        ("15/09/2026", 1),
        ("2026", 1),
        ("2026-09", 1),
        ("2026-09-30", 1),
        ("10/2026", 0),
    ],
)
def test_busca_periodos_que_contienen_fecha_o_mes(
    auth_client, proyecto, periodo, cantidad
):
    crear_rendicion(proyecto)
    respuesta = auth_client.get(
        reverse("rendicioncuentasmensual_auditoria_nueva"),
        {"filtro": "periodo", "busqueda": periodo},
    )
    assert len(respuesta.context["disponibles"]) == cantidad


@pytest.mark.parametrize("periodo", ["invalido", "31/02/2026", "13/2026"])
def test_busqueda_rechaza_periodo_invalido(periodo):
    form = AuditoriaBusquedaForm({"filtro": "periodo", "busqueda": periodo})
    assert not form.is_valid()
    assert "busqueda" in form.errors


@pytest.mark.django_db
def test_solo_incluye_auditadas_con_no_no_validaciones_parciales(proyecto):
    base = crear_rendicion(proyecto)
    completa = crear_sin_acta(proyecto)
    crear_rendicion(proyecto, validada=True, subestado_proceso="en_curso")
    crear_rendicion(proyecto, validada=True, genera_acta_auditoria=False)
    crear_sin_acta(proyecto, validada=False)
    crear_sin_acta(proyecto, genera_acta_auditoria=True)
    assert list(
        RendicionCuentaMensualService.rendiciones_elegibles_para_auditoria(base)
    ) == [completa]


@pytest.mark.django_db
@pytest.mark.parametrize("origen", ["", "busqueda"])
def test_volver_tiene_destino_explicito_y_transitorio(auth_client, proyecto, origen):
    base = crear_rendicion(proyecto)
    respuesta = auth_client.get(
        reverse("rendicioncuentasmensual_auditoria", kwargs={"pk": base.pk}),
        {"origen": origen},
    )
    esperado = (
        reverse("rendicioncuentasmensual_auditoria_nueva")
        if origen
        else reverse("rendicioncuentasmensual_detail", kwargs={"pk": base.pk})
    )
    assert respuesta.context["volver_url"] == esperado
    assert respuesta.context["volver_transitoria"]


@pytest.mark.django_db
def test_detalle_sin_auditoria_oculta_documentacion_y_muestra_no(auth_client, proyecto):
    base = crear_rendicion(proyecto)
    respuesta = auth_client.get(
        reverse("rendicioncuentasmensual_detail", kwargs={"pk": base.pk})
    )
    assert not respuesta.context["mostrar_documentacion_auditoria"]
    assert (
        "Documentación de las rendiciones incluidas" not in respuesta.content.decode()
    )
    assert 'class="js-resumen-rendicion"' not in respuesta.content.decode()
    assert b"Gestionar Auditor" in respuesta.content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "resultado,acciones",
    [("finalizada", False), ("finalizada_con_observaciones", True)],
)
def test_acciones_solo_en_origen_y_post_incorporada_rechazado(
    auth_client, proyecto, superuser, resultado, acciones
):
    base = crear_rendicion(proyecto)
    incluida = crear_sin_acta(proyecto)
    AuditoriaService.guardar(
        rendicion=base,
        actor=superuser,
        datos={
            "validada": True,
            "genera_acta_auditoria": True,
            "resultado": resultado,
            "observaciones": "Comprobantes a regularizar" if acciones else "",
            "rendiciones_incluidas": [incluida],
        },
    )
    for item, habilitada in [(base, acciones), (incluida, False)]:
        respuesta = auth_client.get(
            reverse("rendicioncuentasmensual_detail", kwargs={"pk": item.pk})
        )
        assert respuesta.context["mostrar_acciones_proceso"] is habilitada
        assert (b"Iniciar regularizaci" in respuesta.content) is habilitada
    url_incluida = reverse("rendicioncuentasmensual_detail", kwargs={"pk": incluida.pk})
    respuesta = auth_client.post(
        url_incluida, {"accion_proceso": "iniciar_regularizacion"}
    )
    assert respuesta.status_code == 302
    incluida.refresh_from_db()
    assert incluida.etapa_proceso == "auditoria"
    if acciones:
        url_base = reverse("rendicioncuentasmensual_detail", kwargs={"pk": base.pk})
        auth_client.post(url_base, {"accion_proceso": "iniciar_regularizacion"})
        for item in (base, incluida):
            item.refresh_from_db()
            assert item.etapa_proceso == "regularizacion"
        respuesta = auth_client.get(url_base)
        assert respuesta.context["mostrar_acciones_proceso"]
        assert b"Finalizar regularizaci" in respuesta.content
        with pytest.raises(ValidationError, match="originó"):
            RendicionProcesoService.ejecutar(
                rendicion=incluida,
                actor=superuser,
                accion="finalizar_regularizacion",
                datos={},
            )


def test_datos_de_acta_no_son_editables_desde_datos_generales():
    form = RendicionCuentaMensualForm()
    assert {
        "validada",
        "rendicion_origen_acta",
        "genera_acta_auditoria",
        "rendiciones_incluidas",
    }.isdisjoint(form.fields)


@pytest.mark.django_db
def test_migracion_recupera_origen_por_vinculo_no_por_numero(proyecto):
    fecha = timezone.now()
    incluida = crear_sin_acta(
        proyecto, genera_acta_auditoria=True, fecha_auditada=fecha
    )
    base = crear_sin_acta(proyecto, genera_acta_auditoria=True, fecha_auditada=fecha)
    base.rendiciones_incluidas.set([incluida])
    incluida.rendiciones_incluidas.set([base])
    migration = import_module(
        "rendicioncuentasmensual.migrations.0025_origen_acta_auditoria"
    )
    migration.recuperar_origen_actas(apps, SimpleNamespace(connection=connection))
    for item in (base, incluida):
        item.refresh_from_db()
        assert item.rendicion_origen_acta_id == base.pk


@pytest.mark.django_db
def test_migracion_no_infiere_origen_en_grupo_inconsistente(proyecto):
    base = crear_sin_acta(
        proyecto, genera_acta_auditoria=True, fecha_auditada=timezone.now()
    )
    incluida = crear_sin_acta(proyecto)
    base.rendiciones_incluidas.set([incluida])
    migration = import_module(
        "rendicioncuentasmensual.migrations.0025_origen_acta_auditoria"
    )
    migration.recuperar_origen_actas(apps, SimpleNamespace(connection=connection))
    base.refresh_from_db()
    assert base.rendicion_origen_acta_id is None


@pytest.mark.django_db
def test_permiso_auditoria_no_ofrece_regularizacion(client, user, proyecto, superuser):
    base = crear_rendicion(proyecto)
    AuditoriaService.guardar(
        rendicion=base,
        actor=superuser,
        datos={
            "validada": True,
            "genera_acta_auditoria": True,
            "resultado": "finalizada_con_observaciones",
            "observaciones": "Revisar",
        },
    )
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="rendicioncuentasmensual",
            codename="manage_auditoria_stage",
        )
    )
    client.force_login(user)
    url = reverse("rendicioncuentasmensual_detail", kwargs={"pk": base.pk})
    respuesta = client.get(url)
    assert respuesta.status_code == 200
    assert not respuesta.context["mostrar_acciones_proceso"]
    assert (
        client.post(url, {"accion_proceso": "iniciar_regularizacion"}).status_code
        == 403
    )
    base.refresh_from_db()
    assert base.etapa_proceso == "auditoria"


@pytest.mark.parametrize(
    "validada,subestado,cerrada,etiqueta",
    [
        (True, "en_curso", True, "Auditoría validada sin acta"),
        (False, "en_curso", True, "Auditoría en curso"),
        (None, "en_curso", True, "Auditoría en curso"),
        (True, "en_curso", False, "Auditoría en curso"),
        (True, "finalizada", True, "Auditoría finalizada sin observaciones"),
        (None, "finalizada", False, "Auditoría finalizada sin observaciones"),
        (
            True,
            "finalizada_con_observaciones",
            True,
            "Auditoría finalizada con observaciones",
        ),
    ],
)
def test_etiqueta_sin_acta_no_sustituye_resultados_historicos(
    validada, subestado, cerrada, etiqueta
):
    rendicion = RendicionCuentaMensual(
        mes=9,
        anio=2026,
        etapa_proceso="auditoria",
        subestado_proceso=subestado,
        validada=validada,
        genera_acta_auditoria=False,
        fecha_gestion_auditoria=timezone.now() if cerrada else None,
    )
    assert rendicion.estado_proceso_display == etiqueta


@pytest.mark.django_db
@pytest.mark.parametrize("linea", ["secos", "tradicional"])
def test_rendicion_sin_origen_regulariza_sola_sin_propagar(
    proyecto, superuser, settings, linea
):
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    }
    # Secos nunca registró decisión de acta; las actas legadas no conciliadas
    # quedan sin origen y con vínculos que antes no replicaban estado.
    base = crear_rendicion(
        proyecto,
        linea_programatica=linea,
        genera_acta_auditoria=None if linea == "secos" else True,
        subestado_proceso="finalizada_con_observaciones",
        fecha_auditada=timezone.now(),
    )
    vinculada = crear_sin_acta(proyecto, numero_rendicion=2)
    if linea == "tradicional":
        base.rendiciones_incluidas.set([vinculada])
    assert base.es_origen_acta
    RendicionProcesoService.ejecutar(
        rendicion=base, actor=superuser, accion="iniciar_regularizacion", datos={}
    )
    RendicionProcesoService.ejecutar(
        rendicion=base,
        actor=superuser,
        accion="finalizar_regularizacion",
        datos={
            "documento_regularizacion": SimpleUploadedFile(
                "complementaria.pdf", b"%PDF-1.4 complemento"
            ),
        },
    )
    base.refresh_from_db()
    vinculada.refresh_from_db()
    assert base.etapa_proceso == "regularizacion"
    assert base.subestado_proceso == "finalizada"
    assert vinculada.etapa_proceso == "auditoria"
    assert vinculada.subestado_proceso == "en_curso"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "resultado,esperadas",
    [
        ("finalizada", ("Nota base", "Nota incluida")),
        ("finalizada_con_observaciones", ("Faltan comprobantes",) * 2),
    ],
)
def test_acta_no_vacia_observaciones_generales(
    proyecto, superuser, resultado, esperadas
):
    base = crear_rendicion(proyecto, observaciones="Nota base")
    incluida = crear_sin_acta(
        proyecto, numero_rendicion=2, observaciones="Nota incluida"
    )
    AuditoriaService.guardar(
        rendicion=base,
        actor=superuser,
        datos={
            "validada": True,
            "genera_acta_auditoria": True,
            "resultado": resultado,
            "observaciones": (
                "Faltan comprobantes"
                if resultado == "finalizada_con_observaciones"
                else ""
            ),
            "rendiciones_incluidas": [incluida],
        },
    )
    base.refresh_from_db()
    incluida.refresh_from_db()
    assert (base.observaciones, incluida.observaciones) == esperadas


@pytest.mark.django_db
def test_elegibles_respetan_regla_de_linea(proyecto, superuser):
    tradicional = crear_rendicion(proyecto)
    elegible = crear_sin_acta(proyecto, numero_rendicion=2)
    secos_cerrada = crear_sin_acta(
        proyecto, numero_rendicion=3, linea_programatica="secos"
    )
    secos = crear_rendicion(proyecto, numero_rendicion=4, linea_programatica="secos")
    assert list(
        RendicionCuentaMensualService.rendiciones_elegibles_para_auditoria(tradicional)
    ) == [elegible]
    assert not RendicionCuentaMensualService.rendiciones_elegibles_para_auditoria(
        secos
    ).exists()
    with pytest.raises(ValidationError):
        AuditoriaService.guardar(
            rendicion=secos,
            actor=superuser,
            datos={
                "validada": True,
                "genera_acta_auditoria": True,
                "resultado": "finalizada",
                "rendiciones_incluidas": [secos_cerrada],
            },
        )
