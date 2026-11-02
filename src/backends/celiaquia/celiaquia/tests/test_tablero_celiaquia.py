from datetime import date

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone

from ciudadanos.models import Ciudadano
from core.models import Provincia, Sexo

from celiaquia.models import (
    EstadoCupo,
    EstadoExpediente,
    EstadoLegajo,
    Expediente,
    ExpedienteCiudadano,
    HistorialValidacionTecnica,
    ProvinciaCupo,
    RegistroErroneo,
    ResultadoSintys,
    RevisionTecnico,
    Subsanacion,
    SubsanacionObservacion,
    TipoSubsanacion,
)
from celiaquia.services.tablero_service import construir_tablero
from celiaquia.services.tablero_service.impl import (
    _tipo_de_error,
    _tramo,
    titulares_por_edad_y_sexo,
)

URL = "/celiaquia/tablero/"
MOTIVO_CON_NOMBRE = (
    "RENAPER- falta DNI. Se requiere certificar diagnóstico. Revisó Juana Ficticia"
)


def _permiso(codename):
    """`view_tablero_celiaquia` está en `Meta.permissions`; se crea acá por si la
    base de tests no corrió el `post_migrate`."""
    content_type = ContentType.objects.get_or_create(
        app_label="celiaquia", model="expediente"
    )[0]
    return Permission.objects.get_or_create(
        content_type=content_type, codename=codename, defaults={"name": codename}
    )[0]


def _usuario(username, con_permiso=True):
    user = User.objects.create_user(username=username, password="pass")
    if con_permiso:
        user.user_permissions.add(_permiso("view_tablero_celiaquia"))
    return user


class _Datos:
    """Arma expedientes y legajos con una regla distinta en cada uno."""

    def __init__(self):
        self.salta = Provincia.objects.create(nombre="Salta")
        self.jujuy = Provincia.objects.create(nombre="Jujuy")
        self.femenino = Sexo.objects.create(sexo="Femenino")
        self.masculino = Sexo.objects.create(sexo="Masculino")
        ProvinciaCupo.objects.create(provincia=self.salta, total_asignado=10)
        self.usuario = User.objects.create_user(username="carga", password="x")
        self.finalizado = EstadoExpediente.objects.create(nombre="CRUCE_FINALIZADO")
        self.en_espera = EstadoExpediente.objects.create(nombre="EN_ESPERA")
        self.estado_legajo = EstadoLegajo.objects.create(nombre="ARCHIVO_CARGADO")
        self.documento = 30000000

    def expediente(self, estado=None, numero=""):
        return Expediente.objects.create(
            usuario_provincia=self.usuario,
            estado=estado or self.finalizado,
            numero_expediente=numero,
        )

    def legajo(self, expediente, provincia, sexo=None, nacimiento=None, **campos):
        self.documento += 1
        ciudadano = Ciudadano.objects.create(
            apellido="Apellido Ficticio",
            nombre="Nombre",
            documento=self.documento,
            provincia=provincia,
            sexo=sexo,
            fecha_nacimiento=nacimiento,
        )
        return ExpedienteCiudadano.objects.create(
            expediente=expediente,
            ciudadano=ciudadano,
            estado=self.estado_legajo,
            **campos,
        )


TITULAR = {
    "revision_tecnico": RevisionTecnico.APROBADO,
    "resultado_sintys": ResultadoSintys.MATCH,
    "estado_cupo": EstadoCupo.DENTRO,
    "es_titular_activo": True,
}


