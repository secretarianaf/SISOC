"""Panel del backoffice: escuelas, búsquedas, asignaciones, actas y acceso."""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from inspecciones.models import AsignacionEscuela, Escuela
from inspecciones.services.formato import hoy
from inspecciones.services.importacion import (
    analizar_asignaciones,
    aplicar_asignaciones,
)

pytestmark = pytest.mark.django_db

XHR = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


def _datos_escuela(geografia, **cambios):
    datos = {
        "provincia": geografia["bsas"].pk,
        "localidad": geografia["san_justo"].pk,
        "cueanexo": "060123400",
        "nombre": "EP N° 12",
        "domicilio": "Av. Perón 3245",
        "cp": "b1754abc",
        "telefono": "011 4651-2233",
        "mail": "ep12@abc.gob.ar",
    }
    datos.update(cambios)
    return datos


# --- Alta y edición de escuelas -----------------------------------------


def test_alta_de_escuela(panel, geografia):
    respuesta = panel.post(
        reverse("inspecciones_escuela_nueva"), _datos_escuela(geografia), **XHR
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["ok"] is True
    escuela = Escuela.objects.get()
    assert escuela.codigo == escuela.cue == "060123400"
    assert escuela.cp == "B1754ABC"
    assert escuela.localidad == "San Justo"
    assert escuela.distrito == "La Matanza"
    assert escuela.a_revisar is False


@pytest.mark.parametrize(
    "cambios, campo",
    [
        ({"cueanexo": "06012340"}, "cueanexo"),
        ({"cueanexo": "06012340A"}, "cueanexo"),
        ({"mail": "ep12@"}, "mail"),
        ({"cp": "1754-B"}, "cp"),
        ({"nombre": ""}, "nombre"),
    ],
)
def test_alta_valida_los_campos(panel, geografia, cambios, campo):
    respuesta = panel.post(
        reverse("inspecciones_escuela_nueva"),
        _datos_escuela(geografia, **cambios),
        **XHR,
    )

    assert respuesta.status_code == 400
    assert campo in respuesta.context["form"].errors
    assert Escuela.objects.count() == 0


def test_alta_rechaza_localidad_de_otra_provincia(panel, geografia):
    respuesta = panel.post(
        reverse("inspecciones_escuela_nueva"),
        _datos_escuela(geografia, localidad=geografia["ushuaia"].pk),
        **XHR,
    )

    assert "localidad" in respuesta.context["form"].errors


def test_cueanexo_duplicado_avisa_con_link(panel, geografia):
    existente = Escuela.objects.create(
        codigo="060123400", cue="060123400", nombre="EP 12 vieja"
    )

    respuesta = panel.post(
        reverse("inspecciones_escuela_nueva"), _datos_escuela(geografia), **XHR
    )

    assert respuesta.status_code == 400
    html = respuesta.content.decode()
    assert "Ya existe: EP 12 vieja" in html
    assert f"?editar={existente.pk}" in html


def test_guardar_y_cargar_otra(panel, geografia):
    respuesta = panel.post(
        reverse("inspecciones_escuela_nueva"),
        {**_datos_escuela(geografia), "otra": "1"},
        **XHR,
    )

    assert respuesta.json()["otra"] is True


def test_edicion_mantiene_codigo_y_quita_marca(panel, geografia):
    escuela = Escuela.objects.create(
        codigo="060123400",
        cue="060123400",
        nombre="EP 12",
        mail="roto@",
        a_revisar=True,
        motivos_revision=["mail_invalido", "localidad_inexistente"],
    )
    url = reverse("inspecciones_escuela_editar", args=[escuela.pk])

    formulario = panel.get(url, **XHR)
    assert "Datos a revisar" in formulario.content.decode()
    respuesta = panel.post(
        url, _datos_escuela(geografia, cueanexo="060123499", nombre="EP 12 bis"), **XHR
    )

    assert respuesta.status_code == 200
    escuela.refresh_from_db()
    assert escuela.codigo == "060123400"
    assert escuela.cue == "060123499"
    assert escuela.nombre == "EP 12 bis"
    assert escuela.a_revisar is False
    assert escuela.motivos_revision == []


def test_edicion_permite_conservar_su_propio_cueanexo(panel, geografia):
    escuela = Escuela.objects.create(codigo="060123400", cue="060123400", nombre="EP")

    respuesta = panel.post(
        reverse("inspecciones_escuela_editar", args=[escuela.pk]),
        _datos_escuela(geografia),
        **XHR,
    )

    assert respuesta.status_code == 200


def test_listado_filtra_y_pagina(panel, geografia):
    Escuela.objects.bulk_create(
        [
            Escuela(
                codigo=f"0600000{i:02d}",
                cue=f"0600000{i:02d}",
                nombre=f"Escuela {i:02d}",
                provincia=geografia["bsas"],
                a_revisar=i % 2 == 0,
            )
            for i in range(30)
        ]
    )

    pagina = panel.get(reverse("inspecciones_panel"))
    assert len(pagina.context["escuelas"]) == 25
    assert pagina.context["page_obj"].paginator.count == 30
    a_revisar = panel.get(reverse("inspecciones_panel"), {"a_revisar": "1"})
    assert a_revisar.context["page_obj"].paginator.count == 15
    assert a_revisar.context["contador_a_revisar"] == 15
    busqueda = panel.get(reverse("inspecciones_panel"), {"q": "060000007"})
    assert [e.nombre for e in busqueda.context["escuelas"]] == ["Escuela 07"]
    otra = panel.get(reverse("inspecciones_panel"), {"provincia": geografia["caba"].pk})
    assert otra.context["page_obj"].paginator.count == 0
    invalido = panel.get(
        reverse("inspecciones_panel"), {"provincia": "x", "editar": "y"}
    )
    assert invalido.status_code == 200


# --- Búsquedas AJAX -----------------------------------------------------


def test_busqueda_de_escuelas_desde_tres_letras_con_tope(panel, geografia):
    Escuela.objects.bulk_create(
        [
            Escuela(
                codigo=f"0700000{i:02d}", cue=f"0700000{i:02d}", nombre=f"Sarmiento {i}"
            )
            for i in range(25)
        ]
    )
    url = reverse("inspecciones_ajax_escuelas")

    assert panel.get(url, {"q": "Sa"}).json() == {"results": []}
    resultados = panel.get(url, {"q": "sar"}).json()["results"]
    assert len(resultados) == 20
    assert "070000000" in resultados[0]["detalle"]


def test_busqueda_de_inspectores_solo_rol_inspector(panel, inspector_a, coordinacion):
    inspector_a.last_name = "Gómez"
    inspector_a.save()
    inspector_a.profile.dni = "30123456"
    inspector_a.profile.save(update_fields=["dni"])
    get_user_model().objects.create_user(username="inspector_sin_rol")
    url = reverse("inspecciones_ajax_inspectores")

    assert panel.get(url, {"q": "in"}).json() == {"results": []}
    por_usuario = panel.get(url, {"q": "insp"}).json()["results"]
    assert [r["id"] for r in por_usuario] == [inspector_a.pk]
    assert [r["id"] for r in panel.get(url, {"q": "301"}).json()["results"]] == [
        inspector_a.pk
    ]
    assert panel.get(url, {"q": "coordinacion"}).json()["results"] == []
    programa = panel.get(url, {"q": "coordinacion", "alcance": "programa"}).json()
    assert [r["id"] for r in programa["results"]] == [coordinacion.pk]


def test_busqueda_de_inspectores_tope_de_veinte(panel):
    for i in range(25):
        user = get_user_model().objects.create_user(username=f"insp{i:02d}")
        user.profile.es_inspector_escolar = True
        user.profile.inspecciones_rol = "inspector"
        user.profile.save(update_fields=["es_inspector_escolar", "inspecciones_rol"])

    resultados = panel.get(reverse("inspecciones_ajax_inspectores"), {"q": "insp"})

    assert len(resultados.json()["results"]) == 20


def test_localidades_de_la_provincia_con_municipio(panel, geografia):
    respuesta = panel.get(
        reverse("inspecciones_ajax_localidades"),
        {"provincia": geografia["bsas"].pk, "q": "san jos"},
    ).json()

    assert sorted(r["text"] for r in respuesta["results"]) == [
        "San José · Almirante Brown",
        "San José · Lomas de Zamora",
    ]
    sin_provincia = panel.get(reverse("inspecciones_ajax_localidades"), {"q": "san"})
    assert sin_provincia.json() == {"results": []}


# --- Asignaciones -------------------------------------------------------


def test_alta_de_asignacion(panel, escuela, inspector_a, gestor):
    respuesta = panel.post(
        reverse("inspecciones_asignacion_nueva"),
        {
            "fecha": hoy().isoformat(),
            "inspector": inspector_a.pk,
            "escuela": escuela.pk,
        },
        **XHR,
    )

    assert respuesta.status_code == 200
    asignacion = AsignacionEscuela.objects.get()
    assert asignacion.inspector == inspector_a
    assert asignacion.creada_por == gestor


def test_asignacion_rechaza_usuario_sin_rol_inspector(panel, escuela, coordinacion):
    respuesta = panel.post(
        reverse("inspecciones_asignacion_nueva"),
        {
            "fecha": hoy().isoformat(),
            "inspector": coordinacion.pk,
            "escuela": escuela.pk,
        },
        **XHR,
    )

    assert respuesta.status_code == 400
    assert AsignacionEscuela.objects.count() == 0


def test_asignacion_duplicada_avisa_y_permite_otra_visita(
    panel, escuela, inspector_a, inspector_b
):
    AsignacionEscuela.objects.create(
        escuela=escuela, inspector=inspector_b, fecha=hoy()
    )
    datos = {
        "fecha": hoy().isoformat(),
        "inspector": inspector_a.pk,
        "escuela": escuela.pk,
    }

    aviso = panel.get(reverse("inspecciones_ajax_verificar_asignacion"), datos).json()
    respuesta = panel.post(reverse("inspecciones_asignacion_nueva"), datos, **XHR)

    assert aviso["otras"] == ["Inspector_B"]
    assert "otra visita" in respuesta.json()["mensaje"]
    assert AsignacionEscuela.objects.filter(escuela=escuela, fecha=hoy()).count() == 2
    repetida = panel.post(reverse("inspecciones_asignacion_nueva"), datos, **XHR)
    assert repetida.status_code == 400


def test_quitar_asignacion_sin_acta(panel, asignada_a):
    panel.post(reverse("inspecciones_asignacion_quitar", args=[asignada_a.pk]))

    assert not AsignacionEscuela.objects.filter(pk=asignada_a.pk).exists()


def test_quitar_bloqueado_si_tiene_acta(panel, api_a, escuela, asignada_a, cerrar):
    _uuid, cierre = cerrar(api_a, escuela)
    assert cierre.status_code == 200

    respuesta = panel.post(
        reverse("inspecciones_asignacion_quitar", args=[asignada_a.pk]), follow=True
    )

    assert AsignacionEscuela.objects.filter(pk=asignada_a.pk).exists()
    assert "ya tiene un acta" in respuesta.content.decode()


def test_listado_de_jornada_con_estados(panel, api_a, escuela, asignada_a, cerrar):
    url = reverse("inspecciones_asignaciones")
    pendiente = panel.get(url)
    assert pendiente.context["filas"][0]["estado"] == "pendiente"
    cerrar(api_a, escuela)

    finalizada = panel.get(url)

    fila = finalizada.context["filas"][0]
    assert fila["estado"] == "finalizada"
    assert fila["se_puede_quitar"] is False
    assert finalizada.context["totales"]["finalizada"] == 1
    otra_jornada = panel.get(url, {"fecha": (hoy() + timedelta(days=1)).isoformat()})
    assert otra_jornada.context["totales"]["total"] == 0
    anuladas = panel.get(url, {"estado_acta": "anuladas"})
    assert anuladas.context["filas"] == []


def test_importar_asignaciones(planilla, inspector_a, coordinacion, escuela):
    ajeno = get_user_model().objects.create_user(username="sin_programa")
    inspector_a.profile.dni = "30111222"
    inspector_a.profile.save(update_fields=["dni"])
    archivo = planilla(
        [
            ("fecha", "cueanexo", "inspector"),
            ("2026-10-15", escuela.cue, "inspector_a"),
            ("15/10/2026", "060123400", "30.111.222"),
            ("2026-10-15", "999999999", "inspector_a"),
            ("2026-10-15", "060123400", "sin_programa"),
            ("2026-10-15", "060123400", "coordinacion"),
            ("ayer", "060123400", "inspector_a"),
        ],
        nombre="asignaciones.csv",
    )

    analisis = analizar_asignaciones(archivo)
    assert AsignacionEscuela.objects.count() == 0
    resumen, _ = aplicar_asignaciones(analisis["datos"], actor=coordinacion)

    assert resumen["nuevas"] == 1
    assert resumen["repetidas"] == 1
    assert resumen["rechazadas"] == 4
    asignacion = AsignacionEscuela.objects.get()
    assert asignacion.inspector == inspector_a
    assert asignacion.creada_por == coordinacion
    assert ajeno.asignaciones_inspeccion.count() == 0


# --- Actas ----------------------------------------------------------------


def _acta_cerrada(api_a, escuela, cerrar, imagen, nuevo_uuid):
    inspeccion_uuid = nuevo_uuid()
    imagen_uuid = nuevo_uuid()
    subida = api_a.put(
        f"/api/inspecciones/borradores/{inspeccion_uuid}/imagenes/{imagen_uuid}/",
        {"archivo": imagen(), "tipo": "ingreso", "descripcion": "Frente"},
        format="multipart",
    )
    assert subida.status_code in (200, 201), subida.content
    _uuid, cierre = cerrar(
        api_a, escuela, inspeccion_uuid=inspeccion_uuid, imagen_ingreso=imagen_uuid
    )
    assert cierre.status_code == 200, cierre.content
    return cierre.json()["numero"], imagen_uuid


def test_listado_y_detalle_del_acta(panel, api_a, escuela, cerrar, imagen, nuevo_uuid):
    numero, imagen_uuid = _acta_cerrada(api_a, escuela, cerrar, imagen, nuevo_uuid)

    listado = panel.get(reverse("inspecciones_actas"))
    assert [f["acta"].numero for f in listado.context["filas"]] == [numero]
    detalle = panel.get(reverse("inspecciones_acta_detalle", args=[numero]))

    assert detalle.status_code == 200
    codigos = [fila["codigo"] for fila in detalle.context["respuestas"]]
    assert codigos == [f"F{i:02d}" for i in range(17)]
    html = detalle.content.decode()
    assert "Personal presente / previsto" in html
    assert detalle.context["resumen_acta"]["personal"] == "20 / 24"
    assert reverse("inspecciones_acta_imagen", args=[numero, imagen_uuid]) in html
    imagen_respuesta = panel.get(
        reverse("inspecciones_acta_imagen", args=[numero, imagen_uuid])
    )
    assert imagen_respuesta.status_code == 200
    assert imagen_respuesta["Cache-Control"] == "private, no-store"
    pdf = panel.get(reverse("inspecciones_acta_pdf", args=[numero]))
    assert pdf.status_code == 404
    assert "/media/" not in html


def test_detalle_muestra_anulacion_y_prueba(
    panel, api_a, escuela, cerrar, imagen, nuevo_uuid, gestor
):
    from django.utils import timezone

    from inspecciones.models import Acta

    numero, _ = _acta_cerrada(api_a, escuela, cerrar, imagen, nuevo_uuid)
    Acta.objects.filter(numero=numero).update(
        estado=Acta.Estado.ANULADA,
        anulada_at=timezone.now(),
        anulada_por=gestor,
        motivo_anulacion="Se cargó en la escuela equivocada",
        es_prueba=True,
    )

    html = panel.get(reverse("inspecciones_acta_detalle", args=[numero])).content
    html = html.decode()

    assert "Acta anulada" in html
    assert "Se cargó en la escuela equivocada" in html
    assert "Prueba" in html
    assert 'data-bs-target="#insp-modal-anular"' not in html
    listado = panel.get(reverse("inspecciones_actas"), {"estado": "anuladas"})
    assert len(listado.context["filas"]) == 1
    validas = panel.get(reverse("inspecciones_actas"), {"estado": "validas"})
    assert validas.context["filas"] == []
    assert panel.get(reverse("inspecciones_panel")).context["resumen"]["actas_hoy"] == 0


def test_imagen_de_otra_acta_no_se_sirve(
    panel, api_a, escuela, cerrar, imagen, nuevo_uuid
):
    numero, _ = _acta_cerrada(api_a, escuela, cerrar, imagen, nuevo_uuid)

    respuesta = panel.get(
        reverse("inspecciones_acta_imagen", args=[numero, uuid.uuid4()])
    )

    assert respuesta.status_code == 404


# --- Acceso ---------------------------------------------------------------


def _rutas(escuela, asignacion, numero, imagen_uuid):
    token = "0" * 32
    return [
        ("get", reverse("inspecciones_panel")),
        ("get", reverse("inspecciones_escuela_nueva")),
        ("post", reverse("inspecciones_escuela_nueva")),
        ("get", reverse("inspecciones_escuela_editar", args=[escuela.pk])),
        ("get", reverse("inspecciones_importar_escuelas")),
        ("post", reverse("inspecciones_importar_escuelas")),
        ("get", reverse("inspecciones_importar_escuelas_revision", args=[token])),
        ("post", reverse("inspecciones_importar_escuelas_confirmar", args=[token])),
        ("post", reverse("inspecciones_importar_escuelas_cancelar", args=[token])),
        ("get", reverse("inspecciones_importar_escuelas_observaciones", args=[token])),
        ("get", reverse("inspecciones_asignaciones")),
        ("get", reverse("inspecciones_asignacion_nueva")),
        ("post", reverse("inspecciones_asignacion_quitar", args=[asignacion.pk])),
        ("get", reverse("inspecciones_importar_asignaciones")),
        ("get", reverse("inspecciones_actas")),
        ("get", reverse("inspecciones_acta_detalle", args=[numero])),
        ("get", reverse("inspecciones_acta_pdf", args=[numero])),
        ("get", reverse("inspecciones_acta_imagen", args=[numero, imagen_uuid])),
        (
            "get",
            reverse(
                "inspecciones_acta_notificacion_archivo", args=[numero, uuid.uuid4()]
            ),
        ),
        ("get", reverse("inspecciones_ajax_localidades")),
        ("get", reverse("inspecciones_ajax_inspectores")),
        ("get", reverse("inspecciones_ajax_escuelas")),
        ("get", reverse("inspecciones_ajax_verificar_asignacion")),
    ]


def test_sin_permiso_recibe_403_en_cada_vista(
    client, api_a, escuela, asignada_a, cerrar, imagen, nuevo_uuid, inspector_a
):
    numero, imagen_uuid = _acta_cerrada(api_a, escuela, cerrar, imagen, nuevo_uuid)
    sin_permiso = get_user_model().objects.create_user(username="sin_permiso")

    for usuario in (sin_permiso, inspector_a):
        client.force_login(usuario)
        for metodo, url in _rutas(escuela, asignada_a, numero, imagen_uuid):
            respuesta = getattr(client, metodo)(url)
            assert respuesta.status_code == 403, (usuario.username, metodo, url)
    assert AsignacionEscuela.objects.filter(pk=asignada_a.pk).exists()


def test_formularios_tambien_como_pagina(panel, escuela):
    for nombre in (
        "inspecciones_escuela_nueva",
        "inspecciones_asignacion_nueva",
        "inspecciones_importar_escuelas",
        "inspecciones_importar_asignaciones",
    ):
        assert panel.get(reverse(nombre)).status_code == 200, nombre
    editar = panel.get(reverse("inspecciones_escuela_editar", args=[escuela.pk]))
    assert editar.status_code == 200


def test_anonimo_va_al_login(client, escuela):
    respuesta = client.get(reverse("inspecciones_acta_pdf", args=["ACTA-2026-000001"]))

    assert respuesta.status_code == 302


# --- Compatibilidad con la PWA -------------------------------------------


def test_api_de_la_pwa_mantiene_los_campos(api_a, panel, geografia, asignada_a):
    panel.post(
        reverse("inspecciones_escuela_nueva"),
        _datos_escuela(geografia, cueanexo="060999900", nombre="Escuela nueva"),
        **XHR,
    )

    buscadas = api_a.get("/api/inspecciones/escuelas/", {"q": "Escuela nueva"}).json()
    asignadas = api_a.get("/api/inspecciones/escuelas/asignadas/").json()

    campos = {"id", "nombre", "cue", "distrito", "localidad", "domicilio", "nivel"}
    assert campos <= set(buscadas[0])
    assert buscadas[0]["id"] == buscadas[0]["cue"] == "060999900"
    assert buscadas[0]["distrito"] == "La Matanza"
    assert buscadas[0]["localidad"] == "San Justo"
    assert campos <= set(asignadas[0])
    assert asignadas[0]["id"] == "060123400"


def test_detalle_de_acta_valida_ofrece_anular_y_marcar_prueba(
    panel, api_a, escuela, cerrar, imagen, nuevo_uuid
):
    numero, _ = _acta_cerrada(api_a, escuela, cerrar, imagen, nuevo_uuid)

    html = panel.get(reverse("inspecciones_acta_detalle", args=[numero])).content
    html = html.decode()

    assert 'data-bs-target="#insp-modal-anular"' in html
    assert reverse("inspecciones_anular_acta", args=[numero]) in html
    assert reverse("inspecciones_marcar_prueba_acta", args=[numero]) in html
