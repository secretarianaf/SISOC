"""Issue #2789: operaciones de soporte y listados del admin de VAT."""

from datetime import date, timedelta

from auditlog.models import LogEntry
from django.contrib import admin
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
import pytest

from VAT import admin as vat_admin
from VAT.models import (
    Centro,
    ComisionCurso,
    Curso,
    Inscripcion,
    InstitucionUbicacion,
    ModalidadCursada,
    Voucher,
    VoucherRecarga,
)
from ciudadanos.models import Ciudadano
from core.admin_operaciones import ejecutar_operacion
from core.models import Localidad, Municipio, Programa, Provincia

pytestmark = pytest.mark.django_db


@pytest.fixture(name="programa")
def programa_fixture():
    return Programa.objects.create(nombre="VAT admin")


@pytest.fixture(name="comision_curso")
def comision_curso_fixture():
    provincia = Provincia.objects.create(nombre="Chaco")
    municipio = Municipio.objects.create(nombre="Resistencia", provincia=provincia)
    localidad = Localidad.objects.create(nombre="Centro", municipio=municipio)
    centro = Centro.objects.create(
        nombre="CFP Admin",
        codigo="CFP-ADM",
        provincia=provincia,
        municipio=municipio,
        localidad=localidad,
        calle="1",
        numero=1,
        domicilio_actividad="Calle 1",
        telefono="3620000",
        celular="3620001",
        correo="cfp@vat.test",
        nombre_referente="Ref",
        apellido_referente="Erente",
        telefono_referente="3620002",
        correo_referente="ref@vat.test",
        tipo_gestion="Estatal",
        clase_institucion="Formación Profesional",
        situacion="Institución de ETP",
        activo=True,
    )
    ubicacion = InstitucionUbicacion.objects.create(
        centro=centro,
        localidad=localidad,
        rol_ubicacion="sede_principal",
        domicilio="Calle 1",
        es_principal=True,
    )
    curso = Curso.objects.create(
        centro=centro,
        nombre="Soldadura",
        modalidad=ModalidadCursada.objects.create(nombre="Presencial", activo=True),
        estado="activo",
    )
    return ComisionCurso.objects.create(
        curso=curso,
        ubicacion=ubicacion,
        codigo_comision="COM-ADM",
        nombre="Comisión admin",
        cupo_total=50,
        fecha_inicio=date(2026, 4, 1),
        fecha_fin=date(2026, 12, 30),
        estado="activa",
    )


def _ciudadano(documento):
    return Ciudadano.objects.create(
        apellido=f"Ape{documento}",
        nombre=f"Nom{documento}",
        fecha_nacimiento=date(2000, 1, 1),
        documento=documento,
    )


def _voucher(programa, documento, **extra):
    datos = {
        "ciudadano": _ciudadano(documento),
        "programa": programa,
        "cantidad_inicial": 10,
        "cantidad_disponible": 10,
        "fecha_vencimiento": date.today() + timedelta(days=90),
        **extra,
    }
    return Voucher.objects.create(**datos)


def _operacion(model, slug):
    model_admin = admin.site.get_model_admin(model)
    return next(op for op in model_admin.operaciones if op.slug == slug)


def _ejecutar(model, slug, obj, usuario, **datos):
    return ejecutar_operacion(
        operacion=_operacion(model, slug),
        objetos=[obj],
        usuario=usuario,
        datos={"motivo": "Pedido de soporte", **datos},
    )


def _auditado(obj, slug):
    return LogEntry.objects.filter(
        object_pk=str(obj.pk), additional_data__operacion=slug
    ).exists()


def test_cambiar_estado_inscripcion_llama_al_service(mocker, comision_curso, superuser):
    inscripcion = Inscripcion.objects.create(
        ciudadano=_ciudadano(70000001), comision_curso=comision_curso
    )
    servicio = mocker.patch.object(
        vat_admin.InscripcionService, "actualizar_estado_inscripcion"
    )

    ok, errores = _ejecutar(
        Inscripcion, "cambiar_estado", inscripcion, superuser, nuevo_estado="inscripta"
    )

    assert ok == [inscripcion] and errores == []
    servicio.assert_called_once_with(
        inscripcion=inscripcion, nuevo_estado="inscripta", usuario=superuser
    )
    assert _auditado(inscripcion, "cambiar_estado")


