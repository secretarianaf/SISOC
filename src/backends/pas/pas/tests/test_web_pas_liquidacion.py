"""Web API y vistas nativas: gestión de alertas, liquidación y nómina BNA."""

import io
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from core.models import Municipio, Provincia
from pas.models import (
    PasAviso,
    PasCircuitoMensual,
    PasDeclaracionJurada,
    PasEstado,
    PasHistorialEstado,
    PasIncompatibilidad,
    PasInvitacionDDJJ,
    PasPeriodoFormacion,
    PasPersona,
)
from pas.services import formacion_service, liquidacion_service
from pas.services.cruces_service import obtener_circuito_actual
from pas.services.estructura_salida import COLUMNAS_SALIDA

pytestmark = pytest.mark.django_db

CRUCES = "/api/web/pas/cruces/"
LIQUIDACION = "/api/web/pas/areas/liquidacion/"
DESCARGAR = "/api/web/pas/liquidacion/descargar-nomina/"


def _filas_xlsx(contenido):
    hoja = load_workbook(io.BytesIO(contenido), read_only=True)["nomina"]
    return list(hoja.iter_rows(values_only=True))


def _confirmar_url(pk):
    return f"{CRUCES}incompatibilidades/{pk}/confirmar/"


def _modificar_url(pk):
    return f"{CRUCES}incompatibilidades/{pk}/modificar/"


def _user(username, *codenames):
    user = get_user_model().objects.create_user(username)
    profile = user.profile
    profile.acceso_web = True
    profile.must_change_password = False
    profile.needs_profile_confirmation = False
    profile.save()
    for codename in codenames:
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="pas", codename=codename)
        )
    return user


def _client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture(name="catalogo")
def catalogo_fixture():
    estados = {
        nombre: PasEstado.objects.get_or_create(nombre=nombre)[0]
        for nombre in ("Activo", "Suspendido", "Baja")
    }
    avisos = {}
    for codigo, nombres in ((1, ["Activo"]), (10, ["Suspendido", "Baja"])):
        aviso = PasAviso.objects.get_or_create(
            codigo=codigo, defaults={"descripcion": f"Aviso {codigo}"}
        )[0]
        aviso.estados.add(*(estados[nombre] for nombre in nombres))
        avisos[codigo] = aviso
    return estados, avisos


@pytest.fixture(name="ubicacion")
def ubicacion_fixture():
    provincia = Provincia.objects.create(nombre="Buenos Aires liq")
    return provincia, Municipio.objects.create(
        nombre="La Plata liq", provincia=provincia
    )


def _persona(ubicacion, catalogo, n, estado="Activo", ddjj=True, apellido=None):
    estados, avisos = catalogo
    persona = PasPersona.objects.create(
        id_persona=700000 + n,
        apellidos=apellido or f"Apellido{n:02d}",
        nombres="Ana",
        dni=40000000 + n,
        cuit=f"2740000000{n}",
        provincia=ubicacion[0],
        municipio=ubicacion[1],
        estado=estados[estado],
    )
    persona.avisos.set([avisos[1 if estado == "Activo" else 10]])
    if ddjj:
        PasDeclaracionJurada.objects.bulk_create(
            [
                PasDeclaracionJurada(
                    persona=persona,
                    invitacion=PasInvitacionDDJJ.objects.create(persona=persona),
                    version=1,
                    provincia=ubicacion[0],
                    municipio=ubicacion[1],
                    domicilio="Calle 1",
                    correo_electronico="ana@example.com",
                    telefono_celular="1",
                    datos_mi_argentina_confirmados=True,
                    embarazada=False,
                    hijos_menores_a_cargo=False,
                    gastos_bajo_limite_smvm=True,
                    no_accedio_mercado_cambios=True,
                    acepto_declaracion=True,
                    texto_legal="x",
                    archivo_pdf="ddjj.pdf",
                    finalizada=timezone.now(),
                )
            ]
        )
    return persona


def _alerta(persona, catalogo, estado=PasIncompatibilidad.Estado.PENDIENTE):
    estados, avisos = catalogo
    return PasIncompatibilidad.objects.create(
        persona=persona,
        categoria=PasIncompatibilidad.Categoria.INGRESOS,
        origen=PasIncompatibilidad.Origen.SINTYS,
        periodo_impacto=obtener_circuito_actual().periodo,
        detalle="JUBILACION / PENSION",
        estado=estado,
        estado_propuesto=estados["Suspendido"],
        aviso_propuesto=avisos[10],
    )