@pytest.fixture
def datos(db):
    d = _Datos()
    exp1 = d.expediente(numero="EX-<b>2026</b>")
    d.titular = d.legajo(
        exp1, d.salta, sexo=d.femenino, nacimiento=date(2015, 1, 1), **TITULAR
    )
    d.legajo(
        exp1,
        d.salta,
        revision_tecnico=RevisionTecnico.APROBADO,
        resultado_sintys=ResultadoSintys.NO_MATCH,
    )
    d.legajo(
        exp1,
        d.salta,
        revision_tecnico=RevisionTecnico.APROBADO,
        resultado_sintys=ResultadoSintys.MATCH,
        estado_cupo=EstadoCupo.DENTRO,
        es_titular_activo=False,
    )
    subsanar = d.legajo(exp1, d.salta, revision_tecnico=RevisionTecnico.SUBSANAR)
    subsanacion = Subsanacion.objects.create(legajo=subsanar, motivo_general="x")
    SubsanacionObservacion.objects.create(
        subsanacion=subsanacion, tipo=TipoSubsanacion.DOCUMENTACION
    )
    SubsanacionObservacion.objects.create(
        subsanacion=subsanacion, tipo=TipoSubsanacion.OTROS
    )
    rechazado = d.legajo(exp1, d.salta, revision_tecnico=RevisionTecnico.RECHAZADO)
    HistorialValidacionTecnica.objects.create(
        legajo=rechazado,
        estado_nuevo=RevisionTecnico.RECHAZADO,
        motivo=MOTIVO_CON_NOMBRE,
    )
    # El responsable no recibe la prestación: no se cuenta.
    d.legajo(exp1, d.salta, rol=ExpedienteCiudadano.ROLE_RESPONSABLE, **TITULAR)
    # Legajo con borrado lógico: no se cuenta.
    borrado = d.legajo(exp1, d.salta, **TITULAR)
    ExpedienteCiudadano.all_objects.filter(pk=borrado.pk).update(
        deleted_at=timezone.now()
    )
    # Expediente con borrado lógico: sus legajos no se cuentan.
    exp_borrado = d.expediente()
    d.legajo(exp_borrado, d.salta, **TITULAR)
    Expediente.all_objects.filter(pk=exp_borrado.pk).update(deleted_at=timezone.now())
    # Otra provincia, expediente todavía sin cruce finalizado; rechazado sin motivo.
    exp2 = d.expediente(estado=d.en_espera)
    d.legajo(
        exp2,
        d.jujuy,
        rol=ExpedienteCiudadano.ROLE_BENEFICIARIO_Y_RESPONSABLE,
        revision_tecnico=RevisionTecnico.PENDIENTE,
    )
    d.legajo(exp2, d.jujuy, revision_tecnico=RevisionTecnico.RECHAZADO)
    RegistroErroneo.objects.create(
        expediente=exp1, fila_excel=2, datos_raw={}, mensaje_error=""
    )
    RegistroErroneo.objects.create(
        expediente=exp2,
        fila_excel=3,
        datos_raw={},
        mensaje_error="Field 'documento' expected a number",
    )
    d.exp1, d.exp2 = exp1, exp2
    return d


def _fila(filas, provincia):
    return next(f for f in filas if f["p"] == provincia)


def test_tablero_cuenta_solo_beneficiarios_activos_por_provincia(datos):
    resultado = construir_tablero()

    assert _fila(resultado["provincias"], "Salta") == {
        "p": "Salta",
        "cupo": 10,
        "exp": 1,
        "expProc": 0,
        "leg": 5,
        "per": 5,
        "pend": 0,
        "apr": 3,
        "rech": 1,
        "sub": 1,
        "match": 2,
        "nomatch": 1,
        "sincruce": 0,
        "tit": 1,
        "susp": 1,
        "fuera": 0,
    }
    jujuy = _fila(resultado["provincias"], "Jujuy")
    assert (jujuy["leg"], jujuy["pend"], jujuy["rech"]) == (2, 1, 1)
    assert (jujuy["exp"], jujuy["expProc"], jujuy["cupo"]) == (1, 1, 0)


def test_tablero_cuenta_titulares_por_tramo_y_sexo(datos):
    piramide = construir_tablero()["piramide"]

    # Nacida el 1/1/2015: hoy está en el tramo 6-12 (índice 1).
    assert piramide == {"Salta": {"F": [0, 1, 0, 0, 0, 0, 0], "M": [0] * 7}}


@pytest.mark.parametrize(
    "nacimiento, tramo",
    [
        (date(2021, 6, 2), 0),
        (date(2020, 6, 1), 1),
        (date(2008, 6, 2), 2),
        (date(2008, 6, 1), 3),
        (date(1961, 6, 2), 5),
        (date(1961, 6, 1), 6),
    ],
)
def test_tramo_de_edad_respeta_el_cumpleanos(nacimiento, tramo):
    assert _tramo(nacimiento, date(2026, 6, 1)) == tramo


