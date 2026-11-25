"""Aporte JSON de VAT a Ciudadano 360 (C04.01)."""

from datetime import date, timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from VAT import ciudadano_detail as vat_detail
from VAT.models import (
    AsistenciaSesion,
    Centro,
    Comision,
    ComisionHorario,
    Inscripcion,
    InscripcionOferta,
    ModalidadCursada,
    OfertaInstitucional,
    PlanVersionCurricular,
    Sector,
    SesionComision,
    TituloReferencia,
    Voucher,
)
from ciudadanos import detail_contributions as dc
from ciudadanos.models import Ciudadano
from core.models import Dia, Programa, Provincia

pytestmark = pytest.mark.django_db


@pytest.fixture(name="ciudadano")
def ciudadano_fixture():
    return Ciudadano.objects.create(nombre="Ana", apellido="Vat", documento=30555666)


@pytest.fixture(name="base")
def base_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    centro = Centro.objects.create(
        nombre="CFP 401", codigo="060144900", provincia=provincia
    )
    plan = PlanVersionCurricular.objects.create(
        nombre="Electricidad",
        provincia=provincia,
        sector=Sector.objects.create(nombre="Industria"),
        modalidad_cursada=ModalidadCursada.objects.create(nombre="Presencial"),
        horas_reloj=100,
    )
    TituloReferencia.objects.create(nombre="Electricista", plan_estudio=plan)
    return {"centro": centro, "plan": plan}


def _comision(base, programa, codigo, ciclo=2026):
    oferta = OfertaInstitucional.objects.create(
        centro=base["centro"],
        plan_curricular=base["plan"],
        programa=programa,
        ciclo_lectivo=ciclo,
    )
    return Comision.objects.create(
        oferta=oferta,
        codigo_comision=codigo,
        nombre=f"Comision {codigo}",
        fecha_inicio=date(2026, 3, 1),
        fecha_fin=date(2026, 12, 1),
        cupo=10,
    )


def _voucher(ciudadano, programa, estado, inicial, usada=0):
    return Voucher.objects.create(
        ciudadano=ciudadano,
        programa=programa,
        cantidad_inicial=inicial,
        cantidad_usada=usada,
        cantidad_disponible=inicial - usada,
        fecha_vencimiento=date.today() + timedelta(days=90),
        estado=estado,
    )