def _circuito_cruzado():
    circuito = obtener_circuito_actual(crear=True)
    circuito.fecha_exportacion_sintys = timezone.now()
    circuito.fecha_importacion_sintys = timezone.now()
    circuito.save()
    return circuito


# --- Bandeja de alertas -----------------------------------------------------------


def test_bandeja_proyecta_la_alerta_con_su_cambio_y_las_opciones(ubicacion, catalogo):
    persona = _persona(ubicacion, catalogo, 1)
    alerta = _alerta(persona, catalogo)
    viewer = _client(_user("liq_ve", "view_paspersona"))

    datos = viewer.get(CRUCES).json()

    fila = datos["incompatibilidades"][0]
    assert fila["id"] == alerta.pk
    assert fila["persona_id"] == persona.pk
    assert fila["origen"] == "SINTyS"
    assert fila["categoria"] == "Ingresos"
    assert fila["estado_actual"] == "Activo"
    assert fila["cambio_propuesto"] == "Suspendido (10 - Aviso 10)"
    nombres = [estado["nombre"] for estado in datos["cambio_estado"]["estados"]]
    assert {"Activo", "Suspendido", "Baja"} <= set(nombres)
    assert datos["cambio_estado"]["avisos_por_estado"]
    assert datos["importacion_sintys"] is None


def test_confirmar_y_modificar_requieren_change_paspersona(ubicacion, catalogo):
    alerta = _alerta(_persona(ubicacion, catalogo, 1), catalogo)
    viewer = _client(_user("liq_ve2", "view_paspersona"))

    assert viewer.post(_confirmar_url(alerta.pk)).status_code == 403
    assert viewer.post(_modificar_url(alerta.pk)).status_code == 403
    alerta.refresh_from_db()
    assert alerta.estado == PasIncompatibilidad.Estado.PENDIENTE


def test_confirmar_aplica_el_cambio_y_responde_409_si_se_repite(ubicacion, catalogo):
    estados, _ = catalogo
    persona = _persona(ubicacion, catalogo, 1)
    alerta = _alerta(persona, catalogo)
    editor = _client(_user("liq_ed", "view_paspersona", "change_paspersona"))

    respuesta = editor.post(_confirmar_url(alerta.pk))

    assert respuesta.status_code == 200
    persona.refresh_from_db()
    assert persona.estado == estados["Suspendido"]
    alerta.refresh_from_db()
    assert alerta.estado == PasIncompatibilidad.Estado.CONFIRMADA
    assert editor.post(_confirmar_url(alerta.pk)).status_code == 409
    assert editor.post(_confirmar_url(999999)).status_code == 404
    assert editor.get(CRUCES).json()["incompatibilidades"] == []


def test_modificar_valida_el_formulario_y_confirma(ubicacion, catalogo):
    estados, avisos = catalogo
    persona = _persona(ubicacion, catalogo, 1)
    alerta = _alerta(persona, catalogo)
    editor = _client(_user("liq_ed2", "view_paspersona", "change_paspersona"))

    invalida = editor.post(_modificar_url(alerta.pk), {"estado": estados["Activo"].pk})
    assert invalida.status_code == 400
    assert invalida.json()["messages"] == ["Este campo es requerido."]

    datos = {"estado": estados["Activo"].pk, "avisos": [avisos[1].pk]}
    respuesta = editor.post(_modificar_url(alerta.pk), datos)

    assert respuesta.status_code == 200
    alerta.refresh_from_db()
    assert alerta.estado == PasIncompatibilidad.Estado.CONFIRMADA
    persona.refresh_from_db()
    assert persona.estado == estados["Activo"]
    assert editor.post(_modificar_url(alerta.pk), datos).status_code == 409