def test_cambiar_estado_inscripcion_con_error_del_service_no_audita(
    mocker, comision_curso, superuser
):
    inscripcion = Inscripcion.objects.create(
        ciudadano=_ciudadano(70000002), comision_curso=comision_curso
    )
    mocker.patch.object(
        vat_admin.InscripcionService,
        "actualizar_estado_inscripcion",
        side_effect=ValueError("La comisión no tiene cupos disponibles."),
    )

    ok, errores = _ejecutar(
        Inscripcion, "cambiar_estado", inscripcion, superuser, nuevo_estado="inscripta"
    )

    assert not ok
    assert errores == [(inscripcion, "La comisión no tiene cupos disponibles.")]
    assert not _auditado(inscripcion, "cambiar_estado")


def test_cancelar_voucher_llama_al_service(mocker, programa, superuser):
    voucher = _voucher(programa, 70000003)
    servicio = mocker.patch.object(
        vat_admin.VoucherService, "cancelar_voucher", return_value=True
    )

    ok, _ = _ejecutar(Voucher, "cancelar", voucher, superuser)

    assert ok == [voucher]
    servicio.assert_called_once_with(voucher=voucher, usuario=superuser)
    assert _auditado(voucher, "cancelar")


def test_cancelar_voucher_ya_cancelado_es_error(programa, superuser):
    voucher = _voucher(programa, 70000004, estado="cancelado")

    ok, errores = _ejecutar(Voucher, "cancelar", voucher, superuser)

    assert not ok
    assert errores == [(voucher, "El voucher ya estaba cancelado.")]
    assert not _auditado(voucher, "cancelar")


def test_recargar_voucher_llama_al_service(mocker, programa, superuser):
    voucher = _voucher(programa, 70000005)
    servicio = mocker.patch.object(
        vat_admin.VoucherService, "recargar_voucher", return_value=(True, "ok")
    )

    ok, _ = _ejecutar(
        Voucher, "recargar", voucher, superuser, cantidad=5, tipo_recarga="ajuste"
    )

    assert ok == [voucher]
    servicio.assert_called_once_with(
        voucher=voucher, cantidad=5, motivo="ajuste", usuario=superuser
    )
    assert _auditado(voucher, "recargar")


def test_recargar_voucher_real_suma_saldo_y_registra_recarga(programa, superuser):
    voucher = _voucher(programa, 70000006, cantidad_disponible=0, estado="agotado")

    ok, errores = _ejecutar(
        Voucher, "recargar", voucher, superuser, cantidad=4, tipo_recarga="manual"
    )

    assert ok == [voucher] and errores == []
    voucher.refresh_from_db()
    assert voucher.cantidad_disponible == 4
    assert voucher.estado == "activo"
    assert VoucherRecarga.objects.filter(
        voucher=voucher, cantidad=4, motivo="manual", autorizado_por=superuser
    ).exists()
    entrada = LogEntry.objects.get(
        object_pk=str(voucher.pk), additional_data__operacion="recargar"
    )
    assert entrada.changes_dict == {"cantidad_disponible": ["0", "4"]}


def test_recargar_voucher_cancelado_es_error(programa, superuser):
    voucher = _voucher(programa, 70000007, estado="cancelado")

    ok, errores = _ejecutar(
        Voucher, "recargar", voucher, superuser, cantidad=4, tipo_recarga="manual"
    )

    assert not ok
    assert errores == [(voucher, "No se puede recargar un voucher cancelado.")]


def test_recargar_no_se_ofrece_en_lote():
    assert not _operacion(Voucher, "recargar").en_lote
    assert _operacion(Voucher, "cancelar").destructiva


def test_cancelar_voucher_por_url_del_admin(auth_client, programa):
    voucher = _voucher(programa, 70000008)
    url = reverse("admin:VAT_voucher_operacion_cancelar", args=[voucher.pk])

    respuesta = auth_client.post(
        url, {"confirmar_operacion": "1", "motivo": "Asignado por error"}
    )

    assert respuesta.status_code == 302
    voucher.refresh_from_db()
    assert voucher.estado == "cancelado"
    entrada = LogEntry.objects.get(
        object_pk=str(voucher.pk), additional_data__operacion="cancelar"
    )
    assert entrada.changes_dict == {"estado": ["activo", "cancelado"]}
    assert entrada.additional_data["motivo"] == "Asignado por error"


