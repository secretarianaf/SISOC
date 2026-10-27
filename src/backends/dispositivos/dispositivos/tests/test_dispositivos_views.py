import pytest
from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from core.models import Localidad, Municipio, Provincia
from dispositivos.forms import DispositivoForm
from dispositivos.models import Dispositivo
from users.models import Profile, ProfileTerritorialScope


@pytest.fixture
def provincia_municipio(db):
    provincia = Provincia.objects.create(nombre="Buenos Aires")
    municipio = Municipio.objects.create(nombre="La Plata", provincia=provincia)
    return provincia, municipio


@pytest.fixture
def user_con_permisos(db):
    user = User.objects.create_user(username="disp-admin", password="test1234")
    perms = Permission.objects.filter(
        content_type__app_label="dispositivos",
        codename__in=[
            "add_dispositivo",
            "change_dispositivo",
            "delete_dispositivo",
            "view_dispositivo",
            "ver_mapa_dispositivo",
        ],
    )
    user.user_permissions.add(*perms)
    return user


def _crear_dispositivo(provincia, municipio, indice=0, **overrides):
    data = {
        "nombre_institucion": f"Dispositivo {indice}",
        "tipo_gestion": "estatal",
        "cuit_institucion": f"20{indice:09d}",
        "provincia": provincia,
        "municipio": municipio,
        "calle": f"Calle {indice}",
        "altura": "100",
        "telefono_prefijo": "221",
        "telefono_numero": "9876543",
        "responsable_nombre_completo": "Ana Lopez",
        "responsable_dni": f"{indice:08d}",
        "tipo_dispositivo": "refugio",
        "modalidad_funcionamiento": "permanente",
        "capacidad_total_plazas": "0_15",
    }
    data.update(overrides)
    return Dispositivo.objects.create(**data)