def test_importacion_web_informa_el_resumen_y_errores_de_formato(tmp_path):
    editor = _client(_user("liq_ed3", "view_paspersona", "change_paspersona"))
    malo = SimpleUploadedFile("retorno.txt", b"A|B\n1|2\n")
    bueno = SimpleUploadedFile(
        "retorno.txt",
        b"ID|APELLIDO|NOMBRE|NDOC|CUIT_TXT|EVALUACION|MOTIVO\n"
        b"1|X|Y|2|3|COMPATIBLE|\n",
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        rechazo = editor.post(f"{CRUCES}importar-sintys/", {"archivo": malo})
        ok = editor.post(f"{CRUCES}importar-sintys/", {"archivo": bueno})

    assert rechazo.status_code == 400
    assert "Faltan las columnas" in rechazo.json()["message"]
    assert ok.status_code == 200
    assert ok.json()["resumen"]["compatibles"] == 1
    assert editor.get(CRUCES).json()["importacion_sintys"]["total"] == 1


def test_importacion_nativa_muestra_el_resumen_y_el_error(tmp_path):
    usuario = get_user_model().objects.create_superuser("liq_admin", "a@a.com", "x")
    client = Client()
    client.force_login(usuario)
    malo = SimpleUploadedFile("retorno.txt", b"A|B\n1|2\n")
    bueno = SimpleUploadedFile(
        "retorno.txt",
        b"ID|APELLIDO|NOMBRE|NDOC|CUIT_TXT|EVALUACION|MOTIVO\n" b"1|X|Y|2|3|NADA|\n",
    )
    url = reverse("pas_cruces_importar_sintys")

    with override_settings(MEDIA_ROOT=tmp_path):
        rechazo = client.post(url, {"archivo": malo}, follow=True)
        ok = client.post(url, {"archivo": bueno}, follow=True)

    assert "Faltan las columnas" in rechazo.content.decode()
    contenido = ok.content.decode()
    assert "Retorno SINTyS procesado: 1 registros" in contenido
    assert "evaluación desconocida" in contenido


# --- Liquidación ------------------------------------------------------------------


def test_puntos_de_control_bloquean_hasta_que_los_cruces_esten_ok(ubicacion, catalogo):
    persona = _persona(ubicacion, catalogo, 1)
    circuito = obtener_circuito_actual()

    puntos = liquidacion_service.puntos_de_control(circuito)
    assert [punto["estado"] for punto in puntos] == [
        "pendiente",
        "sin_integrar",
        "sin_integrar",
        "ok",
    ]
    assert puntos[0]["detalle"] == "Falta exportar el padrón a SINTyS."
    assert not liquidacion_service.descarga_habilitada(puntos)

    circuito = obtener_circuito_actual(crear=True)
    circuito.fecha_exportacion_sintys = timezone.now()
    circuito.save()
    assert (
        "importar el retorno"
        in liquidacion_service.puntos_de_control(circuito)[0]["detalle"]
    )

    circuito = _circuito_cruzado()
    _alerta(persona, catalogo)
    assert "1 alertas" in liquidacion_service.puntos_de_control(circuito)[0]["detalle"]

    PasIncompatibilidad.objects.update(estado=PasIncompatibilidad.Estado.CONFIRMADA)
    puntos = liquidacion_service.puntos_de_control(circuito)
    assert puntos[0]["estado"] == "ok"
    assert liquidacion_service.descarga_habilitada(puntos)


def test_ddjj_sin_procesar_bloquea_la_descarga(ubicacion, catalogo):
    persona = _persona(ubicacion, catalogo, 1)
    PasDeclaracionJurada.objects.filter(persona=persona).update(finalizada=None)

    puntos = liquidacion_service.puntos_de_control(_circuito_cruzado())

    assert puntos[3]["estado"] == "pendiente"
    assert "1 declaraciones juradas" in puntos[3]["detalle"]
    assert not liquidacion_service.descarga_habilitada(puntos)


def test_preliquidacion_bloquea_por_estado_ddjj_y_cruces(ubicacion, catalogo):
    habilitado = _persona(ubicacion, catalogo, 1)
    _persona(ubicacion, catalogo, 2, ddjj=False)
    suspendido = _persona(ubicacion, catalogo, 3, estado="Suspendido")
    con_alerta = _persona(ubicacion, catalogo, 4)
    _persona(ubicacion, catalogo, 5, estado="Baja")
    _alerta(con_alerta, catalogo)
    viewer = _client(_user("liq_ve3", "view_paspersona"))

    datos = viewer.get(LIQUIDACION).json()

    liquidacion = datos["liquidacion"]
    assert datos["can_download"] is False
    assert liquidacion["titulares_a_acreditar"] == 1
    assert liquidacion["titulares_bloqueados"] == 3
    assert liquidacion["total_a_liquidar"] == "78000.00"
    assert liquidacion["descarga_habilitada"] is False
    filas = {fila["id"]: fila for fila in liquidacion["filas"]}
    assert len(filas) == 4
    assert filas[habilitado.pk]["estado_final"] == "Habilitado"
    assert filas[habilitado.pk]["monto"] == "78000.00"
    assert filas[habilitado.pk]["fch"] is None
    assert filas[suspendido.pk]["estado_final"] == "Bloqueado: Suspendido"
    assert filas[suspendido.pk]["monto"] == "0.00"
    assert filas[con_alerta.pk]["cruces_ok"] is False
    assert any(fila["estado_final"] == "Bloqueado: Sin DDJJ" for fila in filas.values())


def test_descarga_requiere_permiso_y_responde_409_si_esta_bloqueada(
    ubicacion, catalogo
):
    _persona(ubicacion, catalogo, 1)
    sin_permiso = _client(_user("liq_ve4", "view_paspersona"))
    con_permiso = _client(_user("liq_pago", "view_paspersona", "download_nomina_pago"))

    assert sin_permiso.post(DESCARGAR).status_code == 403
    respuesta = con_permiso.post(DESCARGAR)

    assert respuesta.status_code == 409
    assert respuesta.json()["motivos"] == ["Falta exportar el padrón a SINTyS."]
    assert not PasCircuitoMensual.objects.get().archivo_nomina_pago


def test_descarga_genera_el_excel_bna_una_sola_vez(ubicacion, catalogo, tmp_path):
    habilitado = _persona(ubicacion, catalogo, 1, apellido="=Pérez Gómez")
    _persona(ubicacion, catalogo, 2, ddjj=False)
    _circuito_cruzado()
    usuario = _user("liq_pago2", "view_paspersona", "download_nomina_pago")
    cliente = _client(usuario)

    with override_settings(MEDIA_ROOT=tmp_path):
        respuesta = cliente.post(DESCARGAR)
        _persona(ubicacion, catalogo, 3)
        repetida = cliente.post(DESCARGAR)

    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == liquidacion_service.TIPO_XLSX
    periodo = obtener_circuito_actual().periodo
    assert respuesta["Content-Disposition"] == (
        f'attachment; filename="nomina_pago_pas_bna_{periodo:%Y%m}.xlsx"'
    )
    filas = _filas_xlsx(respuesta.content)
    assert filas[0] == COLUMNAS_SALIDA
    assert filas[1] == (
        habilitado.id_persona,
        "PAS",
        "'=Pérez Gómez",
        "Ana",
        habilitado.dni,
        habilitado.cuit,
        "Buenos Aires liq",
        "La Plata liq",
        78000,
        None,
        None,
        None,
        None,
        None,
        None,
    )
    assert len(filas) == 2
    circuito = PasCircuitoMensual.objects.get()
    assert circuito.fecha_cierre is not None
    assert circuito.nomina_descargada_por == usuario
    assert repetida.content == respuesta.content


def test_descarga_nativa_redirige_si_esta_bloqueada_o_entrega_el_excel(
    ubicacion, catalogo, tmp_path
):
    _persona(ubicacion, catalogo, 1)
    usuario = get_user_model().objects.create_superuser("liq_admin2", "b@b.com", "x")
    client = Client()
    client.force_login(usuario)
    url = reverse("pas_liquidacion_descargar_nomina")

    bloqueada = client.post(url)
    assert bloqueada.status_code == 302
    _circuito_cruzado()
    with override_settings(MEDIA_ROOT=tmp_path):
        ok = client.post(url)

    assert ok.status_code == 200
    assert ok["Content-Type"] == liquidacion_service.TIPO_XLSX
    assert _filas_xlsx(ok.content)[0][:2] == ("idPersona", "Programa")


def test_con_fch_integrado_el_rojo_bloquea_al_titular(ubicacion, catalogo, monkeypatch):
    monkeypatch.setattr(formacion_service, "FORMACION_INTEGRADA", True)
    persona = _persona(ubicacion, catalogo, 1)
    circuito = _circuito_cruzado()

    resumen = liquidacion_service.resumen_liquidacion(circuito)

    assert resumen["puntos_control"][2]["estado"] == "ok"
    assert resumen["titulares_a_acreditar"] == 0
    assert resumen["titulares_bloqueados"] == 1
    assert resumen["filas"][0]["fch"] == "rojo"
    assert resumen["filas"][0]["estado_final"] == "Bloqueado: FCH rojo"
    assert len(_filas_xlsx(liquidacion_service.generar_nomina_bna(circuito))) == 1

    # Con crédito arrastrado suficiente el titular vuelve a quedar habilitado.
    inicio = formacion_service.calcular_periodo_formacion()["inicio_actual"]
    PasPeriodoFormacion.objects.create(
        persona=persona,
        inicio=inicio - timedelta(days=90),
        fin=inicio - timedelta(days=1),
        puntos_periodo=220,
        excedente=120,
        estado=PasPeriodoFormacion.Estado.CUMPLIDO,
    )
    resumen = liquidacion_service.resumen_liquidacion(circuito)
    assert resumen["titulares_a_acreditar"] == 1
    assert resumen["filas"][0]["fch"] == "verde"
    assert len(_filas_xlsx(liquidacion_service.generar_nomina_bna(circuito))) == 2


def test_formacion_arrastra_el_excedente_al_ciclo_siguiente(
    ubicacion, catalogo, monkeypatch
):
    persona = _persona(ubicacion, catalogo, 1)
    inicio = date(2026, 1, 1)
    fin = inicio + timedelta(days=89)
    cursos = [{"puntos": "120", "estado_codigo": "completada"}]

    cerrado = formacion_service.cerrar_periodo_formacion(persona, inicio, fin, cursos)
    assert (cerrado.credito_inicial, cerrado.puntos_periodo, cerrado.excedente) == (
        0,
        120,
        20,
    )
    assert cerrado.estado == PasPeriodoFormacion.Estado.CUMPLIDO

    siguiente = formacion_service.resumir_formacion(
        [{"puntos": 80, "estado_codigo": "completada"}],
        persona=persona,
        fecha_actual=fin + timedelta(days=1),
    )
    assert siguiente["credito_inicial"] == 20
    assert siguiente["puntos"] == 100
    assert siguiente["estado"] == "cumplido"
    assert siguiente["semaforo"] == "verde"
    assert siguiente["bloquea_pago"] is False

    parcial = formacion_service.cerrar_periodo_formacion(
        persona,
        fin + timedelta(days=1),
        fin + timedelta(days=90),
        [{"puntos": 30, "estado_codigo": "en_curso"}],
    )
    assert (parcial.credito_inicial, parcial.excedente) == (20, 0)
    assert parcial.estado == PasPeriodoFormacion.Estado.PARCIAL
    # Idempotente: cerrar dos veces el mismo ciclo actualiza el mismo registro.
    formacion_service.cerrar_periodo_formacion(persona, inicio, fin, cursos)
    assert PasPeriodoFormacion.objects.filter(persona=persona).count() == 2

    sin_cursos = formacion_service.resumir_formacion([], persona=None)
    assert sin_cursos["semaforo"] == "rojo"
    assert sin_cursos["bloquea_pago"] is False  # FCH sin integrar no bloquea
    monkeypatch.setattr(formacion_service, "FORMACION_INTEGRADA", True)
    assert formacion_service.resumir_formacion([])["bloquea_pago"] is True


def test_cierre_masivo_de_ciclos_solo_con_fch_integrado(
    ubicacion, catalogo, monkeypatch
):
    _persona(ubicacion, catalogo, 1)
    _persona(ubicacion, catalogo, 2)

    assert formacion_service.cerrar_periodos_formacion(date(2026, 5, 1)) == {
        "cerrados": 0,
        "integrada": False,
    }
    monkeypatch.setattr(formacion_service, "FORMACION_INTEGRADA", True)
    assert formacion_service.cerrar_periodos_formacion(date(2026, 1, 15)) == {
        "cerrados": 0,
        "integrada": True,
    }
    assert formacion_service.cerrar_periodos_formacion(date(2026, 5, 1)) == {
        "cerrados": 2,
        "integrada": True,
    }
    assert (
        formacion_service.cerrar_periodos_formacion(date(2026, 5, 2))["cerrados"] == 0
    )
    periodo = PasPeriodoFormacion.objects.first()
    assert periodo.inicio == date(2026, 1, 1)
    assert periodo.fin == date(2026, 3, 31)
    assert periodo.estado == PasPeriodoFormacion.Estado.INCUMPLIDO


def test_tarea_celery_delega_en_el_servicio(monkeypatch):
    from pas import tasks  # pylint: disable=import-outside-toplevel

    monkeypatch.setattr(
        tasks, "cerrar_periodos_formacion", lambda: {"cerrados": 7, "integrada": True}
    )

    assert tasks.cerrar_periodo_formacion() == {"cerrados": 7, "integrada": True}


def test_area_formacion_expone_credito_y_semaforo(ubicacion, catalogo):
    persona = _persona(ubicacion, catalogo, 1)
    viewer = _client(_user("liq_ve5", "view_paspersona"))

    resumen = viewer.get(f"/api/web/pas/areas/formacion/?persona={persona.pk}").json()[
        "resumen"
    ]

    assert resumen["credito_inicial"] == 0
    assert resumen["semaforo"] == "rojo"
    assert resumen["bloquea_pago"] is False
    assert resumen["integrada"] is False


# --- Panel: chips, historial y datos de formación locales ---------------------------


def test_listado_marca_ddjj_y_fch_pendientes(ubicacion, catalogo, monkeypatch):
    con_ddjj = _persona(ubicacion, catalogo, 1)
    sin_ddjj = _persona(ubicacion, catalogo, 2, ddjj=False)
    monkeypatch.setattr(
        formacion_service, "_formacion_demo", lambda: {con_ddjj.dni: 100}
    )
    viewer = _client(_user("liq_ve6", "view_paspersona"))

    filas = {
        fila["id"]: fila
        for fila in viewer.get("/api/web/pas/personas/").json()["results"]
    }

    assert (filas[con_ddjj.pk]["tag_ddjj"], filas[con_ddjj.pk]["tag_fch"]) == (
        False,
        False,
    )
    assert (filas[sin_ddjj.pk]["tag_ddjj"], filas[sin_ddjj.pk]["tag_fch"]) == (
        True,
        True,
    )


def test_confirmar_y_modificar_dejan_el_detalle_en_el_historial(ubicacion, catalogo):
    estados, avisos = catalogo
    confirmada = _persona(ubicacion, catalogo, 1)
    modificada = _persona(ubicacion, catalogo, 2)
    alerta = _alerta(confirmada, catalogo)
    alerta.detalle = "MAYOR DE 65 AÑOS + JUBILACION / PENSION"
    alerta.save()
    otra = _alerta(modificada, catalogo)
    editor = _client(_user("liq_ed4", "view_paspersona", "change_paspersona"))

    editor.post(_confirmar_url(alerta.pk))
    editor.post(
        _modificar_url(otra.pk),
        {"estado": estados["Activo"].pk, "avisos": [avisos[1].pk]},
    )

    eventos = editor.get(f"/api/web/pas/panel/{confirmada.pk}/").json()[
        "eventos_historial"
    ]
    assert eventos[0]["observacion"] == (
        "SINTyS · Ingresos: MAYOR DE 65 AÑOS + JUBILACION / PENSION"
    )
    historial = PasHistorialEstado.objects.get(persona=modificada)
    assert historial.observacion == "SINTyS · Ingresos: JUBILACION / PENSION"
    nativo = Client()
    nativo.force_login(
        get_user_model().objects.create_superuser("liq_admin3", "c@c.com", "x")
    )
    assert (
        "MAYOR DE 65 AÑOS + JUBILACION / PENSION"
        in nativo.get(
            reverse("pas_panel_control_persona", kwargs={"pk": confirmada.pk})
        ).content.decode()
    )


def test_formacion_demo_solo_con_debug_y_json_valido(
    ubicacion, catalogo, monkeypatch, settings
):
    persona = _persona(ubicacion, catalogo, 1)
    monkeypatch.setenv("PAS_FORMACION_DEMO", f'{{"{persona.dni}": 50}}')

    settings.DEBUG = False
    assert formacion_service.obtener_formacion_persona(persona) == []
    settings.DEBUG = True
    cursos = formacion_service.obtener_formacion_persona(persona)
    assert [curso["puntos"] for curso in cursos] == [50]
    resumen = formacion_service.resumir_formacion(cursos, persona=persona)
    assert (resumen["puntos"], resumen["semaforo"]) == (50, "amarillo")
    assert formacion_service.obtener_puntos_por_dni([persona])[persona.dni] == {
        "puntos": 50,
        "total_cursos": 1,
    }
    assert formacion_service.obtener_formacion_persona(None) == []
    monkeypatch.setenv("PAS_FORMACION_DEMO", "no es json")
    assert formacion_service.obtener_formacion_persona(persona) == []
    monkeypatch.setenv("PAS_FORMACION_DEMO", "")
    assert formacion_service.obtener_formacion_persona(persona) == []


# --- Preliquidación en CSV ----------------------------------------------------------

PRELIQ_CSV = "/api/web/pas/liquidacion/preliquidacion-csv/"


def _csv_user(username, *codenames):
    """Usuario con el rol transversal de exportación CSV (permiso sobre Group)."""
    user = _user(username, *codenames)
    rol, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Group),
        codename="role_exportar_a_csv",
        defaults={"name": "Exportar a csv"},
    )
    user.user_permissions.add(rol)
    return user


