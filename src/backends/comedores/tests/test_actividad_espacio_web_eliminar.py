"""Eliminación lógica en cascada de actividades de Abordaje Comunitario.

Inactivar es la baja operativa; eliminar es para cargas erróneas: la actividad
y sus inscriptos quedan con borrado lógico, dejan de verse y se pueden
restaurar tal como estaban.
"""

import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from threading import Event

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.urls import reverse

from admisiones.models.admisiones import Admision
from comedores.models import Comedor, Nomina, Programas
from core.models import Dia
from pwa.models import (
    ActividadEspacioPWA,
    AuditoriaOperacionPWA,
    CatalogoActividadPWA,
    InscriptoActividadEspacioPWA,
    NominaEspacioPWA,
)
from pwa.services.actividades_service import eliminar_actividad_espacio
from pwa.services.nomina_service import (
    soft_delete_nomina_persona,
    sync_nomina_asistencia_actividades_web,
)


@pytest.fixture
def comedor(db):
    programa = Programas.objects.create(nombre="PNUD Abordaje eliminar")
    return Comedor.objects.create(nombre="Espacio eliminar", programa=programa)


@pytest.fixture
def actividad(comedor):
    catalogo = CatalogoActividadPWA.objects.create(
        categoria="Deporte", actividad="Fútbol eliminar"
    )
    dia, _ = Dia.objects.get_or_create(nombre="Lunes")
    return ActividadEspacioPWA.objects.create(
        comedor=comedor,
        catalogo_actividad=catalogo,
        dia_actividad=dia,
        hora_inicio=datetime.time(10, 0),
        hora_fin=datetime.time(11, 0),
        horario_actividad="10:00 a 11:00",
    )


@pytest.fixture
def inscriptos(comedor, actividad):
    """Una persona con inscripción vieja inactiva y otra activa, y una segunda."""
    admision = Admision.objects.create(comedor=comedor, activa=True)
    nomina_1 = Nomina.objects.create(admision=admision, estado=Nomina.ESTADO_ACTIVO)
    nomina_2 = Nomina.objects.create(admision=admision, estado=Nomina.ESTADO_ACTIVO)
    return [
        InscriptoActividadEspacioPWA.objects.create(
            actividad_espacio=actividad, nomina=nomina_1, activo=False
        ),
        InscriptoActividadEspacioPWA.objects.create(
            actividad_espacio=actividad, nomina=nomina_1, activo=True
        ),
        InscriptoActividadEspacioPWA.objects.create(
            actividad_espacio=actividad, nomina=nomina_2, activo=True
        ),
    ]


@pytest.fixture
def admin_client(client):
    admin = get_user_model().objects.create_superuser("admin_elim", "e@e.com", "x")
    client.force_login(admin)
    return client, admin


def _url(actividad):
    return reverse(
        "actividad_espacio_pwa_eliminar",
        kwargs={"pk": actividad.comedor_id, "pk2": actividad.pk},
    )


@pytest.mark.django_db
def test_confirmacion_muestra_la_cascada(admin_client, actividad, inscriptos):
    client, _ = admin_client

    response = client.get(_url(actividad))

    assert response.status_code == 200
    preview = response.context["cascade_preview"]
    assert preview["total_afectados"] == 1 + len(inscriptos)
    assert "Eliminar actividad" in response.content.decode()


@pytest.mark.django_db
def test_eliminar_hace_borrado_logico_en_cascada(admin_client, actividad, inscriptos):
    client, admin = admin_client

    response = client.post(_url(actividad))

    assert response.status_code == 302
    assert response.url.endswith("#legajo-actividades-pnud")
    assert not ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()
    assert not InscriptoActividadEspacioPWA.objects.filter(
        actividad_espacio_id=actividad.pk
    ).exists()

    actividad_db = ActividadEspacioPWA.all_objects.get(pk=actividad.pk)
    assert actividad_db.deleted_by == admin
    inscriptos_db = InscriptoActividadEspacioPWA.all_objects.filter(
        actividad_espacio_id=actividad.pk
    )
    assert all(inscripto.is_deleted for inscripto in inscriptos_db)
    # El estado operativo no cambia: se restaura tal como estaba.
    assert actividad_db.activo is True
    assert sorted(i.activo for i in inscriptos_db) == [False, True, True]

    evento = AuditoriaOperacionPWA.objects.get(
        entidad="actividad", entidad_id=actividad.pk, accion="delete"
    )
    assert sorted(evento.metadata["inscriptos_eliminados"]) == sorted(
        i.pk for i in inscriptos
    )