def test_proyeccion_de_programas_igual_al_contexto_del_template(ciudadano, base):
    beta = Programa.objects.create(nombre="beta programa")
    alfa = Programa.objects.create(nombre="Alfa Programa")
    comision = _comision(base, alfa, "COM-1")
    comision_oferta = _comision(base, alfa, "COM-2", ciclo=2027)
    voucher = _voucher(ciudadano, alfa, "activo", 10, 4)
    _voucher(ciudadano, alfa, "vencido", 5)
    _voucher(ciudadano, beta, "agotado", 3, 3)
    inscripcion = Inscripcion.objects.create(
        ciudadano=ciudadano, comision=comision, programa=alfa, estado="inscripta"
    )
    horario = ComisionHorario.objects.create(
        comision=comision,
        dia_semana=Dia.objects.create(nombre="Lunes"),
        hora_desde="09:00",
        hora_hasta="12:00",
    )
    registrador = User.objects.create_user(username="registrador_c04")
    for numero, presente in ((1, True), (2, True), (3, False)):
        sesion = SesionComision.objects.create(
            comision=comision,
            horario=horario,
            numero_sesion=numero,
            fecha=date(2026, 4, numero),
        )
        AsistenciaSesion.objects.create(
            sesion=sesion,
            inscripcion=inscripcion,
            presente=presente,
            registrado_por=registrador,
        )
    inscripcion_oferta = InscripcionOferta.objects.create(
        ciudadano=ciudadano,
        oferta=comision_oferta,
        estado="inscrito",
        inscrito_por=registrador,
    )

    programas = vat_detail.proyectar_aporte(ciudadano)["vat"]["programas"]

    # Orden por ``str(programa).lower()``.
    assert [p["nombre"] for p in programas] == ["Alfa Programa", "beta programa"]
    primero, segundo = programas
    assert primero["voucher_badge"] == {"tipo": "activo", "estado_display": ""}
    assert primero["voucher"] == {
        "id": voucher.pk,
        "url": reverse("vat_voucher_detail", args=[voucher.pk]),
        "estado_display": "Activo",
    }
    assert (primero["creditos_totales"], primero["creditos_actuales"]) == (15, 6)
    # Una inscripcion y una inscripcion de oferta.
    assert primero["cursos_asignados"] == 2
    assert (primero["asistencias_presentes"], primero["asistencias_registradas"]) == (
        2,
        3,
    )
    assert primero["inscripciones"] == [
        {
            "curso_texto": "Electricista",
            "comision": {
                "id": comision.pk,
                "codigo": "COM-1",
                "url": reverse("vat_comision_detail", args=[comision.pk]),
            },
            "estado_display": inscripcion.get_estado_display(),
            "asistencias_presentes": 2,
            "asistencias_registradas": 3,
            "asistencia_porcentaje": 67,
            "url": reverse("vat_inscripcion_detail", args=[inscripcion.pk]),
        }
    ]
    # El template enlaza la comision de la oferta con ``oferta.pk``.
    assert primero["inscripciones_oferta"] == [
        {
            "curso_texto": "Electricista",
            "comision": {
                "id": comision_oferta.pk,
                "codigo": "COM-2",
                "url": reverse("vat_comision_detail", args=[comision_oferta.pk]),
            },
            "estado_display": "Inscrito",
            "url": reverse(
                "vat_inscripcion_oferta_detail", args=[inscripcion_oferta.pk]
            ),
        }
    ]
    assert segundo["voucher_badge"] == {
        "tipo": "referencia",
        "estado_display": "Agotado",
    }
    assert segundo["voucher"]["estado_display"] == "Agotado"
    assert segundo["inscripciones"] == [] and segundo["inscripciones_oferta"] == []


def test_programa_sin_voucher(ciudadano, base):
    programa = Programa.objects.create(nombre="Solo cursos")
    comision = _comision(base, programa, "COM-9")
    Inscripcion.objects.create(
        ciudadano=ciudadano, comision=comision, programa=programa, estado="inscripta"
    )
    (item,) = vat_detail.proyectar_aporte(ciudadano)["vat"]["programas"]
    assert item["voucher_badge"] == {"tipo": "sin_voucher", "estado_display": ""}
    assert item["voucher"] is None
    assert item["inscripciones"][0]["asistencias_registradas"] == 0


def test_sin_registros_es_vacio(ciudadano):
    assert vat_detail.proyectar_aporte(ciudadano) == {"vat": {"programas": []}}


def test_consulta_propaga_la_excepcion_y_el_html_la_absorbe(ciudadano, monkeypatch):
    def roto(_ciudadano):
        raise RuntimeError("base caida")

    monkeypatch.setattr(vat_detail, "consultar_datos", roto)
    with pytest.raises(RuntimeError):
        vat_detail.proyectar_aporte(ciudadano)
    contexto = vat_detail.obtener_contexto(ciudadano, dc.logger_modulo)
    assert contexto == {
        "vat_inscripciones": [],
        "vat_vouchers": [],
        "vat_inscripciones_oferta": [],
        "vat_programas": [],
    }


def test_endpoint_http_bajo_el_prefijo_de_vat(ciudadano):
    client = Client()
    client.force_login(User.objects.create_superuser(username="c04_vat"))
    base = f"/api/web/vat/ciudadanos/{ciudadano.pk}/aportes/"
    respuesta = client.get(base + "vat/")
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "aporte": "vat",
        "secciones": {"vat": {"programas": []}},
    }
    assert client.get(base + "pwa/").status_code == 404
