"""Seleccion personalizada de destinatarios de comunicados (issue #2505)."""

import json

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from comedores.models import Comedor
from comunicados import services_destinatarios
from comunicados.models import Comunicado, SubtipoComunicado, TipoComunicado
from core.models import Provincia
from duplas.models import Dupla
from organizaciones.models import Organizacion, TipoEntidad

pytestmark = pytest.mark.django_db


def _dar_permiso(usuario, codename, modelo=User, nombre=None):
    content_type = ContentType.objects.get_for_model(modelo)
    permiso, _ = Permission.objects.get_or_create(
        codename=codename,
        content_type=content_type,
        defaults={"name": nombre or codename},
    )
    usuario.user_permissions.add(permiso)
    return usuario


def _usuario_editor(username="editor_dest"):
    """Usuario del grupo "Comunicado Editar": edita, pero no crea.

    Es el caso que regresionaba: abria un borrador y el panel le devolvia 403.
    """

    usuario = User.objects.create_user(username, password="test")
    return _dar_permiso(usuario, "change_comunicado", Comunicado)


def _usuario_tecnico_editor(username="tecnico_editor_dest"):
    """Tecnico con permiso de edicion: alcance acotado a su dupla."""

    usuario = _usuario_editor(username)
    return _dar_permiso(usuario, "role_tecnico_comedor", User, nombre="Tecnico Comedor")


def _comedor_de_la_dupla(tecnico, comedor, nombre="Dupla destinatarios"):
    abogado = User.objects.create_user(f"abogado_{tecnico.username}", password="test")
    dupla = Dupla.objects.create(nombre=nombre, estado="Activo", abogado=abogado)
    dupla.tecnico.add(tecnico)
    comedor.dupla = dupla
    comedor.save(update_fields=["dupla"])
    return dupla


def _borrador(usuario, titulo="Borrador editable"):
    return Comunicado.objects.create(
        titulo=titulo,
        cuerpo="Contenido",
        tipo=TipoComunicado.EXTERNO,
        subtipo=SubtipoComunicado.COMEDORES,
        estado="borrador",
        usuario_creador=usuario,
    )


def _filtros(items):
    return json.dumps({"logic": "AND", "items": items})


def _form_data(**overrides):
    data = {
        "titulo": "Comunicado con destinatarios",
        "cuerpo": "Contenido",
        "tipo": TipoComunicado.EXTERNO,
        "subtipo": SubtipoComunicado.COMEDORES,
        "fecha_vencimiento": "",
        "adjuntos-TOTAL_FORMS": "0",
        "adjuntos-INITIAL_FORMS": "0",
        "adjuntos-MIN_NUM_FORMS": "0",
        "adjuntos-MAX_NUM_FORMS": "1000",
    }
    data.update(overrides)
    return data


@pytest.fixture
def admin(client):
    usuario = User.objects.create_superuser("admin_dest", "dest@test.com", "test")
    client.force_login(usuario)
    return usuario