@pytest.mark.django_db
def test_eliminar_no_altera_la_nomina_ni_otras_actividades(
    admin_client, comedor, actividad, inscriptos
):
    client, _ = admin_client
    nomina = inscriptos[1].nomina
    otra_actividad = ActividadEspacioPWA.objects.create(
        comedor=comedor,
        catalogo_actividad=actividad.catalogo_actividad,
        dia_actividad=actividad.dia_actividad,
        hora_inicio=datetime.time(15, 0),
        hora_fin=datetime.time(16, 0),
        horario_actividad="15:00 a 16:00",
    )
    otra_inscripcion = InscriptoActividadEspacioPWA.objects.create(
        actividad_espacio=otra_actividad, nomina=nomina, activo=True
    )
    nomina_antes = Nomina.objects.filter(pk=nomina.pk).values().get()

    client.post(_url(actividad))

    assert Nomina.objects.filter(pk=nomina.pk).values().get() == nomina_antes
    otra_inscripcion.refresh_from_db()
    assert otra_inscripcion.activo is True
    assert not otra_inscripcion.is_deleted
    assert ActividadEspacioPWA.objects.filter(pk=otra_actividad.pk).exists()
    assert list(
        nomina.inscripciones_actividad_pwa.values_list(
            "actividad_espacio_id", flat=True
        )
    ) == [otra_actividad.pk]


@pytest.mark.django_db
def test_pestania_actividades_de_nomina_ignora_inscripciones_eliminadas(
    admin_client, actividad, inscriptos
):
    # pylint: disable=import-outside-toplevel,protected-access
    from comedores.services.comedor_service import impl

    client, _ = admin_client
    nominas = Nomina.objects.filter(pk__in={i.nomina_id for i in inscriptos})
    assert impl._apply_nomina_tab_filter(nominas, "actividades").count() == 2

    client.post(_url(actividad))

    assert impl._apply_nomina_tab_filter(nominas, "actividades").count() == 0
    assert nominas.count() == 2


@pytest.mark.django_db
def test_se_puede_recargar_la_actividad_correcta_tras_eliminar(admin_client, actividad):
    """El horario de la eliminada no bloquea cargar la actividad bien."""
    client, _ = admin_client
    client.post(_url(actividad))
    url = reverse("actividad_espacio_pwa_crear", kwargs={"pk": actividad.comedor_id})

    response = client.post(
        url,
        {
            "categoria": actividad.catalogo_actividad.categoria,
            "catalogo_actividad": actividad.catalogo_actividad_id,
            "schedule_grupo": ["0"],
            "schedule_dias_0": [actividad.dia_actividad_id],
            "schedule_hora_inicio": ["10:00"],
            "schedule_hora_fin": ["11:00"],
        },
    )

    assert response.status_code == 302
    assert ActividadEspacioPWA.objects.filter(comedor=actividad.comedor).count() == 1


@pytest.mark.django_db
def test_actividad_eliminada_no_aparece_en_el_legajo(admin_client, actividad):
    client, _ = admin_client
    detalle = reverse("comedor_detalle", kwargs={"pk": actividad.comedor_id})
    assert "Fútbol eliminar" in client.get(detalle).content.decode()

    client.post(_url(actividad))

    assert "Fútbol eliminar" not in client.get(detalle).content.decode()


@pytest.mark.django_db
def test_restaurar_devuelve_actividad_e_inscriptos(admin_client, actividad, inscriptos):
    client, admin = admin_client
    client.post(_url(actividad))

    ActividadEspacioPWA.all_objects.get(pk=actividad.pk).restore(user=admin)

    assert ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()
    assert InscriptoActividadEspacioPWA.objects.filter(
        actividad_espacio=actividad
    ).count() == len(inscriptos)


@pytest.mark.django_db
def test_eliminar_requiere_permiso(client, actividad):
    usuario = get_user_model().objects.create_user("sin_permiso", password="x")
    client.force_login(usuario)

    assert client.post(_url(actividad)).status_code == 403
    assert ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()


@pytest.mark.django_db
def test_no_elimina_actividades_de_otro_comedor(admin_client, actividad):
    client, _ = admin_client
    otro = Comedor.objects.create(
        nombre="Otro espacio", programa=actividad.comedor.programa
    )
    url = reverse(
        "actividad_espacio_pwa_eliminar", kwargs={"pk": otro.pk, "pk2": actividad.pk}
    )

    assert client.post(url).status_code == 404
    assert ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql_compat