def test_csv_de_preliquidacion_incluye_todas_las_filas(
    ubicacion, catalogo, monkeypatch
):
    monkeypatch.setattr(liquidacion_service, "FILAS_PRELIQUIDACION", 1)
    habilitado = _persona(ubicacion, catalogo, 1, apellido="=Alfa")
    _persona(ubicacion, catalogo, 2, ddjj=False, apellido="Beta")
    cliente = _client(_csv_user("liq_csv", "view_paspersona"))

    datos = cliente.get(LIQUIDACION).json()
    respuesta = cliente.get(PRELIQ_CSV)

    assert datos["can_export_csv"] is True
    assert respuesta.status_code == 200
    periodo = obtener_circuito_actual().periodo
    assert respuesta["Content-Disposition"] == (
        f'attachment; filename="preliquidacion_pas_{periodo:%Y%m}.csv"'
    )
    lineas = respuesta.content.decode("utf-8-sig").splitlines()
    assert lineas[0] == "Titular,CUIL,CBU BNA,Monto,FCH,Cruces,DDJJ,Estado final"
    assert lineas[1] == (
        f'"\'=Alfa, Ana",{habilitado.cuit},,78000.00,Sin integrar,OK,OK,Habilitado'
    )
    assert lineas[2].endswith(",0.00,Sin integrar,OK,No,Bloqueado: Sin DDJJ")
    assert len(lineas) == 3