@pytest.mark.parametrize(
    "mensaje, tipo",
    [
        (None, "Corregido o sin mensaje"),
        ("  ", "Corregido o sin mensaje"),
        ("El documento es obligatorio", "Falta documento"),
        (
            "Municipio inválido para la provincia",
            "Municipio no corresponde a la provincia",
        ),
        ("Algo que no se esperaba", "Otro"),
    ],
)
def test_tipo_de_error_de_importacion(mensaje, tipo):
    assert _tipo_de_error(mensaje) == tipo


def test_piramide_deja_afuera_titulares_sin_sexo_f_m(datos):
    datos.legajo(
        datos.exp1, datos.salta, sexo=None, nacimiento=date(1990, 1, 1), **TITULAR
    )

    piramide = titulares_por_edad_y_sexo(
        ExpedienteCiudadano.objects.filter(expediente=datos.exp1)
    )

    assert sum(piramide["Salta"]["F"]) + sum(piramide["Salta"]["M"]) == 1


def test_tablero_cuenta_cada_motivo_de_rechazo_mencionado(datos):
    rechazo = construir_tablero()["rechazo"]

    assert rechazo["Salta"] == {
        "Diagnóstico no acreditado": 1,
        "Documento de identidad (RENAPER / DNI)": 1,
    }
    assert rechazo["Jujuy"] == {"Sin motivo registrado": 1}


def test_tablero_usa_el_ultimo_motivo_de_rechazo(datos):
    legajo = ExpedienteCiudadano.objects.get(
        expediente=datos.exp1, revision_tecnico=RevisionTecnico.RECHAZADO
    )
    HistorialValidacionTecnica.objects.create(
        legajo=legajo,
        estado_nuevo=RevisionTecnico.RECHAZADO,
        motivo="POSEE OBRA SOCIAL",
    )

    assert construir_tablero()["rechazo"]["Salta"] == {"Tiene obra social": 1}


def test_tablero_cuenta_subsanaciones_y_errores_de_importacion(datos):
    resultado = construir_tablero()

    assert resultado["subsanacion"] == {"Salta": {"Documentación": 1, "Otros": 1}}
    assert resultado["errores"] == {
        "Salta": {"Corregido o sin mensaje": 1},
        "Jujuy": {"Documento no numérico": 1},
    }


def test_tablero_arma_filas_por_expediente(datos):
    expedientes = {e["id"]: e for e in construir_tablero()["expedientes"]}

    assert set(expedientes) == {datos.exp1.pk, datos.exp2.pk}
    exp1 = expedientes[datos.exp1.pk]
    assert (exp1["p"], exp1["n"], exp1["est"], exp1["d"]) == (
        "Salta",
        "EX-<b>2026</b>",
        "CRUCE_FINALIZADO",
        0,
    )
    assert (exp1["leg"], exp1["sub"], exp1["rech"], exp1["tit"]) == (5, 1, 1, 1)


def test_tablero_respeta_provincias_visibles(datos):
    resultado = construir_tablero(provincias_visibles=[datos.salta.pk])

    assert [f["p"] for f in resultado["provincias"]] == ["Salta"]
    assert {e["p"] for e in resultado["expedientes"]} == {"Salta"}
    assert set(resultado["errores"]) == {"Salta"}
    assert set(resultado["rechazo"]) == {"Salta"}


def test_tablero_sin_login_no_muestra_datos(client, db):
    # Mismo control que Cupos y el Reporter: `permissions_any_required` corta
    # con 403 antes de la vista.
    response = client.get(URL)

    assert response.status_code == 403


def test_tablero_sin_permiso_devuelve_403(client, db):
    client.force_login(_usuario("sin_permiso", con_permiso=False))

    response = client.get(URL)

    assert response.status_code == 403


def test_tablero_con_permiso_muestra_datos_agregados_sin_datos_personales(
    client, datos
):
    client.force_login(_usuario("con_permiso"))

    response = client.get(URL)

    assert response.status_code == 200
    contenido = response.content.decode()
    assert 'id="cel-tablero-datos"' in contenido
    assert "Apellido Ficticio" not in contenido
    assert str(datos.documento) not in contenido
    # El texto libre del motivo trae nombres: nunca sale del servidor.
    assert "Juana Ficticia" not in contenido
    # El número de expediente es texto libre: va escapado dentro del JSON.
    assert "<b>2026</b>" not in contenido
    assert [f["p"] for f in response.context["tablero_datos"]["provincias"]] == [
        "Salta",
        "Jujuy",
    ]


def test_tablero_url_con_nombre():
    assert reverse("celiaquia_tablero") == URL