def test_cancelar_voucher_por_url_exige_motivo(auth_client, programa):
    voucher = _voucher(programa, 70000009)
    url = reverse("admin:VAT_voucher_operacion_cancelar", args=[voucher.pk])

    respuesta = auth_client.post(url, {"confirmar_operacion": "1", "motivo": ""})

    assert respuesta.status_code == 200
    voucher.refresh_from_db()
    assert voucher.estado == "activo"


def _consultas(client, url):
    with CaptureQueriesContext(connection) as contexto:
        respuesta = client.get(url)
    assert respuesta.status_code == 200
    return len(contexto.captured_queries)


def test_listado_de_inscripciones_sin_n_mas_1(
    auth_client, comision_curso, programa, django_assert_max_num_queries
):
    url = reverse("admin:VAT_inscripcion_changelist")

    def _cargar(desde):
        for documento in range(desde, desde + 5):
            Inscripcion.objects.create(
                ciudadano=_ciudadano(documento),
                comision_curso=comision_curso,
                programa=programa,
            )

    _cargar(71000000)
    with django_assert_max_num_queries(20):
        consultas_con_5 = _consultas(auth_client, url)
    _cargar(71000100)

    assert _consultas(auth_client, url) == consultas_con_5


def test_listado_de_vouchers_sin_n_mas_1(
    auth_client, programa, django_assert_max_num_queries
):
    url = reverse("admin:VAT_voucher_changelist")

    def _cargar(desde):
        for documento in range(desde, desde + 5):
            _voucher(programa, documento)

    _cargar(72000000)
    with django_assert_max_num_queries(20):
        consultas_con_5 = _consultas(auth_client, url)
    _cargar(72000100)

    assert _consultas(auth_client, url) == consultas_con_5


@pytest.mark.parametrize(
    "modelo",
    ["inscripcion", "voucher", "comisioncurso", "sesioncomision", "actacierrecomision"],
)
def test_busqueda_de_texto_no_rompe_el_listado(auth_client, modelo):
    url = reverse(f"admin:VAT_{modelo}_changelist")

    assert auth_client.get(url, {"q": "abc 123"}).status_code == 200


def test_busqueda_de_resultados_por_ciudadano(auth_client):
    # Antes buscaba por ``inscripcion__persona``, que no existe (FieldError).
    url = reverse("admin:VAT_resultadoevaluacion_changelist")

    assert auth_client.get(url, {"q": "Perez"}).status_code == 200


def test_detalles_con_operaciones_cargan(auth_client, comision_curso, programa):
    voucher = _voucher(programa, 73000001)
    inscripcion = Inscripcion.objects.create(
        ciudadano=_ciudadano(73000002), comision_curso=comision_curso
    )

    for nombre, obj in (("voucher", voucher), ("inscripcion", inscripcion)):
        url = reverse(f"admin:VAT_{nombre}_change", args=[obj.pk])
        assert auth_client.get(url).status_code == 200


def test_cambiar_estado_al_mismo_estado_es_error(mocker, comision_curso, superuser):
    inscripcion = Inscripcion.objects.create(
        ciudadano=_ciudadano(70000009), comision_curso=comision_curso
    )
    servicio = mocker.patch.object(
        vat_admin.InscripcionService, "actualizar_estado_inscripcion"
    )

    ok, errores = _ejecutar(
        Inscripcion,
        "cambiar_estado",
        inscripcion,
        superuser,
        nuevo_estado=inscripcion.estado,
    )

    assert not ok
    assert errores == [(inscripcion, "La inscripción ya tiene ese estado.")]
    servicio.assert_not_called()


def test_alta_de_voucher_permite_cargar_la_cantidad(rf, superuser, programa):
    # cantidad_disponible es obligatoria: en el alta no queda de solo lectura,
    # solo al editar (ahí cambia por las operaciones).
    request = rf.get("/admin/")
    request.user = superuser
    model_admin = admin.site.get_model_admin(Voucher)
    voucher = _voucher(programa, 70000010)

    assert "cantidad_disponible" not in model_admin.get_readonly_fields(request)
    assert "cantidad_disponible" in model_admin.get_readonly_fields(request, voucher)