@pytest.mark.django_db
def test_listado_requiere_login(client):
    response = client.get(reverse("dispositivos_listar"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_crud_dispositivo_con_permisos(client, user_con_permisos, provincia_municipio):
    provincia, municipio = provincia_municipio
    client.force_login(user_con_permisos)

    documento_principal = SimpleUploadedFile(
        "documento-principal.pdf", b"contenido 1", content_type="application/pdf"
    )
    documento_adicional_1 = SimpleUploadedFile(
        "documento-adicional-1.pdf", b"contenido 2", content_type="application/pdf"
    )
    documento_adicional_2 = SimpleUploadedFile(
        "documento-adicional-2.pdf", b"contenido 3", content_type="application/pdf"
    )
    documento_adicional_3 = SimpleUploadedFile(
        "documento-adicional-3.pdf", b"contenido 4", content_type="application/pdf"
    )
    documento_adicional_4 = SimpleUploadedFile(
        "documento-adicional-4.pdf", b"contenido 5", content_type="application/pdf"
    )

    create_url = reverse("dispositivos_crear")
    response_create = client.post(
        create_url,
        data={
            "nombre_institucion": "Dispositivo Test",
            "tipo_gestion": "estatal",
            "cuit_institucion": "20123456789",
            "provincia": provincia.id,
            "municipio": municipio.id,
            "calle": "Calle 1",
            "altura": "123",
            "telefono_prefijo": "221",
            "telefono_numero": "1234567",
            "correo_electronico": "test@example.com",
            "responsable_nombre_completo": "Juan Perez",
            "responsable_dni": "12345678",
            "tipo_dispositivo": "refugio",
            "modalidad_funcionamiento": "permanente",
            "capacidad_total_plazas": "16_30",
            "dias_atencion": ["lunes", "martes"],
            "horarios_funcionamiento": ["manana"],
            "observaciones_adicionales": "Observación de prueba",
            "documentacion_dispositivo": documento_principal,
            "documentacion_dispositivo_adicional_1": documento_adicional_1,
            "documentacion_dispositivo_adicional_2": documento_adicional_2,
            "documentacion_dispositivo_adicional_3": documento_adicional_3,
            "documentacion_dispositivo_adicional_4": documento_adicional_4,
        },
    )
    assert response_create.status_code == 302

    dispositivo = Dispositivo.objects.get(nombre_institucion="Dispositivo Test")

    detail_url = reverse("dispositivos_detalle", kwargs={"pk": dispositivo.pk})
    response_detail = client.get(detail_url)
    assert response_detail.status_code == 200
    contenido_detalle = response_detail.content.decode("utf-8")
    assert "Observación de prueba" in contenido_detalle
    assert "documento-principal.pdf" in contenido_detalle
    assert "documento-adicional-4.pdf" in contenido_detalle

    edit_url = reverse("dispositivos_editar", kwargs={"pk": dispositivo.pk})
    response_edit = client.post(
        edit_url,
        data={
            "nombre_institucion": "Dispositivo Editado",
            "tipo_gestion": "estatal",
            "cuit_institucion": "20123456789",
            "provincia": provincia.id,
            "municipio": municipio.id,
            "calle": "Calle 1",
            "altura": "123",
            "telefono_prefijo": "221",
            "telefono_numero": "1234567",
            "correo_electronico": "test@example.com",
            "responsable_nombre_completo": "Juan Perez",
            "responsable_dni": "12345678",
            "tipo_dispositivo": "refugio",
            "modalidad_funcionamiento": "permanente",
            "capacidad_total_plazas": "16_30",
            "dias_atencion": ["lunes"],
            "horarios_funcionamiento": ["manana"],
        },
    )
    assert response_edit.status_code == 302

    dispositivo.refresh_from_db()
    assert dispositivo.nombre_institucion == "Dispositivo Editado"

    delete_url = reverse("dispositivos_eliminar", kwargs={"pk": dispositivo.pk})
    response_delete = client.post(delete_url)
    assert response_delete.status_code == 302
    assert not Dispositivo.objects.filter(pk=dispositivo.pk).exists()


@pytest.mark.django_db
def test_eliminar_dispositivo_con_relevamientos_avisa_en_vez_de_500(
    client, user_con_permisos, provincia_municipio
):
    # Issue #2750: el FK PROTECT de datacalle.Relevamiento daba ProtectedError (500).
    import datetime  # pylint: disable=import-outside-toplevel

    from datacalle.models import Relevamiento  # pylint: disable=import-outside-toplevel

    provincia, municipio = provincia_municipio
    dispositivo = _crear_dispositivo(provincia, municipio)
    Relevamiento.objects.create(
        denominacion="Operativo con dispositivo",
        provincia=provincia,
        fase=Relevamiento.Fase.ESPACIO_PUBLICO,
        area_operativa="Plaza",
        fecha_inicio=datetime.date(2026, 10, 13),
        fecha_fin=datetime.date(2026, 10, 17),
        dispositivo=dispositivo,
    )
    client.force_login(user_con_permisos)

    response = client.post(
        reverse("dispositivos_eliminar", kwargs={"pk": dispositivo.pk}), follow=True
    )

    assert response.redirect_chain[0] == (
        reverse("dispositivos_detalle", kwargs={"pk": dispositivo.pk}),
        302,
    )
    assert Dispositivo.objects.filter(pk=dispositivo.pk).exists()
    mensajes = [str(m) for m in response.context["messages"]]
    assert any(
        "No se puede eliminar el dispositivo" in m
        and str(Relevamiento._meta.verbose_name_plural) in m
        for m in mensajes
    )


@pytest.mark.django_db
def test_sin_permiso_view_dispositivo_devuelve_403(client, provincia_municipio):
    provincia, municipio = provincia_municipio
    user = User.objects.create_user(username="sin-permiso", password="test1234")
    dispositivo = _crear_dispositivo(
        provincia,
        municipio,
        indice=11222333,
        nombre_institucion="Dispositivo Permisos",
        cuit_institucion="20111222333",
        responsable_dni="33444555",
    )

    client.force_login(user)
    response = client.get(
        reverse("dispositivos_detalle", kwargs={"pk": dispositivo.pk})
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_listado_oculta_acciones_sin_permisos_de_mutacion(client, provincia_municipio):
    provincia, municipio = provincia_municipio
    user = User.objects.create_user(username="disp-viewer", password="test1234")
    permiso_view = Permission.objects.get(
        content_type__app_label="dispositivos",
        codename="view_dispositivo",
    )
    user.user_permissions.add(permiso_view)
    _crear_dispositivo(
        provincia,
        municipio,
        indice=44556677,
        nombre_institucion="Dispositivo Solo Lectura",
        cuit_institucion="20445566777",
        responsable_dni="44556677",
    )

    client.force_login(user)
    response = client.get(reverse("dispositivos_listar"))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    assert "Dispositivo Solo Lectura" in contenido
    assert "Agregar dispositivo" not in contenido
    assert 'title="Editar"' not in contenido
    assert 'title="Eliminar"' not in contenido
    assert "Mapa de dispositivos" not in contenido
    assert "Ver en mapa" not in contenido


@pytest.mark.django_db
def test_listado_renderiza_paginacion_con_mas_de_quince_dispositivos(
    client, user_con_permisos, provincia_municipio
):
    provincia, municipio = provincia_municipio
    for indice in range(1, 17):
        _crear_dispositivo(provincia, municipio, indice=indice)

    client.force_login(user_con_permisos)
    response = client.get(reverse("dispositivos_listar"))

    assert response.status_code == 200
    assert "?page=2" in response.content.decode("utf-8")


@pytest.mark.django_db
def test_formulario_muestra_secciones_modernas(client, user_con_permisos):
    client.force_login(user_con_permisos)

    response = client.get(reverse("dispositivos_crear"))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    assert "Identificación del dispositivo" in contenido
    assert "Características del dispositivo" in contenido
    assert "Población destinataria" in contenido
    assert "Modalidad de ingreso" in contenido
    assert "Servicios brindados" in contenido
    assert "Sistema de registro de personas usuarias" in contenido
    assert "Infraestructura y necesidades" in contenido
    assert "Articulaciones institucionales" in contenido
    assert "Observaciones y documentación" in contenido
    assert "Progreso del Formulario" in contenido
    registro_detalle_index = contenido.index('id="registro-detalle"')
    assert (
        contenido.index('id="id_registra_informacion_personas"')
        < registro_detalle_index
    )
    assert (
        'class="d-none"'
        in contenido[registro_detalle_index : registro_detalle_index + 200]
    )


WRAPPERS_OTRO = [
    "wrapper-tipo_gestion_otra",
    "wrapper-tipo_dispositivo_otro",
    "wrapper-poblacion_destinataria_otro",
    "wrapper-tiempo_permanencia_otro",
    "wrapper-modalidad_ingreso_otro",
    "wrapper-documentacion_ingreso_otro",
    "wrapper-requisitos_ingreso_otro",
    "wrapper-servicios_brindados_otro",
    "wrapper-tipos_actividades_formativas_otro",
    "wrapper-modo_registro_otro",
    "wrapper-tipo_informacion_registrada_otro",
    "wrapper-infraestructura_disponible_otro",
    "wrapper-infraestructura_accesibilidad_otro",
    "wrapper-articulaciones_institucionales_otro",
]


def _tag_for(contenido, wrapper_id):
    needle = f'id="{wrapper_id}"'
    idx = contenido.find(needle)
    assert idx != -1, f"No se encontró {wrapper_id} en el template"
    tag_end = contenido.find(">", idx)
    return contenido[idx:tag_end]


def _doc_slot_tag(contenido, field):
    needle = f'data-field="{field}"'
    idx = contenido.find(needle)
    assert idx != -1, f"No se encontró slot {field} en el template"
    tag_start = contenido.rfind("<div", 0, idx)
    tag_end = contenido.find(">", idx)
    return contenido[tag_start:tag_end]


@pytest.mark.django_db
def test_formulario_oculta_todos_los_wrappers_otro_en_creacion(
    client, user_con_permisos
):
    client.force_login(user_con_permisos)

    response = client.get(reverse("dispositivos_crear"))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    for wrapper_id in WRAPPERS_OTRO:
        tag = _tag_for(contenido, wrapper_id)
        assert "d-none" in tag, f"{wrapper_id} debe iniciar con d-none"


@pytest.mark.django_db
def test_formulario_muestra_wrappers_otro_cuando_dispositivo_tiene_valor(
    client, user_con_permisos, provincia_municipio
):
    provincia, municipio = provincia_municipio
    client.force_login(user_con_permisos)

    dispositivo = _crear_dispositivo(
        provincia,
        municipio,
        indice=99887766,
        nombre_institucion="Dispositivo Otros",
        cuit_institucion="20998877661",
        responsable_dni="99887766",
        tipo_gestion="otra",
        tipo_gestion_otra="Cooperativa local",
        tipo_dispositivo="otro",
        tipo_dispositivo_otro="Centro mixto",
        poblacion_destinataria=["otro"],
        poblacion_destinataria_otro="Personas migrantes",
        tiempo_permanencia_promedio="otro",
        tiempo_permanencia_otro="Variable",
        modalidad_ingreso=["otro"],
        modalidad_ingreso_otro="Acuerdo municipal",
        documentacion_ingreso=["otro"],
        documentacion_ingreso_otro="Acta",
        requisitos_ingreso=["otro"],
        requisitos_ingreso_otro="Compromiso",
        servicios_brindados=["otro"],
        servicios_brindados_otro="Talleres",
        registra_informacion_personas="si",
        modo_registro="otro",
        modo_registro_otro="Sistema propio",
        tipo_informacion_registrada=["otro"],
        tipo_informacion_registrada_otro="Trayectoria",
        infraestructura_disponible=["otro"],
        infraestructura_disponible_otro="Patio",
        infraestructura_accesibilidad=["otro"],
        infraestructura_accesibilidad_otro="Ascensor",
        articulaciones_institucionales=["otro"],
        articulaciones_institucionales_otro="Iglesia local",
        ofrece_actividades_formativas="si",
        tipos_actividades_formativas=["otro"],
        tipos_actividades_formativas_otro="Talleres ad-hoc",
    )

    response = client.get(reverse("dispositivos_editar", kwargs={"pk": dispositivo.pk}))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    for wrapper_id in WRAPPERS_OTRO:
        tag = _tag_for(contenido, wrapper_id)
        assert (
            "d-none" not in tag
        ), f"{wrapper_id} no debe tener d-none cuando 'otro' está seleccionado"


def _doc_slot_tag(contenido, field):
    needle = f'data-field="{field}"'
    idx = contenido.find(needle)
    assert idx != -1, f"No se encontró slot {field} en el template"
    tag_start = contenido.rfind("<div", 0, idx)
    tag_end = contenido.find(">", idx)
    return contenido[tag_start:tag_end]


@pytest.mark.django_db
def test_formulario_solo_muestra_primer_slot_documento_en_creacion(
    client, user_con_permisos
):
    client.force_login(user_con_permisos)

    response = client.get(reverse("dispositivos_crear"))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    principal_tag = _doc_slot_tag(contenido, "documentacion_dispositivo")
    assert "d-none" not in principal_tag, "El slot principal debe ser visible"

    for field in [
        "documentacion_dispositivo_adicional_1",
        "documentacion_dispositivo_adicional_2",
        "documentacion_dispositivo_adicional_3",
        "documentacion_dispositivo_adicional_4",
    ]:
        tag = _doc_slot_tag(contenido, field)
        assert "d-none" in tag, f"Slot {field} debe iniciar oculto"

    assert 'id="btn-add-doc"' in contenido
    assert "Añadir archivo" in contenido


@pytest.mark.django_db
def test_formulario_muestra_slots_con_documentacion_persistida_en_edicion(
    client, user_con_permisos, provincia_municipio
):
    provincia, municipio = provincia_municipio
    client.force_login(user_con_permisos)

    dispositivo = _crear_dispositivo(
        provincia,
        municipio,
        indice=55667788,
        nombre_institucion="Dispositivo con docs",
        cuit_institucion="20556677881",
        responsable_dni="55667788",
    )
    dispositivo.documentacion_dispositivo_adicional_2.save(
        "doc-2.pdf",
        SimpleUploadedFile("doc-2.pdf", b"x", content_type="application/pdf"),
        save=True,
    )

    response = client.get(reverse("dispositivos_editar", kwargs={"pk": dispositivo.pk}))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    tag_2 = _doc_slot_tag(contenido, "documentacion_dispositivo_adicional_2")
    assert "d-none" not in tag_2, "El slot con archivo persistido debe ser visible"
    tag_3 = _doc_slot_tag(contenido, "documentacion_dispositivo_adicional_3")
    assert "d-none" in tag_3, "Slots sin archivo deben mantenerse ocultos"


@pytest.mark.django_db
def test_formulario_micro_ajustes_visibles(client, user_con_permisos):
    client.force_login(user_con_permisos)

    response = client.get(reverse("dispositivos_crear"))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    assert "La Razón Social es la identidad jurídica" in contenido
    assert "Ninguna de las anteriores" in contenido
    assert 'inputmode="numeric"' in contenido
    assert "Debe ingresar los 11 dígitos sin puntos ni guiones" in contenido
    limitaciones_idx = contenido.index('name="principales_limitaciones"')
    necesidades_idx = contenido.index('name="necesidades_prioritarias"')
    bloque_limitaciones = contenido[max(0, limitaciones_idx - 1500) : limitaciones_idx]
    bloque_necesidades = contenido[max(0, necesidades_idx - 1500) : necesidades_idx]
    assert (
        'class="col-md-12"' in bloque_limitaciones
    ), "Principales limitaciones debe estar en col-md-12"
    assert (
        'class="col-md-12"' in bloque_necesidades
    ), "Necesidades prioritarias debe estar en col-md-12"


DISPOSITIVOS_PERMISOS = [
    "add_dispositivo",
    "change_dispositivo",
    "delete_dispositivo",
    "view_dispositivo",
    "ver_mapa_dispositivo",
]


def _agregar_permisos_dispositivos(user):
    perms = Permission.objects.filter(
        content_type__app_label="dispositivos",
        codename__in=DISPOSITIVOS_PERMISOS,
    )
    user.user_permissions.add(*perms)


def _crear_usuario_provincial(
    username, *, provincia, municipio=None, localidad=None, scopes_extra=None
):
    user = User.objects.create_user(username=username, password="test1234")
    _agregar_permisos_dispositivos(user)
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.es_usuario_provincial = True
    profile.save()
    ProfileTerritorialScope.objects.create(
        profile=profile, provincia=provincia, municipio=municipio, localidad=localidad
    )
    for extra in scopes_extra or []:
        ProfileTerritorialScope.objects.create(profile=profile, **extra)
    return user


def _crear_usuario_provincial_sin_alcance(username):
    user = User.objects.create_user(username=username, password="test1234")
    _agregar_permisos_dispositivos(user)
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.es_usuario_provincial = True
    profile.save()
    return user


def _form_post_data(provincia, municipio, **overrides):
    data = {
        "nombre_institucion": "Dispositivo Scope",
        "tipo_gestion": "estatal",
        "cuit_institucion": "20123456789",
        "provincia": provincia.id,
        "municipio": municipio.id,
        "calle": "Calle 1",
        "altura": "123",
        "telefono_prefijo": "221",
        "telefono_numero": "1234567",
        "responsable_nombre_completo": "Juan Perez",
        "responsable_dni": "12345678",
        "tipo_dispositivo": "refugio",
        "modalidad_funcionamiento": "permanente",
        "capacidad_total_plazas": "16_30",
    }
    data.update(overrides)
    return data


@pytest.fixture
def dos_provincias(db):
    provincia_a = Provincia.objects.create(nombre="Buenos Aires")
    provincia_b = Provincia.objects.create(nombre="Cordoba")
    municipio_a = Municipio.objects.create(nombre="La Plata", provincia=provincia_a)
    municipio_b = Municipio.objects.create(nombre="Capital", provincia=provincia_b)
    return provincia_a, municipio_a, provincia_b, municipio_b


@pytest.mark.django_db
def test_listado_usuario_provincial_ve_solo_su_provincia(client, dos_provincias):
    provincia_a, municipio_a, provincia_b, municipio_b = dos_provincias
    _crear_dispositivo(
        provincia_a, municipio_a, indice=1, nombre_institucion="Disp Provincia A"
    )
    _crear_dispositivo(
        provincia_b, municipio_b, indice=2, nombre_institucion="Disp Provincia B"
    )
    user = _crear_usuario_provincial("prov-a", provincia=provincia_a)

    client.force_login(user)
    response = client.get(reverse("dispositivos_listar"))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    assert "Disp Provincia A" in contenido
    assert "Disp Provincia B" not in contenido


@pytest.mark.django_db
def test_listado_usuario_provincial_con_municipio_ve_solo_su_municipio(
    client, dos_provincias
):
    provincia_a, municipio_a, _provincia_b, _municipio_b = dos_provincias
    otro_municipio = Municipio.objects.create(nombre="Quilmes", provincia=provincia_a)
    _crear_dispositivo(
        provincia_a, municipio_a, indice=3, nombre_institucion="Disp Municipio A1"
    )
    _crear_dispositivo(
        provincia_a, otro_municipio, indice=4, nombre_institucion="Disp Municipio A2"
    )
    user = _crear_usuario_provincial(
        "prov-a-muni", provincia=provincia_a, municipio=municipio_a
    )

    client.force_login(user)
    response = client.get(reverse("dispositivos_listar"))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    assert "Disp Municipio A1" in contenido
    assert "Disp Municipio A2" not in contenido


@pytest.mark.django_db
def test_listado_usuario_sin_provincia_ve_todos(
    client, user_con_permisos, dos_provincias
):
    provincia_a, municipio_a, provincia_b, municipio_b = dos_provincias
    _crear_dispositivo(
        provincia_a, municipio_a, indice=5, nombre_institucion="Disp Libre A"
    )
    _crear_dispositivo(
        provincia_b, municipio_b, indice=6, nombre_institucion="Disp Libre B"
    )

    client.force_login(user_con_permisos)
    response = client.get(reverse("dispositivos_listar"))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    assert "Disp Libre A" in contenido
    assert "Disp Libre B" in contenido


@pytest.mark.django_db
def test_listado_superusuario_ve_todos(client, dos_provincias):
    provincia_a, municipio_a, provincia_b, municipio_b = dos_provincias
    _crear_dispositivo(
        provincia_a, municipio_a, indice=7, nombre_institucion="Disp Admin A"
    )
    _crear_dispositivo(
        provincia_b, municipio_b, indice=8, nombre_institucion="Disp Admin B"
    )
    admin = User.objects.create_superuser(
        username="admin-disp", password="test1234", email="admin@example.com"
    )

    client.force_login(admin)
    response = client.get(reverse("dispositivos_listar"))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    assert "Disp Admin A" in contenido
    assert "Disp Admin B" in contenido


@pytest.mark.django_db
def test_detalle_usuario_provincial_accede_en_su_provincia(client, dos_provincias):
    provincia_a, municipio_a, _provincia_b, _municipio_b = dos_provincias
    dispositivo = _crear_dispositivo(provincia_a, municipio_a, indice=9)
    user = _crear_usuario_provincial("prov-a-detalle", provincia=provincia_a)

    client.force_login(user)
    response = client.get(
        reverse("dispositivos_detalle", kwargs={"pk": dispositivo.pk})
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_detalle_usuario_provincial_bloqueado_fuera_de_provincia(
    client, dos_provincias
):
    provincia_a, _municipio_a, provincia_b, municipio_b = dos_provincias
    dispositivo_b = _crear_dispositivo(provincia_b, municipio_b, indice=10)
    user = _crear_usuario_provincial("prov-a-bloqueo", provincia=provincia_a)

    client.force_login(user)
    response = client.get(
        reverse("dispositivos_detalle", kwargs={"pk": dispositivo_b.pk})
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_editar_usuario_provincial_bloqueado_fuera_de_provincia(client, dos_provincias):
    provincia_a, _municipio_a, provincia_b, municipio_b = dos_provincias
    dispositivo_b = _crear_dispositivo(provincia_b, municipio_b, indice=12)
    user = _crear_usuario_provincial("prov-a-editar", provincia=provincia_a)

    client.force_login(user)
    response = client.get(
        reverse("dispositivos_editar", kwargs={"pk": dispositivo_b.pk})
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_formulario_creacion_restringe_provincias(client, dos_provincias):
    provincia_a, _municipio_a, provincia_b, _municipio_b = dos_provincias
    user = _crear_usuario_provincial("prov-a-form", provincia=provincia_a)

    client.force_login(user)
    response = client.get(reverse("dispositivos_crear"))

    assert response.status_code == 200
    provincia_ids = set(
        response.context["form"]
        .fields["provincia"]
        .queryset.values_list("id", flat=True)
    )
    assert provincia_a.id in provincia_ids
    assert provincia_b.id not in provincia_ids


@pytest.mark.django_db
def test_creacion_rechaza_provincia_fuera_de_scope(client, dos_provincias):
    provincia_a, _municipio_a, provincia_b, municipio_b = dos_provincias
    user = _crear_usuario_provincial("prov-a-post", provincia=provincia_a)

    client.force_login(user)
    response = client.post(
        reverse("dispositivos_crear"),
        data=_form_post_data(provincia_b, municipio_b),
    )

    assert response.status_code == 200
    assert not Dispositivo.objects.filter(provincia=provincia_b).exists()


@pytest.mark.django_db
def test_listado_usuario_con_alcance_localidad_ve_su_municipio(client, dos_provincias):
    # El modelo Dispositivo no tiene localidad: un alcance a nivel localidad
    # debe respetarse hasta su municipio (decisión de diseño del fix #1824).
    provincia_a, municipio_a, _provincia_b, _municipio_b = dos_provincias
    otro_municipio = Municipio.objects.create(nombre="Berisso", provincia=provincia_a)
    localidad = Localidad.objects.create(nombre="Centro", municipio=municipio_a)
    _crear_dispositivo(
        provincia_a, municipio_a, indice=13, nombre_institucion="Disp Loc Municipio"
    )
    _crear_dispositivo(
        provincia_a, otro_municipio, indice=14, nombre_institucion="Disp Otro Municipio"
    )
    user = _crear_usuario_provincial(
        "prov-a-loc",
        provincia=provincia_a,
        municipio=municipio_a,
        localidad=localidad,
    )

    client.force_login(user)
    response = client.get(reverse("dispositivos_listar"))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    assert "Disp Loc Municipio" in contenido
    assert "Disp Otro Municipio" not in contenido


@pytest.mark.django_db
def test_listado_usuario_multiprovincia_ve_ambas(client, dos_provincias):
    provincia_a, municipio_a, provincia_b, municipio_b = dos_provincias
    _crear_dispositivo(
        provincia_a, municipio_a, indice=15, nombre_institucion="Disp Multi A"
    )
    _crear_dispositivo(
        provincia_b, municipio_b, indice=16, nombre_institucion="Disp Multi B"
    )
    user = _crear_usuario_provincial(
        "prov-multi",
        provincia=provincia_a,
        scopes_extra=[{"provincia": provincia_b}],
    )

    client.force_login(user)
    response = client.get(reverse("dispositivos_listar"))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    assert "Disp Multi A" in contenido
    assert "Disp Multi B" in contenido


@pytest.mark.django_db
def test_listado_usuario_provincial_sin_alcance_no_ve_nada(client, dos_provincias):
    provincia_a, municipio_a, provincia_b, municipio_b = dos_provincias
    _crear_dispositivo(
        provincia_a, municipio_a, indice=17, nombre_institucion="Disp Sin Alcance A"
    )
    _crear_dispositivo(
        provincia_b, municipio_b, indice=18, nombre_institucion="Disp Sin Alcance B"
    )
    user = _crear_usuario_provincial_sin_alcance("prov-sin-alcance")

    client.force_login(user)
    response = client.get(reverse("dispositivos_listar"))

    assert response.status_code == 200
    contenido = response.content.decode("utf-8")
    assert "Disp Sin Alcance A" not in contenido
    assert "Disp Sin Alcance B" not in contenido


@pytest.mark.django_db
def test_eliminar_usuario_provincial_bloqueado_fuera_de_provincia(
    client, dos_provincias
):
    provincia_a, _municipio_a, provincia_b, municipio_b = dos_provincias
    dispositivo_b = _crear_dispositivo(provincia_b, municipio_b, indice=19)
    user = _crear_usuario_provincial("prov-a-eliminar", provincia=provincia_a)

    client.force_login(user)
    response = client.post(
        reverse("dispositivos_eliminar", kwargs={"pk": dispositivo_b.pk})
    )

    assert response.status_code == 404
    assert Dispositivo.objects.filter(pk=dispositivo_b.pk).exists()


@pytest.mark.django_db
def test_form_municipio_vacio_para_provincia_fuera_de_alcance(dos_provincias):
    # Defensa en profundidad: aunque el campo provincia ya rechaza una provincia
    # fuera de alcance, el queryset de municipio no debe ofrecer opciones de esa
    # provincia.
    provincia_a, municipio_a, provincia_b, _municipio_b = dos_provincias
    user = _crear_usuario_provincial(
        "prov-a-form-hard", provincia=provincia_a, municipio=municipio_a
    )

    form = DispositivoForm(data={"provincia": provincia_b.id}, user=user)

    assert not form.fields["municipio"].queryset.exists()


@pytest.mark.django_db
def test_mapa_requiere_permiso(client):
    url = reverse("dispositivos_mapa")
    assert client.get(url).status_code == 403
    user = User.objects.create_user(username="mapa-sin-permiso")
    client.force_login(user)
    assert client.get(url).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "codenames",
    [["view_dispositivo"], ["ver_mapa_dispositivo"]],
)
def test_mapa_y_ubicacion_requieren_ambos_permisos(
    client, provincia_municipio, codenames
):
    provincia, municipio = provincia_municipio
    device = _crear_dispositivo(provincia, municipio, indice=1)
    user = User.objects.create_user(username="mapa-permiso-parcial")
    user.user_permissions.add(
        *Permission.objects.filter(
            content_type__app_label="dispositivos", codename__in=codenames
        )
    )
    client.force_login(user)
    assert client.get(reverse("dispositivos_mapa")).status_code == 403
    assert (
        client.get(reverse("dispositivos_ubicacion", args=[device.pk])).status_code
        == 403
    )


@pytest.mark.django_db
def test_mapa_incluye_todos_y_respeta_filtros(
    client, user_con_permisos, provincia_municipio
):
    provincia, municipio = provincia_municipio
    for indice in range(16):
        _crear_dispositivo(provincia, municipio, indice=indice)
    client.force_login(user_con_permisos)
    response = client.get(reverse("dispositivos_mapa"))
    assert response.status_code == 200
    assert len(response.context["map_devices"]) == 16
    response = client.get(reverse("dispositivos_mapa"), {"busqueda": "Dispositivo 15"})
    assert len(response.context["map_devices"]) == 1
    assert response.context["map_devices"][0]["name"] == "Dispositivo 15"
    assert "responsable_dni" not in response.context["map_devices"][0]
    response = client.get(
        reverse("dispositivos_listar"), {"busqueda": "Rosario", "page": "1"}
    )
    assert (
        response.context["map_url"]
        == reverse("dispositivos_mapa") + "?busqueda=Rosario"
    )


@pytest.mark.django_db
def test_mapa_y_ubicacion_respetan_scope(client, dos_provincias, monkeypatch):
    provincia_a, municipio_a, provincia_b, municipio_b = dos_provincias
    visible = _crear_dispositivo(provincia_a, municipio_a, indice=1)
    hidden = _crear_dispositivo(provincia_b, municipio_b, indice=2)
    user = _crear_usuario_provincial("mapa-provincial", provincia=provincia_a)
    client.force_login(user)
    response = client.get(reverse("dispositivos_mapa"))
    assert [d["id"] for d in response.context["map_devices"]] == [visible.pk]

    def forbidden_lookup(_device):
        pytest.fail("No debe geocodificar dispositivos fuera del alcance")

    monkeypatch.setattr("dispositivos.views.geolocate_dispositivo", forbidden_lookup)
    assert (
        client.get(reverse("dispositivos_ubicacion", args=[hidden.pk])).status_code
        == 404
    )


@pytest.mark.django_db
def test_ubicacion_respuesta_y_fallback(
    client, user_con_permisos, provincia_municipio, monkeypatch
):
    provincia, municipio = provincia_municipio
    device = _crear_dispositivo(provincia, municipio)
    client.force_login(user_con_permisos)
    url = reverse("dispositivos_ubicacion", args=[device.pk])
    monkeypatch.setattr(
        "dispositivos.views.geolocate_dispositivo",
        lambda _: {"status": "located", "lat": -34.9, "lon": -57.9},
    )
    response = client.get(url)
    assert response.json() == {"status": "located", "lat": -34.9, "lon": -57.9}
    assert response["Cache-Control"] == "private, no-store"
    monkeypatch.setattr(
        "dispositivos.views.geolocate_dispositivo", lambda _: {"status": "unavailable"}
    )
    assert client.get(url).status_code == 503


@pytest.mark.django_db
def test_mapa_listado_con_filtros_combinables(
    client, user_con_permisos, provincia_municipio
):
    import json

    provincia, municipio = provincia_municipio
    visible = _crear_dispositivo(
        provincia, municipio, indice=1, tipo_dispositivo="refugio"
    )
    _crear_dispositivo(
        provincia, municipio, indice=2, tipo_dispositivo="hogar_transito"
    )
    client.force_login(user_con_permisos)
    url = reverse("dispositivos_mapa")
    filters = json.dumps(
        {"items": [{"field": "tipo_dispositivo", "op": "eq", "value": "refugio"}]}
    )
    response = client.get(url, {"filters": filters})
    assert response.status_code == 200
    assert [device["id"] for device in response.context["map_devices"]] == [visible.pk]
    assert response.context["filters_action"] == url
    assert response.context["reset_url"] == url
    content = response.content.decode()
    assert 'id="filters-form"' in content
    assert f'data-map-focus="{visible.pk}"' in content
    assert "Ver en mapa" in content
    assert "Ver detalle" in content


@pytest.mark.django_db
def test_mapa_contacto_provincias_y_seleccion(
    client, user_con_permisos, provincia_municipio
):
    provincia, municipio = provincia_municipio
    device = _crear_dispositivo(provincia, municipio)
    client.force_login(user_con_permisos)
    url = reverse("dispositivos_mapa")
    response = client.get(url, {"dispositivo": device.pk})
    data = response.context["map_devices"][0]
    assert data["representative"] == "Ana Lopez"
    assert data["phone"] == "221 9876543"
    assert data["province_id"] == provincia.pk
    assert "responsable_dni" not in data
    assert response.context["map_provinces"] == [(provincia.pk, provincia.nombre)]
    assert response.context["map_initial_device"] == device.pk
    assert (
        client.get(url, {"dispositivo": "invalido"}).context["map_initial_device"] == ""
    )
    response = client.get(reverse("dispositivos_listar"))
    content = response.content.decode()
    assert "Mapa de dispositivos" in content
    assert f"dispositivo={device.pk}" in content
    assert "Ver en mapa" in content
    assert "Ver detalle" in content


@pytest.mark.django_db
def test_mapa_tiene_un_solo_buscador_sin_boton_ver_mapa(
    client, user_con_permisos, provincia_municipio
):
    import json

    provincia, municipio = provincia_municipio
    _crear_dispositivo(provincia, municipio)
    client.force_login(user_con_permisos)
    filters = json.dumps(
        {"items": [{"field": "estado_ubicacion", "op": "eq", "value": "located"}]}
    )
    response = client.get(reverse("dispositivos_mapa"), {"filters": filters})
    assert response.status_code == 200
    assert response.context["map_url"] is None
    assert response.context["map_location_filters"][0]["value"] == "located"
    fields = {
        field["name"]: field for field in response.context["filters_config"]["fields"]
    }
    assert fields["provincia"]["type"] == "choice"
    assert fields["estado_ubicacion"]["type"] == "choice"
    content = response.content.decode()
    assert content.count('id="filters-form"') == 1
    assert 'id="map-province-filter"' not in content
    assert 'id="map-location-filter"' not in content
    assert ">Ver mapa" not in content


@pytest.mark.django_db
def test_mapa_incluye_ubicacion_guardada_vigente(
    client, user_con_permisos, provincia_municipio, monkeypatch
):
    from dispositivos.services import geolocate_dispositivo
    from unittest.mock import Mock

    provincia, municipio = provincia_municipio
    device = _crear_dispositivo(provincia, municipio)
    monkeypatch.setattr(
        "core.services.geolocation.requests.get",
        Mock(
            return_value=Mock(
                raise_for_status=Mock(),
                json=Mock(
                    return_value={
                        "total": 1,
                        "direcciones": [{"ubicacion": {"lat": -34.9, "lon": -57.9}}],
                    }
                ),
            )
        ),
    )
    geolocate_dispositivo(device)
    client.force_login(user_con_permisos)
    response = client.get(reverse("dispositivos_mapa"))
    assert response.context["map_devices"][0]["location"] == {
        "status": "located",
        "lat": -34.9,
        "lon": -57.9,
    }
    device.altura = "900"
    device.save()
    response = client.get(reverse("dispositivos_mapa"))
    assert response.context["map_devices"][0]["location"] is None


@pytest.mark.django_db
def test_mapa_opciones_de_provincia_no_dependen_del_filtro(
    client, user_con_permisos, dos_provincias
):
    import json

    provincia_a, municipio_a, provincia_b, municipio_b = dos_provincias
    _crear_dispositivo(provincia_a, municipio_a, indice=1)
    _crear_dispositivo(provincia_b, municipio_b, indice=2)
    client.force_login(user_con_permisos)
    filters = json.dumps(
        {"items": [{"field": "provincia", "op": "eq", "value": provincia_a.nombre}]}
    )
    response = client.get(reverse("dispositivos_mapa"), {"filters": filters})
    assert len(response.context["map_devices"]) == 1
    assert set(response.context["map_provinces"]) == {
        (provincia_a.pk, provincia_a.nombre),
        (provincia_b.pk, provincia_b.nombre),
    }


@pytest.mark.django_db
def test_ficha_mapa_coordenadas_y_edicion(
    client, user_con_permisos, provincia_municipio
):
    provincia, municipio = provincia_municipio
    device = _crear_dispositivo(provincia, municipio, latitud="-34.9", longitud="-57.9")
    client.force_login(user_con_permisos)
    response = client.get(reverse("dispositivos_detalle", args=[device.pk]))
    assert response.status_code == 200
    assert response.context["mapa_query"] == "-34.900000%2C-57.900000"
    assert b'id="dispositivo-mapa"' in response.content
    response = client.get(reverse("dispositivos_editar", args=[device.pk]))
    assert response.status_code == 200
    for name in ("localidad", "latitud", "longitud"):
        assert f'id="id_{name}"'.encode() in response.content
    assert b"Previsualizar" in response.content
    device.refresh_from_db()
    assert str(device.latitud) == "-34.900000"


@pytest.mark.django_db
def test_ficha_sin_permiso_de_mapa_no_muestra_mapa(client, provincia_municipio):
    provincia, municipio = provincia_municipio
    device = _crear_dispositivo(provincia, municipio, latitud="-34.9", longitud="-57.9")
    user = User.objects.create_user(username="solo-ficha")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="dispositivos", codename="view_dispositivo"
        )
    )
    client.force_login(user)
    response = client.get(reverse("dispositivos_detalle", args=[device.pk]))
    assert response.status_code == 200
    assert "mapa_query" not in response.context
    assert b'id="dispositivo-mapa"' not in response.content


@pytest.mark.django_db
def test_edicion_coordenadas_requiere_permiso(client, provincia_municipio):
    provincia, municipio = provincia_municipio
    device = _crear_dispositivo(provincia, municipio, latitud="-34.9", longitud="-57.9")
    user = User.objects.create_user(username="solo-lectura")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="dispositivos", codename="view_dispositivo"
        )
    )
    client.force_login(user)
    response = client.post(
        reverse("dispositivos_editar", args=[device.pk]),
        {"latitud": "0", "longitud": "0"},
    )
    assert response.status_code == 403
    device.refresh_from_db()
    assert str(device.latitud) == "-34.900000"


@pytest.mark.django_db
def test_editor_pin_solo_en_formulario_y_guardado_en_legajo(
    client, user_con_permisos, provincia_municipio
):
    provincia, municipio = provincia_municipio
    device = _crear_dispositivo(provincia, municipio, latitud="-34.9", longitud="-57.9")
    client.force_login(user_con_permisos)
    edit_url = reverse("dispositivos_editar", args=[device.pk])
    response = client.get(edit_url)
    assert response.status_code == 200
    assert b"data-pin-editor" in response.content
    assert b'data-latitude-field="id_latitud"' in response.content
    assert (
        reverse("dispositivos_ubicacion", args=[device.pk]).encode() in response.content
    )
    device.refresh_from_db()
    assert str(device.latitud) == "-34.900000"
    payload = _form_post_data(
        provincia,
        municipio,
        latitud="-34.123456",
        longitud="-58.123456",
        calle=device.calle,
        altura=device.altura,
    )
    response = client.post(edit_url, payload)
    assert response.status_code == 302
    device.refresh_from_db()
    assert str(device.latitud) == "-34.123456"
    assert str(device.longitud) == "-58.123456"
    assert device.calle == payload["calle"]
    assert device.altura == payload["altura"]
    response = client.get(reverse("dispositivos_detalle", args=[device.pk]))
    assert response.status_code == 200
    assert response.context["mapa_query"] == "-34.123456%2C-58.123456"
    assert b"data-pin-editor" not in response.content


@pytest.mark.django_db
def test_guardado_pin_invalido_conserva_coordenadas(
    client, user_con_permisos, provincia_municipio
):
    provincia, municipio = provincia_municipio
    device = _crear_dispositivo(provincia, municipio, latitud="-34.9", longitud="-57.9")
    client.force_login(user_con_permisos)
    response = client.post(
        reverse("dispositivos_editar", args=[device.pk]),
        _form_post_data(provincia, municipio, latitud="91", longitud="0"),
    )
    assert response.status_code == 200
    assert "latitud" in response.context["form"].errors
    device.refresh_from_db()
    assert str(device.latitud) == "-34.900000"
    assert str(device.longitud) == "-57.900000"


@pytest.mark.django_db
def test_busqueda_domicilio_en_borrador_no_guarda(
    client, user_con_permisos, provincia_municipio, monkeypatch
):
    provincia, municipio = provincia_municipio
    client.force_login(user_con_permisos)
    count = Dispositivo.objects.count()
    locations = []

    def locate(device):
        locations.append(device)
        return {"status": "located", "lat": -34.9, "lon": -57.9}

    monkeypatch.setattr("dispositivos.views.geolocate_dispositivo", locate)
    response = client.post(
        reverse("dispositivos_previsualizar_ubicacion"),
        {
            "provincia": provincia.pk,
            "municipio": municipio.pk,
            "calle": "Domicilio nuevo",
            "altura": "123",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "located", "lat": -34.9, "lon": -57.9}
    assert locations[0].pk is None
    assert locations[0].calle == "Domicilio nuevo"
    assert locations[0].municipio == municipio
    assert Dispositivo.objects.count() == count
    assert response["Cache-Control"] == "private, no-store"


@pytest.mark.django_db
def test_busqueda_domicilio_rechaza_geografia_invalida(
    client, user_con_permisos, dos_provincias, monkeypatch
):
    provincia_a, municipio_a, provincia_b, municipio_b = dos_provincias
    client.force_login(user_con_permisos)
    monkeypatch.setattr(
        "dispositivos.views.geolocate_dispositivo",
        lambda _: pytest.fail("No debe buscar una dirección inválida"),
    )
    response = client.post(
        reverse("dispositivos_previsualizar_ubicacion"),
        {
            "provincia": provincia_a.pk,
            "municipio": municipio_b.pk,
            "calle": "Calle",
            "altura": "123",
        },
    )
    assert response.status_code == 400
    assert "municipio" in response.json()["errors"]
    response = client.post(reverse("dispositivos_previsualizar_ubicacion"), {})
    assert response.status_code == 400
    assert "calle" in response.json()["errors"]


@pytest.mark.django_db
def test_busqueda_domicilio_respeta_alcance_territorial(
    client, dos_provincias, monkeypatch
):
    provincia_a, municipio_a, provincia_b, municipio_b = dos_provincias
    user = _crear_usuario_provincial("pin-provincia", provincia=provincia_a)
    client.force_login(user)
    monkeypatch.setattr(
        "dispositivos.views.geolocate_dispositivo",
        lambda _: pytest.fail("No debe buscar fuera de alcance"),
    )
    response = client.post(
        reverse("dispositivos_previsualizar_ubicacion"),
        {
            "provincia": provincia_b.pk,
            "municipio": municipio_b.pk,
            "calle": "Calle",
            "altura": "123",
        },
    )
    assert response.status_code == 400
    assert "provincia" in response.json()["errors"]


@pytest.mark.django_db
def test_busqueda_domicilio_requiere_permiso_y_csrf(
    client, user_con_permisos, provincia_municipio
):
    from django.test import Client

    url = reverse("dispositivos_previsualizar_ubicacion")
    user = User.objects.create_user(username="pin-sin-edicion")
    user.user_permissions.add(
        Permission.objects.get(
            content_type__app_label="dispositivos", codename="view_dispositivo"
        )
    )
    client.force_login(user)
    assert client.post(url).status_code == 403
    protected = Client(enforce_csrf_checks=True)
    protected.force_login(user_con_permisos)
    assert protected.post(url).status_code == 403


@pytest.mark.django_db
def test_busqueda_domicilio_servicio_no_disponible(
    client, user_con_permisos, provincia_municipio, monkeypatch
):
    provincia, municipio = provincia_municipio
    client.force_login(user_con_permisos)
    monkeypatch.setattr(
        "dispositivos.views.geolocate_dispositivo", lambda _: {"status": "unavailable"}
    )
    response = client.post(
        reverse("dispositivos_previsualizar_ubicacion"),
        {
            "provincia": provincia.pk,
            "municipio": municipio.pk,
            "calle": "Calle",
            "altura": "123",
        },
    )
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