@pytest.mark.parametrize("primera", ["inscribir", "eliminar"])
@pytest.mark.parametrize("reactivar", [False, True], ids=["alta", "reactivacion"])
@pytest.mark.parametrize("borrado_directo", [False, True], ids=["servicio", "directo"])
def test_eliminar_serializa_cambios_en_inscripciones(
    actividad, primera, reactivar, borrado_directo
):
    if connection.vendor != "mysql":
        pytest.skip("Requiere bloqueos de fila de MySQL.")

    actor = get_user_model().objects.create_superuser(
        "admin_concurrencia", "admin@example.invalid", "clave-sintetica"
    )
    admision = Admision.objects.create(comedor=actividad.comedor, activa=True)
    nomina = Nomina.objects.create(admision=admision, estado=Nomina.ESTADO_ACTIVO)
    if reactivar:
        InscriptoActividadEspacioPWA.objects.create(
            actividad_espacio=actividad, nomina=nomina, activo=False
        )

    escritura_lista, liberar, segunda_iniciada = Event(), Event(), Event()
    tabla = (
        InscriptoActividadEspacioPWA._meta.db_table
        if primera == "inscribir"
        else ActividadEspacioPWA._meta.db_table
    )
    operacion = "UPDATE" if primera == "eliminar" or reactivar else "INSERT"

    def pausar_escritura(execute, sql, params, many, context):
        if sql.lstrip().upper().startswith(operacion) and f"`{tabla}`" in sql:
            escritura_lista.set()
            assert liberar.wait(15), "La prueba no liberó la escritura."
        return execute(sql, params, many, context)

    def inscribir():
        return sync_nomina_asistencia_actividades_web(
            nomina=nomina,
            comedor_id=actividad.comedor_id,
            actor=actor,
            asistencia_alimentaria=False,
            asistencia_actividades=True,
            activity_ids=[actividad.pk],
        )

    def eliminar():
        fresca = ActividadEspacioPWA.objects.get(pk=actividad.pk)
        if borrado_directo:
            eliminados, _ = fresca.delete(user=actor, cascade=True)
            return eliminados
        return eliminar_actividad_espacio(actividad=fresca, actor=actor)

    def ejecutar(tarea, *, pausar):
        try:
            if pausar:
                with connection.execute_wrapper(pausar_escritura):
                    return tarea()
            segunda_iniciada.set()
            return tarea()
        finally:
            connection.close()

    tareas = {"inscribir": inscribir, "eliminar": eliminar}
    segunda = "eliminar" if primera == "inscribir" else "inscribir"
    with ThreadPoolExecutor(max_workers=2) as executor:
        uno = executor.submit(ejecutar, tareas[primera], pausar=True)
        try:
            assert escritura_lista.wait(10), "La primera operación no llegó a escribir."
            dos = executor.submit(ejecutar, tareas[segunda], pausar=False)
            assert segunda_iniciada.wait(10), "La segunda operación no se inició."
            with pytest.raises(FutureTimeout):
                dos.result(timeout=2)
        finally:
            liberar.set()
        uno.result(timeout=10)
        if primera == "eliminar":
            with pytest.raises(ValidationError, match="Actividades inválidas"):
                dos.result(timeout=10)
            assert not NominaEspacioPWA.objects.filter(nomina=nomina).exists()
        else:
            assert dos.result(timeout=10) == 2

    assert not ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()
    assert not InscriptoActividadEspacioPWA.objects.filter(
        actividad_espacio=actividad, nomina=nomina
    ).exists()
    eliminadas = InscriptoActividadEspacioPWA.all_objects.filter(
        actividad_espacio=actividad, nomina=nomina, deleted_at__isnull=False
    )
    assert eliminadas.count() == int(reactivar or primera == "inscribir")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "eliminar_actividad", [False, True], ids=["vigente", "eliminada"]
)
def test_papelera_restaurar_inscripcion_respeta_su_actividad(
    admin_client, actividad, inscriptos, eliminar_actividad
):
    client, admin = admin_client
    inscripto = inscriptos[1]
    if eliminar_actividad:
        client.post(_url(actividad))
    else:
        inscripto.delete(user=admin)
    datos = InscriptoActividadEspacioPWA.all_objects.filter(pk=inscripto.pk)
    antes = datos.values().get()
    assert antes["deleted_at"] is not None
    kwargs = {
        "app_label": "pwa",
        "model_name": "inscriptoactividadespaciopwa",
        "pk": inscripto.pk,
    }

    response = client.post(
        reverse("papelera_restore", kwargs=kwargs), {"confirmed": "1"}
    )

    assert response.status_code == 302
    if eliminar_actividad:
        assert response.url == reverse("papelera_preview_restore", kwargs=kwargs)
        assert datos.values().get() == antes
        assert not ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()
    else:
        assert datos.values().get()["deleted_at"] is None
        assert datos.values().get()["activo"] == antes["activo"]
        assert ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql_compat