def test_buscar_comedores_aplica_filtros_combinables(client, admin):
    buenos_aires = Provincia.objects.create(nombre="Buenos Aires")
    cordoba = Provincia.objects.create(nombre="Cordoba")
    objetivo = Comedor.objects.create(nombre="Comedor Sur", provincia=buenos_aires)
    Comedor.objects.create(nombre="Comedor Sur", provincia=cordoba)
    Comedor.objects.create(nombre="Otro espacio", provincia=buenos_aires)

    response = client.get(
        reverse("comunicados_destinatarios_buscar", args=["comedores"]),
        {
            "filters": _filtros(
                [
                    {"field": "nombre", "op": "contains", "value": "Comedor Sur"},
                    {"field": "provincia", "op": "contains", "value": "Buenos"},
                ]
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["id"] for item in payload["results"]] == [objetivo.pk]
    assert payload["results"][0]["detalle"] == "Buenos Aires"


def test_buscar_organizaciones_usa_los_filtros_del_listado(client, admin):
    tipo = TipoEntidad.objects.create(nombre="Asociacion civil")
    objetivo = Organizacion.objects.create(nombre="Manos Unidas", tipo_entidad=tipo)
    Organizacion.objects.create(nombre="Manos Libres")

    response = client.get(
        reverse("comunicados_destinatarios_buscar", args=["organizaciones"]),
        {
            "filters": _filtros(
                [{"field": "tipo_entidad", "op": "eq", "value": "Asociacion civil"}]
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["results"]] == [objetivo.pk]


def test_buscar_pagina_los_resultados(client, admin, monkeypatch):
    monkeypatch.setattr(services_destinatarios, "PAGE_SIZE", 2)
    for indice in range(5):
        Comedor.objects.create(nombre=f"Comedor {indice:02d}")

    primera = client.get(
        reverse("comunicados_destinatarios_buscar", args=["comedores"]),
        {"filters": _filtros([])},
    ).json()
    segunda = client.get(
        reverse("comunicados_destinatarios_buscar", args=["comedores"]),
        {"filters": _filtros([]), "page": "2"},
    ).json()

    assert primera["total"] == 5
    assert len(primera["results"]) == 2
    assert primera["has_more"] is True
    assert segunda["page"] == 2
    assert [item["nombre"] for item in segunda["results"]] == [
        "Comedor 02",
        "Comedor 03",
    ]


def test_seleccionar_todos_devuelve_los_ids_que_matchean(client, admin):
    incluido = Comedor.objects.create(nombre="Comedor incluido")
    Comedor.objects.create(nombre="Excluido")

    response = client.get(
        reverse("comunicados_destinatarios_todos", args=["comedores"]),
        {"filters": _filtros([{"field": "nombre", "op": "contains", "value": "incl"}])},
    )

    payload = response.json()
    assert payload["truncado"] is False
    assert [item["id"] for item in payload["results"]] == [incluido.pk]


def test_seleccionar_todos_corta_cuando_supera_el_tope(client, admin, monkeypatch):
    monkeypatch.setattr(services_destinatarios, "MAX_SELECCION_MASIVA", 1)
    Comedor.objects.create(nombre="Comedor uno")
    Comedor.objects.create(nombre="Comedor dos")

    payload = client.get(
        reverse("comunicados_destinatarios_todos", args=["comedores"]),
        {"filters": _filtros([])},
    ).json()

    assert payload["truncado"] is True
    assert payload["results"] == []
    assert payload["total"] == 2


def test_buscar_respeta_el_alcance_del_usuario(client):
    """Un tecnico solo ve los comedores de su dupla.

    Con usuarios reales, y no forzando el alcance: tener permiso de crear ya
    implica alcance total, asi que la rama acotada solo se alcanza con alguien
    que entra por el permiso de edicion.
    """

    visible = Comedor.objects.create(nombre="Comedor visible")
    Comedor.objects.create(nombre="Comedor ajeno")
    tecnico = _usuario_tecnico_editor()
    _comedor_de_la_dupla(tecnico, visible)
    client.force_login(tecnico)

    payload = client.get(
        reverse("comunicados_destinatarios_buscar", args=["comedores"]),
        {"filters": _filtros([])},
    ).json()

    assert [item["id"] for item in payload["results"]] == [visible.pk]


def test_el_editor_puede_abrir_el_borrador_y_usar_el_panel(client):
    """La regresion del PR: editar exigia un permiso y el panel, otro."""

    Comedor.objects.create(nombre="Comedor cualquiera")
    editor = _usuario_editor()
    comunicado = _borrador(editor)
    client.force_login(editor)

    edicion = client.get(reverse("comunicados_editar", kwargs={"pk": comunicado.pk}))
    buscar = client.get(
        reverse("comunicados_destinatarios_buscar", args=["comedores"]),
        {"filters": _filtros([])},
    )
    todos = client.get(
        reverse("comunicados_destinatarios_todos", args=["comedores"]),
        {"filters": _filtros([])},
    )

    assert edicion.status_code == 200
    assert buscar.status_code == 200
    assert todos.status_code == 200


def test_el_editor_sin_alcance_no_recibe_destinatarios(client):
    """Puede abrir el panel, pero sin alcance no ve a nadie."""

    Comedor.objects.create(nombre="Comedor fuera de alcance")
    client.force_login(_usuario_editor("editor_sin_alcance"))

    payload = client.get(
        reverse("comunicados_destinatarios_buscar", args=["comedores"]),
        {"filters": _filtros([])},
    ).json()

    assert payload["results"] == []
    assert payload["total"] == 0


def test_seleccionar_todos_respeta_el_alcance_del_tecnico(client):
    suyo = Comedor.objects.create(nombre="Comedor propio")
    Comedor.objects.create(nombre="Comedor de otro")
    tecnico = _usuario_tecnico_editor("tecnico_todos_dest")
    _comedor_de_la_dupla(tecnico, suyo, nombre="Dupla seleccion masiva")
    client.force_login(tecnico)

    payload = client.get(
        reverse("comunicados_destinatarios_todos", args=["comedores"]),
        {"filters": _filtros([])},
    ).json()

    assert [item["id"] for item in payload["results"]] == [suyo.pk]
    assert payload["total"] == 1


def test_universo_desconocido_devuelve_404(client, admin):
    response = client.get(
        reverse("comunicados_destinatarios_buscar", args=["ciudadanos"])
    )

    assert response.status_code == 404


def test_buscar_exige_permiso_sobre_comunicados(client):
    """Sin permiso de crear ni de editar, el panel sigue cerrado."""

    sin_permisos = User.objects.create_user("sin_permisos_dest", password="test")
    client.force_login(sin_permisos)

    response = client.get(
        reverse("comunicados_destinatarios_buscar", args=["comedores"])
    )

    assert response.status_code == 403


def test_formulario_guarda_los_destinatarios_elegidos(client, admin):
    uno = Comedor.objects.create(nombre="Comedor uno")
    dos = Comedor.objects.create(nombre="Comedor dos")

    response = client.post(
        reverse("comunicados_crear"),
        _form_data(comedores=[str(uno.pk), str(dos.pk)]),
    )

    assert response.status_code == 302
    comunicado = Comunicado.objects.get(titulo="Comunicado con destinatarios")
    assert set(comunicado.comedores.values_list("pk", flat=True)) == {uno.pk, dos.pk}


def test_el_formulario_no_renderiza_todo_el_universo_en_un_select(client, admin):
    Comedor.objects.create(nombre="Comedor listado")

    response = client.get(reverse("comunicados_crear"))
    contenido = response.content.decode()

    assert response.status_code == 200
    # El universo ya no se serializa en el HTML: el panel lo consulta por AJAX.
    assert "Comedor listado" not in contenido
    assert 'data-universo="comedores"' in contenido
    assert 'data-universo="organizaciones"' in contenido
    assert "destinatarios-filters-config" in contenido


def test_contexto_trae_config_urls_y_seleccion_previa(client, admin):
    comedor = Comedor.objects.create(nombre="Comedor elegido")
    comunicado = Comunicado.objects.create(
        titulo="Editable",
        cuerpo="Contenido",
        tipo=TipoComunicado.EXTERNO,
        subtipo=SubtipoComunicado.COMEDORES,
        usuario_creador=admin,
    )
    comunicado.comedores.add(comedor)

    response = client.get(reverse("comunicados_editar", kwargs={"pk": comunicado.pk}))
    ctx = response.context

    assert ctx["destinatarios_filters_config"]["comedores"]["fields"]
    assert ctx["destinatarios_filters_config"]["organizaciones"]["fields"]
    assert ctx["destinatarios_seleccionados"]["comedores"] == [
        {"id": comedor.pk, "nombre": "Comedor elegido"}
    ]
    assert ctx["destinatarios_urls"]["comedores"]["buscar"].endswith(
        "/comedores/buscar/"
    )


def test_las_secciones_se_muestran_en_el_orden_pedido(client, admin):
    contenido = client.get(reverse("comunicados_crear")).content.decode()

    orden = [
        contenido.index("Configuración"),
        contenido.index("Destinatarios"),
        contenido.index("Redacción"),
        contenido.index("Archivos Adjuntos"),
    ]

    assert orden == sorted(orden)


def test_alcance_total_no_materializa_los_ids(client, admin, monkeypatch):
    Comedor.objects.create(nombre="Comedor cualquiera")

    def _no_deberia_llamarse(user):
        raise AssertionError("con alcance total no se arma el IN de ids")

    monkeypatch.setattr(
        services_destinatarios, "get_ids_comedores_del_usuario", _no_deberia_llamarse
    )

    payload = client.get(
        reverse("comunicados_destinatarios_buscar", args=["comedores"]),
        {"filters": _filtros([])},
    ).json()

    assert payload["total"] == 1


def test_formulario_guarda_seleccion_masiva_en_un_solo_campo(client, admin):
    # Mas ids que DATA_UPLOAD_MAX_NUMBER_FIELDS (1000): con un input por id el
    # POST respondia 400.
    Comedor.objects.bulk_create(
        [Comedor(nombre=f"Comedor masivo {indice}") for indice in range(1100)]
    )
    ids = list(Comedor.objects.values_list("pk", flat=True))

    response = client.post(
        reverse("comunicados_crear"),
        _form_data(comedores=",".join(str(pk) for pk in ids)),
    )

    assert response.status_code == 302
    comunicado = Comunicado.objects.get(titulo="Comunicado con destinatarios")
    assert comunicado.comedores.count() == 1100


def test_edicion_renderiza_la_seleccion_en_un_solo_input(client, admin):
    uno = Comedor.objects.create(nombre="Comedor uno")
    dos = Comedor.objects.create(nombre="Comedor dos")
    comunicado = Comunicado.objects.create(
        titulo="Editable",
        cuerpo="Contenido",
        tipo=TipoComunicado.EXTERNO,
        subtipo=SubtipoComunicado.COMEDORES,
        usuario_creador=admin,
    )
    comunicado.comedores.add(uno, dos)

    response = client.get(reverse("comunicados_editar", kwargs={"pk": comunicado.pk}))
    contenido = response.content.decode()

    assert contenido.count('name="comedores"') == 1
    assert (
        f'value="{uno.pk},{dos.pk}"' in contenido
        or f'value="{dos.pk},{uno.pk}"' in contenido
    )


def test_post_con_ids_invalidos_no_rompe_el_render(client, admin):
    comedor = Comedor.objects.create(nombre="Comedor valido")

    response = client.post(
        reverse("comunicados_crear"),
        _form_data(comedores=f"{comedor.pk},abc"),
    )

    assert response.status_code == 200
    assert "comedores" in response.context["form"].errors
    assert response.context["destinatarios_seleccionados"]["comedores"] == [
        {"id": comedor.pk, "nombre": "Comedor valido"}
    ]