def test_csv_de_preliquidacion_requiere_el_permiso_de_exportacion(ubicacion, catalogo):
    _persona(ubicacion, catalogo, 1)
    sin_csv = _client(_user("liq_csv_no", "view_paspersona"))

    assert sin_csv.get(LIQUIDACION).json()["can_export_csv"] is False
    assert sin_csv.get(PRELIQ_CSV).status_code == 403
    nativo = Client()
    nativo.force_login(
        get_user_model().objects.create_superuser("liq_csv_admin", "d@d.com", "x")
    )
    ok = nativo.get(reverse("pas_liquidacion_preliquidacion_csv"))
    assert ok.status_code == 200
    assert ok.content.decode("utf-8-sig").startswith("Titular,CUIL,")


def test_los_cursos_solo_quedan_inscriptos_o_aprobados():
    cursos = formacion_service.normalizar_cursos(
        [
            {"curso": "A", "estado": "Completada", "estado_codigo": "completada"},
            {"curso": "B", "estado": "Aprobado", "estado_codigo": ""},
            {"curso": "C", "estado": "En curso", "estado_codigo": "en_curso"},
            {"curso": "D"},
        ]
    )

    assert [(c["estado_codigo"], c["estado"]) for c in cursos] == [
        ("aprobado", "Aprobado"),
        ("aprobado", "Aprobado"),
        ("inscripto", "Inscripto"),
        ("inscripto", "Inscripto"),
    ]
    resumen = formacion_service.resumir_formacion(
        [
            {"puntos": 30, "estado_codigo": "aprobado"},
            {"puntos": 0, "estado": "Inscripto"},
        ]
    )
    assert resumen["cursos_completados"] == 1
    assert "Solo los cursos aprobados suman puntos." in resumen["detalle"]