def test_borrado_espera_restauracion_individual(actividad):
    if connection.vendor != "mysql":
        pytest.skip("Requiere bloqueos de fila de MySQL.")

    actor = get_user_model().objects.create_superuser(
        "admin_restaura", "restaura@example.invalid", "clave-sintetica"
    )
    admision = Admision.objects.create(comedor=actividad.comedor, activa=True)
    nomina = Nomina.objects.create(admision=admision, estado=Nomina.ESTADO_ACTIVO)
    inscripto = InscriptoActividadEspacioPWA.objects.create(
        actividad_espacio=actividad, nomina=nomina, activo=True
    )
    inscripto.delete(user=actor)
    restaurando, continuar, borrando = Event(), Event(), Event()
    tabla = InscriptoActividadEspacioPWA._meta.db_table

    def pausar_escritura(execute, sql, params, many, context):
        if sql.lstrip().upper().startswith("UPDATE") and f"`{tabla}`" in sql:
            restaurando.set()
            assert continuar.wait(15), "La prueba no liberó la restauración."
        return execute(sql, params, many, context)

    def restaurar():
        try:
            with connection.execute_wrapper(pausar_escritura):
                return inscripto.restore(user=actor)
        finally:
            connection.close()

    def eliminar():
        try:
            borrando.set()
            return eliminar_actividad_espacio(actividad=actividad, actor=actor)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        restauracion = executor.submit(restaurar)
        try:
            assert restaurando.wait(10), "La restauración no llegó a escribir."
            borrado = executor.submit(eliminar)
            assert borrando.wait(10), "El borrado no se inició."
            with pytest.raises(FutureTimeout):
                borrado.result(timeout=2)
        finally:
            continuar.set()
        assert restauracion.result(timeout=10)[0] == 1
        assert borrado.result(timeout=10) == 2

    assert not ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()
    assert not InscriptoActividadEspacioPWA.objects.filter(pk=inscripto.pk).exists()
    assert InscriptoActividadEspacioPWA.all_objects.get(pk=inscripto.pk).activo


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql_compat
def test_borrado_espera_alta_desde_admin(actividad, admin_client):
    if connection.vendor != "mysql":
        pytest.skip("Requiere bloqueos de fila de MySQL.")

    client, actor = admin_client
    admision = Admision.objects.create(comedor=actividad.comedor, activa=True)
    nomina = Nomina.objects.create(admision=admision, estado=Nomina.ESTADO_ACTIVO)
    url = reverse("admin:pwa_inscriptoactividadespaciopwa_add")
    alta_lista, continuar, borrando = Event(), Event(), Event()
    tabla = InscriptoActividadEspacioPWA._meta.db_table

    def pausar_alta(execute, sql, params, many, context):
        if sql.lstrip().upper().startswith("INSERT") and f"`{tabla}`" in sql:
            alta_lista.set()
            assert continuar.wait(15), "La prueba no liberó el alta."
        return execute(sql, params, many, context)

    def inscribir():
        try:
            with connection.execute_wrapper(pausar_alta):
                return client.post(
                    url,
                    {
                        "actividad_espacio": actividad.pk,
                        "nomina": nomina.pk,
                        "activo": "on",
                    },
                )
        finally:
            connection.close()

    def borrar():
        try:
            borrando.set()
            return eliminar_actividad_espacio(actividad=actividad, actor=actor)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        alta = executor.submit(inscribir)
        try:
            assert alta_lista.wait(10), "El formulario de Admin no llegó a guardar."
            borrado = executor.submit(borrar)
            assert borrando.wait(10), "El borrado no se inició."
            with pytest.raises(FutureTimeout):
                borrado.result(timeout=2)
        finally:
            continuar.set()
        assert alta.result(timeout=10).status_code == 302
        assert borrado.result(timeout=10) == 2

    assert not ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()
    assert not InscriptoActividadEspacioPWA.objects.filter(
        actividad_espacio=actividad, nomina=nomina
    ).exists()
    assert InscriptoActividadEspacioPWA.all_objects.get(
        actividad_espacio=actividad, nomina=nomina
    ).is_deleted


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql_compat
def test_borrado_de_comedor_incluye_alta_simultanea(actividad):
    if connection.vendor != "mysql":
        pytest.skip("Requiere bloqueos de fila de MySQL.")

    actor = get_user_model().objects.create_superuser(
        "admin_raiz", "raiz@example.invalid", "clave-sintetica"
    )
    comedor = actividad.comedor
    nomina = Nomina.objects.create(comedor=comedor, estado=Nomina.ESTADO_ACTIVO)
    alta_lista, continuar, borrando = Event(), Event(), Event()
    tabla = InscriptoActividadEspacioPWA._meta.db_table

    def pausar_alta(execute, sql, params, many, context):
        if sql.lstrip().upper().startswith("INSERT") and f"`{tabla}`" in sql:
            alta_lista.set()
            assert continuar.wait(15), "La prueba no liberó el alta."
        return execute(sql, params, many, context)

    def inscribir():
        try:
            with connection.execute_wrapper(pausar_alta):
                sync_nomina_asistencia_actividades_web(
                    nomina=nomina,
                    comedor_id=comedor.pk,
                    actor=actor,
                    asistencia_alimentaria=False,
                    asistencia_actividades=True,
                    activity_ids=[actividad.pk],
                )
        finally:
            connection.close()

    def borrar_comedor():
        try:
            borrando.set()
            return comedor.delete(user=actor, cascade=True)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        alta = executor.submit(inscribir)
        try:
            assert alta_lista.wait(10), "La inscripción no llegó a guardar."
            borrado = executor.submit(borrar_comedor)
            assert borrando.wait(10), "El borrado del comedor no se inició."
            with pytest.raises(FutureTimeout):
                borrado.result(timeout=2)
        finally:
            continuar.set()
        alta.result(timeout=10)
        borrado.result(timeout=10)

    assert not Comedor.objects.filter(pk=comedor.pk).exists()
    assert not ActividadEspacioPWA.objects.filter(pk=actividad.pk).exists()
    assert not InscriptoActividadEspacioPWA.objects.filter(
        actividad_espacio=actividad, nomina=nomina
    ).exists()
    assert InscriptoActividadEspacioPWA.all_objects.get(
        actividad_espacio=actividad, nomina=nomina
    ).is_deleted


@pytest.mark.django_db(transaction=True)
@pytest.mark.mysql_compat
def test_borrado_de_comedor_y_baja_de_nomina_simultaneos(actividad):
    if connection.vendor != "mysql":
        pytest.skip("Requiere bloqueos de fila de MySQL.")

    actor = get_user_model().objects.create_superuser(
        "admin_baja", "baja@example.invalid", "clave-sintetica"
    )
    comedor = actividad.comedor
    nomina = Nomina.objects.create(comedor=comedor, estado=Nomina.ESTADO_ACTIVO)
    inscripcion = InscriptoActividadEspacioPWA.objects.create(
        actividad_espacio=actividad, nomina=nomina, activo=True
    )
    auditoria_lista, continuar, borrando = Event(), Event(), Event()
    tabla = AuditoriaOperacionPWA._meta.db_table

    def pausar_auditoria(execute, sql, params, many, context):
        if sql.lstrip().upper().startswith("INSERT") and f"`{tabla}`" in sql:
            auditoria_lista.set()
            assert continuar.wait(15), "La prueba no liberó la baja."
        return execute(sql, params, many, context)

    def dar_baja():
        try:
            with connection.execute_wrapper(pausar_auditoria):
                soft_delete_nomina_persona(nomina=nomina, actor=actor)
        finally:
            connection.close()

    def borrar_comedor():
        try:
            borrando.set()
            comedor.delete(user=actor, cascade=True)
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        baja = executor.submit(dar_baja)
        try:
            assert auditoria_lista.wait(10), "La baja no llegó a la auditoría."
            borrado = executor.submit(borrar_comedor)
            assert borrando.wait(10), "El borrado del comedor no se inició."
            with pytest.raises(FutureTimeout):
                borrado.result(timeout=2)
        finally:
            continuar.set()
        baja.result(timeout=10)
        borrado.result(timeout=10)

    nomina.refresh_from_db()
    assert nomina.estado == Nomina.ESTADO_BAJA
    assert not Comedor.objects.filter(pk=comedor.pk).exists()
    inscripcion = InscriptoActividadEspacioPWA.all_objects.get(pk=inscripcion.pk)
    assert inscripcion.is_deleted and not inscripcion.activo
